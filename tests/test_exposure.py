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


def test_nothing_is_stored_for_it(ran):
    """Decision 81 (d)'s simplest reading: the series is computed on call, so
    the day's paper directory holds the paper file only."""
    state, _, _ = ran
    assert sorted(p.name for p in (state / "paper" / TRACK).iterdir()) == [paper.FILE]


def test_a_column_that_is_not_a_paper_value_is_refused(ran, setup):
    state, _, _ = ran
    with pytest.raises(ValueError):
        paper.adjusted(state, setup, SLOT, W, "trades")
