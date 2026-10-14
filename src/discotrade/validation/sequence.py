"""The validation sequence (DESIGN 12.2; decisions 97 and 98 of 2026-10-14-m12;
owner's decisions O-4, O-17, O-18; decisions 2026-10-12 22, 23, 25, 30; R-23;
I-1, I-7, I-8, I-12).

:func:`validate` runs the five stages of DESIGN 12.2 in order and stops at
the first failure, returning its stage (one of :data:`STAGES`) and an error
text under decision 95 (e); on success it returns stage 2's outcome, whose
:meth:`Outcome.result` is decision 97 (e)'s (decision 98 (d)). Every stage
runs on W of the candidate's day ``D`` (DESIGN 4.1) and reads only W's bars
and their context; nothing is written to the state directory. Nothing calls
it from ``run-day`` or ``replay`` in this step (decisions 98 (d), 99).

The pieces a stage reads:

- :class:`Submission`: a source text (or, for the in-process backend only, a
  function object) with its ``PARAMS`` and ``GRID``. :meth:`Submission.from_source`
  reads the two dict literals with :mod:`ast` (the harness never executes a
  submitted text, I-7); the text is assumed to have passed the static check.
- :class:`Context`: the state and configuration directories, the track's
  :class:`~discotrade.journal.Setup`, the day ``D`` and the sandbox backend.
  ``Context.job`` builds a job for W (``sandbox.base.build_job``, the limits
  from ``<config>/run.toml``); ``Context.windows`` reads W's bars per
  instrument for the harness's own scoring (``backtest.read_window``).
- :class:`Outcome`: either a failure (its ``stage``, one of :data:`STAGES`,
  a ``rule`` and an error text under decision 95 (e)) or success, with the
  fixed combination's ``params``, its targets and evaluations per instrument
  (what stages 3 to 5 read) and :meth:`Outcome.result`, decision 97 (e)'s
  ``grid``, ``metrics_w`` and ``adjusted_w``.

Stage 2 (:func:`dry_run_and_grid`):

(a) The combinations (:func:`combinations`) are the product of ``GRID``'s
values, keys in ``GRID``'s declaration order and each key's values in
declaration order (the first key varying slowest), the other parameters from
``PARAMS``; with no ``GRID`` the one combination is ``PARAMS``. All run in one
job on W, mode ``positions``. A failed job fails the stage ``dry_run``: the
runner's stages ``load`` and ``limit`` map to it (decision 95 (d)), its text
prefixed with ``dry_run:``. The two call-time limits (``validation.call_p95_ms``
and ``validation.call_max_ms``) are enforced only when the backend says it
enforces them, by a true attribute ``enforces_call_limits`` (the design is
silent on how a backend says so; this is the simplest reading, and no backend
of this step has it): then, per combination, over its calls on every
instrument, the 95th percentile (``numpy.percentile``, linear) above
``call_p95_ms`` fails rule ``call_p95``, else a call above ``call_max_ms``
fails rule ``call_max``. Every other backend's call times are recorded and
not read (DESIGN 12.2; I-12).

(b) The harness scores each combination's targets on W with
``backtest.score``, outside the sandbox, all combinations of an instrument in
one call, and computes the plain DESIGN 8 metrics (``metrics.compute``) and
the exposure-adjusted series at 1x and 2x (``paper.adjusted_rows``, O-4 with
``W`` the window, ``R_i(D)`` from ``paper.window_units``).

(c) :func:`fix_combination` fixes the combination with the greatest adjusted
Sharpe at 1x that is a number; on a tie the first in (a)'s order; when no
figure is a number, the first (:func:`first_greatest`; O-17, decision 97
(d)).

(e) The result: ``grid`` (``grid``: the text's ``GRID`` or None; ``fixed``: the
fixed parameters; ``results``: per combination in (a)'s order its
``params``, ``plain`` and ``adjusted``, each ``sharpe`` and ``sharpe_2x``, None
for a figure that is not a number), ``metrics_w`` (the fixed combination's
``metrics.Metrics`` on W as a dict) and ``adjusted_w`` (decision 86 (a)'s
shape: ``sharpe``, ``sharpe_2x``, ``total_return``, ``total_return_2x``, None
for not a number, and ``avg_position``, each track instrument's ``hbar_i(W)``).
Writing them to a trial row is step S3.2's (decision 99).

Stage 1 (static, DESIGN 12.1) is ``validation.static.check`` on the source
text, its rule and message the error text (``static [<rule>]: <message>``). A
submission carrying a function object (the in-process backend, unit tests
only) has no text and skips it: the design is silent, this is the simplest
reading. A text is checked before its ``PARAMS`` and ``GRID`` are read, so that
a text that does not parse fails the stage rather than the harness.

Stage 3 (:func:`determinism`, decision 98 (a)): the fixed combination runs
again on W in a new job of the same backend, mode ``positions``, and its
targets must equal stage 2's exactly (rule ``rerun``); then one job in mode
``reverse_sample`` calls the function, inside one process, on a sample of each
instrument's window bars in descending time order, and its targets must equal
stage 2's for those bars (rule ``reverse_sample``). The sample
(:func:`reverse_sample`) is at most :data:`REVERSE_SAMPLE` window bars per
instrument, drawn without replacement by ``numpy.random.default_rng`` seeded
with the integer of the first 16 hex digits of the text's sha256
(:func:`sample_seed`; a submission without a text uses the empty text's), the
instruments taken in the track's order from one generator. A job that fails
fails the stage with its rule, its text prefixed ``determinism: ``.

Stage 4 (:func:`activity`, decision 98 (b), R-1): the count, summed over the
basket, of the fixed combination's window bars with ``trade(u) >
metrics.TRADE_FLOOR`` (1e-9, decision 25) is at least
``validation.min_changes_w`` (rule ``min_changes_w``).

Stage 5 (:func:`correlation_gate`, DESIGN 12.3, decision 98 (c)): each live
and dormant approach (``correlation.compared``) is run from its frozen source
and fixed parameters on the same W through the same backend and scored by the
harness as stage 2 scores; its position series and the submission's
(``correlation.position_series``) are correlated over the same bars, and an
absolute correlation above ``validation.corr_max`` rejects the submission,
rule ``duplicate``, naming the approach ``correlation.duplicate`` picks (an id
is not a symbol or a date). An approach whose own run fails cannot be
compared: that is the harness's failure, not the submission's, and raises
:class:`ValidationError` naming the approach (the design is silent; this is
the simplest reading). The approaches' series live for one validation only.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import itertools
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from discotrade import backtest, metrics, paper
from discotrade.config import DateRange
from discotrade.journal import Setup
from discotrade.sandbox.base import Sandbox, SandboxJob, SandboxResult, build_job
from discotrade.state import Approach
from discotrade.validation import correlation, static

#: The stages of DESIGN 12.2, in order (decision 98 (d)).
STAGES = ("static", "dry_run", "determinism", "activity", "correlation")
#: The attribute by which a backend says it enforces the call-time limits.
CALL_LIMITS_FLAG = "enforces_call_limits"
#: The percentile of call times ``validation.call_p95_ms`` bounds (DESIGN 12.2).
CALL_PERCENTILE = 95.0
#: The most window bars per instrument the reverse sample calls (decision 98 (a)):
#: a constant of the procedure, not a threshold.
REVERSE_SAMPLE = 20


class ValidationError(RuntimeError):
    """A validation the harness cannot carry out (not a failure of the submission)."""


@dataclass(frozen=True)
class Submission:
    """A strategy to validate: its ``PARAMS``, its ``GRID`` (None without one)
    and its source text, or a function object for the in-process backend."""

    params: Mapping[str, Any]
    grid: Mapping[str, Sequence[Any]] | None = None
    source: str | None = None
    function: Callable[..., Any] | None = None

    @classmethod
    def from_source(cls, source: str) -> Submission:
        """The submission of ``source``, its two literals read with :mod:`ast`."""
        return cls(params=_literal(source, "PARAMS") or {},
                   grid=_literal(source, "GRID"), source=source)

    def combinations(self) -> list[dict[str, Any]]:
        return combinations(self.params, self.grid)


def _literal(source: str, name: str) -> dict[str, Any] | None:
    """The value of the module-level ``name = {...}`` of ``source``, None without one."""
    for stmt in ast.parse(source).body:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == name):
            value = ast.literal_eval(stmt.value)
            if not isinstance(value, dict):
                raise ValueError(f"{name} is not a dict literal")
            return value
    return None


def combinations(params: Mapping[str, Any], grid: Mapping[str, Sequence[Any]] | None
                 ) -> list[dict[str, Any]]:
    """Decision 97 (a)'s combinations, in its order."""
    if not grid:
        return [dict(params)]
    keys = list(grid)
    out = []
    for values in itertools.product(*(list(grid[k]) for k in keys)):
        combo = dict(params)
        combo.update(zip(keys, values, strict=True))
        out.append(combo)
    return out


