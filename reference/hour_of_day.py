"""Hour-of-day rule.

The next bar is taken to open one hour after the last bar's open, in the
instrument calendar's time zone. Long (+1) for the next bar when that hour
is at least `start_hour` and before `end_hour`, flat (0) otherwise. Prices
are not read.
"""

PARAMS = {"start_hour": 9, "end_hour": 16}
GRID = {"start_hour": [8, 9, 10], "end_hour": [12, 16, 20]}


def position(bars, params):
    if len(bars) == 0:
        return 0.0
    next_hour = (int(bars["hour"].iloc[-1]) + 1) % 24
    if params["start_hour"] <= next_hour < params["end_hour"]:
        return 1.0
    return 0.0
