"""Scoring a generated candidate on T (DESIGN 16.1 step 5, 7.1, 8, 10.2, 10.3,
11.3, 12.4; owner's decisions O-4, O-11, O-13, O-17, O-18; decision 135 of
meta/decisions/decisions-2026-10-16-m17.md; I-3, I-7).

The state directory is a copy, under a pytest temporary directory, of
conftest's ``synth_bars_template``: the fixture track ``test_synth`` (four
synthetic instruments, seeds ``SEEDS``, asserted against the fixture records,
bar length 3600 s) fetched in-process at ``--as-of``
``2019-07-25T00:00:00+00:00``, so the store holds bars after ``D``. The day is
``DAY`` 2019-07-15 (W 2019-06-11 to 2019-07-08, T 2019-07-09 to 2019-07-15),
the configuration ``tests/fixtures/config/`` with the production
``config/thresholds.toml`` copied in under the temporary directory, unchanged
(``min_trades_t`` 30, asserted).

The candidate is generated, not written by hand: ``workers.generate.generate``
with ``ScriptedProvider`` over ``tests/fixtures/responses/duplicate_then_invalid``
on a state with no approach, so that its first response (the block of
``tests/fixtures/strategies/trend_ma_flipped.py``, byte for byte) passes
validation on W; the model is ``pool[(29 + 0) mod 3]``, the fixture
``models.toml``'s ``nvidia/nemotron-3-super-120b-a12b`` (cutoff 2026-02-28),
the version ``scripted``. Its sandbox backend is the child-process backend
(decision 104 (d): it runs only a text byte-identical to a repository file).

The test's own computation takes the evaluation rows from
``backtest.evaluate`` of the fixture file loaded by ``strategy`` on T, checks
their positions against its own ``h`` (``h(u0) = 0``, ``h(u) = p(u-1)``), reads
the stored bars from the month Parquet files and the roll records with
``pyarrow``, ``pandas`` and ``json``, and calls none of ``paper.adjusted``,
``paper.adjusted_rows``, ``paper.unit_bars``, ``paper.unit_returns``,
``paper.average_positions``, ``paper.window_units`` or
``paper.window_positions``, nor the function under test; equality is decision
39's. No clock is read and no random draw is made.
"""

from __future__ import annotations

import json
import math
import shutil
import tomllib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT, SYNTH_AS_OF, SYNTH_DAY, copy_template

from discotrade import backtest, daily, journal, ledger, lifecycle, state
from discotrade.config import load_calendar, load_models, load_track_config
from discotrade.sandbox.base import SandboxError, SandboxResult
from discotrade.sandbox.process import ProcessSandbox
from discotrade.strategy import load_strategy_file
from discotrade.workers import generate as gen
from discotrade.workers import pool as pl
from discotrade.workers.providers import ProviderError, ScriptedProvider

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
DAY = date(2019, 7, 15)
T_FIRST, T_LAST = date(2019, 7, 9), date(2019, 7, 15)
#: T's trading days on synth_week (Sunday 18:00 opens Monday's trading date).
T_DAYS = (date(2019, 7, 9), date(2019, 7, 10), date(2019, 7, 11), date(2019, 7, 12),
          date(2019, 7, 15))
#: The open of T's first bar (2019-07-08 18:00 New York) and the end of D
#: (2019-07-15 17:00 New York), in UTC (EDT is UTC-4).
T_OPEN = pd.Timestamp("2019-07-08T22:00:00Z")
D_END = pd.Timestamp("2019-07-15T21:00:00Z")
BAR = pd.Timedelta(seconds=3600)
CELL = ("trend", "short")
BRIEF = ("Write an approach of the family trend for the horizon short that differs "
         "from every line of the registry.")
