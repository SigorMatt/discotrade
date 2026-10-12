"""The evaluation loop and gross returns (DESIGN 6.2, 7.1, 7.2, 5.6; decisions
2026-10-12 22, 23, 24; R-20; I-2, I-12).

The stores are filled by ``bars fetch`` on the fixture track ``test_mixed``
(SYNA rolls quarterly on the ``synth_week`` calendar, SYNL does not roll,
SYNX is always open), with the clock given by ``--as-of``, or built by hand
for the hand-value cases. SYNA's continuous series is one gap-free
underlying plus a constant per contract (DESIGN 17.1), so the gross return
computed from the underlying is the one with no roll gap in it.
"""

import shutil
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade.backtest import (
    ROW_COLUMNS,
    SLICE_COLUMNS,
    MissingRollError,
    evaluate,
)
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange, load_calendar, load_track_config
from discotrade.rolls import Roll, adjust, read_rolls, roll_path
from discotrade.sources.synth import SynthSource
from discotrade.strategy import ResultError, Strategy
from discotrade.tradingcal import trading_date

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
HOUR = 3600
START = datetime(2019, 1, 7, tzinfo=UTC)
TWO_YEARS = "2021-01-07T00:00:00+00:00"
PRICES = ["open", "high", "low", "close"]
#: The spring clock change of America/New_York in 2019: 02:00 EST on 10 March.
SPRING = pd.Timestamp("2019-03-10 07:00", tz="UTC")


def strategy(fn, params=None):
    return Strategy(name="test", source="", params=dict(params or {}), grid=None, position=fn)


def recording(fn=None):
    """A strategy that keeps a copy of every frame it is given, then returns fn's value."""
    frames = []

    def position(bars, params):
        frames.append(bars.copy(deep=True))
        return 1.0 if fn is None else fn(bars, params)
    return strategy(position), frames


def window(first, last=None):
    return DateRange(first, first if last is None else last)


@pytest.fixture(scope="module")
def cfg():
    return load_track_config(FIXTURE_CONFIG, TRACK)


@pytest.fixture(scope="module")
def track(cfg):
    return cfg.track


@pytest.fixture(scope="module")
def instruments(cfg):
    return {i.symbol: i for i in cfg.instruments}


