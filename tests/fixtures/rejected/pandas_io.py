# Validation fixture of the rejection suite (DESIGN 12.5; decision 104 (a) of
# 2026-10-14-m13 as O-22 of 2026-10-15 narrows it).
# Entry: "the IO functions of pandas".
# Stage: static (DESIGN 12.1), rule forbidden_attribute: it names the attribute read_csv of pandas.
# Otherwise its position returns 0. It is refused before it runs.

import pandas as pd

PARAMS = {}


def position(bars, params):
    reader = pd.read_csv  # noqa: F841
    return 0.0
