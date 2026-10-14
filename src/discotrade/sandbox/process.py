"""The child-process backend (DESIGN 12.4, 12.2; decision 96 of 2026-10-14-m12;
decision 2026-10-12 47; I-7, I-13).

Runs :mod:`discotrade.sandbox.runner` in a plain child process: the harness's
own interpreter in isolated mode (``python -I -m discotrade.sandbox.runner
<job dir>``), its working directory a scratch directory of the job, its
standard input empty and its standard error discarded. It is not a security
boundary: it exists so that long replays in tests are fast, and it runs only
a source text whose sha256 is that of a file under this repository's
``reference/`` or ``tests/fixtures/`` (:func:`discotrade.journal.trusted_hashes`,
the rule decision 48 gives the day loop); any other text is refused with
:class:`~discotrade.sandbox.base.SandboxRefused`, rule ``repository_source``,
before anything is written or started. A job carrying a function object is
refused, rule ``function``.

Limits (``[sandbox]`` of ``run.toml``, carried by the job): the address space
(``RLIMIT_AS``, ``memory_bytes``) and the CPU time (``RLIMIT_CPU``,
``cpu_seconds``) are set in the child before it runs, with core files off; the
wall-clock limit is enforced here, by killing the child's process group, and
the result read from standard output is capped at ``output_bytes``. A breach
is a result with stage ``limit``: rule ``wall_clock``, ``output``,
``cpu_time`` (the child ended by ``SIGXCPU``), ``abnormal_exit`` (any other
end that is not a clean exit, a memory exhaustion that kills the interpreter
among them) or ``unreadable_output`` (a clean exit whose output is not one
result document). Call times are recorded by the runner; nothing here enforces
them (DESIGN 12.2), and no measured time enters a result (I-12).

The child's environment is :data:`CHILD_ENV` exactly, built from no variable
of the harness's environment, so that no key reaches it (I-13). The child is a
Python program of this repository that opens no connection (decision 47).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from discotrade.journal import REPO_ROOT, TRUSTED_DIRS, trusted_hashes
from discotrade.sandbox import runner
from discotrade.sandbox.base import (
    SandboxJob,
    SandboxLimits,
    SandboxRefused,
    SandboxResult,
    result_from_doc,
    write_job,
)

#: The child's whole environment: fixed values, none taken from the harness's
#: environment. One thread per numeric library, so that the address-space and
#: CPU-time limits bound one thread of work.
CHILD_ENV: dict[str, str] = {
    "PATH": os.defpath,
    "LC_ALL": "C.UTF-8",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
}
_READ = 1 << 16


def child_env() -> dict[str, str]:
    """The environment the child is started with (I-13)."""
    return dict(CHILD_ENV)


def child_command(job_dir: Path) -> list[str]:
    """The child's command line: this interpreter, isolated, running the runner."""
    return [sys.executable, "-I", "-m", "discotrade.sandbox.runner", str(job_dir)]


def _set_limits(limits: SandboxLimits) -> None:
    """Run in the child before it executes: its resource limits."""
    cpu = limits.wall_seconds if limits.cpu_seconds is None else limits.cpu_seconds
    seconds = math.ceil(cpu)
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 1))
    resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _limit(job: SandboxJob, rule: str, what: str) -> SandboxResult:
    return result_from_doc(job, runner.error_doc("limit", rule, what))


class ProcessSandbox:
    """The child-process backend; job directories go under ``scratch``."""

    def __init__(self, scratch: Path) -> None:
        self.scratch = Path(scratch)

    def run(self, job: SandboxJob) -> SandboxResult:
        if job.source is None:
            raise SandboxRefused("function", "the child-process backend runs a source text; "
                                 "a function object runs only in the in-process backend")
        digest = hashlib.sha256(job.source.encode("utf-8")).hexdigest()
        if digest not in trusted_hashes(REPO_ROOT):
            raise SandboxRefused(
                "repository_source",
                f"the source text (sha256 {digest}) is not that of a file under the "
                f"repository's {' or '.join(d + '/' for d in TRUSTED_DIRS)} (DESIGN 12.4)")
        self.scratch.mkdir(parents=True, exist_ok=True)
        base = Path(tempfile.mkdtemp(prefix="job-", dir=self.scratch))
        try:
            job_dir = write_job(job, base / "input")
            work = base / "work"
            work.mkdir()
            return self._run_child(job, job_dir, work)
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def _run_child(self, job: SandboxJob, job_dir: Path, work: Path) -> SandboxResult:
        limits = job.limits
        proc = subprocess.Popen(
            child_command(job_dir), cwd=work, env=child_env(), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
            preexec_fn=lambda: _set_limits(limits), close_fds=True)
        # The deadline is the one measured time; it decides a kill, never a value (I-12).
        deadline = time.monotonic() + limits.wall_seconds
        out = bytearray()
        breach = None
        try:
            with selectors.DefaultSelector() as sel:
                assert proc.stdout is not None
                fd = proc.stdout.fileno()
                sel.register(fd, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        breach = "wall_clock"
                        break
                    if not sel.select(remaining):
                        continue
                    chunk = os.read(fd, _READ)
                    if not chunk:
                        break
                    out += chunk
                    if len(out) > limits.output_bytes:
                        breach = "output"
                        break
            if breach is None:
                try:
                    proc.wait(timeout=max(0.0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    breach = "wall_clock"
        finally:
            if proc.returncode is None:
                _kill(proc)
            proc.stdout.close()
        if breach == "wall_clock":
            return _limit(job, "wall_clock", "the job ran past its wall-clock limit")
        if breach == "output":
            return _limit(job, "output", "the result is longer than the output cap")
        if proc.returncode == -signal.SIGXCPU:
            return _limit(job, "cpu_time", "the job ran past its CPU-time limit")
        if proc.returncode != 0:
            return _limit(job, "abnormal_exit", "the runner ended without a result "
                          "(a resource limit, such as memory, may have stopped it)")
        try:
            doc = json.loads(out.decode("utf-8"))
            return result_from_doc(job, doc)
        except (ValueError, KeyError, TypeError, IndexError):
            return _limit(job, "unreadable_output", "the output is not one result document")


def _kill(proc: subprocess.Popen) -> None:
    """Kill the child and anything it started (its own process group), then reap it."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()
