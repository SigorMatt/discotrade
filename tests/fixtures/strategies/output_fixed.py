"""Returns the same 17-digit number at every bar: a test of one configured limit,
the container backend's output cap (DESIGN 12.4; O-22 item 4 of
decisions-2026-10-15-owner). Its result's size is fixed by ``POSITION`` and the
job's bars (each target written as ``POSITION``'s 19 characters), longer than the
short output cap of the ``run.toml`` that ``tests/test_sandbox_limits.py`` copies
under its temporary directory and far shorter than the production one. It runs
only through the container backend, in ``tests/test_sandbox_limits.py``.
"""

POSITION = 0.12345678901234568
PARAMS = {}


def position(bars, params):
    return POSITION
