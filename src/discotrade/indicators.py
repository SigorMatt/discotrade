"""The indicator library (DESIGN 6.3; I-2).

Importable inside a strategy as ``indicators``. Every public function is pure:
it takes a Series or array and a window, never modifies its input, and returns
a result aligned to its input (same length; a Series keeps its index, an array
gets a plain index from 0) whose value at row ``i`` depends only on rows up to
``i``. A row with too little history for the window is NaN. A standard
deviation is the sample one (``ddof = 1``). The list of functions given to
workers (DESIGN 13.4) is built from this module's public names and the first
line of each docstring, so that line must stand alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _series(x) -> pd.Series:
    if isinstance(x, pd.Series):
        return x.astype(float)
    return pd.Series(np.asarray(x, dtype=float))


def _wilder(x: pd.Series, window: int) -> pd.Series:
    return x.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def sma(x, window: int) -> pd.Series:
    """Simple moving average of the last `window` values."""
    return _series(x).rolling(window, min_periods=window).mean()


def ema(x, window: int) -> pd.Series:
    """Exponential moving average with alpha = 2 / (window + 1), seeded at the first value."""
    return _series(x).ewm(span=window, adjust=False).mean()


def rolling_std(x, window: int) -> pd.Series:
    """Sample standard deviation of the last `window` values."""
    return _series(x).rolling(window, min_periods=window).std(ddof=1)


def rolling_max(x, window: int) -> pd.Series:
    """Highest of the last `window` values."""
    return _series(x).rolling(window, min_periods=window).max()


def rolling_min(x, window: int) -> pd.Series:
    """Lowest of the last `window` values."""
    return _series(x).rolling(window, min_periods=window).min()


def returns(x, window: int = 1) -> pd.Series:
    """Simple return over `window` rows: x[i] / x[i - window] - 1."""
    s = _series(x)
    return s / s.shift(window) - 1.0


def zscore(x, window: int) -> pd.Series:
    """Distance of each value from its `window` moving average, in rolling standard deviations."""
    s = _series(x)
    return (s - sma(s, window)) / rolling_std(s, window)


def rsi(x, window: int) -> pd.Series:
    """Wilder's relative strength index over `window` changes, from 0 to 100."""
    change = _series(x).diff()
    gain = _wilder(change.clip(lower=0.0), window)
    loss = _wilder((-change).clip(lower=0.0), window)
    return 100.0 - 100.0 / (1.0 + gain / loss)


def atr(high, low, close, window: int) -> pd.Series:
    """Wilder's average true range over `window` bars."""
    h, lo, c = _series(high), _series(low), _series(close)
    previous = c.shift(1)
    true_range = pd.concat(
        [h - lo, (h - previous).abs(), (lo - previous).abs()], axis=1
    ).max(axis=1)
    return _wilder(true_range, window)


def realized_vol(close, window: int) -> pd.Series:
    """Sample standard deviation of the last `window` log returns, not annualized."""
    return rolling_std(np.log(_series(close)).diff(), window)


def bollinger(x, window: int, k: float = 2.0) -> pd.DataFrame:
    """Bollinger bands: columns lower, middle (the sma) and upper, k rolling deviations apart."""
    middle = sma(x, window)
    width = k * rolling_std(x, window)
    return pd.DataFrame({"lower": middle - width, "middle": middle, "upper": middle + width})


def donchian(high, low, window: int) -> pd.DataFrame:
    """Donchian channel: columns lower (lowest low), middle and upper (highest high)."""
    upper = rolling_max(high, window)
    lower = rolling_min(low, window)
    return pd.DataFrame({"lower": lower, "middle": (upper + lower) / 2.0, "upper": upper})


def volume_zscore(volume, window: int) -> pd.Series:
    """Z-score of volume against its last `window` values."""
    return zscore(volume, window)
