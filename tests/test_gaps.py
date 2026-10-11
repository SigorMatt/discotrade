"""The gap check (DESIGN 5.4, 4.1 windows, 15.2 health event; I-5, I-6).

Bars are written directly through the store on the fixture track
``test_synth`` (four instruments on the ``synth_week`` calendar, whose one
closure runs from 2019-07-03 13:00 to 2019-07-04 18:00 New York time). Every
test writes into a pytest ``tmp_path`` state directory.
"""

import json
import shutil
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest

from discotrade.bars.gaps import GAPS_FILE, check_gaps, find_missing
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_thresholds, load_track_config
from discotrade.tradingcal import expected_bars, is_open, trading_date

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
LATE = datetime(2030, 1, 1, tzinfo=UTC)
#: Data from the Sunday open before W of DAY to the end of DAY's trading day.
START = datetime(2019, 6, 2, 0, 0, tzinfo=UTC)
END = datetime(2019, 7, 13, 0, 0, tzinfo=UTC)
DAY = date(2019, 7, 12)   # T = 2019-07-06..07-12, W = 2019-06-08..07-05


@pytest.fixture(scope="module")
def tc():
    return load_track_config(FIXTURE_CONFIG, TRACK)


@pytest.fixture(scope="module")
def calendars(tc):
    names = {inst.calendar for inst in tc.instruments}
    return {n: load_calendar(FIXTURE_CONFIG / "calendars" / f"{n}.toml") for n in names}


def frame(times, symbol):
    n = len(times)
    price = [100.0 + i / 7.0 for i in range(n)]
    return pd.DataFrame({
        "ts": pd.DatetimeIndex(pd.to_datetime(times, utc=True)),
        "open": price,
        "high": [p + 1.0 for p in price],
        "low": [p - 1.0 for p in price],
        "close": price,
        "volume": [1.0] * n,
        "contract": [symbol] * n,
    })


def all_expected(tc, calendars, symbol, start=START, end=END):
    inst = next(i for i in tc.instruments if i.symbol == symbol)
    return expected_bars(calendars[inst.calendar], start, end, tc.track.bar_seconds)


def fill(state, tc, calendars, removed=None, start=START, end=END):
    """Store every expected bar of every instrument except those in ``removed``."""
    removed = removed or {}
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    for inst in tc.instruments:
        drop = set(removed.get(inst.symbol, ()))
        keep = [t for t in all_expected(tc, calendars, inst.symbol, start, end) if t not in drop]
        store.append(inst.symbol, frame(keep, inst.symbol), LATE)
    return store


def gap_lines(state):
    path = state / "bars" / TRACK / GAPS_FILE
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def in_window(tc, calendars, symbol, times, first, last):
    inst = next(i for i in tc.instruments if i.symbol == symbol)
    cal = calendars[inst.calendar]
    return [t for t in times if first <= trading_date(cal, t) <= last]


def test_complete_bars_have_no_gap_across_break_weekend_and_closure(tmp_path, tc, calendars):
    state = tmp_path / "state"
    fill(state, tc, calendars)
    cal = calendars["synth_week"]
    # The stored span holds closed hours of each kind: a daily break, a
    # weekend and the closure. None of them is reported missing.
    shut = [datetime(2019, 6, 4, 21, 30, tzinfo=UTC),    # 17:30 New York, daily break
            datetime(2019, 6, 8, 12, 0, tzinfo=UTC),     # Saturday
            datetime(2019, 7, 4, 12, 0, tzinfo=UTC)]     # the closure
    assert not any(is_open(cal, t) for t in shut)
    for inst in tc.instruments:
        assert find_missing(BarStore(state, TRACK, 3600), inst,
                            calendars[inst.calendar], 3600) == []
    report = check_gaps(state, tc, calendars, DAY, max_fraction=0.01)
    assert report.missing == {inst.symbol: () for inst in tc.instruments}
    assert report.new == 0
    assert gap_lines(state) == []
    assert not report.skip_generation and report.event is None
    assert [w.missing for w in report.windows] == [0, 0]


def test_removed_bars_are_reported_exactly_and_appended_once(tmp_path, tc, calendars):
    state = tmp_path / "state"
    a = all_expected(tc, calendars, "SYNA")
    c = all_expected(tc, calendars, "SYNC")
    # Interior bars: next to the daily break, next to the closure, mid-week,
    # and a run of three.
    removed = {
        "SYNA": [a[20], a[21], a[22], a[200], a[500]],
        "SYNC": [c[333]],
    }
    removed["SYNA"].append(next(t for t in a if t == datetime(2019, 7, 3, 16, 0, tzinfo=UTC)))
    removed["SYNA"].sort()
    fill(state, tc, calendars, removed)

    report = check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    assert report.missing == {
        "SYNA": tuple(removed["SYNA"]), "SYNB": (), "SYNC": tuple(removed["SYNC"]), "SYND": (),
    }
    assert report.new == 7
    lines = gap_lines(state)
    want = [{"symbol": s, "ts": t.isoformat()} for s in ("SYNA", "SYNC") for t in removed[s]]
    assert lines == want

    again = check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    assert again.missing == report.missing
    assert again.new == 0
    assert gap_lines(state) == want


