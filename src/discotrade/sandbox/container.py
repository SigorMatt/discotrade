"""The container backend, its image and its tag (DESIGN 12.4, 3; decision 102 of
2026-10-14-m13; decisions 2026-10-12 47, 2026-10-14-m12 95, 96, 97 (a); I-7, I-11,
I-13, I-14).

:class:`ContainerSandbox` runs :mod:`discotrade.sandbox.runner` in one container
per job, with Docker or Podman: the runtime ``[sandbox] runtime`` of
``run.toml`` names, or, when the key is absent, the first of ``docker`` and
``podman`` found on ``PATH`` (:func:`find_runtime`). No runtime found, or no
image of the current tag, is :class:`~discotrade.sandbox.base.SandboxUnavailable`,
a harness error, never a rejection of a submission. It accepts any source text,
a worker's included (DESIGN 12.4: the only backend allowed for one), refuses a
job carrying a function object, and says it enforces the call-time limits
(``enforces_call_limits``, decision 97 (a)).

Every container is started by the command :func:`run_command` builds, the one
function that holds the options of decision 102 (b): ``--network none``; a
read-only root file system; a ``tmpfs`` at ``/tmp`` of ``tmpfs_bytes``; the
image's non-root user, also given on the command line (:data:`CONTAINER_USER`);
all capabilities dropped; no new privileges; a process limit of ``pids``; a
memory limit of ``memory_bytes`` with no swap beyond it (``--memory-swap`` equal
to it); a CPU limit of ``cpus``; a CPU-time limit of ``cpu_seconds`` and no core
files (``--ulimit``; the design is silent on these two, set because the
child-process backend sets them); the job's input directory as the only mount,
read-only, at ``/job``; an environment of :data:`CONTAINER_ENV` only, nothing
taken from the harness's environment (I-13); ``--pull never``, so that a run
never fetches an image (I-11); no log kept by the runtime; and a name the
harness chose (:attr:`ContainerSandbox.started` lists them), so that it can kill
and remove it. The harness enforces ``wall_seconds``: on expiry it removes the
container by force (which kills it). It reads standard output up to
``output_bytes`` and discards standard error, and it removes the container
after every run, whatever the outcome (no ``--rm``: the removal is the
harness's own, by name).

The runtime's command itself (not the container) is started with
:func:`runtime_env`: ``PATH`` and the few variables that tell the runtime's
client where its daemon or configuration is (:data:`RUNTIME_ENV_NAMES`), none of
which is a key. It is the one subprocess this module starts (decision 47 as
item 102 (f) extends it), and every ``run`` it starts carries ``--network
none``.

The image (decision 102 (e)) is defined under the repository's ``sandbox/``. Its
inputs are :data:`IMAGE_INPUTS`: the definition file, the pins, the package
file and the two modules copied in. Its tag is the configured ``image`` name
with, as its tag, the first 12 hex digits of a sha256 over those inputs
(:func:`inputs_digest`), so a changed runner, library or pin changes the tag.
:func:`build` (``discotrade sandbox build``) builds the image of the current
tag, or nothing when it is present. Building fetches the base image and the
packages; it is a setup step, never run by a test.

The probe (decision 103): :meth:`ContainerSandbox.run_probe` starts
``sandbox/probe.py``, copied into the image (an input of its tag), through
:meth:`ContainerSandbox.run_program` and so with exactly a job's options, its
mount the input directory of a real job. :func:`judge` is the harness's
judgement of its report; a create outside ``/tmp`` passes only when it failed
with ``EROFS``, since the container's user is not root and a create under a
writable root would fail too, with ``EACCES`` (DESIGN 18.3 G2.3: "a read-only
root"). The mount carries no timestamp (``write_job``), so "no bar after W" is
judged by count against the job the harness built, whose last bar's open time it
holds (:func:`expected_mount`), and by any open time the probe finds mounted.
:func:`selftest` is ``discotrade sandbox selftest`` and ``doctor --live
sandbox`` (L5).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, TextIO

from discotrade.config import (
    RUNTIMES,
    Calendar,
    ConfigError,
    DateRange,
    Instrument,
    SandboxSettings,
    load_calendar,
    load_run,
    load_track_config,
)
from discotrade.journal import REPO_ROOT
from discotrade.sandbox import runner
from discotrade.sandbox.base import (
    SandboxJob,
    SandboxLimits,
    SandboxRefused,
    SandboxResult,
    SandboxUnavailable,
    build_job,
    result_from_doc,
    write_job,
)

#: Every input of the image: its name in the build context, and its path in the
#: repository. The sha256 over them gives the tag.
IMAGE_INPUTS: dict[str, str] = {
    "Dockerfile": "sandbox/Dockerfile",
    "requirements.txt": "sandbox/requirements.txt",
    "package_init.py": "sandbox/package_init.py",
    "indicators.py": "src/discotrade/indicators.py",
    "runner.py": "src/discotrade/sandbox/runner.py",
    "probe.py": "sandbox/probe.py",
}
#: The image's non-root user and group (``sandbox/Dockerfile``), also given on the
#: command line.
CONTAINER_USER = "10001:10001"
#: Where the job's input directory is mounted, read-only.
MOUNT = "/job"
#: The runner's command in the container.
RUNNER_ARGV = ("python", "-I", "-m", "discotrade.sandbox.runner", MOUNT)
#: Where the probe of decision 103 lies in the image, and its command there.
PROBE_PATH = "/opt/discotrade/probe.py"
PROBE_ARGV = ("python", "-I", PROBE_PATH, MOUNT)
#: The source text of the probe's job: the probe runs no submission, but its mount
#: is the input directory of a real job, which carries a source text.
PROBE_SOURCE = "# the probe's job (DESIGN 12.4, decision 103): no submission is run\n"
#: The container's whole environment beyond the image's own: fixed values, none
#: taken from the harness's environment (I-13). One thread per numeric library.
CONTAINER_ENV: dict[str, str] = {
    "LC_ALL": "C.UTF-8",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}
#: The variables of the harness's environment the runtime's own command is given,
#: besides ``PATH``: where its daemon, context or configuration is. None is a key.
RUNTIME_ENV_NAMES = ("HOME", "XDG_RUNTIME_DIR", "DOCKER_HOST", "DOCKER_CONTEXT",
                     "DOCKER_CONFIG", "DOCKER_CERT_PATH", "DOCKER_TLS_VERIFY",
                     "CONTAINER_HOST", "CONTAINERS_CONF", "CONTAINERS_STORAGE_CONF")
#: Container names start with this; the rest is random (a name, never a result).
NAME_PREFIX = "discotrade-job-"
#: The runtime's exit status when it could not start the container at all.
_START_FAILED = 125
#: How long a runtime command other than ``run`` may take (seconds).
_COMMAND_SECONDS = 120.0
_READ = 1 << 16


# ------------------------------------------------------------------ the image


def inputs_digest(root: Path = REPO_ROOT) -> str:
    """The sha256, in hex, over every input of the image under ``root``: per input,
    in the order of its build-context name, the name, its length and its bytes."""
    digest = hashlib.sha256()
    for name in sorted(IMAGE_INPUTS):
        data = (Path(root) / IMAGE_INPUTS[name]).read_bytes()
        digest.update(f"{name}\0{len(data)}\0".encode())
        digest.update(data)
    return digest.hexdigest()


def image_tag(root: Path = REPO_ROOT) -> str:
    """The image's tag: the first 12 hex digits of :func:`inputs_digest`."""
    return inputs_digest(root)[:12]


