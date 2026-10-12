"""The cost model (DESIGN 7.3, 5.7; decisions 2026-10-12 24, 26; R-3, R-5; I-4).

Every expected value below is computed by hand from the formulas of DESIGN
7.3 with the fixture records' numbers (SYNA: per-contract fee 0.5, multiplier
10, tick 0.25, the fixture spread table; SYNX: 5 basis points, tick 0.25;
both: 1 tick main, 2 ticks off, slippage coefficient 0.02). They prove the
formulas as written, not that any cost is realistic.
"""

import shutil
import statistics
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import pytest

from discotrade import costs
from discotrade.cli import REPO_ROOT
from discotrade.config import load_calendar, load_instrument, load_track_config
from discotrade.spreads import spread_table, spread_ticks

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "config"


@pytest.fixture(scope="module")
def syna():
    return load_instrument(FIXTURE / "instruments" / "SYNA.toml")


@pytest.fixture(scope="module")
def synx():
    return load_instrument(FIXTURE / "instruments" / "SYNX.toml")


@pytest.fixture(scope="module")
def week():
    return load_calendar(FIXTURE / "calendars" / "synth_week.toml")


def test_version_is_c1():
    assert costs.VERSION == "c1"


# --- fee --------------------------------------------------------------------------------


def test_fee_per_contract_is_fee_over_multiplier_times_raw_open(syna):
    assert costs.fee(syna, 4000.0) == pytest.approx(0.5 / (10.0 * 4000.0), rel=1e-15)
    assert costs.fee(syna, 2000.0) == pytest.approx(2.5e-5, rel=1e-15)


def test_fee_bps_is_proportional_and_does_not_depend_on_price(synx):
    assert costs.fee(synx, 50000.0) == pytest.approx(5e-4, rel=1e-15)
    assert costs.fee(synx, 1.0) == pytest.approx(5e-4, rel=1e-15)


# --- half spread and the spread rule of 5.7 -----------------------------------------------


def test_half_spread_is_half_the_ticks_times_tick_over_raw_open_with_a_half_tick_floor(syna):
    assert costs.half_spread(syna, 2.0, 4000.0) == pytest.approx(0.25 / 4000.0, rel=1e-15)
    assert costs.half_spread(syna, 1.25, 4000.0) == pytest.approx(0.15625 / 4000.0, rel=1e-15)
    # Below one tick the half spread is floored at half a tick.
    assert costs.half_spread(syna, 0.4, 4000.0) == pytest.approx(0.125 / 4000.0, rel=1e-15)
    assert costs.half_spread(syna, 0.0, 4000.0) == pytest.approx(0.125 / 4000.0, rel=1e-15)


def test_half_spread_reads_syna_table_by_exchange_local_hour(syna, week):
    table = spread_table(FIXTURE, "SYNA")
    assert table is not None
    # 2019-06-04 is a Tuesday in EDT (UTC-4): 14:00 UTC is 10:00 local, 13:00 UTC is 09:00.
    ten = datetime(2019, 6, 4, 14, tzinfo=UTC)
    nine = datetime(2019, 6, 4, 13, tzinfo=UTC)
    three = datetime(2019, 6, 4, 7, tzinfo=UTC)
    assert spread_ticks(syna, week, table, ten) == 1.25
    assert spread_ticks(syna, week, table, nine) == 1.0
    assert spread_ticks(syna, week, table, three) == 2.5
    o = 4000.0
    assert costs.half_spread(syna, spread_ticks(syna, week, table, ten), o) == \
        pytest.approx(0.625 * 0.25 / o, rel=1e-15)
    assert costs.half_spread(syna, spread_ticks(syna, week, table, nine), o) == \
        pytest.approx(0.5 * 0.25 / o, rel=1e-15)
    assert costs.half_spread(syna, spread_ticks(syna, week, table, three), o) == \
        pytest.approx(1.25 * 0.25 / o, rel=1e-15)
    # In winter (EST, UTC-5) the same UTC hour is another local hour: 14:00 UTC is 09:00.
    winter = datetime(2019, 12, 3, 14, tzinfo=UTC)
    assert spread_ticks(syna, week, table, winter) == 1.0


