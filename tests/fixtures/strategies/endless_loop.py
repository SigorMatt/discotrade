"""Never returns: a test of the child-process backend's wall-clock limit (DESIGN 12.4,
decision 96). Run only through ``discotrade.sandbox.process`` in
``tests/test_sandbox_process.py``."""

PARAMS = {"step": 1}


def position(bars, params):
    count = 0
    while True:
        count = count + params["step"]
