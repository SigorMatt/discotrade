"""The lifecycle: steps 1 to 4 and admission (DESIGN 10.3, 10.2, 9.1; decisions
2026-10-12 22, 48, 62, 63, 66, 68; I-5, I-6).

The setup is the fixture track ``test_mixed`` (``cell_slots`` 3; SYNX's
always-open calendar makes every calendar date a trading day of the track)
with the production ``config/thresholds.toml`` (``dormant_window_days`` 30,
``revival_min_dormant_days`` 5, ``retire_dormant_days`` 365,
``admission.min_trades_t`` 30, asserted). The wait of step 3 in trading days
(decision 66) is shown on the fixture track ``test_synth``, whose calendar
``synth_week`` has weekends. Approaches are written with
``state.write_approach`` into a pytest temporary directory and their paper
records are frames the test builds, so no bar is read, no strategy runs, no
random draw is made and no clock is read.

Steps 2 and 3 read the adjusted Sharpe (owner's O-11, O-12; decision
2026-10-14 85) through ``paper.adjusted``, which reads the derived exposure
records (decision 84): ``steps`` writes them by hand with ``paper.write_exposure``
under the test's tmp directory, ``R_i(D)`` 0 and no position unless a test
gives them, so that the adjusted series is the plain one there. Where a test
gives them, its expected adjusted series is the test's own: per paper day,
``net_1x`` minus the sum over the track's three instruments of ``hbar_i(W) *
R_i(D)`` over 3, ``hbar_i(W)`` the summed position over the row count of the
approach's position records dated in ``W`` (decisions 81 (c), 84), computed
from the frames the test writes without ``paper.adjusted``, ``paper.hbar`` or
``paper.average_positions``. The rows of ``dormant``, ``returned`` and
``displaced`` carry ``adjusted`` and ``plain`` (decision 87). Admission reads
the candidate's ``adjusted_t["sharpe"]`` and scores a full cell's live
approaches over T's days on their adjusted series (decision 86); its
``admitted`` rows carry the two figures too.
"""

import dataclasses
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
from discotrade.state import approach_id, read_approaches, write_approach
from discotrade.stats import trading_dates

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


def exposure(state, setup, records, units=None, positions=None):
    """The derived exposure records of ``records``' dates, written by hand:
    ``units`` maps (symbol, date) to ``R_i(D)`` (0 where absent), ``positions``
    maps (subject, symbol, date) to the summed position of one journal row."""
    units, positions = units or {}, positions or {}
    days = sorted({d for values in records.values() for d, _ in values})
    symbols = sorted(i.symbol for i in setup.instruments)
    unit = pd.DataFrame([{"instrument": s, "date": d, "unit": float(units.get((s, d), 0.0))}
                         for s in symbols for d in days],
                        columns=["instrument", "date", "unit"])
    held = pd.DataFrame([{"subject": a, "instrument": s, "date": d, "rows": 1,
                          "position": float(p)}
                         for (a, s, d), p in sorted(positions.items())],
                        columns=["subject", "instrument", "date", "rows", "position"])
    paper.write_exposure(state, setup.track.name, unit, held)


def steps(state, setup, day, records, failures=None, units=None, positions=None):
    exposure(state, setup, records, units, positions)
    return lifecycle.run_steps(state, setup, day, frame(records), failures or {})


def put(state, *rows, track=TRACK):
    """Seed the ledger with ``rows``; a row of one of decision 87's four
    reasons given without its figures is written with both ``null``, as
    decision 2026-10-14 93 requires them on append."""
    ledger.append(state, track, ledger.LIFECYCLE, [seeded(r) for r in rows])


def seeded(r):
    if r["reason"] in ledger.FIGURE_REASONS and not set(ledger.FIGURES) & set(r):
        return {**r, "adjusted": None, "plain": None}
    return r


def row(day, aid, frm, to, reason, adjusted=None, plain=None):
    """A lifecycle row; a ``dormant``, ``returned`` or ``displaced`` row with
    its two figures (decision 87) when ``adjusted`` or ``plain`` is given as a
    series (its Sharpe, ``None`` when not a number)."""
    out = {"date": day.isoformat(), "id": aid, "from": frm, "to": to, "reason": reason}
    if adjusted is not None or plain is not None:
        out["adjusted"], out["plain"] = fig(adjusted), fig(plain)
    return out


def fig(values):
    """The Sharpe of ``values`` as a lifecycle row holds it: ``None`` when not
    a number (decision 87)."""
    value = sharpe(pd.Series(list(values), dtype="float64"))
    return None if math.isnan(value) else value


def same(values):
    """Decision 87's two figures where the adjusted series is the plain one
    (no exposure written)."""
    return {"adjusted": values, "plain": values}


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
        [row(day30, a, "live", "dormant", "dormant", **same(values))]


