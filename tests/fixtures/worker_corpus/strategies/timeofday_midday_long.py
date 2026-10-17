"""Time of day, short horizon: the next bar is taken to open one hour after
the last bar's open; long (+1) when that hour is at least `start` and before
`stop`, flat (0) otherwise. Prices are not read.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

PARAMS = {"start": 11, "stop": 14}


def position(bars, params):
    if len(bars) == 0:
        return 0.0
    hour = (int(bars["hour"].iloc[-1]) + 1) % 24
    if params["start"] <= hour < params["stop"]:
        return 1.0
    return 0.0
