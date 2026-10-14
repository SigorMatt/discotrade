"""The pieces of the correlation gate (DESIGN 12.3; decision 98 (c) of
2026-10-14-m12; decision 2026-10-12 63): the Pearson correlation, the
duplicate rule at the production ``corr_max`` (0.7, read from
``config/thresholds.toml``), the position series and which approaches are
compared.

The series here are written in the test or drawn from ``numpy``'s generator
with the seed ``SEED``; the state directories are plain pytest temporary
directories holding approaches written with ``state.write_approach`` and
lifecycle rows written with ``ledger.append`` (no bars, no git, no clock).
"""

import math
import tomllib
from datetime import date

import numpy as np
import pandas as pd
import pytest

from discotrade import backtest, ledger, state
from discotrade.cli import REPO_ROOT
from discotrade.config import load_track_config
from discotrade.validation import correlation

SEED = 20261014
CORR_MAX = tomllib.loads((REPO_ROOT / "config" / "thresholds.toml")
                         .read_text("utf-8"))["validation"]["corr_max"]
TRACK = "test_synth"
DAY = date(2019, 7, 15)


def own(a, b) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def test_corr_max_is_the_production_value():
    assert CORR_MAX == 0.7


def test_pearson_is_the_pearson_correlation():
    rng = np.random.default_rng(SEED)
    a = rng.normal(size=200)
    b = 0.5 * a + rng.normal(size=200)
    assert math.isclose(correlation.pearson(a, b), own(a, b), rel_tol=1e-12)
    assert math.isclose(correlation.pearson(a, -a), -1.0, rel_tol=1e-12)


def test_a_series_with_zero_deviation_gives_no_correlation():
    flat = np.zeros(10)
    other = np.arange(10, dtype=float)
    assert math.isnan(correlation.pearson(flat, other))
    assert math.isnan(correlation.pearson(other, np.full(10, 0.5)))
    assert math.isnan(correlation.pearson(np.ones(1), np.ones(1)))
    with pytest.raises(ValueError):
        correlation.pearson(np.zeros(3), np.zeros(4))


def test_a_pair_with_zero_deviation_is_not_a_duplicate():
    mine = np.arange(20, dtype=float)
    assert correlation.duplicate(mine, {"aflat": np.zeros(20)}, CORR_MAX) is None
    assert correlation.duplicate(np.zeros(20), {"a1": mine, "a2": -mine}, CORR_MAX) is None


def test_a_strong_negative_correlation_is_a_duplicate():
    mine = np.array([1.0, -1.0, 0.0, 1.0, 1.0, -1.0, 0.0, -1.0])
    named = correlation.duplicate(mine, {"a1": -mine}, CORR_MAX)
    assert named is not None and named[0] == "a1"
    assert math.isclose(named[1], own(mine, -mine), rel_tol=1e-12)


def test_only_an_absolute_correlation_above_corr_max_is_a_duplicate():
    rng = np.random.default_rng(SEED)
    mine = rng.normal(size=500)
    noise = rng.normal(size=500)
    # Scaled so the correlation is below and above corr_max.
    below = mine + 1.3 * noise
    above = mine + 0.8 * noise
    r_below, r_above = own(mine, below), own(mine, above)
    assert abs(r_below) < CORR_MAX < abs(r_above), (r_below, r_above)
    assert correlation.duplicate(mine, {"a1": below, "a2": -below}, CORR_MAX) is None
    assert correlation.duplicate(mine, {"a1": -above}, CORR_MAX)[0] == "a1"
    # Exactly corr_max is not above it.
    assert correlation.duplicate(mine, {"a1": above}, abs(correlation.pearson(mine, above))) \
        is None


def test_of_two_over_the_limit_the_larger_absolute_correlation_is_named_lowest_id_on_a_tie():
    rng = np.random.default_rng(SEED)
    mine = rng.normal(size=500)
    close = -mine + 0.1 * rng.normal(size=500)       # about -0.995
    closer = mine + 0.5 * rng.normal(size=500)       # about 0.9
    assert abs(own(mine, close)) > abs(own(mine, closer)) > CORR_MAX
    named = correlation.duplicate(mine, {"a0": closer, "a9": close}, CORR_MAX)
    assert named[0] == "a9"
    assert correlation.duplicate(mine, {"a5": -mine, "a3": mine}, CORR_MAX)[0] == "a3"


def evaluation(symbol, h) -> backtest.Evaluation:
    rows = pd.DataFrame({"h": np.asarray(h, dtype=float)})
    return backtest.Evaluation(symbol, rows, pd.DataFrame(), 0, np.zeros(0),
                               np.zeros(0, dtype=bool))


def test_the_position_series_is_h_concatenated_in_the_order_given():
    evs = [evaluation("X", [0.0, 1.0]), evaluation("Y", []), evaluation("Z", [-1.0])]
    assert correlation.position_series(evs).tolist() == [0.0, 1.0, -1.0]
    assert correlation.position_series([]).tolist() == []


@pytest.fixture
def setup_records():
    tc = load_track_config(REPO_ROOT / "tests" / "fixtures" / "config", TRACK)
    return tc


def write(path, tc, tag, admitted):
    return state.write_approach(
        path, source=(REPO_ROOT / "tests" / "fixtures" / "strategies" / "always_flat.py")
        .read_text(encoding="utf-8"), params={"tag": tag}, cell="trend/short",
        model_id="test-model", model_version="test-model-v0", cutoff=date(2019, 1, 1),
        description="a fixture", profile_version="w-test", admitted=admitted,
        instruments=tc.instruments, spread_tables={})


def test_live_and_dormant_approaches_are_compared_and_retired_ones_are_not(
        tmp_path, setup_records):
    tc = setup_records
    live = write(tmp_path, tc, 1, date(2019, 7, 1))
    dormant = write(tmp_path, tc, 2, date(2019, 7, 1))
    retired = write(tmp_path, tc, 3, date(2019, 7, 1))
    returned = write(tmp_path, tc, 4, date(2019, 7, 1))
    later = write(tmp_path, tc, 5, date(2019, 7, 16))     # admitted after D
    rows = [
        {"date": "2019-07-05", "from": "live", "id": dormant, "reason": "dormant",
         "to": "dormant", "adjusted": -0.5, "plain": -0.25},
        {"date": "2019-07-05", "from": "live", "id": retired, "reason": "failure: a test row",
         "to": "retired"},
        {"date": "2019-07-05", "from": "live", "id": returned, "reason": "failure: a test row",
         "to": "retired"},
        # A row dated after D is not in force on D.
        {"date": "2019-07-20", "from": "live", "id": live, "reason": "failure: a test row",
         "to": "retired"},
    ]
    ledger.append(tmp_path, TRACK, ledger.LIFECYCLE, rows)
    ids = [a.id for a in correlation.compared(tmp_path, TRACK, DAY)]
    assert ids == sorted([live, dormant])
    assert retired not in ids and returned not in ids and later not in ids


def test_without_approaches_nothing_is_compared(tmp_path):
    assert correlation.compared(tmp_path, TRACK, DAY) == []
