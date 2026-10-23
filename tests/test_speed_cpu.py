"""``scripts/speed`` measures CPU time in its own cgroup, with a load backstop
(O-32 items 1, 2 and 6 of meta/decisions/2026-10-21-owner.md, which amends O-26
item 4 of meta/decisions/2026-10-18-owner.md and decisions 156 and 170; I-12).

``scripts/speed.py`` is loaded from its file. The cgroup, ``systemd-run`` and
the load source are fakes written here: no real ``systemd-run`` runs and no
file under ``/proc`` or ``/sys`` is read. The tests prove three things:

- no fallback: when no cgroup can be made (``systemd-run`` missing, or failing
  to make the scope), when the call's cgroup is not a scope of its own, or when
  its ``cpu.stat`` cannot be read or holds no ``usage_usec``, the measurement
  stops with an error and a non-zero status, prints no figure and writes no
  day line;
- the void rule: a run whose two windows' average loads differ by more than
  1.0 is VOID, by at most 1.0 valid; the averages are computed here from the
  fake samples;
- the refusal of a sandbox backend whose work runs outside the cgroup.

The work directory is the test's temporary directory, and no replay day runs.
"""

import importlib.util
import json
from datetime import date
from types import SimpleNamespace

import pytest

from discotrade.cli import REPO_ROOT

FIRST, LAST = date(2019, 6, 3), date(2020, 6, 10)