def test_half_spread_without_a_table_is_main_or_off_session(syna, week):
    main = datetime(2019, 6, 4, 14, tzinfo=UTC)      # 10:00 local, a Tuesday
    off = datetime(2019, 6, 4, 2, tzinfo=UTC)        # 22:00 local on Monday
    assert spread_ticks(syna, week, None, main) == 1.0
    assert spread_ticks(syna, week, None, off) == 2.0
    o = 4000.0
    assert costs.half_spread(syna, spread_ticks(syna, week, None, main), o) == \
        pytest.approx(0.125 / o, rel=1e-15)
    assert costs.half_spread(syna, spread_ticks(syna, week, None, off), o) == \
        pytest.approx(0.25 / o, rel=1e-15)


# --- sigma and slippage ------------------------------------------------------------------


def test_sigma_is_zero_with_fewer_than_two_returns():
    close = np.array([100.0, 101.0, 99.0, 102.0])
    sig = costs.sigma(close, np.zeros(4))
    # sigma(u) uses r(s) for s up to u-1, and r(0) has no previous bar.
    assert sig[0] == 0.0 and sig[1] == 0.0 and sig[2] == 0.0
    assert sig[3] == pytest.approx(statistics.stdev([1 / 100, -2 / 101]), rel=1e-12)


def test_sigma_returns_are_adjusted_as_of_s_over_the_raw_previous_close():
    close = np.array([100.0, 101.0, 112.0, 113.0, 110.0])
    gaps = np.array([0.0, 0.0, 10.0, 0.0, 0.0])        # a roll at bar 2, gap 10
    r = costs.returns(close, gaps)
    assert np.isnan(r[0])
    assert r[1:].tolist() == pytest.approx([1 / 100, (112 - 111) / 101, 1 / 112, -3 / 113],
                                           rel=1e-15)
    sig = costs.sigma(close, gaps)
    assert sig[4] == pytest.approx(statistics.stdev([1 / 100, 1 / 101, 1 / 112]), rel=1e-12)


def test_sigma_uses_the_last_24_returns_with_ddof_1():
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0.0, 1.0, 40))
    gaps = np.zeros(40)
    gaps[20] = 3.0
    r = [(close[s] - close[s - 1] - gaps[s]) / close[s - 1] for s in range(1, 40)]
    sig = costs.sigma(close, gaps)
    for u in range(26, 40):
        want = statistics.stdev(r[u - 25:u - 1])          # r(s), s = u-24 .. u-1
        assert sig[u] == pytest.approx(want, rel=1e-12)
        assert sig[u] != pytest.approx(statistics.stdev(r[u - 26:u - 1]), rel=1e-9)
    # With fewer than 24 returns all of them are used.
    assert sig[10] == pytest.approx(statistics.stdev(r[0:9]), rel=1e-12)


def test_slip_is_the_coefficient_times_sigma(syna):
    assert costs.slip(syna, 0.002) == pytest.approx(0.02 * 0.002, rel=1e-15)
    assert costs.slip(syna, 0.0) == 0.0


# --- roll cost, cost and net ----------------------------------------------------------------


def test_roll_cost_is_paid_by_a_carried_position_only():
    c = 0.0004
    assert costs.roll_cost(0.5, c, True) == pytest.approx(2 * 0.5 * c, rel=1e-15)
    assert costs.roll_cost(-1.0, c, True) == pytest.approx(2 * 1.0 * c, rel=1e-15)
    assert costs.roll_cost(0.0, c, True) == 0.0       # flat: nothing to roll
    assert costs.roll_cost(0.7, c, False) == 0.0      # no roll at this bar


def test_cost_and_net_at_1x_and_2x():
    unit = costs.unit_cost(5e-4, 2e-5, 4e-5)
    assert unit == pytest.approx(5.6e-4, rel=1e-15)
    roll = costs.roll_cost(0.5, unit, True)
    total = costs.cost(1.5, unit, roll)
    assert total == pytest.approx(1.5 * 5.6e-4 + 5.6e-4, rel=1e-15)
    assert costs.net(0.01, total, 1) == pytest.approx(0.01 - total, rel=1e-15)
    assert costs.net(0.01, total, 2) == pytest.approx(0.01 - 2 * total, rel=1e-15)


# --- the config hash (decision 26) -----------------------------------------------------------


def _hash(config, track):
    cfg = load_track_config(config, track)
    return costs.config_hash(cfg.instruments,
                             {i.symbol: spread_table(config, i.symbol) for i in cfg.instruments})


