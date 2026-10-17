"""scripts/gate (DESIGN 18.2) and the skip-is-failure rule of tests/conftest.py."""

import importlib.machinery
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "gate"


def run_gate(*args, cwd=REPO):
    # Decision 45: every run below is of an item or milestone that takes
    # seconds, and the timeout is generous so that load cannot turn it red.
    return subprocess.run(
        [str(GATE), *args], capture_output=True, text=True, cwd=cwd, timeout=1200
    )


def test_milestone_without_gate_tests_fails():
    # M4 has no gate test yet (M3 gained its gate tests in mission 17, U5).
    assert not list((REPO / "tests" / "gates").glob("test_g4_*.py"))
    proc = run_gate("M4")
    assert proc.returncode != 0
    lines = proc.stdout.splitlines()
    assert lines[-1] == "gate M4: FAIL"
    items = [line.split()[0] for line in lines[:-1] if line.startswith("G4.")]
    assert items == ["G4.1", "G4.2", "G4.3", "G4.4", "G4.5", "G4.6"], lines
    for item in items:
        assert any(line.startswith(f"{item} FAIL") for line in lines), item


def test_m2_counts_five_items():
    # Five items for M2: G2.5 added by O-22 item 4 (decisions-2026-10-15-owner).
    assert _gate_module().ITEMS["M2"] == 5


def test_one_item_without_gate_tests_fails():
    # An M4 item: M3's items gained their gate tests in mission 17 (U5).
    assert not list((REPO / "tests" / "gates").glob("test_g4_2_*.py"))
    proc = run_gate("M4", "G4.2")
    assert proc.returncode != 0
    lines = proc.stdout.splitlines()
    assert lines[0].startswith("G4.2 FAIL")
    assert not any(line.startswith("G4.1") for line in lines)
    assert lines[-1] == "gate M4 G4.2: FAIL"
    assert "gate M4: FAIL" not in lines


@pytest.mark.parametrize("args", [[], ["M9"], ["M0", "G1.1"], ["M0", "G0.1", "x"]])
def test_usage_errors_exit_2(args):
    proc = run_gate(*args)
    assert proc.returncode == 2
    assert "usage" in proc.stderr


def _scratch_suite(tmp_path, body):
    shutil.copy(REPO / "tests" / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "test_scratch.py").write_text(body)


def _pytest(tmp_path, gate):
    env = {k: v for k, v in os.environ.items() if k != "DISCOTRADE_GATE"}
    if gate:
        env["DISCOTRADE_GATE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(tmp_path)],
        capture_output=True, text=True, cwd=tmp_path, env=env, timeout=120,
    )


SKIPPING = """
import pytest

def test_skips_in_call():
    pytest.skip("no runtime")

@pytest.mark.skip(reason="marked")
def test_marked_skip():
    pass

@pytest.mark.skipif(True, reason="condition")
def test_skipif():
    pass

def test_passes():
    pass
"""


def test_a_skip_is_a_skip_outside_a_gate(tmp_path):
    _scratch_suite(tmp_path, SKIPPING)
    proc = _pytest(tmp_path, gate=False)
    assert proc.returncode == 0, proc.stdout
    assert "1 passed, 3 skipped" in proc.stdout


def test_a_skip_is_a_failure_under_discotrade_gate(tmp_path):
    _scratch_suite(tmp_path, SKIPPING)
    proc = _pytest(tmp_path, gate=True)
    assert proc.returncode == 1, proc.stdout
    # A skip in the call phase fails; a skip marker is evaluated at setup, so
    # it becomes an error. Either way nothing is reported as skipped.
    assert "1 failed, 1 passed, 2 errors" in proc.stdout
    assert "skipped" not in proc.stdout.splitlines()[-1]
    assert "DISCOTRADE_GATE" in proc.stdout


# --- decision 9 (REVIEW-1 should-fix 7) ----------------------------------------


def test_one_item_run_never_prints_the_milestone_verdict():
    # G0.4 (decision 45): its tests take seconds; G0.3 replays for minutes.
    proc = run_gate("M0", "G0.4")
    lines = proc.stdout.splitlines()
    assert lines[-1] in ("gate M0 G0.4: PASS", "gate M0 G0.4: FAIL")
    assert "gate M0: PASS" not in proc.stdout
    assert "gate M0: FAIL" not in proc.stdout
    assert (proc.returncode == 0) == (lines[-1] == "gate M0 G0.4: PASS")


