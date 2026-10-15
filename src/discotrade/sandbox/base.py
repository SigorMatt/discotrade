"""The sandbox interface, the job and the result (DESIGN 12.4, 6.2, 5.6, 4.1; decision
95 of 2026-10-14-m12 (a), (d), (e); decisions 2026-10-12 23, 24, 36, 37; I-2, I-7, I-13).

A :class:`SandboxJob` is a source text or, for the in-process backend only, a
function object; parameter sets; a mode, ``positions`` or ``reverse_sample``;
per instrument the bars of the window with their context
(:class:`JobInstrument`); and the limits. :func:`build_job` builds one for a
window: per instrument, the stored window bars and, before them, the context
up to ``history_cap_bars`` (decision 23: ``history_cap_bars - 1`` bars, so
that the slice at the first window bar holds the cap), all read through
:func:`discotrade.backtest.read_window`, so that no bar before
``trusted_from`` (decision 36) and none whose trading date is after the
window's last day is in it; the roll flag and gap of every bar, from the roll
records (decisions 24, 37); ``hour`` and ``weekday`` in the calendar's time
zone; and ``shorting``.

:func:`write_job` writes a job carrying a source text to a directory in the
layout :mod:`discotrade.sandbox.runner` reads (``job.json`` and one ``.npz``
per instrument, no symbol and no timestamp in either). A backend that runs
the runner reads its standard output back with :func:`result_from_doc`. A
:class:`SandboxResult` holds, per parameter set (by index) and instrument (by
symbol), the window bars called (indices within the window), the target
``p(t)`` at each and the call times in milliseconds, or an error with its
stage, rule and text. The sandbox never computes a score; the harness does,
outside. No key is ever put in a job (I-13).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from discotrade.backtest import Window, _local_clock, read_window
from discotrade.config import Calendar, DateRange, Instrument, Track, load_run
from discotrade.sandbox.runner import ARRAYS, FORMAT, JOB_FILE, MODES, STAGES

__all__ = ["ARRAYS", "FORMAT", "JOB_FILE", "MODES", "STAGES", "JobInstrument", "Sandbox",
           "SandboxError", "SandboxJob", "SandboxLimits", "SandboxRefused", "SandboxResult",
           "SandboxUnavailable",
           "BACKENDS", "SandboxChoiceError", "build_job", "choose_backend", "job_arrays",
           "job_doc", "job_instrument", "limits_from_config", "open_backend",
           "result_from_doc", "write_job"]


class SandboxRefused(ValueError):
    """A backend refuses a job (DESIGN 12.4); ``rule`` names why."""

    def __init__(self, rule: str, message: str) -> None:
        self.rule = rule
        super().__init__(f"sandbox refused [{rule}]: {message}")


class SandboxUnavailable(RuntimeError):
    """A harness error: the sandbox cannot run a job at all (no container runtime,
    no image of the current tag, a runtime that could not start the container).
    Never a rejection of a submission (decision 102 (a) of 2026-10-14-m13)."""


@dataclass(frozen=True)
class SandboxLimits:
    """The limits a backend enforces from outside the runner (DESIGN 12.4), read
    from ``[sandbox]`` of ``run.toml`` by :func:`limits_from_config` (decision 96).
    ``cpu_seconds`` None means the wall-clock limit's value."""

    wall_seconds: float
    memory_bytes: int
    output_bytes: int
    cpu_seconds: float | None = None


@dataclass(frozen=True)
class JobInstrument:
    """One instrument's bars in a job: ``bars`` (columns ``ts``, ``open``, ``high``,
    ``low``, ``close``, ``volume``, ``hour``, ``weekday``, ``rolled``, ``gap``),
    context first, ``bars.iloc[first]`` the first window bar; ``sample`` the
    window-bar indices of mode ``reverse_sample``. ``ts`` stays with the harness:
    :func:`write_job` does not write it."""

    symbol: str
    bars: pd.DataFrame
    first: int
    shorting: bool
    sample: tuple[int, ...] | None = None

    @property
    def window_bars(self) -> int:
        return len(self.bars) - self.first


@dataclass(frozen=True)
class SandboxJob:
    instruments: tuple[JobInstrument, ...]
    param_sets: tuple[dict[str, Any], ...]
    mode: str
    history_cap_bars: int
    limits: SandboxLimits
    source: str | None = None
    function: Callable[..., Any] | None = None


@dataclass(frozen=True)
class SandboxError:
    """A failed run: its stage (``load``, ``dry_run``, ``limit``), its rule, the
    parameter set and window bar where it happened (when known), and a text fit
    to send back to a worker (decision 95 (e))."""

    stage: str
    rule: str
    text: str
    param_set: int | None = None
    bar: int | None = None