MODEL = "nvidia/nemotron-3-super-120b-a12b"
CUTOFF = date(2026, 2, 28)
SCENARIO = REPO_ROOT / "tests" / "fixtures" / "responses" / "duplicate_then_invalid"
FLIPPED = REPO_ROOT / "tests" / "fixtures" / "strategies" / "trend_ma_flipped.py"
REGISTER = REPO_ROOT / "tests" / "fixtures" / "return_readers.toml"
#: DESIGN 10.2's trial row fields, as the keys decision 62 gives them.
TRIAL_KEYS = {"date", "id", "cell", "model_id", "model_version", "cutoff", "code_sha256",
              "profile_version", "cost_model", "config_hash", "grid", "params", "metrics_w",
              "metrics_t", "adjusted_w", "adjusted_t", "admitted", "reason", "displaced"}
#: DESIGN 8's metrics (with the day count and the 2x total the metrics carry).
METRIC_KEYS = {"days", "total_return", "total_return_2x", "sharpe", "sharpe_2x",
               "max_drawdown", "trades", "avg_holding_bars", "breakeven_cost", "fragile"}
ADJUSTED_KEYS = {"sharpe", "sharpe_2x", "total_return", "total_return_2x", "avg_position"}


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers (None for not a number)."""
    a = math.nan if a is None else float(a)
    b = math.nan if b is None else float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


class Recording:
    """A backend that records each job and runs it on the one it wraps."""

    def __init__(self, inner):
        self.inner = inner
        self.jobs = []

    def run(self, job):
        self.jobs.append(job)
        return self.inner.run(job)


class FailingOnT:
    """A backend whose every run fails at the dry run, as a sandbox error on T."""

    def __init__(self):
        self.jobs = []

    def run(self, job):
        self.jobs.append(job)
        return SandboxResult(error=SandboxError("dry_run", "out_of_range",
                                                "dry_run [out_of_range]: injected"))


# ------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def backend(tmp_path_factory):
    b = ProcessSandbox(tmp_path_factory.mktemp("jobs"), fork_server=True)
    yield b
    b.close()


@pytest.fixture(scope="module")
def state_dir(tmp_path_factory, synth_bars_template):
    assert (SYNTH_AS_OF, SYNTH_DAY) == ("2019-07-25T00:00:00+00:00", DAY)
    return copy_template(synth_bars_template, tmp_path_factory.mktemp("state") / "state")


@pytest.fixture(scope="module")
def generated(config, setup, state_dir, backend):
    models = load_models(config / "models.toml")
    pool = pl.day_pool(models, DAY, [m.id for m in models.models], ())
    tc = load_track_config(config, TRACK)
    calendars = {i.calendar: load_calendar(config / "calendars" / f"{i.calendar}.toml")
                 for i in tc.instruments}
    ordinal = pl.trading_ordinal(DAY, tc.track.epoch,
                                 lambda d: daily.is_trading_day(tc, calendars, d))
    staging = state_dir.parent / "gen-staging"
    out = gen.generate(state_dir, setup, DAY, CELL, BRIEF,
                       provider=ScriptedProvider(SCENARIO), provider_errors=(ProviderError,),
                       pool=pool, ordinal=ordinal, backend=backend, into=staging)
    assert out.candidate is not None, out.rows
    return out.candidate


@pytest.fixture(scope="module")
def scored(config, setup, state_dir, backend, generated):
    recording = Recording(backend)
    candidate = daily.score_on_t(state_dir, config, setup, DAY, generated, recording)
    return candidate, recording.jobs


# ------------------------------------------------------------- the test's own computation


def own_bars(state_dir, symbol) -> pd.DataFrame:
    files = sorted((state_dir / "bars" / TRACK / symbol).glob("*.parquet"))
    bars = pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True)
    return bars.sort_values("ts").reset_index(drop=True)


def own_gaps(state_dir, symbol) -> dict:
    path = state_dir / "rolls" / TRACK / f"{symbol}.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[(pd.Timestamp(r["ts"]), r["old"], r["new"])] = float(r["gap"])
    return out


def own_unit(state_dir, symbol) -> tuple[dict, dict]:
    """Per bar ts: the unit return (both terms of DESIGN 7.2 with h = 1), and
    whether a roll happens at that bar."""
    bars, gaps = own_bars(state_dir, symbol), own_gaps(state_dir, symbol)
    unit, rolled = {}, {}
    for k in range(len(bars)):
        ts = bars["ts"][k]
        o, c = float(bars["open"][k]), float(bars["close"][k])
        if k == 0:
            unit[ts], rolled[ts] = (1.0 * (c - o)) / o, False
            continue
        old, new = bars["contract"][k - 1], bars["contract"][k]
        gap = gaps[(ts, old, new)] if old != new else 0.0
        prev = float(bars["close"][k - 1]) + gap
        unit[ts] = (1.0 * (o - prev) + 1.0 * (c - o)) / o
        rolled[ts] = old != new
    return unit, rolled


def own_sharpe(d) -> float:
    x = [float(v) for v in d]
    if len(x) < 2:
        return math.nan
    sd = float(np.std(x, ddof=1))
    if all(v == x[0] for v in x) or not sd > 1e-12 * max(abs(v) for v in x):
        return math.nan
    return float(np.mean(x)) / sd * math.sqrt(252)


def own_daily(rows: list[pd.DataFrame], column: str) -> dict:
    days = sorted({d for r in rows for d in r["date"]})
    return {d: sum(float(r[column][r["date"] == d].sum()) for r in rows) / len(rows)
            for d in days}


@pytest.fixture(scope="module")
def own(state_dir, setup, generated):
    """The candidate's plain and adjusted figures on T, by hand."""
    strategy = load_strategy_file(FLIPPED, setup.thresholds)
    t = setup.track.windows(DAY).t
    symbols = [i.symbol for i in setup.instruments]
    rows = [backtest.evaluate(state_dir, setup.track, inst, setup.calendars[inst.calendar],
                              strategy, t, dict(generated.params),
                              setup.spread_tables.get(inst.symbol)).rows
            for inst in setup.instruments]
    units = {s: own_unit(state_dir, s) for s in symbols}
    held = {}
    for s, r in zip(symbols, rows, strict=True):
        # T scored on its own (DESIGN 7.1): h(u0) = 0, h(u) = p(u-1).
        p = r["p"].to_numpy(dtype=float)
        h = np.concatenate([[0.0], p[:-1]])
        assert r["date"].iloc[0] == T_FIRST and r["date"].iloc[-1] == T_LAST, s
        assert np.array_equal(r["h"].to_numpy(dtype=float), h), s
        held[s] = h
    hbar = {s: float(held[s].mean()) for s in symbols}
    out = {"hbar": hbar}
    for column in ("net_1x", "net_2x"):
        day_sums = own_daily(rows, column)
        exposure = {}
        for d in day_sums:
            total = 0.0
            for s, r in zip(symbols, rows, strict=True):
                unit = units[s][0]
                big_r = sum(unit[ts] for ts, dd in zip(r["ts"], r["date"], strict=True)
                            if dd == d)
                total += hbar[s] * big_r
            exposure[d] = total / len(rows)
        out[column] = {"plain": list(day_sums.values()),
                       "adjusted": [day_sums[d] - exposure[d] for d in day_sums]}
    one, two = out["net_1x"], out["net_2x"]
    lengths = []
    gross = turnover = 0.0
    for s, r in zip(symbols, rows, strict=True):
        h = held[s]
        run = 0
        for k, v in enumerate(np.sign(h)):
            if v != 0 and run and v == np.sign(h[k - 1]):
                run += 1
                continue
            if run:
                lengths.append(run)
            run = 1 if v != 0 else 0
        if run:
            lengths.append(run)
        gross += float(r["gross"].sum())
        turnover += float(r["trade"].sum())
        rolled = units[s][1]
        for k, ts in enumerate(r["ts"]):
            if rolled[ts]:
                turnover += 2.0 * abs(h[k - 1] if k > 0 else 0.0)
    running = np.concatenate([[0.0], np.cumsum(one["plain"])])
    m = {
        "days": len(one["plain"]),
        "total_return": float(sum(one["plain"])), "total_return_2x": float(sum(two["plain"])),
        "sharpe": own_sharpe(one["plain"]), "sharpe_2x": own_sharpe(two["plain"]),
        "max_drawdown": float(np.max(np.maximum.accumulate(running) - running)),
        "trades": int(sum(int((r["trade"] > 1e-9).sum()) for r in rows)),
        "avg_holding_bars": float(np.mean(lengths)) if lengths else math.nan,
        "breakeven_cost": gross / turnover * 10000.0 if turnover > 0 else math.nan,
    }
    m["fragile"] = bool(m["total_return"] > 0 and m["total_return_2x"] < 0)
    out["metrics"] = m
    out["adjusted"] = {"sharpe": own_sharpe(one["adjusted"]),
                       "sharpe_2x": own_sharpe(two["adjusted"]),
                       "total_return": float(sum(one["adjusted"])),
                       "total_return_2x": float(sum(two["adjusted"]))}
    return out


