"""Allocates a fixed amount of memory, once: a test of one configured limit, the
container backend's memory limit (DESIGN 12.4; O-22 item 4 of
decisions-2026-10-15-owner). Its first call allocates ``ALLOCATE_BYTES`` (512 MiB),
every byte written, and holds it for the rest of the run; every call returns 0.
That is above the short memory limit of the ``run.toml`` that
``tests/test_sandbox_limits.py`` copies under its temporary directory and below the
production one. It runs only through the container backend, in
``tests/test_sandbox_limits.py``.
"""

ALLOCATE_BYTES = 536870912
PARAMS = {}
HELD = []


def position(bars, params):
    if not HELD:
        HELD.append(b"\x01" * ALLOCATE_BYTES)
    return 0.0
