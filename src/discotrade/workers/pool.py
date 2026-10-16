"""The model pool (DESIGN 13.6, 11.3, 15.2; R-21; decision 2026-10-16-m15 124; I-5).

- The day's pool (124 (a)): the ``pool = true`` models of ``models.toml`` in file
  order, each kept when the provider's model list for the day holds it, else
  replaced by its fallback when the list holds that, else dropped for the day.
  Either way a missing model is a ``model_skipped`` health notice (DESIGN 13.6:
  "skipped for the day in favour of its fallback, with a health notice"). A model
  removed under (c) is dropped without a notice, and a removed fallback is not
  used. The list is read by the caller once per day and handed in; ``None`` means
  the read failed, a ``model_list_failed`` notice, and no call that day. An empty
  day's pool is a ``pool_empty`` notice and no call.
- Rotation (124 (b)): the model for a call on ``D`` in cell index ``c`` is
  ``pool[(ordinal(D) + c) mod len(pool)]``, ``ordinal(D)`` the count of the
  track's trading days from its epoch up to and excluding ``D``.
- Failure windows (124 (c), (d)) are derived from ``calls.jsonl`` rows and nothing
  else, so they are rebuilt from the ledger (I-5). A counted call has outcome
  ``trial``, ``duplicate`` or ``invalid:<stage>``; a failure is ``invalid:<stage>``;
  ``provider_error`` and ``budget`` are not counted. A window is evaluated after
  each trading day's calls: full when it holds ``pool.fail_window`` counted calls,
  above when its failure share exceeds ``pool.fail_rate`` (both from
  ``config/thresholds.toml``). A model whose window is full and above after day
  ``D`` is removed from the next trading day on, for good, with one
  ``model_removed`` alert on ``D``. A cell's window holds the counted calls of the
  open models, read here as the rows whose model is a model of ``models.toml``
  (the design is silent on how a row names its provider; every other model is
  the Claude worker's). When it crosses above, the cell is served by the Claude
  worker from the next trading day if ``workers.claude_fallback`` is true;
  while it is false, a ``cell_needs_fallback`` notice is logged on the day it
  crosses, and again only after a full window at or below the limit.

Only rows dated before ``D`` decide ``D``'s pool, so a re-run of ``D`` sees the
pool it saw (I-6). This module imports nothing that reaches the network or a
secret (decision 122 (f)); nothing here is called from ``run-day`` or ``replay``
(decision 118 (a)).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from discotrade.config import Model, ModelsConfig, Thresholds
from discotrade.state import HealthEvent

COUNTED = ("trial", "duplicate")
INVALID_PREFIX = "invalid:"
FAIL_WINDOW = "pool.fail_window"
FAIL_RATE = "pool.fail_rate"

Row = Mapping[str, Any]


def counted(outcome: str) -> bool:
    """Whether a call with this outcome counts in a failure window (124 (c))."""
    return outcome in COUNTED or failed(outcome)


def failed(outcome: str) -> bool:
    """Whether a call with this outcome is a validation failure (124 (c))."""
    return outcome.startswith(INVALID_PREFIX) and len(outcome) > len(INVALID_PREFIX)


def trading_ordinal(day: date, epoch: date, is_trading_day: Callable[[date], bool]) -> int:
    """The count of trading days from ``epoch`` up to and excluding ``day`` (124 (b))."""
    n, d = 0, epoch
    while d < day:
        n += is_trading_day(d)
        d += timedelta(days=1)
    return n


# --- the day's pool -------------------------------------------------------------------


@dataclass(frozen=True)
class DayPool:
    """The models that serve ``day``, in rotation order, and the day's notices."""

    day: date
    models: tuple[Model, ...]
    events: tuple[HealthEvent, ...]


def day_pool(models: ModelsConfig, day: date, listed: Sequence[str] | None,
             removed: Iterable[str]) -> DayPool:
    """The pool for ``day`` given the provider's list (``None``: the read failed)."""
    if listed is None:
        return DayPool(day, (), (HealthEvent(day, "notice", "model_list_failed", "pool",
                                             {"models": [m.id for m in models.pool]}),))
    have, gone = set(listed), set(removed)
    chosen: list[Model] = []
    events: list[HealthEvent] = []
    for model in models.pool:
        if model.id in gone:
            continue
        if model.id in have:
            chosen.append(model)
            continue
        fb = model.fallback
        replaced = fb is not None and fb in have and fb not in gone
        if replaced:
            assert fb is not None
            chosen.append(models.get(fb))
        events.append(HealthEvent(day, "notice", "model_skipped", model.id,
                                  {"fallback": fb, "replaced": replaced}))
    if not chosen:
        events.append(HealthEvent(day, "notice", "pool_empty", "pool",
                                  {"models": [m.id for m in models.pool]}))
    return DayPool(day, tuple(chosen), tuple(events))


