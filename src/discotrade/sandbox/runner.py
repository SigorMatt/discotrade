"""The program that runs inside a sandbox (DESIGN 12.4, 6.2, 7.1, 5.6; decision 95 of
2026-10-14-m12 (b) to (e); decisions 2026-10-12 22, 24, 44; finding D-006; I-2, I-7).

It imports only the standard library, ``numpy``, ``pandas`` and
``discotrade.indicators`` (a test reads its imports), so that it runs in an
image that holds nothing else. Run as ``python -m discotrade.sandbox.runner
<job dir>``: it reads the job from the directory, writes its result as one
JSON document on standard output and exits 0; a missing argument exits 2 and
an unreadable job 1, with nothing on standard output.

The job directory (written by :func:`discotrade.sandbox.base.write_job`) holds
``job.json`` (the source text, the parameter sets, the mode, the history cap
and, per instrument, the index of its first window bar, whether it may be
shorted, the reverse sample and the name of its bar file) and one ``.npz``
file per instrument, read by ``numpy.load`` without pickles (no ``pyarrow``):
the raw ``open``, ``high``, ``low``, ``close``, ``volume`` of the window bars
and their context, ``hour`` and ``weekday`` in the calendar's time zone, and
the roll flag and gap of each bar. No symbol, contract, timestamp or date is in
the job.

For each parameter set and each instrument, in that order, the text is loaded
afresh in a namespace of its own (decision 44), with ``indicators`` bound as
:mod:`discotrade.strategy` binds it. At each window bar ``t`` (mode
``positions``), or at each bar of the instrument's sample in descending time
order (mode ``reverse_sample``, all inside this one process), the slice of
DESIGN 6.2 ending at ``t`` is built here, at most ``history_cap_bars`` rows
with prices adjusted as of ``t`` exactly as :mod:`discotrade.backtest` adjusts
them, and ``position`` is called with it and a copy of the parameters. The
result is checked by decision 22's rule (:func:`check`), a negative one
clipped to 0 where shorting is not allowed; a raise from that check's own
conversion of the result to a number is an error of stage ``dry_run``, rule
``not_a_number`` (decision 111 (b) of 2026-10-15-m14).

The first failure ends the run with an error (decision 95 (d), (e)): stage
``load`` (the text raised while loading, or defines no callable
``position``) or ``dry_run`` (a call raised or returned a result outside the
contract), a rule, and a text naming the stage, the rule, the window bar's
index and what was wrong. Any raise is caught, a ``BaseException`` that is not
an ``Exception`` (``SystemExit``, ``KeyboardInterrupt``, ``GeneratorExit``)
included (decision 101 (c) of 2026-10-14-m13). The text never holds a value
the function was given or returned, an exception's message, a symbol or a
date, nor any name the text chose (decision 101 (a)): a raised exception's
type is named only when it is, by identity, one of :data:`BUILTIN_EXCEPTIONS`
(else ``an exception``), and a result that is not a number is described by its
type only when that type is, by identity, one of :data:`RESULT_TYPES` (else
``an object``). Stage ``limit`` is the backend's, which enforces the limits
from outside. Each call's time is recorded in milliseconds; nothing here
enforces it (DESIGN 12.2).

Before any text loads, :func:`main` duplicates file descriptor 1 to a private
descriptor, points descriptor 1 at descriptor 2 (and Python's ``sys.stdout``
at ``sys.stderr``), and writes its result document only to the private
descriptor (decision 101 (b)): what the text writes or prints, to either,
goes to standard error and cannot reach the result. A run the text ends
before the result is written leaves standard output empty, which the backend
reports as stage ``dry_run``, rule ``no_result`` (:data:`NO_RESULT`).
"""

from __future__ import annotations

import builtins
import contextlib
import json
import math
import numbers
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade import indicators

#: The job's description in its directory.
JOB_FILE = "job.json"
#: The version of the job's layout on disk.
FORMAT = 1
#: The two modes of DESIGN 12.4.
MODES = ("positions", "reverse_sample")
#: The error stages of decision 95 (d).
STAGES = ("load", "dry_run", "limit")
#: The arrays of an instrument's bar file, in order.
ARRAYS = ("open", "high", "low", "close", "volume", "hour", "weekday", "rolled", "gap")
#: The name under which a strategy sees the indicator library (DESIGN 6.3).
INDICATORS_NAME = "indicators"
_PRICES = ("open", "high", "low", "close")

