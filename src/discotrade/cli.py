"""The ``discotrade`` command (DESIGN 3).

Every subcommand takes ``--state``, ``--track``, ``--config`` and ``--as-of``;
they are accepted before or after the subcommand name. A subcommand is added
by writing a ``_add_<name>(subparsers, common)`` function that registers its
parser with ``parents=[common]`` and ``set_defaults(handler=...)``, and
listing it in ``SUBCOMMANDS``. A handler takes ``(ctx, args)`` and returns
the exit status: 0 on success, 1 on failure. A usage error exits 2.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from discotrade import __version__
from discotrade.clock import Clock, FixedClock, SystemClock

#: The code repository: src/discotrade/cli.py -> the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

STATE_ENV = "DISCOTRADE_STATE"
DEFAULT_TRACK = "hourly"


@dataclass(frozen=True)
class Context:
    """What every subcommand receives: resolved common options."""

    state: Path | None
    track: str
    config: Path
    clock: Clock


Handler = Callable[[Context, argparse.Namespace], int]

#: Subcommand registrars, in the order ``--help`` lists them.
SUBCOMMANDS: list[Callable[[argparse._SubParsersAction, argparse.ArgumentParser], None]] = []


def _common_options(parser: argparse.ArgumentParser, *, suppress: bool) -> None:
    # On a subcommand parser the defaults are suppressed so that an option
    # given before the subcommand name is not overwritten by a default.
    default = argparse.SUPPRESS if suppress else None
    group = parser.add_argument_group("common options")
    group.add_argument(
        "--state", metavar="DIR", default=default,
        help=f"state directory (default: ${STATE_ENV}; refused inside the code repository)",
    )
    group.add_argument(
        "--track", metavar="NAME", default=default,
        help=f"track name (default: {DEFAULT_TRACK})",
    )
    group.add_argument(
        "--config", metavar="DIR", default=default,
        help="configuration directory (default: the repository's config/)",
    )
    group.add_argument(
        "--as-of", metavar="INSTANT", dest="as_of", default=default,
        help="ISO 8601 instant with a timezone; sets the injected clock (default: now)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discotrade",
        description="discotrade: tests trading rules on unseen data, net of costs. "
        "Simulation only.",
    )
    parser.add_argument("--version", action="version", version=f"discotrade {__version__}")
    _common_options(parser, suppress=False)
    common = argparse.ArgumentParser(add_help=False)
    _common_options(common, suppress=True)
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    for register in SUBCOMMANDS:
        register(subparsers, common)
    return parser


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _code_repository(path: Path) -> Path | None:
    """The discotrade code repository that holds ``path``, if any.

    A code repository is a directory with both ``pyproject.toml`` and
    ``src/discotrade/`` (decision 7 of meta/decisions/decisions-2026-10-12.md);
    ``path`` itself and every directory above it are examined.
    """
    for directory in (path, *path.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "src" / "discotrade").is_dir():
            return directory
    return None


def _state(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Path | None:
    if args.state is not None:
        if not args.state.strip():
            parser.error("--state is empty; give a state directory outside the code repository")
        state_text = args.state
    else:
        state_text = os.environ.get(STATE_ENV)
        if state_text is None:
            return None
        if not state_text.strip():
            parser.error(f"{STATE_ENV} is empty; unset it or give a state directory")
    state = Path(state_text).expanduser().resolve()
    # I-14: refused inside this package's repository, and inside any directory
    # laid out as a discotrade code repository, however the package is installed.
    repository = REPO_ROOT if _inside(state, REPO_ROOT) else _code_repository(state)
    if repository is not None:
        parser.error(
            f"state directory {state} is inside the code repository {repository} (I-14)"
        )
    return state


def _context(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Context:
    state = _state(parser, args)

    clock: Clock = SystemClock()
    if args.as_of is not None:
        try:
            clock = FixedClock(datetime.fromisoformat(args.as_of))
        except ValueError as exc:
            parser.error(f"--as-of {args.as_of!r}: {exc}")

    config = Path(args.config).expanduser().resolve() if args.config else REPO_ROOT / "config"
    return Context(
        state=state,
        track=args.track if args.track is not None else DEFAULT_TRACK,
        config=config,
        clock=clock,
    )


def parse(argv: Sequence[str] | None = None) -> tuple[Context, argparse.Namespace]:
    """Parse the command line; a usage error raises ``SystemExit(2)``."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return _context(parser, args), args


def _config_check(ctx: Context, args: argparse.Namespace) -> int:
    from discotrade.config import ConfigError, check

    try:
        report = check(ctx.config, ctx.track)
    except ConfigError as exc:
        print(f"config check: FAIL: {exc}", file=sys.stderr)
        return 1
    for line in (*report.lines, *report.unverified):
        print(line)
    print(f"config check: ok, {len(report.unverified)} unverified values")
    return 0


