# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "the IO functions of numpy".
# Stage: static (DESIGN 12.1), rule forbidden_attribute: it names the attribute save of numpy.
# Otherwise its position returns 0. It is refused before it runs.

import numpy as np

PARAMS = {}


def position(bars, params):
    saver = np.save  # noqa: F841
    return 0.0
