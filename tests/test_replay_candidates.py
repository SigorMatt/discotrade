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

A second replay (REVIEW-9 should-fix 3, decision 2026-10-14 79 (b)) covers
Thursday 2019-06-13 to Friday 2019-06-21 with the new fixture
``tests/fixtures/scenarios/u4_t_days.jsonl`` (one candidate, into a full
cell, on 06-21) and pins the T days ``replay`` passes to the admission
function and a verdict that depends on them.

Each line of a scenario file holds ``adjusted_t`` (decision 2026-10-14 86
(a)): its ``sharpe`` is the score (86 (b)), equal to ``metrics_t["sharpe"]``
in ``u6_candidates.jsonl`` so that each verdict is what it was, 0.2 beside a
plain 0.3 in ``u4_t_days.jsonl``; its other figures are ``null`` and its
``avg_position`` 0 on each instrument. A trial row holds ``adjusted_t`` and
``adjusted_w`` (``null``), an ``admitted`` row ``adjusted`` and ``plain``
(decision 87). Adjusted figures the test compares are its own, from the
journal parquet files and the stored bars (``own_adjusted``), as
``tests/test_exposure.py`` computes them.

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

import pandas as pd
import pyarrow.parquet as pq
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
            "metrics_t": line["metrics_t"], "adjusted_t": line["adjusted_t"],
            "adjusted_w": None, "admitted": admitted, "reason": reason, "displaced": None})
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
    # Decision 2026-10-14 87: an admitted row carries the candidate's adjusted
    # score and its plain one; a failure row neither.
    for r, line in ((rows[0], lines[1]), (rows[2], lines[3])):
        assert (r["adjusted"], r["plain"]) == (line["adjusted_t"]["sharpe"],
                                               line["metrics_t"]["sharpe"])
    assert "adjusted" not in rows[1] and "plain" not in rows[1]


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


def _adjusted(**change):
    """The scenario with line 2's ``adjusted_t`` changed (a value None: the key
    removed); ``avg_position`` changes are given as ``avg_position=...``."""
    figures = dict(scenario()[1]["adjusted_t"])
    for k, v in change.items():
        if v is None:
            del figures[k]
        else:
            figures[k] = v
    return _lines(adjusted_t=figures)


def _positions(**change):
    held = dict(scenario()[1]["adjusted_t"]["avg_position"])
    for k, v in change.items():
        if v is None:
            del held[k]
        else:
            held[k] = v
    return _adjusted(avg_position=held)


REFUSED = {
    "two_for_one_day": lambda: _lines(day="2019-06-10"),
    "missing_key": lambda: _lines(metrics_t=None),
    "outside_source": lambda: _lines(source="pyproject.toml"),
    "escaping_source": lambda: _lines(source="reference/../src/discotrade/indicators.py"),
    "absent_source": lambda: _lines(source="reference/absent.py"),
    "src_source": lambda: _lines(source="src/discotrade/indicators.py"),
    # Decision 2026-10-14 86 (a): adjusted_t holds exactly sharpe, sharpe_2x,
    # total_return, total_return_2x (each a number or null) and avg_position
    # (each instrument symbol of the track to a number).
    "no_adjusted_t": lambda: _lines(adjusted_t=None),
    "adjusted_t_not_an_object": lambda: _lines(adjusted_t=[0.5]),
    "adjusted_t_extra_key": lambda: _adjusted(trades=30),
    "adjusted_t_missing_key": lambda: _adjusted(sharpe_2x=None),
    "adjusted_t_sharpe_a_string": lambda: _adjusted(sharpe="0.5"),
    "adjusted_t_sharpe_a_bool": lambda: _adjusted(sharpe=True),
    "adjusted_t_total_return_an_object": lambda: _adjusted(total_return={"x": 1}),
    "avg_position_missing_symbol": lambda: _positions(SYND=None),
    "avg_position_unknown_symbol": lambda: _positions(SYNX=0.5),
    "avg_position_null": lambda: _adjusted(avg_position={
        **scenario()[1]["adjusted_t"]["avg_position"], "SYNA": None}),
    "avg_position_a_string": lambda: _positions(SYNB="0.5"),
    "avg_position_not_an_object": lambda: _adjusted(avg_position=[0.0, 0.0, 0.0, 0.0]),
}


