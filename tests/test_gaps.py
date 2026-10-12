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
from discotrade.bars.store import BarStore, BarStoreError
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


# --- the check for a day reads only bars up to the end of that day (decision 3) -----

AFTER = datetime(2019, 7, 27, 0, 0, tzinfo=UTC)


def _after_day_removed(tc, calendars):
    """Missing bars both before and after the end of DAY's trading day."""
    a = all_expected(tc, calendars, "SYNA", START, AFTER)
    c = all_expected(tc, calendars, "SYNC", START, AFTER)
    end_a = [t for t in a if trading_date(calendars["synth_week"], t) <= DAY]
    return {"SYNA": [a[30], end_a[-3], a[len(end_a) + 40]], "SYNC": [c[len(end_a) + 7]]}


def test_a_replay_of_a_past_day_appends_nothing_beyond_the_original_run(tmp_path, tc,
                                                                       calendars):
    removed = _after_day_removed(tc, calendars)
    original, replay = tmp_path / "original", tmp_path / "replay"
    # The original run of DAY: bars up to the end of DAY.
    fill(original, tc, calendars, removed, START, END)
    first = check_gaps(original, tc, calendars, DAY, max_fraction=1.0)
    lines = (original / "bars" / TRACK / GAPS_FILE).read_bytes()
    assert [ln["ts"] for ln in gap_lines(original)] == [
        removed["SYNA"][0].isoformat(), removed["SYNA"][1].isoformat()]
    # Later bars arrive, with gaps of their own; DAY is replayed.
    store = BarStore(original, TRACK, 3600)
    for inst in tc.instruments:
        drop = set(removed.get(inst.symbol, ()))
        later = [t for t in all_expected(tc, calendars, inst.symbol, END, AFTER)
                 if t not in drop]
        store.append(inst.symbol, frame(later, inst.symbol), LATE)
    again = check_gaps(original, tc, calendars, DAY, max_fraction=1.0)
    assert again.new == 0
    assert again.missing == first.missing
    assert again.windows == first.windows
    assert (original / "bars" / TRACK / GAPS_FILE).read_bytes() == lines
    # A first run of DAY on a store that already holds the later bars.
    fill(replay, tc, calendars, removed, START, AFTER)
    late_first = check_gaps(replay, tc, calendars, DAY, max_fraction=1.0)
    assert late_first.missing == first.missing
    assert late_first.windows == first.windows
    assert (replay / "bars" / TRACK / GAPS_FILE).read_bytes() == lines


# --- a stopped or absent feed counts as missing to the end of D (decision 2) --------


def test_a_feed_that_stopped_counts_as_missing_to_the_end_of_the_day(tmp_path, tc, calendars):
    state = tmp_path / "state"
    wins = tc.track.windows(DAY)
    cal = calendars["synth_week"]
    a = all_expected(tc, calendars, "SYNA")
    in_t = in_window(tc, calendars, "SYNA", a, wins.t.first, wins.t.last)
    stop = in_t[20]
    store = fill(state, tc, calendars, {"SYNA": [t for t in a if t >= stop]})
    assert store.last_ts("SYNA") < stop
    report = check_gaps(state, tc, calendars, DAY, max_fraction=0.01)
    w, t = report.windows
    assert t.missing == len(in_t) - 20
    assert t.expected == 460
    assert w.missing == 0
    assert report.skip_generation and report.event.detail["over"] == ["T"]
    # gaps.jsonl keeps the first definition: nothing after the last stored bar.
    assert report.missing["SYNA"] == ()
    assert gap_lines(state) == []
    assert all(trading_date(cal, x) <= DAY for x in in_t)


def test_an_instrument_with_no_stored_bar_counts_as_missing(tmp_path, tc, calendars):
    state = tmp_path / "state"
    store = BarStore(state, TRACK, 3600)
    for inst in tc.instruments:
        if inst.symbol != "SYND":
            store.append(inst.symbol, frame(all_expected(tc, calendars, inst.symbol),
                                            inst.symbol), LATE)
    report = check_gaps(state, tc, calendars, DAY, max_fraction=0.01)
    w, t = report.windows
    assert (t.missing, t.expected) == (115, 460)
    assert w.missing == w.expected // 4
    assert report.skip_generation and report.event.detail["over"] == ["W", "T"]
    assert report.missing["SYND"] == ()


