"""The status dashboard (DESIGN 15.5, 3, 16.1 step 7; SPEC 13, 14; owner decisions
O-6, O-14, O-16, O-18; decision 2026-10-17-m19 153; I-6, I-10, I-12, I-14).

``render(state_dir, setup, day, *, overlay=None, records=None, exposure=None)``
gives one self-contained HTML page of the state on the day ``day`` (``D``): no
``<script>``, no ``<link>``, no external URL, no ``@import`` and no ``url(``;
inline styles and inline SVG charts; the viewport declaration of decision 153
(a); one column whose width follows the screen; the page names ``D`` and holds
no wall-clock time (I-12). It reads the state files the alert rules read, each
from ``overlay`` (the day's staging directory) first: the paper records
(``records`` when given, the staged frame of the day loop), ``table.json``, the
alert state ``alerts/<track>/state.json`` (the rules' figures are read from it,
never computed again; SPEC 13), the rank-persistence rows, the trials, calls and
lifecycle ledgers, the approaches, and the health log's events dated on or
before ``D``; and the configuration ``setup`` was loaded from: the thresholds
and their ``[[history]]``, ``HISTORY.toml``'s ``[[change]]`` entries when the
file exists, and ``gates.toml`` (``config.load_gates``). ``exposure`` is the pair
(unit records, position records) already read, as ``alerts.rank_rows`` takes it;
None reads them here when needed.

Every threshold the page shows is read from ``setup.thresholds`` (I-10) and
marked ``<span data-threshold="<table.key>">value</span>``; the page shows every
key of ``alerts.THRESHOLD_KEYS``. It has no control that changes anything.

The panels, in SPEC 13's order, each under its ``<h2>`` heading (``HEADINGS``):

1. Gates for the next stage: each SPEC 14 stage-3 condition with its current
   value, threshold, and ``pass`` or ``not yet``. The money condition is
   ``stage3_money``: the sum of ``portfolio_clean``'s ``net_2x`` over all its
   days up to ``D`` and its day count, passing when the sum is above 0 and the
   count is at least ``stage_gate.min_clean_days``. "Beats the random controls"
   is ``group_edge``'s entry of the alert state (value, threshold, active), with
   each live approach's ``adjusted_excess`` from the table below it, for
   information. "Rank persistence statistically above zero" is the
   ``rank_persistence`` entry (its mean, and ``p``) against
   ``alerts.rank_level``. The state's entry holds the mean (``value``) and the
   critical mean (``threshold``, ``t_crit * s / sqrt(n)``), not ``p``; ``p`` is
   ``stats.t_sf(t, n - 1)`` with ``t = t_crit * value / threshold`` (that is,
   ``mean / (s / sqrt(n))``), ``n`` ``alerts.rank_blocks`` (the design is
   silent on where ``p`` is kept; deriving it from the entry is the simplest
   reading that recomputes no figure from the rows). "Journal recomputation has
   shown no mismatch" is the count of ``journal_mismatch`` events of the health
   log, passing at 0. The two owner flags are ``gates.toml``'s. Each value is
   marked ``data-gate="<name>" data-exact="<repr>"`` and each verdict
   ``data-verdict="<name>"``.
2. Alert rules: for each finding rule, its thresholds and each entry of the
   alert state (subject, value, threshold, active, since); for
   ``persistent_approach`` also the base percentile, ``N`` (the trials ledger's
   rows) and ``p(N)`` (``stats.tightened_percentile``), so the tightening shows;
   for ``rank_persistence`` also ``p`` as above.
3. The combined paper portfolio: ``portfolio``'s cumulative ``net_1x`` and
   ``net_2x`` against the band of the random control slots' cumulative plain
   ``net_1x``, its 5% and 95% quantiles (``numpy.quantile``) per day
   (``portfolio_chart``); and O-14's figures (``exposure_part``) over the last
   ``alerts.group_days`` dates of ``portfolio``: its average net position per
   instrument, the equal-weight mean over its members of each member's
   ``paper.hbar`` over the days of that window on which it is a member, and the
   part of its plain net 1x sum that is static exposure, plain minus adjusted,
   the adjusted sum computed as ``alerts.group_edge`` computes its figure, on
   ``portfolio``'s members (the approaches ``paper.members`` names with a paper
   row on the day).
4. Rank persistence: per block, ``timing`` with its running mean over the
   non-null blocks so far, the zero line, and the significance band, the
   one-sided ``alerts.rank_level`` critical mean ``t_crit * s / sqrt(n)`` over
   the blocks so far (``n`` at least 2 and ``s`` above 0); beside it the net 1x
   ``statistic`` and ``gross``, labelled as used by no rule or gate (O-6)
   (``rank_chart``).
5. The table: ``table.json``'s rows, every field of ``table.FIELDS`` formatted
   as ``table.md`` formats it, each figure column headed ``(plain)`` or
   ``(adjusted)`` (``table.LABELS``).
6. The experiment ledger: trials, admissions and the admission rate, the clean
   and exposed paper days of the approaches, and trials and admissions by model
   and by cell.
7. Health: the last journaled day (``D``); ``data_gaps`` events; the
   ``journal_mismatch`` events (no other record of a recomputation is kept in
   the state); each model's failures over its last ``pool.fail_window`` counted
   calls (``workers.pool.counted``, ``failed``); the worker tokens of ``D``'s
   calls against ``budgets.*`` (no coordinator token record is kept in the
   state); the thresholds of the health detectors; the events of ``D``.
8. The history of threshold and configuration changes.

``write(into, track, page)`` writes ``dashboard/<track>/index.html`` under
``into`` atomically. The day loop writes it into the staging directory on a new
day only (step 7), so a re-run of a finished day writes nothing (I-6).
``last_day(state_dir, track)`` is the state's last journaled day, the day
``discotrade dashboard`` renders; that command never writes into the state
directory.
"""

