"""Returns its ``scale`` at every bar: the second combination of its grid
returns 2.0, outside [-1, 1] (decision 2026-10-12 22), and fails the dry run
(DESIGN 12.2 stage 2; decision 2026-10-14-m12 97 (a)). A fixture of
``tests/test_validation_grid.py``.
"""

PARAMS = {"scale": 1.0}
GRID = {"scale": [1.0, 2.0]}


def position(bars, params):
    return params["scale"]
