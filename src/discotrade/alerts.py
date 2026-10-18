"""Alert rules and alert state (DESIGN 15.1 to 15.3, 16.1 step 6). Built in
step S4.1: the rank rows of the day loop, the four finding rules, the health
alerts, their detectors, and the alert state with its payloads, which the day
loop's step 6 writes (decision 2026-10-17-m19 152).

The rank rows on the timing statistic (DESIGN 11.1, 15.1; owner decisions
O-4, O-5, O-6, O-24; decisions 2026-10-12 59, 2026-10-17-m19 149 (a)):

- ``rank_rows(state_dir, setup, records, subjects, blocks, *, overlay=None,
  exposure=None, frames=None)``: decision 59's row for each block ``k`` of
  ``blocks``, in their order, over the candidate ``subjects`` (each mapped to
  its own instruments' calendars, as ``stats.rank_persistence`` takes them),
  with the track's ``epoch``, ``block_days`` and ``bar_seconds`` and
  ``alerts.rank_min_population`` from ``setup``. For blocks ``k - 1`` and
  ``k``, each candidate's gross timing return per day is
  ``paper.adjusted(..., "gross")`` over that block's trading dates (the
  candidate's own, ``stats.trading_dates``): one call per candidate per block,
  so each block is its own window with its own average positions (O-5). The
  values go into a paper-shaped frame (the candidate's ``subject``, ``kind``
  and ``date`` rows) under the column ``timing``. ``stats.rank_persistence``
  is then called three times with the same candidates and arguments: on
  ``timing``, giving the key ``timing``; on ``gross``, giving the key
  ``gross``; and on the default ``net_1x``, the call the day loop made before,
  giving the row with every key it had. The row is that third row with
  ``timing`` and ``gross`` added: ``statistic`` keeps its meaning, the net 1x
  figure of decision 59 (O-24). Rows of the three calls whose ``subjects``
  differ are a defect and raise ``ValueError``.
  ``records`` are the paper records (the staged ones in the day loop, with
  ``overlay`` the staging directory, as ``paper.adjusted`` takes them);
  ``exposure`` is the pair (unit records, position records) already read,
  handed to ``paper.adjusted`` (decision 147 (d)) so that the files are not
  read once per candidate and block; None reads them once here, ``overlay``'s
  first, and only when some candidate has a paper row in the two blocks.
  ``frames``, when a list, receives the timing frame of each block, in order
  (for inspection; the rows do not depend on it).

The two finding rules on the exposure-adjusted series (DESIGN 15.1, 11.2 to
11.4; owner decisions O-7, O-16, O-24; decision 2026-10-17-m19 151). Each is a
function of the day ``D`` and the state: ``(state_dir, setup, day, records, *,
overlay=None, exposure=None)``, ``records`` the paper records (staged ones with
``overlay`` the staging directory, as the table reads them), read up to ``D``;
the lifecycle and trials ledgers and the approaches are read from the state
(``overlay``'s first); ``exposure`` is the pair (unit records, position
records) already read, as ``rank_rows`` takes it, else read once here when
needed. Every threshold comes from ``setup.thresholds`` (I-10); the keys each
rule reads are ``THRESHOLD_KEYS``. Each returns entries ``{"kind", "subject",
"active", "value", "threshold", "payload"}``: ``value`` and ``threshold`` the
rule's figure and what it is compared with (``null`` where not a finite number
or not evaluated), ``payload`` every number behind it and ``thresholds``, the
keys read with their values.

- ``persistent_approach``: one entry per approach live or dormant after ``D``'s
  steps (``lifecycle.states`` on ``D + 1``), by id. ``W`` is its paper days with
  ``clean`` true (DESIGN 11.3). Active when ``W`` has at least
  ``alerts.persistent_min_days`` days, the Sharpe (``metrics.sharpe``) of
  ``paper.adjusted(..., "net_2x")`` over ``W`` is above 0, and that of
  ``paper.adjusted(..., "net_1x")`` (the entry's ``value``) is above
  ``stats.threshold(mu_c, sd_c, N, alerts.persistent_base_percentile,
  alerts.false_alerts_per_year)`` (its ``threshold``); ``(mu_c, sd_c)`` is
  ``stats.control_moments`` with ``column`` on ``slot_series`` over ``W``, ``N``
  the trials ledger's row count (decision 60). A figure that is not a number
  makes it false. With ``W`` empty no series is read. The payload: both
  adjusted Sharpes, the plain Sharpes of paper ``net_1x`` and ``net_2x`` over
  ``W`` beside them (O-18), ``mu_c``, ``sd_c``, ``N``, ``p_N``, the threshold,
  ``days`` (of ``W``), ``clean_days`` and ``exposed_days``
  (``stats.clean_counts``), and the approach's description, source text, cell,
  model id and model version.
- ``group_edge``: one entry, subject the track's name (the design names no
  subject; the track is the simplest, as for ``rank_persistence``). ``W`` is the
  last ``alerts.group_days`` dates of ``portfolio_clean`` on or before ``D``;
  with fewer it is not evaluated (inactive, ``value``, ``threshold`` and
  ``payload`` ``null``). The members of a day are ``paper.clean_members``'s.
  The figure (``value``) is the sum over ``W`` of the mean, over the day's
  members in id order, of each member's ``paper.adjusted(..., "net_1x")`` over
  the days of ``W`` on which it is a member (O-7). ``k`` is the mean member
  count over ``W`` rounded half up (``floor(x + 0.5)``), at least 1.
  ``bootstrap`` draws ``alerts.group_bootstrap`` control portfolios with
  ``numpy.random.default_rng(seed_of(D))``: each ``k`` slots by
  ``rng.choice(len(slots), size=k, replace=False)`` over ``slot_series`` over
  ``W`` in slot order, its figure the sum over ``W`` of the slots' mean. With
  fewer than ``k`` slots it is not evaluated. The ``threshold`` is
  ``numpy.quantile(figures, 1 - alerts.group_level)``; active when the figure is
  above it. The payload: ``figure``, ``plain`` (the sum of
  ``portfolio_clean``'s ``net_1x`` over ``W``), ``k``, ``seed``, ``bootstrap``
  (the count), ``threshold``, ``members`` (every member id over ``W``),
  ``first``, ``last`` and ``days`` of ``W``.
- ``slot_series``: each random control slot with a paper row on every day of
  ``W``, in slot order, mapped to its ``paper.adjusted(..., "net_1x")`` over
  ``W``, each with its own average positions over ``W`` (O-7). Mission 20 U2
  (decisions 2026-10-18-m20 157, 158): it computes each series as
  ``paper.adjusted`` does, from the paper, unit and position records split per
  subject once per content (``_SPLITS``, registered with
  ``state.clear_caches``), instead of filtering every subject's history once
  per slot; ``slot_moments`` takes ``control_moments`` on the series directly.
  ``persistent_approach`` hands ``paper.adjusted`` the approach's own position
  rows and ``rank_rows`` filters the exposure records once per window: the
  rows ``paper.adjusted`` reads, so every figure is the one it was.

The other two rules, the health alerts and the state (DESIGN 15.1 to 15.3,
16.1 step 6; decision 2026-10-17-m19 152; I-5, I-6, I-10, I-12). Each rule
returns entries of the same form as the two above; ``THRESHOLD_KEYS`` names,
by kind, every threshold each rule and detector reads, and each reads them
from ``setup.thresholds`` only.

- ``rank_persistence``: one entry, subject the track. The ``timing`` values of
  the last ``alerts.rank_blocks`` rows of ``rank_persistence.jsonl``
  (``overlay``'s first) whose ``timing`` is not null (a row without the key is
  missing, decision 149 (b)); not evaluated with fewer, or with a sample
  deviation ``s`` (ddof 1) of 0 (decision 152 (c)). Else ``t = mean / (s /
  sqrt(n))``, ``p = stats.t_sf(t, n - 1)``, active when ``p <
  alerts.rank_level``. ``value`` is the mean; ``threshold`` is the critical
  mean ``t_crit * s / sqrt(n)``, ``t_crit`` the one-sided ``rank_level`` value
  found by bisection on ``stats.t_sf`` (the design is silent on the threshold
  of a mean tested by ``p``; this is the mean the test compares it with, and
  the dashboard's significance band). The payload: ``mean``, ``sd``, ``n``,
  ``t``, ``p``, ``critical_mean``, ``blocks`` (the block numbers) and
  ``thresholds``.
- ``revival``: one entry per lifecycle row dated ``D`` from ``dormant`` to
  ``live``, subject the approach id; ``value`` its dormant trading days,
  counted as lifecycle step 3 counts them for
  ``lifecycle.revival_min_dormant_days`` (``stats.trading_dates`` of the
  track's calendars, by name, after the date it went dormant up to ``D``);
  active when at least ``alerts.revival_min_days`` (the ``threshold``). The
  payload: ``dormant_days``, ``dormant_since``, ``reason``, the clean and
  exposed counts, ``thresholds`` and the approach's description, source, cell,
  model id and model version.
- ``health``: one entry per (kind, subject) of an alert-level event of the
  health log dated on or before ``D``; active when one is dated ``D``, its
  payload that event's detail; ``value`` and ``threshold`` null.
- The detectors return health events, which the day loop appends to the health
  log before the rules run (decision 152 (e)): ``cost_stale`` (each ``checked``
  date of the instruments' cost records, their spread tables and the pool's
  ``pool = true`` models more than ``alerts.cost_stale_days`` calendar days
  before ``D``; subject the file and key, e.g. ``spreads/SYNA.toml checked``),
  ``few_valid_candidates`` (on a day whose run reached step 5; the first such
  day is the calls ledger's first date, every step 5 writing a call row) and
  ``no_finding`` (given the day live running began and the dates finding alerts
  fired; the day loop does not call it, decision 152 (e)). Each event's detail
  holds the thresholds it read.
- ``transition(previous, D, entries)``: the state of ``D``, ``{"date", "alerts"}``,
  ``alerts`` keyed ``<kind>|<subject>`` with ``active``, ``since`` (the date it
  last turned true, or null), ``value`` and ``threshold``; and the entries that
  fire: active on ``D`` and not active, or absent, in ``previous`` (DESIGN
  15.3).
- ``write(into, state_dir, track, D, state, fired)``: ``alerts/<track>/state.json``
  and, per fired entry, its payload at
  ``alerts/<track>/payloads/<D>/<kind>/<quote(subject, safe="")>.json``, each as
  ``ledger.line`` writes an object with a newline, atomically, under ``into``;
  a payload already held is never rewritten.
- ``step``: decision 152 (f)'s parts 3 and 4 on a new day, into the staging
  directory, against the stored state of the day before.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import numpy as np
import pandas as pd
import pyarrow as pa

from discotrade import controls, journal, ledger, lifecycle, paper, state, stats
from discotrade.bars.store import write_atomic
from discotrade.config import Calendar, ModelsConfig
from discotrade.metrics import positive, sharpe
from discotrade.state import HealthEvent

#: The column of the timing frame (decision 2026-10-17-m19 149 (a)).
TIMING = "timing"


def _exposure(state_dir: Path, track: str, overlay: Path | None
              ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The unit and position records, ``overlay``'s first, read once."""
    pair = []
    for reader in (paper.read_unit, paper.read_positions):
        frame = None if overlay is None else reader(overlay, track)
        if frame is None:
            frame = reader(state_dir, track)
        if frame is None:
            raise ValueError(f"{track} has no derived exposure records under "
                             f"{paper.PAPER_DIR}/{track}/")
        pair.append(frame)
    return pair[0], pair[1]