from __future__ import annotations

import functools
import html
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade import alerts, journal, ledger, paper, state, stats, table
from discotrade.bars.store import write_atomic
from discotrade.config import load_changes, load_gates
from discotrade.workers import pool as worker_pool

DASHBOARD_DIR, PAGE_FILE = "dashboard", "index.html"
#: The panels' headings, in SPEC 13's order (decision 153 (b)).
HEADINGS = ("Gates for the next stage", "Alert rules", "The combined paper portfolio",
            "Rank persistence", "The table", "The experiment ledger", "Health",
            "The history of threshold and configuration changes")
VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'
#: The quantiles of the random controls' band (decision 153 (b) 3).
BAND = (0.05, 0.95)
PASS, NOT_YET = "pass", "not yet"
JOURNAL_MISMATCH, DATA_GAPS = "journal_mismatch", "data_gaps"
BUDGET_KEYS = ("budgets.worker_tokens_per_day", "budgets.worker_max_output_tokens",
               "budgets.coordinator_tokens_per_day")
HEALTH_KINDS = (alerts.FEW_VALID, alerts.COST_STALE, alerts.NO_FINDING)

_BODY = ("margin:0 auto;max-width:48rem;padding:0.5rem;font-family:sans-serif;"
         "font-size:15px;line-height:1.4;color:#222;background:#fff")
_WRAP = "overflow-x:auto;margin:0.25rem 0 0.75rem 0"
_TABLE = "border-collapse:collapse;font-size:13px"
_CELL = "border:1px solid #ccc;padding:2px 4px;text-align:left;vertical-align:top"
_SVG_W, _SVG_H, _PAD = 320.0, 160.0, 8.0


def page_path(root: Path, track: str) -> Path:
    """``dashboard/<track>/index.html`` under ``root``."""
    return Path(root) / DASHBOARD_DIR / track / PAGE_FILE


def last_day(state_dir: Path, track: str) -> date | None:
    """The state's last journaled day, or None."""
    days = [date.fromisoformat(e["date"]) for e in journal.read_index(state_dir, track)]
    return max(days) if days else None


# ------------------------------------------------------------------ the return readers


def stage3_money(records: pd.DataFrame) -> dict[str, Any]:
    """SPEC 14's money condition (decision 153 (b) 1; O-16, O-18): the sum of
    ``portfolio_clean``'s ``net_2x`` over all its days in ``records`` and their
    count."""
    clean = records[records["subject"] == paper.PORTFOLIO_CLEAN]
    return {"sum": math.fsum(float(x) for x in clean["net_2x"]), "days": int(len(clean))}


def _read_exposure(state_dir: Path, track: str, overlay: Path | None
                   ) -> tuple[pd.DataFrame, pd.DataFrame]:
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


def _approaches(state_dir: Path, overlay: Path | None) -> list[state.Approach]:
    held = {a.id: a for a in state.read_approaches(state_dir)}
    if overlay is not None:
        held.update({a.id: a for a in state.read_approaches(overlay)})
    return [held[k] for k in sorted(held)]


