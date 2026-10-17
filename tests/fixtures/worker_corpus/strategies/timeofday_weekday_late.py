"""Time of day, medium horizon: by the weekday of the last bar (Monday is 0),
long (+1) on the first `early` weekdays, short (-1) from weekday `late` on,
flat (0) between. Prices are not read. The weekday rule of
`timeofday_weekday.py` with the short side starting a day later, so the
correlation gate names it a duplicate of that approach when it is live.
A validation fixture of the worker corpus (DESIGN 12.3, 18.3 G3.1)."""

PARAMS = {"early": 2, "late": 4}


def position(bars, params):
    if len(bars) == 0:
        return 0.0
    day = int(bars["weekday"].iloc[-1])
    if day < params["early"]:
        return 1.0
    if day >= params["late"]:
        return -1.0
    return 0.0
