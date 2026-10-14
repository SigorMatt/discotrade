"""The container backend, its image and ``discotrade sandbox build`` (DESIGN 12.4, 3,
18.1; decision 102 of 2026-10-14-m13; decisions 47, 95, 96, 97 (a), 98 (c); I-7,
I-11, I-13, I-14; REVIEW-12 notes 5 and 6).

Tests marked ``container`` start containers of the image of the current tag,
which ``discotrade sandbox build`` built beforehand as a setup step: no test
builds it, and every container runs with ``--network none``. Outside a gate
such a test skips, printing its reason, when no runtime is found or the image
is not present (``tests/conftest.py``); under ``DISCOTRADE_GATE=1`` that skip
fails. Each container test mounts only a job directory under its pytest
temporary directory, and the ``backend`` fixture asserts, after the test, that
no container the test's backends started remains, removing by name any that
does.

Windows: the comparison with the in-process runner and the short runs use
``test_mixed`` over seven trading dates around SYNA's June roll (as
``tests/test_sandbox_process.py``); the call-time limits and the correlation
stage run on ``test_synth``'s own W of ``DAY`` (433 window bars per
instrument) at the production thresholds of ``config/thresholds.toml``
(``call_p95_ms`` 50, ``call_max_ms`` 500, ``corr_max`` 0.7). The endless
loop, the output cap and the memory bomb run under a configuration copied
under the test's temporary directory whose ``run.toml`` holds a shorter limit
(said in each test). Elapsed time decides only the endless loop's kill and
the call-time stages; no test asserts a measured time (I-12).

Seeds: the synthetic bars come from the fixture records' seeds, written here
(``MIXED_SEEDS``, ``SYNTH_SEEDS``) and checked against them. No random draw is
made here. Every git the correlation test runs (``init-state``,
``state.commit``) is on local paths with ``GIT_ALLOW_PROTOCOL=file`` (decision
47); the only subprocesses this file starts itself are scratch pytest runs of
``tests/conftest.py`` with this interpreter.
"""

import importlib.metadata
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import tomllib
from datetime import UTC, date, datetime

import numpy as np
import pytest
from error_texts import assert_clean, forbidden_words

from discotrade import state as state_mod
from discotrade.cli import REPO_ROOT, main
from discotrade.clock import FixedClock
from discotrade.config import DateRange, load_calendar, load_run, load_track_config
from discotrade.journal import Setup
from discotrade.sandbox import container, runner
from discotrade.sandbox.base import (
    SandboxRefused,
    SandboxUnavailable,
    build_job,
    job_arrays,
    job_doc,
    result_from_doc,
)
from discotrade.sandbox.container import ContainerSandbox
from discotrade.validation import sequence
from discotrade.validation.sequence import Context, Submission

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
REFERENCE = REPO_ROOT / "reference"
TREND = REFERENCE / "trend_ma.py"
MIXED = "test_mixed"
MIXED_SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
MIXED_AS_OF = "2019-06-21T00:00:00+00:00"
#: Seven trading dates; SYNA rolls inside (2019-06-14).
WINDOW = DateRange(date(2019, 6, 11), date(2019, 6, 18))
#: One trading date, for the short runs.
SHORT = DateRange(date(2019, 6, 17), date(2019, 6, 17))
SYNTH = "test_synth"
SYNTH_SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
SYNTH_AS_OF = "2019-07-25T00:00:00+00:00"
#: The day D (a Monday): W is 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
COMMIT_CLOCK = FixedClock(datetime(2019, 7, 25, tzinfo=UTC))
ADMITTED = date(2019, 7, 1)
#: Each reference strategy with a second parameter set taken from its GRID.
REFERENCES = {
    "trend_ma.py": {"fast": 12, "slow": 192},
    "zscore_reversal.py": {"lookback": 24, "entry": 1.0},
    "hour_of_day.py": {"start_hour": 8, "end_hour": 20},
}
TREND_PARAMS = {"fast": 24, "slow": 96}
FAKE_KEY = "DISCOTRADE_TEST_FAKE_API_KEY"
#: The bound on a run that could hang (seconds of the test's own timeout).
BOUND = 180.0
#: A text that is in no file of this repository: trend_ma.py with a comment added.
NOT_A_REPOSITORY_FILE = "\n# written by a worker; no file of the repository holds this text\n"


