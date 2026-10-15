"""The probe, ``discotrade sandbox selftest`` and its judgement (DESIGN 12.4, 18.3 G2.3,
19.3 L5; decision 103 of 2026-10-14-m13; decisions 2026-10-12 15, 19; decision
2026-10-14-m12 95 (a); I-11, I-12).

``sandbox/probe.py`` imports only the standard library (read with ``ast``) and is an
input of the image's tag. On the container backend (tests marked ``container``,
the image of the current tag built beforehand by ``discotrade sandbox build``), a
probe run on the job of ``test_synth``'s W of ``DAY`` reports no route, loopback
only and a failed connection; every create outside ``/tmp`` failed because the file
system is read-only (``EROFS``) and the one under ``/tmp`` succeeded; a non-zero
user id and an empty effective capability set; the limits the runtime set, read
from inside (the cgroup's ``pids.max``, ``memory.max`` with ``memory.swap.max``
and ``cpu.max``, and the probe's own ``RLIMIT_CPU``), each equal to the value the
copied ``run.toml`` and decision 102 (b) require (O-22 item 3 of
decisions-2026-10-15-owner); and per instrument the window's bars and context,
counted here from the store itself, with no bar after W's last day. ``sandbox
selftest`` on that state prints one PASS line per finding and exits 0. The
judgement fails each finding on a report written here by hand with that finding
wrong, a limit missing, unlimited or wider than required among them. The probe
attempts nothing against a limit: it reads them only. With an empty ``PATH``,
``sandbox selftest`` exits 1 naming that no container runtime was found and starts
nothing.

Why ``EROFS``: the container's user is not root, so without ``--read-only`` a
create under ``/`` still fails, with ``EACCES``; only the error says the root is
read-only (DESIGN 18.3 G2.3: "a read-only root").

Seeds: ``test_synth``'s bars come from its fixture records' seeds, written here
(``SYNTH_SEEDS``) and checked against them. No random draw is made here. Time is
read only through ``--as-of``: ``SYNTH_AS_OF`` for ``bars fetch`` (which stores T
and later bars too, so that "no bar after W" means something) and ``AS_OF`` for the
self-test, at which decision 19's ``D`` is ``DAY``. Job directories are written
under the test's temporary directory (``tempfile.tempdir`` set to it for the
command) and no container a test started remains.
"""

import ast
import copy
import json
import math
import shutil
import sys
import tempfile
from datetime import UTC, date, datetime, time

import pytest

from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_run, load_track_config
from discotrade.daily import closed_day
from discotrade.sandbox import container
from discotrade.sandbox.base import build_job, limits_from_config
from discotrade.sandbox.container import ContainerSandbox, Expected, Required, judge
from discotrade.tradingcal import trading_date

PROBE = REPO_ROOT / "sandbox" / "probe.py"
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
SYNTH = "test_synth"
SYNTH_SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
SYNTH_AS_OF = "2019-07-25T00:00:00+00:00"
#: Decision 19's D at AS_OF: 2019-07-16's bars have not closed by midnight UTC.
AS_OF = "2019-07-16T00:00:00+00:00"
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
OUTSIDE_TMP = ("/", "/usr", "/home", "/job")


# ------------------------------------------------------------------ the probe's text


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a relative import"
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) == "__import__":
            raise AssertionError("__import__ in the probe")
    return names


def test_the_probe_imports_only_the_standard_library():
    names = _imports(PROBE)
    assert names, "the probe imports nothing?"
    assert names <= set(sys.stdlib_module_names), names - set(sys.stdlib_module_names)


def test_the_probe_is_an_input_of_the_image_and_copied_into_it():
    assert container.IMAGE_INPUTS["probe.py"] == "sandbox/probe.py"
    text = (REPO_ROOT / "sandbox" / "Dockerfile").read_text(encoding="utf-8")
    assert f"COPY probe.py {container.PROBE_PATH}" in text
    assert container.PROBE_ARGV == ("python", "-I", container.PROBE_PATH, container.MOUNT)


# ------------------------------------------------------------------ the judgement


