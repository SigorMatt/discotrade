"""Offline and live checks (DESIGN 19.3; decision 2026-10-12 15; I-13).

In step S0.2 ``discotrade doctor`` runs only ``--live vendor`` (L1) and
``--live spreads`` (L2); plain ``doctor`` and every other check name are
usage errors (exit 2) that name step S5.1, which builds them.

L1, ``--live vendor``, runs against the real vendor and prints, for every
instrument of the track whose adapter is ``vendor``: the vendor's cost
estimate for the full history (from ``trusted_from`` to ``available_until``);
the real delay (the injected clock's now minus the end of the dataset as the
vendor reports it) beside the adapter's 24-hour embargo; one trading day
fetched (the latest whose bars closed by ``available_until``), with the
contracts it resolved; and that day's gap fraction (missing over expected
bars of the calendar). Without ``DATABENTO_API_KEY`` it refuses before any
request and exits 1. A check that fails prints why and the command exits 1.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any, TextIO

from discotrade.config import ConfigError, load_calendar, load_track_config

#: Where plain ``doctor`` and the checks not built in step S0.2 are built.
LATER_STEP = "S5.1"
#: The checks of DESIGN 19.3 built in step S0.2 (decision 2026-10-12 15), by name.
LIVE: dict[str, Callable[..., int]] = {}
#: Every check step S0.2 builds, whether or not it is registered yet.
STEP_CHECKS = ("vendor", "spreads")


def usage_error(message: str) -> int:
    print(f"doctor: usage error: {message}", file=sys.stderr)
    return 2


def run(ctx: Any, args: argparse.Namespace) -> int:
    """The ``doctor`` dispatcher: exit 0, 1, or 2 on a usage error."""
    name = args.live
    if name is None:
        return usage_error(f"plain 'doctor' (the offline checks) is built by step "
                           f"{LATER_STEP}; in this step give --live vendor or --live spreads")
    check = LIVE.get(name)
    if check is None and name in STEP_CHECKS:
        return usage_error(f"--live {name} is not built yet; step S0.2 builds it")
    if check is None:
        return usage_error(f"no live check {name!r} in this step; the live checks other than "
                           f"vendor and spreads are built by step {LATER_STEP} (DESIGN 19.3)")
    return check(ctx, out=sys.stdout, err=sys.stderr)


def live_vendor(ctx: Any, out: TextIO, err: TextIO) -> int:
    """Live check L1 (DESIGN 19.3) against the real vendor."""
    from discotrade.bars.gaps import day_end, latest_closed_day
    from discotrade.sources.base import SourceError
    from discotrade.sources.vendor import (
        CONTINUOUS,
        EMBARGO,
        VendorSource,
        key_present,
        no_key_message,
    )
    from discotrade.tradingcal import expected_bars

    if not key_present():
        print(f"doctor --live vendor: FAIL: {no_key_message()}", file=err)
        return 1
    try:
        tc = load_track_config(ctx.config, ctx.track)
        calendars = {name: load_calendar(ctx.config / "calendars" / f"{name}.toml")
                     for name in sorted({i.calendar for i in tc.instruments})}
    except (ConfigError, OSError) as exc:
        print(f"doctor --live vendor: FAIL: {exc}", file=err)
        return 1
    vendors = [i for i in tc.instruments if i.source.adapter == "vendor"]
    if not vendors:
        print(f"doctor --live vendor: FAIL: track {tc.track.name} has no instrument whose "
              "adapter is vendor", file=err)
        return 1
    bar = tc.track.bar_seconds
    now = ctx.clock.now()
    source = VendorSource(bar)
    until = source.available_until(now)
    failed = 0
    print(f"L1 vendor: track {tc.track.name}, now {now.isoformat()}, available until "
          f"{until.isoformat()} (embargo {EMBARGO})", file=out)
    for inst in vendors:
        symbol = inst.symbol
        try:
            history = datetime.combine(inst.trusted_from, time(), tzinfo=UTC)
            cost = source.cost(inst, inst.source.get("symbol"), CONTINUOUS, history, until)
            print(f"{symbol}: cost estimate for the full history {history.date().isoformat()} "
                  f"to {until.isoformat()}: {cost:.2f} USD", file=out)
            end = source.dataset_end(inst)
            delay = now - end
            within = "within" if delay <= EMBARGO else "BEYOND"
            print(f"{symbol}: dataset ends {end.isoformat()}, delay {delay}, {within} the "
                  f"embargo", file=out)
            cal = calendars[inst.calendar]
            day = latest_closed_day(cal, until, bar)
            lo, hi = day_end(cal, day - timedelta(days=1)), day_end(cal, day)
            bars = source.fetch(inst, lo, hi)
            expected = expected_bars(cal, lo, hi, bar)
            have = set(bars["ts"].dt.to_pydatetime())
            missing = sum(1 for t in expected if t not in have)
            contracts = sorted(set(bars["contract"]))
            resolved = bool(contracts) and inst.source.get("symbol") not in contracts
            print(f"{symbol}: day {day.isoformat()}: {len(bars)} bars fetched, contracts "
                  f"{contracts}, contract {'resolved' if resolved else 'NOT resolved'}",
                  file=out)
            fraction = missing / len(expected) if expected else 0.0
            print(f"{symbol}: day {day.isoformat()}: {missing} missing of {len(expected)} "
                  f"expected, gap fraction {fraction:.6f}", file=out)
            if not resolved:
                failed += 1
        except (SourceError, ValueError) as exc:
            print(f"{symbol}: FAIL: {exc}", file=out)
            failed += 1
    print(f"doctor --live vendor: {'FAIL' if failed else 'ok'}, {failed} of {len(vendors)} "
          "instruments failed", file=out)
    return 1 if failed else 0


LIVE["vendor"] = live_vendor
