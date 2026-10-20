"""The ``--provider`` and ``--coordinator`` options of ``run-day`` and ``replay``,
and the scripted provider's cursor (decision 137 of
meta/decisions/decisions-2026-10-16-m17.md, amending decision 122 (b) of
decisions-2026-10-16-m15.md; DESIGN 13.5, 14.2, 16.4; I-6, I-12, I-13).

Every state directory is made under a pytest temporary directory by
``init-state`` at ``INIT_AS_OF`` and filled by the commands themselves, run
in-process through ``discotrade.cli.main``: the fixture track ``test_synth``
(four synthetic instruments, seeds ``SEEDS``, asserted against the fixture
records, bar length 3600 s, asserted) on ``tests/fixtures/config/`` copied
under tmp with the production ``config/thresholds.toml`` copied in unchanged.
The tests of a missing or refused ``models.toml`` copy that configuration again
under their own temporary directory and remove the file or replace its text
there, and say so. The replayed days are the four trading days ``DAYS``
(2019-07-15, a Monday, to 2019-07-18), the clock at each day's close (the
replay's clock, or ``--as-of`` for ``run-day``).

The worker provider is ``--provider scripted:<dir>`` over a corpus written by
the test under its temporary directory: one model's subdirectory,
``nvidia__nemotron-3-super-120b-a12b`` (so the pool is the fixture
``models.toml``'s third model alone; the other two are skipped with a notice
each day), whose ``0001.md`` is a copy of
``tests/fixtures/responses/duplicate_then_invalid/<model>/0001.md`` (its Python
block byte-identical to ``tests/fixtures/strategies/trend_ma_flipped.py``, as
tests/test_workers_generate.py asserts), and whose later files are prose with
no code block written here (each fails to parse, so the day retries once and no
source of them runs anywhere). The ``openai`` refusal runs with the key unset
or blank (``monkeypatch``) and a transport that fails the test if called; no
test builds that provider with a key. No socket, real provider, model or
``claude`` binary; no wall clock; no random draw beyond the synthetic sources'
fixed seeds. Every git run is on local paths with ``GIT_ALLOW_PROTOCOL=file``.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
from datetime import date
from pathlib import Path

import httpx
import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT

from discotrade import daily, journal, ledger, replay
from discotrade import state as state_mod
from discotrade.cli import main
from discotrade.config import load_track_config
from discotrade.workers import providers

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
#: The four trading days replayed, each with the close of its last bar (synth_week:
#: 17:00 New York, 21:00 UTC in July).
DAYS = [(date(2019, 7, 15), "2019-07-15T21:00:00+00:00"),
        (date(2019, 7, 16), "2019-07-16T21:00:00+00:00"),
        (date(2019, 7, 17), "2019-07-17T21:00:00+00:00"),
        (date(2019, 7, 18), "2019-07-18T21:00:00+00:00")]
FIRST, LAST = DAYS[0][0], DAYS[-1][0]
MODEL = "nvidia/nemotron-3-super-120b-a12b"
MODEL_DIR = "nvidia__nemotron-3-super-120b-a12b"
VALID = REPO_ROOT / "tests" / "fixtures" / "responses" / "duplicate_then_invalid" / \
    MODEL_DIR / "0001.md"
#: The corpus's files: the valid response, then prose that fails to parse.
CORPUS_FILES = 9


# ------------------------------------------------------------- helpers


def call(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:   # argparse's usage errors
            status = exc.code
    return status, out.getvalue(), err.getvalue()


def run_replay(state, config, first, last, *extra):
    return call("--state", str(state), "--config", str(config), "--track", TRACK,
                "replay", "--from", first.isoformat(), "--to", last.isoformat(), *extra)


def run_day(state, config, day, as_of, *extra):
    return call("--state", str(state), "--config", str(config), "--track", TRACK,
                "--as-of", as_of, "run-day", "--day", day.isoformat(), *extra)


def git(repo, *args) -> str:
    """A git command on the local state repository, through the state module's runner."""
    return state_mod._git(Path(repo), *args).stdout


