# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "a class named from the data".
# Stage: static (DESIGN 12.1), rule construct: it defines a class.
# Otherwise its position returns 0. It is refused before it runs.

PARAMS = {}


class Named(Exception):
    pass


def position(bars, params):
    return 0.0