def test_step_2_uses_the_last_window_only_and_not_a_positive_sharpe(tmp_path, setup):
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    good, bad = series(0.002, 30), series(-0.002, 30)
    day = START + timedelta(days=39)
    out = steps(tmp_path, setup, day, {a: dated(bad[:10] + good), b: dated(good[:10] + bad)})
    assert out == [row(day, b, "live", "dormant", "dormant", **same(bad))]


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
    window = series(0.002, 40)[5:35]            # the last 30 rows up to ``five``
    assert steps(tmp_path, setup, five, records) == \
        [row(five, a, "dormant", "live", "returned", **same(window))]


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    """The fixture track ``test_synth`` (its instruments all on ``synth_week``,
    which has weekends) with the production thresholds."""
    path = tmp_path_factory.mktemp("lcfg_synth") / "config"
    shutil.copytree(REPO_ROOT / "tests" / "fixtures" / "config", path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return journal.Setup.load(path, "test_synth")


def test_step_3_waits_revival_min_dormant_days_trading_days_not_calendar_days(tmp_path,
                                                                              synth):
    # Decision 66: the wait counts trading days of the track after the dormant row.
    assert synth.thresholds["lifecycle.revival_min_dormant_days"] == 5
    assert sorted(synth.calendars) == ["synth_week"]
    a = new(tmp_path, synth, 1)
    since = date(2019, 6, 6)                    # a Thursday
    put(tmp_path, row(since, a, "live", "dormant", "dormant"), track="test_synth")
    records = {a: dated(series(0.002, 40), first=date(2019, 4, 28))}
    calendars = [synth.calendars[n] for n in sorted(synth.calendars)]

    def waited(day):
        return len(trading_dates(calendars, synth.track.bar_seconds,
                                 since + timedelta(days=1), day))

    for day in (date(2019, 6, 11), date(2019, 6, 12)):     # Tuesday, Wednesday
        assert (day - since).days >= 5 and waited(day) < 5
        assert steps(tmp_path, synth, day, records) == []
    fifth = date(2019, 6, 13)                   # Fri, Mon, Tue, Wed, Thu
    assert waited(fifth) == 5
    window = series(0.002, 40)[10:]             # the last 30 rows (to 2019-06-06)
    assert steps(tmp_path, synth, fifth, records) == \
        [row(fifth, a, "dormant", "live", "returned", **same(window))]
    assert ledger.read(tmp_path, "test_synth", ledger.LIFECYCLE)[-1] == \
        row(fifth, a, "dormant", "live", "returned", **same(window))


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
        row(day, a, "dormant", "live", "returned", **same(series(0.001, 40)[6:36])),
        row(day, weak, "live", "dormant", "displaced", **same(series(0.0005, 40)[6:36]))]


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
        row(day, live[2], "live", "dormant", "dormant", **same(series(-0.002, 40)[6:36])),
        row(day, a, "dormant", "live", "returned", **same(series(0.0001, 40)[6:36]))]


def test_returned_and_displaced_on_one_day_both_rows_stand_and_dormancy_counts_from_the_second(
        tmp_path, setup):
    # Decision 68 (b): an approach that returns on D (step 3) and is displaced
    # later on D by another approach's return has both rows dated D, in the order
    # taken, and a later count of its dormancy starts from the second row.
    held = [new(tmp_path, setup, 10 + k) for k in range(2)]      # two live: a free slot
    first, second = sorted([new(tmp_path, setup, 1), new(tmp_path, setup, 2)])
    since = START + timedelta(days=20)
    put(tmp_path, row(since, first, "live", "dormant", "dormant"),
        row(since, second, "live", "dormant", "dormant"))
    records = {held[0]: dated(series(0.003, 50)), held[1]: dated(series(0.003, 50)),
               first: dated(series(0.0005, 50)), second: dated(series(0.002, 50))}
    d = START + timedelta(days=35)
    low, high = series(0.0005, 50)[6:36], series(0.002, 50)[6:36]
    taken = [row(d, first, "dormant", "live", "returned", **same(low)),
             row(d, second, "dormant", "live", "returned", **same(high)),
             row(d, first, "live", "dormant", "displaced", **same(low))]
    assert steps(tmp_path, setup, d, records) == taken
    assert lifecycle_rows(tmp_path)[-3:] == taken
    apps = read_approaches(tmp_path)
    assert lifecycle.states(lifecycle_rows(tmp_path), apps, d + timedelta(days=1))[first] == \
        lifecycle.Status("dormant", d)
    # A failure frees a slot; ``first`` has waited 9 trading days since its first
    # row to dormant but 4 since D, so it stays.
    four = d + timedelta(days=4)
    assert steps(tmp_path, setup, four, records, {held[0]: "boom"}) == \
        [row(four, held[0], "live", "retired", "failure: boom")]
    five = d + timedelta(days=5)
    assert steps(tmp_path, setup, five, records) == \
        [row(five, first, "dormant", "live", "returned", **same(series(0.0005, 50)[11:41]))]


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


