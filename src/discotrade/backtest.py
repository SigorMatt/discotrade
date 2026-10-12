"""The evaluation loop and gross returns (DESIGN 6.2, 7.1, 7.2, 5.6; decisions
2026-10-12 22, 23, 24; R-20; I-2, I-12).

One instrument is evaluated at a time on a window, an inclusive range of
trading dates (decision 23). A stored bar is a window bar when its trading
date, by the instrument's own calendar, lies in the range and its ``ts`` is
not before the instrument's ``trusted_from`` (midnight UTC of that date). The
stored bars before the first window bar ``u0``, up to ``history_cap_bars - 1``
of them and none with ``ts`` before ``trusted_from`` ("history before this
date is never used", DESIGN 4.2), are context, so that the slice at ``u0``
holds up to ``history_cap_bars`` rows, all trusted. No bar before
``trusted_from`` is read into an :class:`Evaluation` at all.

At each window bar ``t`` the harness builds the slice of DESIGN 6.2 from the
bars up to ``t`` (never later: I-2), with prices adjusted as of ``t`` exactly
as :func:`discotrade.rolls.adjust` does, and calls the strategy with a fresh
frame. Its checked result (decision 22) is the target ``p(t)``. The position
in force during a window bar is ``h(u) = p(u-1)``, with ``h(u0) = 0`` (R-20);
the target of the window's last bar is recorded and never traded. The
function is not called at context bars: nothing it could return there is
ever used.

``u-1`` is always the previous stored bar (decision 24). A roll happens at
``u`` when its ``contract`` differs from the previous stored bar's; its gap is
read from ``<state>/rolls/<track>/<symbol>.jsonl`` and a contract change with
no record there with the same ``ts``, old and new contract stops the
evaluation with :class:`MissingRollError` (decision 2026-10-12 37: a record
with the right ``ts`` and other contracts is a missing one). The first bar read
is never a roll, so a contract change across ``trusted_from`` is none
(decision 2026-10-12 36). The gross return of DESIGN 7.2 is

    gross(u) = ( h(u-1) * (Oa(u) - Ca(u-1)) + h(u) * (Ca(u) - Oa(u)) ) / Or(u)

with prices adjusted as of ``u``: ``Oa(u)`` and ``Ca(u)`` are raw, and
``Ca(u-1)`` is the raw previous close plus the gap of a roll at ``u``. At
``u0`` the previous position is 0, so ``gross(u0) = 0``.

Costs (DESIGN 7.3, 7.4; decision 25). The positions become one
:class:`~discotrade.executor.Order` per window bar (decision bar ``u-1``,
previous position ``h(u-1)``, target ``h(u)``; at ``u0`` the previous position
is 0, and the decision bar is the last context bar, or none), priced by
:class:`~discotrade.executor.SimExecutor` against the bars read, with the
instrument's spread table when given. ``sigma`` reads stored bars before the
window too (decision 24): the context read is at least ``costs.SIGMA_RETURNS``
bars before ``u0``, all trusted, even when the history cap is smaller; the
strategy's slice is still capped at ``history_cap_bars`` rows.

The per-bar result is a frame with one row per window bar and decision 25's
columns: ``ts``, ``contract``, ``date`` (the trading date), ``p``, ``h``,
``gross``, ``trade``, ``fee``, ``spread``, ``slippage``, ``roll``, ``cost``,
``net_1x`` and ``net_2x``, the cost columns built from the fills. No clock is
read (I-12).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade import costs, metrics
from discotrade.bars.store import BarStore
from discotrade.config import Calendar, DateRange, Instrument, SpreadTable, Track
from discotrade.executor import Market, Order, SimExecutor
from discotrade.rolls import read_rolls, roll_path
from discotrade.strategy import Strategy, call_position
from discotrade.tradingcal import trading_date

#: The columns of a slice, in order (DESIGN 6.2).
SLICE_COLUMNS = ("open", "high", "low", "close", "volume", "hour", "weekday")
#: The columns of the per-bar result (decision 25).
ROW_COLUMNS = ("ts", "contract", "date", "p", "h", "gross", "trade", "fee", "spread",
               "slippage", "roll", "cost", "net_1x", "net_2x")
_PRICES = ("open", "high", "low", "close")
#: How far beyond a window's dates its bars can lie in UTC: a trading date is
#: the local date or the next one, and no time zone is a day away from UTC.
_MARGIN = timedelta(days=2)


class EvaluationError(RuntimeError):
    """An evaluation that cannot go on."""


class MissingRollError(EvaluationError):
    """A contract change with no roll record (decision 24)."""


@dataclass(frozen=True)
class Evaluation:
    """The evaluation of one strategy on one instrument over one window.

    ``rows`` holds one row per window bar (``ROW_COLUMNS``). ``bars`` holds the
    raw stored bars read (none before ``trusted_from``), context first:
    ``bars.iloc[first]`` is the first window bar, and ``gaps[k]`` is the gap
    of the roll at ``bars.iloc[k]`` (0 where there is none, and at row 0,
    whose previous bar was not read).
    ``rolled[k]`` says whether a roll happens there.
    """

    symbol: str
    rows: pd.DataFrame
    bars: pd.DataFrame
    first: int
    gaps: np.ndarray
    rolled: np.ndarray


def _midnight(day: Any) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, time(), tzinfo=UTC))


def _local_clock(ts: pd.Series, calendar: Calendar) -> tuple[np.ndarray, np.ndarray]:
    """``hour`` and ``weekday`` (Monday 0) of each bar's open in the calendar's
    time zone; UTC for an always-open calendar."""
    tz = "UTC" if calendar.always_open else calendar.tz
    local = ts.dt.tz_convert(tz)
    return (local.dt.hour.to_numpy(dtype=np.int64),
            local.dt.weekday.to_numpy(dtype=np.int64))


def _window_bars(store: BarStore, instrument: Instrument, calendar: Calendar,
                 window: DateRange) -> tuple[pd.DataFrame, list]:
    lo = max(_midnight(window.first) - _MARGIN, _midnight(instrument.trusted_from))
    hi = _midnight(window.last) + _MARGIN
    if hi <= lo:
        return store.read_range(instrument.symbol, lo, lo), []
    bars = store.read_range(instrument.symbol, lo, hi)
    dates = [trading_date(calendar, t.to_pydatetime()) for t in bars["ts"]]
    keep = np.array([d in window for d in dates], dtype=bool)
    keep &= (bars["ts"] >= _midnight(instrument.trusted_from)).to_numpy()
    return (bars[keep].reset_index(drop=True),
            [d for d, k in zip(dates, keep, strict=True) if k])


def _roll_gaps(bars: pd.DataFrame, state_dir: Path, track: str, symbol: str
               ) -> tuple[np.ndarray, np.ndarray]:
    contracts = bars["contract"].to_numpy()
    rolled = np.zeros(len(bars), dtype=bool)
    rolled[1:] = contracts[1:] != contracts[:-1]
    gaps = np.zeros(len(bars))
    if not rolled.any():
        return gaps, rolled
    path = roll_path(state_dir, track, symbol)
    # A record is this roll's only when its ts, old and new contract all match
    # (decision 2026-10-12 37); one with the right ts and other contracts is none.
    records = {(r.ts, r.old, r.new): r for r in read_rolls(path)}
    for k in np.flatnonzero(rolled):
        ts = bars["ts"].iloc[k]
        old, new = contracts[k - 1], contracts[k]
        roll = records.get((ts, old, new))
        if roll is None:
            raise MissingRollError(
                f"{symbol}: the contract changes from {old} to {new} at bar ts "
                f"{ts.isoformat()} and {path} has no record of that roll; run "
                f"`discotrade bars fetch` to record it, then evaluate again")
        gaps[k] = roll.gap
    return gaps, rolled


def _empty_rows() -> pd.DataFrame:
    return pd.DataFrame({
        "ts": pd.Series([], dtype="datetime64[ns, UTC]"),
        "contract": pd.Series([], dtype=object),
        "date": pd.Series([], dtype=object),
        **{name: pd.Series([], dtype="float64") for name in ROW_COLUMNS[3:]},
    })


def evaluate(state_dir: Path, track: Track, instrument: Instrument, calendar: Calendar,
             strategy: Strategy, window: DateRange,
             params: Mapping[str, Any] | None = None,
             spread_table: SpreadTable | None = None) -> Evaluation:
    """Walk ``window`` of ``instrument`` with ``strategy`` (``params``: its own
    ``PARAMS`` by default) and return the targets, positions, gross returns and
    costs; ``spread_table`` is the instrument's measured table (DESIGN 5.7), or
    None when it has none."""
    symbol = instrument.symbol
    params = strategy.params if params is None else params
    store = BarStore(Path(state_dir), track.name, track.bar_seconds)
    inside, dates = _window_bars(store, instrument, calendar, window)
    if inside.empty:
        return Evaluation(symbol, _empty_rows(), inside, 0, np.zeros(0),
                          np.zeros(0, dtype=bool))
    cap = track.history_cap_bars
    context = store.last_n(symbol, inside["ts"].iloc[0],
                           max(cap, costs.SIGMA_RETURNS + 2))
    context = context[context["ts"] >= _midnight(instrument.trusted_from)]
    bars = pd.concat([context.iloc[:-1], inside], ignore_index=True)
    first = len(context) - 1
    gaps, rolled = _roll_gaps(bars, Path(state_dir), track.name, symbol)

    prices = {col: bars[col].to_numpy(dtype=np.float64) for col in _PRICES}
    volume = bars["volume"].to_numpy(dtype=np.float64)
    hour, weekday = _local_clock(bars["ts"], calendar)
    roll_at = np.flatnonzero(rolled)
    stamps = list(bars["ts"])
    n = len(bars)

    targets = np.empty(n - first)
    for i, k in enumerate(range(first, n)):
        j0 = max(0, k - cap + 1)
        # The adjustment as of bar k, summed roll by roll in time order as
        # rolls.adjust does: a roll at r adds its gap to every bar before r.
        offset = np.zeros(k + 1 - j0)
        for r in roll_at[(roll_at > j0) & (roll_at <= k)]:
            offset[: r - j0] += gaps[r]
        frame = pd.DataFrame({
            **{col: prices[col][j0:k + 1] + offset for col in _PRICES},
            "volume": volume[j0:k + 1].copy(),
            "hour": hour[j0:k + 1].copy(),
            "weekday": weekday[j0:k + 1].copy(),
        })
        targets[i] = call_position(strategy.position, frame, params, instrument=symbol,
                                   ts=stamps[k],
                                   shorting=instrument.shorting)

    held = np.zeros_like(targets)
    held[1:] = targets[:-1]
    before = np.zeros_like(targets)
    before[1:] = held[:-1]
    o, c = prices["open"][first:], prices["close"][first:]
    prev_close = np.empty_like(o)
    prev_close[0] = o[0]           # unused: h(u0-1) = 0 (decision 24)
    prev_close[1:] = prices["close"][first:-1] + gaps[first + 1:]
    gross = (before * (o - prev_close) + held * (c - o)) / o
    gross[0] = 0.0
    rows = pd.DataFrame({
        "ts": inside["ts"],
        "contract": inside["contract"].to_numpy(),
        "date": dates,
        "p": targets,
        "h": held,
        "gross": gross,
    })
    market = Market(instrument, calendar, spread_table, bars, gaps, rolled)
    orders = [Order(strategy.name, symbol, stamps[k - 1] if k > 0 else None,
                    float(before[i]), float(held[i]))
              for i, k in enumerate(range(first, n))]
    fills = SimExecutor().execute(orders, {symbol: market})
    rows["trade"] = [f.order.trade for f in fills]
    for name in ("fee", "spread", "slippage", "roll", "cost"):
        rows[name] = [getattr(f, name) for f in fills]
    rows["net_1x"] = [costs.net(g, f.cost, 1) for g, f in zip(gross, fills, strict=True)]
    rows["net_2x"] = [costs.net(g, f.cost, 2) for g, f in zip(gross, fills, strict=True)]
    return Evaluation(symbol, rows[list(ROW_COLUMNS)], bars, first, gaps, rolled)


def daily(evaluations: Sequence[Evaluation]) -> pd.DataFrame:
    """The daily net series of a subject whose instruments gave ``evaluations``,
    one each, an instrument with no window bar included (DESIGN 8; decision
    23): see :func:`discotrade.metrics.daily_series`."""
    return metrics.daily_series([metrics.leg(e) for e in evaluations])
