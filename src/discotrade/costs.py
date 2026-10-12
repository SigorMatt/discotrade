"""The cost model (DESIGN 7.3, 5.7; decisions 2026-10-12 24, 25, 26; R-3, R-5; I-4).

Per unit traded at bar ``u``, in return units (fractions of notional):

    fee(u)         = fee_per_side / (multiplier * Or(u))      or fee_bps / 10000
    half_spread(u) = max(spread_ticks(u) / 2, 0.5) * tick_size / Or(u)
    slip(u)        = slippage_coef * sigma(u)
    c(u)           = fee(u) + half_spread(u) + slip(u)

and per bar

    trade(u)     = | h(u) - h(u-1) |
    roll_cost(u) = 2 * | h(u-1) | * c(u)    when a roll happens at u, else 0 (R-3)
    cost(u)      = trade(u) * c(u) + roll_cost(u)
    net(u, m)    = gross(u) - m * cost(u)   m = 1 and m = 2

``spread_ticks(u)`` is DESIGN 5.7's (``discotrade.spreads.spread_ticks``).
``sigma(u)`` is the sample standard deviation (ddof 1) of the last
``SIGMA_RETURNS`` returns ``r(s) = (Ca(s) - Ca(s-1)) / Cr(s-1)`` with ``s`` up to
``u-1``, the difference taken on closes adjusted as of ``s`` (so the previous
close carries the gap of a roll at ``s``) and divided by the raw previous
close; 0 with fewer than 2 such returns. ``u-1`` is always the previous stored
bar, and the returns use stored bars before the window too (decision 24).

The model's version is ``VERSION``; its config hash (decision 26) is the
sha256, in hex, of the canonical JSON (keys sorted, no whitespace) of a map
from each instrument symbol to its ``[cost]`` values without the companions,
its ``tick_size``, its ``multiplier`` when present, and its spread table's 24
values or null.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from discotrade.config import COST_SOURCED, Instrument, SpreadTable

#: The cost model's version, changed whenever a formula of DESIGN 7.3 changes.
VERSION = "c1"
#: How many returns ``sigma`` looks back over (DESIGN 7.3, R-5).
SIGMA_RETURNS = 24
#: The spread floor: half a tick per side (DESIGN 7.3).
HALF_TICK = 0.5
BPS = 10000.0


def fee(instrument: Instrument, raw_open: float) -> float:
    """The fee per unit traded at a bar whose raw open is ``raw_open``."""
    c = instrument.cost
    if c.fee_bps is not None:
        return c.fee_bps / BPS
    if c.fee_per_side is None or instrument.multiplier is None:
        raise ValueError(f"{instrument.symbol}: neither fee_bps nor fee_per_side with a "
                         "multiplier")
    return c.fee_per_side / (instrument.multiplier * raw_open)


def half_spread(instrument: Instrument, ticks: float, raw_open: float) -> float:
    """Half the spread of ``ticks`` ticks, floored at half a tick, per unit traded."""
    return max(ticks / 2.0, HALF_TICK) * instrument.tick_size / raw_open


def returns(close: np.ndarray, gaps: np.ndarray) -> np.ndarray:
    """``r(s)`` for each stored bar ``s``; ``r(0)`` is NaN (its previous bar is not given).

    ``gaps[s]`` is the gap of a roll at ``s`` (0 where there is none).
    """
    close = np.asarray(close, dtype=np.float64)
    gaps = np.asarray(gaps, dtype=np.float64)
    r = np.full(len(close), np.nan)
    if len(close) > 1:
        r[1:] = (close[1:] - (close[:-1] + gaps[1:])) / close[:-1]
    return r


def sigma(close: np.ndarray, gaps: np.ndarray) -> np.ndarray:
    """``sigma(u)`` for each stored bar ``u`` of ``close`` (with ``gaps`` as in ``returns``)."""
    r = returns(close, gaps)
    out = np.zeros(len(r))
    for u in range(3, len(r)):
        window = r[max(1, u - SIGMA_RETURNS):u]
        out[u] = float(np.std(window, ddof=1))
    return out


def slip(instrument: Instrument, sig: float) -> float:
    """The slippage per unit traded: ``slippage_coef * sigma``."""
    return instrument.cost.slippage_coef * sig


def unit_cost(fee_: float, half_spread_: float, slip_: float) -> float:
    """``c(u)``: the cost per unit traded."""
    return fee_ + half_spread_ + slip_


def roll_cost(previous: float, unit: float, rolled: bool) -> float:
    """Two extra trades of the carried position at a roll, at the full cost (R-3)."""
    return 2.0 * abs(previous) * unit if rolled else 0.0


def cost(trade: float, unit: float, roll: float) -> float:
    return trade * unit + roll


def net(gross: float, cost_: float, m: float) -> float:
    return gross - m * cost_


def cost_tables(instruments: Iterable[Instrument],
                tables: Mapping[str, SpreadTable | None]) -> dict[str, dict[str, Any]]:
    """The values the config hash covers, per instrument symbol (decision 26)."""
    out: dict[str, dict[str, Any]] = {}
    for inst in instruments:
        entry: dict[str, Any] = {
            "cost": {k: getattr(inst.cost, k) for k in COST_SOURCED
                     if getattr(inst.cost, k) is not None},
            "tick_size": inst.tick_size,
        }
        if inst.multiplier is not None:
            entry["multiplier"] = inst.multiplier
        table = tables.get(inst.symbol)
        entry["spread_table"] = None if table is None else list(table.ticks)
        out[inst.symbol] = entry
    return out


def config_hash(instruments: Iterable[Instrument],
                tables: Mapping[str, SpreadTable | None]) -> str:
    """The sha256 of the cost tables and spread tables in force (decision 26)."""
    text = json.dumps(cost_tables(instruments, tables), sort_keys=True,
                      separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
