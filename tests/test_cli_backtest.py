"""The ``backtest`` command (DESIGN 3, 8; decisions 2026-10-12 21, 27; I-4).

One state directory per module, filled by ``bars fetch`` on ``test_mixed``
at a fixed ``--as-of``; each reference strategy is run over a fixed window of
more than sixty trading days.
"""

import contextlib
import io
import json
import math
import shutil
from datetime import date

import pandas as pd
import pytest

from discotrade.backtest import evaluate
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange, load_calendar, load_thresholds, load_track_config
from discotrade.costs import config_hash
from discotrade.spreads import spread_table
from discotrade.strategy import load_strategy_file
from discotrade.tradingcal import trading_date

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-07-02T00:00:00+00:00"
FIRST, LAST = "2019-04-01", "2019-06-28"
FILES = ("trend_ma.py", "zscore_reversal.py", "hour_of_day.py")
SYMBOLS = ("SYNA", "SYNL", "SYNX")
METRICS = ("total_return", "total_return_2x", "sharpe", "sharpe_2x", "max_drawdown",
           "trades", "avg_holding_bars", "breakeven_cost", "fragile")
COSTS = ("fee", "spread", "slippage", "roll")


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def state(tmp_path_factory, config):
    state = tmp_path_factory.mktemp("bt") / "state"
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    return state


def backtest(state, config, file, *extra, first=FIRST, last=LAST):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "backtest", str(file), "--from", first, "--to", last,
                 *extra])


@pytest.fixture(scope="module")
def outputs(state, config):
    """The ``--json`` output text of each reference strategy, run once."""
    out = {}
    for name in FILES:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = backtest(state, config, REPO_ROOT / "reference" / name, "--json")
        assert code == 0, name
        out[name] = buf.getvalue()
    return out


def test_window_holds_at_least_sixty_trading_days(config):
    cal = load_calendar(config / "calendars" / "synth_week.toml")
    days = pd.date_range(FIRST, LAST, freq="D", tz="UTC")
    trading = {trading_date(cal, (d + pd.Timedelta(hours=h)).to_pydatetime())
               for d in days for h in range(24)}
    trading = {d for d in trading if date.fromisoformat(FIRST) <= d <= date.fromisoformat(LAST)}
    assert len(trading) >= 60


@pytest.mark.parametrize("name", FILES)
def test_json_holds_every_metric_costs_version_and_hash(name, outputs, config):
    text = outputs[name]
    assert text.count("\n") == 1 and "NaN" not in text and "Infinity" not in text
    result = json.loads(text)
    for key in METRICS:
        assert key in result, key
        value = result[key]
        assert value is None or isinstance(value, int | float)
        if isinstance(value, float):
            assert math.isfinite(value)
    assert isinstance(result["fragile"], bool)
    assert isinstance(result["trades"], int)
    assert result["days"] >= 60
    assert set(result["costs"]) == set(COSTS)
    assert all(isinstance(result["costs"][k], float) for k in COSTS)
    assert result["cost_model"] == "c1"
    cfg = load_track_config(config, TRACK)
    tables = {i.symbol: spread_table(config, i.symbol) for i in cfg.instruments}
    assert result["config_hash"] == config_hash(cfg.instruments, tables)


def test_a_value_that_is_not_a_number_is_null(state, config, tmp_path, capsys):
    # A one-day window gives one day, so its Sharpe is not a number (DESIGN 8).
    assert backtest(state, config, REPO_ROOT / "reference" / "hour_of_day.py", "--json",
                    first="2019-06-27", last="2019-06-27") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["days"] == 1
    assert result["sharpe"] is None and result["sharpe_2x"] is None


@pytest.mark.parametrize("name", FILES)
def test_each_strategy_trades_on_each_instrument_and_never_shorts_synl(name, outputs):
    per = json.loads(outputs[name])["instruments"]
    assert sorted(per) == sorted(SYMBOLS)
    for symbol in SYMBOLS:
        assert per[symbol]["trades"] > 0, symbol
    assert per["SYNL"]["position_min"] >= 0.0
    assert sum(per[s]["trades"] for s in SYMBOLS) == json.loads(outputs[name])["trades"]


