"""The statistical safeguards (DESIGN 11.1 to 11.4, 8, 9.3, 16.1 step 6;
decisions 2026-10-12 30, 59, 60, 61, 62, 69, 70; I-3, I-5, I-6).

Every function reads paper records only (a frame with ``paper.COLUMNS``),
never W or T (I-3). The control moments take ``control_random`` rows only and
rank persistence the subjects it is given, so neither takes a ``portfolio``
row (decision 69).

Rank persistence (11.1, decision 59):

- ``block_dates(epoch, block_days, k)``: the first and last calendar date of
  block ``k``, the ``block_days`` days from ``epoch + k * block_days``.
- ``trading_dates(calendars, bar_seconds, first, last)``: the union of the
  trading dates in ``[first, last]`` of the given calendars (one per
  instrument of the subject), a date counting for a calendar when it expects
  a bar in it, as the daily run's ``is_trading_day`` counts it.
- ``rank_persistence(paper, subjects, *, epoch, block_days, bar_seconds, k,
  min_population, column="net_1x")``: decision 59's row for block ``k >= 1``. ``subjects``
  maps each candidate subject to its own instruments' calendars; a candidate
  belongs to the population when its trading dates hold at least one day in
  each of blocks ``k - 1`` and ``k`` and it has a paper row on every one of
  them. The statistic is ``spearman`` of the summed paper ``column`` (default
  ``net_1x``, which every production caller uses; owner decision O-1) in block
  ``k - 1`` and in block ``k``, ``None`` with fewer than ``min_population``
  members. The row's keys are ``block``, ``first``, ``last`` (block ``k``),
  ``previous_first``, ``previous_last`` (block ``k - 1``), dates in ISO form,
  ``subjects`` (sorted), ``size`` and ``statistic`` (the design names the
  contents, not the keys; these are the simplest names).
- ``due_blocks(epoch, block_days, first_day, day, done)``: decision 70's
  blocks for a new day ``day``: every ``k >= 1`` whose last calendar day is on
  or before ``day``, whose block ``k - 1`` starts on or after ``first_day``
  (the state's first journaled day) and that is not in ``done`` (the blocks
  with a row), ascending.
- ``read_rank_rows(state_dir, track, into=None)`` and
  ``append_rank_rows(state_dir, track, rows, into=None)``: the rows of
  ``stats/<track>/rank_persistence.jsonl``, appended under decision 62's
  rules (``ledger.line``: keys sorted, one object per line; the whole file
  written atomically beside the old one, every earlier line byte-identical; a
  line already present not appended; a torn last line refused; with ``into``,
  the staging directory, read from it when staged there and written under it
  only).
- ``average_ranks(values)`` and ``spearman(x, y)``: the Pearson correlation
  of the ranks, ties taking the average rank; ``None`` when either rank
  series has zero deviation (every rank equal) or there are fewer than two
  values.

Deflated scores and tightening (11.2, 11.4, decision 60):

- ``z(p)``: the standard normal quantile, ``statistics.NormalDist().inv_cdf``.
- ``control_moments(paper, days, column="net_1x")``: ``(mu_c, sd_c)``, the
  mean and sample standard deviation (ddof 1) of the Sharpes
  (``metrics.sharpe``, decision 30) of the frame's ``column`` over ``days`` of
  the random control slots (kind ``control_random``) with a row on each of
  those days, a slot whose Sharpe is not a number left out; both not a number
  with fewer than two such slots. By default ``column`` is ``net_1x``, the
  paper net Sharpe at 1x, as before; the table's adjusted fields name the
  column of a frame of exposure-adjusted net returns (decision 2026-10-17-m19
  147 (a), O-24).
- ``expected_max(mu_c, sd_c, n)``: ``E(N)`` with ``max(n, 2)``.
- ``excess(s, e)``: ``s - e``; not a number when either is.
- ``tightened_percentile(n, base, false_alerts_per_year)``: ``p(N)`` with
  ``max(n, 1)``.
- ``threshold(mu_c, sd_c, n, base, false_alerts_per_year)``:
  ``mu_c + z(p(N)) * sd_c``.

The one-sided t-test of the ``rank_persistence`` rule (15.1, decision
2026-10-17-m19 150):

- ``t_sf(t, df)``: the upper-tail probability ``P(T > t)`` of Student's t
  with ``df > 0`` degrees of freedom, one-sided, ``0.5 * I_x(df / 2, 1 / 2)``
  with ``x = df / (df + t * t)`` for ``t >= 0`` and ``1 - t_sf(-t, df)``
  below, ``I`` the regularized incomplete beta by its continued fraction
  (modified Lentz), with ``math`` only; not a number for a ``t`` that is not
  a number, 0 and 1 at the two infinities.

Clean and exposed observations (11.3, decision 61):

- ``clean_counts(paper, subject)``: the subject's count of paper rows whose
  ``clean`` flag is true and of those whose flag is false.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

from discotrade import ledger
from discotrade.bars.gaps import day_end
from discotrade.bars.store import write_atomic
from discotrade.config import Calendar
from discotrade.metrics import sharpe
from discotrade.tradingcal import expected_bars

#: The Euler-Mascheroni constant of the E(N) formula (decision 60).
EULER_GAMMA = 0.5772156649015329
CONTROL_RANDOM = "control_random"
STATS_DIR = "stats"
RANK_FILE = "rank_persistence.jsonl"
_NORMAL = NormalDist()


# ------------------------------------------------------------------ 11.1


def block_dates(epoch: date, block_days: int, k: int) -> tuple[date, date]:
    """The first and last calendar date of block ``k``."""
    if block_days < 1 or k < 0:
        raise ValueError(f"block {k} of {block_days} days is not a block")
    first = epoch + timedelta(days=k * block_days)
    return first, first + timedelta(days=block_days - 1)


def trading_dates(calendars: Iterable[Calendar], bar_seconds: int, first: date,
                  last: date) -> list[date]:
    """The sorted union of the calendars' trading dates in ``[first, last]``."""
    cals = {cal.name: cal for cal in calendars}
    out = []
    d = first
    while d <= last:
        for name in sorted(cals):
            cal = cals[name]
            if expected_bars(cal, day_end(cal, d - timedelta(days=1)), day_end(cal, d),
                             bar_seconds):
                out.append(d)
                break
        d += timedelta(days=1)
    return out


