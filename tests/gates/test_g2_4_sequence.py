"""Gate item G2.4: the validation sequence on valid fixtures: the grid fixes the best
combination on W, determinism and activity pass, and each of the five stages fails
on the fixture built to fail it, with an error text (DESIGN 18.3 G2.4, 12.2, 12.3;
decision 106 (a), (e) of 2026-10-14-m13; decisions 97, 98, 101 (f); owner's O-4,
O-17).

As decision 106 (e) reads it, on the container backend, on ``test_synth``'s own W
of ``DAY`` (2019-06-11 to 2019-07-08, which holds SYNA's roll of 2019-06-14), at
the production thresholds and the limits of ``tests/fixtures/config/run.toml``:

- the grid of ``grid_lean.py`` fixes the combination with the greatest
  exposure-adjusted Sharpe at 1x on W (O-17), the figures computed here from the
  evaluation rows and the stored bars, as ``tests/test_validation_grid.py``
  does; on this window the plain Sharpe would fix another combination, so the
  item tells the two apart;
- ``changes_30.py``, a valid fixture, passes determinism and activity (and every
  other stage), with the approach of ``reference/trend_ma.py`` in the state;
- each of the five stages fails on the fixture built to fail it and the
  sequence stops there (no later job runs), with an error text that passes
  decision 101 (f)'s check: ``six_params.py`` (static), ``grid_out_of_range.py``
  (dry run), ``keeps_state.py`` (determinism), ``changes_29.py`` (activity),
  ``trend_ma_flipped.py`` (correlation).

The test's own computation (``own_*``) takes the evaluation rows from
``backtest.evaluate`` of the fixture's text loaded by ``strategy``, the stored
bars from the month Parquet files and the roll records with ``pyarrow``,
``pandas`` and ``json``, and calls none of ``paper.adjusted``,
``paper.adjusted_rows``, ``paper.unit_bars``, ``paper.unit_returns``,
``paper.average_positions``, ``paper.window_units`` or ``paper.window_positions``:
the unit return of a bar is ``(O(u) - (C(u-1) + gap) + C(u) - O(u)) / O(u)`` with
``u-1`` the previous stored bar and ``gap`` the recorded gap of a roll at ``u``;
``hbar_i(W)`` the mean of the rows' ``h``; the adjusted daily figure the plain
one less the mean over the basket of ``hbar_i * R_i(D)``; equality is decision
39's.

Seeds: the synthetic bars come from the fixture records' seeds, written here
(``SEEDS``) and checked. No random draw is made here except the reverse
sample's, whose seed is the text's own (decision 98 (a)). Time is read only
through ``--as-of`` and the ``FixedClock`` of the commits.
"""

import json
import math
from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
from error_texts import assert_clean, forbidden_words
from m2_harness import STRATEGIES, Backends, bars_state, commit, copy_config

from discotrade import backtest, journal, state
from discotrade.cli import REPO_ROOT
from discotrade.clock import FixedClock
from discotrade.strategy import load_strategy_file
from discotrade.validation import sequence
from discotrade.validation.sequence import Context, Submission