#: The exception classes of Python's ``builtins`` an error text may name
#: (decision 101 (a)): every one of them, the ``Warning`` family, ``ExceptionGroup``
#: and ``BaseExceptionGroup`` included (decision 111 (c) of 2026-10-15-m14); any
#: other raised type is named ``an exception``. The two classes ``builtins`` holds
#: only from Python 3.13 on are named here and taken when present, so that the
#: module still imports on the 3.11 the project allows.
BUILTIN_EXCEPTIONS: tuple[type[BaseException], ...] = (
    BaseException, Exception, ArithmeticError, AssertionError, AttributeError,
    BaseExceptionGroup, BlockingIOError, BrokenPipeError, BufferError, BytesWarning,
    ChildProcessError, ConnectionAbortedError, ConnectionError, ConnectionRefusedError,
    ConnectionResetError, DeprecationWarning, EOFError, EncodingWarning, ExceptionGroup,
    FileExistsError, FileNotFoundError, FloatingPointError, FutureWarning, GeneratorExit,
    ImportError, ImportWarning, IndentationError, IndexError, InterruptedError,
    IsADirectoryError, KeyError, KeyboardInterrupt, LookupError, MemoryError,
    ModuleNotFoundError, NameError, NotADirectoryError, NotImplementedError, OSError,
    OverflowError, PendingDeprecationWarning, PermissionError, ProcessLookupError,
    RecursionError, ReferenceError, ResourceWarning, RuntimeError, RuntimeWarning,
    StopAsyncIteration, StopIteration, SyntaxError, SyntaxWarning, SystemError, SystemExit,
    TabError, TimeoutError, TypeError, UnboundLocalError, UnicodeDecodeError,
    UnicodeEncodeError, UnicodeError, UnicodeTranslateError, UnicodeWarning, UserWarning,
    ValueError, Warning, ZeroDivisionError,
) + tuple(getattr(builtins, name) for name in ("PythonFinalizationError",
                                               "_IncompleteInputError")
          if hasattr(builtins, name))
#: The types of a result that is not a number an error text may name (decision
#: 101 (a)): built-in and ``numpy`` types; any other is named ``an object``.
RESULT_TYPES: tuple[type, ...] = (
    type(None), bool, complex, str, bytes, bytearray, list, tuple, dict, set, frozenset,
    range, np.ndarray, np.bool_, np.complex64, np.complex128, np.str_, np.bytes_,
    np.datetime64, np.timedelta64,
)
#: The error a backend reports when the runner ended without writing a result
#: document (decision 101 (b)): its stage, rule and what.
NO_RESULT = ("dry_run", "no_result", "the run ended without a result")


def _named(cls: type, fixed: tuple[type, ...]) -> bool:
    return any(cls is known for known in fixed)


def exception_name(exc: BaseException) -> str:
    """The name of ``exc``'s type when it is a built-in exception class, by
    identity; else ``an exception`` (decision 101 (a))."""
    cls = type(exc)
    return cls.__name__ if _named(cls, BUILTIN_EXCEPTIONS) else "an exception"


def result_name(value: object) -> str:
    """How an error text names a result that is not a number (decision 101 (a))."""
    cls = type(value)
    return f"a value of type {cls.__name__}" if _named(cls, RESULT_TYPES) else "an object"


class LoadFailure(Exception):
    """The text raised while loading, or defines no callable ``position``."""

    def __init__(self, rule: str, what: str) -> None:
        self.rule = rule
        self.what = what
        super().__init__(what)


class BadResult(Exception):
    """A ``position`` result outside the contract (decision 22); ``rule`` names it."""

    def __init__(self, rule: str, what: str) -> None:
        self.rule = rule
        self.what = what
        super().__init__(what)


def _builtins() -> dict[str, Any]:
    """A copy of the builtins whose ``__import__`` resolves ``indicators`` to the library."""
    space = dict(vars(builtins))
    real_import = builtins.__import__

    def strategy_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == INDICATORS_NAME and level == 0:
            return indicators
        return real_import(name, globals, locals, fromlist, level)

    space["__import__"] = strategy_import
    return space


def load_text(source: str) -> Callable[..., Any]:
    """Execute ``source`` in a fresh namespace and return its ``position``."""
    namespace: dict[str, Any] = {
        "__builtins__": _builtins(),
        "__name__": "strategy",
        INDICATORS_NAME: indicators,
    }
    try:
        exec(compile(source, "<strategy>", "exec"), namespace)
    except BaseException as exc:  # noqa: BLE001 - every raise is the text's (101 (c))
        raise LoadFailure(
            "raised", f"the text raised {exception_name(exc)} while loading") from None
    position = namespace.get("position")
    if not callable(position):
        raise LoadFailure("no_position", "the text defines no callable position(bars, params)")
    return position