# ------------------------------------------------------------------ the adjusted measure
# Owner's O-11, O-12; decisions 2026-10-14 85, 87. Production thresholds
# (dormant_window_days 30, asserted in test_the_production_values).

SYMBOLS = ("SYNA", "SYNL", "SYNX")
BASE_KEYS = {"date", "id", "from", "to", "reason"}


def test_the_track_has_three_instruments(setup):
    assert sorted(i.symbol for i in setup.instruments) == list(SYMBOLS)


def own(records, positions, units, aid, window):
    """``aid``'s adjusted ``net_1x`` on its paper days in ``window``, the test's
    own computation from the frames it writes: ``net_1x`` minus the sum over
    the three instruments, in symbol order, of ``hbar_i(W) * R_i(D)`` over 3,
    ``hbar_i(W)`` the summed position over the row count in ``W``, 0 with no
    row."""
    days = set(window)
    hbar = {}
    for s in SYMBOLS:
        mine = [p for (a, sym, d), p in sorted(positions.items())
                if a == aid and sym == s and d in days]
        hbar[s] = sum(mine) / len(mine) if mine else 0.0
    out = []
    for d, v in records[aid]:
        if d in days:
            total = 0.0
            for s in SYMBOLS:
                total = total + hbar[s] * units.get((s, d), 0.0)
            out.append(v - total / 3)
    return out


def plain(records, aid, window):
    days = set(window)
    return [v for d, v in records[aid] if d in days]


def dates_of(records, aid):
    return [d for d, _ in records[aid]]


def held(aid, symbol, dates, position):
    return {(aid, symbol, d): position for d in dates}


def priced(symbol, dates, values):
    values = [values] * len(dates) if isinstance(values, float) else values
    return {(symbol, d): v for d, v in zip(dates, values, strict=True)}


def test_step_2_dormant_on_a_negative_adjusted_sharpe_whose_plain_is_positive(tmp_path, setup):
    a = new(tmp_path, setup, 1)
    records = {a: dated(series(0.002, 30))}
    dates = dates_of(records, a)
    units, positions = priced("SYNX", dates, 0.012), held(a, "SYNX", dates, 1.0)
    adj = own(records, positions, units, a, dates)
    assert fig(plain(records, a, dates)) > 0 > fig(adj)
    day = dates[-1]
    assert steps(tmp_path, setup, day, records, units=units, positions=positions) == \
        [row(day, a, "live", "dormant", "dormant", adj, plain(records, a, dates))]


def test_step_2_stays_live_on_an_adjusted_sharpe_that_is_not_negative_whose_plain_is(
        tmp_path, setup):
    a = new(tmp_path, setup, 1)
    records = {a: dated(series(-0.002, 30))}
    dates = dates_of(records, a)
    units, positions = priced("SYNX", dates, -0.012), held(a, "SYNX", dates, 1.0)
    assert fig(plain(records, a, dates)) < 0 < fig(own(records, positions, units, a, dates))
    assert steps(tmp_path, setup, dates[-1], records, units=units, positions=positions) == []


def test_step_2_reads_the_last_window_rows_not_the_whole_paper_record(tmp_path, setup):
    # W is the dates of the last 30 paper rows: the average position is taken
    # over them, not over the 40 rows of the record.
    a = new(tmp_path, setup, 1)
    records = {a: dated(series(0.002, 40))}
    dates = dates_of(records, a)
    units = priced("SYNX", dates, 0.012)
    positions = {**held(a, "SYNX", dates[:10], 3.0), **held(a, "SYNX", dates[10:], 0.0)}
    assert fig(own(records, positions, units, a, dates[10:])) > 0
    assert fig(own(records, positions, units, a, dates)) < 0       # over the whole record
    assert steps(tmp_path, setup, dates[-1], records, units=units, positions=positions) == []


def constant_units(dates):
    """``R_i(D)`` of the three instruments, each with a negative mean."""
    out = {}
    for j, s in enumerate(SYMBOLS):
        values = [-0.003 + 0.001 * j + (0.01 if k % 2 else -0.01) for k in range(len(dates))]
        out.update(priced(s, dates, values))
    return out


