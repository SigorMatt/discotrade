"""Volatility regime, short horizon: while the realized volatility of the
last `short` bars is above `ratio` times that of the last `long` bars (a
stormy regime), fade the last bar's return (-1 after a rise, +1 after a
fall); flat (0) in any other regime.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

import indicators

PARAMS = {"short": 6, "long": 48, "ratio": 1.2}


def position(bars, params):
    n = int(params["long"])
    if len(bars) < n + 1:
        return 0.0
    close = bars["close"].iloc[-(n + 1):]
    fast = indicators.realized_vol(close, int(params["short"])).iloc[-1]
    slow = indicators.realized_vol(close, n).iloc[-1]
    if not fast > params["ratio"] * slow:
        return 0.0
    last = float(close.iloc[-1] - close.iloc[-2])
    if last > 0:
        return -1.0
    if last < 0:
        return 1.0
    return 0.0
