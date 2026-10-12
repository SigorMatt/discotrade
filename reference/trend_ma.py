"""Moving-average trend rule.

Long (+1) for the next bar when the simple moving average of the last
`fast` closes is above that of the last `slow` closes, short (-1) when it
is below, and flat (0) while there are fewer than `slow` bars or the two
are equal.
"""

import indicators

PARAMS = {"fast": 24, "slow": 96}
GRID = {"fast": [12, 24, 48], "slow": [96, 192, 384]}


def position(bars, params):
    slow = int(params["slow"])
    if len(bars) < slow:
        return 0.0
    close = bars["close"].iloc[-slow:]
    fast_ma = indicators.sma(close, int(params["fast"])).iloc[-1]
    slow_ma = indicators.sma(close, slow).iloc[-1]
    if fast_ma > slow_ma:
        return 1.0
    if fast_ma < slow_ma:
        return -1.0
    return 0.0
