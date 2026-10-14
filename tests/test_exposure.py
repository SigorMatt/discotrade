"""Static exposure, unit return and the adjusted series (owner's decision O-4;
decision 2026-10-14 81; DESIGN 7.2, 8, 9.2, 9.3; decisions 2026-10-12 23, 24,
25, 39).

``run-day`` runs in-process on a pytest temporary state directory made by
``init-state``, on the fixture track ``test_mixed`` (SYNA rolls on 2019-06-14
and has no weekend bars, SYNL has none either, SYNX trades every day), for the
days ``DAYS`` (2019-06-12 to 2019-06-16), at ``--as-of`` ``AS_OF``. Two
approaches are admitted on ``ADMITTED``, so their first journal rows are on
2019-06-13: the reference ``trend_ma.py`` and the fixture ``roll_probe.py``
with both parameters 1.0, which holds a position of 1 on every instrument
from its second bar on. The controls are those the day draws (decision 64);
the random slot used is ``SLOT``.

The test's own computation (``own_*``) reads the journal parquet files, the
stored month bar files and the roll records of the state directory with
``pyarrow``, ``pandas`` and ``json`` only, and calls nothing in
``discotrade``: per bar, ``(1 * (O(u) - (C(u-1) + gap)) + 1 * (C(u) - O(u))) /
O(u)`` with ``u-1`` the previous stored bar and ``gap`` the recorded gap of a
roll at ``u`` (0 otherwise), the trading date of a bar being its journal
rows'; equality is decision 39's. The synthetic instruments' seeds are their
fixture records' (asserted); no other random draw is made.
"""

