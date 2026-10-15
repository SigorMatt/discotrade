"""Gate item G2.1: every text of the rejection suite is rejected at its documented
stage, with the container backend really running, and none produces a trial, a
file outside its scratch space, or a harness failure (DESIGN 18.3 G2.1, 12.5,
12.2; O-22 item 2 of meta/decisions/decisions-2026-10-15-owner.md, which wins
over decision 104 and 106 (b) of 2026-10-14-m13; decisions 104 (a), (b), 101 (f),
106 (a); I-5, I-7, I-14).

As O-22 item 2 states it: the rejection pass of decision 104 (b) over the whole
manifest ``tests/fixtures/rejected/manifest.toml``, against DESIGN 12.5's list held
here as a literal (:data:`ENTRIES`, split as decision 104 (a) splits it, plus
REVIEW-12's two, :data:`REVIEW_12`). Each manifest text goes through the whole
validation sequence (``validation.sequence.validate``) on the container backend,
on ``test_synth``'s own W of ``DAY`` (2019-06-11 to 2019-07-08), at the production
thresholds of ``config/thresholds.toml`` and the limits of
``tests/fixtures/config/run.toml``, except the entries of :data:`SHORTER`, whose
``run.toml``, copied under the temporary directory, holds a shorter limit, said
there. Each is rejected at its manifest stage (and, for the static stage, its
rule), with an error text that passes decision 101 (f)'s check; a static-stage
text starts no container and every run-time-stage text starts at least one
(the backend really ran). Over the pass: the state directory's bytes and
``HEAD`` are unchanged, no ledger or ``trials/`` file exists (no trial), a
sentinel tree outside the job directories is unchanged, no container of the
pass remains, and afterwards the same process validates a valid fixture
(``changes_30.py``) to a pass on the container backend (no harness failure:
any exception a validation raised would fail the pass's fixture).

Seeds: the synthetic bars come from the fixture records' seeds, written here
(``SEEDS``) and checked against them. No random draw is made here except the
reverse sample's, whose seed is the text's own (decision 98 (a)). Time is read
only through ``--as-of`` (``AS_OF``) and the ``FixedClock`` of the commit.
"""

import tomllib
from datetime import UTC, date, datetime

import pytest
from error_texts import assert_clean, forbidden_words
from m2_harness import (
    REJECTED,
    STRATEGIES,
    Backends,
    bars_state,
    bounded,
    copy_config,
    head,
    ledger_and_trials,
    tree,
)

from discotrade.cli import REPO_ROOT
from discotrade.clock import FixedClock
from discotrade.journal import Setup
from discotrade.validation import sequence, static
from discotrade.validation.sequence import Context

pytestmark = [pytest.mark.gate, pytest.mark.gate_m2, pytest.mark.container]

MANIFEST = REJECTED / "manifest.toml"
VALID = STRATEGIES / "changes_30.py"
TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
#: The day D (a Monday): W is 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
W_FIRST, W_LAST = date(2019, 6, 11), date(2019, 7, 8)
AS_OF = "2019-07-25T00:00:00+00:00"
COMMIT_CLOCK = FixedClock(datetime(2019, 7, 25, tzinfo=UTC))
#: The bound on one validation (seconds): a hang fails the item instead of the call.
BOUND = 300.0

#: DESIGN 12.5's list, one entry per item as decision 104 (a) splits it.
ENTRIES = (
    "network access",
    "writing a file",
    "reading a file outside the mount",
    "reading the mounted bars directly",
    "a fork bomb",
    "an endless loop",
    "a memory bomb",
    "forbidden imports",
    "__import__",
    "an attribute walk from a literal to object",
    "eval",
    "exec",
    "state kept between calls by a module-level cache",
    "state kept between calls by a mutable default argument",
    "randomness",
    "the clock",
    "too many lines",
    "too many parameters",
    "a non-numeric parameter",
    "a result that is not a number",
    "a result that is not finite",
    "a result out of range",
    "a huge output",
    "changing bars in place",
    "the IO functions of numpy",
    "the IO functions of pandas",
    "a slow function",
)
#: REVIEW-12's two (decision 104 (a)).
REVIEW_12 = (
    "a class named from the data",
    "a forged result written to descriptor 1",
)
ALL = ENTRIES + REVIEW_12
#: The stages of decision 98 (d) a text may be rejected at, and the run-time ones.
STAGES = ("static", "dry_run", "determinism", "activity", "correlation")
RUN_TIME = ("dry_run", "determinism", "activity")
#: The entries run under a shorter limit, from a run.toml copied under tmp: the
#: endless loop ends at a 10-second wall-clock limit (its CPU-time limit far above
#: it, so that the harness's kill ends it), the memory bomb at a 256 MiB memory
#: limit. Every other entry runs under tests/fixtures/config/run.toml's limits.
SHORTER = {
    "an endless loop": {"wall_seconds": 10.0, "cpu_seconds": 600.0},
    "a memory bomb": {"memory_bytes": 256 * 1024 * 1024},
}


def manifest() -> list[dict]:
    with open(MANIFEST, "rb") as f:
        return tomllib.load(f)["entry"]


def text(entry: dict) -> str:
    return (REPO_ROOT / entry["file"]).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory.mktemp("cfg"))


