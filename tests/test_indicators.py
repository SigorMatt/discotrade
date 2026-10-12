"""The indicator library (DESIGN 6.3; I-2).

Every expected value below is computed by hand from the short fixed input
and written as arithmetic, not taken from pandas.
"""

import inspect
import math
import re

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, seed, settings
from hypothesis import strategies as st

from discotrade import indicators

REQUIRED = (
    "sma", "ema", "rolling_std", "rolling_max", "rolling_min", "returns", "zscore", "rsi",
    "atr", "realized_vol", "bollinger", "donchian", "volume_zscore",
)

X = pd.Series([1.0, 2.0, 4.0, 3.0, 5.0])
HIGH = pd.Series([11.0, 12.0, 13.0, 12.0])
LOW = pd.Series([9.0, 10.0, 11.0, 8.0])
CLOSE = pd.Series([10.0, 11.0, 12.0, 9.0])
NAN = math.nan


def public_functions():
    """Every public function defined by the indicator module, by name."""
    return sorted(
        (name, f) for name, f in inspect.getmembers(indicators, inspect.isfunction)
        if not name.startswith("_") and f.__module__ == indicators.__name__
    )


def same(actual, expected):
    actual = list(np.asarray(actual, dtype=float))
    assert len(actual) == len(expected), (actual, expected)
    for a, e in zip(actual, expected, strict=True):
        if math.isnan(e):
            assert math.isnan(a), (actual, expected)
        else:
            assert a == pytest.approx(e, rel=1e-12, abs=1e-12), (actual, expected)


def sample_std(values):
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def test_required_functions_exist():
    names = {name for name, _ in public_functions()}
    assert set(REQUIRED) <= names


@pytest.mark.parametrize(("name", "f"), public_functions())
def test_first_docstring_line_is_one_line(name, f):
    doc = inspect.getdoc(f)
    assert doc, f"{name} has no docstring"
    lines = doc.splitlines()
    assert lines[0].strip(), f"{name}: first docstring line is empty"
    assert lines[0].rstrip().endswith("."), f"{name}: first line is not a sentence"
    assert len(lines) == 1 or not lines[1].strip(), f"{name}: summary runs past one line"


def test_sma():
    same(indicators.sma(X, 3), [NAN, NAN, 7 / 3, 3.0, 4.0])


def test_ema():
    a = 2 / (3 + 1)
    e1 = 1.0
    e2 = a * 2 + (1 - a) * e1
    e3 = a * 4 + (1 - a) * e2
    e4 = a * 3 + (1 - a) * e3
    e5 = a * 5 + (1 - a) * e4
    same(indicators.ema(X, 3), [e1, e2, e3, e4, e5])
    same(indicators.ema(X, 3), [1.0, 1.5, 2.75, 2.875, 3.9375])


def test_rolling_std():
    same(indicators.rolling_std(X, 3), [NAN, NAN, sample_std([1, 2, 4]),
                                       sample_std([2, 4, 3]), sample_std([4, 3, 5])])
    same(indicators.rolling_std(X, 3), [NAN, NAN, math.sqrt(7 / 3), 1.0, 1.0])


def test_rolling_max_and_min():
    same(indicators.rolling_max(X, 2), [NAN, 2.0, 4.0, 4.0, 5.0])
    same(indicators.rolling_min(X, 2), [NAN, 1.0, 2.0, 3.0, 3.0])


def test_returns():
    same(indicators.returns(X), [NAN, 1.0, 1.0, -0.25, 2 / 3])
    same(indicators.returns(X, 2), [NAN, NAN, 3.0, 0.5, 0.25])


def test_zscore():
    same(indicators.zscore(X, 3), [NAN, NAN, (4 - 7 / 3) / math.sqrt(7 / 3), 0.0, 1.0])


def test_rsi():
    # changes: -, +1, +2, -1, +2 ; Wilder averages with alpha = 1/2 from the first change
    gain = [NAN, 1.0]
    loss = [NAN, 0.0]
    for g, lo in ((2.0, 0.0), (0.0, 1.0), (2.0, 0.0)):
        gain.append(0.5 * g + 0.5 * gain[-1])
        loss.append(0.5 * lo + 0.5 * loss[-1])
    # gain = [nan, 1, 1.5, 0.75, 1.375], loss = [nan, 0, 0, 0.5, 0.25]
    expected = [NAN, NAN, 100.0, 100 - 100 / (1 + 0.75 / 0.5), 100 - 100 / (1 + 1.375 / 0.25)]
    same(indicators.rsi(X, 2), expected)
    same(indicators.rsi(X, 2), [NAN, NAN, 100.0, 60.0, 100 - 100 / 6.5])


def test_rsi_of_a_flat_series_is_undefined():
    same(indicators.rsi(pd.Series([3.0, 3.0, 3.0, 3.0]), 2), [NAN, NAN, NAN, NAN])


def test_atr():
    # true range: 2 (h-l on the first row), max(2, 2, 0)=2, max(2, 2, 0)=2, max(4, 0, 4)=4
    tr = [2.0, 2.0, 2.0, 4.0]
    a1 = tr[0]
    a2 = 0.5 * tr[1] + 0.5 * a1
    a3 = 0.5 * tr[2] + 0.5 * a2
    a4 = 0.5 * tr[3] + 0.5 * a3
    same(indicators.atr(HIGH, LOW, CLOSE, 2), [NAN, a2, a3, a4])
    same(indicators.atr(HIGH, LOW, CLOSE, 2), [NAN, 2.0, 2.0, 3.0])


