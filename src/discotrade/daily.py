"""The daily run, steps 1, 2 and the rank persistence of step 6 (DESIGN 16.1,
16.2, 5.4, 5.6, 9.2, 9.3, 10.4, 10.5, 11.1, 15.2; decisions 2026-10-12 2, 3, 19,
50 to 53, 55, 59, 62, 69, 70, 71; I-5, I-6, I-12, I-14).

``run_day(state_dir, config_dir, track, clock, day=None)`` processes one
trading day ``D`` of the track in a state directory ``init-state`` made
(anything else is refused, decision 50), holding the run lock throughout and
releasing it on success and on failure:

- ``D`` is ``day``, or by default decision 19's ``D`` at the clock's instant
  (``closed_day``: per instrument, the latest trading day whose last expected
  bar closed by its source's ``available_until``; the earliest across the
  track). A ``D`` that is not a trading day of the track (the union of its
  instruments' trading dates, decision 51), or for which an instrument has an
  expected bar of a trading day on or before ``D`` that has not closed by its
  source's ``available_until`` (the design is silent, refusing is the
  simplest safe reading of "fetch bars up to ``D``"; an instrument that does
  not trade on ``D`` needs only its earlier days closed, so that a track whose
  calendars differ runs each of its trading days at decision 72's clock), is
  refused.
- When the journal holds a day before ``D`` and a trading day of the track
  between the last journaled day and ``D`` has no journal file, the run fails
  naming the first such day and writes nothing (decision 51; the catch-up is
  step S4.2's). A ``D`` before the last journaled day that the journal does
  not hold is refused likewise (it cannot be journaled in order).
- Step 1, written as ``bars fetch`` writes (each append atomic, decisions 4,
  5; not staged in step S1.1, decision 50): an interrupted append is
  completed (a ``store_recovered`` notice), each instrument's bars are asked
  for from its last stored bar to the earlier of its source's
  ``available_until`` and the end of ``D`` by its own calendar
  (``gaps.day_end``), bars with a value that is not finite are dropped
  (decision 6), the gap check for ``D`` runs (decisions 2, 3; ``data_gaps``
  above ``gaps.max_fraction``), and rolls are recorded (DESIGN 5.6; a
  ``roll_gap_estimated`` notice per estimated gap). Every event step 1
  returns is appended to the health log at once (decision 52).
- Step 2: the journal day of ``D`` (``journal.journal_day``: the approaches and
  the controls of decision 64, with a new draw's line of
  ``controls/<track>/pools.jsonl``) into the staging
  directory ``state.STAGING``, and, when the day is new, the paper records
  with the staged day's records and its two portfolio rows (decision 69,
  members from the lifecycle rows dated before ``D``) added (``paper.update``,
  mission 9 U3), or, when the dates the stored paper file holds are not
  exactly those of the journal index before ``D`` (a date missing, a date
  extra, no file), rebuilt from the whole journal (decision 2026-10-14 78),
  so that with that rule it equals a rebuild from the whole journal (when
  the stored rows of the dates it holds are a rebuild's), and with them the
  derived exposure records (``paper.update_exposure``, decision 2026-10-14 84:
  ``R_i(D)`` per instrument and date, row count and summed position per
  subject, instrument and date) under the same rule, both written to the
  staging directory (a re-run writes neither); then the lifecycle's steps 1
  to 4 (DESIGN 10.3; decision 63; ``lifecycle.run_steps``)
  on those paper records (the stored ones on a re-run), their rows appended
  to ``ledger/<track>/lifecycle.jsonl`` in the staging directory (decision
  62). An approach whose evaluation breaks decision 22's contract has its rows
  of ``D`` dropped and is retired by step 1; the day goes on. Then, when the
  day is new and a scripted candidate is given (``candidate``; decision 73:
  only ``replay`` gives one, ``run-day`` takes none), its admission or refusal
  after those steps (``lifecycle.admit``, decision 63): its trial row, and its
  approach and lifecycle rows or its ``trials/<id>/`` files, in the staging
  directory; a re-run admits nothing (the day's rows are already in the
  ledgers, I-6). Then, when the day is new, rank persistence (decision 70): for each block of
  ``stats.due_blocks`` (its last calendar day on or before ``D``, its previous
  block starting on or after the first journaled day, no row yet), in
  ascending order, decision 59's row over the approaches whose state after
  ``D``'s steps is ``live`` or ``dormant`` (each on the track's basket, with
  ``alerts.rank_min_population``) is appended to
  ``stats/<track>/rank_persistence.jsonl`` in the staging directory
  (``stats.append_rank_rows``); a re-run computes none. Then, when the day is
  new, the table (DESIGN 10.4; decision 71; ``table.build`` and ``table.write``):
  ``table/<track>/table.json`` and ``table.md`` written to the staging
  directory; a re-run writes neither. Only when all of
  this has succeeded are the staged files moved into place (``os.replace``,
  in path order) and the state committed as ``run <track> <D>``
  (``state.commit``; no commit when nothing was moved). A re-run whose rows
  equal the journal's writes nothing and makes no commit (I-6): its lifecycle
  rows, computed from the states in force on ``D``, are those already in the
  ledger, which appends no line it holds. One whose rows differ moves nothing,
  appends its ``journal_mismatch`` events and fails (the design is silent on
  the exit status; a failure is the simplest way the owner sees it).
- When step 2's sandbox jobs had to start the process's fork server again
  because the one before had died (O-20 of 2026-10-15;
  ``sandbox.process.restarts``), a ``sandbox_restarted`` notice (subject the
  track, detail the backend and the number of restarts) is appended to the
  health log on a day that is written, and on one that fails (DESIGN 16.2
  exempts the health log there); a re-run of a journaled day whose rows are
  unchanged writes none (decision 112 of 2026-10-15-m14, I-6).
- A failure in either step discards the staging directory and moves nothing.
  A reader that refuses a revised data point appends a ``revised_data`` alert
  (subject the track, the reader's message as detail) and the day fails.

Sources are looked up through ``discotrade.sources.source_for`` at call
time, as ``bars fetch`` and ``bars gaps`` look them up, so that decision 19's
``D`` is computed by one function for the three commands. A day builds one
source per adapter (``sources.sources_for``) and uses it for every step of
the day, so that each instrument's source is built once per run (mission 9
U3).

The whole day runs inside ``bars.store.day_run()`` (decision 2026-10-14 80
(b)): each listed month file is hashed once per index entry in the day, and
the next day (of a ``replay`` too) checks every file it reads again.

No wall clock is read (I-12): the instant is the clock's, and the commit's
dates are its.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

from discotrade import journal, ledger, lifecycle, paper, sources, state, stats, table
from discotrade.bars.gaps import check_gaps, day_end, latest_closed_day
from discotrade.bars.store import BarStore, BarStoreError, day_run, finite_rows
from discotrade.clock import Clock
from discotrade.config import Calendar, TrackConfig, load_track_config
from discotrade.rolls import update_rolls
from discotrade.sandbox import process
from discotrade.sandbox.base import Sandbox, choose_backend
from discotrade.sources.base import BarSource
from discotrade.state import HealthEvent
from discotrade.tradingcal import expected_bars

REVISED_DATA = "revised_data"
#: The notice of a fork server started again after one died (O-20 of 2026-10-15).
SANDBOX_RESTARTED = "sandbox_restarted"
#: The phrase by which the bar store's errors name a revised data point.
_REVISED = "a revised data point"


class DailyError(RuntimeError):
    """A day that cannot be run as asked; the command exits 1."""


@dataclass(frozen=True)
class DayRun:
    day: date
    status: str                          # journal.WRITTEN or journal.UNCHANGED
    rows: int
    commit: str | None
    events: tuple[HealthEvent, ...]      # appended to the health log by this run
    changes: tuple[Mapping[str, object], ...] = ()   # lifecycle rows appended by this run
    admission: lifecycle.Admission | None = None      # the day's candidate, when it had one


def _sources(tc: TrackConfig, calendars: Mapping[str, Calendar]) -> dict[str, BarSource]:
    return sources.sources_for(tc.instruments, calendars, tc.track.bar_seconds)


def closed_day(tc: TrackConfig, calendars: Mapping[str, Calendar], now: datetime,
               used: Mapping[str, BarSource] | None = None) -> date:
    """Decision 19's ``D`` at ``now``: per instrument, the latest trading day
    whose last expected bar closed by its source's ``available_until(now)``;
    for the track, the earliest of these. ``used`` gives each instrument's
    source (built here when None)."""
    bar = tc.track.bar_seconds
    used = _sources(tc, calendars) if used is None else used
    days = []
    for inst in tc.instruments:
        source = used[inst.symbol]
        days.append(latest_closed_day(calendars[inst.calendar], source.available_until(now),
                                      bar))
    return min(days)


def is_trading_day(tc: TrackConfig, calendars: Mapping[str, Calendar], day: date) -> bool:
    """Whether ``day`` is a trading date of one of the track's instruments."""
    bar = tc.track.bar_seconds
    for name in sorted({inst.calendar for inst in tc.instruments}):
        cal = calendars[name]
        if expected_bars(cal, day_end(cal, day - timedelta(days=1)), day_end(cal, day), bar):
            return True
    return False


