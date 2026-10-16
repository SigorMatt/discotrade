"""The model pool (DESIGN 13.6, 11.3, 15.2; R-14, R-21; decision 2026-10-16-m15 124).

Every test reads the pool from ``config/models.toml`` (or its fixture copy), the
two thresholds ``pool.fail_window`` and ``pool.fail_rate`` from
``config/thresholds.toml`` at their production values (a copy under the
temporary directory with another value is said so where used), and builds the
failure windows from a ``calls.jsonl`` the test writes under its temporary
state directory with ``ledger.append_calls`` and reads back with
``ledger.read``. Trading days are those of the fixture track ``test_synth``
(epoch 2019-06-03, a Monday; calendar ``synth_week``, Monday to Friday, whose
one closure is 2019-07-04), all in June 2019. No clock, no network, no provider.
"""

from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest

from discotrade import ledger
from discotrade.cli import REPO_ROOT
from discotrade.config import load_calendar, load_models, load_thresholds, load_track_config
from discotrade.daily import is_trading_day
from discotrade.workers import pool as pl

CONFIG = REPO_ROOT / "config"
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
EPOCH = date(2019, 6, 3)
MODELS = load_models(CONFIG / "models.toml")
THRESHOLDS = load_thresholds(CONFIG / "thresholds.toml")
GPT, MINIMAX, NEMOTRON, LIGHTNING = (m.id for m in MODELS.models)
ALL_LISTED = [m.id for m in MODELS.models]


def test_production_thresholds_as_read():
    # SPEC 7: "above 50% over 20 calls"; read from config/thresholds.toml.
    assert THRESHOLDS["pool.fail_window"] == 20
    assert THRESHOLDS["pool.fail_rate"] == 0.5


def test_the_fixture_pool_is_the_configs():
    assert load_models(FIXTURE_CONFIG / "models.toml") == MODELS
    assert [m.id for m in MODELS.pool] == [GPT, MINIMAX, NEMOTRON]


# --- trading days of test_synth -------------------------------------------------------


def trading_days(n: int) -> list[date]:
    """The first ``n`` weekdays from the epoch: test_synth's trading days in June 2019,
    by the test's own reading of synth_week (Monday to Friday, no closure in June)."""
    days, d = [], EPOCH
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    assert days[-1] < date(2019, 7, 1)
    return days


DAYS = trading_days(20)


@pytest.fixture(scope="module")
def is_trading():
    tc = load_track_config(FIXTURE_CONFIG, TRACK)
    calendars = {i.calendar: load_calendar(FIXTURE_CONFIG / "calendars" / f"{i.calendar}.toml")
                 for i in tc.instruments}
    assert tc.track.epoch == EPOCH
    return lambda d: is_trading_day(tc, calendars, d)


def test_trading_ordinal_counts_trading_days_from_the_epoch(is_trading):
    for k, d in enumerate(DAYS):
        assert pl.trading_ordinal(d, EPOCH, is_trading) == k
    # A Saturday's ordinal is the count of the five weekdays before it.
    assert pl.trading_ordinal(date(2019, 6, 8), EPOCH, is_trading) == 5


# --- rotation (decision 124 (b)) ------------------------------------------------------


def test_rotation_over_three_models_for_20_trading_days(is_trading):
    tc = load_track_config(FIXTURE_CONFIG, TRACK)
    cells = tc.track.cells
    served: dict[int, set[str]] = {c: set() for c in range(len(cells))}
    for k, d in enumerate(DAYS):
        day = pl.day_pool(MODELS, d, ALL_LISTED, removed=set())
        assert [m.id for m in day.models] == [GPT, MINIMAX, NEMOTRON]
        assert day.events == ()
        ordinal = pl.trading_ordinal(d, EPOCH, is_trading)
        on_day = set()
        for c in range(len(cells)):
            model = pl.model_for(day, ordinal, c)
            assert model is not None
            # The formula of DESIGN 13.6, computed here: pool[(ordinal + c) mod 3].
            assert model.id == [GPT, MINIMAX, NEMOTRON][(k + c) % 3]
            served[c].add(model.id)
            on_day.add(model.id)
        assert on_day == {GPT, MINIMAX, NEMOTRON}  # one day's cells are not all one model
    assert all(len(models) > 1 for models in served.values())  # no cell always one model


