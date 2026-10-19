"""The daily run, steps 1 to 8 (DESIGN 16.1,
16.2, 15.4, 5.4, 5.6, 9.2, 9.3, 10.4, 10.5, 11.1, 15.1 to 15.3, 15.5; decisions
2026-10-12 2, 3, 19, 50 to 53, 55, 59, 62, 69, 70, 71, 2026-10-17-m19 152, 153;
I-5, I-6, I-12, I-14).

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
  5) but into the staging directory (decision 2026-10-19-m22 181 (a)): the
  whole day runs inside ``bars.store.staged``, so the bar store's month files
  and index, ``gaps.jsonl`` and the roll records are written under
  ``state.STAGING``, read from there first by every later step, and moved
  into place with the day's other staged files; a day that fails leaves the
  stored bars, rolls and gaps file as they were. An interrupted append is
  completed (a ``store_recovered`` notice; its index completed in the staging
  directory), each instrument's bars are asked
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
  ``alerts.rank_min_population``), with ``timing`` and ``gross`` added
  (``alerts.rank_rows``, decision 2026-10-17-m19 149; the day's staged unit and
  position records handed to it, so that they are not read again), is appended
  to ``stats/<track>/rank_persistence.jsonl`` in the staging directory
  (``stats.append_rank_rows``); a re-run computes none. Rows written before
  mission 19 are not rewritten and have neither key (I-5). Then, when the day is
  new, the rest of step 6 (decision 2026-10-17-m19 152 (f)): the detectors'
  events (``alerts.detectors``: ``cost_stale`` over ``<config>/models.toml``
  when the configuration has one, and ``few_valid_candidates`` when the day
  reached step 5) appended to the health log at once, then every rule and the
  alert state with the fired alerts' payloads (``alerts.step``) under
  ``alerts/<track>/`` in the staging directory; a re-run writes none of them.
  ``no_finding`` is not called (152 (e)). Then, when the day is
  new, the table (DESIGN 10.4; decision 71; ``table.build`` and ``table.write``):
  ``table/<track>/table.json`` and ``table.md`` written to the staging
  directory; a re-run writes neither. Then, when the day is new, the dashboard
  (step 7; DESIGN 15.5; decision 2026-10-17-m19 153 (a)): ``dashboard.render`` of
  ``D`` over the staged files, written as ``dashboard/<track>/index.html`` to the
  staging directory (``dashboard.write``); a re-run writes none. Then, when the day
  is new, the rest of step 7 (decision 2026-10-19-m22 179): on a day on which step 6
  fired an entry, the digest page ``digests/<track>/<D>.md`` (``digest.render``: the
  harness's tables of every fired payload, the coordinator's ``write_digest`` prose
  over kinds and subjects only, the day's coordinator tokens and budget); on a day
  with none, the coordinator's ``write_runlog_line`` sentence; both calls through
  ``coordinator.write`` (its events appended to the health log at once); then one
  line appended to ``runlog/<track>.jsonl`` (``date``, ``mode``, the sorted fired
  keys ``alerts``, ``digest`` the page's path or null, ``line`` the sentence or null,
  ``coordinator_tokens``), all in the staging directory; a re-run writes none. Only
  when all of this has succeeded are the staged files moved into place
  (``os.replace``, in path order) and the state committed as ``run <track> <D>``
  (``state.commit``; no commit when nothing was moved). Then step 8 (decision 180),
  only after a commit: ``git push`` of ``main`` to ``origin`` when the state
  repository has one (``[state] push_timeout_seconds``; a failure is a
  ``push_failed`` notice), then one issue per fired entry but ``run_failed``
  through the command's sink (title ``<kind> <subject> <D>``, labels as
  ``digest.issue_labels``, body the entry's section of the page and its path; an
  ``IssueError`` is an ``issue_failed`` notice); these notices are appended after
  the commit and stay uncommitted until the next day's; the day still succeeds. A re-run whose rows
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
- A failure in any step discards the staging directory and moves nothing.
  A reader that refuses a revised data point (``bars.store.RevisedDataError``,
  caught by type, decision 181 (c)) appends a ``revised_data`` alert (subject
  the track, the reader's message as detail) and the day fails.

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

``score_on_t(state_dir, config_dir, setup, day, generated, backend)`` (DESIGN
16.1 step 5, 7.1, 8, 10.2, 10.3; owner's O-4, O-11, O-13, O-17; decision
2026-10-16-m17 135) turns the ``workers.generate.Candidate`` of ``day`` into the
``lifecycle.Candidate`` that ``lifecycle.admit`` takes. Its fixed parameters
(alone, no grid) run on T of ``day`` (``Track.windows(day).t``) through
``backend`` in mode ``positions``, the job holding T's bars and their warm-up
context per instrument and nothing later (``backtest.read_window``), and are
scored by the grid's own code (``validation.sequence.dry_run_and_grid`` with
its window T in place of W): T is scored on its own (``h(u0) = 0``),
``metrics_t`` is the DESIGN 8 metrics on T and ``adjusted_t`` the figures of
``replay.ADJUSTED_KEYS``, the average positions taken over T. The grid, its
results, ``metrics_w`` and ``adjusted_w`` are the generation's. A sandbox error
while scoring T is raised (:class:`DailyError`), never a worker's outcome: the
candidate passed validation on W in the same backend (decision 135 (e)).

Steps 3 to 5 (DESIGN 16.1, 13.6, 13.7, 14.1, 14.3, 15.2, 16.2; decisions
2026-10-16-m15 124 to 126, 2026-10-16-m16 131 (b), (c), 2026-10-16-m17 136; I-5,
I-6, I-8, I-13) run when ``run_day`` is given a ``provider`` (a worker provider:
``list_models`` and ``complete``) and the day is new (its journal file written by
this run), after lifecycle steps 1 to 4 and before rank persistence and the
table; without a provider the day is as before. A ``provider`` and a
``candidate`` together are refused (decision 137 (b): a day has one source of
candidates). In this order:

- Skipped, with no call, when step 1's gap check raised ``data_gaps`` for W or T
  of ``D`` (DESIGN 5.4).
- Step 3: ``coordinator.cell_statuses`` and ``coordinator.offered`` for ``D``,
  which read the states in force on ``D`` (rows dated before ``D``, from the state
  directory, never the staged rows of ``D``'s own lifecycle step; 136 (g)). No
  offered cell: nothing more, no list read and no call (the design is silent on
  the list read; not reading it is the simplest). Then the day's pool:
  ``workers.pool.day_pool`` over ``<config>/models.toml``'s models, the
  provider's ``list_models()`` read once (a failure of the provider's error
  class is ``None``: ``model_list_failed`` and no call), less
  ``pool.removed_models`` of the rows of ``calls.jsonl`` dated before ``D``. An
  empty pool (``pool_empty``) makes no call.
- Step 4: ``coordinator.choose`` with ``coordinator`` (default
  ``ScriptedCoordinator``) over the offered cells and ``coordinator.registry_lines``.
  A coordinator with ``begin_day`` (the Claude Code form) is given ``D`` before
  step 1, so that its token sum is that of one run of the day (decision
  2026-10-18-m20 165).
- Step 5: ``workers.generate.generate`` with the provider, the day's pool, ``D``'s
  trading ordinal and the day's backend, its call rows staged (``into``), its
  responses stored at once under the state directory; a candidate is scored on T
  (``score_on_t``) and admitted or refused (``lifecycle.admit``) into the staging
  directory. Then ``pool.day_events`` over the rows of ``D`` and before
  (``model_removed``, ``cell_needs_fallback``; ``workers.claude_fallback`` from
  ``run.toml``, false when it has no ``[workers]``).

Every health event of these steps (the pool's, the coordinator's, the
generation's, ``day_events``') is appended to the health log when it is
returned, so it survives a day that fails later (DESIGN 16.2's exception). A
re-run of a journaled day runs none of them (I-6). A day that failed after a
response was stored is new on its next run; its generation reads the stored
response and makes no ``complete`` call.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from discotrade import (
    alerts,
    dashboard,
    digest,
    journal,
    ledger,
    lifecycle,
    paper,
    sources,
    state,
    stats,
    table,
)
from discotrade import coordinator as coord
from discotrade.bars.gaps import check_gaps, day_end, latest_closed_day
from discotrade.bars.store import (
    BarStore,
    RevisedDataError,
    day_run,
    finite_rows,
    staged,
    write_atomic,
)
from discotrade.clock import Clock
from discotrade.config import (
    Calendar,
    DateRange,
    ModelsConfig,
    TrackConfig,
    load_models,
    load_run,
    load_track_config,
)
from discotrade.rolls import update_rolls
from discotrade.sandbox import process
from discotrade.sandbox.base import Sandbox, choose_backend
from discotrade.sources.base import BarSource
from discotrade.state import HealthEvent
from discotrade.tradingcal import expected_bars
from discotrade.validation import sequence
from discotrade.workers import generate
from discotrade.workers import pool as worker_pool

REVISED_DATA = "revised_data"
#: The notice of a fork server started again after one died (O-20 of 2026-10-15).
SANDBOX_RESTARTED = "sandbox_restarted"
#: The ``mode`` of a run log line: a day ``run-day`` runs, or one ``replay`` runs
#: (decision 2026-10-19-m22 179 (c)).
MODE_LIVE, MODE_REPLAY = "live", "replay"
MODES = (MODE_LIVE, MODE_REPLAY)
#: The run log and the digest pages, relative to the state directory (DESIGN 15.4).
RUNLOG_DIR, DIGESTS_DIR = "runlog", "digests"
#: The keys of a run log line (decision 179 (c)).
RUNLOG_KEYS = ("alerts", "coordinator_tokens", "date", "digest", "line", "mode")
#: Step 8's notices (decision 180) and the kind whose issue its failure opens (182 (c)).
PUSH_FAILED, ISSUE_FAILED, RUN_FAILED = "push_failed", "issue_failed", "run_failed"


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
    statuses: tuple[coord.CellStatus, ...] = ()       # step 3's cell statuses, when it ran
    brief: coord.Brief | None = None                  # step 4's brief, when it ran
    calls: tuple[Mapping[str, object], ...] = ()      # step 5's call rows, when it ran


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
        # After recover(), every month file is listed: the public reader of the
        # index (decision 35) gives the indexed last bar (181 (c): no private call).
        entry = store.index_entry(inst.symbol)
        last = None if entry is None else pd.Timestamp(entry["last_ts"]).tz_convert("UTC")
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
            used: Mapping[str, BarSource]) -> tuple[list[HealthEvent], bool]:
    """Step 1's events, and whether the gap check skips the day's generation."""
    events = _fetch(state_dir, tc, calendars, day, now, used)
    report = check_gaps(state_dir, tc, calendars, day, max_fraction)
    if report.event is not None:
        events.append(report.event)
    for inst in tc.instruments:
        _, notices = update_rolls(state_dir, tc.track.name, tc.track.bar_seconds, inst,
                                  used[inst.symbol], day)
        events.extend(notices)
    return events, report.skip_generation


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
                      records: pd.DataFrame, staging: Path,
                      exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None
                      ) -> list[Mapping[str, object]]:
    """Decision 70's rows of the new day ``day``, appended in ``staging``, each
    with ``timing`` and ``gross`` (``alerts.rank_rows``, decision 2026-10-17-m19
    149 (b)); ``exposure`` is the day's unit and position records, staged."""
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
    out = alerts.rank_rows(state_dir, setup, records, population, blocks, overlay=staging,
                           exposure=exposure)
    return stats.append_rank_rows(state_dir, track.name, out, into=staging)


