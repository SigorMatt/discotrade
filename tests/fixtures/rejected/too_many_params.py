# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "too many parameters".
# Stage: static (DESIGN 12.1), rule max_params: PARAMS has six entries, one above max_params.
# Otherwise its position returns 0. It is refused before it runs.

PARAMS = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6}


def position(bars, params):
    return 0.0
