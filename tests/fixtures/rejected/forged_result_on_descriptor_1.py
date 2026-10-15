# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "a forged result written to descriptor 1".
# Stage: static (DESIGN 12.1), rule import: it imports write from os.
# Otherwise its position returns 0. It is refused before it runs.

from os import write  # noqa: F401

PARAMS = {}


def position(bars, params):
    return 0.0
