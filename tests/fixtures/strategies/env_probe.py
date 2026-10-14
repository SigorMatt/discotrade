"""Reports on its process's environment: a test of the child-process backend's
allow-list (DESIGN 12.4, decision 96, I-13). Run only through
``discotrade.sandbox.process`` in ``tests/test_sandbox_process.py``.

``probe`` 0: 1.0 when the fake key variable the test sets in the harness is in
the environment, else 0.0. ``probe`` 1: 1.0 when the environment holds a
variable outside the backend's allow-list, else 0.0."""

import os

PARAMS = {"probe": 0}


def position(bars, params):
    if params["probe"] == 0:
        return 1.0 if "DISCOTRADE_TEST_FAKE_API_KEY" in os.environ else 0.0
    from discotrade.sandbox.process import CHILD_ENV
    return 0.0 if set(os.environ) <= set(CHILD_ENV) else 1.0
