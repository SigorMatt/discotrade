"""G0.1: the reference strategies against the independent calculation
(DESIGN 18.3 G0.1; decisions 2026-10-12 23 to 27, 39).

``bars fetch`` runs in-process on the fixture track ``test_mixed`` into a
pytest temporary state directory at ``AS_OF``, after the window. The window
(``FIRST`` to ``LAST``, more than eight weeks) holds what G0.1 names, and a
test asserts it: a SYNA roll, the ``synth_week`` closure of 2019-07-03 to
2019-07-04, a negative target that SYNL (which cannot be shorted) has
clipped to 0, SYNX's proportional fee, and dropped bars of every
instrument (taken from the generator, not from the gap check).

Each of the three files under ``reference/`` is then evaluated by
discotrade (``discotrade.backtest.evaluate`` and ``discotrade.metrics``, what
``backtest`` uses, and the ``backtest`` command itself in-process with
``--json``) and by ``independent_calc.calculate``, which receives only the
strategy's callable and ``PARAMS`` from discotrade's loader (decision 39).
Every per-bar field of every instrument, both daily series, every metric of
DESIGN 8 and the cost totals by component must be equal by decision 39:
``|a - b| <= 1e-12 * max(1, |a|, |b|)``, both or neither not a number, and
exact equality for counts, booleans, contracts, timestamps and dates.

The synthetic instruments' seeds are those of their fixture records under
``tests/fixtures/config/instruments/`` (``SEEDS`` below, asserted); no other
random draw is made.
"""

import contextlib
import io
import json
import math
import shutil
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from independent_calc import calculate

from discotrade import costs, metrics
from discotrade.backtest import evaluate
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange, load_calendar, load_thresholds, load_track_config
from discotrade.sources.synth import SynthSource
from discotrade.spreads import spread_table
from discotrade.strategy import load_strategy_file
from discotrade.tradingcal import trading_date

pytestmark = [pytest.mark.gate, pytest.mark.gate_m0]

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-08-05T00:00:00+00:00"
FIRST, LAST = date(2019, 6, 3), date(2019, 7, 31)
FILES = ("trend_ma.py", "zscore_reversal.py", "hour_of_day.py")
SYMBOLS = ("SYNA", "SYNL", "SYNX")
#: The seed of every random draw this gate depends on: the synthetic sources'.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
FLOATS = ("p", "h", "gross", "trade", "fee", "spread", "slippage", "roll", "cost",
          "net_1x", "net_2x")
METRICS = ("total_return", "total_return_2x", "sharpe", "sharpe_2x", "max_drawdown",
           "trades", "avg_holding_bars", "breakeven_cost", "fragile")
COSTS = ("fee", "spread", "slippage", "roll")
CLOSURE = (datetime(2019, 7, 3, 13, 0), datetime(2019, 7, 4, 18, 0))


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers."""
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


def assert_eq(a, b, what):
    assert eq(a, b), f"{what}: discotrade {a!r} != independent {b!r}"


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("g01cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def tc(config):
    return load_track_config(config, TRACK)


@pytest.fixture(scope="module")
def calendars(config, tc):
    return {name: load_calendar(config / "calendars" / f"{name}.toml")
            for name in sorted({inst.calendar for inst in tc.instruments})}


@pytest.fixture(scope="module")
def state(tmp_path_factory, config):
    state = tmp_path_factory.mktemp("g01") / "state"
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["--state", str(state), "--config", str(config), "--track", TRACK,
                     "--as-of", AS_OF, "bars", "fetch"])
    assert code == 0, out.getvalue()
    return state


@pytest.fixture(scope="module")
def thresholds(config):
    return load_thresholds(config / "thresholds.toml")


class Recorder:
    """The strategy's callable, recording each raw result (before any clip)."""

    def __init__(self, position):
        self.position = position
        self.raw: list[float] = []

    def __call__(self, bars, params):
        value = self.position(bars, params)
        self.raw.append(float(value))
        return value


def discotrade_run(state, config, tc, calendars, strat, first=FIRST, last=LAST):
    window = DateRange(first, last)
    evaluations = [
        evaluate(state, tc.track, inst, calendars[inst.calendar], strat, window,
                 spread_table=spread_table(config, inst.symbol))
        for inst in tc.instruments
    ]
    legs = [metrics.leg(e) for e in evaluations]
    return evaluations, metrics.daily_series(legs), metrics.compute(legs)


