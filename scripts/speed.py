"""The measurement of O-26 item 4 (meta/decisions/2026-10-18-owner.md; decision
156 of meta/decisions/decisions-2026-10-18-m20.md; DESIGN 16.4; I-12, I-14),
measured in CPU time with a load backstop under O-32 items 1 and 2
(meta/decisions/2026-10-21-owner.md), which win over decisions 156 and 170
where they disagree.

Run through ``scripts/speed``, which runs this file with the project's
environment:

    scripts/speed --work <dir> [--cold] [--from D] [--to D] [--budget-seconds S]
                  [--profile D ...]

The cgroup (O-32 item 1). Each call runs in its own cgroup, made with
``systemd-run --user --scope``: run as a script, this file first checks that
``systemd-run`` makes a scope (``systemd-run --user --scope --quiet true``),
then executes itself again under ``systemd-run --user --scope --quiet`` with
``DISCOTRADE_SPEED_SCOPE=1`` in its environment, so that the replay, its fork
server, the sandbox children and the fresh process all run in that one scope.
Inside, before anything is replayed, it checks that its cgroup (cgroup v2, the
``0::`` line of ``/proc/self/cgroup``) is a ``.scope`` whose ``cgroup.procs``
holds only this process, and that its ``cpu.stat`` gives ``usage_usec``. There
is no fallback: when ``systemd-run`` is missing, fails to make the scope, or
the cgroup or its ``cpu.stat`` cannot be read, at the start or at any day
boundary, the call prints ``speed: error: ...; the measurement stops, no
fallback to wall time`` and exits 1. (The simplest of the ways the brief
allows: one re-execution, no second process left outside the scope.)

The backend (O-32 item 1). The replay keeps the backend the G1.3 track gets by
default, the subprocess backend with its fork server, whose children run in
the call's cgroup. A backend whose work runs outside the cgroup (anything not
in ``INSIDE_CGROUP``, such as ``container``) is refused, exit 1, before any
day is replayed.

It replays the G1.3 scenario on the gate configuration as
``tests/gates/test_g1_3_lifecycle.py`` sets it up: track ``test_synth``,
``tests/fixtures/config/`` copied to ``<dir>/config`` with
``thresholds_gate.toml`` copied in as its ``thresholds.toml``, ``init-state``
of ``<dir>/state`` at 2019-06-03T00:00:00+00:00, the candidates file
``tests/fixtures/scenarios/g1_lifecycle.jsonl``, from 2019-06-03 to 2020-06-10
(``--from``, ``--to``), in process, through ``discotrade.cli.main``. The gate
replays its span in three ``replay`` calls; this command makes one ``replay``
call per trading day (``replay.replay_days``), which runs the same
``daily.run_day`` for each day and lets the command measure each day, stop
between days, and clear the caches before each day under ``--cold``.

``<dir>`` must lie outside the code repository (I-14); a path inside it is
refused with status 2. The first call creates ``<dir>/config`` and
``<dir>/state``. Every call continues from the first day of the span the
journal index does not hold, in one process, until a day ends past
``--budget-seconds`` (default 1020) of wall time from the process's start (the
20-minute cap stays a wall-clock one, O-32 item 8), or the span is done.
Before the span's last day it copies ``<dir>/state`` whole, ``.git/``
included, to ``<dir>/before-last``. After each day it appends one line to
``<dir>/days.jsonl``: ``date``, ``seconds`` (CPU seconds of the call's cgroup,
``usage_usec`` of its ``cpu.stat``, from the previous day boundary of the same
call to this one; for the first day of a call, from the reading at the call's
start; the command's own bookkeeping after a day ends, that is the subject
count, the line, the copy and a profile's dump, is left out), ``process`` (1
for the first call, one more for each later call) and ``subjects`` (the number
of distinct ``subject`` values in that day's decision-journal rows). Nothing is
written in the state directory: a measurement, not a result (I-12). A call
that stops early prints ``speed: continue <done> of <total> days`` and exits 0.

The load backstop (O-32 item 2). While a day of either window is replayed, a
thread reads the one-minute load average (the first field of
``/proc/loadavg``) every 30 seconds, the first time as soon as a window's day
starts, and each call appends its samples to ``<dir>/load.jsonl`` (``date``,
the day being replayed, and ``load``). The samples are the measurement's
only: no day's output reads them.

When the span is done, the command copies ``<dir>/before-last`` to
``<dir>/fresh`` (so that ``before-last`` stays as it was and a later call can
measure again) and runs the last day there in one fresh process (``discotrade
replay`` for that one day, through ``subprocess``, in the same cgroup),
measures its CPU seconds (and its wall time, for information only), and
prints:

    speed first30: <x> CPU s per subject-day (<n> days counted)
    speed last30: <x> CPU s per subject-day (<n> days counted)
    speed ratio: <last30 / first30, three decimals>
    speed fresh last day: <x> CPU s (wall <y> s, for information)
    speed process starts: <the first date of each process>
    speed load first30: <the samples> (average <a>)
    speed load last30: <the samples> (average <a>)
    speed load: valid, the windows' average loads differ by <d> (at most 1.0)
      or: speed: VOID: <why>; this run is not counted (O-32 item 2)
    speed: done

``first30`` is the span's first 30 calendar days (2019-06-03 to 2019-07-02),
``last30`` its last 30 (2020-05-12 to 2020-06-10). A day counts unless it is
the span's first day or the first day of a process; a window's figure is the
total ``seconds`` of its counted days over the total of their ``subjects``
(``nan`` with none). A run is VOID when the two windows' average loads differ
by more than 1.0, or when a window has no load sample (O-32 is silent on that
case; a run whose load cannot be compared is not counted).

``--cold`` calls ``discotrade.state.clear_caches`` (decision 157 (b)) before
every day; the command imports it only then, so that it runs at a parent that
has no such function (decision 156 (e)). ``--profile D`` (repeatable) runs day
``D`` under ``cProfile`` and writes its cumulative listing to
``<dir>/profile-<D>.txt`` (decision 158's profiles); the profiled day's own
time includes the profiler's cost, so a profile is taken on a day outside both
windows.
"""

