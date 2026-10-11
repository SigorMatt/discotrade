"""Rolls and the adjusted series (DESIGN 5.6; decision 2026-10-12 16; I-5, I-6, I-12).

A roll happens at stored bar ``u`` of an instrument when ``contract(u)``
differs from ``contract(u-1)``. Rolls are found on the stored bars, so a roll
whose bar is the first bar of a fetch is compared with the last bar stored
before it.

Each roll is recorded once, append-only, as one JSON line (keys sorted) of
``<state>/rolls/<track>/<symbol>.jsonl``: ``ts`` (the roll bar's open, ISO
8601 UTC), ``old`` and ``new`` (the contracts), ``gap``, ``estimated`` and
``measured_at``. The gap is ``close_new(v) - close_old(v)``, where ``v`` is
the latest bar time at which both contracts have a bar (``fetch_contract``)
in the span of the 24 stored bars before ``u`` (from the open of bar
``u-24``, or of the first stored bar when fewer are stored, to the open of
``u``, exclusive); ``measured_at`` is ``v``. DESIGN 5.6 says "within 24
bars" without saying which bars: these are the instrument's stored bars,
the simplest reading that needs no calendar. When no such ``v`` exists the
gap is ``open(u) - close(u-1)`` of the stored series, ``estimated`` is true,
``measured_at`` is null, and a ``roll_gap_estimated`` health notice
(DESIGN 15.2, decision 16) is returned for the caller to print or log.

``update_rolls`` looks only at stored bars from the last recorded roll on, so
a recorded roll is never measured again: re-running a fetch with no new bar
appends nothing (I-6). An append writes the whole file beside the old one
with every earlier line byte-identical, ``fsync``-s it and renames it into
place, as the bar store does (I-5).

The adjusted series as of bar ``t`` is the stored series up to ``t`` with,
for every bar ``s``, the sum of the gaps of the rolls after ``s`` and not
after ``t`` added to its four prices. Its last bar is raw, and volume is
never adjusted.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade.bars.store import BarStore, BarStoreError, write_atomic
from discotrade.config import Instrument
from discotrade.sources.base import BarSource
from discotrade.state import HealthEvent

ROLLS_DIR = "rolls"
ROLL_GAP_ESTIMATED = "roll_gap_estimated"
#: How many stored bars before a roll the gap's common bar may lie in (DESIGN 5.6).
WINDOW_BARS = 24
PRICES = ("open", "high", "low", "close")


@dataclass(frozen=True)
class Roll:
    ts: pd.Timestamp                  # the roll bar's open, UTC
    old: str
    new: str
    gap: float
    estimated: bool
    measured_at: pd.Timestamp | None  # v, or None when estimated

    def to_json(self) -> str:
        return json.dumps({
            "ts": _iso(self.ts), "old": self.old, "new": self.new, "gap": self.gap,
            "estimated": self.estimated,
            "measured_at": None if self.measured_at is None else _iso(self.measured_at),
        }, sort_keys=True)

    @classmethod
    def from_json(cls, line: str) -> Roll:
        row = json.loads(line)
        return cls(ts=_stamp(row["ts"]), old=row["old"], new=row["new"],
                   gap=float(row["gap"]), estimated=bool(row["estimated"]),
                   measured_at=None if row["measured_at"] is None
                   else _stamp(row["measured_at"]))


def _iso(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").isoformat()


def _stamp(value: Any) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise ValueError(f"time {value!r} has no time zone; expected UTC")
    return stamp.tz_convert("UTC")


def roll_path(state_dir: Path, track: str, symbol: str) -> Path:
    if not symbol or "/" in symbol or "\\" in symbol or symbol.startswith("."):
        raise ValueError(f"bad symbol {symbol!r}")
    return Path(state_dir) / ROLLS_DIR / track / f"{symbol}.jsonl"


def read_rolls(path: Path) -> list[Roll]:
    """The recorded rolls of one instrument, in file (time) order; none when no file."""
    if not path.exists():
        return []
    return [Roll.from_json(line)
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def detect_rolls(contracts: Sequence[str]) -> list[int]:
    """The positions ``u`` at which ``contracts[u]`` differs from ``contracts[u-1]``."""
    return [u for u in range(1, len(contracts)) if contracts[u] != contracts[u - 1]]


def _measure(source: BarSource, instrument: Instrument, old: str, new: str,
             start: pd.Timestamp, end: pd.Timestamp) -> tuple[float, pd.Timestamp] | None:
    """``(close_new(v) - close_old(v), v)`` for the latest common bar ``v`` in
    [start, end), or None when there is none."""
    frames = []
    for contract in (old, new):
        bars = source.fetch_contract(instrument, contract, start.to_pydatetime(),
                                     end.to_pydatetime())
        if bars.empty:
            return None
        ts = bars["ts"].dt.tz_convert("UTC")
        keep = ((ts >= start) & (ts < end)).to_numpy()
        frames.append(pd.DataFrame({"ts": ts[keep].to_numpy(),
                                    "close": bars["close"].to_numpy()[keep]}))
    common = frames[0].merge(frames[1], on="ts", suffixes=("_old", "_new"))
    if common.empty:
        return None
    last = common.sort_values("ts", kind="mergesort").iloc[-1]
    return float(last["close_new"] - last["close_old"]), _stamp(last["ts"])


def update_rolls(state_dir: Path, track: str, bar_seconds: int, instrument: Instrument,
                 source: BarSource, day: date) -> tuple[tuple[Roll, ...], tuple[HealthEvent, ...]]:
    """Record the rolls of ``instrument`` found in its stored bars since the
    last recorded roll; return the new rolls and a ``roll_gap_estimated``
    notice, dated ``day``, per estimated gap."""
    symbol = instrument.symbol
    store = BarStore(Path(state_dir), track, bar_seconds)
    entry = store.index().get(symbol)
    if entry is None:
        return (), ()
    path = roll_path(state_dir, track, symbol)
    recorded = read_rolls(path)
    first = _stamp(entry["first_ts"]) if not recorded else recorded[-1].ts
    last = _stamp(entry["last_ts"])
    bars = store.read_range(symbol, first, last + pd.Timedelta(seconds=bar_seconds))
    contracts = bars["contract"].tolist()
    rolls: list[Roll] = []
    events: list[HealthEvent] = []
    for u in detect_rolls(contracts):
        ts = bars["ts"].iloc[u]
        old, new = contracts[u - 1], contracts[u]
        before = store.last_n(symbol, bars["ts"].iloc[u - 1], WINDOW_BARS)
        measured = _measure(source, instrument, old, new, before["ts"].iloc[0], ts)
        if measured is None:
            gap = float(bars["open"].iloc[u] - bars["close"].iloc[u - 1])
            roll = Roll(ts=ts, old=old, new=new, gap=gap, estimated=True, measured_at=None)
            events.append(HealthEvent(
                date=day, level="notice", kind=ROLL_GAP_ESTIMATED, subject=symbol,
                detail={"ts": _iso(ts), "old": old, "new": new, "gap": gap},
            ))
        else:
            roll = Roll(ts=ts, old=old, new=new, gap=measured[0], estimated=False,
                        measured_at=measured[1])
        rolls.append(roll)
    if rolls:
        old_bytes = path.read_bytes() if path.exists() else b""
        data = old_bytes + "".join(r.to_json() + "\n" for r in rolls).encode("utf-8")
        write_atomic(path, lambda p: p.write_bytes(data))
    return tuple(rolls), tuple(events)


def adjust(bars: pd.DataFrame, rolls: Sequence[Roll], t: datetime | pd.Timestamp) -> pd.DataFrame:
    """The adjusted series as of bar ``t`` of the raw ``bars`` (sorted by ``ts``)."""
    t = _stamp(t)
    out = bars[bars["ts"] <= t].reset_index(drop=True).copy()
    ts = out["ts"]
    offset = np.zeros(len(out))
    for roll in rolls:
        if roll.ts <= t:
            offset[(ts < roll.ts).to_numpy()] += roll.gap
    for col in PRICES:
        out[col] = out[col].to_numpy() + offset
    return out


def adjusted_as_of(state_dir: Path, track: str, bar_seconds: int, symbol: str,
                   t: datetime | pd.Timestamp,
                   start: datetime | pd.Timestamp | None = None) -> pd.DataFrame:
    """The adjusted series as of bar ``t`` of the stored bars of ``symbol`` from
    ``start`` (default: the first stored bar)."""
    store = BarStore(Path(state_dir), track, bar_seconds)
    entry = store.index().get(symbol)
    if entry is None:
        raise BarStoreError(f"{symbol}: no stored bar")
    lo = _stamp(entry["first_ts"]) if start is None else _stamp(start)
    bars = store.read_range(symbol, lo, _stamp(t) + pd.Timedelta(nanoseconds=1))
    return adjust(bars, read_rolls(roll_path(state_dir, track, symbol)), t)
