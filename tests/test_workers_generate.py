"""The day's generation (DESIGN 13.4 (storage), 13.7, 10.2, 12.2, 12.3, 16.2; R-25;
decision 126 of meta/decisions/decisions-2026-10-16-m15.md, with decisions
2026-10-12 62 (the call row keys) and 2026-10-14-m13 104 (d) (the child-process
backend's trusted-text rule); I-5, I-6, I-13).

Every state directory here is a copy, under a pytest temporary directory, of
conftest's ``synth_bars_template``: the fixture track ``test_synth`` (four
synthetic instruments, seeds ``SEEDS``, asserted against the fixture records)
fetched in-process at ``--as-of`` ``2019-07-25T00:00:00+00:00``. The day is
``DAY`` 2019-07-15 (W 2019-06-11 to 2019-07-08), the cell ``trend/short``
(cell index 0), the configuration ``tests/fixtures/config/`` with the
production ``config/thresholds.toml`` copied in (``worker_tokens_per_day``
60000, ``worker_max_output_tokens`` 8000, ``min_changes_w`` 30, ``corr_max``
0.7, asserted). The pool is the fixture ``models.toml``'s three pool models,
all listed; ``DAY``'s trading ordinal from the epoch 2019-06-03 is 29 (the
weekdays of 2019-06-03 to 2019-07-12, less the closure 2019-07-04, counted
here), so the call's model is ``pool[(29 + 0) mod 3]``, the third,
``nvidia/nemotron-3-super-120b-a12b`` (cutoff month 2026-02, so the cutoff
date 2026-02-28).

The provider is ``ScriptedProvider`` over a scenario directory of
``tests/fixtures/responses/`` (each holding one subdirectory, the model's), or
a fake that raises when called; no real provider, model or ``claude`` binary,
no key. Each fixture response's Python block is byte-identical to a strategy
file under ``tests/fixtures/strategies/`` (asserted), so that the child-process
backend (its fork server, O-20, closed after the module), which runs only a text
byte-identical to a repository file (decision
104 (d)), validates it; one test, marked ``container``, runs one response
through the container backend, with its job directories under the temporary
directory and every container it started removed by name. Token counts are
the scripted provider's rule (``ceil(characters / 4)``), computed here. No
clock is read and no random draw is made.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT, SYNTH_AS_OF, SYNTH_DAY, copy_template

from discotrade import journal, ledger, state
from discotrade.config import load_calendar, load_models, load_track_config
from discotrade.daily import is_trading_day
from discotrade.sandbox import container
from discotrade.sandbox.container import ContainerSandbox
from discotrade.sandbox.process import ProcessSandbox
from discotrade.state import HealthEvent
from discotrade.workers import generate as gen
from discotrade.workers import parse as parse_mod
from discotrade.workers import pool as pl
from discotrade.workers import prompt
from discotrade.workers.providers import ProviderError, ScriptedProvider

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
DAY = date(2019, 7, 15)
EPOCH = date(2019, 6, 3)
CLOSED = date(2019, 7, 4)
CELL = ("trend", "short")
CELL_NAME = "trend/short"
BRIEF = ("Write an approach of the family trend for the horizon short that differs "
         "from every line of the registry.")
MODEL = "nvidia/nemotron-3-super-120b-a12b"
MODEL_DIR = "nvidia__nemotron-3-super-120b-a12b"
CUTOFF = date(2026, 2, 28)
RESPONSES = REPO_ROOT / "tests" / "fixtures" / "responses"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
TREND_MA = REPO_ROOT / "reference" / "trend_ma.py"
DUPLICATED = {"fast": 6, "slow": 48}
#: Decision 62's call row keys (DESIGN 10.2's fields), written out here.
CALL_KEYS = {"call", "date", "cell", "model", "attempt", "tokens_in", "tokens_out",
             "outcome", "response"}
#: Decision 126 (c)'s stored response keys, written out here.
RESPONSE_KEYS = {"call", "date", "cell", "model", "attempt", "messages", "text",
                 "tokens_in", "tokens_out", "model_version", "raw"}
#: The strategy file each fixture response's Python block is, and its description.
SCENARIOS = {
    "valid": ["changes_30.py"],
    "invalid_then_valid": ["changes_29.py", "changes_30.py"],
    "duplicate_then_invalid": ["trend_ma_flipped.py", "changes_29.py", "changes_30.py"],
    "parse_failures": [None, None, "changes_30.py"],
}
DESCRIPTION_30 = ("Momentum over a fixed lookback: long when the last close is above the "
                  "close that many bars before, short otherwise.")
ACTIVITY_29 = ("activity [min_changes_w]: 29 position changes on W summed over the basket; "
               "at least min_changes_w (30) are needed")


# ------------------------------------------------------------- helpers


def call_id(attempt: int) -> str:
    text = f"{TRACK}|{DAY.isoformat()}|{attempt}"
    return "c" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def response_path(state_dir: Path, attempt: int) -> Path:
    return state_dir / "responses" / TRACK / DAY.isoformat() / f"{call_id(attempt)}.json"


def relative(attempt: int) -> str:
    return f"responses/{TRACK}/{DAY.isoformat()}/{call_id(attempt)}.json"


def fixture_text(scenario: str, k: int) -> str:
    return (RESPONSES / scenario / MODEL_DIR / f"{k:04d}.md").read_text(encoding="utf-8")


class Recording:
    """A provider that records each call and each completion of the one it wraps."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = []
        self.completions = []

    def complete(self, model, messages, max_tokens):
        self.calls.append((model, [dict(m) for m in messages], max_tokens))
        done = self.inner.complete(model, messages, max_tokens)
        self.completions.append(done)
        return done


