"""The lifecycle (DESIGN 10.3, 9.1, 10.2; decisions 2026-10-12 22, 48, 62, 63; I-5, I-6).

States ``candidate``, ``live``, ``dormant``, ``retired``. The state of an
approach is the ``to`` of its last row in ``ledger/<track>/lifecycle.jsonl``;
an approach under ``approaches/`` with no row is ``live`` from its admission
date (decision 63). Every change is one lifecycle row dated ``D`` and takes
effect from the next trading day: ``states(rows, approaches, day)`` gives the
states in force on ``day``, from the rows dated before ``day`` and the
approaches admitted before it, and the journal of ``day`` holds the
approaches whose state in force is ``live`` or ``dormant``
(``journaled_ids``). An approach is journaled on ``day`` unless that state is
``retired``, and on the day its contract failed its rows are not journaled
(step 1), so ``was_journaled`` also excludes a day with a ``failure: ...`` row.

``run_steps(state_dir, setup, day, paper, failures, into=None)`` runs steps 1
to 4 after the journaling of ``day``, in that order; within a step the
approaches are taken in ascending id order, and each step and each approach
sees the states the earlier ones left. ``paper`` is the paper records (rows
dated after ``day`` are ignored); ``failures`` maps each approach whose
evaluation on ``day`` broke decision 22's contract to the error text. With
``N = lifecycle.dormant_window_days`` and a Sharpe over a window ``W`` (a set
of dates) meaning, for steps 2 and 3, ``metrics.sharpe`` of
``paper.adjusted(state_dir, setup, aid, W, "net_1x", records=paper,
overlay=into)``: the approach's paper ``net_1x`` on its paper days in ``W``
less its static exposure, with its own average positions over its rows of
``W`` (owner's O-11, O-12; decision 2026-10-14 85; the staging directory
``into`` is passed as ``overlay`` so that the staged day's exposure records
are read, decision 84):

1. a failed approach is retired, reason ``failure: <text>``;
2. a live approach with at least ``N`` paper rows whose Sharpe over its last
   ``N`` rows is negative goes dormant, reason ``dormant`` (a Sharpe that is
   not a number is not negative);
3. a dormant approach dormant for at least ``lifecycle.revival_min_dormant_days``
   trading days of the track (counted after the date of its row to
   ``dormant``, up to and including ``day``; ``stats.trading_dates`` of the
   track's calendars) whose Sharpe over its last ``N`` paper rows (all of them
   when it has fewer: the design is silent, this is the simplest reading) is
   positive returns to live, reason ``returned``, when its cell has fewer than
   ``cell_slots`` live approaches, or when that Sharpe beats the weakest live
   approach of its cell over the same days (the dates of those paper rows),
   each live approach scored on its own adjusted series with its own average
   positions over its rows of those dates (O-12), which goes dormant, reason
   ``displaced``;
4. an approach dormant for at least ``lifecycle.retire_dormant_days`` calendar
   days (``day`` minus the date of its row to ``dormant``) is retired, reason
   ``retired_dormant``.

The weakest live approach of a cell (``weakest``) has the lowest Sharpe over
the days compared, a Sharpe that is not a number counting as the lowest,
ties to the lowest id. A score beats the weakest when it is positive and
above the weakest's Sharpe, a weakest Sharpe that is not a number being below
every positive score (it counts as the lowest; the design is silent on
``above`` a value that is not a number, this is that rule's reading). Where a
newcomer displaces the weakest, the newcomer's row comes first.

A row whose reason is ``admitted``, ``displaced``, ``dormant`` or
``returned`` carries ``adjusted``, the adjusted Sharpe at 1x that decided it,
and ``plain``, the Sharpe at 1x of the plain paper ``net_1x`` over the same
window (decision 87): for ``dormant`` and ``returned`` the approach's own over
its ``W``; for ``displaced`` the displaced approach's over the days compared
(the returning one's ``W`` in step 3, T's days at admission); for
``admitted`` the candidate's ``adjusted_t["sharpe"]`` and
``metrics_t["sharpe"]``; ``None`` (JSON ``null``) for a figure that is not a
number. Rows of other reasons carry neither.

``admit(state_dir, setup, candidate, day, into=None)`` applies DESIGN 10.3's
admission rule after steps 1 to 4 of ``day`` (decision 63), from the states
in force after ``day``, on the adjusted measure (owner's O-11, O-12;
decision 2026-10-14 86): refused ``not_positive`` when the score
(``candidate.adjusted_t["sharpe"]``, the Sharpe at 1x of the candidate's
exposure-adjusted net series on T with its average positions over T) is not
positive (a score that is not a number or ``None`` included), else
``too_few_trades`` below ``admission.min_trades_t`` (still
``metrics_t["trades"]``), else admitted ``free_slot`` when the cell has fewer
than ``cell_slots`` live approaches, else admitted ``displaced`` when the
score beats the weakest live approach, each live approach scored over T's
days on ``metrics.sharpe`` of ``paper.adjusted(..., T's days, "net_1x")``,
its own adjusted series with its own average positions over its rows of
those days (that approach goes dormant, reason ``displaced``), else refused
``not_better_than_weakest``. It writes one trial row (``ledger.TRIALS``,
with ``adjusted_t`` and ``adjusted_w`` beside ``metrics_t`` and
``metrics_w``) and, when admitted, the approach (admission date ``day``,
``state.write_approach``) and its ``candidate`` to ``live`` row, reason
``admitted``; a trial not admitted is written under ``trials/<id>/``
(``state.write_trial``). The grid, the W metrics and the W adjusted figures
of a candidate that does not carry them are ``null``.

Rows are appended through ``ledger.append``: a row already in the ledger is
not appended again, so a re-run of a day appends nothing (I-6). No clock is
read (I-12).
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from discotrade import costs, ledger, state
from discotrade.metrics import sharpe
from discotrade.state import Approach
from discotrade.stats import trading_dates

CANDIDATE, LIVE, DORMANT, RETIRED = "candidate", "live", "dormant", "retired"
FAILURE_PREFIX = "failure: "
DORMANT_REASON, RETURNED, DISPLACED, RETIRED_DORMANT, ADMITTED = (
    "dormant", "returned", "displaced", "retired_dormant", "admitted")
FREE_SLOT, NOT_POSITIVE, TOO_FEW_TRADES, NOT_BETTER = (
    "free_slot", "not_positive", "too_few_trades", "not_better_than_weakest")


@dataclass(frozen=True)
class Status:
    """An approach's state and the date it entered it."""

    state: str
    since: date