#: Two instruments' expectations, written by hand: the mount must hold 912 bars of
#: SYNA (433 of W, 479 of context) and 900 of SYNB, the last opening before W ends.
W_END = datetime(2019, 7, 8, 21, tzinfo=UTC)
EXPECTED = [
    Expected("SYNA", count=912, window=433, last_open=datetime(2019, 7, 8, 20, tzinfo=UTC),
             w_end=W_END),
    Expected("SYNB", count=900, window=430, last_open=datetime(2019, 7, 8, 20, tzinfo=UTC),
             w_end=W_END),
]


#: The limits required, by hand: those of tests/fixtures/config/run.toml (pids 64,
#: memory_bytes 2 GiB with no swap, cpus 1.0, cpu_seconds 1200: a soft RLIMIT_CPU of
#: 1200 s and a hard one of 1201 s, as run_command sets them).
REQUIRED = Required(pids=64, memory_bytes=2147483648, cpus=1.0, cpu_soft=1200, cpu_hard=1201)


def good_report():
    """A report, by hand, on which every finding passes."""
    def inst(i, n):
        return {"index": i, "file": f"bars-{i}.npz", "count": n, "latest_open": None,
                "arrays": {k: n for k in ("open", "high", "low", "close", "volume", "hour",
                                          "weekday", "rolled", "gap")}}
    return {
        "probe": 1,
        "network": {"routes": [], "interfaces": ["lo"],
                    "connect": {"target": "192.0.2.1:9", "connected": False,
                                "error": "ENETUNREACH"}},
        "creates": [*({"under": d, "created": False, "error": "EROFS"} for d in OUTSIDE_TMP),
                    {"under": "/tmp", "created": True, "error": None}],
        "identity": {"uid": 10001, "euid": 10001, "gid": 10001, "egid": 10001,
                     "cap_eff": "0000000000000000"},
        "limits": {"cgroup": "/sys/fs/cgroup", "pids.max": "64", "memory.max": "2147483648",
                   "memory.swap.max": "0", "cpu.max": "100000 100000",
                   "rlimit_cpu": [1200, 1201]},
        "mount": {"path": "/job", "files": [], "instruments": [inst(0, 912), inst(1, 900)]},
    }


def names(findings):
    return [f.name for f in findings]


ALL = ["network.routes", "network.interfaces", "network.connect", "create /",
       "create /usr", "create /home", "create /job", "create /tmp", "user.uid",
       "user.capabilities", "limits.pids", "limits.memory", "limits.cpu", "limits.cpu_time",
       "mount.instruments", "mount.SYNA", "mount.SYNB"]


def test_on_a_good_report_every_finding_passes():
    findings = judge(good_report(), EXPECTED, REQUIRED)
    assert names(findings) == ALL
    assert all(f.ok for f in findings), [f for f in findings if not f.ok]


def _route(r):
    r["network"]["routes"] = ["eth0 00000000 010011AC 0003 0 0 0 00000000 0 0 0"]


def _interface(r):
    r["network"]["interfaces"] = ["eth0", "lo"]


def _connected(r):
    r["network"]["connect"].update(connected=True, error=None)


def _writable_root(r):
    r["creates"][0].update(created=True, error=None)


def _root_not_read_only(r):
    r["creates"][0]["error"] = "EACCES"


def _writable_usr(r):
    r["creates"][1].update(created=True, error=None)


def _writable_home(r):
    r["creates"][2].update(created=True, error=None)


def _writable_mount(r):
    r["creates"][3].update(created=True, error=None)


def _tmp_not_writable(r):
    r["creates"][4].update(created=False, error="EROFS")


def _user_0(r):
    r["identity"].update(uid=0, euid=0)


def _capability(r):
    r["identity"]["cap_eff"] = "0000000000000400"  # CAP_NET_BIND_SERVICE


def _extra_instrument(r):
    r["mount"]["instruments"].append(copy.deepcopy(r["mount"]["instruments"][1]))


def _bar_after_w(r):
    # One more bar mounted than the job's window and context: a bar after W.
    r["mount"]["instruments"][0]["count"] = 913
    for k in r["mount"]["instruments"][0]["arrays"]:
        r["mount"]["instruments"][0]["arrays"][k] = 913


