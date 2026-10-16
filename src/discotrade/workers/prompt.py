"""The prompt of a worker (DESIGN 13.4, 6, 7.3, 12.1, 12.2, 13.2, 13.3;
decision 117 (a), (b) of 2026-10-15-m14; I-8, I-10, I-13).

:func:`build` makes one user message, deterministic in its inputs, of five
parts in DESIGN 13.4's order, each under its fixed heading
(:data:`HEADINGS`, rendered by :func:`heading`), the parts separated by one
blank line and the message ending with one newline:

1. :func:`cell_line`, naming the cell's family and its holding time in bars
   (the horizon's bounds from the track), then the coordinator's brief,
   sanitized as a description is (:func:`discotrade.workers.registry.sanitize`)
   and cut to ``coordinator.brief_max_chars``;
2. a line saying what the profile is, then the W profile of the cell
   (``workers.profile``), anonymized for the call (``workers.anonymize``) and
   rendered by :func:`render_profile`: JSON, keys sorted, no whitespace, every
   float to 4 significant digits (Python's ``.4g``), a non-finite float and a
   ``None`` as ``null``;
3. the registry block (``workers.registry``) and the instruction
   :data:`ABSENT`;
4. the contract of DESIGN 6 in words (:func:`contract`): the caps read from
   the thresholds (:data:`CAPS`, written ``name = value``) and the track's
   ``history_cap_bars``; the allowed imports and the refused names and
   attributes from ``validation.static``'s own tables; the indicator function
   list from ``discotrade.indicators``' public functions, each with its
   parameters and the first line of its docstring (:func:`indicator_lines`);
   the validation of DESIGN 12.2; and the cost model of DESIGN 7.3 in words
   with one line per label (:func:`cost_lines`), the means over W's bars of
   the cost per unit traded at 1x and of its fee, half spread and slippage,
   in basis points to 4 significant digits, computed by ``discotrade.costs``'s
   functions on the bars ``backtest.read_window`` reads for W (the context
   before W feeds sigma, as in an evaluation);
5. the output format: one fenced Python block, then a one-sentence
   description on the next non-empty line.

Every instrument-keyed part uses the call's one labelling (decision 116 (a)),
in label order; no symbol, date or price appears. Readings where the
decision is silent, each the simplest: an empty sanitized brief is the line
``(none)``; the indicator lines carry each function's parameter names (and
defaults) beside its docstring line; a label with no W bar has the cost line
``not defined``. Nothing here reads a clock, the network or a secret; it reads
the state directory only.
"""

from __future__ import annotations

import inspect
import json
import math
import numbers
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from discotrade import costs, indicators
from discotrade.backtest import read_window
from discotrade.spreads import spread_ticks
from discotrade.validation import static
from discotrade.workers import anonymize, profile, registry

if TYPE_CHECKING:
    from discotrade.journal import Setup

HEADINGS = ("1. Brief", "2. W profile", "3. Registry", "4. Contract", "5. Output format")
BRIEF_KEY = "coordinator.brief_max_chars"
#: The caps of part 4, each ``validation.<name>`` of the thresholds (I-10).
CAPS = ("max_lines", "max_params", "grid_max_params", "grid_max_values", "call_p95_ms",
        "call_max_ms", "min_changes_w", "corr_max")
ABSENT = ("Propose an approach that is absent from this registry: not one of the "
          "approaches listed above, nor a variant of one of them.")
NONE = "(none)"
SIGNIFICANT = ".4g"


def heading(k: int) -> str:
    """The heading line of part ``k`` (0 to 4)."""
    return f"## {HEADINGS[k]}"


def _g(x: float) -> str:
    return format(float(x), SIGNIFICANT)


def _value(x: Any) -> str:
    return str(int(x)) if isinstance(x, numbers.Integral) else repr(float(x))


def render_profile(document: Any) -> str:
    """``document`` as JSON: keys sorted, no whitespace, floats to 4
    significant digits, a non-finite float and ``None`` as ``null``."""
    if isinstance(document, Mapping):
        items = sorted((str(k), v) for k, v in document.items())
        return "{" + ",".join(f"{json.dumps(k)}:{render_profile(v)}" for k, v in items) + "}"
    if isinstance(document, list | tuple):
        return "[" + ",".join(render_profile(v) for v in document) + "]"
    if document is None or isinstance(document, bool | str):
        return json.dumps(document)
    if isinstance(document, numbers.Integral):
        return str(int(document))
    if isinstance(document, numbers.Real):
        return _g(document) if math.isfinite(float(document)) else "null"
    raise TypeError(f"a profile holds no {type(document).__name__}")


def cell_line(track: Any, cell: tuple[str, str]) -> str:
    """Part 1's harness line: the cell's family and holding time in bars."""
    low, high = dict(track.horizons)[cell[1]]
    return (f"Cell: family {cell[0]}, horizon {cell[1]}: hold a position for "
            f"{low} to {high} bars (one bar is {track.bar_seconds} seconds).")


