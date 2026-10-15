# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "state kept between calls by a mutable default argument".
# Stage: determinism (DESIGN 12.2 stage 3, rule reverse_sample): a helper's
# mutable default counts the calls made since the text was loaded, and the
# position grows with that count. Called on W's bars in time order it gives the
# same positions on every fresh load, so it passes the dry run and the second
# run; called on a sample of bars in reverse order inside one process it gives
# other positions for them. It passes the static check.

PARAMS = {"scale": 1000}


def calls(made=[]):  # noqa: B006
    made.append(1)
    return len(made)


def position(bars, params):
    return min(1.0, calls() / params["scale"])