def due_blocks(epoch: date, block_days: int, first_day: date, day: date,
               done: Iterable[int]) -> list[int]:
    """Decision 70's blocks to append on the new day ``day``, ascending."""
    if block_days < 1:
        raise ValueError(f"a block of {block_days} days is not a block")
    last = ((day - epoch).days + 1) // block_days - 1       # last day of k <= day
    lo = max(1, -(-(first_day - epoch).days // block_days) + 1)   # k - 1 starts >= first
    held = set(done)
    return [k for k in range(lo, last + 1) if k not in held]


def rank_path(root: Path, track: str) -> Path:
    return Path(root) / STATS_DIR / track / RANK_FILE


def _rank_bytes(path: Path) -> bytes:
    data = path.read_bytes() if path.exists() else b""
    if data and not data.endswith(b"\n"):
        raise ledger.LedgerError(f"{path} does not end with a newline; its last line is torn")
    return data


def read_rank_rows(state_dir: Path, track: str, into: Path | None = None
                   ) -> list[dict[str, Any]]:
    """The rows of the rank-persistence file, in file order (from ``into``
    when staged there)."""
    path = rank_path(state_dir, track)
    if into is not None and rank_path(into, track).exists():
        path = rank_path(into, track)
    return [json.loads(x) for x in _rank_bytes(path).decode("utf-8").splitlines()]


def append_rank_rows(state_dir: Path, track: str, rows: Iterable[Mapping[str, Any]],
                     into: Path | None = None) -> list[Mapping[str, Any]]:
    """Append each row whose line the file does not hold; return those appended."""
    source = rank_path(state_dir, track)
    target = source if into is None else rank_path(into, track)
    old = _rank_bytes(target if target.exists() else source)
    present = set(old.decode("utf-8").splitlines())
    appended: list[Mapping[str, Any]] = []
    lines: list[str] = []
    for row in rows:
        text = ledger.line(row)
        if text in present:
            continue
        present.add(text)
        appended.append(row)
        lines.append(text + "\n")
    if lines:
        data = old + "".join(lines).encode("utf-8")
        write_atomic(target, lambda p: p.write_bytes(data))
    return appended


def average_ranks(values: Sequence[float]) -> np.ndarray:
    """1-based ranks of ``values``, ties taking the average of the ranks they span."""
    x = np.asarray(values, dtype=np.float64)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=np.float64)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """The Spearman rank correlation of ``x`` and ``y``, or None (zero deviation)."""
    if len(x) != len(y):
        raise ValueError("the two series differ in length")
    if len(x) < 2:
        return None
    rx, ry = average_ranks(x), average_ranks(y)
    if bool(np.all(rx == rx[0])) or bool(np.all(ry == ry[0])):
        return None
    dx, dy = rx - rx.mean(), ry - ry.mean()
    return float(np.sum(dx * dy) / math.sqrt(float(np.sum(dx * dx)) * float(np.sum(dy * dy))))


def rank_persistence(paper: pd.DataFrame, subjects: Mapping[str, Sequence[Calendar]], *,
                     epoch: date, block_days: int, bar_seconds: int, k: int,
                     min_population: int, column: str = "net_1x") -> dict[str, Any]:
    """Decision 59's row for block ``k`` over the candidate ``subjects``, summing the
    paper ``column`` (owner decision O-1; production callers keep ``net_1x``)."""
    if k < 1:
        raise ValueError(f"block {k} has no block before it")
    prev = block_dates(epoch, block_days, k - 1)
    cur = block_dates(epoch, block_days, k)
    held: dict[str, dict[date, float]] = {}
    span = paper[paper["subject"].isin(list(subjects)) & (paper["date"] >= prev[0])
                 & (paper["date"] <= cur[1])]
    for subject, mine in span.groupby("subject", sort=True):
        held[str(subject)] = {d: float(x) for d, x in zip(mine["date"], mine[column],
                                                          strict=True)}
    members, sums_prev, sums_cur = [], [], []
    for subject in sorted(subjects):
        rows = held.get(subject, {})
        sums = []
        for first, last in (prev, cur):
            dates = trading_dates(subjects[subject], bar_seconds, first, last)
            if not dates or any(d not in rows for d in dates):
                break
            sums.append(math.fsum(rows[d] for d in dates))
        else:
            members.append(subject)
            sums_prev.append(sums[0])
            sums_cur.append(sums[1])
    statistic = None
    if len(members) >= min_population:
        statistic = spearman(sums_prev, sums_cur)
    return {"block": k, "first": cur[0].isoformat(), "last": cur[1].isoformat(),
            "previous_first": prev[0].isoformat(), "previous_last": prev[1].isoformat(),
            "subjects": members, "size": len(members), "statistic": statistic}


# ------------------------------------------------------------------ 11.2, 11.4


def z(p: float) -> float:
    """The standard normal quantile (decision 60)."""
    return _NORMAL.inv_cdf(p)


def control_moments(paper: pd.DataFrame, days: Iterable[date],
                    column: str = "net_1x") -> tuple[float, float]:
    """``(mu_c, sd_c)`` of the random control slots' Sharpes of ``column``
    (``net_1x`` by default) over ``days``."""
    span = sorted(set(days))
    slots = paper[paper["kind"] == CONTROL_RANDOM]
    sharpes = []
    for _, mine in slots.groupby("subject", sort=True):
        by_day = dict(zip(mine["date"], mine[column], strict=True))
        if not span or any(d not in by_day for d in span):
            continue
        s = sharpe(pd.Series([float(by_day[d]) for d in span], dtype=np.float64))
        if not math.isnan(s):
            sharpes.append(s)
    return moments(sharpes)


def moments(values: Sequence[float]) -> tuple[float, float]:
    """``(mean, sd)`` of ``values`` (``sd`` with one degree of freedom), each not
    a number with fewer than two values: ``control_moments``' last step
    (decision 2026-10-18-m20 157)."""
    if len(values) < 2:
        return math.nan, math.nan
    x = np.asarray(values, dtype=np.float64)
    return float(np.mean(x)), float(np.std(x, ddof=1))


def expected_max(mu_c: float, sd_c: float, n: int) -> float:
    """``E(N)``, the Sharpe expected from the best of ``max(n, 2)`` random trials."""
    if math.isnan(mu_c) or math.isnan(sd_c):
        return math.nan
    m = max(n, 2)
    return mu_c + sd_c * ((1 - EULER_GAMMA) * z(1 - 1 / m)
                          + EULER_GAMMA * z(1 - 1 / (m * math.e)))


def excess(s: float, e: float) -> float:
    """``S - E(N)``: not a number when either is."""
    return s - e


def tightened_percentile(n: int, base: float, false_alerts_per_year: float) -> float:
    """``p(N) = 1 - min(1 - base, false_alerts_per_year / max(N, 1))``."""
    return 1 - min(1 - base, false_alerts_per_year / max(n, 1))


def threshold(mu_c: float, sd_c: float, n: int, base: float,
              false_alerts_per_year: float) -> float:
    """``mu_c + z(p(N)) * sd_c``."""
    if math.isnan(mu_c) or math.isnan(sd_c):
        return math.nan
    return mu_c + z(tightened_percentile(n, base, false_alerts_per_year)) * sd_c


# ------------------------------------------------------------------ 15.1

_BETA_EPS = 4 * 2.220446049250313e-16
_BETA_TINY = 1e-300
_BETA_STEPS = 10000


def _beta_fraction(a: float, b: float, x: float) -> float:
    """The continued fraction of ``I_x(a, b)`` (modified Lentz)."""
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) >= _BETA_TINY else _BETA_TINY)
    h = d
    for m in range(1, _BETA_STEPS + 1):
        for aa in (m * (b - m) * x / ((a + 2 * m - 1.0) * (a + 2 * m)),
                   -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1.0))):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) >= _BETA_TINY else _BETA_TINY)
            c = 1.0 + aa / c
            c = c if abs(c) >= _BETA_TINY else _BETA_TINY
            step = c * d
            h *= step
        if abs(step - 1.0) <= _BETA_EPS:
            return h
    raise ArithmeticError(f"the incomplete beta fraction of a={a}, b={b}, x={x} "
                          f"did not converge")


