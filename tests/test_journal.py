"""Approaches and the decision journal (DESIGN 6.2, 7, 9.1, 9.2; decisions
2026-10-12 24, 25, 39, 48, 49, 51; I-5, I-6, I-7).

``bars fetch`` runs in-process on the fixture track ``test_mixed`` into a
pytest temporary state directory at ``AS_OF``; each test journals into a copy
of it under its own temporary directory. Approaches are written with
``state.write_approach`` (decision 48: the function tests call in place of
admission), from the repository's ``reference/`` files with their ``PARAMS``.
The span ``DAYS`` (2019-06-08 to 2019-06-19) holds the SYNA roll of
2019-06-14, which a test asserts. The synthetic instruments' seeds are those
of their fixture records (``SEEDS``, asserted); no other random draw is made.
Time comes only from ``--as-of``.
"""

import hashlib
import json
import math
import os
import shutil
from datetime import date, timedelta

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from discotrade import costs, journal
from discotrade.backtest import evaluate
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange
from discotrade.state import StateError, content_hash, read_approaches, write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-06-26T00:00:00+00:00"
#: The seed of every random draw these tests depend on: the synthetic sources'.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
ADMITTED = date(2019, 6, 7)
DAYS = tuple(date(2019, 6, 8) + timedelta(days=k) for k in range(12))
FILES = ("trend_ma.py", "zscore_reversal.py", "hour_of_day.py")
META_FIELDS = {"id", "cell", "model_id", "model_version", "cutoff", "description", "params",
               "code_sha256", "profile_version", "cost_model", "config_hash", "admitted"}
COMPARED = ("p", "h", "gross", "trade", "fee", "spread", "slippage", "roll", "cost",
            "net_1x", "net_2x")
