"""The lifecycle: steps 1 to 4 and admission (DESIGN 10.3, 10.2, 9.1; decisions
2026-10-12 22, 48, 62, 63; I-5, I-6).

The setup is the fixture track ``test_mixed`` (``cell_slots`` 3; SYNX's
always-open calendar makes every calendar date a trading day of the track)
with the production ``config/thresholds.toml`` (``dormant_window_days`` 30,
``revival_min_dormant_days`` 5, ``retire_dormant_days`` 365,
``admission.min_trades_t`` 30, asserted). Approaches are written with
``state.write_approach`` into a pytest temporary directory and their paper
records are frames the test builds, so no bar is read, no strategy runs, no
random draw is made and no clock is read.
"""

import hashlib
import math
import shutil
from datetime import date, timedelta

import pandas as pd
import pytest

from discotrade import costs, journal, ledger, lifecycle, paper
from discotrade.cli import REPO_ROOT
from discotrade.lifecycle import Candidate
from discotrade.metrics import sharpe
from discotrade.state import read_approaches, write_approach

TRACK = "test_mixed"
CELL = "trend/short"
START = date(2019, 1, 1)
ADMITTED = START - timedelta(days=1)


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    path = tmp_path_factory.mktemp("lcfg") / "config"
    shutil.copytree(REPO_ROOT / "tests" / "fixtures" / "config", path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return journal.Setup.load(path, TRACK)


def test_the_production_values(setup):
    th = setup.thresholds
    assert th["lifecycle.dormant_window_days"] == 30
    assert th["lifecycle.revival_min_dormant_days"] == 5
    assert th["lifecycle.retire_dormant_days"] == 365
    assert th["admission.min_trades_t"] == 30
    assert setup.track.cell_slots == 3


def new(state, setup, k, cell=CELL, admitted=ADMITTED):
    return write_approach(
        state, source=f"# approach {k}\nPARAMS = {{}}\n", params={"k": k}, cell=cell,
        model_id="test-model", model_version="v0", cutoff=date(2018, 1, 1),
        description=f"approach {k}", profile_version="w-test", admitted=admitted,
        instruments=setup.instruments, spread_tables=setup.spread_tables)


def series(mean, n, amp=0.01):
    """``n`` daily values with the given mean and a deviation of ``amp``."""
    return [mean + (amp if k % 2 else -amp) for k in range(n)]


def frame(records):
    """Paper records from ``{subject: [(date, net_1x), ...]}``."""
    rows = [{"date": d, "subject": s, "kind": "approach", "gross": v, "net_1x": v,
             "net_2x": v, "trades": 1, "clean": True}
            for s, values in records.items() for d, v in values]
    return paper.build(pd.DataFrame(), 1, {}) if not rows else \
        pd.DataFrame(rows, columns=list(paper.COLUMNS))


def dated(values, first=START):
    return [(first + timedelta(days=k), v) for k, v in enumerate(values)]


def lifecycle_rows(state):
    return ledger.read(state, TRACK, ledger.LIFECYCLE)


def steps(state, setup, day, records, failures=None):
    return lifecycle.run_steps(state, setup, day, frame(records), failures or {})


def put(state, *rows):
    ledger.append(state, TRACK, ledger.LIFECYCLE, list(rows))


def row(day, aid, frm, to, reason):
    return {"date": day.isoformat(), "id": aid, "from": frm, "to": to, "reason": reason}


# ------------------------------------------------------------------ states


def test_the_state_is_the_last_rows_to_and_live_without_a_row(tmp_path, setup):
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    c = new(tmp_path, setup, 3, admitted=date(2019, 3, 1))
    d = date(2019, 2, 1)
    put(tmp_path, row(d, b, "live", "dormant", "dormant"))
    rows, apps = lifecycle_rows(tmp_path), read_approaches(tmp_path)
    on_d = lifecycle.states(rows, apps, d)
    assert on_d[a] == lifecycle.Status("live", ADMITTED)
    assert on_d[b].state == "live" and c not in on_d          # the change is not yet in force
    after = lifecycle.states(rows, apps, d + timedelta(days=1))
    assert after[b] == lifecycle.Status("dormant", d)
    assert lifecycle.journaled_ids(rows, apps, date(2019, 3, 2)) == sorted([a, b, c])
    put(tmp_path, row(d + timedelta(days=3), b, "dormant", "retired", "retired_dormant"))
    rows = lifecycle_rows(tmp_path)
    assert b in lifecycle.journaled_ids(rows, apps, d + timedelta(days=3))
    assert b not in lifecycle.journaled_ids(rows, apps, d + timedelta(days=4))


# ------------------------------------------------------------------ step 1


def test_step_1_retires_a_failure_with_its_error_text(tmp_path, setup):
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    d = START + timedelta(days=3)
    put(tmp_path, row(START, b, "live", "dormant", "dormant"))
    out = steps(tmp_path, setup, d, {}, {b: "position on SYNA at bar ts x returned 2.0",
                                         a: "boom"})
    assert out == [row(d, a, "live", "retired", "failure: boom"),
                   row(d, b, "dormant", "retired",
                       "failure: position on SYNA at bar ts x returned 2.0")]


# ------------------------------------------------------------------ step 2


def test_step_2_dormancy_at_dormant_window_days_and_not_before(tmp_path, setup):
    a = new(tmp_path, setup, 1)
    values = series(-0.002, 30)
    assert sharpe(pd.Series(values)) < 0 and sharpe(pd.Series(values[:29])) < 0
    day29 = START + timedelta(days=28)
    assert steps(tmp_path, setup, day29, {a: dated(values[:29])}) == []
    day30 = day29 + timedelta(days=1)
    # Rows after the day are not read.
    assert steps(tmp_path, setup, day29, {a: dated(values)}) == []
    assert steps(tmp_path, setup, day30, {a: dated(values)}) == \
        [row(day30, a, "live", "dormant", "dormant")]


def test_step_2_uses_the_last_window_only_and_not_a_positive_sharpe(tmp_path, setup):
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    good, bad = series(0.002, 30), series(-0.002, 30)
    day = START + timedelta(days=39)
    out = steps(tmp_path, setup, day, {a: dated(bad[:10] + good), b: dated(good[:10] + bad)})
    assert out == [row(day, b, "live", "dormant", "dormant")]


def test_step_2_a_sharpe_that_is_not_a_number_is_not_negative(tmp_path, setup):
    a = new(tmp_path, setup, 1)
    flat = [-0.002] * 30            # a deviation of 0: the Sharpe is not a number
    assert math.isnan(sharpe(pd.Series(flat)))
    assert steps(tmp_path, setup, START + timedelta(days=29), {a: dated(flat)}) == []


# ------------------------------------------------------------------ step 3


def test_step_3_returns_into_a_free_slot_not_before_revival_min_dormant_days(tmp_path, setup):
    a = new(tmp_path, setup, 1)
    since = START + timedelta(days=29)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    records = {a: dated(series(0.002, 40))}
    four = since + timedelta(days=4)            # 4 trading days after the dormant row
    assert steps(tmp_path, setup, four, records) == []
    five = since + timedelta(days=5)
    assert steps(tmp_path, setup, five, records) == [row(five, a, "dormant", "live", "returned")]


def test_step_3_a_dormant_approach_with_no_positive_sharpe_stays(tmp_path, setup):
    a = new(tmp_path, setup, 1)
    since = START + timedelta(days=29)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    day = since + timedelta(days=10)
    assert steps(tmp_path, setup, day, {a: dated(series(-0.002, 40))}) == []
    assert steps(tmp_path, setup, day, {a: dated([0.001] * 40)}) == []     # not a number


def full_cell(state, setup, means):
    """Three live approaches of ``CELL`` with paper means ``means`` (None: a
    Sharpe that is not a number) and one dormant approach; their ids and records."""
    live = [new(state, setup, 10 + k) for k in range(3)]
    other = new(state, setup, 20, cell="trend/medium")      # another cell takes no slot
    records = {aid: dated([0.001] * 40 if m is None else series(m, 40))
               for aid, m in zip(live, means, strict=True)}
    records[other] = dated(series(0.003, 40))
    return live, records


def test_step_3_returns_by_displacing_the_weakest(tmp_path, setup):
    live, records = full_cell(tmp_path, setup, [0.003, 0.0005, 0.002])
    a = new(tmp_path, setup, 1)
    since = START + timedelta(days=30)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    records[a] = dated(series(0.001, 40))
    day = since + timedelta(days=5)
    weak = live[1]
    assert steps(tmp_path, setup, day, records) == [
        row(day, a, "dormant", "live", "returned"),
        row(day, weak, "live", "dormant", "displaced")]


def test_step_3_stays_dormant_when_not_above_the_weakest(tmp_path, setup):
    live, records = full_cell(tmp_path, setup, [0.003, 0.002, 0.004])
    a = new(tmp_path, setup, 1)
    since = START + timedelta(days=30)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    records[a] = dated(series(0.001, 40))
    assert steps(tmp_path, setup, since + timedelta(days=5), records) == []


def test_step_3_sees_the_slot_step_2_freed(tmp_path, setup):
    live, records = full_cell(tmp_path, setup, [0.003, 0.003, 0.003])
    a = new(tmp_path, setup, 1)
    since = START + timedelta(days=30)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    records[a] = dated(series(0.0001, 40))
    records[live[2]] = dated(series(-0.002, 40))
    day = since + timedelta(days=5)
    assert steps(tmp_path, setup, day, records) == [
        row(day, live[2], "live", "dormant", "dormant"),
        row(day, a, "dormant", "live", "returned")]


# ------------------------------------------------------------------ step 4


def test_step_4_retires_after_retire_dormant_days_calendar_days(tmp_path, setup):
    a = new(tmp_path, setup, 1)
    since = START + timedelta(days=29)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    records = {a: dated(series(-0.002, 30))}
    assert steps(tmp_path, setup, since + timedelta(days=364), records) == []
    day = since + timedelta(days=365)
    assert steps(tmp_path, setup, day, records) == \
        [row(day, a, "dormant", "retired", "retired_dormant")]


# ------------------------------------------------------------------ the weakest, re-runs


def test_the_weakest_is_the_lowest_sharpe_not_a_number_lowest_ties_to_the_lowest_id():
    assert lifecycle.weakest({"a2": 0.5, "a1": 0.7, "a3": 0.6}) == "a2"
    assert lifecycle.weakest({"a1": -3.0, "a3": math.nan, "a2": 0.1}) == "a3"
    assert lifecycle.weakest({"a1": math.nan, "a3": math.nan, "a2": -1.0}) == "a1"
    assert lifecycle.weakest({"a3": 0.2, "a2": 0.2, "a4": 0.9}) == "a2"


def test_run_steps_again_for_the_same_day_appends_nothing(tmp_path, setup):
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    day = START + timedelta(days=29)
    records = {a: dated(series(-0.002, 30)), b: dated(series(0.002, 30))}
    first = steps(tmp_path, setup, day, records, {b: "boom"})
    assert [(r["id"], r["to"]) for r in first] == [(b, "retired"), (a, "dormant")]
    held = ledger.ledger_path(tmp_path, TRACK, ledger.LIFECYCLE).read_bytes()
    assert steps(tmp_path, setup, day, records, {b: "boom"}) == []
    assert ledger.ledger_path(tmp_path, TRACK, ledger.LIFECYCLE).read_bytes() == held


# ------------------------------------------------------------------ admission


T_DAYS = tuple(START + timedelta(days=k) for k in range(33, 40))
DAY = T_DAYS[-1]


def candidate(sharpe_t, trades, k=99, grid=None, metrics_w=None):
    return Candidate(
        source=f"# candidate {k}\nPARAMS = {{}}\n", params={"k": k}, cell=CELL,
        model_id="test-model", model_version="v0", cutoff=date(2018, 6, 1),
        description="a candidate", profile_version="w-test",
        metrics_t={"sharpe": sharpe_t, "trades": trades, "days": len(T_DAYS)},
        t_days=T_DAYS, grid=grid, metrics_w=metrics_w)


def trials(state):
    return ledger.read(state, TRACK, ledger.TRIALS)


def write_paper(state, records):
    paper.write(state, TRACK, frame(records))


def test_admission_into_a_free_slot_writes_the_trial_the_approach_and_one_row(tmp_path,
                                                                              setup):
    c = candidate(1.5, 30)
    done = lifecycle.admit(tmp_path, setup, c, DAY)
    assert (done.admitted, done.reason, done.displaced) == (True, "free_slot", None)
    [trial] = trials(tmp_path)
    assert set(trial) == set(ledger.KEYS[ledger.TRIALS])
    assert trial == {
        "date": DAY.isoformat(), "id": done.id, "cell": CELL, "model_id": "test-model",
        "model_version": "v0", "cutoff": "2018-06-01",
        "code_sha256": hashlib.sha256(c.source.encode("utf-8")).hexdigest(),
        "profile_version": "w-test", "cost_model": costs.VERSION,
        "config_hash": costs.config_hash(setup.instruments, setup.spread_tables),
        "grid": None, "params": {"k": 99}, "metrics_w": None,
        "metrics_t": {"sharpe": 1.5, "trades": 30, "days": 7},
        "admitted": True, "reason": "free_slot", "displaced": None}
    [held] = read_approaches(tmp_path)
    assert held.id == done.id and held.admitted == DAY
    assert lifecycle_rows(tmp_path) == [row(DAY, done.id, "candidate", "live", "admitted")]
    assert not (tmp_path / "trials").exists()


def test_a_trial_row_keeps_the_grid_and_w_metrics_it_carries(tmp_path, setup):
    grid = {"values": {"k": [1, 2]}, "results": [{"k": 1, "sharpe": 0.3}]}
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 30, grid=grid,
                                                      metrics_w={"sharpe": 0.9}), DAY)
    [trial] = trials(tmp_path)
    assert trial["grid"] == grid and trial["metrics_w"] == {"sharpe": 0.9}
    assert done.admitted


