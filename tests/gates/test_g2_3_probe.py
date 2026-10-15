"""Gate item G2.3: a trusted probe run through the container backend reports from
inside no route to the network, a read-only root, a non-root user, and a mount that
holds the W bars and no later bar; and the limits the runtime set (DESIGN 18.3
G2.3, 12.4; decision 103 (a), (b), (c) and 106 (a), (d) of 2026-10-14-m13; O-22
item 3 of meta/decisions/decisions-2026-10-15-owner.md; decision 102 (b);
decision 19 of 2026-10-12).

The probe (``sandbox/probe.py``, in the image) runs on the container backend with
exactly a job's options and, as its mount, the input directory of the job of
``test_synth``'s W of ``DAY`` (2019-06-11 to 2019-07-08), built from a store that
also holds T's and later bars (fetched at ``SYNTH_AS_OF``). Decision 103 (b)'s
judgement, made here on the report and also by ``container.judge``:

- the routing table holds no route, only loopback is present, and a connection
  to TEST-NET-1 failed;
- every create under ``/``, ``/usr``, ``/home`` and the mount failed with
  ``EROFS`` (read-only), and the one under ``/tmp`` succeeded;
- a non-zero user id and an empty effective capability set;
- per instrument, the mount holds exactly W's bars and the context the job
  carries, counted here from the store itself, so no bar after W's last day
  (and the store holds bars after W, so that this means something);
- O-22 item 3: the limits read from inside (the cgroup's ``pids.max``,
  ``memory.max`` with ``memory.swap.max``, ``cpu.max``, and the probe's own
  ``RLIMIT_CPU``) each equal the value ``run.toml`` (its ``[sandbox]``, that of
  ``config/run.toml``) and decision 102 (b) require: a limit missing or wider
  fails the item. The probe attempts nothing against a limit.

``discotrade sandbox selftest`` (decision 103 (c)) on the same state at
``AS_OF``, whose decision-19 ``D`` is ``DAY``, prints one PASS line per finding
and exits 0. No container a test started remains.

Seeds: ``test_synth``'s bars come from its fixture records' seeds, written here
(``SEEDS``) and checked. No random draw is made here. Time is read only through
``--as-of``. Job directories go under the test's temporary directory
(``tempfile.tempdir`` set to it for the command).
"""

import math
import tempfile
from datetime import UTC, date, datetime, time

import pytest
from m2_harness import copy_config

from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_run, load_track_config
from discotrade.daily import closed_day
from discotrade.sandbox import container
from discotrade.sandbox.base import build_job
from discotrade.sandbox.container import ContainerSandbox, judge
from discotrade.tradingcal import trading_date

pytestmark = [pytest.mark.gate, pytest.mark.gate_m2, pytest.mark.container]

SYNTH = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
SYNTH_AS_OF = "2019-07-25T00:00:00+00:00"
#: Decision 19's D at AS_OF: 2019-07-16's bars have not closed by midnight UTC.
AS_OF = "2019-07-16T00:00:00+00:00"
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
OUTSIDE_TMP = ("/", "/usr", "/home", "/job")
FINDINGS = ["network.routes", "network.interfaces", "network.connect", "create /",
            "create /usr", "create /home", "create /job", "create /tmp", "user.uid",
            "user.capabilities", "limits.pids", "limits.memory", "limits.cpu",
            "limits.cpu_time", "mount.instruments",
            *(f"mount.{s}" for s in SEEDS)]


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory.mktemp("cfg"))


@pytest.fixture(scope="module")
def tc(config):
    return load_track_config(config, SYNTH)


@pytest.fixture(scope="module")
def calendars(config):
    return {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def synth_state(tmp_path_factory, config):
    path = tmp_path_factory.mktemp("synth") / "state"
    path.mkdir()
    assert main(["--state", str(path), "--config", str(config), "--track", SYNTH,
                 "--as-of", SYNTH_AS_OF, "bars", "fetch"]) == 0
    return path


@pytest.fixture
def backends(monkeypatch, tmp_path):
    """Every ContainerSandbox made during the test, its jobs under ``tmp_path``; after
    the test none of their containers remains (removed by name if one does)."""
    made = []

    class Recording(ContainerSandbox):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            made.append(self)

    monkeypatch.setattr(container, "ContainerSandbox", Recording)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    yield made
    left = []
    for b in made:
        for name in b.started:
            if container.container_exists(b.runtime(), name):
                left.append(name)
                container.remove(b.runtime(), name)
    assert left == [], f"containers left behind: {left}"


def store_counts(state, tc, calendars):
    """Per instrument, from the store itself: the bars of W, the context the job
    holds before them (up to history_cap_bars - 1, none before trusted_from), and the
    stored bars after W."""
    counts = {}
    store = BarStore(state, SYNTH, tc.track.bar_seconds)
    for inst in tc.instruments:
        cal = calendars[inst.calendar]
        start = datetime.combine(inst.trusted_from, time(), tzinfo=UTC)
        bars = store.read_range(inst.symbol, start, datetime(2030, 1, 1, tzinfo=UTC))
        dates = [trading_date(cal, ts.to_pydatetime()) for ts in bars["ts"]]
        window = sum(1 for d in dates if W_FIRST <= d <= W_LAST)
        before = sum(1 for d in dates if d < W_FIRST)
        after = sum(1 for d in dates if d > W_LAST)
        counts[inst.symbol] = (window, min(before, tc.track.history_cap_bars - 1), after)
    return counts


def test_the_facts_written_here(tc, calendars, config):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS
    assert closed_day(tc, calendars, datetime.fromisoformat(AS_OF)) == DAY
    w = tc.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)
    # The limits the probe is judged against are the production ones.
    assert load_run(config).sandbox == load_run(REPO_ROOT / "config").sandbox


