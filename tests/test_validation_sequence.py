"""The validation sequence: determinism, activity, the correlation gate and the
five stages in order (DESIGN 12.2 stages 1, 3, 4 and 5, 12.3; R-1; decision 98
of 2026-10-14-m12; decisions 2026-10-12 25, 63; decision 95 (e); I-5, I-8).

The state directory is made by ``init-state`` and filled by ``bars fetch`` on
the fixture track ``test_synth`` (four synthetic instruments, every one
shortable; seeds ``SEEDS``, those of the fixture records, asserted), both run
in-process (``discotrade.cli.main``) with the clock given by ``--as-of``
``AS_OF``, under a pytest temporary directory; approaches are written with
``state.write_approach`` (decision 48), lifecycle rows with ``ledger.append``,
and the state is committed with ``state.commit`` under a ``FixedClock``. Every
git this file runs (through ``init-state`` and ``state.commit``) is on local
paths with ``GIT_ALLOW_PROTOCOL=file`` (decision 47). The states of the
correlation tests are copies of that directory under the temporary directory.

Every stage runs on W of the day ``DAY`` (2019-06-11 to 2019-07-08, the track's
own W, 433 window bars per instrument) at the production thresholds
(``config/thresholds.toml`` copied into the fixture configuration:
``min_changes_w`` 30, ``corr_max`` 0.7) and the limits of
``tests/fixtures/config/run.toml``, on the child-process backend unless a test
says otherwise; job directories go under a pytest temporary directory.

The test's own series come from ``backtest.evaluate`` of the texts loaded by
``strategy`` in this process (``own_h``), not from the sandbox or the
sequence; its correlations are ``numpy.corrcoef`` of two such series, its
change counts the rows with ``trade > 1e-9``. No random draw is made here
except the reverse sample's, whose seed is pinned.
"""

import hashlib
import math
import re
import shutil
import tomllib
from datetime import UTC, date, datetime

import numpy as np
import pyarrow.parquet as pq
import pytest

from discotrade import backtest, journal, ledger, state
from discotrade.cli import REPO_ROOT, main
from discotrade.clock import FixedClock
from discotrade.sandbox.process import ProcessSandbox
from discotrade.strategy import load_strategy_file
from discotrade.validation import correlation, sequence
from discotrade.validation.sequence import Context, Submission

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
TREND_MA = REPO_ROOT / "reference" / "trend_ma.py"
TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
#: The day D (a Monday): W is 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
WINDOW_BARS = 433
AS_OF = "2019-07-25T00:00:00+00:00"
COMMIT_CLOCK = FixedClock(datetime(2019, 7, 25, tzinfo=UTC))
ADMITTED = date(2019, 7, 1)
#: The approach the flipped fixture duplicates, and a second one close to it.
DUPLICATED = {"fast": 6, "slow": 48}
NEIGHBOUR = {"fast": 12, "slow": 48}
KEEPS_STATE = STRATEGIES / "keeps_state.py"
CHANGES_29 = STRATEGIES / "changes_29.py"
CHANGES_30 = STRATEGIES / "changes_30.py"
FLIPPED = STRATEGIES / "trend_ma_flipped.py"
#: The reverse sample of keeps_state.py's text (decision 98 (a)), pinned.
KEEPS_STATE_SEED = int("f13f40bf245d0021", 16)
KEEPS_STATE_SAMPLE = {
    "SYNA": (420, 395, 357, 317, 305, 270, 238, 225, 223, 187, 167, 120, 97, 87, 83, 47, 46,
             39, 11, 6),
    "SYNB": (405, 376, 372, 370, 330, 299, 264, 245, 244, 227, 210, 195, 186, 148, 142, 138,
             109, 80, 46, 42),
    "SYNC": (421, 419, 408, 380, 362, 339, 313, 290, 274, 245, 230, 163, 149, 121, 94, 83, 74,
             72, 59, 53),
    "SYND": (431, 422, 396, 368, 364, 363, 355, 344, 321, 296, 281, 269, 245, 226, 218, 213,
             120, 49, 36, 30),
}
ERROR_TEXTS: list[str] = []


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
def bars_state(tmp_path_factory, config):
    """A state directory with the track's bars and no approach, committed."""
    path = tmp_path_factory.mktemp("bars") / "state"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        assert main(["init-state", "--state", str(path), "--as-of", AS_OF]) == 0
        assert main(["--state", str(path), "--config", str(config), "--track", TRACK,
                     "--as-of", AS_OF, "bars", "fetch"]) == 0
        state.commit(path, TRACK, DAY, COMMIT_CLOCK)
    return path