def test_cost_tables_hold_the_values_of_decision_26(syna, synx):
    table = spread_table(FIXTURE, "SYNA")
    tables = costs.cost_tables([syna, synx], {"SYNA": table, "SYNX": None})
    assert tables == {
        "SYNA": {"cost": {"fee_per_side": 0.5, "spread_ticks_main": 1.0,
                          "spread_ticks_off": 2.0, "slippage_coef": 0.02},
                 "tick_size": 0.25, "multiplier": 10.0, "spread_table": list(table.ticks)},
        "SYNX": {"cost": {"fee_bps": 5.0, "spread_ticks_main": 1.0,
                          "spread_ticks_off": 2.0, "slippage_coef": 0.02},
                 "tick_size": 0.25, "spread_table": None},
    }


def test_config_hash_is_stable_across_runs():
    here = _hash(FIXTURE, "test_mixed")
    assert len(here) == 64 and int(here, 16) >= 0
    assert _hash(FIXTURE, "test_mixed") == here
    code = ("from pathlib import Path; from discotrade import costs; "
            "from discotrade.config import load_track_config; "
            "from discotrade.spreads import spread_table; "
            f"p = Path({str(FIXTURE)!r}); c = load_track_config(p, 'test_mixed'); "
            "print(costs.config_hash(c.instruments, "
            "{i.symbol: spread_table(p, i.symbol) for i in c.instruments}))")
    for seed in ("1", "2"):
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             check=True, env={"PYTHONHASHSEED": seed}, timeout=120)
        assert out.stdout.strip() == here


def _edit(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new))


@pytest.fixture
def fixture_copy(tmp_path):
    path = tmp_path / "config"
    shutil.copytree(FIXTURE, path)
    return path


def test_config_hash_changes_with_a_cost_value(fixture_copy):
    before = _hash(fixture_copy, "test_mixed")
    _edit(fixture_copy / "instruments" / "SYNA.toml", "slippage_coef = 0.02",
          "slippage_coef = 0.03")
    assert _hash(fixture_copy, "test_mixed") != before


def test_config_hash_changes_with_tick_size(fixture_copy):
    before = _hash(fixture_copy, "test_mixed")
    _edit(fixture_copy / "instruments" / "SYNX.toml", "tick_size = 0.25", "tick_size = 0.5")
    assert _hash(fixture_copy, "test_mixed") != before


def test_config_hash_changes_with_one_spread_table_value(fixture_copy):
    before = _hash(fixture_copy, "test_mixed")
    _edit(fixture_copy / "spreads" / "SYNA.toml", "1.5, 1.0, 1.25,", "1.5, 1.0, 1.5,")
    assert _hash(fixture_copy, "test_mixed") != before


def test_config_hash_is_unchanged_by_a_companion(fixture_copy, tmp_path):
    before = _hash(fixture_copy, "test_mixed")
    table = fixture_copy / "spreads" / "SYNA.toml"
    _edit(table, 'checked = "2026-10-12"', 'checked = "2026-10-13"')
    _edit(table, 'source = "invented for tests"', 'source = "another text"')
    _edit(table, "verified = false", "verified = true")
    _edit(table, 'description = "invented', 'description = "changed: invented')
    assert _hash(fixture_copy, "test_mixed") == before
    # The repository's own records carry [cost] companions: change all three.
    real = tmp_path / "real"
    shutil.copytree(REPO_ROOT / "config", real)
    first = _hash(real, "hourly")
    for path in sorted((real / "instruments").glob("*.toml")):
        text = path.read_text()
        start = text.index("[cost]")
        end = text.index("\n[", start + 1)
        block = text[start:end]
        changed = block.replace("verified = false", "verified = true")
        changed = changed.replace('checked = "', 'checked = "2000-01-01" # was "', 1)
        changed = changed.replace('source = "', 'source = "edited: ', 1)
        assert changed != block
        path.write_text(text[:start] + changed + text[end:])
        assert load_instrument(path).cost.provenance.verified is True
    assert _hash(real, "hourly") == first


def test_config_hash_covers_multiplier(syna):
    tables = {"SYNA": None}
    assert costs.config_hash([syna], tables) != \
        costs.config_hash([replace(syna, multiplier=20.0)], tables)