def test_an_empty_store_skips_generation(tmp_path, tc, calendars):
    report = check_gaps(tmp_path / "state", tc, calendars, DAY, max_fraction=0.01)
    w, t = report.windows
    assert (t.missing, t.expected) == (460, 460)
    assert w.missing == w.expected > 0
    assert report.skip_generation


def test_window_counts_start_no_earlier_than_trusted_from(tmp_path, tc, calendars):
    """A window that starts before ``trusted_from`` expects nothing before it."""
    inst = tc.instruments[0]
    trusted = inst.trusted_from
    day = trusted + timedelta(days=3)
    report = check_gaps(tmp_path / "state", tc, calendars, day, max_fraction=1.0)
    cal = calendars[inst.calendar]
    start = datetime.combine(trusted, datetime.min.time(), tzinfo=UTC)
    t_bars = [x for x in expected_bars(cal, start, start + timedelta(days=5), 3600)
              if trading_date(cal, x) <= day]
    assert report.windows[1].expected == 4 * len(t_bars)
    assert report.windows[0].expected == 0


# --- gaps.jsonl is appended atomically (decision 4) ----------------------------------


def test_an_append_to_gaps_jsonl_leaves_every_earlier_line_byte_identical(tmp_path, tc,
                                                                         calendars):
    state = tmp_path / "state"
    mid = datetime(2019, 6, 20, 0, 0, tzinfo=UTC)
    a1 = all_expected(tc, calendars, "SYNA", START, mid)
    store = fill(state, tc, calendars, {"SYNA": [a1[10], a1[11]]}, START, mid)
    check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    path = state / "bars" / TRACK / GAPS_FILE
    old = path.read_bytes()
    assert old.count(b"\n") == 2
    for inst in tc.instruments:
        times = all_expected(tc, calendars, inst.symbol, mid, END)
        store.append(inst.symbol, frame(times[:5] + times[6:], inst.symbol), LATE)
    assert check_gaps(state, tc, calendars, DAY, max_fraction=1.0).new == 4
    new = path.read_bytes()
    assert new.startswith(old) and new.count(b"\n") == 6
    assert not list(path.parent.glob("*.tmp"))


def test_a_crash_before_the_rename_leaves_gaps_jsonl_intact(tmp_path, tc, calendars,
                                                           monkeypatch):
    import os

    state = tmp_path / "state"
    mid = datetime(2019, 6, 20, 0, 0, tzinfo=UTC)
    a1 = all_expected(tc, calendars, "SYNA", START, mid)
    store = fill(state, tc, calendars, {"SYNA": [a1[10]]}, START, mid)
    check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    path = state / "bars" / TRACK / GAPS_FILE
    old = path.read_bytes()
    for inst in tc.instruments:
        times = all_expected(tc, calendars, inst.symbol, mid, END)
        store.append(inst.symbol, frame(times[:5] + times[6:], inst.symbol), LATE)

    def crash(src, dst):
        raise OSError("simulated crash before the rename")
    with monkeypatch.context() as m:
        m.setattr(os, "replace", crash)
        with pytest.raises(OSError, match="simulated"):
            check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    assert path.read_bytes() == old
    # The next run appends the lines the crashed one did not.
    assert check_gaps(state, tc, calendars, DAY, max_fraction=1.0).new == 4
    assert path.read_bytes().startswith(old)


def test_fsync_is_called_on_gaps_jsonl_before_its_rename(tmp_path, tc, calendars,
                                                       monkeypatch):
    import os

    state = tmp_path / "state"
    a = all_expected(tc, calendars, "SYNA")
    fill(state, tc, calendars, {"SYNA": [a[100]]})
    log = []
    real_fsync, real_replace = os.fsync, os.replace

    def fsync(fd):
        log.append(("fsync", os.readlink(f"/proc/self/fd/{fd}")))
        return real_fsync(fd)

    def replace(src, dst):
        log.append(("replace", str(src)))
        return real_replace(src, dst)
    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "replace", replace)
    check_gaps(state, tc, calendars, DAY, max_fraction=1.0)
    assert log[-3:] == [("fsync", str(state / "bars" / TRACK / (GAPS_FILE + ".tmp"))),
                        ("replace", str(state / "bars" / TRACK / (GAPS_FILE + ".tmp"))),
                        ("fsync", str(state / "bars" / TRACK))]