def files(root, skip: tuple[str, ...] = ()) -> dict[str, bytes]:
    """Every file under ``root`` but ``.git/`` and the top directories ``skip``."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and ".git" not in rel.parts and rel.parts[0] not in skip:
            out[rel.as_posix()] = p.read_bytes()
    return out


def fresh(path: Path) -> Path:
    status, _, err = call("init-state", "--state", str(path), "--as-of", INIT_AS_OF)
    assert status == 0, err
    return path


def corpus(root: Path, valid: bool = True) -> Path:
    """The corpus under ``root``: ``CORPUS_FILES`` files of the one model."""
    folder = root / MODEL_DIR
    folder.mkdir(parents=True)
    for k in range(1, CORPUS_FILES + 1):
        if k == 1 and valid:
            shutil.copy(VALID, folder / "0001.md")
        else:
            (folder / f"{k:04d}.md").write_text(
                f"Response {k}: I would follow the trend, but I give no code here.\n",
                encoding="utf-8")
    return root


def served(state) -> list[tuple[str, str]]:
    """(model, corpus file) of every stored response, in call order."""
    out = []
    root = Path(state) / "responses" / TRACK
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in root.glob("*/*.json")]
    for doc in sorted(docs, key=lambda d: (d["date"], d["attempt"])):
        out.append((doc["model"], doc["raw"]["file"]))
    return out


def calls(state) -> list[dict]:
    return ledger.read(state, TRACK, ledger.CALLS)


def failing_transport(monkeypatch):
    def fail(request):
        pytest.fail(f"the transport was called: {request.method} {request.url}")

    monkeypatch.setattr(replay, "WORKERS_TRANSPORT", httpx.MockTransport(fail))


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
def scripted(tmp_path_factory):
    return "scripted:" + str(corpus(tmp_path_factory.mktemp("corpus")))


@pytest.fixture(scope="module")
def single(tmp_path_factory, config, scripted):
    """One replay over the four days with the scripted roles, counting the
    scripted providers built."""
    built = []

    class Counting(providers.ScriptedProvider):
        def __init__(self, *args, **kw):
            built.append((args, kw))
            super().__init__(*args, **kw)

    state = fresh(tmp_path_factory.mktemp("single") / "state")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        mp.setattr(providers, "ScriptedProvider", Counting)
        result = run_replay(state, config, FIRST, LAST, "--provider", scripted,
                            "--coordinator", "scripted")
    return {"state": state, "result": result, "built": built}


# ------------------------------------------------------------- the facts the tests stand on


def test_the_seeds_and_days_are_the_ones_written_here(config):
    tc = load_track_config(config, TRACK)
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS
    assert tc.track.bar_seconds == 3600
    setup = journal.Setup.load(config, TRACK)
    got = list(replay.replay_days(tc, dict(setup.calendars), FIRST, LAST))
    assert [(d, t.isoformat()) for d, t in got] == DAYS


# ------------------------------------------------------------- replays with the scripted roles


def test_a_scripted_replay_calls_the_provider_each_day(single):
    status, out, err = single["result"]
    assert status == 0, err
    assert len(out.splitlines()) == len(DAYS)
    rows = calls(single["state"])
    assert sorted({r["date"] for r in rows}) == [d.isoformat() for d, _ in DAYS]
    assert {r["model"] for r in rows} == {MODEL}
    # Day 1 is served the valid file; every later day parses nothing and retries once.
    assert served(single["state"]) == [(MODEL, f"{k:04d}.md") for k in range(1, 8)]


def test_the_provider_is_built_once_per_command(single):
    assert single["result"][0] == 0
    assert len(single["built"]) == 1


def test_two_replays_from_scratch_give_identical_states(tmp_path, config, scripted, single):
    state = fresh(tmp_path / "state")
    status, _, err = run_replay(state, config, FIRST, LAST, "--provider", scripted)
    assert status == 0, err
    one = single["state"]
    assert files(state) == files(one)
    assert git(state, "rev-parse", "HEAD^{tree}") == git(one, "rev-parse", "HEAD^{tree}")
    assert [e["content_hash"] for e in journal.read_index(state, TRACK)] == \
        [e["content_hash"] for e in journal.read_index(one, TRACK)]


def test_a_replay_in_two_calls_equals_one_call(tmp_path, config, scripted, single):
    state = fresh(tmp_path / "state")
    for first, last in ((DAYS[0][0], DAYS[1][0]), (DAYS[2][0], DAYS[3][0])):
        status, _, err = run_replay(state, config, first, last, "--provider", scripted)
        assert status == 0, err
    one = single["state"]
    assert len(set(served(state))) == len(served(state))
    assert served(state) == served(one)
    assert files(state) == files(one)
    assert git(state, "rev-parse", "HEAD^{tree}") == git(one, "rev-parse", "HEAD^{tree}")


def test_a_split_replay_after_a_day_failed_with_its_response_stored(tmp_path, config,
                                                                     scripted, single,
                                                                     monkeypatch):
    """The third day fails after its responses were stored (a failure of the
    rank-persistence step injected for that day, here), on both attempts of its
    command (decision 2026-10-19-m22 182 (a): a day is retried once in the same
    command); the second call over the last two days is run again. No corpus file
    is served twice, and every file but the health log (whose notices of the failed
    run stay, DESIGN 16.2) equals the one-call replay's, once that replay's health
    log holds the failed run's ``run_failed`` alert, which the re-run day's step 6
    reads (decision 182 (c), (f))."""
    bad = DAYS[2][0]
    real = daily._rank_persistence
    hit = []

    def failing(state_dir, setup, day, *rest):
        if day == bad and len(hit) < 2:
            hit.append(day)
            raise daily.DailyError("injected failure after the generation")
        return real(state_dir, setup, day, *rest)

    monkeypatch.setattr(daily, "_rank_persistence", failing)
    state = fresh(tmp_path / "state")
    status, _, err = run_replay(state, config, DAYS[0][0], DAYS[1][0], "--provider", scripted)
    assert status == 0, err
    status, _, err = run_replay(state, config, DAYS[2][0], DAYS[3][0], "--provider", scripted)
    assert status == 1 and "injected failure" in err
    assert hit == [bad, bad]
    # The failed day's two responses stay stored (DESIGN 16.2); its call rows do not.
    assert served(state)[-2:] == [(MODEL, "0004.md"), (MODEL, "0005.md")]
    assert {r["date"] for r in calls(state)} == {d.isoformat() for d, _ in DAYS[:2]}
    status, _, err = run_replay(state, config, DAYS[2][0], DAYS[3][0], "--provider", scripted)
    assert status == 0, err
    one = single["state"]
    assert len(set(served(state))) == len(served(state))
    assert served(state) == served(one)
    # The one-call replay's files, given the failed run's run_failed line before the
    # third day: the one-call replay of the first two days, the line, then the rest
    # (a split replay equals the one-call replay, as the test above shows).
    log = f"health/{TRACK}.jsonl"
    failed = [x for x in (state / log).read_text(encoding="utf-8").splitlines()
              if '"run_failed"' in x]
    assert len(failed) == 1
    ref = fresh(tmp_path / "ref")
    assert run_replay(ref, config, DAYS[0][0], DAYS[1][0], "--provider", scripted)[0] == 0
    (ref / log).parent.mkdir(exist_ok=True)
    with (ref / log).open("a", encoding="utf-8") as f:
        f.write(failed[0] + "\n")
    assert run_replay(ref, config, DAYS[2][0], DAYS[3][0], "--provider", scripted)[0] == 0
    assert served(ref) == served(one)
    assert files(state, skip=("health",)) == files(ref, skip=("health",))


def test_run_day_continues_the_cursor_from_the_stored_responses(tmp_path, config):
    """Two run-day commands, each building its provider: the second day is
    served the files after the first day's."""
    root = corpus(tmp_path / "prose", valid=False)
    state = fresh(tmp_path / "state")
    for d, as_of in DAYS[:2]:
        status, out, err = run_day(state, config, d, as_of, "--provider", f"scripted:{root}")
        assert status == 0, err
    assert served(state) == [(MODEL, f"{k:04d}.md") for k in range(1, 5)]
    assert [(r["date"], r["attempt"], r["outcome"]) for r in calls(state)] == [
        (d.isoformat(), a, "invalid:parse") for d, _ in DAYS[:2] for a in (1, 2)]


