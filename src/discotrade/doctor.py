"""Offline and live checks (DESIGN 19.3; decision 2026-10-12 15; I-13).

``discotrade doctor`` runs ``--live vendor`` (L1) and ``--live spreads`` (L2),
built in step S0.2, ``--live sandbox`` (L5), built in step S2.2 (decision
2026-10-14-m13 103 (d)), and ``--live workers`` (L3) for its offline behaviour
and the model list, built in step S3.2a (decision 2026-10-16-m15 122 (e));
plain ``doctor`` and every other check name are usage errors (exit 2) that name
step S5.1, which builds them.

L1, ``--live vendor``, runs against the real vendor and prints, for every
instrument of the track whose adapter is ``vendor``: the vendor's cost
estimate for the full history (from ``trusted_from`` to ``available_until``);
the real delay (the injected clock's now minus the end of the dataset as the
vendor reports it) beside the adapter's 24-hour embargo; one trading day
fetched (the latest whose bars closed by ``available_until``), with the
contracts it resolved; and that day's gap fraction (missing over expected
bars of the calendar). Without ``DATABENTO_API_KEY`` it refuses before any
request and exits 1. A check that fails prints why and the command exits 1.

L2, ``--live spreads``, measures, for every instrument of the track whose
adapter is ``vendor``, the median quoted spread per exchange-local hour from a
sample of the vendor's quotes (``--days`` calendar days ending at the vendor's
``available_until``), writes ``<config>/spreads/<symbol>.toml`` (never over an
existing table), and reports every instrument with a main-session hour above
one tick (SPEC decision 14). Without ``DATABENTO_API_KEY`` it refuses before
any request, writes nothing and exits 1.

L3, ``--live workers`` (decision 2026-10-16-m15 122 (e)), reads
``<config>/models.toml`` and prints each configured model against the worker
provider's model list, exit 1 when one is not listed. Without the worker
key, without ``models.toml`` or with an empty ``base_url`` it
refuses with one line, exits 1 and makes no request. The rest of L3 (whether a
seed is accepted, twenty replay days with the real pool) is step S3.2b's.

L5, ``--live sandbox``, runs the container self-test of ``discotrade sandbox
selftest`` (:func:`discotrade.sandbox.container.selftest`). Without a container
runtime it refuses, naming that none was found, exits 1 and starts nothing.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any, TextIO

from discotrade.config import ConfigError, load_calendar, load_track_config

#: Where plain ``doctor`` and the checks not built in step S0.2 are built.
LATER_STEP = "S5.1"
#: The checks of DESIGN 19.3 built so far (decision 2026-10-12 15; decision
#: 2026-10-14-m13 103 (d)), by name.
LIVE: dict[str, Callable[..., int]] = {}
#: The transport L3 hands the worker provider; ``None`` is the real network. Tests
#: put an ``httpx.MockTransport`` here (I-11).
WORKERS_TRANSPORT: Any = None
#: L3's request timeout in seconds: decision 123 (d)'s ``request_timeout_seconds``,
#: which step S3.2a U4 adds to ``config/run.toml``.
WORKERS_TIMEOUT_SECONDS = 300.0


def usage_error(message: str) -> int:
    print(f"doctor: usage error: {message}", file=sys.stderr)
    return 2


def run(ctx: Any, args: argparse.Namespace) -> int:
    """The ``doctor`` dispatcher: exit 0, 1, or 2 on a usage error."""
    name = args.live
    if name is None:
        return usage_error(f"plain 'doctor' (the offline checks) is built by step "
                           f"{LATER_STEP}; in this step give --live vendor, --live spreads, "
                           f"--live workers or --live sandbox")
    check = LIVE.get(name)
    if check is None:
        return usage_error(f"no live check {name!r} in this step; the live checks other than "
                           f"vendor, spreads, workers and sandbox are built by step "
                           f"{LATER_STEP} (DESIGN 19.3)")
    return check(ctx, out=sys.stdout, err=sys.stderr, args=args)


def live_vendor(ctx: Any, out: TextIO, err: TextIO, args: Any = None) -> int:
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


def live_spreads(ctx: Any, out: TextIO, err: TextIO, args: Any = None) -> int:
    """Live check L2 (DESIGN 19.3) against the real vendor's quotes."""
    from discotrade.sources.base import SourceError
    from discotrade.sources.vendor import VendorSource, key_present, no_key_message
    from discotrade.spreads import (
        COMMIT_NOTE,
        DEFAULT_DAYS,
        SpreadError,
        marginal_line,
        measure_and_write,
        refuse_existing,
        vendor_quotes,
    )

    if not key_present():
        print(f"doctor --live spreads: FAIL: {no_key_message()}", file=err)
        return 1
    days = getattr(args, "days", None) or DEFAULT_DAYS
    try:
        tc = load_track_config(ctx.config, ctx.track)
        calendars = {name: load_calendar(ctx.config / "calendars" / f"{name}.toml")
                     for name in sorted({i.calendar for i in tc.instruments})}
    except (ConfigError, OSError) as exc:
        print(f"doctor --live spreads: FAIL: {exc}", file=err)
        return 1
    vendors = [i for i in tc.instruments if i.source.adapter == "vendor"]
    if not vendors:
        print(f"doctor --live spreads: FAIL: track {tc.track.name} has no instrument whose "
              "adapter is vendor", file=err)
        return 1
    now = ctx.clock.now()
    source = VendorSource(tc.track.bar_seconds)
    until = source.available_until(now)
    start = until - timedelta(days=days)
    print(f"L2 spreads: track {tc.track.name}, quotes {start.isoformat()} to "
          f"{until.isoformat()}", file=out)
    failed = 0
    marginal = []
    for inst in vendors:
        try:
            refuse_existing(ctx.config, inst.symbol)
            quotes, text = vendor_quotes(inst, start, until, source)
            path, table = measure_and_write(ctx.config, inst, calendars[inst.calendar],
                                            quotes, text, now.date())
        except (SpreadError, SourceError, OSError, ValueError) as exc:
            print(f"{inst.symbol}: FAIL: {exc}", file=out)
            failed += 1
            continue
        print(f"{inst.symbol}: wrote {path}", file=out)
        line = marginal_line(inst, table)
        print(line, file=out)
        if table.marginal(inst.main_session):
            marginal.append(inst.symbol)
    print(f"marginal instruments (SPEC decision 14): {', '.join(marginal) or 'none'}",
          file=out)
    if failed < len(vendors):
        print(f"note: {COMMIT_NOTE}", file=out)
    print(f"doctor --live spreads: {'FAIL' if failed else 'ok'}, {failed} of {len(vendors)} "
          "instruments failed", file=out)
    return 1 if failed else 0