def _open_after_w(r):
    r["mount"]["instruments"][1]["latest_open"] = "2019-07-09T13:00:00+00:00"


def _missing_bar(r):
    r["mount"]["instruments"][1]["count"] = 899


def _limit(key, value):
    def change(r):
        if value is None:
            del r["limits"][key]
        else:
            r["limits"][key] = value
    return change


WRONG = {
    "a route": (_route, "network.routes"),
    "an interface": (_interface, "network.interfaces"),
    "a connection": (_connected, "network.connect"),
    "a writable root": (_writable_root, "create /"),
    "a root failing for another reason than read-only": (_root_not_read_only, "create /"),
    "a writable /usr": (_writable_usr, "create /usr"),
    "a writable /home": (_writable_home, "create /home"),
    "a writable mount": (_writable_mount, "create /job"),
    "no /tmp": (_tmp_not_writable, "create /tmp"),
    "user id 0": (_user_0, "user.uid"),
    "a capability": (_capability, "user.capabilities"),
    "an instrument not in the job": (_extra_instrument, "mount.instruments"),
    "a bar after W": (_bar_after_w, "mount.SYNA"),
    "a latest open after W": (_open_after_w, "mount.SYNB"),
    "a bar missing": (_missing_bar, "mount.SYNB"),
    "no process limit": (_limit("pids.max", None), "limits.pids"),
    "an unlimited process count": (_limit("pids.max", "max"), "limits.pids"),
    "a process limit wider than required": (_limit("pids.max", "65"), "limits.pids"),
    "no memory limit": (_limit("memory.max", None), "limits.memory"),
    "an unlimited memory": (_limit("memory.max", "max"), "limits.memory"),
    "a memory limit wider than required": (_limit("memory.max", "2147487744"),
                                           "limits.memory"),
    "swap beyond the memory limit": (_limit("memory.swap.max", "max"), "limits.memory"),
    "no swap value": (_limit("memory.swap.max", None), "limits.memory"),
    "no CPU limit": (_limit("cpu.max", None), "limits.cpu"),
    "an unlimited CPU": (_limit("cpu.max", "max 100000"), "limits.cpu"),
    "a CPU limit wider than required": (_limit("cpu.max", "150000 100000"), "limits.cpu"),
    "no CPU-time limit": (_limit("rlimit_cpu", None), "limits.cpu_time"),
    "an unlimited CPU time": (_limit("rlimit_cpu", [None, None]), "limits.cpu_time"),
    "a CPU-time limit wider than required": (_limit("rlimit_cpu", [1201, 1202]),
                                             "limits.cpu_time"),
    "a hard CPU-time limit left unlimited": (_limit("rlimit_cpu", [1200, None]),
                                             "limits.cpu_time"),
}


def test_narrower_limits_than_required_pass():
    report = good_report()
    report["limits"].update({"pids.max": "32", "memory.max": "1073741824",
                             "cpu.max": "50000 100000", "rlimit_cpu": [600, 601]})
    assert all(f.ok for f in judge(report, EXPECTED, REQUIRED))


def test_the_required_limits_are_those_of_run_toml_as_run_command_sets_them():
    settings = load_run(FIXTURE_CONFIG).sandbox
    limits = limits_from_config(FIXTURE_CONFIG)
    assert container.required_limits(limits, settings) == REQUIRED


@pytest.mark.parametrize("what", sorted(WRONG))
def test_the_judgement_fails_exactly_the_finding_a_report_has_wrong(what):
    change, name = WRONG[what]
    report = good_report()
    change(report)
    findings = judge(report, EXPECTED, REQUIRED)
    assert [f.name for f in findings if not f.ok] == [name], findings


def test_a_job_bar_after_w_fails_the_instrument_even_when_the_mount_matches_the_job():
    late = [Expected("SYNA", count=912, window=433,
                     last_open=datetime(2019, 7, 9, 13, tzinfo=UTC), w_end=W_END),
            EXPECTED[1]]
    failed = [f.name for f in judge(good_report(), late, REQUIRED) if not f.ok]
    assert failed == ["mount.SYNA"]