def test_one_constant_position_neither_goes_dormant_nor_returns(tmp_path, setup):
    # O-11: a subject holding one constant position has an adjusted series of
    # zeros (no costs here), hence no Sharpe: not negative, not positive.
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    days = [START + timedelta(days=k) for k in range(40)]
    units = constant_units(days)
    positions = {}
    records = {}
    for aid, h in ((a, 1.0), (b, -1.0)):           # a long throughout, b short throughout
        values = []
        for d in days:
            total = 0.0
            for s in SYMBOLS:
                total = total + h * units[(s, d)]
            values.append(total / 3)
        records[aid] = list(zip(days, values, strict=True))
        for s in SYMBOLS:
            positions.update(held(aid, s, days, h))
    since = START + timedelta(days=20)
    put(tmp_path, row(since, b, "live", "dormant", "dormant"))
    day = days[-1]
    w = days[-30:]
    for aid in (a, b):
        assert own(records, positions, units, aid, w) == [0.0] * 30
        assert fig(own(records, positions, units, aid, w)) is None
    assert fig(plain(records, a, w)) < 0 < fig(plain(records, b, w))
    assert steps(tmp_path, setup, day, records, units=units, positions=positions) == []


def test_step_3_returns_on_a_positive_adjusted_sharpe_and_not_on_a_positive_plain_one(
        tmp_path, setup):
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    since = START + timedelta(days=30)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"),
        row(since, b, "live", "dormant", "dormant"))
    records = {a: dated(series(-0.002, 40)), b: dated(series(0.002, 40))}
    days = dates_of(records, a)
    units = {**priced("SYNX", days, -0.012), **priced("SYNL", days, 0.012)}
    positions = {**held(a, "SYNX", days, 1.0), **held(b, "SYNL", days, 1.0)}
    day = since + timedelta(days=5)
    w = days[6:36]                                  # the last 30 rows up to ``day``
    assert fig(plain(records, a, w)) < 0 < fig(own(records, positions, units, a, w))
    assert fig(own(records, positions, units, b, w)) < 0 < fig(plain(records, b, w))
    assert steps(tmp_path, setup, day, records, units=units, positions=positions) == [
        row(day, a, "dormant", "live", "returned", own(records, positions, units, a, w),
            plain(records, a, w))]


def test_step_3_displaces_the_lowest_adjusted_sharpe_each_on_its_own_positions(
        tmp_path, setup):
    # O-12: each live approach is scored over the returning approach's W on its
    # own adjusted series with its own average positions. The plain measure
    # names live[0] (the lowest plain mean); the adjusted one live[1].
    live = [new(tmp_path, setup, 10 + k) for k in range(3)]
    other = new(tmp_path, setup, 20, cell="trend/medium")
    a = new(tmp_path, setup, 1)
    since = START + timedelta(days=30)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    records = {live[0]: dated(series(0.0005, 40)), live[1]: dated(series(0.002, 40)),
               live[2]: dated(series(0.003, 40)), other: dated(series(0.003, 40)),
               a: dated(series(0.003, 40))}
    days = dates_of(records, a)
    units = priced("SYNX", days, 0.0048)
    positions = held(live[1], "SYNX", days, 1.0)
    day = since + timedelta(days=5)
    w = days[6:36]
    adjusted = {aid: fig(own(records, positions, units, aid, w)) for aid in live}
    plains = {aid: fig(plain(records, aid, w)) for aid in live}
    assert min(plains, key=plains.get) == live[0]
    # live[1]'s adjusted Sharpe is positive (step 2 keeps it live) and the lowest.
    assert min(adjusted, key=adjusted.get) == live[1] and adjusted[live[1]] > 0
    assert steps(tmp_path, setup, day, records, units=units, positions=positions) == [
        row(day, a, "dormant", "live", "returned", plain(records, a, w), plain(records, a, w)),
        row(day, live[1], "live", "dormant", "displaced",
            own(records, positions, units, live[1], w), plain(records, live[1], w))]


def test_a_figure_that_is_not_a_number_is_written_null(tmp_path, setup):
    # Decision 87: a dormant row whose plain Sharpe is not a number (a constant
    # plain series), and a displaced row whose adjusted Sharpe is not a number
    # (one constant position, no costs: the weakest, as a Sharpe that is not a
    # number counts the lowest).
    a = new(tmp_path, setup, 1)
    records = {a: dated([0.001] * 30)}
    dates = dates_of(records, a)
    units = priced("SYNX", dates, series(0.012, 30, amp=0.03))
    positions = held(a, "SYNX", dates, 1.0)
    adj = own(records, positions, units, a, dates)
    assert fig(adj) < 0 and fig(plain(records, a, dates)) is None
    day = dates[-1]
    assert steps(tmp_path, setup, day, records, units=units, positions=positions) == \
        [row(day, a, "live", "dormant", "dormant", adj, [0.001] * 30)]
    line = ledger.ledger_path(tmp_path, TRACK, ledger.LIFECYCLE).read_text().splitlines()[-1]
    assert '"plain":null' in line and f'"adjusted":{fig(adj)!r}' in line

    state = tmp_path / "displaced"
    live = [new(state, setup, 10 + k) for k in range(3)]
    b = new(state, setup, 2)
    since = START + timedelta(days=30)
    put(state, row(since, b, "live", "dormant", "dormant"))
    days = [START + timedelta(days=k) for k in range(40)]
    units = constant_units(days)
    flat = []
    for d in days:
        total = 0.0
        for s in SYMBOLS:
            total = total + 1.0 * units[(s, d)]
        flat.append(total / 3)
    records = {live[0]: dated(series(0.002, 40)), live[1]: list(zip(days, flat, strict=True)),
               live[2]: dated(series(0.003, 40)), b: dated(series(0.003, 40))}
    positions = {}
    for s in SYMBOLS:
        positions.update(held(live[1], s, days, 1.0))
    day = since + timedelta(days=5)
    w = days[6:36]
    assert fig(own(records, positions, units, live[1], w)) is None
    assert fig(plain(records, live[1], w)) is not None
    assert steps(state, setup, day, records, units=units, positions=positions) == [
        row(day, b, "dormant", "live", "returned", plain(records, b, w), plain(records, b, w)),
        row(day, live[1], "live", "dormant", "displaced", [0.0] * 30,
            plain(records, live[1], w))]
    line = ledger.ledger_path(state, TRACK, ledger.LIFECYCLE).read_text().splitlines()[-1]
    assert '"adjusted":null' in line and '"reason":"displaced"' in line


