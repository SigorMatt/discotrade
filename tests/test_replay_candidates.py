"""Scripted candidates in the replay (DESIGN 10.2, 10.3, 16.1 step 5, 16.2;
decisions 2026-10-12 48, 62, 63, 73; I-5, I-6).

``discotrade replay --candidates <file>`` runs in-process through
``discotrade.cli.main`` on the fixture track ``test_synth`` (four synthetic
instruments on ``synth_week``, ``cell_slots`` 3) into a state directory made
by ``init-state`` under the test's tmp directory at ``INIT_AS_OF``. The
configuration is ``tests/fixtures/config/`` copied under tmp with the
production ``config/thresholds.toml`` (so ``admission.min_trades_t`` is its
production 30), one value lowered in that copy, said so:
``controls.random_pool`` 4 in place of 50 (fewer control slots, so that the
replayed days stay quick; no rule tested here reads it).

Before the replay, three approaches are written by ``state.write_approach``
(decision 48), admitted Friday 2019-06-07, all in the cell ``trend/short``
(which is then full): ``reference/trend_ma.py`` with its own parameters and
with ``fast`` 6, ``slow`` 24, and
``tests/fixtures/strategies/breaks_thursday_noon.py``, which breaks decision
22's contract on Thursday 2019-06-13 and is retired that day (step 1).

The replay covers Monday 2019-06-10 to Thursday 2019-06-13 with the new
fixture ``tests/fixtures/scenarios/u6_candidates.jsonl``, one candidate a day:

- 06-10 ``reference/zscore_reversal.py``, score -0.25: refused ``not_positive``;
- 06-11 ``tests/fixtures/strategies/valid_bound.py`` into ``breakout/short``,
  score 0.5 with 30 trades: admitted ``free_slot``, journaled from 06-12;
- 06-12 ``reference/trend_ma.py`` with ``fast`` 12, ``slow`` 48, 29 trades:
  refused ``too_few_trades`` (production ``min_trades_t`` 30);
- 06-13 ``reference/hour_of_day.py`` into the full ``trend/short``: admitted
  ``free_slot`` only because step 1 of 06-13 retired the failing approach
  first, so its lifecycle row comes after the retirement.

The synthetic instruments' seeds are those of their fixture records
(``SEEDS``, asserted); no other random draw is made. Time comes only from
``--as-of`` and the replay's clock. Every git run is on local paths with
``GIT_ALLOW_PROTOCOL=file`` (decision 47).
"""

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
from datetime import date

import pytest

from discotrade import costs, journal, ledger, lifecycle, state, table
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_track_config
from discotrade.state import approach_id, write_approach
from discotrade.strategy import load_strategy_file

TRACK = "test_synth"
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
SCENARIO = REPO_ROOT / "tests" / "fixtures" / "scenarios" / "u6_candidates.jsonl"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
ADMITTED = date(2019, 6, 7)
FIRST, LAST = date(2019, 6, 10), date(2019, 6, 13)
DAYS = [date(2019, 6, d) for d in (10, 11, 12, 13)]

TREND = REPO_ROOT / "reference" / "trend_ma.py"
BREAKS = REPO_ROOT / "tests" / "fixtures" / "strategies" / "breaks_thursday_noon.py"
#: The approaches written before the replay: (file, params; None for its own).
EARLY = [(TREND, None), (TREND, {"fast": 6, "slow": 24}), (BREAKS, None)]


def git(repo, *args) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def files(root, *under) -> dict[str, bytes]:
    """Every file under ``root`` but ``.git/`` (only under ``under`` when given)."""
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and ".git" not in rel.parts and (not under or rel.parts[0] in under):
            out[rel.as_posix()] = p.read_bytes()
    return out


def head(path) -> str:
    return git(path, "rev-parse", "HEAD").strip()