def _unclosed(tc: TrackConfig, calendars: Mapping[str, Calendar], day: date,
              now: datetime, used: Mapping[str, BarSource]) -> tuple[str, date] | None:
    """The first instrument, with its latest closed trading day, that has an
    expected bar of a trading day on or before ``day`` not closed by its
    source's ``available_until(now)``; None when every one has closed. A day
    on which an instrument does not trade asks nothing more of it than its
    trading days before (decision 2026-10-12 72's clock on a track whose
    instruments' calendars differ)."""
    bar = tc.track.bar_seconds
    for inst in tc.instruments:
        cal = calendars[inst.calendar]
        source = used[inst.symbol]
        last = latest_closed_day(cal, source.available_until(now), bar)
        if day > last and expected_bars(cal, day_end(cal, last), day_end(cal, day), bar):
            return inst.symbol, last
    return None


def _missing_day(tc: TrackConfig, calendars: Mapping[str, Calendar], journaled: set[date],
                 day: date) -> date | None:
    """The first trading day between the last journaled day and ``day`` that
    the journal does not hold, or None."""
    if not journaled:
        return None
    last = max(journaled)
    if day <= last:
        return None
    d = last + timedelta(days=1)
    while d < day:
        if d not in journaled and is_trading_day(tc, calendars, d):
            return d
        d += timedelta(days=1)
    return None