def test_only_newly_found_missing_bars_are_appended(tmp_path, tc, calendars):
    state = tmp_path / "state"
    mid = datetime(2019, 6, 20, 0, 0, tzinfo=UTC)
    a1 = all_expected(tc, calendars, "SYNA", START, mid)
    store = fill(state, tc, calendars, {"SYNA": [a1[10]]}, START, mid)
    check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    a2 = all_expected(tc, calendars, "SYNA", mid, END)
    for inst in tc.instruments:
        times = all_expected(tc, calendars, inst.symbol, mid, END)
        if inst.symbol == "SYNA":
            times = [t for t in times if t != a2[5]]
        store.append(inst.symbol, frame(times, inst.symbol), LATE)
    report = check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    assert report.missing["SYNA"] == (a1[10], a2[5])
    assert report.new == 1
    assert [ln["ts"] for ln in gap_lines(state)] == [a1[10].isoformat(), a2[5].isoformat()]


def test_span_starts_at_first_stored_bar_and_ends_at_last(tmp_path, tc, calendars):
    """Expected bars before the first stored bar or after the last are not missing."""
    state = tmp_path / "state"
    a = all_expected(tc, calendars, "SYNA")
    store = BarStore(state, TRACK, 3600)
    store.append("SYNA", frame(a[50:60], "SYNA"), LATE)
    inst = tc.instruments[0]
    assert find_missing(store, inst, calendars[inst.calendar], 3600) == []
    store.append("SYNA", frame(a[62:70], "SYNA"), LATE)
    assert find_missing(store, inst, calendars[inst.calendar], 3600) == [a[60], a[61]]


def test_span_starts_no_earlier_than_trusted_from(tmp_path, tc, calendars):
    inst = tc.instruments[0]
    cal = calendars[inst.calendar]
    trusted = datetime.combine(inst.trusted_from, datetime.min.time(), tzinfo=UTC)
    before = expected_bars(cal, trusted - timedelta(days=7), trusted + timedelta(days=7), 3600)
    store = BarStore(tmp_path / "state", TRACK, 3600)
    # Bars before trusted_from are stored with holes; the holes are not missing.
    early = [t for t in before if t < trusted]
    late = [t for t in before if t >= trusted]
    keep = early[::2] + late[:3] + late[4:]
    store.append(inst.symbol, frame(sorted(keep), inst.symbol), LATE)
    assert find_missing(store, inst, cal, 3600) == [late[3]]


def test_window_fraction_is_pooled_over_the_track_instruments(tmp_path, tc, calendars):
    state = tmp_path / "state"
    wins = tc.track.windows(DAY)
    a = all_expected(tc, calendars, "SYNA")
    in_t = in_window(tc, calendars, "SYNA", a, wins.t.first, wins.t.last)
    in_w = in_window(tc, calendars, "SYNA", a, wins.w.first, wins.w.last)
    removed = {"SYNA": sorted([in_t[3], in_t[40], in_w[7]])}
    fill(state, tc, calendars, removed)
    report = check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    w, t = report.windows
    assert (w.name, w.first, w.last) == ("W", wins.w.first, wins.w.last)
    assert (t.name, t.first, t.last) == ("T", wins.t.first, wins.t.last)
    expected_t = sum(len(in_window(tc, calendars, i.symbol,
                                   all_expected(tc, calendars, i.symbol),
                                   wins.t.first, wins.t.last)) for i in tc.instruments)
    expected_w = sum(len(in_window(tc, calendars, i.symbol,
                                   all_expected(tc, calendars, i.symbol),
                                   wins.w.first, wins.w.last)) for i in tc.instruments)
    assert (t.missing, t.expected) == (2, expected_t)
    assert (w.missing, w.expected) == (1, expected_w)
    assert t.fraction == 2 / expected_t
    assert w.fraction == 1 / expected_w
    # Pooled, not per instrument: SYNA alone would be four times higher.
    assert t.fraction < 2 / len(in_t)


