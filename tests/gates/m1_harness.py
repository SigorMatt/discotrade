"""Helpers of the M1 gate tests (DESIGN 18.2, 18.3 M1; decisions 2026-10-12 47,
72, 74). Not a test file: it holds no seed, no date and no assertion of an
item.

- ``gate_config(root)``: decision 72's gate configuration, a copy of
  ``tests/fixtures/config/`` under ``root`` with
  ``tests/fixtures/config/thresholds_gate.toml`` copied in, unchanged, as its
  ``thresholds.toml``.
- ``call(*argv)``: ``discotrade`` run in-process through ``discotrade.cli.main``,
  the function the console script calls; returns (status, stdout, stderr).
- ``init_state(path, as_of)``: ``discotrade init-state`` at ``as_of``.
- ``replay(state, config, track, first, last, *extra)``: ``discotrade replay``.
- ``files(root)``: every file under ``root`` but ``.git/``, with its bytes.
- ``git(repo, *args)``, ``head(repo)``, ``tree(repo)``: git on a local state
  directory with ``GIT_ALLOW_PROTOCOL=file`` (decision 47).
- ``read_paper(state, track)``: ``paper/<track>/daily.parquet`` read with
  pyarrow (not through ``paper.py``).
- ``read_jsonl(path)``: the JSON objects of a JSON lines file.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

from discotrade.cli import REPO_ROOT, main

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
GATE_THRESHOLDS = FIXTURE_CONFIG / "thresholds_gate.toml"


def gate_config(root: Path) -> Path:
    path = Path(root) / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copyfile(GATE_THRESHOLDS, path / "thresholds.toml")
    assert (path / "thresholds.toml").read_bytes() == GATE_THRESHOLDS.read_bytes()
    return path


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:   # argparse's usage errors
            status = exc.code
    return status, out.getvalue(), err.getvalue()


def init_state(path: Path, as_of: str) -> Path:
    status, _, err = call("init-state", "--state", str(path), "--as-of", as_of)
    assert status == 0, err
    return path


def replay(state: Path, config: Path, track: str, first: date, last: date,
           *extra: str) -> tuple[int, str, str]:
    return call("--state", str(state), "--config", str(config), "--track", track, "replay",
                "--from", first.isoformat(), "--to", last.isoformat(), *extra)


def files(root: Path) -> dict[str, bytes]:
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").strip()


def tree(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD^{tree}").strip()


def read_paper(state: Path, track: str):
    return pq.read_table(Path(state) / "paper" / track / "daily.parquet").to_pandas()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines()]
