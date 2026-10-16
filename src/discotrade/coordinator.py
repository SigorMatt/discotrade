"""The coordinator (DESIGN 14.1, 14.2 (the scripted form), 14.3, 16.1 step 3;
decision 2026-10-16-m15 125; I-8, I-10).

- The interface (14.1): :class:`Coordinator` chooses one cell from the offered
  :class:`CellStatus` list and the registry lines and writes its :class:`Brief`;
  it writes the digest prose from :class:`AlertPayload` records and the run log
  line from a :class:`RunSummary`. ``AlertPayload`` and ``RunSummary`` are
  minimal records that steps S4.1 and S4.2 extend.
- A :class:`CellStatus` holds a cell, its count of live approaches, its free
  slots and the flag ``weak``, and nothing else: no score, no return, no rank
  (I-8). :func:`cell_statuses` builds one per cell of the track, in cell order,
  for a day ``D`` from the approaches, the lifecycle rows and the paper day
  counts. The states are those in force on ``D`` (``lifecycle.states``: rows
  dated before ``D``, approaches admitted before ``D``), as the registry reads
  them (decision 116 (b); decision 125 says "live in the cell on D"). ``free``
  is ``cell_slots`` less the live count, never below 0. ``weak`` is true when
  the cell has no live approach, or when every approach live in it on ``D`` has
  a lifecycle row to ``dormant`` (any reason) dated before ``D`` and within its
  first ``coordinator.weak_window_days`` paper days: its paper days are the
  dates of its rows in the paper records, and a row dated ``d`` is within the
  first ``k`` when the approach has at most ``k`` paper days on or before ``d``
  (the design is silent on the count; this is the simplest reading). Only the
  ``subject`` and ``date`` columns of the paper records are read; no return,
  no lifecycle figure and no trial row is read (I-8; owner's O-18 note on the
  flag).
- The offered cells (16.1 step 3; 125 (b)): :func:`offered`, the cells with a
  free slot or flagged weak, in cell order.
- The registry the coordinator is given: :func:`registry_lines`, the
  ``workers.registry`` line of every approach live or dormant on ``D``, by cell
  index then id (the decision names the argument, not its content; the lines of
  every cell are the simplest reading).
- The scripted form (14.2; 125 (c)): :class:`ScriptedCoordinator` takes the
  offered cell with the fewest live approaches, the lowest cell index of its
  track on a tie; its brief is a fixed template naming the cell's family and
  horizon; the digest and the run log line are fixed templates of their
  inputs. No template holds a date, a symbol or a number taken from a score.
- What the harness does with the output (14.3; 125 (d)): :func:`choose`. No
  offered cell means no call and no generation (``(None, [])``). A chosen cell
  that is not one of the offered is replaced by the scripted choice (its cell
  and brief) with a ``coordinator_fallback`` health notice (subject the chosen
  cell, detail the chosen and used cells). The brief text is sanitized and cut
  to ``coordinator.brief_max_chars`` by ``workers.registry.sanitize`` (decision
  116 (b)). The coordinator's token budget is step S4.2's.

Nothing here reads a clock, the network or a secret, and nothing here is called
from ``run-day`` or ``replay`` (decision 118 (a)).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import pyarrow.parquet as pq

from discotrade import ledger, lifecycle, paper, state
from discotrade.config import Thresholds, Track
from discotrade.state import HealthEvent
from discotrade.workers import registry

WEAK_KEY = "coordinator.weak_window_days"
BRIEF_KEY = "coordinator.brief_max_chars"
FALLBACK = "coordinator_fallback"

Cell = tuple[str, str]


@dataclass(frozen=True)
class CellStatus:
    """A cell, its live approaches, its free slots and the weak flag (DESIGN 14.1)."""

    cell: Cell
    live: int
    free: int
    weak: bool


@dataclass(frozen=True)
class Brief:
    """The chosen cell and the brief for its worker."""

    cell: Cell
    text: str


@dataclass(frozen=True)
class AlertPayload:
    """An alert that fired: its kind and subject (extended by step S4.1)."""

    kind: str
    subject: str


@dataclass(frozen=True)
class RunSummary:
    """A day with no alert: the track and the cell generated in, if any
    (extended by step S4.2)."""

    track: str
    cell: Cell | None


class Coordinator(Protocol):
    def choose_cell(self, cells: list[CellStatus], registry: list[str]) -> Brief: ...
    def write_digest(self, alerts: list[AlertPayload]) -> str: ...
    def write_runlog_line(self, summary: RunSummary) -> str: ...


def _name(cell: Cell) -> str:
    return f"{cell[0]}/{cell[1]}"


# --- the coordinator's input (DESIGN 14.1, 16.1 step 3) -------------------------------------


def _paper_dates(state_dir: Path, track: str) -> dict[str, list[date]]:
    """Each subject's paper dates, sorted; only ``subject`` and ``date`` are read."""
    path = paper.paper_path(Path(state_dir), track)
    if not path.is_file():
        return {}
    frame = pq.read_table(path, columns=["subject", "date"]).to_pandas()
    out: dict[str, list[date]] = {}
    for subject, day in zip(frame["subject"], frame["date"], strict=True):
        out.setdefault(str(subject), []).append(day)
    return {k: sorted(v) for k, v in out.items()}


