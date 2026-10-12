"""The three ledgers (DESIGN 10.2; decisions 2026-10-12 4, 52, 62; I-5, I-6).

``ledger/<track>/trials.jsonl``, ``calls.jsonl`` and ``lifecycle.jsonl`` under
the state directory hold one JSON object per line, keys sorted, no whitespace
(``line``). Each ledger's rows hold exactly the keys of ``KEYS``:

- ``trials``: ``date``, ``id``, ``cell``, ``model_id``, ``model_version``,
  ``cutoff``, ``code_sha256``, ``profile_version``, ``cost_model``,
  ``config_hash``, ``grid`` (the grid and its results on W), ``params``,
  ``metrics_w``, ``metrics_t``, ``admitted``, ``reason`` and ``displaced``
  (decision 62);
- ``lifecycle``: ``date``, ``id``, ``from``, ``to``, ``reason``;
- ``calls``: ``call``, ``date``, ``cell``, ``model``, ``attempt``,
  ``tokens_in``, ``tokens_out``, ``outcome`` (``trial``, ``duplicate``,
  ``invalid:<stage>``, ``provider_error`` or ``budget``) and ``response``
  (the response file), DESIGN 10.2's fields under the simplest names; its
  first caller is step S3.2.

A value is written as JSON: a date in ISO form, a tuple as a list, a numpy
scalar as the Python number, a float that is not finite as ``null`` (JSON has
no such number; the design is silent, ``null`` is the simplest strict-JSON
reading, and nothing is invented in its place).

``append(state_dir, track, name, rows, into=None)`` appends each row's line
that the ledger does not already hold (nor an earlier row of the same call)
as decision 4 appends ``gaps.jsonl``: the whole file is written beside the
old one, every earlier line byte-identical, ``fsync``-ed and renamed. With
``into`` (the day's staging directory, DESIGN 16.2) the ledger is read from
``into`` when it is staged there, else from ``state_dir``, and written under
``into`` only. A ledger whose last line is torn (no final newline) is refused,
by ``append`` and by ``read``. Returns the rows appended; nothing to append
writes nothing, so a re-run of a day appends no line (I-6).
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from discotrade.bars.store import write_atomic
from discotrade.state import StateError

LEDGER_DIR = "ledger"
TRIALS, CALLS, LIFECYCLE = "trials", "calls", "lifecycle"
KEYS: Mapping[str, tuple[str, ...]] = {
    TRIALS: ("admitted", "cell", "code_sha256", "config_hash", "cost_model", "cutoff",
             "date", "displaced", "grid", "id", "metrics_t", "metrics_w", "model_id",
             "model_version", "params", "profile_version", "reason"),
    CALLS: ("attempt", "call", "cell", "date", "model", "outcome", "response",
            "tokens_in", "tokens_out"),
    LIFECYCLE: ("date", "from", "id", "reason", "to"),
}
CALL_OUTCOMES = ("trial", "duplicate", "provider_error", "budget")
INVALID_PREFIX = "invalid:"


class LedgerError(StateError):
    """A ledger that cannot be read or appended as asked (a ``StateError``, so
    that the commands that read the state report it and exit 1)."""


def ledger_path(root: Path, track: str, name: str) -> Path:
    """``ledger/<track>/<name>.jsonl`` under ``root``."""
    if name not in KEYS:
        raise LedgerError(f"no ledger named {name!r}; the ledgers are {sorted(KEYS)}")
    return Path(root) / LEDGER_DIR / track / f"{name}.jsonl"


def _plain(value: Any) -> Any:
    if isinstance(value, bool | np.bool_):
        return bool(value)
    if isinstance(value, int | np.integer):
        return int(value)
    if isinstance(value, float | np.floating):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, str):
        return value
    raise LedgerError(f"a ledger cannot hold {value!r} ({type(value).__name__})")


def line(row: Mapping[str, Any]) -> str:
    """The row as one JSON line (no newline): keys sorted, no whitespace."""
    return json.dumps(_plain(row), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _check(name: str, row: Mapping[str, Any]) -> None:
    keys = KEYS[name]
    if set(row) != set(keys):
        raise LedgerError(f"a {name} row holds the keys {sorted(row)}, not {list(keys)}")
    if name == CALLS:
        outcome = row["outcome"]
        if not isinstance(outcome, str) or not (
                outcome in CALL_OUTCOMES
                or (outcome.startswith(INVALID_PREFIX) and len(outcome) > len(INVALID_PREFIX))):
            raise LedgerError(f"a call's outcome is one of {list(CALL_OUTCOMES)} or "
                              f"invalid:<stage>, not {outcome!r}")


def _bytes(path: Path) -> bytes:
    data = path.read_bytes() if path.exists() else b""
    if data and not data.endswith(b"\n"):
        raise LedgerError(f"{path} does not end with a newline; its last line is torn")
    return data


def read(state_dir: Path, track: str, name: str, into: Path | None = None
         ) -> list[dict[str, Any]]:
    """The rows of a ledger, in file order (from ``into`` when staged there)."""
    path = ledger_path(state_dir, track, name)
    if into is not None and ledger_path(into, track, name).exists():
        path = ledger_path(into, track, name)
    return [json.loads(x) for x in _bytes(path).decode("utf-8").splitlines()]


def append(state_dir: Path, track: str, name: str, rows: Iterable[Mapping[str, Any]],
           into: Path | None = None) -> list[Mapping[str, Any]]:
    """Append each row whose line the ledger does not hold; return those appended."""
    source = ledger_path(state_dir, track, name)
    target = source if into is None else ledger_path(into, track, name)
    old = _bytes(target if target.exists() else source)
    present = set(old.decode("utf-8").splitlines())
    appended: list[Mapping[str, Any]] = []
    lines: list[str] = []
    for row in rows:
        _check(name, row)
        text = line(row)
        if text in present:
            continue
        present.add(text)
        appended.append(row)
        lines.append(text + "\n")
    if lines:
        data = old + "".join(lines).encode("utf-8")
        write_atomic(target, lambda p: p.write_bytes(data))
    return appended


def append_calls(state_dir: Path, track: str, rows: Iterable[Mapping[str, Any]],
                 into: Path | None = None) -> list[Mapping[str, Any]]:
    """The writer of ``calls.jsonl`` (DESIGN 10.2; decision 62)."""
    return append(state_dir, track, CALLS, rows, into=into)
