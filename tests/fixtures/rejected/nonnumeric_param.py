# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "a non-numeric parameter".
# Stage: static (DESIGN 12.1), rule param_value: a PARAMS value is a string.
# Otherwise its position returns 0. It is refused before it runs.

PARAMS = {"a": "text"}


def position(bars, params):
    return 0.0