def image_ref(image: str, root: Path = REPO_ROOT) -> str:
    """``<image>:<tag>``, the image of the current inputs."""
    return f"{image}:{image_tag(root)}"


# ------------------------------------------------------------------ the runtime


def find_runtime(configured: str | None) -> str:
    """The path of the runtime's command: ``configured`` (``docker`` or
    ``podman``) found on ``PATH``, or the first of the two found when it is None.
    None found is :class:`SandboxUnavailable`, naming what was looked for."""
    names = (configured,) if configured is not None else RUNTIMES
    for name in names:
        found = shutil.which(name)
        if found is not None:
            return found
    looked = " or ".join(names)
    raise SandboxUnavailable(f"no container runtime found: {looked} is not on PATH "
                             f"(DESIGN 12.4; [sandbox] runtime of run.toml)")


def runtime_env() -> dict[str, str]:
    """The environment of the runtime's own command (never the container's)."""
    env = {"PATH": os.environ.get("PATH", os.defpath)}
    env.update({k: os.environ[k] for k in RUNTIME_ENV_NAMES if k in os.environ})
    return env


def _runtime(runtime: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([runtime, *args], env=runtime_env(), stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=_COMMAND_SECONDS, check=False)


def image_present(runtime: str, ref: str) -> bool:
    """Whether the image ``ref`` is present in the runtime's store (nothing fetched)."""
    return _runtime(runtime, "image", "inspect", "--format", "{{.Id}}", ref).returncode == 0


def container_exists(runtime: str, name: str) -> bool:
    """Whether a container named ``name`` exists, running or not."""
    return _runtime(runtime, "container", "inspect", "--format", "{{.Id}}",
                    name).returncode == 0


def remove(runtime: str, name: str) -> None:
    """Remove the container ``name`` by force (killing it if it runs); nothing when
    there is none."""
    _runtime(runtime, "rm", "--force", name)


def unavailable(config_dir: Path = REPO_ROOT / "config", root: Path = REPO_ROOT
                ) -> str | None:
    """Why a container cannot be run now (no runtime, or no image of the current
    tag), or None when one can: the reason a ``container`` test skips (DESIGN 18.1)."""
    settings = load_run(Path(config_dir)).sandbox
    try:
        runtime = find_runtime(settings.runtime)
    except SandboxUnavailable as exc:
        return str(exc)
    ref = image_ref(settings.image, root)
    if not image_present(runtime, ref):
        return _no_image(ref)
    return None


def _no_image(ref: str) -> str:
    return f"the sandbox image {ref} is not present; build it with `discotrade sandbox build`"


# ------------------------------------------------------------------ the options


def run_command(runtime: str, ref: str, name: str, input_dir: Path, limits: SandboxLimits,
                settings: SandboxSettings, argv: Sequence[str]) -> list[str]:
    """The command that starts one container (decision 102 (b)); every run uses it."""
    source = str(Path(input_dir))
    if "," in source or "=" in source:
        raise ValueError(f"a mount source may hold no ',' or '=': {source}")
    cpu = limits.wall_seconds if limits.cpu_seconds is None else limits.cpu_seconds
    seconds = math.ceil(cpu)
    options = [
        "--name", name,
        "--pull", "never",
        "--network", "none",
        "--read-only",
        "--tmpfs", f"/tmp:rw,nosuid,nodev,noexec,size={settings.tmpfs_bytes}",
        "--user", CONTAINER_USER,
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", str(settings.pids),
        "--memory", str(limits.memory_bytes),
        "--memory-swap", str(limits.memory_bytes),
        "--cpus", f"{settings.cpus:g}",
        "--ulimit", f"cpu={seconds}:{seconds + 1}",
        "--ulimit", "core=0",
        "--log-driver", "none",
        "--mount", f"type=bind,source={source},target={MOUNT},readonly",
        "--workdir", "/tmp",
    ]
    for key, value in CONTAINER_ENV.items():
        options += ["--env", f"{key}={value}"]
    return [runtime, "run", *options, ref, *argv]


# ------------------------------------------------------------------ the backend


@dataclass(frozen=True)
class Execution:
    """One container's run: its exit status (None when the harness ended it), its
    standard output up to the cap, and the limit it breached (``wall_clock``,
    ``output``) or None."""

    returncode: int | None
    out: bytes
    breach: str | None


class ContainerSandbox:
    """The container backend; job directories go under ``scratch``, settings come
    from ``[sandbox]`` of ``<config_dir>/run.toml``, the image's inputs from ``root``."""

    #: Decision 97 (a): the dry run on this backend applies the call-time limits.
    enforces_call_limits = True

    def __init__(self, scratch: Path, config_dir: Path, root: Path = REPO_ROOT) -> None:
        self.scratch = Path(scratch)
        self.settings = load_run(Path(config_dir)).sandbox
        self.root = Path(root)
        #: The name of every container this backend started, in order.
        self.started: list[str] = []
        self._runtime: str | None = None
        self._checked: str | None = None

    @property
    def ref(self) -> str:
        return image_ref(self.settings.image, self.root)

    def runtime(self) -> str:
        """The runtime's command; :class:`SandboxUnavailable` when none is found."""
        if self._runtime is None:
            self._runtime = find_runtime(self.settings.runtime)
        return self._runtime

    def _ready(self) -> tuple[str, str]:
        runtime, ref = self.runtime(), self.ref
        if self._checked != ref:
            if not image_present(runtime, ref):
                raise SandboxUnavailable(_no_image(ref))
            self._checked = ref
        return runtime, ref

    def run(self, job: SandboxJob) -> SandboxResult:
        if job.source is None:
            raise SandboxRefused("function", "the container backend runs a source text; "
                                 "a function object runs only in the in-process backend")
        self._ready()
        self.scratch.mkdir(parents=True, exist_ok=True)
        base = Path(tempfile.mkdtemp(prefix="job-", dir=self.scratch))
        try:
            job_dir = write_job(job, base / "input")
            return self._result(job, self.run_program(RUNNER_ARGV, job_dir, job.limits))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def run_program(self, argv: Sequence[str], input_dir: Path, limits: SandboxLimits
                ) -> Execution:
        """Run ``argv`` in one container of the image with ``input_dir`` mounted
        read-only at ``/job``, under ``limits``; the container is removed after."""
        runtime, ref = self._ready()
        _readable(Path(input_dir))
        name = NAME_PREFIX + uuid.uuid4().hex[:16]
        command = run_command(runtime, ref, name, Path(input_dir), limits, self.settings,
                              argv)
        self.started.append(name)
        proc = subprocess.Popen(command, env=runtime_env(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                start_new_session=True, close_fds=True)
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
            # Whatever the outcome: the container is killed and removed by name, then
            # the runtime's command is ended and reaped.
            remove(runtime, name)
            if proc.returncode is None:
                _end(proc)
            assert proc.stdout is not None
            proc.stdout.close()
        if breach is not None:
            return Execution(None, bytes(out), breach)
        if proc.returncode == _START_FAILED:
            raise SandboxUnavailable(f"the container runtime could not start the job's "
                                     f"container (exit {_START_FAILED})")
        return Execution(proc.returncode, bytes(out), None)

    def run_probe(self, job: SandboxJob) -> dict[str, Any]:
        """Run the probe (decision 103 (a)) in one container started with exactly a
        job's options (:func:`run_command`), its mount the input directory of
        ``job``, written as for a run; return its report. A probe that gives no
        report is :class:`ProbeFailed`."""
        if job.source is None:
            raise SandboxRefused("function", "the probe's job carries a source text")
        self._ready()
        self.scratch.mkdir(parents=True, exist_ok=True)
        base = Path(tempfile.mkdtemp(prefix="probe-", dir=self.scratch))
        try:
            job_dir = write_job(job, base / "input")
            run = self.run_program(PROBE_ARGV, job_dir, job.limits)
        finally:
            shutil.rmtree(base, ignore_errors=True)
        if run.breach is not None or run.returncode != 0:
            why = run.breach or f"exit {run.returncode}"
            raise ProbeFailed(f"the probe gave no report ({why})")
        try:
            report = json.loads(run.out.decode("utf-8"))
        except ValueError as exc:
            raise ProbeFailed(f"the probe's output is not one JSON document: {exc}") from exc
        if not isinstance(report, dict):
            raise ProbeFailed("the probe's output is not a JSON object")
        return report

    def _result(self, job: SandboxJob, run: Execution) -> SandboxResult:
        if run.breach == "wall_clock":
            return _limit(job, "wall_clock", "the job ran past its wall-clock limit")
        if run.breach == "output":
            return _limit(job, "output", "the result is longer than the output cap")
        if run.returncode == 128 + signal.SIGXCPU:
            return _limit(job, "cpu_time", "the job ran past its CPU-time limit")
        if run.returncode != 0:
            return _limit(job, "abnormal_exit", "the runner ended without a result "
                          "(a resource limit, such as memory, may have stopped it)")
        if not run.out:
            return result_from_doc(job, runner.error_doc(*runner.NO_RESULT))
        try:
            return result_from_doc(job, json.loads(run.out.decode("utf-8")))
        except (ValueError, KeyError, TypeError, IndexError):
            return _limit(job, "unreadable_output", "the output is not one result document")


def _limit(job: SandboxJob, rule: str, what: str) -> SandboxResult:
    return result_from_doc(job, runner.error_doc("limit", rule, what))


def _readable(directory: Path) -> None:
    """Let the container's user read the mounted directory: directories 0755, files
    0644 (the mount is read-only whatever the modes)."""
    for path in directory.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)
    directory.chmod(0o755)


def _end(proc: subprocess.Popen) -> None:
    """End the runtime's command and anything it started, then reap it."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


# ------------------------------------------------------------------ the build


class BuildFailed(RuntimeError):
    """``sandbox build`` could not build the image; carries the command and its output."""

    def __init__(self, command: Sequence[str], output: str) -> None:
        self.command = list(command)
        self.output = output
        super().__init__(f"the image build failed: {' '.join(command)}\n{output}")


def build(settings: SandboxSettings, root: Path = REPO_ROOT) -> tuple[str, bool]:
    """Build the image of the current tag from ``root``'s inputs: ``(ref, built)``,
    ``built`` False when the image was present and nothing was built."""
    runtime = find_runtime(settings.runtime)
    ref = image_ref(settings.image, root)
    if image_present(runtime, ref):
        return ref, False
    with tempfile.TemporaryDirectory(prefix="discotrade-image-") as tmp:
        context = Path(tmp)
        for name, rel in IMAGE_INPUTS.items():
            shutil.copyfile(Path(root) / rel, context / name)
        command = [runtime, "build", "--tag", ref, "--file", str(context / "Dockerfile"),
                   str(context)]
        proc = subprocess.run(command, env=runtime_env(), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.returncode != 0:
        raise BuildFailed(command, proc.stdout.decode("utf-8", errors="replace"))
    return ref, True


# ------------------------------------------------------------------ the probe and its judgement


class ProbeFailed(RuntimeError):
    """The probe ran but gave no report the harness can read."""


#: The directories outside ``/tmp`` under which the probe tries a create, in its
#: report's order; then ``/tmp``.
OUTSIDE_TMP = ("/", "/usr", "/home", MOUNT)
#: The one error that says a create failed because the file system is read-only.
READ_ONLY = "EROFS"


@dataclass(frozen=True)
class Finding:
    """One finding of the self-test: its name, whether it passed, what was seen."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class Expected:
    """What the mount must hold for one instrument, from the job the harness built:
    ``count`` bars, ``window`` of them W's, the last opening at ``last_open``, every
    one before ``w_end``, the end of W's last trading day."""

    symbol: str
    count: int
    window: int
    last_open: datetime | None
    w_end: datetime


def expected_mount(job: SandboxJob, instruments: Sequence[Instrument],
                   calendars: dict[str, Calendar], window: DateRange) -> list[Expected]:
    """Per instrument of ``job`` (in ``instruments``' order), what its mount holds."""
    from discotrade.bars.gaps import day_end

    out = []
    for inst, ji in zip(instruments, job.instruments, strict=True):
        ts = ji.bars["ts"]
        last = None if ts.empty else ts.iloc[-1].to_pydatetime()
        out.append(Expected(ji.symbol, len(ji.bars), ji.window_bars, last,
                            day_end(calendars[inst.calendar], window.last)))
    return out


def _get(doc: Any, *keys: Any) -> Any:
    for key in keys:
        if isinstance(doc, dict):
            doc = doc.get(key)
        elif isinstance(doc, list) and isinstance(key, int) and 0 <= key < len(doc):
            doc = doc[key]
        else:
            return None
    return doc


def _instant(text: Any) -> datetime | None:
    if not isinstance(text, str):
        return None
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        return None
    return value if value.tzinfo is not None else None


def judge(report: Any, expected: Sequence[Expected]) -> list[Finding]:
    """The harness's judgement of a probe report (decision 103 (b)), one finding per
    rule, in a fixed order; a part missing or malformed fails its findings."""
    found: list[Finding] = []

    def add(name: str, ok: bool, detail: str) -> None:
        found.append(Finding(name, bool(ok), detail))

    routes = _get(report, "network", "routes")
    add("network.routes", routes == [],
        "no route in the routing table" if routes == [] else f"routes: {routes!r}")
    ifaces = _get(report, "network", "interfaces")
    add("network.interfaces", ifaces == ["lo"],
        f"interfaces present: {ifaces!r}" + ("" if ifaces == ["lo"] else ", not loopback only"))
    conn = _get(report, "network", "connect")
    failed = isinstance(conn, dict) and conn.get("connected") is False
    add("network.connect", failed,
        f"connection to {_get(conn, 'target')} " + (f"failed ({conn.get('error')})" if failed
                                                     else f"did not fail: {conn!r}"))
    creates = _get(report, "creates")
    by_dir = ({c.get("under"): c for c in creates if isinstance(c, dict)}
              if isinstance(creates, list) else {})
    for directory in OUTSIDE_TMP:
        c = by_dir.get(directory)
        ok = isinstance(c, dict) and c.get("created") is False and c.get("error") == READ_ONLY
        add(f"create {directory}", ok,
            "create failed: read-only file system" if ok else f"create was not refused as "
            f"read-only: {c!r}")
    tmp = by_dir.get("/tmp")
    ok = isinstance(tmp, dict) and tmp.get("created") is True
    add("create /tmp", ok, "create succeeded" if ok else f"create failed: {tmp!r}")
    uid, euid = _get(report, "identity", "uid"), _get(report, "identity", "euid")
    ok = all(isinstance(u, int) and not isinstance(u, bool) and u != 0 for u in (uid, euid))
    add("user.uid", ok, f"user id {uid}, effective {euid}" + ("" if ok else ", not non-root"))
    cap = _get(report, "identity", "cap_eff")
    try:
        caps = int(cap, 16) if isinstance(cap, str) else None
    except ValueError:
        caps = None
    add("user.capabilities", caps == 0,
        f"effective capability set {cap}" + (" (empty)" if caps == 0 else ", not empty"))
    mounted = _get(report, "mount", "instruments")
    mounted = mounted if isinstance(mounted, list) else None
    n = None if mounted is None else len(mounted)
    add("mount.instruments", n == len(expected),
        f"{n} instruments mounted, the job has {len(expected)}")
    for i, e in enumerate(expected):
        m = _get(mounted, i)
        count = _get(m, "count")
        arrays = _get(m, "arrays")
        latest = _get(m, "latest_open")
        problems = []
        if count != e.count or not isinstance(arrays, dict) or set(arrays.values()) != {e.count}:
            problems.append(f"{count} bars mounted, the job's window and context are {e.count}")
        if e.last_open is not None and e.last_open >= e.w_end:
            problems.append(f"the job's last bar opens {e.last_open.isoformat()}, after W")
        if latest is not None:
            at = _instant(latest)
            if at is None or at >= e.w_end:
                problems.append(f"a mounted bar opens {latest}, after W")
        detail = (f"{e.count} bars mounted ({e.window} of W, {e.count - e.window} of "
                  f"context), none after W's last day" if not problems
                  else "; ".join(problems))
        add(f"mount.{e.symbol}", not problems, detail)
    return found


def selftest(ctx: Any, out: TextIO, err: TextIO, command: str = "sandbox selftest") -> int:
    """``discotrade sandbox selftest`` (decision 103 (c)): build the job of W of
    decision 19's ``D`` on ``ctx``'s track, run the probe on it, print one line per
    finding with PASS or FAIL; exit 0 only when all pass. With no runtime or no image
    of the current tag, exit 1 naming which, starting nothing."""
    from discotrade.daily import closed_day

    def fail(why: object) -> int:
        print(f"{command}: FAIL: {why}", file=err)
        return 1

    try:
        settings = load_run(Path(ctx.config)).sandbox
        runtime = find_runtime(settings.runtime)
    except (ConfigError, SandboxUnavailable, OSError) as exc:
        return fail(exc)
    ref = image_ref(settings.image)
    if not image_present(runtime, ref):
        return fail(_no_image(ref))
    if ctx.state is None:
        return fail("no state directory (--state or $DISCOTRADE_STATE)")
    try:
        tc = load_track_config(ctx.config, ctx.track)
        calendars = {name: load_calendar(Path(ctx.config) / "calendars" / f"{name}.toml")
                     for name in sorted({i.calendar for i in tc.instruments})}
        day: date = closed_day(tc, calendars, ctx.clock.now())
        window = tc.track.windows(day).w
        job = build_job(ctx.state, tc.track, tc.instruments, calendars, window,
                        source=PROBE_SOURCE, param_sets=[{}], config_dir=Path(ctx.config))
        expected = expected_mount(job, tc.instruments, calendars, window)
    except (ConfigError, OSError, ValueError) as exc:
        return fail(exc)
    print(f"{command}: track {tc.track.name}, day {day.isoformat()}, W "
          f"{window.first.isoformat()} to {window.last.isoformat()}, image {ref}", file=out)
    with tempfile.TemporaryDirectory(prefix="discotrade-selftest-") as scratch:
        backend = ContainerSandbox(Path(scratch), Path(ctx.config))
        try:
            report = backend.run_probe(job)
        except (SandboxUnavailable, ProbeFailed, OSError) as exc:
            return fail(exc)
    findings = judge(report, expected)
    for f in findings:
        print(f"{'PASS' if f.ok else 'FAIL'} {f.name}: {f.detail}", file=out)
    bad = sum(1 for f in findings if not f.ok)
    print(f"{command}: {'FAIL' if bad else 'ok'}, {bad} of {len(findings)} findings failed",
          file=out)
    return 1 if bad else 0
