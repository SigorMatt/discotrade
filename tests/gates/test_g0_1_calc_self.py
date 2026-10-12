"""G0.1: the independent calculation checks itself (DESIGN 18.3 G0.1).

Before ``independent_calc.py`` is compared with discotrade's evaluation, it
is checked here on its own: its imports are read with ``ast`` (decision 39:
the standard library, numpy, pandas, pyarrow and tomllib, and nothing from
discotrade), and its results are compared with values computed by hand, on
small stores written with pyarrow under a pytest temporary directory, with
the derivation of each value in a comment. No random draw is used, so no
seed is needed. Equality is decision 39's: ``|a - b| <= 1e-12 * max(1, |a|,
|b|)``, both or neither not a number.
"""

import ast
import datetime as dt
import json
import math
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from independent_calc import CalcError, calculate, max_drawdown, sharpe

pytestmark = [pytest.mark.gate, pytest.mark.gate_m0]

CALC = Path(__file__).resolve().parent / "independent_calc.py"
ALLOWED_THIRD_PARTY = {"numpy", "pandas", "pyarrow"}
D7, D8, D9, D12 = (dt.date(2019, 1, d) for d in (7, 8, 9, 12))


def eq(a, b) -> bool:
    if isinstance(a, float) and math.isnan(a) or isinstance(b, float) and math.isnan(b):
        return isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


def assert_eq(actual, expected, what=""):
    assert eq(actual, expected), f"{what}: {actual!r} != {expected!r}"


def utc(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text).replace(tzinfo=dt.UTC)


# ------------------------------------------------------------ store builders


def toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    return repr(v)


def write_toml(path: Path, top: dict, tables: dict | None = None, arrays: dict | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k} = {toml_value(v)}" for k, v in top.items()]
    for name, table in (tables or {}).items():
        lines.append(f"\n[{name}]")
        lines += [f"{k} = {toml_value(v)}" for k, v in table.items()]
    for name, items in (arrays or {}).items():
        for table in items:
            lines.append(f"\n[[{name}]]")
            lines += [f"{k} = {toml_value(v)}" for k, v in table.items()]
    path.write_text("\n".join(lines) + "\n")


def write_calendars(config: Path):
    write_toml(config / "calendars" / "wk.toml", {
        "name": "wk", "tz": "America/New_York", "week_open": ["Sun", "18:00"],
        "week_close": ["Fri", "17:00"], "daily_break": ["17:00", "18:00"],
        "day_rolls_at": "17:00",
    }, arrays={"closure": [{"start": "2019-07-03 13:00", "end": "2019-07-04 18:00",
                            "note": "invented"}]})
    write_toml(config / "calendars" / "open.toml", {"name": "open", "always_open": True})


def write_track(config: Path, name: str, instruments: list[str], cap: int):
    write_toml(config / "tracks" / f"{name}.toml", {
        "name": name, "bar_seconds": 3600, "w_days": 28, "t_days": 7,
        "history_cap_bars": cap, "block_days": 7, "epoch": "2019-01-07",
        "instruments": instruments, "families": ["trend"], "cell_slots": 1,
    }, tables={"horizons": {"short": [1, 6]}})


def write_instrument(config: Path, symbol: str, calendar: str, shorting: bool,
                     tick: float, cost: dict, multiplier: float | None = None):
    top = {"symbol": symbol, "venue": "SYNTH", "quote_currency": "USD",
           "calendar": calendar}
    if multiplier is not None:
        top["multiplier"] = multiplier
    top.update({"tick_size": tick, "shorting": shorting, "test_only": True,
                "trusted_from": "2019-01-07", "main_session": ["09:30", "16:00"]})
    write_toml(config / "instruments" / f"{symbol}.toml", top,
               tables={"cost": cost, "source": {"adapter": "synth"}})


def write_bars(state: Path, track: str, symbol: str, bars: list[tuple]):
    """bars: (ts text UTC, open, close, volume, contract); high/low enclose them."""
    by_month: dict[str, list[tuple]] = {}
    for bar in bars:
        by_month.setdefault(bar[0][:7], []).append(bar)
    folder = state / "bars" / track / symbol
    folder.mkdir(parents=True, exist_ok=True)
    for month, rows in by_month.items():
        table = pa.table({
            "ts": pa.array([utc(r[0]) for r in rows], pa.timestamp("ns", tz="UTC")),
            "open": pa.array([float(r[1]) for r in rows], pa.float64()),
            "high": pa.array([max(r[1], r[2]) + 1.0 for r in rows], pa.float64()),
            "low": pa.array([min(r[1], r[2]) - 1.0 for r in rows], pa.float64()),
            "close": pa.array([float(r[2]) for r in rows], pa.float64()),
            "volume": pa.array([float(r[3]) for r in rows], pa.float64()),
            "contract": pa.array([r[4] for r in rows], pa.large_string()),
        })
        pq.write_table(table, folder / f"{month}.parquet")


def write_rolls(state: Path, track: str, symbol: str, records: list[dict]):
    path = state / "rolls" / track / f"{symbol}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))


def by_volume(bars, params):
    """The target is coded in the last bar's volume: 110 -> 1, 95 -> -0.5."""
    return (float(bars["volume"].iloc[-1]) - 100.0) / 10.0


FIELDS = ("p", "h", "gross", "trade", "fee", "spread", "slippage", "roll", "cost",
          "net_1x", "net_2x")


