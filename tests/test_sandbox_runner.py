"""The sandbox runner and the in-process backend (DESIGN 12.4, 6.2, 7.1, 5.6;
decision 95 (b) to (f); decisions 2026-10-12 22, 23, 24, 44; finding D-006; I-2, I-7).

The runner is exercised in-process: its ``main`` is called on a job directory
the test writes with ``write_job``, and its standard output (one JSON
document) is read back with ``capsys``. The stores are filled by ``bars
fetch`` on the fixture track ``test_mixed`` (SYNA rolls on 2019-06-14, SYNL
cannot be shorted, SYNX is always open), run in-process
(``discotrade.cli.main``) with the clock given by ``--as-of``, under a pytest
temporary directory. The window is short (seven trading dates around SYNA's
June roll) so that each comparison stays quick; its context is the full
history cap.

Seeds: the synthetic bars come from the fixture records' seeds, written here
in ``SEEDS`` and checked against them; the reverse sample is drawn with
``numpy.random.default_rng(SAMPLE_SEED)``.
"""

import ast
import json
import math
import re
import shutil
import sys
import tomllib
from datetime import date

import numpy as np
import pandas as pd
import pytest

from discotrade.backtest import evaluate
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange, load_calendar, load_thresholds, load_track_config
from discotrade.sandbox import runner
from discotrade.sandbox.base import (
    SandboxJob,
    SandboxLimits,
    SandboxRefused,
    build_job,
    result_from_doc,
    write_job,
)
from discotrade.sandbox.inprocess import InProcessSandbox
from discotrade.strategy import ResultError, Strategy, check_result, load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
CHEAT = STRATEGIES / "cheat_lookahead.py"
RUNNER = REPO_ROOT / "src" / "discotrade" / "sandbox" / "runner.py"
TRACK = "test_mixed"
HOUR = 3600
#: The seed of each instrument's synthetic source, as its fixture record gives it.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
AS_OF = "2019-06-21T00:00:00+00:00"
#: Seven trading dates; SYNA rolls inside (2019-06-14).
WINDOW = DateRange(date(2019, 6, 11), date(2019, 6, 18))
SYNA_ROLL = pd.Timestamp("2019-06-14 00:00", tz="UTC")
SAMPLE_SEED = 20191014
LIMITS = SandboxLimits(wall_seconds=60.0, memory_bytes=1 << 30, output_bytes=1 << 22)
#: Each reference strategy with a second parameter set taken from its GRID.
REFERENCES = {
    "trend_ma.py": {"fast": 12, "slow": 192},
    "zscore_reversal.py": {"lookback": 24, "entry": 1.0},
    "hour_of_day.py": {"start_hour": 8, "end_hour": 20},
}
#: Every error text a test of this file produced, checked at the end (decision 95 (e)).
ERROR_TEXTS: list[str] = []


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