import functools
import itertools
import json
import math
import shutil
from datetime import date, timedelta

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from discotrade import journal, metrics, paper
from discotrade.cli import REPO_ROOT, main
from discotrade.state import write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-06-26T00:00:00+00:00"
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
DAYS = tuple(date(2019, 6, 12) + timedelta(days=k) for k in range(5))
ADMITTED = date(2019, 6, 12)
ROLL_DAY = date(2019, 6, 14)
WEEKEND = (date(2019, 6, 15), date(2019, 6, 16))
#: A window holding SYNA's roll and a weekend, and no subject's first journal row.
W = frozenset({ROLL_DAY, *WEEKEND})
#: Another window: it adds 2019-06-13, the approaches' first journaled day.
W2 = frozenset({date(2019, 6, 13), ROLL_DAY, *WEEKEND})
SLOT = "rc:1"
COLUMNS = ("gross", "net_1x", "net_2x")


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers."""
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("xcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


def admit(state, setup, path, params):
    strat = load_strategy_file(path, setup.thresholds)
    return write_approach(
        state, source=path.read_text(encoding="utf-8"),
        params=strat.params if params is None else params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description=f"the strategy {path.name}",
        profile_version="w-test", admitted=ADMITTED, instruments=setup.instruments,
        spread_tables=setup.spread_tables)


@pytest.fixture(scope="module")
def ran(tmp_path_factory, config, setup):
    state = tmp_path_factory.mktemp("xran") / "state"
    assert main(["init-state", "--state", str(state), "--as-of", AS_OF]) == 0
    trend = admit(state, setup, REPO_ROOT / "reference" / "trend_ma.py", None)
    const = admit(state, setup, REPO_ROOT / "tests" / "fixtures" / "strategies" / "roll_probe.py",
                  {"even": 1.0, "odd": 1.0})
    for d in DAYS:
        assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                     "--as-of", AS_OF, "run-day", "--day", d.isoformat()]) == 0
    return state, trend, const


# ------------------------------------------------------------- the test's own computation


@functools.cache
def own_journal(state) -> pd.DataFrame:
    files = sorted((state / "journal" / TRACK).rglob("*.parquet"))
    return pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True)


def own_bars(state, symbol) -> pd.DataFrame:
    files = sorted((state / "bars" / TRACK / symbol).glob("*.parquet"))
    bars = pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True)
    return bars.sort_values("ts").reset_index(drop=True)


def own_gaps(state, symbol) -> dict:
    path = state / "rolls" / TRACK / f"{symbol}.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[(pd.Timestamp(r["ts"]), r["old"], r["new"])] = float(r["gap"])
    return out


@functools.cache
def own_unit(state, symbol) -> dict:
    """Per bar ts: the unit return, from the stored bars and the roll records
    (cached per state directory, which no test changes)."""
    bars, gaps = own_bars(state, symbol), own_gaps(state, symbol)
    out = {}
    for k in range(len(bars)):
        o, c = float(bars["open"][k]), float(bars["close"][k])
        if k == 0:
            out[bars["ts"][k]] = (1.0 * (c - o)) / o
            continue
        gap = 0.0
        if bars["contract"][k] != bars["contract"][k - 1]:
            gap = gaps[(bars["ts"][k], bars["contract"][k - 1], bars["contract"][k])]
        prev = float(bars["close"][k - 1]) + gap
        out[bars["ts"][k]] = (1.0 * (o - prev) + 1.0 * (c - o)) / o
    return out


def own_day_units(state, rows, symbols, window) -> dict:
    """``R_i(D)`` per (symbol, date in ``window``), the bars' dates the journal's."""
    out = {}
    for s in symbols:
        unit = own_unit(state, s)
        mine = rows[(rows["instrument"] == s) & rows["date"].isin(window)]
        for (d, ts) in sorted(set(zip(mine["date"], mine["ts"], strict=True))):
            out[(s, d)] = out.get((s, d), 0.0) + unit[ts]
    return out


def own_hbar(rows, subject, symbols, window) -> dict:
    out = {}
    for s in symbols:
        mine = rows[(rows["subject"] == subject) & (rows["instrument"] == s)
                    & rows["date"].isin(window)]
        out[s] = float(mine["position"].mean()) if len(mine) else 0.0
    return out


def own_series(state, subject, window, column, n, symbols):
    """Per paper day of ``subject`` in ``window``: (plain, exposure, adjusted)."""
    rows = own_journal(state)
    units = own_day_units(state, rows, symbols, window)
    hbar = own_hbar(rows, subject, symbols, window)
    mine = rows[(rows["subject"] == subject) & rows["date"].isin(window)]
    out = {}
    for d in sorted(set(mine["date"])):
        plain = float(mine[mine["date"] == d][column].sum()) / n
        exposure = sum(hbar[s] * units.get((s, d), 0.0) for s in symbols) / n
        out[d] = (plain, exposure, plain - exposure)
    return out


# ------------------------------------------------------------------------- the tests


def test_seeds_are_the_fixture_records(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS


def test_the_window_holds_a_roll_and_a_weekend(ran):
    state, _, _ = ran
    rows = own_journal(state)
    syna = rows[(rows["instrument"] == "SYNA") & rows["date"].isin(W)]
    assert set(syna["date"]) == {ROLL_DAY}                     # no SYNA bar on the weekend
    assert syna["roll"].any()
    synx = rows[(rows["instrument"] == "SYNX") & rows["date"].isin(W)]
    assert set(synx["date"]) == set(W)                          # SYNX trades every day


def test_unit_returns_equal_the_journal_gross_of_buy_and_hold_rows_on_the_same_bars(ran, setup):
    state, _, _ = ran
    rows = own_journal(state)
    checked_roll = False
    for inst in setup.instruments:
        bh = rows[(rows["subject"] == f"bh:{inst.symbol}") & rows["date"].isin(W2)]
        assert (bh["prev_position"] == 1.0).all() and (bh["position"] == 1.0).all()
        unit = paper.unit_bars(state, setup, inst, W2)
        assert list(unit["ts"]) == list(bh["ts"])
        assert list(unit["date"]) == list(bh["date"])
        for u, g in zip(unit["unit"], bh["gross"], strict=True):
            assert eq(u, g)
        own = own_unit(state, inst.symbol)
        for ts, u in zip(unit["ts"], unit["unit"], strict=True):
            assert eq(u, own[ts]), (inst.symbol, ts)
        checked_roll |= bool(bh["roll"].any())
        # R_i(D) is the sum of the day's bars.
        for d, r in paper.unit_returns(state, setup, inst, W2).items():
            assert eq(r, float(unit["unit"][unit["date"] == d].sum()))
    assert checked_roll


def test_the_roll_gap_is_not_a_return(ran, setup):
    """At SYNA's roll bar the unit return is on prices adjusted as of the bar,
    which differs from the raw-price one by the gap."""
    state, _, _ = ran
    syna = next(i for i in setup.instruments if i.symbol == "SYNA")
    bars = own_bars(state, "SYNA")
    k = next(k for k in range(1, len(bars)) if bars["contract"][k] != bars["contract"][k - 1]
             and bars["ts"][k] >= pd.Timestamp("2019-06-01", tz="UTC"))
    unit = paper.unit_bars(state, setup, syna, {ROLL_DAY})
    got = float(unit["unit"][unit["ts"] == bars["ts"][k]].iloc[0])
    o, c, prev = float(bars["open"][k]), float(bars["close"][k]), float(bars["close"][k - 1])
    raw = (1.0 * (o - prev) + 1.0 * (c - o)) / o
    assert eq(got, own_unit(state, "SYNA")[bars["ts"][k]])
    assert not eq(got, raw)


def test_at_an_instruments_first_stored_bar_only_the_second_term_counts(ran, setup):
    state, _, _ = ran
    syna = next(i for i in setup.instruments if i.symbol == "SYNA")
    bars = own_bars(state, "SYNA")
    assert bars["ts"][0] == pd.Timestamp(syna.trusted_from.isoformat(), tz="UTC")
    unit = paper.unit_bars(state, setup, syna, {syna.trusted_from})
    assert unit["ts"].iloc[0] == bars["ts"][0]
    own = own_unit(state, "SYNA")
    for ts, u in zip(unit["ts"], unit["unit"], strict=True):
        assert eq(u, own[ts])
    o, c = float(bars["open"][0]), float(bars["close"][0])
    assert eq(unit["unit"].iloc[0], (c - o) / o)


def subjects(ran):
    _, trend, _ = ran
    return (trend, SLOT)


@pytest.mark.parametrize("window", [W, W2], ids=["W", "W2"])
def test_hbar_exposure_and_the_adjusted_series_equal_the_tests_own(ran, setup, window):
    state, _, _ = ran
    symbols = sorted(i.symbol for i in setup.instruments)
    n = len(symbols)
    rows = own_journal(state)
    for subject in subjects(ran):
        mine = rows[(rows["subject"] == subject) & rows["date"].isin(window)]
        assert paper.average_positions(mine, symbols) == pytest.approx(
            own_hbar(rows, subject, symbols, window), rel=1e-12, abs=1e-12)
        for column in COLUMNS:
            own = own_series(state, subject, window, column, n, symbols)
            got = paper.adjusted(state, setup, subject, window, column)
            assert list(got.index) == sorted(own) == sorted(window)
            for d, value in got.items():
                assert eq(value, own[d][2]), (subject, column, d)
                assert not eq(own[d][1], 0.0) or column != "gross", (subject, d)


def test_the_average_positions_change_with_w_and_the_function_uses_the_w_given(ran, setup):
    state, _, _ = ran
    symbols = sorted(i.symbol for i in setup.instruments)
    rows = own_journal(state)
    record = set(paper.read(state, TRACK)["date"])
    for subject in subjects(ran):
        h1 = own_hbar(rows, subject, symbols, W)
        h2 = own_hbar(rows, subject, symbols, W2)
        whole = own_hbar(rows, subject, symbols, record)
        assert any(not eq(h1[s], h2[s]) for s in symbols), subject
        assert any(not eq(h1[s], whole[s]) for s in symbols), subject
        got = paper.adjusted(state, setup, subject, W, "gross")
        with_w2 = own_series(state, subject, W2, "gross", len(symbols), symbols)
        # On a day both windows hold, the value follows the window's hbar.
        assert any(not eq(got[d], with_w2[d][2]) for d in W), subject


def windows_without(first):
    days = sorted(set(DAYS) - {first})
    for k in range(1, len(days) + 1):
        yield from (frozenset(c) for c in itertools.combinations(days, k))


def test_a_buy_and_hold_controls_gross_timing_return_is_zero(ran, setup):
    state, _, _ = ran
    rows = own_journal(state)
    for inst in setup.instruments:
        subject = f"bh:{inst.symbol}"
        first = min(rows[rows["subject"] == subject]["date"])
        assert first == DAYS[0]
        seen = 0
        for window in windows_without(first):
            got = paper.adjusted(state, setup, subject, window, "gross")
            for d, value in got.items():
                assert abs(value) <= 1e-12, (subject, sorted(window), d)
                seen += 1
        assert seen > 0
        # A window holding the first journaled row (position 0 at its first bar) does not.
        held = paper.adjusted(state, setup, subject, {first}, "gross")
        assert abs(held[first]) > 1e-12


def test_a_constant_position_has_an_adjusted_series_of_zeros_with_no_sharpe(ran, setup):
    state, _, const = ran
    rows = own_journal(state)
    mine = rows[(rows["subject"] == const) & rows["date"].isin(W)]
    assert (mine["prev_position"] == 1.0).all() and (mine["position"] == 1.0).all()
    timing = paper.adjusted(state, setup, const, W, "gross")
    assert list(timing.index) == sorted(W)
    assert (timing == 0.0).all()
    assert math.isnan(metrics.sharpe(timing))
    # Costs are not adjusted: off the roll day (no trade, no roll) the net is gross.
    for column in ("net_1x", "net_2x"):
        series = paper.adjusted(state, setup, const, set(WEEKEND), column)
        assert list(series.index) == list(WEEKEND)
        assert (series == 0.0).all()
        assert math.isnan(metrics.sharpe(series))
    on_roll = paper.adjusted(state, setup, const, W, "net_1x")[ROLL_DAY]
    roll_cost = float(mine[mine["date"] == ROLL_DAY]["roll_cost"].sum()) / len(setup.instruments)
    assert roll_cost > 0 and eq(on_roll, -roll_cost)


def test_net_minus_adjusted_equals_gross_minus_timing_on_every_day(ran, setup):
    state, trend, const = ran
    records = paper.read(state, TRACK)
    for subject in (trend, SLOT, const, "bh:SYNA", "bh:SYNX"):
        mine = records[records["subject"] == subject].set_index("date")
        timing = paper.adjusted(state, setup, subject, W, "gross")
        assert len(timing) > 0
        for column in ("net_1x", "net_2x"):
            adj = paper.adjusted(state, setup, subject, W, column)
            assert list(adj.index) == list(timing.index)
            for d in adj.index:
                assert eq(mine[column][d] - adj[d], mine["gross"][d] - timing[d])


def test_nothing_is_stored_for_it_but_the_records(ran):
    """Decision 2026-10-14 84 replaces decision 81 (d)'s simplest reading
    (nothing stored): the day's paper directory holds the paper file and the
    two derived exposure records, nothing else."""
    state, _, _ = ran
    assert sorted(p.name for p in (state / "paper" / TRACK).iterdir()) == sorted(
        [paper.FILE, paper.UNIT_FILE, paper.POSITIONS_FILE])


def test_a_column_that_is_not_a_paper_value_is_refused(ran, setup):
    state, _, _ = ran
    with pytest.raises(ValueError):
        paper.adjusted(state, setup, SLOT, W, "trades")


# ------------------------------------------ the derived exposure records (decision 84)
#
# The day stores, under paper/<track>/, ``R_i(D)`` per instrument and journaled
# date (0 on a date the instrument has no bar) and, per subject, instrument and
# date, the journal row count and summed position. The tests below compare them
# with the test's own computation above, run one more day (2019-06-17, a Monday)
# on copies of the state, and fetch bars past SYNA's next quarterly roll
# (2019-09-14) on another copy. No random draw is made beyond the day's own.

NEXT = date(2019, 6, 17)
#: A window holding the staged day, the roll and the weekend.
W_NEXT = frozenset({ROLL_DAY, *WEEKEND, NEXT})
LATER_AS_OF = "2019-09-20T00:00:00+00:00"


def records_paths(state):
    return (state / "paper" / TRACK / paper.UNIT_FILE,
            state / "paper" / TRACK / paper.POSITIONS_FILE)


def own_records(state):
    """``(unit, positions)`` of the state, each a dict keyed as the records are."""
    unit_path, positions_path = records_paths(state)
    unit = pq.read_table(unit_path).to_pandas()
    positions = pq.read_table(positions_path).to_pandas()
    return ({(r["instrument"], r["date"]): float(r["unit"]) for r in unit.to_dict("records")},
            {(r["subject"], r["instrument"], r["date"]): (int(r["rows"]), float(r["position"]))
             for r in positions.to_dict("records")})


def own_journaled(state):
    index = state / "journal" / TRACK / "index.jsonl"
    return sorted(date.fromisoformat(json.loads(line)["date"])
                  for line in index.read_text(encoding="utf-8").splitlines())


def assert_records_are_the_tests_own(state, setup):
    rows = own_journal(state)
    days = own_journaled(state)
    symbols = sorted(i.symbol for i in setup.instruments)
    unit, positions = own_records(state)
    units = own_day_units(state, rows, symbols, set(days))
    assert set(unit) == {(s, d) for s in symbols for d in days}
    for (s, d), value in unit.items():
        assert eq(value, units.get((s, d), 0.0)), (s, d)
    own = {}
    for (subject, symbol, d), mine in rows.groupby(["subject", "instrument", "date"]):
        own[(subject, symbol, d)] = (len(mine), float(mine["position"].sum()))
    assert set(positions) == set(own)
    for key, (n, total) in positions.items():
        assert n == own[key][0] and eq(total, own[key][1]), key


def test_the_stored_records_equal_the_tests_own_over_a_roll_and_a_weekend(ran, setup):
    state, _, _ = ran
    days = own_journaled(state)
    assert days == list(DAYS) and ROLL_DAY in days and set(WEEKEND) <= set(days)
    assert_records_are_the_tests_own(state, setup)
    unit, _ = own_records(state)
    assert unit[("SYNA", WEEKEND[0])] == 0.0 and unit[("SYNX", WEEKEND[0])] != 0.0


def test_hbar_is_the_summed_position_over_the_summed_rows_not_a_mean_of_daily_means():
    d1, d2, d3 = date(2019, 6, 13), date(2019, 6, 14), date(2019, 6, 15)
    positions = pd.DataFrame({
        "subject": ["s", "s", "s", "t"], "instrument": ["A", "A", "A", "A"],
        "date": [d1, d2, d3, d1], "rows": [3, 1, 2, 4],
        "position": [3.0, -1.0, 0.5, 4.0]})
    got = paper.hbar(positions, "s", ["A", "B"], {d1, d2})
    assert got == {"A": 2.0 / 4.0, "B": 0.0}       # mean of daily means would be 0.0
    assert paper.hbar(positions, "s", ["A"], {d1, d2, d3}) == {"A": 2.5 / 6.0}
    assert paper.hbar(positions, "s", ["A"], {date(2019, 6, 16)}) == {"A": 0.0}


@pytest.mark.parametrize("window", [W, W2], ids=["W", "W2"])
def test_adjusted_from_the_records_equals_the_on_call_computation(ran, setup, window,
                                                                 monkeypatch):
    """For an approach, a random slot and a buy-and-hold control: the value
    from the stored records equals the test's own on-call computation (the
    parent's), with the on-call functions made unusable."""
    state, trend, _ = ran
    symbols = sorted(i.symbol for i in setup.instruments)
    expected = {}
    for subject, n, mine in ((trend, len(symbols), symbols), (SLOT, len(symbols), symbols),
                             ("bh:SYNA", 1, ["SYNA"])):
        for column in COLUMNS:
            expected[(subject, column)] = own_series(state, subject, window, column, n, mine)

    def refused(*args, **kwargs):
        raise AssertionError("computed on call")

    for name in ("unit_bars", "unit_returns", "average_positions"):
        monkeypatch.setattr(paper, name, refused)
    monkeypatch.setattr(journal, "read_day", refused)
    for (subject, column), own in expected.items():
        got = paper.adjusted(state, setup, subject, window, column)
        assert list(got.index) == sorted(own)
        assert subject == "bh:SYNA" or sorted(own) == sorted(window)
        assert ROLL_DAY in own
        for d, value in got.items():
            assert abs(value - own[d][2]) <= 1e-12, (subject, column, d)