def _models(config_dir: Path) -> ModelsConfig | None:
    """``<config>/models.toml``, or None when the configuration has none."""
    path = Path(config_dir) / "models.toml"
    return load_models(path) if path.exists() else None


def runlog_path(root: Path, track: str) -> Path:
    """``runlog/<track>.jsonl`` under ``root``."""
    return Path(root) / RUNLOG_DIR / f"{track}.jsonl"


def digest_path(root: Path, track: str, day: date) -> Path:
    """``digests/<track>/<D>.md`` under ``root``."""
    return Path(root) / DIGESTS_DIR / track / f"{day.isoformat()}.md"


def _append_runlog(state_dir: Path, track: str, row: Mapping[str, Any], staging: Path) -> None:
    """Append ``row``'s line to the run log in ``staging``, after the lines the stored
    log holds, as the ledgers' lines are appended."""
    target, source = runlog_path(staging, track), runlog_path(state_dir, track)
    held = target if target.exists() else source
    old = held.read_bytes() if held.exists() else b""
    if old and not old.endswith(b"\n"):
        raise state.StateError(f"{held} does not end with a newline; its last line is torn")
    data = old + (ledger.line(row) + "\n").encode("utf-8")
    write_atomic(target, lambda p: p.write_bytes(data))


def _step_7(state_dir: Path, setup: journal.Setup, d: date, fired: Sequence[Mapping[str, Any]],
            coordinator: coord.Coordinator | None, brief: coord.Brief | None, mode: str,
            staging: Path) -> list[HealthEvent]:
    """Step 7's digest page (a day on which an entry fired) or the coordinator's run log
    sentence (a day with none), then the day's run log line, in ``staging`` (decision
    179); return the health events, appended at once (DESIGN 16.2's exception)."""
    track = setup.track
    line, rel = None, None
    if fired:
        prose, events = coord.write(coordinator, track, d, "write_digest",
                                    digest.alert_payloads(fired))
        page = digest.render(track.name, d, fired, prose, coord.day_tokens(coordinator),
                             int(setup.thresholds[coord.BUDGET_KEY]))
        target = digest_path(staging, track.name, d)
        write_atomic(target, lambda p: p.write_bytes(page.encode("utf-8")))
        rel = target.relative_to(staging).as_posix()
    else:
        summary = coord.RunSummary(track.name, None if brief is None else brief.cell)
        line, events = coord.write(coordinator, track, d, "write_runlog_line", summary)
    appended = state.append_health(state_dir, track.name, events)
    _append_runlog(state_dir, track.name, {
        "date": d.isoformat(), "mode": mode,
        "alerts": sorted(alerts.key_of(e["kind"], e["subject"]) for e in fired),
        "digest": rel, "line": line, "coordinator_tokens": coord.day_tokens(coordinator)},
        staging)
    return appended


