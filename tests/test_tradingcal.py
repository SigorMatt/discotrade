"""The trading calendar (DESIGN 5.3; calendar records DESIGN 4.3, I-10)."""

import tomllib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from discotrade.cli import REPO_ROOT
from discotrade.config import ConfigError, load_calendar
from discotrade.tradingcal import (
    expected_bars,
    in_main_session,
    is_open,
    open_intervals,
    trading_date,
)

CONFIG = REPO_ROOT / "config"
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
GLOBEX = load_calendar(CONFIG / "calendars" / "cme_globex.toml")
SYNTH = load_calendar(FIXTURE_CONFIG / "calendars" / "synth_week.toml")
ALWAYS = load_calendar(FIXTURE_CONFIG / "calendars" / "always_open.toml")
NY = ZoneInfo("America/New_York")
HOUR = 3600
MAIN = ("09:30", "16:00")


def ny(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=NY)


def utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


# --- the records ---------------------------------------------------------------


def test_globex_record_as_designed():
    assert GLOBEX.name == "cme_globex"
    assert not GLOBEX.always_open
    assert GLOBEX.tz == "America/New_York"
    assert GLOBEX.week_open == ("Sun", "18:00")
    assert GLOBEX.week_close == ("Fri", "17:00")
    assert GLOBEX.daily_break == ("17:00", "18:00")
    assert GLOBEX.day_rolls_at == "17:00"
    # The closure DESIGN 5.3 shows.
    christmas = [c for c in GLOBEX.closures if c.start == datetime(2026, 12, 24, 13, 15)]
    assert len(christmas) == 1 and christmas[0].end == datetime(2026, 12, 27, 18, 0)


def test_globex_closures_cover_2019_to_2027_and_none_is_verified():
    years = {c.start.year for c in GLOBEX.closures} | {c.end.year for c in GLOBEX.closures}
    assert set(range(2019, 2028)) <= years
    assert GLOBEX.provenance is not None and GLOBEX.provenance.verified is False
    for c in GLOBEX.closures:
        assert c.provenance is not None and c.provenance.verified is False
        assert c.provenance.source and c.note and c.start < c.end
    # Every closure is listed as unverified, with the four schedule values.
    keys = [k for k, _, _ in GLOBEX.unverified()]
    assert keys[:4] == ["week_open", "week_close", "daily_break", "day_rolls_at"]
    assert keys[4:] == [f"closure.{i}" for i in range(len(GLOBEX.closures))]


def test_fixture_calendars():
    assert SYNTH.name == "synth_week" and len(SYNTH.closures) == 1
    assert SYNTH.provenance is None and SYNTH.unverified() == []
    assert ALWAYS.name == "always_open" and ALWAYS.always_open and ALWAYS.closures == ()
    assert ALWAYS.unverified() == []


def calendars_named(config: Path) -> set[str]:
    names = set()
    for path in (config / "instruments").glob("*.toml"):
        with open(path, "rb") as f:
            names.add(tomllib.load(f)["calendar"])
    return names


@pytest.mark.parametrize("config", [CONFIG, FIXTURE_CONFIG])
def test_every_named_calendar_has_a_record(config):
    names = calendars_named(config)
    assert names
    for name in names:
        assert load_calendar(config / "calendars" / f"{name}.toml").name == name


CAL = """\
name = "cal"
tz = "America/New_York"
week_open = ["Sun", "18:00"]
week_close = ["Fri", "17:00"]
daily_break = ["17:00", "18:00"]
day_rolls_at = "17:00"

[[closure]]
start = "2026-12-24 13:15"
end = "2026-12-27 18:00"
note = "Christmas"
checked = "2026-10-11"
source = "exchange holiday calendar"
verified = false
"""


