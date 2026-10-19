"""The table's random-slot figures with O-4's subtraction taken for every slot
at once (O-26 items 2 and 3 of meta/decisions/2026-10-18-owner.md; decision 158
of meta/decisions/decisions-2026-10-18-m20.md; decision 2026-10-17-m19 148 (a);
DESIGN 10.4).

``table.adjusted_deflated`` with ``exposure`` gives the figures the parent gave
bit for bit: the approach's ``paper.adjusted`` Sharpe, and ``E_N`` from
the moments of every random slot's ``paper.adjusted`` Sharpe over the
approach's days, computed here one slot at a time without calling
``adjusted_deflated``; with one row per slot and date these are
``stats.control_moments``' moments (the figure before mission 20). A slot
holding two rows of one date takes the scalar subtraction over both rows, as
at d67f708 (finding D-021: ``stats.control_moments`` keeps the last of them).
The records are written by the product's writers
(``tests/test_alerts_cache.py``'s ``write_records``) from
``numpy.random.default_rng(SEED)``; nothing reads a clock.
"""

import math
import shutil

import numpy as np
import pandas as pd
import pytest
from test_alerts_cache import SEED, SLOTS, TRACK, W, write_records

from discotrade import journal, paper, state, stats, table
from discotrade.cli import REPO_ROOT
from discotrade.metrics import sharpe

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    config = tmp_path_factory.mktemp("tscfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copyfile(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    return journal.Setup.load(config, TRACK)


def own(root, setup, records, days, n):
    wanted = set(days)
    near = records[records["date"].isin(wanted)]
    s = sharpe(paper.adjusted(root, setup, "a-1", days, "net_1x", records=near))
    frames, sharpes = [], []
    for slot in sorted(f"rc:{j}" for j in range(SLOTS)):       # the frame's subject order
        if set(near[near["subject"] == slot]["date"]) != wanted:
            continue
        series = paper.adjusted(root, setup, slot, days, "net_1x", records=near)
        frames.append(pd.DataFrame({"subject": slot, "kind": stats.CONTROL_RANDOM,
                                    "date": list(series.index),
                                    table.SLOT_COLUMN: series.to_numpy(dtype=np.float64)}))
        if not math.isnan(sharpe(series)):
            sharpes.append(sharpe(series))
    x = np.asarray(sharpes, dtype=np.float64)
    mu, sd = float(np.mean(x)), float(np.std(x, ddof=1))
    plain = stats.control_moments(pd.concat(frames, ignore_index=True), days,
                                  column=table.SLOT_COLUMN)
    e_n = stats.expected_max(mu, sd, n)
    return {"adjusted_S": s, "adjusted_E_N": e_n,
            "adjusted_excess": stats.excess(s, e_n)}, (mu, sd) == plain


@pytest.mark.parametrize("twice", [None, "rc:5"])
def test_the_slot_figures_are_the_parents_bit_for_bit(tmp_path, setup, twice):
    state.clear_caches()
    root = tmp_path / "state"
    records, exposure = write_records(root, np.random.default_rng(SEED), twice=twice)
    days = sorted(W)
    for n in (2, 7, 40):
        want, as_control_moments = own(root, setup, records, days, n)
        assert as_control_moments == (twice is None)
        got = table.adjusted_deflated(root, setup, "a-1", days, n, records, exposure=exposure)
        assert all(math.isfinite(v) for v in want.values())
        assert {k: repr(v) for k, v in got.items()} == {k: repr(v) for k, v in want.items()}
