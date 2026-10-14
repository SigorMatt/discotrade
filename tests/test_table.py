"""The table (DESIGN 10.4, 8, 11.2, 16.2; decisions 2026-10-12 25, 30, 41, 60, 62,
63, 71; I-6).

``discotrade replay`` runs in-process through ``discotrade.cli.main`` on the
fixture track ``test_synth`` (four synthetic instruments on ``synth_week``,
``cell_slots`` 3) into a state directory made by ``init-state`` under the
test's tmp directory. Every approach is written by the lifecycle's admission
function (``lifecycle.admit``, decision 63), with its trial row and its
lifecycle row:

- on Friday 2019-06-07, into the cell ``trend/short``: ``trend_ma.py`` with
  its own parameters and with ``fast`` 12, ``slow`` 48, and ``hour_of_day.py``
  (the cell is then full); into ``mean_reversion/short``:
  ``zscore_reversal.py``; into ``breakout/short``:
  ``tests/fixtures/strategies/breaks_thursday_noon.py``, which breaks the
  contract on Thursday 2019-06-13 and is retired that day (step 1);
- after the run of Wednesday 2019-06-12, dated that day, ``trend_ma.py`` with
  ``fast`` 6, ``slow`` 24 into the full ``trend/short`` with a score that
  displaces the weakest live approach of the cell, which goes dormant. Its
  files and rows are committed with Thursday's run; its paper days (06-13,
  06-14) are fewer than the track's, so that its deflated figures over its
  own paper days differ from those over the track's.

The replay covers Monday 2019-06-10 to Friday 2019-06-14. The configuration
is ``tests/fixtures/config/`` copied under tmp with the production
``config/thresholds.toml``, one value lowered in that copy, said so:
``controls.random_pool`` 4 in place of 50 (fewer control slots, so that five
replayed days stay quick). The listing of the 50 slots at the production
value is tested on a state with no journaled day. Every expected value is
computed in the test: the states from the lifecycle ledger, the paper record
from the paper rows with decision 30's Sharpe and decision 41's drawdown
written here, ``breakeven_cost`` from the journal files, ``E(N)`` with the
test's own normal quantile (bisection on ``math.erf``/``math.erfc``) and the
control slots' Sharpes over the subject's own paper days. The synthetic
instruments' seeds are those of their fixture records (``SEEDS``, asserted);
no other random draw is made. Time comes only from ``--as-of`` and the
replay's clock. Every git run is on local paths with ``GIT_ALLOW_PROTOCOL=file``
(decision 47).
"""

import json
import math
import os
import re
import shutil
import statistics
import subprocess
from datetime import date

import pandas as pd
import pyarrow.parquet as pq
import pytest

from discotrade import journal, ledger, lifecycle, paper, table
from discotrade.cli import REPO_ROOT, main
from discotrade.state import read_approaches
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
ADMITTED = date(2019, 6, 7)
FIRST = date(2019, 6, 10)
LATE = date(2019, 6, 12)                 # the late admission's date
LAST = date(2019, 6, 14)
DAYS = [date(2019, 6, d) for d in (10, 11, 12, 13, 14)]
CUTOFF = date(2019, 6, 11)               # rows up to it are exposed
REF = REPO_ROOT / "reference"
BREAKS = REPO_ROOT / "tests" / "fixtures" / "strategies" / "breaks_thursday_noon.py"
#: (file, cell, params or None for its own, score on T)
EARLY = [(REF / "trend_ma.py", "trend/short", None, 1.25),
         (REF / "trend_ma.py", "trend/short", {"fast": 12, "slow": 48}, 0.75),
         (REF / "hour_of_day.py", "trend/short", None, 0.5),
         (REF / "zscore_reversal.py", "mean_reversion/short", None, 2.0),
         (BREAKS, "breakout/short", None, 1.0)]
LATE_ONE = (REF / "trend_ma.py", "trend/short", {"fast": 6, "slow": 24}, 3.5)
REALS = ("admission_score", "sharpe", "sharpe_2x", "max_drawdown", "breakeven_cost", "S",
         "E_N", "excess")
