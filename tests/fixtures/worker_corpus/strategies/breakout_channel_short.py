"""Breakout, short horizon: long (+1) for the next bar when the last close is
above the highest high of the `channel` bars before it, short (-1) when it
is below their lowest low, flat (0) otherwise.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

PARAMS = {"channel": 24}


def position(bars, params):
    k = int(params["channel"])
    if len(bars) < k + 1:
        return 0.0
    high = bars["high"].to_numpy()[-k - 1:-1]
    low = bars["low"].to_numpy()[-k - 1:-1]
    close = float(bars["close"].iloc[-1])
    if close > high.max():
        return 1.0
    if close < low.min():
        return -1.0
    return 0.0
