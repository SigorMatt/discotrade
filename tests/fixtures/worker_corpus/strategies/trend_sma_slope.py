"""Trend, medium horizon: the sign of the slope of the simple moving average
of the last `length` closes, measured over `step` bars, held as a half
position: +0.5 when it rises, -0.5 when it falls, 0 otherwise.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

import indicators

PARAMS = {"length": 96, "step": 48}


def position(bars, params):
    length = int(params["length"])
    step = int(params["step"])
    if len(bars) < length + step:
        return 0.0
    average = indicators.sma(bars["close"].iloc[-(length + step):], length)
    slope = average.iloc[-1] - average.iloc[-1 - step]
    if slope > 0:
        return 0.5
    if slope < 0:
        return -0.5
    return 0.0