def _day(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def states(rows: Sequence[Mapping[str, Any]], approaches: Sequence[Approach],
           day: date) -> dict[str, Status]:
    """The states in force on ``day``: each approach admitted before ``day``,
    by the last of its rows dated before ``day``, else ``live`` since its
    admission date."""
    out = {a.id: Status(LIVE, a.admitted) for a in approaches if a.admitted < day}
    for row in rows:
        when = _day(row["date"])
        if when < day and row["id"] in out:
            out[row["id"]] = Status(row["to"], when)
    return out


def journaled_ids(rows: Sequence[Mapping[str, Any]], approaches: Sequence[Approach],
                  day: date) -> list[str]:
    """The approaches the journal of ``day`` evaluates: those whose state in
    force on ``day`` is live or dormant, by id."""
    return sorted(aid for aid, s in states(rows, approaches, day).items()
                  if s.state in (LIVE, DORMANT))


def was_journaled(rows: Sequence[Mapping[str, Any]], approaches: Sequence[Approach],
                  day: date) -> list[str]:
    """``journaled_ids`` less the approaches retired on ``day`` for a contract
    failure (their rows of ``day`` are not journaled, step 1)."""
    failed = {r["id"] for r in rows if _day(r["date"]) == day
              and str(r["reason"]).startswith(FAILURE_PREFIX)}
    return [aid for aid in journaled_ids(rows, approaches, day) if aid not in failed]


def weakest(scores: Mapping[str, float]) -> str:
    """The id with the lowest score, one that is not a number lowest, ties to
    the lowest id."""
    if not scores:
        raise ValueError("no approach to choose the weakest from")
    return min(scores, key=lambda k: (-math.inf if math.isnan(scores[k]) else scores[k], k))


def beats(score: float, weakest_score: float) -> bool:
    """A positive ``score`` above ``weakest_score``, one that is not a number
    being below every positive score."""
    if math.isnan(score) or not score > 0:
        return False
    return math.isnan(weakest_score) or score > weakest_score


def _subject(paper: pd.DataFrame, aid: str) -> pd.DataFrame:
    mine = paper[paper["subject"] == aid]
    return mine.sort_values("date", kind="mergesort")


def _sharpe_on(paper: pd.DataFrame, aid: str, days: set[date]) -> float:
    mine = _subject(paper, aid)
    return sharpe(mine[mine["date"].isin(days)]["net_1x"])


def _figures(state_dir: Path, setup: Any, paper: pd.DataFrame, aid: str, days: set[date],
             overlay: Path | None) -> tuple[float, float]:
    """``(adjusted, plain)``: the Sharpe at 1x of ``aid``'s adjusted paper
    ``net_1x`` on its paper days in ``days``, with its own average positions
    over its rows of ``days`` (O-11, O-12; decision 85), and of its plain one
    on the same days (decision 87)."""
    from discotrade import paper as paper_module  # paper imports this module

    adjusted = sharpe(paper_module.adjusted(state_dir, setup, aid, days, "net_1x",
                                            records=paper, overlay=overlay))
    return adjusted, _sharpe_on(paper, aid, days)


def _figure(value: float) -> float | None:
    return None if math.isnan(value) else float(value)


def _cells(approaches: Sequence[Approach]) -> dict[str, str]:
    return {a.id: str(a.meta["cell"]) for a in approaches}


def _live_in(cell: str, current: Mapping[str, Status], cells: Mapping[str, str]) -> list[str]:
    return sorted(aid for aid, s in current.items() if s.state == LIVE and cells[aid] == cell)


def _row(day: date, aid: str, frm: str, to: str, reason: str,
         figures: tuple[float, float] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"date": day.isoformat(), "id": aid, "from": frm, "to": to,
                           "reason": reason}
    if figures is not None:
        out["adjusted"], out["plain"] = _figure(figures[0]), _figure(figures[1])
    return out


def step_rows(setup: Any, day: date, rows: Sequence[Mapping[str, Any]],
              approaches: Sequence[Approach], paper: pd.DataFrame,
              failures: Mapping[str, str], *, state_dir: Path,
              overlay: Path | None = None) -> list[dict[str, Any]]:
    """The lifecycle rows of steps 1 to 4 of ``day`` (DESIGN 10.3; decisions 63,
    85, 87); the exposure records are read from ``overlay`` first, then
    ``state_dir``."""
    th = setup.thresholds
    n = int(th["lifecycle.dormant_window_days"])
    revival = int(th["lifecycle.revival_min_dormant_days"])
    retire = int(th["lifecycle.retire_dormant_days"])
    slots = int(setup.track.cell_slots)
    paper = paper[paper["date"] <= day]
    current = states(rows, approaches, day)
    cells = _cells(approaches)
    out: list[dict[str, Any]] = []

    def change(aid: str, to: str, reason: str,
               figures: tuple[float, float] | None = None) -> None:
        out.append(_row(day, aid, current[aid].state, to, reason, figures))
        current[aid] = Status(to, day)

    def measured(aid: str, days: set[date]) -> tuple[float, float]:
        return _figures(state_dir, setup, paper, aid, days, overlay)

    # 1. Retire failures.
    for aid in sorted(failures):
        if aid in current and current[aid].state in (LIVE, DORMANT):
            change(aid, RETIRED, FAILURE_PREFIX + failures[aid])
    # 2. Go dormant.
    for aid in sorted(current):
        if current[aid].state != LIVE:
            continue
        mine = _subject(paper, aid)
        if n > 0 and len(mine) >= n:
            figures = measured(aid, set(mine["date"].iloc[-n:]))
            if figures[0] < 0:
                change(aid, DORMANT, DORMANT_REASON, figures)
    # 3. Return.
    calendars = [setup.calendars[name] for name in sorted(setup.calendars)]
    for aid in sorted(current):
        s = current[aid]
        if s.state != DORMANT or s.since >= day:
            continue
        waited = trading_dates(calendars, setup.track.bar_seconds,
                               s.since + timedelta(days=1), day)
        if len(waited) < revival:
            continue
        days = set(_subject(paper, aid)["date"].iloc[-n:])
        figures = measured(aid, days)
        score = figures[0]
        if math.isnan(score) or not score > 0:
            continue
        live = _live_in(cells[aid], current, cells)
        if len(live) < slots:
            change(aid, LIVE, RETURNED, figures)
            continue
        others = {other: measured(other, days) for other in live}
        weak = weakest({other: f[0] for other, f in others.items()})
        if beats(score, others[weak][0]):
            change(aid, LIVE, RETURNED, figures)
            change(weak, DORMANT, DISPLACED, others[weak])
    # 4. Retire the long dormant.
    for aid in sorted(current):
        s = current[aid]
        if s.state == DORMANT and (day - s.since).days >= retire:
            change(aid, RETIRED, RETIRED_DORMANT)
    return out


def run_steps(state_dir: Path, setup: Any, day: date, paper: pd.DataFrame | None,
              failures: Mapping[str, str], into: Path | None = None
              ) -> list[Mapping[str, Any]]:
    """Steps 1 to 4 of ``day``, appended to the lifecycle ledger (into the
    staging directory ``into`` when given); returns the rows appended."""
    track = setup.track.name
    rows = ledger.read(state_dir, track, ledger.LIFECYCLE, into=into)
    approaches = state.read_approaches(state_dir)
    if paper is None:
        from discotrade import paper as paper_module
        paper = paper_module.build(pd.DataFrame(), 1, {})
    changes = step_rows(setup, day, rows, approaches, paper, failures,
                        state_dir=Path(state_dir), overlay=into)
    return ledger.append(state_dir, track, ledger.LIFECYCLE, changes, into=into)


# --- admission (DESIGN 10.3; decision 63) ------------------------------------------------

@dataclass(frozen=True)
class Candidate:
    """A candidate scored on T: its source and fixed parameters, provenance,
    the grid and W metrics when it has them, its DESIGN 8 metrics on T (a
    ``metrics.Metrics`` or a mapping with at least ``sharpe`` and ``trades``),
    its exposure-adjusted figures on T (``adjusted_t``, a mapping holding
    ``sharpe``, ``sharpe_2x``, ``total_return``, ``total_return_2x`` and
    ``avg_position``, decision 2026-10-14 86 (a)), those on W when it has them
    (``adjusted_w``) and T's trading days."""

    source: str
    params: Mapping[str, Any]
    cell: str
    model_id: str
    model_version: str
    cutoff: date
    description: str
    profile_version: str
    metrics_t: Any
    adjusted_t: Mapping[str, Any]
    t_days: Sequence[date]
    grid: Any = None
    metrics_w: Any = None
    adjusted_w: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class Admission:
    id: str
    admitted: bool
    reason: str
    displaced: str | None
    trial: Mapping[str, Any]
    lifecycle: tuple[Mapping[str, Any], ...]


def _number(value: Any) -> float:
    """A score as a float, ``None`` being not a number."""
    return math.nan if value is None else float(value)


def _as_dict(metrics: Any) -> dict[str, Any] | None:
    if metrics is None:
        return None
    if dataclasses.is_dataclass(metrics) and not isinstance(metrics, type):
        return dataclasses.asdict(metrics)
    return dict(metrics)


def admit(state_dir: Path, setup: Any, candidate: Candidate, day: date,
          into: Path | None = None) -> Admission:
    """Admit or refuse ``candidate`` on ``day`` and write its ledger rows and files."""
    from discotrade import paper as paper_module  # paper imports journal, which imports this

    state_dir = Path(state_dir)
    track = setup.track.name
    out = state_dir if into is None else Path(into)
    th = setup.thresholds
    metrics_t = _as_dict(candidate.metrics_t) or {}
    adjusted_t = _as_dict(candidate.adjusted_t) or {}
    score = _number(adjusted_t["sharpe"])
    trades = int(metrics_t["trades"])
    aid = state.approach_id(candidate.source, candidate.params)

    rows = ledger.read(state_dir, track, ledger.LIFECYCLE, into=into)
    approaches = state.read_approaches(state_dir)
    current = states(rows, approaches, day + timedelta(days=1))   # after steps 1 to 4 of day
    cells = _cells(approaches)
    live = _live_in(candidate.cell, current, cells)
    displaced: str | None = None
    scores: dict[str, tuple[float, float]] = {}
    if math.isnan(score) or not score > 0:
        reason, admitted = NOT_POSITIVE, False
    elif trades < int(th["admission.min_trades_t"]):
        reason, admitted = TOO_FEW_TRADES, False
    elif len(live) < int(setup.track.cell_slots):
        reason, admitted = FREE_SLOT, True
    else:
        records = None
        if into is not None:
            records = paper_module.read(into, track)
        if records is None:
            records = paper_module.read(state_dir, track)
        if records is None:
            records = paper_module.build(pd.DataFrame(), 1, {})
        days = set(candidate.t_days)
        scores = {other: _figures(state_dir, setup, records, other, days, into)
                  for other in live}
        weak = weakest({other: f[0] for other, f in scores.items()})
        if beats(score, scores[weak][0]):
            reason, admitted, displaced = DISPLACED, True, weak
        else:
            reason, admitted = NOT_BETTER, False

    trial = {
        "date": day.isoformat(), "id": aid, "cell": candidate.cell,
        "model_id": candidate.model_id, "model_version": candidate.model_version,
        "cutoff": candidate.cutoff.isoformat(),
        "code_sha256": hashlib.sha256(candidate.source.encode("utf-8")).hexdigest(),
        "profile_version": candidate.profile_version, "cost_model": costs.VERSION,
        "config_hash": costs.config_hash(setup.instruments, setup.spread_tables),
        "grid": candidate.grid, "params": dict(candidate.params),
        "metrics_w": _as_dict(candidate.metrics_w), "metrics_t": metrics_t,
        "adjusted_w": _as_dict(candidate.adjusted_w), "adjusted_t": adjusted_t,
        "admitted": admitted, "reason": reason, "displaced": displaced,
    }
    ledger.append(state_dir, track, ledger.TRIALS, [trial], into=into)
    common = dict(source=candidate.source, params=candidate.params, cell=candidate.cell,
                  model_id=candidate.model_id, model_version=candidate.model_version,
                  cutoff=candidate.cutoff, description=candidate.description,
                  profile_version=candidate.profile_version, instruments=setup.instruments,
                  spread_tables=setup.spread_tables)
    changes: list[dict[str, Any]] = []
    if admitted:
        state.write_approach(out, admitted=day, **common)
        changes.append(_row(day, aid, CANDIDATE, LIVE, ADMITTED,
                            (score, _number(metrics_t.get("sharpe")))))
        if displaced is not None:
            changes.append(_row(day, displaced, LIVE, DORMANT, DISPLACED, scores[displaced]))
        ledger.append(state_dir, track, ledger.LIFECYCLE, changes, into=into)
    else:
        state.write_trial(out, **common)
    return Admission(aid, admitted, reason, displaced, trial, tuple(changes))