class Refusing:
    """A provider that fails the test when it is called."""

    def complete(self, model, messages, max_tokens):
        raise AssertionError(f"the provider was called for {model}")


def scripted(scenario: str) -> Recording:
    return Recording(ScriptedProvider(RESPONSES / scenario))


def calls(state_dir: Path, into: Path | None = None) -> list[dict]:
    return ledger.read(state_dir, TRACK, ledger.CALLS, into=into)


def calls_bytes(root: Path) -> bytes:
    return ledger.ledger_path(root, TRACK, ledger.CALLS).read_bytes()


def stored(state_dir: Path, attempt: int) -> dict:
    return json.loads(response_path(state_dir, attempt).read_text(encoding="utf-8"))


# ------------------------------------------------------------- fixtures


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
def models(config):
    return load_models(config / "models.toml")


@pytest.fixture(scope="module")
def day_pool(models):
    return pl.day_pool(models, DAY, [m.id for m in models.models], ())


@pytest.fixture(scope="module")
def ordinal(config):
    tc = load_track_config(config, TRACK)
    calendars = {i.calendar: load_calendar(config / "calendars" / f"{i.calendar}.toml")
                 for i in tc.instruments}
    return pl.trading_ordinal(DAY, tc.track.epoch, lambda d: is_trading_day(tc, calendars, d))


@pytest.fixture(scope="module")
def scratch(tmp_path_factory):
    return tmp_path_factory.mktemp("jobs")


@pytest.fixture(scope="module")
def backend(scratch):
    b = ProcessSandbox(scratch, fork_server=True)
    yield b
    b.close()


@pytest.fixture(scope="module")
def fresh(tmp_path_factory, synth_bars_template):
    """A factory of state directories: copies of the bars template under tmp."""
    assert (SYNTH_AS_OF, SYNTH_DAY) == ("2019-07-25T00:00:00+00:00", DAY)

    def make(name: str) -> Path:
        return copy_template(synth_bars_template, tmp_path_factory.mktemp(name) / "state")

    return make


def run(setup, state_dir, provider, backend, day_pool, ordinal, into=None):
    return gen.generate(state_dir, setup, DAY, CELL, BRIEF, provider=provider,
                        provider_errors=(ProviderError,), pool=day_pool, ordinal=ordinal,
                        backend=backend, into=into)


def admit_duplicated(state_dir, setup) -> str:
    return state.write_approach(
        state_dir, source=TREND_MA.read_text(encoding="utf-8"), params=DUPLICATED,
        cell=CELL_NAME, model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description="a reference strategy", profile_version="w-test",
        admitted=date(2019, 7, 1), instruments=setup.instruments,
        spread_tables=setup.spread_tables)


@pytest.fixture(scope="module")
def valid_run(fresh, setup, backend, day_pool, ordinal):
    """The ``valid`` scenario, its rows staged under ``staging``."""
    path = fresh("valid")
    staging = path.parent / "staging"
    provider = scripted("valid")
    out = run(setup, path, provider, backend, day_pool, ordinal, into=staging)
    return {"state": path, "staging": staging, "provider": provider, "out": out}