import time

_START = time.perf_counter()

import argparse  # noqa: E402
import contextlib  # noqa: E402
import cProfile  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import pstats  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
from collections.abc import Callable, Sequence  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
FIRST, LAST = date(2019, 6, 3), date(2020, 6, 10)
SCENARIO = REPO / "tests" / "fixtures" / "scenarios" / "g1_lifecycle.jsonl"
FIXTURE_CONFIG = REPO / "tests" / "fixtures" / "config"
GATE_THRESHOLDS = FIXTURE_CONFIG / "thresholds_gate.toml"
WINDOW_DAYS = 30
BUDGET_SECONDS = 1020.0
PROFILE_LINES = 60
DAYS_FILE = "days.jsonl"
LOAD_FILE = "load.jsonl"
#: Seconds between two load samples (O-32 item 2).
LOAD_INTERVAL = 30.0
#: A run is void when its windows' average loads differ by more (O-32 item 2).
VOID_LOAD_DIFFERENCE = 1.0
#: The sandbox backends whose work runs in the call's cgroup (O-32 item 1).
INSIDE_CGROUP = ("process",)
#: Set in the environment of the call re-executed in its own scope.
SCOPE_ENV = "DISCOTRADE_SPEED_SCOPE"
NO_FALLBACK = "the measurement stops, no fallback to wall time (O-32 item 1)"
PROC_CGROUP = Path("/proc/self/cgroup")
CGROUP_ROOT = Path("/sys/fs/cgroup")
PROC_LOADAVG = Path("/proc/loadavg")

#: The wall clock, for the budget and information only; a test replaces it.
clock: Callable[[], float] = time.perf_counter


class CgroupError(Exception):
    """The call's own cgroup cannot be made or read."""