# --- the default day of `bars gaps` (decision 3, DESIGN 16.1) ------------------------


@pytest.mark.parametrize("as_of, day", [
    # 19:00 New York on Thursday: UTC date 07-11, trading date 07-12 (in progress).
    ("2019-07-11T23:00:00+00:00", "2019-07-11"),
    # Friday's last bar (20:00 UTC) closes at 21:00 UTC exactly.
    ("2019-07-12T21:00:00+00:00", "2019-07-12"),
    ("2019-07-12T20:59:00+00:00", "2019-07-11"),
    # Monday morning: the weekend dates have no bar, so D is Friday.
    ("2019-07-15T03:00:00+00:00", "2019-07-12"),
])
def test_bars_gaps_default_day_is_the_latest_closed_trading_day(tmp_path, tc, calendars,
                                                                 capsys, as_of, day):
    state = tmp_path / "state"
    fill(state, tc, calendars)
    config = _cli_config(tmp_path)
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "bars", "gaps"]) == 0
    assert f"track {TRACK}, day {day}" in capsys.readouterr().out


# --- the default day of `bars fetch` is the same D (decision 19, DESIGN 16.1) -------


class Lagged:
    """The synthetic source with the vendor's lag: ``available_until(now) = now -
    24 hours`` (DESIGN 5.5), and the bars at the times in ``hide`` never served."""

    name = "lagged"

    def __init__(self, inner, hide=()):
        self.inner, self.hide = inner, set(hide)

    def available_until(self, now):
        return self.inner.available_until(now) - timedelta(hours=24)

    def fetch(self, instrument, start, end):
        bars = self.inner.fetch(instrument, start, end)
        return bars[~bars["ts"].isin(self.hide)].reset_index(drop=True)

    def fetch_contract(self, instrument, contract, start, end):
        return self.inner.fetch_contract(instrument, contract, start, end)


def _lag(monkeypatch, hide=()):
    import discotrade.sources as sources
    real = sources.source_for

    def source_for(adapter, calendars, bar_seconds):
        return Lagged(real(adapter, calendars, bar_seconds), hide)
    monkeypatch.setattr(sources, "source_for", source_for)


def _run(state, config, as_of, action, *extra):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "bars", action, *extra])


def _day_line(out):
    days = [ln for ln in out.splitlines() if ln.startswith(f"track {TRACK}, day ")]
    assert len(days) == 1, out
    return days[0].rsplit(" ", 1)[1]


@pytest.mark.parametrize("lagged, as_of, day", [
    # 19:00 New York on Thursday: the UTC date minus one is 07-10, D is 07-11.
    (False, "2019-07-11T23:00:00+00:00", "2019-07-11"),
    # Monday morning: the UTC date minus one is a Sunday, D is Friday.
    (False, "2019-07-15T03:00:00+00:00", "2019-07-12"),
    # Lagged by 24 hours: Friday's last bar (closing 21:00 UTC) is not yet
    # available, so D is Thursday while the UTC date minus one is Friday.
    (True, "2019-07-13T20:00:00+00:00", "2019-07-11"),
    (True, "2019-07-13T21:00:00+00:00", "2019-07-12"),
])
def test_bars_fetch_default_day_is_the_day_bars_gaps_checks(tmp_path, monkeypatch, capsys,
                                                            lagged, as_of, day):
    if lagged:
        _lag(monkeypatch)
    state, config = tmp_path / "state", _cli_config(tmp_path)
    assert _run(state, config, as_of, "fetch") == 0
    fetched = _day_line(capsys.readouterr().out)
    assert _run(state, config, as_of, "gaps") == 0
    assert fetched == _day_line(capsys.readouterr().out) == day