#: Journal column of each compared field of the module's per-bar rows.
AS_JOURNAL = {"p": "target_next", "h": "position", "roll": "roll_cost"}


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers."""
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("jcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def bars_state(tmp_path_factory, config):
    state = tmp_path_factory.mktemp("jbars") / "state"
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    return state


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture
def state(tmp_path, bars_state):
    path = tmp_path / "state"
    shutil.copytree(bars_state, path)
    return path


def admit(state, setup, name="trend_ma.py", source=None, admitted=ADMITTED):
    path = REPO_ROOT / "reference" / name
    strat = load_strategy_file(path, setup.thresholds)
    return write_approach(
        state, source=path.read_text(encoding="utf-8") if source is None else source,
        params=strat.params, cell="trend/short", model_id="test-model",
        model_version="test-model-v0", cutoff=date(2019, 1, 1),
        description=f"the reference strategy {name}", profile_version="w-test",
        admitted=admitted, instruments=setup.instruments, spread_tables=setup.spread_tables)


def journal_days(state, setup, days):
    return [journal.journal_day(state, setup, d) for d in days]


def day_file(state, d):
    return state / "journal" / TRACK / f"{d.year:04d}" / f"{d.isoformat()}.parquet"


def index_file(state):
    return state / "journal" / TRACK / "index.jsonl"


def snapshot(path):
    st = os.stat(path)
    return path.read_bytes(), st.st_ino, st.st_mtime_ns


def all_rows(state, days):
    return pd.concat([pd.read_parquet(day_file(state, d)) for d in days], ignore_index=True)


# ------------------------------------------------------------------ the span


def test_seeds_are_the_fixture_records(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS


def test_the_span_holds_the_syna_roll(state, setup):
    admit(state, setup)
    journal_days(state, setup, DAYS)
    rows = all_rows(state, DAYS)
    syna = rows[rows["instrument"] == "SYNA"]
    assert syna["roll"].any()
    rolled = syna[syna["roll"]]
    assert all(DAYS[0] < d <= DAYS[-1] for d in rolled["date"])


# ------------------------------------------------------------------ approaches


def test_approach_id_is_decision_48s(state, setup):
    source = (REPO_ROOT / "reference" / "trend_ma.py").read_text(encoding="utf-8")
    params = load_strategy_file(REPO_ROOT / "reference" / "trend_ma.py",
                                setup.thresholds).params
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"))
    expected = "a" + hashlib.sha256(
        source.encode("utf-8") + b"\n" + canonical.encode("utf-8")).hexdigest()[:12]
    assert admit(state, setup) == expected
    assert (state / "approaches" / expected / "strategy.py").read_bytes() == \
        source.encode("utf-8")
    assert [a.id for a in read_approaches(state)] == [expected]


def test_meta_json_holds_every_field_of_9_1(state, setup):
    aid = admit(state, setup)
    meta = json.loads((state / "approaches" / aid / "meta.json").read_text(encoding="utf-8"))
    assert set(meta) == META_FIELDS
    source = (REPO_ROOT / "reference" / "trend_ma.py").read_bytes()
    assert meta["id"] == aid
    assert meta["code_sha256"] == hashlib.sha256(source).hexdigest()
    assert meta["params"] == {"fast": 24, "slow": 96}
    assert meta["cost_model"] == costs.VERSION == "c1"
    assert meta["config_hash"] == costs.config_hash(setup.instruments, setup.spread_tables)
    assert meta["admitted"] == "2019-06-07"
    assert meta["cutoff"] == "2019-01-01"
    assert (meta["cell"], meta["model_id"], meta["model_version"], meta["profile_version"]) \
        == ("trend/short", "test-model", "test-model-v0", "w-test")
    assert meta["description"] == "the reference strategy trend_ma.py"


def test_writing_an_approach_again_changes_nothing_and_a_different_one_is_refused(
        state, setup):
    aid = admit(state, setup)
    before = snapshot(state / "approaches" / aid / "meta.json")
    assert admit(state, setup) == aid
    assert snapshot(state / "approaches" / aid / "meta.json") == before
    with pytest.raises(StateError, match=aid):
        admit(state, setup, admitted=date(2019, 6, 1))


def test_a_source_that_is_not_a_repository_file_fails_the_day_naming_the_approach(
        state, setup):
    text = (REPO_ROOT / "reference" / "trend_ma.py").read_text(encoding="utf-8")
    aid = admit(state, setup, source=text + "\n# not a repository file\n")
    with pytest.raises(journal.JournalError, match=aid):
        journal.journal_day(state, setup, DAYS[0])
    assert not (state / "journal").exists()


def test_a_test_fixture_source_is_accepted(state, setup):
    path = REPO_ROOT / "tests" / "fixtures" / "strategies" / "roll_probe.py"
    strat = load_strategy_file(path, setup.thresholds)
    write_approach(state, source=path.read_text(encoding="utf-8"), params=strat.params,
                   cell="trend/short", model_id="m", model_version="v", cutoff=date(2019, 1, 1),
                   description="probe", profile_version="p", admitted=ADMITTED,
                   instruments=setup.instruments, spread_tables=setup.spread_tables)
    assert journal.journal_day(state, setup, DAYS[0]).status == "written"


# ------------------------------------------------------------------ rows


def test_a_days_rows_have_decision_49s_columns_first_row_and_carry(state, setup):
    aid = admit(state, setup)
    days = DAYS[:5]
    journal_days(state, setup, days)
    store = BarStore(state, TRACK, setup.track.bar_seconds)
    boundaries_carried = 0
    for d in days:
        rows = pd.read_parquet(day_file(state, d))
        assert tuple(rows.columns) == journal.COLUMNS
        assert (rows["date"] == d).all()
        assert (rows["subject"] == aid).all() and (rows["kind"] == "approach").all()
    rows = all_rows(state, days)
    for symbol in ("SYNA", "SYNL", "SYNX"):
        inst = rows[rows["instrument"] == symbol].sort_values("ts").reset_index(drop=True)
        assert len(inst) > 0
        assert inst["prev_position"].iloc[0] == 0.0
        assert inst["position"].iloc[0] == 0.0
        for k in range(1, len(inst)):
            assert inst["position"].iloc[k] == inst["target_next"].iloc[k - 1]
            assert inst["prev_position"].iloc[k] == inst["position"].iloc[k - 1]
            if inst["date"].iloc[k] != inst["date"].iloc[k - 1] \
                    and inst["target_next"].iloc[k - 1] != 0.0:
                boundaries_carried += 1
        raw = store.read_range(symbol, inst["ts"].iloc[0],
                               inst["ts"].iloc[-1] + pd.Timedelta(seconds=1))
        assert list(raw["ts"]) == list(inst["ts"])
        assert list(raw["open"]) == list(inst["fill_price"])
        assert (inst["trade"] == (inst["position"] - inst["prev_position"]).abs()).all()
    assert boundaries_carried > 0, "no non-zero target carried across a day boundary"


def test_a_day_file_is_written_once_with_its_index_line(state, setup):
    admit(state, setup)
    result = journal.journal_day(state, setup, DAYS[0])
    assert result.status == "written" and result.events == ()
    rows = pd.read_parquet(day_file(state, DAYS[0]))
    assert len(rows) > 0
    lines = index_file(state).read_text(encoding="utf-8").splitlines()
    assert [json.loads(x) for x in lines] == [{
        "date": "2019-06-08", "rows": len(rows),
        "content_hash": content_hash(rows, ("subject", "instrument", "ts")),
        "key": ["subject", "instrument", "ts"],
    }]
    assert result.content_hash == content_hash(rows, journal.KEY)
    journal.journal_day(state, setup, DAYS[1])
    assert len(index_file(state).read_text(encoding="utf-8").splitlines()) == 2


def test_a_rerun_with_equal_rows_writes_nothing(state, setup):
    admit(state, setup)
    journal_days(state, setup, DAYS[:2])
    before = [snapshot(day_file(state, d)) for d in DAYS[:2]] + [snapshot(index_file(state))]
    for d in DAYS[:2]:
        result = journal.journal_day(state, setup, d)
        assert result.status == "unchanged" and result.events == ()
    after = [snapshot(day_file(state, d)) for d in DAYS[:2]] + [snapshot(index_file(state))]
    assert after == before


def test_a_rerun_with_unequal_rows_leaves_the_file_and_returns_journal_mismatch(
        state, setup):
    aid = admit(state, setup)
    journal_days(state, setup, DAYS[:2])
    # Change the stored previous day's last SYNX target_next, which day 2 starts from.
    first = day_file(state, DAYS[0])
    rows = pd.read_parquet(first)
    last = rows[rows["instrument"] == "SYNX"]["ts"].idxmax()
    rows.loc[last, "target_next"] = 0.5 if rows.loc[last, "target_next"] != 0.5 else -0.5
    pq.write_table(pa.Table.from_pandas(rows, schema=journal.SCHEMA, preserve_index=False),
                   first)
    before = [snapshot(day_file(state, DAYS[1])), snapshot(index_file(state))]
    result = journal.journal_day(state, setup, DAYS[1])
    assert result.status == "mismatch"
    assert [(e.kind, e.level, e.date, e.subject) for e in result.events] == [
        ("journal_mismatch", "alert", DAYS[1], aid)]
    assert [snapshot(day_file(state, DAYS[1])), snapshot(index_file(state))] == before


def test_a_day_with_no_subject_writes_an_empty_file_and_its_index_line(state, setup):
    result = journal.journal_day(state, setup, DAYS[0])
    assert result.status == "written"
    rows = pd.read_parquet(day_file(state, DAYS[0]))
    assert len(rows) == 0 and tuple(rows.columns) == journal.COLUMNS
    [line] = index_file(state).read_text(encoding="utf-8").splitlines()
    assert json.loads(line)["rows"] == 0 and json.loads(line)["date"] == "2019-06-08"


def test_a_skipped_day_fails_the_next_and_writes_nothing(state, setup):
    admit(state, setup)
    journal.journal_day(state, setup, DAYS[0])
    before = snapshot(index_file(state))
    with pytest.raises(journal.JournalError, match="skipped"):
        journal.journal_day(state, setup, DAYS[2])
    assert not day_file(state, DAYS[2]).exists()
    assert snapshot(index_file(state)) == before


def test_an_approach_is_journaled_only_after_its_admission_date(state, setup):
    admit(state, setup, admitted=DAYS[1])
    journal_days(state, setup, DAYS[:3])
    assert len(pd.read_parquet(day_file(state, DAYS[0]))) == 0
    assert len(pd.read_parquet(day_file(state, DAYS[1]))) == 0
    assert len(pd.read_parquet(day_file(state, DAYS[2]))) > 0


# ------------------------------------------------------------------ one implementation of §7


@pytest.mark.parametrize("name", FILES)
def test_journal_equals_the_module_evaluation_over_the_span(state, setup, name):
    aid = admit(state, setup, name)
    journal_days(state, setup, DAYS)
    rows = all_rows(state, DAYS)
    assert (rows["subject"] == aid).all()
    strat = load_strategy_file(REPO_ROOT / "reference" / name, setup.thresholds)
    window = DateRange(DAYS[0], DAYS[-1])
    for inst in setup.instruments:
        ev = evaluate(state, setup.track, inst, setup.calendars[inst.calendar], strat, window,
                      spread_table=setup.spread_tables[inst.symbol])
        mine = rows[rows["instrument"] == inst.symbol].sort_values("ts").reset_index(drop=True)
        mine["cost"] = mine["fee"] + mine["spread"] + mine["slippage"] + mine["roll_cost"]
        assert len(ev.rows) == len(mine) > 0
        assert list(ev.rows["ts"]) == list(mine["ts"])
        assert list(ev.rows["date"]) == list(mine["date"])
        for field in COMPARED:
            column = AS_JOURNAL.get(field, field)
            for k, (a, b) in enumerate(zip(mine[column], ev.rows[field], strict=True)):
                assert eq(a, b), f"{name} {inst.symbol} row {k} {field}: {a!r} != {b!r}"
