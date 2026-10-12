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
import json
import math
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

#: The directory whose strategy files ``backtest`` runs (decision 2026-10-12 21).
#: Tests point it at a temporary directory in-process; nothing else changes it.
REFERENCE_ROOT = REPO_ROOT / "reference"

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
    for line in (*report.lines, *report.unverified, *report.warnings):
        print(line)
    warned = f", {len(report.warnings)} warnings" if report.warnings else ""
    print(f"config check: ok, {len(report.unverified)} unverified values{warned}")
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


def _notice_day(ctx: Context, args: argparse.Namespace, command: str) -> date | None:
    """The date ``bars fetch`` gives its health notices: ``--day``, else the day
    before the UTC date of ``--as-of`` (unchanged; decision 2026-10-12 19 moves
    only the gap-check day). None, after a message, for a bad ``--day``."""
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
    day = _notice_day(ctx, args, "bars fetch")
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
        # With no --day, the gap check is for DESIGN 16.1's D at --as-of, the
        # day `bars gaps` checks, by the same function (decision 2026-10-12 19).
        gap_day = day if args.day else _closed_day(tc, calendars, now)
        report = check_gaps(ctx.state, tc, calendars, gap_day, limit)
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
        help="trading day whose W and T the gap check reports, and the date of the "
        "notices (default: for the gap check, the day bars gaps checks, DESIGN 16.1; for "
        "the notices, the day before the UTC date of --as-of)",
    )
    fetch.set_defaults(handler=_bars_fetch)


SUBCOMMANDS.append(_add_bars)


def _spreads_measure(ctx: Context, args: argparse.Namespace) -> int:
    from discotrade.config import ConfigError, load_calendar, load_instrument
    from discotrade.sources.base import SourceError
    from discotrade.sources.vendor import VendorSource
    from discotrade.spreads import (
        COMMIT_NOTE,
        DEFAULT_DAYS,
        SpreadError,
        marginal_line,
        measure_and_write,
        read_quotes,
        refuse_existing,
        vendor_quotes,
    )

    def fail(why: object) -> int:
        print(f"spreads measure: FAIL: {why}", file=sys.stderr)
        return 1

    days = DEFAULT_DAYS if args.days is None else args.days
    if days < 1:
        return fail(f"--days must be at least 1, not {days}")
    try:
        inst = load_instrument(ctx.config / "instruments" / f"{args.symbol}.toml")
        cal = load_calendar(ctx.config / "calendars" / f"{inst.calendar}.toml")
        refuse_existing(ctx.config, inst.symbol)
        if args.quotes:
            quotes = read_quotes(Path(args.quotes))
            source = f"quote sample file {Path(args.quotes).name}"
        else:
            vendor = VendorSource(3600)   # the bar length only picks a bar schema
            until = vendor.available_until(ctx.clock.now())
            quotes, source = vendor_quotes(inst, until - timedelta(days=days), until,
                                           vendor)
        path, table = measure_and_write(ctx.config, inst, cal, quotes, source,
                                        ctx.clock.now().date())
    except (ConfigError, SpreadError, SourceError, OSError) as exc:
        return fail(exc)
    print(f"spreads measure: wrote {path}")
    print(" ".join(f"{h:02d}:{v:g}" for h, v in enumerate(table.ticks)))
    print(marginal_line(inst, table))
    print(f"note: {COMMIT_NOTE}")
    return 0