def brief_part(setup: Setup, cell: tuple[str, str], brief: str) -> str:
    text = registry.sanitize(brief, int(setup.thresholds[BRIEF_KEY]))
    return "\n".join((cell_line(setup.track, cell), text or NONE))


def profile_part(state_dir: Path, setup: Setup, day: date, cell: tuple[str, str],
                 call_id: str) -> str:
    doc = profile.profile(state_dir, setup.track, setup.instruments, setup.calendars, day,
                          cell)
    intro = ("The W profile of this cell, as JSON: statistics of the returns of each "
             "instrument over the devising window W, the instruments labelled A, B, ...; "
             "keys ending in _bp are in basis points; null is a statistic with too few "
             "observations; lists by hour run 0 to 23, by weekday 0 (Monday) to 6, "
             "autocorrelation by lag from 1.")
    return "\n".join((intro, render_profile(anonymize.anonymize(doc, call_id))))


def registry_part(state_dir: Path, setup: Setup, day: date, cell: tuple[str, str]) -> str:
    block = registry.registry(state_dir, setup.track, setup.thresholds, day, cell)
    return "\n".join((block, ABSENT))


def unit_costs(state_dir: Path, setup: Setup, day: date
               ) -> dict[str, tuple[float, float, float, float] | None]:
    """Per symbol, the means over W's bars of the fee, half spread, slippage
    and cost per unit traded at 1x, in basis points; None with no W bar."""
    window = setup.track.windows(day).w
    out: dict[str, tuple[float, float, float, float] | None] = {}
    for inst in setup.instruments:
        cal = setup.calendars[inst.calendar]
        win = read_window(state_dir, setup.track, inst, cal, window,
                          setup.spread_tables.get(inst.symbol))
        if win.empty:
            out[inst.symbol] = None
            continue
        bars = win.bars
        opens = bars["open"].to_numpy(dtype=np.float64)
        sigma = costs.sigma(bars["close"].to_numpy(dtype=np.float64), win.gaps)
        stamps = list(bars["ts"])
        rows = []
        for u in range(win.first, len(bars)):
            o = float(opens[u])
            ticks = spread_ticks(inst, cal, win.spread_table, stamps[u].to_pydatetime())
            fee, half = costs.fee(inst, o), costs.half_spread(inst, ticks, o)
            slip = costs.slip(inst, float(sigma[u]))
            rows.append((fee, half, slip, costs.unit_cost(fee, half, slip)))
        means = np.asarray(rows).mean(axis=0) * costs.BPS
        out[inst.symbol] = (float(means[0]), float(means[1]), float(means[2]),
                            float(means[3]))
    return out


def cost_lines(units: Mapping[str, tuple[float, float, float, float] | None],
               labelling: anonymize.Labelling) -> list[str]:
    """One line per label, in label order."""
    out = []
    for label, symbol in labelling.labels:
        u = units[symbol]
        if u is None:
            out.append(f"- {label}: mean cost per unit traded not defined (no bar in W)")
            continue
        fee, half, slip, unit = u
        out.append(f"- {label}: mean cost per unit traded {_g(unit)} bp: fee {_g(fee)} bp, "
                   f"half spread {_g(half)} bp, slippage {_g(slip)} bp")
    return out


def _signature(function: Any) -> str:
    params = []
    for p in inspect.signature(function).parameters.values():
        params.append(p.name if p.default is inspect.Parameter.empty
                      else f"{p.name}={p.default!r}")
    return ", ".join(params)


def indicator_lines() -> list[str]:
    """``discotrade.indicators``' public functions, in source order, each with
    its parameters and the first line of its docstring (DESIGN 6.3)."""
    found = [(f.__code__.co_firstlineno, name, f)
             for name, f in inspect.getmembers(indicators, inspect.isfunction)
             if f.__module__ == indicators.__name__ and not name.startswith("_")]
    return [f"- indicators.{name}({_signature(f)}): {inspect.getdoc(f).splitlines()[0]}"
            for _, name, f in sorted(found)]


def caps(setup: Setup) -> dict[str, Any]:
    """The caps part 4 states, as the validation code reads them (I-10)."""
    return {**{key: setup.thresholds[f"validation.{key}"] for key in CAPS},
            "history_cap_bars": setup.track.history_cap_bars}