def exposure_part(state_dir: Path, setup: journal.Setup, day: date, records: pd.DataFrame, *,
                  overlay: Path | None = None,
                  exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None
                  ) -> dict[str, Any]:
    """O-14's figures over ``W``, the last ``alerts.group_days`` dates of
    ``portfolio`` on or before ``day``: ``plain`` (the sum of its ``net_1x``),
    ``adjusted`` (the sum over ``W`` of the mean over the day's members of each
    member's ``paper.adjusted`` net 1x over its member days of ``W``),
    ``static`` (plain minus adjusted) and ``position`` (each instrument to the
    equal-weight mean over the members of their ``paper.hbar`` over their member
    days of ``W``). Display."""
    track = setup.track.name
    group_days = int(setup.thresholds["alerts.group_days"])
    records = records[records["date"] <= day]
    port = records[records["subject"] == paper.PORTFOLIO]
    w = sorted(set(port["date"]))[-group_days:] if group_days > 0 else []
    symbols = sorted(inst.symbol for inst in setup.instruments)
    mine = records[records["kind"] == paper.APPROACH]
    held = set(zip(mine["subject"].astype(str), mine["date"], strict=True))
    life = ledger.read(state_dir, track, ledger.LIFECYCLE, into=overlay)
    approaches = _approaches(state_dir, overlay)
    members = {d: [aid for aid in paper.members(life, approaches, d) if (aid, d) in held]
               for d in w}
    ids = sorted({m for day_members in members.values() for m in day_members})
    series: dict[str, pd.Series] = {}
    position = {s: 0.0 for s in symbols}
    if ids:
        if exposure is None:
            exposure = _read_exposure(state_dir, track, overlay)
        wanted = set(w)
        near = (exposure[0][exposure[0]["date"].isin(wanted)],
                exposure[1][exposure[1]["date"].isin(wanted)])
        bars: dict[str, dict[str, float]] = {}
        for m in ids:
            days = [d for d in w if m in members[d]]
            series[m] = paper.adjusted(state_dir, setup, m, days, "net_1x",
                                       records=records[records["subject"] == m],
                                       overlay=overlay, exposure=near)
            bars[m] = paper.hbar(near[1], m, symbols, days)
        position = {s: math.fsum(bars[m][s] for m in ids) / len(ids) for s in symbols}
    adjusted = math.fsum(
        math.fsum(float(series[m][d]) for m in members[d]) / len(members[d])
        for d in w if members[d])
    in_w = port[port["date"].isin(set(w))]
    plain = math.fsum(float(x) for x in in_w["net_1x"])
    return {"days": len(w), "first": w[0].isoformat() if w else None,
            "last": w[-1].isoformat() if w else None, "plain": plain, "adjusted": adjusted,
            "static": plain - adjusted, "position": position, "members": ids}


def portfolio_chart(records: pd.DataFrame) -> dict[str, Any]:
    """The portfolio panel's chart: per date, ``portfolio``'s cumulative ``net_1x``
    and ``net_2x``, and the ``BAND`` quantiles of the random control slots'
    cumulative ``net_1x`` (a slot with no row on a date adds 0). Display."""
    port = records[records["subject"] == paper.PORTFOLIO].sort_values("date", kind="stable")
    dates = list(port["date"])
    one = np.cumsum(port["net_1x"].to_numpy(dtype=np.float64))
    two = np.cumsum(port["net_2x"].to_numpy(dtype=np.float64))
    slots = records[records["kind"] == stats.CONTROL_RANDOM]
    lo = hi = np.full(len(dates), np.nan)
    if len(slots) and dates:
        grid = (slots.pivot_table(index="subject", columns="date", values="net_1x",
                                  aggfunc="sum")
                .reindex(columns=dates).fillna(0.0).to_numpy(dtype=np.float64))
        cumulative = np.cumsum(grid, axis=1)
        lo, hi = np.quantile(cumulative, BAND, axis=0)
    return {"dates": dates, "net_1x": [float(x) for x in one],
            "net_2x": [float(x) for x in two], "low": [float(x) for x in lo],
            "high": [float(x) for x in hi]}


@functools.cache
def _t_critical(level: float, df: int) -> float:
    return alerts._t_critical(level, df)


state.register_cache("discotrade.dashboard._t_critical", _t_critical.cache_clear)


