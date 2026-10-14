"""Stage 2 of the validation sequence: the dry run and the grid on W, on the
exposure-adjusted measure (DESIGN 12.2 stage 2, 4.1, 8; owner's decisions O-4,
O-17, O-18; decision 97 of 2026-10-14-m12; decisions 2026-10-14 81, 86 (a), 89;
decisions 2026-10-12 23, 25, 30, 39; R-23).

The stores are filled by ``bars fetch`` on the fixture track ``test_synth``
(every instrument shortable, on ``synth_week``; SYNA rolls on 2019-06-14,
inside W), run in-process (``discotrade.cli.main``) with the clock given by
``--as-of`` ``AS_OF``, under a pytest temporary directory. Every stage runs on W
of the day ``DAY`` (2019-06-11 to 2019-07-08), the track's own W, at the
production thresholds (``config/thresholds.toml`` copied into the fixture
configuration, as the sandbox tests do) and the limits of
``tests/fixtures/config/run.toml`` (those of ``config/run.toml``). Job
directories go under a pytest temporary directory.

The test's own computation (``own_*``) takes the evaluation rows from
``backtest.evaluate`` of the fixture's text loaded by ``strategy``, the stored
bars from the month Parquet files and the roll records with ``pyarrow``,
``pandas`` and ``json``, and calls none of ``paper.adjusted``,
``paper.adjusted_rows``, ``paper.unit_bars``, ``paper.unit_returns``,
``paper.average_positions``, ``paper.window_units`` or
``paper.window_positions``: the unit return of a bar is ``(1 * (O(u) - (C(u-1)
+ gap)) + 1 * (C(u) - O(u))) / O(u)`` with ``u-1`` the previous stored bar and
``gap`` the recorded gap of a roll at ``u``; ``hbar_i(W)`` the mean of the rows'
``h``; equality is decision 39's.

The slow fixture's tests are the only ones here that meet elapsed time; they
assert the stage, never a measured time (I-12). Seeds: the synthetic bars come
from the fixture records' seeds, written here in ``SEEDS`` and checked. No
random draw is made here.
"""