def _fetch(state_dir: Path, tc: TrackConfig, calendars: Mapping[str, Calendar], day: date,
           now: datetime, used: Mapping[str, BarSource]) -> list[HealthEvent]:
    """Complete interrupted appends and fetch each instrument's bars to the end
    of ``day`` from its source in ``used``; return the notices."""
    bar = tc.track.bar_seconds
    store = BarStore(state_dir, tc.track.name, bar)
    notices = [event for inst in tc.instruments for event in store.recover(inst.symbol, day)]
    for inst in tc.instruments:          # a revised data point stops step 1 before a write
        store._verify_stored(inst.symbol)
    batches = []
    for inst in tc.instruments:
        source = used[inst.symbol]
        until = min(source.available_until(now), day_end(calendars[inst.calendar], day))
        last = store._indexed_last_ts(inst.symbol)   # after recover() (decision 31)
        start = (datetime.combine(inst.trusted_from, time(), tzinfo=UTC) if last is None
                 else last.to_pydatetime() + timedelta(seconds=bar))
        bars = source.fetch(inst, start, until) if start < until else None
        if bars is not None:
            bars = bars[bars["ts"] + pd.Timedelta(seconds=bar) <= pd.Timestamp(until)]
            bars = bars[finite_rows(bars)]
        batches.append((inst.symbol, bars, until))
    for symbol, bars, until in batches:
        if bars is not None:
            store.append(symbol, bars, until)
    notices.extend(store.notices)
    return notices


