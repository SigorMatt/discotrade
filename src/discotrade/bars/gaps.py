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
earlier line byte-identical, ``fsync``-ed and renamed into place. Inside a
staged day (``bars.store.staged``, decision 2026-10-19-m22 181) the file is read
from and written to the staging directory, as the bar store's files are. Missing
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

``find_missing`` takes an instrument's span month by month, the UTC months of
the store's files, and keeps the missing bars of each month before the one
holding the last stored bar of the span in ``_MONTH_MISSING`` for the process
(decision 2026-10-18-m20 157 (a), O-26): keyed by the month file's path and
index entry (row count and content hash; none for a month with no file), the
calendar record, the bar size and the month's lower bound, for one store at a
time. Every month file of the span is still read through the store first, as
before, so a revised file is refused (decision 2026-10-14 80 (b)). A month's
expected bars are those of ``expected_bars`` over the span that lie in it, so
the months' lists, in order, are the span's.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from discotrade.bars.store import BarStore, month_frames, read_place, write_atomic, write_place
from discotrade.config import Calendar, DateRange, Instrument, TrackConfig
from discotrade.state import HealthEvent, register_cache
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


#: The missing bars of each complete month of a span, keyed by (month file
#: path, index rows, index hash, calendar record, bar size, lower bound); the
#: rows and hash are None for a month the index does not list.
_MONTH_MISSING: dict[tuple[object, ...], list[datetime]] = {}
_MONTH_MISSING_ROOT: list[str] = []


def _clear_month_missing() -> None:
    _MONTH_MISSING.clear()
    _MONTH_MISSING_ROOT.clear()


register_cache("discotrade.bars.gaps._MONTH_MISSING", _clear_month_missing)


def cached_months() -> list[str]:
    """The month file paths ``_MONTH_MISSING`` holds, sorted."""
    return sorted({str(key[0]) for key in _MONTH_MISSING})


def _month_start(year: int, month: int) -> datetime:
    return datetime(year + (month - 1) // 12, (month - 1) % 12 + 1, 1, tzinfo=UTC)


def find_missing(store: BarStore, inst: Instrument, cal: Calendar,
                 bar_seconds: int, until: datetime | None = None) -> list[datetime]:
    """The missing bars of one instrument (DESIGN 5.4), in time order, among
    the stored bars before ``until`` when given: the expected bar times from
    the later of the first stored bar and ``trusted_from`` to the last stored
    bar before ``until`` with no stored bar, taken month by month."""
    entry = store.index_entry(inst.symbol)   # refuses an unlisted file (decision 35)
    if entry is None:
        return []
    first = datetime.fromisoformat(entry["first_ts"]).astimezone(UTC)
    last = datetime.fromisoformat(entry["last_ts"]).astimezone(UTC)
    start = max(first, _trusted(inst))
    end = last + timedelta(seconds=bar_seconds)
    if until is not None:
        end = min(end, until)
    if start >= end:
        return []
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    frames = {month: frame for month, _, frame in
              month_frames(store, inst.symbol, start, end)}         # each read and verified
    stored: dict[str, pd.Series] = {}

    def inside(month: str) -> pd.Series:
        """The stored times of ``month``'s file in [start, end)."""
        if month not in stored:
            ts = frames[month]["ts"]
            stored[month] = ts[(ts >= lo) & (ts < hi)]
        return stored[month]

    final = None
    for month in sorted(frames, reverse=True):
        if not inside(month).empty:
            final = inside(month).iloc[-1].to_pydatetime()
            break
    if final is None:
        return []
    limit = final + timedelta(seconds=1)
    months = entry["months"]
    root = os.path.abspath(store.root)
    if _MONTH_MISSING_ROOT != [root]:
        _clear_month_missing()
        _MONTH_MISSING_ROOT.append(root)
    out: list[datetime] = []
    year, month_number = start.year, start.month
    while True:
        lower_month = _month_start(year, month_number)
        if lower_month >= limit:
            break
        upper_month = _month_start(year, month_number + 1)
        name = f"{year:04d}-{month_number:02d}"
        lower = max(start, lower_month)
        complete = upper_month <= final
        listed = months.get(name)
        key = (os.path.abspath(store.month_path(inst.symbol, name)),
               None if listed is None else int(listed["rows"]),
               None if listed is None else str(listed["hash"]), cal, bar_seconds, lower)
        missing = _MONTH_MISSING.get(key) if complete else None
        if missing is None:
            have = set() if name not in frames else {t.to_pydatetime() for t in inside(name)}
            missing = [t for t in expected_bars(cal, lower, upper_month if complete else limit,
                                                bar_seconds) if t not in have]
            if complete:
                _MONTH_MISSING[key] = missing
        out.extend(missing)
        year, month_number = (year + 1, 1) if month_number == 12 else (year, month_number + 1)
    return out


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
    """Append the newly missing bars to ``gaps.jsonl`` at ``path``, read from and
    written to its staged place inside a staged day (decision 2026-10-19-m22 181)."""
    seen: set[tuple[str, str]] = set()
    held = read_place(path)
    old = held.read_bytes() if held.exists() else b""
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
        write_atomic(write_place(path), lambda p: p.write_bytes(data))
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