@pytest.mark.parametrize("score", [0.0, -0.4, math.nan])
def test_a_score_that_is_not_positive_is_refused_and_written_under_trials(tmp_path, setup,
                                                                          score):
    done = lifecycle.admit(tmp_path, setup, candidate(score, 300), DAY)
    assert (done.admitted, done.reason, done.displaced) == (False, "not_positive", None)
    [trial] = trials(tmp_path)
    assert trial["admitted"] is False and trial["reason"] == "not_positive"
    assert trial["metrics_t"]["sharpe"] == (None if math.isnan(score) else score)
    assert (tmp_path / "trials" / done.id / "strategy.py").read_text(encoding="utf-8") == \
        candidate(score, 300).source
    assert (tmp_path / "trials" / done.id / "meta.json").is_file()
    assert read_approaches(tmp_path) == [] and lifecycle_rows(tmp_path) == []


def test_too_few_trades_at_min_trades_t_is_refused(tmp_path, setup):
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 29), DAY)
    assert (done.admitted, done.reason) == (False, "too_few_trades")
    assert len(trials(tmp_path)) == 1 and lifecycle_rows(tmp_path) == []
    assert (tmp_path / "trials" / done.id).is_dir() and read_approaches(tmp_path) == []
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 30, k=98), DAY)
    assert (done.admitted, done.reason) == (True, "free_slot")