def admit(path, setup, params, source_path=TREND_MA) -> str:
    return state.write_approach(
        path, source=source_path.read_text(encoding="utf-8"), params=params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description="a reference strategy", profile_version="w-test",
        admitted=ADMITTED, instruments=setup.instruments, spread_tables=setup.spread_tables)


def lifecycle_row(path, aid, to, reason, day=date(2019, 7, 5), **figures):
    row = {"date": day.isoformat(), "from": "live", "id": aid, "reason": reason, "to": to,
           **figures}
    ledger.append(path, TRACK, ledger.LIFECYCLE, [row])


def copy_state(bars_state, tmp_path_factory, name):
    path = tmp_path_factory.mktemp(name) / "state"
    shutil.copytree(bars_state, path)
    return path


@pytest.fixture(scope="module")
def live_state(bars_state, tmp_path_factory, setup):
    """One live approach admitted from reference/trend_ma.py at DUPLICATED, committed."""
    path = copy_state(bars_state, tmp_path_factory, "live")
    aid = admit(path, setup, DUPLICATED)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        assert state.commit(path, TRACK, DAY, COMMIT_CLOCK) is not None
    return path, aid


@pytest.fixture(scope="module")
def scratch(tmp_path_factory):
    return tmp_path_factory.mktemp("jobs")


class Recorder:
    """The child-process backend, recording each job's mode, parameter sets and
    reverse sample (None in mode ``positions``)."""

    def __init__(self, scratch):
        self.inner = ProcessSandbox(scratch)
        self.jobs = []

    def run(self, job):
        self.jobs.append((job.mode, [dict(p) for p in job.param_sets],
                          {i.symbol: i.sample for i in job.instruments}
                          if job.mode == "reverse_sample" else None))
        return self.inner.run(job)

    @property
    def modes(self):
        return [m for m, _, _ in self.jobs]


def context(path, config, setup, backend):
    return Context(path, config, setup, DAY, backend)


def text(path) -> str:
    return path.read_text(encoding="utf-8")


def snapshot(path) -> dict:
    """Every file's bytes under ``path``, ``.git`` included."""
    return {str(p.relative_to(path)): p.read_bytes()
            for p in sorted(path.rglob("*")) if p.is_file()}


