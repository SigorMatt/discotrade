"""A grid with a long-leaning and a short-leaning value (owner's decision O-17;
decision 2026-10-14-m12 97). The target is ``bias`` plus half a step that
follows the sign of the change of the close over the last ``lookback`` bars:
``bias`` 0.5 holds 0 or 1, ``bias`` -0.5 holds -1 or 0. ``spare`` is read by
nothing, so two combinations that differ only in it tie. A fixture of
``tests/test_validation_grid.py``.
"""

PARAMS = {"bias": 0.5, "spare": 1, "lookback": 192}
GRID = {"bias": [0.5, -0.5], "spare": [1, 2]}


def position(bars, params):
    close = bars["close"].to_numpy()
    k = int(params["lookback"])
    if len(close) < k + 1:
        return params["bias"]
    step = 0.5 if close[-1] > close[-1 - k] else -0.5
    return params["bias"] + step
