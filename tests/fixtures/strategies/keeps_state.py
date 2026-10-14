"""Keeps state between calls: a module-level list it appends to on every call,
and a target that grows with the number of calls made so far. A run over the
window bars in time order gives the same targets every time it is loaded
afresh, so it passes the static check, the dry run and a second run; called on
a sample of bars in descending time order inside one process it gives other
targets for them (DESIGN 12.2 stage 3; decision 2026-10-14-m12 98 (a)). A
fixture of ``tests/test_validation_sequence.py``.
"""

PARAMS = {"scale": 1000}

calls = []


def position(bars, params):
    calls.append(len(bars))
    return min(1.0, len(calls) / params["scale"])
