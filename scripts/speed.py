"""The measurement of O-26 item 4 (meta/decisions/2026-10-18-owner.md; decision
156 of meta/decisions/decisions-2026-10-18-m20.md; DESIGN 16.4; I-12, I-14).

Run through ``scripts/speed``, which runs this file with the project's
environment:

    scripts/speed --work <dir> [--cold] [--from D] [--to D] [--budget-seconds S]
                  [--profile D ...]

It replays the G1.3 scenario on the gate configuration as
``tests/gates/test_g1_3_lifecycle.py`` sets it up: track ``test_synth``,
``tests/fixtures/config/`` copied to ``<dir>/config`` with
``thresholds_gate.toml`` copied in as its ``thresholds.toml``, ``init-state``
of ``<dir>/state`` at 2019-06-03T00:00:00+00:00, the candidates file
``tests/fixtures/scenarios/g1_lifecycle.jsonl``, from 2019-06-03 to 2020-06-10
(``--from``, ``--to``), in process, through ``discotrade.cli.main``. The gate
replays its span in three ``replay`` calls; this command makes one ``replay``
call per trading day (``replay.replay_days``), which runs the same
``daily.run_day`` for each day and lets the command time each day, stop
between days, and clear the caches before each day under ``--cold``.

``<dir>`` must lie outside the code repository (I-14); a path inside it is
refused with status 2. The first call creates ``<dir>/config`` and
``<dir>/state``. Every call continues from the first day of the span the
journal index does not hold, in one process, until a day ends past
``--budget-seconds`` (default 1020) from the process's start, or the span is
done. Before the span's last day it copies ``<dir>/state`` whole, ``.git/``
included, to ``<dir>/before-last``. After each day it appends one line to
``<dir>/days.jsonl``: ``date``, ``seconds`` (from the end of the previous day of
the same process to the end of this one; for the first day of a process, from
the process's start; the command's own bookkeeping after a day ends, that is
the subject count, the line, the copy and a profile's dump, is left out),
``process`` (1 for the first call, one more for each later call) and
``subjects`` (the number of distinct ``subject`` values in that day's
decision-journal rows). Time is read with ``time.perf_counter`` (``clock``)
and nothing is written in the state directory: a measurement, not a result
(I-12). A call that stops early prints ``speed: continue <done> of <total>
days`` and exits 0.

When the span is done, the command copies ``<dir>/before-last`` to
``<dir>/fresh`` (so that ``before-last`` stays as it was and a later call can
measure again) and runs the last day there in one fresh process (``discotrade
replay`` for that one day, through ``subprocess``), times it, and prints:

    speed first30: <x> s per subject-day (<n> days counted)
    speed last30: <x> s per subject-day (<n> days counted)
    speed ratio: <last30 / first30, three decimals>
    speed fresh last day: <x> s
    speed process starts: <the first date of each process>
    speed: done

``first30`` is the span's first 30 calendar days (2019-06-03 to 2019-07-02),
``last30`` its last 30 (2020-05-12 to 2020-06-10). A day counts unless it is
the span's first day or the first day of a process; a window's figure is the
total ``seconds`` of its counted days over the total of their ``subjects``
(``nan`` with none).

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

#: The timer; a test replaces it.
clock: Callable[[], float] = time.perf_counter


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


def main(argv: Sequence[str], start: float | None = None) -> int:
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

    prev = start
    for k, d in enumerate(todo):
        if d == args.last:
            t0 = clock()
            _copy_state(state, work / "before-last")
            prev += clock() - t0
        profiler = cProfile.Profile() if d in profiles else None
        if clear is not None:
            clear()
        if profiler is not None:
            profiler.enable()
        status, _, err = call("--state", str(state), "--config", str(config), "--track",
                              TRACK, "replay", "--from", d.isoformat(), "--to", d.isoformat(),
                              "--candidates", str(SCENARIO))
        if profiler is not None:
            profiler.disable()
        end = clock()
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
            if end - start > args.budget_seconds:
                print(f"speed: continue {done} of {len(span)} days")
                return 0
            prev = clock()

    before = work / "before-last"
    if not before.is_dir():
        print(f"speed: error: {before} does not exist; the last day was replayed without "
              "it", file=sys.stderr)
        return 1
    fresh = work / "fresh"
    _copy_state(before, fresh)
    t0 = clock()
    proc = subprocess.run(_fresh_command(fresh, config, args.last), capture_output=True,
                          text=True, env=dict(os.environ))
    wall = clock() - t0
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
    print(f"speed first30: {_fmt(w1[0])} s per subject-day ({w1[1]} days counted)")
    print(f"speed last30: {_fmt(w2[0])} s per subject-day ({w2[1]} days counted)")
    print(f"speed ratio: {'nan' if math.isnan(ratio) else f'{ratio:.3f}'}")
    print(f"speed fresh last day: {wall:.3f} s")
    print(f"speed process starts: {' '.join(process_starts(days))}")
    print("speed: done")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], start=_START))
