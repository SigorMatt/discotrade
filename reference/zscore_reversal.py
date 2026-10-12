"""Z-score reversal rule.

The z-score of the last close is its distance from the moving average of
the last `lookback` closes in their sample standard deviations. Short (-1)
for the next bar when it is above `entry`, long (+1) when it is below
-`entry`, and flat (0) otherwise, while there are fewer than `lookback`
bars, or when the deviation is 0.
"""

import indicators

PARAMS = {"lookback": 48, "entry": 1.5}
GRID = {"lookback": [24, 48, 96], "entry": [1.0, 1.5, 2.0]}


def position(bars, params):
    lookback = int(params["lookback"])
    if len(bars) < lookback:
        return 0.0
    z = indicators.zscore(bars["close"].iloc[-lookback:], lookback).iloc[-1]
    if not z == z or abs(z) == float("inf"):
        return 0.0
    if z > params["entry"]:
        return -1.0
    if z < -params["entry"]:
        return 1.0
    return 0.0