def check_rows(rows, expected):
    assert len(rows) == len(expected)
    for i, (row, exp) in enumerate(zip(rows, expected, strict=True)):
        for key, value in exp.items():
            if key in ("ts", "contract", "date"):
                assert row[key] == value, f"bar {i} {key}: {row[key]!r} != {value!r}"
            else:
                assert_eq(row[key], value, f"bar {i} {key}")


def full(p, h, gross, trade, fee, spread, slippage, roll):
    cost = fee + spread + slippage + roll
    return {"p": p, "h": h, "gross": gross, "trade": trade, "fee": fee, "spread": spread,
            "slippage": slippage, "roll": roll, "cost": cost,
            "net_1x": gross - cost, "net_2x": gross - 2 * cost}


# ------------------------------------------------------------ imports


def test_calc_imports_only_what_decision_39_allows():
    tree = ast.parse(CALC.read_text())
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import"
            roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "__import__", "dynamic import"
        elif isinstance(node, ast.Name | ast.Attribute):
            name = node.id if isinstance(node, ast.Name) else node.attr
            assert name not in ("importlib", "import_module", "discotrade")
    assert "discotrade" not in roots
    assert "importlib" not in roots
    outside = {r for r in roots if r not in sys.stdlib_module_names}
    assert outside <= ALLOWED_THIRD_PARTY, outside
    assert "tomllib" in roots   # it reads the TOML itself


# ------------------------------------------------------------ scenario A: rolls


SPREAD_A = [2.0] * 24
SPREAD_A[10] = 3.0
SPREAD_A[11] = 4.0
SPREAD_A[13] = 0.5   # half of it is under the 0.5-tick floor
SPREAD_A[16] = 6.0


@pytest.fixture
def store_a(tmp_path):
    """Instrument TA on calendar wk (New York, UTC-5 in January), track ta.

    Per-contract fee 0.5 per side, multiplier 10, so fee(u) = 0.05 / Or(u);
    tick 0.25 and the spread table SPREAD_A by local hour; slippage_coef 0.
    Bars (UTC, local = UTC-5), target coded in the volume:
      x 01-06 23:00 Sun 18:00  A-0  before trusted_from: never read, and
                                    A-0 -> A-1 is therefore no roll.
      0 01-07 14:00 09:00 A-1 O100 C100  p=1   date 01-07
      1 01-07 15:00 10:00 A-1 O100 C102  p=1
      2 01-07 16:00 11:00 A-2 O113 C114  p=0   roll A-1 -> A-2, gap +10, carried
        01-07 17:00 missing bar
      3 01-07 18:00 13:00 A-2 O116 C110  p=0
      4 01-07 21:00 16:00 A-2 O110 C110  p=0   last bar before the daily break
      5 01-07 23:00 18:00 A-3 O106 C105  p=-1  first after it: date 01-08;
                                               roll A-2 -> A-3, gap -5, flat
      6 01-08 00:00 19:00 A-3 O105 C100  p=0
      7 01-08 01:00 20:00 A-3 O98  C97   p=1   recorded, never traded
    """
    config, state = tmp_path / "config", tmp_path / "state"
    write_calendars(config)
    write_track(config, "ta", ["TA"], cap=3)
    write_instrument(config, "TA", "wk", True, 0.25, {
        "fee_per_side": 0.5, "spread_ticks_main": 1.0, "spread_ticks_off": 2.0,
        "slippage_coef": 0.0}, multiplier=10.0)
    write_toml(config / "spreads" / "TA.toml", {"symbol": "TA", "spread_ticks": SPREAD_A})
    write_bars(state, "ta", "TA", [
        ("2019-01-06 23:00", 500, 500, 100, "A-0"),
        ("2019-01-07 14:00", 100, 100, 110, "A-1"),
        ("2019-01-07 15:00", 100, 102, 110, "A-1"),
        ("2019-01-07 16:00", 113, 114, 100, "A-2"),
        ("2019-01-07 18:00", 116, 110, 100, "A-2"),
        ("2019-01-07 21:00", 110, 110, 100, "A-2"),
        ("2019-01-07 23:00", 106, 105, 90, "A-3"),
        ("2019-01-08 00:00", 105, 100, 100, "A-3"),
        ("2019-01-08 01:00", 98, 97, 110, "A-3"),
    ])
    write_rolls(state, "ta", "TA", [
        {"ts": "2019-01-07T16:00:00+00:00", "old": "A-1", "new": "A-2", "gap": 10.0,
         "estimated": False},
        {"ts": "2019-01-07T23:00:00+00:00", "old": "A-2", "new": "A-3", "gap": -5.0,
         "estimated": False},
    ])
    return state, config