pytestmark = [pytest.mark.gate, pytest.mark.gate_m2, pytest.mark.container]

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
#: The day D (a Monday): W is 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
AS_OF = "2019-07-25T00:00:00+00:00"
COMMIT_CLOCK = FixedClock(datetime(2019, 7, 25, tzinfo=UTC))
ADMITTED = date(2019, 7, 1)
TREND_MA = REPO_ROOT / "reference" / "trend_ma.py"
DUPLICATED = {"fast": 6, "slow": 48}
LEAN = STRATEGIES / "grid_lean.py"
LEAN_COMBOS = [{"bias": b, "spare": s, "lookback": 192} for b in (0.5, -0.5) for s in (1, 2)]
VALID = STRATEGIES / "changes_30.py"
#: Each stage, its fixture built to fail it, the rule, and the jobs the sequence ran
#: before stopping there.
FAILING = {
    "static": ("six_params.py", "max_params", []),
    "dry_run": ("grid_out_of_range.py", "out_of_range", ["positions"]),
    "determinism": ("keeps_state.py", "reverse_sample",
                    ["positions", "positions", "reverse_sample"]),
    "activity": ("changes_29.py", "min_changes_w", ["positions", "positions", "reverse_sample"]),
    "correlation": ("trend_ma_flipped.py", "duplicate",
                    ["positions", "positions", "reverse_sample", "positions"]),
}


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers (None for not a number)."""
    a = math.nan if a is None else float(a)
    b = math.nan if b is None else float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory.mktemp("cfg"))


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def live_state(tmp_path_factory, config, setup):
    """The track's bars and one live approach admitted from reference/trend_ma.py."""
    path = bars_state(tmp_path_factory.mktemp("live") / "state", config, TRACK, AS_OF, DAY,
                      COMMIT_CLOCK)
    aid = state.write_approach(
        path, source=TREND_MA.read_text(encoding="utf-8"), params=DUPLICATED,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description="a reference strategy", profile_version="w-test",
        admitted=ADMITTED, instruments=setup.instruments, spread_tables=setup.spread_tables)
    assert commit(path, TRACK, DAY, COMMIT_CLOCK) is not None
    return path, aid


@pytest.fixture(scope="module")
def backends(tmp_path_factory):
    made = Backends(tmp_path_factory.mktemp("jobs"))
    yield made
    left = made.remove_left()
    assert left == [], f"containers left behind: {left}"


@pytest.fixture(scope="module")
def words(live_state):
    path, _ = live_state
    found = forbidden_words(path, TRACK, SEEDS)
    assert {"SYNA", "SYNA-2019-06", "MES"} <= found
    return found


def test_the_facts_written_here(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    w = setup.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)
    assert setup.thresholds["validation.min_changes_w"] == 30
    assert setup.thresholds["validation.corr_max"] == 0.7
    assert setup.thresholds["validation.call_p95_ms"] == 50
    assert setup.thresholds["validation.call_max_ms"] == 500
    assert Submission.from_source(LEAN.read_text(encoding="utf-8")).combinations() == LEAN_COMBOS


# ------------------------------------------------------------- the test's own computation


def own_bars(state_dir, symbol) -> pd.DataFrame:
    files = sorted((state_dir / "bars" / TRACK / symbol).glob("*.parquet"))
    bars = pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True)
    return bars.sort_values("ts").reset_index(drop=True)


def own_gaps(state_dir, symbol) -> dict:
    path = state_dir / "rolls" / TRACK / f"{symbol}.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[(pd.Timestamp(r["ts"]), r["old"], r["new"])] = float(r["gap"])
    return out


def own_unit(state_dir, symbol) -> dict:
    """Per bar ts: the unit return of one long unit held over the bar."""
    bars, gaps = own_bars(state_dir, symbol), own_gaps(state_dir, symbol)
    unit = {}
    for k in range(len(bars)):
        ts = bars["ts"][k]
        o, c = float(bars["open"][k]), float(bars["close"][k])
        if k == 0:
            unit[ts] = (c - o) / o
            continue
        old, new = bars["contract"][k - 1], bars["contract"][k]
        gap = gaps[(ts, old, new)] if old != new else 0.0
        prev = float(bars["close"][k - 1]) + gap
        unit[ts] = ((o - prev) + (c - o)) / o
    return unit


def own_sharpe(d) -> float:
    x = [float(v) for v in d]
    if len(x) < 2:
        return math.nan
    sd = float(np.std(x, ddof=1))
    if all(v == x[0] for v in x) or not sd > 1e-12 * max(abs(v) for v in x):
        return math.nan
    return float(np.mean(x)) / sd * math.sqrt(252)