import ast
import dataclasses
import json
import math
import re
import shutil
import tomllib
from datetime import date

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from discotrade import backtest, journal
from discotrade.cli import REPO_ROOT, main
from discotrade.sandbox.inprocess import InProcessSandbox
from discotrade.sandbox.process import ProcessSandbox
from discotrade.strategy import load_strategy_file
from discotrade.validation import sequence
from discotrade.validation.sequence import Context, Submission

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
REGISTER = REPO_ROOT / "tests" / "fixtures" / "return_readers.toml"
TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
#: The day D (a Monday): W is 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
AS_OF = "2019-07-25T00:00:00+00:00"
LEAN = STRATEGIES / "grid_lean.py"
ERROR_TEXTS: list[str] = []


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers (None for not a number)."""
    a = math.nan if a is None else float(a)
    b = math.nan if b is None else float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def state(tmp_path_factory, config):
    path = tmp_path_factory.mktemp("state")
    assert main(["--state", str(path), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    return path


@pytest.fixture(scope="module")
def scratch(tmp_path_factory):
    return tmp_path_factory.mktemp("jobs")


def context(state, config, setup, backend):
    return Context(state, config, setup, DAY, backend)


def from_file(path) -> Submission:
    return Submission.from_source(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def lean(state, config, setup, scratch):
    """The lean fixture through stage 2 on the child-process backend."""
    return sequence.dry_run_and_grid(context(state, config, setup, ProcessSandbox(scratch)),
                                     from_file(LEAN))


def test_the_seeds_window_and_thresholds_are_the_ones_written_here(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    w = setup.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)
    assert setup.thresholds["validation.call_p95_ms"] == 50
    assert setup.thresholds["validation.call_max_ms"] == 500


# ------------------------------------------------------------- the combinations


def test_the_combinations_come_in_decision_97_a_order_for_a_grid_of_two_keys():
    params = {"a": 1, "b": 2, "c": 3}
    grid = {"b": [20, 21], "a": [10, 11, 12]}
    assert sequence.combinations(params, grid) == [
        {"a": 10, "b": 20, "c": 3}, {"a": 11, "b": 20, "c": 3}, {"a": 12, "b": 20, "c": 3},
        {"a": 10, "b": 21, "c": 3}, {"a": 11, "b": 21, "c": 3}, {"a": 12, "b": 21, "c": 3}]
    assert sequence.combinations(params, None) == [params]
    sub = from_file(LEAN)
    assert sub.params == {"bias": 0.5, "spare": 1, "lookback": 192}
    assert sub.grid == {"bias": [0.5, -0.5], "spare": [1, 2]}


def test_the_grid_runs_its_combinations_in_that_order(lean):
    assert lean.ok, lean.text
    assert [r["params"] for r in lean.grid["results"]] == [
        {"bias": 0.5, "spare": 1, "lookback": 192}, {"bias": 0.5, "spare": 2, "lookback": 192},
        {"bias": -0.5, "spare": 1, "lookback": 192}, {"bias": -0.5, "spare": 2, "lookback": 192}]


# ------------------------------------------------------------- the dry run


def test_a_combination_returning_a_value_out_of_range_fails_the_dry_run(
        state, config, setup, scratch):
    out = sequence.dry_run_and_grid(context(state, config, setup, ProcessSandbox(scratch)),
                                    from_file(STRATEGIES / "grid_out_of_range.py"))
    assert not out.ok
    assert (out.stage, out.rule) == ("dry_run", "out_of_range")
    assert out.text == ("dry_run [out_of_range]: position returned a number outside [-1, 1] "
                        "at window bar 0 (parameter set 1)")
    with pytest.raises(ValueError):
        out.result()
    ERROR_TEXTS.append(out.text)


def test_a_text_that_fails_to_load_fails_the_dry_run(state, config, setup, scratch):
    # The runner's stage ``load`` maps to the sequence's ``dry_run`` (decision 95 (d)).
    source = (STRATEGIES / "no_position.py").read_text(encoding="utf-8")
    out = sequence.dry_run_and_grid(context(state, config, setup, ProcessSandbox(scratch)),
                                    Submission.from_source(source))
    assert (out.stage, out.rule) == ("dry_run", "no_position")
    assert out.text.startswith("dry_run: load [no_position]: ")
    ERROR_TEXTS.append(out.text)


# ------------------------------------------------------------- the test's own computation


def own_bars(state, symbol) -> pd.DataFrame:
    files = sorted((state / "bars" / TRACK / symbol).glob("*.parquet"))
    bars = pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True)
    return bars.sort_values("ts").reset_index(drop=True)


def own_gaps(state, symbol) -> dict:
    path = state / "rolls" / TRACK / f"{symbol}.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[(pd.Timestamp(r["ts"]), r["old"], r["new"])] = float(r["gap"])
    return out


def own_unit(state, symbol) -> tuple[dict, dict]:
    """Per bar ts: the unit return, and whether a roll happens at that bar."""
    bars, gaps = own_bars(state, symbol), own_gaps(state, symbol)
    unit, rolled = {}, {}
    for k in range(len(bars)):
        ts = bars["ts"][k]
        o, c = float(bars["open"][k]), float(bars["close"][k])
        if k == 0:
            unit[ts], rolled[ts] = (1.0 * (c - o)) / o, False
            continue
        old, new = bars["contract"][k - 1], bars["contract"][k]
        gap = gaps[(ts, old, new)] if old != new else 0.0
        prev = float(bars["close"][k - 1]) + gap
        unit[ts] = (1.0 * (o - prev) + 1.0 * (c - o)) / o
        rolled[ts] = old != new
    return unit, rolled


def own_rows(state, setup, params) -> list[pd.DataFrame]:
    """The evaluation rows of the lean text under ``params`` on W, per instrument."""
    strategy = load_strategy_file(LEAN, setup.thresholds)
    w = setup.track.windows(DAY).w
    return [backtest.evaluate(state, setup.track, inst, setup.calendars[inst.calendar],
                              strategy, w, params, setup.spread_tables.get(inst.symbol)).rows
            for inst in setup.instruments]


def own_sharpe(d) -> float:
    x = [float(v) for v in d]
    if len(x) < 2:
        return math.nan
    sd = float(np.std(x, ddof=1))
    if all(v == x[0] for v in x) or not sd > 1e-12 * max(abs(v) for v in x):
        return math.nan
    return float(np.mean(x)) / sd * math.sqrt(252)


def own_daily(rows: list[pd.DataFrame], column: str) -> dict:
    days = sorted({d for r in rows for d in r["date"]})
    return {d: sum(float(r[column][r["date"] == d].sum()) for r in rows) / len(rows)
            for d in days}


def own_figures(state, setup, params, units) -> dict:
    """Plain and adjusted figures and metrics of ``params`` on W, by hand."""
    rows = own_rows(state, setup, params)
    symbols = [i.symbol for i in setup.instruments]
    hbar = {s: float(r["h"].mean()) if len(r) else 0.0 for s, r in zip(symbols, rows, strict=True)}
    out = {"hbar": hbar}
    for column in ("net_1x", "net_2x"):
        daily = own_daily(rows, column)
        exposure = {}
        for d in daily:
            total = 0.0
            for s, r in zip(symbols, rows, strict=True):
                unit = units[s][0]
                big_r = sum(unit[ts] for ts, dd in zip(r["ts"], r["date"], strict=True) if dd == d)
                total += hbar[s] * big_r
            exposure[d] = total / len(rows)
        adjusted = [daily[d] - exposure[d] for d in daily]
        out[column] = {"plain": list(daily.values()), "adjusted": adjusted}
    one, two = out["net_1x"], out["net_2x"]
    lengths = []
    gross = turnover = 0.0
    for s, r in zip(symbols, rows, strict=True):
        h = r["h"].to_numpy(dtype=float)
        run = 0
        for k, v in enumerate(np.sign(h)):
            if v != 0 and run and v == np.sign(h[k - 1]):
                run += 1
                continue
            if run:
                lengths.append(run)
            run = 1 if v != 0 else 0
        if run:
            lengths.append(run)
        gross += float(r["gross"].sum())
        turnover += float(r["trade"].sum())
        rolled = units[s][1]
        for k, ts in enumerate(r["ts"]):
            if rolled[ts]:
                turnover += 2.0 * abs(h[k - 1] if k > 0 else 0.0)
    running = np.concatenate([[0.0], np.cumsum(one["plain"])])
    out["metrics"] = {
        "days": len(one["plain"]),
        "total_return": float(sum(one["plain"])), "total_return_2x": float(sum(two["plain"])),
        "sharpe": own_sharpe(one["plain"]), "sharpe_2x": own_sharpe(two["plain"]),
        "max_drawdown": float(np.max(np.maximum.accumulate(running) - running)),
        "trades": int(sum(int((r["trade"] > 1e-9).sum()) for r in rows)),
        "avg_holding_bars": float(np.mean(lengths)) if lengths else math.nan,
        "breakeven_cost": gross / turnover * 10000.0 if turnover > 0 else math.nan,
    }
    m = out["metrics"]
    m["fragile"] = bool(m["total_return"] > 0 and m["total_return_2x"] < 0)
    out["adjusted"] = {"sharpe": own_sharpe(one["adjusted"]),
                       "sharpe_2x": own_sharpe(two["adjusted"]),
                       "total_return": float(sum(one["adjusted"])),
                       "total_return_2x": float(sum(two["adjusted"]))}
    return out


@pytest.fixture(scope="module")
def own(state, setup):
    """The test's own figures for each combination of the lean fixture, in order."""
    units = {i.symbol: own_unit(state, i.symbol) for i in setup.instruments}
    combos = [{"bias": b, "spare": s, "lookback": 192} for b in (0.5, -0.5) for s in (1, 2)]
    return [own_figures(state, setup, c, units) for c in combos]