def load_speed():
    path = REPO_ROOT / "scripts" / "speed.py"
    spec = importlib.util.spec_from_file_location("speed_cpu_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------- no cgroup, no fallback

def test_no_systemd_run_is_an_error_with_no_fallback(capsys):
    speed = load_speed()
    execs = []
    status = speed.enter_scope(["--work", "/tmp/x"], which=lambda name: None,
                               run=lambda *a, **k: pytest.fail("probe ran"),
                               execvpe=lambda *a: execs.append(a))
    assert status == 1 and execs == []
    err = capsys.readouterr().err
    assert "systemd-run" in err and "no fallback to wall time" in err


def test_a_scope_that_cannot_be_made_is_an_error_with_no_fallback(capsys):
    speed = load_speed()
    execs, probes = [], []

    def run(cmd, **kwargs):
        probes.append(cmd)
        return SimpleNamespace(returncode=1, stdout="", stderr="Failed to connect to bus\n")

    status = speed.enter_scope(["--work", "/tmp/x"], which=lambda name: "/usr/bin/" + name,
                               run=run, execvpe=lambda *a: execs.append(a))
    assert status == 1 and execs == []
    assert probes and probes[0][:4] == ["/usr/bin/systemd-run", "--user", "--scope", "--quiet"]
    err = capsys.readouterr().err
    assert "Failed to connect to bus" in err and "no fallback to wall time" in err


def test_a_made_scope_re_executes_the_call_inside_it():
    speed = load_speed()
    execs = []

    def run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    speed.enter_scope(["--work", "/tmp/x"], which=lambda name: "/usr/bin/" + name, run=run,
                      execvpe=lambda *a: execs.append(a))
    [(file, cmd, env)] = execs
    assert file == "/usr/bin/systemd-run"
    assert cmd[:5] == ["/usr/bin/systemd-run", "--user", "--scope", "--quiet", "--"]
    assert cmd[-2:] == ["--work", "/tmp/x"]
    assert env[speed.SCOPE_ENV] == "1"


def write_proc(tmp_path, cgroup_line, procs, stat):
    proc = tmp_path / "proc-self-cgroup"
    proc.write_text(cgroup_line + "\n", encoding="utf-8")
    root = tmp_path / "cgroup"
    path = root / "user.slice" / "run-u7.scope"
    path.mkdir(parents=True)
    (path / "cgroup.procs").write_text("".join(f"{p}\n" for p in procs), encoding="utf-8")
    if stat is not None:
        (path / "cpu.stat").write_text(stat, encoding="utf-8")
    return proc, root


def test_the_own_cgroup_reads_usage_usec(tmp_path):
    speed = load_speed()
    proc, root = write_proc(tmp_path, "0::/user.slice/run-u7.scope", [41],
                            "usage_usec 2500000\nuser_usec 2000000\n")
    group = speed.own_cgroup(proc=proc, root=root, pid=41)
    assert group.seconds() == 2.5


@pytest.mark.parametrize("line, procs, stat, says", [
    ("0::/user.slice/session-2.scope/x", [41], "usage_usec 1\n", "not a scope"),
    ("0::/user.slice/run-u7.scope", [41, 42], "usage_usec 1\n", "not its own"),
    ("0::/user.slice/run-u7.scope", [41], None, "cpu.stat"),
    ("0::/user.slice/run-u7.scope", [41], "user_usec 1\n", "usage_usec"),
    ("1:name=systemd:/x", [41], "usage_usec 1\n", "cgroup v2"),
])
def test_a_cgroup_that_is_not_usable_is_refused(tmp_path, line, procs, stat, says):
    speed = load_speed()
    proc, root = write_proc(tmp_path, line, procs, stat)
    with pytest.raises(speed.CgroupError, match=says):
        speed.own_cgroup(proc=proc, root=root, pid=41)


def test_main_stops_with_an_error_when_no_cgroup_is_made(tmp_path, monkeypatch, capsys):
    speed = load_speed()

    def refuse():
        raise speed.CgroupError("the call is not in a scope of its own")

    monkeypatch.setattr(speed, "open_cgroup", refuse)
    work = tmp_path / "work"
    assert speed.main(["--work", str(work)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "not in a scope of its own" in err and "no fallback to wall time" in err
    assert not (work / speed.DAYS_FILE).exists()


def test_main_stops_with_an_error_when_cpu_stat_cannot_be_read(tmp_path, monkeypatch, capsys):
    speed = load_speed()

    class BrokenCgroup:
        def seconds(self):
            raise speed.CgroupError("cannot read /sys/fs/cgroup/x/cpu.stat")

    monkeypatch.setattr(speed, "open_cgroup", BrokenCgroup)
    work = tmp_path / "work"
    assert speed.main(["--work", str(work)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "cpu.stat" in err and "no fallback to wall time" in err
    assert not (work / speed.DAYS_FILE).exists()


# ------------------------------------------------------------- the void rule

def samples(first, last):
    """Load samples tagged with days of the first and the last window."""
    return ([{"date": "2019-06-04", "load": x} for x in first]
            + [{"date": "2019-08-01", "load": 9.0}]          # outside both windows
            + [{"date": "2020-06-09", "load": x} for x in last])


@pytest.mark.parametrize("first, last", [
    ([1.0, 2.0], [2.0, 3.0, 2.5]),        # averages 1.5 and 2.5: 1.0 apart
    ([3.25, 3.75], [2.5, 2.5]),           # 3.5 and 2.5: 1.0 apart, the other way
    ([0.5, 0.75, 0.25], [0.5]),           # 0.5 and 0.5
    ([1.0, 2.0], [2.0, 3.0, 2.75]),       # 1.5 and 2.5833...: more than 1.0
    ([4.0], [2.5, 3.25]),                 # 4.0 and 2.875: more than 1.0
    ([0.0, 0.25], [1.5, 1.0]),            # 0.125 and 1.25: more than 1.0
])
def test_the_void_rule(first, last):
    speed = load_speed()
    avg1, avg2 = sum(first) / len(first), sum(last) / len(last)
    void = abs(avg1 - avg2) > 1.0
    lines = speed.load_lines(samples(first, last), FIRST, LAST)
    assert lines[0] == ("speed load first30: " + " ".join(f"{x:.2f}" for x in first)
                        + f" (average {avg1:.3f})")
    assert lines[1] == ("speed load last30: " + " ".join(f"{x:.2f}" for x in last)
                        + f" (average {avg2:.3f})")
    if void:
        assert lines[2].startswith("speed: VOID: ")
        assert f"{abs(avg1 - avg2):.3f}" in lines[2] and "not counted" in lines[2]
    else:
        assert lines[2] == (f"speed load: valid, the windows' average loads differ by "
                            f"{abs(avg1 - avg2):.3f} (at most 1.0)")
    assert len(lines) == 3


def test_a_window_with_no_load_sample_is_void():
    speed = load_speed()
    lines = speed.load_lines(samples([], [1.0]), FIRST, LAST)
    assert lines[0] == "speed load first30: (no sample)"
    assert lines[2].startswith("speed: VOID: ") and "no load sample" in lines[2]


def test_the_load_sampler_samples_only_inside_the_windows():
    speed = load_speed()
    reads = iter([0.5, 0.75, 1.25])
    sampler = speed.LoadSampler(lambda: next(reads), interval=30.0)
    sampler.day = date(2019, 6, 4)
    sampler.tick()
    sampler.day = None
    sampler.tick()                    # outside both windows: nothing read
    sampler.day = date(2020, 6, 9)
    sampler.tick()
    sampler.tick()
    assert sampler.samples == [{"date": "2019-06-04", "load": 0.5},
                               {"date": "2020-06-09", "load": 0.75},
                               {"date": "2020-06-09", "load": 1.25}]
    assert speed.LOAD_INTERVAL == 30.0


def test_the_load_average_is_the_first_field_of_loadavg(tmp_path):
    speed = load_speed()
    path = tmp_path / "loadavg"
    path.write_text("1.73 0.92 0.40 2/913 12345\n", encoding="utf-8")
    assert speed.read_loadavg(path) == 1.73


# ------------------------------------------------------------- the backend

def test_a_backend_outside_the_cgroup_is_refused(tmp_path, monkeypatch, capsys):
    speed = load_speed()

    class Group:
        def seconds(self):
            return 1.0

    monkeypatch.setattr(speed, "open_cgroup", Group)
    monkeypatch.setattr(speed, "replay_backend", lambda instruments: "container")
    work = tmp_path / "work"
    assert speed.main(["--work", str(work)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "container" in err and "outside" in err and "cgroup" in err
    assert not (work / speed.DAYS_FILE).exists()
    assert speed.INSIDE_CGROUP == ("process",)


def test_the_replay_backend_of_the_g1_3_track_is_the_process_backend():
    speed = load_speed()
    from discotrade.config import load_track_config
    tc = load_track_config(speed.FIXTURE_CONFIG, speed.TRACK)
    assert speed.replay_backend(tc.instruments) == "process"


def test_the_samples_file_holds_json_lines(tmp_path):
    speed = load_speed()
    path = tmp_path / speed.LOAD_FILE
    speed.append_samples(path, [{"date": "2019-06-04", "load": 0.5}])
    speed.append_samples(path, [{"date": "2020-06-09", "load": 1.0}])
    assert [json.loads(x) for x in path.read_text("utf-8").splitlines()] == [
        {"date": "2019-06-04", "load": 0.5}, {"date": "2020-06-09", "load": 1.0}]
    assert speed.read_days(path) == [{"date": "2019-06-04", "load": 0.5},
                                     {"date": "2020-06-09", "load": 1.0}]
