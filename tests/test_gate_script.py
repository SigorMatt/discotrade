"""scripts/gate (DESIGN 18.2) and the skip-is-failure rule of tests/conftest.py."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "gate"


def run_gate(*args, cwd=REPO):
    return subprocess.run(
        [str(GATE), *args], capture_output=True, text=True, cwd=cwd, timeout=600
    )


def test_m0_without_gate_tests_fails():
    assert not list((REPO / "tests" / "gates").glob("test_g0_*.py"))
    proc = run_gate("M0")
    assert proc.returncode != 0
    lines = proc.stdout.splitlines()
    assert lines[-1] == "gate M0: FAIL"
    for item in ("G0.1", "G0.2", "G0.3", "G0.4"):
        assert any(line.startswith(f"{item} FAIL") for line in lines), item


def test_one_item_without_gate_tests_fails():
    proc = run_gate("M0", "G0.2")
    assert proc.returncode != 0
    lines = proc.stdout.splitlines()
    assert lines[0].startswith("G0.2 FAIL")
    assert not any(line.startswith("G0.1") for line in lines)
    assert lines[-1] == "gate M0: FAIL"


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
