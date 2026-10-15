# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "a result that is not a number".
# Stage: dry_run (DESIGN 12.2 stage 2): position returns None, which is not a
# number (runner rule not_a_number). It passes the static check.

PARAMS = {}


def position(bars, params):
    return None
