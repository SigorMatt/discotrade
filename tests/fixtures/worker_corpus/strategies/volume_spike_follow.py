"""Volume, short horizon: when the volume z-score of the last bar over the
last `length` bars is above `entry`, follow that bar's direction for the
next bar (+1 for a rise, -1 for a fall); flat (0) otherwise.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

import indicators

PARAMS = {"length": 24, "entry": 1.0}


def position(bars, params):
    k = int(params["length"])
    if len(bars) < k:
        return 0.0
    z = indicators.volume_zscore(bars["volume"].iloc[-k:], k).iloc[-1]
    if not z > params["entry"]:
        return 0.0
    body = float(bars["close"].iloc[-1] - bars["open"].iloc[-1])
    if body > 0:
        return 1.0
    if body < 0:
        return -1.0
    return 0.0
