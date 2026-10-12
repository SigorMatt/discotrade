"""A valid strategy that writes `import indicators`."""

import indicators

PARAMS = {"lookback": 3}


def position(bars, params):
    """Short below the moving average, flat otherwise."""
    average = indicators.sma(bars["close"], params["lookback"])
    if average.iloc[-1] != average.iloc[-1]:
        return 0.0
    return -1.0 if bars["close"].iloc[-1] < average.iloc[-1] else 0.0
