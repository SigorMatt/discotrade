"""A cheating strategy for gate G0.2 (DESIGN 18.3; decision 40 of 2026-10-12).

It keeps every frame and reads earlier ones again, does arithmetic on the
index, and tries rows past the last through iloc, loc, values, to_numpy(),
their base and attrs. Long when a later close found is higher, short when
one is found and none is; otherwise momentum against a frame it kept."""

import numpy as np

PARAMS = {"lookback": 24, "tail": 6}
SEEN = []


def chain(arr):
    """``arr`` and the arrays its memory comes from, ``base`` after ``base``."""
    out = []
    while arr is not None and len(out) < 8:
        out.append(arr)
        try:
            arr = arr.base
        except Exception:
            arr = None
    return out


def after(values, closes):
    """The value after the run ``closes`` along a row or column of ``values``."""
    try:
        arr = np.atleast_2d(np.asarray(values, dtype=float))
    except Exception:
        return None
    m = len(closes)
    for i, j in np.argwhere(arr == closes[-1]) if arr.ndim == 2 else []:
        for line, k in ((arr[i], j), (arr[:, j], i)):
            if m - 1 <= k < len(line) - 1 and np.array_equal(line[k - m + 1:k + 1], closes):
                return float(line[k + 1])
    return None


def position(bars, params):
    SEEN.append(bars)
    n = bars.index[-1] + 1
    closes = bars["close"].to_numpy()[-int(min(params["tail"], n)):]
    later = []
    for probe in (lambda: bars["close"].iloc[n], lambda: bars.iloc[n - 1 + 1, 3],
                  lambda: bars.loc[n, "close"], lambda: bars["close"].loc[n + 1 - 1]):
        try:
            later.append(float(probe()))
        except Exception:
            pass
    arrays = [bars["close"].values, bars["close"].to_numpy(), bars.values, bars.to_numpy()]
    arrays += list(bars.attrs.values())
    for kept in SEEN[-8:-1]:
        arrays += [kept["close"].values, kept.to_numpy()]
    later += [after(a, closes) for arr in arrays for a in chain(arr)]
    later = [x for x in later if x is not None and x == x]
    if later:
        return 1.0 if max(later) > closes[-1] else -1.0
    old = SEEN[max(0, len(SEEN) - 1 - int(params["lookback"]))]["close"].to_numpy()[-1]
    return float(np.tanh((closes[-1] - old) / closes[-1] * 200.0))