def write(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def test_temporary_record_loads(tmp_path):
    cal = load_calendar(write(tmp_path / "cal.toml", CAL))
    assert cal.closures[0].note == "Christmas"
    assert cal.closures[0].provenance.checked == date(2026, 10, 11)


@pytest.mark.parametrize(
    "edit, match",
    [
        (lambda s: s.replace('day_rolls_at = "17:00"', 'day_rolls_at = "17:00"\nx = 1'),
         "unknown key 'x'"),
        (lambda s: s.replace('note = "Christmas"', 'note = "Christmas"\nwho = 1'),
         "unknown key 'closure.who'"),
        (lambda s: s.replace('tz = "America/New_York"\n', ""), "missing key 'tz'"),
        (lambda s: s.replace("America/New_York", "Mars/Olympus"), "'tz'"),
        (lambda s: s.replace('["Sun", "18:00"]', '["Sunday", "18:00"]'), "week_open"),
        (lambda s: s.replace('["Fri", "17:00"]', '["Fri", "25:00"]'), "week_close"),
        (lambda s: s.replace('["17:00", "18:00"]', '["18:00", "17:00"]'), "daily_break"),
        (lambda s: s.replace('day_rolls_at = "17:00"', 'day_rolls_at = "5pm"'), "day_rolls_at"),
        (lambda s: s.replace('"2026-12-27 18:00"', '"2026-12-24 13:15"'), "closure.end"),
        (lambda s: s.replace('"2026-12-24 13:15"', '"2026-12-24"'), "closure.start"),
        (lambda s: s.replace("verified = false\n", ""), "closure.verified"),
        (lambda s: s.replace('name = "cal"', 'name = "other"'), "file name"),
    ],
)
def test_calendar_refusals(tmp_path, edit, match):
    path = write(tmp_path / "cal.toml", edit(CAL))
    with pytest.raises(ConfigError, match=match):
        load_calendar(path)


def test_always_open_has_no_other_key(tmp_path):
    path = write(tmp_path / "c.toml", 'name = "c"\nalways_open = true\ntz = "UTC"\n')
    with pytest.raises(ConfigError, match="always_open"):
        load_calendar(path)
    path = write(tmp_path / "c.toml", 'name = "c"\nalways_open = false\n')
    with pytest.raises(ConfigError, match="always_open"):
        load_calendar(path)


def test_closure_without_companions_loads(tmp_path):
    text = CAL.split("checked")[0]
    cal = load_calendar(write(tmp_path / "cal.toml", text))
    assert cal.closures[0].provenance is None and cal.unverified() == []


def test_naive_instant_refused():
    with pytest.raises(ValueError):
        is_open(GLOBEX, datetime(2024, 3, 11, 12, 0))


# --- open or closed ------------------------------------------------------------


@pytest.mark.parametrize(
    "instant, expected",
    [
        # Spring week: clocks go forward Sunday 2024-03-10 (New York, UTC-5 -> UTC-4).
        ("2024-03-08 21:59", True),    # Friday 16:59 EST
        ("2024-03-08 22:00", False),   # Friday 17:00 EST: week close
        ("2024-03-09 15:00", False),   # Saturday
        ("2024-03-10 21:59", False),   # Sunday 17:59 EDT
        ("2024-03-10 22:00", True),    # Sunday 18:00 EDT: week open
        ("2024-03-11 20:59", True),    # Monday 16:59 EDT
        ("2024-03-11 21:00", False),   # Monday 17:00 EDT: daily break
        ("2024-03-11 21:59", False),
        ("2024-03-11 22:00", True),    # Monday 18:00 EDT
        # The week before, still on standard time: the week opened an hour later in UTC.
        ("2024-03-03 22:00", False),
        ("2024-03-03 23:00", True),
        # Autumn week: clocks go back Sunday 2024-11-03 (UTC-4 -> UTC-5).
        ("2024-11-01 20:59", True),    # Friday 16:59 EDT
        ("2024-11-01 21:00", False),   # Friday 17:00 EDT
        ("2024-11-03 22:00", False),   # Sunday 17:00 EST
        ("2024-11-03 23:00", True),    # Sunday 18:00 EST
        ("2024-11-05 22:00", False),   # Tuesday 17:00 EST: daily break
        ("2024-11-05 23:00", True),
        # Closure: Christmas 2026, 24th 13:15 to 27th 18:00 New York time (EST).
        ("2026-12-24 18:14", True),
        ("2026-12-24 18:15", False),
        ("2026-12-25 15:00", False),
        ("2026-12-27 22:59", False),
        ("2026-12-27 23:00", True),
    ],
)
def test_is_open_globex(instant, expected):
    assert is_open(GLOBEX, utc(instant)) is expected


def test_is_open_synth_closure_and_always_open():
    assert is_open(SYNTH, ny("2019-07-03 12:59"))
    assert not is_open(SYNTH, ny("2019-07-03 13:00"))
    assert not is_open(SYNTH, ny("2019-07-04 17:59"))
    assert is_open(SYNTH, ny("2019-07-04 18:00"))
    assert is_open(SYNTH, ny("2020-07-03 13:00"))   # the closure is dated, not yearly
    for instant in ("2024-03-09 15:00", "2024-03-10 07:00", "2024-12-25 12:00"):
        assert is_open(ALWAYS, utc(instant))


def test_open_intervals_spring_week():
    got = open_intervals(GLOBEX, utc("2024-03-10 00:00"), utc("2024-03-16 00:00"))
    assert got[0] == (utc("2024-03-10 22:00"), utc("2024-03-11 21:00"))
    assert got[-1] == (utc("2024-03-14 22:00"), utc("2024-03-15 21:00"))
    assert len(got) == 5
    assert all(b - a == timedelta(hours=23) for a, b in got)


# --- the trading date ----------------------------------------------------------


@pytest.mark.parametrize(
    "bar, expected",
    [
        ("2024-03-10 22:00", "2024-03-11"),   # Sunday 18:00 EDT -> Monday
        ("2024-03-11 20:00", "2024-03-11"),   # Monday 16:00 EDT
        ("2024-03-11 22:00", "2024-03-12"),   # Monday 18:00 EDT -> Tuesday
        ("2024-03-08 21:00", "2024-03-08"),   # Friday 16:00 EST
        ("2024-03-08 03:00", "2024-03-08"),   # Thursday 22:00 EST -> Friday
        ("2024-11-03 23:00", "2024-11-04"),   # Sunday 18:00 EST -> Monday
        ("2024-11-01 20:00", "2024-11-01"),   # Friday 16:00 EDT
        ("2024-11-04 21:00", "2024-11-04"),   # Monday 16:00 EST
        ("2024-11-04 22:00", "2024-11-05"),   # Monday 17:00 EST: the next trading day
    ],
)
def test_trading_date_globex(bar, expected):
    assert trading_date(GLOBEX, utc(bar)) == date.fromisoformat(expected)


def test_trading_date_always_open_is_the_utc_date():
    assert trading_date(ALWAYS, utc("2024-03-10 23:00")) == date(2024, 3, 10)
    assert trading_date(ALWAYS, utc("2024-03-11 00:00")) == date(2024, 3, 11)


# --- expected bars -------------------------------------------------------------


def by_date(cal, bars):
    out: dict[date, int] = {}
    for b in bars:
        out[trading_date(cal, b)] = out.get(trading_date(cal, b), 0) + 1
    return out


def test_expected_bars_spring_week():
    bars = expected_bars(GLOBEX, utc("2024-03-09 00:00"), utc("2024-03-16 00:00"), HOUR)
    assert len(bars) == 5 * 23
    assert bars[0] == utc("2024-03-10 22:00") and bars[-1] == utc("2024-03-15 20:00")
    assert utc("2024-03-11 21:00") not in bars           # daily break
    assert by_date(GLOBEX, bars) == {date(2024, 3, d): 23 for d in range(11, 16)}


def test_expected_bars_autumn_week():
    bars = expected_bars(GLOBEX, utc("2024-11-02 00:00"), utc("2024-11-09 00:00"), HOUR)
    assert len(bars) == 5 * 23
    assert bars[0] == utc("2024-11-03 23:00") and bars[-1] == utc("2024-11-08 21:00")
    assert utc("2024-11-04 22:00") not in bars           # daily break, EST
    assert utc("2024-11-04 21:00") in bars


def test_expected_bars_the_week_before_the_spring_change():
    bars = expected_bars(GLOBEX, utc("2024-03-02 00:00"), utc("2024-03-09 00:00"), HOUR)
    assert len(bars) == 5 * 23
    assert bars[0] == utc("2024-03-03 23:00") and bars[-1] == utc("2024-03-08 21:00")


def test_expected_bars_none_on_a_weekend():
    assert expected_bars(GLOBEX, utc("2024-03-09 00:00"), utc("2024-03-10 21:00"), HOUR) == []


def test_expected_bars_around_a_closure():
    bars = expected_bars(GLOBEX, utc("2026-12-20 00:00"), utc("2026-12-28 00:00"), HOUR)
    counts = by_date(GLOBEX, bars)
    # 24th: 18:00 on the 23rd to the bar opening 13:00 (it overlaps 13:00 to 13:15).
    assert counts[date(2026, 12, 24)] == 20
    assert utc("2026-12-24 18:00") in bars and utc("2026-12-24 19:00") not in bars
    assert date(2026, 12, 25) not in counts
    assert counts[date(2026, 12, 21)] == 23 and counts[date(2026, 12, 23)] == 23
    assert bars[-1] == utc("2026-12-27 23:00")


def test_expected_bars_half_open_range_and_alignment():
    bars = expected_bars(GLOBEX, utc("2024-03-11 10:30"), utc("2024-03-11 13:00"), HOUR)
    assert bars == [utc("2024-03-11 11:00"), utc("2024-03-11 12:00")]
    quarter = expected_bars(GLOBEX, utc("2024-03-11 20:00"), utc("2024-03-11 23:00"), 900)
    assert len(quarter) == 4 + 4


def test_expected_bars_always_open():
    bars = expected_bars(ALWAYS, utc("2024-03-09 00:00"), utc("2024-03-11 00:00"), HOUR)
    assert len(bars) == 48


def test_expected_bars_synth_closure():
    bars = expected_bars(SYNTH, utc("2019-07-01 00:00"), utc("2019-07-06 00:00"), HOUR)
    counts = by_date(SYNTH, bars)
    assert counts[date(2019, 7, 3)] == 19          # 18:00 on the 2nd to the 12:00 bar
    assert date(2019, 7, 4) not in counts
    assert counts[date(2019, 7, 5)] == 23


# --- the main session ----------------------------------------------------------


def main_bars(cal, first, last):
    return [b for b in expected_bars(cal, utc(first), utc(last), HOUR)
            if in_main_session(cal, MAIN, b)]


def test_main_session_spring_and_autumn_weeks():
    spring = main_bars(GLOBEX, "2024-03-09 00:00", "2024-03-16 00:00")
    assert len(spring) == 5 * 6
    assert spring[0] == utc("2024-03-11 14:00")    # 10:00 EDT
    autumn = main_bars(GLOBEX, "2024-11-02 00:00", "2024-11-09 00:00")
    assert len(autumn) == 5 * 6
    assert autumn[0] == utc("2024-11-04 15:00")    # 10:00 EST
    before = main_bars(GLOBEX, "2024-03-02 00:00", "2024-03-09 00:00")
    assert before[0] == utc("2024-03-04 15:00")    # 10:00 EST


def test_main_session_edges():
    assert not in_main_session(GLOBEX, MAIN, ny("2024-03-11 09:00"))
    assert in_main_session(GLOBEX, MAIN, ny("2024-03-11 09:30"))
    assert in_main_session(GLOBEX, MAIN, ny("2024-03-11 15:59"))
    assert not in_main_session(GLOBEX, MAIN, ny("2024-03-11 16:00"))
    assert not in_main_session(GLOBEX, MAIN, ny("2024-03-09 12:00"))   # Saturday
    assert not in_main_session(GLOBEX, MAIN, ny("2024-03-10 12:00"))   # Sunday


def test_main_session_not_in_a_closure():
    # Day after Thanksgiving 2026: early close at 13:15.
    bars = main_bars(GLOBEX, "2026-11-27 00:00", "2026-11-28 00:00")
    assert [b.astimezone(NY).hour for b in bars] == [10, 11, 12, 13]
    assert not in_main_session(GLOBEX, MAIN, ny("2026-12-25 11:00"))
    assert not in_main_session(SYNTH, MAIN, ny("2019-07-04 11:00"))


def test_main_session_always_open_is_utc_weekdays():
    assert in_main_session(ALWAYS, MAIN, utc("2024-03-11 10:00"))
    assert not in_main_session(ALWAYS, MAIN, utc("2024-03-10 10:00"))
    assert not in_main_session(ALWAYS, MAIN, utc("2024-03-11 17:00"))


# --- properties ----------------------------------------------------------------

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def oracle_open(cal, instant: datetime) -> bool:
    """Open by the wall-clock rule of DESIGN 5.3, written apart from tradingcal."""
    if cal.always_open:
        return True
    local = instant.astimezone(ZoneInfo(cal.tz))
    minute = local.weekday() * 1440 + local.hour * 60 + local.minute

    def week_minute(day, hhmm):
        h, m = hhmm.split(":")
        return DAYS.index(day) * 1440 + int(h) * 60 + int(m)

    start, end = week_minute(*cal.week_open), week_minute(*cal.week_close)
    in_week = start <= minute < end if start < end else (minute >= start or minute < end)
    hhmm = f"{local.hour:02d}:{local.minute:02d}"
    in_break = cal.daily_break[0] <= hhmm < cal.daily_break[1]
    naive = local.replace(tzinfo=None)
    closed = any(c.start <= naive < c.end for c in cal.closures)
    return in_week and not in_break and not closed


STEP = 900   # every boundary in these calendars is on a quarter hour
FIRST = int(datetime(2019, 1, 1, tzinfo=UTC).timestamp())
LAST = int(datetime(2027, 12, 31, tzinfo=UTC).timestamp())
CALENDARS = {"globex": GLOBEX, "synth": SYNTH, "always": ALWAYS}


@settings(derandomize=True, max_examples=150, deadline=None)
@given(
    cal=st.sampled_from(sorted(CALENDARS)),
    start=st.integers(FIRST, LAST),
    hours=st.integers(1, 24 * 9),
    bar_seconds=st.sampled_from([900, 1800, 3600, 7200, 14400]),
)
def test_expected_bars_are_exactly_the_bars_that_touch_open_time(cal, start, hours, bar_seconds):
    """Every expected bar overlaps an open interval; no bar inside closed time is expected."""
    cal = CALENDARS[cal]
    begin = datetime.fromtimestamp(start, UTC)
    end = begin + timedelta(hours=hours)
    bars = expected_bars(cal, begin, end, bar_seconds)
    assert bars == sorted(set(bars))
    t = -(-start // bar_seconds) * bar_seconds
    expected = set(bars)
    while t < end.timestamp():
        bar = datetime.fromtimestamp(t, UTC)
        points = [datetime.fromtimestamp(p, UTC) for p in range(t, t + bar_seconds, STEP)]
        touches = any(oracle_open(cal, p) for p in points)
        assert (bar in expected) is touches, bar
        if touches:
            assert open_intervals(cal, bar, bar + timedelta(seconds=bar_seconds))
        t += bar_seconds
    assert all(begin <= b < end for b in bars)


@settings(derandomize=True, max_examples=400, deadline=None)
@given(cal=st.sampled_from(sorted(CALENDARS)), quarter=st.integers(FIRST // STEP, LAST // STEP))
def test_is_open_agrees_with_the_wall_clock_rule(cal, quarter):
    cal = CALENDARS[cal]
    instant = datetime.fromtimestamp(quarter * STEP, UTC)
    assert is_open(cal, instant) is oracle_open(cal, instant)
