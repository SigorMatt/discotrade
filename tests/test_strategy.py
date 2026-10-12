"""The strategy contract and its loader (DESIGN 6.1, 6.2; decisions 21, 22; I-10)."""

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from discotrade.config import load_thresholds
from discotrade.strategy import (
    ResultError,
    StrategyError,
    call_position,
    check_result,
    load_strategy,
    load_strategy_file,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "strategies"
THRESHOLDS = ROOT / "config" / "thresholds.toml"


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds(THRESHOLDS)


def bars(closes):
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    return pd.DataFrame({
        "open": closes, "high": closes + 1.0, "low": closes - 1.0, "close": closes,
        "volume": np.full(n, 100.0), "hour": np.arange(n) % 24, "weekday": np.zeros(n, int),
    })


# --- the loader ------------------------------------------------------------------


def test_bound_name_strategy_loads_and_runs(thresholds):
    s = load_strategy_file(FIXTURES / "valid_bound.py", thresholds)
    assert s.params == {"lookback": 3, "threshold": 0.5}
    assert s.grid == {"lookback": [2, 3, 4], "threshold": [0.25, 0.5]}
    # sma(3) of the last three closes is 11; the last close 12 is above it.
    assert s.position(bars([10, 11, 10, 11, 12]), dict(s.params)) == 1.0
    # last close 9 below sma(3) = 10: -threshold
    assert s.position(bars([10, 11, 10, 11, 9]), dict(s.params)) == -0.5
    # too few bars for the window: sma is NaN, the strategy returns 0
    assert s.position(bars([10, 11]), dict(s.params)) == 0.0


def test_import_indicators_strategy_loads_and_runs(thresholds):
    s = load_strategy_file(FIXTURES / "valid_import.py", thresholds)
    assert s.grid is None
    assert s.position(bars([10, 11, 10, 11, 9]), dict(s.params)) == -1.0
    assert s.position(bars([10, 11, 10, 11, 12]), dict(s.params)) == 0.0


def test_import_indicators_inside_the_function(thresholds):
    text = (
        'PARAMS = {"w": 2}\n'
        "def position(bars, params):\n"
        "    from indicators import rolling_max\n"
        '    return 1.0 if bars["close"].iloc[-1] >= rolling_max(bars["close"], 2).iloc[-1]'
        " else 0.0\n"
    )
    s = load_strategy(text, thresholds)
    assert s.position(bars([1, 2]), s.params) == 1.0


def test_loader_does_not_install_a_global_indicators_module(thresholds):
    import sys

    load_strategy_file(FIXTURES / "valid_import.py", thresholds)
    assert "indicators" not in sys.modules


REFUSALS = [
    ("six_params.py", "max_params", r"6 parameters.*at most 5"),
    ("nonnumeric_param.py", "params_numeric", r"'mode'"),
    ("grid_unknown_key.py", "grid_keys", r"'window'"),
    ("grid_three_keys.py", "grid_max_params", r"3 parameters.*at most 2"),
    ("grid_four_values.py", "grid_max_values", r"'lookback'.*4 values.*at most 3"),
    ("no_position.py", "position", r"callable"),
]


@pytest.mark.parametrize(("name", "rule", "detail"), REFUSALS)
def test_loader_refuses_naming_the_rule(thresholds, name, rule, detail):
    with pytest.raises(StrategyError) as err:
        load_strategy_file(FIXTURES / name, thresholds)
    assert err.value.rule == rule
    assert f"[{rule}]" in str(err.value)
    assert re.search(detail, str(err.value)), str(err.value)


def test_loader_refuses_a_missing_position(thresholds):
    with pytest.raises(StrategyError) as err:
        load_strategy('PARAMS = {"a": 1}\n', thresholds)
    assert err.value.rule == "position"


def padded(lines):
    """The valid bound-name text padded with comment lines to exactly ``lines`` lines."""
    text = (FIXTURES / "valid_bound.py").read_text()
    have = len(text.splitlines())
    assert have <= lines
    return text + "".join(f"# pad {k}\n" for k in range(lines - have))


def test_loader_refuses_one_line_over_max_lines(thresholds):
    limit = thresholds["validation.max_lines"]
    load_strategy(padded(limit), thresholds)
    with pytest.raises(StrategyError) as err:
        load_strategy(padded(limit + 1), thresholds)
    assert err.value.rule == "max_lines"
    assert f"{limit + 1} lines" in str(err.value)
    assert f"at most {limit}" in str(err.value)


def test_line_limit_is_read_from_the_thresholds_file(thresholds, tmp_path):
    limit = thresholds["validation.max_lines"]
    text = THRESHOLDS.read_text()
    assert f"max_lines = {limit}\n" in text
    copy = tmp_path / "thresholds.toml"
    copy.write_text(text.replace(f"max_lines = {limit}\n", f"max_lines = {limit + 5}\n"))
    raised = load_thresholds(copy)
    assert raised["validation.max_lines"] == limit + 5
    over = padded(limit + 1)
    with pytest.raises(StrategyError):
        load_strategy(over, thresholds)
    assert load_strategy(over, raised).params == {"lookback": 3, "threshold": 0.5}

    copy.write_text(text.replace(f"max_lines = {limit}\n", f"max_lines = {limit - 1}\n"))
    lowered = load_thresholds(copy)
    with pytest.raises(StrategyError) as err:
        load_strategy(padded(limit), lowered)
    assert err.value.rule == "max_lines"


def test_parameter_limits_are_read_from_the_thresholds_file(thresholds, tmp_path):
    text = THRESHOLDS.read_text()
    for key in ("max_params", "grid_max_params", "grid_max_values"):
        value = thresholds[f"validation.{key}"]
        assert f"\n{key} = {value}\n" in text
        text = text.replace(f"\n{key} = {value}\n", f"\n{key} = {value + 1}\n")
    copy = tmp_path / "thresholds.toml"
    copy.write_text(text)
    raised = load_thresholds(copy)
    for name in ("six_params.py", "grid_three_keys.py", "grid_four_values.py"):
        load_strategy_file(FIXTURES / name, raised)


# --- the result check -------------------------------------------------------------

TS = pd.Timestamp("2026-10-12T14:00:00Z")

BAD_RESULTS = [
    (math.nan, "finite"),
    (math.inf, "finite"),
    (-math.inf, "finite"),
    (1.5, r"\[-1, 1\]"),
    (-1.0000001, r"\[-1, 1\]"),
    ("0.5", "not a real number"),
]


@pytest.mark.parametrize(("value", "why"), BAD_RESULTS)
@pytest.mark.parametrize("shorting", [True, False])
def test_result_check_refuses_naming_instrument_and_ts(value, why, shorting):
    with pytest.raises(ResultError) as err:
        check_result(value, instrument="SYM1", ts=TS, shorting=shorting)
    message = str(err.value)
    assert "SYM1" in message
    assert str(TS) in message
    assert re.search(why, message), message


@pytest.mark.parametrize(("value", "why"), BAD_RESULTS)
def test_call_position_refuses_a_bad_result(value, why):
    with pytest.raises(ResultError) as err:
        call_position(lambda b, p: value, bars([1.0]), {}, instrument="SYM1", ts=TS,
                      shorting=True)
    assert "SYM1" in str(err.value) and str(TS) in str(err.value)
    assert re.search(why, str(err.value))


def test_call_position_turns_a_raising_call_into_an_error():
    def boom(b, p):
        raise ZeroDivisionError("division by zero")

    with pytest.raises(ResultError) as err:
        call_position(boom, bars([1.0]), {}, instrument="SYM2", ts=TS, shorting=False)
    message = str(err.value)
    assert "SYM2" in message and str(TS) in message
    assert "ZeroDivisionError" in message
    assert isinstance(err.value.__cause__, ZeroDivisionError)


@pytest.mark.parametrize("value", [-1.0, -0.25, -1e-12])
def test_negative_result_clipped_only_without_shorting(value):
    assert check_result(value, instrument="S", ts=TS, shorting=False) == 0.0
    assert check_result(value, instrument="S", ts=TS, shorting=True) == value


@pytest.mark.parametrize("value", [0, 0.0, 1, 1.0, 0.5, np.float64(0.75), np.int64(1)])
@pytest.mark.parametrize("shorting", [True, False])
def test_valid_non_negative_results_pass_unchanged(value, shorting):
    out = check_result(value, instrument="S", ts=TS, shorting=shorting)
    assert out == float(value)
    assert type(out) is float


def test_bool_is_not_a_real_number_here():
    with pytest.raises(ResultError):
        check_result(True, instrument="S", ts=TS, shorting=True)


def test_call_position_passes_a_copy_of_params():
    seen = {}

    def strategy(b, p):
        p["x"] = 99
        seen.update(p)
        return -0.5

    params = {"x": 1}
    out = call_position(strategy, bars([1.0]), params, instrument="S", ts=TS, shorting=False)
    assert out == 0.0
    assert params == {"x": 1}
    assert seen == {"x": 99}