def head(path) -> bytes:
    ref = (path / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    assert ref.startswith("ref: ")
    return (path / ".git" / ref[len("ref: "):]).read_bytes()


_OWN: dict = {}


def own_h(state_dir, setup, source_path, params=None) -> tuple[np.ndarray, list[int]]:
    """The test's own position series on W (``h`` concatenated in track order)
    and change count per instrument, from ``backtest.evaluate`` in this process.
    Every state of this file holds the same bars, so each is computed once."""
    key = (str(source_path), tuple(sorted((params or {}).items())))
    if key not in _OWN:
        strategy = load_strategy_file(source_path, setup.thresholds)
        w = setup.track.windows(DAY).w
        evs = [backtest.evaluate(state_dir, setup.track, inst, setup.calendars[inst.calendar],
                                 strategy, w, params, setup.spread_tables.get(inst.symbol))
               for inst in setup.instruments]
        h = np.concatenate([ev.rows["h"].to_numpy(dtype=float) for ev in evs])
        _OWN[key] = (h, [int((ev.rows["trade"] > 1e-9).sum()) for ev in evs])
    return _OWN[key]


def own_corr(a, b) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def test_the_seeds_window_and_thresholds_are_the_ones_written_here(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    w = setup.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)
    assert setup.thresholds["validation.min_changes_w"] == 30
    assert setup.thresholds["validation.corr_max"] == 0.7
    production = tomllib.loads((REPO_ROOT / "config" / "thresholds.toml").read_text("utf-8"))
    assert production["validation"]["min_changes_w"] == 30
    assert production["validation"]["corr_max"] == 0.7


# ------------------------------------------------------------- the full sequence passes


@pytest.fixture(scope="module")
def passing(live_state, config, setup, scratch):
    """changes_30.py through the whole sequence, with the live approach in the
    state; the state's bytes and HEAD before and after."""
    path, _ = live_state
    before, head_before = snapshot(path), head(path)
    rec = Recorder(scratch)
    out = sequence.validate(context(path, config, setup, rec), text(CHANGES_30))
    return out, rec, before, head_before


def test_a_valid_fixture_passes_every_stage(passing, live_state, setup):
    out, rec, _, _ = passing
    assert out.ok and out.stage is None, out.text
    # Stage 2's job, the second run, the reverse sample, the approach's run.
    assert rec.modes == ["positions", "positions", "reverse_sample", "positions"]
    assert rec.jobs[3][1] == [DUPLICATED]


def test_exactly_min_changes_w_position_changes_pass_the_activity_stage(
        passing, live_state, setup):
    # R-1 at the production value 30, summed over the basket: no instrument makes 30 alone.
    path, _ = live_state
    _, counts = own_h(path, setup, CHANGES_30)
    assert sum(counts) == 30 and max(counts) < 30, counts
    out = passing[0]
    assert sequence.changes(out.evaluations) == 30
    assert out.metrics_w["trades"] == 30


def test_a_fixture_below_corr_max_with_the_approach_passes_the_correlation_gate(
        passing, live_state, setup):
    path, _ = live_state
    mine, _ = own_h(path, setup, CHANGES_30)
    theirs, _ = own_h(path, setup, TREND_MA, DUPLICATED)
    r = own_corr(mine, theirs)
    assert abs(r) < 0.7, r
    assert passing[0].ok


def same(a, b) -> bool:
    """Equality of two results, a float that is not a number equal to another."""
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return a == b


def test_the_sequence_returns_decision_97_e_s_result(passing, live_state, config, setup,
                                                     scratch):
    out = passing[0]
    result = out.result()
    assert set(result) == {"grid", "metrics_w", "adjusted_w"}
    assert result["grid"]["grid"] is None
    assert result["grid"]["fixed"] == {"lookback": 215}
    assert [r["params"] for r in result["grid"]["results"]] == [{"lookback": 215}]
    assert list(result["adjusted_w"]["avg_position"]) == list(SEEDS)
    path, _ = live_state
    alone = sequence.dry_run_and_grid(context(path, config, setup, ProcessSandbox(scratch)),
                                      Submission.from_source(text(CHANGES_30)))
    assert same(result, alone.result())


def test_the_sequence_writes_nothing_to_the_state_directory(passing, live_state):
    path, _ = live_state
    _, _, before, head_before = passing
    assert snapshot(path) == before
    assert head(path) == head_before


# ------------------------------------------------------------- each stage fails and stops there


def test_stage_static_fails_and_stops_there(live_state, config, setup, scratch):
    path, _ = live_state
    rec = Recorder(scratch)
    out = sequence.validate(context(path, config, setup, rec), text(STRATEGIES / "six_params.py"))
    assert (out.stage, out.rule) == ("static", "max_params")
    assert out.text == "static [max_params]: line 1: PARAMS has 6 entries; at most 5 are allowed"
    assert rec.jobs == []
    ERROR_TEXTS.append(out.text)


def test_a_text_that_does_not_parse_fails_stage_static(live_state, config, setup, scratch):
    path, _ = live_state
    rec = Recorder(scratch)
    out = sequence.validate(context(path, config, setup, rec), "PARAMS = {\n")
    assert (out.stage, out.rule) == ("static", "parse")
    assert rec.jobs == []
    ERROR_TEXTS.append(out.text)


def test_stage_dry_run_fails_and_stops_there(live_state, config, setup, scratch):
    path, _ = live_state
    rec = Recorder(scratch)
    out = sequence.validate(context(path, config, setup, rec),
                            text(STRATEGIES / "grid_out_of_range.py"))
    assert (out.stage, out.rule) == ("dry_run", "out_of_range")
    assert out.text.startswith("dry_run [out_of_range]: ")
    assert rec.modes == ["positions"]
    ERROR_TEXTS.append(out.text)


@pytest.fixture(scope="module")
def stateful(live_state, config, setup, scratch):
    path, _ = live_state
    rec = Recorder(scratch)
    return sequence.validate(context(path, config, setup, rec), text(KEEPS_STATE)), rec


def test_a_fixture_keeping_state_passes_static_and_fails_determinism_on_the_reverse_sample(
        stateful, setup):
    from discotrade.validation import static
    assert static.check(text(KEEPS_STATE), setup.thresholds) is None
    out, rec = stateful
    assert (out.stage, out.rule) == ("determinism", "reverse_sample")
    assert out.text == ("determinism [reverse_sample]: calling a sample of bars in reverse "
                        "order inside one process gave another position at window bar 420 "
                        "(the function keeps state between calls)")
    # Stage 2, the second run (which agreed), the reverse sample; no later stage ran.
    assert rec.modes == ["positions", "positions", "reverse_sample"]
    ERROR_TEXTS.append(out.text)


def test_the_reverse_sample_is_drawn_as_decision_98_a_says(stateful):
    source = text(KEEPS_STATE)
    seed = int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:16], 16)
    assert seed == KEEPS_STATE_SEED == sequence.sample_seed(source)
    assert sequence.REVERSE_SAMPLE == 20
    counts = dict.fromkeys(SEEDS, WINDOW_BARS)
    assert sequence.reverse_sample(source, counts) == KEEPS_STATE_SAMPLE
    # The same draw, made here: one generator, the instruments in track order.
    rng = np.random.default_rng(seed)
    for symbol in SEEDS:
        drawn = rng.choice(WINDOW_BARS, size=20, replace=False)
        assert tuple(sorted((int(i) for i in drawn), reverse=True)) == \
            KEEPS_STATE_SAMPLE[symbol]
    # And it is the sample the reverse job carried.
    _, rec = stateful
    assert rec.jobs[2][2] == KEEPS_STATE_SAMPLE
    assert rec.jobs[2][1] == [{"scale": 1000}]


