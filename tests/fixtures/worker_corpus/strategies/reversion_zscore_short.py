"""Mean reversion, short horizon: the z-score of the last close over the
last `lookback` closes; short (-1) for the next bar above `entry`, long (+1)
below -`entry`, flat (0) otherwise or while the slice is shorter.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

import indicators

PARAMS = {"lookback": 12, "entry": 1.5}


def position(bars, params):
    k = int(params["lookback"])
    if len(bars) < k:
        return 0.0
    z = indicators.zscore(bars["close"].iloc[-k:], k).iloc[-1]
    if not z == z:
        return 0.0
    if z > params["entry"]:
        return -1.0
    if z < -params["entry"]:
        return 1.0
    return 0.0