def rank_chart(rows: Sequence[Mapping[str, Any]], level: float) -> list[dict[str, Any]]:
    """The rank panel's rows, in file order: ``block``, ``timing``, its running
    mean and the critical mean ``t_crit * s / sqrt(n)`` over the non-null
    ``timing`` values so far (``None`` below 2 values or with ``s`` 0), and the
    net 1x ``statistic`` and ``gross`` beside them. Display (O-6)."""
    out, seen = [], []
    for row in rows:
        timing = row.get(alerts.TIMING)
        if timing is not None:
            seen.append(float(timing))
        n = len(seen)
        mean = math.fsum(seen) / n if n else None
        band = None
        if n >= 2:
            s = float(np.std(np.asarray(seen, dtype=np.float64), ddof=1))
            if math.isfinite(s) and s > 0:
                band = _t_critical(level, n - 1) * s / math.sqrt(n)
        out.append({"block": int(row["block"]), "first": row.get("first"),
                    "last": row.get("last"), "timing": timing, "mean": mean, "band": band,
                    "statistic": row.get("statistic"), "gross": row.get("gross")})
    return out


# ------------------------------------------------------------------ formatting


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _real(x: Any) -> float | None:
    if x is None or isinstance(x, bool):
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _n(x: Any) -> str:
    """A number as the page shows it: an integer as itself, a real to six
    significant digits, a missing or non-finite one as ``-``."""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int | np.integer):
        return str(int(x))
    r = _real(x)
    return "-" if r is None else f"{r:.6g}"


def _exact(x: Any) -> str:
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int | np.integer):
        return str(int(x))
    r = _real(x)
    return "-" if r is None else repr(r)


def _th(setup: journal.Setup, key: str) -> str:
    """A threshold, read from ``setup.thresholds`` and marked with its key."""
    return f'<span data-threshold="{_e(key)}">{_e(repr(setup.thresholds[key]))}</span>'


def _gate(name: str, value: Any, shown: str | None = None) -> str:
    return (f'<span data-gate="{_e(name)}" data-exact="{_e(_exact(value))}">'
            f"{_e(_n(value) if shown is None else shown)}</span>")


def _verdict(name: str, ok: bool) -> str:
    return f'<span data-verdict="{_e(name)}">{PASS if ok else NOT_YET}</span>'


def _table(head: Sequence[str], rows: Iterable[Sequence[str]],
           attrs: Sequence[str] | None = None) -> str:
    """A table; ``head`` is text (escaped here), each cell of ``rows`` is HTML."""
    th = "".join(f'<th style="{_CELL}">{_e(h)}</th>' for h in head)
    body = []
    for i, row in enumerate(rows):
        extra = "" if attrs is None else f" {attrs[i]}"
        body.append(f"<tr{extra}>" + "".join(f'<td style="{_CELL}">{c}</td>' for c in row)
                    + "</tr>")
    return (f'<div style="{_WRAP}"><table style="{_TABLE}"><thead><tr>{th}</tr></thead>'
            f"<tbody>{''.join(body)}</tbody></table></div>")


def _p(text: str) -> str:
    return f'<p style="margin:0.25rem 0">{text}</p>'


def _svg(lines: Sequence[tuple[str, Sequence[float | None], str]],
         band: tuple[Sequence[float | None], Sequence[float | None]] | None,
         label: str) -> str:
    """An inline SVG chart: ``lines`` (label, values, colour) over a common x
    index, an optional shaded ``band`` (low, high), and the zero line."""
    values = [v for _, vs, _ in lines for v in vs if v is not None and math.isfinite(v)]
    if band is not None:
        values += [v for vs in band for v in vs if v is not None and math.isfinite(v)]
    count = max([len(vs) for _, vs, _ in lines] + [0])
    lo, hi = min(values + [0.0]), max(values + [0.0])
    if hi - lo <= 0:
        lo, hi = lo - 1.0, hi + 1.0

    def x(i: int) -> float:
        return _PAD + (i * (_SVG_W - 2 * _PAD) / (count - 1) if count > 1 else 0.0)

    def y(v: float) -> float:
        return _PAD + (hi - v) * (_SVG_H - 2 * _PAD) / (hi - lo)

    def points(vs: Sequence[float | None]) -> list[str]:
        return [f"{x(i):.2f},{y(v):.2f}" for i, v in enumerate(vs)
                if v is not None and math.isfinite(v)]

    parts = [f'<svg viewBox="0 0 {_SVG_W:.0f} {_SVG_H:.0f}" width="100%" role="img" '
             f'aria-label="{_e(label)}" style="max-width:40rem;border:1px solid #ddd">']
    if band is not None:
        upper, lower = points(band[1]), points(band[0])
        if upper and lower:
            parts.append(f'<polygon points="{" ".join(upper + lower[::-1])}" '
                         f'fill="#cfe3f5" stroke="none"/>')
    parts.append(f'<line x1="{_PAD:.2f}" y1="{y(0.0):.2f}" x2="{_SVG_W - _PAD:.2f}" '
                 f'y2="{y(0.0):.2f}" stroke="#999" stroke-dasharray="3,3"/>')
    for _, vs, colour in lines:
        pts = points(vs)
        if len(pts) == 1:
            cx, cy = pts[0].split(",")
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="2" fill="{colour}"/>')
        elif pts:
            parts.append(f'<polyline points="{" ".join(pts)}" fill="none" '
                         f'stroke="{colour}" stroke-width="1.5"/>')
    parts.append("</svg>")
    legend = ", ".join(f'<span style="color:{c}">{_e(name)}</span>' for name, _, c in lines)
    return "".join(parts) + _p(legend + (", shaded: the band" if band is not None else "")
                               + f"; dashed: zero; top {_e(_n(hi))}, bottom {_e(_n(lo))}")