def check(value: Any, shorting: bool) -> float:
    """``value`` as a float if it meets DESIGN 6.2, clipped to 0 if short and not
    allowed; else :class:`BadResult`. The rule of :func:`discotrade.strategy.check_result`."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise BadResult("not_a_number",
                        f"position returned {result_name(value)}, not a real number")
    result = float(value)
    if not math.isfinite(result):
        raise BadResult("not_finite", "position returned a number that is not finite")
    if not -1.0 <= result <= 1.0:
        raise BadResult("out_of_range", "position returned a number outside [-1, 1]")
    if result < 0.0 and not shorting:
        return 0.0
    return result


def frame_at(arrays: Mapping[str, np.ndarray], roll_at: np.ndarray, k: int, cap: int
             ) -> pd.DataFrame:
    """The slice of DESIGN 6.2 ending at bar ``k``: at most ``cap`` rows, prices
    adjusted as of bar ``k`` (DESIGN 5.6), summed roll by roll in time order as
    :func:`discotrade.backtest._strategy_targets` sums them."""
    j0 = max(0, k - cap + 1)
    gaps = arrays["gap"]
    offset = np.zeros(k + 1 - j0)
    for r in roll_at[(roll_at > j0) & (roll_at <= k)]:
        offset[: r - j0] += gaps[r]
    return pd.DataFrame({
        **{col: arrays[col][j0:k + 1] + offset for col in _PRICES},
        "volume": arrays["volume"][j0:k + 1].copy(),
        "hour": arrays["hour"][j0:k + 1].copy(),
        "weekday": arrays["weekday"][j0:k + 1].copy(),
    })


def error_doc(stage: str, rule: str, what: str, param_set: int | None = None,
              bar: int | None = None) -> dict[str, Any]:
    """The result document of a failed run (decision 95 (e))."""
    text = f"{stage} [{rule}]: {what}"
    if bar is not None:
        text += f" at window bar {bar}"
    if param_set is not None:
        text += f" (parameter set {param_set})"
    return {"ok": False, "error": {"stage": stage, "rule": rule, "param_set": param_set,
                                   "bar": bar, "text": text}}


def execute(job: Mapping[str, Any], bars: Sequence[Mapping[str, np.ndarray]],
            load: Callable[[], Callable[..., Any]]) -> dict[str, Any]:
    """Run ``job`` (``job.json``'s content) on the instruments' ``bars`` and return
    the result document. ``load`` returns a freshly loaded ``position`` each time
    it is called, or raises :class:`LoadFailure`."""
    mode = job["mode"]
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    cap = int(job["history_cap_bars"])
    results = []
    for p, params in enumerate(job["params"]):
        for j, (meta, arrays) in enumerate(zip(job["instruments"], bars, strict=True)):
            try:
                position = load()
            except LoadFailure as exc:
                return error_doc("load", exc.rule, exc.what, p)
            first = int(meta["first"])
            shorting = bool(meta["shorting"])
            roll_at = np.flatnonzero(arrays["rolled"])
            n = len(arrays["close"]) - first
            if mode == "positions":
                order = list(range(n))
            else:
                order = sorted((int(i) for i in meta["sample"]), reverse=True)
            targets, call_ms = [], []
            for i in order:
                frame = frame_at(arrays, roll_at, first + i, cap)
                start = time.perf_counter_ns()
                try:
                    value = position(frame, dict(params))
                except BaseException as exc:  # noqa: BLE001 - decision 101 (c)
                    return error_doc("dry_run", "raised",
                                     f"position raised {exception_name(exc)}", p, i)
                call_ms.append((time.perf_counter_ns() - start) / 1e6)
                try:
                    targets.append(check(value, shorting))
                except BadResult as exc:
                    return error_doc("dry_run", exc.rule, exc.what, p, i)
                except BaseException as exc:  # noqa: BLE001 - decision 111 (b)
                    # The result's own conversion to a number raised (REVIEW-13 note 3).
                    return error_doc("dry_run", "not_a_number",
                                     f"position returned {result_name(value)} whose "
                                     f"conversion to a number raised {exception_name(exc)}",
                                     p, i)
            results.append({"param_set": p, "instrument": j, "bars": order,
                            "targets": targets, "call_ms": call_ms})
    return {"ok": True, "results": results}


def read_job(directory: Path) -> tuple[dict[str, Any], list[dict[str, np.ndarray]]]:
    """``job.json`` and each instrument's arrays, from a job directory."""
    directory = Path(directory)
    job = json.loads((directory / JOB_FILE).read_text(encoding="utf-8"))
    if job.get("format") != FORMAT:
        raise ValueError(f"job format {job.get('format')!r}; this runner reads {FORMAT}")
    bars = []
    for meta in job["instruments"]:
        with np.load(directory / meta["bars"], allow_pickle=False) as data:
            bars.append({name: data[name] for name in ARRAYS})
    return job, bars


def main(argv: Sequence[str] | None = None) -> int:
    """Read the job in ``argv[0]``, run it and write the result to standard output."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m discotrade.sandbox.runner <job dir>", file=sys.stderr)
        return 2
    try:
        job, bars = read_job(Path(args[0]))
    except (OSError, ValueError, KeyError) as exc:
        print(f"runner: cannot read the job: {type(exc).__name__}", file=sys.stderr)
        return 1
    source = job["source"]
    sys.stdout.flush()
    private = os.dup(1)
    try:
        os.dup2(2, 1)
        with contextlib.redirect_stdout(sys.stderr):
            doc = execute(job, bars, lambda: load_text(source))
        sys.stdout.flush()
        _write_all(private, (json.dumps(doc) + "\n").encode("utf-8"))
    finally:
        os.dup2(private, 1)
        os.close(private)
    return 0


def _write_all(fd: int, data: bytes) -> None:
    """Write all of ``data`` to the descriptor ``fd``."""
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


if __name__ == "__main__":
    raise SystemExit(main())