# ------------------------------------------------------------- usage errors and refusals


@pytest.fixture
def state(tmp_path):
    return fresh(tmp_path / "state")


def both(state, config, *extra):
    """Each command's result for ``extra``: replay over the span, run-day of day 1."""
    return {"replay": run_replay(state, config, FIRST, LAST, *extra),
            "run-day": run_day(state, config, *DAYS[0], *extra)}


def assert_refused(results, state, before, status, needle):
    for command, (got, out, err) in results.items():
        assert got == status, (command, err)
        assert out == "", command
        assert len(err.strip().splitlines()) == 1, (command, err)
        assert needle in err, (command, err)
    assert files(state) == before
    assert journal.read_index(state, TRACK) == []


def test_candidates_with_a_provider_is_a_usage_error(state, config, scripted, tmp_path):
    before = files(state)
    got, out, err = run_replay(state, config, FIRST, LAST, "--provider", scripted,
                               "--candidates", str(tmp_path / "candidates.jsonl"))
    assert_refused({"replay": (got, out, err)}, state, before, 2, "--candidates")


def test_a_missing_scripted_directory_is_refused(state, config, tmp_path):
    before = files(state)
    missing = tmp_path / "no-such-corpus"
    assert_refused(both(state, config, "--provider", f"scripted:{missing}"), state, before, 2,
                   str(missing))