# ------------------------------------------------------------------ the panels


def _entries(held: Mapping[str, Any] | None, kind: str) -> list[tuple[str, dict[str, Any]]]:
    if held is None:
        return []
    prefix = f"{kind}|"
    return [(key[len(prefix):], dict(entry)) for key, entry in sorted(held["alerts"].items())
            if key.startswith(prefix)]


def _rank_p(setup: journal.Setup, entry: Mapping[str, Any] | None) -> float | None:
    """``p`` of the ``rank_persistence`` entry, from its mean and critical mean."""
    if entry is None:
        return None
    mean, critical = _real(entry.get("value")), _real(entry.get("threshold"))
    n = int(setup.thresholds["alerts.rank_blocks"])
    if mean is None or critical is None or critical == 0 or n < 2:
        return None
    t = _t_critical(float(setup.thresholds["alerts.rank_level"]), n - 1) * mean / critical
    return stats.t_sf(t, n - 1)


def _gates_panel(setup: journal.Setup, records: pd.DataFrame, held: Mapping[str, Any] | None,
                 rows: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]]) -> str:
    track = setup.track.name
    money = stage3_money(records)
    least = int(setup.thresholds["stage_gate.min_clean_days"])
    alerts_held = {} if held is None else held["alerts"]
    group = alerts_held.get(alerts.key_of(alerts.GROUP, track))
    rank = alerts_held.get(alerts.key_of(alerts.RANK, track))
    mismatches = sum(1 for e in events if e["kind"] == JOURNAL_MISMATCH)
    owner = load_gates(_config_dir(setup))
    p = _rank_p(setup, rank)
    out = [_table(("condition", "current value", "threshold", ""), [
        ("positive net of 2x costs: <code>portfolio_clean</code> net 2x, summed over its days",
         f"{_gate('money', money['sum'])} over {_gate('money_days', money['days'])} days",
         f"above 0 over at least {_th(setup, 'stage_gate.min_clean_days')} days of clean "
         f"record",
         _verdict("money", money["sum"] > 0 and money["days"] >= least)),
        ("beats the random controls: <code>group_edge</code>, adjusted net 1x over the last "
         f"{_th(setup, 'alerts.group_days')} days",
         _gate("group_edge", None if group is None else group["value"]),
         "the bootstrap quantile " + _e(_n(None if group is None else group["threshold"])),
         _verdict("group_edge", bool(group is not None and group["active"]))),
        ("rank persistence statistically above zero: <code>rank_persistence</code>, "
         "mean timing statistic",
         f"{_gate('rank_persistence', None if rank is None else rank['value'])}, "
         f"p {_gate('rank_p', p)}",
         f"p below {_th(setup, 'alerts.rank_level')}",
         _verdict("rank_persistence", bool(rank is not None and rank["active"]))),
        ("journal recomputation has shown no mismatch: <code>journal_mismatch</code> events",
         _gate("journal_mismatch", mismatches), "0",
         _verdict("journal_mismatch", mismatches == 0)),
        ("stage 2 fills match the cost model within a set tolerance (the owner's, "
         "<code>gates.toml</code>)",
         _gate("stage2_fills_match", owner.stage2_fills_match), "true",
         _verdict("stage2_fills_match", owner.stage2_fills_match)),
        ("tax treatment is confirmed with an accountant (the owner's, "
         "<code>gates.toml</code>)",
         _gate("tax_confirmed", owner.tax_confirmed), "true",
         _verdict("tax_confirmed", owner.tax_confirmed)),
    ])]
    live = [r for r in rows if r["section"] == table.LIVE]
    out.append(_p("For information, each live approach's <code>adjusted_excess</code> "
                  "from the table:"))
    out.append(_table(("approach", "cell", "adjusted_excess (adjusted)"),
                      [(_e(r["subject"]), _e(r["cell"]), _e(_n(r["adjusted_excess"])))
                       for r in live]))
    return "".join(out)