def contract(setup: Setup, costs_lines: Sequence[str]) -> str:
    """Part 4: DESIGN 6's contract, the static check, the validation and the costs."""
    c = {k: _value(v) for k, v in caps(setup).items()}
    imports = ", ".join(static.MODULES)
    names = ", ".join(static.FORBIDDEN_NAMES)
    attributes = ", ".join(static.FORBIDDEN_ATTRIBUTES)
    prefixes = " or ".join(static.FORBIDDEN_PREFIXES)
    spared = ", ".join(static.ALLOWED_PREFIXED)
    lines = [
        "Write one Python source text that defines:",
        "- PARAMS: a module-level dict literal of the fixed parameters, string keys, each "
        "value an int or float literal;",
        "- GRID (optional): a module-level dict literal whose keys are keys of PARAMS and "
        "whose values are lists of numeric literals, the values the harness tries;",
        "- def position(bars, params): returning a target position in [-1.0, 1.0] for the "
        "next bar.",
        "Helper functions may be defined at module level.",
        "",
        "Caps:",
        f"- max_lines = {c['max_lines']}: the whole text has at most this many physical "
        "lines;",
        f"- max_params = {c['max_params']}: PARAMS has at most this many entries;",
        f"- grid_max_params = {c['grid_max_params']}: GRID names at most this many "
        "parameters;",
        f"- grid_max_values = {c['grid_max_values']}: each GRID list has at most this many "
        "values;",
        f"- history_cap_bars = {c['history_cap_bars']}: bars holds at most this many rows.",
        "",
        "bars is a pandas DataFrame of the most recent closed bars of one instrument, oldest "
        "first, with a plain integer index from 0 and the columns open, high, low, close, "
        "volume (float64, prices adjusted for contract rolls as of the last row) and hour, "
        "weekday (small integers: the bar's open time in its market's time zone, Monday is "
        "0). There is no date and no symbol in it. params is a dict of the parameter "
        "values. position is called once per bar, per instrument, with a fresh copy of the "
        "frame; a target computed at the close of a bar is traded at the open of the next. "
        "The result must be a finite real number in [-1, 1]; where an instrument cannot be "
        "shorted, a negative result is taken as 0. The function must be pure: no state "
        "between calls, no file, network or process access, no randomness, no clock.",
        "",
        "The text is checked before it runs, and refused for:",
        f"- an import other than {imports} (plain or aliased), or a from-import outside "
        "those three;",
        "- a class, a decorator, global, nonlocal, async, await, yield or with;",
        "- any name or attribute beginning with an underscore;",
        f"- the names {names};",
        f"- the attributes {attributes}, and any attribute beginning {prefixes} except "
        f"{spared}.",
        "",
        "The indicator library, importable as indicators (each value at row i depends only "
        "on rows up to i):",
        *indicator_lines(),
        "",
        "Validation, on W only, in a sandbox, each step ending it at the first failure:",
        f"- every call returns a finite number in range; the 95th percentile of call times "
        f"is at most call_p95_ms = {c['call_p95_ms']} and no call exceeds call_max_ms = "
        f"{c['call_max_ms']} (milliseconds); the harness scores each GRID combination on W "
        "and fixes the one with the best exposure-adjusted net Sharpe ratio at 1x;",
        "- a second run gives identical positions, and calls in another order give the same "
        "positions (no state between calls);",
        f"- at least min_changes_w = {c['min_changes_w']} position changes on W, summed over "
        "the instruments;",
        f"- an absolute correlation of its positions on W above corr_max = {c['corr_max']} "
        "with any live or dormant approach rejects it as a duplicate (a strong negative "
        "correlation counts).",
        "",
        "Costs. A trade is the change of position between two bars; each unit traded pays "
        "a fee, half the spread (at least half a tick) and slippage, a coefficient times the "
        f"sample deviation of the last {costs.SIGMA_RETURNS} bar returns. At a contract roll "
        "a carried position pays two extra trades at the full cost. Scores are taken net of "
        "costs at 1x and at 2x. Per instrument, the mean over W's bars:",
        *costs_lines,
    ]
    return "\n".join(lines)


def output_part(setup: Setup) -> str:
    cap = registry.description_cap(setup.thresholds)
    return ("Reply with one fenced Python block: a line ```python, the source text, a line "
            "```. Then, on the next non-empty line, a one-sentence description of the "
            f"approach (at most {cap} characters are kept). Only the last Python block of "
            "the reply is read.")


def build(state_dir: Path, setup: Setup, day: date, cell: tuple[str, str], brief: str,
          call_id: str) -> str:
    """The prompt of call ``call_id`` for ``cell`` on trading day ``day``."""
    cell = (cell[0], cell[1])
    state_dir = Path(state_dir)
    lab = anonymize.labelling(call_id, setup.track.instruments)
    bodies = (
        brief_part(setup, cell, brief),
        profile_part(state_dir, setup, day, cell, call_id),
        registry_part(state_dir, setup, day, cell),
        contract(setup, cost_lines(unit_costs(state_dir, setup, day), lab)),
        output_part(setup),
    )
    return "\n\n".join(f"{heading(k)}\n{body}" for k, body in enumerate(bodies)) + "\n"