@pytest.mark.parametrize("case", sorted(REFUSED))
def test_a_refused_file_runs_no_day(first_day, config, tmp_path, case):
    lines = REFUSED[case]()
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


# ------------------------------------------------------------------ T's days at admission
# REVIEW-9 should-fix 3, decision 2026-10-14 79 (b); DESIGN 4.1, 10.3; decision 63.

T_SCENARIO = REPO_ROOT / "tests" / "fixtures" / "scenarios" / "u4_t_days.jsonl"
T_ADMITTED = date(2019, 6, 12)
T_FIRST, T_DAY = date(2019, 6, 13), date(2019, 6, 21)
#: DESIGN 4.1 for D = Friday 2019-06-21 and t_days 7: the trading days whose
#: date lies in 2019-06-15 to 2019-06-21, a span holding a weekend.
T_RIGHT = tuple(date(2019, 6, d) for d in (17, 18, 19, 20, 21))
#: The wrong window: the last seven trading days ending with D.
T_WRONG = tuple(date(2019, 6, d) for d in (13, 14, 17, 18, 19, 20, 21))
#: The full cell: three parameter sets of reference/trend_ma.py in trend/short,
#: chosen (decision 2026-10-14 86 (e)) so that the weakest's adjusted Sharpe is
#: positive over T and negative over the wrong window (the earlier three were
#: negative over both on the adjusted measure, so no positive score depended
#: on the window).
T_CELL = [{"fast": 16, "slow": 48}, {"fast": 24, "slow": 64}, {"fast": 12, "slow": 64}]


def own_journal(path) -> pd.DataFrame:
    files_ = sorted((path / "journal" / TRACK).rglob("*.parquet"))
    return pd.concat([pq.read_table(f).to_pandas() for f in files_], ignore_index=True)


def own_unit(path, symbol) -> dict:
    """Per bar ts: the unit return of ``symbol`` from its stored bars and roll
    records, as tests/test_exposure.py computes it (decision 81 (a))."""
    bars = pd.concat([pq.read_table(f).to_pandas()
                      for f in sorted((path / "bars" / TRACK / symbol).glob("*.parquet"))],
                     ignore_index=True).sort_values("ts").reset_index(drop=True)
    gaps = {}
    rolls = path / "rolls" / TRACK / f"{symbol}.jsonl"
    if rolls.exists():
        for raw in rolls.read_text(encoding="utf-8").splitlines():
            r = json.loads(raw)
            gaps[(pd.Timestamp(r["ts"]), r["old"], r["new"])] = float(r["gap"])
    out = {}
    for k in range(len(bars)):
        o, c = float(bars["open"][k]), float(bars["close"][k])
        if k == 0:
            out[bars["ts"][k]] = (c - o) / o
            continue
        gap = 0.0
        if bars["contract"][k] != bars["contract"][k - 1]:
            gap = gaps[(bars["ts"][k], bars["contract"][k - 1], bars["contract"][k])]
        out[bars["ts"][k]] = ((o - (float(bars["close"][k - 1]) + gap)) + (c - o)) / o
    return out


def own_adjusted(path, subject, window, symbols) -> list[float]:
    """``subject``'s adjusted ``net_1x`` on its journaled days in ``window``,
    the test's own computation from the journal parquet files and the stored
    bars (no function of ``paper.py``): per day, its summed ``net_1x`` over the
    ``N`` instruments less the sum of ``hbar_i(W) * R_i(D)``, over ``N``."""
    rows = own_journal(path)
    rows = rows[rows["date"].isin(set(window))]
    units = {}
    for sym in symbols:
        unit = own_unit(path, sym)
        mine = rows[rows["instrument"] == sym]
        for d, ts in sorted(set(zip(mine["date"], mine["ts"], strict=True))):
            units[(sym, d)] = units.get((sym, d), 0.0) + unit[ts]
    mine = rows[rows["subject"] == subject]
    hbar = {}
    for sym in symbols:
        leg = mine[mine["instrument"] == sym]
        hbar[sym] = float(leg["position"].mean()) if len(leg) else 0.0
    n = len(symbols)
    out = []
    for d in sorted(set(mine["date"])):
        plain = float(mine[mine["date"] == d]["net_1x"].sum()) / n
        out.append(plain - sum(hbar[s] * units.get((s, d), 0.0) for s in symbols) / n)
    return out