def test_retired_dormant_and_failure_rows_carry_neither_figure(tmp_path, setup):
    a, b = new(tmp_path, setup, 1), new(tmp_path, setup, 2)
    since = START + timedelta(days=29)
    put(tmp_path, row(since, a, "live", "dormant", "dormant"))
    day = since + timedelta(days=365)
    records = {a: dated(series(-0.002, 30)), b: dated(series(0.002, 30))}
    out = steps(tmp_path, setup, day, records, {b: "boom"})
    assert [(r["id"], r["reason"]) for r in out] == [(b, "failure: boom"),
                                                    (a, "retired_dormant")]
    assert all(set(r) == BASE_KEYS for r in out)
    assert all(set(r) == BASE_KEYS for r in lifecycle_rows(tmp_path)[-2:])


# ------------------------------------------------------------------ admission
# Decisions 2026-10-14 86, 87 (owner's O-11 to O-13): the admission score is
# the candidate's ``adjusted_t["sharpe"]``; a full cell's live approaches are
# scored over T's days on their own adjusted series with their own average
# positions; the trial row holds ``adjusted_t`` and ``adjusted_w`` beside
# ``metrics_t`` and ``metrics_w``; the ``admitted`` and ``displaced`` rows carry
# ``adjusted`` and ``plain``. Where a test writes no exposure (every ``R_i(D)``
# 0) a live approach's adjusted series is its plain one.


T_DAYS = tuple(START + timedelta(days=k) for k in range(33, 40))
DAY = T_DAYS[-1]
SAME = object()
FLAT = {s: 0.0 for s in SYMBOLS}


def adjusted_t(score, avg_position=None):
    """A candidate's ``adjusted_t`` (decision 86 (a)): the score, the other
    figures ``None``, its average positions (0 on each symbol unless given)."""
    return {"sharpe": score, "sharpe_2x": None, "total_return": None,
            "total_return_2x": None, "avg_position": dict(avg_position or FLAT)}


def candidate(sharpe_t, trades, k=99, grid=None, metrics_w=None, adjusted=SAME,
              t_days=T_DAYS, adjusted_w=None):
    """A candidate whose ``metrics_t["sharpe"]`` is ``sharpe_t`` and whose
    ``adjusted_t["sharpe"]`` is ``adjusted`` (``sharpe_t`` unless given)."""
    return Candidate(
        source=f"# candidate {k}\nPARAMS = {{}}\n", params={"k": k}, cell=CELL,
        model_id="test-model", model_version="v0", cutoff=date(2018, 6, 1),
        description="a candidate", profile_version="w-test",
        metrics_t={"sharpe": sharpe_t, "trades": trades, "days": len(t_days)},
        adjusted_t=adjusted_t(sharpe_t if adjusted is SAME else adjusted),
        t_days=t_days, grid=grid, metrics_w=metrics_w, adjusted_w=adjusted_w)


def scored(r, adjusted, plain):
    """Lifecycle row ``r`` with decision 87's two figures, given as numbers."""
    def one(v):
        return None if v is None or math.isnan(v) else v
    return {**r, "adjusted": one(adjusted), "plain": one(plain)}


def trials(state):
    return ledger.read(state, TRACK, ledger.TRIALS)


def write_paper(state, setup, records, units=None, positions=None):
    paper.write(state, TRACK, frame(records))
    exposure(state, setup, records, units, positions)


