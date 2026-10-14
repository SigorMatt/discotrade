"""Flat at every bar whatever ``tag`` says: every combination's net returns are
0, so every Sharpe of its grid is not a number (DESIGN 8, decision 2026-10-12
30) and the grid fixes the first (decision 2026-10-14-m12 97 (d)). A fixture of
``tests/test_validation_grid.py``.
"""

PARAMS = {"tag": 1}
GRID = {"tag": [1, 2, 3]}


def position(bars, params):
    return 0.0
