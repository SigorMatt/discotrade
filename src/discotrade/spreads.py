"""Spread tables and their measurement (DESIGN 5.7; decisions 2026-10-12 13, 14; I-10).

**The rule.** The spread of an instrument at a bar, in ticks, is the measured
table's value for the bar's exchange-local hour of day (the hour of the bar's
open time in the calendar's time zone; UTC for an always-open calendar) when
``<config>/spreads/<symbol>.toml`` exists, and otherwise ``spread_ticks_main``
when the bar lies in the instrument's main session (``tradingcal``) and
``spread_ticks_off`` when it does not.

**The measurement** (decision 13). From a quote sample (``ts`` UTC, ``bid``,
``ask``): quotes with a value that is not finite or with the ask below the bid
are dropped, and so are quotes at an instant the calendar is closed; each kept
quote's spread is ``(ask - bid) / tick_size`` ticks, rounded to 6 decimals; an
hour's value is the median over the kept quotes whose exchange-local hour it
is. The sample's days are the exchange-local dates from the first kept quote's
to the last's, whole. An hour in which the calendar is never open in those
days (a daily break) takes the largest median of the measured hours, and the
file's description lists it; an hour in which the calendar is open but no quote
was kept is an error naming the hour, and nothing is written. A table is
written once: an existing file is never overwritten (DESIGN 4.3: a change to
it is the owner's).

**The vendor's quotes.** Without ``--quotes`` the sample comes from the vendor
adapter's client, with the key handling of ``sources/vendor.py`` (no key, no
request; errors redacted). The calls, NOT PROVEN against the real service
until live check L2: ``metadata.get_cost(dataset=, symbols=[...],
schema="bbo-1m", stype_in="continuous", start=, end=)`` (refused above the
instrument's ``max_cost_usd``, nothing fetched), then
``timeseries.get_range(...)`` with the same keywords, whose
``.to_df(price_type="float", pretty_ts=True, map_symbols=False)`` is a frame
indexed (or with a column) ``ts_recv`` with ``bid_px_00`` and ``ask_px_00``.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from discotrade.config import (
    HOURS,
    MARGINAL_SPREAD_TICKS,
    Calendar,
    Instrument,
    SpreadTable,
    load_spread_table,
)
from discotrade.tradingcal import in_main_session, open_intervals

#: The vendor's quote schema used for a sample: the best bid and offer each minute.
QUOTE_SCHEMA = "bbo-1m"
#: Calendar days of vendor quotes measured when none are given (DESIGN is silent).
DEFAULT_DAYS = 20
DECIMALS = 6


class SpreadError(ValueError):
    """A quote sample cannot give a spread table, or the table cannot be written."""


# --- the rule (DESIGN 5.7) -----------------------------------------------------------


def _zone(calendar: Calendar) -> tzinfo:
    return UTC if calendar.always_open else ZoneInfo(calendar.tz or "UTC")


def local_hour(calendar: Calendar, ts: datetime) -> int:
    """The exchange-local hour of day of the instant ``ts`` (timezone-aware)."""
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError(f"instant {ts!r} must be timezone-aware")
    return ts.astimezone(_zone(calendar)).hour


def table_path(config_dir: Path, symbol: str) -> Path:
    return Path(config_dir) / "spreads" / f"{symbol}.toml"


def spread_table(config_dir: Path, symbol: str) -> SpreadTable | None:
    """The instrument's measured table, or None when it has none."""
    path = table_path(config_dir, symbol)
    return load_spread_table(path) if path.is_file() else None


def spread_ticks(instrument: Instrument, calendar: Calendar, table: SpreadTable | None,
                 ts: datetime) -> float:
    """The spread, in ticks, of ``instrument`` at the bar opening at ``ts``."""
    if table is not None:
        if table.symbol != instrument.symbol:
            raise ValueError(f"the spread table of {table.symbol!r} is not "
                             f"{instrument.symbol!r}'s")
        return table.ticks[local_hour(calendar, ts)]
    if in_main_session(calendar, instrument.main_session, ts):
        return instrument.cost.spread_ticks_main
    return instrument.cost.spread_ticks_off