@dataclass(frozen=True)
class Context:
    """Where a validation runs: W of ``day`` on ``setup``'s track, through ``backend``."""

    state_dir: Path
    config_dir: Path
    setup: Setup
    day: date
    backend: Sandbox

    @property
    def window(self) -> DateRange:
        return self.setup.track.windows(self.day).w

    def job(self, submission: Submission, param_sets: Sequence[Mapping[str, Any]], *,
            mode: str = "positions",
            samples: Mapping[str, Sequence[int]] | None = None) -> SandboxJob:
        s = self.setup
        return build_job(Path(self.state_dir), s.track, s.instruments, s.calendars,
                         self.window, param_sets=param_sets, config_dir=Path(self.config_dir),
                         source=submission.source, function=submission.function, mode=mode,
                         samples=samples)

    def windows(self) -> list[backtest.Window]:
        """W's bars of each instrument of the track, in its order, for scoring."""
        s = self.setup
        return [backtest.read_window(Path(self.state_dir), s.track, inst,
                                     s.calendars[inst.calendar], self.window,
                                     s.spread_tables.get(inst.symbol))
                for inst in s.instruments]

    def threshold(self, key: str) -> Any:
        return self.setup.thresholds[key]


@dataclass(frozen=True)
class Outcome:
    """A stage's outcome: a failure (``stage``, ``rule``, ``text``) or success.

    On success, ``params`` are the fixed parameters, ``targets`` and
    ``evaluations`` the fixed combination's per instrument (track order), and
    ``grid``, ``metrics_w`` and ``adjusted_w`` decision 97 (e)'s values."""

    stage: str | None = None
    rule: str | None = None
    text: str | None = None
    params: Mapping[str, Any] | None = None
    targets: Mapping[str, np.ndarray] = field(default_factory=dict)
    evaluations: tuple[backtest.Evaluation, ...] = ()
    grid: Mapping[str, Any] | None = None
    metrics_w: Mapping[str, Any] | None = None
    adjusted_w: Mapping[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.stage is None

    def result(self) -> dict[str, Any]:
        """Decision 97 (e)'s ``grid``, ``metrics_w`` and ``adjusted_w``."""
        if not self.ok:
            raise ValueError(f"stage {self.stage} failed; there is no result")
        return {"grid": self.grid, "metrics_w": self.metrics_w, "adjusted_w": self.adjusted_w}


def failed(stage: str, rule: str, text: str) -> Outcome:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}")
    return Outcome(stage=stage, rule=rule, text=text)