def _step_1(state_dir: Path, tc: TrackConfig, calendars: Mapping[str, Calendar], day: date,
            now: datetime, max_fraction: float,
            used: Mapping[str, BarSource]) -> list[HealthEvent]:
    events = _fetch(state_dir, tc, calendars, day, now, used)
    report = check_gaps(state_dir, tc, calendars, day, max_fraction)
    if report.event is not None:
        events.append(report.event)
    for inst in tc.instruments:
        _, notices = update_rolls(state_dir, tc.track.name, tc.track.bar_seconds, inst,
                                  used[inst.symbol], day)
        events.extend(notices)
    return events


def _move(staging: Path, state_dir: Path) -> list[str]:
    """Move every staged file into place, in path order; return their paths."""
    moved = []
    for path in sorted(p for p in staging.rglob("*") if p.is_file()):
        rel = path.relative_to(staging)
        target = state_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, target)
        moved.append(rel.as_posix())
    return moved


def _rank_persistence(state_dir: Path, setup: journal.Setup, day: date, first: date,
                      records: pd.DataFrame, staging: Path) -> list[Mapping[str, object]]:
    """Decision 70's rows of the new day ``day``, appended in ``staging``."""
    track = setup.track
    done = {int(row["block"]) for row in stats.read_rank_rows(state_dir, track.name,
                                                              into=staging)}
    blocks = stats.due_blocks(track.epoch, track.block_days, first, day, done)
    if not blocks:
        return []
    rows = ledger.read(state_dir, track.name, ledger.LIFECYCLE, into=staging)
    after = lifecycle.states(rows, state.read_approaches(state_dir), day + timedelta(days=1))
    basket = [setup.calendars[inst.calendar] for inst in setup.instruments]
    population = {aid: basket for aid, s in after.items()
                  if s.state in (lifecycle.LIVE, lifecycle.DORMANT)}
    out = [stats.rank_persistence(records, population, epoch=track.epoch,
                                  block_days=track.block_days, bar_seconds=track.bar_seconds,
                                  k=k,
                                  min_population=int(
                                      setup.thresholds["alerts.rank_min_population"]))
           for k in blocks]
    return stats.append_rank_rows(state_dir, track.name, out, into=staging)


def run_day(state_dir: Path, config_dir: Path, track: str, clock: Clock,
            day: date | None = None, candidate: lifecycle.Candidate | None = None,
            sandbox: Sandbox | str | None = None) -> DayRun:
    """Run steps 1 and 2 of ``day`` (or decision 19's ``D``), with the
    admission of ``candidate`` when given, and commit it. Approaches run on
    ``sandbox``: a backend, or the name of one (None: the track's default,
    decision 2026-10-14-m13 105 (b)); a name the track does not allow is
    refused (``SandboxChoiceError``) before anything is read or written."""
    state_dir = Path(state_dir)
    if sandbox is None or isinstance(sandbox, str):
        choose_backend(load_track_config(Path(config_dir), track).instruments, sandbox)
    state.require_state_directory(state_dir)
    with state.lock(state_dir), day_run():
        return _locked(state_dir, Path(config_dir), track, clock, day, candidate, sandbox)