def rank_rows(state_dir: Path, setup: journal.Setup, records: pd.DataFrame,
              subjects: Mapping[str, Sequence[Calendar]], blocks: Iterable[int], *,
              overlay: Path | None = None,
              exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None,
              frames: list[pd.DataFrame] | None = None) -> list[dict[str, Any]]:
    """Decision 2026-10-17-m19 149 (a)'s row of each block of ``blocks``:
    decision 59's net 1x row with ``timing`` and ``gross`` added (O-5, O-24)."""
    track = setup.track
    min_population = int(setup.thresholds["alerts.rank_min_population"])
    out: list[dict[str, Any]] = []
    for k in blocks:
        windows = [stats.block_dates(track.epoch, track.block_days, j) for j in (k - 1, k)]
        span = records[(records["date"] >= windows[0][0]) & (records["date"] <= windows[1][1])
                       & records["subject"].isin(list(subjects))]
        timing: list[pd.DataFrame] = []
        # The exposure rows of each window's dates, filtered once per window rather
        # than once per candidate: the same rows for every candidate.
        nears: dict[tuple[date, ...], tuple[pd.DataFrame, pd.DataFrame]] = {}
        for subject in sorted(set(span["subject"])):
            mine = span[span["subject"] == subject]
            kind = str(mine["kind"].iloc[0])
            for first, last in windows:
                window = stats.trading_dates(subjects[subject], track.bar_seconds, first, last)
                if not window:
                    continue
                if exposure is None:
                    exposure = _exposure(state_dir, track.name, overlay)
                near = nears.get(tuple(window))
                if near is None:
                    near = (exposure[0][exposure[0]["date"].isin(window)],
                            exposure[1][exposure[1]["date"].isin(window)])
                    nears[tuple(window)] = near
                series = paper.adjusted(state_dir, setup, subject, window, "gross",
                                        records=mine, overlay=overlay, exposure=near)
                timing.append(pd.DataFrame({"subject": subject, "kind": kind,
                                            "date": list(series.index),
                                            TIMING: series.to_numpy(dtype="float64")}))
        frame = (pd.concat(timing, ignore_index=True) if timing
                 else pd.DataFrame(columns=["subject", "kind", "date", TIMING]))
        if frames is not None:
            frames.append(frame)
        kwargs: dict[str, Any] = {"epoch": track.epoch, "block_days": track.block_days,
                                  "bar_seconds": track.bar_seconds, "k": k,
                                  "min_population": min_population}
        on_timing = stats.rank_persistence(frame, subjects, column=TIMING, **kwargs)
        on_gross = stats.rank_persistence(span, subjects, column="gross", **kwargs)
        row = stats.rank_persistence(span, subjects, **kwargs)
        if not on_timing["subjects"] == on_gross["subjects"] == row["subjects"]:
            raise ValueError(f"block {k}: the timing, gross and net_1x rows hold different "
                             f"subjects ({on_timing['subjects']}, {on_gross['subjects']}, "
                             f"{row['subjects']})")
        row[TIMING] = on_timing["statistic"]
        row["gross"] = on_gross["statistic"]
        out.append(row)
    return out


