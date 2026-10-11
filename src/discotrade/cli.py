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
from datetime import datetime
from pathlib import Path

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


def _context(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Context:
    state_text = args.state if args.state is not None else os.environ.get(STATE_ENV) or None
    state: Path | None = None
    if state_text is not None:
        state = Path(state_text).expanduser().resolve()
        if _inside(state, REPO_ROOT):
            parser.error(
                f"state directory {state} is inside the code repository {REPO_ROOT} (I-14)"
            )

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


def _bars_gaps(ctx: Context, args: argparse.Namespace) -> int:
    from datetime import date, timedelta

    from discotrade.bars.gaps import check_gaps
    from discotrade.bars.store import BarStoreError
    from discotrade.config import (
        ConfigError,
        load_calendar,
        load_thresholds,
        load_track_config,
    )

    if ctx.state is None:
        print("bars gaps: FAIL: no state directory (--state or $DISCOTRADE_STATE)",
              file=sys.stderr)
        return 1
    try:
        day = (date.fromisoformat(args.day) if args.day
               else ctx.clock.now().date() - timedelta(days=1))
    except ValueError as exc:
        print(f"bars gaps: FAIL: --day {args.day!r}: {exc}", file=sys.stderr)
        return 1
    try:
        tc = load_track_config(ctx.config, ctx.track)
        calendars = {
            name: load_calendar(ctx.config / "calendars" / f"{name}.toml")
            for name in sorted({inst.calendar for inst in tc.instruments})
        }
        limit = load_thresholds(ctx.config / "thresholds.toml")["gaps.max_fraction"]
        report = check_gaps(ctx.state, tc, calendars, day, limit)
    except (ConfigError, BarStoreError, OSError) as exc:
        print(f"bars gaps: FAIL: {exc}", file=sys.stderr)
        return 1
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
        help="trading day whose W and T are checked (default: the day before the "
        "UTC date of --as-of)",
    )
    gaps.set_defaults(handler=_bars_gaps)


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