@pytest.fixture(scope="module")
def runs(state, config, tc, calendars, thresholds):
    """Per reference file: discotrade's evaluations, daily series and metrics,
    the independent result, the raw SYNL targets the independent calculation
    saw, and the ``backtest --json`` output."""
    out = {}
    for name in FILES:
        path = REPO_ROOT / "reference" / name
        strat = load_strategy_file(path, thresholds)
        evaluations, daily, m = discotrade_run(state, config, tc, calendars, strat)
        # The independent calculation evaluates the instruments in the track's
        # order, one call per window bar: SYNL's raw targets are the calls made
        # after SYNA's and before SYNX's.
        recorder = Recorder(strat.position)
        results = calculate(state, config, TRACK, FIRST, LAST, recorder, dict(strat.params))
        n = {s: len(results.rows[s]) for s in SYMBOLS}
        assert len(recorder.raw) == sum(n.values())
        raw_synl = recorder.raw[n["SYNA"]:n["SYNA"] + n["SYNL"]]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--state", str(state), "--config", str(config), "--track", TRACK,
                         "--as-of", AS_OF, "backtest", str(path), "--from",
                         FIRST.isoformat(), "--to", LAST.isoformat(), "--json"])
        assert code == 0, name
        out[name] = {"evaluations": evaluations, "daily": daily, "metrics": m,
                     "calc": results, "raw_synl": raw_synl, "path": path,
                     "params": dict(strat.params),
                     "json": json.loads(buf.getvalue())}
    return out


# ------------------------------------------------------- what the window holds


def test_seeds_are_the_fixture_records(tc):
    assert {inst.symbol: inst.source.get("seed") for inst in tc.instruments} == SEEDS
    assert tuple(inst.symbol for inst in tc.instruments) == SYMBOLS


def test_window_is_at_least_eight_weeks():
    assert (LAST - FIRST).days + 1 >= 56
    assert datetime.fromisoformat(AS_OF).date() > LAST + timedelta(days=1)


def test_syna_rolls_in_the_window(state, tc, calendars):
    syna = next(i for i in tc.instruments if i.symbol == "SYNA")
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    bars = store.read_range("SYNA", pd.Timestamp(FIRST, tz="UTC") - pd.Timedelta(days=2),
                            pd.Timestamp(LAST, tz="UTC") + pd.Timedelta(days=2))
    dates = [trading_date(calendars[syna.calendar], t.to_pydatetime()) for t in bars["ts"]]
    inside = bars[[FIRST <= d <= LAST for d in dates]].reset_index(drop=True)
    changes = [k for k in range(1, len(inside))
               if inside["contract"].iloc[k] != inside["contract"].iloc[k - 1]]
    assert changes, "no SYNA roll in the window"
    records = [json.loads(line) for line in
               (state / "rolls" / TRACK / "SYNA.jsonl").read_text().splitlines()]
    for k in changes:
        ts = inside["ts"].iloc[k]
        assert any(pd.Timestamp(r["ts"]) == ts
                   and r["old"] == inside["contract"].iloc[k - 1]
                   and r["new"] == inside["contract"].iloc[k] for r in records)


def test_window_holds_the_synth_week_closure(state, tc, calendars):
    cal = calendars["synth_week"]
    tz = ZoneInfo(cal.tz)
    assert any((c.start, c.end) == CLOSURE for c in cal.closures)
    assert FIRST <= date(2019, 7, 3) and date(2019, 7, 4) <= LAST
    start = pd.Timestamp(CLOSURE[0], tz=tz).tz_convert("UTC")
    end = pd.Timestamp(CLOSURE[1], tz=tz).tz_convert("UTC")
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    for inst in tc.instruments:
        if inst.calendar != "synth_week":
            continue
        bars = store.read_range(inst.symbol, start - pd.Timedelta(days=1),
                                end + pd.Timedelta(days=1))
        assert ((bars["ts"] < start - pd.Timedelta(hours=1)).any()
                and (bars["ts"] >= end).any()), inst.symbol
        assert not ((bars["ts"] > start - pd.Timedelta(hours=1))
                    & (bars["ts"] < end)).any(), inst.symbol