# --- the day's pool (decision 124 (a)) ------------------------------------------------


def test_a_missing_model_is_replaced_by_its_fallback():
    listed = [GPT, MINIMAX, LIGHTNING]
    day = pl.day_pool(MODELS, DAYS[0], listed, removed=set())
    assert [m.id for m in day.models] == [GPT, MINIMAX, LIGHTNING]
    assert [(e.level, e.kind, e.subject) for e in day.events] == [
        ("notice", "model_skipped", NEMOTRON)]
    assert day.events[0].detail["fallback"] == LIGHTNING
    assert day.events[0].detail["replaced"] is True


def test_a_missing_model_without_a_fallback_is_skipped_with_the_notice():
    listed = [GPT, NEMOTRON, LIGHTNING]
    day = pl.day_pool(MODELS, DAYS[0], listed, removed=set())
    assert [m.id for m in day.models] == [GPT, NEMOTRON]
    assert [(e.level, e.kind, e.subject) for e in day.events] == [
        ("notice", "model_skipped", MINIMAX)]
    assert day.events[0].detail == {"fallback": None, "replaced": False}


def test_a_missing_model_whose_fallback_is_missing_too_is_skipped():
    day = pl.day_pool(MODELS, DAYS[0], [GPT, MINIMAX], removed=set())
    assert [m.id for m in day.models] == [GPT, MINIMAX]
    assert day.events[0].subject == NEMOTRON
    assert day.events[0].detail == {"fallback": LIGHTNING, "replaced": False}


def test_a_failed_list_read_makes_no_call():
    day = pl.day_pool(MODELS, DAYS[0], None, removed=set())
    assert day.models == ()
    assert [(e.level, e.kind) for e in day.events] == [("notice", "model_list_failed")]
    assert pl.model_for(day, 0, 0) is None


def test_an_empty_pool_makes_no_call():
    day = pl.day_pool(MODELS, DAYS[0], [], removed=set())
    assert day.models == ()
    assert [e.kind for e in day.events] == ["model_skipped"] * 3 + ["pool_empty"]
    assert pl.model_for(day, 0, 0) is None


# --- calls.jsonl, written by the test -------------------------------------------------


class Calls:
    """Rows appended to ``ledger/test_synth/calls.jsonl`` under a temporary state dir."""

    def __init__(self, state: Path) -> None:
        self.state = state
        self.n = 0

    def add(self, day: date, model: str, outcomes: list[str], cell: str = "trend/short"):
        rows = []
        for outcome in outcomes:
            self.n += 1
            call = f"c{self.n:012x}"
            rows.append({
                "call": call, "date": day, "cell": cell, "model": model, "attempt": 1,
                "tokens_in": 100, "tokens_out": 50, "outcome": outcome,
                "response": f"responses/{TRACK}/{day.isoformat()}/{call}.json",
            })
        assert len(ledger.append_calls(self.state, TRACK, rows)) == len(rows)

    def rows(self):
        return ledger.read(self.state, TRACK, ledger.CALLS)


@pytest.fixture
def calls(tmp_path):
    return Calls(tmp_path / "state")


FAIL, OK = "invalid:static", "trial"


def window(fails: int, oks: int) -> list[str]:
    """``fails`` failures and ``oks`` counted successes, interleaved, failures last."""
    return [OK] * oks + [FAIL] * fails


# --- removal (decision 124 (c)) -------------------------------------------------------


