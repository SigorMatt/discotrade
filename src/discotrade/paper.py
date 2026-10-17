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
gives these rows for ``days`` from the approach rows of ``records``;
``clean_members`` with the same arguments gives, per day with a
``portfolio_clean`` row, the ids it averages (decision 2026-10-17-m19 151 (b),
for ``alerts.group_edge``; ``portfolio`` does not call it and is unchanged).

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
  first) and ``day``'s ``portfolio`` rows merged in, in ``KEY`` order, when
  the set of dates the stored records hold is exactly the set of dates of the
  journal index before ``day``; otherwise (no records stored, a journaled
  date missing, a date the index does not name before ``day``) it is
  ``rebuild`` (decision 2026-10-14 78: this heals a day whose paper rows an
  interrupted move left out). With that rule the result equals a rebuild
  from the whole journal (when the stored rows of the dates it holds are a
  rebuild's), since a day's records depend only on that day's rows and
  the lifecycle rows dated before it (mission 9 U3: the day no longer
  rebuilds every day from the whole journal).
- ``write(root, track, frame)`` writes the file under ``root`` atomically;
  ``read(state_dir, track)`` reads it back (None when there is none);
  ``paper_path(root, track)``.

Static exposure and the adjusted series (owner's decision O-4; decision
2026-10-14 81; decisions 2026-10-12 23, 24, 25). ``adjusted(state_dir, setup,
subject, days, column)`` gives, for each date of ``subject``'s paper record in
the set of trading dates ``days`` (its ``W``), that ``column`` (``gross``,
``net_1x`` or ``net_2x``) of the paper record minus the static exposure on
that date: the gross timing return for ``gross``, the exposure-adjusted net
return otherwise (costs are not adjusted). The pieces:

- ``unit_returns``: ``R_i(D)``, the sum over the bars of instrument ``i``
  whose trading date is ``D`` of the unit return ``r_i(u)``, the journal's
  ``gross(u)`` from ``backtest.score`` (the same code) with the previous and
  the current position 1 (``u-1`` the previous stored bar, prices adjusted as
  of ``u``, so a roll gap is not a return). At an instrument's first stored
  bar read (none trusted before it) there is no previous bar and only the
  second term counts. The bars' sum per day is taken as ``build`` sums an
  instrument's rows of a day.
- ``average_positions``: ``hbar_i(W)``, the mean of the journal ``position``
  of ``subject`` on ``i`` over its rows whose date is in ``W``; 0 with no row
  (from journal rows; ``adjusted`` takes it from the records by ``hbar``).
- The static exposure on ``D``: the sum over the subject's ``N`` instruments,
  in symbol order, of ``hbar_i(W) * R_i(D)``, divided by ``N`` (decision 23:
  an instrument with no bar on ``D`` contributes 0, ``N`` and the
  instruments are those of the paper ``gross``: the track's basket, or the
  one instrument of a ``control_bh``).

The derived exposure records (decision 2026-10-14 84; REVIEW-10 note 3).
``adjusted`` reads them, not the journal or the bars:

- ``paper/<track>/unit.parquet`` (``UNIT_SCHEMA``, key ``UNIT_KEY``): for each
  instrument of the track and each journaled date ``D``, ``R_i(D)``
  (``unit_returns``), 0.0 on a date the instrument has no stored bar (the
  simplest reading: one row per instrument and journaled date, so that the
  file's dates are the journal index's). A stored ``R_i(D)`` does not change
  with a later roll: prices are adjusted as of each bar (decision 81 (b)).
- ``paper/<track>/positions.parquet`` (``POSITIONS_SCHEMA``, key
  ``POSITIONS_KEY``): per subject, instrument and journaled date with a
  journal row of that subject on that instrument, the row count ``rows`` and
  the summed ``position``. ``hbar(positions, subject, symbols, W)`` is the
  summed position over ``W`` divided by the row count over ``W``, 0 with no
  row.
- ``unit_records(state_dir, setup, days)``, ``position_records(rows)``;
  ``rebuild_exposure(state_dir, setup, overlay=None)``: both of every journaled
  day (``overlay``'s index and day files first); ``update_exposure(state_dir,
  setup, day, overlay=None)``: the stored ones with ``day``'s added when the
  unit records' dates are exactly the journal index's before ``day`` and the
  position records' are exactly those of them with a row (index ``rows`` > 0),
  else ``rebuild_exposure`` (decision 78's rule), so that with that rule the
  result equals a rebuild's; ``write_exposure(root, track, unit, positions)``,
  ``read_unit``, ``read_positions``. The day writes them into its staging
  directory on a new day only (``daily``); a re-run writes neither (I-6).
- ``adjusted(..., records=None, overlay=None)`` reads the records from
  ``overlay`` first: a caller passing staged paper ``records`` passes the
  staging directory as ``overlay`` too, so that the staged day's own rows are
  read; a paper day of ``subject`` in ``W`` that the unit records do not hold
  is refused with ``ValueError``, as are absent records.

No rule reads ``adjusted`` in this unit (decision 81 (e)).

The same series on a window ``W`` from evaluation rows (decision 2026-10-14-m12
97 (b), (c); O-17): ``adjusted_rows(evaluations, units, column)`` takes a
subject's per-instrument evaluations on ``W`` (``backtest.score``'s) in place of
its stored records, with ``hbar_i(W)`` the mean of their ``h`` over the
window bars (``window_positions``), and ``units`` from ``window_units(win)``,
``R_i(D)`` of each trading date of ``win``'s window bars, computed by the code
``unit_bars`` uses. ``adjusted``
and ``adjusted_rows`` compute the subtraction through one private function,
``_less_exposure``, so that O-4 has one implementation.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from discotrade import backtest, journal, ledger, lifecycle
from discotrade.bars.store import write_atomic
from discotrade.config import DateRange, Instrument
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
#: The derived exposure records (decision 2026-10-14 84).
UNIT_FILE = "unit.parquet"
POSITIONS_FILE = "positions.parquet"
UNIT_KEY = ("instrument", "date")
POSITIONS_KEY = ("subject", "instrument", "date")
UNIT_SCHEMA = pa.schema([("instrument", pa.string()), ("date", pa.date32()),
                         ("unit", pa.float64())])
POSITIONS_SCHEMA = pa.schema([("subject", pa.string()), ("instrument", pa.string()),
                              ("date", pa.date32()), ("rows", pa.int64()),
                              ("position", pa.float64())])


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


def clean_members(records: pd.DataFrame, days: Iterable[date],
                  lifecycle_rows: Sequence[Mapping[str, Any]],
                  approaches: Sequence[Approach]) -> dict[date, list[str]]:
    """The members ``portfolio`` counts in ``portfolio_clean`` on each of ``days``
    (decision 2026-10-17-m19 151 (b)): the approaches live at the start of the
    day (``members``) with a clean paper row in ``records`` that day, by id. A
    day with none is left out, as ``portfolio_clean`` has no row on it."""
    mine = records[records["kind"] == APPROACH]
    clean = {(str(s), d) for s, d, c in zip(mine["subject"], mine["date"], mine["clean"],
                                            strict=True) if bool(c)}
    out = {}
    for day in sorted(set(days)):
        ids = [aid for aid in members(lifecycle_rows, approaches, day) if (aid, day) in clean]
        if ids:
            out[day] = ids
    return out


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


def _journaled_before(state_dir: Path, track: str, day: date,
                      overlay: Path | None) -> set[date]:
    """The dates of the journal index of ``track`` before ``day``, ``overlay``'s
    index read first."""
    staged = overlay is not None and journal.index_path(overlay, track).exists()
    index = journal.read_index(Path(overlay) if staged else Path(state_dir), track)
    return {d for d in (date.fromisoformat(e["date"]) for e in index) if d < day}


def update(state_dir: Path, track: str, n_instruments: int, day: date,
           overlay: Path | None = None) -> pd.DataFrame:
    """The stored paper records with ``day``'s journal rows added, sorted by ``KEY``."""
    stored = read(state_dir, track)
    if stored is None or set(stored["date"]) != _journaled_before(state_dir, track, day,
                                                                  overlay):
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


# --- static exposure and the adjusted series (O-4; decision 2026-10-14 81) ------------------

#: The ``gross`` of a position of 1 held into and through a bar (decision 81 (b)).
_UNIT = "unit"


def _window_units(win: backtest.Window) -> np.ndarray:
    """The unit return ``r_i(u)`` of each window bar of ``win``, in bar order
    (decision 81 (b)): the journal's ``gross`` from ``backtest.score`` with the
    previous and the current position 1."""
    head: list[float] = []
    if win.first == 0:
        # The instrument's first stored bar: no previous bar, so only the
        # second term of DESIGN 7.2 with h(u) = 1; the later bars are scored
        # with that bar as the one before them.
        o, c = float(win.inside["open"].iloc[0]), float(win.inside["close"].iloc[0])
        head = [(1.0 * (c - o)) / o]
        win = dataclasses.replace(win, inside=win.inside.iloc[1:], dates=list(win.dates)[1:],
                                  first=1)
    unit = np.array(head, dtype=np.float64)
    if not win.empty:
        ones = np.ones(len(win.inside), dtype=np.float64)
        ev = backtest.score(win, [(_UNIT, ones, (1.0, 1.0))])[0]
        unit = np.concatenate([unit, ev.rows["gross"].to_numpy(dtype=np.float64)])
    return unit


def unit_bars(state_dir: Path, setup: journal.Setup, instrument: Instrument,
              days: Iterable[date]) -> pd.DataFrame:
    """The unit return ``r_i(u)`` (column ``unit``) of each stored bar ``u`` of
    ``instrument`` whose trading date (column ``date``) is in ``days``, with
    its ``ts``, in bar order (decision 81 (b))."""
    wanted = set(days)
    empty = pd.DataFrame({"ts": pd.Series([], dtype="datetime64[ns, UTC]"),
                          "date": pd.Series([], dtype=object),
                          "unit": pd.Series([], dtype="float64")})
    if not wanted:
        return empty
    win = backtest.read_window(state_dir, setup.track, instrument,
                               setup.calendars[instrument.calendar],
                               DateRange(min(wanted), max(wanted)),
                               setup.spread_tables.get(instrument.symbol))
    if win.empty:
        return empty
    stamps, dates = win.inside["ts"].to_numpy(), list(win.dates)
    unit = _window_units(win)
    keep = np.array([d in wanted for d in dates], dtype=bool)
    return pd.DataFrame({"ts": stamps[keep],
                         "date": [d for d, k in zip(dates, keep, strict=True) if k],
                         "unit": unit[keep]})


def window_units(win: backtest.Window) -> dict[date, float]:
    """``R_i(D)`` of the instrument of ``win`` for each trading date ``D`` of its
    window bars: their unit returns (decision 81 (b)) summed per date in bar
    order, as ``unit_returns`` sums them (decision 2026-10-14-m12 97 (b))."""
    if win.empty:
        return {}
    frame = pd.DataFrame({"date": list(win.dates), "unit": _window_units(win)})
    return {d: float(leg.to_numpy(dtype=np.float64).sum())
            for d, leg in frame.groupby("date", sort=True)["unit"]}


def unit_returns(state_dir: Path, setup: journal.Setup, instrument: Instrument,
                 days: Iterable[date]) -> dict[date, float]:
    """``R_i(D)`` of ``instrument`` for each date ``D`` of ``days`` on which it
    has a stored bar: its bars' unit returns summed as ``build`` sums an
    instrument's rows of a day (decision 81 (b))."""
    bars = unit_bars(state_dir, setup, instrument, days)
    return {d: float(leg.to_numpy(dtype=np.float64).sum())
            for d, leg in bars.groupby("date", sort=True)["unit"]}


def average_positions(rows: pd.DataFrame, symbols: Sequence[str]) -> dict[str, float]:
    """``hbar_i(W)`` for each of ``symbols`` from one subject's journal ``rows``
    of ``W`` (decision 81 (c)): the mean of ``position``, 0 with no row."""
    out = {}
    for symbol in symbols:
        mine = rows["position"][rows["instrument"] == symbol].to_numpy(dtype=np.float64)
        out[symbol] = float(mine.mean()) if len(mine) else 0.0
    return out


def hbar(positions: pd.DataFrame, subject: str, symbols: Sequence[str],
         days: Iterable[date]) -> dict[str, float]:
    """``hbar_i(W)`` for each of ``symbols`` from the position records
    ``positions`` of ``subject`` whose date is in ``days`` (decisions 81 (c),
    84): the summed position over ``W`` divided by the row count over ``W``,
    0 with no row."""
    wanted = set(days)
    mine = positions[(positions["subject"] == subject) & positions["date"].isin(wanted)]
    out = {}
    for symbol in symbols:
        leg = mine[mine["instrument"] == symbol]
        rows = int(leg["rows"].to_numpy(dtype=np.int64).sum())
        total = float(leg["position"].to_numpy(dtype=np.float64).sum())
        out[symbol] = total / rows if rows else 0.0
    return out


def unit_records(state_dir: Path, setup: journal.Setup, days: Iterable[date]) -> pd.DataFrame:
    """The unit records of ``days``: for each instrument of the track and each
    date of ``days``, ``R_i(D)`` (``unit_returns``; 0.0 on a date it has no
    stored bar), sorted by ``UNIT_KEY``."""
    wanted = sorted(set(days))
    out = []
    for inst in sorted(setup.instruments, key=lambda i: i.symbol):
        unit = unit_returns(state_dir, setup, inst, wanted) if wanted else {}
        out.extend({"instrument": inst.symbol, "date": d, "unit": unit.get(d, 0.0)}
                   for d in wanted)
    return pa.Table.from_pylist(out, schema=UNIT_SCHEMA).to_pandas()


def position_records(rows: pd.DataFrame) -> pd.DataFrame:
    """The position records of journal ``rows``: per subject, instrument and
    date, the row count and the summed ``position``, sorted by ``POSITIONS_KEY``."""
    out = []
    if len(rows):
        for (subject, symbol, day), mine in rows.groupby(["subject", "instrument", "date"],
                                                         sort=True):
            out.append({"subject": subject, "instrument": symbol, "date": day,
                        "rows": len(mine),
                        "position": float(mine["position"].to_numpy(dtype=np.float64).sum())})
    return pa.Table.from_pylist(out, schema=POSITIONS_SCHEMA).to_pandas()


def _index(state_dir: Path, track: str, overlay: Path | None) -> list[dict[str, Any]]:
    staged = overlay is not None and journal.index_path(overlay, track).exists()
    return journal.read_index(Path(overlay) if staged else Path(state_dir), track)


def _day_rows(state_dir: Path, track: str, day: date, overlay: Path | None) -> pd.DataFrame:
    rows = None if overlay is None else journal.read_day(overlay, track, day)
    if rows is None:
        rows = journal.read_day(state_dir, track, day)
    if rows is None:
        raise journal.JournalError(f"{track} has no journal file for {day.isoformat()}")
    return rows


def _sorted(frame: pd.DataFrame, key: Sequence[str]) -> pd.DataFrame:
    return frame.sort_values(list(key), kind="stable").reset_index(drop=True)


def rebuild_exposure(state_dir: Path, setup: journal.Setup, overlay: Path | None = None
                     ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(unit, positions)`` of every journaled day of the track, ``overlay``'s
    index and day files read first."""
    track = setup.track.name
    days = [date.fromisoformat(e["date"]) for e in _index(state_dir, track, overlay)]
    frames = [position_records(_day_rows(state_dir, track, d, overlay)) for d in days]
    held = [f for f in frames if len(f)]
    positions = (_sorted(pd.concat(held, ignore_index=True), POSITIONS_KEY) if held
                 else POSITIONS_SCHEMA.empty_table().to_pandas())
    return unit_records(state_dir, setup, days), positions


def update_exposure(state_dir: Path, setup: journal.Setup, day: date,
                    overlay: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The stored records with ``day``'s added, when the dates the unit records
    hold are exactly the journal index's before ``day`` and the dates the
    position records hold are exactly those of them with a row; otherwise
    ``rebuild_exposure`` (decision 2026-10-14 78)."""
    track = setup.track.name
    unit, positions = read_unit(state_dir, track), read_positions(state_dir, track)
    before = [e for e in _index(state_dir, track, overlay)
              if date.fromisoformat(e["date"]) < day]
    if (unit is None or positions is None
            or set(unit["date"]) != {date.fromisoformat(e["date"]) for e in before}
            or set(positions["date"]) != {date.fromisoformat(e["date"]) for e in before
                                          if int(e["rows"]) > 0}):
        return rebuild_exposure(state_dir, setup, overlay=overlay)
    new_unit = unit_records(state_dir, setup, [day])
    new_positions = position_records(_day_rows(state_dir, track, day, overlay))
    unit = _sorted(pd.concat([unit, new_unit], ignore_index=True), UNIT_KEY)
    if len(new_positions):
        positions = _sorted(pd.concat([positions, new_positions], ignore_index=True)
                            if len(positions) else new_positions, POSITIONS_KEY)
    return unit, positions


def unit_path(root: Path, track: str) -> Path:
    return Path(root) / PAPER_DIR / track / UNIT_FILE


def positions_path(root: Path, track: str) -> Path:
    return Path(root) / PAPER_DIR / track / POSITIONS_FILE


def write_exposure(root: Path, track: str, unit: pd.DataFrame,
                   positions: pd.DataFrame) -> tuple[Path, Path]:
    """Write the two records under ``root`` atomically; return their paths."""
    out = []
    for path, frame, schema in ((unit_path(root, track), unit, UNIT_SCHEMA),
                                (positions_path(root, track), positions, POSITIONS_SCHEMA)):
        table = pa.Table.from_pandas(frame[list(schema.names)], schema=schema,
                                     preserve_index=False)
        write_atomic(path, lambda p, table=table: pq.write_table(table, p))
        out.append(path)
    return out[0], out[1]


def read_unit(state_dir: Path, track: str) -> pd.DataFrame | None:
    path = unit_path(state_dir, track)
    return pq.read_table(path).to_pandas() if path.is_file() else None


def read_positions(state_dir: Path, track: str) -> pd.DataFrame | None:
    path = positions_path(state_dir, track)
    return pq.read_table(path).to_pandas() if path.is_file() else None


def _read_staged(reader: Any, state_dir: Path, track: str,
                 overlay: Path | None) -> pd.DataFrame:
    frame = None if overlay is None else reader(overlay, track)
    if frame is None:
        frame = reader(state_dir, track)
    if frame is None:
        raise ValueError(f"{track} has no derived exposure records under "
                         f"{PAPER_DIR}/{track}/")
    return frame


def adjusted(state_dir: Path, setup: journal.Setup, subject: str, days: Iterable[date],
             column: str, records: pd.DataFrame | None = None,
             overlay: Path | None = None,
             exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None) -> pd.Series:
    """``column`` of ``subject``'s paper record minus its static exposure, on
    each of its paper days in ``days`` (decision 81 (a)), indexed by date in
    order, from the derived exposure records (decision 84; ``overlay``'s
    first). ``records`` are the paper records (the stored ones when None); a
    caller passing staged records passes ``overlay`` too. ``exposure`` is the
    pair (unit records, position records) a caller has already read, as this
    function reads them, holding at least their rows dated in ``days``; None
    reads them here, and the result is the same (decision 2026-10-17-m19
    147 (d))."""
    if column not in _VALUES:
        raise ValueError(f"{column!r} is not one of {', '.join(_VALUES)}")
    state_dir = Path(state_dir)
    track = setup.track.name
    wanted = set(days)
    if records is None:
        records = read(state_dir, track)
    if records is None or not wanted:
        return pd.Series([], dtype="float64", name=column)
    mine = records[(records["subject"] == subject) & records["date"].isin(wanted)]
    mine = mine.sort_values("date", kind="stable")
    if mine.empty:
        return pd.Series([], dtype="float64", name=column)
    kinds = sorted(set(mine["kind"]))
    if kinds == [PORTFOLIO_KIND] or len(kinds) != 1:
        raise ValueError(f"{subject} is not a subject of the journal")
    if exposure is None:
        unit_frame = _read_staged(read_unit, state_dir, track, overlay)
        positions = _read_staged(read_positions, state_dir, track, overlay)
    else:
        unit_frame, positions = exposure
    if kinds[0] == BH:
        held = positions[(positions["subject"] == subject) & positions["date"].isin(wanted)]
        symbols = sorted(set(held["instrument"]))
        n = 1
    else:
        symbols = sorted(inst.symbol for inst in setup.instruments)
        n = len(setup.instruments)
    average = hbar(positions, subject, symbols, wanted)
    paper_days = set(mine["date"])
    near = unit_frame[unit_frame["date"].isin(paper_days)]
    unit = {(str(s), d): float(v) for s, d, v in zip(near["instrument"], near["date"],
                                                     near["unit"], strict=True)}
    missing = sorted(paper_days - set(near["date"]))
    if missing:
        raise ValueError(f"the exposure records of {track} hold no {missing[0].isoformat()}; "
                         f"a caller passing staged paper records passes overlay too")
    values = _less_exposure(zip(mine["date"], mine[column], strict=True), symbols, average,
                            unit, n)
    return pd.Series(values, index=list(mine["date"]), dtype="float64", name=column)


def _less_exposure(values: Iterable[tuple[date, Any]], symbols: Sequence[str],
                   average: Mapping[str, float], unit: Mapping[tuple[str, date], float],
                   n: int) -> list[float]:
    """O-4's one subtraction: each ``(D, value)`` of ``values`` less the static
    exposure on ``D``, the sum over ``symbols``, in their order, of
    ``average[i] * unit[(i, D)]`` (0 where ``unit`` holds no ``(i, D)``) divided
    by ``n``. ``adjusted`` and ``adjusted_rows`` both compute through it
    (decision 2026-10-14-m12 97 (c))."""
    out = []
    for day, value in values:
        total = 0.0
        for s in symbols:
            total = total + average[s] * unit.get((s, day), 0.0)
        out.append(float(value) - total / n)
    return out


def window_positions(evaluations: Sequence[backtest.Evaluation]) -> dict[str, float]:
    """``hbar_i(W)`` of each evaluation's instrument: the mean of its rows' ``h``
    over its window bars, 0 with none (decision 2026-10-14-m12 97 (b))."""
    out = {}
    for ev in evaluations:
        held = ev.rows["h"].to_numpy(dtype=np.float64)
        out[ev.symbol] = float(held.mean()) if len(held) else 0.0
    return out


def adjusted_rows(evaluations: Sequence[backtest.Evaluation],
                  units: Sequence[Mapping[date, float]], column: str) -> pd.Series:
    """O-4's series over a window ``W`` from per-instrument evaluation rows, in
    place of a subject's stored records (decision 2026-10-14-m12 97 (b), (c)).

    ``evaluations`` are the subject's, one per instrument (an instrument with no
    window bar included), and ``units[k]`` the ``R_i(D)`` of the instrument of
    ``evaluations[k]`` on its window's trading dates (``window_units``). On
    each of the subject's days (the sorted union of the trading dates of its
    rows, decision 23), the value is the decision-23 daily ``column``
    (``gross``, ``net_1x`` or ``net_2x``: the sum over the ``N`` instruments, in
    symbol order, of the instrument's summed ``column`` that day, over ``N``)
    less the static exposure, ``hbar_i(W)`` being the mean of the rows' ``h``
    over the window bars (0 with none). Indexed by date in order."""
    if column not in _VALUES:
        raise ValueError(f"{column!r} is not one of {', '.join(_VALUES)}")
    if len(evaluations) != len(units):
        raise ValueError(f"{len(evaluations)} evaluations for {len(units)} unit records")
    n = len(evaluations)
    if n < 1:
        raise ValueError("a subject has at least one instrument")
    legs = sorted(zip(evaluations, units, strict=True), key=lambda leg: leg[0].symbol)
    symbols = [ev.symbol for ev, _ in legs]
    if len(set(symbols)) != n:
        raise ValueError("each instrument gives one evaluation")
    average = window_positions([ev for ev, _ in legs])
    unit: dict[tuple[str, date], float] = {}
    per_day: list[dict[date, float]] = []
    for ev, mine in legs:
        unit.update({(ev.symbol, d): float(v) for d, v in mine.items()})
        per_day.append({d: float(leg.to_numpy(dtype=np.float64).sum())
                        for d, leg in ev.rows.groupby("date", sort=True)[column]}
                       if len(ev.rows) else {})
    days = sorted({d for sums in per_day for d in sums})
    daily = []
    for day in days:
        total = 0.0
        for sums in per_day:
            total = total + sums.get(day, 0.0)
        daily.append((day, total / n))
    values = _less_exposure(daily, symbols, average, unit, n)
    return pd.Series(values, index=days, dtype="float64", name=column)