def test_rolls_missing_bar_daily_break_and_spread_table(store_a):
    state, config = store_a
    res = calculate(state, config, "ta", "2019-01-07", "2019-01-08", by_volume, {})
    rows = res.rows["TA"]
    expected = [
        # 0: first window bar: h = 0 and previous position 0 (R-20, decision 24).
        full(1, 0, 0.0, 0, 0, 0, 0, 0),
        # 1: h 0 -> 1. gross = (0 + 1 * (102 - 100)) / 100 = 0.02; trade 1;
        #    fee 0.05/100; local hour 10 -> 3.0 ticks: 1.5 * 0.25 / 100.
        full(1, 1, 0.02, 1, 0.05 / 100, 0.375 / 100, 0, 0),
        # 2: roll +10 with h(1) = 1 carried. As of bar 2, Ca(1) = 102 + 10 = 112:
        #    gross = (1 * (113 - 112) + 1 * (114 - 113)) / 113 = 2 / 113; trade 0;
        #    c = 0.05/113 + (4.0 / 2) * 0.25 / 113 = 0.55 / 113 (hour 11);
        #    roll = 2 * |1| * c = 1.1 / 113.
        full(0, 1, 2 / 113, 0, 0, 0, 0, 1.1 / 113),
        # 3: u-1 is bar 2 (17:00 is missing). h 1 -> 0.
        #    gross = (1 * (116 - 114) + 0) / 116 = 2 / 116; trade 1; fee 0.05/116;
        #    hour 13 -> 0.5 ticks, floored: max(0.25, 0.5) * 0.25 / 116 = 0.125 / 116.
        full(0, 0, 2 / 116, 1, 0.05 / 116, 0.125 / 116, 0, 0),
        # 4: flat, nothing.
        full(0, 0, 0.0, 0, 0, 0, 0, 0),
        # 5: roll -5 with h(4) = 0: a flat roll costs nothing. p = -1 (shortable).
        full(-1, 0, 0.0, 0, 0, 0, 0, 0),
        # 6: h 0 -> -1. gross = (0 + -1 * (100 - 105)) / 105 = 5 / 105; trade 1;
        #    fee 0.05/105; hour 19 -> 2.0 ticks: 1 * 0.25 / 105.
        full(0, -1, 5 / 105, 1, 0.05 / 105, 0.25 / 105, 0, 0),
        # 7: h -1 -> 0. gross = (-1 * (98 - 100) + 0) / 98 = 2 / 98; trade 1;
        #    fee 0.05/98; hour 20 -> 0.25/98. p(7) = 1 is recorded, never traded.
        full(1, 0, 2 / 98, 1, 0.05 / 98, 0.25 / 98, 0, 0),
    ]
    check_rows(rows, expected)
    assert [r["contract"] for r in rows] == ["A-1", "A-1", "A-2", "A-2", "A-2", "A-3",
                                             "A-3", "A-3"]
    assert [r["date"] for r in rows] == [D7] * 5 + [D8] * 3
    assert rows[0]["ts"].isoformat() == "2019-01-07T14:00:00+00:00"

    # Daily series, N = 1: bars 0-4 are 01-07, bars 5-7 (after the break) 01-08.
    d1 = [0.01575 + 0.9 / 113 + 1.825 / 116, 4.7 / 105 + 1.7 / 98]
    d2 = [0.0115 - 0.2 / 113 + 1.65 / 116, 4.4 / 105 + 1.4 / 98]
    assert res.days == [D7, D8]
    for a, b in zip(res.daily_1x, d1, strict=True):
        assert_eq(a, b, "d1")
    for a, b in zip(res.daily_2x, d2, strict=True):
        assert_eq(a, b, "d2")

    m = res.metrics
    assert_eq(m["total_return"], sum(d1), "total_return")
    assert_eq(m["total_return_2x"], sum(d2), "total_return_2x")
    # Two days: std(ddof=1) = |a - b| / sqrt(2).
    assert_eq(m["sharpe"], (sum(d1) / 2) / (abs(d1[0] - d1[1]) / math.sqrt(2))
              * math.sqrt(252), "sharpe")
    assert_eq(m["sharpe_2x"], (sum(d2) / 2) / (abs(d2[0] - d2[1]) / math.sqrt(2))
              * math.sqrt(252), "sharpe_2x")
    assert_eq(m["max_drawdown"], 0.0, "max_drawdown")   # both days gain
    assert m["trades"] == 4                              # bars 1, 3, 6, 7
    # h = 0 1 1 0 0 0 -1 0: runs of 2 and 1 bars.
    assert_eq(m["avg_holding_bars"], 1.5, "avg_holding_bars")
    # Turnover: trades 4 plus the carried roll at bar 2, 2 * |h(1)| = 2.
    gross = 0.02 + 2 / 113 + 2 / 116 + 5 / 105 + 2 / 98
    assert_eq(m["breakeven_cost"], gross / 6 * 10000, "breakeven_cost")
    assert m["fragile"] is False
    assert_eq(res.costs["fee"], 0.05 / 100 + 0.05 / 116 + 0.05 / 105 + 0.05 / 98, "fee")
    assert_eq(res.costs["spread"], 0.375 / 100 + 0.125 / 116 + 0.25 / 105 + 0.25 / 98,
              "spread")
    assert_eq(res.costs["slippage"], 0.0, "slippage")
    assert_eq(res.costs["roll"], 1.1 / 113, "roll")
    assert res.costs_by_instrument["TA"] == res.costs


def test_slice_is_capped_adjusted_and_local(store_a):
    state, config = store_a
    frames = []

    def record(bars, params):
        frames.append(bars)
        return 0.0

    calculate(state, config, "ta", "2019-01-07", "2019-01-08", record, {})
    assert len(frames) == 8
    for f in frames:
        assert list(f.columns) == ["open", "high", "low", "close", "volume", "hour",
                                   "weekday"]
        assert list(f.index) == list(range(len(f)))
    # Bar 0: bar x lies before trusted_from and is not in the slice.
    assert len(frames[0]) == 1
    # Bar 2 (cap 3): bars 0, 1, 2 adjusted as of bar 2 (+10 before the roll).
    f = frames[2]
    assert list(f["close"]) == [110.0, 112.0, 114.0]
    assert list(f["open"]) == [110.0, 110.0, 113.0]
    assert list(f["volume"]) == [110.0, 110.0, 100.0]       # never adjusted
    assert list(f["hour"]) == [9, 10, 11]                    # New York hours
    assert list(f["weekday"]) == [0, 0, 0]                   # Monday is 0
    # Bar 5: bars 3, 4, 5 adjusted as of 5 (-5); the +10 roll is before them all.
    assert list(frames[5]["close"]) == [105.0, 105.0, 105.0]
    assert list(frames[5]["hour"]) == [13, 16, 18]
    # Bar 7: bars 5, 6, 7 raw (no roll after bar 5).
    assert list(frames[7]["close"]) == [105.0, 100.0, 97.0]
    assert list(frames[7]["hour"]) == [18, 19, 20]
    # A window starting 01-08: its first bar (5) gets bars 3 and 4 as context.
    frames.clear()
    res = calculate(state, config, "ta", "2019-01-08", "2019-01-08", record, {})
    assert len(frames[0]) == 3 and list(frames[0]["hour"]) == [13, 16, 18]
    assert [r["h"] for r in res.rows["TA"]] == [0.0, 0.0, 0.0]


