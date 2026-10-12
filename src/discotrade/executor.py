"""The executor (DESIGN 7.4, 7.3; decision 2026-10-12 25; I-15).

An :class:`Order` names the subject, the instrument, the decision bar (the
``ts`` of bar ``u-1``, or None when the fill bar is the first bar given), the
previous position ``h(u-1)`` and the target ``h(u)``. A :class:`Fill` adds the
fill bar ``u`` (the next stored bar after the decision bar), the raw fill
price ``Or(u)`` and the four cost components at 1x in return units
(decision 25): ``fee = trade * fee(u)``, ``spread = trade * half_spread(u)``,
``slippage = trade * slip(u)`` and ``roll = roll_cost(u)``, with the formulas
of ``discotrade.costs``. An order with no trade has zero fee, spread and
slippage and may still carry a roll cost.

:class:`SimExecutor` is the only implementation of :class:`Executor` (I-15):
it sends nothing anywhere; it prices orders against the stored bars it is
given. Orders are market orders; limit orders are not modeled.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from discotrade import costs
from discotrade.config import Calendar, Instrument, SpreadTable
from discotrade.spreads import spread_ticks


class ExecutionError(RuntimeError):
    """An order that the bars given cannot fill."""


@dataclass(frozen=True)
class Order:
    subject: str
    instrument: str
    decision: pd.Timestamp | None   # the decision bar u-1; None: fill at the first bar
    previous: float                 # h(u-1)
    target: float                   # h(u)

    @property
    def trade(self) -> float:
        return abs(self.target - self.previous)


@dataclass(frozen=True)
class Fill:
    order: Order
    bar: pd.Timestamp               # the fill bar u
    price: float                    # the raw open Or(u)
    fee: float
    spread: float
    slippage: float
    roll: float

    @property
    def cost(self) -> float:
        return self.fee + self.spread + self.slippage + self.roll


@dataclass(frozen=True)
class Market:
    """One instrument's stored bars, oldest first, as the executor prices them.

    ``bars`` has at least ``ts``, ``open`` and ``close`` (raw); ``gaps[k]`` is
    the gap of the roll at ``bars.iloc[k]`` (0 where there is none) and
    ``rolled[k]`` says whether a roll happens there.
    """

    instrument: Instrument
    calendar: Calendar
    spread_table: SpreadTable | None
    bars: pd.DataFrame
    gaps: np.ndarray
    rolled: np.ndarray


@runtime_checkable
class Executor(Protocol):
    def execute(self, orders: list[Order], bars: Mapping[str, Market]) -> list[Fill]: ...


class _Priced:
    """Per-bar values of one market, computed once per ``execute`` call."""

    def __init__(self, market: Market) -> None:
        self.market = market
        self.ts = pd.DatetimeIndex(market.bars["ts"])
        self.open = market.bars["open"].to_numpy(dtype=np.float64)
        self.sigma = costs.sigma(market.bars["close"].to_numpy(dtype=np.float64),
                                 market.gaps)

    def fill_bar(self, order: Order) -> int:
        if not len(self.ts):
            raise ExecutionError(f"{order.instrument}: no stored bar to fill on")
        if order.decision is None:
            return 0
        at = self.ts.get_indexer([pd.Timestamp(order.decision)])[0]
        if at < 0:
            raise ExecutionError(f"{order.instrument}: no stored bar at the decision bar "
                                 f"{pd.Timestamp(order.decision).isoformat()}")
        if at + 1 >= len(self.ts):
            raise ExecutionError(f"{order.instrument}: no bar after the decision bar "
                                 f"{pd.Timestamp(order.decision).isoformat()} to fill on")
        return int(at + 1)


class SimExecutor:
    """The simulator: DESIGN 7.1 to 7.3, and the only executor (I-15)."""

    def execute(self, orders: Sequence[Order], bars: Mapping[str, Market]) -> list[Fill]:
        priced: dict[str, _Priced] = {}
        fills = []
        for order in orders:
            if order.instrument not in bars:
                raise ExecutionError(f"{order.instrument}: no bars given for this instrument")
            if order.instrument not in priced:
                priced[order.instrument] = _Priced(bars[order.instrument])
            p = priced[order.instrument]
            m = p.market
            inst = m.instrument
            u = p.fill_bar(order)
            o = float(p.open[u])
            ticks = spread_ticks(inst, m.calendar, m.spread_table, p.ts[u].to_pydatetime())
            fee = costs.fee(inst, o)
            half = costs.half_spread(inst, ticks, o)
            slip = costs.slip(inst, float(p.sigma[u]))
            unit = costs.unit_cost(fee, half, slip)
            trade = order.trade
            fills.append(Fill(
                order=order, bar=p.ts[u], price=o,
                fee=trade * fee, spread=trade * half, slippage=trade * slip,
                roll=costs.roll_cost(order.previous, unit, bool(m.rolled[u])),
            ))
        return fills
