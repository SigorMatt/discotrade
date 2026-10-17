"""Gate item G3.2: over G3.1's days no cell is always served by the same model; a
retry carries the error text; every response is stored in full; a model whose
failure rate crosses the limit over a full window is removed and the health
alert is raised; the token budget ends generation while journaling completes
(DESIGN 18.3 G3.2, 18.2, 13.5, 13.6, 13.7, 15.2, 16.1 steps 3 to 5, 16.2, 16.3;
decisions 139 (b), 138, 136, 126, 124 and 72 of meta/decisions/; R-21, R-25;
I-5, I-11, I-12).

Two replays, each in-process through ``discotrade.cli.main`` on decision 72's
gate configuration (``tests/fixtures/config/`` with ``thresholds_gate.toml``
copied in unchanged under the test's temporary directory, the fixture
``models.toml``), the child-process backend, the scripted coordinator and
``--provider scripted:<corpus>``, each into a state made by ``init-state`` at
``INIT_AS_OF``:

- G3.1's replay: ``tests/fixtures/worker_corpus/m3/`` over the twenty trading
  days ``FIRST`` 2019-07-15 to ``LAST`` 2019-08-09. Every call row's model equals
  ``pool[(ordinal(D) + c) mod len(pool)]``, computed here: the pool is the
  ``pool = true`` models of ``models.toml`` in file order (each listed by the
  corpus, none skipped or removed in the health log); ``ordinal(D)`` is the count
  of trading days of ``synth_week`` from the track's epoch ``EPOCH`` up to and
  excluding ``D``, the weekdays less the closed day ``CLOSED`` 2019-07-04 (the
  calendar's closure runs from 13:00 on the 3rd to 18:00 on the 4th, so the
  session of the 4th never opens), computed with numpy; ``c`` is the cell's index
  in the track's order (families, then horizons). For every cell index, the
  twenty days' ordinals give at least two models, and at least one cell is
  served by two models in the call rows. Every attempt-2 response's messages are
  attempt 1's prompt, attempt 1's reply as the assistant's message and a last
  user message that begins with the fixed retry text (``RETRY_TEXT``, written
  here) and holds attempt 1's error text, taken from the validation run here on
  attempt 1's stored text (``workers.parse`` for a reply that does not parse,
  else ``validation.sequence.validate`` on W of the day through the child-process
  backend); for a duplicate it names the approach and holds ``corr_max = <the
  value>``. Every row with a response names a file that exists, holds every key
  of a stored response, and whose ``text`` equals, byte for byte, the corpus file
  the cursor served: the k-th response of a model, in row order, is the model's
  k-th file in name order.
- ``tests/fixtures/worker_corpus/m3_pool/`` (one model, whose replies fail
  validation) over ``FIRST`` to ``POOL_LAST`` 2019-07-31. ``pool.fail_window``
  and ``pool.fail_rate`` are read at their production values
  (``config/thresholds.toml``, asserted equal in the gate copy). The test walks
  the model's counted call rows (``trial``, ``duplicate``, ``invalid:<stage>``)
  day by day and finds the first trading day after whose calls the last
  ``fail_window`` of them form a full window with a failure share above
  ``fail_rate``; the health log holds one ``model_removed`` alert for the model,
  dated that day, none earlier; the model has calls that day and the trading day
  before (it was not removed the day before) and none after. The day whose
  attempt 2 meets the budget (``budgets.*`` at production values: attempt 1's
  tokens, ``ceil(characters / 4)`` of its text out, plus
  ``worker_max_output_tokens`` above ``worker_tokens_per_day``) has a ``budget``
  row with no response and zero tokens, a ``token_budget`` alert, one stored
  response (no second call), and its journal file written and committed in the
  state repository.

Seeds: the synthetic instruments' seeds are their fixture records' (``SEEDS``,
asserted); no other random draw is made. Time comes only from ``--as-of`` of
``init-state`` and the replay's clock. Git runs on local paths only, with
``GIT_ALLOW_PROTOCOL=file`` (``m1_harness.git``, decision 47).
"""

import math
import tomllib
from datetime import date, timedelta

import numpy as np
import pytest
from m1_harness import git
from m3_harness import (
    M3,
    M3_POOL,
    backend,
    calls,
    corpus_files,
    health,
    models_toml,
    stored,
    worker_replay,
)

from discotrade import journal
from discotrade.cli import REPO_ROOT
from discotrade.config import load_track_config
from discotrade.validation import sequence
from discotrade.workers import parse

pytestmark = [pytest.mark.gate, pytest.mark.gate_m3]

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
EPOCH = date(2019, 6, 3)
CLOSED = date(2019, 7, 4)
FIRST, LAST = date(2019, 7, 15), date(2019, 8, 9)
POOL_LAST = date(2019, 7, 31)
FIRST_ORDINAL = 29
TRADING_DAYS = 20
RETRY_TEXT = ("Your reply was refused by the validation, for the reason below. Reply once "
              "more in the output format the first message gives: one fenced Python block, "
              "then a one-sentence description. This is the last attempt.")