def test_missing_or_mismatched_roll_record_is_an_error(store_a):
    state, config = store_a
    path = state / "rolls" / "ta" / "TA.jsonl"
    path.unlink()
    with pytest.raises(CalcError, match="bars fetch"):
        calculate(state, config, "ta", "2019-01-07", "2019-01-08", by_volume, {})
    # Decision 37: right ts, other contracts, is a missing record.
    write_rolls(state, "ta", "TA", [
        {"ts": "2019-01-07T16:00:00+00:00", "old": "A-0", "new": "A-2", "gap": 10.0},
        {"ts": "2019-01-07T23:00:00+00:00", "old": "A-2", "new": "A-3", "gap": -5.0},
    ])
    with pytest.raises(CalcError, match="bars fetch"):
        calculate(state, config, "ta", "2019-01-07", "2019-01-08", by_volume, {})


@pytest.mark.parametrize("bad", [1.5, -1.0000001, float("nan"), float("inf"), "1", None,
                                 True])
def test_result_outside_the_contract_is_an_error(store_a, bad):
    state, config = store_a
    with pytest.raises(CalcError, match="TA at 2019-01-07T14:00:00"):
        calculate(state, config, "ta", "2019-01-07", "2019-01-08", lambda b, p: bad, {})


def test_a_raising_strategy_is_an_error(store_a):
    state, config = store_a

    def boom(bars, params):
        raise ZeroDivisionError("x")

    with pytest.raises(CalcError, match="TA at 2019-01-07T14:00:00"):
        calculate(state, config, "ta", "2019-01-07", "2019-01-08", boom, {})


# ------------------------------------------------- scenario B: no short, fee_bps


@pytest.fixture
def store_b(tmp_path):
    """Track tb with TB (calendar wk, cannot short, no spread table: main
    session 09:30-16:00 New York at 1.0 tick, off at 3.0) and TC (always open,
    UTC, fee_bps 5 so fee = 0.0005 per unit, tick 0.5, main 1.0, off 2.0).
    Slippage 0 for both. N = 2.

    TB (local = UTC-5):
      0 01-08 14:00 09:00 O50 C50 vol 90  -> -1, clipped to 0
      1 01-08 15:00 10:00 O50 C51 vol 105 -> 0.5
      2 01-08 16:00 11:00 O52 C50 vol 95  -> -0.5, clipped to 0   main session
      3 01-08 21:00 16:00 O48 C49 vol 100 -> 0                    off session
      4 01-08 23:00 18:00 O49 C49 vol 100 -> 0                    date 01-09
    TC (UTC):
      0 01-08 14:00 Tue O1000 C1000 -> 1
      1 01-08 15:00 Tue O1000 C1010 -> 1                          main session
      2 01-08 23:00 Tue O1020 C1000 -> 0
      3 01-09 01:00 Wed O1000 C990  -> 1                          off session
      4 01-12 15:00 Sat O1000 C1000 -> 0                          off: Saturday
    """
    config, state = tmp_path / "config", tmp_path / "state"
    write_calendars(config)
    write_track(config, "tb", ["TB", "TC"], cap=480)
    write_instrument(config, "TB", "wk", False, 0.25, {
        "fee_per_side": 0.5, "spread_ticks_main": 1.0, "spread_ticks_off": 3.0,
        "slippage_coef": 0.0}, multiplier=10.0)
    write_instrument(config, "TC", "open", True, 0.5, {
        "fee_bps": 5.0, "spread_ticks_main": 1.0, "spread_ticks_off": 2.0,
        "slippage_coef": 0.0})
    write_bars(state, "tb", "TB", [
        ("2019-01-08 14:00", 50, 50, 90, "TB"),
        ("2019-01-08 15:00", 50, 51, 105, "TB"),
        ("2019-01-08 16:00", 52, 50, 95, "TB"),
        ("2019-01-08 21:00", 48, 49, 100, "TB"),
        ("2019-01-08 23:00", 49, 49, 100, "TB"),
    ])
    write_bars(state, "tb", "TC", [
        ("2019-01-08 14:00", 1000, 1000, 110, "TC"),
        ("2019-01-08 15:00", 1000, 1010, 110, "TC"),
        ("2019-01-08 23:00", 1020, 1000, 100, "TC"),
        ("2019-01-09 01:00", 1000, 990, 110, "TC"),
        ("2019-01-12 15:00", 1000, 1000, 100, "TC"),
    ])
    return state, config


