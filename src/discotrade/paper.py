"""Paper records (DESIGN 9.3, 8, 10.5, 11.3; decisions 2026-10-12 23, 53, 61, 63,
69; I-3, I-6).

``paper/<track>/daily.parquet`` is derived from the decision journal: one row
per subject and trading day on which the journal holds a row of that subject,
so from its first journaled day on, with the columns ``COLUMNS`` in the types
of ``SCHEMA``:

- ``date``, ``subject``, ``kind`` (the journal's);
- ``gross``, ``net_1x``, ``net_2x``: decision 23's daily mean, the sum over
  the subject's ``N`` instruments of that instrument's summed value over its
  rows of the day, divided by ``N`` (an instrument with no row that day adds
  0), summed in instrument order as ``metrics.daily_series`` does;
- ``trades``: the count of the subject's rows of the day with
  ``trade > metrics.TRADE_FLOOR`` (1e-9; DESIGN 8's floor; a roll adds no
  trade);
- ``clean`` (decision 61): for an approach, true when the row's date is after
  the ``cutoff`` date of its ``meta.json`` (the model's cutoff as used, DESIGN
  9.1, 11.3), false on and before it; for a control (``control_random``,
  ``control_bh``), always true. An approach with no cutoff, or a row of
  another kind, is refused.

An approach and a random control (``control_random``) run on the whole
basket, so their ``N`` is the number of the track's instruments, given by the
caller; a buy-and-hold control (``control_bh``) runs on its one instrument
(DESIGN 10.1), so its ``N`` is 1 (the design is silent on how the journal
tells ``N``; this is the simplest reading of decision 23). The key columns of the content hash are
``subject`` and ``date``.

The combined portfolio (DESIGN 10.5, decision 69) adds rows of the two
subjects ``portfolio`` and ``portfolio_clean``, of kind ``portfolio`` (the
design names the subjects, not their kind; one kind for both is the simplest
reading). The members of a day ``D`` are the approaches whose state at the
start of ``D`` (``lifecycle.states`` of the lifecycle rows dated before ``D``
and the admissions before ``D``, decision 63) is ``live`` and that have a
paper row on ``D``; ``portfolio_clean``'s are those of them whose row is
clean. A series' ``gross``, ``net_1x`` and ``net_2x`` are the equal-weight
means of its members' values (``math.fsum`` in id order over the count) and
``trades`` the sum of theirs. ``portfolio`` has a row on every journaled day
(every trading day of the track from the first journaled day, decision 51),
0 in each value with no member, ``clean`` true exactly when every member's row
is clean; ``portfolio_clean`` has a row only on a day with a clean member,
``clean`` true. ``portfolio(records, days, lifecycle_rows, approaches)``
gives these rows for ``days`` from the approach rows of ``records``.

The API:

- ``build(rows, n_instruments, cutoffs)``: the paper records of journal
  ``rows``; ``cutoffs`` maps each approach id to its cutoff date.
- ``rebuild(state_dir, track, n_instruments, overlay=None)``: ``build`` of every
  day the journal index names, the cutoffs read from the state directory's
  ``approaches/<id>/meta.json`` (``state.read_approaches``), with the
  ``portfolio`` rows of every one of those days from the lifecycle ledger
  (``ledger.read``, from ``overlay`` when staged there); with ``overlay``
  (a staging directory), its index and day files are read in place of the
  state directory's where they exist, so that a staged day is included before
  it is moved into place.
- ``update(state_dir, track, n_instruments, day, overlay=None)``: the stored
  records with ``build`` of ``day``'s journal file (read from ``overlay``
  first) and ``day``'s ``portfolio`` rows merged in, in ``KEY`` order: what
  ``rebuild`` gives when the stored records are a rebuild of the journal
  before ``day``, since a day's records depend only on that day's rows and
  the lifecycle rows dated before it (mission 9 U3: the day no longer
  rebuilds every day from the whole journal). When no records are stored, or they
  hold a day on or after ``day``, it is ``rebuild``.
- ``write(root, track, frame)`` writes the file under ``root`` atomically;
  ``read(state_dir, track)`` reads it back (None when there is none);
  ``paper_path(root, track)``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from discotrade import journal, ledger, lifecycle
from discotrade.bars.store import write_atomic
from discotrade.metrics import TRADE_FLOOR
from discotrade.state import Approach, read_approaches

PAPER_DIR = "paper"
FILE = "daily.parquet"
COLUMNS = ("date", "subject", "kind", "gross", "net_1x", "net_2x", "trades", "clean")
KEY = ("subject", "date")
_VALUES = ("gross", "net_1x", "net_2x")
SCHEMA = pa.schema([("date", pa.date32()), ("subject", pa.string()), ("kind", pa.string()),
                    ("gross", pa.float64()), ("net_1x", pa.float64()),
                    ("net_2x", pa.float64()), ("trades", pa.int64()),
                    ("clean", pa.bool_())])
assert tuple(SCHEMA.names) == COLUMNS
APPROACH = "approach"
CONTROL_KINDS = ("control_random", "control_bh")
BH = "control_bh"
PORTFOLIO, PORTFOLIO_CLEAN = "portfolio", "portfolio_clean"
PORTFOLIO_KIND = "portfolio"


def paper_path(root: Path, track: str) -> Path:
    return Path(root) / PAPER_DIR / track / FILE


def _empty() -> pd.DataFrame:
    return SCHEMA.empty_table().to_pandas()


def _clean(subject: str, kind: str, day: date, cutoffs: Mapping[str, date]) -> bool:
    """DESIGN 11.3's flag of one paper row (decision 61)."""
    if kind in CONTROL_KINDS:
        return True
    if kind != APPROACH:
        raise ValueError(f"subject {subject} has rows of the unknown kind {kind!r}")
    if subject not in cutoffs:
        raise ValueError(f"approach {subject} has no recorded model cutoff")
    return bool(day > cutoffs[subject])


