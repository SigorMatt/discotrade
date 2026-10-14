"""The child-process backend and ``config/run.toml`` (DESIGN 12.4, 3; decision 96 of
2026-10-14-m12; decision 2026-10-12 47; I-7, I-11, I-12, I-13).

The backend runs ``python -I -m discotrade.sandbox.runner <job dir>`` in a
child process; every job directory and scratch directory is under a pytest
temporary directory. The stores are filled by ``bars fetch`` on the fixture
track ``test_mixed``, run in-process (``discotrade.cli.main``) with the clock
given by ``--as-of``. Windows are short (a few trading dates) so that each run
stays quick.

Limits: the comparison with the in-process runner, the refusals and the
environment test run under the limits of ``tests/fixtures/config/run.toml``,
which are those of ``config/run.toml``. The endless loop, the output cap and
the memory bomb run under a configuration copied under the test's temporary
directory whose ``run.toml`` holds a shorter limit (said in each test). The
endless-loop test is the only one here that meets elapsed time; it asserts the
stage and the rule, never a measured time (I-12). Each run that could hang is
made in a daemon thread joined with a bound, so that a backend that failed to
kill its child fails the test instead of hanging the suite.

Seeds: the synthetic bars come from the fixture records' seeds, written here in
``SEEDS`` and checked against them. No random draw is made here.
"""

import shutil
import sys
import threading
import tomllib
from datetime import date

import numpy as np
import pytest
from error_texts import assert_clean, forbidden_words

from discotrade.cli import REPO_ROOT, main
from discotrade.config import (
    ConfigError,
    DateRange,
    load_calendar,
    load_run,
    load_track_config,
)
from discotrade.sandbox import runner
from discotrade.sandbox.base import SandboxRefused, build_job, job_arrays, job_doc, result_from_doc
from discotrade.sandbox.process import CHILD_ENV, ProcessSandbox, child_command, child_env

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
TREND = REPO_ROOT / "reference" / "trend_ma.py"
TRACK = "test_mixed"
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
AS_OF = "2019-06-21T00:00:00+00:00"
#: Seven trading dates; SYNA rolls inside (2019-06-14).
WINDOW = DateRange(date(2019, 6, 11), date(2019, 6, 18))
#: One trading date, for the runs that fail.
SHORT = DateRange(date(2019, 6, 17), date(2019, 6, 17))
#: The bound on a run that could hang (seconds of the test's own timeout).
BOUND = 120.0
FAKE_KEY = "DISCOTRADE_TEST_FAKE_API_KEY"
TREND_PARAMS = {"fast": 24, "slow": 96}


def copy_config(tmp_path_factory, run_toml: str | None = None):
    """``tests/fixtures/config/`` copied under tmp with ``config/thresholds.toml``
    (as the runner tests do); ``run.toml`` replaced by ``run_toml`` when given."""
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    if run_toml is not None:
        (path / "run.toml").write_text(run_toml, encoding="utf-8")
    return path


def short_run(**values) -> str:
    """A ``run.toml`` holding the fixture's values with ``values`` in their place."""
    with open(FIXTURE_CONFIG / "run.toml", "rb") as f:
        sandbox = tomllib.load(f)["sandbox"]
    sandbox.update(values)
    return "[sandbox]\n" + "".join(f"{k} = {v!r}\n" for k, v in sandbox.items())


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory)


@pytest.fixture(scope="module")
def tc(config):
    return load_track_config(config, TRACK)


