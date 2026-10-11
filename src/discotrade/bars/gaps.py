"""The gap check (DESIGN 5.4, 4.1 windows, 15.2 health event; I-5, I-6).

For each instrument, the missing bars are the calendar's expected bar open
times with no stored bar, from the later of ``trusted_from`` and the first
stored bar to the last stored bar (both included). ``trusted_from`` is read
as midnight UTC of that date. Each newly found missing bar is appended, once,
to ``<state>/bars/<track>/gaps.jsonl`` as one JSON line ``{"symbol", "ts"}``
(``ts`` ISO 8601 UTC, keys sorted), in the track's instrument order and then
in time order; a bar already in the file is not written again, so re-running
the check writes nothing new. Missing bars are never filled in.

For a window (W or T of DESIGN 4.1) the gap fraction is the missing bars over
the expected bars, both counted over the bars whose trading date lies in the
window and that lie within each instrument's checked span above, pooled
across the track's instruments. When the fraction of W or of T is above
``gaps.max_fraction``, generation is skipped and the result carries a
``data_gaps`` alert-level health event (DESIGN 15.2); at or below it, not.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from discotrade.bars.store import BarStore
from discotrade.config import Calendar, DateRange, Instrument, TrackConfig
from discotrade.state import HealthEvent
from discotrade.tradingcal import expected_bars, trading_date

GAPS_FILE = "gaps.jsonl"
DATA_GAPS = "data_gaps"


@dataclass(frozen=True)
class WindowGaps:
    """Missing and expected bars of one window, pooled over the track's instruments."""

    name: str          # "W" or "T"
    first: date
    last: date
    expected: int
    missing: int

    @property
    def fraction(self) -> float:
        return self.missing / self.expected if self.expected else 0.0

    def detail(self) -> dict[str, object]:
        return {"first": self.first.isoformat(), "last": self.last.isoformat(),
                "expected": self.expected, "missing": self.missing,
                "fraction": self.fraction}


@dataclass(frozen=True)
class GapReport:
    track: str
    day: date
    missing: Mapping[str, tuple[datetime, ...]]   # per symbol, in time order
    new: int                                      # lines appended to gaps.jsonl
    windows: tuple[WindowGaps, WindowGaps]        # (W, T)
    max_fraction: float
    skip_generation: bool
    event: HealthEvent | None


def _span(store: BarStore, inst: Instrument, bar_seconds: int,
          cal: Calendar) -> tuple[list[datetime], set[datetime]]:
    """The expected bar times of the instrument's checked span and its stored times."""
    entry = store.index().get(inst.symbol)
    if entry is None:
        return [], set()
    first = datetime.fromisoformat(entry["first_ts"]).astimezone(UTC)
    last = datetime.fromisoformat(entry["last_ts"]).astimezone(UTC)
    trusted = datetime.combine(inst.trusted_from, time(), tzinfo=UTC)
    start = max(first, trusted)
    end = last + timedelta(seconds=bar_seconds)
    if start >= end:
        return [], set()
    stored = store.read_range(inst.symbol, start, end)["ts"]
    have = {t.to_pydatetime() for t in stored}
    return expected_bars(cal, start, last + timedelta(seconds=1), bar_seconds), have


def find_missing(store: BarStore, inst: Instrument, cal: Calendar,
                 bar_seconds: int) -> list[datetime]:
    """The missing bars of one instrument (DESIGN 5.4), in time order."""
    expected, have = _span(store, inst, bar_seconds, cal)
    return [t for t in expected if t not in have]


def _record(path: Path, missing: Mapping[str, tuple[datetime, ...]]) -> int:
    seen: set[tuple[str, str]] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                seen.add((row["symbol"], row["ts"]))
    lines = []
    for symbol, times in missing.items():
        for t in times:
            key = (symbol, t.isoformat())
            if key not in seen:
                seen.add(key)
                lines.append(json.dumps({"symbol": symbol, "ts": key[1]}, sort_keys=True))
    if lines:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write("".join(line + "\n" for line in lines))
    return len(lines)


def check_gaps(state_dir: Path, tc: TrackConfig, calendars: Mapping[str, Calendar],
               day: date, max_fraction: float) -> GapReport:
    """Run the gap check of the track for trading day ``day``.

    Appends newly found missing bars to ``gaps.jsonl`` and returns the report;
    ``calendars`` maps a calendar name to its record.
    """
    track = tc.track
    store = BarStore(Path(state_dir), track.name, track.bar_seconds)
    wins = track.windows(day)
    ranges: tuple[tuple[str, DateRange], ...] = (("W", wins.w), ("T", wins.t))
    counts = {name: [0, 0] for name, _ in ranges}   # expected, missing
    missing: dict[str, tuple[datetime, ...]] = {}
    for inst in tc.instruments:
        cal = calendars[inst.calendar]
        expected, have = _span(store, inst, track.bar_seconds, cal)
        missing[inst.symbol] = tuple(t for t in expected if t not in have)
        for t in expected:
            d = trading_date(cal, t)
            for name, rng in ranges:
                if d in rng:
                    counts[name][0] += 1
                    counts[name][1] += t not in have

    new = _record(store.root / GAPS_FILE, missing)
    w, t = (WindowGaps(name, rng.first, rng.last, *counts[name]) for name, rng in ranges)
    over = [win.name for win in (w, t) if win.fraction > max_fraction]
    event = None
    if over:
        event = HealthEvent(
            date=day, level="alert", kind=DATA_GAPS, subject=track.name,
            detail={"over": over, "max_fraction": max_fraction,
                    "windows": {win.name: win.detail() for win in (w, t)}},
        )
    return GapReport(track=track.name, day=day, missing=missing, new=new, windows=(w, t),
                     max_fraction=max_fraction, skip_generation=bool(over), event=event)
