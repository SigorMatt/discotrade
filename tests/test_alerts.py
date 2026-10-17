"""The rank rows of the day loop on the timing statistic (DESIGN 11.1, 15.1,
16.1 step 6; owner decisions O-4, O-5, O-6, O-24; decisions 2026-10-12 59,
2026-10-17-m19 149).

``alerts.rank_rows`` is called on a state written under the test's tmp
directory by the writers the product uses (``paper.write`` for the paper
records, ``paper.write_exposure`` for the unit and position records), on the
fixture track ``test_synth`` (``epoch`` 2019-06-03, ``block_days`` 7, four
instruments on ``synth_week``, so the trading days of block 0 are 06-03..07
and of block 1 06-10..14), with the fixture configuration and the production
``config/thresholds.toml`` (``alerts.rank_min_population`` 5, asserted).

The values are drawn in the test from ``numpy.random.default_rng(SEED)`` with
the seed written here: each instrument's unit return ``R_i(D)`` per day; six
approaches ``lean0..lean5`` whose position on each instrument leans one way in
block 0 and another in block 1 and moves around that lean each day, their
gross the mean over the instruments of position times unit return plus a
draw, their costs a draw; and one approach ``const`` holding a constant
position on each instrument, its gross the mean of those positions times the
unit returns. Every expected figure is the test's own: ``hbar_i`` of a block
as the summed position over the row count of the block's days, the static
exposure as the mean over the instruments of ``hbar_i * R_i(D)``, the timing
sums with ``math.fsum``, the ranks by counting and the correlation with
``math``. Nothing here calls ``paper.adjusted`` or ``stats.rank_persistence``
for an expected value. The tests prove the rows on these inputs only.
"""

import math
import shutil
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade import alerts, journal, paper, stats
from discotrade.cli import REPO_ROOT

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
SEED = 20191017
SYMBOLS = ("SYNA", "SYNB", "SYNC", "SYND")
BLOCK_0 = [date(2019, 6, 3) + timedelta(days=i) for i in range(5)]
BLOCK_1 = [date(2019, 6, 10) + timedelta(days=i) for i in range(5)]
DAYS = BLOCK_0 + BLOCK_1
ROWS = 10                                   # journal rows per subject, instrument and day
CONST = (1.0, -0.5, 0.25, 0.8)              # const's position on each instrument
LEANS = [((1.5, 0.5, -1.0, 0.0), (-1.0, 1.0, 0.5, -0.5)),
         ((-0.5, 1.5, 0.0, 1.0), (1.0, -1.0, 1.5, 0.0)),
         ((0.0, -1.0, 1.0, 1.5), (0.5, 0.5, -1.5, 1.0)),
         ((1.0, 1.0, 1.0, 1.0), (-1.0, -1.0, -1.0, -1.0)),
         ((-1.5, 0.0, 0.5, -0.5), (1.5, 0.0, -0.5, 0.5)),
         ((0.5, -0.5, 1.5, -1.5), (0.0, 1.5, -0.5, 1.0))]
