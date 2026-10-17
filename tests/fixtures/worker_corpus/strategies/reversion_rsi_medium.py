"""Mean reversion, medium horizon: the relative strength index of the last
`length` closes, read from a tail of `tail` closes; long (+1) for the next
bar below `low`, short (-1) above 100 - `low`, flat (0) between.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

import indicators

PARAMS = {"length": 48, "tail": 144, "low": 42}


def position(bars, params):
    tail = int(params["tail"])
    if len(bars) < tail:
        return 0.0
    value = indicators.rsi(bars["close"].iloc[-tail:], int(params["length"])).iloc[-1]
    if not value == value:
        return 0.0
    if value < params["low"]:
        return 1.0
    if value > 100 - params["low"]:
        return -1.0
    return 0.0
