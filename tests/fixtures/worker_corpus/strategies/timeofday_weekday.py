"""Time of day, medium horizon: by the weekday of the last bar (Monday is 0),
long (+1) on the first `early` weekdays, short (-1) from weekday `late` on,
flat (0) between. Prices are not read.
A validation fixture of the worker corpus (DESIGN 18.3 G3.1)."""

PARAMS = {"early": 2, "late": 3}


def position(bars, params):
    if len(bars) == 0:
        return 0.0
    day = int(bars["weekday"].iloc[-1])
    if day < params["early"]:
        return 1.0
    if day >= params["late"]:
        return -1.0
    return 0.0