# --- persistent_approach and group_edge (decision 2026-10-17-m19 151) ----------------------

PERSISTENT, GROUP = "persistent_approach", "group_edge"
RANK, REVIVAL = "rank_persistence", "revival"
FEW_VALID, COST_STALE, NO_FINDING = "few_valid_candidates", "cost_stale", "no_finding"
#: Every threshold key each rule and detector here reads, by kind (decision
#: 2026-10-17-m19 152 (b)); ``rank_persistence`` also names the population minimum
#: of the rank rows it reads (``rank_rows``).
THRESHOLD_KEYS: Mapping[str, tuple[str, ...]] = {
    PERSISTENT: ("alerts.persistent_min_days", "alerts.persistent_base_percentile",
                 "alerts.false_alerts_per_year"),
    GROUP: ("alerts.group_days", "alerts.group_level", "alerts.group_bootstrap"),
    RANK: ("alerts.rank_blocks", "alerts.rank_level", "alerts.rank_min_population"),
    REVIVAL: ("alerts.revival_min_days",),
    FEW_VALID: ("alerts.min_valid_candidates", "alerts.valid_candidates_window_days"),
    COST_STALE: ("alerts.cost_stale_days",),
    NO_FINDING: ("alerts.no_finding_months",),
}
#: The column of the slot frame ``stats.control_moments`` reads.
SLOT_COLUMN = "adjusted_net"


def in_force(setup: journal.Setup, kind: str) -> dict[str, Any]:
    """The thresholds ``kind`` reads, each key with its value (I-10)."""
    return {key: setup.thresholds[key] for key in THRESHOLD_KEYS[kind]}


def seed_of(day: date) -> int:
    """The bootstrap's seed: the integer ``YYYYMMDD`` of ``day``."""
    return day.year * 10000 + day.month * 100 + day.day


def _real(x: Any) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _near(exposure: tuple[pd.DataFrame, pd.DataFrame], days: Iterable[date]
          ) -> tuple[pd.DataFrame, pd.DataFrame]:
    wanted = set(days)
    return (exposure[0][exposure[0]["date"].isin(wanted)],
            exposure[1][exposure[1]["date"].isin(wanted)])


def _approaches(state_dir: Path, overlay: Path | None) -> list[state.Approach]:
    held = {a.id: a for a in state.read_approaches(state_dir)}
    if overlay is not None:
        held.update({a.id: a for a in state.read_approaches(overlay)})
    return [held[k] for k in sorted(held)]


#: Step 6's split frames (decision 2026-10-18-m20 157 (a), 158): for one (state
#: directory, track), ``scope``, and per role (``slots``, ``positions``, ``unit``) the
#: content identity of the frame last split for it and what was split from it.
_SPLITS: dict[str, Any] = {"scope": None, "held": {}}


def _clear_splits() -> None:
    _SPLITS["scope"] = None
    _SPLITS["held"] = {}


state.register_cache("discotrade.alerts._SPLITS", _clear_splits)


def cached_splits() -> dict[str, tuple[int, str]]:
    """The roles the split cache holds, each with its content identity."""
    return {role: held[0] for role, held in sorted(_SPLITS["held"].items())}


def _day_numbers(values: Sequence[Any]) -> np.ndarray | None:
    """Each date's number of days since 1970-01-01; None unless every value is
    a ``datetime.date`` itself (a ``datetime`` never equals a date)."""
    values = np.asarray(values, dtype=object)
    if not len(values):
        return np.zeros(0, dtype=np.int64)
    if set(map(type, values)) != {date}:
        return None
    numbers = pa.array(values, type=pa.date32()).cast(pa.int32())
    return numbers.to_numpy(zero_copy_only=False).astype(np.int64)


def _column(frame: pd.DataFrame, name: str, kind: str) -> tuple[np.ndarray, bytes] | None:
    """``frame[name]`` as an array (``text``: objects, ``day``: day numbers,
    ``int`` or ``float``: 64-bit) and the bytes its content identity hashes;
    None when a value is not of the kind."""
    if kind == "day":
        days = _day_numbers(frame[name].to_numpy(dtype=object))
        return None if days is None else (days, days.tobytes())
    if kind == "text":
        values = frame[name].to_numpy(dtype=object)
        if len(values) and set(map(type, values)) != {str}:
            return None
        lengths = np.fromiter(map(len, values), dtype=np.int64, count=len(values))
        return values, "\x00".join(values).encode("utf-8", "surrogatepass") + lengths.tobytes()
    array = frame[name].to_numpy(dtype=np.int64 if kind == "int" else np.float64)
    return array, array.tobytes()