def on_t_values(mean):
    return series(mean, len(T_DAYS), amp=0.001)


def cell_on_t(state, setup, means):
    """Three live approaches of ``CELL`` with paper means ``means`` over T's
    days (None: a Sharpe that is not a number), and other days around them."""
    live = [new(state, setup, 10 + k) for k in range(3)]
    records = {}
    for aid, m in zip(live, means, strict=True):
        on_t = [0.001] * len(T_DAYS) if m is None else on_t_values(m)
        records[aid] = dated(series(0.01, 33) + on_t)        # strong before T
    write_paper(state, records)
    return live


def test_admission_displacing_the_weakest_makes_it_dormant(tmp_path, setup):
    live = cell_on_t(tmp_path, setup, [0.002, 0.0005, 0.003])
    weak = live[1]
    low, next_up = sharpe(pd.Series(on_t_values(0.0005))), sharpe(pd.Series(on_t_values(0.002)))
    assert 0 < low < next_up
    score = (low + next_up) / 2
    done = lifecycle.admit(tmp_path, setup, candidate(score, 30), DAY)
    assert (done.admitted, done.reason, done.displaced) == (True, "displaced", weak)
    [trial] = trials(tmp_path)
    assert trial["displaced"] == weak and trial["reason"] == "displaced"
    assert lifecycle_rows(tmp_path) == [row(DAY, done.id, "candidate", "live", "admitted"),
                                        row(DAY, weak, "live", "dormant", "displaced")]
    assert done.id in {a.id for a in read_approaches(tmp_path)}