def _add_config(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    config = subparsers.add_parser(
        "config", parents=[common], help="configuration records (DESIGN 4)"
    )
    actions = config.add_subparsers(dest="action", metavar="action", required=True)
    checker = actions.add_parser(
        "check", parents=[common],
        help="load every record, list each unverified value, fail on an invalid one",
    )
    checker.set_defaults(handler=_config_check)


SUBCOMMANDS.append(_add_config)


def _gap_day(ctx: Context, args: argparse.Namespace, command: str) -> date | None:
    try:
        return (date.fromisoformat(args.day) if args.day
                else ctx.clock.now().date() - timedelta(days=1))
    except ValueError as exc:
        print(f"{command}: FAIL: --day {args.day!r}: {exc}", file=sys.stderr)
        return None


def _closed_day(tc: Any, calendars: dict[str, Any], now: datetime) -> date:
    """DESIGN 16.1's ``D`` at ``now`` (decision 2026-10-12 3): per instrument, the
    latest trading day whose last expected bar closed at or before its source's
    ``available_until(now)``; for the track, the earliest of these, so that
    every instrument's day ``D`` has closed (DESIGN is silent on a track whose
    instruments differ in calendar or source; the simplest safe choice)."""
    from discotrade.bars.gaps import latest_closed_day
    from discotrade.sources import source_for

    bar = tc.track.bar_seconds
    days = []
    for inst in tc.instruments:
        source = source_for(inst.source.adapter, calendars, bar)
        days.append(latest_closed_day(calendars[inst.calendar], source.available_until(now),
                                      bar))
    return min(days)


def _load_for_gaps(ctx: Context) -> tuple[Any, dict[str, Any], float]:
    from discotrade.config import load_calendar, load_thresholds, load_track_config

    tc = load_track_config(ctx.config, ctx.track)
    calendars = {
        name: load_calendar(ctx.config / "calendars" / f"{name}.toml")
        for name in sorted({inst.calendar for inst in tc.instruments})
    }
    limit = load_thresholds(ctx.config / "thresholds.toml")["gaps.max_fraction"]
    return tc, calendars, limit


def _print_gaps(report: Any) -> None:
    print(f"track {report.track}, day {report.day.isoformat()}")
    for symbol, times in report.missing.items():
        print(f"{symbol}: {len(times)} missing")
        for t in times:
            print(f"missing {symbol} {t.isoformat()}")
    for win in report.windows:
        print(f"{win.name} {win.first.isoformat()} to {win.last.isoformat()}: "
              f"{win.missing} missing of {win.expected} expected, fraction {win.fraction:.6f}")
    print(f"new in gaps.jsonl: {report.new}")
    if report.skip_generation:
        over = " and ".join(report.event.detail["over"]) if report.event else ""
        print(f"generation: skipped (data_gaps: {over} above gaps.max_fraction "
              f"{report.max_fraction:g})")
    else:
        print("generation: ok")


def _bars_gaps(ctx: Context, args: argparse.Namespace) -> int:
    from discotrade.bars.gaps import check_gaps
    from discotrade.bars.store import BarStoreError
    from discotrade.config import ConfigError
    from discotrade.sources import NotBuiltError

    if ctx.state is None:
        print("bars gaps: FAIL: no state directory (--state or $DISCOTRADE_STATE)",
              file=sys.stderr)
        return 1
    try:
        day = date.fromisoformat(args.day) if args.day else None
    except ValueError as exc:
        print(f"bars gaps: FAIL: --day {args.day!r}: {exc}", file=sys.stderr)
        return 1
    try:
        tc, calendars, limit = _load_for_gaps(ctx)
        if day is None:
            day = _closed_day(tc, calendars, ctx.clock.now())
        report = check_gaps(ctx.state, tc, calendars, day, limit)
    except NotBuiltError as exc:
        print(f"bars gaps: FAIL: not built: {exc}; give --day", file=sys.stderr)
        return 1
    except (ConfigError, BarStoreError, OSError, ValueError) as exc:
        print(f"bars gaps: FAIL: {exc}", file=sys.stderr)
        return 1
    _print_gaps(report)
    return 0


def _bars_fetch(ctx: Context, args: argparse.Namespace) -> int:
    import pandas as pd

    from discotrade.bars.gaps import check_gaps
    from discotrade.bars.store import BarStore, BarStoreError, finite_rows
    from discotrade.config import ConfigError
    from discotrade.rolls import update_rolls
    from discotrade.sources import NotBuiltError, source_for

    if ctx.state is None:
        print("bars fetch: FAIL: no state directory (--state or $DISCOTRADE_STATE)",
              file=sys.stderr)
        return 1
    day = _gap_day(ctx, args, "bars fetch")
    if day is None:
        return 1
    try:
        tc, calendars, limit = _load_for_gaps(ctx)
        bar = tc.track.bar_seconds
        store = BarStore(ctx.state, tc.track.name, bar)
        now = ctx.clock.now()
        # An interrupted append is completed before any fetch (decision
        # 2026-10-12 5); a revised data point stops the fetch.
        notices = [event for inst in tc.instruments
                   for event in store.recover(inst.symbol, day)]
        for event in notices:
            print(f"notice {event.to_json()}")
        # Every instrument's bars are asked for before any is written, so a
        # source that cannot serve one instrument leaves the store untouched.
        batches = []
        sources = {}
        for inst in tc.instruments:
            source = source_for(inst.source.adapter, calendars, bar)
            until = source.available_until(now)
            last = store.last_ts(inst.symbol)
            start = (datetime.combine(inst.trusted_from, time(), tzinfo=UTC) if last is None
                     else last.to_pydatetime() + timedelta(seconds=bar))
            bars = source.fetch(inst, start, until) if start < until else None
            dropped = 0
            if bars is not None:
                bars = bars[bars["ts"] + pd.Timedelta(seconds=bar) <= pd.Timestamp(until)]
                # A bar with a value that is not finite is not stored; to the
                # gap check it is a missing bar (decision 2026-10-12 6).
                finite = finite_rows(bars)
                dropped = int((~finite).sum())
                bars = bars[finite]
            batches.append((inst.symbol, bars, until, dropped))
            sources[inst.symbol] = source
        for symbol, bars, until, dropped in batches:
            written = 0 if bars is None else store.append(symbol, bars, until)
            print(f"fetched {symbol}: {written} bars written, {dropped} dropped as not "
                  f"finite, available until {until.isoformat()}")
        report = check_gaps(ctx.state, tc, calendars, day, limit)
        # Rolls are found on the stored bars and recorded once (DESIGN 5.6).
        rolls = [update_rolls(ctx.state, tc.track.name, bar, inst, sources[inst.symbol], day)
                 for inst in tc.instruments]
    except NotBuiltError as exc:
        print(f"bars fetch: FAIL: not built: {exc}", file=sys.stderr)
        return 1
    except (ConfigError, BarStoreError, OSError, ValueError) as exc:
        print(f"bars fetch: FAIL: {exc}", file=sys.stderr)
        return 1
    _print_gaps(report)
    for inst, (new, events) in zip(tc.instruments, rolls, strict=True):
        for roll in new:
            how = ("(estimated)" if roll.measured_at is None
                   else f"(measured at {roll.measured_at.isoformat()})")
            print(f"roll {inst.symbol} {roll.ts.isoformat()} {roll.old} -> {roll.new} "
                  f"gap {roll.gap!r} {how}")
        for event in events:
            print(f"notice {event.to_json()}")
    return 0


def _add_bars(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    bars = subparsers.add_parser("bars", parents=[common], help="the bar store (DESIGN 5)")
    actions = bars.add_subparsers(dest="action", metavar="action", required=True)
    gaps = actions.add_parser(
        "gaps", parents=[common],
        help="report missing bars, append new ones to gaps.jsonl, and the W and T gap "
        "fractions (DESIGN 5.4)",
    )
    gaps.add_argument(
        "--day", metavar="YYYY-MM-DD", default=None,
        help="trading day whose W and T are checked; stored bars after it are ignored "
        "(default: the latest trading day whose last bar closed by each source's "
        "available_until at --as-of, the earliest across the track, DESIGN 16.1)",
    )
    gaps.set_defaults(handler=_bars_gaps)
    fetch = actions.add_parser(
        "fetch", parents=[common],
        help="complete an interrupted append, ask each instrument's source for its bars "
        "from the last stored bar to the source's available_until at --as-of, drop bars "
        "with a value that is not finite, write the closed ones, run the gap check, then "
        "record new rolls with their gaps (DESIGN 5.5, 5.4, 5.6)",
    )
    fetch.add_argument(
        "--day", metavar="YYYY-MM-DD", default=None,
        help="trading day whose W and T the gap check reports (default: the day before "
        "the UTC date of --as-of)",
    )
    fetch.set_defaults(handler=_bars_fetch)


SUBCOMMANDS.append(_add_bars)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ctx = _context(parser, args)
    handler: Handler | None = getattr(args, "handler", None)
    if handler is None:
        parser.error("a command is required")
    return handler(ctx, args)


if __name__ == "__main__":
    sys.exit(main())