class Perturbing:
    """The child-process backend, but the second job in mode ``positions`` it runs
    gets another target at window bar 5 of its first instrument."""

    def __init__(self, scratch):
        self.inner = ProcessSandbox(scratch)
        self.positions = 0

    def run(self, job):
        result = self.inner.run(job)
        if job.mode == "positions":
            self.positions += 1
            if self.positions == 2:
                key = (0, job.instruments[0].symbol)
                targets = result.targets[key].copy()
                targets[5] = 0.5 if targets[5] != 0.5 else 0.25
                result.targets[key] = targets
        return result


def test_the_second_run_is_a_new_job_whose_positions_must_equal_the_first(
        live_state, config, setup, scratch):
    path, _ = live_state
    backend = Perturbing(scratch)
    out = sequence.validate(context(path, config, setup, backend),
                            text(STRATEGIES / "always_flat.py"))
    assert backend.positions == 2
    assert (out.stage, out.rule) == ("determinism", "rerun")
    assert out.text == ("determinism [rerun]: a second run on W in a new sandbox gave other "
                        "positions, first at window bar 5")
    ERROR_TEXTS.append(out.text)


def test_stage_activity_fails_below_min_changes_w_and_stops_there(
        live_state, config, setup, scratch):
    path, _ = live_state
    _, counts = own_h(path, setup, CHANGES_29)
    assert sum(counts) == 29, counts
    rec = Recorder(scratch)
    out = sequence.validate(context(path, config, setup, rec), text(CHANGES_29))
    assert (out.stage, out.rule) == ("activity", "min_changes_w")
    assert out.text == ("activity [min_changes_w]: 29 position changes on W summed over the "
                        "basket; at least min_changes_w (30) are needed")
    # The live approach was never run: the correlation gate did not start.
    assert rec.modes == ["positions", "positions", "reverse_sample"]
    ERROR_TEXTS.append(out.text)


# ------------------------------------------------------------- the correlation gate


def test_the_sign_flipped_duplicate_fails_stage_correlation_naming_the_approach(
        live_state, config, setup, scratch):
    path, aid = live_state
    mine, counts = own_h(path, setup, FLIPPED)
    theirs, _ = own_h(path, setup, TREND_MA, DUPLICATED)
    r = own_corr(mine, theirs)
    assert r < -0.7 and abs(r) > 0.7, r
    assert sum(counts) >= 30
    rec = Recorder(scratch)
    out = sequence.validate(context(path, config, setup, rec), text(FLIPPED))
    assert (out.stage, out.rule) == ("correlation", "duplicate")
    assert out.text == ("correlation [duplicate]: the position series on W has an absolute "
                        f"correlation above corr_max with approach {aid}")
    assert rec.modes == ["positions", "positions", "reverse_sample", "positions"]
    ERROR_TEXTS.append(out.text)


