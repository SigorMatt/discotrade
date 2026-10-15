"""Waits a fixed time, once: a test of one configured limit, the container
backend's wall-clock limit (DESIGN 12.4; O-22 item 4 of
decisions-2026-10-15-owner). Its first call sleeps ``WAIT_SECONDS`` (10 s), longer
than the short wall-clock limit of the ``run.toml`` that
``tests/test_sandbox_limits.py`` copies under its temporary directory and far
shorter than the production one; every call returns 0. It imports ``time``, which
the static check refuses (DESIGN 12.1): it runs only through the container
backend, in ``tests/test_sandbox_limits.py``.
"""

import time

WAIT_SECONDS = 10.0
PARAMS = {}
WAITED = []


def position(bars, params):
    if not WAITED:
        WAITED.append(1)
        time.sleep(WAIT_SECONDS)
    return 0.0
