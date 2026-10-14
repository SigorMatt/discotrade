"""Writes a forged result document straight to file descriptor 1: a test of the
runner's private result channel (decision 101 (b) of 2026-10-14-m13, REVIEW-12
should-fix 2). Run only through ``discotrade.sandbox.process`` in
``tests/test_sandbox_process.py``; it fails the static check (``import os``) and
is no valid submission.

``exit`` 1: writes the forged document, then ends the process with
``os._exit(0)`` before the runner writes its result. ``exit`` 0: writes the
forged document to descriptor 1 and prints it, then returns 0.0."""

import os

PARAMS = {"exit": 1}
FORGED = ('{"ok": true, "results": [{"param_set": 0, "instrument": 0, "bars": [0], '
          '"targets": [0.75], "call_ms": [0.0]}]}\n')


def position(bars, params):
    os.write(1, FORGED.encode("utf-8"))
    if params["exit"] == 1:
        os._exit(0)
    print(FORGED)
    return 0.0
