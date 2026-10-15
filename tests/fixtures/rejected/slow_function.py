# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "a slow function".
# Stage: dry_run (DESIGN 12.2 stage 2, rule call_max on the container backend):
# the first call after each load counts to `loops`, which takes longer than
# call_max_ms (500 ms); every call returns 0. The work is bounded by `loops`.
# It passes the static check.

PARAMS = {"loops": 15000000}
DONE = []


def position(bars, params):
    if not DONE:
        DONE.append(1)
        count = 0
        while count < params["loops"]:
            count = count + 1
    return 0.0