FIELDS = ("cell", "description", "model_id", "model_version", "admitted",
          "admission_score", "days", "clean_days", "sharpe", "sharpe_2x", "trades",
          "max_drawdown", "breakeven_cost", "S", "E_N", "excess", "state_history")
APPROACH_ONLY = ("cell", "description", "model_id", "model_version", "admitted",
                 "admission_score", "S", "E_N", "excess", "state_history")


def git(repo, *args) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def files(root) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def replay(state, config, first, last):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "replay", "--from", first.isoformat(), "--to", last.isoformat()])


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers, ``None`` for a value that is not one."""
    if a is None or b is None:
        return a is None and b is None
    a, b = float(a), float(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


def real(x):
    """``None`` for a value that is not a finite number, as table.json writes it."""
    return None if x is None or not math.isfinite(x) else float(x)


# ------------------------------------------------------------------ the test's own rules


def own_sharpe(d):
    """DESIGN 8 with decision 30: not a number with fewer than 2 days, or when
    every value equals the first, or when the deviation is not above 1e-12
    times the largest absolute value."""
    d = [float(x) for x in d]
    if len(d) < 2 or all(x == d[0] for x in d):
        return math.nan
    sd = statistics.stdev(d)
    if not sd > 1e-12 * max(abs(x) for x in d):
        return math.nan
    return statistics.fmean(d) / sd * math.sqrt(252)


def own_drawdown(d):
    """Decision 41: the running sum starts at 0, which counts as a peak."""
    total, peak, worst = 0.0, 0.0, 0.0
    for x in d:
        total += float(x)
        peak = max(peak, total)
        worst = max(worst, peak - total)
    return worst


def own_z(p):
    """The standard normal quantile by bisection on math.erf / math.erfc to 1e-15."""
    def below(x):
        if p > 0.5:
            return 0.5 * math.erfc(x / math.sqrt(2.0)) > 1.0 - p
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0))) < p
    lo, hi = -40.0, 40.0
    for _ in range(400):
        if hi - lo <= 1e-15:
            break
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            break
        if below(mid):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def test_own_quantile_gives_the_published_values():
    for p, want in ((0.95, 1.6448536269514722), (0.975, 1.959963984540054),
                    (0.99, 2.3263478740408408)):
        assert abs(own_z(p) - want) <= 1e-12


def own_expected(mu, sd, n):
    if math.isnan(mu) or math.isnan(sd):
        return math.nan
    g = 0.5772156649015329
    m = max(n, 2)
    return mu + sd * ((1 - g) * own_z(1 - 1 / m) + g * own_z(1 - 1 / (m * math.e)))


# ------------------------------------------------------------------ the run


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("tbcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    text = (REPO_ROOT / "config" / "thresholds.toml").read_text(encoding="utf-8")
    assert text.count("random_pool = 50") == 1
    (path / "thresholds.toml").write_text(text.replace("random_pool = 50", "random_pool = 4 "),
                                          encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


def candidate(setup, spec, t_days=()):
    path, cell, params, score = spec
    strat = load_strategy_file(path, setup.thresholds)
    return lifecycle.Candidate(
        source=path.read_text(encoding="utf-8"), params=params or strat.params, cell=cell,
        model_id="test-model", model_version="test-model-v0", cutoff=CUTOFF,
        description=f"{path.stem} | {cell}", profile_version="w-test",
        metrics_t={"sharpe": score, "trades": 40},
        adjusted_t={"sharpe": score, "sharpe_2x": None, "total_return": None,
                    "total_return_2x": None,
                    "avg_position": {i.symbol: 0.0 for i in setup.instruments}},
        t_days=list(t_days))


@pytest.fixture(scope="module")
def ran(tmp_path_factory, config, setup):
    state = tmp_path_factory.mktemp("tbran") / "state"
    assert main(["init-state", "--state", str(state), "--as-of", INIT_AS_OF]) == 0
    ids = [lifecycle.admit(state, setup, candidate(setup, spec), ADMITTED) for spec in EARLY]
    assert all(a.admitted for a in ids)
    assert replay(state, config, FIRST, LATE) == 0
    late = lifecycle.admit(state, setup, candidate(setup, LATE_ONE, DAYS[:3]), LATE)
    assert late.admitted and late.reason == "displaced" and late.displaced is not None
    assert replay(state, config, date(2019, 6, 13), LAST) == 0
    return state, [a.id for a in ids], late


def test_the_fixture_values(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    assert setup.track.cell_slots == 3
    assert int(setup.thresholds["admission.min_trades_t"]) == 30
    assert int(setup.thresholds["lifecycle.dormant_window_days"]) == 30


def own_states(state, day):
    """Each approach's state after ``day``'s steps: the ``to`` of its last
    lifecycle row dated on or before ``day``."""
    rows = ledger.read(state, TRACK, ledger.LIFECYCLE)
    out = {}
    for a in read_approaches(state):
        if a.admitted <= day:
            out[a.id] = "live"
            for r in rows:
                if r["id"] == a.id and date.fromisoformat(r["date"]) <= day:
                    out[a.id] = r["to"]
    return out


def own_journal_sums(state):
    """Per subject, sum of gross, sum of trade, and 2 * |prev_position| summed
    over its rows with a roll, from every journal file."""
    out = {}
    for path in sorted((state / "journal" / TRACK).rglob("*.parquet")):
        for r in pq.read_table(path).to_pylist():
            s = out.setdefault(r["subject"], [0.0, 0.0, 0.0])
            s[0] += r["gross"]
            s[1] += r["trade"]
            if r["roll"]:
                s[2] += 2 * abs(r["prev_position"])
    return out


def own_expected_rows(state, setup, n):
    states = own_states(state, LAST)
    approaches = {a.id: a for a in read_approaches(state)}
    held = paper.read(state, TRACK)
    held = held.sort_values(["subject", "date"], kind="mergesort")
    life = ledger.read(state, TRACK, ledger.LIFECYCLE)
    trials = ledger.read(state, TRACK, ledger.TRIALS)
    sums = own_journal_sums(state)
    pool = int(setup.thresholds["controls.random_pool"])
    slots = [f"rc:{k}" for k in range(pool)]

    def record(subject):
        mine = held[held["subject"] == subject]
        n1, n2 = list(mine["net_1x"]), list(mine["net_2x"])
        return {"days": len(mine), "clean_days": int(sum(bool(c) for c in mine["clean"])),
                "sharpe": real(own_sharpe(n1)), "sharpe_2x": real(own_sharpe(n2)),
                "trades": int(sum(int(t) for t in mine["trades"])),
                "max_drawdown": real(own_drawdown(n1))}

    def be(subject):
        g, t, r = sums.get(subject, (0.0, 0.0, 0.0))
        return real(g / (t + r) * 10000) if t + r > 0 else None

    def approach(section, aid):
        meta = approaches[aid].meta
        rec = record(aid)
        days = list(held[held["subject"] == aid]["date"])
        sharpes = []
        for slot in slots:
            mine = held[held["subject"] == slot]
            by_day = dict(zip(mine["date"], mine["net_1x"], strict=True))
            if days and all(d in by_day for d in days):
                s = own_sharpe([by_day[d] for d in days])
                if not math.isnan(s):
                    sharpes.append(s)
        mu, sd = ((statistics.fmean(sharpes), statistics.stdev(sharpes))
                  if len(sharpes) >= 2 else (math.nan, math.nan))
        e_n = own_expected(mu, sd, n)
        s = math.nan if rec["sharpe"] is None else rec["sharpe"]
        trial = [t for t in trials if t["id"] == aid]
        return {"section": section, "subject": aid, "cell": meta["cell"],
                "description": meta["description"], "model_id": meta["model_id"],
                "model_version": meta["model_version"], "admitted": meta["admitted"],
                "admission_score": trial[-1]["metrics_t"]["sharpe"], **rec,
                "breakeven_cost": be(aid), "S": rec["sharpe"], "E_N": real(e_n),
                "excess": real(s - e_n),
                "state_history": [{k: r[k] for k in ("date", "from", "to", "reason")}
                                  for r in life if r["id"] == aid]}

    def other(section, subject):
        return {"section": section, "subject": subject, **dict.fromkeys(APPROACH_ONLY),
                **record(subject), "breakeven_cost": be(subject) if section == "control"
                else None}

    live = sorted((approaches[a].meta["cell"], a) for a, s in states.items() if s == "live")
    dormant = sorted(a for a, s in states.items() if s == "dormant")
    rows = [approach("live", a) for _, a in live] + [approach("dormant", a) for a in dormant]
    rows += [other("control", f"bh:{s}") for s in SEEDS] + [other("control", s) for s in slots]
    rows += [other("portfolio", "portfolio"), other("portfolio", "portfolio_clean")]
    return rows, states


def table_json(state):
    return json.loads((state / "table" / TRACK / "table.json").read_text(encoding="utf-8"))


def test_table_json_holds_decision_71s_rows_in_order(ran, setup):
    state, early, late = ran
    got = table_json(state)
    n = len(ledger.read(state, TRACK, ledger.TRIALS))
    assert n == 6
    assert set(got) == {"track", "date", "N", "rows"}
    assert (got["track"], got["date"], got["N"]) == (TRACK, LAST.isoformat(), n)
    want, states = own_expected_rows(state, setup, n)
    # The state the gate asks for: live approaches in two cells, a dormant and
    # a retired one, the controls and the portfolio series.
    live_cells = {r["cell"] for r in want if r["section"] == "live"}
    assert len(live_cells) == 2
    assert [r["subject"] for r in want if r["section"] == "dormant"] == [late.displaced]
    retired = [a for a, s in states.items() if s == "retired"]
    assert len(retired) == 1
    assert [r["subject"] for r in got["rows"]] == [r["subject"] for r in want]
    assert retired[0] not in {r["subject"] for r in got["rows"]}
    sections = [r["section"] for r in got["rows"]]
    assert sections == sorted(sections, key=["live", "dormant", "control",
                                             "portfolio"].index)
    for g, w in zip(got["rows"], want, strict=True):
        assert set(g) == {"section", "subject", *FIELDS}, g["subject"]
        for k in ("section", "subject", *FIELDS):
            if k in REALS:
                assert eq(g[k], w[k]), (g["subject"], k, g[k], w[k])
            else:
                assert g[k] == w[k], (g["subject"], k, g[k], w[k])
    # Nulls where decision 71 says, and real values where the data allow.
    by = {r["subject"]: r for r in got["rows"]}
    for s in ("bh:SYNA", "rc:0", "portfolio", "portfolio_clean"):
        assert all(by[s][k] is None for k in APPROACH_ONLY)
    assert by["portfolio"]["breakeven_cost"] is None
    assert by["rc:0"]["breakeven_cost"] is not None
    new = by[late.id]
    assert new["days"] == 2 and new["E_N"] is not None and new["excess"] is not None
    assert 0 < by[early[0]]["clean_days"] < by[early[0]]["days"]


def test_the_deflated_figures_are_over_the_subjects_own_paper_days(ran, setup):
    """The late approach's ``E_N`` differs from one taken over every journaled day."""
    state, _, late = ran
    got = {r["subject"]: r for r in table_json(state)["rows"]}[late.id]
    held = paper.read(state, TRACK)
    sharpes = [own_sharpe(list(held[held["subject"] == f"rc:{k}"]
                               .sort_values("date")["net_1x"])) for k in range(4)]
    whole = own_expected(statistics.fmean(sharpes), statistics.stdev(sharpes), 6)
    assert not eq(got["E_N"], whole)