def test_admission_into_a_free_slot_writes_the_trial_the_approach_and_one_row(tmp_path,
                                                                              setup):
    c = candidate(1.5, 30)
    done = lifecycle.admit(tmp_path, setup, c, DAY)
    assert (done.admitted, done.reason, done.displaced) == (True, "free_slot", None)
    [trial] = trials(tmp_path)
    assert set(trial) == set(ledger.KEYS[ledger.TRIALS]) | set(ledger.TRIAL_FIGURES)
    assert trial == {
        "date": DAY.isoformat(), "id": done.id, "cell": CELL, "model_id": "test-model",
        "model_version": "v0", "cutoff": "2018-06-01",
        "code_sha256": hashlib.sha256(c.source.encode("utf-8")).hexdigest(),
        "profile_version": "w-test", "cost_model": costs.VERSION,
        "config_hash": costs.config_hash(setup.instruments, setup.spread_tables),
        "grid": None, "params": {"k": 99}, "metrics_w": None,
        "metrics_t": {"sharpe": 1.5, "trades": 30, "days": 7},
        "adjusted_t": adjusted_t(1.5), "adjusted_w": None,
        "admitted": True, "reason": "free_slot", "displaced": None}
    [held] = read_approaches(tmp_path)
    assert held.id == done.id and held.admitted == DAY
    assert lifecycle_rows(tmp_path) == [
        scored(row(DAY, done.id, "candidate", "live", "admitted"), 1.5, 1.5)]
    assert not (tmp_path / "trials").exists()


def test_a_trial_row_keeps_the_grid_and_w_metrics_it_carries(tmp_path, setup):
    grid = {"values": {"k": [1, 2]}, "results": [{"k": 1, "sharpe": 0.3}]}
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 30, grid=grid,
                                                      metrics_w={"sharpe": 0.9},
                                                      adjusted_w=adjusted_t(0.7)), DAY)
    [trial] = trials(tmp_path)
    assert trial["grid"] == grid and trial["metrics_w"] == {"sharpe": 0.9}
    assert trial["adjusted_w"] == adjusted_t(0.7)
    assert done.admitted


@pytest.mark.parametrize("score", [0.0, -0.4, math.nan])
def test_a_score_that_is_not_positive_is_refused_and_written_under_trials(tmp_path, setup,
                                                                          score):
    done = lifecycle.admit(tmp_path, setup, candidate(score, 300), DAY)
    assert (done.admitted, done.reason, done.displaced) == (False, "not_positive", None)
    [trial] = trials(tmp_path)
    assert trial["admitted"] is False and trial["reason"] == "not_positive"
    assert trial["metrics_t"]["sharpe"] == (None if math.isnan(score) else score)
    assert trial["adjusted_t"]["sharpe"] == (None if math.isnan(score) else score)
    assert (tmp_path / "trials" / done.id / "strategy.py").read_text(encoding="utf-8") == \
        candidate(score, 300).source
    assert (tmp_path / "trials" / done.id / "meta.json").is_file()
    assert read_approaches(tmp_path) == [] and lifecycle_rows(tmp_path) == []


@pytest.mark.parametrize("adjusted", [0.0, -0.4, math.nan, None])
def test_the_score_is_the_adjusted_sharpe_not_the_plain_one(tmp_path, setup, adjusted):
    # O-11, decision 86 (b): a positive plain score with an adjusted one that is
    # not positive (or null, not a number) is refused not_positive.
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 300, adjusted=adjusted), DAY)
    assert (done.admitted, done.reason) == (False, "not_positive")
    [trial] = trials(tmp_path)
    assert trial["metrics_t"]["sharpe"] == 1.5
    assert trial["adjusted_t"]["sharpe"] == (
        None if adjusted is None or math.isnan(adjusted) else adjusted)
    assert read_approaches(tmp_path) == [] and lifecycle_rows(tmp_path) == []


@pytest.mark.parametrize("plain_score", [0.0, -0.4, math.nan, None])
def test_a_positive_adjusted_score_is_admitted_whatever_the_plain_one(tmp_path, setup,
                                                                       plain_score):
    done = lifecycle.admit(tmp_path, setup, candidate(plain_score, 30, adjusted=0.6), DAY)
    assert (done.admitted, done.reason) == (True, "free_slot")
    assert lifecycle_rows(tmp_path) == [
        scored(row(DAY, done.id, "candidate", "live", "admitted"), 0.6, plain_score)]


def test_too_few_trades_at_min_trades_t_is_refused(tmp_path, setup):
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 29), DAY)
    assert (done.admitted, done.reason) == (False, "too_few_trades")
    assert len(trials(tmp_path)) == 1 and lifecycle_rows(tmp_path) == []
    assert (tmp_path / "trials" / done.id).is_dir() and read_approaches(tmp_path) == []
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 30, k=98), DAY)
    assert (done.admitted, done.reason) == (True, "free_slot")


def on_t_values(mean):
    return series(mean, len(T_DAYS), amp=0.001)


