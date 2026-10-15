"""The rejection suite (DESIGN 12.5, 12.1, 12.2, 12.4; decision 104 (a), (b) and
(d) of 2026-10-14-m13 as the owner's O-22 of 2026-10-15 narrows it, 104 (c)
dropped; decisions 94, 98, 101 (f), 102; I-7, I-14).

``tests/fixtures/rejected/manifest.toml`` names, per entry of DESIGN 12.5's list
(:data:`ENTRIES`, held here as a literal) and REVIEW-12's two
(:data:`REVIEW_12`), one validation fixture: its file, the entry it covers, the
stage of DESIGN 12.2 that rejects it and, for the static stage, the rule of
12.1. A static-stage fixture is the smallest text that trips its rule and is
refused before it runs; a run-time fixture (``dry_run``, ``determinism``,
``activity``) is a text of ``tests/fixtures/strategies/`` where one exists, else
the smallest text whose result the stage refuses.

The rejection pass (104 (b)): each fixture through the whole validation
sequence (``validation.sequence.validate``) on the container backend, on
``test_synth``'s own W of ``DAY`` (2019-06-11 to 2019-07-08) at the production
thresholds of ``config/thresholds.toml`` and the limits of
``tests/fixtures/config/run.toml``, except the two entries of
:data:`SHORTER`, whose ``run.toml``, copied under the temporary directory,
holds a shorter wall-clock limit (the endless loop) or memory limit (the memory
bomb). Each is rejected at its manifest stage with an error text that passes
decision 101 (f)'s check; the state directory's bytes and ``HEAD`` are
unchanged; no ledger or ``trials/`` file is created; a sentinel tree outside the
job directories is unchanged; no container of the suite remains; and, after the
suite, the same process validates a valid fixture (``changes_30.py``) to a pass.

The state directory is made by ``init-state`` and filled by ``bars fetch`` run
in-process (``discotrade.cli.main``) with ``--as-of`` ``AS_OF``, committed with
``state.commit`` under a ``FixedClock``, all under a pytest temporary directory;
every git that runs is on local paths with ``GIT_ALLOW_PROTOCOL=file``
(decision 47). Seeds: the synthetic bars come from the fixture records' seeds,
written here (``SEEDS``) and checked against them. No random draw is made here
except the reverse sample's, whose seed is the text's own (decision 98 (a)).
"""

import shutil
import threading
import tomllib
from datetime import UTC, date, datetime

import pytest
from error_texts import assert_clean, forbidden_words

from discotrade import state as state_mod
from discotrade.cli import REPO_ROOT, main
from discotrade.clock import FixedClock
from discotrade.journal import Setup
from discotrade.ledger import LEDGER_DIR
from discotrade.sandbox import container
from discotrade.sandbox.container import ContainerSandbox
from discotrade.validation import sequence, static
from discotrade.validation.sequence import Context

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
REJECTED = REPO_ROOT / "tests" / "fixtures" / "rejected"
STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
MANIFEST = REJECTED / "manifest.toml"
VALID = STRATEGIES / "changes_30.py"
TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
#: The day D (a Monday): W is 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
AS_OF = "2019-07-25T00:00:00+00:00"
COMMIT_CLOCK = FixedClock(datetime(2019, 7, 25, tzinfo=UTC))
#: The bound on one validation that could hang (seconds of the test's own timeout).
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
#: The stages a manifest entry may name (decision 98 (d)), and the run-time ones.
RUN_TIME = ("dry_run", "determinism", "activity")
FIELDS = {"file", "entry", "stage", "rule"}
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


def by_entry() -> dict[str, dict]:
    return {e["entry"]: e for e in manifest()}


def text(entry: dict) -> str:
    return (REPO_ROOT / entry["file"]).read_text(encoding="utf-8")


def tree(path) -> dict:
    """Every file's bytes under ``path``, ``.git`` included."""
    return {str(p.relative_to(path)): p.read_bytes()
            for p in sorted(path.rglob("*")) if p.is_file()}