def _locked(state_dir: Path, config_dir: Path, track: str, clock: Clock,
            day: date | None, candidate: lifecycle.Candidate | None,
            sandbox: Sandbox | str | None) -> DayRun:
    setup = journal.Setup.load(config_dir, track)
    tc = load_track_config(config_dir, track)
    calendars = dict(setup.calendars)
    now = clock.now()
    used = _sources(tc, calendars)
    latest = closed_day(tc, calendars, now, used)
    d = latest if day is None else day
    unclosed = _unclosed(tc, calendars, d, now, used)
    if unclosed is not None:
        symbol, last = unclosed
        raise DailyError(f"{d.isoformat()} has not closed at {now.isoformat()}: the latest "
                         f"closed trading day of {symbol} in {track} is {last.isoformat()}")
    if not is_trading_day(tc, calendars, d):
        raise DailyError(f"{d.isoformat()} is not a trading day of {track}")
    journaled = {date.fromisoformat(e["date"]) for e in journal.read_index(state_dir, track)}
    gap = _missing_day(tc, calendars, journaled, d)
    if gap is not None:
        raise DailyError(f"{gap.isoformat()} is a trading day of {track} with no journal file "
                         f"between {max(journaled).isoformat()} and {d.isoformat()}; run it "
                         f"first (the catch-up of missed days is step S4.2's)")
    if journaled and d < max(journaled) and d not in journaled:
        raise DailyError(f"{d.isoformat()} is before the last journaled day "
                         f"{max(journaled).isoformat()} and is not in the journal")

    appended: list[HealthEvent] = []
    staging = state_dir / state.STAGING
    try:
        events = _step_1(state_dir, tc, calendars, d, now,
                         float(setup.thresholds["gaps.max_fraction"]), used)
        appended += state.append_health(state_dir, track, events)
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir()
        before = process.restarts()
        result = None
        try:
            result = journal.journal_day(state_dir, setup, d, into=staging, sandbox=sandbox)
        finally:
            restarted = process.restarts() - before
            # Decision 112 of 2026-10-15-m14 (I-6): a re-run whose rows equal the
            # journal's writes nothing, this notice included.
            if restarted and (result is None or result.status != journal.UNCHANGED):
                appended += state.append_health(state_dir, track, [HealthEvent(
                    d, "notice", SANDBOX_RESTARTED, track,
                    {"backend": "process", "restarts": restarted})])
        if result.status == journal.MISMATCH:
            appended += state.append_health(state_dir, track, result.events)
            raise DailyError(f"{d.isoformat()}: the recomputed rows differ from the journal "
                             f"(journal_mismatch for "
                             f"{', '.join(e.subject for e in result.events)}); the journal "
                             f"is left untouched")
        if result.status == journal.WRITTEN:
            records = paper.update(state_dir, track, len(setup.instruments), d, overlay=staging)
            paper.write(staging, track, records)
            unit, positions = paper.update_exposure(state_dir, setup, d, overlay=staging)
            paper.write_exposure(staging, track, unit, positions)
        else:
            records = paper.read(state_dir, track)
        changes = list(lifecycle.run_steps(state_dir, setup, d, records,
                                           dict(result.failures), into=staging))
        admission = None
        if result.status == journal.WRITTEN and candidate is not None:
            admission = lifecycle.admit(state_dir, setup, candidate, d, into=staging)
            changes += admission.lifecycle
        if result.status == journal.WRITTEN:
            _rank_persistence(state_dir, setup, d, min(journaled | {d}), records, staging)
            table.write(staging, track, table.build(state_dir, setup, d, records,
                                                    into=staging))
        moved = _move(staging, state_dir)
    except BarStoreError as exc:
        if _REVISED in str(exc):
            state.append_health(state_dir, track, [HealthEvent(
                d, "alert", REVISED_DATA, track, {"error": str(exc)})])
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    sha = state.commit(state_dir, track, d, clock) if moved else None
    return DayRun(d, result.status, result.rows, sha, tuple(appended), tuple(changes),
                  admission)


def describe(run: DayRun, track: str) -> Sequence[str]:
    """The lines ``run-day`` prints."""
    lines = [f"notice {e.to_json()}" if e.level == "notice" else f"alert {e.to_json()}"
             for e in run.events]
    lines += [f"lifecycle {ledger.line(row)}" for row in run.changes]
    if run.status == journal.WRITTEN:
        lines.append(f"run-day: {track} {run.day.isoformat()}: journal written, {run.rows} "
                     f"rows; committed {run.commit}")
    else:
        lines.append(f"run-day: {track} {run.day.isoformat()}: already journaled with equal "
                     f"rows; nothing written")
    return lines
