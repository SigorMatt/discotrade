"""The replay (DESIGN 16.4; decisions 2026-10-12 19, 51, 55, 72; I-6, I-12).

``replay(state_dir, config_dir, track, first, last)`` runs, for each trading
day ``D`` of the track (decision 51: the union of its instruments' trading
dates) from ``first`` to ``last`` in ascending order, the day function of
``run-day`` (``daily.run_day``) for ``D`` with the injected clock fixed at
``close_instant(D)``: the instant at which the last expected bar of ``D``
among the track's instruments closes. Each day takes and releases the state's
lock as ``run-day`` does; a day that fails stops the replay, the days before
it staying committed. A day already journaled is a re-run and writes nothing
(I-6); a day after a gap in the journal is refused as ``run-day`` refuses it.

No wall clock is read (I-12): every instant comes from the calendars.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from datetime import date, datetime, timedelta
from pathlib import Path

from discotrade.bars.gaps import day_end
from discotrade.clock import FixedClock
from discotrade.config import Calendar, TrackConfig
from discotrade.daily import DayRun, is_trading_day, run_day
from discotrade.tradingcal import expected_bars


def close_instant(tc: TrackConfig, calendars: Mapping[str, Calendar], day: date) -> datetime:
    """The instant at which the last expected bar of ``day`` among the
    track's instruments closes (its open plus the bar length)."""
    bar = tc.track.bar_seconds
    closes = []
    for name in sorted({inst.calendar for inst in tc.instruments}):
        cal = calendars[name]
        bars = expected_bars(cal, day_end(cal, day - timedelta(days=1)), day_end(cal, day), bar)
        if bars:
            closes.append(bars[-1] + timedelta(seconds=bar))
    if not closes:
        raise ValueError(f"{day.isoformat()} is not a trading day of {tc.track.name}")
    return max(closes)


def replay_days(tc: TrackConfig, calendars: Mapping[str, Calendar], first: date,
                last: date) -> Iterator[tuple[date, datetime]]:
    """Each trading day of the track from ``first`` to ``last``, both
    included, in ascending order, with its ``close_instant``."""
    d = first
    while d <= last:
        if is_trading_day(tc, calendars, d):
            yield d, close_instant(tc, calendars, d)
        d += timedelta(days=1)


class DayFailed(RuntimeError):
    """A replayed day failed; ``day`` names it and ``__cause__`` says why."""

    def __init__(self, day: date, instant: datetime, cause: Exception) -> None:
        super().__init__(f"{day.isoformat()} (clock {instant.isoformat()}): {cause}")
        self.day = day
        self.instant = instant


def replay(state_dir: Path, config_dir: Path, track: str, tc: TrackConfig,
           calendars: Mapping[str, Calendar], first: date, last: date,
           on_day: Callable[[DayRun, datetime], None],
           failures: tuple[type[Exception], ...]) -> int:
    """Run every day of ``replay_days``; call ``on_day`` after each success.
    An exception of a type in ``failures`` stops the replay as ``DayFailed``.
    Return the number of days run."""
    count = 0
    for d, instant in replay_days(tc, calendars, first, last):
        try:
            done = run_day(state_dir, config_dir, track, FixedClock(instant), d)
        except failures as exc:
            raise DayFailed(d, instant, exc) from exc
        on_day(done, instant)
        count += 1
    return count