# --- the measurement (decision 2026-10-12 13) ----------------------------------------


@dataclass(frozen=True)
class Measurement:
    ticks: tuple[float, ...]      # per exchange-local hour, 0 to 23
    filled: tuple[int, ...]       # hours never open in the sample's days
    kept: int                     # quotes measured
    dropped: int                  # not finite, or ask below bid
    closed: int                   # at an instant the calendar is closed
    first: datetime               # first and last kept quote, UTC
    last: datetime
    first_day: date               # the sample's exchange-local dates
    last_day: date
    zone: str


def _open_hours(calendar: Calendar, first_day: date, last_day: date) -> set[int]:
    """The exchange-local hours of day in which the calendar is open on those dates."""
    zone = _zone(calendar)
    lo = datetime.combine(first_day, datetime.min.time(), tzinfo=zone)
    hi = datetime.combine(last_day + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    hours: set[int] = set()
    for a, b in open_intervals(calendar, lo.astimezone(UTC), hi.astimezone(UTC)):
        t = a
        while t < b:
            local = t.astimezone(zone)
            hours.add(local.hour)
            into = local.minute * 60 + local.second + local.microsecond / 1e6
            t += timedelta(seconds=3600 - into)
    return hours


def _open_mask(calendar: Calendar, ts: pd.Series) -> np.ndarray:
    lo = ts.min().to_pydatetime()
    hi = ts.max().to_pydatetime() + timedelta(seconds=1)
    intervals = open_intervals(calendar, lo, hi)
    if not intervals:
        return np.zeros(len(ts), dtype=bool)
    starts = pd.DatetimeIndex([a for a, _ in intervals]).as_unit("ns").asi8
    ends = pd.DatetimeIndex([b for _, b in intervals]).as_unit("ns").asi8
    nanos = pd.DatetimeIndex(ts).as_unit("ns").asi8
    at = np.searchsorted(starts, nanos, side="right") - 1
    return (at >= 0) & (nanos < ends[np.clip(at, 0, None)])


def _quotes(frame: Any) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise SpreadError("the quote sample is not a table")
    missing = [c for c in ("ts", "bid", "ask") if c not in frame.columns]
    if missing:
        raise SpreadError(f"the quote sample lacks the columns {missing} (ts, bid, ask)")
    try:
        ts = pd.DatetimeIndex(frame["ts"])
        bid = frame["bid"].astype("float64").to_numpy()
        ask = frame["ask"].astype("float64").to_numpy()
    except (TypeError, ValueError) as exc:
        raise SpreadError(f"the quote sample is malformed: {exc}") from None
    if ts.tz is None and len(ts):
        raise SpreadError("the quote sample has times without a time zone")
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    return pd.DataFrame({"ts": pd.Series(ts.tz_convert("UTC")), "bid": bid, "ask": ask})


def measure(quotes: Any, instrument: Instrument, calendar: Calendar) -> Measurement:
    """The median quoted spread per exchange-local hour, in ticks (decision 13)."""
    q = _quotes(quotes)
    good = np.isfinite(q["bid"]) & np.isfinite(q["ask"]) & (q["ask"] >= q["bid"])
    dropped = int((~good).sum())
    q = q[good.to_numpy()].reset_index(drop=True)
    closed = 0
    if len(q):
        is_open = _open_mask(calendar, q["ts"])
        closed = int((~is_open).sum())
        q = q[is_open].reset_index(drop=True)
    if not len(q):
        raise SpreadError(f"the quote sample has no quote to measure ({dropped} dropped as "
                          f"not finite or crossed, {closed} at a closed instant)")
    zone = _zone(calendar)
    local = q["ts"].dt.tz_convert(zone)
    spread = ((q["ask"] - q["bid"]) / instrument.tick_size).round(DECIMALS)
    medians = spread.groupby(local.dt.hour.to_numpy()).median()
    first, last = q["ts"].min().to_pydatetime(), q["ts"].max().to_pydatetime()
    first_day, last_day = local.min().date(), local.max().date()
    open_hours = _open_hours(calendar, first_day, last_day)
    empty = sorted(h for h in open_hours if h not in medians.index)
    if empty:
        named = ", ".join(f"{h:02d}" for h in empty)
        raise SpreadError(f"{instrument.symbol}: the calendar is open in the exchange-local "
                          f"hour(s) {named} of the sample's days ({first_day} to {last_day}) "
                          "but the sample has no quote there; nothing was written")
    largest = float(medians.max())
    filled = tuple(h for h in range(HOURS) if h not in medians.index)
    ticks = tuple(round(float(medians[h]), DECIMALS) if h in medians.index else largest
                  for h in range(HOURS))
    return Measurement(
        ticks=ticks, filled=filled, kept=len(q), dropped=dropped, closed=closed,
        first=first, last=last, first_day=first_day, last_day=last_day,
        zone=str(getattr(zone, "key", "UTC")),
    )


def describe(m: Measurement, tick_size: float) -> str:
    filled = ", ".join(f"{h:02d}" for h in m.filled) or "none"
    return (
        f"{m.kept} quotes (ts, bid, ask) from {m.first.isoformat()} to {m.last.isoformat()}, "
        f"exchange-local dates {m.first_day.isoformat()} to {m.last_day.isoformat()} in "
        f"{m.zone}; median quoted spread per exchange-local hour in ticks of {tick_size:g}; "
        f"{m.dropped} quotes dropped as not finite or crossed, {m.closed} at a closed "
        f"instant; hours never open in the sample's days, given the largest measured "
        f"median (decision 2026-10-12 13): {filled}"
    )


def render(symbol: str, m: Measurement, tick_size: float, source: str, checked: date) -> str:
    """The table file's text (TOML)."""
    rows = []
    for i in range(0, HOURS, 8):
        values = ", ".join(repr(v) for v in m.ticks[i:i + 8])
        rows.append(f"    {values},   # {i:02d} to {i + 7:02d}")
    return "\n".join([
        "# Measured spread table (DESIGN 5.7; decision 2026-10-12 13): the median quoted",
        "# spread in ticks per exchange-local hour of day, index 0 is 00:00 to 01:00.",
        "# Frozen once committed (DESIGN 4.3, I-10): committing it needs a",
        "# config/HISTORY.toml entry and a decisions file.",
        f"symbol = {json.dumps(symbol)}",
        "spread_ticks = [",
        *rows,
        "]",
        f"description = {json.dumps(describe(m, tick_size))}",
        f'checked = "{checked.isoformat()}"',
        f"source = {json.dumps(source)}",
        "verified = false",
        "",
    ])


def refuse_existing(config_dir: Path, symbol: str) -> Path:
    path = table_path(config_dir, symbol)
    if path.exists():
        raise SpreadError(f"{path} exists; a spread table is never overwritten (DESIGN 4.3: "
                          "changing it is the owner's decision)")
    return path


def write_table(config_dir: Path, symbol: str, text: str) -> Path:
    """Write the new table beside, then link it into place; never overwrite."""
    path = refuse_existing(config_dir, symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{symbol}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise SpreadError(f"{path} exists; a spread table is never overwritten") from None
    finally:
        os.unlink(tmp)
    return path


def read_quotes(path: Path) -> pd.DataFrame:
    """A quote sample from a Parquet file with columns ts, bid, ask."""
    try:
        return pd.read_parquet(path)
    except (OSError, ValueError) as exc:
        raise SpreadError(f"{path}: cannot read the quote sample: {exc}") from None


# --- the vendor's quotes -------------------------------------------------------------


def vendor_quotes(instrument: Instrument, start: datetime, end: datetime,
                  source: Any = None) -> tuple[pd.DataFrame, str]:
    """A quote sample in [start, end) from the vendor, and a text naming it.

    Refuses without the key before any request, and above ``max_cost_usd``
    before fetching (``SourceError``, whose text never holds the key).
    """
    from discotrade.sources.base import SourceError
    from discotrade.sources.vendor import CONTINUOUS, DEFAULT_MAX_COST_USD, VendorSource

    if instrument.source.adapter != "vendor":
        raise SpreadError(f"{instrument.symbol}: source adapter is "
                          f"{instrument.source.adapter!r}, not 'vendor'; give --quotes")
    # The bar length only picks the adapter's bar schema, which quotes do not use.
    source = source if source is not None else VendorSource(3600)
    dataset, symbol = instrument.source.get("dataset"), instrument.source.get("symbol")
    client = source.client()
    keywords = dict(dataset=dataset, symbols=[symbol], schema=QUOTE_SCHEMA,
                    stype_in=CONTINUOUS, start=start.astimezone(UTC).isoformat(),
                    end=end.astimezone(UTC).isoformat())
    guard: Callable[[str, Callable[[], Any]], Any] = source._guard
    cost = guard("cost estimate", lambda: client.metadata.get_cost(**keywords))
    if isinstance(cost, bool) or not isinstance(cost, int | float) or not math.isfinite(cost):
        raise SourceError(f"{instrument.symbol}: the vendor's cost estimate is not a number: "
                          f"{cost!r}")
    limit = instrument.source.get("max_cost_usd", DEFAULT_MAX_COST_USD)
    if cost > limit:
        raise SourceError(f"{instrument.symbol}: the vendor's cost estimate {cost:.2f} USD for "
                          f"quotes {keywords['start']} to {keywords['end']} is above "
                          f"max_cost_usd {limit:g}; nothing was fetched")
    frame = guard("quotes", lambda: client.timeseries.get_range(**keywords).to_df(
        price_type="float", pretty_ts=True, map_symbols=False))
    if not isinstance(frame, pd.DataFrame):
        raise SourceError(f"{instrument.symbol}: the vendor's quotes are not a table")
    if frame.index.name == "ts_recv":
        frame = frame.reset_index()
    missing = [c for c in ("ts_recv", "bid_px_00", "ask_px_00") if c not in frame.columns]
    if missing:
        raise SourceError(f"{instrument.symbol}: the vendor's quotes lack the columns "
                          f"{missing}")
    quotes = pd.DataFrame({"ts": frame["ts_recv"].to_numpy(),
                           "bid": frame["bid_px_00"].to_numpy(),
                           "ask": frame["ask_px_00"].to_numpy()})
    text = (f"vendor quote sample: dataset {dataset}, symbol {symbol}, schema "
            f"{QUOTE_SCHEMA}, {keywords['start']} to {keywords['end']}")
    return quotes, text


def measure_and_write(config_dir: Path, instrument: Instrument, calendar: Calendar,
                      quotes: Any, source: str, checked: date) -> tuple[Path, SpreadTable]:
    """Measure, then write ``<config>/spreads/<symbol>.toml``; nothing is written on error."""
    refuse_existing(config_dir, instrument.symbol)
    m = measure(quotes, instrument, calendar)
    text = render(instrument.symbol, m, instrument.tick_size, source, checked)
    path = write_table(config_dir, instrument.symbol, text)
    return path, load_spread_table(path)


#: What a new table needs before it is committed (DESIGN 4.3; decision 13).
COMMIT_NOTE = ("the new file needs a config/HISTORY.toml entry (key \"*\") and a decisions "
               "file under meta/decisions/ before it is committed (DESIGN 4.3)")


def marginal_line(instrument: Instrument, table: SpreadTable) -> str:
    over = table.marginal(instrument.main_session)
    if not over:
        return (f"{instrument.symbol}: no main-session hour above {MARGINAL_SPREAD_TICKS:g} "
                "tick")
    hours = ", ".join(f"hour {h:02d} {v:g} ticks" for h, v in over)
    return (f"{instrument.symbol}: marginal: main-session spread above "
            f"{MARGINAL_SPREAD_TICKS:g} tick ({hours}); SPEC decision 14 applies")