def test_admission_reads_t_s_trading_days_for_a_weekend_window(tmp_path, config, setup,
                                                                 monkeypatch):
    """Three approaches of ``reference/trend_ma.py`` (``T_CELL``) are written
    admitted Wednesday 2019-06-12 into ``trend/short`` (full, ``cell_slots``
    3); the replay runs Thursday 2019-06-13 to Friday 2019-06-21 (seven
    trading days) with ``u4_t_days.jsonl``: one candidate dated 06-21 into
    that cell, adjusted score 0.2 (plain 0.3) with 40 trades. ``replay``
    passes the admission function exactly the five weekdays 06-17 to 06-21
    (DESIGN 4.1 over 06-15 to 06-21). Over those days the weakest live approach's adjusted
    net Sharpe at 1x (decision 2026-10-14 86 (c): each scored on its own
    adjusted series with its own average positions over those days, computed
    here from the journal parquet files and the stored bars) is above the
    candidate's ``adjusted_t["sharpe"]``, so the candidate is refused
    ``not_better_than_weakest``; over the last seven trading days (06-13 to
    06-21) it is below it, which would have displaced it."""
    import math

    from discotrade.metrics import sharpe

    path = tmp_path / "state"
    assert main(["init-state", "--state", str(path), "--as-of", INIT_AS_OF]) == 0
    ids = []
    for params in T_CELL:
        source = TREND.read_text(encoding="utf-8")
        write_approach(
            path, source=source, params=params, cell="trend/short", model_id="test-model",
            model_version="test-model-v0", cutoff=date(2019, 1, 1), description="trend_ma",
            profile_version="w-test", admitted=T_ADMITTED, instruments=setup.instruments,
            spread_tables=setup.spread_tables)
        ids.append(approach_id(source, params))
    seen = []
    real = lifecycle.admit

    def admit(state_dir, setup_, candidate, day, **kw):
        seen.append((day, tuple(candidate.t_days)))
        return real(state_dir, setup_, candidate, day, **kw)

    monkeypatch.setattr(lifecycle, "admit", admit)
    status, out, err = replay(path, config, T_FIRST, T_DAY, T_SCENARIO)
    assert status == 0, err
    assert len(out.splitlines()) == 7
    assert seen == [(T_DAY, T_RIGHT)]

    line = json.loads(T_SCENARIO.read_text(encoding="utf-8"))
    score = line["adjusted_t"]["sharpe"]
    journaled = sorted(set(own_journal(path)["date"]))
    assert tuple(journaled[-7:]) == T_WRONG
    symbols = sorted(SEEDS)

    def weakest_on(days):
        values = []
        for aid in ids:
            series = own_adjusted(path, aid, days, symbols)
            assert len(series) == len(days)
            values.append(sharpe(pd.Series(series, dtype="float64")))
        assert not any(math.isnan(v) for v in values)
        return min(values)

    assert weakest_on(T_RIGHT) > score > 0 > weakest_on(T_WRONG)
    aid = cid(line)
    assert out.splitlines()[-1].endswith(f"; candidate {aid} refused (not_better_than_weakest)")
    trial = ledger.read(path, TRACK, ledger.TRIALS)
    assert [(r["id"], r["admitted"], r["reason"], r["displaced"]) for r in trial] == \
        [(aid, False, "not_better_than_weakest", None)]
    assert ledger.read(path, TRACK, ledger.LIFECYCLE) == []


def test_a_line_s_adjusted_t_is_carried_and_null_means_not_a_number(tmp_path):
    # Decision 2026-10-14 86 (a): the candidate carries adjusted_t as the line
    # holds it and adjusted_w None; a null figure is accepted (not a number;
    # lifecycle.admit refuses a null score not_positive).
    from discotrade.replay import read_candidates

    lines = scenario()
    lines[1]["adjusted_t"]["sharpe"] = None
    path = tmp_path / "candidates.jsonl"
    path.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in lines),
                    encoding="utf-8")
    held = read_candidates(path, sorted(SEEDS))
    assert [d.isoformat() for d in held] == [x["day"] for x in lines]
    for line, c in zip(lines, held.values(), strict=True):
        assert c.adjusted_t == line["adjusted_t"] and c.adjusted_w is None
        assert c.metrics_t == line["metrics_t"]