def test_a_replay_of_the_fetch_day_appends_nothing_to_gaps_jsonl(tmp_path, monkeypatch,
                                                                 capsys):
    """Friday's 18:00 UTC bar is never served. At the first --as-of the source
    is available until Friday 18:00, so Friday is still open and the first run
    must not check it; a later run checking the first run's day, once Friday's
    later bars are stored, must then find nothing the first did not."""
    hole = pd.Timestamp("2019-07-12T18:00:00+00:00")
    _lag(monkeypatch, hide=[hole])
    state, config = tmp_path / "state", _cli_config(tmp_path)
    gaps = state / "bars" / TRACK / GAPS_FILE
    assert _run(state, config, "2019-07-13T18:00:00+00:00", "fetch") == 0
    day = _day_line(capsys.readouterr().out)
    assert day == "2019-07-11"
    before = gaps.read_bytes() if gaps.exists() else b""

    assert _run(state, config, "2019-07-13T18:00:00+00:00", "fetch") == 0
    assert _day_line(capsys.readouterr().out) == day
    assert (gaps.read_bytes() if gaps.exists() else b"") == before

    assert _run(state, config, "2019-07-16T12:00:00+00:00", "fetch", "--day", day) == 0
    out = capsys.readouterr().out
    assert _day_line(out) == day
    assert "new in gaps.jsonl: 0" in out
    assert (gaps.read_bytes() if gaps.exists() else b"") == before
    # The hole now lies inside the stored span: a check of Friday finds it.
    assert _run(state, config, "2019-07-16T12:00:00+00:00", "gaps", "--day",
                "2019-07-12") == 0
    assert f"missing SYNA {hole.isoformat()}" in capsys.readouterr().out


# --- `bars fetch` completes an interrupted append; the reader then reads (decision 18) --


def test_reads_refuse_an_unlisted_file_until_bars_fetch_completes_it(tmp_path, monkeypatch,
                                                                    capsys):
    state, config = tmp_path / "state", _cli_config(tmp_path)
    assert _run(state, config, "2019-06-28T00:00:00+00:00", "fetch") == 0
    store = BarStore(state, TRACK, 3600)
    early = (pd.Timestamp("2019-02-01", tz="UTC"), pd.Timestamp("2019-02-08", tz="UTC"))
    early_rows = store.read_range("SYNA", *early)
    at = early_rows["ts"].iloc[-1]

    def crash(self, index):
        raise OSError("simulated crash before the index write")
    with monkeypatch.context() as m:
        m.setattr(BarStore, "_write_index", crash)
        assert _run(state, config, "2019-07-03T00:00:00+00:00", "fetch") == 1
    capsys.readouterr()
    july = store.month_path("SYNA", "2019-07")
    assert july.exists() and "2019-07" not in store.index()["SYNA"]["months"]
    written = pd.read_parquet(july)

    # Reads whose range does not cover June or July are refused too.
    with pytest.raises(BarStoreError, match="interrupted append"):
        store.read_range("SYNA", *early)
    with pytest.raises(BarStoreError, match="interrupted append"):
        store.last_n("SYNA", at, 10)

    assert _run(state, config, "2019-07-03T00:00:00+00:00", "fetch") == 0
    out = capsys.readouterr().out
    assert "store_recovered" in out
    pd.testing.assert_frame_equal(store.read_range("SYNA", *early), early_rows)
    assert len(store.last_n("SYNA", at, 10)) == 10
    got = store.read_range("SYNA", pd.Timestamp("2019-07-01", tz="UTC"),
                           pd.Timestamp("2019-08-01", tz="UTC"))
    pd.testing.assert_frame_equal(got, written)
    # The completed store reads as one fetch to the same instant would.
    clean = tmp_path / "clean"
    assert _run(clean, config, "2019-07-03T00:00:00+00:00", "fetch") == 0
    whole = (pd.Timestamp("2019-01-01", tz="UTC"), pd.Timestamp("2019-08-01", tz="UTC"))
    pd.testing.assert_frame_equal(store.read_range("SYNA", *whole),
                                  BarStore(clean, TRACK, 3600).read_range("SYNA", *whole))


# --- an instrument with no index entry (decision 35) --------------------------------