def test_a_model_above_the_rate_over_a_full_window_is_removed_for_good(calls):
    fw, fr = THRESHOLDS["pool.fail_window"], THRESHOLDS["pool.fail_rate"]
    fails = int(fw * fr) + 1           # 11 of 20: above the rate
    calls.add(DAYS[0], GPT, window(fails, fw - fails))
    calls.add(DAYS[0], MINIMAX, [OK] * fw)
    rows = calls.rows()
    events = pl.day_events(rows, MODELS, DAYS[0], THRESHOLDS, claude_fallback=False)
    assert [(e.level, e.kind, e.subject) for e in events] == [("alert", "model_removed", GPT)]
    assert events[0].detail == {"calls": fw, "failures": fails, "fail_window": fw,
                                "fail_rate": fr}
    # Not removed on the day itself (a re-run of the day sees the same pool, I-6).
    assert pl.removed_models(rows, MODELS, DAYS[0], THRESHOLDS) == {}
    # Other models' calls on later days; the model is never chosen again.
    for k, d in enumerate(DAYS[1:], start=1):
        calls.add(d, MINIMAX, [OK])
        rows = calls.rows()
        removed = pl.removed_models(rows, MODELS, d, THRESHOLDS)
        assert removed == {GPT: DAYS[0]}
        day = pl.day_pool(MODELS, d, ALL_LISTED, removed=set(removed))
        assert GPT not in [m.id for m in day.models]
        assert day.events == ()      # a removed model is dropped without a notice
        assert all(pl.model_for(day, k, c).id != GPT for c in range(12))
        # The removal is raised once, on the day it happened.
        assert pl.day_events(rows, MODELS, d, THRESHOLDS, claude_fallback=False) == []


def test_at_the_rate_is_not_above_it(calls):
    fw, fr = THRESHOLDS["pool.fail_window"], THRESHOLDS["pool.fail_rate"]
    fails = int(fw * fr)              # 10 of 20: at the rate, not above
    calls.add(DAYS[0], GPT, window(fails, fw - fails))
    rows = calls.rows()
    assert pl.day_events(rows, MODELS, DAYS[0], THRESHOLDS, claude_fallback=False) == []
    assert pl.removed_models(rows, MODELS, DAYS[1], THRESHOLDS) == {}


def test_a_window_not_yet_full_removes_nothing(calls):
    fw = THRESHOLDS["pool.fail_window"]
    calls.add(DAYS[0], GPT, [FAIL] * (fw - 1))
    rows = calls.rows()
    assert pl.day_events(rows, MODELS, DAYS[0], THRESHOLDS, claude_fallback=False) == []
    assert pl.removed_models(rows, MODELS, DAYS[1], THRESHOLDS) == {}
    calls.add(DAYS[1], GPT, [FAIL])        # the 20th counted call fills the window
    rows = calls.rows()
    events = pl.day_events(rows, MODELS, DAYS[1], THRESHOLDS, claude_fallback=False)
    assert [e.subject for e in events if e.kind == "model_removed"] == [GPT]
    assert pl.removed_models(rows, MODELS, DAYS[2], THRESHOLDS) == {GPT: DAYS[1]}


def test_provider_error_and_budget_rows_are_not_counted(calls):
    fw, fr = THRESHOLDS["pool.fail_window"], THRESHOLDS["pool.fail_rate"]
    fails = int(fw * fr)              # 10 of 20 counted: at the rate
    calls.add(DAYS[0], GPT, [OK] * (fw - fails) + [FAIL] * fails
              + ["provider_error"] * 5 + ["budget"] * 2)
    calls.add(DAYS[0], MINIMAX, ["provider_error"] * (2 * fw))
    rows = calls.rows()
    assert pl.day_events(rows, MODELS, DAYS[0], THRESHOLDS, claude_fallback=False) == []
    assert pl.removed_models(rows, MODELS, DAYS[1], THRESHOLDS) == {}