def _push(state_dir: Path, config_dir: Path) -> str | None:
    """Push ``main`` of the state repository to its ``origin`` (decision 180 (a)); None
    when it went, else git's error text."""
    from discotrade.config import ConfigError

    try:
        settings = load_run(config_dir).state
    except ConfigError as exc:
        return str(exc)
    if settings is None:
        return f"{Path(config_dir) / 'run.toml'} has no [state] table"
    try:
        done = subprocess.run(["git", "-C", str(state_dir), "push", "-q", digest.ORIGIN,
                               "main"], env=state.git_environment(), capture_output=True,
                              text=True, check=False, stdin=subprocess.DEVNULL,
                              timeout=settings.push_timeout_seconds)
    except subprocess.TimeoutExpired:
        return f"git push: timeout after {settings.push_timeout_seconds:g} s"
    except OSError as exc:
        return f"git push could not start: {type(exc).__name__}"
    if done.returncode != 0:
        return (done.stderr.strip() or f"git push: exit status {done.returncode}")
    return None


def _labels(config_dir: Path) -> tuple[str, ...]:
    """``[issues] labels`` of ``run.toml`` (decision 178 (c)); none without the table."""
    from discotrade.config import ConfigError

    try:
        settings = load_run(config_dir).issues
    except ConfigError:
        return ()
    return () if settings is None else settings.labels