def _held(role: str, scope: tuple[str, str], frame: pd.DataFrame,
          columns: Sequence[tuple[str, str]], split: Any,
          memo: dict[str, tuple[pd.DataFrame, Any]] | None = None) -> Any:
    """``split`` of ``frame``'s ``columns`` (name, kind), through the cache: reused
    while the frame's content identity, its row count and the sha256 of every
    byte of those columns, is the one held for ``role``; computed again on any
    other. None when a column holds a value not of its kind. ``memo``, kept by a
    caller for one call of its own over frames it does not change, gives the
    same frame object's value again without hashing it again."""
    if memo is not None and role in memo and memo[role][0] is frame:
        return memo[role][1]
    if _SPLITS["scope"] != scope:
        _clear_splits()
        _SPLITS["scope"] = scope
    parts = [_column(frame, name, kind) for name, kind in columns]
    value = None
    if all(p is not None for p in parts):
        digest = hashlib.sha256()
        for (name, _), part in zip(columns, parts, strict=True):
            assert part is not None
            for chunk in (name.encode("utf-8"), part[1]):
                digest.update(len(chunk).to_bytes(8, "little"))
                digest.update(chunk)
        identity = (len(frame), digest.hexdigest())
        held = _SPLITS["held"].get(role)
        if held is not None and held[0] == identity:
            value = held[1]
        else:
            value = split(*(p[0] for p in parts if p is not None))
            _SPLITS["held"][role] = (identity, value)
    if memo is not None:
        memo[role] = (frame, value)
    return value


def _groups(*keys: np.ndarray) -> dict[Any, np.ndarray]:
    """The row numbers of each value (each tuple of values) of ``keys``, ascending."""
    if not len(keys[0]):
        return {}
    frame = pd.DataFrame({str(i): k for i, k in enumerate(keys)})
    by = list(frame.columns) if len(keys) > 1 else frame.columns[0]
    return {key: np.sort(where) for key, where in frame.groupby(by, sort=False).indices.items()}


def _split_slots(subjects: np.ndarray, kinds: np.ndarray, days: np.ndarray,
                 values: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]] | None:
    """Each random control slot's rows: its day numbers ascending and the values in
    that order (a stable sort, as ``paper.adjusted`` sorts); None when a slot holds
    two rows of one date."""
    rows = np.flatnonzero(kinds == stats.CONTROL_RANDOM)
    out = {}
    for slot, where in _groups(subjects[rows]).items():
        mine = rows[where]
        order = mine[np.argsort(days[mine], kind="stable")]
        when = days[order]
        if bool(np.any(when[1:] == when[:-1])):
            return None
        out[str(slot)] = (when, values[order])
    return out


