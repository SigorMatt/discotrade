"""The reference strategies under ``reference/`` (DESIGN 3, 6.1, 18.3 G0.1;
decision 2026-10-12 21).

Each file passes the loader with the repository's thresholds, says its rule
in a docstring, and gives a target within [-1, 1] on frames built by hand.
"""

import ast

import numpy as np
import pandas as pd
import pytest

from discotrade.cli import REPO_ROOT
from discotrade.config import load_thresholds
from discotrade.strategy import load_strategy_file

REFERENCE = REPO_ROOT / "reference"
FILES = ("trend_ma.py", "zscore_reversal.py", "hour_of_day.py")


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds(REPO_ROOT / "config" / "thresholds.toml")


def frame(close, hour=None):
    close = np.asarray(close, dtype=float)
    n = len(close)
    return pd.DataFrame({
        "open": close, "high": close, "low": close, "close": close,
        "volume": np.full(n, 1000.0),
        "hour": np.asarray(hour if hour is not None else np.arange(n) % 24, dtype=np.int64),
        "weekday": np.zeros(n, dtype=np.int64),
    })


def test_reference_holds_exactly_the_three_strategies():
    assert sorted(p.name for p in REFERENCE.glob("*.py")) == sorted(FILES)


@pytest.mark.parametrize("name", FILES)
def test_each_file_passes_the_loader_with_the_repository_thresholds(name, thresholds):
    strat = load_strategy_file(REFERENCE / name, thresholds)
    assert strat.params
    assert callable(strat.position)


@pytest.mark.parametrize("name", FILES)
def test_each_file_has_a_docstring_saying_its_rule(name):
    doc = ast.get_docstring(ast.parse((REFERENCE / name).read_text(encoding="utf-8")))
    assert doc and len(doc.split()) >= 10


def test_trend_rule_follows_the_moving_averages(thresholds):
    s = load_strategy_file(REFERENCE / "trend_ma.py", thresholds)
    slow = s.params["slow"]
    assert s.position(frame(np.linspace(100, 110, slow)), s.params) == 1.0
    assert s.position(frame(np.linspace(110, 100, slow)), s.params) == -1.0
    assert s.position(frame(np.full(slow, 100.0)), s.params) == 0.0
    assert s.position(frame(np.linspace(100, 110, slow - 1)), s.params) == 0.0


def test_zscore_rule_fades_a_stretched_close(thresholds):
    s = load_strategy_file(REFERENCE / "zscore_reversal.py", thresholds)
    n = s.params["lookback"]
    base = 100.0 + 0.1 * np.sin(np.arange(n))
    up, down = base.copy(), base.copy()
    up[-1] += 5.0
    down[-1] -= 5.0
    assert s.position(frame(up), s.params) == -1.0
    assert s.position(frame(down), s.params) == 1.0
    assert s.position(frame(base), s.params) == 0.0
    assert s.position(frame(np.full(n, 100.0)), s.params) == 0.0
    assert s.position(frame(up[:-1][: n - 1]), s.params) == 0.0


def test_hour_rule_is_long_only_inside_its_hours(thresholds):
    s = load_strategy_file(REFERENCE / "hour_of_day.py", thresholds)
    start, end = s.params["start_hour"], s.params["end_hour"]
    for last in range(24):
        expected = 1.0 if start <= (last + 1) % 24 < end else 0.0
        assert s.position(frame([1.0, 2.0], hour=[0, last]), s.params) == expected