STORED_KEYS = {"attempt", "call", "cell", "date", "messages", "model", "model_version", "raw",
               "text", "tokens_in", "tokens_out"}
PRODUCTION = REPO_ROOT / "config" / "thresholds.toml"


def ordinal(day: date) -> int:
    return int(np.busday_count(EPOCH, day, weekmask="1111100", holidays=[CLOSED]))


def trading_days(first: date, last: date) -> list[date]:
    out = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    return [d for d in out if np.is_busday(d, weekmask="1111100", holidays=[CLOSED])]


def counted(outcome: str) -> bool:
    return outcome in ("trial", "duplicate") or (outcome.startswith("invalid:")
                                                  and len(outcome) > len("invalid:"))


@pytest.fixture(scope="module")
def replayed(tmp_path_factory):
    state, config, status, out, err = worker_replay(
        tmp_path_factory.mktemp("g32"), M3, TRACK, INIT_AS_OF, FIRST, LAST)
    assert status == 0, err
    return state, config


@pytest.fixture(scope="module")
def pooled(tmp_path_factory):
    state, config, status, out, err = worker_replay(
        tmp_path_factory.mktemp("g32pool"), M3_POOL, TRACK, INIT_AS_OF, FIRST, POOL_LAST)
    assert status == 0, err
    return state, config


@pytest.fixture(scope="module")
def production():
    with open(PRODUCTION, "rb") as f:
        return tomllib.load(f)


def the_pool(config, corpus) -> list[str]:
    listed = {p.name.replace("__", "/") for p in corpus.iterdir() if p.is_dir()}
    return [m["id"] for m in models_toml(config)["model"] if m["pool"] and m["id"] in listed]


def test_span_ordinals_and_seeds(replayed):
    state, config = replayed
    tc = load_track_config(config, TRACK)
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS
    assert tc.track.epoch == EPOCH
    days = trading_days(FIRST, LAST)
    assert len(days) == TRADING_DAYS and days[0] == FIRST and days[-1] == LAST
    assert ordinal(FIRST) == FIRST_ORDINAL
    assert [ordinal(d) for d in days] == list(range(FIRST_ORDINAL, FIRST_ORDINAL + 20))
    journaled = {p.stem for p in (state / "journal" / TRACK).rglob("*.parquet")}
    assert journaled == {d.isoformat() for d in days}


def test_every_call_row_model_is_the_rotation(replayed):
    state, config = replayed
    track = load_track_config(config, TRACK).track
    pool = the_pool(config, M3)
    assert len(pool) == 3
    kinds = {e["kind"] for e in health(state, TRACK)}
    assert not kinds & {"model_skipped", "model_removed", "model_list_failed", "pool_empty"}
    rows = calls(state, TRACK)
    assert rows
    for r in rows:
        family, horizon = r["cell"].split("/")
        c = track.cell_index(family, horizon)
        day = date.fromisoformat(r["date"])
        assert r["model"] == pool[(ordinal(day) + c) % len(pool)], r


def test_no_cell_is_always_served_by_one_model(replayed):
    state, config = replayed
    track = load_track_config(config, TRACK).track
    pool = the_pool(config, M3)
    ordinals = [ordinal(d) for d in trading_days(FIRST, LAST)]
    for c in range(len(track.cells)):
        assert len({pool[(o + c) % len(pool)] for o in ordinals}) >= 2, c
    served: dict[str, set[str]] = {}
    for r in calls(state, TRACK):
        served.setdefault(r["cell"], set()).add(r["model"])
    assert any(len(models) >= 2 for models in served.values()), served


def test_a_retry_carries_the_error_text(replayed, tmp_path):
    state, config = replayed
    setup = journal.Setup.load(config, TRACK)
    corr_max = setup.thresholds["validation.corr_max"]
    rows = calls(state, TRACK)
    firsts = {r["date"]: r for r in rows if r["attempt"] == 1}
    retries = [r for r in rows if r["attempt"] == 2 and r["response"] is not None]
    kinds = set()
    with backend(tmp_path / "jobs") as box:
        for r in retries:
            first = firsts[r["date"]]
            before, doc = stored(state, first), stored(state, r)
            messages = doc["messages"]
            assert messages[:2] == [before["messages"][0],
                                    {"role": "assistant", "content": before["text"]}]
            assert len(messages) == 3 and messages[2]["role"] == "user"
            last = messages[2]["content"]
            assert last.startswith(RETRY_TEXT), last
            parsed = parse.parse(before["text"], setup.thresholds)
            if isinstance(parsed, parse.Failure):
                text, stage = parsed.text, "parse"
            else:
                ctx = sequence.Context(state, config, setup, date.fromisoformat(r["date"]),
                                       box)
                out = sequence.validate(ctx, parsed.source)
                assert not out.ok
                text, stage = out.text, out.stage
            assert first["outcome"] == ("duplicate" if stage == "correlation"
                                        else f"invalid:{stage}")
            assert text and text in last, (r["date"], text, last)
            if stage == "correlation":
                named = text.rsplit("approach ", 1)[1].split()[0]
                assert (state / "approaches" / named).is_dir()
                assert named in last and f"corr_max = {corr_max}" in last
            kinds.add(stage)
    assert "correlation" in kinds and kinds - {"correlation", "parse"}, kinds