def test_synl_cannot_be_shorted_and_its_negative_target_is_clipped(tc, runs):
    synl = next(i for i in tc.instruments if i.symbol == "SYNL")
    assert synl.shorting is False
    clipped = 0
    for name in FILES:
        run = runs[name]
        raw = run["raw_synl"]
        rows = run["evaluations"][SYMBOLS.index("SYNL")].rows
        assert len(raw) == len(rows)
        for value, p, q in zip(raw, rows["p"], [r["p"] for r in run["calc"].rows["SYNL"]],
                               strict=True):
            if value < 0:
                clipped += 1
                assert p == 0.0 and q == 0.0, name
        assert (rows["h"] >= 0).all(), name
    assert clipped > 0, "no reference strategy gives SYNL a negative target in the window"


def test_synx_has_a_proportional_fee(tc, runs):
    synx = next(i for i in tc.instruments if i.symbol == "SYNX")
    assert synx.cost.fee_bps is not None and synx.cost.fee_per_side is None
    traded = 0
    for name in FILES:
        rows = runs[name]["evaluations"][SYMBOLS.index("SYNX")].rows
        for trade, fee in zip(rows["trade"], rows["fee"], strict=True):
            assert_eq(fee, trade * synx.cost.fee_bps / 10000.0, f"{name} SYNX fee")
            traded += trade > 1e-9
    assert traded > 0


def test_each_instrument_has_dropped_bars_in_the_window(state, tc, calendars):
    source = SynthSource(calendars, tc.track.bar_seconds)
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    lo = datetime.combine(FIRST - timedelta(days=2), datetime.min.time(), tzinfo=UTC)
    hi = datetime.combine(LAST + timedelta(days=2), datetime.min.time(), tzinfo=UTC)
    for inst in tc.instruments:
        cal = calendars[inst.calendar]
        dropped = [t for t in source.dropped(inst, lo, hi)
                   if FIRST <= trading_date(cal, t) <= LAST]
        assert dropped, f"{inst.symbol}: no dropped bar in the window"
        stored = set(store.read_range(inst.symbol, pd.Timestamp(lo), pd.Timestamp(hi))["ts"])
        assert not {pd.Timestamp(t) for t in dropped} & stored, inst.symbol


# ------------------------------------------------------------- the comparison


@pytest.mark.parametrize("name", FILES)
def test_per_bar_rows_are_equal(runs, name):
    run = runs[name]
    for e in run["evaluations"]:
        mine = e.rows
        theirs = run["calc"].rows[e.symbol]
        assert len(mine) == len(theirs), f"{name} {e.symbol}: row counts"
        assert len(mine) > 0, f"{name} {e.symbol}: no window bar"
        for k, row in enumerate(theirs):
            where = f"{name} {e.symbol} bar {row['ts'].isoformat()}"
            assert mine["ts"].iloc[k] == row["ts"], where
            assert mine["contract"].iloc[k] == row["contract"], where
            assert mine["date"].iloc[k] == row["date"], where
            for field in FLOATS:
                assert_eq(mine[field].iloc[k], row[field], f"{where} {field}")


@pytest.mark.parametrize("name", FILES)
def test_daily_series_are_equal(runs, name):
    run = runs[name]
    daily, calc = run["daily"], run["calc"]
    assert list(daily["date"]) == calc.days, name
    for k, day in enumerate(calc.days):
        assert_eq(daily["net_1x"].iloc[k], calc.daily_1x[k], f"{name} {day} net_1x")
        assert_eq(daily["net_2x"].iloc[k], calc.daily_2x[k], f"{name} {day} net_2x")


@pytest.mark.parametrize("name", FILES)
def test_metrics_are_equal(runs, name):
    run = runs[name]
    m, calc = run["metrics"], run["calc"].metrics
    assert m.days == len(run["calc"].days), name
    for key in METRICS:
        mine, theirs = getattr(m, key), calc[key]
        if key in ("trades", "fragile"):
            assert type(mine) is type(theirs) and mine == theirs, f"{name} {key}"
        else:
            assert_eq(mine, theirs, f"{name} {key}")


def discotrade_costs(evaluations):
    per = {e.symbol: {k: float(e.rows[k].sum()) for k in COSTS} for e in evaluations}
    subject = {k: sum(p[k] for p in per.values()) / len(evaluations) for k in COSTS}
    return subject, per