@pytest.mark.parametrize("part", ["network", "creates", "identity", "limits", "mount"])
def test_a_report_missing_a_part_fails_its_findings_and_never_raises(part):
    report = good_report()
    del report[part]
    findings = judge(report, EXPECTED, REQUIRED)
    assert names(findings) == ALL
    assert any(not f.ok for f in findings)


# ------------------------------------------------------------------ no runtime, no image


def _no_start(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError(f"a process was started: {args}")
    # The two places container.py starts a process: the runtime's commands and a run.
    monkeypatch.setattr(container, "_runtime", refuse)
    monkeypatch.setattr(container.ContainerSandbox, "run_program", refuse)


def test_selftest_with_an_empty_path_exits_1_naming_no_runtime_and_starts_nothing(
        monkeypatch, capsys, tmp_path):
    _no_start(monkeypatch)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("PATH", "")
    assert main(["--as-of", AS_OF, "sandbox", "selftest"]) == 1
    captured = capsys.readouterr()
    assert "no container runtime found" in captured.err
    assert "PASS" not in captured.out and list(tmp_path.iterdir()) == []


def test_selftest_without_the_image_exits_1_naming_it_and_starts_nothing(monkeypatch, capsys,
                                                                         tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "docker"
    stub.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")  # found, never run
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    _no_start(monkeypatch)
    monkeypatch.setattr(container, "image_present", lambda runtime, ref: False)
    assert main(["--as-of", AS_OF, "sandbox", "selftest"]) == 1
    err = capsys.readouterr().err
    assert container.image_ref("discotrade-sandbox") in err
    assert "discotrade sandbox build" in err


# ------------------------------------------------------------------ in the container


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


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


def test_the_fixture_facts_written_here(tc, calendars):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SYNTH_SEEDS
    assert closed_day(tc, calendars, datetime.fromisoformat(AS_OF)) == DAY
    w = tc.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)


def store_counts(state, tc, calendars):
    """Per instrument, from the store itself: the bars of W and the context the job
    holds before them (up to history_cap_bars - 1, none before trusted_from), and
    the number of stored bars after W (so that "none mounted" means something)."""
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


@pytest.mark.container
def test_a_probe_run_on_ws_job_reports_the_isolation_and_ws_bars_only(
        backends, tmp_path, synth_state, tc, calendars, config):
    window = tc.track.windows(DAY).w
    job = build_job(synth_state, tc.track, tc.instruments, calendars, window,
                    source=container.PROBE_SOURCE, param_sets=[{}], config_dir=config)
    b = container.ContainerSandbox(tmp_path / "scratch", config)
    report = b.run_probe(job)
    net = report["network"]
    assert net["routes"] == []
    assert net["interfaces"] == ["lo"]
    assert net["connect"]["connected"] is False and net["connect"]["target"] == "192.0.2.1:9"
    creates = {c["under"]: c for c in report["creates"]}
    assert sorted(creates) == sorted([*OUTSIDE_TMP, "/tmp"])
    for d in OUTSIDE_TMP:
        assert (creates[d]["created"], creates[d]["error"]) == (False, "EROFS"), d
    assert creates["/tmp"]["created"] is True
    ident = report["identity"]
    assert ident["uid"] != 0 and ident["euid"] != 0
    assert int(ident["cap_eff"], 16) == 0
    counts = store_counts(synth_state, tc, calendars)
    mounted = report["mount"]["instruments"]
    assert len(mounted) == len(tc.instruments)
    for inst, m in zip(tc.instruments, mounted, strict=True):
        window_bars, context, after = counts[inst.symbol]
        assert after > 0, "the store holds no bar after W: the test would prove nothing"
        assert m["count"] == window_bars + context, inst.symbol
        assert set(m["arrays"].values()) == {window_bars + context}, inst.symbol
        assert m["latest_open"] is None  # the mount carries no timestamp
    expected = container.expected_mount(job, tc.instruments, calendars, window)
    assert [(e.count, e.window) for e in expected] == [
        (sum(counts[i.symbol][:2]), counts[i.symbol][0]) for i in tc.instruments]
    # The limits the runtime set, read from inside, are the copied run.toml's.
    settings = load_run(config).sandbox
    lim = report["limits"]
    assert lim["pids.max"] == str(settings.pids)
    assert lim["memory.max"] == str(job.limits.memory_bytes)
    assert lim["memory.swap.max"] == "0"
    quota, period = (int(v) for v in lim["cpu.max"].split())
    assert quota == round(settings.cpus * period)
    assert lim["rlimit_cpu"] == [1200, 1201] == [math.ceil(job.limits.cpu_seconds),
                                                 math.ceil(job.limits.cpu_seconds) + 1]
    findings = judge(report, expected, container.required_limits(job.limits, settings))
    assert all(f.ok for f in findings), [f for f in findings if not f.ok]
    assert b.started and not any(container.container_exists(b.runtime(), n)
                                 for n in b.started)
    assert list((tmp_path / "scratch").iterdir()) == []  # the job directory is removed


@pytest.mark.container
def test_sandbox_selftest_prints_one_pass_line_per_finding_and_exits_0(
        backends, capsys, synth_state, tc, config):
    assert main(["--state", str(synth_state), "--config", str(config), "--track", SYNTH,
                 "--as-of", AS_OF, "sandbox", "selftest"]) == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith(("PASS ", "FAIL "))]
    want = [*ALL[:-2], *(f"mount.{i.symbol}" for i in tc.instruments)]
    assert [ln.split(":")[0].split(" ", 1)[1] for ln in lines] == want
    assert all(ln.startswith("PASS ") for ln in lines), out
    assert f"day {DAY.isoformat()}" in out
    assert f"W {W_FIRST.isoformat()} to {W_LAST.isoformat()}" in out
    assert len(backends) == 1 and len(backends[0].started) == 1


