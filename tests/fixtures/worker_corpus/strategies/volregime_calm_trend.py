"""Volatility regime, medium horizon: while the realized volatility of the
last `short` bars is below `ratio` times that of the last `long` bars (a
calm regime), follow the sign of the return over the last `short` bars;
flat (0) in any other regime.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

import indicators

PARAMS = {"short": 12, "long": 96, "ratio": 0.9}


def position(bars, params):
    n = int(params["long"])
    k = int(params["short"])
    if len(bars) < n + 1:
        return 0.0
    close = bars["close"].iloc[-(n + 1):]
    fast = indicators.realized_vol(close, k).iloc[-1]
    slow = indicators.realized_vol(close, n).iloc[-1]
    if not fast < params["ratio"] * slow:
        return 0.0
    move = float(close.iloc[-1] / close.iloc[-1 - k] - 1.0)
    if move > 0:
        return 1.0
    if move < 0:
        return -1.0
    return 0.0