def model_for(pool: DayPool, ordinal: int, cell_index: int) -> Model | None:
    """``pool[(ordinal + cell_index) mod len(pool)]``; None for an empty pool."""
    if not pool.models:
        return None
    return pool.models[(ordinal + cell_index) % len(pool.models)]


# --- failure windows from calls.jsonl -------------------------------------------------


@dataclass(frozen=True)
class _Point:
    """A window after one trading day's calls of its key."""

    day: date
    calls: int
    failures: int
    full: bool
    above: bool


def _points(rows: Iterable[Row], key: Callable[[Row], str | None], last: date,
            thresholds: Thresholds) -> dict[str, list[_Point]]:
    """Per key, its window after each trading day up to ``last`` that holds its
    counted calls; rows in date order, file order within a date."""
    fail_window = int(thresholds[FAIL_WINDOW])
    fail_rate = float(thresholds[FAIL_RATE])
    by_day: dict[date, list[Row]] = {}
    for row in rows:
        day = date.fromisoformat(str(row["date"]))
        if day <= last and counted(str(row["outcome"])):
            by_day.setdefault(day, []).append(row)
    seen: dict[str, list[bool]] = {}
    points: dict[str, list[_Point]] = {}
    for day in sorted(by_day):
        touched: list[str] = []
        for row in by_day[day]:
            k = key(row)
            if k is None:
                continue
            seen.setdefault(k, []).append(failed(str(row["outcome"])))
            if k not in touched:
                touched.append(k)
        for k in touched:
            window = seen[k][-fail_window:]
            full = fail_window > 0 and len(window) == fail_window
            fails = sum(window)
            points.setdefault(k, []).append(
                _Point(day, len(window), fails, full, full and fails / fail_window > fail_rate))
    return points


def _detail(point: _Point, thresholds: Thresholds) -> dict[str, Any]:
    return {"calls": point.calls, "failures": point.failures,
            "fail_window": thresholds[FAIL_WINDOW], "fail_rate": thresholds[FAIL_RATE]}


def _removals(rows: Iterable[Row], last: date,
              thresholds: Thresholds) -> dict[str, _Point]:
    points = _points(rows, lambda r: str(r["model"]), last, thresholds)
    return {k: next(p for p in ps if p.above)
            for k, ps in sorted(points.items()) if any(p.above for p in ps)}


def removed_models(rows: Iterable[Row], models: ModelsConfig, day: date,
                   thresholds: Thresholds) -> dict[str, date]:
    """The models removed for ``day``: id to the trading day whose calls removed it.
    Only rows dated before ``day`` count; a removal is for good (124 (c))."""
    ids = {m.id for m in models.models}
    found = _removals(rows, day - timedelta(days=1), thresholds)
    return {k: p.day for k, p in found.items() if k in ids}


def _open_cell(models: ModelsConfig) -> Callable[[Row], str | None]:
    ids = {m.id for m in models.models}
    return lambda r: str(r["cell"]) if r["model"] in ids else None


def _cell_notices(points: Sequence[_Point]) -> list[_Point]:
    """The points at which a ``cell_needs_fallback`` notice is logged (124 (d))."""
    armed, out = True, []
    for p in points:
        if not p.full:
            continue
        if p.above and armed:
            out.append(p)
            armed = False
        elif not p.above:
            armed = True
    return out


def claude_cells(rows: Iterable[Row], models: ModelsConfig, day: date,
                 thresholds: Thresholds, claude_fallback: bool) -> frozenset[str]:
    """The cells the Claude worker serves on ``day`` (124 (d); R-21): none while
    ``claude_fallback`` is false; else each cell whose open-model window was full
    and above the rate after a trading day before ``day``."""
    if not claude_fallback:
        return frozenset()
    points = _points(rows, _open_cell(models), day - timedelta(days=1), thresholds)
    return frozenset(k for k, ps in points.items() if any(p.above for p in ps))


def day_events(rows: Iterable[Row], models: ModelsConfig, day: date,
               thresholds: Thresholds, claude_fallback: bool) -> list[HealthEvent]:
    """The health events of ``day``'s calls: one ``model_removed`` alert per model
    whose window crossed on ``day``, and, while ``claude_fallback`` is false, one
    ``cell_needs_fallback`` notice per cell whose window crossed on ``day``."""
    rows = list(rows)
    ids = {m.id for m in models.models}
    events = [HealthEvent(day, "alert", "model_removed", k, _detail(p, thresholds))
              for k, p in _removals(rows, day, thresholds).items()
              if k in ids and p.day == day]
    if not claude_fallback:
        points = _points(rows, _open_cell(models), day, thresholds)
        for cell, ps in sorted(points.items()):
            events += [HealthEvent(day, "notice", "cell_needs_fallback", cell,
                                   _detail(p, thresholds))
                       for p in _cell_notices(ps) if p.day == day]
    return events
