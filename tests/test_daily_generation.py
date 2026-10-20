"""Daily steps 3 to 5 in ``run_day`` (DESIGN 16.1 steps 3 to 5, 13.6, 13.7, 14.1,
14.3, 15.2, 16.2; decision 136 of meta/decisions/decisions-2026-10-16-m17.md,
with decisions 124, 125, 126 of decisions-2026-10-16-m15.md and 131 (b), (c) of
decisions-2026-10-16-m16.md; REVIEW-15 notes 2 and 4; I-5, I-6, I-8, I-13).

Every state directory is a copy, under a pytest temporary directory, of
conftest's ``synth_committed_template``: ``init-state`` at
``2019-07-25T00:00:00+00:00``, the fixture track ``test_synth`` (four synthetic
instruments, seeds ``SEEDS``, asserted against the fixture records, bar length
3600 s) fetched at that instant and committed. ``run_day`` is called in-process
with a ``FixedClock`` at that instant, on ``D`` 2019-07-15 (trading ordinal 29
from the epoch 2019-06-03, asserted) and ``NEXT`` 2019-07-16, on the track's
default backend, the child-process one (decision 104 (d): it runs only a text
byte-identical to a repository file). The configuration is
``tests/fixtures/config/`` with the production ``config/thresholds.toml``
copied in under the temporary directory, unchanged; the tests that need another
one copy it again under their own temporary directory and change it there, each
saying which value (the gap limit ``gaps.max_fraction``, the day's token budget
``budgets.worker_tokens_per_day``, and a track record with one cell).

The provider is ``ScriptedProvider`` over a corpus directory under the test's
temporary directory holding one model's subdirectory,
``nvidia__nemotron-3-super-120b-a12b``, whose files are copies of files of
``tests/fixtures/responses/`` (their Python blocks byte-identical to
``tests/fixtures/strategies/`` files, as tests/test_workers_generate.py
asserts), or a fake that fails the test when called. The pool is thus the
fixture ``models.toml``'s third model alone (the other two are skipped with a
``model_skipped`` notice each), and the call's model is that one. No socket,
key, real provider, model or ``claude`` binary; no wall clock; no random draw
beyond the synthetic sources' fixed seeds.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT, SYNTH_AS_OF, SYNTH_DAY, copy_template

from discotrade import daily, journal, ledger, lifecycle
from discotrade.cli import main
from discotrade.clock import FixedClock
from discotrade.config import load_calendar, load_track_config
from discotrade.coordinator import Brief, CellStatus
from discotrade.state import STAGING, write_approach
from discotrade.workers import generate as gen
from discotrade.workers import pool as pl
from discotrade.workers.providers import ProviderError, ScriptedProvider

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
D = date(2019, 7, 15)
NEXT = date(2019, 7, 16)
INSTANT = datetime(2019, 7, 25, tzinfo=UTC)
EPOCH = date(2019, 6, 3)
CELL = ("trend", "short")
CELL_NAME = "trend/short"
MODEL = "nvidia/nemotron-3-super-120b-a12b"
MODEL_DIR = "nvidia__nemotron-3-super-120b-a12b"
SKIPPED = ("openai/gpt-oss-120b", "MiniMaxAI/MiniMax-M3")
RESPONSES = REPO_ROOT / "tests" / "fixtures" / "responses"
TREND_MA = REPO_ROOT / "reference" / "trend_ma.py"
DUPLICATED = {"fast": 6, "slow": 48}
#: The fixture responses each corpus copies, in cursor order.
VALID = [RESPONSES / "duplicate_then_invalid" / MODEL_DIR / "0001.md"]      # trend_ma_flipped
DUPLICATE_THEN_INVALID = [RESPONSES / "duplicate_then_invalid" / MODEL_DIR / f"000{k}.md"
                          for k in (1, 2)]                          # trend_ma_flipped, changes_29


# ------------------------------------------------------------- helpers


def call_id(day: date, attempt: int) -> str:
    text = f"{TRACK}|{day.isoformat()}|{attempt}"
    return "c" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def corpus(root: Path, files: list[Path]) -> Path:
    folder = root / MODEL_DIR
    folder.mkdir(parents=True)
    for k, path in enumerate(files, 1):
        shutil.copy(path, folder / f"{k:04d}.md")
    return root


class Recording:
    """A provider that records each call of the one it wraps."""

    def __init__(self, inner):
        self.inner = inner
        self.lists = 0
        self.calls = []

    def list_models(self):
        self.lists += 1
        return self.inner.list_models()

    def complete(self, model, messages, max_tokens):
        self.calls.append((model, [dict(m) for m in messages], max_tokens))
        return self.inner.complete(model, messages, max_tokens)


class Refusing:
    """A provider that fails the test when it is called at all."""

    def list_models(self):
        raise AssertionError("the provider's model list was read")

    def complete(self, model, messages, max_tokens):
        raise AssertionError(f"the provider was called for {model}")


class ListOnly:
    """A provider that lists ``models`` and fails the test when called."""

    def __init__(self, models):
        self.models = list(models)

    def list_models(self):
        return list(self.models)

    def complete(self, model, messages, max_tokens):
        raise AssertionError(f"the provider was called for {model}")


class ListFails:
    """A provider whose model list fails; a call fails the test."""

    def list_models(self):
        raise ProviderError("injected: the model list cannot be read")

    def complete(self, model, messages, max_tokens):
        raise AssertionError(f"the provider was called for {model}")


class OutOfList:
    """A coordinator that chooses a cell that is not offered (DESIGN 14.3)."""

    def choose_cell(self, cells, registry):
        return Brief(("no_such_family", "short"), "Write an approach.")

    def write_digest(self, alerts):
        return ""

    def write_runlog_line(self, summary):
        return ""


def run(state, config, day=D, **kw):
    return daily.run_day(state, config, TRACK, FixedClock(INSTANT), day, **kw)


def rows(state, name):
    return ledger.read(state, TRACK, name)


def ledger_bytes(state, name):
    path = ledger.ledger_path(state, TRACK, name)
    return path.read_bytes() if path.exists() else None


def health(state) -> list[dict]:
    path = state / "health" / f"{TRACK}.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def files(root) -> dict[str, tuple[bytes, int]]:
    """Every file under ``root`` but ``.git/``, with its bytes and mtime."""
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def admit_trend_ma(state, setup, admitted, cell=CELL_NAME) -> str:
    return write_approach(
        state, source=TREND_MA.read_text(encoding="utf-8"), params=DUPLICATED, cell=cell,
        model_id="test-model", model_version="test-model-v0", cutoff=date(2019, 1, 1),
        description="a reference strategy", profile_version="w-test", admitted=admitted,
        instruments=setup.instruments, spread_tables=setup.spread_tables)


def changed_copy(config: Path, dest: Path, name: str, old: str, new: str) -> Path:
    """A copy of ``config`` at ``dest`` with ``old`` replaced by ``new`` in ``name``."""
    shutil.copytree(config, dest)
    path = dest / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (name, old)
    path.write_text(text.replace(old, new), encoding="utf-8")
    return dest


# ------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _git_local(monkeypatch):
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")


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
def fresh(tmp_path_factory, synth_committed_template):
    """A factory of state directories: copies of the committed template under tmp."""
    assert (SYNTH_AS_OF, SYNTH_DAY) == (INSTANT.isoformat(), D)

    def make(name: str) -> Path:
        return copy_template(synth_committed_template, tmp_path_factory.mktemp(name) / "state")

    return make


@pytest.fixture(scope="module")
def valid_day(fresh, config, tmp_path_factory):
    """``D`` run with the scripted provider over a corpus of one valid response."""
    state = fresh("valid")
    provider = Recording(ScriptedProvider(corpus(tmp_path_factory.mktemp("valid-corpus"),
                                                 VALID)))
    done = run(state, config, provider=provider)
    return {"state": state, "provider": provider, "done": done}


# ------------------------------------------------------------- the facts the tests stand on


def test_the_seeds_ordinal_and_thresholds_are_the_ones_written_here(config, setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    assert setup.track.epoch == EPOCH
    tc = load_track_config(config, TRACK)
    calendars = {i.calendar: load_calendar(config / "calendars" / f"{i.calendar}.toml")
                 for i in tc.instruments}
    ordinal = pl.trading_ordinal(D, EPOCH, lambda d: daily.is_trading_day(tc, calendars, d))
    # Weekdays from the epoch to D, less the closure 2019-07-04, counted here.
    own = sum(1 for k in range((D - EPOCH).days)
              if (EPOCH + timedelta(days=k)).weekday() < 5
              and EPOCH + timedelta(days=k) != date(2019, 7, 4))
    assert ordinal == own == 29
    assert setup.track.cells[0] == CELL and setup.track.cell_slots == 3
    t = setup.thresholds
    assert t["coordinator.weak_window_days"] == 30
    assert t["validation.corr_max"] == 0.7
    assert t["gaps.max_fraction"] == 0.01
    assert t["budgets.worker_tokens_per_day"] == 60000
    assert t["budgets.worker_max_output_tokens"] == 8000


# ------------------------------------------------------------- a valid response (136 (i))


def test_a_day_with_a_valid_response_writes_one_trial_call_one_trial_and_its_lifecycle_row(
        valid_day, setup):
    state, provider, done = valid_day["state"], valid_day["provider"], valid_day["done"]
    assert done.status == journal.WRITTEN and done.commit
    assert provider.lists == 1 and len(provider.calls) == 1
    model, messages, max_tokens = provider.calls[0]
    assert (model, max_tokens) == (MODEL, 8000)
    assert done.brief is not None and done.brief.cell == CELL
    text = VALID[0].read_text(encoding="utf-8")
    want = {"call": call_id(D, 1), "date": D.isoformat(), "cell": CELL_NAME, "model": MODEL,
            "attempt": 1, "tokens_in": tokens(messages[0]["content"]),
            "tokens_out": tokens(text), "outcome": "trial",
            "response": f"responses/{TRACK}/{D.isoformat()}/{call_id(D, 1)}.json"}
    assert rows(state, ledger.CALLS) == [want]
    assert [dict(r) for r in done.calls] == [want]
    [trial] = rows(state, ledger.TRIALS)
    assert (trial["date"], trial["cell"], trial["model_id"], trial["model_version"],
            trial["cutoff"], trial["admitted"]) == (D.isoformat(), CELL_NAME, MODEL,
                                                    "scripted", "2026-02-28", True)
    [row] = [r for r in rows(state, ledger.LIFECYCLE) if r["date"] == D.isoformat()]
    assert (row["id"], row["from"], row["to"], row["reason"]) == (trial["id"], "candidate",
                                                                  "live", "admitted")
    assert done.admission is not None and done.admission.id == trial["id"]
    assert (state / "approaches" / trial["id"] / "meta.json").is_file()
    assert (state / f"responses/{TRACK}/{D.isoformat()}/{call_id(D, 1)}.json").is_file()
    assert not (state / STAGING).exists()
    # The pool's notices are in the health log, dated D.
    skipped = [(e["kind"], e["subject"]) for e in health(state) if e["date"] == D.isoformat()]
    assert skipped == [("model_skipped", m) for m in SKIPPED]


def test_a_rerun_of_the_journaled_day_writes_nothing_and_makes_no_provider_call(
        valid_day, config, tmp_path):
    state = copy_template(valid_day["state"], tmp_path / "state")
    before = files(state)
    done = run(state, config, provider=Refusing())
    assert done.status == journal.UNCHANGED and done.commit is None
    assert (done.statuses, done.brief, done.calls, done.events) == ((), None, (), ())
    assert files(state) == before


def test_a_day_failed_after_its_response_was_stored_runs_again_with_no_call_and_same_rows(
        valid_day, fresh, config, tmp_path, monkeypatch):
    state = fresh("failed")
    provider = Recording(ScriptedProvider(corpus(tmp_path / "corpus", VALID)))

    def fail(*args, **kwargs):
        raise RuntimeError("injected after the generation")

    monkeypatch.setattr(daily, "_rank_persistence", fail)
    with pytest.raises(RuntimeError, match="injected"):
        run(state, config, provider=provider)
    monkeypatch.undo()
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    assert len(provider.calls) == 1
    response = state / f"responses/{TRACK}/{D.isoformat()}/{call_id(D, 1)}.json"
    assert response.is_file()
    stored = response.read_bytes()
    # Nothing but the response and the health log survived the failed day.
    for name in (ledger.CALLS, ledger.TRIALS, ledger.LIFECYCLE):
        assert ledger_bytes(state, name) is None, name
    assert not journal.read_index(state, TRACK)
    assert not (state / STAGING).exists()
    again = run(state, config, provider=ListOnly([MODEL]))
    assert again.status == journal.WRITTEN
    assert response.read_bytes() == stored
    ref = valid_day["state"]
    for name in (ledger.CALLS, ledger.TRIALS, ledger.LIFECYCLE):
        assert ledger_bytes(state, name) == ledger_bytes(ref, name), name
    assert response.read_bytes() == \
        (ref / f"responses/{TRACK}/{D.isoformat()}/{call_id(D, 1)}.json").read_bytes()


def test_every_health_event_of_steps_3_to_5_is_logged_on_a_day_that_fails_after_them(
        fresh, config, tmp_path, monkeypatch):
    # budgets.worker_tokens_per_day 7999 on a copy under tmp: the first call's
    # check, 0 + 8000 > 7999, makes no call (DESIGN 13.7).
    low = changed_copy(config, tmp_path / "config", "thresholds.toml",
                       "worker_tokens_per_day = 60000", "worker_tokens_per_day = 7999 ")
    state = fresh("events")

    def fail(*args, **kwargs):
        raise RuntimeError("injected after the generation")

    monkeypatch.setattr(daily, "_rank_persistence", fail)
    with pytest.raises(RuntimeError, match="injected"):
        run(state, low, provider=ListOnly([MODEL]), coordinator=OutOfList())
    logged = [(e["date"], e["level"], e["kind"], e["subject"]) for e in health(state)]
    assert logged == [
        (D.isoformat(), "notice", "model_skipped", SKIPPED[0]),        # the pool's
        (D.isoformat(), "notice", "model_skipped", SKIPPED[1]),
        (D.isoformat(), "notice", "coordinator_fallback", "no_such_family/short"),
        (D.isoformat(), "alert", "token_budget", TRACK),               # the generation's
        # Decision 2026-10-19-m22 182 (c), (f): the retry's equal events are not appended
        # again, and its second failure appends run_failed.
        (D.isoformat(), "alert", "run_failed", TRACK),
    ]
    assert ledger_bytes(state, ledger.CALLS) is None


# ------------------------------------------------------------- no call (136 (a), (b), (i))


def test_a_day_with_data_gaps_makes_no_call(config, tmp_path):
    # SYNA's drop_fraction 0.05 (0.002 in the fixture record) on a configuration
    # copied under tmp, its bars fetched by the day's own step 1 into a state
    # directory init-state made at the same instant, so that W or T of D is
    # above gaps.max_fraction (0.01, unchanged).
    dropping = changed_copy(config, tmp_path / "config", "instruments/SYNA.toml",
                            "drop_fraction = 0.002\n", "drop_fraction = 0.05\n")
    state = tmp_path / "state"
    assert main(["init-state", "--state", str(state), "--as-of", INSTANT.isoformat()]) == 0
    done = run(state, dropping, provider=Refusing())
    assert done.status == journal.WRITTEN
    [gaps] = [e for e in done.events if e.kind == "data_gaps"]
    assert gaps.date == D and gaps.detail["over"]
    assert (done.statuses, done.brief, done.calls) == ((), None, ())
    assert ledger_bytes(state, ledger.CALLS) is None
    assert not (state / "responses").exists()


def test_a_day_with_no_offered_cell_makes_no_call(fresh, config, setup, tmp_path):
    # A track record copied under tmp with one cell (family trend, horizon short)
    # and one slot, held by a live approach that never went dormant: no free
    # slot, not weak, so no cell is offered.
    one = changed_copy(config, tmp_path / "config", f"tracks/{TRACK}.toml",
                       'families = ["trend", "mean_reversion", "breakout", "volatility_regime",\n'
                       '            "volume", "time_of_day"]\ncell_slots = 3\n',
                       'families = ["trend"]\ncell_slots = 1\n')
    text = (one / f"tracks/{TRACK}.toml").read_text(encoding="utf-8")
    (one / f"tracks/{TRACK}.toml").write_text(text.replace("medium = [6, 48]\n", ""),
                                              encoding="utf-8")
    narrow = journal.Setup.load(one, TRACK)
    assert narrow.track.cells == (CELL,) and narrow.track.cell_slots == 1
    state = fresh("no-offer")
    aid = admit_trend_ma(state, setup, date(2019, 7, 12))
    done = run(state, one, provider=Refusing())
    assert done.status == journal.WRITTEN
    assert done.statuses == (CellStatus(CELL, 1, 0, False),)
    assert (done.brief, done.calls) == (None, ())
    assert ledger_bytes(state, ledger.CALLS) is None
    assert aid in set(journal.read_day(state, TRACK, D)["subject"])


def test_a_day_whose_model_list_fails_makes_no_call_and_logs_model_list_failed(fresh, config):
    state = fresh("list-fails")
    done = run(state, config, provider=ListFails())
    assert done.status == journal.WRITTEN
    assert len(done.statuses) == 12 and all(s.free == 3 for s in done.statuses)
    assert (done.brief, done.calls) == (None, ())
    assert ledger_bytes(state, ledger.CALLS) is None
    logged = [(e["date"], e["level"], e["kind"], e["subject"]) for e in health(state)]
    assert logged == [(D.isoformat(), "notice", "model_list_failed", "pool")]


# ------------------------------------------------------------- the weak flag (136 (g))


def test_a_cell_whose_only_live_approach_goes_dormant_on_d_is_weak_from_the_next_day(
        fresh, config, setup, monkeypatch):
    state = fresh("weak-next")
    aid = admit_trend_ma(state, setup, date(2019, 7, 12))
    real = lifecycle.step_rows

    def dormant_on_d(setup_, day, rows_, approaches, paper, failures, **kw):
        out = real(setup_, day, rows_, approaches, paper, failures, **kw)
        if day == D:      # D's own lifecycle step writes the approach's row to dormant
            out.append({"date": D.isoformat(), "id": aid, "from": "live", "to": "dormant",
                        "reason": "dormant", "adjusted": -1.0, "plain": -1.0})
        return out

    monkeypatch.setattr(lifecycle, "step_rows", dormant_on_d)
    on_d = run(state, config, provider=ListFails())
    monkeypatch.setattr(lifecycle, "step_rows", real)
    assert [(r["date"], r["id"], r["to"]) for r in rows(state, ledger.LIFECYCLE)] == [
        (D.isoformat(), aid, "dormant")]
    assert on_d.statuses[0] == CellStatus(CELL, 1, 2, False)
    on_next = run(state, config, NEXT, provider=ListFails())
    assert on_next.statuses[0] == CellStatus(CELL, 0, 3, True)
    assert all(s.weak and s.live == 0 for s in on_next.statuses)


def test_a_row_to_dormant_before_the_first_paper_day_flags_the_cell_weak(
        fresh, config, setup):
    state = fresh("weak-day-0")
    aid = admit_trend_ma(state, setup, date(2019, 7, 12))
    # Rows written here (no lifecycle step writes them): to dormant and back to
    # live, both dated 2019-07-12, before its first paper day (the journal
    # starts on D, and an approach admitted later than the stored bars before D
    # cannot be journaled): the row to dormant is at paper day 0.
    ledger.append(state, TRACK, ledger.LIFECYCLE, [
        {"date": "2019-07-12", "id": aid, "from": "live", "to": "dormant",
         "reason": "dormant", "adjusted": -1.0, "plain": -1.0},
        {"date": "2019-07-12", "id": aid, "from": "dormant", "to": "live",
         "reason": "returned", "adjusted": 1.0, "plain": 1.0}])
    done = run(state, config, provider=ListFails())
    assert done.statuses[0] == CellStatus(CELL, 1, 2, True)
    assert all(s.weak for s in done.statuses)


# ------------------------------------------------------------- a duplicate retried (136 (h))


def test_a_duplicate_on_attempt_1_gives_attempt_2_the_whole_list_of_messages(
        fresh, config, setup, tmp_path):
    state = fresh("duplicate")
    aid = admit_trend_ma(state, setup, date(2019, 7, 12))
    provider = Recording(ScriptedProvider(corpus(tmp_path / "corpus",
                                                 DUPLICATE_THEN_INVALID)))
    done = run(state, config, provider=provider)
    # The cell with the fewest live approaches, the lowest index on a tie: the
    # second cell, trend/medium (trend/short holds the approach).
    assert done.brief is not None and done.brief.cell == ("trend", "medium")
    assert len(provider.calls) == 2
    first = provider.calls[0][1]
    assert [m["role"] for m in first] == ["user"]
    reply = DUPLICATE_THEN_INVALID[0].read_text(encoding="utf-8")
    error = (f"correlation [duplicate]: the position series on W has an absolute "
             f"correlation above corr_max with approach {aid} (corr_max = 0.7)")
    assert provider.calls[1][1] == [
        first[0],
        {"role": "assistant", "content": reply},
        {"role": "user", "content": gen.RETRY_TEXT + "\n\n" + error},
    ]
    assert [(r["attempt"], r["outcome"]) for r in rows(state, ledger.CALLS)] == [
        (1, "duplicate"), (2, "invalid:activity")]
    assert ledger_bytes(state, ledger.TRIALS) is None
