"""Allocates memory without end: a test of the child-process backend's memory limit
(DESIGN 12.4, decision 96). Run only through ``discotrade.sandbox.process``, under
a memory limit, in ``tests/test_sandbox_process.py``."""

PARAMS = {"chunk": 67108864}


def position(bars, params):
    held = []
    while True:
        held.append(bytearray(int(params["chunk"])))