def cell_on_t(state, setup, means, units=None, positions=None):
    """Three live approaches of ``CELL`` with paper means ``means`` over T's
    days (None: a Sharpe that is not a number), and other days around them;
    their exposure records written (``R_i(D)`` 0 and no position unless given)."""
    live = [new(state, setup, 10 + k) for k in range(3)]
    records = {}
    for aid, m in zip(live, means, strict=True):
        on_t = [0.001] * len(T_DAYS) if m is None else on_t_values(m)
        records[aid] = dated(series(0.01, 33) + on_t)        # strong before T
    write_paper(state, setup, records, units, positions)
    return live, records


def test_admission_displacing_the_weakest_makes_it_dormant(tmp_path, setup):
    live, _ = cell_on_t(tmp_path, setup, [0.002, 0.0005, 0.003])
    weak = live[1]
    low, next_up = sharpe(pd.Series(on_t_values(0.0005))), sharpe(pd.Series(on_t_values(0.002)))
    assert 0 < low < next_up
    score = (low + next_up) / 2
    done = lifecycle.admit(tmp_path, setup, candidate(score, 30), DAY)
    assert (done.admitted, done.reason, done.displaced) == (True, "displaced", weak)
    [trial] = trials(tmp_path)
    assert trial["displaced"] == weak and trial["reason"] == "displaced"
    assert lifecycle_rows(tmp_path) == [
        scored(row(DAY, done.id, "candidate", "live", "admitted"), score, score),
        scored(row(DAY, weak, "live", "dormant", "displaced"), low, low)]
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
    live, _ = cell_on_t(tmp_path, setup, [0.0001, None, 0.0001])
    done = lifecycle.admit(tmp_path, setup, candidate(0.01, 30), DAY)
    assert done.displaced == live[1]
    other = tmp_path / "ties"
    live, _ = cell_on_t(other, setup, [0.003, 0.0005, 0.0005])
    done = lifecycle.admit(other, setup, candidate(1000.0, 30), DAY)
    assert done.displaced == min(live[1], live[2])


def test_admission_counts_the_states_after_the_days_steps(tmp_path, setup):
    # A live approach made dormant on DAY frees its slot for the candidate of DAY.
    live, _ = cell_on_t(tmp_path, setup, [0.002, 0.0005, 0.003])
    put(tmp_path, row(DAY, live[0], "live", "dormant", "dormant"))
    done = lifecycle.admit(tmp_path, setup, candidate(0.01, 30), DAY)
    assert (done.reason, done.displaced) == ("free_slot", None)


def test_the_weakest_of_a_full_cell_is_chosen_on_its_adjusted_sharpe_over_t(tmp_path, setup):
    # O-12, decision 86 (c): each live approach is scored over T's days on its
    # own adjusted net_1x with its own average positions over those days. The
    # plain measure names live[0] (the lowest plain mean on T), whose plain
    # Sharpe is above the score, so it would refuse; the adjusted one names
    # live[1], which holds SYNX long on T (and short before T, so that an
    # average over its whole record would not make it the weakest). The
    # candidate's own average positions (short SYNX) are not the live ones'.
    live, records = cell_on_t(tmp_path, setup, [0.0005, 0.002, 0.003])
    units = priced("SYNX", T_DAYS, 0.0048)
    before = [START + timedelta(days=k) for k in range(33)]
    positions = {**held(live[1], "SYNX", before, -2.0), **held(live[1], "SYNX", T_DAYS, 1.0)}
    exposure(tmp_path, setup, records, units, positions)
    adjusted = {aid: fig(own(records, positions, units, aid, T_DAYS)) for aid in live}
    plains = {aid: fig(plain(records, aid, T_DAYS)) for aid in live}
    whole = {aid: fig(own(records, positions, units, aid, dates_of(records, aid)))
             for aid in live}
    assert min(plains, key=plains.get) == live[0]
    assert min(adjusted, key=adjusted.get) == live[1]
    assert min(whole, key=whole.get) == live[0]
    score = (adjusted[live[1]] + plains[live[0]]) / 2
    assert 0 < adjusted[live[1]] < score < plains[live[0]] == adjusted[live[0]]
    c = dataclasses.replace(candidate(-1.0, 30),
                            adjusted_t=adjusted_t(score, {**FLAT, "SYNX": -1.0}))
    done = lifecycle.admit(tmp_path, setup, c, DAY)
    assert (done.admitted, done.reason, done.displaced) == (True, "displaced", live[1])
    assert lifecycle_rows(tmp_path) == [
        scored(row(DAY, done.id, "candidate", "live", "admitted"), score, -1.0),
        scored(row(DAY, live[1], "live", "dormant", "displaced"), adjusted[live[1]],
               plains[live[1]])]
    [trial] = trials(tmp_path)
    assert trial["adjusted_t"]["avg_position"] == {**FLAT, "SYNX": -1.0}
    assert trial["metrics_t"]["sharpe"] == -1.0 and trial["adjusted_w"] is None