# ------------------------------------------------------------------ helpers


def copy_config(tmp_path_factory, **values):
    """``tests/fixtures/config/`` copied under tmp with ``config/thresholds.toml``
    (the production thresholds); ``[sandbox]`` values replaced by ``values``."""
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    if values:
        with open(FIXTURE_CONFIG / "run.toml", "rb") as f:
            sandbox = tomllib.load(f)["sandbox"]
        sandbox.update(values)
        (path / "run.toml").write_text(
            "[sandbox]\n" + "".join(f"{k} = {v!r}\n" for k, v in sandbox.items()),
            encoding="utf-8")
    return path


def bounded(fn):
    """``fn()``'s value, run in a daemon thread joined for at most ``BOUND`` seconds."""
    box = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - handed back to the test
            box["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(BOUND)
    assert not thread.is_alive(), f"the backend did not return within {BOUND} s"
    if "error" in box:
        raise box["error"]
    return box["value"]


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory)


@pytest.fixture(scope="module")
def tc(config):
    return load_track_config(config, MIXED)


@pytest.fixture(scope="module")
def calendars(config):
    return {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def mixed_state(tmp_path_factory, config):
    path = tmp_path_factory.mktemp("mixed") / "state"
    path.mkdir()
    assert main(["--state", str(path), "--config", str(config), "--track", MIXED,
                 "--as-of", MIXED_AS_OF, "bars", "fetch"]) == 0
    return path


def job_for(state, tc, calendars, config, source, param_sets, window=WINDOW,
            instruments=None):
    return build_job(state, tc.track, instruments or tc.instruments, calendars, window,
                     source=source, param_sets=param_sets, config_dir=config)


@pytest.fixture
def backend(tmp_path):
    """A factory of container backends whose job directories are under ``tmp_path``.
    After the test, no container any of them started remains (removed by name if one
    does, and the test then fails)."""
    made = []

    def make(config_dir):
        b = ContainerSandbox(tmp_path / f"scratch-{len(made)}", config_dir)
        made.append(b)
        return b

    yield make
    left = []
    for b in made:
        for name in b.started:
            if container.container_exists(b.runtime(), name):
                left.append(name)
                container.remove(b.runtime(), name)
    assert left == [], f"containers left behind: {left}"


def assert_no_container_of(b):
    assert b.started, "the backend started no container"
    assert [n for n in b.started if container.container_exists(b.runtime(), n)] == []


# ------------------------------------------------------------------ fixtures' facts


def test_the_synthetic_seeds_are_the_ones_written_here(tc, config):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == MIXED_SEEDS
    synth = load_track_config(config, SYNTH)
    assert {i.symbol: i.source.get("seed") for i in synth.instruments} == SYNTH_SEEDS
    w = synth.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)


# ------------------------------------------------------------------ the image's inputs and tag


def copy_inputs(root):
    """Every input of the image copied under ``root``, at its repository path."""
    for rel in container.IMAGE_INPUTS.values():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, root / rel)
    return root


def test_the_tag_is_the_image_name_and_12_hex_digits_of_the_inputs_hash():
    s = load_run(REPO_ROOT / "config").sandbox
    ref = container.image_ref(s.image)
    name, tag = ref.split(":")
    assert name == s.image == "discotrade-sandbox"
    assert re.fullmatch(r"[0-9a-f]{12}", tag)
    assert tag == container.inputs_digest(REPO_ROOT)[:12]