@pytest.fixture(scope="module")
def retry_run(fresh, setup, backend, day_pool, ordinal):
    """The ``invalid_then_valid`` scenario, its rows staged under ``staging``."""
    path = fresh("retry")
    staging = path.parent / "staging"
    provider = scripted("invalid_then_valid")
    out = run(setup, path, provider, backend, day_pool, ordinal, into=staging)
    return {"state": path, "staging": staging, "provider": provider, "out": out}


@pytest.fixture(scope="module")
def duplicate_run(fresh, setup, backend, day_pool, ordinal):
    """``duplicate_then_invalid`` on a state holding one live approach admitted from
    reference/trend_ma.py at ``DUPLICATED`` (rows written to the state directory)."""
    path = fresh("duplicate")
    aid = admit_duplicated(path, setup)
    provider = scripted("duplicate_then_invalid")
    out = run(setup, path, provider, backend, day_pool, ordinal)
    return {"state": path, "aid": aid, "provider": provider, "out": out}


# ------------------------------------------------------------- the facts the tests stand on


def test_the_seeds_day_pool_and_thresholds_are_the_ones_written_here(
        setup, models, day_pool, ordinal):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    assert setup.track.epoch == EPOCH
    assert setup.track.windows(DAY).w.first == date(2019, 6, 11)
    assert setup.track.windows(DAY).w.last == date(2019, 7, 8)
    t = setup.thresholds
    assert t["budgets.worker_tokens_per_day"] == 60000
    assert t["budgets.worker_max_output_tokens"] == 8000
    assert t["validation.min_changes_w"] == 30
    assert t["validation.corr_max"] == 0.7
    # The ordinal by this test's own count: weekdays from the epoch, less 2019-07-04.
    own = sum(1 for k in range((DAY - EPOCH).days)
              if (EPOCH + timedelta(days=k)).weekday() < 5
              and EPOCH + timedelta(days=k) != CLOSED)
    assert own == ordinal == 29
    assert setup.track.cell_index(*CELL) == 0
    ids = [m.id for m in day_pool.models]
    assert ids == ["openai/gpt-oss-120b", "MiniMaxAI/MiniMax-M3", MODEL]
    assert ids[(29 + 0) % 3] == MODEL
    assert models.get(MODEL).cutoff == "2026-02"
    assert day_pool.events == ()


def test_each_fixture_response_s_block_is_a_strategy_file_byte_for_byte(setup):
    for scenario, files in SCENARIOS.items():
        folder = RESPONSES / scenario
        assert sorted(p.name for p in folder.iterdir()) == [MODEL_DIR]
        names = sorted(p.name for p in (folder / MODEL_DIR).iterdir())
        assert names == [f"{k:04d}.md" for k in range(1, len(files) + 1)]
        for k, name in enumerate(files, 1):
            parsed = parse_mod.parse(fixture_text(scenario, k), setup.thresholds)
            if name is None:
                assert isinstance(parsed, parse_mod.Failure)
                continue
            assert isinstance(parsed, parse_mod.Parsed)
            assert parsed.source == (STRATEGIES / name).read_text(encoding="utf-8")


def test_the_call_id_is_c_and_twelve_hex_digits_of_the_sha256_of_track_day_attempt():
    for attempt in (1, 2):
        text = f"test_synth|2019-07-15|{attempt}"
        want = "c" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        assert gen.call_id(TRACK, DAY, attempt) == want
    assert gen.call_id(TRACK, DAY, 1) != gen.call_id(TRACK, DAY, 2)


