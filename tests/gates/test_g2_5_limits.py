"""Gate item G2.5: the container backend's limits, by trusted fixtures (O-22 item 4
of meta/decisions/decisions-2026-10-15-owner.md, which adds G2.5 to DESIGN 18.3;
DESIGN 12.4; decision 102 (b), 106 (a) of 2026-10-14-m13; I-7, I-12, I-14).

Each fixture under ``tests/fixtures/strategies/`` is a test of one configured
limit, bounded by a value in its own text: ``wall_wait.py`` sleeps
``WAIT_SECONDS`` once; ``output_fixed.py`` returns ``POSITION`` (19 characters) at
every bar; ``memory_fixed.py`` allocates and writes ``ALLOCATE_BYTES`` once. Each
runs through the container backend under a ``run.toml`` copied under the test's
temporary directory holding one short limit (said in each test):

- wall clock: the text that waits longer than the short wall limit ends with
  the backend's ``limit`` error naming ``wall_clock``, within the limit plus
  ``KILL_GRACE``, and no container remains;
- output cap: the text whose output exceeds the short cap ends with the
  ``limit`` error for ``output``, and the result read is no longer than the cap;
- memory: the text that allocates a fixed amount above the short memory limit
  ends with a ``limit`` or ``dry_run`` error, never a harness failure, and the
  harness process's own memory does not grow by the allocation.

Each test also runs its fixture under the production limits
(``tests/fixtures/config/run.toml`` unchanged, whose ``[sandbox]`` equals
``config/run.toml``'s, checked here) and shows it passing, as its comment says,
so that the short limit is what the test exercises.

Process count and CPU are proven by G2.3's inspection, not by attempt (O-22 item
4): the probe reads ``pids.max``, ``cpu.max`` and its own ``RLIMIT_CPU`` from
inside the container and ``tests/gates/test_g2_3_probe.py`` compares each with
``run.toml``. No fixture here tries to exhaust them; the last test records that
choice.

Time: the wall-clock test measures the job's duration with ``time.monotonic``
around the backend's run, the timer the backend uses for the limit; it decides an
assertion, never a result (I-12). Kill grace: the design names none, so
``KILL_GRACE`` is this test's bound on the forced removal of the container and the
reaping of the runtime's command after the limit expires. Memory of the harness:
read from ``/proc/self/status``; its peak (``VmHWM``) is reset through
``/proc/self/clear_refs`` before each run.

Every test mounts only a job directory under its temporary directory and leaves
no container behind. Bars: ``test_mixed`` fetched at ``MIXED_AS_OF``, its seeds
written here (``MIXED_SEEDS``) and checked. No random draw is made here.
"""

import time
from datetime import date

import pytest
from m2_harness import STRATEGIES, Backends, copy_config

from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange, load_calendar, load_run, load_track_config
from discotrade.sandbox import container
from discotrade.sandbox.base import build_job
from discotrade.sandbox.container import ContainerSandbox

pytestmark = [pytest.mark.gate, pytest.mark.gate_m2, pytest.mark.container]

MIXED = "test_mixed"
MIXED_SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
MIXED_AS_OF = "2019-06-21T00:00:00+00:00"
#: One trading date, one instrument: the wall-clock and memory runs.
SHORT = DateRange(date(2019, 6, 17), date(2019, 6, 17))
#: Seven trading dates, three instruments: the output runs.
WINDOW = DateRange(date(2019, 6, 11), date(2019, 6, 18))
#: The short limits of the copied run.toml, one per test.
SHORT_WALL_SECONDS = 3.0
SHORT_OUTPUT_BYTES = 4096
SHORT_MEMORY_BYTES = 268435456  # 256 MiB
#: This test's bound on the forced removal after the wall-clock limit (seconds).
KILL_GRACE = 5.0
#: The fixtures' own bounds, as their texts write them (checked below).
WAIT_SECONDS = 10.0
ALLOCATE_BYTES = 536870912  # 512 MiB
#: How much the harness's own peak memory may grow over a run: an eighth of the
#: fixture's allocation, so that the allocation landing here would fail the test.
HARNESS_GROWTH = ALLOCATE_BYTES // 8


class Recording(ContainerSandbox):
    """The container backend, recording the Execution of each run it judges."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executions = []

    def _result(self, job, run):
        self.executions.append(run)
        return super()._result(job, run)


@pytest.fixture(scope="module")
def production(tmp_path_factory):
    return copy_config(tmp_path_factory.mktemp("prod"))


@pytest.fixture(scope="module")
def tc(production):
    return load_track_config(production, MIXED)


@pytest.fixture(scope="module")
def calendars(production):
    return {p.stem: load_calendar(p) for p in sorted((production / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def mixed_state(tmp_path_factory, production):
    path = tmp_path_factory.mktemp("mixed") / "state"
    path.mkdir()
    assert main(["--state", str(path), "--config", str(production), "--track", MIXED,
                 "--as-of", MIXED_AS_OF, "bars", "fetch"]) == 0
    return path


@pytest.fixture
def backend(tmp_path):
    """A factory of recording container backends, jobs under ``tmp_path``; after the
    test no container any of them started remains."""
    made = Backends(tmp_path / "jobs")

    def make(config_dir):
        b = Recording(made.root / f"scratch-{len(made.made)}", config_dir)
        made.made.append(b)
        return b

    yield make
    left = made.remove_left()
    assert left == [], f"containers left behind: {left}"


def text(name):
    return (STRATEGIES / name).read_text(encoding="utf-8")


def job_for(state, tc, calendars, config, source, window=SHORT, instruments=None):
    return build_job(state, tc.track, instruments or tc.instruments[:1], calendars, window,
                     source=source, param_sets=[{}], config_dir=config)


def assert_no_container_of(b):
    assert b.started, "the backend started no container"
    assert [n for n in b.started if container.container_exists(b.runtime(), n)] == []


def status(field):
    """A ``kB`` field of this process's ``/proc/self/status``, in bytes."""
    with open("/proc/self/status", encoding="ascii") as handle:
        for line in handle:
            if line.startswith(field + ":"):
                return int(line.split()[1]) * 1024
    raise AssertionError(f"no {field} in /proc/self/status")