def _remove_in(tc, calendars, which, count):
    wins = tc.track.windows(DAY)
    rng = wins.t if which == "T" else wins.w
    a = all_expected(tc, calendars, "SYNA")
    b = all_expected(tc, calendars, "SYNB")
    pool = ([("SYNA", t) for t in in_window(tc, calendars, "SYNA", a, rng.first, rng.last)][1::9]
            + [("SYNB", t) for t in in_window(tc, calendars, "SYNB", b, rng.first, rng.last)][2::9])
    chosen = pool[:count]
    out: dict[str, list] = {}
    for sym, t in chosen:
        out.setdefault(sym, []).append(t)
    return {s: sorted(v) for s, v in out.items()}


@pytest.mark.parametrize("which", ["W", "T"])
def test_above_the_limit_generation_is_skipped_with_a_data_gaps_event(tmp_path, tc, calendars,
                                                                      which):
    state = tmp_path / "state"
    fill(state, tc, calendars, _remove_in(tc, calendars, which, 6))
    probe = check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    window = next(w for w in probe.windows if w.name == which)
    other = next(w for w in probe.windows if w.name != which)
    assert window.missing == 6 and other.missing == 0

    limit = 5 / window.expected        # 6 missing is above it
    report = check_gaps(state, tc, calendars, DAY, max_fraction=limit)
    assert report.skip_generation
    ev = report.event
    assert ev is not None
    assert (ev.date, ev.level, ev.kind, ev.subject) == (DAY, "alert", "data_gaps", TRACK)
    assert ev.detail["over"] == [which]
    assert ev.detail["max_fraction"] == limit
    assert ev.detail["windows"][which] == {
        "first": window.first.isoformat(), "last": window.last.isoformat(),
        "expected": window.expected, "missing": 6, "fraction": 6 / window.expected,
    }
    line = json.loads(ev.to_json())
    assert line == {"date": DAY.isoformat(), "level": "alert", "kind": "data_gaps",
                    "subject": TRACK, "detail": ev.detail}
    assert "\n" not in ev.to_json()


@pytest.mark.parametrize("which", ["W", "T"])
def test_at_the_limit_generation_is_not_skipped(tmp_path, tc, calendars, which):
    state = tmp_path / "state"
    fill(state, tc, calendars, _remove_in(tc, calendars, which, 6))
    probe = check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    window = next(w for w in probe.windows if w.name == which)
    report = check_gaps(state, tc, calendars, DAY, max_fraction=6 / window.expected)
    assert window.fraction == 6 / window.expected
    assert not report.skip_generation
    assert report.event is None


def test_the_configured_limit_is_the_one_in_thresholds(tmp_path, tc, calendars):
    """With gaps.max_fraction from config/thresholds.toml (0.01): 4 of the 460
    expected T bars is at or below it, 5 is above it."""
    limit = load_thresholds(REPO_ROOT / "config" / "thresholds.toml")["gaps.max_fraction"]
    assert limit == 0.01
    for count, skipped in ((4, False), (5, True)):
        state = tmp_path / f"state{count}"
        fill(state, tc, calendars, _remove_in(tc, calendars, "T", count))
        report = check_gaps(state, tc, calendars, DAY, max_fraction=limit)
        t = report.windows[1]
        assert t.expected == 460
        assert report.skip_generation is skipped
        assert (report.event is not None) is skipped


def _cli_config(tmp_path):
    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    return config


def test_bars_gaps_command_reports_missing_bars(tmp_path, tc, calendars, capsys):
    state = tmp_path / "state"
    a = all_expected(tc, calendars, "SYNA")
    fill(state, tc, calendars, {"SYNA": [a[100]]})
    config = _cli_config(tmp_path)
    argv = ["--state", str(state), "--config", str(config), "--track", TRACK,
            "--as-of", "2019-07-13T00:00:00+00:00", "bars", "gaps"]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert f"missing SYNA {a[100].isoformat()}" in out
    assert [ln for ln in out.splitlines() if ln.startswith("missing ")] == [
        f"missing SYNA {a[100].isoformat()}"]
    assert "day 2019-07-12" in out
    assert "generation: ok" in out
    assert len(gap_lines(state)) == 1
    assert main(argv) == 0
    assert len(gap_lines(state)) == 1


def test_bars_gaps_command_says_when_generation_is_skipped(tmp_path, tc, calendars, capsys):
    state = tmp_path / "state"
    fill(state, tc, calendars, _remove_in(tc, calendars, "T", 5))
    config = _cli_config(tmp_path)
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "bars", "gaps", "--day", "2019-07-12"]) == 0
    out = capsys.readouterr().out
    assert "generation: skipped (data_gaps: T above gaps.max_fraction 0.01)" in out


def test_bars_gaps_command_needs_a_state_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    config = _cli_config(tmp_path)
    assert main(["--config", str(config), "--track", TRACK, "bars", "gaps",
                 "--day", "2019-07-12"]) == 1
    assert "state directory" in capsys.readouterr().err
