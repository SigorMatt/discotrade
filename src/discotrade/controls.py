"""The controls (DESIGN 10.1, 7, 8; decisions 2026-10-12 23, 25, 49, 54, 64; I-1, I-5,
I-6, I-12).

Controls are harness code, not strategy functions: each supplies its target
``p(t)`` at every bar, and the targets go through the same evaluation loop,
executor and cost model as a strategy's (:func:`discotrade.backtest.score`).

- **Buy and hold**, ``bh:<symbol>`` (kind ``control_bh``), one per instrument
  of the track, on that instrument only: the target 1 at every bar
  (``bh_targets``).
- **Random**, ``rc:0`` to ``rc:<pool - 1>`` (kind ``control_random``) with
  ``pool = controls.random_pool``, each on every instrument of the track.

**Draws** (``Draw``). A draw is made on the first day the controls are
journaled and on the first trading day of the track in each later calendar
month (``is_draw_day``); its seed is the integer ``YYYYMM`` of that day's month
(``seed_of``). ``make_draw`` takes, per slot in slot order, ``H`` and ``q`` from
``numpy.random.default_rng(seed)``: with measured pairs (``pairs`` given and
not empty), one ``rng.integers(len(pairs))`` call per slot chooses a pair; else
one ``rng.uniform(ln lo, ln hi)`` call per slot gives ``H = exp(...)`` with
``lo`` and ``hi`` the smallest and largest bound of the track's horizons, and
``q = 1 / H``. The pairs are those of the approaches live at the start of the
draw's day with at least ``controls.match_window_days`` paper rows before it,
when there are at least ``controls.match_min_live`` such approaches
(``measured_pairs``); a pair is the approach's ``avg_holding_bars`` (DESIGN 8,
from its journal ``position``, ``metrics.avg_holding_bars``) and its trades per
bar (rows with ``trade > 1e-9`` over rows) over its last
``match_window_days`` paper days, in approach-id order, one whose ``H`` is not
a number left out. When every pair is left out, the draw falls back to the
horizons (the design is silent; this is the simplest reading).

**The pool file** ``controls/<track>/pools.jsonl``: one line per draw, the JSON
of ``Draw.row`` (keys sorted, no whitespace, ``ledger.line``): ``month``
(``YYYY-MM``), ``day``, ``seed``, ``H`` and ``q`` (per slot, in slot order) and
``pairs`` (the measured pairs used, each with its approach ``id``; empty for a
draw from the horizons). ``append_draw`` writes the whole file beside the old
one (every earlier line byte-identical) and renames it, as decision 4 appends
``gaps.jsonl``; a draw already recorded is never appended again, and a torn
last line is refused. With ``into`` (the day's staging directory) the file is
read from there when staged, and written there only.

**The state machine** (``random_targets``). Each per-bar random number is the
first 8 bytes of the sha256 of ``<seed>|<slot>|<instrument>|<bar ts in
ns>|<purpose>``, read big-endian, over ``2**64`` (``uniform``), the purposes
being ``enter``, ``side`` and ``exit``. On each instrument the draw in force at
a bar is the latest draw whose day is on or before the bar's trading date; at
the first bar of a draw the machine starts flat. At each bar, flat, it enters
when ``enter < q``, long when ``side < 0.5`` or when the instrument does not
allow shorting, short otherwise; in a position it leaves when ``exit < 1 / H``.
The target ``p(t)`` is the state after the bar (1, -1 or 0). The position
carries across a redraw: the first target of a new draw trades against the
old position.

No clock is read (I-12).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade import ledger, metrics
from discotrade.bars.store import write_atomic
from discotrade.state import StateError

CONTROLS_DIR = "controls"
POOLS = "pools.jsonl"
KIND_BH, KIND_RANDOM = "control_bh", "control_random"
KINDS = (KIND_BH, KIND_RANDOM)
BH_PREFIX, RC_PREFIX = "bh:", "rc:"
ENTER, SIDE, EXIT = "enter", "side", "exit"
_SCALE = float(2 ** 64)


class ControlError(StateError):
    """A pool file or a draw that cannot be read or used as asked."""


# --- subjects ----------------------------------------------------------------------------

def bh_subject(symbol: str) -> str:
    return f"{BH_PREFIX}{symbol}"


def rc_subject(slot: int) -> str:
    return f"{RC_PREFIX}{slot}"


def kind_of(subject: str) -> str | None:
    """The control kind of ``subject``, or None when it is not a control."""
    if subject.startswith(BH_PREFIX):
        return KIND_BH
    if subject.startswith(RC_PREFIX):
        return KIND_RANDOM
    return None


def slot_of(subject: str) -> int:
    return int(subject[len(RC_PREFIX):])


def subjects(symbols: Sequence[str], pool: int) -> list[str]:
    """Every control subject of a track: ``bh:<symbol>`` and ``rc:0`` to ``rc:<pool-1>``."""
    return [bh_subject(s) for s in symbols] + [rc_subject(k) for k in range(pool)]


# --- draws -------------------------------------------------------------------------------

def seed_of(day: date) -> int:
    """The seed of a draw made on ``day``: the integer ``YYYYMM`` of its month."""
    return day.year * 100 + day.month


def is_draw_day(day: date, first: date, trading_days_before_in_month: Sequence[date]) -> bool:
    """Whether a draw is made on ``day``: the first day the controls are
    journaled (``first``), or a later day with no trading day of the track
    before it in its calendar month."""
    if day == first:
        return True
    return day > first and not [d for d in trading_days_before_in_month
                                if d.year == day.year and d.month == day.month and d < day]


@dataclass(frozen=True)
class Pair:
    """A live approach's measured pair: mean holding bars and trades per bar."""

    id: str
    H: float
    q: float

    def row(self) -> dict[str, Any]:
        return {"id": self.id, "H": self.H, "q": self.q}


