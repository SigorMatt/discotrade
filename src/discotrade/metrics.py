"""Metrics (DESIGN 8; decisions 2026-10-12 23, 25, 30; R-7; I-4).

A subject runs on ``N`` instruments; each gives a :class:`Leg`, its per-bar
rows (decision 25's columns) with the roll flags of those bars. Its daily
series (decision 23) is built over the sorted union of the trading dates of
its legs' rows: on each day, the sum over the legs of that leg's summed
``net_1x`` (and ``net_2x``) over its rows of that day, divided by ``N``, a leg
with no row that day contributing 0. ``N`` counts every leg, one with no row
included.

From the daily series ``d`` (at 1x unless stated; returns summed, not
compounded, R-7):

- ``total_return``: the sum of ``d``; ``total_return_2x`` the same at 2x.
- ``sharpe``: ``mean(d) / std(d, ddof=1) * sqrt(252)``; not a number with
  fewer than 2 days or a deviation of 0; ``sharpe_2x`` the same at 2x. By
  decision 30 the deviation is 0 when every value of ``d`` equals the first,
  or when ``std(d, ddof=1)`` is not above ``1e-12`` times the largest
  absolute value in ``d`` (a floating-point rounding residue).
- ``max_drawdown``: the largest fall of the running sum of ``d`` from a
  running peak, the start (0) counting as a peak; 0 with no fall.
- ``fragile``: ``total_return`` positive and ``total_return_2x`` negative.

From the per-bar rows (decision 25):

- ``trades``: the count of rows with ``trade > TRADE_FLOOR``; a roll adds no
  row, so roll trades are not counted.
- ``avg_holding_bars``: the mean length in rows of the maximal runs of
  non-zero ``h`` of one sign, run per leg; not a number with no run.
- ``breakeven_cost``: the sum of ``gross`` over the sum of ``trade`` plus
  ``2 * |h(u-1)|`` at each roll, times 10000 (basis points); not a number
  without turnover. ``h(u-1)`` at a leg's first row is 0.

No statistic is computed from window-by-window scores: :func:`compute` reads
only the daily series and the per-bar rows. ``breakeven_cost`` is the one
figure that reads ``gross``, and it is returned only inside :class:`Metrics`,
beside the net figures at 1x and 2x (I-4). A Sharpe that is not a number is
never positive, never negative and never above or below anything in
:func:`positive`, :func:`negative` and :func:`above`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "Leg", "Metrics", "leg", "daily_series", "compute", "total_return", "sharpe",
    "max_drawdown", "trades", "avg_holding_bars", "fragile", "positive", "negative",
    "above", "TRADE_FLOOR", "PERIODS_PER_YEAR",
]

#: A row is a trade when its ``trade`` exceeds this (DESIGN 8).
TRADE_FLOOR = 1e-9
#: Trading days per year, for the annualised Sharpe (R-7).
PERIODS_PER_YEAR = 252
_BPS = 10000.0
#: The deviation of a daily series is 0 when ``std(d, ddof=1)`` is not above
#: this times the largest absolute value in ``d`` (decision 30).
_DEVIATION_TOLERANCE = 1e-12


@dataclass(frozen=True)
class Leg:
    """One instrument's per-bar rows and the roll flag of each row's bar."""

    rows: pd.DataFrame
    rolled: np.ndarray


def leg(evaluation: Any) -> Leg:
    """The leg of a :class:`discotrade.backtest.Evaluation`: its rows and the
    roll flags of its window bars."""
    return Leg(evaluation.rows, np.asarray(evaluation.rolled[evaluation.first:], dtype=bool))


@dataclass(frozen=True)
class Metrics:
    days: int
    total_return: float
    total_return_2x: float
    sharpe: float
    sharpe_2x: float
    max_drawdown: float
    trades: int
    avg_holding_bars: float
    breakeven_cost: float
    fragile: bool


def daily_series(legs: Sequence[Leg]) -> pd.DataFrame:
    """The subject's daily net series at 1x and 2x (decision 23): columns
    ``date``, ``net_1x``, ``net_2x``, one row per day, sorted by date."""
    if not legs:
        raise ValueError("a subject has at least one instrument")
    per_leg = [g.rows.groupby("date", sort=False)[["net_1x", "net_2x"]].sum()
               for g in legs if len(g.rows)]
    days = sorted({d for frame in per_leg for d in frame.index})
    total = pd.DataFrame(0.0, index=pd.Index(days, dtype=object),
                         columns=["net_1x", "net_2x"])
    for frame in per_leg:
        total = total.add(frame.reindex(total.index, fill_value=0.0))
    total = total / len(legs)
    return pd.DataFrame({"date": days,
                         "net_1x": total["net_1x"].to_numpy(dtype=np.float64),
                         "net_2x": total["net_2x"].to_numpy(dtype=np.float64)})


def total_return(d: pd.Series) -> float:
    return float(np.sum(np.asarray(d, dtype=np.float64)))


def sharpe(d: pd.Series) -> float:
    x = np.asarray(d, dtype=np.float64)
    if len(x) < 2:
        return math.nan
    sd = float(np.std(x, ddof=1))
    if bool(np.all(x == x[0])) or not sd > _DEVIATION_TOLERANCE * float(np.max(np.abs(x))):
        return math.nan
    return float(np.mean(x)) / sd * math.sqrt(PERIODS_PER_YEAR)


def max_drawdown(d: pd.Series) -> float:
    x = np.asarray(d, dtype=np.float64)
    if len(x) == 0:
        return 0.0
    running = np.concatenate([[0.0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(running) - running))


def positive(x: float) -> bool:
    """``x > 0``; never for a value that is not a number."""
    return bool(not math.isnan(x) and x > 0)


def negative(x: float) -> bool:
    """``x < 0``; never for a value that is not a number."""
    return bool(not math.isnan(x) and x < 0)


def above(x: float, y: float) -> bool:
    """``x > y``; never when either is not a number."""
    return bool(not math.isnan(x) and not math.isnan(y) and x > y)


def fragile(total_1x: float, total_2x: float) -> bool:
    return positive(total_1x) and negative(total_2x)


def _previous(h: np.ndarray) -> np.ndarray:
    before = np.zeros_like(h)
    before[1:] = h[:-1]
    return before


def trades(legs: Sequence[Leg]) -> int:
    return int(sum(int(np.count_nonzero(g.rows["trade"].to_numpy(dtype=np.float64)
                                        > TRADE_FLOOR)) for g in legs))


def avg_holding_bars(legs: Sequence[Leg]) -> float:
    lengths: list[int] = []
    for g in legs:
        sign = np.sign(g.rows["h"].to_numpy(dtype=np.float64))
        run = 0
        for k, s in enumerate(sign):
            if s != 0 and run and s == sign[k - 1]:
                run += 1
                continue
            if run:
                lengths.append(run)
            run = 1 if s != 0 else 0
        if run:
            lengths.append(run)
    return float(np.mean(lengths)) if lengths else math.nan


def _breakeven_cost(legs: Sequence[Leg]) -> float:
    gross = 0.0
    turnover = 0.0
    for g in legs:
        h = g.rows["h"].to_numpy(dtype=np.float64)
        gross += float(np.sum(g.rows["gross"].to_numpy(dtype=np.float64)))
        turnover += float(np.sum(g.rows["trade"].to_numpy(dtype=np.float64)))
        turnover += float(np.sum(2.0 * np.abs(_previous(h))[np.asarray(g.rolled, bool)]))
    if not turnover > 0:
        return math.nan
    return gross / turnover * _BPS


def compute(legs: Sequence[Leg]) -> Metrics:
    """The metrics of a subject whose instruments gave ``legs``."""
    d = daily_series(legs)
    total_1x = total_return(d["net_1x"])
    total_2x = total_return(d["net_2x"])
    return Metrics(
        days=len(d),
        total_return=total_1x,
        total_return_2x=total_2x,
        sharpe=sharpe(d["net_1x"]),
        sharpe_2x=sharpe(d["net_2x"]),
        max_drawdown=max_drawdown(d["net_1x"]),
        trades=trades(legs),
        avg_holding_bars=avg_holding_bars(legs),
        breakeven_cost=_breakeven_cost(legs),
        fragile=fragile(total_1x, total_2x),
    )