def test_realized_vol():
    r = [math.log(2), math.log(2), math.log(3 / 4), math.log(5 / 3)]
    same(indicators.realized_vol(X, 2), [NAN, NAN, sample_std(r[0:2]), sample_std(r[1:3]),
                                        sample_std(r[2:4])])


def test_bollinger():
    out = indicators.bollinger(X, 3, 2.0)
    assert list(out.columns) == ["lower", "middle", "upper"]
    s = [NAN, NAN, math.sqrt(7 / 3), 1.0, 1.0]
    m = [NAN, NAN, 7 / 3, 3.0, 4.0]
    same(out["middle"], m)
    same(out["upper"], [mi + 2 * si for mi, si in zip(m, s, strict=True)])
    same(out["lower"], [mi - 2 * si for mi, si in zip(m, s, strict=True)])
    same(indicators.bollinger(X, 3)["upper"], [NAN, NAN, 7 / 3 + 2 * math.sqrt(7 / 3), 5.0, 6.0])


def test_donchian():
    out = indicators.donchian(HIGH, LOW, 2)
    assert list(out.columns) == ["lower", "middle", "upper"]
    same(out["upper"], [NAN, 12.0, 13.0, 13.0])
    same(out["lower"], [NAN, 9.0, 10.0, 8.0])
    same(out["middle"], [NAN, 10.5, 11.5, 10.5])


def test_volume_zscore():
    v = pd.Series([100.0, 200.0, 400.0, 300.0, 500.0])
    same(indicators.volume_zscore(v, 3), [NAN, NAN, (400 - 700 / 3) / (100 * math.sqrt(7 / 3)),
                                          0.0, 1.0])


def test_arrays_are_accepted_and_results_aligned():
    out = indicators.sma(np.array([1.0, 2.0, 4.0]), 2)
    assert isinstance(out, pd.Series)
    assert list(out.index) == [0, 1, 2]
    indexed = pd.Series([1.0, 2.0, 4.0], index=[5, 6, 7])
    assert list(indicators.sma(indexed, 2).index) == [5, 6, 7]


def test_inputs_are_not_modified():
    bars = frame([1.0, 2.0, 4.0, 3.0, 5.0])
    before = bars.copy()
    for _, f in public_functions():
        f(**arguments(f, bars, 2))
    pd.testing.assert_frame_equal(bars, before)


# --- no lookahead, by truncation (DESIGN 6.3, I-2) ---------------------------------

SERIES_ARGUMENTS = ("x", "close", "high", "low", "volume")


def frame(closes):
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "close": closes,
        "high": closes * 1.01,
        "low": closes * 0.99,
        "volume": closes * 10.0,
    })


def arguments(f, bars, window):
    """Arguments for ``f`` built from ``bars`` by parameter name; fails on an unknown one."""
    out = {}
    for p in inspect.signature(f).parameters.values():
        if p.name == "window":
            out[p.name] = window
        elif p.name in SERIES_ARGUMENTS:
            out[p.name] = bars["close" if p.name == "x" else p.name]
        elif p.default is inspect.Parameter.empty:
            raise AssertionError(
                f"{f.__name__}: the no-lookahead test cannot build parameter {p.name!r}; "
                f"extend arguments() so the new function is covered"
            )
    return out


def rows(result):
    return np.asarray(result, dtype=float).reshape(len(result), -1)


def test_every_public_function_has_buildable_arguments():
    for _, f in public_functions():
        arguments(f, frame([1.0, 2.0]), 1)


prices = st.lists(
    st.floats(min_value=0.5, max_value=1000.0, allow_nan=False, allow_infinity=False),
    min_size=1, max_size=40,
)


@pytest.mark.parametrize(("name", "f"), public_functions())
@seed(20261012)
@settings(max_examples=60, deadline=None, derandomize=True, database=None)
@given(closes=prices, window=st.integers(min_value=1, max_value=12), data=st.data())
def test_value_at_i_does_not_depend_on_later_rows(name, f, closes, window, data):
    bars = frame(closes)
    full = rows(f(**arguments(f, bars, window)))
    assert len(full) == len(bars), name
    i = data.draw(st.integers(min_value=0, max_value=len(bars) - 1), label="i")
    cut = rows(f(**arguments(f, bars.iloc[: i + 1], window)))
    assert len(cut) == i + 1, name
    np.testing.assert_array_equal(cut[i], full[i], err_msg=f"{name} at row {i}")


# --- the module text is true of every function at row 0 (decision 32; DESIGN 6.3, 13.4) ---


def seeded_names():
    """Public functions named in a module docstring sentence saying "seeded at the first value"."""
    public = {name for name, _ in public_functions()}
    text = " ".join(inspect.getdoc(indicators).split())
    names = set()
    for sentence in re.split(r"(?<=\.)\s", text):
        if "seeded at the first value" in sentence:
            names |= set(re.findall(r"``(\w+)``", sentence)) & public
    return names


def test_module_docstring_names_ema_as_seeded():
    assert "ema" in seeded_names()


@pytest.mark.parametrize(("name", "f"), public_functions())
@pytest.mark.parametrize("window", [2, 3, 12])
@pytest.mark.parametrize("closes", [[7.0], [5.0, 6.0], list(np.linspace(10.0, 30.0, 25))])
def test_row_zero_is_as_the_module_text_says(name, f, window, closes):
    assert "window" in inspect.signature(f).parameters, f"{name} takes no window"
    first = rows(f(**arguments(f, frame(closes), window)))[0]
    if name in seeded_names():
        assert not np.isnan(first).any(), f"{name} is named as seeded but is NaN at row 0"
    else:
        assert np.isnan(first).all(), f"{name} is not named as seeded but has a number at row 0"