def _step_8(state_dir: Path, config_dir: Path, track: str, d: date,
            fired: Sequence[Mapping[str, Any]], issues: Any) -> list[HealthEvent]:
    """Step 8 after the day's commit (decision 180): the push when the state repository
    has ``origin`` (``push_failed`` when it fails), then one issue per fired entry but
    ``run_failed`` through ``issues`` (``issue_failed`` when the sink raises), its body
    the entry's section of the digest page and the page's path. The notices are
    appended to the health log now and committed with the next day (180 (c))."""
    events: list[HealthEvent] = []
    if digest.has_origin(state_dir):
        error = _push(state_dir, config_dir)
        if error is not None:
            events.append(HealthEvent(d, "notice", PUSH_FAILED, track,
                                      {"day": d.isoformat(), "error": error}))
    entries = [e for e in fired if e["kind"] != RUN_FAILED]
    if issues is not None and entries:
        labels = _labels(config_dir)
        page = f"{DIGESTS_DIR}/{track}/{d.isoformat()}.md"
        for e in entries:
            title = f"{e['kind']} {e['subject']} {d.isoformat()}"
            body = f"{digest.section(e)}\n\nDigest page: {page}\n"
            try:
                issues.open(title, body, digest.issue_labels(labels, e["kind"]))
            except digest.IssueError as exc:
                events.append(HealthEvent(d, "notice", ISSUE_FAILED, track,
                                          {"title": title, "error": str(exc)}))
    return state.append_health(state_dir, track, events)


