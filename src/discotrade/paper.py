"""Paper records (DESIGN 9.3, 8, 11.3; decisions 2026-10-12 23, 53, 61; I-3, I-6).

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

The API:

- ``build(rows, n_instruments, cutoffs)``: the paper records of journal
  ``rows``; ``cutoffs`` maps each approach id to its cutoff date.
- ``rebuild(state_dir, track, n_instruments, overlay=None)``: ``build`` of every
  day the journal index names, the cutoffs read from the state directory's
  ``approaches/<id>/meta.json`` (``state.read_approaches``); with ``overlay``
  (a staging directory), its index and day files are read in place of the
  state directory's where they exist, so that a staged day is included before
  it is moved into place.
- ``write(root, track, frame)`` writes the file under ``root`` atomically;
  ``read(state_dir, track)`` reads it back (None when there is none);
  ``paper_path(root, track)``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from discotrade import journal
from discotrade.bars.store import write_atomic
from discotrade.metrics import TRADE_FLOOR
from discotrade.state import read_approaches

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


def rebuild(state_dir: Path, track: str, n_instruments: int,
            overlay: Path | None = None) -> pd.DataFrame:
    """``build`` of every journaled day of ``track``, ``overlay`` read first."""
    state_dir = Path(state_dir)
    staged = overlay is not None and journal.index_path(overlay, track).exists()
    index = journal.read_index(Path(overlay) if staged else state_dir, track)
    frames = []
    for entry in index:
        day = pd.Timestamp(entry["date"]).date()
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
    if not frames:
        return _empty()
    cutoffs = {a.id: date.fromisoformat(a.meta["cutoff"]) for a in read_approaches(state_dir)}
    return build(pd.concat(frames, ignore_index=True), n_instruments, cutoffs)


def write(root: Path, track: str, frame: pd.DataFrame) -> Path:
    """Write the paper records under ``root`` atomically; return the path."""
    table = pa.Table.from_pandas(frame[list(COLUMNS)], schema=SCHEMA, preserve_index=False)
    path = paper_path(root, track)
    write_atomic(path, lambda p: pq.write_table(table, p))
    return path


def read(state_dir: Path, track: str) -> pd.DataFrame | None:
    path = paper_path(state_dir, track)
    return pq.read_table(path).to_pandas() if path.is_file() else None