def test_a_duplicate_is_counted_and_is_not_a_failure(calls):
    fw = THRESHOLDS["pool.fail_window"]
    calls.add(DAYS[0], GPT, ["duplicate"] * fw)
    rows = calls.rows()
    assert pl.removed_models(rows, MODELS, DAYS[1], THRESHOLDS) == {}
    # Each invalid stage is a failure.
    calls.add(DAYS[1], MINIMAX, ["invalid:parse", "invalid:dry_run"] * (fw // 2))
    rows = calls.rows()
    assert pl.removed_models(rows, MODELS, DAYS[2], THRESHOLDS) == {MINIMAX: DAYS[1]}


def test_a_removed_fallback_is_not_used(calls):
    fw = THRESHOLDS["pool.fail_window"]
    calls.add(DAYS[0], LIGHTNING, [FAIL] * fw)
    removed = pl.removed_models(calls.rows(), MODELS, DAYS[1], THRESHOLDS)
    assert removed == {LIGHTNING: DAYS[0]}
    day = pl.day_pool(MODELS, DAYS[1], [GPT, MINIMAX, LIGHTNING], removed=set(removed))
    assert [m.id for m in day.models] == [GPT, MINIMAX]
    assert day.events[0].detail == {"fallback": LIGHTNING, "replaced": False}


# --- the thresholds come from config/thresholds.toml ----------------------------------


def copied_thresholds(tmp_path, old, new):
    """config/thresholds.toml copied under the temporary directory with one value changed."""
    path = tmp_path / "thresholds.toml"
    shutil.copy(CONFIG / "thresholds.toml", path)
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))
    return load_thresholds(path)


def test_a_copied_fail_window_changes_the_outcome(calls, tmp_path):
    # A copy with fail_window = 10: ten failures fill it; at 20 they do not.
    calls.add(DAYS[0], GPT, [FAIL] * 10)
    rows = calls.rows()
    assert pl.removed_models(rows, MODELS, DAYS[1], THRESHOLDS) == {}
    short = copied_thresholds(tmp_path, "fail_window = 20", "fail_window = 10")
    assert short["pool.fail_window"] == 10
    assert pl.removed_models(rows, MODELS, DAYS[1], short) == {GPT: DAYS[0]}


def test_a_copied_fail_rate_changes_the_outcome(calls, tmp_path):
    # 11 of 20 is above 0.5 and not above a copy's 0.6.
    calls.add(DAYS[0], GPT, window(11, 9))
    rows = calls.rows()
    assert pl.removed_models(rows, MODELS, DAYS[1], THRESHOLDS) == {GPT: DAYS[0]}
    high = copied_thresholds(tmp_path, "fail_rate = 0.5", "fail_rate = 0.6")
    assert high["pool.fail_rate"] == 0.6
    assert pl.removed_models(rows, MODELS, DAYS[1], high) == {}


# --- the cell window (decision 124 (d); R-21) ------------------------------------------

CELL = "breakout/medium"


def cell_notices(rows, day, flag=False):
    return [e for e in pl.day_events(rows, MODELS, day, THRESHOLDS, claude_fallback=flag)
            if e.kind == "cell_needs_fallback"]