def head(path) -> bytes:
    ref = (path / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    assert ref.startswith("ref: ")
    return (path / ".git" / ref[len("ref: "):]).read_bytes()


def copy_config(root, **values):
    """``tests/fixtures/config/`` copied to ``root`` with ``config/thresholds.toml``
    (the production thresholds); ``[sandbox]`` values replaced by ``values``."""
    path = root / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    if values:
        with open(FIXTURE_CONFIG / "run.toml", "rb") as f:
            sandbox = tomllib.load(f)["sandbox"]
        sandbox.update(values)
        (path / "run.toml").write_text(
            "[sandbox]\n" + "".join(f"{k} = {v!r}\n" for k, v in sandbox.items()),
            encoding="utf-8")
    return path


def bounded(fn):
    """``fn()``'s value, run in a daemon thread joined for at most ``BOUND`` seconds."""
    box = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - handed back to the test
            box["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(BOUND)
    assert not thread.is_alive(), f"the validation did not return within {BOUND} s"
    if "error" in box:
        raise box["error"]
    return box["value"]


# ------------------------------------------------------------- the manifest (no container)


def test_the_manifest_has_one_file_per_entry_of_the_list_and_review_12s_two():
    entries = [e["entry"] for e in manifest()]
    assert len(entries) == len(set(entries)), "an entry is named twice"
    assert set(entries) == set(ALL), (sorted(set(ALL) - set(entries)),
                                      sorted(set(entries) - set(ALL)))
    files = [e["file"] for e in manifest()]
    assert len(files) == len(set(files)), "a file covers two entries"


def test_each_manifest_entry_names_a_file_a_stage_and_for_static_a_rule_and_no_more():
    for e in manifest():
        assert set(e) <= FIELDS and {"file", "entry", "stage"} <= set(e), e
        assert "containment" not in e, e  # 104 (c) is dropped (O-22 item 1)
        assert (REPO_ROOT / e["file"]).is_file(), e
        assert e["stage"] in ("static", *RUN_TIME), e
        if e["stage"] == "static":
            assert e["rule"] in static.RULES, e
            assert (REPO_ROOT / e["file"]).parent == REJECTED, e
        else:
            assert "rule" not in e, e
            assert (REPO_ROOT / e["file"]).parent in (REJECTED, STRATEGIES), e


def test_every_text_under_the_suite_directory_is_named_by_the_manifest():
    named = {(REPO_ROOT / e["file"]).resolve() for e in manifest()}
    texts = {p.resolve() for p in REJECTED.glob("*.py")}
    assert texts <= named, sorted(str(p) for p in texts - named)


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory.mktemp("cfg"))


@pytest.fixture(scope="module")
def setup(config):
    return Setup.load(config, TRACK)


def test_the_production_thresholds_are_the_ones_the_suite_is_written_for(setup):
    t = setup.thresholds
    assert (t["validation.max_lines"], t["validation.max_params"]) == (60, 5)
    assert (t["validation.call_p95_ms"], t["validation.call_max_ms"]) == (50, 500)
    assert t["validation.min_changes_w"] == 30


def test_each_static_text_is_refused_at_its_rule_and_each_run_time_text_passes_the_check(
        setup):
    for e in manifest():
        refusal = static.check(text(e), setup.thresholds)
        if e["stage"] == "static":
            assert refusal is not None and refusal.rule == e["rule"], (e, refusal)
        else:
            assert refusal is None, (e, refusal)


# ------------------------------------------------------------- the rejection pass (container)


@pytest.fixture(scope="module")
def synth_state(tmp_path_factory, config):
    """A state directory with ``test_synth``'s bars and no approach, committed."""
    path = tmp_path_factory.mktemp("synth") / "state"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        assert main(["init-state", "--state", str(path), "--as-of", AS_OF]) == 0
        assert main(["--state", str(path), "--config", str(config), "--track", TRACK,
                     "--as-of", AS_OF, "bars", "fetch"]) == 0
        state_mod.commit(path, TRACK, DAY, COMMIT_CLOCK)
    return path


def test_the_synthetic_seeds_are_the_ones_written_here(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS


def ledger_and_trials(path) -> list[str]:
    """Every ledger file and every file under a ``trials`` directory of ``path``."""
    return sorted(str(p.relative_to(path)) for p in path.rglob("*")
                  if p.is_file() and (LEDGER_DIR in p.relative_to(path).parts[:1]
                                      or state_mod.TRIALS in p.relative_to(path).parts))


@pytest.fixture(scope="module")
def rejection_pass(tmp_path_factory, config, setup, synth_state):
    """Every manifest entry through the whole sequence on the container backend, then
    the valid fixture; what the state, the sentinel tree and the runtime held
    before and after. Any container a backend left is removed by name after."""
    root = tmp_path_factory.mktemp("pass")
    sentinel = root / "sentinel"
    (sentinel / "deep").mkdir(parents=True)
    (sentinel / "note.txt").write_text("a sentinel outside every job directory\n",
                                       encoding="utf-8")
    (sentinel / "deep" / "data.bin").write_bytes(bytes(range(256)))
    before = {"state": tree(synth_state), "head": head(synth_state),
              "ledger": ledger_and_trials(synth_state), "sentinel": tree(sentinel)}
    backends: list[ContainerSandbox] = []
    outcomes: dict[str, sequence.Outcome] = {}
    try:
        for k, e in enumerate(manifest()):
            cfg = (copy_config(root / f"cfg-{k}", **SHORTER[e["entry"]])
                   if e["entry"] in SHORTER else config)
            b = ContainerSandbox(root / f"scratch-{k}", cfg)
            backends.append(b)
            ctx = Context(synth_state, cfg, setup, DAY, b)
            outcomes[e["entry"]] = bounded(lambda ctx=ctx, e=e: sequence.validate(ctx, text(e)))
        b = ContainerSandbox(root / "scratch-valid", config)
        backends.append(b)
        ctx = Context(synth_state, config, setup, DAY, b)
        valid = bounded(lambda: sequence.validate(ctx, VALID.read_text(encoding="utf-8")))
        after = {"state": tree(synth_state), "head": head(synth_state),
                 "ledger": ledger_and_trials(synth_state), "sentinel": tree(sentinel)}
        left = [n for b in backends for n in b.started
                if container.container_exists(b.runtime(), n)]
    finally:
        for b in backends:
            for name in b.started:
                if container.container_exists(b.runtime(), name):
                    container.remove(b.runtime(), name)
    return {"outcomes": outcomes, "valid": valid, "before": before, "after": after,
            "left": left, "started": [n for b in backends for n in b.started]}


@pytest.mark.container
@pytest.mark.parametrize("entry", ALL)
def test_each_entry_is_rejected_at_its_manifest_stage(rejection_pass, entry):
    e = by_entry()[entry]
    out = rejection_pass["outcomes"][entry]
    assert not out.ok, f"{entry}: {e['file']} passed every stage"
    assert out.stage == e["stage"], (entry, e["file"], out.stage, out.rule, out.text)
    if e["stage"] == "static":
        assert out.rule == e["rule"], (entry, out.rule, out.text)


@pytest.mark.container
def test_every_error_text_of_the_pass_passes_decision_101_f(rejection_pass, synth_state):
    assert_clean([out.text for out in rejection_pass["outcomes"].values()],
                 forbidden_words(synth_state, TRACK, SEEDS))


@pytest.mark.container
def test_the_state_directory_and_head_are_unchanged_and_no_ledger_or_trial_is_written(
        rejection_pass):
    before, after = rejection_pass["before"], rejection_pass["after"]
    assert after["head"] == before["head"]
    assert after["state"] == before["state"]
    assert after["ledger"] == before["ledger"] == []


@pytest.mark.container
def test_the_sentinel_tree_is_unchanged(rejection_pass):
    assert rejection_pass["after"]["sentinel"] == rejection_pass["before"]["sentinel"]
    assert len(rejection_pass["before"]["sentinel"]) == 2


@pytest.mark.container
def test_no_container_of_the_suite_remains(rejection_pass):
    assert rejection_pass["started"], "the suite started no container"
    assert rejection_pass["left"] == []


@pytest.mark.container
def test_after_the_suite_the_same_process_validates_a_valid_fixture_to_a_pass(rejection_pass):
    valid = rejection_pass["valid"]
    assert valid.ok and valid.stage is None, valid.text