def call(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:   # argparse's usage errors
            status = exc.code
    return status, out.getvalue(), err.getvalue()


def replay(path, config, first, last, candidates=SCENARIO):
    return call("--state", str(path), "--config", str(config), "--track", TRACK, "replay",
                "--from", first.isoformat(), "--to", last.isoformat(),
                "--candidates", str(candidates))


def scenario() -> list[dict]:
    return [json.loads(x) for x in SCENARIO.read_text(encoding="utf-8").splitlines()]


def cid(line) -> str:
    return approach_id((REPO_ROOT / line["source"]).read_text(encoding="utf-8"),
                       line["params"])


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("ccfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    text = (REPO_ROOT / "config" / "thresholds.toml").read_text(encoding="utf-8")
    assert text.count("random_pool = 50") == 1
    assert text.count("min_trades_t = 30") == 1
    (path / "thresholds.toml").write_text(text.replace("random_pool = 50", "random_pool = 4 "),
                                          encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def early_ids(setup):
    out = []
    for path, params in EARLY:
        strat = load_strategy_file(path, setup.thresholds)
        out.append(approach_id(path.read_text(encoding="utf-8"), params or strat.params))
    return out


def fresh(path, setup):
    assert main(["init-state", "--state", str(path), "--as-of", INIT_AS_OF]) == 0
    for src, params in EARLY:
        strat = load_strategy_file(src, setup.thresholds)
        write_approach(
            path, source=src.read_text(encoding="utf-8"), params=params or strat.params,
            cell="trend/short", model_id="test-model", model_version="test-model-v0",
            cutoff=date(2019, 1, 1), description=f"{src.stem}", profile_version="w-test",
            admitted=ADMITTED, instruments=setup.instruments,
            spread_tables=setup.spread_tables)
    return path


@pytest.fixture(scope="module")
def first_day(tmp_path_factory, config, setup):
    """A state replayed over Monday 2019-06-10 only, with the scenario."""
    path = fresh(tmp_path_factory.mktemp("cfirst") / "state", setup)
    status, _, err = replay(path, config, FIRST, FIRST)
    assert status == 0, err
    return path


@pytest.fixture(scope="module")
def ran(tmp_path_factory, config, setup):
    """A state replayed over the whole span with the scenario, and its output."""
    path = fresh(tmp_path_factory.mktemp("cran") / "state", setup)
    return (path, *replay(path, config, FIRST, LAST))


def copy_of(src, tmp_path):
    out = tmp_path / "state"
    shutil.copytree(src, out)
    return out


# ------------------------------------------------------------------ the scenario


def test_seeds_and_scenario_are_the_fixture_records(config):
    tc = load_track_config(config, TRACK)
    assert {inst.symbol: inst.source.get("seed") for inst in tc.instruments} == SEEDS
    assert [x["day"] for x in scenario()] == [d.isoformat() for d in DAYS]


def test_replay_runs_every_day_and_names_each_verdict(ran):
    _, status, out, err = ran
    assert status == 0, err
    lines = out.splitlines()
    assert len(lines) == len(DAYS)
    lines_ids = [cid(x) for x in scenario()]
    verdicts = ["refused (not_positive)", "admitted (free_slot)",
                "refused (too_few_trades)", "admitted (free_slot)"]
    for line, d, aid, verdict in zip(lines, DAYS, lines_ids, verdicts, strict=True):
        assert line.startswith(f"replay: {TRACK} {d.isoformat()} at ")
        assert line.endswith(f"; candidate {aid} {verdict}")


def test_one_trial_row_per_candidate_with_grid_and_w_metrics_null(ran, setup):
    path = ran[0]
    want = []
    for line, (admitted, reason) in zip(scenario(), [
            (False, "not_positive"), (True, "free_slot"), (False, "too_few_trades"),
            (True, "free_slot")], strict=True):
        source = (REPO_ROOT / line["source"]).read_text(encoding="utf-8")
        want.append({
            "date": line["day"], "id": cid(line), "cell": line["cell"],
            "model_id": line["model_id"], "model_version": line["model_version"],
            "cutoff": line["cutoff"],
            "code_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "profile_version": line["profile_version"], "cost_model": costs.VERSION,
            "config_hash": costs.config_hash(setup.instruments, setup.spread_tables),
            "grid": None, "params": line["params"], "metrics_w": None,
            "metrics_t": line["metrics_t"], "admitted": admitted, "reason": reason,
            "displaced": None})
    assert ledger.read(path, TRACK, ledger.TRIALS) == want


def test_lifecycle_rows_admission_after_steps_1_to_4(ran, early_ids):
    """The whole lifecycle ledger, in order: on 06-13 step 1 retires the failing
    approach before the day's candidate takes the slot it frees."""
    path = ran[0]
    lines = scenario()
    rows = ledger.read(path, TRACK, ledger.LIFECYCLE)
    assert [{k: r[k] for k in ("date", "id", "from", "to")} for r in rows] == [
        {"date": "2019-06-11", "id": cid(lines[1]), "from": "candidate", "to": "live"},
        {"date": "2019-06-13", "id": early_ids[2], "from": "live", "to": "retired"},
        {"date": "2019-06-13", "id": cid(lines[3]), "from": "candidate", "to": "live"},
    ]
    assert rows[0]["reason"] == "admitted"
    assert rows[1]["reason"].startswith("failure: ")
    assert rows[2]["reason"] == "admitted"


def test_admitted_under_approaches_refused_under_trials(ran):
    path = ran[0]
    lines = scenario()
    for line, admitted in zip(lines, [False, True, False, True], strict=True):
        aid = cid(line)
        held, other = ((state.approach_dir(path, aid), state.trial_dir(path, aid)) if admitted
                       else (state.trial_dir(path, aid), state.approach_dir(path, aid)))
        assert not other.exists()
        source = (REPO_ROOT / line["source"]).read_text(encoding="utf-8")
        assert (held / "strategy.py").read_text(encoding="utf-8") == source
        meta = json.loads((held / "meta.json").read_text(encoding="utf-8"))
        assert meta["id"] == aid and meta["cell"] == line["cell"]
        assert meta["params"] == line["params"]
        assert meta["admitted"] == (line["day"] if admitted else None)


def test_admitted_approach_is_journaled_from_the_next_trading_day(ran, early_ids):
    path = ran[0]
    lines = scenario()
    subjects = {d: set(journal.read_day(path, TRACK, d)["subject"]) for d in DAYS}
    vb, hod = cid(lines[1]), cid(lines[3])
    assert vb not in subjects[date(2019, 6, 10)] | subjects[date(2019, 6, 11)]
    assert vb in subjects[date(2019, 6, 12)] and vb in subjects[date(2019, 6, 13)]
    assert hod not in set().union(*subjects.values())
    for refused in (cid(lines[0]), cid(lines[2])):
        assert refused not in set().union(*subjects.values())
    assert early_ids[2] in subjects[date(2019, 6, 12)]
    assert early_ids[2] not in subjects[date(2019, 6, 13)]


def test_a_rerun_of_the_days_appends_nothing(ran, config, tmp_path):
    path = copy_of(ran[0], tmp_path)
    before, sha = files(path), head(path)
    status, out, err = replay(path, config, FIRST, LAST)
    assert status == 0, err
    assert files(path) == before
    assert head(path) == sha
    lines = out.splitlines()
    assert len(lines) == len(DAYS)
    assert all("already journaled with equal rows; nothing written" in x for x in lines)
    assert all("candidate" not in x for x in lines)


# ------------------------------------------------------------------ staged with the day


@pytest.mark.parametrize("where", ["lifecycle_steps", "table_after_admission"])
def test_a_failing_day_leaves_ledgers_and_approaches_untouched(first_day, config, tmp_path,
                                                               monkeypatch, where):
    """06-11 (whose candidate is admitted) fails in step 2's lifecycle steps,
    or after its admission when the table is built: no ledger, approach,
    trial or journal file changes and no commit is made."""
    path = copy_of(first_day, tmp_path)
    kept = ("ledger", "approaches", "trials", "journal", "paper", "table")
    before, sha = files(path, *kept), head(path)
    seen = []

    def boom(*args, **kw):
        seen.append(where)
        raise journal.JournalError("injected failure")

    if where == "lifecycle_steps":
        monkeypatch.setattr(lifecycle, "run_steps", boom)
    else:
        real = lifecycle.admit

        def admit(*args, **kw):
            seen.append("admit")
            return real(*args, **kw)

        monkeypatch.setattr(lifecycle, "admit", admit)
        monkeypatch.setattr(table, "build", boom)
    status, _, err = replay(path, config, date(2019, 6, 11), date(2019, 6, 11))
    assert status == 1
    assert "2019-06-11" in err and "injected failure" in err
    assert seen == ([where] if where == "lifecycle_steps" else ["admit", where])
    assert files(path, *kept) == before
    assert head(path) == sha
    assert not (path / state.STAGING).exists()


# ------------------------------------------------------------------ refused files


def _lines(**change):
    out = scenario()
    second = dict(out[1])
    for k, v in change.items():
        if v is None:
            del second[k]
        else:
            second[k] = v
    out[1] = second
    return out


@pytest.mark.parametrize("case", [
    "two_for_one_day", "missing_key", "outside_source", "escaping_source", "absent_source",
    "src_source"])
def test_a_refused_file_runs_no_day(first_day, config, tmp_path, case):
    lines = {
        "two_for_one_day": _lines(day="2019-06-10"),
        "missing_key": _lines(metrics_t=None),
        "outside_source": _lines(source="pyproject.toml"),
        "escaping_source": _lines(source="reference/../src/discotrade/indicators.py"),
        "absent_source": _lines(source="reference/absent.py"),
        "src_source": _lines(source="src/discotrade/indicators.py"),
    }[case]
    bad = tmp_path / "candidates.jsonl"
    bad.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in lines),
                   encoding="utf-8")
    path = copy_of(first_day, tmp_path)
    before, sha = files(path), head(path)
    status, out, err = replay(path, config, date(2019, 6, 11), date(2019, 6, 11), bad)
    assert status == 2
    assert out == "" and "discotrade replay: error:" in err and "line 2" in err
    assert files(path) == before
    assert head(path) == sha


def test_run_day_takes_no_candidate(first_day, config, tmp_path):
    path = copy_of(first_day, tmp_path)
    before = files(path)
    status, out, _ = call("--state", str(path), "--config", str(config), "--track", TRACK,
                          "--as-of", "2019-06-11T21:00:00+00:00", "run-day", "--day",
                          "2019-06-11", "--candidates", str(SCENARIO))
    assert status == 2 and out == ""
    assert files(path) == before
