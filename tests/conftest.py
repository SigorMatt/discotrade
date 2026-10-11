"""Shared test configuration.

Under ``DISCOTRADE_GATE=1`` (set by ``scripts/gate``) a test that would skip
fails instead: a gate never passes by skipping (DESIGN 18.2).

A test that lives under ``tests/gates/`` or carries a ``gate_m0`` to
``gate_m5`` marker must carry ``gate`` and exactly one milestone marker;
collection fails otherwise, naming the test (DESIGN 18.1; decision 9 of
meta/decisions/decisions-2026-10-12.md). The check runs before ``-m``
deselects anything, so it holds under every selection.
"""

import os
from pathlib import Path

import pytest

GATE_ENV = "DISCOTRADE_GATE"
GATES_DIR = Path(__file__).resolve().parent / "gates"
MILESTONES = tuple(f"gate_m{n}" for n in range(6))


def gate_marker_problem(item) -> str | None:
    """Why ``item``'s gate markers are wrong, or None when they are right."""
    names = {mark.name for mark in item.iter_markers()}
    milestones = sorted(names.intersection(MILESTONES))
    under_gates = GATES_DIR in Path(item.path).resolve().parents
    if not under_gates and not milestones:
        return None
    if "gate" not in names:
        return "has no 'gate' marker"
    if len(milestones) != 1:
        found = ", ".join(milestones) or "none"
        return f"needs exactly one milestone marker gate_m0..gate_m5 (found: {found})"
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    problems = [
        f"{item.nodeid}: {why}" for item in items if (why := gate_marker_problem(item))
    ]
    if problems:
        raise pytest.UsageError(
            "gate markers: a test under tests/gates/ or marked gate_m<n> must carry "
            "'gate' and exactly one milestone marker:\n  " + "\n  ".join(problems)
        )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if os.environ.get(GATE_ENV) == "1" and report.skipped:
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else report.longrepr
        report.outcome = "failed"
        report.longrepr = f"skipped under {GATE_ENV}=1, which is a failure: {reason}"