def test_a_stored_unit_return_equals_the_one_computed_after_a_later_roll(ran, config, setup,
                                                                        tmp_path):
    state, _, _ = ran
    later = tmp_path / "later"
    shutil.copytree(state, later)
    assert main(["--state", str(later), "--config", str(config), "--track",
                 TRACK, "--as-of", LATER_AS_OF, "bars", "fetch", "--day", "2019-09-19"]) == 0
    rolls = [json.loads(line) for line in
             (later / "rolls" / TRACK / "SYNA.jsonl").read_text(encoding="utf-8").splitlines()]
    after = [r for r in rolls if pd.Timestamp(r["ts"]) > pd.Timestamp("2019-06-17", tz="UTC")]
    assert after, "no later roll of SYNA"
    unit, _ = own_records(state)
    syna = next(i for i in setup.instruments if i.symbol == "SYNA")
    days = own_journaled(state)
    roll_day = pd.Timestamp(after[0]["ts"]).date()
    span = {*days, roll_day, roll_day + timedelta(days=3)}
    whole = paper.unit_returns(later, setup, syna, span)
    assert roll_day in whole or roll_day + timedelta(days=3) in whole
    for d in days:
        one = paper.unit_returns(later, setup, syna, {d}).get(d, 0.0)
        assert eq(unit[("SYNA", d)], one), d
        assert eq(unit[("SYNA", d)], whole.get(d, 0.0)), d