def test_the_tag_changes_when_the_copied_runner_changes_and_no_build_is_made(tmp_path):
    root = copy_inputs(tmp_path / "copy")
    before = container.image_tag(root)
    assert before == container.image_tag(REPO_ROOT)  # a pure function of the inputs
    runner_copy = root / "src" / "discotrade" / "sandbox" / "runner.py"
    runner_copy.write_text(runner_copy.read_text(encoding="utf-8") + "\n# changed\n",
                           encoding="utf-8")
    assert container.image_tag(root) != before
    for rel in ("src/discotrade/indicators.py", "sandbox/Dockerfile",
                "sandbox/requirements.txt", "sandbox/package_init.py"):
        other = copy_inputs(tmp_path / rel.replace("/", "_"))
        (other / rel).write_bytes((other / rel).read_bytes() + b"\n")
        assert container.image_tag(other) != before, rel


def test_the_image_inputs_are_the_definition_the_pins_the_runner_and_the_library():
    assert sorted(container.IMAGE_INPUTS.values()) == [
        "sandbox/Dockerfile", "sandbox/package_init.py", "sandbox/requirements.txt",
        "src/discotrade/indicators.py", "src/discotrade/sandbox/runner.py"]
    assert sorted(p.name for p in (REPO_ROOT / "sandbox").iterdir()) == [
        "Dockerfile", "package_init.py", "requirements.txt"]


def test_the_base_image_is_pinned_by_digest_at_the_projects_minor_version():
    text = (REPO_ROOT / "sandbox" / "Dockerfile").read_text(encoding="utf-8")
    froms = re.findall(r"^FROM (\S+)", text, flags=re.M)
    assert len(froms) == 1
    m = re.fullmatch(r"python:(\d+)\.(\d+)\.\d+-slim@sha256:([0-9a-f]{64})", froms[0])
    assert m, froms[0]
    assert (int(m[1]), int(m[2])) == sys.version_info[:2]


def _locked(name):
    with open(REPO_ROOT / "uv.lock", "rb") as f:
        lock = tomllib.load(f)
    return [p for p in lock["package"] if p["name"] == name]


def test_numpy_and_pandas_are_pinned_to_the_versions_uv_lock_holds():
    text = (REPO_ROOT / "sandbox" / "requirements.txt").read_text(encoding="utf-8")
    pins = dict(re.findall(r"^([a-z0-9-]+)==(\S+)", text, flags=re.M))
    assert sorted(pins) == ["numpy", "pandas", "python-dateutil", "six"]
    for name, version in pins.items():
        locked = _locked(name)
        assert version in [p["version"] for p in locked], name
        # The version uv installed for this interpreter, the image's minor version.
        assert version == importlib.metadata.version(name), name
        entry = next(p for p in locked if p["version"] == version)
        hashes = re.findall(rf"^{re.escape(name)}==.*?(?=^\S|\Z)", text, flags=re.M | re.S)
        for digest in re.findall(r"sha256:[0-9a-f]{64}", hashes[0]):
            assert digest in [w["hash"] for w in entry["wheels"]], (name, digest)
    assert "pyarrow" not in pins and "httpx" not in pins


# ------------------------------------------------------------------ the options


def test_one_function_builds_the_options_of_decision_102_b(tmp_path, monkeypatch, config):
    monkeypatch.setenv(FAKE_KEY, "fake-key-not-a-secret")
    s = load_run(config).sandbox
    limits = build_limits(config)
    job_dir = tmp_path / "input"
    cmd = container.run_command("/usr/bin/docker", "discotrade-sandbox:0123456789ab",
                                "discotrade-job-x", job_dir, limits, s, container.RUNNER_ARGV)
    assert cmd[:2] == ["/usr/bin/docker", "run"]
    image_at = cmd.index("discotrade-sandbox:0123456789ab")
    options, argv = cmd[2:image_at], cmd[image_at + 1:]
    assert argv == ["python", "-I", "-m", "discotrade.sandbox.runner", "/job"]

    def values(flag):
        return [options[i + 1] for i, o in enumerate(options) if o == flag]

    assert values("--network") == ["none"]
    assert "--read-only" in options
    assert values("--tmpfs") == [f"/tmp:rw,nosuid,nodev,noexec,size={s.tmpfs_bytes}"]
    assert values("--user") == [container.CONTAINER_USER] and container.CONTAINER_USER != "0:0"
    assert values("--cap-drop") == ["ALL"]
    assert values("--security-opt") == ["no-new-privileges"]
    assert values("--pids-limit") == [str(s.pids)]
    assert values("--memory") == values("--memory-swap") == [str(limits.memory_bytes)]
    assert values("--cpus") == [f"{s.cpus:g}"]
    assert values("--mount") == [f"type=bind,source={job_dir},target=/job,readonly"]
    assert "--volume" not in options and "-v" not in options
    assert values("--name") == ["discotrade-job-x"]
    assert values("--pull") == ["never"]
    env = values("--env")
    assert env == [f"{k}={v}" for k, v in container.CONTAINER_ENV.items()]
    assert not any(FAKE_KEY in o for o in cmd)
    assert "--env-file" not in options and "--rm" not in options