def first_best(values) -> int:
    best = None
    for k, v in enumerate(values):
        if not math.isnan(v) and (best is None or v > values[best]):
            best = k
    return 0 if best is None else best


# ------------------------------------------------------------- the grid on W


def test_the_grid_fixes_the_greatest_adjusted_sharpe_where_the_plain_would_fix_another(
        lean, own):
    # O-17: the window holds SYNA's roll (2019-06-14), so a roll gap is in it.
    adjusted = [f["adjusted"]["sharpe"] for f in own]
    plain = [f["metrics"]["sharpe"] for f in own]
    by_adjusted, by_plain = first_best(adjusted), first_best(plain)
    assert by_adjusted == 0 and by_plain == 2     # long-leaning by adjusted, short by plain
    assert lean.ok, lean.text
    assert lean.params == {"bias": 0.5, "spare": 1, "lookback": 192}
    assert lean.grid["fixed"] == lean.params


def test_a_tie_fixes_the_first_in_order(lean, own):
    # ``spare`` is read by nothing: combinations 0 and 1 tie, and 2 and 3.
    assert own[0]["adjusted"]["sharpe"] == own[1]["adjusted"]["sharpe"]
    results = lean.grid["results"]
    assert results[0]["adjusted"] == results[1]["adjusted"]
    assert lean.grid["fixed"]["spare"] == 1
    assert sequence.first_greatest([1.0, 2.0, 2.0, 1.5]) == 1
    assert sequence.first_greatest([math.nan, -3.0, -3.0]) == 1
    assert sequence.first_greatest([-1.0, math.nan, 0.5]) == 2