# ------------------------------------------------------------- tests


def test_the_seeds_window_thresholds_and_generated_candidate_are_the_ones_written_here(
        setup, generated):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    assert setup.track.bar_seconds == 3600
    t = setup.track.windows(DAY).t
    assert (t.first, t.last) == (T_FIRST, T_LAST)
    assert setup.thresholds["admission.min_trades_t"] == 30
    assert generated.source == FLIPPED.read_text(encoding="utf-8")
    assert dict(generated.params) == {"fast": 6, "slow": 48}
    assert (generated.model_id, generated.model_version, generated.cutoff) == (
        MODEL, "scripted", CUTOFF)


def test_metrics_t_and_adjusted_t_equal_the_test_s_own_computation(scored, own, setup):
    candidate, _ = scored
    metrics_t = dict(candidate.metrics_t)
    assert set(metrics_t) == METRIC_KEYS
    for key, value in own["metrics"].items():
        if key in ("days", "trades", "fragile"):
            assert metrics_t[key] == value, key
        else:
            assert eq(metrics_t[key], value), key
    assert metrics_t["days"] == len(T_DAYS)
    adjusted_t = dict(candidate.adjusted_t)
    assert set(adjusted_t) == ADJUSTED_KEYS
    for key, value in own["adjusted"].items():
        assert eq(adjusted_t[key], value), key
    # The average positions are taken over T (O-11), not over W.
    assert list(adjusted_t["avg_position"]) == [i.symbol for i in setup.instruments]
    for symbol, value in own["hbar"].items():
        assert eq(adjusted_t["avg_position"][symbol], value), symbol