@pytest.fixture(scope="module")
def flipped_first(bars_state, config, setup, scratch):
    """The flipped fixture through stage 2 (the state holds no approach)."""
    out = sequence.dry_run_and_grid(context(bars_state, config, setup, ProcessSandbox(scratch)),
                                    Submission.from_source(text(FLIPPED)))
    assert out.ok, out.text
    return out


def test_a_retired_approach_is_not_compared_and_a_flat_one_is_not_a_duplicate(
        bars_state, tmp_path_factory, config, setup, scratch, flipped_first):
    path = copy_state(bars_state, tmp_path_factory, "retired")
    retired = admit(path, setup, DUPLICATED)
    lifecycle_row(path, retired, "retired", "failure: a test row")
    flat = admit(path, setup, {"tag": 1}, STRATEGIES / "always_flat.py")
    rec = Recorder(scratch)
    out = sequence.correlation_gate(context(path, config, setup, rec), flipped_first)
    assert out is None
    # Only the flat approach ran: its series has zero deviation, so the pair is no duplicate.
    assert [p for _, p, _ in rec.jobs] == [[{"tag": 1}]]
    assert [a.id for a in correlation.compared(path, TRACK, DAY)] == [flat]


def test_a_dormant_approach_is_compared_and_of_two_over_the_limit_the_larger_is_named(
        bars_state, tmp_path_factory, config, setup, scratch, flipped_first):
    # One state for both: the duplicated approach is dormant, its neighbour live, and
    # both are over the limit; naming the dormant one shows it was compared, and that
    # the larger absolute correlation wins over the lower id.
    path = copy_state(bars_state, tmp_path_factory, "two")
    duplicated = admit(path, setup, DUPLICATED)
    neighbour = admit(path, setup, NEIGHBOUR)
    lifecycle_row(path, duplicated, "dormant", "dormant", adjusted=-0.5, plain=-0.25)
    assert [a.id for a in correlation.compared(path, TRACK, DAY)] == [neighbour, duplicated]
    mine, _ = own_h(path, setup, FLIPPED)
    r_dup = own_corr(mine, own_h(path, setup, TREND_MA, DUPLICATED)[0])
    r_nbr = own_corr(mine, own_h(path, setup, TREND_MA, NEIGHBOUR)[0])
    assert abs(r_nbr) > 0.7 and abs(r_dup) > abs(r_nbr), (r_dup, r_nbr)
    # The one named is not the lowest id: the lowest id would name the neighbour.
    assert neighbour < duplicated
    rec = Recorder(scratch)
    out = sequence.correlation_gate(context(path, config, setup, rec), flipped_first)
    assert out is not None
    assert (out.stage, out.rule) == ("correlation", "duplicate")
    assert out.text.endswith(f"with approach {duplicated}")
    assert sorted(p[0]["fast"] for _, p, _ in rec.jobs) == [6, 12]
    ERROR_TEXTS.append(out.text)


# ------------------------------------------------------------- decision 95 (e)


def test_zz_no_error_text_holds_a_symbol_venue_contract_or_date(bars_state):
    # Runs after the failing tests of this file (pytest keeps file order).
    assert len(ERROR_TEXTS) >= 8
    words = set()
    for root in (REPO_ROOT / "config", FIXTURE_CONFIG):
        for path in sorted((root / "instruments").glob("*.toml")):
            record = tomllib.loads(path.read_text(encoding="utf-8"))
            words |= {record["symbol"], record["venue"]}
            words |= {str(v) for k, v in record.get("source", {}).items()
                      if "contract" in k or k in ("dataset", "symbol")}
    for symbol in SEEDS:
        for f in sorted((bars_state / "bars" / TRACK / symbol).glob("*.parquet")):
            words |= set(pq.read_table(f).column("contract").to_pylist())
    words = {w for w in words if w}
    assert {"SYNA", "SYNA-2019-06", "MES"} <= words
    for message in ERROR_TEXTS:
        for word in words:
            assert word not in message, (word, message)
        assert not re.search(r"\d{4}-\d{2}|\d{1,2}:\d{2}|\d\.\d", message), message
