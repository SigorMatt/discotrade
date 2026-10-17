"""Breakout, medium horizon: long (+1) for the next bar while the last close
is above the upper Bollinger band of the last `length` closes at `k`
deviations, short (-1) while below the lower band, flat (0) inside.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

import indicators

PARAMS = {"length": 48, "k": 2.0}


def position(bars, params):
    n = int(params["length"])
    if len(bars) < n:
        return 0.0
    band = indicators.bollinger(bars["close"].iloc[-n:], n, params["k"]).iloc[-1]
    close = float(bars["close"].iloc[-1])
    if close > band["upper"]:
        return 1.0
    if close < band["lower"]:
        return -1.0
    return 0.0