def test_a_grid_whose_figures_are_all_not_a_number_fixes_the_first(
        state, config, setup, scratch):
    out = sequence.dry_run_and_grid(context(state, config, setup, ProcessSandbox(scratch)),
                                    from_file(STRATEGIES / "grid_flat.py"))
    assert out.ok, out.text
    assert out.params == {"tag": 1}
    for r in out.grid["results"]:
        assert r["plain"] == r["adjusted"] == {"sharpe": None, "sharpe_2x": None}
    assert sequence.first_greatest([math.nan, math.nan, math.nan]) == 0


def test_the_result_has_decision_97_e_shapes_and_the_test_s_values(lean, own, setup):
    result = lean.result()
    assert set(result) == {"grid", "metrics_w", "adjusted_w"}
    grid = result["grid"]
    assert set(grid) == {"grid", "fixed", "results"}
    assert grid["grid"] == {"bias": [0.5, -0.5], "spare": [1, 2]}
    assert len(grid["results"]) == len(own) == 4
    for entry, mine in zip(grid["results"], own, strict=True):
        assert set(entry) == {"params", "plain", "adjusted"}
        for measure, figures in (("plain", mine["metrics"]), ("adjusted", mine["adjusted"])):
            assert set(entry[measure]) == {"sharpe", "sharpe_2x"}
            for key in ("sharpe", "sharpe_2x"):
                assert eq(entry[measure][key], figures[key]), (measure, key)
                assert entry[measure][key] is None or isinstance(entry[measure][key], float)
    fixed = own[0]
    metrics_w = result["metrics_w"]
    assert set(metrics_w) == set(fixed["metrics"])
    for key, value in fixed["metrics"].items():
        if key in ("days", "trades", "fragile"):
            assert metrics_w[key] == value, key
        else:
            assert eq(metrics_w[key], value), key
    adjusted_w = result["adjusted_w"]
    assert set(adjusted_w) == {"sharpe", "sharpe_2x", "total_return", "total_return_2x",
                               "avg_position"}
    for key, value in fixed["adjusted"].items():
        assert eq(adjusted_w[key], value), key
    assert list(adjusted_w["avg_position"]) == [i.symbol for i in setup.instruments]
    for symbol, value in fixed["hbar"].items():
        assert eq(adjusted_w["avg_position"][symbol], value), symbol
    # The fixed combination's targets and evaluations, for stages 3 to 5.
    assert set(lean.targets) == set(SEEDS)
    assert [ev.symbol for ev in lean.evaluations] == list(SEEDS)


# ------------------------------------------------------------- the call-time limits


@pytest.fixture(scope="module")
def slow_function():
    source = (STRATEGIES / "slow_call.py").read_text(encoding="utf-8")
    namespace: dict = {}
    exec(compile(source, "slow_call.py", "exec"), namespace)   # a fixture of this repository
    return namespace


def test_the_child_process_backend_does_not_enforce_the_call_time_limits(
        state, config, setup, scratch):
    # One call of each instrument sleeps longer than call_max_ms; the stage passes
    # within the job's wall-clock limit. Asserts the stage, never a time (I-12).
    assert not getattr(ProcessSandbox(scratch), sequence.CALL_LIMITS_FLAG, False)
    out = sequence.dry_run_and_grid(context(state, config, setup, ProcessSandbox(scratch)),
                                    from_file(STRATEGIES / "slow_call.py"))
    assert out.ok and out.stage is None, out.text


def test_the_in_process_backend_does_not_enforce_the_call_time_limits(
        state, config, setup, slow_function):
    assert not getattr(InProcessSandbox(), sequence.CALL_LIMITS_FLAG, False)
    sub = Submission(params=slow_function["PARAMS"], function=slow_function["position"])
    out = sequence.dry_run_and_grid(context(state, config, setup, InProcessSandbox()), sub)
    assert out.ok, out.text


class TimedSandbox:
    """A fake backend whose result carries the call times it is given: every call
    ``base`` ms, and the calls ``slow`` of the first instrument ``slow_ms``."""

    def __init__(self, enforces: bool, base: float, slow: int = 0, slow_ms: float = 0.0):
        self.enforces_call_limits = enforces
        self.base, self.slow, self.slow_ms = base, slow, slow_ms

    def run(self, job):
        result = InProcessSandbox().run(job)
        call_ms = {}
        for k, (key, times) in enumerate(sorted(result.call_ms.items())):
            fake = np.full(len(times), self.base)
            if k == 0:
                fake[:self.slow] = self.slow_ms
            call_ms[key] = fake
        return dataclasses.replace(result, call_ms=call_ms)


