"""Paper records (DESIGN 9.3, 8; decisions 2026-10-12 23, 53; I-3, I-6).

``paper.build`` is tested on a journal frame the test writes by hand (so that
a row with ``0 < trade <= 1e-9`` exists), and ``paper/<track>/daily.parquet``
as ``run-day`` writes it on the fixture track ``test_mixed`` is compared with a
rebuild from the journal and with the module's daily series
(``metrics.daily_series`` of ``backtest.evaluate`` over the span, decision 23).
``run-day`` runs in-process on a pytest temporary state directory made by
``init-state``; approaches are written with ``state.write_approach`` (decision
48). The ``clean`` column (DESIGN 9.3, 11.3; decision 61) is tested on the
hand frame with cutoffs the test gives, on a control-kind row the test
builds, and on a rebuild of the run-day state after the test rewrites one
approach's recorded ``cutoff`` in a copy under its temporary directory. The
synthetic instruments' seeds are those of their fixture records
(``SEEDS``, asserted); no other random draw is made. Time comes only from
``--as-of``.
"""

import json
import math
import shutil
from datetime import date, timedelta

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from discotrade import journal, metrics, paper, stats
from discotrade.backtest import evaluate
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange
from discotrade.state import META_FILE, approach_dir, canonical_json, content_hash, write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-06-26T00:00:00+00:00"
#: The seed of every random draw these tests depend on: the synthetic sources'.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
DAYS = tuple(date(2019, 6, 8) + timedelta(days=k) for k in range(6))
FIRST = date(2019, 6, 7)       # admission of the first approach
LATER = date(2019, 6, 9)       # admission of the second


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers."""
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


# ------------------------------------------------------------------ build, by hand


def hand_rows() -> pd.DataFrame:
    """Two subjects on a basket of three; subject a1 has bars on two instruments
    on day 1 and one on day 2; trades straddle the 1e-9 floor."""
    d1, d2 = date(2020, 1, 6), date(2020, 1, 7)
    rows = [
        # date, subject, instrument, ts hour, trade, gross, net_1x, net_2x
        (d1, "a1", "X", 0, 0.5, 0.010, 0.008, 0.006),
        (d1, "a1", "X", 1, 5e-10, -0.002, -0.003, -0.004),   # above 0, not above 1e-9
        (d1, "a1", "Y", 0, 1e-9, 0.001, 0.001, 0.001),       # at the floor: not counted
        (d1, "a1", "Y", 1, 2e-9, 0.004, 0.002, 0.000),       # above the floor
        (d2, "a1", "X", 24, 0.0, 0.003, 0.003, 0.003),
        (d1, "a2", "Z", 0, 1.0, -0.006, -0.009, -0.012),
    ]
    frame = pd.DataFrame(rows, columns=["date", "subject", "instrument", "hour", "trade",
                                        "gross", "net_1x", "net_2x"])
    frame["ts"] = pd.Timestamp("2020-01-06", tz="UTC") + pd.to_timedelta(frame["hour"], "h")
    frame = frame.drop(columns="hour")
    frame["kind"] = "approach"
    for column in ("prev_position", "position", "target_next", "fill_price", "fee", "spread",
                   "slippage", "roll_cost"):
        frame[column] = 0.0
    frame["roll"] = False
    return frame[list(journal.COLUMNS)]


#: The model cutoffs of the hand subjects (decision 61: from meta.json; here given).
CUTOFFS = {"a1": date(2020, 1, 6), "a2": date(2020, 1, 5)}


def test_build_is_decision_23s_daily_mean_and_counts_trades_above_the_floor():
    out = paper.build(hand_rows(), 3, CUTOFFS)
    assert tuple(out.columns) == paper.COLUMNS
    got = {(r.subject, r.date): r for r in out.itertuples(index=False)}
    assert sorted(got) == [("a1", date(2020, 1, 6)), ("a1", date(2020, 1, 7)),
                           ("a2", date(2020, 1, 6))]
    a = got[("a1", date(2020, 1, 6))]
    assert eq(a.gross, ((0.010 - 0.002) + (0.001 + 0.004)) / 3)
    assert eq(a.net_1x, ((0.008 - 0.003) + (0.001 + 0.002)) / 3)
    assert eq(a.net_2x, ((0.006 - 0.004) + (0.001 + 0.000)) / 3)
    assert a.trades == 2          # 0.5 and 2e-9; not 5e-10, not 1e-9
    b = got[("a1", date(2020, 1, 7))]
    assert eq(b.gross, 0.003 / 3) and b.trades == 0
    c = got[("a2", date(2020, 1, 6))]
    assert eq(c.net_2x, -0.012 / 3) and c.trades == 1
    assert all(r.kind == "approach" for r in out.itertuples(index=False))


def test_build_of_no_rows_is_an_empty_table_with_the_columns():
    out = paper.build(hand_rows().iloc[:0], 3, CUTOFFS)
    assert tuple(out.columns) == paper.COLUMNS and len(out) == 0


def test_build_does_not_depend_on_the_row_order():
    rows = hand_rows()
    shuffled = rows.sample(frac=1.0, random_state=7).reset_index(drop=True)   # seed 7
    assert content_hash(paper.build(shuffled, 3, CUTOFFS), paper.KEY) == \
        content_hash(paper.build(rows, 3, CUTOFFS), paper.KEY)


def test_an_approach_is_clean_only_on_days_after_its_cutoff():
    out = paper.build(hand_rows(), 3, CUTOFFS)
    got = {(r.subject, r.date): r.clean for r in out.itertuples(index=False)}
    assert got == {("a1", date(2020, 1, 6)): False,    # on the cutoff: exposed
                   ("a1", date(2020, 1, 7)): True,     # after it: clean
                   ("a2", date(2020, 1, 6)): True}
    assert out["clean"].dtype == bool
    before = paper.build(hand_rows(), 3, {"a1": date(2020, 1, 7), "a2": date(2020, 1, 6)})
    assert not before["clean"].any()                   # on or before the cutoff: exposed


def test_a_control_row_is_always_clean():
    rows = hand_rows()
    rows.loc[rows["subject"] == "a1", "kind"] = "control_random"
    rows.loc[rows["subject"] == "a2", "kind"] = "control_bh"
    out = paper.build(rows, 3, {})                     # no cutoff is needed for a control
    assert out["clean"].tolist() == [True, True, True]
    assert stats.clean_counts(out, "a1") == (2, 0)


def test_an_approach_without_a_cutoff_is_refused():
    with pytest.raises(ValueError, match="cutoff"):
        paper.build(hand_rows(), 3, {"a1": date(2020, 1, 1)})


# ------------------------------------------------------------------ as run-day writes it


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("pcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


def admit(state, setup, name, admitted):
    path = REPO_ROOT / "reference" / name
    strat = load_strategy_file(path, setup.thresholds)
    return write_approach(
        state, source=path.read_text(encoding="utf-8"), params=strat.params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description=f"the reference strategy {name}",
        profile_version="w-test", admitted=admitted, instruments=setup.instruments,
        spread_tables=setup.spread_tables)


@pytest.fixture(scope="module")
def ran(tmp_path_factory, config, setup):
    state = tmp_path_factory.mktemp("pran") / "state"
    assert main(["init-state", "--state", str(state), "--as-of", AS_OF]) == 0
    first = admit(state, setup, "trend_ma.py", FIRST)
    second = admit(state, setup, "zscore_reversal.py", LATER)
    after = []
    for d in DAYS:
        assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                     "--as-of", AS_OF, "run-day", "--day", d.isoformat()]) == 0
        after.append((d, paper.paper_path(state, TRACK).read_bytes(),
                      paper.rebuild(state, TRACK, len(setup.instruments))))
    AFTER_EACH_DAY[:] = after
    return state, {first: ("trend_ma.py", FIRST), second: ("zscore_reversal.py", LATER)}


#: Filled by ``ran``: per day of ``DAYS``, the stored paper file's bytes and a
#: full rebuild from the journal, taken right after that day's run.
AFTER_EACH_DAY: list = []


def test_after_every_day_the_paper_file_equals_a_full_rebuild(ran, setup, tmp_path):
    """The day updates the paper file from its own journal file (mission 9 U3);
    after every day of the run the file has the content hash of a full rebuild
    from the whole journal, and the bytes ``paper.write`` gives that rebuild."""
    assert [d for d, _, _ in AFTER_EACH_DAY] == list(DAYS)
    for d, stored_bytes, rebuilt in AFTER_EACH_DAY:
        root = tmp_path / d.isoformat()
        paper.write(root, TRACK, rebuilt)
        assert paper.paper_path(root, TRACK).read_bytes() == stored_bytes, d
        stored = pq.read_table(pa.BufferReader(stored_bytes)).to_pandas()
        assert content_hash(stored, paper.KEY) == content_hash(rebuilt, paper.KEY), d
        assert max(stored["date"]) == d
    # Approach rows begin after their admission, so later days add subjects.
    assert len(set(AFTER_EACH_DAY[0][2]["subject"])) < len(set(AFTER_EACH_DAY[-1][2]["subject"]))


def test_seeds_are_the_fixture_records(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS


def test_the_stored_paper_records_rebuild_from_the_journal_to_the_same_hash(ran, setup):
    state, _ = ran
    stored = paper.read(state, TRACK)
    assert stored is not None and len(stored) > 0
    assert tuple(stored.columns) == paper.COLUMNS
    rebuilt = paper.rebuild(state, TRACK, len(setup.instruments))
    assert content_hash(rebuilt, paper.KEY) == content_hash(stored, paper.KEY)


def test_one_row_per_subject_and_day_from_its_first_journaled_day(ran):
    state, subjects = ran
    stored = paper.read(state, TRACK)
    for aid, (_, admitted) in subjects.items():
        mine = stored[stored["subject"] == aid]
        assert list(mine["date"]) == [d for d in DAYS if d > admitted]


def test_paper_is_the_module_daily_series_and_counts_journal_trades(ran, setup):
    state, subjects = ran
    stored = paper.read(state, TRACK)
    rows = pd.concat([journal.read_day(state, TRACK, d) for d in DAYS], ignore_index=True)
    for aid, (name, admitted) in subjects.items():
        strat = load_strategy_file(REPO_ROOT / "reference" / name, setup.thresholds)
        window = DateRange(admitted + timedelta(days=1), DAYS[-1])
        evs = [evaluate(state, setup.track, inst, setup.calendars[inst.calendar], strat,
                        window, spread_table=setup.spread_tables[inst.symbol])
               for inst in setup.instruments]
        series = metrics.daily_series([metrics.leg(e) for e in evs])
        gross = {}
        for e in evs:
            for d, g in e.rows.groupby("date")["gross"].sum().items():
                gross[d] = gross.get(d, 0.0) + g
        mine = stored[stored["subject"] == aid].reset_index(drop=True)
        assert list(mine["date"]) == list(series["date"])
        for k in range(len(mine)):
            d = mine["date"][k]
            assert eq(mine["net_1x"][k], series["net_1x"][k]), (aid, d)
            assert eq(mine["net_2x"][k], series["net_2x"][k]), (aid, d)
            assert eq(mine["gross"][k], gross[d] / len(setup.instruments)), (aid, d)
            day_rows = rows[(rows["subject"] == aid) & (rows["date"] == d)]
            assert mine["trades"][k] == int((day_rows["trade"] > 1e-9).sum())
    assert stored["trades"].sum() > 0


def test_the_clean_column_follows_each_approachs_recorded_cutoff(ran, setup, tmp_path):
    state, subjects = ran
    stored = paper.read(state, TRACK)
    for aid in subjects:                              # cutoff 2019-01-01: every row clean
        assert stored[stored["subject"] == aid]["clean"].all()
    copy = tmp_path / "state"
    shutil.copytree(state, copy)
    (aid, _), = [(a, v) for a, v in subjects.items() if v[0] == "zscore_reversal.py"]
    meta_path = approach_dir(copy, aid) / META_FILE
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cutoff = date(2019, 6, 11)
    meta["cutoff"] = cutoff.isoformat()
    meta_path.write_text(canonical_json(meta) + "\n", encoding="utf-8")
    rebuilt = paper.rebuild(copy, TRACK, len(setup.instruments))
    mine = rebuilt[rebuilt["subject"] == aid]
    assert list(mine["clean"]) == [d > cutoff for d in mine["date"]]
    assert stats.clean_counts(rebuilt, aid) == (sum(d > cutoff for d in mine["date"]),
                                                sum(d <= cutoff for d in mine["date"]))
    assert 0 < stats.clean_counts(rebuilt, aid)[0] < len(mine)
    # Decision 69: a portfolio row is clean only when every member's row is.
    other = rebuilt[(rebuilt["subject"] != aid) & (rebuilt["subject"] != "portfolio")]
    assert other["clean"].all()