def test_no_short_session_spreads_proportional_fee_and_mixed_calendars(store_b):
    state, config = store_b
    res = calculate(state, config, "tb", D8, D12, by_volume, {})
    check_rows(res.rows["TB"], [
        full(0, 0, 0.0, 0, 0, 0, 0, 0),           # -1 clipped to 0 (decision 22)
        # 1: h = p(0) = 0 (clipped); unclipped it would be -1 and trade.
        full(0.5, 0, 0.0, 0, 0, 0, 0, 0),
        # 2: h 0 -> 0.5. gross = 0.5 * (50 - 52) / 52 = -1 / 52; trade 0.5;
        #    fee 0.5 * 0.05 / 52; main session 1.0 tick -> 0.5 tick:
        #    0.5 * 0.5 * 0.25 / 52 = 0.0625 / 52.
        full(0, 0.5, -1 / 52, 0.5, 0.025 / 52, 0.0625 / 52, 0, 0),
        # 3: h 0.5 -> 0. gross = 0.5 * (48 - 50) / 48 = -1 / 48; trade 0.5;
        #    fee 0.025 / 48; 16:00 local is off session, 3.0 ticks -> 1.5:
        #    0.5 * 1.5 * 0.25 / 48 = 0.1875 / 48.
        full(0, 0, -1 / 48, 0.5, 0.025 / 48, 0.1875 / 48, 0, 0),
        full(0, 0, 0.0, 0, 0, 0, 0, 0),
    ])
    assert [r["date"] for r in res.rows["TB"]] == [D8, D8, D8, D8, D9]
    check_rows(res.rows["TC"], [
        full(1, 0, 0.0, 0, 0, 0, 0, 0),
        # 1: h 0 -> 1. gross = 10 / 1000; fee 5 bps; main 1.0 tick -> 0.5 tick:
        #    0.5 * 0.5 / 1000 = 0.00025.
        full(1, 1, 0.01, 1, 0.0005, 0.00025, 0, 0),
        # 2: h 1 -> 1. gross = (1 * (1020 - 1010) + 1 * (1000 - 1020)) / 1020.
        full(0, 1, -10 / 1020, 0, 0, 0, 0, 0),
        # 3: h 1 -> 0. gross = (1 * (1000 - 1000) + 0) / 1000 = 0; off 2.0 -> 1 tick:
        #    0.5 / 1000 = 0.0005.
        full(1, 0, 0.0, 1, 0.0005, 0.0005, 0, 0),
        # 4: h 0 -> 1 on a Saturday at 15:00 UTC: off session, 0.0005.
        full(0, 1, 0.0, 1, 0.0005, 0.0005, 0, 0),
    ])
    assert [r["date"] for r in res.rows["TC"]] == [D8, D8, D8, D9, D12]

    # Days are the union of both calendars' dates; each day's sum over
    # instruments is divided by N = 2, a missing instrument contributing 0.
    b8 = (-1 - 0.0875) / 52 + (-1 - 0.2125) / 48
    c8 = 0.01 - 0.00075 - 10 / 1020
    b8_2 = (-1 - 0.175) / 52 + (-1 - 0.425) / 48
    c8_2 = 0.01 - 0.0015 - 10 / 1020
    d1 = [(b8 + c8) / 2, (0 - 0.001) / 2, -0.001 / 2]
    d2 = [(b8_2 + c8_2) / 2, (0 - 0.002) / 2, -0.002 / 2]
    assert res.days == [D8, D9, D12]
    for a, b in zip(res.daily_1x + res.daily_2x, d1 + d2, strict=True):
        assert_eq(a, b, "daily")

    m = res.metrics
    assert_eq(m["total_return"], sum(d1), "total_return")
    assert_eq(m["total_return_2x"], sum(d2), "total_return_2x")
    mean = sum(d1) / 3
    std = math.sqrt(sum((x - mean) ** 2 for x in d1) / 2)
    assert_eq(m["sharpe"], mean / std * math.sqrt(252), "sharpe")
    mean2 = sum(d2) / 3
    std2 = math.sqrt(sum((x - mean2) ** 2 for x in d2) / 2)
    assert_eq(m["sharpe_2x"], mean2 / std2 * math.sqrt(252), "sharpe_2x")
    # Running sum falls every day, from day 1 on (d1[0] < 0). Decision on
    # D-004 (to be decision 41): the running sum starts at 0 and that 0 is a
    # peak, so the trough is the last running sum and max_drawdown is
    # 0 - sum(d1) = -d1[0] + 0.0005 + 0.0005 (it was 0.001 before the decision,
    # when the peak was the first running sum d1[0]).
    assert d1[0] < 0
    assert_eq(m["max_drawdown"], -sum(d1), "max_drawdown")
    assert m["trades"] == 5                     # TB bars 2, 3; TC bars 1, 3, 4
    # TB h 0 0 0.5 0 0: one run of 1; TC h 0 1 1 0 1: runs of 2 and 1.
    assert_eq(m["avg_holding_bars"], 4 / 3, "avg_holding_bars")
    gross = -1 / 52 - 1 / 48 + 0.01 - 10 / 1020
    assert_eq(m["breakeven_cost"], gross / 4 * 10000, "breakeven_cost")  # turnover 4
    assert m["fragile"] is False                # negative at 1x
    tb = {"fee": 0.025 / 52 + 0.025 / 48, "spread": 0.0625 / 52 + 0.1875 / 48,
          "slippage": 0.0, "roll": 0.0}
    tc = {"fee": 0.0015, "spread": 0.00125, "slippage": 0.0, "roll": 0.0}
    for k in ("fee", "spread", "slippage", "roll"):
        assert_eq(res.costs_by_instrument["TB"][k], tb[k], f"TB {k}")
        assert_eq(res.costs_by_instrument["TC"][k], tc[k], f"TC {k}")
        assert_eq(res.costs[k], (tb[k] + tc[k]) / 2, f"subject {k}")