def test_every_response_is_stored_in_full(replayed):
    state, config = replayed
    served: dict[str, int] = {}
    with_response = 0
    for r in calls(state, TRACK):
        if r["response"] is None:
            continue
        with_response += 1
        path = state / r["response"]
        assert path.is_file(), r
        doc = stored(state, r)
        assert set(doc) == STORED_KEYS
        assert (doc["call"], doc["date"], doc["model"], doc["attempt"]) == \
            (r["call"], r["date"], r["model"], r["attempt"])
        assert (doc["tokens_in"], doc["tokens_out"]) == (r["tokens_in"], r["tokens_out"])
        k = served.get(r["model"], 0)
        served[r["model"]] = k + 1
        corpus_file = corpus_files(M3, r["model"])[k]
        assert doc["text"].encode("utf-8") == corpus_file.read_bytes(), (r, corpus_file)
    assert with_response == len(list((state / "responses" / TRACK).rglob("*.json")))


def test_production_values_of_the_pool_and_budget_keys(pooled, production):
    _, config = pooled
    with open(config / "thresholds.toml", "rb") as f:
        gate = tomllib.load(f)
    for section, key in (("pool", "fail_window"), ("pool", "fail_rate"),
                         ("budgets", "worker_tokens_per_day"),
                         ("budgets", "worker_max_output_tokens")):
        assert gate[section][key] == production[section][key], key


def test_a_failing_model_is_removed_after_a_full_window(pooled, production):
    state, config = pooled
    window = int(production["pool"]["fail_window"])
    rate = float(production["pool"]["fail_rate"])
    pool = the_pool(config, M3_POOL)
    assert len(pool) == 1
    model = pool[0]
    rows = [r for r in calls(state, TRACK) if r["model"] == model]
    days = trading_days(FIRST, POOL_LAST)
    outcomes: list[str] = []
    removal = None
    for d in days:
        outcomes += [r["outcome"] for r in rows
                     if r["date"] == d.isoformat() and counted(r["outcome"])]
        last = outcomes[-window:]
        if len(last) == window and sum(o.startswith("invalid:") for o in last) / window > rate:
            removal = d
            break
    assert removal is not None and removal < POOL_LAST
    before = days[days.index(removal) - 1]
    alerts = [e for e in health(state, TRACK) if e["kind"] == "model_removed"]
    assert alerts == [{"date": removal.isoformat(), "detail": alerts[0]["detail"],
                       "kind": "model_removed", "level": "alert", "subject": model}]
    called = {r["date"] for r in rows}
    assert removal.isoformat() in called and before.isoformat() in called
    assert not [r for r in rows if date.fromisoformat(r["date"]) > removal]
    assert all(r["model"] == model for r in calls(state, TRACK))
    journaled = {p.stem for p in (state / "journal" / TRACK).rglob("*.parquet")}
    assert journaled == {d.isoformat() for d in days}
    print(f"G3.2: {model} removed on {removal} (calls on {before} and {removal})")


def test_the_token_budget_ends_generation_and_the_day_is_journaled(pooled, production):
    state, _ = pooled
    per_day = int(production["budgets"]["worker_tokens_per_day"])
    max_out = int(production["budgets"]["worker_max_output_tokens"])
    rows = calls(state, TRACK)
    budget = [r for r in rows if r["outcome"] == "budget"]
    assert len(budget) == 1
    b = budget[0]
    day = b["date"]
    assert (b["attempt"], b["response"], b["tokens_in"], b["tokens_out"]) == (2, None, 0, 0)
    same_day = [r for r in rows if r["date"] == day]
    assert [r["attempt"] for r in same_day] == [1, 2]
    first = same_day[0]
    doc = stored(state, first)
    assert first["tokens_out"] == math.ceil(len(doc["text"]) / 4)
    assert first["tokens_in"] + first["tokens_out"] + max_out > per_day
    assert first["tokens_in"] + first["tokens_out"] <= per_day
    assert [p.name for p in (state / "responses" / TRACK / day).iterdir()] == \
        [f"{first['call']}.json"]
    alerts = [e for e in health(state, TRACK) if e["kind"] == "token_budget"]
    assert [(e["date"], e["level"]) for e in alerts] == [(day, "alert")]
    journal_file = f"journal/{TRACK}/{day[:4]}/{day}.parquet"
    assert (state / journal_file).is_file()
    assert git(state, "ls-files", journal_file).split() == [journal_file]
    assert f"run {TRACK} {day}" in git(state, "log", "--format=%s").splitlines()