def reset_peak():
    """Reset this process's peak resident size (``VmHWM``) to its current one."""
    with open("/proc/self/clear_refs", "w", encoding="ascii") as handle:
        handle.write("5")


def test_the_facts_written_here(production, tc):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == MIXED_SEEDS
    assert load_run(production).sandbox == load_run(REPO_ROOT / "config").sandbox
    prod = load_run(production).sandbox
    assert SHORT_WALL_SECONDS + KILL_GRACE < WAIT_SECONDS < prod.wall_seconds
    assert SHORT_MEMORY_BYTES < ALLOCATE_BYTES < prod.memory_bytes
    assert SHORT_OUTPUT_BYTES < prod.output_bytes
    assert f"WAIT_SECONDS = {WAIT_SECONDS!r}" in text("wall_wait.py")
    assert f"ALLOCATE_BYTES = {ALLOCATE_BYTES!r}" in text("memory_fixed.py")
    assert "POSITION = 0.12345678901234568" in text("output_fixed.py")


def test_a_wait_past_the_short_wall_limit_ends_with_limit_wall_clock_within_the_grace(
        tmp_path, backend, mixed_state, tc, calendars, production):
    # A copied run.toml with a 3-second wall-clock limit (cpu_seconds left at its
    # production value, far above it): wall_wait.py sleeps 10 s.
    config = copy_config(tmp_path / "short", wall_seconds=SHORT_WALL_SECONDS)
    b = backend(config)
    job = job_for(mixed_state, tc, calendars, config, text("wall_wait.py"))
    start = time.monotonic()
    result = b.run(job)
    took = time.monotonic() - start
    assert not result.ok
    assert (result.error.stage, result.error.rule) == ("limit", "wall_clock"), result.error
    assert SHORT_WALL_SECONDS <= took <= SHORT_WALL_SECONDS + KILL_GRACE, took
    assert_no_container_of(b)
    # Under the production limits the same text passes: it waits its 10 s and ends.
    p = backend(production)
    passed = p.run(job_for(mixed_state, tc, calendars, production, text("wall_wait.py")))
    assert passed.ok, passed.error
    assert_no_container_of(p)


def test_an_output_over_the_short_cap_ends_with_limit_output_and_reads_no_more(
        tmp_path, backend, mixed_state, tc, calendars, production):
    # Under the production limits output_fixed.py passes, and its result is longer
    # than the short cap: so the short cap is what the second run exercises.
    p = backend(production)
    passed = p.run(job_for(mixed_state, tc, calendars, production, text("output_fixed.py"),
                           window=WINDOW, instruments=tc.instruments))
    assert passed.ok, passed.error
    (full,) = p.executions
    assert len(full.out) > SHORT_OUTPUT_BYTES, len(full.out)
    assert_no_container_of(p)
    # A copied run.toml with a 4096-byte output cap.
    config = copy_config(tmp_path / "short", output_bytes=SHORT_OUTPUT_BYTES)
    b = backend(config)
    result = b.run(job_for(mixed_state, tc, calendars, config, text("output_fixed.py"),
                           window=WINDOW, instruments=tc.instruments))
    assert not result.ok
    assert (result.error.stage, result.error.rule) == ("limit", "output"), result.error
    (cut,) = b.executions
    assert cut.breach == "output"
    assert len(cut.out) <= SHORT_OUTPUT_BYTES, len(cut.out)
    assert_no_container_of(b)


def test_an_allocation_over_the_short_memory_limit_ends_with_limit_or_dry_run(
        tmp_path, backend, mixed_state, tc, calendars, production):
    # A copied run.toml with a 256 MiB memory limit: memory_fixed.py allocates 512 MiB.
    config = copy_config(tmp_path / "short", memory_bytes=SHORT_MEMORY_BYTES)
    b = backend(config)
    job = job_for(mixed_state, tc, calendars, config, text("memory_fixed.py"))
    reset_peak()
    before = status("VmRSS")
    result = b.run(job)  # a harness failure would raise here
    assert status("VmHWM") - before < HARNESS_GROWTH
    assert not result.ok
    assert result.error.stage in ("limit", "dry_run"), result.error
    assert_no_container_of(b)
    # Under the production limits (2 GiB) the same text passes, and the harness's own
    # memory still does not grow by the allocation.
    p = backend(production)
    reset_peak()
    before = status("VmRSS")
    passed = p.run(job_for(mixed_state, tc, calendars, production, text("memory_fixed.py")))
    assert status("VmHWM") - before < HARNESS_GROWTH
    assert passed.ok, passed.error
    assert_no_container_of(p)


def test_process_count_and_cpu_are_proven_by_g2_3s_inspection_not_by_attempt():
    # O-22 item 4's choice, recorded: G2.3 reads and compares these three limits.
    g2_3 = (REPO_ROOT / "tests" / "gates" / "test_g2_3_probe.py").read_text(encoding="utf-8")
    for key in ('"pids.max"', '"cpu.max"', '"rlimit_cpu"'):
        assert f"lim[{key}]" in g2_3, key
    for finding in ('"limits.pids"', '"limits.cpu"', '"limits.cpu_time"'):
        assert finding in g2_3, finding