def test_flat_strategy_gives_a_constant_series(store_b):
    state, config = store_b
    res = calculate(state, config, "tb", D8, D12, lambda b, p: 0.0, {})
    assert res.daily_1x == [0.0, 0.0, 0.0] and res.daily_2x == [0.0, 0.0, 0.0]
    m = res.metrics
    assert math.isnan(m["sharpe"]) and math.isnan(m["sharpe_2x"])
    assert m["total_return"] == 0.0 and m["max_drawdown"] == 0.0 and m["trades"] == 0
    assert math.isnan(m["avg_holding_bars"]) and math.isnan(m["breakeven_cost"])
    assert m["fragile"] is False


# ------------------------------------------------------------ scenario D: sigma


def sigma_closes():
    """C0 100, C1 200 (r = 1.0), C2 100 (r = -0.5), C3 100 (r = 0), then for k in
    4..9: 101 when k is even (r = 0.01), 100 when odd (r = -1/101); a roll at
    k = 10 with gap +50.5 (as of bar 10, Ca(9) = 150.5, so r(10) = 1 / 100); for
    k >= 10: 151.5 when even (r = 1.5 / 150 = 0.01), 150 when odd (r = -1/101).
    """
    closes = [100.0, 200.0, 100.0, 100.0]
    for k in range(4, 30):
        if k < 10:
            closes.append(101.0 if k % 2 == 0 else 100.0)
        else:
            closes.append(151.5 if k % 2 == 0 else 150.0)
    return closes


@pytest.fixture
def store_d(tmp_path):
    """TD, always open, 30 hourly bars from 2019-01-07 00:00 UTC (k = 0..23 on
    01-07, 24..29 on 01-08), slippage_coef 0.5. Targets: p(0) = 1, p(1) = 0,
    p(2..26) = 1, p(27..29) = 0."""
    config, state = tmp_path / "config", tmp_path / "state"
    write_calendars(config)
    write_track(config, "td", ["TD"], cap=480)
    write_instrument(config, "TD", "open", True, 0.01, {
        "fee_bps": 0.0, "spread_ticks_main": 1.0, "spread_ticks_off": 1.0,
        "slippage_coef": 0.5})
    closes = sigma_closes()
    start = dt.datetime(2019, 1, 7)
    bars = []
    for k, close in enumerate(closes):
        target = 1 if k == 0 or 2 <= k <= 26 else 0
        ts = (start + dt.timedelta(hours=k)).strftime("%Y-%m-%d %H:%M")
        bars.append((ts, closes[k - 1] if k else 100.0, close, 100 + 10 * target,
                     "TD-1" if k < 10 else "TD-2"))
    write_bars(state, "td", "TD", bars)
    write_rolls(state, "td", "TD", [{"ts": "2019-01-07T10:00:00+00:00", "old": "TD-1",
                                     "new": "TD-2", "gap": 50.5, "estimated": False}])
    return state, config


# The last 24 returns before bar 28 (s = 4..27) are twelve 0.01 and twelve
# -1/101: mean (0.01 - 1/101) / 2, every deviation +-delta with
# delta = (0.01 + 1/101) / 2, so std(ddof=1) = delta * sqrt(24 / 23).
SIGMA_28 = (0.01 + 1 / 101) / 2 * math.sqrt(24 / 23)


def test_sigma_edges_and_last_24_returns(store_d):
    state, config = store_d
    rows = calculate(state, config, "td", "2019-01-07", "2019-01-08", by_volume, {}).rows["TD"]
    assert [i for i, r in enumerate(rows) if r["trade"] > 1e-9] == [1, 2, 3, 28]
    # Bar 1: no return before it (r(0) needs a bar before the first): sigma 0.
    assert_eq(rows[1]["slippage"], 0.0, "bar 1")
    # Bar 2: one return, r(1) = 1.0: fewer than 2, sigma 0.
    assert_eq(rows[2]["slippage"], 0.0, "bar 2")
    # Bar 3: r(1) = 1.0, r(2) = -0.5: mean 0.25, std = sqrt(2 * 0.75**2 / 1).
    assert_eq(rows[3]["slippage"], 0.5 * math.sqrt(1.125), "bar 3")
    # Bar 28: more than 24 returns exist (27); only s = 4..27 are used.
    assert_eq(rows[28]["slippage"], 0.5 * SIGMA_28, "bar 28")


def test_sigma_reads_bars_before_the_window(store_d):
    state, config = store_d
    rows = calculate(state, config, "td", "2019-01-08", "2019-01-08", by_volume, {}).rows["TD"]
    assert len(rows) == 6 and rows[0]["h"] == 0.0
    # Bar 28 is row 4; its 24 returns reach back to bar 4, before the window.
    assert rows[4]["trade"] == 1.0
    assert_eq(rows[4]["slippage"], 0.5 * SIGMA_28, "bar 28")


# ------------------------------------- scenario E: the position changes at the roll
#
# Decision 43 (a), D-005: a roll cost or a rolled turnover taken on h(u)
# instead of h(u-1) must fail here. In scenario A the position does not
# change at either roll bar (1 -> 1, 0 -> 0), so it cannot see that mistake.
# DESIGN 7.3: roll_cost(u) = 2 * |h(u-1)| * c(u); decision 25: breakeven_cost
# divides by the sum of trade plus the rolled turnover 2 * |h(u-1)| at each roll.