def run_day(state_dir: Path, config_dir: Path, track: str, clock: Clock,
            day: date | None = None, candidate: lifecycle.Candidate | None = None,
            sandbox: Sandbox | str | None = None, provider: Any = None,
            coordinator: coord.Coordinator | None = None, issues: Any = None,
            mode: str = MODE_REPLAY) -> DayRun:
    """Run steps 1 and 2 of ``day`` (or decision 19's ``D``), with the
    admission of ``candidate`` when given, or steps 3 to 5 with ``provider``
    when given (and ``coordinator``, the scripted one by default), steps 6 and 7,
    and commit it; then step 8's push and one issue per fired entry through
    ``issues`` (an ``IssueSink``; None opens none). ``mode`` is the run log line's
    (``live`` for ``run-day``, ``replay`` for ``replay``, decision 179 (c)).
    Approaches run on ``sandbox``: a backend, or the name of one (None: the
    track's default, decision 2026-10-14-m13 105 (b)); a name the track does
    not allow is refused (``SandboxChoiceError``) before anything is read or
    written."""
    state_dir = Path(state_dir)
    if mode not in MODES:
        raise ValueError(f"mode {mode!r} is not one of {', '.join(MODES)}")
    if candidate is not None and provider is not None:
        raise ValueError("a day has one source of candidates: a scripted candidate or a "
                         "worker provider, not both (decision 2026-10-16-m17 137 (b))")
    if sandbox is None or isinstance(sandbox, str):
        choose_backend(load_track_config(Path(config_dir), track).instruments, sandbox)
    state.require_state_directory(state_dir)
    with state.lock(state_dir), day_run():
        return _locked(state_dir, Path(config_dir), track, clock, day, candidate, sandbox,
                       provider, coordinator, issues, mode)