def own_cell(key, value):
    if value is None:
        return "-"
    if key in REALS:
        return f"{float(value):.4f}"
    if key == "state_history":
        return "; ".join(f"{h['date']} {h['from']}>{h['to']} {h['reason']}" for h in value)
    return str(value).replace("|", "\\|")


def test_table_md_holds_the_same_rows_with_four_decimals(ran):
    state, _, _ = ran
    got = table_json(state)
    text = (state / "table" / TRACK / "table.md").read_text(encoding="utf-8")
    assert not re.search(r"\d\d:\d\d", text)            # no time of day
    headings = [line[3:] for line in text.splitlines() if line.startswith("## ")]
    assert headings == ["live", "dormant", "control", "portfolio"]
    section = None
    rows = []
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:]
        elif line.startswith("| ") and not line.startswith("| subject |"):
            cells = re.split(r"(?<!\\) \| ", line[2:-2])
            rows.append((section, cells))
    assert len(rows) == len(got["rows"])
    for (section, cells), r in zip(rows, got["rows"], strict=True):
        assert section == r["section"]
        assert cells == [own_cell(k, r[k]) for k in ("subject", *FIELDS)], r["subject"]
        for k, c in zip(("subject", *FIELDS), cells, strict=True):
            if k in REALS and c != "-":
                assert re.fullmatch(r"-?\d+\.\d{4}", c), (k, c)
    assert any(c == "-" for _, cells in rows for c in cells)


