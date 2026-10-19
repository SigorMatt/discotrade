"""``stats.trading_dates`` reusing the dates it has already decided (O-26 items 2
and 3 of meta/decisions/2026-10-18-owner.md; decisions 157 (a), (b) and 158 of
meta/decisions/decisions-2026-10-18-m20.md; DESIGN 11.1).

Whether a calendar expects a bar on a date is kept per calendar record and bar
size (``stats._OPEN_DAYS``), keyed by the whole record, closures included, so
a changed record is decided again; ``state.clear_caches`` empties it, and it
holds at most ``stats.OPEN_DAYS_CALENDARS`` calendars at a time. The expected
dates are computed here from ``tradingcal.expected_bars``, as the function's
docstring defines them, without calling ``trading_dates``.

The calendars are the fixture records; nothing reads a clock and no random draw
is made.
"""

import dataclasses
from datetime import date, datetime, timedelta

import pytest

from discotrade import state, stats, tradingcal
from discotrade.bars.gaps import day_end
from discotrade.cli import REPO_ROOT
from discotrade.config import Closure, load_calendar

CALENDARS = REPO_ROOT / "tests" / "fixtures" / "config" / "calendars"
FIRST, LAST = date(2019, 6, 1), date(2019, 8, 31)
BAR = 3600


def calendar(name):
    return load_calendar(CALENDARS / f"{name}.toml")


def expected(cals, bar_seconds, first, last):
    out, d = [], first
    while d <= last:
        if any(tradingcal.expected_bars(c, day_end(c, d - timedelta(days=1)), day_end(c, d),
                                        bar_seconds) for c in cals):
            out.append(d)
        d += timedelta(days=1)
    return out


def counting(monkeypatch):
    calls = []
    real = stats.expected_bars

    def counted(*args, **kw):
        calls.append(args)
        return real(*args, **kw)

    monkeypatch.setattr(stats, "expected_bars", counted)
    return calls


@pytest.mark.parametrize("names", [("synth_week",), ("always_open",),
                                   ("always_open", "synth_week")])
def test_the_dates_equal_the_calendars_and_are_reused(monkeypatch, names):
    state.clear_caches()
    cals = [calendar(n) for n in names]
    want = expected(cals, BAR, FIRST, LAST)
    calls = counting(monkeypatch)
    assert stats.trading_dates(cals, BAR, FIRST, LAST) == want
    assert calls
    del calls[:]
    assert stats.trading_dates(cals, BAR, FIRST, LAST) == want
    assert stats.trading_dates(cals, BAR, FIRST + timedelta(days=5), LAST) == \
        [d for d in want if d >= FIRST + timedelta(days=5)]
    assert calls == []                                   # every date decided before
    longer = LAST + timedelta(days=10)
    assert stats.trading_dates(cals, BAR, FIRST, longer) == expected(cals, BAR, FIRST, longer)
    assert calls                                          # only the new dates decided


def test_the_synthetic_week_has_its_closure_and_weekends_off():
    got = stats.trading_dates([calendar("synth_week")], BAR, date(2019, 7, 1),
                              date(2019, 7, 8))
    assert date(2019, 7, 4) not in got and date(2019, 7, 6) not in got
    assert date(2019, 7, 5) in got and date(2019, 7, 8) in got


def test_a_changed_calendar_record_is_decided_again():
    state.clear_caches()
    week = calendar("synth_week")
    day = date(2019, 6, 12)
    assert day in stats.trading_dates([week], BAR, FIRST, LAST)
    shut = dataclasses.replace(week, closures=week.closures + (Closure(
        start=datetime(2019, 6, 11, 17, 0), end=datetime(2019, 6, 12, 18, 0),
        note="a test closure", provenance=None),))
    got = stats.trading_dates([shut], BAR, FIRST, LAST)
    assert day not in got
    assert got == expected([shut], BAR, FIRST, LAST)
    assert day in stats.trading_dates([week], BAR, FIRST, LAST)
    assert stats.trading_dates([week], 1800, FIRST, LAST) == expected([week], 1800, FIRST, LAST)


def test_clear_caches_empties_the_trading_days():
    stats.trading_dates([calendar("synth_week")], BAR, FIRST, LAST)
    assert stats._OPEN_DAYS
    assert "discotrade.stats._OPEN_DAYS" in state.clear_caches()
    assert stats._OPEN_DAYS == {}


def test_the_cache_holds_a_bounded_number_of_calendars():
    state.clear_caches()
    week = calendar("synth_week")
    for k in range(stats.OPEN_DAYS_CALENDARS + 3):
        renamed = dataclasses.replace(week, name=f"synth_week_{k}")
        stats.trading_dates([renamed], BAR, FIRST, FIRST + timedelta(days=3))
        assert 1 <= len(stats._OPEN_DAYS) <= stats.OPEN_DAYS_CALENDARS