class Cgroup:
    """A cgroup v2 directory; :meth:`seconds` is its ``usage_usec`` in seconds."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def seconds(self) -> float:
        stat = self.path / "cpu.stat"
        try:
            text = stat.read_text(encoding="ascii")
        except (OSError, UnicodeDecodeError) as exc:
            raise CgroupError(f"cannot read {stat}: {exc}") from exc
        for line in text.splitlines():
            key, _, value = line.partition(" ")
            if key == "usage_usec":
                try:
                    return int(value) / 1e6
                except ValueError:
                    break
        raise CgroupError(f"{stat} gives no usage_usec")


def own_cgroup(proc: Path = PROC_CGROUP, root: Path = CGROUP_ROOT,
               pid: int | None = None) -> Cgroup:
    """The call's cgroup: a cgroup v2 ``.scope`` holding only process ``pid``
    (this one), whose ``cpu.stat`` gives ``usage_usec``; :class:`CgroupError`
    otherwise."""
    pid = os.getpid() if pid is None else pid
    try:
        lines = proc.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CgroupError(f"cannot read {proc}: {exc}") from exc
    rel = next((x[3:] for x in lines if x.startswith("0::")), None)
    if rel is None:
        raise CgroupError(f"{proc} names no cgroup v2 path")
    if not rel.endswith(".scope"):
        raise CgroupError(f"the call's cgroup {rel} is not a scope made for it")
    path = root / rel.lstrip("/")
    try:
        procs = [int(x) for x in (path / "cgroup.procs").read_text(
            encoding="ascii").split()]
    except (OSError, ValueError) as exc:
        raise CgroupError(f"cannot read {path / 'cgroup.procs'}: {exc}") from exc
    if procs != [pid]:
        raise CgroupError(f"the scope {rel} is not its own: it holds processes {procs}")
    group = Cgroup(path)
    group.seconds()
    return group


#: Opens the call's cgroup; a test replaces it.
open_cgroup: Callable[[], Cgroup] = own_cgroup


def enter_scope(argv: Sequence[str], which: Callable = shutil.which,
                run: Callable = subprocess.run, execvpe: Callable = os.execvpe) -> int:
    """Execute this file again with ``argv`` in a scope of its own (``systemd-run
    --user --scope``); returns 1, printing why, when no scope can be made."""
    systemd_run = which("systemd-run")
    if systemd_run is None:
        print(f"speed: error: systemd-run is not found, so no cgroup can be made; "
              f"{NO_FALLBACK}", file=sys.stderr)
        return 1
    head = [systemd_run, "--user", "--scope", "--quiet"]
    try:
        probe = run([*head, "true"], capture_output=True, text=True)
    except OSError as exc:
        print(f"speed: error: {systemd_run} cannot run: {exc}; {NO_FALLBACK}",
              file=sys.stderr)
        return 1
    if probe.returncode != 0:
        print(f"speed: error: systemd-run --user --scope made no cgroup (exit "
              f"{probe.returncode}): {probe.stderr.strip()}; {NO_FALLBACK}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env[SCOPE_ENV] = "1"
    execvpe(systemd_run, [*head, "--", sys.executable, str(Path(__file__).resolve()),
                          *argv], env)
    return 1


def read_loadavg(path: Path = PROC_LOADAVG) -> float:
    """The one-minute load average: the first field of ``/proc/loadavg``."""
    return float(path.read_text(encoding="ascii").split()[0])


class LoadSampler:
    """Reads the load every ``interval`` seconds on a thread while ``day`` (the
    day being replayed, set by the command) is not None, the first time as soon
    as it is set; :meth:`stop` returns the samples. A failed read is kept and
    raised by :meth:`stop`."""

    def __init__(self, read: Callable[[], float], interval: float = LOAD_INTERVAL) -> None:
        self.read = read
        self.interval = interval
        self.samples: list[dict] = []
        self.error: Exception | None = None
        self._day: date | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._run, name="speed-load", daemon=True)

    @property
    def day(self) -> date | None:
        return self._day

    @day.setter
    def day(self, value: date | None) -> None:
        sampling = self._day is not None
        self._day = value
        if value is not None and not sampling:
            self._wake.set()

    def tick(self) -> None:
        if self._day is not None:
            self.samples.append({"date": self._day.isoformat(), "load": self.read()})

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._day is None:
                self._wake.wait()
                self._wake.clear()
                continue
            try:
                self.tick()
            except (OSError, ValueError, IndexError) as exc:
                self.error = exc
                return
            self._stop.wait(self.interval)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> list[dict]:
        self._stop.set()
        self._wake.set()
        self._thread.join()
        if self.error is not None:
            raise CgroupError(f"cannot read the load average: {self.error}")
        return self.samples


#: Makes the call's load sampler; a test replaces it.
load_sampler: Callable[[], LoadSampler] = lambda: LoadSampler(read_loadavg)  # noqa: E731


def replay_backend(instruments) -> str:
    """The sandbox backend the replay of the track's ``instruments`` runs on."""
    from discotrade.sandbox.base import choose_backend
    return choose_backend(instruments)


