"""G0.2: a deliberately cheating strategy cannot gain (DESIGN 18.3 G0.2, 6.2, 7.1,
12.1; I-2; decision 40 of meta/decisions/decisions-2026-10-12.md).

The strategy is ``tests/fixtures/strategies/cheat_lookahead.py``, a text a
worker could submit. It is run through the module API (decision 40) on the
fixture track ``test_mixed``, whose stores are filled by the ``discotrade``
command run in-process (``discotrade.cli.main``, the console script's
function) with ``bars fetch`` and a clock given by ``--as-of``, under a pytest
temporary directory. A store "ends at t" when its fetch clock is the close
of bar ``t``; the long store's clock is more than a year after the window.

Each evaluation loads the text afresh, so that its module-level list holds
the frames of that evaluation only: state carried between evaluations is
for the sandbox (DESIGN 12.4) to refuse, not for this item.

Seeds: the test draws nothing at random. The synthetic bars come from the
fixture records' seeds, written here in ``SEEDS`` and checked against them.
"""

import ast
import math
import shutil
from dataclasses import asdict
from datetime import date

import numpy as np
import pandas as pd
import pytest

from discotrade import metrics
from discotrade.backtest import evaluate
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange, load_calendar, load_thresholds, load_track_config
from discotrade.spreads import spread_table
from discotrade.strategy import Strategy, load_strategy_file

pytestmark = [pytest.mark.gate, pytest.mark.gate_m0]

CHEAT = REPO_ROOT / "tests" / "fixtures" / "strategies" / "cheat_lookahead.py"
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
HOUR = 3600
#: The seed of each instrument's synthetic source, as its fixture record gives it.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
#: A window of 29 days; SYNA rolls inside it (2019-06-14).
WINDOW = DateRange(date(2019, 6, 3), date(2019, 7, 1))
LONG_AS_OF = pd.Timestamp("2020-07-15 00:00", tz="UTC")
#: Bars spread evenly over the window, besides the first, the last and the roll's.
SPREAD = 9

# DESIGN 12.1, as written there.
ALLOWED_IMPORTS = {"numpy", "pandas", "indicators"}
REJECTED_NAMES = {
    "eval", "exec", "compile", "open", "input", "breakpoint", "globals", "locals", "vars",
    "dir", "getattr", "setattr", "delattr", "type", "object", "super", "memoryview", "exit",
    "quit", "help", "print"}
REJECTED_ATTRIBUTES = {
    "eval", "query", "pipe", "system", "popen", "load", "loads", "save", "savez", "loadtxt",
    "savetxt", "genfromtxt", "fromfile", "tofile", "memmap", "ctypeslib", "random",
    "default_rng", "RandomState", "now", "today", "time", "datetime", "testing", "f2py",
    "distutils"}
REJECTED_NODES = (ast.ClassDef, ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.AsyncFor,
                  ast.AsyncWith, ast.Await, ast.Yield, ast.YieldFrom, ast.With)


def as_of_text(ts: pd.Timestamp) -> str:
    return ts.isoformat()


# ------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def tc(config):
    return load_track_config(config, TRACK)


@pytest.fixture(scope="module")
def thresholds(config):
    return load_thresholds(config / "thresholds.toml")


@pytest.fixture(scope="module")
def calendars(config):
    return {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}


def fetch(tmp_path_factory, config, as_of: pd.Timestamp):
    state = tmp_path_factory.mktemp("state")
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of_text(as_of), "bars", "fetch"]) == 0
    return state


@pytest.fixture(scope="module")
def long_state(tmp_path_factory, config):
    return fetch(tmp_path_factory, config, LONG_AS_OF)


def cheat(thresholds):
    """The cheating text, loaded afresh by discotrade's loader."""
    return load_strategy_file(CHEAT, thresholds)


def run(state, tc, calendars, config, symbol, strat, window=WINDOW):
    inst = next(i for i in tc.instruments if i.symbol == symbol)
    return evaluate(state, tc.track, inst, calendars[inst.calendar], strat, window,
                    spread_table=spread_table(config, symbol))


@pytest.fixture(scope="module")
def long_runs(long_state, tc, calendars, config, thresholds):
    return {s: run(long_state, tc, calendars, config, s, cheat(thresholds))
            for s in tc.track.instruments}


