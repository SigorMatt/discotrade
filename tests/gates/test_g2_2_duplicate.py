"""Gate item G2.2: a duplicate with the sign flipped is caught by the correlation
gate and named; a submission correlated below the limit passes (DESIGN 18.3 G2.2,
12.3, 12.2 stage 5; decision 106 (a), (c) of 2026-10-14-m13; decision 98 (c),
101 (f); R-1).

As decision 106 (c) reads it: with an approach admitted from
``reference/trend_ma.py`` (parameters ``DUPLICATED``) in the state, its
sign-flipped duplicate ``tests/fixtures/strategies/trend_ma_flipped.py`` fails
stage ``correlation`` naming the approach's id, and ``changes_30.py``, whose
absolute correlation with it is below ``corr_max``, passes every stage; both
correlations are computed here from the two position series. The flipped one is
negative and its absolute value above ``corr_max`` (so that only the absolute
value catches it); the other's absolute value is below.

Everything runs through ``validation.sequence.validate`` on the container
backend, on ``test_synth``'s own W of ``DAY`` (2019-06-11 to 2019-07-08), at the
production thresholds (``corr_max`` 0.7, ``min_changes_w`` 30) and the limits of
``tests/fixtures/config/run.toml``. The test's own series are ``h`` from
``backtest.evaluate`` of the trusted texts loaded by ``strategy`` in this
process, concatenated in the track's order; its correlation is
``numpy.corrcoef``.

Seeds: the synthetic bars come from the fixture records' seeds, written here
(``SEEDS``) and checked. No random draw is made here except the reverse
sample's, whose seed is the text's own (decision 98 (a)). Time is read only
through ``--as-of`` and the ``FixedClock`` of the commits.
"""

from datetime import UTC, date, datetime

import numpy as np
import pytest
from error_texts import assert_clean, forbidden_words
from m2_harness import STRATEGIES, Backends, bars_state, commit, copy_config

from discotrade import backtest, journal, state
from discotrade.cli import REPO_ROOT
from discotrade.clock import FixedClock
from discotrade.strategy import load_strategy_file
from discotrade.validation import correlation, sequence
from discotrade.validation.sequence import Context

pytestmark = [pytest.mark.gate, pytest.mark.gate_m2, pytest.mark.container]

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
#: The day D (a Monday): W is 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
AS_OF = "2019-07-25T00:00:00+00:00"
COMMIT_CLOCK = FixedClock(datetime(2019, 7, 25, tzinfo=UTC))
ADMITTED = date(2019, 7, 1)
TREND_MA = REPO_ROOT / "reference" / "trend_ma.py"
DUPLICATED = {"fast": 6, "slow": 48}
FLIPPED = STRATEGIES / "trend_ma_flipped.py"
BELOW = STRATEGIES / "changes_30.py"
CORR_MAX = 0.7


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory.mktemp("cfg"))


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def live_state(tmp_path_factory, config, setup):
    """The track's bars and one live approach admitted from reference/trend_ma.py."""
    path = bars_state(tmp_path_factory.mktemp("live") / "state", config, TRACK, AS_OF, DAY,
                      COMMIT_CLOCK)
    aid = state.write_approach(
        path, source=TREND_MA.read_text(encoding="utf-8"), params=DUPLICATED,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description="a reference strategy", profile_version="w-test",
        admitted=ADMITTED, instruments=setup.instruments, spread_tables=setup.spread_tables)
    assert commit(path, TRACK, DAY, COMMIT_CLOCK) is not None
    return path, aid


@pytest.fixture
def backends(tmp_path):
    made = Backends(tmp_path / "jobs")
    yield made
    left = made.remove_left()
    assert left == [], f"containers left behind: {left}"


def own_h(state_dir, setup, source_path, params=None) -> np.ndarray:
    """The position series on W (``h``, concatenated in track order), by hand."""
    strategy = load_strategy_file(source_path, setup.thresholds)
    w = setup.track.windows(DAY).w
    return np.concatenate([
        backtest.evaluate(state_dir, setup.track, inst, setup.calendars[inst.calendar],
                          strategy, w, params, setup.spread_tables.get(inst.symbol)
                          ).rows["h"].to_numpy(dtype=float)
        for inst in setup.instruments])


def own_corr(a, b) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def test_the_facts_written_here(setup, live_state):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    w = setup.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)
    assert setup.thresholds["validation.corr_max"] == CORR_MAX
    path, aid = live_state
    assert [a.id for a in correlation.compared(path, TRACK, DAY)] == [aid]


def test_the_sign_flipped_duplicate_fails_stage_correlation_naming_the_approach(
        live_state, config, setup, backends):
    path, aid = live_state
    r = own_corr(own_h(path, setup, FLIPPED), own_h(path, setup, TREND_MA, DUPLICATED))
    # Negative: only the absolute value puts it above corr_max.
    assert r < -CORR_MAX, r
    b = backends.make(config)
    out = sequence.validate(Context(path, config, setup, DAY, b),
                            FLIPPED.read_text(encoding="utf-8"))
    assert (out.stage, out.rule) == ("correlation", "duplicate"), out.text
    assert out.text == ("correlation [duplicate]: the position series on W has an absolute "
                        f"correlation above corr_max with approach {aid}")
    # Every earlier stage ran and passed; the approach was run for the gate.
    assert b.modes == ["positions", "positions", "reverse_sample", "positions"]
    assert b.jobs[3][1] == [DUPLICATED]
    assert_clean([out.text], forbidden_words(path, TRACK, SEEDS))


def test_a_submission_correlated_below_the_limit_passes(live_state, config, setup, backends):
    path, _ = live_state
    r = own_corr(own_h(path, setup, BELOW), own_h(path, setup, TREND_MA, DUPLICATED))
    assert abs(r) < CORR_MAX, r
    b = backends.make(config)
    out = sequence.validate(Context(path, config, setup, DAY, b),
                            BELOW.read_text(encoding="utf-8"))
    assert out.ok and out.stage is None, out.text
    # The correlation gate ran: the approach's job is the last one.
    assert b.modes == ["positions", "positions", "reverse_sample", "positions"]
    assert b.jobs[3][1] == [DUPLICATED]