def _gate_module():
    loader = importlib.machinery.SourceFileLoader("scripts_gate", str(GATE))
    module = types.ModuleType(loader.name)
    module.__file__ = str(GATE)
    loader.exec_module(module)
    return module


@pytest.mark.parametrize("ok", [True, False])
def test_one_item_verdict_follows_the_item(ok, monkeypatch, capsys):
    gate = _gate_module()
    monkeypatch.setattr(gate, "run_item", lambda milestone, item: (ok, "1 passed"))
    code = gate.main(["M0", "g0.3"])
    lines = capsys.readouterr().out.splitlines()
    verdict = "PASS" if ok else "FAIL"
    assert lines == [f"G0.3 {verdict} 1 passed", f"gate M0 G0.3: {verdict}"]
    assert code == (0 if ok else 1)


@pytest.mark.parametrize("ok", [True, False])
def test_whole_milestone_prints_the_milestone_verdict(ok, monkeypatch, capsys):
    gate = _gate_module()
    monkeypatch.setattr(gate, "run_item", lambda milestone, item: (ok, "1 passed"))
    code = gate.main(["M0"])
    lines = capsys.readouterr().out.splitlines()
    verdict = "PASS" if ok else "FAIL"
    assert len(lines) == 5 and lines[-1] == f"gate M0: {verdict}"
    assert code == (0 if ok else 1)


def _marker_suite(tmp_path, files):
    """A scratch suite: tests/conftest.py (the repository's) and the given test files."""
    tests = tmp_path / "tests"
    (tests / "gates").mkdir(parents=True)
    shutil.copy(REPO / "tests" / "conftest.py", tests / "conftest.py")
    for name, body in files.items():
        (tests / name).write_text(body)
    return tests


def _collect(tests, *args):
    env = {k: v for k, v in os.environ.items() if k != "DISCOTRADE_GATE"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "-W", "ignore::pytest.PytestUnknownMarkWarning", *args, str(tests)],
        capture_output=True, text=True, cwd=tests.parent, env=env, timeout=120,
    )


GOOD = """
import pytest

@pytest.mark.gate
@pytest.mark.gate_m0
def test_good():
    pass
"""

ONLY_MILESTONE = """
import pytest

def test_plain():
    pass

@pytest.mark.gate_m0
def test_milestone_without_gate():
    pass
"""

ONLY_GATE = """
import pytest

@pytest.mark.gate
def test_gate_without_milestone():
    pass
"""

UNMARKED = """
def test_unmarked():
    pass
"""

TWO_MILESTONES = """
import pytest

@pytest.mark.gate
@pytest.mark.gate_m0
@pytest.mark.gate_m1
def test_two_milestones():
    pass
"""


@pytest.mark.parametrize("selection", [[], ["-m", "not gate"], ["-m", "gate_m0"]])
def test_well_marked_gate_tests_collect(tmp_path, selection):
    tests = _marker_suite(tmp_path, {"gates/test_g0_1_good.py": GOOD, "test_plain.py": UNMARKED})
    proc = _collect(tests, *selection)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize(
    "name, body, test",
    [
        ("test_scratch.py", ONLY_MILESTONE, "test_milestone_without_gate"),
        ("gates/test_g0_1_x.py", ONLY_GATE, "test_gate_without_milestone"),
        ("gates/test_g0_1_y.py", UNMARKED, "test_unmarked"),
        ("gates/test_g0_1_z.py", TWO_MILESTONES, "test_two_milestones"),
        ("test_scratch.py", TWO_MILESTONES, "test_two_milestones"),
    ],
)
@pytest.mark.parametrize("selection", [[], ["-m", "not gate"], ["-m", "gate_m0"]])
def test_badly_marked_test_fails_collection_naming_it(tmp_path, name, body, test, selection):
    tests = _marker_suite(tmp_path, {name: body, "test_plain.py": UNMARKED})
    proc = _collect(tests, *selection)
    out = proc.stdout + proc.stderr
    assert proc.returncode not in (0, 5), out
    assert f"{name.split('/')[-1]}::{test}" in out
    assert " passed" not in out
