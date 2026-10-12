"""The executor and the per-bar rows (DESIGN 7.3, 7.4, 5.7; decisions 2026-10-12 24,
25; R-3, R-5, R-20; I-4, I-15).

The constructed cases are hand-built stores of the fixture instrument SYNX
(5 basis points, tick 0.25, always open, no spread table: its bars at 00:00
to 05:00 UTC lie outside its 09:30 to 16:00 main session, so 2 ticks) and
direct orders on SYNA (per-contract fee, the fixture spread table). Every
expected number is written from the formulas of DESIGN 7.3.
"""

import ast
import statistics
from dataclasses import replace
from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest

from discotrade import executor as executor_module
from discotrade.backtest import ROW_COLUMNS, evaluate
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT
from discotrade.config import DateRange, load_calendar, load_track_config
from discotrade.executor import ExecutionError, Fill, Market, Order, SimExecutor
from discotrade.rolls import Roll, roll_path
from discotrade.spreads import spread_table
from discotrade.strategy import Strategy

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
HOUR = 3600
SRC = REPO_ROOT / "src" / "discotrade"


@pytest.fixture(scope="module")
def cfg():
    return load_track_config(FIXTURE, TRACK)


@pytest.fixture(scope="module")
def instruments(cfg):
    return {i.symbol: i for i in cfg.instruments}


@pytest.fixture(scope="module")
def calendars():
    return {p.stem: load_calendar(p) for p in sorted((FIXTURE / "calendars").glob("*.toml"))}


def _bar(ts, o, c, contract):
    return {"ts": pd.Timestamp(ts, tz="UTC"), "open": o, "high": max(o, c) + 1.0,
            "low": min(o, c) - 1.0, "close": c, "volume": 5.0, "contract": contract}


HAND = [
    _bar("2020-01-05 22:00", 97.0, 98.0, "A"),    # context
    _bar("2020-01-05 23:00", 98.0, 99.0, "A"),    # context
    _bar("2020-01-06 00:00", 100.0, 101.0, "A"),  # u0
    _bar("2020-01-06 01:00", 101.0, 102.0, "A"),
    _bar("2020-01-06 02:00", 102.0, 100.0, "A"),
    # 03:00 is missing
    _bar("2020-01-06 04:00", 112.0, 111.0, "B"),  # roll, gap 10
    _bar("2020-01-06 05:00", 110.0, 109.0, "B"),
]


def _store(state, bars, roll_ts=None, old="A", new="B", gap=10.0):
    BarStore(state, TRACK, HOUR).append("SYNX", pd.DataFrame(bars),
                                        datetime(2020, 1, 7, tzinfo=UTC))
    if roll_ts is not None:
        path = roll_path(state, TRACK, "SYNX")
        path.parent.mkdir(parents=True, exist_ok=True)
        r = Roll(ts=pd.Timestamp(roll_ts, tz="UTC"), old=old, new=new, gap=gap,
                 estimated=True, measured_at=None)
        path.write_text(r.to_json() + "\n", encoding="utf-8")


def by_close(targets):
    def position(bars, params):
        return targets[float(bars["close"].iloc[-1])]
    return Strategy(name="subject-1", source="", params={}, grid=None, position=position)


def _eval(state, track, inst, calendars, strat, first, last=None):
    return evaluate(state, track, inst, calendars[inst.calendar], strat,
                    DateRange(first, first if last is None else last))


# --- the executor is the simulator only (I-15) ------------------------------------------