@pytest.mark.parametrize("name", FILES)
def test_cost_totals_are_equal(runs, name):
    run = runs[name]
    subject, per = discotrade_costs(run["evaluations"])
    for k in COSTS:
        assert_eq(subject[k], run["calc"].costs[k], f"{name} subject {k}")
        for symbol in SYMBOLS:
            assert_eq(per[symbol][k], run["calc"].costs_by_instrument[symbol][k],
                      f"{name} {symbol} {k}")


def figure(value):
    return math.nan if value is None else value


# Decision 42: every key of the ``--json`` object and of each per-instrument
# map is compared with the module's evaluation and the independent
# calculation, for each reference file on the G0.1 window and for one more
# case, ``LOW``: zscore_reversal.py on a weekend where SYNX's target at the
# last window bar (-1) is below every earlier target and 0, so that the
# lowest position read from ``h`` alone differs from the lowest of ``p`` and
# ``h`` (asserted by ``test_low_case_ends_on_a_new_low``), and where SYNA and
# SYNL have no window bar (their positions print as null).
LOW_FILE, LOW_SYMBOL = "zscore_reversal.py", "SYNX"
LOW_FIRST, LOW_LAST = date(2019, 3, 23), date(2019, 3, 24)
LOW = f"{LOW_FILE} {LOW_FIRST.isoformat()} to {LOW_LAST.isoformat()}"
CASES = (*FILES, LOW)
DESCRIPTIVE = ("strategy", "params", "track", "from", "to", "cost_model", "config_hash")
JSON_KEYS = frozenset((*DESCRIPTIVE, "days", *METRICS, "costs", "instruments"))
SUMS = (*COSTS, "cost", "net_1x", "net_2x")
INSTRUMENT_KEYS = frozenset(("bars", "trades", "position_min", "position_max", *SUMS))


def backtest_json(state, config, path, first, last):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(["--state", str(state), "--config", str(config), "--track", TRACK,
                     "--as-of", AS_OF, "backtest", str(path), "--from", first.isoformat(),
                     "--to", last.isoformat(), "--json"])
    assert code == 0, path.name
    return json.loads(buf.getvalue())


@pytest.fixture(scope="module")
def cases(runs, state, config, tc, calendars, thresholds):
    """Per case: discotrade's evaluations and metrics, the independent
    result, the ``backtest --json`` output, the file, its ``PARAMS`` and the
    window."""
    out = {name: {**runs[name], "first": FIRST, "last": LAST} for name in FILES}
    path = REPO_ROOT / "reference" / LOW_FILE
    strat = load_strategy_file(path, thresholds)
    evaluations, daily, m = discotrade_run(state, config, tc, calendars, strat,
                                           LOW_FIRST, LOW_LAST)
    calc = calculate(state, config, TRACK, LOW_FIRST, LOW_LAST, strat.position,
                     dict(strat.params))
    out[LOW] = {"evaluations": evaluations, "daily": daily, "metrics": m, "calc": calc,
                "path": path, "params": dict(strat.params), "first": LOW_FIRST,
                "last": LOW_LAST,
                "json": backtest_json(state, config, path, LOW_FIRST, LOW_LAST)}
    return out


@pytest.mark.parametrize("name", CASES)
def test_backtest_json_equals_the_module(cases, name):
    run = cases[name]
    out, m = run["json"], run["metrics"]
    assert out["days"] == m.days
    for key in METRICS:
        mine = getattr(m, key)
        if key in ("trades", "fragile"):
            assert out[key] == mine and type(out[key]) is type(mine), f"{name} {key}"
            assert out[key] == run["calc"].metrics[key], f"{name} --json {key}"
        else:
            assert_eq(figure(out[key]), mine, f"{name} --json {key}")
            assert_eq(figure(out[key]), run["calc"].metrics[key], f"{name} --json {key}")
    assert out["days"] == len(run["calc"].days), f"{name} --json days"
    subject, per = discotrade_costs(run["evaluations"])
    for k in COSTS:
        assert_eq(out["costs"][k], subject[k], f"{name} --json costs {k}")
        assert_eq(out["costs"][k], run["calc"].costs[k], f"{name} --json costs {k}")
        for symbol in SYMBOLS:
            assert_eq(out["instruments"][symbol][k], per[symbol][k],
                      f"{name} --json {symbol} {k}")
    for e in run["evaluations"]:
        assert out["instruments"][e.symbol]["bars"] == len(e.rows)
        assert out["instruments"][e.symbol]["bars"] == len(run["calc"].rows[e.symbol])