def _beta_regularized(a: float, b: float, x: float, y: float) -> float:
    """``I_x(a, b)``, with ``y = 1 - x`` given so that neither is cancelled."""
    if x <= 0.0:
        return 0.0
    if y <= 0.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log(y))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_fraction(a, b, x) / a
    return 1.0 - front * _beta_fraction(b, a, y) / b


def t_sf(t: float, df: float) -> float:
    """``P(T > t)`` for Student's t with ``df`` degrees of freedom, one-sided
    (decision 2026-10-17-m19 150)."""
    t, df = float(t), float(df)
    if not df > 0 or math.isinf(df):
        raise ValueError(f"{df} is not a number of degrees of freedom")
    if math.isnan(t):
        return math.nan
    if math.isinf(t):
        return 0.0 if t > 0 else 1.0
    tt = t * t
    tail = 0.5 * _beta_regularized(df / 2.0, 0.5, df / (df + tt), tt / (df + tt))
    return tail if t >= 0 else 1.0 - tail


# ------------------------------------------------------------------ 11.3


def clean_counts(paper: pd.DataFrame, subject: str) -> tuple[int, int]:
    """The subject's (clean, exposed) paper day counts."""
    flags = paper.loc[paper["subject"] == subject, "clean"].astype(bool)
    clean = int(flags.sum())
    return clean, int(len(flags)) - clean