def _split_legs(subjects: np.ndarray, symbols: np.ndarray, days: np.ndarray,
                rows: np.ndarray, held: np.ndarray
                ) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Per (subject, instrument), the day numbers, ``rows`` and ``position`` of its
    position records, in frame order."""
    return {(str(s), str(i)): (days[where], rows[where], held[where])
            for (s, i), where in _groups(subjects, symbols).items()}


def _split_unit(symbols: np.ndarray, days: np.ndarray, values: np.ndarray
                ) -> tuple[dict[str, dict[int, float]], set[int]]:
    """Per instrument, its unit return by day number (a later row of the same
    instrument and date replaces an earlier one, as a dict built in frame order
    does), and every day number the records hold."""
    out: dict[str, dict[int, float]] = {}
    for symbol, day, value in zip(symbols, days.tolist(), values.tolist(), strict=True):
        out.setdefault(str(symbol), {})[day] = float(value)
    return out, set(days.tolist())


_NO_LEG = (np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64),
           np.zeros(0, dtype=np.float64))


def _within(values: np.ndarray, sorted_unique: np.ndarray) -> np.ndarray:
    """``numpy.isin(values, sorted_unique)`` for a sorted array of distinct values."""
    if not len(sorted_unique):
        return np.zeros(len(values), dtype=bool)
    at = np.minimum(np.searchsorted(sorted_unique, values), len(sorted_unique) - 1)
    return sorted_unique[at] == values


def _less_exposure_rows(values: np.ndarray, average: np.ndarray, unit: np.ndarray,
                        n: int) -> np.ndarray:
    """``paper.less_exposure`` of every row of ``values`` at once: row ``r``, day
    ``t`` is ``values[r, t]`` less the sum over the symbols, in their order,
    starting from 0.0, of ``average[r, s] * unit[s, t]`` (``unit`` 0.0 where the
    records hold none), divided by ``n``. Each element goes through the same
    IEEE operations in the same order as the scalar loop, so each is the same."""
    total = np.zeros(values.shape, dtype=np.float64)
    for s in range(unit.shape[0]):
        total = total + average[:, s:s + 1] * unit[s:s + 1, :]
    return values - total / n


def slot_series(state_dir: Path, setup: journal.Setup, days: Iterable[date],
                records: pd.DataFrame, *, overlay: Path | None = None,
                exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None,
                memo: dict[str, tuple[pd.DataFrame, Any]] | None = None
                ) -> dict[str, pd.Series]:
    """Each random control slot with a paper row on every day of ``days``, in slot
    order: its exposure-adjusted net 1x over ``days``, with its own average
    positions over them (O-7).

    Each slot's series is computed as ``paper.adjusted`` computes it, from the
    paper, unit and position records split once per content (``_held``,
    ``_SPLITS``) instead of every slot filtering every subject's history again
    (decision 2026-10-18-m20 157, 158): its values on the days of ``days`` in
    date order; for each instrument, in symbol order, its ``hbar_i`` the summed
    ``position`` of its position rows dated in ``days``, in frame order, over
    their summed ``rows`` (0 with none), as ``paper.hbar``; the unit return of
    each instrument and day the unit records hold; and O-4's one subtraction,
    ``paper.less_exposure``'s, taken for every slot and day at once element by
    element (``_less_exposure_rows``). The same numbers go through the same
    operations in the same order, so each series is the same. Where a frame holds a value of
    another type than its records hold (a ``date`` column with a value that is
    not a ``datetime.date``, a text column with one that is not a ``str``), or a
    slot holds two rows of one date, each series is ``paper.adjusted``'s own.
    ``memo`` is ``_held``'s, for a caller that calls this more than once over
    the same frames."""
    span = sorted(set(days))
    wanted = set(span)
    if not span:
        return {}
    track = setup.track.name
    scope = (str(Path(state_dir).resolve()), track)
    when = _day_numbers(span)
    split = (None if when is None else
             _held("slots", scope, records, (("subject", "text"), ("kind", "text"),
                                             ("date", "day"), ("net_1x", "float")),
                   _split_slots, memo))
    if split is not None and when is not None:
        inside_w = {slot: np.isin(have, when) for slot, (have, _) in split.items()}
        chosen = [(slot, split[slot][1][inside_w[slot]])
                  for slot in sorted((s for s, inside in inside_w.items() if inside.any()),
                                     key=controls.slot_of)
                  if int(inside_w[slot].sum()) == len(span)]
        if not chosen:
            return {}
        if exposure is None:
            exposure = _exposure(state_dir, track, overlay)
        units = _held("unit", scope, exposure[0], (("instrument", "text"), ("date", "day"),
                                                   ("unit", "float")), _split_unit, memo)
        legs = _held("positions", scope, exposure[1],
                     (("subject", "text"), ("instrument", "text"), ("date", "day"),
                      ("rows", "int"), ("position", "float")), _split_legs, memo)
        if units is not None and legs is not None:
            numbers = when.tolist()
            missing = [d for d, n in zip(span, numbers, strict=True) if n not in units[1]]
            if missing:
                raise ValueError(f"the exposure records of {track} hold no "
                                 f"{missing[0].isoformat()}; a caller passing staged paper "
                                 f"records passes overlay too")
            symbols = sorted(inst.symbol for inst in setup.instruments)
            width = len(setup.instruments)
            unit = np.array([[units[0].get(s, {}).get(n, 0.0) for n in numbers]
                             for s in symbols], dtype=np.float64).reshape(len(symbols), -1)
            average = np.zeros((len(chosen), len(symbols)), dtype=np.float64)
            for i, (slot, _) in enumerate(chosen):
                for j, s in enumerate(symbols):
                    days_of, rows, held = legs.get((slot, s), _NO_LEG)
                    inside = _within(days_of, when)
                    count, summed = int(rows[inside].sum()), float(held[inside].sum())
                    average[i, j] = summed / count if count else 0.0
            values = np.vstack([v for _, v in chosen]).astype(np.float64)
            adjusted = _less_exposure_rows(values, average, unit, width)
            out: dict[str, pd.Series] = {}
            index: Any = list(span)
            for i, (slot, _) in enumerate(chosen):
                out[slot] = pd.Series(adjusted[i].copy(), index=index, dtype="float64",
                                      name="net_1x")
                # the first series' index, an immutable Index of the same dates, for the rest
                index = out[slot].index
            return out
    slots = records[(records["kind"] == stats.CONTROL_RANDOM) & records["date"].isin(wanted)]
    near = None if exposure is None else _near(exposure, wanted)
    out = {}
    groups = {str(s): g for s, g in slots.groupby("subject", sort=False)}
    for slot in sorted(groups, key=controls.slot_of):
        mine = groups[slot]
        if set(mine["date"]) != wanted:
            continue
        out[slot] = paper.adjusted(state_dir, setup, slot, span, "net_1x", records=mine,
                                   overlay=overlay, exposure=near)
    return out


def _slot_frame(series: Mapping[str, pd.Series]) -> pd.DataFrame:
    frames = [pd.DataFrame({"subject": slot, "kind": stats.CONTROL_RANDOM,
                            "date": list(s.index), SLOT_COLUMN: s.to_numpy(dtype=np.float64)})
              for slot, s in series.items()]
    return (pd.concat(frames, ignore_index=True) if frames
            else pd.DataFrame(columns=["subject", "kind", "date", SLOT_COLUMN]))


def slot_moments(slots: Mapping[str, pd.Series], days: Iterable[date]) -> tuple[float, float]:
    """``stats.control_moments`` of ``slots`` (``slot_series``) over ``days`` on
    ``SLOT_COLUMN``. When every series is indexed by the days of ``days`` once
    each, in date order, as ``slot_series`` gives them, each slot's Sharpe is taken
    on its series' values directly, the slots in subject order, which are the
    values and the order ``control_moments`` takes from the slot frame; otherwise
    through the slot frame itself (decision 2026-10-18-m20 158)."""
    days = list(days)
    span = sorted(set(days))
    if all(list(s.index) == span for s in slots.values()):
        # metrics.sharpe reads its argument through numpy.asarray as float64
        sharpes = [sharpe(slots[k].to_numpy(dtype=np.float64))
                   for k in sorted(slots)]
        return stats.moments([x for x in sharpes if not math.isnan(x)])
    return stats.control_moments(_slot_frame(slots), days, column=SLOT_COLUMN)


def persistent_approach(state_dir: Path, setup: journal.Setup, day: date,
                        records: pd.DataFrame, *, overlay: Path | None = None,
                        exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None
                        ) -> list[dict[str, Any]]:
    """DESIGN 15.1's ``persistent_approach`` on ``day`` for each approach live or
    dormant after its steps, on the exposure-adjusted series (O-7; decision
    2026-10-17-m19 151 (a))."""
    track = setup.track.name
    force = in_force(setup, PERSISTENT)
    min_days = int(force["alerts.persistent_min_days"])
    base = float(force["alerts.persistent_base_percentile"])
    per_year = float(force["alerts.false_alerts_per_year"])
    records = records[records["date"] <= day]
    life = ledger.read(state_dir, track, ledger.LIFECYCLE, into=overlay)
    n = len(ledger.read(state_dir, track, ledger.TRIALS, into=overlay))
    p_n = stats.tightened_percentile(n, base, per_year)
    approaches = _approaches(state_dir, overlay)
    by_id = {a.id: a for a in approaches}
    after = lifecycle.states(life, approaches, day + timedelta(days=1))
    out: list[dict[str, Any]] = []
    memo: dict[str, tuple[pd.DataFrame, Any]] = {}
    for aid in sorted(a for a, s in after.items()
                      if s.state in (lifecycle.LIVE, lifecycle.DORMANT)):
        mine = records[records["subject"] == aid].sort_values("date", kind="stable")
        clean_rows = mine[mine["clean"].astype(bool)]
        w = list(clean_rows["date"])
        s1 = s2 = plain_1x = plain_2x = mu_c = sd_c = math.nan
        if w:
            if exposure is None:
                exposure = _exposure(state_dir, track, overlay)
            # The approach's own position rows: the rows paper.adjusted reads of it.
            own = (exposure[0][exposure[0]["date"].isin(set(w))],
                   exposure[1][exposure[1]["subject"] == aid])
            s1, s2 = (sharpe(paper.adjusted(state_dir, setup, aid, w, c, records=mine,
                                            overlay=overlay, exposure=own))
                      for c in ("net_1x", "net_2x"))
            plain_1x, plain_2x = sharpe(clean_rows["net_1x"]), sharpe(clean_rows["net_2x"])
            slots = slot_series(state_dir, setup, w, records, overlay=overlay,
                                exposure=exposure, memo=memo)
            mu_c, sd_c = slot_moments(slots, w)
        threshold = stats.threshold(mu_c, sd_c, n, base, per_year)
        active = (len(w) >= min_days and positive(s2) and math.isfinite(s1)
                  and math.isfinite(threshold) and s1 > threshold)
        clean, exposed = stats.clean_counts(records, aid)
        a = by_id[aid]
        payload = {"adjusted_sharpe": _real(s1), "adjusted_sharpe_2x": _real(s2),
                   "sharpe": _real(plain_1x), "sharpe_2x": _real(plain_2x),
                   "mu_c": _real(mu_c), "sd_c": _real(sd_c), "N": n, "p_N": p_n,
                   "threshold": _real(threshold), "days": len(w), "clean_days": clean,
                   "exposed_days": exposed, "thresholds": force,
                   "description": a.meta["description"], "source": a.source,
                   "cell": a.meta["cell"], "model_id": a.meta["model_id"],
                   "model_version": a.meta["model_version"]}
        out.append({"kind": PERSISTENT, "subject": aid, "active": bool(active),
                    "value": _real(s1), "threshold": _real(threshold), "payload": payload})
    return out


def bootstrap(state_dir: Path, setup: journal.Setup, day: date, days: Sequence[date],
              records: pd.DataFrame, k: int, count: int, *, overlay: Path | None = None,
              exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None
              ) -> np.ndarray | None:
    """``count`` control portfolios' figures over ``days``: each ``k`` slots of
    ``slot_series`` drawn without replacement, in slot order, by
    ``numpy.random.default_rng(seed_of(day))``; a portfolio's figure the sum over
    ``days`` of its slots' mean. None with fewer than ``k`` slots."""
    slots = slot_series(state_dir, setup, days, records, overlay=overlay, exposure=exposure)
    if len(slots) < k:
        return None
    matrix = np.vstack([s.to_numpy(dtype=np.float64) for s in slots.values()])
    rng = np.random.default_rng(seed_of(day))
    figures = np.empty(count, dtype=np.float64)
    for b in range(count):
        pick = rng.choice(len(slots), size=k, replace=False)
        figures[b] = float(matrix[pick].mean(axis=0).sum())
    return figures