def append_samples(path: Path, samples: Sequence[dict]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        for x in samples:
            fh.write(json.dumps(x, sort_keys=True) + "\n")


def load_lines(samples: Sequence[dict], span_first: date, span_last: date) -> list[str]:
    """The two windows' load samples and averages, and the verdict: VOID when
    the averages differ by more than ``VOID_LOAD_DIFFERENCE`` or a window has no
    sample (O-32 item 2)."""
    windows = (("first30", span_first, span_first + timedelta(days=WINDOW_DAYS - 1)),
               ("last30", span_last - timedelta(days=WINDOW_DAYS - 1), span_last))
    lines, averages, empty = [], [], []
    for name, lo, hi in windows:
        loads = [float(x["load"]) for x in samples
                 if lo <= date.fromisoformat(x["date"]) <= hi]
        if not loads:
            lines.append(f"speed load {name}: (no sample)")
            empty.append(name)
            continue
        avg = sum(loads) / len(loads)
        averages.append(avg)
        lines.append(f"speed load {name}: {' '.join(f'{x:.2f}' for x in loads)} "
                     f"(average {avg:.3f})")
    if empty:
        lines.append(f"speed: VOID: the {' and '.join(empty)} window has no load sample; "
                     "this run is not counted (O-32 item 2)")
        return lines
    diff = abs(averages[1] - averages[0])
    if diff > VOID_LOAD_DIFFERENCE:
        lines.append(f"speed: VOID: the windows' average loads differ by {diff:.3f}, more "
                     f"than {VOID_LOAD_DIFFERENCE}; this run is not counted (O-32 item 2)")
    else:
        lines.append(f"speed load: valid, the windows' average loads differ by {diff:.3f} "
                     f"(at most {VOID_LOAD_DIFFERENCE})")
    return lines


def call(*argv: str) -> tuple[int, str, str]:
    """``discotrade`` in-process through ``discotrade.cli.main``."""
    from discotrade.cli import main

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:
            status = exc.code if isinstance(exc.code, int) else 1
    return status, out.getvalue(), err.getvalue()


def read_days(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def window_figure(days: Sequence[dict], first: date, last: date,
                  span_first: date) -> tuple[float, int]:
    """Seconds per subject-day over ``first``..``last`` and the counted days."""
    starts: set[int] = set()
    seconds = subjects = 0.0
    counted = 0
    for line in days:
        process = int(line["process"])
        first_of_process = process not in starts
        starts.add(process)
        d = date.fromisoformat(line["date"])
        if first_of_process or d == span_first or not first <= d <= last:
            continue
        seconds += float(line["seconds"])
        subjects += int(line["subjects"])
        counted += 1
    return (seconds / subjects if subjects else math.nan), counted


def process_starts(days: Sequence[dict]) -> list[str]:
    out: dict[int, str] = {}
    for line in days:
        out.setdefault(int(line["process"]), line["date"])
    return [out[k] for k in sorted(out)]


def _copy_state(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=True)


def _fresh_command(state: Path, config: Path, day: date) -> list[str]:
    script = Path(sys.executable).with_name("discotrade")
    head = [str(script)] if script.is_file() else [sys.executable, "-m", "discotrade.cli"]
    return [*head, "--state", str(state), "--config", str(config), "--track", TRACK,
            "replay", "--from", day.isoformat(), "--to", day.isoformat(),
            "--candidates", str(SCENARIO)]


def _fmt(x: float) -> str:
    return "nan" if math.isnan(x) else f"{x:.6f}"


def parse(argv: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts/speed", description=__doc__.splitlines()[0])
    p.add_argument("--work", required=True, type=Path,
                   help="the work directory, outside the code repository")
    p.add_argument("--cold", action="store_true",
                   help="clear every cache of the process before every day (decision 157)")
    p.add_argument("--from", dest="first", type=date.fromisoformat, default=FIRST)
    p.add_argument("--to", dest="last", type=date.fromisoformat, default=LAST)
    p.add_argument("--budget-seconds", type=float, default=BUDGET_SECONDS)
    p.add_argument("--profile", type=date.fromisoformat, action="append", default=[],
                   metavar="YYYY-MM-DD", help="profile this day (repeatable)")
    return p.parse_args(list(argv))


def in_window(d: date, first: date, last: date) -> bool:
    return (first <= d <= first + timedelta(days=WINDOW_DAYS - 1)
            or last - timedelta(days=WINDOW_DAYS - 1) <= d <= last)


def main(argv: Sequence[str], start: float | None = None) -> int:
    """One call; ``start`` is the wall clock at the process's start."""
    start = clock() if start is None else start
    args = parse(argv)
    work = args.work.resolve()
    if work == REPO or work.is_relative_to(REPO):
        print(f"speed: error: {work} is inside the code repository {REPO} (I-14)",
              file=sys.stderr)
        return 2
    if args.first > args.last:
        print("speed: error: --from is after --to", file=sys.stderr)
        return 2
    try:
        group = open_cgroup()
        cpu_start = group.seconds()
        return _measure(args, work, group, cpu_start, start)
    except CgroupError as exc:
        print(f"speed: error: {exc}; {NO_FALLBACK}", file=sys.stderr)
        return 1


def _measure(args: argparse.Namespace, work: Path, group: Cgroup, cpu_start: float,
             start: float) -> int:
    cpu = group.seconds
    state, config = work / "state", work / "config"
    if not (state / ".git").exists():
        work.mkdir(parents=True, exist_ok=True)
        for leftover in (state, config):
            if leftover.exists():
                shutil.rmtree(leftover)
        shutil.copytree(FIXTURE_CONFIG, config)
        shutil.copyfile(GATE_THRESHOLDS, config / "thresholds.toml")
        status, _, err = call("init-state", "--state", str(state), "--as-of", INIT_AS_OF)
        if status != 0:
            print(f"speed: init-state failed: {err.strip()}", file=sys.stderr)
            return 1

    from discotrade.config import load_track_config
    from discotrade.journal import Setup, read_day, read_index
    from discotrade.replay import replay_days

    tc = load_track_config(config, TRACK)
    backend = replay_backend(tc.instruments)
    if backend not in INSIDE_CGROUP:
        print(f"speed: error: the replay's sandbox backend is {backend}, whose work runs "
              f"outside this call's cgroup; the measurement refuses it rather than "
              f"under-count (O-32 item 1)", file=sys.stderr)
        return 1
    calendars = dict(Setup.load(config, TRACK).calendars)
    span = [d for d, _ in replay_days(tc, calendars, args.first, args.last)]
    journaled = {date.fromisoformat(str(e["date"])) for e in read_index(state, TRACK)}
    todo = [d for d in span if d not in journaled]
    log = work / DAYS_FILE
    earlier = read_days(log)
    process = 1 + max((int(x["process"]) for x in earlier), default=0)
    clear = None
    if args.cold:
        from discotrade.state import clear_caches as clear
    profiles = set(args.profile)
    done = len(span) - len(todo)

    sampler = load_sampler()
    sampler.start()
    try:
        stopped = _days(args, work, state, config, todo, span, done, process, clear,
                        profiles, cpu, cpu_start, start, sampler, read_day)
    finally:
        sampler.day = None
        samples = sampler.stop()
        if samples:
            append_samples(work / LOAD_FILE, samples)
    if stopped is not None:
        return stopped

    before = work / "before-last"
    if not before.is_dir():
        print(f"speed: error: {before} does not exist; the last day was replayed without "
              "it", file=sys.stderr)
        return 1
    fresh = work / "fresh"
    _copy_state(before, fresh)
    wall0, cpu0 = clock(), cpu()
    proc = subprocess.run(_fresh_command(fresh, config, args.last), capture_output=True,
                          text=True, env=dict(os.environ))
    cpu1, wall1 = cpu(), clock()
    if proc.returncode != 0:
        print(f"speed: the fresh process failed ({proc.returncode}): {proc.stderr.strip()}",
              file=sys.stderr)
        return 1
    days = read_days(log)
    w1 = window_figure(days, args.first, args.first + timedelta(days=WINDOW_DAYS - 1),
                       args.first)
    w2 = window_figure(days, args.last - timedelta(days=WINDOW_DAYS - 1), args.last,
                       args.first)
    ratio = w2[0] / w1[0] if w1[0] else math.nan
    print(f"speed first30: {_fmt(w1[0])} CPU s per subject-day ({w1[1]} days counted)")
    print(f"speed last30: {_fmt(w2[0])} CPU s per subject-day ({w2[1]} days counted)")
    print(f"speed ratio: {'nan' if math.isnan(ratio) else f'{ratio:.3f}'}")
    print(f"speed fresh last day: {cpu1 - cpu0:.3f} CPU s "
          f"(wall {wall1 - wall0:.3f} s, for information)")
    print(f"speed process starts: {' '.join(process_starts(days))}")
    for line in load_lines(read_days(work / LOAD_FILE), args.first, args.last):
        print(line)
    print("speed: done")
    return 0


def _days(args, work, state, config, todo, span, done, process, clear, profiles, cpu,
          cpu_start, start, sampler, read_day) -> int | None:
    """Replays ``todo``; returns the call's status when it stops early, None when
    the span is done."""
    log = work / DAYS_FILE
    prev = cpu_start
    for k, d in enumerate(todo):
        if d == args.last:
            t0 = cpu()
            _copy_state(state, work / "before-last")
            prev += cpu() - t0
        profiler = cProfile.Profile() if d in profiles else None
        sampler.day = d if in_window(d, args.first, args.last) else None
        if clear is not None:
            clear()
        if profiler is not None:
            profiler.enable()
        status, _, err = call("--state", str(state), "--config", str(config), "--track",
                              TRACK, "replay", "--from", d.isoformat(), "--to", d.isoformat(),
                              "--candidates", str(SCENARIO))
        if profiler is not None:
            profiler.disable()
        end = cpu()
        wall = clock()
        if status != 0:
            print(f"speed: replay of {d.isoformat()} failed ({status}): {err.strip()}",
                  file=sys.stderr)
            return 1
        rows = read_day(state, TRACK, d)
        subjects = 0 if rows is None else int(rows["subject"].nunique())
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"date": d.isoformat(), "seconds": end - prev,
                                 "process": process, "subjects": subjects},
                                sort_keys=True) + "\n")
        if profiler is not None:
            listing = io.StringIO()
            pstats.Stats(profiler, stream=listing).sort_stats("cumulative").print_stats(
                PROFILE_LINES)
            (work / f"profile-{d.isoformat()}.txt").write_text(listing.getvalue(),
                                                              encoding="utf-8")
        done += 1
        if k + 1 < len(todo):
            if wall - start > args.budget_seconds:
                print(f"speed: continue {done} of {len(span)} days")
                return 0
            prev = cpu()
    return None


if __name__ == "__main__":
    if os.environ.get(SCOPE_ENV) != "1":
        sys.exit(enter_scope(sys.argv[1:]))
    sys.exit(main(sys.argv[1:], start=_START))
