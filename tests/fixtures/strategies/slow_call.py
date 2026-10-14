"""Slow on its first call: the first call after the text is loaded sleeps
``pause`` seconds, longer than ``validation.call_max_ms`` (500 ms), and every
call returns 0. It imports ``time``, which the static check refuses (DESIGN
12.1): it is run only through stage 2 by ``tests/test_validation_grid.py``, to
show that the child-process backend does not enforce the call-time limits
(DESIGN 12.2; decision 2026-10-14-m12 97 (a)).
"""

import time

PARAMS = {"pause": 0.6}
CALLS = []


def position(bars, params):
    if not CALLS:
        CALLS.append(1)
        time.sleep(params["pause"])
    return 0.0