def _unlisted_first_append(state, tc, calendars, revised=False):
    """SYNB, SYNC and SYND are stored and indexed; SYNA's first append crashed
    before its index write, so its directory holds a June file the index does
    not list. With ``revised`` the file fails decision 5's test with ``r = 0``
    (its rows are not in increasing ``ts`` order, which the writer never
    writes)."""
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    for inst in tc.instruments[1:]:
        store.append(inst.symbol, frame(all_expected(tc, calendars, inst.symbol), inst.symbol),
                     LATE)
    times = all_expected(tc, calendars, "SYNA", START, datetime(2019, 6, 10, tzinfo=UTC))
    rows = frame(times, "SYNA")
    if revised:
        rows = rows.iloc[::-1].reset_index(drop=True)
    path = store.month_path("SYNA", "2019-06")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows.to_parquet(path, index=False)
    assert "SYNA" not in store.index()
    return store


@pytest.mark.parametrize("revised, case, other", [
    (False, "interrupted append", "revised"), (True, "revised data point", "interrupted")])
def test_the_gap_check_refuses_an_unlisted_file_of_an_instrument_with_no_entry(
        tmp_path, tc, calendars, revised, case, other):
    state = tmp_path / "state"
    store = _unlisted_first_append(state, tc, calendars, revised)
    syna = next(i for i in tc.instruments if i.symbol == "SYNA")
    cal = calendars[syna.calendar]
    for call in (lambda: find_missing(store, syna, cal, tc.track.bar_seconds),
                 lambda: find_missing(store, syna, cal, tc.track.bar_seconds,
                                      datetime(2019, 6, 5, tzinfo=UTC))):
        with pytest.raises(BarStoreError, match=f"SYNA 2019-06.*{case}") as err:
            call()
        assert other not in str(err.value)
    with pytest.raises(BarStoreError, match=f"SYNA 2019-06.*{case}"):
        check_gaps(state, tc, calendars, DAY, 0.02)
    assert gap_lines(state) == []


@pytest.mark.parametrize("make_dir", [False, True])
def test_the_gap_check_reports_no_stored_bar_when_the_directory_holds_no_month_file(
        tmp_path, tc, calendars, make_dir):
    state = tmp_path / "state"
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    for inst in tc.instruments[1:]:
        store.append(inst.symbol, frame(all_expected(tc, calendars, inst.symbol), inst.symbol),
                     LATE)
    if make_dir:
        store.month_path("SYNA", "x").parent.mkdir(parents=True)
    syna = next(i for i in tc.instruments if i.symbol == "SYNA")
    assert find_missing(store, syna, calendars[syna.calendar], tc.track.bar_seconds) == []
    report = check_gaps(state, tc, calendars, DAY, 0.02)
    assert report.missing["SYNA"] == ()


def test_the_gap_check_after_bars_fetch_completes_an_interrupted_first_append(
        tmp_path, tc, calendars, monkeypatch, capsys):
    config = _cli_config(tmp_path)
    as_of = "2019-07-13T00:00:00+00:00"
    state, clean = tmp_path / "state", tmp_path / "clean"
    # The first fetch crashes before any index write: SYNA's month files are
    # renamed into place, unlisted, and pass decision 5's test with r = 0.
    with monkeypatch.context() as m:
        def crash(self, index):
            raise OSError("simulated crash before the index write")
        m.setattr(BarStore, "_write_index", crash)
        assert _run(state, config, as_of, "fetch") == 1
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    assert list(store.month_path("SYNA", "x").parent.glob("*.parquet"))
    assert not store.index_path.exists()
    syna = next(i for i in tc.instruments if i.symbol == "SYNA")
    for call in (lambda: find_missing(store, syna, calendars[syna.calendar],
                                      tc.track.bar_seconds),
                 lambda: check_gaps(state, tc, calendars, DAY, 0.02)):
        with pytest.raises(BarStoreError, match="SYNA .*interrupted append") as err:
            call()
        assert "revised" not in str(err.value)

    capsys.readouterr()
    assert _run(state, config, as_of, "fetch") == 0
    assert "store_recovered" in capsys.readouterr().out
    assert _run(clean, config, as_of, "fetch") == 0
    assert gap_lines(state) == gap_lines(clean)
    got, want = (check_gaps(s, tc, calendars, DAY, 0.02) for s in (state, clean))
    assert got == want
    assert gap_lines(state) == gap_lines(clean)