def test_selftest_needs_a_state_directory(monkeypatch, capsys):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    monkeypatch.setattr(container, "find_runtime", lambda configured: "/nonexistent/docker")
    monkeypatch.setattr(container, "image_present", lambda runtime, ref: True)
    _no_start(monkeypatch)
    assert main(["--as-of", AS_OF, "sandbox", "selftest"]) == 1
    assert "no state directory" in capsys.readouterr().err


def test_the_probe_runs_on_the_host_and_reports_a_json_document(tmp_path, monkeypatch):
    """The probe's report on a job directory, run here as a function (no container,
    no new process, no connection: the connection attempt is replaced). Its text is
    compiled here, so no bytecode is written under sandbox/."""
    import types
    probe = types.ModuleType("probe_under_test")
    exec(compile(PROBE.read_text(encoding="utf-8"), str(PROBE), "exec"), probe.__dict__)
    monkeypatch.setattr(probe, "connect", lambda: {"target": "x", "connected": False,
                                                   "error": "stubbed"})
    # Every create goes under the test's temporary directory, never the host's own.
    under = [tmp_path / n for n in ("root", "usr", "home", "tmp")]
    for d in under:
        d.mkdir()
    monkeypatch.setattr(probe, "CREATE_UNDER", tuple(str(d) for d in under))
    import numpy as np
    job = tmp_path / "job"
    job.mkdir()
    np.savez(job / "bars-0.npz", close=np.arange(5.0), hour=np.arange(5),
             ts=np.array(["2019-07-08T20:00", "2019-07-08T21:00", "2019-07-08T22:00",
                          "2019-07-09T13:00", "2019-07-08T23:00"], dtype="datetime64[ns]"))
    (job / "job.json").write_text(json.dumps({"instruments": [{"bars": "bars-0.npz"}]}),
                                  encoding="utf-8")
    report = probe.report(str(job))
    json.dumps(report)
    (m,) = report["mount"]["instruments"]
    assert m["count"] == 5 and m["arrays"] == {"close": 5, "hour": 5, "ts": 5}
    assert m["latest_open"] == "2019-07-09T13:00:00+00:00"
    creates = {c["under"]: c for c in report["creates"]}
    assert list(creates) == [*(str(d) for d in under[:3]), str(job), str(under[3])]
    assert all(c["created"] for c in creates.values())
    assert all(list(d.iterdir()) == [] for d in under)  # each created file removed
    assert not (job / probe.PROBE_FILE).exists()
    assert sorted(f["name"] for f in report["mount"]["files"]) == ["bars-0.npz", "job.json"]