def build(rows: pd.DataFrame, n_instruments: int,
          cutoffs: Mapping[str, date]) -> pd.DataFrame:
    """The paper records of the journal ``rows``, sorted by ``KEY``."""
    if n_instruments < 1:
        raise ValueError("a subject has at least one instrument")
    if rows.empty:
        return _empty()
    out = []
    for (subject, day), mine in rows.groupby(["subject", "date"], sort=True):
        kinds = sorted(set(mine["kind"]))
        if len(kinds) != 1:
            raise ValueError(f"subject {subject} has rows of kinds {kinds} on {day}")
        n = 1 if kinds[0] == BH else n_instruments
        totals = dict.fromkeys(_VALUES, 0.0)
        for _, leg in mine.groupby("instrument", sort=True):
            for name in _VALUES:
                totals[name] = totals[name] + float(leg[name].to_numpy(dtype=np.float64).sum())
        out.append({
            "date": day, "subject": subject, "kind": kinds[0],
            **{name: totals[name] / n for name in _VALUES},
            "trades": int(np.count_nonzero(mine["trade"].to_numpy(dtype=np.float64)
                                           > TRADE_FLOOR)),
            "clean": _clean(str(subject), kinds[0], day, cutoffs),
        })
    table = pa.Table.from_pylist(out, schema=SCHEMA)
    return table.to_pandas()


def members(lifecycle_rows: Sequence[Mapping[str, Any]], approaches: Sequence[Approach],
            day: date) -> list[str]:
    """The approaches live at the start of ``day`` (decision 63), by id."""
    return sorted(aid for aid, s in lifecycle.states(lifecycle_rows, approaches, day).items()
                  if s.state == lifecycle.LIVE)


