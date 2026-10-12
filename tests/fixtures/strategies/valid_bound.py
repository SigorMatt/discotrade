"""A valid strategy that uses the indicator library by its bound name."""

PARAMS = {"lookback": 3, "threshold": 0.5}
GRID = {"lookback": [2, 3, 4], "threshold": [0.25, 0.5]}


def position(bars, params):
    """Long above the moving average, flat otherwise."""
    average = indicators.sma(bars["close"], int(params["lookback"]))  # noqa: F821
    if average.iloc[-1] != average.iloc[-1]:
        return 0.0
    return 1.0 if bars["close"].iloc[-1] > average.iloc[-1] else -params["threshold"]