def test_some_strategy_pays_a_roll_cost_on_syna(outputs):
    rolls = [json.loads(outputs[name])["instruments"]["SYNA"]["roll"] for name in FILES]
    assert any(r > 0 for r in rolls)
    # Only SYNA rolls.
    for name in FILES:
        per = json.loads(outputs[name])["instruments"]
        assert per["SYNL"]["roll"] == 0.0 and per["SYNX"]["roll"] == 0.0


def test_cost_totals_are_the_subject_totals_of_the_instruments(outputs):
    for name in FILES:
        result = json.loads(outputs[name])
        per = result["instruments"]
        for k in COSTS:
            assert result["costs"][k] == pytest.approx(
                sum(per[s][k] for s in SYMBOLS) / len(SYMBOLS), rel=1e-12, abs=1e-15)
        assert result["total_return"] == pytest.approx(
            sum(per[s]["net_1x"] for s in SYMBOLS) / len(SYMBOLS), rel=1e-9, abs=1e-15)


def test_syna_spread_cost_comes_from_its_fixture_table(state, config, outputs):
    cfg = load_track_config(config, TRACK)
    inst = {i.symbol: i for i in cfg.instruments}["SYNA"]
    cal = load_calendar(config / "calendars" / f"{inst.calendar}.toml")
    strat = load_strategy_file(REPO_ROOT / "reference" / "trend_ma.py",
                               load_thresholds(config / "thresholds.toml"))
    window = DateRange(date.fromisoformat(FIRST), date.fromisoformat(LAST))
    table = spread_table(config, "SYNA")
    assert table is not None
    with_table = evaluate(state, cfg.track, inst, cal, strat, window, spread_table=table)
    without = evaluate(state, cfg.track, inst, cal, strat, window)
    shown = json.loads(outputs["trend_ma.py"])["instruments"]["SYNA"]["spread"]
    assert shown == float(with_table.rows["spread"].sum())
    assert shown != float(without.rows["spread"].sum())


@pytest.mark.parametrize("name", FILES)
def test_two_runs_give_byte_identical_json(name, state, config, outputs, capsys):
    capsys.readouterr()
    assert backtest(state, config, REPO_ROOT / "reference" / name, "--json") == 0
    assert capsys.readouterr().out == outputs[name]


def test_a_file_outside_reference_exits_2(state, config, capsys):
    outside = REPO_ROOT / "tests" / "fixtures" / "strategies" / "valid_import.py"
    assert backtest(state, config, outside) == 2
    assert "reference" in capsys.readouterr().err


def test_a_path_that_climbs_out_of_reference_exits_2(state, config):
    climbing = REPO_ROOT / "reference" / ".." / "tests" / "fixtures" / "strategies" \
        / "valid_import.py"
    assert backtest(state, config, climbing) == 2


def test_from_after_to_exits_2(state, config, capsys):
    assert backtest(state, config, REPO_ROOT / "reference" / "trend_ma.py",
                    first="2019-06-28", last="2019-04-01") == 2
    assert "--from" in capsys.readouterr().err


def test_a_refused_bar_file_exits_1(tmp_path, config, state, capsys):
    copy = tmp_path / "state"
    shutil.copytree(state, copy)
    store = BarStore(copy, TRACK, 3600)
    path = store.month_path("SYNL", "2019-05")
    revised = pd.read_parquet(path)
    revised.loc[1, "close"] = revised.loc[1, "close"] + 1e-9
    revised.to_parquet(path, index=False)
    capsys.readouterr()
    assert backtest(copy, config, REPO_ROOT / "reference" / "trend_ma.py") == 1
    assert "SYNL" in capsys.readouterr().err


def test_plain_output_prints_no_gross_figure_without_the_net_ones(state, config, capsys):
    capsys.readouterr()
    assert backtest(state, config, REPO_ROOT / "reference" / "trend_ma.py") == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert any("breakeven_cost" in line for line in lines)
    for line in lines:
        if "gross" in line or "breakeven" in line:
            assert "net_1x" in line and "net_2x" in line, line
    assert "c1" in out and "config hash" in out
    for key in ("sharpe_2x", "total_return_2x", "max_drawdown", "avg_holding_bars",
                "fragile", "trades"):
        assert key in out, key