def group_edge(state_dir: Path, setup: journal.Setup, day: date, records: pd.DataFrame, *,
               overlay: Path | None = None,
               exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None) -> dict[str, Any]:
    """DESIGN 15.1's ``group_edge`` on ``day`` on the members' and the slots'
    exposure-adjusted series (O-7; decision 2026-10-17-m19 151 (b))."""
    track = setup.track.name
    force = in_force(setup, GROUP)
    group_days = int(force["alerts.group_days"])
    level = float(force["alerts.group_level"])
    count = int(force["alerts.group_bootstrap"])
    entry: dict[str, Any] = {"kind": GROUP, "subject": track, "active": False, "value": None,
                             "threshold": None, "payload": None}
    records = records[records["date"] <= day]
    portfolio = records[records["subject"] == paper.PORTFOLIO_CLEAN]
    dates = sorted(set(portfolio["date"]))
    if len(dates) < group_days:
        return entry
    w = dates[-group_days:]
    life = ledger.read(state_dir, track, ledger.LIFECYCLE, into=overlay)
    members = paper.clean_members(records, w, life, _approaches(state_dir, overlay))
    if set(members) != set(w):
        raise ValueError(f"{track}: portfolio_clean has a row on a day with no clean member, "
                         f"or none on a day with one, in {w[0]}..{w[-1]}")
    if exposure is None:
        exposure = _exposure(state_dir, track, overlay)
    near = _near(exposure, w)
    ids = sorted({m for held in members.values() for m in held})
    series = {}
    for m in ids:
        mine = [d for d in w if m in members[d]]
        series[m] = paper.adjusted(state_dir, setup, m, mine, "net_1x",
                                   records=records[records["subject"] == m], overlay=overlay,
                                   exposure=near)
    figure = math.fsum(math.fsum(float(series[m][d]) for m in members[d]) / len(members[d])
                       for d in w)
    k = max(1, math.floor(sum(len(members[d]) for d in w) / len(w) + 0.5))
    figures = bootstrap(state_dir, setup, day, w, records, k, count, overlay=overlay,
                        exposure=near)
    if figures is None:
        return entry
    threshold = float(np.quantile(figures, 1 - level))
    in_w = portfolio[portfolio["date"].isin(set(w))]
    payload = {"figure": _real(figure),
               "plain": _real(math.fsum(float(x) for x in in_w["net_1x"])),
               "k": k, "seed": seed_of(day), "bootstrap": count, "threshold": _real(threshold),
               "members": ids, "first": w[0].isoformat(), "last": w[-1].isoformat(),
               "days": len(w), "thresholds": force}
    entry.update(active=bool(math.isfinite(figure) and math.isfinite(threshold)
                             and figure > threshold),
                 value=_real(figure), threshold=_real(threshold), payload=payload)
    return entry


# --- the alert state, the firing, the payloads, the other rules, health (decision 152) ----

#: The finding rules, in the order the day loop evaluates them (DESIGN 15.1).
FINDING_KINDS = (PERSISTENT, GROUP, RANK, REVIVAL)
ALERTS_DIR, STATE_FILE, PAYLOADS = "alerts", "state.json", "payloads"
#: The keys of an entry of the state (decision 152 (a)).
ENTRY_KEYS = ("active", "since", "value", "threshold")


def _entry(kind: str, subject: str) -> dict[str, Any]:
    return {"kind": kind, "subject": subject, "active": False, "value": None,
            "threshold": None, "payload": None}


def _described(a: state.Approach) -> dict[str, Any]:
    return {"description": a.meta["description"], "source": a.source, "cell": a.meta["cell"],
            "model_id": a.meta["model_id"], "model_version": a.meta["model_version"]}


def _t_critical(level: float, df: int) -> float:
    """The ``t`` whose one-sided upper tail ``stats.t_sf(t, df)`` is ``level``, by
    bisection (``t_sf`` falls as ``t`` rises)."""
    lo, hi = -1.0, 1.0
    while stats.t_sf(lo, df) < level:
        lo *= 2.0
    while stats.t_sf(hi, df) > level:
        hi *= 2.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if mid in (lo, hi):
            break
        lo, hi = (mid, hi) if stats.t_sf(mid, df) > level else (lo, mid)
    return (lo + hi) / 2.0