def test_a_rebuild_from_the_journal_and_the_bars_has_the_same_content_hash(ran, setup):
    from discotrade.state import content_hash

    state, _, _ = ran
    unit, positions = paper.rebuild_exposure(state, setup)
    unit_path, positions_path = records_paths(state)
    stored_unit = pq.read_table(unit_path).to_pandas()
    stored_positions = pq.read_table(positions_path).to_pandas()
    assert content_hash(unit, paper.UNIT_KEY) == content_hash(stored_unit, paper.UNIT_KEY)
    assert (content_hash(positions, paper.POSITIONS_KEY)
            == content_hash(stored_positions, paper.POSITIONS_KEY))


def run_next(state, config):
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "run-day", "--day", NEXT.isoformat()]) == 0


@pytest.fixture(scope="module")
def next_day(tmp_path_factory, ran, config, setup):
    """A copy of ``ran`` that runs 2019-06-17 and then again, recording the
    staged files each run moves and, inside the new day (from the lifecycle's
    call, as mission 11's readers are called), ``paper.adjusted`` on the staged
    records with ``overlay`` and without it."""
    from discotrade import daily, lifecycle

    state, trend, _ = ran
    copy = tmp_path_factory.mktemp("xnext") / "state"
    shutil.copytree(state, copy)
    moved, seen = [], {}
    original_move, original_steps = daily._move, lifecycle.run_steps

    def move(staging, state_dir):
        moved.append(sorted(p.relative_to(staging).as_posix()
                            for p in staging.rglob("*") if p.is_file()))
        return original_move(staging, state_dir)

    def steps(state_dir, setup_, day, records, failures, into=None):
        if not seen:
            for subject in (trend, SLOT):
                for column in COLUMNS:
                    seen[(subject, column)] = paper.adjusted(
                        state_dir, setup_, subject, W_NEXT, column, records=records,
                        overlay=into)
                try:
                    paper.adjusted(state_dir, setup_, subject, W_NEXT, "gross",
                                   records=records)
                except ValueError as exc:
                    seen[(subject, "without overlay")] = str(exc)
        return original_steps(state_dir, setup_, day, records, failures, into=into)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(daily, "_move", move)
        mp.setattr(lifecycle, "run_steps", steps)
        run_next(copy, config)
        before = [p.read_bytes() for p in records_paths(copy)]
        run_next(copy, config)
    after = [p.read_bytes() for p in records_paths(copy)]
    return copy, moved, seen, before, after


