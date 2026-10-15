# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "an attribute walk from a literal to object".
# Stage: static (DESIGN 12.1), rule underscore: it names the attribute __class__ of a literal.
# Otherwise its position returns 0. It is refused before it runs.

PARAMS = {}


def position(bars, params):
    walked = ().__class__  # noqa: F841
    return 0.0
