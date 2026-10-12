"""Breaks decision 22's contract on known bars: returns 2.0, outside [-1, 1], at
the bar opening at 12:00 local time on a Thursday; otherwise long when the
last close is above the previous one, short when below, flat when equal. A
fixture for the lifecycle's step 1 (DESIGN 10.3; decision 63)."""

PARAMS = {"weekday": 3, "hour": 12}


def position(bars, params):
    if bars["weekday"].iloc[-1] == params["weekday"] and bars["hour"].iloc[-1] == params["hour"]:
        return 2.0
    if len(bars) < 2:
        return 0.0
    change = bars["close"].iloc[-1] - bars["close"].iloc[-2]
    return 1.0 if change > 0 else (-1.0 if change < 0 else 0.0)