@dataclass(frozen=True)
class Draw:
    day: date
    seed: int
    H: tuple[float, ...]
    q: tuple[float, ...]
    pairs: tuple[Pair, ...]

    @property
    def month(self) -> str:
        return f"{self.day.year:04d}-{self.day.month:02d}"

    def row(self) -> dict[str, Any]:
        return {"month": self.month, "day": self.day.isoformat(), "seed": self.seed,
                "H": list(self.H), "q": list(self.q),
                "pairs": [p.row() for p in self.pairs]}

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Draw:
        try:
            day = date.fromisoformat(str(row["day"]))
            draw = cls(day, int(row["seed"]), tuple(float(x) for x in row["H"]),
                       tuple(float(x) for x in row["q"]),
                       tuple(Pair(str(p["id"]), float(p["H"]), float(p["q"]))
                             for p in row["pairs"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ControlError(f"a pool record {row!r} is not a draw: {exc}") from exc
        if row.get("month") != draw.month or len(draw.H) != len(draw.q):
            raise ControlError(f"a pool record {row!r} is not a draw")
        return draw


def horizon_bounds(horizons: Sequence[tuple[str, tuple[int, int]]]) -> tuple[float, float]:
    """The smallest and the largest bound of the track's horizons."""
    bounds = [b for _, pair in horizons for b in pair]
    return float(min(bounds)), float(max(bounds))


def make_draw(day: date, pool: int, bounds: tuple[float, float],
              pairs: Sequence[Pair] | None) -> Draw:
    """The draw of ``day`` (decision 64): from ``pairs`` when given and not
    empty, else from the horizon ``bounds``."""
    seed = seed_of(day)
    rng = np.random.default_rng(seed)
    hs, qs = [], []
    if pairs:
        for _ in range(pool):
            chosen = pairs[int(rng.integers(len(pairs)))]
            hs.append(float(chosen.H))
            qs.append(float(chosen.q))
        used = tuple(pairs)
    else:
        lo, hi = bounds
        for _ in range(pool):
            h = float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
            hs.append(h)
            qs.append(1.0 / h)
        used = ()
    return Draw(day, seed, tuple(hs), tuple(qs), used)


def measured_pair(aid: str, rows: pd.DataFrame) -> Pair:
    """The pair of approach ``aid`` from its journal ``rows`` over the days
    measured: ``avg_holding_bars`` of its ``position`` per instrument in ``ts``
    order, and the rows with ``trade > 1e-9`` over the rows."""
    legs = [metrics.Leg(pd.DataFrame({"h": leg.sort_values("ts")["position"]
                                      .to_numpy(dtype=np.float64)}), np.zeros(len(leg), bool))
            for _, leg in rows.groupby("instrument", sort=True)]
    h = metrics.avg_holding_bars(legs)
    trades = int(np.count_nonzero(rows["trade"].to_numpy(dtype=np.float64)
                                  > metrics.TRADE_FLOOR))
    return Pair(aid, h, trades / len(rows) if len(rows) else math.nan)


def measured_pairs(rows_by_day: Mapping[str, Mapping[date, pd.DataFrame]], live: Sequence[str],
                   window: int, min_live: int) -> list[Pair] | None:
    """The pairs of a draw, or None when fewer than ``min_live`` of the ``live``
    approaches have at least ``window`` paper days; ``rows_by_day`` maps each
    approach to its journal rows per paper day before the draw's day."""
    qualifying = sorted(aid for aid in live if len(rows_by_day.get(aid, {})) >= window)
    if len(qualifying) < min_live:
        return None
    out = []
    for aid in qualifying:
        days = sorted(rows_by_day[aid])[-window:]
        pair = measured_pair(aid, pd.concat([rows_by_day[aid][d] for d in days],
                                            ignore_index=True))
        if not math.isnan(pair.H):
            out.append(pair)
    return out


# --- the pool file -----------------------------------------------------------------------

def pools_path(root: Path, track: str) -> Path:
    return Path(root) / CONTROLS_DIR / track / POOLS


def _bytes(path: Path) -> bytes:
    data = path.read_bytes() if path.exists() else b""
    if data and not data.endswith(b"\n"):
        raise ControlError(f"{path} does not end with a newline; its last line is torn")
    return data


def _source(state_dir: Path, track: str, into: Path | None) -> Path:
    if into is not None and pools_path(into, track).exists():
        return pools_path(into, track)
    return pools_path(state_dir, track)


def read_draws(state_dir: Path, track: str, into: Path | None = None) -> list[Draw]:
    """The recorded draws, in file order (from ``into`` when staged there)."""
    data = _bytes(_source(state_dir, track, into))
    draws = [Draw.from_row(json.loads(x)) for x in data.decode("utf-8").splitlines()]
    days = [d.day for d in draws]
    if days != sorted(set(days)):
        raise ControlError(f"{pools_path(state_dir, track)} does not hold one draw per day "
                           f"in date order")
    return draws


def append_draw(state_dir: Path, track: str, draw: Draw, into: Path | None = None) -> bool:
    """Append ``draw``'s line unless a draw of its day is recorded; return
    whether it was appended."""
    old = _bytes(_source(state_dir, track, into))
    recorded = [Draw.from_row(json.loads(x)) for x in old.decode("utf-8").splitlines()]
    if any(d.day == draw.day for d in recorded):
        return False
    if recorded and recorded[-1].day > draw.day:
        raise ControlError(f"a draw of {draw.day.isoformat()} cannot follow the recorded "
                           f"draw of {recorded[-1].day.isoformat()}")
    data = old + (ledger.line(draw.row()) + "\n").encode("utf-8")
    target = pools_path(state_dir if into is None else into, track)
    write_atomic(target, lambda p: p.write_bytes(data))
    return True


# --- targets -----------------------------------------------------------------------------

def uniform(seed: int, slot: int, symbol: str, ts: pd.Timestamp, purpose: str) -> float:
    """The per-bar random number of decision 64, in [0, 1)."""
    key = f"{seed}|{slot}|{symbol}|{pd.Timestamp(ts).value}|{purpose}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big") / _SCALE


def in_force(draws: Sequence[Draw], day: date) -> Draw | None:
    """The latest draw made on or before ``day``."""
    found = None
    for d in draws:
        if d.day <= day:
            found = d
    return found


def bh_targets(n: int) -> np.ndarray:
    return np.ones(n, dtype=np.float64)


def random_targets(draws: Sequence[Draw], slot: int, symbol: str, shorting: bool,
                   stamps: Sequence[pd.Timestamp], dates: Sequence[date],
                   start: tuple[float, date] | None = None) -> np.ndarray:
    """The targets of slot ``slot`` on ``symbol`` at the bars ``stamps`` (with
    their trading ``dates``); ``start`` is the state after the previous bar and
    that bar's trading date, or None for a flat start."""
    state, current = 0.0, None
    if start is not None:
        state, current = float(start[0]), in_force(draws, start[1])
    out = np.empty(len(stamps), dtype=np.float64)
    for k, (ts, day) in enumerate(zip(stamps, dates, strict=True)):
        draw = in_force(draws, day)
        if draw is None:
            raise ControlError(f"rc:{slot} on {symbol}: no draw is in force on "
                               f"{day.isoformat()}")
        if current is None or draw.day != current.day:
            state, current = 0.0, draw
        h, q = draw.H[slot], draw.q[slot]
        if state == 0.0:
            if uniform(draw.seed, slot, symbol, ts, ENTER) < q:
                long = uniform(draw.seed, slot, symbol, ts, SIDE) < 0.5 or not shorting
                state = 1.0 if long else -1.0
        elif uniform(draw.seed, slot, symbol, ts, EXIT) < 1.0 / h:
            state = 0.0
        out[k] = state
    return out