def _early_dormant(aid: str, rows: Sequence[Mapping[str, Any]], day: date,
                   dates: Sequence[date], window: int) -> bool:
    """Whether ``aid`` has a row to dormant dated before ``day`` within its first
    ``window`` paper days."""
    for row in rows:
        when = date.fromisoformat(str(row["date"]))
        if row["id"] == aid and row["to"] == lifecycle.DORMANT and when < day:
            if sum(1 for d in dates if d <= when) <= window:
                return True
    return False


def cell_statuses(state_dir: Path, track: Track, thresholds: Thresholds,
                  day: date) -> list[CellStatus]:
    """One :class:`CellStatus` per cell of ``track`` on ``day``, in cell order."""
    window = int(thresholds[WEAK_KEY])
    approaches = state.read_approaches(Path(state_dir))
    rows = ledger.read(Path(state_dir), track.name, ledger.LIFECYCLE)
    in_force = lifecycle.states(rows, approaches, day)
    cells = {a.id: str(a.meta["cell"]) for a in approaches}
    dates = _paper_dates(Path(state_dir), track.name)
    out = []
    for cell in track.cells:
        live = sorted(aid for aid, s in in_force.items()
                      if s.state == lifecycle.LIVE and cells[aid] == _name(cell))
        weak = not live or all(_early_dormant(aid, rows, day, dates.get(aid, []), window)
                               for aid in live)
        out.append(CellStatus(cell, len(live), max(0, int(track.cell_slots) - len(live)),
                              weak))
    return out


def offered(statuses: Sequence[CellStatus]) -> list[CellStatus]:
    """The cells with a free slot or flagged weak, in the order given."""
    return [s for s in statuses if s.free > 0 or s.weak]


def registry_lines(state_dir: Path, track: Track, thresholds: Thresholds,
                   day: date) -> list[str]:
    """The registry line of every approach live or dormant on ``day``, by cell
    index then id."""
    out: list[str] = []
    for cell in track.cells:
        out += [line for line in registry.lines(state_dir, track, thresholds, day, cell)
                if line.split(registry.SEPARATOR)[1] == _name(cell)]
    return out


# --- the scripted form (DESIGN 14.2) ----------------------------------------------------------


class ScriptedCoordinator:
    """The deterministic coordinator of tests, gates and replays."""

    def __init__(self, track: Track) -> None:
        self.track = track

    def choose_cell(self, cells: list[CellStatus], registry: list[str]) -> Brief:
        if not cells:
            raise ValueError("no offered cell to choose from")
        pick = min(cells, key=lambda s: (s.live, self.track.cell_index(*s.cell)))
        family, horizon = pick.cell
        text = (f"Write an approach of the family {family} for the horizon {horizon} "
                "that differs from every line of the registry.")
        return Brief(pick.cell, text)

    def write_digest(self, alerts: list[AlertPayload]) -> str:
        lines = ["Alerts fired today:"]
        lines += [f"- {a.kind} on {a.subject}." for a in alerts]
        lines.append("The tables below give the numbers behind each alert.")
        return "\n".join(lines)

    def write_runlog_line(self, summary: RunSummary) -> str:
        if summary.cell is None:
            return f"Track {summary.track}: no alert, no generation."
        return f"Track {summary.track}: no alert, generation in {_name(summary.cell)}."


# --- what the harness does with the output (DESIGN 14.3) -------------------------------------


def choose(coordinator: Coordinator, cells: Sequence[CellStatus], lines: Sequence[str],
           track: Track, thresholds: Thresholds, day: date
           ) -> tuple[Brief | None, list[HealthEvent]]:
    """The day's brief from ``coordinator`` over the offered ``cells``, and the
    health events; ``(None, [])`` when no cell is offered."""
    cells = list(cells)
    if not cells:
        return None, []
    events: list[HealthEvent] = []
    brief = coordinator.choose_cell(list(cells), list(lines))
    chosen = tuple(brief.cell)
    if chosen not in [s.cell for s in cells]:
        used = ScriptedCoordinator(track).choose_cell(list(cells), list(lines))
        name = "/".join(str(part) for part in chosen)
        events.append(HealthEvent(day, "notice", FALLBACK, name,
                                  {"chosen": name, "used": _name(used.cell)}))
        brief = used
    text = registry.sanitize(brief.text, int(thresholds[BRIEF_KEY]))
    return Brief((brief.cell[0], brief.cell[1]), text), events
