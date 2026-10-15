"""The child-process backend (DESIGN 12.4, 12.2; decision 96 of 2026-10-14-m12;
decision 2026-10-12 47; I-7, I-13).

Runs :mod:`discotrade.sandbox.runner` in a plain child process: the harness's
own interpreter in isolated mode (``python -I -m discotrade.sandbox.runner
<job dir>``), its working directory a scratch directory of the job, its
standard input empty and its standard error discarded. It is not a security
boundary: it exists so that long replays in tests are fast, and it runs only
a source text whose sha256 is that of a file under this repository's
``reference/`` or ``tests/fixtures/`` (:func:`discotrade.journal.trusted_hashes`,
the rule decision 48 gives the day loop), leaving out the rejection suite's
directory :data:`REJECTED_DIR` (decision 104 (d) of 2026-10-14-m13, O-22 of
2026-10-15: no text of it ever runs here); any other text is refused with
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
result document). A clean exit with nothing on standard output is the run the
text ended before the runner wrote its result (for example by ``os._exit(0)``):
stage ``dry_run``, rule ``no_result`` (:data:`discotrade.sandbox.runner.NO_RESULT`,
decision 101 (b) of 2026-10-14-m13), never a harness failure and never a
result. Call times are recorded by the runner; nothing here enforces
them (DESIGN 12.2), and no measured time enters a result (I-12).

The child's environment is :data:`CHILD_ENV` exactly, built from no variable
of the harness's environment, so that no key reaches it (I-13). The child is a
Python program of this repository that opens no connection (decision 47).

The fork server (decision 105 (e) of 2026-10-14-m13), for the day loop only
(``ProcessSandbox(scratch, fork_server=True)``): instead of starting the
interpreter afresh for each job, the backend starts, at its first job, one
server process (:data:`SERVER_CODE`, run as ``python -I -c``, with
:data:`CHILD_ENV` and its standard input, output and error closed or
discarded) that imports only the runner's modules (:mod:`discotrade.sandbox.runner`
and what it imports) and never runs a text. For each job the backend hands it,
over a Unix-domain socket pair (no address, nothing leaves the host), the job's
input and scratch directories, its limits and the write end of a fresh pipe;
the server forks one fresh child, which starts a session of its own, sets the
CPU-time, address-space and core-file limits, points its standard input and
error at ``/dev/null`` and its standard output at the pipe, closes every other
descriptor, enters the scratch directory and runs :func:`runner.main` on the
job, then exits; a child is never reused for a second job. The backend reads
the pipe with the same wall-clock limit and output cap, kills the child's
session on a breach, and only then lets the server reap it and report its exit
status, which is judged as a plain child's is.

One server per harness process (O-20 of 2026-10-15, which changes 105 (e)'s
"one process per run of the day loop"): the server is shared by every fork-server
backend of the process. It starts on the first job and lives for the whole
``replay``, ``run-day``, ``journal recompute`` or test process; it is stopped
when that process ends (:func:`stop_server`, registered with ``atexit``; its end
of the socket pair also closes when the process dies) and by any fork-server
backend's :meth:`ProcessSandbox.close`. A server that has died (found ended
before a job, or failing a job) is started again on the next job, and
:func:`restarts` counts each such start, from which the day run writes a
health notice (:data:`discotrade.daily.SANDBOX_RESTARTED`).
"""

from __future__ import annotations