def _number(value: float) -> float | None:
    """A figure as written in a result: None for one that is not a number."""
    return None if math.isnan(value) else float(value)


def first_greatest(values: Sequence[float]) -> int:
    """The index of the greatest of ``values`` that is a number, the first on a
    tie; 0 when none is a number (decision 97 (d))."""
    best = 0
    held: float | None = None
    for k, value in enumerate(values):
        if math.isnan(value):
            continue
        if held is None or value > held:
            best, held = k, value
    return best


def _call_limits(ctx: Context, job: SandboxJob, result: SandboxResult) -> Outcome | None:
    """The call-time limits, when the backend says it enforces them (decision 97 (a))."""
    if not getattr(ctx.backend, CALL_LIMITS_FLAG, False):
        return None
    p95_ms = float(ctx.threshold("validation.call_p95_ms"))
    max_ms = float(ctx.threshold("validation.call_max_ms"))
    for p in range(len(job.param_sets)):
        times = np.concatenate([np.asarray(result.call_ms[(p, inst.symbol)], dtype=np.float64)
                                for inst in job.instruments])
        if not len(times):
            continue
        if float(np.percentile(times, CALL_PERCENTILE)) > p95_ms:
            return failed("dry_run", "call_p95",
                          f"dry_run [call_p95]: the 95th percentile of call times is above "
                          f"call_p95_ms (parameter set {p})")
        if float(np.max(times)) > max_ms:
            return failed("dry_run", "call_max",
                          f"dry_run [call_max]: a call took longer than call_max_ms "
                          f"(parameter set {p})")
    return None


def fix_combination(scored: Sequence[Sequence[backtest.Evaluation]],
                    units: Sequence[Mapping[date, float]]
                    ) -> tuple[int, list[dict[str, Any]]]:
    """O-17: the index of the combination the grid fixes, by the greatest
    exposure-adjusted Sharpe at 1x on W (decision 97 (b), (d)), and each
    combination's adjusted figures (decision 86 (a)'s keys, not-a-number kept
    as ``nan``). ``scored[k]`` is combination ``k``'s evaluations per
    instrument; ``units`` the instruments' ``R_i(D)`` in the same order."""
    figures = []
    for evaluations in scored:
        one = paper.adjusted_rows(evaluations, units, "net_1x")
        two = paper.adjusted_rows(evaluations, units, "net_2x")
        figures.append({
            "sharpe": metrics.sharpe(one), "sharpe_2x": metrics.sharpe(two),
            "total_return": metrics.total_return(one),
            "total_return_2x": metrics.total_return(two),
            "avg_position": paper.window_positions(evaluations),
        })
    return first_greatest([f["sharpe"] for f in figures]), figures


