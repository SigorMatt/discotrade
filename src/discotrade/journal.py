"""The decision journal (DESIGN 9.2, 9.4, 7, 6.2; decisions 2026-10-12 24, 25, 48,
49, 51, 54; I-5, I-6, I-7, I-12).

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
- ``day_rows(state_dir, setup, day)``: the rows of trading day ``day`` for
  every approach the state holds whose admission date is before ``day``
  (decision 48; the lifecycle is step S1.2's), sorted by ``KEY``. Each
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
- ``write_day(state_dir, track, day, rows, into=None)``: a day not yet in the
  index has its file and its index line written (each atomically; into the
  directory ``into`` instead of ``state_dir`` when given, for a staging
  directory, the index there being the whole new index). A day already in
  the index is compared: equal content hashes write nothing (I-6, status
  ``unchanged``); unequal ones leave every file untouched and return one
  ``journal_mismatch`` alert per subject whose rows differ, dated ``day``
  (status ``mismatch``).
- ``journal_day(state_dir, setup, day, into=None)``: ``day_rows`` then
  ``write_day``; returns a ``DayResult``.
- ``read_index``, ``read_day``, ``journal_path``, ``index_path``.
- Recomputation (DESIGN 9.4; decision 54), for ``journal recompute``:
  ``journal_pairs(state_dir, track)`` lists every journaled (day, subject)
  pair (each index day with each approach admitted before it);
  ``sample_pairs(pairs, n, day)`` draws ``n`` of those before ``day`` (all
  when fewer exist) with ``numpy.random.default_rng(YYYYMMDD of day)``,
  choosing indices into the sorted pool without replacement (the design
  names the seed, not the draw; this is the simplest); ``recompute(state_dir,
  setup, pairs)`` evaluates each subject once from its first journaled day to
  the last asked for (``span_rows``, no stored row read), compares each
  pair's rows with the stored ones by content hash on ``KEY``, and returns a
  ``Recompute`` with one ``journal_mismatch`` alert per mismatched pair. It
  writes nothing; the command appends the alerts to the health log.

A day with no subject has a file with no row and its index line. No clock
is read (I-12).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from discotrade.backtest import Evaluation, evaluate
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
from discotrade.strategy import load_strategy
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
    position: float
    target_next: float


def _carries(state_dir: Path, track: str, day: date, subjects: Mapping[str, date],
             symbols: Sequence[str]) -> dict[tuple[str, str], _Last]:
    """The last journaled row before ``day`` of each (subject, instrument) that
    has one; ``subjects`` maps each subject to its admission date."""
    wanted = {(s, i) for s in subjects for i in symbols}
    out: dict[tuple[str, str], _Last] = {}
    if not wanted:
        return out
    earliest = min(subjects.values())
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
        for (subject, symbol) in sorted(wanted - out.keys()):
            mine = rows[(rows["subject"] == subject) & (rows["instrument"] == symbol)]
            if len(mine):
                last = mine.loc[mine["ts"].idxmax()]
                out[(subject, symbol)] = _Last(pd.Timestamp(last["ts"]),
                                               float(last["position"]),
                                               float(last["target_next"]))
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
        if last is not None and before != last.ts:
            raise JournalError(
                f"{kind} {subject} on {inst.symbol}: its last journaled row is at "
                f"{last.ts.isoformat()} but the stored bar before {day.isoformat()} is at "
                f"{before.isoformat() if before is not None else 'none'}; a day was skipped")
        if last is None and before is not None \
                and trading_date(calendar, before.to_pydatetime()) > admitted:
            raise JournalError(
                f"{kind} {subject} on {inst.symbol}: the stored bar at {before.isoformat()} "
                f"is after its admission on {admitted.isoformat()} and has no journal row; "
                f"journal the days in order")
        frames.append(_rows(subject, kind, day, ev, 0.0 if last is None else last.position))
    return frames


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


def day_rows(state_dir: Path, setup: Setup, day: date) -> pd.DataFrame:
    """The rows of ``day`` of every approach admitted before it, sorted by ``KEY``."""
    approaches: list[Approach] = [a for a in read_approaches(state_dir) if a.admitted < day]
    _require_trusted(approaches)
    carries = _carries(state_dir, setup.track.name, day, {a.id: a.admitted for a in approaches},
                       [i.symbol for i in setup.instruments])
    frames = [f for a in approaches
              for f in subject_rows(state_dir, setup, day, a.id, KIND_APPROACH, a.source,
                                    a.params, a.admitted, carries)]
    return _frame(pd.concat(frames, ignore_index=True)) if frames else _empty()


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
    """Compute ``day``'s rows and write or compare them."""
    return write_day(state_dir, setup.track.name, day, day_rows(state_dir, setup, day),
                     into=into)


# --- recomputation (DESIGN 9.4; decision 54) ---------------------------------------------

Pair = tuple[date, str]


@dataclass(frozen=True)
class Recompute:
    pairs: tuple[Pair, ...]              # recomputed, in (day, subject) order
    mismatches: tuple[Pair, ...]
    events: tuple[HealthEvent, ...]      # one journal_mismatch per mismatched pair


def journal_pairs(state_dir: Path, track: str) -> list[Pair]:
    """Every journaled (day, subject) pair: each day of the index with each
    approach of the state admitted before it (the subjects ``day_rows``
    journals that day), in (day, subject) order."""
    days = sorted(date.fromisoformat(e["date"]) for e in read_index(state_dir, track))
    approaches = read_approaches(state_dir)
    return sorted((d, a.id) for d in days for a in approaches if a.admitted < d)


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
    wanted: dict[str, list[date]] = {}
    for d, subject in pairs:
        if subject not in known:
            raise JournalError(f"{subject} is not an approach of the state")
        wanted.setdefault(subject, []).append(d)
    _require_trusted([known[s] for s in sorted(wanted)])
    computed = {}
    for subject, asked in sorted(wanted.items()):
        a = known[subject]
        first = min(d for d in days if d > a.admitted)
        computed[subject] = span_rows(state_dir, setup, a, first, max(asked))
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