def _implementations(root):
    """Classes under ``root`` that define ``execute`` or name ``Executor`` as a base."""
    found = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name == "Executor":
                continue
            bases = {b.id if isinstance(b, ast.Name) else getattr(b, "attr", "")
                     for b in node.bases}
            methods = {n.name for n in node.body
                       if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
            if "Executor" in bases or "execute" in methods:
                found.append(f"{path.relative_to(root)}:{node.name}")
    return found


def test_simexecutor_is_the_only_executor_in_the_package():
    assert _implementations(SRC) == ["executor.py:SimExecutor"]
    assert isinstance(SimExecutor(), executor_module.Executor)


def test_the_scan_finds_a_planted_executor(tmp_path):
    (tmp_path / "a.py").write_text("class Broker:\n    def execute(self, orders, bars):\n"
                                   "        return []\n")
    (tmp_path / "b.py").write_text("class Live(Executor):\n    pass\n")
    assert _implementations(tmp_path) == ["a.py:Broker", "b.py:Live"]


# --- fills -------------------------------------------------------------------------------------


def _market(inst, calendar, table, bars, gaps=None, rolled=None):
    frame = pd.DataFrame(bars)
    n = len(frame)
    return Market(instrument=inst, calendar=calendar, spread_table=table, bars=frame,
                  gaps=np.zeros(n) if gaps is None else np.asarray(gaps, dtype=float),
                  rolled=np.zeros(n, dtype=bool) if rolled is None
                  else np.asarray(rolled, dtype=bool))


def test_one_fill_per_order_with_fill_bar_raw_price_and_components(instruments, calendars):
    syna = instruments["SYNA"]
    table = spread_table(FIXTURE, "SYNA")
    # Tuesday 2019-06-04 in EDT: 13:00 UTC is 09:00 local (1.0 tick), 14:00 is 10:00
    # (1.25 ticks), 15:00 is 11:00 (1.0 tick).
    bars = [_bar("2019-06-04 12:00", 3990.0, 4000.0, "X"),
            _bar("2019-06-04 13:00", 4000.0, 4010.0, "X"),
            _bar("2019-06-04 14:00", 4050.0, 4020.0, "Y"),
            _bar("2019-06-04 15:00", 4020.0, 4030.0, "Y")]
    market = _market(syna, calendars["synth_week"], table, bars,
                     gaps=[0, 0, 30.0, 0], rolled=[False, False, True, False])
    ts = [pd.Timestamp(b["ts"]) for b in bars]
    orders = [Order("s", "SYNA", ts[0], 0.0, 1.0),
              Order("s", "SYNA", ts[1], 1.0, -0.5),
              Order("s", "SYNA", ts[2], -0.5, -0.5)]
    fills = SimExecutor().execute(orders, {"SYNA": market})
    assert len(fills) == 3 and all(isinstance(f, Fill) for f in fills)
    assert [f.order for f in fills] == orders
    assert [f.bar for f in fills] == ts[1:]
    assert [f.price for f in fills] == [4000.0, 4050.0, 4020.0]
    # r(1) = 10/4000; r(2) = (4020 - (4010 + 30)) / 4010; sigma needs two returns.
    r1, r2 = 10 / 4000, -20 / 4010
    f1, f2, f3 = fills
    assert f1.fee == pytest.approx(0.5 / (10 * 4000), rel=1e-12)
    assert f1.spread == pytest.approx(0.5 * 0.25 / 4000, rel=1e-12)
    assert f1.slippage == 0.0                                   # one return: sigma 0
    assert f1.roll == 0.0
    c2 = 0.5 / (10 * 4050) + 0.625 * 0.25 / 4050 + 0.0      # sigma(2) uses r(1) only
    assert f2.fee == pytest.approx(1.5 * 0.5 / (10 * 4050), rel=1e-12)
    assert f2.spread == pytest.approx(1.5 * 0.625 * 0.25 / 4050, rel=1e-12)
    assert f2.slippage == 0.0
    assert f2.roll == pytest.approx(2 * 1.0 * c2, rel=1e-12)    # carried 1.0 into a roll
    # No trade: zero fee, spread and slippage, and no roll at bar 3.
    assert (f3.fee, f3.spread, f3.slippage, f3.roll) == (0.0, 0.0, 0.0, 0.0)
    for f in fills:
        assert f.cost == f.fee + f.spread + f.slippage + f.roll
    # Bar 3's sigma would be stdev(r1, r2): seen once the order trades.
    one = SimExecutor().execute([Order("s", "SYNA", ts[2], 0.0, 1.0)], {"SYNA": market})[0]
    assert one.slippage == pytest.approx(0.02 * statistics.stdev([r1, r2]), rel=1e-12)


def test_an_order_with_no_trade_still_pays_a_roll(instruments, calendars):
    synx = instruments["SYNX"]
    market = _market(synx, calendars["always_open"], None, HAND,
                     gaps=[0, 0, 0, 0, 0, 10.0, 0], rolled=[False] * 5 + [True, False])
    fill = SimExecutor().execute([Order("s", "SYNX", HAND[4]["ts"], -0.5, -0.5)],
                                 {"SYNX": market})[0]
    assert (fill.fee, fill.spread, fill.slippage) == (0.0, 0.0, 0.0)
    r = [(99 - 98) / 98, (101 - 99) / 99, (102 - 101) / 101, (100 - 102) / 102]
    c = 5e-4 + 0.25 / 112 + 0.02 * statistics.stdev(r)
    assert fill.roll == pytest.approx(2 * 0.5 * c, rel=1e-12)
    assert fill.cost == fill.roll


def test_an_order_the_market_cannot_fill_is_refused(instruments, calendars):
    synx = instruments["SYNX"]
    market = _market(synx, calendars["always_open"], None, HAND)
    with pytest.raises(ExecutionError, match="no bar after"):
        SimExecutor().execute([Order("s", "SYNX", HAND[-1]["ts"], 0.0, 1.0)],
                              {"SYNX": market})
    with pytest.raises(ExecutionError, match="no stored bar"):
        SimExecutor().execute([Order("s", "SYNX", pd.Timestamp("2020-01-06 03:00", tz="UTC"),
                                     0.0, 1.0)], {"SYNX": market})
    with pytest.raises(ExecutionError, match="SYNA"):
        SimExecutor().execute([Order("s", "SYNA", HAND[2]["ts"], 0.0, 1.0)],
                              {"SYNX": market})


# --- the per-bar rows of decision 25 ------------------------------------------------------------


TARGETS = {101.0: 1.0, 102.0: -0.5, 100.0: 0.5, 111.0: -1.0, 109.0: 0.25}


def _returns(closes_and_gaps):
    return [(c - p - g) / p for p, c, g in closes_and_gaps]


def test_rows_of_decision_25_for_a_constructed_case(tmp_path, cfg, instruments, calendars):
    _store(tmp_path, HAND, roll_ts="2020-01-06 04:00")
    ev = _eval(tmp_path, cfg.track, instruments["SYNX"], calendars, by_close(TARGETS),
               date(2020, 1, 6))
    rows = ev.rows
    assert tuple(rows.columns) == ROW_COLUMNS == (
        "ts", "contract", "date", "p", "h", "gross", "trade", "fee", "spread", "slippage",
        "roll", "cost", "net_1x", "net_2x")
    assert rows["h"].tolist() == [0.0, 1.0, -0.5, 0.5, -1.0]
    assert rows["trade"].tolist() == [0.0, 1.0, 1.5, 1.0, 1.5]
    # r(s) over stored bars from the first context bar (decision 24: context counts).
    r = _returns([(98, 99, 0), (99, 101, 0), (101, 102, 0), (102, 100, 0), (100, 111, 10)])
    sig = [statistics.stdev(r[:k]) for k in (2, 3, 4, 5)]
    opens = [101.0, 102.0, 112.0, 110.0]
    trade = [1.0, 1.5, 1.0, 1.5]
    unit = [5e-4 + 0.25 / o + 0.02 * s for o, s in zip(opens, sig, strict=True)]
    want_fee = [0.0] + [t * 5e-4 for t in trade]
    want_spread = [0.0] + [t * 0.25 / o for t, o in zip(trade, opens, strict=True)]
    want_slip = [0.0] + [t * 0.02 * s for t, s in zip(trade, sig, strict=True)]
    want_roll = [0.0, 0.0, 0.0, 2 * 0.5 * unit[2], 0.0]
    for col, want in (("fee", want_fee), ("spread", want_spread),
                      ("slippage", want_slip), ("roll", want_roll)):
        assert np.allclose(rows[col].to_numpy(), want, rtol=1e-12, atol=0), col
    cost = [a + b + c + d for a, b, c, d in
            zip(want_fee, want_spread, want_slip, want_roll, strict=True)]
    assert np.allclose(rows["cost"].to_numpy(), cost, rtol=1e-12, atol=0)
    gross = [0.0, 1 / 101, 1 / 102, -1.5 / 112, 0.5 / 110]
    assert np.allclose(rows["gross"].to_numpy(), gross, rtol=0, atol=1e-15)
    assert np.allclose(rows["net_1x"].to_numpy(),
                       [g - c for g, c in zip(gross, cost, strict=True)], rtol=1e-12, atol=1e-18)
    assert np.allclose(rows["net_2x"].to_numpy(),
                       [g - 2 * c for g, c in zip(gross, cost, strict=True)],
                       rtol=1e-12, atol=1e-18)
    # The first window bar: nothing traded, nothing rolled, nothing charged.
    assert rows.iloc[0][["trade", "fee", "spread", "slippage", "roll", "cost"]].tolist() == \
        [0.0] * 6


def test_sigma_reads_only_trusted_bars(tmp_path, cfg, instruments, calendars):
    _store(tmp_path, HAND, roll_ts="2020-01-06 04:00")
    inst = replace(instruments["SYNX"], trusted_from=date(2020, 1, 6))
    ev = _eval(tmp_path, cfg.track, inst, calendars, by_close(TARGETS), date(2020, 1, 6))
    rows = ev.rows
    # Without the two untrusted bars, r(s) starts at the 01:00 bar: sigma at 01:00 and
    # 02:00 has fewer than two returns, so their slippage is 0.
    assert rows["slippage"].tolist()[:3] == [0.0, 0.0, 0.0]
    r = _returns([(101, 102, 0), (102, 100, 0)])
    assert rows["slippage"].iloc[3] == pytest.approx(1.0 * 0.02 * statistics.stdev(r),
                                                     rel=1e-12)


def test_sigma_reaches_context_beyond_a_small_history_cap(tmp_path, cfg, instruments,
                                                          calendars):
    _store(tmp_path, HAND, roll_ts="2020-01-06 04:00")
    small = replace(cfg.track, history_cap_bars=1)
    ev = _eval(tmp_path, small, instruments["SYNX"], calendars, by_close(TARGETS),
               date(2020, 1, 6))
    r = _returns([(98, 99, 0), (99, 101, 0)])
    assert ev.rows["slippage"].iloc[1] == pytest.approx(0.02 * statistics.stdev(r), rel=1e-12)


def test_a_flat_position_pays_no_roll(tmp_path, cfg, instruments, calendars):
    _store(tmp_path, HAND, roll_ts="2020-01-06 04:00")
    flat = {101.0: 1.0, 102.0: 0.0, 100.0: 0.0, 111.0: 0.0, 109.0: 0.0}
    ev = _eval(tmp_path, cfg.track, instruments["SYNX"], calendars, by_close(flat),
               date(2020, 1, 6))
    rows = ev.rows
    assert rows["h"].tolist() == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert rows["roll"].tolist() == [0.0] * 5
    assert rows.iloc[3]["cost"] == 0.0


def test_no_roll_cost_at_a_windows_first_bar(tmp_path, cfg, instruments, calendars):
    bars = [_bar("2020-01-05 22:00", 97.0, 98.0, "A"),
            _bar("2020-01-05 23:00", 98.0, 99.0, "A"),
            _bar("2020-01-06 00:00", 110.0, 111.0, "B"),    # u0 and a roll
            _bar("2020-01-06 01:00", 111.0, 112.0, "B")]
    _store(tmp_path, bars, roll_ts="2020-01-06 00:00", gap=11.0)
    always = Strategy(name="s", source="", params={}, grid=None, position=lambda b, p: 1.0)
    ev = _eval(tmp_path, cfg.track, instruments["SYNX"], calendars, always, date(2020, 1, 6))
    assert ev.rolled[ev.first]
    first = ev.rows.iloc[0]
    assert (first["h"], first["trade"], first["roll"], first["cost"]) == (0.0, 0.0, 0.0, 0.0)
    # The window starting the day before carries a position into the same roll and pays.
    ev = _eval(tmp_path, cfg.track, instruments["SYNX"], calendars, always,
               date(2020, 1, 5), date(2020, 1, 6))
    at_roll = ev.rows[ev.rows["ts"] == pd.Timestamp("2020-01-06 00:00", tz="UTC")].iloc[0]
    assert at_roll["h"] == 1.0 and at_roll["trade"] == 0.0 and at_roll["roll"] > 0.0
    assert at_roll["cost"] == at_roll["roll"]
