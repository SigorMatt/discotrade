"""G1.1: a replay of one year of the null market with controls only, on the gate
configuration (DESIGN 18.3 G1.1, 18.2, 10.1, 11.1, 8; decisions 2026-10-12 59,
64, 70, 72, 74; I-4).

One controls-only replay (no approach, no candidate) of the fixture track
``test_synth`` on decision 72's gate configuration, from ``FIRST`` 2019-06-03
(the track's ``epoch``) to ``LAST`` 2020-06-01, into a state directory made by
``init-state`` under the test's tmp directory at ``INIT_AS_OF``; the replay
runs in-process through ``discotrade.cli.main`` once, in a module-scoped
fixture, and every test below asserts on it. Over the
``controls.random_pool`` slots (50 in the gate configuration), each slot's
sums taken over its paper rows of the year, with SE the sample standard
deviation over the slots (ddof 1) divided by the square root of their number:

- the mean summed ``gross`` is within four SE of 0;
- the mean summed cost (``gross - net_1x``) is positive;
- the mean summed ``net_1x`` is within four SE (of the summed ``net_1x``) of
  minus the mean summed cost;
- decision 59's statistic (``stats.rank_persistence``), computed for each block
  completed in the year with the random slots as the population, has at least
  40 values that are not missing, and their mean is within four SE of 0;
- ``stats/test_synth/rank_persistence.jsonl`` holds one row per completed
  block, blocks 1 to 51 (decision 70: block ``k`` is the 7 days from
  2019-06-03 + 7k; block 51 is 2020-05-25 to 2020-05-31, the last that ends by
  ``LAST``; block 0 has no block before it).

Seeds: the synthetic instruments' seeds are those of their fixture records
(``SEEDS``, asserted); the random pool's draws are seeded by decision 64 with
the month (``YYYYMM``), and the test asserts the 13 draws' seeds 201906 to
202006. No other random draw is made. Time comes only from ``--as-of`` and the
replay's clock.
"""

import math
from datetime import date

import numpy as np
import pytest
from m1_harness import gate_config, init_state, read_jsonl, read_paper, replay

from discotrade import journal, stats
from discotrade.config import load_track_config

pytestmark = [pytest.mark.gate, pytest.mark.gate_m1]

TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
FIRST, LAST = date(2019, 6, 3), date(2020, 6, 1)
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
POOL_SEEDS = [201906, 201907, 201908, 201909, 201910, 201911, 201912,
              202001, 202002, 202003, 202004, 202005, 202006]
SLOTS = 50
BLOCKS = list(range(1, 52))
MIN_VALUES = 40


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    root = tmp_path_factory.mktemp("g11")
    config = gate_config(root)
    state = init_state(root / "state", INIT_AS_OF)
    status, out, err = replay(state, config, TRACK, FIRST, LAST)
    assert status == 0, err
    return state, config, out


@pytest.fixture(scope="module")
def setup(ran):
    return journal.Setup.load(ran[1], TRACK)


@pytest.fixture(scope="module")
def records(ran):
    return read_paper(ran[0], TRACK)


@pytest.fixture(scope="module")
def slot_sums(records, setup):
    assert int(setup.thresholds["controls.random_pool"]) == SLOTS
    mine = records[records["kind"] == "control_random"]
    assert sorted(set(mine["subject"])) == sorted(f"rc:{k}" for k in range(SLOTS))
    assert min(mine["date"]) == FIRST and max(mine["date"]) <= LAST
    sums = {}
    for subject, rows in mine.groupby("subject", sort=True):
        gross = math.fsum(float(x) for x in rows["gross"])
        net = math.fsum(float(x) for x in rows["net_1x"])
        sums[str(subject)] = (gross, net, gross - net)
    return sums


def mean_se(values) -> tuple[float, float]:
    x = np.asarray(values, dtype=np.float64)
    return float(np.mean(x)), float(np.std(x, ddof=1)) / math.sqrt(len(x))


def test_seeds_dates_and_controls_only(ran, records, setup):
    state, config, out = ran
    tc = load_track_config(config, TRACK)
    assert {inst.symbol: inst.source.get("seed") for inst in tc.instruments} == SEEDS
    assert tc.track.epoch == FIRST
    assert int(setup.track.block_days) == 7
    assert set(records["kind"]) == {"control_random", "control_bh", "portfolio"}
    assert not (state / "approaches").exists() or not any((state / "approaches").iterdir())
    pools = read_jsonl(state / "controls" / TRACK / "pools.jsonl")
    assert [p["seed"] for p in pools] == POOL_SEEDS
    days = out.splitlines()
    assert days[0].startswith(f"replay: {TRACK} {FIRST.isoformat()} ")
    assert days[-1].startswith(f"replay: {TRACK} {LAST.isoformat()} ")


def test_mean_summed_gross_is_within_four_se_of_zero(slot_sums):
    mean, se = mean_se([g for g, _, _ in slot_sums.values()])
    assert se > 0
    assert abs(mean) <= 4 * se, (mean, se)


def test_mean_summed_cost_is_positive(slot_sums):
    cost = math.fsum(c for _, _, c in slot_sums.values()) / len(slot_sums)
    assert cost > 0, cost


def test_mean_summed_net_is_within_four_se_of_minus_the_cost(slot_sums):
    mean, se = mean_se([n for _, n, _ in slot_sums.values()])
    cost = math.fsum(c for _, _, c in slot_sums.values()) / len(slot_sums)
    assert se > 0
    assert abs(mean - (-cost)) <= 4 * se, (mean, cost, se)


def test_rank_persistence_of_the_random_slots_is_centred_on_zero(records, setup):
    cal = setup.calendars["synth_week"]
    subjects = {f"rc:{k}": [cal] for k in range(SLOTS)}
    values = []
    for k in BLOCKS:
        row = stats.rank_persistence(
            records, subjects, epoch=FIRST, block_days=7, bar_seconds=3600, k=k,
            min_population=int(setup.thresholds["alerts.rank_min_population"]))
        first, last = stats.block_dates(FIRST, 7, k)
        assert last <= LAST
        if row["statistic"] is not None:
            values.append(row["statistic"])
    assert len(values) >= MIN_VALUES, len(values)
    mean, se = mean_se(values)
    assert abs(mean) <= 4 * se, (mean, se, len(values))


def test_one_rank_persistence_row_per_completed_block(ran):
    rows = read_jsonl(ran[0] / "stats" / TRACK / "rank_persistence.jsonl")
    assert [r["block"] for r in rows] == BLOCKS
    assert rows[0]["first"] == "2019-06-10" and rows[0]["previous_first"] == "2019-06-03"
    assert rows[-1]["first"] == "2020-05-25" and rows[-1]["last"] == "2020-05-31"
    # Controls only: the day loop's population (approaches) is empty.
    assert all(r["size"] == 0 and r["statistic"] is None for r in rows)