def _alerts_panel(setup: journal.Setup, held: Mapping[str, Any] | None,
                  trials: Sequence[Mapping[str, Any]]) -> str:
    track = setup.track.name
    out = []
    for kind in alerts.FINDING_KINDS:
        out.append(f"<h3>{_e(kind)}</h3>")
        out.append(_p("thresholds: " + ", ".join(
            f"<code>{_e(k)}</code> {_th(setup, k)}" for k in alerts.THRESHOLD_KEYS[kind])))
        if kind == alerts.PERSISTENT:
            force = alerts.in_force(setup, kind)
            n = len(trials)
            p_n = stats.tightened_percentile(
                n, float(force["alerts.persistent_base_percentile"]),
                float(force["alerts.false_alerts_per_year"]))
            out.append(_p(f"the control percentile tightens with the trial count: base "
                          f"{_th(setup, 'alerts.persistent_base_percentile')}, N {n}, "
                          f"p(N) {_e(_n(p_n))}; each approach's threshold below is at the "
                          f"current N"))
        if kind == alerts.RANK:
            entry = None if held is None else held["alerts"].get(alerts.key_of(kind, track))
            out.append(_p(f"p {_e(_n(_rank_p(setup, entry)))}"))
        entries = _entries(held, kind)
        out.append(_table(("subject", "value", "threshold", "active", "since"),
                          [(_e(subject), _e(_n(e["value"])), _e(_n(e["threshold"])),
                            "yes" if e["active"] else "no", _e(e["since"] or "-"))
                           for subject, e in entries]) if entries
                   else _p("no entry in the alert state"))
    return "".join(out)


def _portfolio_panel(state_dir: Path, setup: journal.Setup, day: date, records: pd.DataFrame,
                     overlay: Path | None,
                     exposure: tuple[pd.DataFrame, pd.DataFrame] | None) -> str:
    chart = portfolio_chart(records)
    part = exposure_part(state_dir, setup, day, records, overlay=overlay, exposure=exposure)
    dates = chart["dates"]
    out = [_p("Cumulative plain net result of <code>portfolio</code> at 1x and 2x costs, "
              "against the band of the random control slots' cumulative plain net 1x "
              "(5% and 95% quantiles per day)"
              + (f", {_e(dates[0].isoformat())} to {_e(dates[-1].isoformat())}"
                 if dates else "")),
           _svg([("net 1x", chart["net_1x"], "#1f5fa8"), ("net 2x", chart["net_2x"], "#b8462e")],
                (chart["low"], chart["high"]), "combined paper portfolio")]
    if dates:
        out.append(_table(("date", "net 1x", "net 2x", "band 5%", "band 95%"), [(
            _e(dates[-1].isoformat()), _e(_n(chart["net_1x"][-1])),
            _e(_n(chart["net_2x"][-1])), _e(_n(chart["low"][-1])),
            _e(_n(chart["high"][-1])))]))
    out.append(_p(f"Exposure (O-14), over the last {_th(setup, 'alerts.group_days')} days of "
                  f"<code>portfolio</code> ({part['days']} days"
                  + (f", {_e(part['first'])} to {_e(part['last'])}" if part["first"] else "")
                  + "): plain net 1x " + _e(_n(part["plain"])) + ", adjusted "
                  + _e(_n(part["adjusted"])) + ", static exposure (plain minus adjusted) "
                  + _e(_n(part["static"]))))
    out.append(_table(("instrument", "average net position"),
                      [(_e(s), _e(_n(v))) for s, v in sorted(part["position"].items())]))
    return "".join(out)


def _rank_panel(setup: journal.Setup, rows: Sequence[Mapping[str, Any]]) -> str:
    level = float(setup.thresholds["alerts.rank_level"])
    chart = rank_chart(rows, level)
    out = [_p(f"The timing statistic per block (the rule's), its running mean, the zero "
              f"line and the significance band: the one-sided critical mean at "
              f"{_th(setup, 'alerts.rank_level')} over the blocks so far."),
           _svg([("timing", [_real(r["timing"]) for r in chart], "#1f5fa8"),
                 ("running mean", [_real(r["mean"]) for r in chart], "#2e7d32"),
                 ("band", [_real(r["band"]) for r in chart], "#b8462e")], None,
                "rank persistence"),
           _p("The net 1x statistic and the gross statistic are shown for information: "
              "they are used by no rule or gate (O-6).")]
    out.append(_table(("block", "first", "last", "timing", "running mean", "band",
                       "net 1x (no rule)", "gross (no rule)"),
                      [(_e(r["block"]), _e(r["first"] or "-"), _e(r["last"] or "-"),
                        _e(_n(r["timing"])), _e(_n(r["mean"])), _e(_n(r["band"])),
                        _e(_n(r["statistic"])), _e(_n(r["gross"]))) for r in chart]))
    return "".join(out)