@pytest.mark.parametrize("change", ["missing", "refused"])
def test_a_missing_or_refused_models_toml_is_refused(state, config, scripted, tmp_path,
                                                     change):
    """The configuration is copied again under tmp; its models.toml is removed
    (missing) or given one unknown key (refused)."""
    other = tmp_path / "config"
    shutil.copytree(config, other)
    path = other / "models.toml"
    if change == "missing":
        path.unlink()
    else:
        path.write_text(path.read_text(encoding="utf-8") + "\nunknown_key = 1\n",
                        encoding="utf-8")
    before = files(state)
    assert_refused(both(state, other, "--provider", scripted), state, before, 2,
                   "models.toml")


@pytest.mark.parametrize("key", ["unset", "spaces"])
def test_openai_without_a_usable_key_never_calls_the_transport(state, config, monkeypatch,
                                                               key):
    failing_transport(monkeypatch)
    if key == "unset":
        monkeypatch.delenv(providers.KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(providers.KEY_ENV, "   ")
    before = files(state)
    assert_refused(both(state, config, "--provider", "openai"), state, before, 1,
                   providers.KEY_ENV)


@pytest.mark.parametrize("value", ["bogus", "scripted:", "Scripted:x"])
def test_an_unknown_provider_is_a_usage_error(state, config, value):
    before = files(state)
    for command, (got, _, err) in both(state, config, "--provider", value).items():
        assert got == 2, (command, err)
        assert "--provider" in err
    assert files(state) == before


@pytest.mark.parametrize("value", ["bogus", "Claude", "scripted:"])
def test_an_unknown_coordinator_is_a_usage_error(state, config, value):
    """Each value is really unknown (decision 2026-10-19-m21 171 (a)): ``claude`` is a
    known coordinator since step S4.2, so it is not one of them."""
    before = files(state)
    for command, (got, _, err) in both(state, config, "--coordinator", value).items():
        assert got == 2, (command, err)
        assert "--coordinator" in err
    assert files(state) == before


def test_coordinator_claude_with_no_claude_on_path_resolves_none(state, config, monkeypatch,
                                                                 tmp_path):
    """Decision 2026-10-18-m20 163 (e), held whatever the environment holds (decision
    2026-10-19-m21 171 (b)): a dummy key set here, the fixture's ``binary = "claude"``
    and ``PATH`` an empty temporary directory. Each command is refused before any day
    with one line and exit 1, no file changes, every ``shutil.which`` made returns
    None, and no ``ClaudeCodeCoordinator`` is built."""
    from discotrade import coordinator as coord

    empty = tmp_path / "empty-path"
    empty.mkdir()
    monkeypatch.setenv(coord.KEY_ENV, "sk-test-not-a-key")
    monkeypatch.setenv("PATH", str(empty))
    real_which = shutil.which
    resolved = []

    def which(name, *args, **kw):
        got = real_which(name, *args, **kw)
        resolved.append((name, got))
        return got

    def built(*args, **kw):
        pytest.fail("a ClaudeCodeCoordinator was built")

    monkeypatch.setattr(shutil, "which", which)
    monkeypatch.setattr(coord, "ClaudeCodeCoordinator", built)
    assert load_run_binary(config) == "claude"
    before = files(state)
    results = both(state, config, "--coordinator", "claude")
    assert_refused(results, state, before, 1, "not found on PATH")
    for command, (_, _, err) in results.items():
        assert "sk-test-not-a-key" not in err, command
    assert resolved == [("claude", None)] * 2


def load_run_binary(config) -> str:
    from discotrade.config import load_run

    return load_run(Path(config)).coordinator.binary