@pytest.fixture(scope="module")
def roll_bar(long_runs):
    """The index, in SYNA's window rows, of its one roll inside the window."""
    contract = long_runs["SYNA"].rows["contract"].to_numpy()
    rolls = [k for k in range(1, len(contract)) if contract[k] != contract[k - 1]]
    assert len(rolls) == 1
    return rolls[0]


@pytest.fixture(scope="module")
def clocks(long_runs, roll_bar):
    """The fetch clocks (close of a bar) of the truncated stores, and the bars
    every instrument must see as its last at one of them."""
    must = {}
    for symbol, ev in long_runs.items():
        ts = ev.rows["ts"]
        picks = [0, len(ts) - 1]
        picks += [round(k * (len(ts) - 1) / (SPREAD + 1)) for k in range(1, SPREAD + 1)]
        must[symbol] = {ts.iloc[k] for k in picks}
    syna = long_runs["SYNA"].rows["ts"]
    must["SYNA"] |= {syna.iloc[roll_bar + d] for d in (-1, 0, 1)}
    every = sorted({t for ts in must.values() for t in ts})
    return [t + pd.Timedelta(seconds=HOUR) for t in every], must


@pytest.fixture(scope="module")
def truncated(tmp_path_factory, config, clocks):
    """One store per clock, each ending at that clock."""
    return {c: fetch(tmp_path_factory, config, c) for c in clocks[0]}


def store_last(state, symbol):
    return BarStore(state, TRACK, HOUR).last_ts(symbol)


def metric_dict(m):
    return {k: ("nan" if isinstance(v, float) and math.isnan(v) else v)
            for k, v in asdict(m).items()}


# ------------------------------------------------------------------- the text


def test_the_text_passes_the_loader_and_uses_nothing_the_static_check_rejects(thresholds):
    strat = cheat(thresholds)
    assert strat.params == {"lookback": 24, "tail": 6} and strat.grid is None
    source = CHEAT.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= thresholds["validation.max_lines"]
    tree = ast.parse(source)
    names, attributes, imports = set(), set(), set()
    for node in ast.walk(tree):
        assert not isinstance(node, REJECTED_NODES), ast.dump(node)
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.FunctionDef | ast.Lambda):
            if isinstance(node, ast.FunctionDef):
                names.add(node.name)
                assert not node.decorator_list
        elif isinstance(node, ast.Import):
            imports |= {a.name for a in node.names}
            names |= {a.asname for a in node.names if a.asname}
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    assert imports and imports <= ALLOWED_IMPORTS
    assert not [n for n in names | attributes if n.startswith("_")]
    assert not names & REJECTED_NAMES
    assert not attributes & REJECTED_ATTRIBUTES
    assert not [a for a in attributes if a.startswith("read_")
                or (a.startswith("to_") and a != "to_numpy")]
    # What decision 40 lists: earlier frames kept at module level and read
    # again, the index, and rows past the end through each of these routes.
    assert {"iloc", "loc", "values", "to_numpy", "base", "attrs", "index",
            "append"} <= attributes
    module_level = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets}
    assert "SEEN" in module_level


def frame_of(closes):
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    return pd.DataFrame({"open": closes, "high": closes + 1, "low": closes - 1,
                         "close": closes, "volume": np.full(n, 1000.0),
                         "hour": np.arange(n) % 24, "weekday": np.zeros(n, dtype=np.int64)})


@pytest.mark.parametrize("step, want", [(+1.0, 1.0), (-1.0, -1.0)])
def test_the_text_reads_later_rows_wherever_a_frame_holds_them(thresholds, step, want):
    closes = 100.0 + np.sin(np.arange(40)) * 3
    later = np.append(closes, closes[-1] + step)
    plain = frame_of(closes)
    # Through the base of a view of a longer frame.
    view = frame_of(later).iloc[:-1]
    pd.testing.assert_frame_equal(view, plain)
    assert cheat(thresholds).position(view, {"lookback": 24, "tail": 6}) == want
    # Through attrs.
    tagged = plain.copy()
    tagged.attrs["later"] = later
    assert cheat(thresholds).position(tagged, {"lookback": 24, "tail": 6}) == want
    # Through an earlier frame it kept, read again at a later call.
    strat = cheat(thresholds)
    strat.position(frame_of(later).iloc[:-2], {"lookback": 24, "tail": 6})
    assert strat.position(plain, {"lookback": 24, "tail": 6}) == want
    # A plain frame holds nothing later: the momentum rule decides.
    assert abs(cheat(thresholds).position(plain, {"lookback": 24, "tail": 6})) < 1.0


