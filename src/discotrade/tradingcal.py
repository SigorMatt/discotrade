"""The trading calendar (DESIGN 5.3).

Four questions, all pure functions of a calendar record (``config.Calendar``):
whether the market is open at an instant, the trading date of a bar, the
expected bar open times in a range, and whether a bar lies in an instrument's
main session.

A record's times are wall-clock times in its time zone. The open time is the
weekly session (``week_open`` to ``week_close``) less each day's
``daily_break`` and less every closure, each interval being converted to UTC
on its own local date, so a clock change moves the UTC times of the sessions
after it. Every instant passed in must be timezone-aware; every instant
returned is in UTC. An ``always_open`` calendar is open at every instant and
its trading day is the UTC date.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from discotrade.config import WEEKDAYS, Calendar

Interval = tuple[int, int]   # [start, end) in POSIX seconds

#: How far beyond a queried range sessions and cuts are built: a weekly session
#: spans at most seven days, so a session that reaches the range starts within it.
_MARGIN = timedelta(days=8)


def _seconds(instant: datetime) -> float:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError(f"instant {instant!r} must be timezone-aware")
    return instant.timestamp()


def _utc(seconds: int) -> datetime:
    return datetime.fromtimestamp(seconds, UTC)


def _hhmm(text: str) -> time:
    return time.fromisoformat(text)


def _merge(intervals: Iterable[Interval]) -> list[Interval]:
    out: list[Interval] = []
    for a, b in sorted(intervals):
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _subtract(keep: list[Interval], cut: list[Interval]) -> list[Interval]:
    """``keep`` less ``cut``; both merged and sorted."""
    out: list[Interval] = []
    for a, b in keep:
        for c, d in cut:
            if d <= a or c >= b:
                continue
            if c > a:
                out.append((a, c))
            a = max(a, d)
            if a >= b:
                break
        if a < b:
            out.append((a, b))
    return out


def _open(cal: Calendar, lo: int, hi: int) -> list[Interval]:
    """The open intervals of ``cal`` clipped to [lo, hi), in POSIX seconds."""
    if hi <= lo:
        return []
    if cal.always_open:
        return [(lo, hi)]
    assert cal.tz and cal.week_open and cal.week_close and cal.daily_break
    tz = ZoneInfo(cal.tz)

    def local(day: date, hhmm: str) -> int:
        return int(datetime.combine(day, _hhmm(hhmm), tzinfo=tz).timestamp())

    first = datetime.fromtimestamp(lo, tz).date() - _MARGIN
    last = datetime.fromtimestamp(hi, tz).date() + _MARGIN
    open_day, open_at = WEEKDAYS.index(cal.week_open[0]), cal.week_open[1]
    close_day, close_at = WEEKDAYS.index(cal.week_close[0]), cal.week_close[1]
    span = (close_day - open_day) % 7
    if span == 0 and close_at <= open_at:
        span = 7

    sessions: list[Interval] = []
    cuts: list[Interval] = []
    day = first
    while day <= last:
        if day.weekday() == open_day:
            sessions.append((local(day, open_at), local(day + timedelta(days=span), close_at)))
        cuts.append((local(day, cal.daily_break[0]), local(day, cal.daily_break[1])))
        day += timedelta(days=1)
    for c in cal.closures:
        start = int(c.start.replace(tzinfo=tz).timestamp())
        end = int(c.end.replace(tzinfo=tz).timestamp())
        if end > lo and start < hi:
            cuts.append((start, end))

    clipped = []
    for a, b in _subtract(_merge(sessions), _merge(cuts)):
        a, b = max(a, lo), min(b, hi)
        if a < b:
            clipped.append((a, b))
    return clipped


def open_intervals(
    cal: Calendar, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    """The market's open intervals within [start, end), clipped to it, in UTC."""
    lo, hi = math.floor(_seconds(start)), math.ceil(_seconds(end))
    out = [(_utc(a), _utc(b)) for a, b in _open(cal, lo, hi)]
    return [(max(a, start), min(b, end)) for a, b in out if max(a, start) < min(b, end)]


def is_open(cal: Calendar, instant: datetime) -> bool:
    """Whether the market is open at ``instant``."""
    s = _seconds(instant)
    return any(a <= s < b for a, b in _open(cal, math.floor(s), math.floor(s) + 1))


def trading_date(cal: Calendar, ts: datetime) -> date:
    """The trading date of the bar opening at ``ts``.

    A bar belongs to the trading day that ends at the next ``day_rolls_at``
    local: a bar opening at or after that time belongs to the next date.
    """
    _seconds(ts)
    if cal.always_open:
        return ts.astimezone(UTC).date()
    assert cal.tz and cal.day_rolls_at
    local = ts.astimezone(ZoneInfo(cal.tz))
    if local.time() >= _hhmm(cal.day_rolls_at):
        return local.date() + timedelta(days=1)
    return local.date()


def expected_bars(
    cal: Calendar, start: datetime, end: datetime, bar_seconds: int
) -> list[datetime]:
    """Every ``bar_seconds``-aligned UTC instant in [start, end) whose bar overlaps open time."""
    if isinstance(bar_seconds, bool) or not isinstance(bar_seconds, int) or bar_seconds < 1:
        raise ValueError(f"bar_seconds must be a positive integer, not {bar_seconds!r}")
    first = math.ceil(_seconds(start) / bar_seconds) * bar_seconds
    limit = _seconds(end)
    found: set[int] = set()
    for a, b in _open(cal, first, math.ceil(limit) + bar_seconds):
        t = (a // bar_seconds) * bar_seconds
        while t < b:
            if first <= t < limit:
                found.add(t)
            t += bar_seconds
    return [_utc(t) for t in sorted(found)]


def in_main_session(cal: Calendar, main_session: tuple[str, str], ts: datetime) -> bool:
    """Whether the bar opening at ``ts`` lies in the instrument's main session.

    True when, in the calendar's time zone (UTC for an always-open calendar),
    ``ts`` falls on a Monday to Friday, its time of day lies in
    [main_session[0], main_session[1]), and the market is open at ``ts``.
    """
    _seconds(ts)
    local = ts.astimezone(UTC if cal.always_open else ZoneInfo(cal.tz or "UTC"))
    if local.weekday() >= 5:
        return False
    if not _hhmm(main_session[0]) <= local.time() < _hhmm(main_session[1]):
        return False
    return is_open(cal, ts)
