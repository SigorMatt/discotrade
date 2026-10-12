"""The gap check (DESIGN 5.4, 4.1 windows, 15.2 health event; I-5, I-6, I-12;
decisions 2026-10-12 2 to 4).

The check for trading day ``D`` reads only stored bars before the end of
``D``'s trading day (decision 3), so a replay of a past day equals the
original run of that day. The end of ``D`` is ``day_rolls_at`` local on
``D`` (the UTC midnight after ``D`` for an always-open calendar).

For each instrument, the missing bars are the calendar's expected bar open
times with no stored bar, from the later of ``trusted_from`` and the first
stored bar to the last stored bar before the end of ``D`` (both included).
``trusted_from`` is read as midnight UTC of that date. Each newly found
missing bar is appended, once, to ``<state>/bars/<track>/gaps.jsonl`` as one
JSON line ``{"symbol", "ts"}`` (``ts`` ISO 8601 UTC, keys sorted), in the
track's instrument order and then in time order; a bar already in the file is
not written again, so re-running the check writes nothing new. The append is
atomic (decision 4): the whole file is written beside the old one with every
earlier line byte-identical, ``fsync``-ed and renamed into place. Missing
bars are never filled in. An instrument with no index entry has no stored
bar only when its directory holds no month file; otherwise the check refuses
with the reader's error, interrupted append or revised data point (decision
2026-10-12 35).

For a window (W or T of DESIGN 4.1) the gap fraction is the missing bars over
the expected bars, pooled across the track's instruments, where an
instrument's expected bars are its expected bar times whose trading date lies
in the window, from the later of the window's start and ``trusted_from`` to
the end of ``D``, and its missing bars are those with no stored bar
(decision 2): a feed that stopped, or that never started, counts as missing.
When the fraction of W or of T is above ``gaps.max_fraction``, generation is
skipped and the result carries a ``data_gaps`` alert-level health event
(DESIGN 15.2); at or below it, not.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from discotrade.bars.store import BarStore, write_atomic
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


def day_end(cal: Calendar, day: date) -> datetime:
    """The end of trading day ``day`` in UTC: a bar opening before it has a
    trading date not later than ``day`` (``tradingcal.trading_date``)."""
    if cal.always_open:
        return datetime.combine(day + timedelta(days=1), time(), tzinfo=UTC)
    assert cal.tz and cal.day_rolls_at
    local = datetime.combine(day, time.fromisoformat(cal.day_rolls_at),
                             tzinfo=ZoneInfo(cal.tz))
    return local.astimezone(UTC)


def latest_closed_day(cal: Calendar, until: datetime, bar_seconds: int) -> date:
    """The latest trading day with an expected bar whose last expected bar
    closed at or before ``until`` (DESIGN 16.1's ``D``; decision 2026-10-12 3).
    A date with no expected bar is not a trading day."""
    day = trading_date(cal, until)
    for _ in range(366):
        bars = expected_bars(cal, day_end(cal, day - timedelta(days=1)), day_end(cal, day),
                             bar_seconds)
        if bars and bars[-1] + timedelta(seconds=bar_seconds) <= until:
            return day
        day -= timedelta(days=1)
    raise ValueError(f"no trading day closed in the year before {until.isoformat()}")


def _trusted(inst: Instrument) -> datetime:
    return datetime.combine(inst.trusted_from, time(), tzinfo=UTC)


def _span(store: BarStore, inst: Instrument, bar_seconds: int, cal: Calendar,
          until: datetime | None) -> tuple[list[datetime], set[datetime]]:
    """The expected bar times of the instrument's checked span, bounded by
    ``until`` (exclusive) when given, and its stored times."""
    entry = store.index_entry(inst.symbol)   # refuses an unlisted file (decision 35)
    if entry is None:
        return [], set()
    first = datetime.fromisoformat(entry["first_ts"]).astimezone(UTC)
    last = datetime.fromisoformat(entry["last_ts"]).astimezone(UTC)
    start = max(first, _trusted(inst))
    end = last + timedelta(seconds=bar_seconds)
    if until is not None:
        end = min(end, until)
    if start >= end:
        return [], set()
    stored = store.read_range(inst.symbol, start, end)["ts"]
    if stored.empty:
        return [], set()
    have = {t.to_pydatetime() for t in stored}
    last = stored.iloc[-1].to_pydatetime()
    return expected_bars(cal, start, last + timedelta(seconds=1), bar_seconds), have


def find_missing(store: BarStore, inst: Instrument, cal: Calendar,
                 bar_seconds: int, until: datetime | None = None) -> list[datetime]:
    """The missing bars of one instrument (DESIGN 5.4), in time order, among
    the stored bars before ``until`` when given."""
    expected, have = _span(store, inst, bar_seconds, cal, until)
    return [t for t in expected if t not in have]


def _window(store: BarStore, inst: Instrument, cal: Calendar, bar_seconds: int,
            rng: DateRange, day: date) -> tuple[int, int]:
    """Expected and missing bars of one instrument in one window (decision 2)."""
    start = max(day_end(cal, rng.first - timedelta(days=1)), _trusted(inst))
    end = day_end(cal, min(rng.last, day))
    if start >= end:
        return 0, 0
    expected = expected_bars(cal, start, end, bar_seconds)
    stored = store.read_range(inst.symbol, start, end)["ts"]
    have = {t.to_pydatetime() for t in stored}
    return len(expected), sum(t not in have for t in expected)


def _record(path: Path, missing: Mapping[str, tuple[datetime, ...]]) -> int:
    seen: set[tuple[str, str]] = set()
    old = path.read_bytes() if path.exists() else b""
    for line in old.decode("utf-8").splitlines():
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
        data = old + "".join(line + "\n" for line in lines).encode("utf-8")
        write_atomic(path, lambda p: p.write_bytes(data))
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
        missing[inst.symbol] = tuple(
            find_missing(store, inst, cal, track.bar_seconds, day_end(cal, day)))
        for name, rng in ranges:
            expected, lacking = _window(store, inst, cal, track.bar_seconds, rng, day)
            counts[name][0] += expected
            counts[name][1] += lacking

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