@dataclass(frozen=True)
class _Generated:
    """What steps 3 to 5 of a day did."""

    events: tuple[HealthEvent, ...] = ()
    statuses: tuple[coord.CellStatus, ...] = ()
    brief: coord.Brief | None = None
    calls: tuple[Mapping[str, object], ...] = ()
    admission: lifecycle.Admission | None = None


def _steps_3_to_5(state_dir: Path, config_dir: Path, setup: journal.Setup, tc: TrackConfig,
                  calendars: Mapping[str, Calendar], d: date, provider: Any,
                  coordinator: coord.Coordinator | None, sandbox: Sandbox | str | None,
                  staging: Path) -> _Generated:
    """Steps 3 to 5 of the new day ``d`` (decision 136), each health event
    appended to the health log as it is returned."""
    from discotrade.workers.providers import ProviderError

    track = setup.track
    th = setup.thresholds
    appended: list[HealthEvent] = []

    def log(events: Sequence[HealthEvent]) -> None:
        appended.extend(state.append_health(state_dir, track.name, events))

    # Step 3: the cells, in force on d (rows dated before d; decision 136 (g)).
    statuses = tuple(coord.cell_statuses(state_dir, track, th, d))
    cells = coord.offered(statuses)
    if not cells:
        return _Generated(tuple(appended), statuses)
    models = load_models(config_dir / "models.toml")
    before = ledger.read(state_dir, track.name, ledger.CALLS)
    removed = worker_pool.removed_models(before, models, d, th)
    try:
        listed: list[str] | None = list(provider.list_models())
    except ProviderError:
        listed = None
    pool = worker_pool.day_pool(models, d, listed, removed)
    log(pool.events)
    if not pool.models:
        return _Generated(tuple(appended), statuses)
    # Step 4: the coordinator's choice (DESIGN 14.3).
    lines = coord.registry_lines(state_dir, track, th, d)
    brief, events = coord.choose(coordinator or coord.ScriptedCoordinator(track), cells,
                                 lines, track, th, d)
    log(events)
    if brief is None:
        return _Generated(tuple(appended), statuses)
    # Step 5: the call, validation, scoring on T, admission.
    ordinal = worker_pool.trading_ordinal(d, track.epoch,
                                          lambda x: is_trading_day(tc, calendars, x))
    admission = None
    with journal.backend(setup, sandbox) as box:
        out = generate.generate(state_dir, setup, d, brief.cell, brief.text,
                                provider=provider, provider_errors=(ProviderError,),
                                pool=pool, ordinal=ordinal, backend=box, into=staging)
        log(out.events)
        if out.candidate is not None:
            scored = score_on_t(state_dir, config_dir, setup, d, out.candidate, box)
            admission = lifecycle.admit(state_dir, setup, scored, d, into=staging)
    run = load_run(config_dir)
    fallback = bool(run.workers.claude_fallback) if run.workers is not None else False
    rows = ledger.read(state_dir, track.name, ledger.CALLS, into=staging)
    log(worker_pool.day_events(rows, models, d, th, fallback))
    return _Generated(tuple(appended), statuses, brief, tuple(out.rows), admission)