def test_t_is_run_in_one_positions_job_holding_no_bar_after_the_end_of_d(
        scored, state_dir, generated):
    _, jobs = scored
    assert len(jobs) == 1
    job = jobs[0]
    assert job.mode == "positions"
    assert job.param_sets == (dict(generated.params),)
    assert job.source == generated.source
    assert [i.symbol for i in job.instruments] == list(SEEDS)
    for inst in job.instruments:
        ts = pd.to_datetime(inst.bars["ts"], utc=True)
        assert ts.iloc[inst.first] == T_OPEN, inst.symbol
        assert ts.iloc[-1] + BAR == D_END, inst.symbol
        assert (ts + BAR <= D_END).all(), inst.symbol
        assert inst.first > 0, inst.symbol            # warm-up context before T
        # The store holds later bars: the job left them out.
        stored = pd.to_datetime(own_bars(state_dir, inst.symbol)["ts"], utc=True)
        assert (stored + BAR > D_END).any(), inst.symbol


def test_the_candidate_carries_every_field_of_decision_135_c(scored, generated):
    candidate, _ = scored
    assert isinstance(candidate, lifecycle.Candidate)
    assert candidate.source == generated.source
    assert dict(candidate.params) == {"fast": 6, "slow": 48}
    assert candidate.cell == "trend/short"
    assert candidate.model_id == MODEL
    assert candidate.model_version == "scripted"
    assert candidate.cutoff == CUTOFF
    assert candidate.description == generated.description
    assert candidate.description
    assert candidate.profile_version == generated.profile_version
    assert tuple(candidate.t_days) == T_DAYS
    # The grid and the W figures are the generation's (O-17).
    assert candidate.grid == generated.grid
    assert candidate.grid is not None and candidate.grid["fixed"] == {"fast": 6, "slow": 48}
    assert candidate.metrics_w == generated.metrics_w
    assert candidate.adjusted_w == generated.adjusted_w
    assert candidate.metrics_w is not None and candidate.adjusted_w is not None