def _table_panel(held: Mapping[str, Any] | None) -> str:
    if held is None:
        return _p("no table")
    head = ("section", "subject") + table.FIELDS
    labels = [f"{k} ({table.LABELS[k]})" if k in table.LABELS else k for k in head]
    rows = held["rows"]
    return (_p(f"{_e(held['track'])} {_e(held['date'])}, N {_e(held['N'])}")
            + _table(labels, [[_e(table._cell(k, r[k])) for k in head] for r in rows],
                     [f'data-row="{_e(r["section"])}"' for r in rows]))


def _ledger_panel(records: pd.DataFrame, trials: Sequence[Mapping[str, Any]]) -> str:
    n = len(trials)
    admitted = sum(1 for r in trials if r["admitted"])
    mine = records[records["kind"] == paper.APPROACH]
    clean = int(mine["clean"].astype(bool).sum())
    out = [_p(f"trials {n}, admitted {admitted}, admission rate "
              f"{_e(_n(admitted / n if n else None))}; approach paper days clean {clean}, "
              f"exposed {len(mine) - clean}")]
    for name, key in (("model", "model_id"), ("cell", "cell")):
        counts: dict[str, list[int]] = {}
        for r in trials:
            c = counts.setdefault(str(r[key]), [0, 0])
            c[0] += 1
            c[1] += 1 if r["admitted"] else 0
        out.append(_table((name, "trials", "admitted"),
                          [(_e(k), _e(v[0]), _e(v[1])) for k, v in sorted(counts.items())]))
    return "".join(out)


def _health_panel(setup: journal.Setup, day: date, events: Sequence[Mapping[str, Any]],
                  calls: Sequence[Mapping[str, Any]]) -> str:
    gaps = [e for e in events if e["kind"] == DATA_GAPS]
    bad = [e for e in events if e["kind"] == JOURNAL_MISMATCH]
    out = [_p(f"last journaled day {_e(day.isoformat())}"),
           _p(f"data_gaps events {len(gaps)}"
              + (f", the last on {_e(gaps[-1]['date'])}" if gaps else "")),
           _p(f"journal recomputation: journal_mismatch events {len(bad)}"
              + (f", the last on {_e(bad[-1]['date'])}" if bad else "")
              + "; the state keeps no other record of a recomputation")]
    window = int(setup.thresholds["pool.fail_window"])
    by_model: dict[str, list[bool]] = {}
    for r in calls:
        if date.fromisoformat(str(r["date"])) <= day and worker_pool.counted(str(r["outcome"])):
            by_model.setdefault(str(r["model"]), []).append(
                worker_pool.failed(str(r["outcome"])))
    out.append(_p(f"worker failures over each model's last {_th(setup, 'pool.fail_window')} "
                  f"counted calls, against the rate {_th(setup, 'pool.fail_rate')}:"))
    out.append(_table(("model", "counted calls", "failures"),
                      [(_e(m), _e(len(v[-window:])), _e(sum(v[-window:])))
                       for m, v in sorted(by_model.items())]))
    today = [r for r in calls if str(r["date"]) == day.isoformat()]
    tokens = sum(int(r["tokens_in"] or 0) + int(r["tokens_out"] or 0) for r in today)
    out.append(_p(f"tokens of {_e(day.isoformat())}: worker {tokens} against "
                  f"{_th(setup, 'budgets.worker_tokens_per_day')} (at most "
                  f"{_th(setup, 'budgets.worker_max_output_tokens')} out per call); "
                  f"coordinator: no record kept in the state, budget "
                  f"{_th(setup, 'budgets.coordinator_tokens_per_day')}"))
    out.append(_p("health alert thresholds: " + "; ".join(
        f"{_e(kind)} " + ", ".join(f"<code>{_e(k)}</code> {_th(setup, k)}"
                                   for k in alerts.THRESHOLD_KEYS[kind])
        for kind in HEALTH_KINDS)))
    mine = [e for e in events if e["date"] == day.isoformat()]
    out.append(_table(("level", "kind", "subject", "detail"),
                      [(_e(e["level"]), _e(e["kind"]), _e(e["subject"]),
                        _e(json.dumps(e["detail"], sort_keys=True))) for e in mine])
               if mine else _p(f"no health event on {_e(day.isoformat())}"))
    return "".join(out)