def _locked(state_dir: Path, config_dir: Path, track: str, clock: Clock,
            day: date | None, candidate: lifecycle.Candidate | None,
            sandbox: Sandbox | str | None, provider: Any = None,
            coordinator: coord.Coordinator | None = None, issues: Any = None,
            mode: str = MODE_REPLAY) -> DayRun:
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

    begin = getattr(coordinator, "begin_day", None)
    if begin is not None:  # the coordinator's token sum is per run of a day (165)
        begin(d)
    appended: list[HealthEvent] = []
    staging = state_dir / state.STAGING
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        # Step 1 to 7 write to the staging directory and read from it first
        # (decision 2026-10-19-m22 181 (a)); the move puts them in place together.
        with staged(state_dir, staging):
            events, skip = _step_1(state_dir, tc, calendars, d, now,
                                   float(setup.thresholds["gaps.max_fraction"]), used)
            appended += state.append_health(state_dir, track, events)
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
            generated = _Generated()
            fired: list[Mapping[str, Any]] = []
            if result.status == journal.WRITTEN and candidate is not None:
                admission = lifecycle.admit(state_dir, setup, candidate, d, into=staging)
                changes += admission.lifecycle
            if result.status == journal.WRITTEN and provider is not None and not skip:
                generated = _steps_3_to_5(state_dir, config_dir, setup, tc, calendars, d,
                                          provider, coordinator, sandbox, staging)
                appended += generated.events
                admission = generated.admission
                if admission is not None:
                    changes += admission.lifecycle
            if result.status == journal.WRITTEN:
                _rank_persistence(state_dir, setup, d, min(journaled | {d}), records, staging,
                                  (unit, positions))
                appended += state.append_health(state_dir, track, alerts.detectors(
                    state_dir, setup, d, reached_step_5=generated.brief is not None,
                    models=_models(config_dir), overlay=staging))
                _, fired = alerts.step(state_dir, setup, d, records, into=staging,
                                       exposure=(unit, positions))
                table.write(staging, track, table.build(state_dir, setup, d, records,
                                                        into=staging))
                dashboard.write(staging, track, dashboard.render(
                    state_dir, setup, d, overlay=staging, records=records,
                    exposure=(unit, positions)))
                appended += _step_7(state_dir, setup, d, fired, coordinator, generated.brief,
                                    mode, staging)
            moved = _move(staging, state_dir)
    except RevisedDataError as exc:     # the store's refusal, by type (181 (c))
        state.append_health(state_dir, track, [HealthEvent(
            d, "alert", REVISED_DATA, track, {"error": str(exc)})])
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    sha = state.commit(state_dir, track, d, clock) if moved else None
    if sha is not None:  # step 8 (decision 180); a re-run commits, pushes and opens nothing
        appended += _step_8(state_dir, config_dir, track, d, fired, issues)
    return DayRun(d, result.status, result.rows, sha, tuple(appended), tuple(changes),
                  admission, generated.statuses, generated.brief, generated.calls)


@dataclass(frozen=True)
class _OnT(sequence.Context):
    """The grid's context with T of ``day`` as its window (decision 135 (a))."""

    @property
    def window(self) -> DateRange:
        return self.setup.track.windows(self.day).t


def score_on_t(state_dir: Path, config_dir: Path, setup: journal.Setup, day: date,
               generated: generate.Candidate, backend: Sandbox) -> lifecycle.Candidate:
    """The ``lifecycle.Candidate`` of ``generated``, scored on T of ``day`` in
    ``backend`` (decision 135); ``DailyError`` when the sandbox fails on T."""
    ctx = _OnT(Path(state_dir), Path(config_dir), setup, day, backend)
    fixed = sequence.Submission(params=dict(generated.params), source=generated.source)
    out = sequence.dry_run_and_grid(ctx, fixed)
    if not out.ok:
        raise DailyError(f"{day.isoformat()}: the candidate of call {generated.call} failed "
                         f"in the sandbox while scored on T, after it passed on W: "
                         f"{out.text}")
    t = ctx.window
    calendars = [setup.calendars[name]
                 for name in sorted({inst.calendar for inst in setup.instruments})]
    return lifecycle.Candidate(
        source=generated.source, params=dict(generated.params),
        cell=f"{generated.cell[0]}/{generated.cell[1]}", model_id=generated.model_id,
        model_version=generated.model_version, cutoff=generated.cutoff,
        description=generated.description, profile_version=generated.profile_version,
        metrics_t=out.metrics_w, adjusted_t=out.adjusted_w,
        t_days=tuple(stats.trading_dates(calendars, setup.track.bar_seconds, t.first,
                                         t.last)),
        grid=generated.grid, metrics_w=generated.metrics_w, adjusted_w=generated.adjusted_w)


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
