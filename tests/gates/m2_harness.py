"""Helpers of the M2 gate tests (DESIGN 18.2, 18.3 M2; decision 106 of
2026-10-14-m13; O-22 of decisions-2026-10-15-owner; decisions 2026-10-12 47, 72).
Not a test file: it holds no seed, no date and no assertion of an item.

- ``copy_config(root, **sandbox)``: ``tests/fixtures/config/`` copied to
  ``root/config`` with ``config/thresholds.toml`` (the production thresholds,
  decision 106 (a)) as its ``thresholds.toml``; each ``sandbox`` value replaces
  the one of ``[sandbox]`` in the copied ``run.toml`` (none given: the file is
  copied unchanged).
- ``bars_state(path, config, track, as_of, day, clock)``: ``init-state`` and
  ``bars fetch`` run in-process through ``discotrade.cli.main`` at ``as_of``, then
  ``state.commit`` for ``day`` under ``clock``; git on local paths only, with
  ``GIT_ALLOW_PROTOCOL=file`` (decision 47).
- ``tree(path)``, ``head(path)``: every file's bytes under ``path`` (``.git``
  included); the commit ``HEAD`` points to.
- ``ledger_and_trials(path)``: every ledger file and every file under a
  ``trials`` directory of ``path``.
- ``bounded(fn, seconds)``: ``fn()``'s value from a daemon thread joined for at
  most ``seconds``.
- ``Backends``: a factory of container backends (``RecordingSandbox``) whose job
  directories go under a given root; each records the mode and parameter sets of
  the jobs it runs; ``left()`` names the containers any of them started that
  still exist, and ``remove_left()`` removes those by name.
"""

import shutil
import threading
import tomllib
from pathlib import Path

import pytest

from discotrade import state as state_mod
from discotrade.cli import REPO_ROOT, main
from discotrade.ledger import LEDGER_DIR
from discotrade.sandbox import container
from discotrade.sandbox.container import ContainerSandbox

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
PRODUCTION_THRESHOLDS = REPO_ROOT / "config" / "thresholds.toml"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
REJECTED = REPO_ROOT / "tests" / "fixtures" / "rejected"


def copy_config(root: Path, **sandbox) -> Path:
    path = Path(root) / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copyfile(PRODUCTION_THRESHOLDS, path / "thresholds.toml")
    if sandbox:
        with open(FIXTURE_CONFIG / "run.toml", "rb") as f:
            values = tomllib.load(f)["sandbox"]
        unknown = set(sandbox) - set(values)
        if unknown:
            raise KeyError(f"not a [sandbox] key of run.toml: {sorted(unknown)}")
        values.update(sandbox)
        (path / "run.toml").write_text(
            "[sandbox]\n" + "".join(f"{k} = {v!r}\n" for k, v in values.items()),
            encoding="utf-8")
    return path


def bars_state(path: Path, config: Path, track: str, as_of: str, day, clock) -> Path:
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        if main(["init-state", "--state", str(path), "--as-of", as_of]) != 0:
            raise RuntimeError("init-state failed")
        if main(["--state", str(path), "--config", str(config), "--track", track,
                 "--as-of", as_of, "bars", "fetch"]) != 0:
            raise RuntimeError("bars fetch failed")
        state_mod.commit(path, track, day, clock)
    return path


def commit(path: Path, track: str, day, clock):
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        return state_mod.commit(path, track, day, clock)


def tree(path: Path) -> dict[str, bytes]:
    path = Path(path)
    return {str(p.relative_to(path)): p.read_bytes()
            for p in sorted(path.rglob("*")) if p.is_file()}


def head(path: Path) -> bytes:
    ref = (Path(path) / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    if not ref.startswith("ref: "):
        raise ValueError(f"HEAD is not a ref: {ref!r}")
    return (Path(path) / ".git" / ref[len("ref: "):]).read_bytes()


def ledger_and_trials(path: Path) -> list[str]:
    path = Path(path)
    return sorted(str(p.relative_to(path)) for p in path.rglob("*")
                  if p.is_file() and (LEDGER_DIR in p.relative_to(path).parts[:1]
                                      or state_mod.TRIALS in p.relative_to(path).parts))


def bounded(fn, seconds: float):
    box: dict = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - handed back to the caller
            box["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(seconds)
    if thread.is_alive():
        raise TimeoutError(f"no return within {seconds} s")
    if "error" in box:
        raise box["error"]
    return box["value"]


class RecordingSandbox(ContainerSandbox):
    """The container backend, recording each job's mode and parameter sets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jobs: list[tuple[str, list[dict]]] = []

    def run(self, job):
        self.jobs.append((job.mode, [dict(p) for p in job.param_sets]))
        return super().run(job)

    @property
    def modes(self) -> list[str]:
        return [m for m, _ in self.jobs]


class Backends:
    """Container backends made for one test or fixture, their jobs under ``root``."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.made: list[RecordingSandbox] = []

    def make(self, config_dir: Path) -> RecordingSandbox:
        b = RecordingSandbox(self.root / f"scratch-{len(self.made)}", config_dir)
        self.made.append(b)
        return b

    @property
    def started(self) -> list[str]:
        return [n for b in self.made for n in b.started]

    def left(self) -> list[str]:
        return [n for b in self.made for n in b.started
                if container.container_exists(b.runtime(), n)]

    def remove_left(self) -> list[str]:
        left = []
        for b in self.made:
            for name in b.started:
                if container.container_exists(b.runtime(), name):
                    left.append(name)
                    container.remove(b.runtime(), name)
        return left