def test_the_cell_rule_with_the_flag_false_logs_the_notice_once(calls):
    from discotrade.config import load_run

    flag = load_run(FIXTURE_CONFIG).workers.claude_fallback
    assert flag is False                        # R-21, read from run.toml
    fw = THRESHOLDS["pool.fail_window"]
    # Three open models, 7 calls each with 4 failures each for the cell: 12 of 21; the
    # window of 20 holds the last 20 calls, 12 failures (11 when the first was one).
    calls.add(DAYS[0], GPT, [OK] * 3 + [FAIL] * 4, cell=CELL)
    calls.add(DAYS[0], MINIMAX, [OK] * 3 + [FAIL] * 4, cell=CELL)
    calls.add(DAYS[0], NEMOTRON, [OK] * 3 + [FAIL] * 4, cell=CELL)
    # Calls by a model that is not an open model of models.toml are not counted.
    calls.add(DAYS[0], "claude-worker", [OK] * fw, cell=CELL)
    notices = cell_notices(calls.rows(), DAYS[0], flag)
    assert [(e.level, e.subject) for e in notices] == [("notice", CELL)]
    assert notices[0].detail["failures"] == 12 and notices[0].detail["calls"] == fw
    # Still above on the next days: no second notice.
    calls.add(DAYS[1], GPT, [FAIL], cell=CELL)
    assert cell_notices(calls.rows(), DAYS[1], flag) == []
    calls.add(DAYS[2], MINIMAX, [OK], cell=CELL)
    assert cell_notices(calls.rows(), DAYS[2], flag) == []
    # At or below the limit over a full window, then above again: logged again.
    calls.add(DAYS[3], NEMOTRON, [OK] * fw, cell=CELL)
    assert cell_notices(calls.rows(), DAYS[3], flag) == []
    calls.add(DAYS[4], GPT, [FAIL] * 11, cell=CELL)
    assert [e.subject for e in cell_notices(calls.rows(), DAYS[4], flag)] == [CELL]
    # With the flag false no cell is served by the Claude worker.
    assert pl.claude_cells(calls.rows(), MODELS, DAYS[5], THRESHOLDS, flag) == frozenset()
    # The model windows are separate: no model reached 20 counted calls above the rate.
    assert pl.removed_models(calls.rows(), MODELS, DAYS[5], THRESHOLDS) == {}


def test_the_cell_rule_with_the_flag_true_serves_the_cell_by_claude_from_the_next_day(calls):
    fw = THRESHOLDS["pool.fail_window"]
    calls.add(DAYS[0], GPT, [FAIL] * 7, cell=CELL)
    calls.add(DAYS[0], MINIMAX, [FAIL] * 7, cell=CELL)
    calls.add(DAYS[0], NEMOTRON, [OK] * 6, cell=CELL)
    rows = calls.rows()
    assert pl.claude_cells(rows, MODELS, DAYS[0], THRESHOLDS, True) == frozenset()
    assert cell_notices(rows, DAYS[0], flag=True) == []
    for d in DAYS[1:4]:
        assert pl.claude_cells(rows, MODELS, d, THRESHOLDS, True) == {CELL}
    # A window not yet full in another cell changes nothing.
    calls.add(DAYS[1], GPT, [FAIL] * (fw - 1), cell="trend/short")
    assert pl.claude_cells(calls.rows(), MODELS, DAYS[2], THRESHOLDS, True) == {CELL}


def test_the_same_rows_give_the_same_answers_twice(calls):
    calls.add(DAYS[0], GPT, window(11, 9))
    calls.add(DAYS[1], MINIMAX, [FAIL] * 20, cell=CELL)
    rows = calls.rows()
    first = (pl.removed_models(rows, MODELS, DAYS[2], THRESHOLDS),
             pl.day_events(rows, MODELS, DAYS[1], THRESHOLDS, claude_fallback=False))
    again = (pl.removed_models(calls.rows(), MODELS, DAYS[2], THRESHOLDS),
             pl.day_events(calls.rows(), MODELS, DAYS[1], THRESHOLDS, claude_fallback=False))
    assert first == again


# --- what pool.py imports (decision 122 (f)) ------------------------------------------


def test_pool_imports_nothing_that_reaches_the_network_or_a_secret():
    import ast

    tree = ast.parse((REPO_ROOT / "src" / "discotrade" / "workers" / "pool.py").read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    banned = ("httpx", "socket", "sub" + "process", "urllib", "http", "os",
              "discotrade.workers.providers", "discotrade.sources")
    assert not [n for n in names if any(n == b or n.startswith(b + ".") for b in banned)]