def _history_panel(setup: journal.Setup) -> str:
    out = [_p("<code>thresholds.toml</code> history:"),
           _table(("date", "key", "old", "new", "reason"),
                  [(_e(h.date.isoformat()), _e(h.key), _e("-" if h.old is None else h.old),
                    _e("-" if h.new is None else h.new), _e(h.reason))
                   for h in setup.thresholds.history])]
    path = _config_dir(setup) / "HISTORY.toml"
    changes = load_changes(path) if path.is_file() else ()
    out.append(_p("<code>HISTORY.toml</code> changes:"))
    out.append(_table(("date", "file", "key", "old", "new", "reason", "decision"),
                      [(_e(c.date.isoformat()), _e(c.file), _e(c.key),
                        _e("-" if c.old is None else c.old), _e("-" if c.new is None else c.new),
                        _e(c.reason), _e(c.decision)) for c in changes])
               if changes else _p("none"))
    return "".join(out)


def _config_dir(setup: journal.Setup) -> Path:
    if setup.config_dir is None:
        raise ValueError("the dashboard needs the configuration directory the setup was "
                         "loaded from")
    return Path(setup.config_dir)


def _health_events(state_dir: Path, track: str, day: date) -> list[dict[str, Any]]:
    path = state.health_path(state_dir, track)
    if not path.exists():
        return []
    events = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    return [e for e in events if date.fromisoformat(e["date"]) <= day]


def _json(state_dir: Path, overlay: Path | None, rel: Path) -> Any:
    for root in ([] if overlay is None else [overlay]) + [state_dir]:
        path = Path(root) / rel
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def render(state_dir: Path, setup: journal.Setup, day: date, *, overlay: Path | None = None,
           records: pd.DataFrame | None = None,
           exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None) -> str:
    """The page of the state on ``day`` (decision 153 (a), (b))."""
    state_dir = Path(state_dir)
    track = setup.track.name
    if records is None:
        records = None if overlay is None else paper.read(overlay, track)
        if records is None:
            records = paper.read(state_dir, track)
    if records is None:
        records = pd.DataFrame(columns=list(paper.COLUMNS))
    records = records[records["date"] <= day]
    held_table = _json(state_dir, overlay, Path(table.TABLE_DIR) / track / table.JSON_FILE)
    held = _json(state_dir, overlay, Path(alerts.ALERTS_DIR) / track / alerts.STATE_FILE)
    rank_rows = stats.read_rank_rows(state_dir, track, into=overlay)
    trials = [r for r in ledger.read(state_dir, track, ledger.TRIALS, into=overlay)
              if date.fromisoformat(str(r["date"])) <= day]
    calls = ledger.read(state_dir, track, ledger.CALLS, into=overlay)
    events = _health_events(state_dir, track, day)
    table_rows = [] if held_table is None else held_table["rows"]
    panels = (
        _gates_panel(setup, records, held, table_rows, events),
        _alerts_panel(setup, held, trials),
        _portfolio_panel(state_dir, setup, day, records, overlay, exposure),
        _rank_panel(setup, rank_rows),
        _table_panel(held_table),
        _ledger_panel(records, trials),
        _health_panel(setup, day, events, calls),
        _history_panel(setup),
    )
    title = f"discotrade {track} {day.isoformat()}"
    states = "" if held is None else (
        f"; alert state of {_e(held['date'])}" if held["date"] != day.isoformat() else "")
    body = "".join(f'<section style="margin:0 0 1rem 0"><h2>{_e(h)}</h2>{p}</section>'
                   for h, p in zip(HEADINGS, panels, strict=True))
    return ("<!DOCTYPE html>\n"
            f'<html lang="en"><head><meta charset="utf-8">{VIEWPORT}'
            f"<title>{_e(title)}</title></head>"
            f'<body style="{_BODY}"><h1 style="font-size:1.3rem">{_e(title)}</h1>'
            + _p(f"The state on {_e(day.isoformat())}, the last journaled day{states}. "
                 "Read-only: this page shows thresholds and cannot change them. "
                 "Simulation only.")
            + body + "</body></html>\n")


def write(into: Path, track: str, page: str) -> str:
    """Write ``page`` to ``dashboard/<track>/index.html`` under ``into``, atomically;
    return its path relative to ``into``."""
    data = page.encode("utf-8")
    path = page_path(into, track)
    write_atomic(path, lambda p: p.write_bytes(data))
    return path.relative_to(into).as_posix()