@pytest.fixture(scope="module")
def setup(config):
    return Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def synth_state(tmp_path_factory, config):
    """A state directory with ``test_synth``'s bars and no approach, committed."""
    return bars_state(tmp_path_factory.mktemp("synth") / "state", config, TRACK, AS_OF, DAY,
                      COMMIT_CLOCK)


@pytest.fixture(scope="module")
def rejection_pass(tmp_path_factory, config, setup, synth_state):
    """Every manifest text through the whole sequence on the container backend, one
    backend per text, then the valid fixture; what the state, the sentinel tree and
    the runtime held before and after. A container left is removed by name after."""
    root = tmp_path_factory.mktemp("pass")
    sentinel = root / "sentinel"
    (sentinel / "deep").mkdir(parents=True)
    (sentinel / "note.txt").write_text("a sentinel outside every job directory\n",
                                       encoding="utf-8")
    (sentinel / "deep" / "data.bin").write_bytes(bytes(range(256)))
    before = {"state": tree(synth_state), "head": head(synth_state),
              "ledger": ledger_and_trials(synth_state), "sentinel": tree(sentinel)}
    backends = Backends(root / "jobs")
    outcomes, started = {}, {}
    try:
        for k, e in enumerate(manifest()):
            cfg = (copy_config(root / f"cfg-{k}", **SHORTER[e["entry"]])
                   if e["entry"] in SHORTER else config)
            b = backends.make(cfg)
            ctx = Context(synth_state, cfg, setup, DAY, b)
            outcomes[e["entry"]] = bounded(lambda ctx=ctx, e=e: sequence.validate(ctx, text(e)),
                                           BOUND)
            started[e["entry"]] = list(b.started)
        b = backends.make(config)
        ctx = Context(synth_state, config, setup, DAY, b)
        valid = bounded(lambda: sequence.validate(ctx, VALID.read_text(encoding="utf-8")),
                        BOUND)
        valid_started = list(b.started)
        after = {"state": tree(synth_state), "head": head(synth_state),
                 "ledger": ledger_and_trials(synth_state), "sentinel": tree(sentinel)}
        left = backends.left()
    finally:
        backends.remove_left()
    return {"outcomes": outcomes, "started": started, "valid": valid,
            "valid_started": valid_started, "before": before, "after": after, "left": left,
            "all_started": backends.started}


def test_the_facts_written_here(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    w = setup.track.windows(DAY).w
    assert (w.first, w.last) == (W_FIRST, W_LAST)
    production = tomllib.loads((REPO_ROOT / "config" / "thresholds.toml").read_text("utf-8"))
    for key in ("max_lines", "max_params", "call_p95_ms", "call_max_ms", "min_changes_w",
                "corr_max"):
        assert setup.thresholds[f"validation.{key}"] == production["validation"][key], key


def test_the_manifest_covers_exactly_the_list_one_file_each_at_a_stage_of_the_sequence():
    entries = manifest()
    named = [e["entry"] for e in entries]
    assert len(named) == len(set(named)), "an entry is named twice"
    assert set(named) == set(ALL), (sorted(set(ALL) - set(named)), sorted(set(named) - set(ALL)))
    files = [e["file"] for e in entries]
    assert len(files) == len(set(files)), "a file covers two entries"
    for e in entries:
        assert (REPO_ROOT / e["file"]).is_file(), e
        assert e["stage"] in STAGES, e
        if e["stage"] == "static":
            assert e["rule"] in static.RULES, e


@pytest.mark.parametrize("entry", ALL)
def test_each_text_is_rejected_at_its_manifest_stage_on_the_container_backend(
        rejection_pass, entry):
    e = {x["entry"]: x for x in manifest()}[entry]
    out = rejection_pass["outcomes"][entry]
    assert not out.ok, f"{entry}: {e['file']} passed every stage"
    assert out.stage == e["stage"], (entry, e["file"], out.stage, out.rule, out.text)
    if e["stage"] == "static":
        assert out.rule == e["rule"], (entry, out.rule, out.text)
        # Refused before it ran: no container was started for it.
        assert rejection_pass["started"][entry] == [], entry
    else:
        assert e["stage"] in RUN_TIME, e
        # The container backend really ran it.
        assert rejection_pass["started"][entry], entry


def test_every_error_text_of_the_pass_passes_decision_101_f(rejection_pass, synth_state):
    texts = [out.text for out in rejection_pass["outcomes"].values()]
    assert len(texts) == len(ALL) and all(texts)
    assert_clean(texts, forbidden_words(synth_state, TRACK, SEEDS))


def test_the_state_directory_and_head_are_unchanged_and_no_trial_or_ledger_exists(
        rejection_pass):
    before, after = rejection_pass["before"], rejection_pass["after"]
    assert after["head"] == before["head"]
    assert after["state"] == before["state"]
    assert after["ledger"] == before["ledger"] == []


def test_the_sentinel_tree_outside_the_job_directories_is_unchanged(rejection_pass):
    assert len(rejection_pass["before"]["sentinel"]) == 2
    assert rejection_pass["after"]["sentinel"] == rejection_pass["before"]["sentinel"]


def test_no_container_of_the_pass_remains(rejection_pass):
    assert rejection_pass["all_started"], "the pass started no container"
    assert rejection_pass["left"] == []


def test_afterwards_the_same_process_validates_a_valid_fixture_to_a_pass(rejection_pass):
    valid = rejection_pass["valid"]
    assert valid.ok and valid.stage is None, valid.text
    assert rejection_pass["valid_started"], "the valid fixture ran in no container"