import atexit
import hashlib
import json
import math
import os
import resource
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from discotrade.journal import REPO_ROOT, TRUSTED_DIRS, trusted_hashes
from discotrade.sandbox import runner
from discotrade.sandbox.base import (
    SandboxJob,
    SandboxLimits,
    SandboxRefused,
    SandboxResult,
    SandboxUnavailable,
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
#: The rejection suite's validation fixtures (DESIGN 12.5; decision 104 (d)): under
#: ``tests/fixtures/``, yet no source this backend accepts.
REJECTED_DIR = "tests/fixtures/rejected"


def accepted_hashes(root: Path = REPO_ROOT) -> frozenset[str]:
    """The sha256 of every source text this backend accepts: the files under
    ``reference/`` and ``tests/fixtures/`` of ``root``, but :data:`REJECTED_DIR`'s."""
    return trusted_hashes(root, exclude=(REJECTED_DIR,))


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


#: The fork server's program (decision 105 (e)): it imports only the runner's
#: modules and never runs a text. Its one argument is the descriptor of its end of
#: the socket pair. Per job: a request (one JSON line carrying the write end of the
#: job's output pipe), to which it forks one child and answers its pid; ``wait``,
#: to which it answers the child's exit status once the child has ended (a negative
#: signal number when a signal ended it, as ``subprocess`` reports it) without
#: reaping it, so that its pid names it until the backend is done with it; and
#: ``reap``, to which it reaps the child and answers. When the backend's end of the
#: socket closes, it kills any child it holds and ends.
SERVER_CODE = r'''
import json, os, resource, signal, socket, sys
from discotrade.sandbox import runner

def child(req, out_fd, sock):
    code = 1
    try:
        os.setsid()
        sock.close()
        null = os.open(os.devnull, os.O_RDWR)
        os.dup2(null, 0)
        os.dup2(out_fd, 1)
        os.dup2(null, 2)
        for name in os.listdir("/proc/self/fd"):
            if int(name) > 2:
                try:
                    os.close(int(name))
                except OSError:
                    pass
        os.chdir(req["work"])
        cpu = int(req["cpu"])
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        memory = int(req["memory"])
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        code = runner.main([req["job"]])
        sys.stdout.flush()
    except BaseException:
        code = 1
    finally:
        os._exit(code)

def line(sock):
    data = b""
    while not data.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            return None
        data += chunk
    return data.strip()

def send(sock, doc):
    sock.sendall(json.dumps(doc).encode("utf-8") + b"\n")

def end(pid):
    for kill in (os.killpg, os.kill):
        try:
            kill(pid, signal.SIGKILL)
        except OSError:
            pass
    os.waitpid(pid, 0)

def serve(sock):
    while True:
        msg, fds, _, _ = socket.recv_fds(sock, 65536, 1)
        if not msg or len(fds) != 1:
            return
        req = json.loads(msg)
        pid = os.fork()
        if pid == 0:
            child(req, fds[0], sock)
        os.close(fds[0])
        send(sock, {"pid": pid})
        if line(sock) != b"wait":
            end(pid)
            return
        info = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
        exited = info.si_code == os.CLD_EXITED
        send(sock, {"status": info.si_status if exited else -info.si_status})
        if line(sock) != b"reap":
            end(pid)
            return
        os.waitpid(pid, 0)
        send(sock, {"reaped": pid})

serve(socket.socket(fileno=int(sys.argv[1])))
'''


def server_command(fd: int) -> list[str]:
    """The fork server's command line: this interpreter, isolated, running
    :data:`SERVER_CODE` with its end of the socket pair at descriptor ``fd``."""
    return [sys.executable, "-I", "-c", SERVER_CODE, str(fd)]


class _ForkServer:
    """The backend's handle on its fork server (decision 105 (e))."""

    def __init__(self) -> None:
        mine, theirs = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.proc = subprocess.Popen(
                server_command(theirs.fileno()), cwd="/", env=child_env(),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, pass_fds=(theirs.fileno(),), close_fds=True)
        except BaseException:
            mine.close()
            raise
        finally:
            theirs.close()
        self.sock = mine
        self._buf = b""

    def _line(self, timeout: float | None = None) -> dict[str, Any]:
        """The server's next answer; ``TimeoutError`` when none came in ``timeout`` s
        (a ``BlockingIOError`` of the read is that timeout, decision 111 (a) of
        2026-10-15-m14)."""
        self.sock.settimeout(timeout)
        try:
            while b"\n" not in self._buf:
                try:
                    chunk = self.sock.recv(4096)
                except BlockingIOError as exc:
                    raise TimeoutError("no answer from the fork server in time") from exc
                if not chunk:
                    raise OSError("the fork server ended")
                self._buf += chunk
        finally:
            self.sock.settimeout(None)
        line, self._buf = self._buf.split(b"\n", 1)
        doc = json.loads(line)
        if not isinstance(doc, dict):
            raise OSError("the fork server's answer is not a JSON object")
        return doc

    def start(self, job_dir: Path, work: Path, limits: SandboxLimits, out_fd: int) -> int:
        """One fresh child running the job of ``job_dir``, its standard output
        ``out_fd``; its pid."""
        cpu = limits.wall_seconds if limits.cpu_seconds is None else limits.cpu_seconds
        req = {"job": str(job_dir), "work": str(work), "cpu": math.ceil(cpu),
               "memory": int(limits.memory_bytes)}
        socket.send_fds(self.sock, [json.dumps(req).encode("utf-8") + b"\n"], [out_fd])
        return int(self._line()["pid"])

    def wait(self, timeout: float | None) -> int:
        """The child's exit status as ``Popen.returncode`` once it has ended, the
        child left unreaped; ``TimeoutError`` when it has not ended in ``timeout`` s,
        at once when ``timeout`` is at or below zero, with no read of the socket
        (decision 111 (a) of 2026-10-15-m14); the question stays asked either way:
        call :meth:`answer` after ending the child."""
        self.sock.sendall(b"wait\n")
        if timeout is not None and timeout <= 0:
            raise TimeoutError("the wall-clock limit was reached before the answer")
        return int(self._line(timeout)["status"])

    def answer(self) -> int:
        """The answer to a :meth:`wait` that timed out."""
        return int(self._line()["status"])

    def reap(self) -> None:
        """Let the server reap the ended child."""
        self.sock.sendall(b"reap\n")
        self._line()

    def close(self) -> None:
        self.sock.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


#: The process's one fork server (O-20), None before its first job and once stopped.
_SERVER: _ForkServer | None = None
#: Whether the last server ended without being stopped (it died, or failed a job).
_LOST = False
#: How many times a server was started again after one had died.
_RESTARTS = 0


def _shared_server() -> _ForkServer:
    """The process's fork server: the running one, else a new one; a new one
    replacing a server that died counts as a restart (:func:`restarts`)."""
    global _SERVER, _RESTARTS
    if _SERVER is not None and _SERVER.proc.poll() is not None:
        _discard()
    if _SERVER is None:
        _SERVER = _ForkServer()
        if _LOST:
            _RESTARTS += 1
    return _SERVER


def _discard() -> None:
    """End the server that died or failed a job; the next job starts a new one."""
    global _SERVER, _LOST
    server, _SERVER = _SERVER, None
    _LOST = True
    if server is not None:
        server.close()


def stop_server() -> None:
    """Stop the process's fork server, if one is running (at the process's end,
    and by a fork-server backend's close)."""
    global _SERVER, _LOST
    server, _SERVER = _SERVER, None
    _LOST = False
    if server is not None:
        server.close()


atexit.register(stop_server)


def server_pid() -> int | None:
    """The pid of the process's running fork server, None when none runs."""
    return None if _SERVER is None else _SERVER.proc.pid


def restarts() -> int:
    """How many times this process started a fork server again after one had died."""
    return _RESTARTS


def _launch(job_dir: Path, work: Path, limits: SandboxLimits) -> tuple[_ForkServer, int, int]:
    """The job of ``job_dir`` started by the process's fork server: the server, the
    child's pid and the read end of the child's output pipe. A server that fails to
    take the job (it died after the check of :func:`_shared_server`) is replaced
    once, the job sent again over a fresh pipe."""
    for attempt in (1, 2):
        server = _shared_server()
        read_end, write_end = os.pipe()
        try:
            pid = server.start(job_dir, work, limits, write_end)
        except OSError:
            os.close(read_end)
            _discard()
            if attempt == 2:
                raise
            continue
        finally:
            os.close(write_end)
        return server, pid, read_end
    raise AssertionError("unreachable")


def _end(pid: int) -> None:
    """Kill the unreaped child ``pid`` and its session."""
    for kill in (os.killpg, os.kill):
        try:
            kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _limit(job: SandboxJob, rule: str, what: str) -> SandboxResult:
    return result_from_doc(job, runner.error_doc("limit", rule, what))


class ProcessSandbox:
    """The child-process backend; job directories go under ``scratch``. With
    ``fork_server`` (the day loop's, decision 105 (e)) its children are forked by
    the process's one fork server (O-20), started at the first job of any such
    backend and stopped by :meth:`close` or at the process's end."""

    def __init__(self, scratch: Path, fork_server: bool = False) -> None:
        self.scratch = Path(scratch)
        self.fork_server = fork_server

    def close(self) -> None:
        """Stop the process's fork server, if this is a fork-server backend and
        one is running (:func:`stop_server`)."""
        if self.fork_server:
            stop_server()

    def run(self, job: SandboxJob) -> SandboxResult:
        if job.source is None:
            raise SandboxRefused("function", "the child-process backend runs a source text; "
                                 "a function object runs only in the in-process backend")
        digest = hashlib.sha256(job.source.encode("utf-8")).hexdigest()
        if digest not in accepted_hashes(REPO_ROOT):
            raise SandboxRefused(
                "repository_source",
                f"the source text (sha256 {digest}) is not that of a file under the "
                f"repository's {' or '.join(d + '/' for d in TRUSTED_DIRS)} outside "
                f"{REJECTED_DIR}/ (DESIGN 12.4)")
        self.scratch.mkdir(parents=True, exist_ok=True)
        base = Path(tempfile.mkdtemp(prefix="job-", dir=self.scratch))
        try:
            job_dir = write_job(job, base / "input")
            work = base / "work"
            work.mkdir()
            if self.fork_server:
                return self._run_forked(job, job_dir, work)
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
        try:
            assert proc.stdout is not None
            out, breach = _read(proc.stdout.fileno(), deadline, limits.output_bytes)
            if breach is None:
                try:
                    proc.wait(timeout=max(0.0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    breach = "wall_clock"
        finally:
            if proc.returncode is None:
                _kill(proc)
            proc.stdout.close()
        return self._judge(job, out, breach, proc.returncode)

    def _run_forked(self, job: SandboxJob, job_dir: Path, work: Path) -> SandboxResult:
        """The job run by a child of the fork server (decision 105 (e))."""
        limits = job.limits
        try:
            server, pid, read_end = _launch(job_dir, work, limits)
        except OSError as exc:
            raise SandboxUnavailable(f"the fork server of the child-process backend "
                                     f"failed: {exc}") from exc
        try:
            # The deadline is the one measured time; it decides a kill, never a value (I-12).
            deadline = time.monotonic() + limits.wall_seconds
            out, breach = _read(read_end, deadline, limits.output_bytes)
            if breach is not None:
                _end(pid)
                returncode = server.wait(None)
            else:
                try:
                    # A remaining time at or below zero is the breach (decision 111 (a)).
                    returncode = server.wait(deadline - time.monotonic())
                except TimeoutError:
                    breach = "wall_clock"
                    _end(pid)
                    returncode = server.answer()
            server.reap()
        except OSError as exc:
            _discard()
            raise SandboxUnavailable(f"the fork server of the child-process backend "
                                     f"failed: {exc}") from exc
        finally:
            os.close(read_end)
        return self._judge(job, out, breach, returncode)

    def _judge(self, job: SandboxJob, out: bytes, breach: str | None,
               returncode: int | None) -> SandboxResult:
        if breach == "wall_clock":
            return _limit(job, "wall_clock", "the job ran past its wall-clock limit")
        if breach == "output":
            return _limit(job, "output", "the result is longer than the output cap")
        if returncode == -signal.SIGXCPU:
            return _limit(job, "cpu_time", "the job ran past its CPU-time limit")
        if returncode != 0:
            return _limit(job, "abnormal_exit", "the runner ended without a result "
                          "(a resource limit, such as memory, may have stopped it)")
        if not out:
            return result_from_doc(job, runner.error_doc(*runner.NO_RESULT))
        try:
            doc = json.loads(out.decode("utf-8"))
            return result_from_doc(job, doc)
        except (ValueError, KeyError, TypeError, IndexError):
            return _limit(job, "unreadable_output", "the output is not one result document")


def _read(fd: int, deadline: float, cap: int) -> tuple[bytes, str | None]:
    """Read ``fd`` to its end, until ``deadline`` (``time.monotonic``) or past
    ``cap`` bytes; the bytes read and the breach (``wall_clock``, ``output``) or None."""
    out = bytearray()
    with selectors.DefaultSelector() as sel:
        sel.register(fd, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return bytes(out), "wall_clock"
            if not sel.select(remaining):
                continue
            chunk = os.read(fd, _READ)
            if not chunk:
                return bytes(out), None
            out += chunk
            if len(out) > cap:
                return bytes(out), "output"


def _kill(proc: subprocess.Popen) -> None:
    """Kill the child and anything it started (its own process group), then reap it."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()
