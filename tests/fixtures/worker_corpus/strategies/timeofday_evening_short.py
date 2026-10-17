"""Time of day, short horizon: the next bar is taken to open one hour after
the last bar's open; short (-1) when that hour is at least `start` or before
`stop` (the evening and night session), flat (0) otherwise. Prices are not
read.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

PARAMS = {"start": 20, "stop": 2}


def position(bars, params):
    if len(bars) == 0:
        return 0.0
    hour = (int(bars["hour"].iloc[-1]) + 1) % 24
    if hour >= params["start"] or hour < params["stop"]:
        return -1.0
    return 0.0