@pytest.fixture(scope="module")
def calendars():
    return {p.stem: load_calendar(p)
            for p in sorted((FIXTURE_CONFIG / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


def fetch(state, config, as_of):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "bars", "fetch"])


@pytest.fixture(scope="module")
def long_state(tmp_path_factory, config):
    state = tmp_path_factory.mktemp("long") / "state"
    assert fetch(state, config, TWO_YEARS) == 0
    return state


def run(state, track, instruments, calendars, symbol, strat, win):
    inst = instruments[symbol]
    return evaluate(state, track, inst, calendars[inst.calendar], strat, win)


def stored(state, symbol):
    return BarStore(state, TRACK, HOUR).read_range(symbol, START - timedelta(days=30),
                                                   datetime(2030, 1, 1, tzinfo=UTC))


# --- the slice (DESIGN 6.2) ------------------------------------------------------------


def test_the_slice_has_the_contract_columns_and_index_and_nothing_else(
        long_state, track, instruments, calendars):
    strat, frames = recording()
    run(long_state, track, instruments, calendars, "SYNA", strat,
        window(date(2019, 6, 3), date(2019, 6, 4)))
    assert len(frames) > 40
    for frame in frames:
        assert tuple(frame.columns) == SLICE_COLUMNS
        assert isinstance(frame.index, pd.RangeIndex)
        assert frame.index.start == 0 and frame.index.step == 1
        assert frame.index.name is None and frame.columns.name is None
        assert 1 <= len(frame) <= track.history_cap_bars
        assert frame.attrs == {}
        for col in PRICES + ["volume"]:
            assert frame[col].dtype == np.float64
        for col in ("hour", "weekday"):
            assert np.issubdtype(frame[col].dtype, np.integer)
        # No date and no symbol anywhere: every column is a plain number.
        assert not any(isinstance(v, str) for v in frame.to_numpy().ravel())
    assert len(frames[0]) == track.history_cap_bars


def test_slice_prices_are_the_adjusted_series_as_of_its_last_row_across_a_roll(
        long_state, track, instruments, calendars):
    bars = stored(long_state, "SYNA")
    rolls = read_rolls(roll_path(long_state, TRACK, "SYNA"))
    roll = rolls[2]
    roll_day = trading_date(calendars["synth_week"], roll.ts.to_pydatetime())
    strat, frames = recording()
    ev = run(long_state, track, instruments, calendars, "SYNA", strat,
             window(roll_day - timedelta(days=4), roll_day))
    assert (ev.rows["ts"] == roll.ts).any()
    assert ev.rows["contract"].nunique() == 2
    cap = track.history_cap_bars
    for frame, t in zip(frames, ev.rows["ts"], strict=True):
        want = adjust(bars, rolls, t).tail(cap).reset_index(drop=True)
        for col in PRICES + ["volume"]:
            assert np.array_equal(frame[col].to_numpy(), want[col].to_numpy()), (t, col)
    # Before the roll the slice is raw; from the roll bar on, its older rows carry the gap.
    k = int(np.flatnonzero((ev.rows["ts"] == roll.ts).to_numpy())[0])
    at, before = frames[k], frames[k - 1]
    assert np.allclose(at["close"].to_numpy()[:-1], before["close"].to_numpy()[1:] + roll.gap,
                       rtol=0, atol=1e-9)


def _local(ts, offset_hours):
    return (ts + pd.Timedelta(hours=offset_hours)).tz_convert(None)


def test_hour_and_weekday_are_in_the_calendars_zone_across_the_spring_change(
        long_state, track, instruments, calendars):
    cap = track.history_cap_bars
    for symbol in ("SYNA", "SYNX"):
        bars = stored(long_state, symbol)
        strat, frames = recording()
        ev = run(long_state, track, instruments, calendars, symbol, strat,
                 window(date(2019, 3, 11)))
        assert frames
        for frame, t in zip(frames, ev.rows["ts"], strict=True):
            ts = bars["ts"][bars["ts"] <= t].tail(cap).reset_index(drop=True)
            assert ts.iloc[0] < SPRING < ts.iloc[-1]
            if symbol == "SYNA":   # EST is UTC-5 before the change, EDT UTC-4 after
                offset = np.where(ts < SPRING, -5, -4)
            else:                  # always open: UTC
                offset = np.zeros(len(ts), dtype=int)
            local = [_local(x, o) for x, o in zip(ts, offset, strict=True)]
            assert frame["hour"].tolist() == [x.hour for x in local]
            assert frame["weekday"].tolist() == [x.weekday() for x in local]
    # A hand point on each side: Fri 8 March 14:00 UTC is 09:00 EST; Mon 11 March
    # 14:00 UTC is 10:00 EDT.
    assert (_local(pd.Timestamp("2019-03-08 14:00", tz="UTC"), -5).hour, 4) == (9, 4)


def test_every_call_gets_a_fresh_frame(long_state, track, instruments, calendars):
    win = window(date(2019, 6, 3), date(2019, 6, 4))

    def vandal(bars, params):
        bars["close"] *= 0.0
        bars.iloc[:, 0] = -1.0
        bars["extra"] = 1.0
        bars.drop(index=bars.index[:-1], inplace=True)
        bars.sort_values("hour", inplace=True)
        return 0.5

    plain, seen_plain = recording(lambda b, p: 0.5)
    mutating, seen_mutating = recording(vandal)
    a = run(long_state, track, instruments, calendars, "SYNA", plain, win)
    b = run(long_state, track, instruments, calendars, "SYNA", mutating, win)
    assert len(seen_plain) == len(seen_mutating) > 1
    for x, y in zip(seen_plain, seen_mutating, strict=True):
        pd.testing.assert_frame_equal(x, y, check_exact=True)
    pd.testing.assert_frame_equal(a.rows, b.rows, check_exact=True)


def test_params_are_passed_and_a_result_outside_the_contract_stops(
        long_state, track, instruments, calendars):
    seen = []

    def position(bars, params):
        seen.append(dict(params))
        return 2.0 if len(seen) == 3 else 0.0
    with pytest.raises(ResultError, match="SYNA"):
        run(long_state, track, instruments, calendars, "SYNA",
            strategy(position, {"lookback": 4}), window(date(2019, 6, 3)))
    assert seen == [{"lookback": 4}] * 3


# --- positions (DESIGN 7.1, R-20) --------------------------------------------------------


def test_h_is_the_previous_target_flat_at_the_first_bar_last_target_untraded(
        long_state, track, instruments, calendars):
    bars = stored(long_state, "SYNA")
    strat, frames = recording(lambda b, p: (int(b["hour"].iloc[-1]) % 5 - 2) / 2.0)
    win = window(date(2019, 6, 4), date(2019, 6, 6))
    ev = run(long_state, track, instruments, calendars, "SYNA", strat, win)
    rows = ev.rows
    assert tuple(rows.columns) == ROW_COLUMNS
    assert len(rows) == len(frames) > 40
    assert set(rows["date"]) == {date(2019, 6, 4), date(2019, 6, 5), date(2019, 6, 6)}
    p, h = rows["p"].to_numpy(), rows["h"].to_numpy()
    assert h[0] == 0.0
    assert np.array_equal(h[1:], p[:-1])
    assert np.array_equal(p, [(int(f["hour"].iloc[-1]) % 5 - 2) / 2.0 for f in frames])
    # The last target is recorded and is no row's position.
    assert p[-1] == (int(frames[-1]["hour"].iloc[-1]) % 5 - 2) / 2.0
    assert len(h) == len(p)
    # Context: the first slice is the cap's worth of stored bars ending at u0.
    u0 = rows["ts"].iloc[0]
    want = bars[bars["ts"] <= u0].tail(track.history_cap_bars).reset_index(drop=True)
    assert len(frames[0]) == track.history_cap_bars
    assert (want["ts"] < u0).sum() == track.history_cap_bars - 1
    assert np.array_equal(frames[0]["close"].to_numpy(), want["close"].to_numpy())


def test_h_u0_is_zero_whatever_was_returned_before_the_window(
        long_state, track, instruments, calendars):
    calls = []

    def always_long(bars, params):
        calls.append(len(bars))
        return 1.0
    win = window(date(2019, 6, 4), date(2019, 6, 5))
    ev = run(long_state, track, instruments, calendars, "SYNA", strategy(always_long), win)
    assert ev.rows["h"].iloc[0] == 0.0 and (ev.rows["h"].iloc[1:] == 1.0).all()
    assert (ev.rows["p"] == 1.0).all()
    assert ev.rows["gross"].iloc[0] == 0.0
    # The window right before it was long throughout; this one still starts flat.
    before = run(long_state, track, instruments, calendars, "SYNA", strategy(always_long),
                 window(date(2019, 6, 3)))
    assert before.rows["p"].iloc[-1] == 1.0
    # A window at the first stored bar has no context: its first slice has one row.
    calls.clear()
    run(long_state, track, instruments, calendars, "SYNA", strategy(always_long),
        window(date(2019, 1, 7)))
    assert calls[0] == 1


def test_window_membership_follows_each_instruments_own_calendar(
        long_state, track, instruments, calendars):
    win = window(date(2019, 3, 13))
    a = run(long_state, track, instruments, calendars, "SYNA", strategy(lambda b, p: 0.0), win)
    x = run(long_state, track, instruments, calendars, "SYNX", strategy(lambda b, p: 0.0), win)
    syna, synx = stored(long_state, "SYNA"), stored(long_state, "SYNX")
    # SYNA (America/New_York, day rolls at 17:00 EDT = 21:00 UTC) vs SYNX (UTC date).
    a_lo, a_hi = pd.Timestamp("2019-03-12 21:00", tz="UTC"), pd.Timestamp(
        "2019-03-13 21:00", tz="UTC")
    x_lo, x_hi = pd.Timestamp("2019-03-13", tz="UTC"), pd.Timestamp("2019-03-14", tz="UTC")
    want_a = syna["ts"][(syna["ts"] >= a_lo) & (syna["ts"] < a_hi)].tolist()
    want_x = synx["ts"][(synx["ts"] >= x_lo) & (synx["ts"] < x_hi)].tolist()
    assert a.rows["ts"].tolist() == want_a and len(want_a) >= 20
    assert x.rows["ts"].tolist() == want_x and len(want_x) >= 20
    assert set(a.rows["date"]) == set(x.rows["date"]) == {date(2019, 3, 13)}
    # 22:00 UTC on the 12th is in SYNA's window and not in SYNX's; 22:00 UTC on
    # the 13th the other way round.
    evening_12 = pd.Timestamp("2019-03-12 22:00", tz="UTC")
    evening_13 = pd.Timestamp("2019-03-13 22:00", tz="UTC")
    assert evening_12 in want_a and evening_12 in synx["ts"].tolist()
    assert evening_12 not in want_x
    assert evening_13 in want_x and evening_13 not in want_a


# --- gross returns on a hand-built store (DESIGN 7.2, decision 24) ------------------------


def _bar(ts, o, c, contract):
    return {"ts": pd.Timestamp(ts, tz="UTC"), "open": o, "high": max(o, c) + 1.0,
            "low": min(o, c) - 1.0, "close": c, "volume": 5.0, "contract": contract}


HAND = [
    _bar("2020-01-05 22:00", 97.0, 98.0, "A"),    # context
    _bar("2020-01-05 23:00", 98.0, 99.0, "A"),    # context
    _bar("2020-01-06 00:00", 100.0, 101.0, "A"),  # u0
    _bar("2020-01-06 01:00", 101.0, 102.0, "A"),
    _bar("2020-01-06 02:00", 102.0, 100.0, "A"),
    # 03:00 is missing
    _bar("2020-01-06 04:00", 112.0, 111.0, "B"),  # roll, gap 10
    _bar("2020-01-06 05:00", 110.0, 109.0, "B"),
]
TARGET_BY_CLOSE = {101.0: 1.0, 102.0: -0.5, 100.0: 0.5, 111.0: -1.0, 109.0: 0.25}


def _hand_store(state, roll=True):
    BarStore(state, TRACK, HOUR).append("SYNX", pd.DataFrame(HAND),
                                        datetime(2020, 1, 7, tzinfo=UTC))
    if roll:
        path = roll_path(state, TRACK, "SYNX")
        path.parent.mkdir(parents=True, exist_ok=True)
        r = Roll(ts=pd.Timestamp("2020-01-06 04:00", tz="UTC"), old="A", new="B", gap=10.0,
                 estimated=False, measured_at=pd.Timestamp("2020-01-06 02:00", tz="UTC"))
        path.write_text(r.to_json() + "\n", encoding="utf-8")


def test_gross_equals_hand_values_with_one_roll_and_one_missing_bar(
        tmp_path, track, instruments, calendars):
    _hand_store(tmp_path)
    strat, frames = recording(lambda b, p: TARGET_BY_CLOSE[float(b["close"].iloc[-1])])
    ev = run(tmp_path, track, instruments, calendars, "SYNX", strat, window(date(2020, 1, 6)))
    rows = ev.rows
    assert rows["ts"].dt.hour.tolist() == [0, 1, 2, 4, 5]
    assert rows["contract"].tolist() == ["A", "A", "A", "B", "B"]
    assert rows["p"].tolist() == [1.0, -0.5, 0.5, -1.0, 0.25]
    assert rows["h"].tolist() == [0.0, 1.0, -0.5, 0.5, -1.0]
    want = [0.0, 1 / 101, 1 / 102, -1.5 / 112, 0.5 / 110]
    assert np.allclose(rows["gross"].to_numpy(), want, rtol=0, atol=1e-15)
    # The slice at the roll bar: every earlier close carries the gap; the last is raw.
    assert frames[3]["close"].tolist() == [108.0, 109.0, 111.0, 112.0, 110.0, 111.0]
    assert frames[0]["close"].tolist() == [98.0, 99.0, 101.0]
    assert ev.first == 2 and ev.rolled.tolist() == [False] * 5 + [True, False]
    assert ev.gaps.tolist() == [0.0] * 5 + [10.0, 0.0]


def test_window_bars_start_at_trusted_from_and_earlier_bars_are_context(
        tmp_path, track, instruments, calendars):
    _hand_store(tmp_path)
    inst = replace(instruments["SYNX"], trusted_from=date(2020, 1, 6))
    strat, frames = recording()
    ev = evaluate(tmp_path, track, inst, calendars["always_open"], strat,
                  window(date(2020, 1, 5), date(2020, 1, 6)))
    assert ev.rows["ts"].iloc[0] == pd.Timestamp("2020-01-06 00:00", tz="UTC")
    assert len(frames[0]) == 3


def test_a_contract_change_with_no_roll_record_stops_the_evaluation(
        tmp_path, track, instruments, calendars):
    _hand_store(tmp_path, roll=False)
    with pytest.raises(MissingRollError, match="bars fetch") as err:
        run(tmp_path, track, instruments, calendars, "SYNX", strategy(lambda b, p: 1.0),
            window(date(2020, 1, 6)))
    assert "2020-01-06T04:00:00+00:00" in str(err.value) and "SYNX" in str(err.value)
    # A record for another bar is no record of this roll.
    path = roll_path(tmp_path, TRACK, "SYNX")
    path.parent.mkdir(parents=True, exist_ok=True)
    other = Roll(ts=pd.Timestamp("2020-01-06 05:00", tz="UTC"), old="A", new="B", gap=1.0,
                 estimated=True, measured_at=None)
    path.write_text(other.to_json() + "\n", encoding="utf-8")
    with pytest.raises(MissingRollError, match="bars fetch"):
        run(tmp_path, track, instruments, calendars, "SYNX", strategy(lambda b, p: 1.0),
            window(date(2020, 1, 6)))


# --- the roll gap is never profit or loss (DESIGN 5.6, 7.2) ------------------------------


@pytest.fixture(scope="module")
def underlying(calendars, instruments, long_state):
    rec = instruments["SYNA"]
    params = tuple((k, "none" if k == "roll_schedule" else v) for k, v in rec.source.params)
    flat = replace(rec, source=replace(rec.source, params=params))
    under = SynthSource(calendars, HOUR).fetch(flat, START, datetime(2021, 1, 7, tzinfo=UTC))
    assert np.array_equal(under["ts"].to_numpy(),
                          stored(long_state, "SYNA")["ts"].to_numpy())
    return under


@pytest.mark.parametrize("name", ["always_long", "alternating"])
def test_syna_gross_equals_the_gap_free_underlyings_across_every_roll(
        name, long_state, track, instruments, calendars, underlying):
    fns = {"always_long": lambda b, p: 1.0,
           "alternating": lambda b, p: 1.0 if int(b["hour"].iloc[-1]) % 2 else -1.0}
    ev = run(long_state, track, instruments, calendars, "SYNA", strategy(fns[name]),
             window(date(2019, 1, 7), date(2021, 1, 7)))
    rows = ev.rows
    assert np.array_equal(rows["ts"].to_numpy(), underlying["ts"].to_numpy())
    rolls = read_rolls(roll_path(long_state, TRACK, "SYNA"))
    assert len(rolls) == 8 and ev.rolled.sum() == 8
    assert set(r.ts for r in rolls) <= set(rows["ts"])
    h = rows["h"].to_numpy()
    if name == "alternating":
        assert (h[1:] == -1.0).any() and (h[1:] == 1.0).any()
    uo, uc = underlying["open"].to_numpy(), underlying["close"].to_numpy()
    raw_open = ev.bars["open"].to_numpy()[ev.first:]
    want = np.zeros(len(rows))
    want[1:] = (h[:-1] * (uo[1:] - uc[:-1]) + h[1:] * (uc[1:] - uo[1:])) / raw_open[1:]
    assert np.abs(rows["gross"].to_numpy() - want).max() <= 1e-12
    # At each roll bar, the raw gap would have been a visible jump.
    for r in rolls:
        assert abs(r.gap) > 1e-6


# --- truncation invariance (DESIGN 7.1, I-2) ----------------------------------------------


def whole_slice(bars, params):
    """Reads every row and every column of its slice."""
    close = bars["close"]
    x = (close.iloc[-1] - close.mean()) / (close.std(ddof=0) + 1e-9)
    x += (bars["high"] - bars["low"]).mean() / (close.abs().mean() + 1e-9)
    x += (bars["volume"].mean() - 1000.0) / 1000.0 + bars["open"].iloc[0] * 0.0
    x += 0.01 * bars["hour"].mean() - 0.01 * bars["weekday"].mean() + 0.001 * len(bars)
    return float(np.tanh(x))


@pytest.mark.parametrize("as_of", ["2019-06-20T15:00:00+00:00",
                                   "2019-09-16T13:00:00+00:00",
                                   "2019-12-16T09:00:00+00:00"])
def test_positions_up_to_t_do_not_depend_on_later_bars(
        as_of, tmp_path, config, long_state, track, instruments, calendars):
    assert fetch(tmp_path, config, as_of) == 0
    t = pd.Timestamp(as_of)
    assert pd.Timestamp(TWO_YEARS) - t >= pd.Timedelta(days=365)
    win = window(t.date() - timedelta(days=13), t.date())
    short_store = BarStore(tmp_path, TRACK, HOUR)
    for symbol in track.instruments:
        last = short_store.last_ts(symbol)
        assert last < t and BarStore(long_state, TRACK, HOUR).last_ts(symbol) > last
        a = run(tmp_path, track, instruments, calendars, symbol, strategy(whole_slice), win)
        b = run(long_state, track, instruments, calendars, symbol, strategy(whole_slice), win)
        assert a.rows["ts"].iloc[-1] == last and len(a.rows) > 100
        assert len(b.rows) >= len(a.rows)
        assert a.rows["p"].nunique() > 10
        head = b.rows[b.rows["ts"] <= last].reset_index(drop=True)
        pd.testing.assert_frame_equal(a.rows, head, check_exact=True)