@dataclass(frozen=True)
class SandboxResult:
    targets: dict[tuple[int, str], np.ndarray] = field(default_factory=dict)
    bars: dict[tuple[int, str], np.ndarray] = field(default_factory=dict)
    call_ms: dict[tuple[int, str], np.ndarray] = field(default_factory=dict)
    error: SandboxError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class Sandbox(Protocol):
    def run(self, job: SandboxJob) -> SandboxResult: ...


#: The backends the day loop, the replay and ``journal recompute`` run approaches on
#: (decision 105 (b) of 2026-10-14-m13).
BACKENDS = ("container", "process")
#: The adapter of a synthetic source (DESIGN 17).
SYNTHETIC = "synth"


class SandboxChoiceError(ValueError):
    """A backend asked for that the track does not allow (decision 105 (b)); the
    command exits 2."""


def choose_backend(instruments: Sequence[Instrument], asked: str | None = None) -> str:
    """The backend that runs approaches on a track of ``instruments`` (decision 105
    (b)): ``asked`` when given, else ``process`` when every instrument's source is
    synthetic (``adapter = "synth"``) and ``container`` otherwise. ``process`` asked
    for on a track holding any other source is refused (:class:`SandboxChoiceError`,
    naming DESIGN 12.4): the child-process backend is not a boundary and is allowed
    only for a run on synthetic sources."""
    synthetic = all(inst.source.adapter == SYNTHETIC for inst in instruments)
    if asked is None:
        return "process" if synthetic else "container"
    if asked not in BACKENDS:
        raise SandboxChoiceError(f"unknown sandbox backend {asked!r}; one of "
                                 f"{', '.join(BACKENDS)}")
    if asked == "process" and not synthetic:
        others = sorted(inst.symbol for inst in instruments
                        if inst.source.adapter != SYNTHETIC)
        raise SandboxChoiceError(
            f"--sandbox process is refused: the track holds {', '.join(others)}, whose "
            f"source is not synthetic; the child-process backend is allowed only for a run "
            f"on synthetic sources (DESIGN 12.4); use --sandbox container")
    return asked


def open_backend(name: str, scratch: Path, config_dir: Path) -> Sandbox:
    """The backend ``name`` of :data:`BACKENDS` for the day loop, the replay and
    ``journal recompute``, its job directories under ``scratch``, its settings from
    ``<config_dir>/run.toml``; ``process`` forks its children from the process's
    one fork server (decision 105 (e), O-20 of 2026-10-15), which lives until the
    process ends or the backend's ``close`` stops it."""
    if name == "process":
        from discotrade.sandbox.process import ProcessSandbox
        return ProcessSandbox(Path(scratch), fork_server=True)
    if name == "container":
        from discotrade.sandbox.container import ContainerSandbox
        return ContainerSandbox(Path(scratch), Path(config_dir))
    raise SandboxChoiceError(f"unknown sandbox backend {name!r}; one of {', '.join(BACKENDS)}")


def limits_from_config(config_dir: Path) -> SandboxLimits:
    """The limits of ``[sandbox]`` in ``<config_dir>/run.toml``; a configuration
    without the file is refused naming it (``ConfigError``, decision 96)."""
    s = load_run(config_dir).sandbox
    return SandboxLimits(wall_seconds=s.wall_seconds, memory_bytes=s.memory_bytes,
                         output_bytes=s.output_bytes, cpu_seconds=s.cpu_seconds)


def build_job(state_dir: Path, track: Track, instruments: Sequence[Instrument],
              calendars: Mapping[str, Calendar], window: DateRange, *,
              param_sets: Sequence[Mapping[str, Any]], limits: SandboxLimits | None = None,
              config_dir: Path | None = None,
              source: str | None = None, function: Callable[..., Any] | None = None,
              mode: str = "positions",
              samples: Mapping[str, Sequence[int]] | None = None) -> SandboxJob:
    """The job that runs ``source`` (or ``function``) on ``window`` of each of
    ``instruments``, in their order, under each of ``param_sets``. Its limits are
    ``limits``, or those of ``config_dir``'s ``run.toml`` (exactly one is given)."""
    if (limits is None) == (config_dir is None):
        raise ValueError("a job takes its limits from exactly one of limits and config_dir")
    if limits is None:
        limits = limits_from_config(Path(config_dir))
    if (source is None) == (function is None):
        raise ValueError("a job carries exactly one of a source text and a function object")
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; one of {', '.join(MODES)}")
    if mode == "reverse_sample" and samples is None:
        raise ValueError("mode reverse_sample needs a sample per instrument")
    cap = track.history_cap_bars
    out = []
    for inst in instruments:
        win = read_window(Path(state_dir), track, inst, calendars[inst.calendar], window)
        sample = None
        if mode == "reverse_sample":
            sample = tuple(int(i) for i in samples[inst.symbol])
        out.append(job_instrument(win, cap, sample))
    return SandboxJob(instruments=tuple(out),
                      param_sets=tuple(dict(p) for p in param_sets), mode=mode,
                      history_cap_bars=cap, limits=limits, source=source, function=function)


