"""Alert rules and alert state (DESIGN 15.1 to 15.3, 16.1 step 6). Built in
step S4.1; this module holds, so far, the rank rows of the day loop and the
finding rules ``persistent_approach`` and ``group_edge``, which the day loop
does not call yet.

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
  ``W``, each with its own average positions over ``W`` (O-7).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade import controls, journal, ledger, lifecycle, paper, state, stats
from discotrade.config import Calendar
from discotrade.metrics import positive, sharpe

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
        for subject in sorted(set(span["subject"])):
            mine = span[span["subject"] == subject]
            kind = str(mine["kind"].iloc[0])
            for first, last in windows:
                window = stats.trading_dates(subjects[subject], track.bar_seconds, first, last)
                if not window:
                    continue
                if exposure is None:
                    exposure = _exposure(state_dir, track.name, overlay)
                near = (exposure[0][exposure[0]["date"].isin(window)],
                        exposure[1][exposure[1]["date"].isin(window)])
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
#: Every threshold key each finding rule here reads (decision 2026-10-17-m19 152 (b)).
THRESHOLD_KEYS: Mapping[str, tuple[str, ...]] = {
    PERSISTENT: ("alerts.persistent_min_days", "alerts.persistent_base_percentile",
                 "alerts.false_alerts_per_year"),
    GROUP: ("alerts.group_days", "alerts.group_level", "alerts.group_bootstrap"),
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


def slot_series(state_dir: Path, setup: journal.Setup, days: Iterable[date],
                records: pd.DataFrame, *, overlay: Path | None = None,
                exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None
                ) -> dict[str, pd.Series]:
    """Each random control slot with a paper row on every day of ``days``, in slot
    order: its exposure-adjusted net 1x over ``days``, with its own average
    positions over them (O-7)."""
    span = sorted(set(days))
    wanted = set(span)
    if not span:
        return {}
    slots = records[(records["kind"] == stats.CONTROL_RANDOM) & records["date"].isin(wanted)]
    near = None if exposure is None else _near(exposure, wanted)
    out: dict[str, pd.Series] = {}
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
    for aid in sorted(a for a, s in after.items()
                      if s.state in (lifecycle.LIVE, lifecycle.DORMANT)):
        mine = records[records["subject"] == aid].sort_values("date", kind="stable")
        clean_rows = mine[mine["clean"].astype(bool)]
        w = list(clean_rows["date"])
        s1 = s2 = plain_1x = plain_2x = mu_c = sd_c = math.nan
        if w:
            if exposure is None:
                exposure = _exposure(state_dir, track, overlay)
            near = _near(exposure, w)
            s1, s2 = (sharpe(paper.adjusted(state_dir, setup, aid, w, c, records=mine,
                                            overlay=overlay, exposure=near))
                      for c in ("net_1x", "net_2x"))
            plain_1x, plain_2x = sharpe(clean_rows["net_1x"]), sharpe(clean_rows["net_2x"])
            slots = slot_series(state_dir, setup, w, records, overlay=overlay, exposure=near)
            mu_c, sd_c = stats.control_moments(_slot_frame(slots), w, column=SLOT_COLUMN)
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