def _add_spreads(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    spreads = subparsers.add_parser("spreads", parents=[common],
                                    help="measured spread tables (DESIGN 5.7)")
    actions = spreads.add_subparsers(dest="action", metavar="action", required=True)
    measure = actions.add_parser(
        "measure", parents=[common],
        help="measure the median quoted spread per exchange-local hour, in ticks, and "
        "write <config>/spreads/<symbol>.toml; never overwrites (decision 2026-10-12 13)",
    )
    measure.add_argument("--symbol", required=True, help="the instrument to measure")
    measure.add_argument(
        "--quotes", metavar="FILE", default=None,
        help="a Parquet quote sample with columns ts (UTC), bid, ask (default: the "
        "vendor's quotes, which need DATABENTO_API_KEY)",
    )
    measure.add_argument(
        "--days", type=int, default=None,
        help="calendar days of vendor quotes, ending at the vendor's available_until at "
        "--as-of (default: 20)",
    )
    measure.set_defaults(handler=_spreads_measure)


SUBCOMMANDS.append(_add_spreads)


def _doctor(ctx: Context, args: argparse.Namespace) -> int:
    from discotrade.doctor import run

    return run(ctx, args)


def _add_doctor(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    doctor = subparsers.add_parser(
        "doctor", parents=[common],
        help="live checks against the real services (DESIGN 19.3); in this step only "
        "--live vendor (L1) and --live spreads (L2)",
    )
    doctor.add_argument(
        "--live", metavar="NAME", default=None,
        help="the live check to run: vendor (L1) and spreads (L2) need DATABENTO_API_KEY "
        "and refuse, exit 1, without it; plain doctor and the other checks are built by "
        "step S5.1",
    )
    doctor.add_argument(
        "--days", type=int, default=None,
        help="spreads (L2): calendar days of vendor quotes, ending at the vendor's "
        "available_until at --as-of (default: that of spreads measure)",
    )
    doctor.set_defaults(handler=_doctor)


SUBCOMMANDS.append(_add_doctor)


#: The cost components, in the order they are reported (DESIGN 7.3).
_COSTS = ("fee", "spread", "slippage", "roll")


def _number(value: Any) -> Any:
    """A float that is not a finite number becomes None (JSON ``null``; decision 27)."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _backtest_result(path: Path, tc: Any, window: Any, strat: Any, evaluations: list,
                     tables: dict[str, Any]) -> dict[str, Any]:
    """The result of a backtest as a plain map: the metrics of DESIGN 8 at 1x
    with ``sharpe_2x`` and ``total_return_2x``, the cost totals by component,
    the cost model's version and config hash (decision 27), and per instrument
    its bars, trades, lowest and highest position, cost components and net
    totals. A subject's cost total is the sum over its instruments divided by
    their count, as its daily net return is (decision 23), so that
    ``total_return`` is the summed gross over the count less the summed cost
    totals."""
    from dataclasses import asdict

    from discotrade import costs, metrics

    m = metrics.compute([metrics.leg(e) for e in evaluations])
    n = len(evaluations)
    per: dict[str, Any] = {}
    for e in evaluations:
        rows = e.rows
        positions = [*rows["p"].tolist(), *rows["h"].tolist()]
        per[e.symbol] = {
            "bars": len(rows),
            "trades": metrics.trades([metrics.leg(e)]),
            "position_min": min(positions) if positions else None,
            "position_max": max(positions) if positions else None,
            **{k: float(rows[k].sum()) for k in (*_COSTS, "cost", "net_1x", "net_2x")},
        }
    result: dict[str, Any] = {
        "strategy": path.relative_to(REPO_ROOT).as_posix(),
        "params": dict(strat.params),
        "track": tc.track.name,
        "from": window.first.isoformat(),
        "to": window.last.isoformat(),
        **asdict(m),
        "costs": {k: sum(p[k] for p in per.values()) / n for k in _COSTS},
        "cost_model": costs.VERSION,
        "config_hash": costs.config_hash(tc.instruments, tables),
        "instruments": per,
    }

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        return _number(value)

    return clean(result)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool) or isinstance(value, int):
        return str(value)
    return f"{value:.6g}"


def _print_backtest(r: dict[str, Any]) -> None:
    """The plain report. I-4: the one figure read from gross returns,
    ``breakeven_cost``, is printed on the line of the net totals at 1x and 2x."""
    net = f"net_1x total_return {_fmt(r['total_return'])}, " \
          f"net_2x total_return_2x {_fmt(r['total_return_2x'])}"
    params = " ".join(f"{k}={_fmt(v)}" for k, v in r["params"].items())
    print(f"backtest {r['strategy']} ({params}) on track {r['track']}, "
          f"{r['from']} to {r['to']}: {len(r['instruments'])} instruments, {r['days']} days")
    print(net)
    print(f"sharpe {_fmt(r['sharpe'])}, sharpe_2x {_fmt(r['sharpe_2x'])}")
    print(f"max_drawdown {_fmt(r['max_drawdown'])}, trades {r['trades']}, "
          f"avg_holding_bars {_fmt(r['avg_holding_bars'])}, fragile {r['fragile']}")
    print(f"breakeven_cost {_fmt(r['breakeven_cost'])} bps, beside {net}")
    print("costs at 1x: " + ", ".join(f"{k} {_fmt(r['costs'][k])}" for k in _COSTS))
    for symbol, p in r["instruments"].items():
        print(f"{symbol}: {p['bars']} bars, trades {p['trades']}, position "
              f"{_fmt(p['position_min'])} to {_fmt(p['position_max'])}, "
              + ", ".join(f"{k} {_fmt(p[k])}" for k in _COSTS)
              + f", net_1x {_fmt(p['net_1x'])}, net_2x {_fmt(p['net_2x'])}")
    print(f"cost model {r['cost_model']}, config hash {r['config_hash']}")


def _backtest(ctx: Context, args: argparse.Namespace) -> int:
    from discotrade.backtest import EvaluationError, evaluate
    from discotrade.bars.store import BarStoreError
    from discotrade.config import (
        ConfigError,
        DateRange,
        load_calendar,
        load_thresholds,
        load_track_config,
    )
    from discotrade.spreads import spread_table
    from discotrade.strategy import ResultError, StrategyError, load_strategy_file

    def fail(why: object) -> int:
        print(f"backtest: FAIL: {why}", file=sys.stderr)
        return 1

    def usage(why: str) -> int:
        print(f"discotrade backtest: error: {why}", file=sys.stderr)
        return 2

    # Usage errors first (decision 27): a file outside reference/, --from after --to.
    reference = REFERENCE_ROOT
    path = Path(args.file).expanduser().resolve()
    if not _inside(path, reference) or path == reference:
        return usage(f"{args.file} does not lie under {reference}; only the repository's "
                     f"reference strategies are run (decision 2026-10-12 21)")
    if not path.is_file():
        return usage(f"{args.file} is not a file")
    if args.first > args.last:
        return usage(f"--from {args.first.isoformat()} is after --to {args.last.isoformat()}")
    if ctx.state is None:
        return fail("no state directory (--state or $DISCOTRADE_STATE)")
    window = DateRange(args.first, args.last)
    try:
        thresholds = load_thresholds(ctx.config / "thresholds.toml")
        strat = load_strategy_file(path, thresholds)
        tc = load_track_config(ctx.config, ctx.track)
        calendars = {
            name: load_calendar(ctx.config / "calendars" / f"{name}.toml")
            for name in sorted({inst.calendar for inst in tc.instruments})
        }
        # Each instrument's measured spread table when it has one (DESIGN 5.7).
        tables = {inst.symbol: spread_table(ctx.config, inst.symbol)
                  for inst in tc.instruments}
        evaluations = [
            evaluate(ctx.state, tc.track, inst, calendars[inst.calendar], strat, window,
                     spread_table=tables[inst.symbol])
            for inst in tc.instruments
        ]
    except (ConfigError, StrategyError, ResultError, EvaluationError, BarStoreError,
            OSError, ValueError) as exc:
        return fail(exc)
    result = _backtest_result(path, tc, window, strat, evaluations, tables)
    if args.json:
        print(json.dumps(result, sort_keys=True, allow_nan=False, separators=(",", ":")))
    else:
        _print_backtest(result)
    return 0


def _add_backtest(subparsers: argparse._SubParsersAction,
                  common: argparse.ArgumentParser) -> None:
    backtest = subparsers.add_parser(
        "backtest", parents=[common],
        help="evaluate a strategy file from the repository's reference/ with its PARAMS on "
        "every instrument of --track, from the stored bars and rolls, over a window, and "
        "print the metrics of DESIGN 8 net of costs at 1x and 2x (decision 2026-10-12 27)",
    )
    backtest.add_argument("file", help="a strategy file under the repository's reference/")
    backtest.add_argument("--from", dest="first", metavar="YYYY-MM-DD", required=True,
                          type=date.fromisoformat, help="first trading date of the window")
    backtest.add_argument("--to", dest="last", metavar="YYYY-MM-DD", required=True,
                          type=date.fromisoformat, help="last trading date of the window")
    backtest.add_argument("--json", action="store_true",
                          help="print one JSON object; a value that is not a number is null")
    backtest.set_defaults(handler=_backtest)


SUBCOMMANDS.append(_add_backtest)


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