def roll_store(tmp_path, symbol: str, bars: list[tuple], roll: dict):
    """One instrument on calendar open (UTC), track ``symbol.lower()``, N = 1.

    fee_bps 10, so fee(u) = 0.001; tick 0.5 and 1.0 tick in and out of the main
    session, so half_spread(u) = max(1.0 / 2, 0.5) * 0.5 / Or(u) = 0.25 / Or(u);
    slippage_coef 0. Hence c(u) = 0.001 + 0.25 / Or(u).
    """
    config, state = tmp_path / "config", tmp_path / "state"
    track = symbol.lower()
    write_calendars(config)
    write_track(config, track, [symbol], cap=480)
    write_instrument(config, symbol, "open", True, 0.5, {
        "fee_bps": 10.0, "spread_ticks_main": 1.0, "spread_ticks_off": 1.0,
        "slippage_coef": 0.0})
    write_bars(state, track, symbol, bars)
    write_rolls(state, track, symbol, [roll])
    return state, config


@pytest.fixture
def store_e(tmp_path):
    """TE: a carried position changes size and sign at the roll, 1 -> -0.5.

      0 01-07 00:00 E-1 O100 C100 vol 110 -> p = 1
      1 01-07 01:00 E-1 O100 C102 vol 95  -> p = -0.5
      2 01-07 02:00 E-2 O111 C110 vol 100 -> p = 0    roll E-1 -> E-2, gap +10;
                                                      h(1) = 1, h(2) = -0.5
      3 01-07 03:00 E-2 O109 C108 vol 100 -> p = 0
    """
    return roll_store(tmp_path, "TE", [
        ("2019-01-07 00:00", 100, 100, 110, "E-1"),
        ("2019-01-07 01:00", 100, 102, 95, "E-1"),
        ("2019-01-07 02:00", 111, 110, 100, "E-2"),
        ("2019-01-07 03:00", 109, 108, 100, "E-2"),
    ], {"ts": "2019-01-07T02:00:00+00:00", "old": "E-1", "new": "E-2", "gap": 10.0,
        "estimated": False})


def test_carried_position_changes_sign_at_the_roll(store_e):
    state, config = store_e
    res = calculate(state, config, "te", D7, D7, by_volume, {})
    expected = [
        # 0: first window bar, h = 0, nothing.
        full(1, 0, 0.0, 0, 0, 0, 0, 0),
        # 1: h 0 -> 1. gross = (0 + 1 * (102 - 100)) / 100 = 0.02; trade 1;
        #    fee 0.001; spread 0.25 / 100.
        full(-0.5, 1, 0.02, 1, 0.001, 0.25 / 100, 0, 0),
        # 2: roll +10, h(1) = 1 -> h(2) = -0.5. As of bar 2, Ca(1) = 102 + 10 = 112:
        #    gross = (1 * (111 - 112) + -0.5 * (110 - 111)) / 111 = -0.5 / 111;
        #    trade 1.5; fee 1.5 * 0.001 = 0.0015; spread 1.5 * 0.25 / 111 = 0.375 / 111;
        #    c(2) = 0.001 + 0.25 / 111; roll = 2 * |h(1)| * c(2) = 0.002 + 0.5 / 111
        #    (on h(2) it would be 2 * 0.5 * c(2) = 0.001 + 0.25 / 111).
        full(0, -0.5, -0.5 / 111, 1.5, 0.0015, 0.375 / 111, 0, 0.002 + 0.5 / 111),
        # 3: h -0.5 -> 0. gross = (-0.5 * (109 - 110) + 0) / 109 = 0.5 / 109;
        #    trade 0.5; fee 0.0005; spread 0.5 * 0.25 / 109 = 0.125 / 109.
        full(0, 0, 0.5 / 109, 0.5, 0.0005, 0.125 / 109, 0, 0),
    ]
    rows = res.rows["TE"]
    check_rows(rows, expected)
    # The row's cost, net_1x and net_2x at the roll bar, written out:
    # cost = 0.0015 + 0.375 / 111 + 0.002 + 0.5 / 111 = 0.0035 + 0.875 / 111.
    cost2 = 0.0035 + 0.875 / 111
    assert_eq(rows[2]["roll"], 0.002 + 0.5 / 111, "roll")
    assert_eq(rows[2]["cost"], cost2, "cost")
    assert_eq(rows[2]["net_1x"], -0.5 / 111 - cost2, "net_1x")
    assert_eq(rows[2]["net_2x"], -0.5 / 111 - 2 * cost2, "net_2x")

    # One day, N = 1: the day's net is the sum of the rows'.
    gross = 0.02 - 0.5 / 111 + 0.5 / 109
    cost = (0.001 + 0.0025) + cost2 + (0.0005 + 0.125 / 109)
    assert res.days == [D7]
    assert_eq(res.daily_1x[0], gross - cost, "d1")
    assert_eq(res.daily_2x[0], gross - 2 * cost, "d2")
    m = res.metrics
    assert m["trades"] == 3                       # bars 1, 2, 3
    # Turnover: trades 1 + 1.5 + 0.5 = 3, plus the rolled 2 * |h(1)| = 2: 5
    # (on h(2) it would be 2 * 0.5 = 1: 4).
    assert_eq(m["breakeven_cost"], gross / 5 * 10000, "breakeven_cost")
    assert_eq(res.costs["roll"], 0.002 + 0.5 / 111, "costs roll")