def own_sharpes(state_dir, setup, params, units) -> tuple[float, float]:
    """The plain and the exposure-adjusted Sharpe at 1x of ``params`` on W, by hand."""
    strategy = load_strategy_file(LEAN, setup.thresholds)
    w = setup.track.windows(DAY).w
    rows = [backtest.evaluate(state_dir, setup.track, inst, setup.calendars[inst.calendar],
                              strategy, w, params, setup.spread_tables.get(inst.symbol)).rows
            for inst in setup.instruments]
    symbols = [i.symbol for i in setup.instruments]
    hbar = {s: float(r["h"].mean()) if len(r) else 0.0 for s, r in zip(symbols, rows, strict=True)}
    days = sorted({d for r in rows for d in r["date"]})
    plain = {d: sum(float(r["net_1x"][r["date"] == d].sum()) for r in rows) / len(rows)
             for d in days}
    adjusted = []
    for d in days:
        exposure = sum(hbar[s] * sum(units[s][ts] for ts, dd in zip(r["ts"], r["date"],
                                                                     strict=True) if dd == d)
                       for s, r in zip(symbols, rows, strict=True)) / len(rows)
        adjusted.append(plain[d] - exposure)
    return own_sharpe(list(plain.values())), own_sharpe(adjusted)


def first_best(values) -> int:
    best = None
    for k, v in enumerate(values):
        if not math.isnan(v) and (best is None or v > values[best]):
            best = k
    return 0 if best is None else best


# ------------------------------------------------------------- the grid fixes the best


@pytest.fixture(scope="module")
def lean(live_state, config, setup, backends):
    path, _ = live_state
    b = backends.make(config)
    out = sequence.dry_run_and_grid(Context(path, config, setup, DAY, b),
                                    Submission.from_source(LEAN.read_text(encoding="utf-8")))
    return out, b


def test_the_grid_fixes_the_combination_with_the_greatest_adjusted_sharpe_on_w(
        lean, live_state, setup):
    path, _ = live_state
    units = {i.symbol: own_unit(path, i.symbol) for i in setup.instruments}
    own = [own_sharpes(path, setup, c, units) for c in LEAN_COMBOS]
    plain, adjusted = [p for p, _ in own], [a for _, a in own]
    best = first_best(adjusted)
    # The window tells the two measures apart: the plain Sharpe would fix another.
    assert first_best(plain) != best, (plain, adjusted)
    out, b = lean
    assert out.ok, out.text
    assert b.modes == ["positions"] and b.started  # one job, in a container
    assert out.params == LEAN_COMBOS[best]
    assert out.grid["fixed"] == LEAN_COMBOS[best]
    assert [r["params"] for r in out.grid["results"]] == LEAN_COMBOS
    for entry, (p, a) in zip(out.grid["results"], own, strict=True):
        assert eq(entry["plain"]["sharpe"], p)
        assert eq(entry["adjusted"]["sharpe"], a)


# ------------------------------------------------------------- a valid fixture passes


def test_a_valid_fixture_passes_determinism_and_activity_and_every_stage(
        live_state, config, setup, backends):
    path, _ = live_state
    b = backends.make(config)
    out = sequence.validate(Context(path, config, setup, DAY, b),
                            VALID.read_text(encoding="utf-8"))
    assert out.ok and out.stage is None, out.text
    # Stage 2's job, determinism's second run and reverse sample, the correlation gate's.
    assert b.modes == ["positions", "positions", "reverse_sample", "positions"]
    assert sequence.changes(out.evaluations) >= setup.thresholds["validation.min_changes_w"]


# ------------------------------------------------------------- each stage fails and stops there


@pytest.mark.parametrize("stage", list(FAILING))
def test_each_stage_fails_on_its_fixture_and_stops_there_with_an_error_text(
        stage, live_state, config, setup, backends, words):
    name, rule, jobs = FAILING[stage]
    path, aid = live_state
    b = backends.make(config)
    out = sequence.validate(Context(path, config, setup, DAY, b),
                            (STRATEGIES / name).read_text(encoding="utf-8"))
    assert not out.ok
    assert (out.stage, out.rule) == (stage, rule), out.text
    assert out.text.startswith(f"{stage} [{rule}]: "), out.text
    assert b.modes == jobs
    assert bool(b.started) == bool(jobs)
    if stage == "correlation":
        assert out.text.endswith(f"with approach {aid}")
    assert_clean([out.text], words)


def test_no_container_of_the_item_remains(backends):
    assert backends.started
    assert backends.left() == []