@pytest.fixture(scope="module")
def state(tmp_path_factory, config):
    path = tmp_path_factory.mktemp("state")
    assert main(["--state", str(path), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    return path


def job_for(state, tc, calendars, *, source=None, function=None, param_sets, window=WINDOW,
            mode="positions", samples=None, instruments=None):
    return build_job(state, tc.track, instruments or tc.instruments, calendars, window,
                     source=source, function=function, param_sets=param_sets,
                     limits=LIMITS, mode=mode, samples=samples)


def run_runner(job: SandboxJob, directory, capsys):
    """Write ``job`` under ``directory``, call the runner's ``main`` on it, and
    return its result read back from standard output."""
    path = write_job(job, directory)
    capsys.readouterr()
    assert runner.main([str(path)]) == 0
    out = capsys.readouterr().out
    return result_from_doc(job, json.loads(out))


def alone(state, tc, calendars, symbol, strat, params):
    """The targets of ``strat`` on ``symbol`` evaluated alone by ``backtest.evaluate``."""
    inst = next(i for i in tc.instruments if i.symbol == symbol)
    ev = evaluate(state, tc.track, inst, calendars[inst.calendar], strat, WINDOW,
                  params=params)
    return ev.rows["p"].to_numpy(dtype=np.float64)


def same(a, b) -> bool:
    """Equal exactly, bit for bit (so -0.0 and 0.0 differ)."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return a.shape == b.shape and a.tobytes() == b.tobytes()


def test_the_synthetic_seeds_are_the_ones_written_here(tc):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS


def test_the_window_holds_a_syna_roll(state, tc, calendars):
    job = job_for(state, tc, calendars, source="", param_sets=[{}])
    syna = job.instruments[0]
    inside = syna.bars.iloc[syna.first + 1:]
    assert SYNA_ROLL in set(inside["ts"][inside["rolled"]])


# ------------------------------------------------------------ the imports


def test_the_runner_imports_only_the_standard_library_numpy_pandas_and_indicators():
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, ast.dump(node)
            if node.module == "discotrade":
                names = [f"discotrade.{alias.name}" for alias in node.names]
            else:
                names = [node.module]
        else:
            continue
        for name in names:
            seen.add(name)
            top = name.split(".")[0]
            assert (name == "discotrade.indicators" or top in ("numpy", "pandas")
                    or top in sys.stdlib_module_names), name
    assert "discotrade.indicators" in seen
    # Nothing reaches the import machinery by another route.
    text = RUNNER.read_text(encoding="utf-8")
    assert "importlib" not in text


# ----------------------------------------------- targets equal backtest's


@pytest.mark.parametrize("name", sorted(REFERENCES))
def test_the_runners_targets_equal_backtest_evaluate_for_two_parameter_sets(
        name, state, tc, calendars, thresholds, tmp_path, capsys):
    path = REPO_ROOT / "reference" / name
    strat = load_strategy_file(path, thresholds)
    param_sets = [strat.params, REFERENCES[name]]
    assert set(REFERENCES[name]) == set(strat.params)
    job = job_for(state, tc, calendars, source=path.read_text(encoding="utf-8"),
                  param_sets=param_sets)
    result = run_runner(job, tmp_path / "job", capsys)
    assert result.error is None
    for p, params in enumerate(param_sets):
        for symbol in tc.track.instruments:
            want = alone(state, tc, calendars, symbol, strat, params)
            got = result.targets[(p, symbol)]
            assert len(want) > 50, symbol
            assert same(got, want), (name, p, symbol)
            assert np.array_equal(result.bars[(p, symbol)], np.arange(len(want)))
            assert len(result.call_ms[(p, symbol)]) == len(want)
    # The two parameter sets give different targets somewhere.
    assert any(not same(result.targets[(0, s)], result.targets[(1, s)])
               for s in tc.track.instruments), name


# ------------------------------------------------------ the result check


def _table():
    return [1, 0, -1, 0.5, -0.0, 1.0, -1.0, 1.0000001, -1.0000001, float("nan"),
            float("inf"), float("-inf"), True, False, "0.5", None, np.float64(0.25),
            np.float64(-0.25), np.float32(0.5), np.int64(1), -0.5, -1, [0.5], 2]


@pytest.mark.parametrize("shorting", [True, False])
@pytest.mark.parametrize("value", _table(), ids=repr)
def test_the_runners_result_check_agrees_with_strategy_check_result(value, shorting):
    try:
        want = check_result(value, instrument="X", ts=0, shorting=shorting)
    except ResultError as exc:
        message = str(exc)
        rule = ("not_a_number" if "not a real number" in message
                else "not_finite" if "not finite" in message
                else "out_of_range" if "outside" in message else "?")
        with pytest.raises(runner.BadResult) as err:
            runner.check(value, shorting)
        assert err.value.rule == rule
        return
    got = runner.check(value, shorting)
    assert type(got) is float
    assert same([got], [want]) and math.copysign(1, got) == math.copysign(1, want)


def test_a_negative_result_is_clipped_where_shorting_is_not_allowed():
    assert runner.check(-0.5, False) == 0.0
    assert runner.check(-0.5, True) == -0.5


# ------------------------------------------------------ errors and stages


def _one_instrument_job(state, tc, calendars, source):
    syna = [i for i in tc.instruments if i.symbol == "SYNA"]
    return job_for(state, tc, calendars, source=source, param_sets=[{"a": 1}],
                   instruments=syna)


RAISES_ON_LOAD = "PARAMS = {'a': 1}\nx = 1 / 0\n\ndef position(bars, params):\n    return 0.0\n"
NOT_CALLABLE = "PARAMS = {'a': 1}\nposition = 0.5\n"
RAISES_AT_BAR_3 = (
    "PARAMS = {'a': 1}\nCALLS = []\n\ndef position(bars, params):\n"
    "    CALLS.append(1)\n    if len(CALLS) == 4:\n"
    "        raise ValueError(str(bars['close'].iloc[-1]) + ' SYNA 2019-06-12')\n"
    "    return 0.0\n")
RETURNS_TWO = "PARAMS = {'a': 1}\n\ndef position(bars, params):\n    return 2.0\n"
RETURNS_NAN = "PARAMS = {'a': 1}\n\ndef position(bars, params):\n    return float('nan')\n"
RETURNS_TEXT = "PARAMS = {'a': 1}\n\ndef position(bars, params):\n    return 'long'\n"


@pytest.mark.parametrize("source, stage, rule, bar", [
    (RAISES_ON_LOAD, "load", "raised", None),
    (NOT_CALLABLE, "load", "no_position", None),
    ((STRATEGIES / "no_position.py").read_text(encoding="utf-8"), "load", "no_position",
     None),
    ("def position(bars, params:\n", "load", "raised", None),
    (RAISES_AT_BAR_3, "dry_run", "raised", 3),
    (RETURNS_TWO, "dry_run", "out_of_range", 0),
    (RETURNS_NAN, "dry_run", "not_finite", 0),
    (RETURNS_TEXT, "dry_run", "not_a_number", 0),
], ids=["load-raises", "position-not-callable", "no-position-fixture", "syntax",
        "call-raises", "returns-2.0", "returns-nan", "returns-text"])
def test_a_bad_text_gives_its_stage_and_an_error_text(source, stage, rule, bar, state, tc,
                                                     calendars, tmp_path, capsys):
    job = _one_instrument_job(state, tc, calendars, source)
    result = run_runner(job, tmp_path / "job", capsys)
    err = result.error
    assert err is not None and not result.targets
    assert (err.stage, err.rule, err.bar) == (stage, rule, bar)
    assert err.text.startswith(f"{stage} [{rule}]: ")
    if bar is not None:
        assert f"window bar {bar}" in err.text
    ERROR_TEXTS.append(err.text)


def test_an_error_stops_the_run_at_the_first_bad_result(state, tc, calendars, tmp_path,
                                                        capsys):
    job = job_for(state, tc, calendars, source=RETURNS_TWO, param_sets=[{"a": 1}, {"a": 2}])
    result = run_runner(job, tmp_path / "job", capsys)
    assert result.error.param_set == 0 and result.error.bar == 0
    ERROR_TEXTS.append(result.error.text)


def _forbidden_words(state):
    """Every symbol, venue and contract in config/ and tests/fixtures/config/, and
    every contract in the test's store."""
    words = set()
    for root in (REPO_ROOT / "config", FIXTURE_CONFIG):
        for path in sorted((root / "instruments").glob("*.toml")):
            record = tomllib.loads(path.read_text(encoding="utf-8"))
            words |= {record["symbol"], record["venue"]}
            words |= {str(v) for k, v in record.get("source", {}).items()
                      if "contract" in k or k in ("dataset", "symbol")}
    store = BarStore(state, TRACK, HOUR)
    for symbol in SEEDS:
        bars = store.read_range(symbol, pd.Timestamp("2019-01-01", tz="UTC"),
                                pd.Timestamp("2019-07-01", tz="UTC"))
        words |= set(bars["contract"])
    return {w for w in words if w}


def test_zz_no_error_text_holds_a_symbol_venue_contract_date_or_price(state):
    # Runs after the error tests of this file (pytest keeps file order).
    assert len(ERROR_TEXTS) >= 9
    words = _forbidden_words(state)
    assert {"SYNA", "SYNTH", "SYNA-2019-06", "MES", "CME"} <= words
    for text in ERROR_TEXTS:
        for word in words:
            assert word not in text, (word, text)
        assert not re.search(r"\d{4}-\d{2}|\d{1,2}:\d{2}|\d\.\d", text), text


# ------------------------------------------------- D-006, a fresh load


def test_the_cheating_text_through_the_runner_gives_each_instrument_its_targets_alone(
        state, tc, calendars, thresholds, tmp_path, capsys):
    """D-006 (decision 44): the cheating text keeps every frame at module level;
    through the runner, each instrument's targets under each parameter set equal
    those of the text loaded afresh and evaluated on that instrument alone."""
    param_sets = [{"lookback": 24, "tail": 6}, {"lookback": 12, "tail": 4}]
    job = job_for(state, tc, calendars, source=CHEAT.read_text(encoding="utf-8"),
                  param_sets=param_sets)
    result = run_runner(job, tmp_path / "job", capsys)
    assert result.error is None
    for p, params in enumerate(param_sets):
        for symbol in tc.track.instruments:
            want = alone(state, tc, calendars, symbol, load_strategy_file(CHEAT, thresholds),
                         params)
            assert np.unique(want).size > 10, symbol
            assert same(result.targets[(p, symbol)], want), (p, symbol)


# ----------------------------------------------------- reverse sample


def test_reverse_sample_gives_for_its_bars_the_targets_of_positions(
        state, tc, calendars, tmp_path, capsys):
    path = REPO_ROOT / "reference" / "trend_ma.py"
    source = path.read_text(encoding="utf-8")
    param_sets = [{"fast": 24, "slow": 96}, REFERENCES["trend_ma.py"]]
    forward = run_runner(job_for(state, tc, calendars, source=source,
                                 param_sets=param_sets), tmp_path / "fwd", capsys)
    rng = np.random.default_rng(SAMPLE_SEED)
    samples = {}
    for inst in forward_job_instruments(state, tc, calendars):
        n = len(inst.bars) - inst.first
        samples[inst.symbol] = tuple(int(i) for i in rng.choice(n, size=12, replace=False))
    job = job_for(state, tc, calendars, source=source, param_sets=param_sets,
                  mode="reverse_sample", samples=samples)
    back = run_runner(job, tmp_path / "rev", capsys)
    assert back.error is None
    seen = set()
    for p in range(len(param_sets)):
        for symbol in tc.track.instruments:
            bars = back.bars[(p, symbol)]
            assert list(bars) == sorted(samples[symbol], reverse=True)
            assert same(back.targets[(p, symbol)], forward.targets[(p, symbol)][bars])
            seen |= set(back.targets[(p, symbol)])
    assert len(seen) > 1


def forward_job_instruments(state, tc, calendars):
    return job_for(state, tc, calendars, source="", param_sets=[{}]).instruments


def test_a_sample_outside_the_window_is_refused(state, tc, calendars):
    with pytest.raises(ValueError, match="sample"):
        job_for(state, tc, calendars, source="", param_sets=[{}], mode="reverse_sample",
                samples={"SYNA": (10_000,), "SYNL": (0,), "SYNX": (0,)})
    with pytest.raises(ValueError, match="mode"):
        job_for(state, tc, calendars, source="", param_sets=[{}], mode="reverse sample")


# ---------------------------------------------------- the in-process backend


def level_probe(bars, params):
    """Reads the absolute price level of the last close, adjusted as of it: a slice
    adjusted as of a later bar gives another value."""
    return float((bars["close"].iloc[-1] % params["m"]) / params["m"] * 2.0 - 1.0)


def test_the_in_process_backend_runs_a_function_object(state, tc, calendars, thresholds):
    trend = load_strategy_file(REPO_ROOT / "reference" / "trend_ma.py", thresholds)
    for fn, param_sets in ((level_probe, [{"m": 10.0}, {"m": 7.0}]),
                           (trend.position, [trend.params, REFERENCES["trend_ma.py"]])):
        job = job_for(state, tc, calendars, function=fn, param_sets=param_sets)
        result = InProcessSandbox().run(job)
        assert result.error is None
        strat = Strategy(name="fn", source="", params=param_sets[0], grid=None, position=fn)
        for p, params in enumerate(param_sets):
            for symbol in tc.track.instruments:
                want = alone(state, tc, calendars, symbol, strat, params)
                assert same(result.targets[(p, symbol)], want), (fn.__name__, p, symbol)


def test_the_in_process_backend_reports_a_bad_result_with_its_stage(state, tc, calendars):
    job = job_for(state, tc, calendars, function=lambda bars, params: 2.0,
                  param_sets=[{}])
    result = InProcessSandbox().run(job)
    assert (result.error.stage, result.error.rule, result.error.bar) == (
        "dry_run", "out_of_range", 0)
    ERROR_TEXTS.append(result.error.text)


def test_the_in_process_backend_refuses_source_text(state, tc, calendars):
    job = job_for(state, tc, calendars, source=RETURNS_TWO, param_sets=[{"a": 1}])
    with pytest.raises(SandboxRefused, match="source") as err:
        InProcessSandbox().run(job)
    assert err.value.rule == "source"


# ------------------------------------------------------------- the program


def test_the_runner_without_a_job_directory_is_a_usage_error(capsys, tmp_path):
    assert runner.main([]) == 2
    assert runner.main([str(tmp_path / "missing")]) == 1
    assert capsys.readouterr().out == ""


def test_what_the_text_prints_does_not_reach_the_result(state, tc, calendars, tmp_path,
                                                        capsys):
    source = ("PARAMS = {'a': 1}\n\ndef position(bars, params):\n"
              "    print('{\"ok\": false}')\n    return 0.0\n")
    job = _one_instrument_job(state, tc, calendars, source)
    result = run_runner(job, tmp_path / "job", capsys)
    assert result.error is None
