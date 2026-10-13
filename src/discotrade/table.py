"""The table (DESIGN 10.4, 8, 11.2; decisions 2026-10-12 25, 30, 41, 60, 62, 63,
69, 71; I-3, I-4, I-6).

``build(state_dir, setup, day, records, into=None)`` gives decision 71's table
of the new day ``day``: one object holding ``track``, ``date`` (``day``),
``N`` (the row count of ``ledger/<track>/trials.jsonl``, decision 60) and
``rows``, in this order:

- ``live``: the approaches whose state after ``day``'s steps
  (``lifecycle.states`` of the lifecycle rows dated on or before ``day``) is
  ``live``, grouped by cell, cells in ascending string order, ids ascending
  within a cell;
- ``dormant``: the dormant approaches by ascending id;
- ``control``: ``bh:<symbol>`` in the track's instrument order, then ``rc:0``
  to the last slot of ``controls.random_pool`` in slot order (a control with
  no paper row yet is listed with an empty record);
- ``portfolio``: ``portfolio`` then ``portfolio_clean``.

Retired approaches are not listed. Each row holds ``section``, ``subject``,
the approach fields ``cell``, ``description``, ``model_id``,
``model_version``, ``admitted`` (from its ``meta.json``) and
``admission_score`` (the ``sharpe`` of the ``metrics_t`` of its trial row: the
last row of the trials ledger with its id and ``admitted`` true; ``null`` when
the ledger holds none, as for an approach written without the admission
function; the design is silent, this is the simplest reading), the paper
record over all its paper days (``days``, ``clean_days``, ``sharpe``,
``sharpe_2x``, ``trades``, ``max_drawdown``: DESIGN 8 by ``metrics.sharpe``
with decision 30 and ``metrics.max_drawdown`` with decision 41, over its paper
``net_1x`` and ``net_2x`` in date order; ``trades`` the sum of its paper
``trades``), ``breakeven_cost`` (decision 25 over its journal rows: the sum of
``gross`` over the sum of ``trade`` plus ``2 * |prev_position|`` on each row
with ``roll``, times 10000; not a number without turnover), the deflated
figures over its paper days (``S`` its ``sharpe``, ``E_N`` from
``stats.control_moments`` over those days and ``stats.expected_max`` with
``N``, ``excess`` ``S - E_N``; decision 60) and ``state_history`` (its
lifecycle rows, ``date``, ``from``, ``to``, ``reason``, in ledger order). The
approach fields, ``state_history`` and the deflated figures are ``null`` for
the controls and the portfolio series, and ``breakeven_cost`` for the
portfolio series. A float that is not finite is ``null``.

The journal sums of ``breakeven_cost`` are kept per journal day in a cache of
the process keyed by the day's content hash in the journal index (equal
hashes are equal rows, ``state.content_hash`` covering every column), so that
a replay reads each journal day once rather than every day again; the cache
changes no result.

``write(root, track, table)`` writes ``table/<track>/table.json`` (the object
as ``ledger.line`` writes a row: keys sorted, no whitespace, a newline) and
``table.md`` (``render``: a title, ``N``, then one Markdown table per section
in the order above, the same rows in the same order, every real number to
four decimals, ``null`` as ``-``; no wall-clock time) under ``root``, each
atomically. The daily run writes them to the staging directory on a new day
only, so a re-run of a finished day writes neither (I-6).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade import journal, ledger, lifecycle, paper, state, stats
from discotrade.bars.store import write_atomic
from discotrade.metrics import max_drawdown, sharpe
from discotrade.state import Approach

TABLE_DIR = "table"
JSON_FILE = "table.json"
MD_FILE = "table.md"
LIVE, DORMANT, CONTROL, PORTFOLIO = "live", "dormant", "control", "portfolio"
SECTIONS = (LIVE, DORMANT, CONTROL, PORTFOLIO)
_BPS = 10000.0
#: The row's keys after ``section`` and ``subject``, in the order ``table.md`` shows them.
FIELDS = ("cell", "description", "model_id", "model_version", "admitted", "admission_score",
          "days", "clean_days", "sharpe", "sharpe_2x", "trades", "max_drawdown",
          "breakeven_cost", "S", "E_N", "excess", "state_history")
_APPROACH_FIELDS = ("cell", "description", "model_id", "model_version", "admitted",
                    "admission_score", "S", "E_N", "excess", "state_history")
_REALS = frozenset(("admission_score", "sharpe", "sharpe_2x", "max_drawdown",
                    "breakeven_cost", "S", "E_N", "excess"))

#: (track, day, content hash) -> subject -> (gross, trade, rolled turnover) sums.
_DAY_SUMS: dict[tuple[str, str, str], dict[str, tuple[float, float, float]]] = {}


def table_dir(root: Path, track: str) -> Path:
    return Path(root) / TABLE_DIR / track


def _day_sums(rows: pd.DataFrame) -> dict[str, tuple[float, float, float]]:
    if rows.empty:
        return {}
    gross = rows["gross"].to_numpy(dtype=np.float64)
    trade = rows["trade"].to_numpy(dtype=np.float64)
    rolled = np.where(rows["roll"].to_numpy(dtype=bool),
                      2.0 * np.abs(rows["prev_position"].to_numpy(dtype=np.float64)), 0.0)
    frame = pd.DataFrame({"subject": rows["subject"].to_numpy(), "gross": gross,
                          "trade": trade, "rolled": rolled})
    summed = frame.groupby("subject", sort=True)[["gross", "trade", "rolled"]].sum()
    return {str(s): (float(g), float(t), float(r))
            for s, g, t, r in zip(summed.index, summed["gross"], summed["trade"],
                                  summed["rolled"], strict=True)}


def journal_sums(state_dir: Path, track: str, into: Path | None = None
                 ) -> dict[str, list[tuple[float, float, float]]]:
    """Per subject, its (gross, trade, rolled turnover) sums of each journal
    day, in index order (``into`` read first, as the staged day is there)."""
    staged = into is not None and journal.index_path(into, track).exists()
    index = journal.read_index(Path(into) if staged else Path(state_dir), track)
    out: dict[str, list[tuple[float, float, float]]] = {}
    for entry in index:
        key = (track, str(entry["date"]), str(entry["content_hash"]))
        sums = _DAY_SUMS.get(key)
        if sums is None:
            day = date.fromisoformat(str(entry["date"]))
            rows = None if into is None else journal.read_day(into, track, day)
            if rows is None:
                rows = journal.read_day(state_dir, track, day)
            if rows is None:
                raise journal.JournalError(f"the index of {track} names {entry['date']}, "
                                           f"which has no journal file")
            sums = _day_sums(rows)
            _DAY_SUMS[key] = sums
        for subject, values in sums.items():
            out.setdefault(subject, []).append(values)
    return out


def breakeven(sums: Sequence[tuple[float, float, float]]) -> float:
    """Decision 25's ``breakeven_cost`` from per-day (gross, trade, rolled) sums."""
    gross = math.fsum(s[0] for s in sums)
    turnover = math.fsum(s[1] for s in sums) + math.fsum(s[2] for s in sums)
    if not turnover > 0:
        return math.nan
    return gross / turnover * _BPS