def _series(subject: str, day: date, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    return {"date": day, "subject": subject, "kind": PORTFOLIO_KIND,
            **{name: (math.fsum(float(r[name]) for r in rows) / n if n else 0.0)
               for name in _VALUES},
            "trades": sum(int(r["trades"]) for r in rows),
            "clean": all(bool(r["clean"]) for r in rows)}


def portfolio(records: pd.DataFrame, days: Iterable[date],
              lifecycle_rows: Sequence[Mapping[str, Any]],
              approaches: Sequence[Approach]) -> pd.DataFrame:
    """The ``portfolio`` and ``portfolio_clean`` rows of ``days`` (decision 69)
    from the approach rows of ``records``, sorted by ``KEY``."""
    mine = records[records["kind"] == APPROACH]
    held = {(str(r["subject"]), r["date"]): r for r in mine.to_dict("records")}
    out = []
    for day in sorted(set(days)):
        rows = [held[(aid, day)] for aid in members(lifecycle_rows, approaches, day)
                if (aid, day) in held]
        out.append(_series(PORTFOLIO, day, rows))
        clean = [r for r in rows if bool(r["clean"])]
        if clean:
            out.append(_series(PORTFOLIO_CLEAN, day, clean))
    if not out:
        return _empty()
    frame = pa.Table.from_pylist(out, schema=SCHEMA).to_pandas()
    return frame.sort_values(list(KEY), kind="stable").reset_index(drop=True)


def _merge(*frames: pd.DataFrame) -> pd.DataFrame:
    held = [f for f in frames if len(f)]
    if not held:
        return _empty()
    merged = pd.concat(held, ignore_index=True) if len(held) > 1 else held[0]
    return merged.sort_values(list(KEY), kind="stable").reset_index(drop=True)


def rebuild(state_dir: Path, track: str, n_instruments: int,
            overlay: Path | None = None) -> pd.DataFrame:
    """``build`` of every journaled day of ``track``, ``overlay`` read first."""
    state_dir = Path(state_dir)
    staged = overlay is not None and journal.index_path(overlay, track).exists()
    index = journal.read_index(Path(overlay) if staged else state_dir, track)
    frames = []
    days = []
    for entry in index:
        day = pd.Timestamp(entry["date"]).date()
        days.append(day)
        rows = None
        if overlay is not None:
            rows = journal.read_day(overlay, track, day)
        if rows is None:
            rows = journal.read_day(state_dir, track, day)
        if rows is None:
            raise journal.JournalError(f"the index of {track} names {entry['date']}, which "
                                       f"has no journal file")
        if len(rows):
            frames.append(rows)
    if not days:
        return _empty()
    approaches = read_approaches(state_dir)
    cutoffs = {a.id: date.fromisoformat(a.meta["cutoff"]) for a in approaches}
    records = (build(pd.concat(frames, ignore_index=True), n_instruments, cutoffs)
               if frames else _empty())
    life = ledger.read(state_dir, track, ledger.LIFECYCLE, into=overlay)
    return _merge(records, portfolio(records, days, life, approaches))


def update(state_dir: Path, track: str, n_instruments: int, day: date,
           overlay: Path | None = None) -> pd.DataFrame:
    """The stored paper records with ``day``'s journal rows added, sorted by ``KEY``."""
    stored = read(state_dir, track)
    if stored is None or (len(stored) and max(stored["date"]) >= day):
        return rebuild(state_dir, track, n_instruments, overlay=overlay)
    rows = None if overlay is None else journal.read_day(overlay, track, day)
    if rows is None:
        rows = journal.read_day(state_dir, track, day)
    if rows is None:
        raise journal.JournalError(f"{track} has no journal file for {day.isoformat()}")
    approaches = read_approaches(state_dir)
    cutoffs = {a.id: date.fromisoformat(a.meta["cutoff"]) for a in approaches}
    new = build(rows, n_instruments, cutoffs) if len(rows) else _empty()
    life = ledger.read(state_dir, track, ledger.LIFECYCLE, into=overlay)
    return _merge(stored, new, portfolio(new, [day], life, approaches))


def write(root: Path, track: str, frame: pd.DataFrame) -> Path:
    """Write the paper records under ``root`` atomically; return the path."""
    table = pa.Table.from_pandas(frame[list(COLUMNS)], schema=SCHEMA, preserve_index=False)
    path = paper_path(root, track)
    write_atomic(path, lambda p: pq.write_table(table, p))
    return path


def read(state_dir: Path, track: str) -> pd.DataFrame | None:
    path = paper_path(state_dir, track)
    return pq.read_table(path).to_pandas() if path.is_file() else None