def instrument_figures(rows: pd.DataFrame) -> dict:
    """One instrument's ``--json`` map computed in the test from per-bar rows
    (DESIGN 8, decisions 25, 27 and 42): its bar count, its count of bars
    with ``trade > 1e-9``, the lowest and highest of every ``p`` and ``h`` of
    its window bars (not a number when it has none), and the sum over its
    bars of each cost component, ``cost``, ``net_1x`` and ``net_2x``."""
    positions = [*rows["p"].tolist(), *rows["h"].tolist()]
    return {
        "bars": len(rows),
        "trades": int((rows["trade"].to_numpy(dtype=float) > 1e-9).sum()),
        "position_min": float(min(positions)) if positions else math.nan,
        "position_max": float(max(positions)) if positions else math.nan,
        **{k: float(rows[k].sum()) for k in SUMS},
    }


def test_low_case_ends_on_a_new_low(cases):
    for rows in (cases[LOW]["evaluations"][SYMBOLS.index(LOW_SYMBOL)].rows,
                 pd.DataFrame(cases[LOW]["calc"].rows[LOW_SYMBOL], columns=list(FLOATS))):
        assert len(rows) > 0
        assert min(*rows["p"], *rows["h"]) < min(rows["h"])
    for symbol in SYMBOLS:
        if symbol != LOW_SYMBOL:
            assert len(cases[LOW]["evaluations"][SYMBOLS.index(symbol)].rows) == 0, symbol


@pytest.mark.parametrize("name", CASES)
def test_backtest_json_keys_are_exactly_those_compared(cases, name):
    out = cases[name]["json"]
    assert set(out) == JSON_KEYS, f"{name}: --json keys"
    assert set(out["costs"]) == set(COSTS), f"{name}: --json costs keys"
    assert tuple(out["instruments"]) == tuple(sorted(SYMBOLS)), f"{name}: --json instruments"
    for symbol in SYMBOLS:
        assert set(out["instruments"][symbol]) == INSTRUMENT_KEYS, f"{name} {symbol}: keys"


@pytest.mark.parametrize("name", CASES)
def test_backtest_json_descriptive_keys(cases, config, tc, name):
    run = cases[name]
    out = run["json"]
    assert out["strategy"] == f"reference/{run['path'].name}"
    assert out["strategy"] == run["path"].relative_to(REPO_ROOT).as_posix()
    assert out["params"] == run["params"] and out["params"]
    assert out["track"] == TRACK
    assert out["from"] == run["first"].isoformat() and out["to"] == run["last"].isoformat()
    assert out["cost_model"] == "c1" == costs.VERSION
    tables = {inst.symbol: spread_table(config, inst.symbol) for inst in tc.instruments}
    assert out["config_hash"] == costs.config_hash(tc.instruments, tables)


@pytest.mark.parametrize("name", CASES)
def test_backtest_json_per_instrument_maps(cases, name):
    """Every key of each instrument's ``--json`` map equals the figure
    computed from discotrade's per-bar rows and from the independent
    calculation's rows (decision 42); counts exactly, reals by decision 39,
    and a position of an instrument with no window bar is null."""
    run = cases[name]
    out = run["json"]["instruments"]
    for e in run["evaluations"]:
        mine = instrument_figures(e.rows)
        theirs = instrument_figures(pd.DataFrame(run["calc"].rows[e.symbol],
                                                 columns=list(FLOATS)))
        got = out[e.symbol]
        assert set(mine) == set(theirs) == INSTRUMENT_KEYS
        for key in ("bars", "trades"):
            assert type(got[key]) is int, f"{name} {e.symbol} --json {key} type"
            assert got[key] == mine[key] == theirs[key], (
                f"{name} {e.symbol} --json {key}: {got[key]} module {mine[key]} "
                f"independent {theirs[key]}")
        for key in ("position_min", "position_max"):
            assert (got[key] is None) == (len(e.rows) == 0), f"{name} {e.symbol} {key}"
        for key in ("position_min", "position_max", *SUMS):
            assert_eq(figure(got[key]), mine[key], f"{name} {e.symbol} --json {key} (module)")
            assert_eq(figure(got[key]), theirs[key],
                      f"{name} {e.symbol} --json {key} (independent)")
