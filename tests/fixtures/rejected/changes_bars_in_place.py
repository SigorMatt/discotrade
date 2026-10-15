# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "changing bars in place".
# Stage: activity (DESIGN 12.2 stage 4, rule min_changes_w): position overwrites
# a column of the bars it is given and holds a flat position, so it makes no
# position change on W. Each call gets its own slice (DESIGN 6.2), so the change
# reaches neither a later call nor the harness's own bars. It passes the static
# check.

PARAMS = {"mark": -1.0}


def position(bars, params):
    bars["volume"] = params["mark"]
    return 0.0