# ------------------------------------------------------------- the harness


def test_the_synthetic_seeds_are_the_ones_written_here(tc):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS


def test_positions_are_truncation_invariant(long_state, long_runs, clocks, truncated, tc,
                                            calendars, config, thresholds):
    clock_list, must = clocks
    for symbol in tc.track.instruments:
        b = long_runs[symbol]
        assert store_last(long_state, symbol) - b.rows["ts"].iloc[-1] > pd.Timedelta(days=365)
        seen = set()
        for c in clock_list:
            state = truncated[c]
            t = store_last(state, symbol)
            if t not in set(b.rows["ts"]):
                continue            # this store ends outside the window for this one
            a = run(state, tc, calendars, config, symbol, cheat(thresholds))
            assert a.rows["ts"].iloc[-1] == t
            head = b.rows[b.rows["ts"] <= t].reset_index(drop=True)
            pd.testing.assert_frame_equal(a.rows, head, check_exact=True)
            seen.add(t)
        assert must[symbol] <= seen, (symbol, sorted(must[symbol] - seen))
        assert len(seen) >= 10, (symbol, len(seen))
        assert b.rows["p"].nunique() > 10, symbol


def test_rows_and_metrics_do_not_depend_on_later_bars(long_runs, clocks, truncated, tc,
                                                       calendars, config, thresholds):
    assert WINDOW.days() >= 28
    short_runs = {}
    for symbol in tc.track.instruments:
        b = long_runs[symbol]
        last = b.rows["ts"].iloc[-1]
        state = truncated[last + pd.Timedelta(seconds=HOUR)]
        assert store_last(state, symbol) == last
        a = run(state, tc, calendars, config, symbol, cheat(thresholds))
        pd.testing.assert_frame_equal(a.rows, b.rows, check_exact=True)
        assert (metric_dict(metrics.compute([metrics.leg(a)]))
                == metric_dict(metrics.compute([metrics.leg(b)])))
        short_runs[symbol] = a
    order = tc.track.instruments
    assert (metric_dict(metrics.compute([metrics.leg(short_runs[s]) for s in order]))
            == metric_dict(metrics.compute([metrics.leg(long_runs[s]) for s in order])))


def leaking(strat, ev):
    """``strat`` given, at each window bar, the harness's frame inside a longer
    one that holds the next stored bar (prices continued as of the frame's last
    row), so that the frame's base reaches it."""
    closes = ev.bars["close"].to_numpy() - ev.gaps
    calls = []

    def position(bars, params):
        k = ev.first + len(calls)
        calls.append(k)
        if k + 1 < len(ev.bars):
            extra = bars.iloc[[-1]].copy()
            extra["close"] = closes[k + 1]
            bigger = pd.concat([bars, extra], ignore_index=True)
            view = bigger.iloc[:-1]
            pd.testing.assert_frame_equal(view, bars)
            bars = view
        return strat.position(bars, params)
    return Strategy(name="leak", source=strat.source, params=strat.params, grid=None,
                    position=position)


#: The instruments on which one bar of foresight earns more than it costs. On
#: SYNL (price near 30, tick 0.25) a one-tick spread alone is near 0.8% a
#: trade, more than an hourly bar moves, so the control's gain there is gross
#: only; the subject of all three gains net.
NET_GAIN = {"SYNA", "SYNX"}


def test_control_the_comparison_sees_a_gain_when_a_frame_holds_later_rows(
        long_state, long_runs, tc, calendars, config, thresholds):
    leaked = {}
    for symbol in tc.track.instruments:
        honest = long_runs[symbol]
        ev = run(long_state, tc, calendars, config, symbol,
                 leaking(cheat(thresholds), honest))
        assert not np.array_equal(ev.rows["p"].to_numpy(), honest.rows["p"].to_numpy())
        assert ev.rows["gross"].sum() > honest.rows["gross"].sum(), symbol
        got = metrics.compute([metrics.leg(ev)]).total_return
        base = metrics.compute([metrics.leg(honest)]).total_return
        if symbol in NET_GAIN:
            assert got > base, (symbol, got, base)
        leaked[symbol] = ev
    order = tc.track.instruments
    assert (metrics.compute([metrics.leg(leaked[s]) for s in order]).total_return
            > metrics.compute([metrics.leg(long_runs[s]) for s in order]).total_return)