def _grid_result(submission: Submission, combos: Sequence[Mapping[str, Any]], fixed: int,
                 plain: Sequence[metrics.Metrics], adjusted: Sequence[Mapping[str, Any]]
                 ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Decision 97 (e)'s ``grid``, ``metrics_w`` and ``adjusted_w``."""
    results = [{"params": dict(c),
                "plain": {"sharpe": _number(m.sharpe), "sharpe_2x": _number(m.sharpe_2x)},
                "adjusted": {"sharpe": _number(a["sharpe"]),
                             "sharpe_2x": _number(a["sharpe_2x"])}}
               for c, m, a in zip(combos, plain, adjusted, strict=True)]
    grid = {"grid": None if submission.grid is None
            else {k: list(v) for k, v in submission.grid.items()},
            "fixed": dict(combos[fixed]), "results": results}
    chosen = adjusted[fixed]
    adjusted_w = {key: _number(chosen[key])
                  for key in ("sharpe", "sharpe_2x", "total_return", "total_return_2x")}
    adjusted_w["avg_position"] = dict(chosen["avg_position"])
    return grid, dataclasses.asdict(plain[fixed]), adjusted_w


def dry_run_and_grid(ctx: Context, submission: Submission) -> Outcome:
    """Stage 2 of DESIGN 12.2 on W of ``ctx.day`` (decision 97)."""
    combos = submission.combinations()
    job = ctx.job(submission, combos)
    result = ctx.backend.run(job)
    if result.error is not None:
        e = result.error
        text = e.text if e.stage == "dry_run" else f"dry_run: {e.text}"
        return failed("dry_run", e.rule, text)
    limited = _call_limits(ctx, job, result)
    if limited is not None:
        return limited
    windows = ctx.windows()
    units = [paper.window_units(win) for win in windows]
    scored: list[list[backtest.Evaluation]] = [[] for _ in combos]
    for win in windows:
        symbol = win.instrument.symbol
        subjects = [(f"combination-{p}", result.targets[(p, symbol)], None)
                    for p in range(len(combos))]
        for p, ev in enumerate(backtest.score(win, subjects)):
            scored[p].append(ev)
    plain = [metrics.compute([metrics.leg(ev) for ev in evs]) for evs in scored]
    fixed, adjusted = fix_combination(scored, units)
    grid, metrics_w, adjusted_w = _grid_result(submission, combos, fixed, plain, adjusted)
    return Outcome(params=dict(combos[fixed]),
                   targets={w.instrument.symbol: result.targets[(fixed, w.instrument.symbol)]
                            for w in windows},
                   evaluations=tuple(scored[fixed]), grid=grid, metrics_w=metrics_w,
                   adjusted_w=adjusted_w)


# ------------------------------------------------------------- stage 3, determinism


def sample_seed(source: str | None) -> int:
    """The integer of the first 16 hex digits of the sha256 of ``source`` (the
    empty text for None), the seed of the reverse sample (decision 98 (a))."""
    text = "" if source is None else source
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def reverse_sample(source: str | None, counts: Mapping[str, int]) -> dict[str, tuple[int, ...]]:
    """Per instrument of ``counts`` (its window bars, in the track's order), at
    most :data:`REVERSE_SAMPLE` distinct window-bar indices, in descending order."""
    rng = np.random.default_rng(sample_seed(source))
    out = {}
    for symbol, n in counts.items():
        drawn = rng.choice(int(n), size=min(REVERSE_SAMPLE, int(n)), replace=False)
        out[symbol] = tuple(sorted((int(i) for i in drawn), reverse=True))
    return out


def _first_difference(got: np.ndarray, want: np.ndarray) -> int:
    """The first index at which ``got`` and ``want`` differ (their common length
    when one is a prefix of the other)."""
    n = min(len(got), len(want))
    differ = np.flatnonzero(got[:n] != want[:n])
    return int(differ[0]) if len(differ) else n


def determinism(ctx: Context, submission: Submission, first: Outcome) -> Outcome | None:
    """Stage 3 on the fixed combination of ``first`` (decision 98 (a)); None when it passes."""
    fixed = [dict(first.params or {})]
    again = ctx.backend.run(ctx.job(submission, fixed))
    if again.error is not None:
        return failed("determinism", again.error.rule, f"determinism: {again.error.text}")
    for symbol, want in first.targets.items():
        got = np.asarray(again.targets[(0, symbol)], dtype=np.float64)
        if len(got) != len(want) or not np.array_equal(got, want):
            return failed("determinism", "rerun",
                          f"determinism [rerun]: a second run on W in a new sandbox gave "
                          f"other positions, first at window bar "
                          f"{_first_difference(got, want)}")
    samples = reverse_sample(submission.source,
                             {symbol: len(t) for symbol, t in first.targets.items()})
    back = ctx.backend.run(ctx.job(submission, fixed, mode="reverse_sample", samples=samples))
    if back.error is not None:
        return failed("determinism", back.error.rule, f"determinism: {back.error.text}")
    for symbol, want in first.targets.items():
        called = np.asarray(back.bars[(0, symbol)], dtype=np.int64)
        got = np.asarray(back.targets[(0, symbol)], dtype=np.float64)
        for i, value in zip(called, got, strict=True):
            if value != want[int(i)]:
                return failed("determinism", "reverse_sample",
                              f"determinism [reverse_sample]: calling a sample of bars in "
                              f"reverse order inside one process gave another position at "
                              f"window bar {int(i)} (the function keeps state between calls)")
    return None


# ------------------------------------------------------------- stage 4, activity


def changes(evaluations: Sequence[backtest.Evaluation]) -> int:
    """The window bars with ``trade(u) > metrics.TRADE_FLOOR``, summed over the basket."""
    return sum(int((ev.rows["trade"].to_numpy(dtype=np.float64) > metrics.TRADE_FLOOR).sum())
               for ev in evaluations)


def activity(ctx: Context, first: Outcome) -> Outcome | None:
    """Stage 4 on the fixed combination of ``first`` (decision 98 (b)); None when it passes."""
    needed = int(ctx.threshold("validation.min_changes_w"))
    made = changes(first.evaluations)
    if made < needed:
        return failed("activity", "min_changes_w",
                      f"activity [min_changes_w]: {made} position changes on W summed over "
                      f"the basket; at least min_changes_w ({needed}) are needed")
    return None


# ------------------------------------------------------------- stage 5, the correlation gate


def approach_series(ctx: Context, approach: Approach,
                    windows: Sequence[backtest.Window]) -> np.ndarray:
    """``approach``'s position series on W, from its frozen source and fixed
    parameters, run through ``ctx.backend`` and scored as stage 2 scores."""
    sub = Submission(params=dict(approach.params), source=approach.source)
    result = ctx.backend.run(ctx.job(sub, [sub.params]))
    if result.error is not None:
        raise ValidationError(f"approach {approach.id} could not be run on W for the "
                              f"correlation gate: {result.error.text}")
    evaluations = [backtest.score(win, [(approach.id,
                                         result.targets[(0, win.instrument.symbol)], None)])[0]
                   for win in windows]
    return correlation.position_series(evaluations)


def correlation_gate(ctx: Context, first: Outcome) -> Outcome | None:
    """Stage 5 on the fixed combination of ``first`` (DESIGN 12.3, decision 98 (c));
    None when it passes."""
    approaches = correlation.compared(Path(ctx.state_dir), ctx.setup.track.name, ctx.day)
    if not approaches:
        return None
    windows = ctx.windows()
    others = {a.id: approach_series(ctx, a, windows) for a in approaches}
    named = correlation.duplicate(correlation.position_series(first.evaluations), others,
                                  float(ctx.threshold("validation.corr_max")))
    if named is not None:
        return failed("correlation", "duplicate",
                      f"correlation [duplicate]: the position series on W has an absolute "
                      f"correlation above corr_max with approach {named[0]}")
    return None


# ------------------------------------------------------------- the sequence


def validate(ctx: Context, submission: Submission | str) -> Outcome:
    """The five stages of DESIGN 12.2 in order on ``submission`` (a source text
    or a :class:`Submission`), stopping at the first failure (decision 98 (d))."""
    source = submission if isinstance(submission, str) else submission.source
    if source is not None:
        refusal = static.check(source, ctx.setup.thresholds)
        if refusal is not None:
            return failed("static", refusal.rule, f"static [{refusal.rule}]: {refusal.message}")
    if isinstance(submission, str):
        submission = Submission.from_source(submission)
    first = dry_run_and_grid(ctx, submission)
    if not first.ok:
        return first
    for stage in (lambda: determinism(ctx, submission, first),
                  lambda: activity(ctx, first),
                  lambda: correlation_gate(ctx, first)):
        out = stage()
        if out is not None:
            return out
    return first