LIVE["spreads"] = live_spreads


def live_workers(ctx: Any, out: TextIO, err: TextIO, args: Any = None) -> int:
    """Live check L3 (DESIGN 19.3), its first part: the pool against the provider's list."""
    from discotrade.workers.providers import (
        ProviderError,
        key_present,
        no_key_message,
        openai_compat_from_env,
    )

    head = "doctor --live workers: FAIL:"
    if not key_present():
        print(f"{head} {no_key_message()}", file=err)
        return 1
    path = ctx.config / "models.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        base_url = data.get("base_url", "")
        models = [(m["id"], bool(m.get("pool", True))) for m in data.get("model", [])]
        if not isinstance(base_url, str) or not all(isinstance(i, str) for i, _ in models):
            raise ValueError("base_url and every model id must be strings")
    except FileNotFoundError:
        print(f"{head} {path} does not exist (step S3.2a U4 creates config/models.toml); "
              "no request was made", file=err)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"{head} {path} cannot be read: {exc}; no request was made", file=err)
        return 1
    try:
        provider = openai_compat_from_env(base_url, WORKERS_TIMEOUT_SECONDS,
                                          transport=WORKERS_TRANSPORT)
        listed = set(provider.list_models())
    except ProviderError as exc:
        print(f"{head} {exc}", file=err)
        return 1
    print(f"L3 workers: {provider.base_url}, the provider lists {len(listed)} models",
          file=out)
    missing = 0
    for model, pool in models:
        found = model in listed
        missing += not found
        print(f"{model} ({'pool' if pool else 'fallback'}): "
              f"{'listed' if found else 'NOT listed'}", file=out)
    print(f"doctor --live workers: {'FAIL' if missing else 'ok'}, {missing} of {len(models)} "
          "configured models not listed; the seed and the twenty replay days of L3 are "
          "step S3.2b's", file=out)
    return 1 if missing else 0


LIVE["workers"] = live_workers


def live_sandbox(ctx: Any, out: TextIO, err: TextIO, args: Any = None) -> int:
    """Live check L5 (DESIGN 19.3): the container self-test on this machine."""
    from discotrade.sandbox.container import selftest

    return selftest(ctx, out=out, err=err, command="doctor --live sandbox")


LIVE["sandbox"] = live_sandbox