def test_admit_writes_a_trial_row_and_an_approach_holding_the_model_version_and_cutoff(
        scored, setup, own, tmp_path, synth_bars_template):
    candidate, _ = scored
    # A state of its own, so that the admission writes into a fresh staging directory.
    path = copy_template(synth_bars_template, tmp_path / "state")
    staging = tmp_path / "staging"
    admission = lifecycle.admit(path, setup, candidate, DAY, into=staging)
    # The test's own figures admit it: a positive adjusted Sharpe, at least
    # min_trades_t trades on T, and a free slot in an empty cell.
    assert own["adjusted"]["sharpe"] > 0 and own["metrics"]["trades"] >= 30
    assert (admission.admitted, admission.reason) == (True, "free_slot")
    rows = ledger.read(path, TRACK, ledger.TRIALS, into=staging)
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == TRIAL_KEYS
    assert (row["date"], row["cell"]) == (DAY.isoformat(), "trend/short")
    assert (row["model_id"], row["model_version"], row["cutoff"]) == (
        MODEL, "scripted", CUTOFF.isoformat())
    assert row["id"] == state.approach_id(candidate.source, candidate.params)
    assert row["params"] == {"fast": 6, "slow": 48}
    assert row["metrics_t"] == dict(candidate.metrics_t)
    assert row["adjusted_t"] == dict(candidate.adjusted_t)
    assert row["grid"] == candidate.grid
    meta = json.loads((staging / "approaches" / row["id"] / "meta.json")
                      .read_text(encoding="utf-8"))
    assert (meta["model_id"], meta["model_version"], meta["cutoff"]) == (
        MODEL, "scripted", CUTOFF.isoformat())


def test_a_sandbox_error_on_t_is_raised_and_recorded_as_no_worker_outcome(
        config, setup, state_dir, generated):
    calls = ledger.ledger_path(state_dir, TRACK, ledger.CALLS)
    before = calls.read_bytes() if calls.exists() else None
    files = sorted(p.relative_to(state_dir) for p in Path(state_dir).rglob("*"))
    failing = FailingOnT()
    with pytest.raises(daily.DailyError, match="while scored on T"):
        daily.score_on_t(state_dir, config, setup, DAY, generated, failing)
    assert len(failing.jobs) == 1
    assert (calls.read_bytes() if calls.exists() else None) == before
    assert sorted(p.relative_to(state_dir) for p in Path(state_dir).rglob("*")) == files


def test_the_scoring_function_is_registered_a_producer():
    with open(REGISTER, "rb") as f:
        entries = tomllib.load(f)["reader"]
    classes = {(e["module"], e["function"]): e["class"] for e in entries}
    assert classes[("discotrade.daily", "score_on_t")] == "producer"
    # Admission stays the adjusted reader it is (decision 135 (d)).
    assert classes[("discotrade.lifecycle", "admit")] == "adjusted"