def test_both_files_are_staged_and_committed_with_each_day(ran):
    state, _, _ = ran
    log = git(state, "log", "--format=%H %s").splitlines()
    commits = {line.split(" ", 1)[1]: line.split(" ", 1)[0] for line in log}
    for d in DAYS:
        sha = commits[f"run {TRACK} {d.isoformat()}"]
        changed = git(state, "show", "--name-only", "--format=", sha).split()
        assert f"table/{TRACK}/table.json" in changed and f"table/{TRACK}/table.md" in changed
        held = json.loads(git(state, "show", f"{sha}:table/{TRACK}/table.json"))
        assert held["date"] == d.isoformat()
    assert git(state, "show", f"HEAD:table/{TRACK}/table.json") == \
        (state / "table" / TRACK / "table.json").read_text(encoding="utf-8")
    assert git(state, "status", "--porcelain") == ""
    assert not (state / ".staging").exists()


def test_a_rerun_of_a_finished_day_writes_neither_file(tmp_path, ran, config):
    state = tmp_path / "state"
    shutil.copytree(ran[0], state)
    before, head = files(state), git(state, "rev-parse", "HEAD")
    assert replay(state, config, LAST, LAST) == 0
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", "2019-06-15T00:00:00+00:00", "run-day", "--day",
                 date(2019, 6, 11).isoformat()]) == 0
    assert files(state) == before and git(state, "rev-parse", "HEAD") == head


def test_every_control_slot_is_listed_in_slot_order_at_the_production_pool(tmp_path):
    """``controls.random_pool`` at its production value, 50: ``rc:10`` follows
    ``rc:9``; a state with no journaled day gives empty records."""
    cfg = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, cfg)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", cfg / "thresholds.toml")
    prod = journal.Setup.load(cfg, TRACK)
    assert int(prod.thresholds["controls.random_pool"]) == 50
    state = tmp_path / "state"
    assert main(["init-state", "--state", str(state), "--as-of", INIT_AS_OF]) == 0
    got = table.build(state, prod, FIRST, paper.build(pd.DataFrame(), 1, {}))
    assert [r["subject"] for r in got["rows"]] == (
        [f"bh:{s}" for s in SEEDS] + [f"rc:{k}" for k in range(50)]
        + ["portfolio", "portfolio_clean"])
    assert got["N"] == 0
    assert all(r["days"] == 0 and r["sharpe"] != r["sharpe"] and r["max_drawdown"] == 0.0
               for r in got["rows"])
