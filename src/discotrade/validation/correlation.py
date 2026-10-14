"""The correlation gate (DESIGN 12.3, 12.2 stage 5; decision 98 (c) of
2026-10-14-m12; decision 2026-10-12 63; I-1, I-5, I-14).

The pieces the gate of :mod:`discotrade.validation.sequence` is built from,
each pure except :func:`compared`, which only reads the state directory:

- :func:`position_series`: a subject's position series on W, the positions
  ``h(u)`` of its evaluation rows over W's window bars, concatenated over the
  basket in the order the evaluations are given (the track's instrument
  order).
- :func:`compared`: the approaches whose series the submission is compared
  with, those whose state is ``live`` or ``dormant`` (decision 63's state:
  the ``to`` of an approach's last row in ``lifecycle.jsonl``, ``live`` from
  its admission date without one). The state is the one in force after the
  day ``D`` (``lifecycle.states`` of the day after ``D``: rows dated on or
  before ``D``, approaches admitted on or before ``D``), the reading
  ``lifecycle.admit`` makes of the same day.
- :func:`pearson`: the Pearson correlation of two series over the same bars;
  not a number (``nan``) when either has zero deviation (every value equal)
  or fewer than two values, so that such a pair is never a duplicate.
- :func:`duplicate`: the approach a series duplicates, the one with the
  largest absolute correlation above ``corr_max`` (the lowest id on a tie),
  or None. A strong negative correlation counts: it is the same idea with the
  sign flipped (DESIGN 12.3).

Nothing here writes to the state directory; the approaches' series may be
held in memory for one validation and are never state (DESIGN 12.3).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from discotrade import backtest, ledger, lifecycle, state
from discotrade.state import Approach

#: The states whose approaches the gate compares (DESIGN 12.3).
COMPARED = (lifecycle.LIVE, lifecycle.DORMANT)


def position_series(evaluations: Sequence[backtest.Evaluation]) -> np.ndarray:
    """``h(u)`` over the window bars of each evaluation, concatenated in order."""
    parts = [ev.rows["h"].to_numpy(dtype=np.float64) for ev in evaluations]
    return np.concatenate(parts) if parts else np.zeros(0)


def compared(state_dir: Path, track: str, day: date) -> list[Approach]:
    """The live and dormant approaches after ``day``, by id."""
    rows = ledger.read(Path(state_dir), track, ledger.LIFECYCLE)
    approaches = state.read_approaches(Path(state_dir))
    current = lifecycle.states(rows, approaches, day + timedelta(days=1))
    return [a for a in approaches
            if a.id in current and current[a.id].state in COMPARED]


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    """The Pearson correlation of ``a`` and ``b`` (the same bars); ``nan`` when
    either has zero deviation or fewer than two values."""
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    if len(x) != len(y):
        raise ValueError(f"series of {len(x)} and {len(y)} bars are not over the same bars")
    if len(x) < 2 or bool(np.all(x == x[0])) or bool(np.all(y == y[0])):
        return math.nan
    dx = x - x.mean()
    dy = y - y.mean()
    denominator = math.sqrt(float(np.dot(dx, dx)) * float(np.dot(dy, dy)))
    if not denominator > 0.0:
        return math.nan
    return float(np.dot(dx, dy)) / denominator


def duplicate(series: np.ndarray, others: Mapping[str, np.ndarray], corr_max: float
              ) -> tuple[str, float] | None:
    """The id of the approach ``series`` duplicates and the correlation, or None:
    among ``others`` whose absolute correlation with ``series`` is above
    ``corr_max``, the largest absolute correlation, the lowest id on a tie."""
    named: tuple[str, float] | None = None
    for aid in sorted(others):
        r = pearson(series, others[aid])
        if math.isnan(r) or not abs(r) > corr_max:
            continue
        if named is None or abs(r) > abs(named[1]):
            named = (aid, r)
    return named