@pytest.fixture(scope="module")
def probe_run(tmp_path_factory, synth_state, tc, calendars, config):
    """One probe run on W's job; the container is gone after it (removed by name and
    failed on if one remains)."""
    window = tc.track.windows(DAY).w
    job = build_job(synth_state, tc.track, tc.instruments, calendars, window,
                    source=container.PROBE_SOURCE, param_sets=[{}], config_dir=config)
    scratch = tmp_path_factory.mktemp("probe") / "scratch"
    b = ContainerSandbox(scratch, config)
    try:
        report = b.run_probe(job)
        left = [n for n in b.started if container.container_exists(b.runtime(), n)]
    finally:
        for name in b.started:
            if container.container_exists(b.runtime(), name):
                container.remove(b.runtime(), name)
    assert left == [], f"containers left behind: {left}"
    assert list(scratch.iterdir()) == []  # the job directory is removed
    return job, b, report, window


def test_the_probe_reports_no_route_to_the_network(probe_run):
    _, _, report, _ = probe_run
    net = report["network"]
    assert net["routes"] == []
    assert net["interfaces"] == ["lo"]
    assert net["connect"]["target"] == "192.0.2.1:9"
    assert net["connect"]["connected"] is False


def test_the_probe_reports_a_read_only_root_and_a_writable_tmp(probe_run):
    _, _, report, _ = probe_run
    creates = {c["under"]: c for c in report["creates"]}
    assert sorted(creates) == sorted([*OUTSIDE_TMP, "/tmp"])
    for d in OUTSIDE_TMP:
        assert (creates[d]["created"], creates[d]["error"]) == (False, "EROFS"), d
    assert creates["/tmp"]["created"] is True


def test_the_probe_reports_a_non_root_user_without_capabilities(probe_run):
    _, _, report, _ = probe_run
    ident = report["identity"]
    assert ident["uid"] != 0 and ident["euid"] != 0
    assert ident["gid"] != 0 and ident["egid"] != 0
    assert int(ident["cap_eff"], 16) == 0


def test_the_mount_holds_the_w_bars_and_their_context_and_no_later_bar(
        probe_run, synth_state, tc, calendars):
    job, _, report, window = probe_run
    counts = store_counts(synth_state, tc, calendars)
    mounted = report["mount"]["instruments"]
    assert len(mounted) == len(tc.instruments)
    for inst, m in zip(tc.instruments, mounted, strict=True):
        window_bars, context, after = counts[inst.symbol]
        assert after > 0, "the store holds no bar after W: the test would prove nothing"
        assert window_bars > 0, inst.symbol
        assert m["count"] == window_bars + context, (inst.symbol, m["count"], counts)
        assert set(m["arrays"].values()) == {window_bars + context}, inst.symbol
        assert m["latest_open"] is None  # the mount carries no timestamp
    expected = container.expected_mount(job, tc.instruments, calendars, window)
    assert [(e.count, e.window) for e in expected] == [
        (sum(counts[i.symbol][:2]), counts[i.symbol][0]) for i in tc.instruments]


def test_the_limits_read_from_inside_are_those_run_toml_and_decision_102_b_require(
        probe_run, config):
    job, _, report, _ = probe_run
    settings = load_run(config).sandbox
    lim = report["limits"]
    assert lim["pids.max"] == str(settings.pids)
    assert lim["memory.max"] == str(settings.memory_bytes) == str(job.limits.memory_bytes)
    assert lim["memory.swap.max"] == "0"
    quota, period = (int(v) for v in lim["cpu.max"].split())
    assert period > 0 and quota == round(settings.cpus * period)
    soft = math.ceil(settings.cpu_seconds)
    assert lim["rlimit_cpu"] == [soft, soft + 1]


def test_the_harness_judges_every_finding_of_the_probe_run_a_pass(
        probe_run, tc, calendars, config):
    job, b, report, window = probe_run
    expected = container.expected_mount(job, tc.instruments, calendars, window)
    required = container.required_limits(job.limits, load_run(config).sandbox)
    findings = judge(report, expected, required)
    assert [f.name for f in findings] == FINDINGS
    assert all(f.ok for f in findings), [f for f in findings if not f.ok]
    assert len(b.started) == 1  # the probe ran in one container, removed after


def test_sandbox_selftest_prints_one_pass_line_per_finding_and_exits_0(
        backends, capsys, synth_state, config):
    assert main(["--state", str(synth_state), "--config", str(config), "--track", SYNTH,
                 "--as-of", AS_OF, "sandbox", "selftest"]) == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith(("PASS ", "FAIL "))]
    assert [ln.split(":")[0].split(" ", 1)[1] for ln in lines] == FINDINGS
    assert all(ln.startswith("PASS ") for ln in lines), out
    assert f"day {DAY.isoformat()}" in out
    assert f"W {W_FIRST.isoformat()} to {W_LAST.isoformat()}" in out
    assert len(backends) == 1 and len(backends[0].started) == 1