def test_the_records_are_staged_on_a_new_day_only_and_a_rerun_writes_nothing(next_day):
    _, moved, _, before, after = next_day
    names = {f"paper/{TRACK}/{paper.UNIT_FILE}", f"paper/{TRACK}/{paper.POSITIONS_FILE}"}
    assert len(moved) == 2
    assert names <= set(moved[0])
    assert not names & set(moved[1])
    assert before == after


def test_after_the_next_day_the_records_are_the_tests_own(next_day, setup):
    state, _, _, _, _ = next_day
    assert own_journaled(state)[-1] == NEXT
    assert_records_are_the_tests_own(state, setup)


def test_a_caller_passing_staged_records_and_overlay_reads_the_staged_days_rows(
        next_day, ran, setup):
    state, _, seen, _, _ = next_day
    _, trend, _ = ran
    symbols = sorted(i.symbol for i in setup.instruments)
    for subject in (trend, SLOT):
        assert "overlay" in seen[(subject, "without overlay")]
        for column in COLUMNS:
            own = own_series(state, subject, W_NEXT, column, len(symbols), symbols)
            got = seen[(subject, column)]
            assert list(got.index) == sorted(own) == sorted(W_NEXT)
            for d, value in got.items():
                assert abs(value - own[d][2]) <= 1e-12, (subject, column, d)