def test_generate_imports_nothing_that_reaches_the_network_or_a_secret():
    tree = ast.parse((REPO_ROOT / "src" / "discotrade" / "workers" / "generate.py")
                     .read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    banned = ("httpx", "socket", "sub" + "process", "urllib", "http", "os",
              "discotrade.workers.providers", "discotrade.sources")
    assert not [n for n in names if any(n == b or n.startswith(b + ".") for b in banned)]


# ------------------------------------------------------------- a valid response


def test_a_valid_response_gives_a_candidate_and_one_trial_row(valid_run, setup):
    out, path, staging = valid_run["out"], valid_run["state"], valid_run["staging"]
    sent = valid_run["provider"].calls
    assert len(sent) == 1
    model, messages, max_tokens = sent[0]
    assert (model, max_tokens) == (MODEL, 8000)
    first = prompt.build(path, setup, DAY, CELL, BRIEF, call_id(1))
    assert messages == [{"role": "user", "content": first}]
    text = fixture_text("valid", 1)
    want = {"call": call_id(1), "date": "2019-07-15", "cell": CELL_NAME, "model": MODEL,
            "attempt": 1, "tokens_in": tokens(first), "tokens_out": tokens(text),
            "outcome": "trial", "response": relative(1)}
    rows = calls(path, into=staging)
    assert rows == [want]
    assert set(rows[0]) == CALL_KEYS == set(ledger.KEYS[ledger.CALLS])
    assert [dict(r) for r in out.rows] == [want]
    assert out.events == ()
    c = out.candidate
    assert c is not None
    assert c.source == (STRATEGIES / "changes_30.py").read_text(encoding="utf-8")
    assert c.description == DESCRIPTION_30
    assert dict(c.params) == {"lookback": 215}
    assert c.grid["grid"] is None and c.grid["fixed"] == {"lookback": 215}
    assert [r["params"] for r in c.grid["results"]] == [{"lookback": 215}]
    assert set(c.metrics_w) >= {"trades", "sharpe"}
    assert set(c.adjusted_w) == {"sharpe", "sharpe_2x", "total_return", "total_return_2x",
                                 "avg_position"}
    assert set(c.adjusted_w["avg_position"]) == set(SEEDS)
    assert (c.model_id, c.model_version, c.cutoff) == (MODEL, "scripted", CUTOFF)
    assert c.profile_version == "p1"
    assert (c.day, c.cell, c.call) == (DAY, CELL, call_id(1))


def test_rows_go_to_the_ledger_location_given_and_no_trial_is_written(valid_run):
    path, staging = valid_run["state"], valid_run["staging"]
    assert ledger.ledger_path(staging, TRACK, ledger.CALLS).exists()
    assert not ledger.ledger_path(path, TRACK, ledger.CALLS).exists()
    for name in (ledger.TRIALS, ledger.LIFECYCLE):
        assert not ledger.ledger_path(path, TRACK, name).exists()
        assert not ledger.ledger_path(staging, TRACK, name).exists()
    assert not (path / "trials").exists() and not (path / "approaches").exists()
    # The response is stored outside the staging directory (DESIGN 16.2).
    assert response_path(path, 1).is_file()
    assert not (staging / "responses").exists()


def test_the_response_file_read_back_is_what_the_provider_returned(valid_run):
    path = valid_run["state"]
    [(model, messages, _)] = valid_run["provider"].calls
    [done] = valid_run["provider"].completions
    raw = response_path(path, 1).read_text(encoding="utf-8")
    doc = json.loads(raw)
    assert set(doc) == RESPONSE_KEYS
    assert doc == {"call": call_id(1), "date": "2019-07-15", "cell": CELL_NAME,
                   "model": model, "attempt": 1, "messages": messages, "text": done.text,
                   "tokens_in": done.tokens_in, "tokens_out": done.tokens_out,
                   "model_version": done.model_version, "raw": dict(done.raw)}
    assert raw == json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n"


# ------------------------------------------------------------- one retry in all (R-25)


def test_an_invalid_then_a_valid_response_give_two_rows_and_the_retry_holds_the_error(
        retry_run, setup):
    path, staging = retry_run["state"], retry_run["staging"]
    sent = retry_run["provider"].calls
    assert len(sent) == 2
    first = prompt.build(path, setup, DAY, CELL, BRIEF, call_id(1))
    reply = fixture_text("invalid_then_valid", 1)
    assert sent[0][1] == [{"role": "user", "content": first}]
    retry = sent[1][1]
    assert sent[1][0] == MODEL                     # a retry uses the first call's model
    assert [m["role"] for m in retry] == ["user", "assistant", "user"]
    assert retry[0]["content"] == first and retry[1]["content"] == reply
    assert retry[2]["content"] == gen.RETRY_TEXT + "\n\n" + ACTIVITY_29
    rows = calls(path, into=staging)
    assert [(r["call"], r["attempt"], r["outcome"]) for r in rows] == [
        (call_id(1), 1, "invalid:activity"), (call_id(2), 2, "trial")]
    assert rows[1]["tokens_in"] == tokens("".join(m["content"] for m in retry))
    assert rows[1]["tokens_out"] == tokens(fixture_text("invalid_then_valid", 2))
    assert all(set(r) == CALL_KEYS for r in rows)
    assert stored(path, 2)["messages"] == retry
    assert retry_run["out"].candidate is not None
    assert retry_run["out"].candidate.call == call_id(2)


def test_a_duplicate_then_a_second_failure_give_two_rows_and_the_retry_names_the_approach(
        duplicate_run):
    path, aid = duplicate_run["state"], duplicate_run["aid"]
    assert aid == state.approach_id(TREND_MA.read_text(encoding="utf-8"), DUPLICATED)
    sent = duplicate_run["provider"].calls
    # The corpus holds a third, valid response: a second retry would take it.
    assert len(sent) == 2
    error = sent[1][1][2]["content"]
    assert error.startswith(gen.RETRY_TEXT + "\n\n")
    assert f"approach {aid}" in error
    assert "corr_max = 0.7" in error
    rows = calls(path)
    assert [(r["attempt"], r["outcome"]) for r in rows] == [(1, "duplicate"),
                                                            (2, "invalid:activity")]
    assert all(set(r) == CALL_KEYS for r in rows)
    assert duplicate_run["out"].candidate is None


def test_a_parse_failure_is_stored_in_full_before_it_is_refused(
        fresh, setup, backend, day_pool, ordinal, monkeypatch):
    path = fresh("parse")
    provider = scripted("parse_failures")
    seen = []
    real = parse_mod.parse

    def spy(text, thresholds):
        attempt = len(seen) + 1
        where = response_path(path, attempt)
        assert where.is_file(), "the response was parsed before it was stored"
        assert json.loads(where.read_text(encoding="utf-8"))["text"] == text
        seen.append(attempt)
        return real(text, thresholds)

    monkeypatch.setattr(parse_mod, "parse", spy)
    out = run(setup, path, provider, backend, day_pool, ordinal)
    assert seen == [1, 2]
    assert len(provider.calls) == 2
    for attempt in (1, 2):
        assert stored(path, attempt)["text"] == fixture_text("parse_failures", attempt)
    rows = calls(path)
    assert [(r["attempt"], r["outcome"]) for r in rows] == [(1, "invalid:parse"),
                                                            (2, "invalid:parse")]
    retry = provider.calls[1][1]
    assert retry[2]["content"] == (gen.RETRY_TEXT + "\n\n"
                                   + parse_mod.TEXTS[parse_mod.NO_BLOCK])
    assert out.candidate is None


# ------------------------------------------------------------- the budget


def earlier_rows(path, staging, earlier: int):
    """A row of the day before with many tokens in the state's ledger, and one of
    ``DAY`` with ``earlier`` tokens staged under ``staging``."""
    base = {"cell": CELL_NAME, "model": MODEL, "attempt": 1, "outcome": "trial",
            "response": None}
    ledger.append_calls(path, TRACK, [{**base, "call": "cprevious0000", "date": "2019-07-12",
                                       "tokens_in": 59000, "tokens_out": 900}])
    ledger.append_calls(path, TRACK, [{**base, "call": "cearlier00000", "date": "2019-07-15",
                                       "tokens_in": earlier - 1000, "tokens_out": 1000}],
                        into=staging)


def test_a_budget_reached_makes_no_call_and_writes_a_budget_row_and_the_event(
        fresh, setup, backend, day_pool, ordinal):
    path = fresh("budget-now")
    staging = path.parent / "staging"
    # 52001 + 8000 = 60001 > 60000.
    earlier_rows(path, staging, 52001)
    out = run(setup, path, Refusing(), backend, day_pool, ordinal, into=staging)
    rows = calls(path, into=staging)
    budget = {"call": call_id(1), "date": "2019-07-15", "cell": CELL_NAME, "model": MODEL,
              "attempt": 1, "tokens_in": 0, "tokens_out": 0, "outcome": "budget",
              "response": None}
    assert rows[-1] == budget and len(rows) == 3
    assert set(rows[-1]) == CALL_KEYS
    assert out.candidate is None
    assert list(out.events) == [HealthEvent(DAY, "alert", "token_budget", TRACK,
                                            {"call": call_id(1), "day_tokens": 52001,
                                             "max_output_tokens": 8000,
                                             "tokens_per_day": 60000})]
    assert not (path / "responses").exists()


def test_the_budget_counts_the_day_s_earlier_tokens_staged_rows_and_attempt_1_included(
        fresh, setup, backend, day_pool, ordinal):
    path = fresh("budget-retry")
    staging = path.parent / "staging"
    # 52000 + 8000 = 60000 is not above the budget: attempt 1 is made.
    earlier_rows(path, staging, 52000)
    provider = scripted("parse_failures")
    out = run(setup, path, provider, backend, day_pool, ordinal, into=staging)
    assert len(provider.calls) == 1
    rows = calls(path, into=staging)
    assert [r["call"] for r in rows[:2]] == ["cprevious0000", "cearlier00000"]
    first = rows[2]
    assert (first["attempt"], first["outcome"]) == (1, "invalid:parse")
    spent = first["tokens_in"] + first["tokens_out"]
    assert spent > 0 and 52000 + spent + 8000 > 60000
    assert len(rows) == 4
    assert rows[3] == {"call": call_id(2), "date": "2019-07-15", "cell": CELL_NAME,
                       "model": MODEL, "attempt": 2, "tokens_in": 0, "tokens_out": 0,
                       "outcome": "budget", "response": None}
    assert [e.kind for e in out.events] == ["token_budget"]
    assert out.events[0].level == "alert"
    assert out.events[0].detail["day_tokens"] == 52000 + spent


# ------------------------------------------------------------- stored responses, errors, bytes


def test_a_day_whose_response_files_exist_makes_no_provider_call_and_gives_the_same_rows(
        retry_run, setup, backend, day_pool, ordinal):
    path, staging = retry_run["state"], retry_run["staging"]
    before = calls_bytes(staging)
    files = {a: response_path(path, a).read_bytes() for a in (1, 2)}
    again = path.parent / "staging-again"          # a clean staging directory
    out = run(setup, path, Refusing(), backend, day_pool, ordinal, into=again)
    assert calls_bytes(again) == before
    assert {a: response_path(path, a).read_bytes() for a in (1, 2)} == files
    assert out.candidate == retry_run["out"].candidate
    assert out.rows == retry_run["out"].rows


def test_a_provider_error_writes_one_row_and_no_retry(
        fresh, setup, backend, day_pool, ordinal, tmp_path):
    path = fresh("provider-error")
    provider = Recording(ScriptedProvider(tmp_path / "no-corpus"))
    out = run(setup, path, provider, backend, day_pool, ordinal)
    assert len(provider.calls) == 1 and provider.completions == []
    assert calls(path) == [{"call": call_id(1), "date": "2019-07-15", "cell": CELL_NAME,
                            "model": MODEL, "attempt": 1, "tokens_in": 0, "tokens_out": 0,
                            "outcome": "provider_error", "response": None}]
    assert out.candidate is None and out.events == ()
    assert not (path / "responses").exists()


def test_the_same_inputs_give_the_same_bytes_twice(
        valid_run, fresh, setup, backend, day_pool, ordinal):
    path = fresh("valid-again")
    staging = path.parent / "staging"
    out = run(setup, path, scripted("valid"), backend, day_pool, ordinal, into=staging)
    assert calls_bytes(staging) == calls_bytes(valid_run["staging"])
    assert response_path(path, 1).read_bytes() == \
        response_path(valid_run["state"], 1).read_bytes()
    assert out == valid_run["out"]


def test_an_empty_pool_makes_no_call(fresh, setup, backend, models):
    path = fresh("empty-pool")
    empty = pl.day_pool(models, DAY, [], ())
    out = run(setup, path, Refusing(), backend, empty, 29)
    assert out.candidate is None and out.rows == () and out.events == ()
    assert not ledger.ledger_path(path, TRACK, ledger.CALLS).exists()


# ------------------------------------------------------------- the container backend


@pytest.mark.container
def test_one_fixture_response_runs_through_the_container_backend(
        fresh, setup, day_pool, ordinal, config, tmp_path):
    path = fresh("container")
    b = ContainerSandbox(tmp_path / "scratch", config)
    try:
        out = run(setup, path, scripted("valid"), b, day_pool, ordinal)
        left = [n for n in b.started if container.container_exists(b.runtime(), n)]
    finally:
        for name in b.started:
            if container.container_exists(b.runtime(), name):
                container.remove(b.runtime(), name)
    assert b.started, "the backend started no container"
    assert left == []
    assert [r["outcome"] for r in calls(path)] == ["trial"]
    assert out.candidate is not None
    assert out.candidate.source == (STRATEGIES / "changes_30.py").read_text(encoding="utf-8")
