"""Helpers of the M3 gate tests (DESIGN 18.2, 18.3 M3; decision 139 of
meta/decisions/decisions-2026-10-16-m17.md; decisions 2026-10-12 40, 47, 72).
Not a test file: it holds no seed, no date and no assertion of an item.

- ``CORPUS``: ``tests/fixtures/worker_corpus/`` (decision 138); ``M3`` and
  ``M3_POOL`` its two corpora.
- ``worker_replay(root, corpus, track, init_as_of, first, last)``: decision 72's
  gate configuration under ``root`` (``m1_harness.gate_config``: the fixture
  configuration with ``thresholds_gate.toml`` copied in unchanged), a state made
  by ``init-state`` at ``init_as_of``, then ``discotrade replay`` from ``first``
  to ``last`` with the child-process backend (``--sandbox process``), the scripted
  provider over ``corpus`` (``--provider scripted:<corpus>``) and the scripted
  coordinator, run in-process through ``discotrade.cli.main``. Returns the
  state and configuration directories, the replay's exit status and output.
- ``calls``, ``trials``, ``lifecycle``, ``health``: the rows of the state's
  ``calls.jsonl``, ``trials.jsonl``, ``lifecycle.jsonl`` and health log, read as
  JSON lines (not through ``ledger``).
- ``stored(state, row)``: the stored response a call row names, as JSON.
- ``corpus_files(corpus, model)``: the response files of ``model`` in the
  corpus, in the order the scripted provider serves them (sorted names).
- ``models_toml(config)``: ``models.toml`` read with ``tomllib``.
- ``backend(root)``: the child-process backend (``ProcessSandbox``) with its job
  directories under ``root``, closed on exit.
- ``positions(box, state, config, setup, window, source, params)``: the targets
  of a source text with fixed parameters at the window bars of ``window`` (a
  ``DateRange``), from one ``positions`` job of that backend, and the bars'
  open times, per instrument in the track's order.
- ``words(text)``, ``numbers(text)``: the whole words and the whole numeric
  tokens of a text.
"""

import contextlib
import json
import re
import tomllib
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import numpy as np
from m1_harness import gate_config, init_state, replay

from discotrade.backtest import read_window
from discotrade.cli import REPO_ROOT
from discotrade.config import DateRange
from discotrade.sandbox.base import build_job
from discotrade.sandbox.process import ProcessSandbox

CORPUS = REPO_ROOT / "tests" / "fixtures" / "worker_corpus"
M3 = CORPUS / "m3"
M3_POOL = CORPUS / "m3_pool"

_WORD = re.compile(r"[A-Za-z0-9_]+")
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")


def worker_replay(root: Path, corpus: Path, track: str, init_as_of: str, first: date,
                  last: date) -> tuple[Path, Path, int, str, str]:
    root = Path(root)
    config = gate_config(root)
    state = init_state(root / "state", init_as_of)
    status, out, err = replay(state, config, track, first, last, "--sandbox", "process",
                              "--provider", f"scripted:{corpus}", "--coordinator", "scripted")
    return state, config, status, out, err


def _jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def calls(state: Path, track: str) -> list[dict]:
    return _jsonl(Path(state) / "ledger" / track / "calls.jsonl")


def trials(state: Path, track: str) -> list[dict]:
    return _jsonl(Path(state) / "ledger" / track / "trials.jsonl")


def lifecycle(state: Path, track: str) -> list[dict]:
    return _jsonl(Path(state) / "ledger" / track / "lifecycle.jsonl")


def health(state: Path, track: str) -> list[dict]:
    return _jsonl(Path(state) / "health" / f"{track}.jsonl")


def stored(state: Path, row: dict) -> dict:
    return json.loads((Path(state) / row["response"]).read_text(encoding="utf-8"))


def corpus_files(corpus: Path, model: str) -> list[Path]:
    folder = Path(corpus) / model.replace("/", "__")
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == ".md")


def models_toml(config: Path) -> dict:
    with open(Path(config) / "models.toml", "rb") as f:
        return tomllib.load(f)


@contextlib.contextmanager
def backend(root: Path) -> Iterator[ProcessSandbox]:
    box = ProcessSandbox(Path(root), fork_server=True)
    try:
        yield box
    finally:
        box.close()


def positions(box, state: Path, config: Path, setup, window: DateRange, source: str,
              params: dict) -> list[tuple[np.ndarray, np.ndarray]]:
    """(open times, targets p(t)) at ``window``'s bars, per instrument in track order."""
    job = build_job(Path(state), setup.track, setup.instruments, setup.calendars, window,
                    param_sets=[dict(params)], config_dir=Path(config), source=source)
    result = box.run(job)
    if result.error is not None:
        raise AssertionError(f"the positions job failed: {result.error.text}")
    out = []
    for inst in setup.instruments:
        win = read_window(Path(state), setup.track, inst, setup.calendars[inst.calendar],
                          window)
        out.append((win.inside["ts"].to_numpy(),
                    np.asarray(result.targets[(0, inst.symbol)], dtype=np.float64)))
    return out


def words(text: str) -> set[str]:
    return set(_WORD.findall(text))


def numbers(text: str) -> set[str]:
    return set(_NUMBER.findall(text))