def test_admission_refused_when_not_better_than_the_weakest(tmp_path, setup):
    cell_on_t(tmp_path, setup, [0.002, 0.0005, 0.003])
    score = sharpe(pd.Series(on_t_values(0.0005)))     # equal is not above
    assert score > 0
    done = lifecycle.admit(tmp_path, setup, candidate(score, 30), DAY)
    assert (done.admitted, done.reason, done.displaced) == \
        (False, "not_better_than_weakest", None)
    assert len(trials(tmp_path)) == 1 and lifecycle_rows(tmp_path) == []
    assert (tmp_path / "trials" / done.id).is_dir()
    assert done.id not in {a.id for a in read_approaches(tmp_path)}


def test_admission_displaces_a_sharpe_that_is_not_a_number_and_ties_to_the_lowest_id(
        tmp_path, setup):
    live = cell_on_t(tmp_path, setup, [0.0001, None, 0.0001])
    done = lifecycle.admit(tmp_path, setup, candidate(0.01, 30), DAY)
    assert done.displaced == live[1]
    other = tmp_path / "ties"
    live = cell_on_t(other, setup, [0.003, 0.0005, 0.0005])
    done = lifecycle.admit(other, setup, candidate(1000.0, 30), DAY)
    assert done.displaced == min(live[1], live[2])


def test_admission_counts_the_states_after_the_days_steps(tmp_path, setup):
    # A live approach made dormant on DAY frees its slot for the candidate of DAY.
    live = cell_on_t(tmp_path, setup, [0.002, 0.0005, 0.003])
    put(tmp_path, row(DAY, live[0], "live", "dormant", "dormant"))
    done = lifecycle.admit(tmp_path, setup, candidate(0.01, 30), DAY)
    assert (done.reason, done.displaced) == ("free_slot", None)