@pytest.fixture
def store_f(tmp_path):
    """TF: a flat position opens at the roll, h(1) = 0 -> h(2) = 0.5.

      0 01-07 00:00 F-1 O100 C100 vol 100 -> p = 0
      1 01-07 01:00 F-1 O100 C101 vol 105 -> p = 0.5
      2 01-07 02:00 F-2 O96  C98  vol 100 -> p = 0    roll F-1 -> F-2, gap -5;
                                                      h(1) = 0, h(2) = 0.5
      3 01-07 03:00 F-2 O99  C99  vol 100 -> p = 0
    """
    return roll_store(tmp_path, "TF", [
        ("2019-01-07 00:00", 100, 100, 100, "F-1"),
        ("2019-01-07 01:00", 100, 101, 105, "F-1"),
        ("2019-01-07 02:00", 96, 98, 100, "F-2"),
        ("2019-01-07 03:00", 99, 99, 100, "F-2"),
    ], {"ts": "2019-01-07T02:00:00+00:00", "old": "F-1", "new": "F-2", "gap": -5.0,
        "estimated": False})


def test_flat_position_opens_at_the_roll(store_f):
    state, config = store_f
    res = calculate(state, config, "tf", D7, D7, by_volume, {})
    expected = [
        full(0, 0, 0.0, 0, 0, 0, 0, 0),
        # 1: h 0 -> 0: nothing.
        full(0.5, 0, 0.0, 0, 0, 0, 0, 0),
        # 2: roll -5, h(1) = 0 -> h(2) = 0.5. As of bar 2, Ca(1) = 101 - 5 = 96:
        #    gross = (0 * (96 - 96) + 0.5 * (98 - 96)) / 96 = 1 / 96; trade 0.5;
        #    fee 0.0005; spread 0.5 * 0.25 / 96 = 0.125 / 96;
        #    roll = 2 * |h(1)| * c(2) = 0 (on h(2) it would be
        #    2 * 0.5 * (0.001 + 0.25 / 96) = 0.001 + 0.25 / 96).
        full(0, 0.5, 1 / 96, 0.5, 0.0005, 0.125 / 96, 0, 0),
        # 3: h 0.5 -> 0. gross = (0.5 * (99 - 98) + 0) / 99 = 0.5 / 99; trade 0.5;
        #    fee 0.0005; spread 0.125 / 99.
        full(0, 0, 0.5 / 99, 0.5, 0.0005, 0.125 / 99, 0, 0),
    ]
    rows = res.rows["TF"]
    check_rows(rows, expected)
    # The row's cost, net_1x and net_2x at the roll bar, written out:
    # cost = 0.0005 + 0.125 / 96 + 0.
    cost2 = 0.0005 + 0.125 / 96
    assert rows[2]["roll"] == 0.0
    assert_eq(rows[2]["cost"], cost2, "cost")
    assert_eq(rows[2]["net_1x"], 1 / 96 - cost2, "net_1x")
    assert_eq(rows[2]["net_2x"], 1 / 96 - 2 * cost2, "net_2x")

    gross = 1 / 96 + 0.5 / 99
    cost = cost2 + 0.0005 + 0.125 / 99
    assert res.days == [D7]
    assert_eq(res.daily_1x[0], gross - cost, "d1")
    assert_eq(res.daily_2x[0], gross - 2 * cost, "d2")
    m = res.metrics
    assert m["trades"] == 2                       # bars 2, 3
    # Turnover: trades 0.5 + 0.5 = 1, plus the rolled 2 * |h(1)| = 0: 1
    # (on h(2) it would be 2 * 0.5 = 1: 2).
    assert_eq(m["breakeven_cost"], gross / 1 * 10000, "breakeven_cost")
    assert res.costs["roll"] == 0.0


# ------------------------------------------------------------ metrics edges


def test_sharpe_edges_decision_30():
    assert math.isnan(sharpe([]))
    assert math.isnan(sharpe([0.1]))                      # fewer than 2 days
    assert math.isnan(sharpe([0.1, 0.1, 0.1]))            # constant (decision 30)
    assert math.isnan(sharpe([1.0, 1.0 + 2.0 ** -52]))   # std ~1.6e-16 <= 1e-12 * 1
    # [0.01, 0.03]: mean 0.02, std = 0.01 * sqrt(2): 0.02 / (0.01 * sqrt 2) * sqrt 252
    # = sqrt(2) * sqrt(252) = sqrt(504).
    assert_eq(sharpe([0.01, 0.03]), math.sqrt(504), "sharpe")


def test_max_drawdown_hand_value():
    # Running sum 1, -1, -0.5, -1.5, 1.5: peak 1, trough -1.5.
    assert_eq(max_drawdown([1.0, -2.0, 0.5, -1.0, 3.0]), 2.5, "max_drawdown")


def test_max_drawdown_first_day_loss_decision_on_d004():
    # Decision on D-004 (to be decision 41): the running sum starts at 0
    # before the first day and that 0 counts as a peak.
    # d = [-0.01, 0.004, -0.02]: running sums -0.01, -0.006, -0.026.
    # It never recovers above 0, so the peak stays 0; trough -0.026.
    # max_drawdown = 0 - (-0.026) = 0.026.
    assert_eq(max_drawdown([-0.01, 0.004, -0.02]), 0.026, "max_drawdown")
    # One losing day alone is a drawdown: 0 -> -0.01.
    assert_eq(max_drawdown([-0.01]), 0.01, "max_drawdown")
    # No fall: 0.
    assert max_drawdown([0.01, 0.02]) == 0.0
    assert max_drawdown([]) == 0.0
