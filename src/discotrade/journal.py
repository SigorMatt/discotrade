"""The decision journal (DESIGN 9.2, 9.4, 7, 6.2, 10.1; decisions 2026-10-12 24, 25,
48, 49, 51, 54, 64; I-5, I-6, I-7, I-12).

One Parquet file per trading day ``journal/<track>/<YYYY>/<YYYY-MM-DD>.parquet``
holds one row per subject, instrument and bar of that day, with the columns
``COLUMNS`` (decision 49) in the types of ``SCHEMA``; ``journal/<track>/index.jsonl``
holds one line per day, the canonical JSON (keys sorted, no whitespace) of
``date``, ``rows``, ``content_hash`` and ``key`` (the key columns ``KEY``:
``subject``, ``instrument``, ``ts``), the field names being chosen here where
the design is silent. The content hash is :func:`discotrade.state.content_hash`
of the day's rows on ``KEY``.

The API, for the units that build on it:

- ``Setup.load(config_dir, track_name)``: the track, its instruments, their
  calendars and spread tables, and the thresholds (for the loader).
- ``day_rows(state_dir, setup, day, failures=None)``: the rows of trading day
  ``day`` for every approach the state holds whose admission date is before
  ``day`` and whose lifecycle state in force on ``day`` is live or dormant
  (decisions 48, 63; ``journaled_approaches``), sorted by ``KEY``. With a
  ``failures`` dict, an approach whose evaluation breaks decision 22's
  contract (``ResultError``) has all its rows of ``day`` dropped and its
  error text recorded there (decision 63 step 1: the day goes on). Each
  approach's frozen source runs in-process through the decision-21 loader,
  loaded afresh for each instrument, with its fixed parameters, and only
  when its sha256 is that of a file under the repository's ``reference/`` or
  ``tests/fixtures/`` (``trusted_hashes``); any other source raises
  ``JournalError`` naming the approach before anything is written. The rows
  of an instrument are its bars whose trading date by its own calendar is
  ``day`` and whose ``ts`` is not before ``trusted_from``, evaluated by
  :func:`discotrade.backtest.evaluate` (the one implementation of DESIGN 7,
  its executor and cost model) on the one-day window. Its first row starts
  flat (``prev_position`` and ``position`` 0) when the journal holds no
  earlier row of that approach and instrument; otherwise from that last
  row's ``position`` and ``target_next`` (the state as it stood before
  ``day``, decision 51), whatever day it belongs to. A carried row that is
  not the previous stored bar, or a flat start with an earlier stored bar
  after the admission date, means a day was skipped: ``JournalError``.
  Errors of the loader and the evaluation (``StrategyError``,
  ``ResultError``, ``EvaluationError``, ``BarStoreError``) pass through.
- The controls (DESIGN 10.1; decision 64; :mod:`discotrade.controls`) are in
  ``day_rows`` too, every day from the first day the journal holds
  (``first_day``): ``bh:<symbol>`` on its instrument and ``rc:<slot>`` on every
  instrument, kinds ``control_bh`` and ``control_random``, through
  ``control_evaluations`` (one ``backtest.read_window`` per instrument and one
  ``backtest.score`` of every control's targets on it: the same evaluation
  loop, executor and cost model as approaches), each instrument's first row
  flat and every later one carried from the last journaled row as for an
  approach (a control's admission being the day before the first journaled
  day). The draws in force are those of ``controls/<track>/pools.jsonl`` made
  on or before the day, and, on a draw day whose draw is not recorded, the
  new draw (``draws_for``, ``new_draw``: the live approaches by the lifecycle
  rows dated before the day, their paper days read from the journal days
  before it).
- ``write_day(state_dir, track, day, rows, into=None)``: a day not yet in the
  index has its file and its index line written (each atomically; into the
  directory ``into`` instead of ``state_dir`` when given, for a staging
  directory, the index there being the whole new index). A day already in
  the index is compared: equal content hashes write nothing (I-6, status
  ``unchanged``); unequal ones leave every file untouched and return one
  ``journal_mismatch`` alert per subject whose rows differ, dated ``day``
  (status ``mismatch``).
- ``journal_day(state_dir, setup, day, into=None)``: ``day_rows`` (with a
  ``failures`` dict) then ``write_day``; returns a ``DayResult`` whose
  ``failures`` names each approach dropped for a contract failure. When the
  day is written and a new draw was made, its line is appended to
  ``pools.jsonl`` (into ``into`` when given); a re-run appends none.
- ``read_index``, ``read_day``, ``journal_path``, ``index_path``.
- Recomputation (DESIGN 9.4; decision 54), for ``journal recompute``:
  ``journal_pairs(state_dir, track, setup=None)`` lists every journaled (day,
  subject) pair (each index day with each approach journaled that day,
  decision 63, and with ``setup`` each control journaled that day);
  ``sample_pairs(pairs, n, day)`` draws ``n`` of those before ``day`` (all
  when fewer exist) with ``numpy.random.default_rng(YYYYMMDD of day)``,
  choosing indices into the sorted pool without replacement (the design
  names the seed, not the draw; this is the simplest); ``recompute(state_dir,
  setup, pairs)`` evaluates each subject once from its first journaled day to
  the last asked for (``span_rows``; the controls from the journal's first
  day with the recorded draws, ``control_span_rows``; no stored row read),
  compares each
  pair's rows with the stored ones by content hash on ``KEY``, and returns a
  ``Recompute`` with one ``journal_mismatch`` alert per mismatched pair. It
  writes nothing; the command appends the alerts to the health log.

A day with no approach holds the controls' rows only (decision 64). No clock
is read (I-12).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from discotrade import controls, ledger, lifecycle
from discotrade.backtest import Evaluation, evaluate, read_window, score
from discotrade.bars.store import write_atomic
from discotrade.config import (
    Calendar,
    DateRange,
    Instrument,
    SpreadTable,
    Thresholds,
    Track,
    load_calendar,
    load_thresholds,
    load_track_config,
)
from discotrade.spreads import spread_table
from discotrade.state import Approach, HealthEvent, canonical_json, content_hash, read_approaches
from discotrade.stats import trading_dates
from discotrade.strategy import ResultError, load_strategy
from discotrade.tradingcal import trading_date

#: The repository whose files an approach's source must equal (decision 48).
REPO_ROOT = Path(__file__).resolve().parents[2]
TRUSTED_DIRS = ("reference", "tests/fixtures")

JOURNAL_DIR = "journal"
INDEX = "index.jsonl"
KIND_APPROACH = "approach"
JOURNAL_MISMATCH = "journal_mismatch"
WRITTEN, UNCHANGED, MISMATCH = "written", "unchanged", "mismatch"

#: The columns of a journal row (DESIGN 9.2; decision 49), in order.
COLUMNS = ("date", "ts", "subject", "kind", "instrument",
           "prev_position", "position", "target_next",
           "fill_price", "trade", "roll",
           "fee", "spread", "slippage", "roll_cost",
           "gross", "net_1x", "net_2x")
#: The key columns of the content hash (decision 49).
KEY = ("subject", "instrument", "ts")
_FLOATS = ("prev_position", "position", "target_next", "fill_price", "trade",
           "fee", "spread", "slippage", "roll_cost", "gross", "net_1x", "net_2x")
SCHEMA = pa.schema(
    [("date", pa.date32()), ("ts", pa.timestamp("ns", tz="UTC")),
     ("subject", pa.string()), ("kind", pa.string()), ("instrument", pa.string())]
    + [(c, pa.bool_() if c == "roll" else pa.float64()) for c in COLUMNS[5:]]
)
assert tuple(SCHEMA.names) == COLUMNS and not set(_FLOATS) - set(COLUMNS)


class JournalError(RuntimeError):
    """A day that cannot be journaled; nothing of it is written."""


@dataclass(frozen=True)
class Setup:
    """What a day of a track is journaled with."""

    track: Track
    instruments: tuple[Instrument, ...]
    calendars: Mapping[str, Calendar]
    spread_tables: Mapping[str, SpreadTable | None]
    thresholds: Thresholds

    @classmethod
    def load(cls, config_dir: Path, track_name: str) -> Setup:
        config_dir = Path(config_dir)
        tc = load_track_config(config_dir, track_name)
        return cls(
            track=tc.track,
            instruments=tc.instruments,
            calendars={name: load_calendar(config_dir / "calendars" / f"{name}.toml")
                       for name in sorted({i.calendar for i in tc.instruments})},
            spread_tables={i.symbol: spread_table(config_dir, i.symbol)
                           for i in tc.instruments},
            thresholds=load_thresholds(config_dir / "thresholds.toml"),
        )


@dataclass(frozen=True)
class DayResult:
    day: date
    status: str                      # WRITTEN, UNCHANGED or MISMATCH
    rows: int
    content_hash: str
    events: tuple[HealthEvent, ...] = ()
    #: (approach id, error text) of each approach whose evaluation broke
    #: decision 22's contract; its rows of the day are not journaled.
    failures: tuple[tuple[str, str], ...] = ()


# --- paths and reading -------------------------------------------------------------------

def journal_path(state_dir: Path, track: str, day: date) -> Path:
    return (Path(state_dir) / JOURNAL_DIR / track / f"{day.year:04d}"
            / f"{day.isoformat()}.parquet")


def index_path(state_dir: Path, track: str) -> Path:
    return Path(state_dir) / JOURNAL_DIR / track / INDEX


def read_index(state_dir: Path, track: str) -> list[dict[str, Any]]:
    """The index lines, in file order; a torn last line is refused."""
    path = index_path(state_dir, track)
    if not path.exists():
        return []
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise JournalError(f"{path} does not end with a newline; its last line is torn")
    return [json.loads(line) for line in data.decode("utf-8").splitlines()]


def _frame(rows: pd.DataFrame) -> pd.DataFrame:
    """``rows`` in the column types a stored file reads back with, sorted by ``KEY``."""
    table = pa.Table.from_pandas(rows[list(COLUMNS)], schema=SCHEMA, preserve_index=False)
    frame = table.to_pandas()
    return frame.sort_values(list(KEY), kind="mergesort").reset_index(drop=True)


def _empty() -> pd.DataFrame:
    return SCHEMA.empty_table().to_pandas()


def read_day(state_dir: Path, track: str, day: date) -> pd.DataFrame | None:
    """The stored rows of ``day``, or None when it has no file."""
    path = journal_path(state_dir, track, day)
    return pq.read_table(path).to_pandas() if path.is_file() else None


# --- the rows of a day -------------------------------------------------------------------

def trusted_hashes(root: Path = REPO_ROOT) -> frozenset[str]:
    """The sha256 of every file under ``reference/`` and ``tests/fixtures/`` of ``root``."""
    out = set()
    for name in TRUSTED_DIRS:
        for path in sorted((root / name).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                out.add(hashlib.sha256(path.read_bytes()).hexdigest())
    return frozenset(out)


@dataclass(frozen=True)
class _Last:
    ts: pd.Timestamp
    date: date
    position: float
    target_next: float


def _carries(state_dir: Path, track: str, day: date, subjects: Mapping[str, date],
             wanted: set[tuple[str, str]]) -> dict[tuple[str, str], _Last]:
    """The last journaled row before ``day`` of each (subject, instrument) of
    ``wanted`` that has one; ``subjects`` maps each subject to its admission
    date (a control's is the day before the first journaled day)."""
    out: dict[tuple[str, str], _Last] = {}
    if not wanted:
        return out
    earliest = min(subjects[s] for s, _ in wanted)
    days = sorted((date.fromisoformat(e["date"]) for e in read_index(state_dir, track)),
                  reverse=True)
    for d in days:
        if d >= day:
            continue
        if d <= earliest or not wanted - out.keys():
            break
        rows = read_day(state_dir, track, d)
        if rows is None:
            raise JournalError(f"the index of {track} names {d.isoformat()}, which has no "
                               f"file {journal_path(state_dir, track, d)}")
        if rows.empty:
            continue
        last = rows.sort_values("ts", kind="mergesort").groupby(
            ["subject", "instrument"], sort=False).tail(1)
        for row in last.itertuples(index=False):
            key = (str(row.subject), str(row.instrument))
            if key in wanted and key not in out:
                out[key] = _Last(pd.Timestamp(row.ts), row.date, float(row.position),
                                 float(row.target_next))
    return out


def _rows(subject: str, kind: str, day: date | None, ev: Evaluation, previous: float
          ) -> pd.DataFrame:
    """The journal rows of ``ev``, dated ``day``, or each its own trading date
    (``ev.rows["date"]``) when ``day`` is None."""
    r = ev.rows
    h = r["h"].to_numpy(dtype=np.float64)
    return pd.DataFrame({
        "date": list(r["date"]) if day is None else [day] * len(r),
        "ts": r["ts"].to_numpy(),
        "subject": subject,
        "kind": kind,
        "instrument": ev.symbol,
        "prev_position": np.concatenate([[previous], h[:-1]]),
        "position": h,
        "target_next": r["p"].to_numpy(dtype=np.float64),
        "fill_price": ev.bars["open"].to_numpy(dtype=np.float64)[ev.first:],
        "trade": r["trade"].to_numpy(dtype=np.float64),
        "roll": ev.rolled[ev.first:].astype(bool),
        "fee": r["fee"].to_numpy(dtype=np.float64),
        "spread": r["spread"].to_numpy(dtype=np.float64),
        "slippage": r["slippage"].to_numpy(dtype=np.float64),
        "roll_cost": r["roll"].to_numpy(dtype=np.float64),
        "gross": r["gross"].to_numpy(dtype=np.float64),
        "net_1x": r["net_1x"].to_numpy(dtype=np.float64),
        "net_2x": r["net_2x"].to_numpy(dtype=np.float64),
    })


def subject_rows(state_dir: Path, setup: Setup, day: date, subject: str, kind: str,
                 source: str, params: Mapping[str, Any], admitted: date,
                 carries: Mapping[tuple[str, str], _Last]) -> list[pd.DataFrame]:
    """The rows of ``day`` of one subject, one frame per instrument with a bar
    that day; the function every subject's rows go through (decision 48)."""
    frames = []
    for inst in setup.instruments:
        calendar = setup.calendars[inst.calendar]
        strat = load_strategy(source, setup.thresholds, name=f"{kind} {subject}")
        last = carries.get((subject, inst.symbol))
        ev = evaluate(state_dir, setup.track, inst, calendar, strat, DateRange(day, day),
                      params=params, spread_table=setup.spread_tables[inst.symbol],
                      start=None if last is None else (last.position, last.target_next))
        if ev.rows.empty:
            continue
        before = ev.bars["ts"].iloc[ev.first - 1] if ev.first > 0 else None
        _check_carry(kind, subject, inst.symbol, calendar, day, admitted, last, before)
        frames.append(_rows(subject, kind, day, ev, 0.0 if last is None else last.position))
    return frames


def _check_carry(kind: str, subject: str, symbol: str, calendar: Calendar, day: date,
                 admitted: date, last: _Last | None, before: pd.Timestamp | None) -> None:
    """Refuse a day whose previous day was skipped (``day_rows``)."""
    if last is not None and before != last.ts:
        raise JournalError(
            f"{kind} {subject} on {symbol}: its last journaled row is at "
            f"{last.ts.isoformat()} but the stored bar before {day.isoformat()} is at "
            f"{before.isoformat() if before is not None else 'none'}; a day was skipped")
    if last is None and before is not None \
            and trading_date(calendar, before.to_pydatetime()) > admitted:
        raise JournalError(
            f"{kind} {subject} on {symbol}: the stored bar at {before.isoformat()} "
            f"is after its admission on {admitted.isoformat()} and has no journal row; "
            f"journal the days in order")


# --- the controls (DESIGN 10.1; decision 64) ---------------------------------------------

def control_names(setup: Setup) -> list[str]:
    """Every control subject of the track."""
    return controls.subjects([i.symbol for i in setup.instruments],
                             int(setup.thresholds["controls.random_pool"]))


def _control_wanted(setup: Setup) -> set[tuple[str, str]]:
    pool = int(setup.thresholds["controls.random_pool"])
    out = {(controls.bh_subject(i.symbol), i.symbol) for i in setup.instruments}
    out |= {(controls.rc_subject(k), i.symbol) for k in range(pool) for i in setup.instruments}
    return out


def control_evaluations(state_dir: Path, setup: Setup, window: DateRange,
                        draws: Sequence[controls.Draw],
                        carries: Mapping[tuple[str, str], _Last] | None = None,
                        check: tuple[date, date] | None = None
                        ) -> list[tuple[str, str, Evaluation, float]]:
    """Every control's evaluation on each instrument over ``window``:
    (subject, kind, evaluation, previous position of its first row), in
    instrument then subject order. Without ``carries`` each instrument's first
    window bar is flat (DESIGN 7.1); with them, each (subject, instrument) that
    has a carried row starts from it (decision 49). ``check`` is (the day, the
    controls' admission) for ``_check_carry``."""
    pool = int(setup.thresholds["controls.random_pool"])
    carries = {} if carries is None else carries
    out = []
    for inst in setup.instruments:
        calendar = setup.calendars[inst.calendar]
        win = read_window(state_dir, setup.track, inst, calendar, window,
                          setup.spread_tables[inst.symbol])
        if win.empty:
            continue
        before = win.bars["ts"].iloc[win.first - 1] if win.first > 0 else None
        stamps = list(win.inside["ts"])
        names = [controls.bh_subject(inst.symbol)] + [controls.rc_subject(k)
                                                       for k in range(pool)]
        items = []
        for name in names:
            kind = controls.kind_of(name) or ""
            last = carries.get((name, inst.symbol))
            if check is not None:
                _check_carry(kind, name, inst.symbol, calendar, check[0], check[1], last,
                             before)
            if kind == controls.KIND_BH:
                targets = controls.bh_targets(len(stamps))
            else:
                targets = controls.random_targets(
                    draws, controls.slot_of(name), inst.symbol, inst.shorting, stamps,
                    win.dates, None if last is None else (last.target_next, last.date))
            items.append((name, targets,
                          None if last is None else (last.position, last.target_next)))
        for (name, _, start), ev in zip(items, score(win, items), strict=True):
            out.append((name, controls.kind_of(name) or "", ev,
                        0.0 if start is None else start[0]))
    return out


def first_day(state_dir: Path, track: str, day: date) -> date:
    """The first day the controls are journaled: the journal's first day, or
    ``day`` when the journal holds none before it."""
    days = [date.fromisoformat(e["date"]) for e in read_index(state_dir, track)]
    return min(days + [day])


def _paper_days(state_dir: Path, track: str, day: date, ids: Sequence[str], window: int
                ) -> dict[str, dict[date, pd.DataFrame]]:
    """Each approach's journal rows per journaled day before ``day``, its last
    ``window`` such days at most."""
    out: dict[str, dict[date, pd.DataFrame]] = {aid: {} for aid in ids}
    days = sorted((date.fromisoformat(e["date"]) for e in read_index(state_dir, track)
                   if date.fromisoformat(e["date"]) < day), reverse=True)
    for d in days:
        if all(len(v) >= window for v in out.values()):
            break
        rows = read_day(state_dir, track, d)
        if rows is None:
            raise JournalError(f"the index of {track} names {d.isoformat()}, which has no "
                               f"file {journal_path(state_dir, track, d)}")
        for aid in ids:
            if len(out[aid]) < window:
                mine = rows[rows["subject"] == aid]
                if len(mine):
                    out[aid][d] = mine
    return out


def new_draw(state_dir: Path, setup: Setup, day: date) -> controls.Draw:
    """The draw made on ``day`` (decision 64), from the live approaches'
    measured pairs or from the track's horizons."""
    th = setup.thresholds
    track = setup.track.name
    pool = int(th["controls.random_pool"])
    window = int(th["controls.match_window_days"])
    min_live = int(th["controls.match_min_live"])
    approaches = read_approaches(state_dir)
    rows = ledger.read(state_dir, track, ledger.LIFECYCLE)
    live = sorted(aid for aid, s in lifecycle.states(rows, approaches, day).items()
                  if s.state == lifecycle.LIVE)
    pairs = None
    if len(live) >= min_live:
        pairs = controls.measured_pairs(_paper_days(state_dir, track, day, live, window),
                                        live, window, min_live)
    return controls.make_draw(day, pool, controls.horizon_bounds(setup.track.horizons), pairs)


def draws_for(state_dir: Path, setup: Setup, day: date, into: Path | None = None
              ) -> tuple[list[controls.Draw], controls.Draw | None]:
    """The draws in force up to ``day`` and, when ``day`` is a draw day whose
    draw is not recorded, that new draw (also in the list)."""
    track = setup.track.name
    recorded = [d for d in controls.read_draws(state_dir, track, into) if d.day <= day]
    first = first_day(state_dir, track, day)
    calendars = [setup.calendars[n] for n in sorted(setup.calendars)]
    earlier = trading_dates(calendars, setup.track.bar_seconds, day.replace(day=1),
                            day - timedelta(days=1)) if day.day > 1 else []
    if not controls.is_draw_day(day, first, earlier) or any(d.day == day for d in recorded):
        return recorded, None
    draw = new_draw(state_dir, setup, day)
    return recorded + [draw], draw


def _require_trusted(approaches: Sequence[Approach]) -> None:
    """Refuse an approach whose source is not a trusted file (decision 48)."""
    if not approaches:
        return
    trusted = trusted_hashes()
    for a in approaches:
        digest = hashlib.sha256(a.source.encode("utf-8")).hexdigest()
        if digest not in trusted:
            raise JournalError(
                f"approach {a.id}: its source (sha256 {digest}) is not that of a file "
                f"under the repository's {' or '.join(d + '/' for d in TRUSTED_DIRS)}; "
                f"until the sandbox, only those run (decision 48); the day fails")


def journaled_approaches(state_dir: Path, track: str, day: date) -> list[Approach]:
    """The approaches journaled on ``day``: admitted before it and, by the
    lifecycle rows dated before it, live or dormant (decision 63), by id."""
    approaches = read_approaches(state_dir)
    rows = ledger.read(state_dir, track, ledger.LIFECYCLE)
    wanted = set(lifecycle.journaled_ids(rows, approaches, day))
    return [a for a in approaches if a.id in wanted]


def day_rows(state_dir: Path, setup: Setup, day: date,
             failures: dict[str, str] | None = None) -> pd.DataFrame:
    """The rows of ``day`` of every approach journaled on it and of every
    control (decision 64), sorted by ``KEY``.

    With ``failures`` given, an approach whose evaluation breaks decision 22's
    contract (``ResultError``) has none of its rows of ``day`` returned and its
    error text recorded there under its id (decision 63, step 1); without it,
    the error passes through."""
    return _day_rows(state_dir, setup, day, failures)[0]


def _day_rows(state_dir: Path, setup: Setup, day: date, failures: dict[str, str] | None,
              into: Path | None = None) -> tuple[pd.DataFrame, controls.Draw | None]:
    track = setup.track.name
    approaches = journaled_approaches(state_dir, track, day)
    _require_trusted(approaches)
    draws, drawn = draws_for(state_dir, setup, day, into)
    first = first_day(state_dir, track, day)
    admitted = {a.id: a.admitted for a in approaches}
    admitted.update(dict.fromkeys(control_names(setup), first - timedelta(days=1)))
    wanted = {(a.id, i.symbol) for a in approaches for i in setup.instruments}
    wanted |= _control_wanted(setup)
    carries = _carries(state_dir, track, day, admitted, wanted)
    frames = []
    for a in approaches:
        try:
            frames += subject_rows(state_dir, setup, day, a.id, KIND_APPROACH, a.source,
                                   a.params, a.admitted, carries)
        except ResultError as exc:
            if failures is None:
                raise
            failures[a.id] = str(exc)
    for name, kind, ev, previous in control_evaluations(
            state_dir, setup, DateRange(day, day), draws, carries,
            check=(day, first - timedelta(days=1))):
        if not ev.rows.empty:
            frames.append(_rows(name, kind, day, ev, previous))
    rows = _frame(pd.concat(frames, ignore_index=True)) if frames else _empty()
    return rows, drawn


# --- writing a day -----------------------------------------------------------------------

def _mismatches(track: str, day: date, stored: pd.DataFrame, rows: pd.DataFrame
                ) -> tuple[HealthEvent, ...]:
    events = []
    for subject in sorted(set(stored["subject"]) | set(rows["subject"])):
        a = content_hash(stored[stored["subject"] == subject], KEY)
        b = content_hash(rows[rows["subject"] == subject], KEY)
        if a != b:
            events.append(HealthEvent(day, "alert", JOURNAL_MISMATCH, subject,
                                      {"track": track, "stored": a, "computed": b}))
    if not events:  # the tables differ, but no subject's rows do (their columns or types)
        events.append(HealthEvent(day, "alert", JOURNAL_MISMATCH, "*",
                                  {"track": track, "stored": content_hash(stored, KEY),
                                   "computed": content_hash(rows, KEY)}))
    return tuple(events)


def write_day(state_dir: Path, track: str, day: date, rows: pd.DataFrame,
              into: Path | None = None) -> DayResult:
    """Write ``day``'s file and index line once; on a re-run compare (DESIGN 9.2)."""
    rows = _frame(rows) if len(rows) else _empty()
    digest = content_hash(rows, KEY)
    index = read_index(state_dir, track)
    entry = next((e for e in index if e["date"] == day.isoformat()), None)
    path = journal_path(state_dir, track, day)
    if entry is None:
        if path.exists():
            raise JournalError(f"{path} exists and the index has no line for it")
        out = Path(state_dir) if into is None else Path(into)
        table = pa.Table.from_pandas(rows, schema=SCHEMA, preserve_index=False)
        write_atomic(journal_path(out, track, day), lambda p: pq.write_table(table, p))
        old = index_path(state_dir, track)
        data = (old.read_bytes() if old.exists() else b"") + (canonical_json({
            "date": day.isoformat(), "rows": len(rows), "content_hash": digest,
            "key": list(KEY)}) + "\n").encode("utf-8")
        write_atomic(index_path(out, track), lambda p: p.write_bytes(data))
        return DayResult(day, WRITTEN, len(rows), digest)
    stored = read_day(state_dir, track, day)
    if stored is None:
        raise JournalError(f"the index of {track} names {day.isoformat()}, which has no "
                           f"file {path}")
    if entry["content_hash"] == digest:
        return DayResult(day, UNCHANGED, len(rows), digest)
    return DayResult(day, MISMATCH, len(rows), digest, _mismatches(track, day, stored, rows))


def journal_day(state_dir: Path, setup: Setup, day: date,
                into: Path | None = None) -> DayResult:
    """Compute ``day``'s rows and write or compare them; an approach that breaks
    decision 22's contract has its rows dropped and is named in ``failures``.
    A new day made on a draw day appends its draw to ``pools.jsonl`` (into
    ``into`` when given); a re-run appends none (decision 64; I-6)."""
    failures: dict[str, str] = {}
    rows, drawn = _day_rows(state_dir, setup, day, failures, into)
    result = write_day(state_dir, setup.track.name, day, rows, into=into)
    if drawn is not None and result.status == WRITTEN:
        controls.append_draw(state_dir, setup.track.name, drawn, into=into)
    return dataclasses.replace(result, failures=tuple(sorted(failures.items())))


# --- recomputation (DESIGN 9.4; decision 54) ---------------------------------------------

Pair = tuple[date, str]


@dataclass(frozen=True)
class Recompute:
    pairs: tuple[Pair, ...]              # recomputed, in (day, subject) order
    mismatches: tuple[Pair, ...]
    events: tuple[HealthEvent, ...]      # one journal_mismatch per mismatched pair


def journal_pairs(state_dir: Path, track: str, setup: Setup | None = None) -> list[Pair]:
    """Every journaled (day, subject) pair: each day of the index with each
    approach ``day_rows`` journals that day (admitted before it and live or
    dormant by the lifecycle, decision 63), less one retired that day for a
    contract failure (its rows of the day are not journaled), and, with
    ``setup``, each control journaled that day (decision 64): every ``rc:<slot>``,
    and ``bh:<symbol>`` on the trading dates of its instrument's calendar, in
    (day, subject) order."""
    days = sorted(date.fromisoformat(e["date"]) for e in read_index(state_dir, track))
    approaches = read_approaches(state_dir)
    rows = ledger.read(state_dir, track, ledger.LIFECYCLE)
    out = [(d, aid) for d in days for aid in lifecycle.was_journaled(rows, approaches, d)]
    if setup is not None and days:
        pool = int(setup.thresholds["controls.random_pool"])
        out += [(d, controls.rc_subject(k)) for d in days for k in range(pool)]
        for inst in setup.instruments:
            on = set(trading_dates([setup.calendars[inst.calendar]], setup.track.bar_seconds,
                                   days[0], days[-1]))
            out += [(d, controls.bh_subject(inst.symbol)) for d in days if d in on]
    return sorted(out)


def sample_pairs(pairs: Sequence[Pair], n: int, day: date) -> list[Pair]:
    """``n`` of the ``pairs`` of days before ``day`` (all of them when fewer
    exist), drawn without replacement by ``numpy.random.default_rng`` seeded
    with ``day`` as the integer ``YYYYMMDD`` (decision 54), in (day, subject)
    order."""
    pool = sorted(p for p in pairs if p[0] < day)
    if len(pool) <= n:
        return pool
    picks = np.random.default_rng(int(day.strftime("%Y%m%d"))).choice(
        len(pool), size=n, replace=False)
    return [pool[k] for k in sorted(int(k) for k in picks)]


def span_rows(state_dir: Path, setup: Setup, approach: Approach, first: date, last: date
              ) -> pd.DataFrame:
    """The rows of ``approach`` from ``first`` to ``last``, evaluated once over
    that window per instrument (its first bar flat, DESIGN 7.1), sorted by
    ``KEY``; each row dated by its instrument's trading date."""
    frames = []
    for inst in setup.instruments:
        strat = load_strategy(approach.source, setup.thresholds,
                              name=f"{KIND_APPROACH} {approach.id}")
        ev = evaluate(state_dir, setup.track, inst, setup.calendars[inst.calendar], strat,
                      DateRange(first, last), params=approach.params,
                      spread_table=setup.spread_tables[inst.symbol])
        if not ev.rows.empty:
            frames.append(_rows(approach.id, KIND_APPROACH, None, ev, 0.0))
    return _frame(pd.concat(frames, ignore_index=True)) if frames else _empty()


def control_span_rows(state_dir: Path, setup: Setup, first: date, last: date,
                      names: Sequence[str] | None = None) -> dict[str, pd.DataFrame]:
    """The rows of each control (of ``names``, all by default) from ``first``
    to ``last``, evaluated once over that window per instrument (its first bar
    flat, DESIGN 7.1) with the draws of ``pools.jsonl`` (decision 64), each
    sorted by ``KEY`` and dated by its instrument's trading date."""
    draws = [d for d in controls.read_draws(state_dir, setup.track.name) if d.day <= last]
    wanted = set(control_names(setup) if names is None else names)
    frames: dict[str, list[pd.DataFrame]] = {name: [] for name in sorted(wanted)}
    for name, kind, ev, _ in control_evaluations(state_dir, setup, DateRange(first, last),
                                                 draws):
        if name in wanted and not ev.rows.empty:
            frames[name].append(_rows(name, kind, None, ev, 0.0))
    return {name: _frame(pd.concat(f, ignore_index=True)) if f else _empty()
            for name, f in frames.items()}


def recompute(state_dir: Path, setup: Setup, pairs: Sequence[Pair]) -> Recompute:
    """Recompute ``pairs`` from the stored bars and the frozen sources and
    compare each with the journal (DESIGN 9.4; decision 54). Each subject is
    evaluated once, from its first journaled day (the first day of the index
    after its admission) to the last day it is asked for; a pair matches when
    the content hashes on ``KEY`` of its stored and recomputed rows are equal.
    A mismatch returns a ``journal_mismatch`` alert dated the pair's day,
    naming its subject, with ``write_day``'s detail. Nothing is written."""
    track = setup.track.name
    pairs = sorted(set(pairs))
    days = sorted(date.fromisoformat(e["date"]) for e in read_index(state_dir, track))
    known = {a.id: a for a in read_approaches(state_dir)}
    names = set(control_names(setup))
    wanted: dict[str, list[date]] = {}
    for d, subject in pairs:
        if subject not in known and subject not in names:
            raise JournalError(f"{subject} is not an approach of the state or a control")
        wanted.setdefault(subject, []).append(d)
    _require_trusted([known[s] for s in sorted(wanted) if s in known])
    computed = {}
    for subject, asked in sorted(wanted.items()):
        if subject in known:
            a = known[subject]
            first = min(d for d in days if d > a.admitted)
            computed[subject] = span_rows(state_dir, setup, a, first, max(asked))
    asked_controls = sorted(s for s in wanted if s in names)
    if asked_controls:
        computed.update(control_span_rows(
            state_dir, setup, days[0], max(max(wanted[s]) for s in asked_controls),
            asked_controls))
    stored_days: dict[date, pd.DataFrame] = {}
    mismatches, events = [], []
    for d, subject in pairs:
        if d not in stored_days:
            rows = read_day(state_dir, track, d)
            if rows is None:
                raise JournalError(f"the index of {track} names {d.isoformat()}, which has "
                                   f"no file {journal_path(state_dir, track, d)}")
            stored_days[d] = rows
        stored = stored_days[d]
        mine = computed[subject]
        a = content_hash(stored[stored["subject"] == subject], KEY)
        b = content_hash(mine[mine["date"] == d], KEY)
        if a != b:
            mismatches.append((d, subject))
            events.append(HealthEvent(d, "alert", JOURNAL_MISMATCH, subject,
                                      {"track": track, "stored": a, "computed": b}))
    return Recompute(tuple(pairs), tuple(mismatches), tuple(events))