def rank_persistence(state_dir: Path, setup: journal.Setup, day: date, *,
                     overlay: Path | None = None) -> dict[str, Any]:
    """DESIGN 15.1's ``rank_persistence`` on ``day`` (decision 152 (c)): the
    ``timing`` of the last ``alerts.rank_blocks`` rows whose ``timing`` is not
    null, by a one-sided one-sample t-test at ``alerts.rank_level``."""
    track = setup.track.name
    force = in_force(setup, RANK)
    blocks = int(force["alerts.rank_blocks"])
    level = float(force["alerts.rank_level"])
    entry = _entry(RANK, track)
    rows = [r for r in stats.read_rank_rows(state_dir, track, into=overlay)
            if r.get(TIMING) is not None]
    if blocks < 2 or len(rows) < blocks:
        return entry
    last = rows[-blocks:]
    values = [float(r[TIMING]) for r in last]
    n = len(values)
    mean = math.fsum(values) / n
    sd = float(np.std(np.asarray(values, dtype=np.float64), ddof=1))
    if not (math.isfinite(mean) and math.isfinite(sd) and sd > 0):
        return entry
    se = sd / math.sqrt(n)
    t = mean / se
    p = stats.t_sf(t, n - 1)
    critical = _t_critical(level, n - 1) * se
    entry.update(active=bool(p < level), value=_real(mean), threshold=_real(critical),
                 payload={"mean": _real(mean), "sd": _real(sd), "n": n, "t": _real(t),
                          "p": _real(p), "critical_mean": _real(critical),
                          "blocks": [int(r["block"]) for r in last], "thresholds": force})
    return entry


def revival(state_dir: Path, setup: journal.Setup, day: date, records: pd.DataFrame, *,
            overlay: Path | None = None) -> list[dict[str, Any]]:
    """DESIGN 15.1's ``revival`` on ``day`` (decision 152 (d)): one entry per
    lifecycle row dated ``day`` from ``dormant`` to ``live``, its dormant trading
    days counted as lifecycle step 3 counts them (``stats.trading_dates`` of the
    track's calendars after the date it went dormant, up to ``day``)."""
    track = setup.track.name
    force = in_force(setup, REVIVAL)
    least = int(force["alerts.revival_min_days"])
    life = ledger.read(state_dir, track, ledger.LIFECYCLE, into=overlay)
    approaches = _approaches(state_dir, overlay)
    by_id = {a.id: a for a in approaches}
    before = lifecycle.states(life, approaches, day)
    calendars = [setup.calendars[name] for name in sorted(setup.calendars)]
    records = records[records["date"] <= day]
    out = []
    for row in life:
        if (row["date"] != day.isoformat() or row["from"] != lifecycle.DORMANT
                or row["to"] != lifecycle.LIVE):
            continue
        aid = str(row["id"])
        since = before[aid].since
        count = len(stats.trading_dates(calendars, setup.track.bar_seconds,
                                        since + timedelta(days=1), day))
        clean, exposed = stats.clean_counts(records, aid)
        payload = {"dormant_days": count, "dormant_since": since.isoformat(),
                   "reason": row["reason"], "clean_days": clean, "exposed_days": exposed,
                   "thresholds": force, **_described(by_id[aid])}
        out.append({"kind": REVIVAL, "subject": aid, "active": count >= least, "value": count,
                    "threshold": least, "payload": payload})
    return sorted(out, key=lambda e: e["subject"])


def health(state_dir: Path, track: str, day: date) -> list[dict[str, Any]]:
    """One entry per (kind, subject) of an alert-level event of the health log
    dated on or before ``day``, active when one is dated ``day``, its payload
    that event's detail (the last such, in log order); decision 152 (e)."""
    path = state.health_path(state_dir, track)
    raised: dict[tuple[str, str], Any] = {}
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for text in lines:
        event = json.loads(text)
        when = date.fromisoformat(event["date"])
        if event["level"] != "alert" or when > day:
            continue
        key = (str(event["kind"]), str(event["subject"]))
        if when == day:
            raised[key] = (True, event["detail"])
        else:
            raised.setdefault(key, (False, None))
    return [{"kind": kind, "subject": subject, "active": active, "value": None,
             "threshold": None, "payload": detail}
            for (kind, subject), (active, detail) in sorted(raised.items())]


def few_valid_candidates(state_dir: Path, setup: journal.Setup, day: date, *,
                         overlay: Path | None = None) -> list[HealthEvent]:
    """Decision 152 (e)'s detector, for a day whose run reached step 5 with a
    provider: the first such day is the first date of the calls ledger (every
    step 5 writes a call row); once ``alerts.valid_candidates_window_days``
    calendar days have passed since it, an alert when the trials ledger holds
    fewer than ``alerts.min_valid_candidates`` rows dated in the window of that
    many calendar days ending ``day``."""
    track = setup.track.name
    force = in_force(setup, FEW_VALID)
    least = int(force["alerts.min_valid_candidates"])
    window = int(force["alerts.valid_candidates_window_days"])
    calls = ledger.read(state_dir, track, ledger.CALLS, into=overlay)
    if not calls:
        return []
    first = min(date.fromisoformat(r["date"]) for r in calls)
    if (day - first).days < window:
        return []
    start = day - timedelta(days=window - 1)
    trials = ledger.read(state_dir, track, ledger.TRIALS, into=overlay)
    count = sum(1 for r in trials if start <= date.fromisoformat(r["date"]) <= day)
    if count >= least:
        return []
    return [HealthEvent(day, "alert", FEW_VALID, track, {
        "trials": count, "first": start.isoformat(), "last": day.isoformat(),
        "since": first.isoformat(), "thresholds": force})]


def cost_stale(setup: journal.Setup, day: date, models: ModelsConfig | None = None
               ) -> list[HealthEvent]:
    """Decision 152 (e)'s detector: an alert for each ``checked`` date of the
    track's instruments' cost records (fees and spreads in ticks), of their
    measured spread tables and of the pool's models (``pool = true``) that lies
    more than ``alerts.cost_stale_days`` calendar days before ``day``; subject the
    file and key."""
    force = in_force(setup, COST_STALE)
    limit = int(force["alerts.cost_stale_days"])
    checked: list[tuple[str, date]] = []
    for inst in sorted(setup.instruments, key=lambda i: i.symbol):
        if inst.cost.provenance is not None:
            checked.append((f"instruments/{inst.symbol}.toml cost.checked",
                            inst.cost.provenance.checked))
        table = setup.spread_tables.get(inst.symbol)
        if table is not None:
            checked.append((f"spreads/{inst.symbol}.toml checked", table.provenance.checked))
    if models is not None:
        checked += [(f"models.toml model.{m.id}.checked", m.provenance.checked)
                    for m in models.models if m.pool]
    return [HealthEvent(day, "alert", COST_STALE, subject,
                        {"checked": when.isoformat(), "days": (day - when).days,
                         "thresholds": force})
            for subject, when in checked if (day - when).days > limit]


