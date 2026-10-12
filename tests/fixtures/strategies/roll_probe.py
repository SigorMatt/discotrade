"""Test-only roll probe for gate item G0.1 (decision 2026-10-12 43 (c)).

The target alternates with the parity of the last bar's hour: `even` after
a bar that opened at an even hour, `odd` after one that opened at an odd
hour. On consecutive hourly bars the position therefore changes at every
bar, its size as well as its sign, so a roll bar is one where the carried
position `h(u-1)` and the new one `h(u)` differ. Prices are not read.
"""

PARAMS = {"even": 1.0, "odd": -0.5}


def position(bars, params):
    if len(bars) == 0:
        return 0.0
    if int(bars["hour"].iloc[-1]) % 2 == 0:
        return params["even"]
    return params["odd"]
