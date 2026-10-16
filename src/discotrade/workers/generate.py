"""The day's generation (DESIGN 13.4 (storage), 13.7, 10.2, 12.2, 12.3, 16.2;
R-25; decision 2026-10-16-m15 126, calling the modules of 122 to 125; decision
2026-10-12 62; I-5, I-6, I-13).

:func:`generate` makes the worker calls of one track, day ``D``, cell and brief,
given the provider, the day's pool (``workers.pool.DayPool``) with ``D``'s
trading ordinal, and a sandbox backend. It writes call rows to the ledger
location it is given (``ledger.append_calls`` with ``into``, the day's staging
directory when step S3.2b calls it) and returns a :class:`Generation`: the
validated :class:`Candidate` or None, the rows, and the health events, which
the caller appends to the health log (DESIGN 15.2: the code that detects a
condition returns the event). It writes no trial row and nothing under
``trials/`` or ``approaches/`` (decision 118 (a)).

- The model (124 (b)): ``workers.pool.model_for(pool, ordinal, cell index)``;
  an empty pool makes no call and writes nothing (its ``pool_empty`` notice is
  the pool's). A retry uses the first call's model.
- Call ids (126 (a)): :func:`call_id`, ``c`` and the first 12 hex digits of the
  sha256 of ``<track>|<D>|<attempt>``, attempts 1 and 2.
- Stored responses (126 (c); I-6, DESIGN 16.2): when
  ``responses/<track>/<D>/<call>.json`` exists under the state directory it is
  read and no call is made (nor is the budget checked: no call is made). Else
  the budget is checked, the call is made with ``max_tokens`` =
  ``budgets.worker_max_output_tokens``, and the response is written at once,
  atomically, before it is parsed, under the state directory (outside the
  staging directory): :data:`RESPONSE_KEYS`, JSON with sorted keys, no
  whitespace, one final newline. A provider failure (an exception of the
  classes the caller names in ``provider_errors``: this module imports nothing
  of ``workers.providers``, decision 122 (f)) writes a row with outcome
  ``provider_error``, no response file, and ends the generation: no retry.
- The budget (126 (b)): before a call, the day's tokens (the sum of
  ``tokens_in`` and ``tokens_out`` of the rows of ``D`` in ``calls.jsonl``,
  read from ``into`` when staged there, so staged rows and attempt 1's row
  count) plus ``budgets.worker_max_output_tokens`` above
  ``budgets.worker_tokens_per_day`` makes no call: a row with outcome
  ``budget`` and zero tokens, a ``token_budget`` health event at level
  ``alert`` (subject the track; the design is silent, the budget is the
  track's day's), and the generation ends.
- Outcomes (126 (d)): a parse failure (``workers.parse``) is
  ``invalid:parse``; a parsed source goes through ``validation.sequence.validate``
  on W of ``D``: a failure at a stage is ``invalid:<stage>``, at the
  correlation gate ``duplicate``, a pass ``trial``. A harness failure
  (``ValidationError``, ``SandboxRefused``) is raised, not recorded: it is not
  the worker's (the stored response keeps the paid call).
- The retry (126 (e), R-25: one retry in all): after ``invalid:<stage>`` or
  ``duplicate`` on attempt 1, attempt 2 sends the first prompt, the first
  response as the assistant's message, and a user message of
  :data:`RETRY_TEXT`, a blank line and the error text (DESIGN 12.2's text;
  for a duplicate, which names the approach, the limit's value is added:
  ``(corr_max = <value>)``). Attempt 2's outcome ends the generation.
- Rows (126 (f)): decision 62's keys, ``ledger.KEYS["calls"]``: ``call``,
  ``date``, ``cell`` (``family/horizon``), ``model``, ``attempt``,
  ``tokens_in``, ``tokens_out``, ``outcome`` and ``response`` (the response
  file relative to the state directory; ``null`` for a ``budget`` or
  ``provider_error`` row, which has none). A row replayed from a stored
  response carries its stored tokens (its model is the pool's, the same on a
  re-run of the day, since only rows before ``D`` decide ``D``'s pool), so a re-run appends no line
  (``ledger.append`` writes no line it holds; I-6).

Where the decision is silent, the simplest: the stored file of attempt 1 gives
attempt 2's first two messages; the response file is not compared with the
call it replaces. Nothing here reads a clock, the network or a secret, no key
is read or written, and nothing here is called from ``run-day`` or ``replay``
(decision 118 (a)).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from discotrade import ledger
from discotrade.bars.store import write_atomic
from discotrade.config import Model
from discotrade.journal import Setup
from discotrade.sandbox.base import Sandbox
from discotrade.state import HealthEvent
from discotrade.validation import sequence
from discotrade.workers import parse, profile, prompt
from discotrade.workers.pool import DayPool, model_for

RESPONSES = "responses"
ATTEMPTS = (1, 2)
TOKENS_PER_DAY = "budgets.worker_tokens_per_day"
MAX_OUTPUT = "budgets.worker_max_output_tokens"
CORR_MAX = "validation.corr_max"
TOKEN_BUDGET = "token_budget"
TRIAL, DUPLICATE, PROVIDER_ERROR, BUDGET = "trial", "duplicate", "provider_error", "budget"
#: The stored response's keys (decision 126 (c)).
RESPONSE_KEYS = ("attempt", "call", "cell", "date", "messages", "model", "model_version",
                 "raw", "text", "tokens_in", "tokens_out")
#: The fixed opening of the retry's user message (decision 126 (e)).
RETRY_TEXT = ("Your reply was refused by the validation, for the reason below. Reply once "
              "more in the output format the first message gives: one fenced Python block, "
              "then a one-sentence description. This is the last attempt.")

Cell = tuple[str, str]
Message = Mapping[str, str]


class Provider(Protocol):
    """What the generation needs of a provider (DESIGN 13.5's ``complete``)."""

    def complete(self, model: str, messages: Sequence[Message], max_tokens: int) -> Any: ...


@dataclass(frozen=True)
class Candidate:
    """A validated submission, for step S3.2b to score on T (decision 126 (f))."""

    day: date
    cell: Cell
    call: str
    source: str
    description: str
    params: Mapping[str, Any]
    grid: Mapping[str, Any] | None
    metrics_w: Mapping[str, Any] | None
    adjusted_w: Mapping[str, Any] | None
    model_id: str
    model_version: str
    cutoff: date
    profile_version: str


@dataclass(frozen=True)
class Generation:
    """The day's candidate (or None), the call rows written and the health events."""

    candidate: Candidate | None
    rows: tuple[Mapping[str, Any], ...]
    events: tuple[HealthEvent, ...]


def call_id(track: str, day: date, attempt: int) -> str:
    """``c`` and the first 12 hex digits of the sha256 of ``<track>|<D>|<attempt>``."""
    text = f"{track}|{day.isoformat()}|{attempt}"
    return "c" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def response_file(track: str, day: date, call: str) -> str:
    """``responses/<track>/<D>/<call>.json``, relative to the state directory."""
    return f"{RESPONSES}/{track}/{day.isoformat()}/{call}.json"


def response_text(doc: Mapping[str, Any]) -> str:
    """A stored response as written: JSON, keys sorted, no whitespace, a final newline."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def store(state_dir: Path, relative: str, doc: Mapping[str, Any]) -> None:
    """Write a response at once, atomically (decision 126 (c))."""
    data = response_text(doc).encode("utf-8")
    write_atomic(Path(state_dir) / relative, lambda p: p.write_bytes(data))


def day_tokens(state_dir: Path, track: str, day: date, into: Path | None) -> int:
    """The tokens in and out of the rows of ``day`` in ``calls.jsonl`` (staged rows
    included; decision 126 (b))."""
    rows = ledger.read(Path(state_dir), track, ledger.CALLS, into=into)
    return sum(int(r["tokens_in"]) + int(r["tokens_out"]) for r in rows
               if r["date"] == day.isoformat())


def retry_message(outcome: str, text: str, corr_max: Any) -> str:
    """The retry's user message: :data:`RETRY_TEXT` and the error text."""
    if outcome == DUPLICATE:
        text = f"{text} (corr_max = {corr_max})"
    return f"{RETRY_TEXT}\n\n{text}"


def _name(cell: Cell) -> str:
    return f"{cell[0]}/{cell[1]}"


def generate(state_dir: Path, setup: Setup, day: date, cell: Cell, brief: str, *,
             provider: Provider, provider_errors: tuple[type[BaseException], ...],
             pool: DayPool, ordinal: int, backend: Sandbox,
             into: Path | None = None) -> Generation:
    """The generation of ``setup``'s track for ``day`` in ``cell`` (decision 126)."""
    state_dir = Path(state_dir)
    cell = (cell[0], cell[1])
    track = setup.track.name
    model = model_for(pool, ordinal, setup.track.cell_index(*cell))
    if model is None:
        return Generation(None, (), ())
    thresholds = setup.thresholds
    max_out = int(thresholds[MAX_OUTPUT])
    limit = int(thresholds[TOKENS_PER_DAY])
    rows: list[Mapping[str, Any]] = []
    events: list[HealthEvent] = []
    messages: list[dict[str, str]] = []
    previous: Mapping[str, Any] | None = None

    def row(call: str, attempt: int, model_id: str, outcome: str, tokens_in: int,
            tokens_out: int, response: str | None) -> None:
        r = {"call": call, "date": day.isoformat(), "cell": _name(cell), "model": model_id,
             "attempt": attempt, "tokens_in": tokens_in, "tokens_out": tokens_out,
             "outcome": outcome, "response": response}
        ledger.append_calls(state_dir, track, [r], into=into)
        rows.append(r)

    for attempt in ATTEMPTS:
        call = call_id(track, day, attempt)
        relative = response_file(track, day, call)
        if attempt == 1:
            messages = [{"role": "user",
                         "content": prompt.build(state_dir, setup, day, cell, brief, call)}]
        path = state_dir / relative
        if path.exists():
            doc = json.loads(path.read_text(encoding="utf-8"))
        else:
            used = day_tokens(state_dir, track, day, into)
            if used + max_out > limit:
                row(call, attempt, model.id, BUDGET, 0, 0, None)
                events.append(HealthEvent(day, "alert", TOKEN_BUDGET, track,
                                          {"call": call, "day_tokens": used,
                                           "max_output_tokens": max_out,
                                           "tokens_per_day": limit}))
                break
            try:
                done = provider.complete(model.id, messages, max_out)
            except provider_errors:
                row(call, attempt, model.id, PROVIDER_ERROR, 0, 0, None)
                break
            doc = {"call": call, "date": day.isoformat(), "cell": _name(cell),
                   "model": model.id, "attempt": attempt, "messages": messages,
                   "text": done.text, "tokens_in": int(done.tokens_in),
                   "tokens_out": int(done.tokens_out),
                   "model_version": str(done.model_version), "raw": dict(done.raw)}
            store(state_dir, relative, doc)
        if attempt == 1:
            previous = doc
        outcome, text, candidate = _judge(state_dir, setup, day, cell, call, doc, model,
                                          backend)
        row(call, attempt, model.id, outcome, int(doc["tokens_in"]),
            int(doc["tokens_out"]), relative)
        if candidate is not None:
            return Generation(candidate, tuple(rows), tuple(events))
        assert previous is not None
        messages = [dict(m) for m in previous["messages"]] + [
            {"role": "assistant", "content": str(previous["text"])},
            {"role": "user", "content": retry_message(outcome, text,
                                                      thresholds[CORR_MAX])}]
    return Generation(None, tuple(rows), tuple(events))


def _judge(state_dir: Path, setup: Setup, day: date, cell: Cell, call: str,
           doc: Mapping[str, Any], model: Model, backend: Sandbox
           ) -> tuple[str, str, Candidate | None]:
    """The outcome of a stored response, its error text and the candidate on a pass."""
    parsed = parse.parse(str(doc["text"]), setup.thresholds)
    if isinstance(parsed, parse.Failure):
        return f"{ledger.INVALID_PREFIX}{parsed.stage}", parsed.text, None
    if setup.config_dir is None:
        raise ValueError("the setup names no configuration directory: the sandbox's "
                         "run.toml is read from it")
    ctx = sequence.Context(state_dir, Path(setup.config_dir), setup, day, backend)
    out = sequence.validate(ctx, parsed.source)
    if not out.ok:
        outcome = DUPLICATE if out.stage == "correlation" else \
            f"{ledger.INVALID_PREFIX}{out.stage}"
        return outcome, str(out.text), None
    candidate = Candidate(
        day=day, cell=cell, call=call, source=parsed.source,
        description=parsed.description, params=dict(out.params or {}), grid=out.grid,
        metrics_w=out.metrics_w, adjusted_w=out.adjusted_w, model_id=model.id,
        model_version=str(doc["model_version"]), cutoff=model.cutoff_date,
        profile_version=profile.VERSION)
    return TRIAL, "", candidate