def build_limits(config):
    from discotrade.sandbox.base import limits_from_config
    return limits_from_config(config)


def test_the_runtime_command_gets_no_key_from_the_harness(monkeypatch):
    monkeypatch.setenv(FAKE_KEY, "fake-key-not-a-secret")
    env = container.runtime_env()
    assert FAKE_KEY not in env
    assert set(env) <= {"PATH", *container.RUNTIME_ENV_NAMES}


def stub(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")  # found, never run
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_the_runtime_is_the_named_one_or_the_first_of_docker_and_podman(tmp_path,
                                                                        monkeypatch):
    both, only_podman = tmp_path / "both", tmp_path / "podman"
    stub(both, "docker"), stub(both, "podman"), stub(only_podman, "podman")
    monkeypatch.setenv("PATH", str(both))
    assert container.find_runtime(None) == str(both / "docker")
    assert container.find_runtime("podman") == str(both / "podman")
    monkeypatch.setenv("PATH", str(only_podman))
    assert container.find_runtime(None) == str(only_podman / "podman")
    with pytest.raises(SandboxUnavailable, match="docker"):
        container.find_runtime("docker")


def test_with_no_runtime_found_the_backend_raises_the_harness_error(
        tmp_path, monkeypatch, mixed_state, tc, calendars, config):
    job = job_for(mixed_state, tc, calendars, config, TREND.read_text(encoding="utf-8"),
                  [TREND_PARAMS], window=SHORT)
    monkeypatch.setenv("PATH", "")
    b = ContainerSandbox(tmp_path / "scratch", config)
    with pytest.raises(SandboxUnavailable, match="no container runtime found") as info:
        b.run(job)
    assert not isinstance(info.value, SandboxRefused)  # never a rejection of the text
    assert "docker" in str(info.value) and "podman" in str(info.value)
    assert b.started == [] and not (tmp_path / "scratch").exists()  # nothing written


def test_sandbox_build_with_no_runtime_exits_1_naming_it(monkeypatch, capsys):
    monkeypatch.setenv("PATH", "")
    assert main(["sandbox", "build"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no container runtime found" in captured.err


def test_a_job_carrying_a_function_object_is_refused(tmp_path, mixed_state, tc, calendars,
                                                     config):
    job = build_job(mixed_state, tc.track, tc.instruments, calendars, SHORT,
                    function=lambda bars, params: 0.0, param_sets=[{}], config_dir=config)
    with pytest.raises(SandboxRefused) as info:
        ContainerSandbox(tmp_path, config).run(job)
    assert info.value.rule == "function"


def test_the_backend_says_it_enforces_the_call_time_limits(tmp_path, config):
    assert getattr(ContainerSandbox(tmp_path, config), sequence.CALL_LIMITS_FLAG) is True


# ------------------------------------------------------------------ the skip rule


CONTAINER_TEST = """
import pytest

@pytest.mark.container
def test_needs_a_container():
    pass

def test_plain():
    pass
"""


def scratch_pytest(tmp_path, gate):
    """A scratch suite (the repository's tests/conftest.py and one ``container``
    test) run with this interpreter and an empty ``PATH``, so that no runtime is
    found; under ``DISCOTRADE_GATE=1`` when ``gate``."""
    shutil.copy(REPO_ROOT / "tests" / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "test_scratch.py").write_text(CONTAINER_TEST, encoding="utf-8")
    env = {"PATH": "", "GIT_ALLOW_PROTOCOL": "file"}
    if gate:
        env["DISCOTRADE_GATE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider",
         str(tmp_path)],
        capture_output=True, text=True, cwd=tmp_path, env=env, timeout=120)


def test_a_container_test_skips_printing_its_reason_when_no_runtime_is_found(tmp_path):
    proc = scratch_pytest(tmp_path, gate=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 passed, 1 skipped" in proc.stdout
    assert re.search(r"SKIPPED \[1\] .*no container runtime found", proc.stdout), proc.stdout


def test_under_discotrade_gate_that_skip_is_a_failure(tmp_path):
    proc = scratch_pytest(tmp_path, gate=True)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    last = proc.stdout.splitlines()[-1]
    assert "skipped" not in last and "1 passed" in last
    assert "DISCOTRADE_GATE" in proc.stdout and "no container runtime found" in proc.stdout


def test_the_skip_reason_names_sandbox_build_when_the_image_is_absent(tmp_path, monkeypatch):
    # A runtime is found (a stub, never run: the image check is replaced), but the
    # image of the current tag is not present.
    monkeypatch.setenv("PATH", str(stub(tmp_path / "bin", "docker").parent))
    monkeypatch.setattr(container, "image_present", lambda runtime, ref: False)
    reason = container.unavailable(REPO_ROOT / "config")
    assert reason is not None and "discotrade sandbox build" in reason
    assert container.image_ref("discotrade-sandbox") in reason


# ------------------------------------------------------------------ in the container


@pytest.mark.container
def test_sandbox_build_prints_the_present_tag_and_builds_nothing(capsys):
    assert main(["sandbox", "build"]) == 0
    out = capsys.readouterr().out
    assert out == container.image_ref("discotrade-sandbox") + "\n"


IMAGE_REPORT = r"""
import importlib.util, json, os, sys
import numpy, pandas
import discotrade, discotrade.indicators
site = os.path.dirname(discotrade.__file__)
files = sorted(os.path.relpath(os.path.join(d, f), site) for d, _, fs in os.walk(site)
               for f in fs if f.endswith(".py"))
print(json.dumps({
    "numpy": numpy.__version__, "pandas": pandas.__version__,
    "pyarrow": importlib.util.find_spec("pyarrow") is not None,
    "httpx": importlib.util.find_spec("httpx") is not None,
    "pip": importlib.util.find_spec("pip") is not None,
    "indicators": discotrade.indicators.__file__, "files": files,
    "version": list(sys.version_info[:2]), "uid": os.getuid(), "gid": os.getgid(),
}))
"""


@pytest.mark.container
def test_the_image_holds_numpy_and_pandas_at_the_locked_versions_and_no_pyarrow_or_httpx(
        tmp_path, backend, config):
    import json

    b = backend(config)
    job_dir = tmp_path / "empty"
    job_dir.mkdir()
    run = b.run_program(["python", "-I", "-c", IMAGE_REPORT], job_dir, build_limits(config))
    assert run.breach is None and run.returncode == 0, run
    report = json.loads(run.out.decode("utf-8"))
    assert report["pyarrow"] is False and report["httpx"] is False and report["pip"] is False
    assert report["numpy"] == importlib.metadata.version("numpy")
    assert report["pandas"] == importlib.metadata.version("pandas")
    assert report["version"] == list(sys.version_info[:2])
    assert report["indicators"].endswith("/site-packages/discotrade/indicators.py")
    assert report["files"] == ["__init__.py", "indicators.py", "sandbox/__init__.py",
                               "sandbox/runner.py"]
    assert report["uid"] != 0 and report["gid"] != 0
    assert_no_container_of(b)


@pytest.mark.container
@pytest.mark.parametrize("name", sorted(REFERENCES))
def test_the_reference_strategies_give_the_in_process_runners_targets(
        name, tmp_path, backend, mixed_state, tc, calendars, config):
    source = (REFERENCE / name).read_text(encoding="utf-8")
    params = Submission.from_source(source).params
    job = job_for(mixed_state, tc, calendars, config, source, [params, REFERENCES[name]])
    b = backend(config)
    got = bounded(lambda: b.run(job))
    assert got.ok, got.error
    doc = runner.execute(job_doc(job), [job_arrays(i) for i in job.instruments],
                         lambda: runner.load_text(source))
    want = result_from_doc(job, doc)
    assert sorted(got.targets) == sorted(want.targets)
    assert len(got.targets) == 2 * len(tc.instruments)
    for key, targets in want.targets.items():
        assert len(targets) > 50, key
        assert got.targets[key].tobytes() == targets.tobytes(), key
        assert np.array_equal(got.bars[key], want.bars[key])
        assert len(got.call_ms[key]) == len(targets)
    assert any(not np.array_equal(got.targets[(0, s)], got.targets[(1, s)])
               for s in tc.track.instruments), name
    assert_no_container_of(b)
    assert list((tmp_path / "scratch-0").iterdir()) == []  # the job's directories are removed


@pytest.mark.container
def test_a_source_text_that_is_not_a_repository_file_runs(tmp_path, backend, mixed_state, tc,
                                                          calendars, config):
    source = TREND.read_text(encoding="utf-8") + NOT_A_REPOSITORY_FILE
    job = job_for(mixed_state, tc, calendars, config, source, [TREND_PARAMS],
                  instruments=tc.instruments[:1])
    result = bounded(lambda: backend(config).run(job))
    assert result.ok, result.error
    want = runner.execute(job_doc(job), [job_arrays(i) for i in job.instruments],
                          lambda: runner.load_text(source))
    key = (0, tc.instruments[0].symbol)
    assert result.targets[key].tobytes() == result_from_doc(job, want).targets[key].tobytes()


ENV_PROBE = """
import os

PARAMS = {"probe": 0}


def position(bars, params):
    if params["probe"] == 0:
        return 1.0 if "DISCOTRADE_TEST_FAKE_API_KEY" in os.environ else 0.0
    return 1.0 if set(params["names"]) & set(os.environ) else 0.0
"""


@pytest.mark.container
def test_a_fake_key_set_in_the_parent_is_absent_in_the_container(
        monkeypatch, backend, mixed_state, tc, calendars, config):
    monkeypatch.setenv(FAKE_KEY, "fake-key-not-a-secret")
    # Every variable of the harness's environment the container has no reason to
    # hold: not one of the allow-list's, nor PATH, HOME or HOSTNAME (the image's
    # and the runtime's own).
    names = sorted(set(os.environ) - set(container.CONTAINER_ENV) - {"PATH", "HOME",
                                                                     "HOSTNAME"})
    assert FAKE_KEY in names
    job = job_for(mixed_state, tc, calendars, config, ENV_PROBE,
                  [{"probe": 0}, {"probe": 1, "names": names}], window=SHORT,
                  instruments=tc.instruments[:1])
    b = backend(config)
    result = bounded(lambda: b.run(job))
    assert result.ok, result.error
    symbol = tc.instruments[0].symbol
    assert len(result.targets[(0, symbol)]) > 0
    assert np.all(result.targets[(0, symbol)] == 0.0), "the fake key reached the container"
    assert np.all(result.targets[(1, symbol)] == 0.0), "the harness's environment reached it"
    assert_no_container_of(b)


ISOLATION_PROBE = """
import os

PARAMS = {"probe": "network"}


def _creates(path):
    try:
        with open(path, "w") as handle:
            handle.write("x")
        return True
    except OSError:
        return False


def position(bars, params):
    probe = params["probe"]
    if probe == "network":
        with open("/proc/net/route") as handle:
            routes = handle.read().splitlines()[1:]
        return 1.0 if routes or sorted(os.listdir("/sys/class/net")) != ["lo"] else 0.0
    if probe == "root":
        return 1.0 if os.getuid() == 0 or os.getgid() == 0 else 0.0
    if probe == "write":
        outside = any(_creates(p) for p in ("/x", "/usr/x", "/home/x", "/job/x"))
        return 1.0 if outside or not _creates("/tmp/x") else 0.0
    return 1.0
"""


@pytest.mark.container
def test_the_container_has_no_network_a_read_only_root_and_a_non_root_user(
        backend, mixed_state, tc, calendars, config):
    job = job_for(mixed_state, tc, calendars, config, ISOLATION_PROBE,
                  [{"probe": "network"}, {"probe": "root"}, {"probe": "write"}],
                  window=SHORT, instruments=tc.instruments[:1])
    b = backend(config)
    result = bounded(lambda: b.run(job))
    assert result.ok, result.error
    symbol = tc.instruments[0].symbol
    for p, what in enumerate(("network", "root", "write")):
        assert len(result.targets[(p, symbol)]) > 0
        assert np.all(result.targets[(p, symbol)] == 0.0), what
    assert_no_container_of(b)


@pytest.mark.container
def test_an_endless_loop_returns_limit_at_the_wall_clock_and_leaves_no_container(
        tmp_path_factory, backend, mixed_state, tc, calendars):
    # A copied run.toml with a 5-second wall-clock limit and a CPU-time limit far
    # above it, so that only the harness's kill and removal can end the loop in time.
    config = copy_config(tmp_path_factory, wall_seconds=5.0, cpu_seconds=600.0)
    source = (STRATEGIES / "endless_loop.py").read_text(encoding="utf-8")
    job = job_for(mixed_state, tc, calendars, config, source, [{"step": 1}], window=SHORT,
                  instruments=tc.instruments[:1])
    b = backend(config)
    result = bounded(lambda: b.run(job))
    assert not result.ok
    assert (result.error.stage, result.error.rule) == ("limit", "wall_clock"), result.error
    assert result.error.text.startswith("limit [wall_clock]")
    assert_no_container_of(b)
    # The harness goes on: the same backend runs the next job.
    good = job_for(mixed_state, tc, calendars, config, TREND.read_text(encoding="utf-8"),
                   [TREND_PARAMS], window=SHORT, instruments=tc.instruments[:1])
    assert bounded(lambda: b.run(good)).ok
    assert_no_container_of(b)


@pytest.mark.container
def test_an_output_over_the_cap_returns_limit(tmp_path_factory, backend, mixed_state, tc,
                                              calendars):
    # A copied run.toml with a 1000-byte output cap; the result of seven trading
    # dates on three instruments is far longer.
    config = copy_config(tmp_path_factory, output_bytes=1000)
    job = job_for(mixed_state, tc, calendars, config, TREND.read_text(encoding="utf-8"),
                  [TREND_PARAMS])
    b = backend(config)
    result = bounded(lambda: b.run(job))
    assert not result.ok
    assert (result.error.stage, result.error.rule) == ("limit", "output"), result.error
    assert_no_container_of(b)


@pytest.mark.container
def test_a_memory_bomb_returns_limit_or_a_dry_run_error(tmp_path_factory, backend,
                                                        mixed_state, tc, calendars):
    # A copied run.toml with a 256 MiB memory limit, so that the bomb is stopped
    # early whatever the machine holds.
    config = copy_config(tmp_path_factory, memory_bytes=256 * 1024 * 1024)
    source = (STRATEGIES / "memory_bomb.py").read_text(encoding="utf-8")
    job = job_for(mixed_state, tc, calendars, config, source, [{"chunk": 67108864}],
                  window=SHORT, instruments=tc.instruments[:1])
    b = backend(config)
    result = bounded(lambda: b.run(job))
    assert not result.ok
    assert result.error.stage in ("limit", "dry_run"), result.error
    assert_no_container_of(b)


# ------------------------------------------------------------------ on test_synth's own W


@pytest.fixture(scope="module")
def synth_setup(config):
    return Setup.load(config, SYNTH)


@pytest.fixture(scope="module")
def synth_state(tmp_path_factory, config):
    """A state directory with ``test_synth``'s bars, committed."""
    path = tmp_path_factory.mktemp("synth") / "state"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        assert main(["init-state", "--state", str(path), "--as-of", SYNTH_AS_OF]) == 0
        assert main(["--state", str(path), "--config", str(config), "--track", SYNTH,
                     "--as-of", SYNTH_AS_OF, "bars", "fetch"]) == 0
        state_mod.commit(path, SYNTH, DAY, COMMIT_CLOCK)
    return path


def test_the_production_call_time_thresholds_are_the_ones_written_here(synth_setup):
    assert synth_setup.thresholds["validation.call_p95_ms"] == 50
    assert synth_setup.thresholds["validation.call_max_ms"] == 500
    assert synth_setup.thresholds["validation.corr_max"] == 0.7


#: Sleeps 60 ms on every tenth call of each instrument (10% of the calls), so that
#: the 95th percentile of call times is above call_p95_ms (50 ms) and no call is
#: above call_max_ms (500 ms). It imports time: it is run past the static check.
SLOW_P95 = """
import time

PARAMS = {"pause": 0.06}
CALLS = [0]


def position(bars, params):
    CALLS[0] += 1
    if CALLS[0] % 10 == 0:
        time.sleep(params["pause"])
    return 0.0
"""


@pytest.mark.container
def test_a_slow_fixture_fails_the_dry_run_on_call_p95_at_the_production_value(
        backend, synth_state, synth_setup, config):
    b = backend(config)
    ctx = Context(synth_state, config, synth_setup, DAY, b)
    out = sequence.dry_run_and_grid(ctx, Submission.from_source(SLOW_P95))
    assert (out.stage, out.rule) == ("dry_run", "call_p95"), out.text
    assert_clean([out.text], forbidden_words(synth_state, SYNTH, SYNTH_SEEDS))
    assert_no_container_of(b)


@pytest.mark.container
def test_one_call_above_call_max_ms_fails_on_call_max_at_the_production_value(
        backend, synth_state, synth_setup, config):
    # slow_call.py: the first call of each instrument sleeps 0.6 s (above 500 ms),
    # the other calls return at once, so the 95th percentile stays below 50 ms.
    b = backend(config)
    ctx = Context(synth_state, config, synth_setup, DAY, b)
    source = (STRATEGIES / "slow_call.py").read_text(encoding="utf-8")
    out = sequence.dry_run_and_grid(ctx, Submission.from_source(source))
    assert (out.stage, out.rule) == ("dry_run", "call_max"), out.text
    assert_no_container_of(b)


@pytest.mark.container
def test_the_correlation_stage_runs_an_approach_whose_frozen_source_is_no_repository_file(
        tmp_path_factory, backend, synth_state, synth_setup, config):
    """REVIEW-12 note 5: an approach whose frozen source is a worker's text (here
    trend_ma.py with a comment added, at the flipped fixture's parameters) is run by
    the container backend in the correlation stage, and its sign-flipped duplicate
    fails stage ``correlation`` naming it."""
    path = tmp_path_factory.mktemp("approach") / "state"
    shutil.copytree(synth_state, path)
    flipped = (STRATEGIES / "trend_ma_flipped.py").read_text(encoding="utf-8")
    params = Submission.from_source(flipped).params
    aid = state_mod.write_approach(
        path, source=TREND.read_text(encoding="utf-8") + NOT_A_REPOSITORY_FILE,
        params=params, cell="trend/short", model_id="test-model",
        model_version="test-model-v0", cutoff=date(2019, 1, 1),
        description="a worker's text", profile_version="w-test", admitted=ADMITTED,
        instruments=synth_setup.instruments, spread_tables=synth_setup.spread_tables)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        assert state_mod.commit(path, SYNTH, DAY, COMMIT_CLOCK) is not None
    b = backend(config)
    out = sequence.validate(Context(path, config, synth_setup, DAY, b), flipped)
    assert (out.stage, out.rule) == ("correlation", "duplicate"), out.text
    assert out.text.endswith(f"with approach {aid}")
    assert_no_container_of(b)