def months_before(day: date, months: int) -> date:
    """``day`` moved back ``months`` calendar months, its day of month clamped."""
    index = day.year * 12 + day.month - 1 - months
    year, month = divmod(index, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


def no_finding(setup: journal.Setup, day: date, since: date, fired: Iterable[date]
               ) -> list[HealthEvent]:
    """DESIGN 15.2's ``no_finding``: an alert (subject the track) when live
    running began on or before the day ``alerts.no_finding_months`` months before
    ``day`` and no finding alert fired (``fired``, their dates) after that day,
    up to ``day``. Built, not called by the day loop (decision 152 (e))."""
    force = in_force(setup, NO_FINDING)
    start = months_before(day, int(force["alerts.no_finding_months"]))
    if since > start:
        return []
    held = sorted(d for d in fired if d <= day)
    if held and held[-1] > start:
        return []
    return [HealthEvent(day, "alert", NO_FINDING, setup.track.name, {
        "since": since.isoformat(), "first": start.isoformat(),
        "last_finding": held[-1].isoformat() if held else None, "thresholds": force})]


def detectors(state_dir: Path, setup: journal.Setup, day: date, *, reached_step_5: bool,
              models: ModelsConfig | None = None, overlay: Path | None = None
              ) -> list[HealthEvent]:
    """The events of decision 152 (e)'s detectors on ``day``: ``cost_stale``, and
    ``few_valid_candidates`` when the day's run reached step 5 with a provider."""
    events = cost_stale(setup, day, models)
    if reached_step_5:
        events += few_valid_candidates(state_dir, setup, day, overlay=overlay)
    return events


def rules(state_dir: Path, setup: journal.Setup, day: date, records: pd.DataFrame, *,
          overlay: Path | None = None,
          exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None) -> list[dict[str, Any]]:
    """Every entry of ``day``: the finding rules', then the health kinds'."""
    return [*persistent_approach(state_dir, setup, day, records, overlay=overlay,
                                 exposure=exposure),
            group_edge(state_dir, setup, day, records, overlay=overlay, exposure=exposure),
            rank_persistence(state_dir, setup, day, overlay=overlay),
            *revival(state_dir, setup, day, records, overlay=overlay),
            *health(state_dir, setup.track.name, day)]


def key_of(kind: str, subject: str) -> str:
    return f"{kind}|{subject}"


def state_path(root: Path, track: str) -> Path:
    """``alerts/<track>/state.json`` under ``root``."""
    return Path(root) / ALERTS_DIR / track / STATE_FILE


def payload_path(root: Path, track: str, day: date, kind: str, subject: str) -> Path:
    """``alerts/<track>/payloads/<D>/<kind>/<quoted subject>.json`` under ``root``."""
    return (Path(root) / ALERTS_DIR / track / PAYLOADS / day.isoformat() / kind
            / f"{quote(subject, safe='')}.json")


def read_state(root: Path, track: str) -> dict[str, Any] | None:
    path = state_path(root, track)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def transition(previous: Mapping[str, Any] | None, day: date,
               entries: Iterable[Mapping[str, Any]]
               ) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    """The state of ``day`` and the entries that fire on it (DESIGN 15.3;
    decision 152 (a), (b)): an entry fires when it is active and was not
    active, or did not exist, in ``previous``; ``since`` is the date it last
    turned true, or null."""
    held = {} if previous is None else previous["alerts"]
    out: dict[str, dict[str, Any]] = {}
    fired = []
    for e in entries:
        key = key_of(e["kind"], e["subject"])
        if key in out:
            raise ValueError(f"two entries for {key} on {day.isoformat()}")
        before = held.get(key)
        was = before is not None and bool(before["active"])
        if e["active"] and not was:
            since: str | None = day.isoformat()
            fired.append(e)
        else:
            since = None if before is None else before["since"]
        out[key] = {"active": bool(e["active"]), "since": since, "value": e["value"],
                    "threshold": e["threshold"]}
    return {"date": day.isoformat(), "alerts": dict(sorted(out.items()))}, fired


def write(into: Path, state_dir: Path, track: str, day: date, new: Mapping[str, Any],
          fired: Iterable[Mapping[str, Any]]) -> list[str]:
    """Write the state and each fired entry's payload under ``into`` (the staging
    directory), each as ``ledger.line`` writes an object with a newline,
    atomically; return their paths relative to ``into``. A payload already in
    ``state_dir`` or ``into`` is never rewritten: the same bytes are left, other
    bytes are refused (``StateError``)."""
    written = []
    for e in fired:
        data = (ledger.line(e["payload"]) + "\n").encode("utf-8")
        target = payload_path(into, track, day, e["kind"], e["subject"])
        held = [p for p in (payload_path(state_dir, track, day, e["kind"], e["subject"]),
                            target) if p.exists()]
        if held:
            if any(p.read_bytes() != data for p in held):
                raise state.StateError(f"{held[0]} holds another payload; a payload is "
                                       f"never rewritten")
            continue
        write_atomic(target, lambda p, data=data: p.write_bytes(data))
        written.append(target.relative_to(into).as_posix())
    text = (ledger.line(new) + "\n").encode("utf-8")
    path = state_path(into, track)
    write_atomic(path, lambda p: p.write_bytes(text))
    written.append(path.relative_to(into).as_posix())
    return written


def step(state_dir: Path, setup: journal.Setup, day: date, records: pd.DataFrame, *,
         into: Path, exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None
         ) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    """Step 6's rules, state and payloads on the new day ``day`` (decision 152
    (f) 3 and 4): every rule over the paper records ``records`` (``into`` the
    staging directory, read first), the state against the stored state of the
    day before, both written to ``into``."""
    entries = rules(state_dir, setup, day, records, overlay=into, exposure=exposure)
    new, fired = transition(read_state(state_dir, setup.track.name), day, entries)
    write(into, state_dir, setup.track.name, day, new, fired)
    return new, fired