OLD_KEYS = {"block", "first", "last", "previous_first", "previous_last", "subjects", "size",
            "statistic"}


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    config = tmp_path_factory.mktemp("alcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copyfile(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    return journal.Setup.load(config, TRACK)


def test_the_fixture_and_production_values(setup):
    assert tuple(sorted(i.symbol for i in setup.instruments)) == SYMBOLS
    assert setup.track.epoch == date(2019, 6, 3) and setup.track.block_days == 7
    assert int(setup.thresholds["alerts.rank_min_population"]) == 5
    assert all(d.weekday() < 5 for d in DAYS)


def draw():
    """The test's inputs: unit returns, positions and paper rows, all drawn here."""
    rng = np.random.default_rng(SEED)
    unit = {(s, d): float(rng.normal(0.002, 0.01)) for d in DAYS for s in SYMBOLS}
    held = {}                                # (subject, symbol, day) -> position per row
    gross, cost = {}, {}
    for j, (lean_0, lean_1) in enumerate(LEANS):
        name = f"lean{j}"
        for d in DAYS:
            lean = lean_0 if d in BLOCK_0 else lean_1
            for s, h in zip(SYMBOLS, lean, strict=True):
                held[(name, s, d)] = h + float(rng.normal(0.0, 0.3))
            gross[(name, d)] = (math.fsum(held[(name, s, d)] * unit[(s, d)] for s in SYMBOLS)
                                / 4 + float(rng.normal(0.0, 0.004)))
            cost[(name, d)] = float(rng.uniform(0.0, 0.01))
    for d in DAYS:
        for s, h in zip(SYMBOLS, CONST, strict=True):
            held[("const", s, d)] = h
        gross[("const", d)] = math.fsum(h * unit[(s, d)]
                                        for s, h in zip(SYMBOLS, CONST, strict=True)) / 4
        cost[("const", d)] = float(rng.uniform(0.0, 0.01))
    return unit, held, gross, cost


def write_state(root):
    unit, held, gross, cost = draw()
    records = pd.DataFrame([{"date": d, "subject": subject, "kind": paper.APPROACH,
                             "gross": g, "net_1x": g - cost[(subject, d)],
                             "net_2x": g - 2 * cost[(subject, d)], "trades": 1, "clean": True}
                            for (subject, d), g in sorted(gross.items())])
    paper.write(root, TRACK, records)
    units = pd.DataFrame([{"instrument": s, "date": d, "unit": v}
                          for (s, d), v in sorted(unit.items())])
    positions = pd.DataFrame([{"subject": subject, "instrument": s, "date": d, "rows": ROWS,
                               "position": ROWS * h}
                              for (subject, s, d), h in sorted(held.items())])
    paper.write_exposure(root, TRACK, units, positions)
    return unit, held, gross, cost


@pytest.fixture(scope="module")
def state(tmp_path_factory):
    root = tmp_path_factory.mktemp("alstate") / "state"
    return root, write_state(root)


def subjects(setup):
    basket = [setup.calendars[inst.calendar] for inst in setup.instruments]
    return {name: basket for name in ["const"] + [f"lean{j}" for j in range(len(LEANS))]}


def own_ranks(values):
    return [sum(1 for w in values if w < v) + (sum(1 for w in values if w == v) + 1) / 2
            for v in values]


def own_spearman(x, y):
    rx, ry = own_ranks(x), own_ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den


def own_hbar(held, subject, window):
    """``hbar_i`` over ``window``: summed position over the row count."""
    return {s: math.fsum(ROWS * held[(subject, s, d)] for d in window) / (ROWS * len(window))
            for s in SYMBOLS}


def own_timing(unit, held, gross, subject, block, window):
    """The subject's gross timing return on each day of ``block``, its average
    positions taken over ``window`` (the block itself, under O-5)."""
    hbar = own_hbar(held, subject, window)
    return [gross[(subject, d)] - math.fsum(hbar[s] * unit[(s, d)] for s in SYMBOLS) / 4
            for d in block]


def own_statistics(unit, held, gross, cost, names):
    sums = {"timing": ([], []), "one_window": ([], []), "gross": ([], []), "net_1x": ([], [])}
    for name in names:
        for b, block in enumerate((BLOCK_0, BLOCK_1)):
            sums["timing"][b].append(math.fsum(own_timing(unit, held, gross, name, block,
                                                          block)))
            sums["one_window"][b].append(math.fsum(own_timing(unit, held, gross, name, block,
                                                              DAYS)))
            sums["gross"][b].append(math.fsum(gross[(name, d)] for d in block))
            sums["net_1x"][b].append(math.fsum(gross[(name, d)] - cost[(name, d)]
                                               for d in block))
    return {k: own_spearman(*v) for k, v in sums.items()}


def test_a_constant_position_approach_has_a_timing_return_of_zero_on_every_day(setup, state):
    root, _ = state
    frames = []
    alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1],
                     frames=frames)
    [frame] = frames
    mine = frame[frame["subject"] == "const"]
    assert sorted(mine["date"]) == DAYS
    assert all(abs(float(v)) <= 1e-12 for v in mine["timing"])
    # the leaning approaches' timing returns are not zero, so the bound says something
    lean = frame[frame["subject"] == "lean0"]
    assert max(abs(float(v)) for v in lean["timing"]) > 1e-4


def test_the_row_holds_timing_and_gross_beside_decision_59s_net_statistic(setup, state):
    root, (unit, held, gross, cost) = state
    [row] = alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1])
    names = sorted(subjects(setup))
    own = own_statistics(unit, held, gross, cost, names)
    # the test's inputs tell the four figures apart, so each wrong reading shows
    for a, b in (("timing", "gross"), ("timing", "net_1x"), ("timing", "one_window"),
                 ("gross", "net_1x")):
        assert abs(own[a] - own[b]) > 1e-3, (a, b, own)
    assert set(row) == OLD_KEYS | {"timing", "gross"}
    assert row["subjects"] == names and row["size"] == len(names)
    assert (row["block"], row["first"], row["last"], row["previous_first"],
            row["previous_last"]) == (1, "2019-06-10", "2019-06-16", "2019-06-03",
                                      "2019-06-09")
    assert abs(row["timing"] - own["timing"]) <= 1e-12
    assert abs(row["gross"] - own["gross"]) <= 1e-12
    assert abs(row["statistic"] - own["net_1x"]) <= 1e-12     # decision 59's, unchanged


def test_exposure_records_passed_give_the_rows_read_from_the_files(setup, state):
    root, _ = state
    records = paper.read(root, TRACK)
    exposure = (paper.read_unit(root, TRACK), paper.read_positions(root, TRACK))
    read = alerts.rank_rows(root, setup, records, subjects(setup), [1])
    given = alerts.rank_rows(root, setup, records, subjects(setup), [1], exposure=exposure)
    assert given == read


def test_rows_appended_again_append_nothing(tmp_path, setup, state):
    root = tmp_path / "state"
    shutil.copytree(state[0], root)
    rows = alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1])
    assert stats.append_rank_rows(root, TRACK, rows) == rows
    before = stats.rank_path(root, TRACK).read_bytes()
    again = alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1])
    assert again == rows
    assert stats.append_rank_rows(root, TRACK, again) == []
    assert stats.rank_path(root, TRACK).read_bytes() == before


def test_an_empty_population_gives_every_statistic_null(setup, state):
    root, _ = state
    [row] = alerts.rank_rows(root, setup, paper.read(root, TRACK), {}, [1])
    assert row["size"] == 0 and row["subjects"] == []
    assert row["statistic"] is None and row["timing"] is None and row["gross"] is None


def test_below_the_minimum_population_every_statistic_is_null(setup, state):
    root, _ = state
    few = dict(list(subjects(setup).items())[:4])
    [row] = alerts.rank_rows(root, setup, paper.read(root, TRACK), few, [1])
    assert row["size"] == 4
    assert row["statistic"] is None and row["timing"] is None and row["gross"] is None


def test_no_due_block_gives_no_row(setup, state):
    root, _ = state
    assert alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), []) == []