def job_instrument(win: Window, cap: int, sample: tuple[int, ...] | None = None
                   ) -> JobInstrument:
    """One instrument's part of a job from its window ``win`` (read by
    :func:`discotrade.backtest.read_window`): the window bars and, before them,
    at most ``cap - 1`` context bars (decision 23), with their clock, roll flags
    and gaps; ``sample`` the window-bar indices of mode ``reverse_sample``."""
    inst = win.instrument
    if win.empty:
        bars = win.bars.iloc[0:0]
        first = 0
        hour = weekday = np.zeros(0, dtype=np.int64)
        gaps, rolled = np.zeros(0), np.zeros(0, dtype=bool)
    else:
        start = max(0, win.first - cap + 1)
        bars = win.bars.iloc[start:].reset_index(drop=True)
        first = win.first - start
        hour, weekday = _local_clock(bars["ts"], win.calendar)
        gaps, rolled = win.gaps[start:], win.rolled[start:]
    frame = pd.DataFrame({
        "ts": bars["ts"].to_numpy(),
        **{col: bars[col].to_numpy(dtype=np.float64)
           for col in ("open", "high", "low", "close", "volume")},
        "hour": np.asarray(hour, dtype=np.int64),
        "weekday": np.asarray(weekday, dtype=np.int64),
        "rolled": np.asarray(rolled, dtype=bool),
        "gap": np.asarray(gaps, dtype=np.float64),
    })
    if sample is not None:
        n = len(frame) - first
        if any(not 0 <= i < n for i in sample) or len(set(sample)) != len(sample):
            raise ValueError(f"{inst.symbol}: the sample must be distinct window-bar "
                             f"indices in [0, {n})")
    return JobInstrument(inst.symbol, frame, first, bool(inst.shorting), sample)


def job_arrays(inst: JobInstrument) -> dict[str, np.ndarray]:
    """The arrays the runner reads for ``inst`` (``ARRAYS``)."""
    bars = inst.bars
    return {
        **{col: bars[col].to_numpy(dtype=np.float64)
           for col in ("open", "high", "low", "close", "volume")},
        "hour": bars["hour"].to_numpy(dtype=np.int64),
        "weekday": bars["weekday"].to_numpy(dtype=np.int64),
        "rolled": bars["rolled"].to_numpy(dtype=bool),
        "gap": bars["gap"].to_numpy(dtype=np.float64),
    }


def job_doc(job: SandboxJob) -> dict[str, Any]:
    """``job.json``'s content, the source text aside (``source`` is None for a job
    carrying a function object)."""
    return {
        "format": FORMAT,
        "source": job.source,
        "params": [dict(p) for p in job.param_sets],
        "mode": job.mode,
        "history_cap_bars": job.history_cap_bars,
        "instruments": [
            {"bars": f"bars-{j}.npz", "first": inst.first, "shorting": inst.shorting,
             "sample": None if inst.sample is None else list(inst.sample)}
            for j, inst in enumerate(job.instruments)],
    }


def write_job(job: SandboxJob, directory: Path) -> Path:
    """Write ``job`` (a source text) to the new directory ``directory``; return it."""
    if job.source is None:
        raise SandboxRefused("function", "a job carrying a function object cannot be "
                             "written for the runner; only the in-process backend runs it")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    doc = job_doc(job)
    for meta, inst in zip(doc["instruments"], job.instruments, strict=True):
        with open(directory / meta["bars"], "wb") as handle:
            np.savez(handle, **job_arrays(inst))
    (directory / JOB_FILE).write_text(json_text(doc), encoding="utf-8")
    return directory


def json_text(doc: Mapping[str, Any]) -> str:
    """``doc`` as the text of ``job.json``."""
    return json.dumps(doc, sort_keys=True, allow_nan=False) + "\n"


def result_from_doc(job: SandboxJob, doc: Mapping[str, Any]) -> SandboxResult:
    """The :class:`SandboxResult` of the runner's result document for ``job``."""
    if not doc.get("ok"):
        e = doc["error"]
        if e["stage"] not in STAGES:
            raise ValueError(f"unknown stage {e['stage']!r} in a sandbox result")
        return SandboxResult(error=SandboxError(e["stage"], e["rule"], e["text"],
                                                e.get("param_set"), e.get("bar")))
    targets, bars, call_ms = {}, {}, {}
    for entry in doc["results"]:
        key = (int(entry["param_set"]), job.instruments[int(entry["instrument"])].symbol)
        targets[key] = np.asarray(entry["targets"], dtype=np.float64)
        bars[key] = np.asarray(entry["bars"], dtype=np.int64)
        call_ms[key] = np.asarray(entry["call_ms"], dtype=np.float64)
    return SandboxResult(targets=targets, bars=bars, call_ms=call_ms)
