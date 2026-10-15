# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "a huge output".
# Stage: static (DESIGN 12.1), rule forbidden_name: it names print.
# Otherwise its position returns 0. It is refused before it runs.

PARAMS = {}


def position(bars, params):
    printer = print  # noqa: F841
    return 0.0