def _record(mine: pd.DataFrame | None) -> dict[str, Any]:
    if mine is None or mine.empty:
        empty = pd.Series([], dtype=np.float64)
        return {"days": 0, "clean_days": 0, "sharpe": sharpe(empty),
                "sharpe_2x": sharpe(empty), "trades": 0, "max_drawdown": max_drawdown(empty)}
    return {"days": int(len(mine)), "clean_days": int(mine["clean"].astype(bool).sum()),
            "sharpe": sharpe(mine["net_1x"]), "sharpe_2x": sharpe(mine["net_2x"]),
            "trades": int(mine["trades"].sum()), "max_drawdown": max_drawdown(mine["net_1x"])}


def _approaches(state_dir: Path, into: Path | None) -> list[Approach]:
    held = {a.id: a for a in state.read_approaches(state_dir)}
    if into is not None:
        held.update({a.id: a for a in state.read_approaches(into)})
    return [held[k] for k in sorted(held)]


def build(state_dir: Path, setup: Any, day: date, records: pd.DataFrame,
          into: Path | None = None) -> dict[str, Any]:
    """Decision 71's table of ``day`` from the paper ``records`` and the state."""
    track = setup.track.name
    life = ledger.read(state_dir, track, ledger.LIFECYCLE, into=into)
    trials = ledger.read(state_dir, track, ledger.TRIALS, into=into)
    n = len(trials)
    approaches = _approaches(state_dir, into)
    after = lifecycle.states(life, approaches, day + timedelta(days=1))
    by_id = {a.id: a for a in approaches}
    records = records[records["date"] <= day]
    groups = {str(s): g.sort_values("date", kind="mergesort")
              for s, g in records.groupby("subject", sort=False)}
    sums = journal_sums(state_dir, track, into)

    live = sorted((str(by_id[a].meta["cell"]), a) for a, s in after.items() if s.state == LIVE)
    dormant = sorted(a for a, s in after.items() if s.state == DORMANT)
    controls = ([f"bh:{inst.symbol}" for inst in setup.instruments]
                + [f"rc:{k}" for k in range(int(setup.thresholds["controls.random_pool"]))])

    rows: list[dict[str, Any]] = []

    def approach_row(section: str, aid: str) -> dict[str, Any]:
        a = by_id[aid]
        mine = groups.get(aid)
        record = _record(mine)
        trial = [t for t in trials if t["id"] == aid and t["admitted"]]
        score = (float(trial[-1]["metrics_t"]["sharpe"])
                 if trial and trial[-1]["metrics_t"].get("sharpe") is not None else None)
        days = [] if mine is None else list(mine["date"])
        mu_c, sd_c = stats.control_moments(records, days)
        e_n = stats.expected_max(mu_c, sd_c, n)
        return {"section": section, "subject": aid, "cell": a.meta["cell"],
                "description": a.meta["description"], "model_id": a.meta["model_id"],
                "model_version": a.meta["model_version"], "admitted": a.meta["admitted"],
                "admission_score": score, **record,
                "breakeven_cost": breakeven(sums.get(aid, [])),
                "S": record["sharpe"], "E_N": e_n, "excess": stats.excess(record["sharpe"], e_n),
                "state_history": [{"date": r["date"], "from": r["from"], "to": r["to"],
                                   "reason": r["reason"]} for r in life if r["id"] == aid]}

    def other_row(section: str, subject: str) -> dict[str, Any]:
        row: dict[str, Any] = {"section": section, "subject": subject,
                               **dict.fromkeys(_APPROACH_FIELDS),
                               **_record(groups.get(subject)), "breakeven_cost": None}
        if section == CONTROL:
            row["breakeven_cost"] = breakeven(sums.get(subject, []))
        return row

    rows += [approach_row(LIVE, aid) for _, aid in live]
    rows += [approach_row(DORMANT, aid) for aid in dormant]
    rows += [other_row(CONTROL, s) for s in controls]
    rows += [other_row(PORTFOLIO, s) for s in (paper.PORTFOLIO, paper.PORTFOLIO_CLEAN)]
    return {"track": track, "date": day.isoformat(), "N": n, "rows": rows}