@pytest.fixture(scope="module")
def calendars(config):
    return {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def state(tmp_path_factory, config):
    path = tmp_path_factory.mktemp("state")
    assert main(["--state", str(path), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    return path


def job_for(state, tc, calendars, config, source, param_sets, window=WINDOW,
            instruments=None):
    return build_job(state, tc.track, instruments or tc.instruments, calendars, window,
                     source=source, param_sets=param_sets, config_dir=config)


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


def test_the_synthetic_seeds_are_the_ones_written_here(tc):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS


# --- run.toml ------------------------------------------------------------------------


def test_run_toml_loads_and_the_fixture_holds_the_values_of_config():
    run = load_run(REPO_ROOT / "config")
    assert run == load_run(FIXTURE_CONFIG)
    s = run.sandbox
    assert s.wall_seconds > 0 and s.cpu_seconds > 0
    assert s.memory_bytes > 0 and s.output_bytes > 0


@pytest.mark.parametrize("text, name", [
    ("[sandbox]\nwall_seconds = 1.0\ncpu_seconds = 1.0\nmemory_bytes = 1\n"
     "output_bytes = 1\nmemroy_bytes = 2\n", "sandbox.memroy_bytes"),
    ("colour = 1\n[sandbox]\nwall_seconds = 1.0\ncpu_seconds = 1.0\nmemory_bytes = 1\n"
     "output_bytes = 1\n", "colour"),
])
def test_run_toml_refuses_an_unknown_key_naming_it(tmp_path, text, name):
    (tmp_path / "run.toml").write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match=f"unknown key '{name}'"):
        load_run(tmp_path)


def test_run_toml_loads_the_container_keys_of_decision_102_d():
    for where in (REPO_ROOT / "config", FIXTURE_CONFIG):
        s = load_run(where).sandbox
        assert s.image == "discotrade-sandbox"
        assert s.pids >= 1 and s.cpus > 0 and s.tmpfs_bytes >= 1
        assert s.runtime is None  # absent: the first of docker and podman found on PATH
    with open(FIXTURE_CONFIG / "run.toml", "rb") as f:
        keys = set(tomllib.load(f)["sandbox"])
    assert {"image", "pids", "cpus", "tmpfs_bytes"} <= keys


@pytest.mark.parametrize("values, name, why", [
    ({"runtime": "lxc"}, "sandbox.runtime", "must be one of docker, podman"),
    ({"image": "discotrade-sandbox:latest"}, "sandbox.image", "must be an image repository"),
    ({"pids": 0}, "sandbox.pids", "must be at least 1"),
    ({"cpus": 0.0}, "sandbox.cpus", "must be positive"),
    ({"tmpfs_bytes": 0}, "sandbox.tmpfs_bytes", "must be at least 1"),
])
def test_run_toml_refuses_a_bad_container_value_naming_it(tmp_path, values, name, why):
    (tmp_path / "run.toml").write_text(short_run(**values), encoding="utf-8")
    with pytest.raises(ConfigError, match=f"'{name}' {why}"):
        load_run(tmp_path)


def test_run_toml_accepts_a_named_runtime(tmp_path):
    (tmp_path / "run.toml").write_text(short_run(runtime="podman"), encoding="utf-8")
    assert load_run(tmp_path).sandbox.runtime == "podman"


def test_job_building_refuses_a_configuration_without_run_toml(tmp_path_factory, state, tc,
                                                               calendars):
    config = copy_config(tmp_path_factory)
    (config / "run.toml").unlink()
    with pytest.raises(ConfigError, match="run.toml"):
        job_for(state, tc, calendars, config, TREND.read_text(encoding="utf-8"), [{}])


def test_job_building_reads_its_limits_from_run_toml(state, tc, calendars, config):
    job = job_for(state, tc, calendars, config, TREND.read_text(encoding="utf-8"), [{}],
                  window=SHORT)
    s = load_run(config).sandbox
    assert (job.limits.wall_seconds, job.limits.cpu_seconds, job.limits.memory_bytes,
            job.limits.output_bytes) == (s.wall_seconds, s.cpu_seconds, s.memory_bytes,
                                         s.output_bytes)


@pytest.mark.parametrize("where", ["config", "fixtures"])
def test_config_check_still_passes(tmp_path_factory, capsys, where):
    if where == "config":
        args = ["--config", str(REPO_ROOT / "config")]
    else:
        args = ["--config", str(copy_config(tmp_path_factory)), "--track", TRACK]
    assert main([*args, "config", "check"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert any(line.startswith("run: sandbox") for line in out)
    assert any(line.startswith("run: container image discotrade-sandbox") for line in out)
    assert out[-1].startswith("config check: ok")


# --- the backend ---------------------------------------------------------------------


def test_the_child_is_this_interpreter_in_isolated_mode(tmp_path):
    command = child_command(tmp_path)
    assert command[:5] == [sys.executable, "-I", "-m", "discotrade.sandbox.runner",
                           str(tmp_path)]


def test_trend_ma_gives_the_targets_of_the_in_process_runner(tmp_path, state, tc, calendars,
                                                             config):
    source = TREND.read_text(encoding="utf-8")
    job = job_for(state, tc, calendars, config, source,
                  [{"fast": 24, "slow": 96}, {"fast": 12, "slow": 192}])
    got = ProcessSandbox(tmp_path).run(job)
    assert got.ok, got.error
    doc = runner.execute(job_doc(job), [job_arrays(i) for i in job.instruments],
                         lambda: runner.load_text(source))
    want = result_from_doc(job, doc)
    assert sorted(got.targets) == sorted(want.targets)
    assert len(got.targets) == 2 * len(tc.instruments)
    for key, targets in want.targets.items():
        assert got.targets[key].tobytes() == targets.tobytes(), key
        assert np.array_equal(got.bars[key], want.bars[key])
        assert len(got.call_ms[key]) == len(targets)
    assert any(np.any(t != 0.0) for t in got.targets.values())
    assert list(tmp_path.iterdir()) == []  # the job's directories are removed


def test_a_source_not_in_the_repository_is_refused_naming_the_rule(tmp_path, state, tc,
                                                                  calendars, config):
    source = TREND.read_text(encoding="utf-8") + "# not a file of this repository\n"
    job = job_for(state, tc, calendars, config, source, [{}], window=SHORT)
    with pytest.raises(SandboxRefused, match=r"\[repository_source\]") as info:
        ProcessSandbox(tmp_path).run(job)
    assert info.value.rule == "repository_source"
    assert list(tmp_path.iterdir()) == []  # nothing ran, nothing was written


def test_a_job_carrying_a_function_object_is_refused(tmp_path, state, tc, calendars, config):
    job = build_job(state, tc.track, tc.instruments, calendars, SHORT,
                    function=lambda bars, params: 0.0, param_sets=[{}], config_dir=config)
    with pytest.raises(SandboxRefused) as info:
        ProcessSandbox(tmp_path).run(job)
    assert info.value.rule == "function"


def test_the_child_environment_holds_only_the_allow_list(tmp_path, monkeypatch, state, tc,
                                                         calendars, config):
    monkeypatch.setenv(FAKE_KEY, "fake-key-not-a-secret")
    assert FAKE_KEY not in child_env()
    assert set(child_env()) <= set(CHILD_ENV)
    source = (STRATEGIES / "env_probe.py").read_text(encoding="utf-8")
    job = job_for(state, tc, calendars, config, source, [{"probe": 0}, {"probe": 1}],
                  window=SHORT, instruments=tc.instruments[:1])
    result = ProcessSandbox(tmp_path).run(job)
    assert result.ok, result.error
    symbol = tc.instruments[0].symbol
    assert len(result.targets[(0, symbol)]) > 0
    assert np.all(result.targets[(0, symbol)] == 0.0), "the fake key reached the child"
    assert np.all(result.targets[(1, symbol)] == 0.0), "a variable outside the allow-list"


def test_an_endless_loop_is_killed_at_the_wall_clock_limit(tmp_path, tmp_path_factory, state,
                                                           tc, calendars):
    # A copied run.toml with a 3-second wall-clock limit and a CPU-time limit far
    # above it, so that only the harness's kill can end the loop in time.
    config = copy_config(tmp_path_factory, short_run(wall_seconds=3.0, cpu_seconds=600.0))
    source = (STRATEGIES / "endless_loop.py").read_text(encoding="utf-8")
    job = job_for(state, tc, calendars, config, source, [{"step": 1}], window=SHORT,
                  instruments=tc.instruments[:1])
    backend = ProcessSandbox(tmp_path)
    result = bounded(lambda: backend.run(job))
    assert not result.ok
    assert (result.error.stage, result.error.rule) == ("limit", "wall_clock"), result.error
    assert result.error.text.startswith("limit [wall_clock]")
    # The harness goes on: the same backend runs the next job.
    good = job_for(state, tc, calendars, config, TREND.read_text(encoding="utf-8"),
                   [TREND_PARAMS], window=SHORT, instruments=tc.instruments[:1])
    assert bounded(lambda: backend.run(good)).ok
    assert list(tmp_path.iterdir()) == []


def test_an_output_over_the_cap_returns_limit(tmp_path, tmp_path_factory, state, tc,
                                              calendars):
    # A copied run.toml with a 1000-byte output cap; the result of seven trading
    # dates on three instruments is far longer.
    config = copy_config(tmp_path_factory, short_run(output_bytes=1000))
    job = job_for(state, tc, calendars, config, TREND.read_text(encoding="utf-8"),
                  [TREND_PARAMS])
    result = bounded(lambda: ProcessSandbox(tmp_path).run(job))
    assert not result.ok
    assert (result.error.stage, result.error.rule) == ("limit", "output"), result.error


def test_a_memory_bomb_returns_limit_or_a_dry_run_error(tmp_path, tmp_path_factory, state, tc,
                                                        calendars):
    # A copied run.toml with a 768 MiB address-space limit, so that the bomb is
    # stopped early whatever the machine holds.
    config = copy_config(tmp_path_factory, short_run(memory_bytes=768 * 1024 * 1024))
    source = (STRATEGIES / "memory_bomb.py").read_text(encoding="utf-8")
    job = job_for(state, tc, calendars, config, source, [{"chunk": 67108864}], window=SHORT,
                  instruments=tc.instruments[:1])
    result = bounded(lambda: ProcessSandbox(tmp_path).run(job))
    assert not result.ok
    assert result.error.stage in ("limit", "dry_run"), result.error
    if result.error.stage == "dry_run":
        assert result.error.text == "dry_run [raised]: position raised MemoryError at window " \
            "bar 0 (parameter set 0)"


# --- decision 101 (b): the runner's private result channel -------------------------


FORGED = STRATEGIES / "forged_result.py"


def test_a_text_that_forges_a_result_on_descriptor_1_and_exits_gives_no_result(
        tmp_path, state, tc, calendars, config):
    """REVIEW-12 should-fix 2: the text writes a forged result document to
    descriptor 1 and calls ``os._exit(0)``; the result is stage ``dry_run``, rule
    ``no_result``, not the forged targets."""
    job = job_for(state, tc, calendars, config, FORGED.read_text(encoding="utf-8"),
                  [{"exit": 1}], window=SHORT, instruments=tc.instruments[:1])
    result = bounded(lambda: ProcessSandbox(tmp_path).run(job))
    assert not result.ok and not result.targets
    assert (result.error.stage, result.error.rule) == ("dry_run", "no_result"), result.error
    assert result.error.text == "dry_run [no_result]: the run ended without a result"
    assert_clean([result.error.text], forbidden_words(state, TRACK, SEEDS))
    assert list(tmp_path.iterdir()) == []


def test_what_a_text_writes_to_descriptor_1_or_prints_never_reaches_the_result(
        tmp_path, state, tc, calendars, config):
    job = job_for(state, tc, calendars, config, FORGED.read_text(encoding="utf-8"),
                  [{"exit": 0}], window=SHORT, instruments=tc.instruments[:1])
    result = bounded(lambda: ProcessSandbox(tmp_path).run(job))
    assert result.ok, result.error
    targets = result.targets[(0, tc.instruments[0].symbol)]
    assert len(targets) > 1 and np.all(targets == 0.0)