def flat_submission() -> Submission:
    return Submission(params={"tag": 1}, function=lambda bars, params: 0.0)


@pytest.mark.parametrize(("base", "slow", "slow_ms", "rule"), [
    (51.0, 0, 0.0, "call_p95"),       # every call above call_p95_ms = 50
    (1.0, 1, 501.0, "call_max"),      # one call above call_max_ms = 500, p95 at 1
])
def test_a_backend_that_enforces_the_call_time_limits_fails_a_slow_run(
        state, config, setup, base, slow, slow_ms, rule):
    enforcing = TimedSandbox(True, base, slow, slow_ms)
    out = sequence.dry_run_and_grid(context(state, config, setup, enforcing), flat_submission())
    assert (out.stage, out.rule) == ("dry_run", rule)
    assert out.text.startswith(f"dry_run [{rule}]: ")
    ERROR_TEXTS.append(out.text)
    lax = TimedSandbox(False, base, slow, slow_ms)
    assert sequence.dry_run_and_grid(context(state, config, setup, lax), flat_submission()).ok


def test_at_the_limits_a_run_passes(state, config, setup):
    # p95 exactly call_p95_ms and the slowest call exactly call_max_ms: not above.
    at = TimedSandbox(True, 50.0, 1, 500.0)
    assert sequence.dry_run_and_grid(context(state, config, setup, at), flat_submission()).ok


def test_zz_no_error_text_holds_a_symbol_venue_contract_or_date(state):
    # Runs after the failing tests of this file (pytest keeps file order).
    assert len(ERROR_TEXTS) >= 4
    words = set()
    for root in (REPO_ROOT / "config", FIXTURE_CONFIG):
        for path in sorted((root / "instruments").glob("*.toml")):
            record = tomllib.loads(path.read_text(encoding="utf-8"))
            words |= {record["symbol"], record["venue"]}
            words |= {str(v) for k, v in record.get("source", {}).items()
                      if "contract" in k or k in ("dataset", "symbol")}
    for symbol in SEEDS:
        words |= set(own_bars(state, symbol)["contract"])
    words = {w for w in words if w}
    assert {"SYNA", "SYNA-2019-06", "MES"} <= words
    for text in ERROR_TEXTS:
        for word in words:
            assert word not in text, (word, text)
        assert not re.search(r"\d{4}-\d{2}|\d{1,2}:\d{2}|\d\.\d", text), text


# ------------------------------------------------------------- the register, O-4's one subtraction


def test_the_grid_s_function_is_registered_adjusted_and_adjusted_rows_producer():
    with open(REGISTER, "rb") as f:
        entries = tomllib.load(f)["reader"]
    classes = {(e["module"], e["function"]): e["class"] for e in entries}
    assert classes[("discotrade.validation.sequence", "fix_combination")] == "adjusted"
    assert classes[("discotrade.paper", "adjusted_rows")] == "producer"
    tree = ast.parse((REPO_ROOT / "src" / "discotrade" / "validation" / "sequence.py")
                     .read_text(encoding="utf-8"))
    fix = next(n for n in tree.body
               if isinstance(n, ast.FunctionDef) and n.name == "fix_combination")
    assert any(isinstance(n, ast.Attribute) and n.attr == "adjusted_rows"
               for n in ast.walk(fix))


def test_adjusted_and_adjusted_rows_subtract_through_one_private_function():
    # Decision 97 (c): O-4 has one implementation of the subtraction.
    tree = ast.parse((REPO_ROOT / "src" / "discotrade" / "paper.py").read_text(encoding="utf-8"))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for name in ("adjusted", "adjusted_rows"):
        body = list(ast.walk(functions[name]))
        assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "_less_exposure" for n in body), name
        # The only subtraction each holds is a set difference (``x - set(...)``).
        assert all(isinstance(n.right, ast.Call) and isinstance(n.right.func, ast.Name)
                   and n.right.func.id == "set"
                   for n in body if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub)), name
    assert any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub)
               for n in ast.walk(functions["_less_exposure"]))


def test_the_harness_reads_params_and_grid_without_running_the_text():
    # I-7: the literals are read with ast; a text that would raise on loading
    # still gives them.
    source = 'PARAMS = {"a": 1}\nGRID = {"a": [1, 2]}\nraise SystemExit\n'
    sub = Submission.from_source(source)
    assert (sub.params, sub.grid) == ({"a": 1}, {"a": [1, 2]})