def _cell(name: str, value: Any) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "-"
    if name in _REALS:
        return f"{float(value):.4f}"
    if name == "state_history":
        return "; ".join(f"{h['date']} {h['from']}>{h['to']} {h['reason']}"
                         for h in value) or "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(table: Mapping[str, Any]) -> str:
    """``table.md``: the same rows, in the same order, one Markdown table per section."""
    lines = [f"# {table['track']} {table['date']}", "", f"N: {table['N']}", ""]
    head = ("subject",) + FIELDS
    for section in SECTIONS:
        lines += [f"## {section}", "", "| " + " | ".join(head) + " |",
                  "|" + "---|" * len(head)]
        for row in table["rows"]:
            if row["section"] == section:
                lines.append("| " + " | ".join(_cell(k, row[k]) for k in head) + " |")
        lines.append("")
    return "\n".join(lines)


def write(root: Path, track: str, table: Mapping[str, Any]) -> list[Path]:
    """Write ``table.json`` and ``table.md`` under ``root`` atomically."""
    where = table_dir(root, track)
    line = ledger.line(table)
    text = (line + "\n").encode("utf-8")
    md = render(json.loads(line)).encode("utf-8")
    write_atomic(where / JSON_FILE, lambda p: p.write_bytes(text))
    write_atomic(where / MD_FILE, lambda p: p.write_bytes(md))
    return [where / JSON_FILE, where / MD_FILE]