def test_returned_on_d_and_displaced_by_d_s_admission_both_rows_stand(tmp_path, setup):
    # Decision 68 (b) with the day's admission doing the displacing (decision
    # 86 (f), the REVIEW-9 note): ``first`` returns into the free slot in step 3
    # of D, then D's candidate fills the full cell by displacing it (the lowest
    # Sharpe over T's days). The rows dated D stand in the order taken
    # (returned, admitted, displaced) and a later count of its dormancy starts
    # from the displaced row.
    held_ = [new(tmp_path, setup, 10 + k) for k in range(2)]      # two live: a free slot
    first = new(tmp_path, setup, 1)
    since = START + timedelta(days=20)
    put(tmp_path, row(since, first, "live", "dormant", "dormant"))
    records = {held_[0]: dated(series(0.003, 50)), held_[1]: dated(series(0.003, 50)),
               first: dated(series(0.0005, 50))}
    exposure(tmp_path, setup, records)
    paper.write(tmp_path, TRACK, frame(records))
    d = START + timedelta(days=35)
    t_days = tuple(d - timedelta(days=k) for k in range(6, -1, -1))
    returned = row(d, first, "dormant", "live", "returned", **same(series(0.0005, 50)[6:36]))
    assert lifecycle.run_steps(tmp_path, setup, d, frame(records), {}) == [returned]
    done = lifecycle.admit(tmp_path, setup, candidate(1000.0, 30, t_days=t_days), d)
    on_t = series(0.0005, 50)[29:36]
    assert (done.admitted, done.reason, done.displaced) == (True, "displaced", first)
    taken = [returned,
             scored(row(d, done.id, "candidate", "live", "admitted"), 1000.0, 1000.0),
             row(d, first, "live", "dormant", "displaced", **same(on_t))]
    assert lifecycle_rows(tmp_path)[-3:] == taken
    apps = read_approaches(tmp_path)
    assert lifecycle.states(lifecycle_rows(tmp_path), apps, d + timedelta(days=1))[first] == \
        lifecycle.Status("dormant", d)
    # A failure frees a slot; ``first`` has waited 19 trading days since its
    # first row to dormant but 4 since D, so it stays; on the fifth it returns.
    four = d + timedelta(days=4)
    assert steps(tmp_path, setup, four, records, {held_[0]: "boom"}) == \
        [row(four, held_[0], "live", "retired", "failure: boom")]
    five = d + timedelta(days=5)
    assert steps(tmp_path, setup, five, records) == \
        [row(five, first, "dormant", "live", "returned", **same(series(0.0005, 50)[11:41]))]


#: The lines the parent's code (e80ccb0, before decisions 86 and 87 reached
#: admission) wrote for one admission: a trial row without ``adjusted_t`` and
#: ``adjusted_w`` and an ``admitted`` row without ``adjusted`` and ``plain``.
OLD_TRIAL = ('{"admitted":true,"cell":"trend/short","code_sha256":"%s","config_hash":"%s",'
             '"cost_model":"%s","cutoff":"2018-06-01","date":"2019-02-01","displaced":null,'
             '"grid":null,"id":"%s","metrics_t":{"days":7,"sharpe":1.5,"trades":30},'
             '"metrics_w":null,"model_id":"test-model","model_version":"v0",'
             '"params":{"k":97},"profile_version":"w-test","reason":"free_slot"}')
OLD_ROW = ('{"date":"2019-02-01","from":"candidate","id":"%s","reason":"admitted",'
           '"to":"live"}')


def test_rows_written_before_are_not_rewritten_after_a_new_day(tmp_path, setup):
    old = candidate(1.5, 30, k=97)
    aid = approach_id(old.source, old.params)
    trial_line = OLD_TRIAL % (hashlib.sha256(old.source.encode("utf-8")).hexdigest(),
                              costs.config_hash(setup.instruments, setup.spread_tables),
                              costs.VERSION, aid)
    for name, text in ((ledger.TRIALS, trial_line), (ledger.LIFECYCLE, OLD_ROW % aid)):
        path = ledger.ledger_path(tmp_path, TRACK, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    records = {new(tmp_path, setup, 1): dated(series(0.002, 40))}
    write_paper(tmp_path, setup, records)
    lifecycle.run_steps(tmp_path, setup, DAY, frame(records), {})
    done = lifecycle.admit(tmp_path, setup, candidate(1.5, 30), DAY)
    assert done.admitted
    trials_text = ledger.ledger_path(tmp_path, TRACK, ledger.TRIALS).read_text().splitlines()
    rows_text = ledger.ledger_path(tmp_path, TRACK, ledger.LIFECYCLE).read_text().splitlines()
    assert trials_text[0] == trial_line and rows_text[0] == OLD_ROW % aid
    assert "adjusted_t" in trials_text[-1] and '"adjusted":1.5' in rows_text[-1]