def _drop_day(path, day):
    frame = pq.read_table(path).to_pandas()
    pq.write_table(pa.Table.from_pandas(frame[frame["date"] != day], preserve_index=False,
                                        schema=pq.read_schema(path)), path)


def _add_day(path, day):
    frame = pq.read_table(path).to_pandas()
    extra = frame[frame["date"] == frame["date"].max()].copy()
    extra["date"] = day
    both = pd.concat([frame, extra], ignore_index=True)
    pq.write_table(pa.Table.from_pandas(both, preserve_index=False,
                                        schema=pq.read_schema(path)), path)


@pytest.mark.parametrize("damage", ["day removed", "day removed from positions",
                                    "extra date", "files removed"])
def test_the_next_day_heals_the_records(ran, config, setup, tmp_path, damage):
    """Decision 78's rule for the records: a journaled day missing from them, a
    date the journal index does not name, or no file, is healed by the next day."""
    from discotrade.state import content_hash

    state = tmp_path / "state"
    shutil.copytree(ran[0], state)
    unit_path, positions_path = records_paths(state)
    if damage == "day removed":
        _drop_day(unit_path, WEEKEND[1])
        _drop_day(positions_path, WEEKEND[1])
    elif damage == "day removed from positions":
        _drop_day(positions_path, WEEKEND[0])
    elif damage == "extra date":
        _add_day(unit_path, date(2019, 6, 11))
        _add_day(positions_path, date(2019, 6, 11))
    else:
        unit_path.unlink()
        positions_path.unlink()
    run_next(state, config)
    assert_records_are_the_tests_own(state, setup)
    unit, positions = paper.rebuild_exposure(state, setup)
    assert (content_hash(pq.read_table(unit_path).to_pandas(), paper.UNIT_KEY)
            == content_hash(unit, paper.UNIT_KEY))
    assert (content_hash(pq.read_table(positions_path).to_pandas(), paper.POSITIONS_KEY)
            == content_hash(positions, paper.POSITIONS_KEY))


