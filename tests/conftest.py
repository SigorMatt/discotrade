"""Shared test configuration.

Under ``DISCOTRADE_GATE=1`` (set by ``scripts/gate``) a test that would skip
fails instead: a gate never passes by skipping (DESIGN 18.2).
"""

import os

import pytest

GATE_ENV = "DISCOTRADE_GATE"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if os.environ.get(GATE_ENV) == "1" and report.skipped:
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else report.longrepr
        report.outcome = "failed"
        report.longrepr = f"skipped under {GATE_ENV}=1, which is a failure: {reason}"