def test_paper_no_longer_calls_the_private_journal_empty():
    text = (REPO_ROOT / "src" / "discotrade" / "paper.py").read_text(encoding="utf-8")
    assert "journal._empty" not in text


# ------------------------------------------- the lifecycle reads it (decisions 2026-10-14 85, 87)

#: ``lifecycle.dormant_window_days`` on a configuration copied under tmp, in
#: place of the production 30 (which tests/test_lifecycle.py uses): 30 paper
#: rows would need 30 more days of runs. 4 rows: 2019-06-14 to 2019-06-17.
LOW_WINDOW = 4


def test_run_day_step_2_reads_the_staged_adjusted_series_and_writes_both_figures(
        ran, config, setup, tmp_path):
    """A copy of ``ran`` runs 2019-06-17 at ``dormant_window_days`` 4: each
    approach (5 paper rows) goes dormant exactly when the test's own adjusted
    Sharpe at 1x over its last 4 paper days, from the journal parquet files and
    the stored bars, is negative, and its row carries that figure and the plain
    one (decision 39's equality). The staged day 2019-06-17 is in W: the
    exposure records it needs are only in the staging directory."""
    state, trend, const = ran
    copy = tmp_path / "state"
    shutil.copytree(state, copy)
    low = tmp_path / "config"
    shutil.copytree(config, low)
    text = (low / "thresholds.toml").read_text(encoding="utf-8")
    assert "dormant_window_days = 30 " in text
    (low / "thresholds.toml").write_text(
        text.replace("dormant_window_days = 30 ", f"dormant_window_days = {LOW_WINDOW}  "),
        encoding="utf-8")
    run_next(copy, low)
    window = frozenset({ROLL_DAY, *WEEKEND, NEXT})
    symbols = sorted(i.symbol for i in setup.instruments)
    expected = []
    for aid in sorted((trend, const)):
        days = sorted(set(own_journal(copy).query("subject == @aid")["date"]))
        assert len(days) == 5 and set(days[-LOW_WINDOW:]) == window
        own = own_series(copy, aid, window, "net_1x", len(symbols), symbols)
        adjusted = metrics.sharpe(pd.Series([own[d][2] for d in sorted(own)]))
        plain = metrics.sharpe(pd.Series([own[d][0] for d in sorted(own)]))
        if adjusted < 0:
            expected.append((aid, adjusted, plain))
    # One of them goes dormant on its adjusted Sharpe while its plain one is
    # positive: the plain measure would have kept it live.
    assert any(plain > 0 for _, _, plain in expected)
    rows = [r for r in json.loads("[" + ",".join(
        (copy / "ledger" / TRACK / "lifecycle.jsonl").read_text(encoding="utf-8").splitlines())
        + "]") if r["date"] == NEXT.isoformat()]
    assert [(r["id"], r["from"], r["to"], r["reason"]) for r in rows] == \
        [(aid, "live", "dormant", "dormant") for aid, _, _ in expected]
    for r, (_, adjusted, plain) in zip(rows, expected, strict=True):
        assert set(r) == {"date", "id", "from", "to", "reason", "adjusted", "plain"}
        assert eq(r["adjusted"], adjusted)
        assert (r["plain"] is None and math.isnan(plain)) or eq(r["plain"], plain)
