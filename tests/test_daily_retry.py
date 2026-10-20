"""The retry of a failed day, ``run_retried`` and ``run_failed`` (decision 182 of
meta/decisions/decisions-2026-10-19-m22.md; DESIGN 16.1, 16.2, 15.2; SPEC §11;
REVIEW-17 notes 3 and 4, REVIEW-19 notes 4 and 6; I-5, I-6).

A day whose steps raise is retried once, inside the run lock, from a clean
staging directory. A first failure the retry repairs appends one ``run_retried``
notice and the day is committed once; a second failure leaves every state file
but the health log and the stored responses as it was, appends one ``run_failed``
alert, opens one issue through the command's sink and re-raises, so that the
command exits 1.

Most tests run ``run-day`` in-process through ``discotrade.cli.main`` on a copy of
conftest's ``mixed_ran_template`` (track ``test_mixed``, ``RAN_DAYS`` run at
``RAN_AS_OF``), for ``NEXT`` 2019-06-13, under a pytest temporary directory. The
tests with a worker provider call ``daily.run_day`` on a copy of conftest's
``synth_committed_template`` (track ``test_synth``) for ``SYNTH_DAY`` with the clock
at ``SYNTH_AS_OF``, the provider ``ScriptedProvider`` over a corpus of one fixture
response (tests/test_daily_generation.py's helpers). Every failure is injected by
the test with ``monkeypatch`` of one step's function (decision 182 (e)); no strategy
is written for the purpose. The call-limit test (REVIEW-17 note 3's second half) is
marked ``container``: it runs the fixture ``tests/fixtures/rejected/slow_function.py``
(unchanged; its first call after each load takes longer than ``call_max_ms``) as the
day's candidate, scored on T in the container backend, the only backend that
enforces the call limits; the generation is replaced (``monkeypatch``) so that the
candidate reaches T without its W validation, which that fixture would fail.

Issues go to a ``FileIssueSink`` directory under tmp. The synthetic sources' seeds are
their fixture records'; no other random draw is made. Time comes only from
``--as-of`` or the test's ``FixedClock``. Every git is on local paths with
``GIT_ALLOW_PROTOCOL=file`` (decision 47). No socket, key, real model, ``claude`` or
``gh``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from conftest import (
    FIXTURE_CONFIG,
    RAN_AS_OF,
    REPO_ROOT,
    SYNTH_AS_OF,
    SYNTH_DAY,
    copy_template,
)
from test_daily_generation import MODEL, VALID, ListOnly, Recording, corpus

from discotrade import alerts, daily, journal, table
from discotrade.cli import main
from discotrade.clock import FixedClock
from discotrade.sandbox import container
from discotrade.sandbox.container import ContainerSandbox
from discotrade.state import LOCK, STAGING
from discotrade.workers import generate as gen
from discotrade.workers.providers import ScriptedProvider

TRACK = "test_mixed"
SYNTH = "test_synth"
NEXT = date(2019, 6, 13)
INSTANT = datetime(2019, 7, 25, tzinfo=UTC)
#: What a failed day may change (DESIGN 16.2): the health log and the stored responses.
SURVIVORS = ("health", "responses")
#: The rejection suite's slow function (its docstring): its first call after each load
#: takes longer than ``validation.call_max_ms``.
SLOW = REPO_ROOT / "tests" / "fixtures" / "rejected" / "slow_function.py"


# ------------------------------------------------------------- helpers


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def commits(state: Path) -> list[str]:
    return git(state, "log", "--format=%s").splitlines()


def tree(root: Path, skip: tuple[str, ...] = ()) -> dict[str, bytes]:
    """The bytes of every file under ``root``, ``.git/`` and the top directories
    ``skip`` left out."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and p.relative_to(root).parts[0] not in (".git", *skip)}


def health_lines(state: Path, track: str = TRACK) -> list[str]:
    path = state / "health" / f"{track}.jsonl"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def of_kind(state: Path, kind: str, track: str = TRACK) -> list[dict]:
    return [e for e in map(json.loads, health_lines(state, track)) if e["kind"] == kind]


def run(state: Path, config: Path, *extra: str) -> int:
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", RAN_AS_OF, "run-day", "--day", NEXT.isoformat(), *extra])


def fail(monkeypatch, owner, name: str, times: int, error=daily.DailyError) -> list[int]:
    """Replace ``owner.name`` by a function that raises ``error("injected failure <n>")``
    on its first ``times`` calls and calls the real one after; return the call list."""
    real = getattr(owner, name)
    calls: list[int] = []

    def failing(*args, **kwargs):
        calls.append(1)
        if len(calls) <= times:
            raise error(f"injected failure {len(calls)}")
        return real(*args, **kwargs)

    monkeypatch.setattr(owner, name, failing)
    return calls


def issue_text(title: str, labels: str, body: str) -> str:
    """A ``FileIssueSink`` file, as tests/test_digest.py reads one (decision 178 (a))."""
    return f"title: {title}\nlabels: {labels}\n\n{body}\n"


# ------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _git_local(monkeypatch):
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("rcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def ran(tmp_path_factory, mixed_ran_template):
    return copy_template(mixed_ran_template, tmp_path_factory.mktemp("rran") / "state")


@pytest.fixture
def state(tmp_path, ran):
    return copy_template(ran, tmp_path / "state")


# ------------------------------------------------------------- 182 (c), (g): two failures

#: The injected failures of a day that fails twice: a step's own error, and
#: ``alerts.group_edge``'s ``ValueError`` when ``portfolio_clean``'s dates and the clean
#: members disagree (REVIEW-19 note 4; decision 182 (e)), each on both attempts.
TWICE = {
    "table.build": (table, "build", daily.DailyError, "DailyError"),
    "alerts.group_edge": (alerts, "group_edge", ValueError, "ValueError"),
}


@pytest.mark.parametrize("where", sorted(TWICE))
def test_a_day_failing_twice_leaves_the_state_records_run_failed_opens_its_issue_exits_1(
        tmp_path, state, config, monkeypatch, capsys, where):
    owner, name, error, type_name = TWICE[where]
    before, head, log = tree(state, SURVIVORS), commits(state), health_lines(state)
    issues = tmp_path / "issues"
    calls = fail(monkeypatch, owner, name, times=2, error=error)
    assert run(state, config, "--issues", f"file:{issues}") == 1
    err = capsys.readouterr().err
    assert len(calls) == 2                       # the day ran twice, in one command
    assert "injected failure 2" in err
    # Every file but the health log and the stored responses is as it was.
    assert tree(state, SURVIVORS) == before
    assert commits(state) == head
    assert not (state / LOCK).exists() and not (state / STAGING).exists()
    assert journal.read_day(state, TRACK, NEXT) is None
    # One run_failed alert with both errors; no run_retried.
    first, second = f"{type_name}: injected failure 1", f"{type_name}: injected failure 2"
    assert of_kind(state, daily.RUN_FAILED) == [{
        "date": NEXT.isoformat(), "level": "alert", "kind": "run_failed", "subject": TRACK,
        "detail": {"day": NEXT.isoformat(), "first": first, "second": second}}]
    assert of_kind(state, daily.RUN_RETRIED) == []
    assert health_lines(state)[:len(log)] == log           # appended only (I-5)
    # One issue through the command's sink.
    folder = issues / TRACK
    assert sorted(p.name for p in folder.iterdir()) == ["0001.md"]
    body = (f"{NEXT.isoformat()} of {TRACK} failed twice.\n\n"
            f"First attempt: {first}\n\nSecond attempt: {second}")
    assert (folder / "0001.md").read_text(encoding="utf-8") == issue_text(
        f"run_failed {TRACK} {NEXT.isoformat()}", "discotrade, health, run_failed", body)


def test_a_day_failing_twice_on_the_day_function_re_raises_the_second_error(
        state, config, monkeypatch):
    fail(monkeypatch, table, "build", times=2)
    clock = FixedClock(datetime.fromisoformat(RAN_AS_OF))
    with pytest.raises(daily.DailyError, match="injected failure 2"):
        daily.run_day(state, config, TRACK, clock, NEXT)
    assert len(of_kind(state, daily.RUN_FAILED)) == 1


# ------------------------------------------------------------- 182 (b), (g): one failure


#: Where a day fails once: in step 6's table, or at the move into place, when steps 1 to
#: 7 have all staged their files (the run log line among them).
ONCE = {"table.build": (table, "build"), "daily._move": (daily, "_move")}


@pytest.mark.parametrize("where", sorted(ONCE))
def test_a_day_failing_once_is_committed_once_with_run_retried_and_equals_a_clean_run(
        tmp_path, state, ran, config, monkeypatch, capsys, where):
    head, log = commits(state), health_lines(state)
    calls = fail(monkeypatch, *ONCE[where], times=1)
    assert run(state, config) == 0
    out = capsys.readouterr().out
    assert len(calls) == 2
    assert commits(state) == [f"run {TRACK} {NEXT.isoformat()}", *head]
    assert git(state, "status", "--porcelain") == ""      # run_retried is committed
    retried = {"date": NEXT.isoformat(), "level": "notice", "kind": "run_retried",
               "subject": TRACK,
               "detail": {"day": NEXT.isoformat(), "error": "DailyError: injected failure 1"}}
    assert of_kind(state, daily.RUN_RETRIED) == [retried]
    assert of_kind(state, daily.RUN_FAILED) == []
    assert f"notice {json.dumps(retried, sort_keys=True)}" in out.splitlines()
    assert health_lines(state)[:len(log)] == log
    # A run that never failed writes the same files, the run_retried line aside.
    monkeypatch.undo()
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    straight = copy_template(ran, tmp_path / "straight")
    assert run(straight, config) == 0
    assert tree(state, ("health",)) == tree(straight, ("health",))
    line = json.dumps(retried, sort_keys=True)
    assert [x for x in health_lines(state) if x != line] == health_lines(straight)


def test_a_day_with_a_stored_response_failing_once_makes_one_provider_call_in_all(
        tmp_path, config, synth_committed_template, monkeypatch):
    assert SYNTH_AS_OF == INSTANT.isoformat()
    state = copy_template(synth_committed_template, tmp_path / "state")
    provider = Recording(ScriptedProvider(corpus(tmp_path / "corpus", VALID)))
    calls = fail(monkeypatch, daily, "_rank_persistence", times=1)
    done = daily.run_day(state, config, SYNTH, FixedClock(INSTANT), SYNTH_DAY,
                         provider=provider)
    assert len(calls) == 2
    assert len(provider.calls) == 1               # the retry replayed the stored response
    assert done.status == journal.WRITTEN and done.commit is not None
    assert done.admission is not None
    assert [e.kind for e in done.events].count(daily.RUN_RETRIED) == 1
    assert len(of_kind(state, daily.RUN_RETRIED, SYNTH)) == 1
    # The same day never failed, with a provider of its own: the same files.
    monkeypatch.undo()
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    straight = copy_template(synth_committed_template, tmp_path / "straight")
    other = Recording(ScriptedProvider(corpus(tmp_path / "corpus2", VALID)))
    daily.run_day(straight, config, SYNTH, FixedClock(INSTANT), SYNTH_DAY, provider=other)
    assert len(other.calls) == 1
    assert tree(state, ("health",)) == tree(straight, ("health",))


# ------------------------------------------------------------- 182 (e): a call-limit breach on T


@pytest.mark.container
def test_a_call_limit_breach_on_t_is_a_daily_error_retried_then_run_failed(
        tmp_path, config, synth_committed_template, monkeypatch):
    """REVIEW-17 note 3's second half. The day's candidate is the rejection suite's
    ``slow_function.py`` byte for byte with its own ``PARAMS``; the generation is
    replaced so that it reaches T without the W validation it would fail. Scored on T
    in the container backend, its first call passes ``call_max_ms``: ``DailyError``,
    retried once, then ``run_failed``, the provider never called."""
    state = copy_template(synth_committed_template, tmp_path / "state")
    source = SLOW.read_text(encoding="utf-8")
    generated: list[gen.Candidate] = []

    def generate(state_dir, setup, day, cell, brief, **kwargs):
        candidate = gen.Candidate(
            day=day, cell=(cell[0], cell[1]), call="c-slow-function", source=source,
            description="the rejection suite's slow function", params={"loops": 15000000},
            grid=None, metrics_w=None, adjusted_w=None, model_id=MODEL,
            model_version="scripted", cutoff=date(2026, 2, 28), profile_version="w-test")
        generated.append(candidate)
        return gen.Generation(candidate, (), ())

    monkeypatch.setattr(gen, "generate", generate)
    before = tree(state, SURVIVORS)
    issues = tmp_path / "issues"
    from discotrade.digest import FileIssueSink

    box = ContainerSandbox(tmp_path / "scratch", config)
    try:
        with pytest.raises(daily.DailyError) as raised:
            daily.run_day(state, config, SYNTH, FixedClock(INSTANT), SYNTH_DAY,
                          provider=ListOnly([MODEL]), sandbox=box,
                          issues=FileIssueSink(issues, SYNTH))
    finally:
        left = [n for n in box.started if container.container_exists(box.runtime(), n)]
        for name in left:
            container.remove(box.runtime(), name)
    assert left == []
    assert len(generated) == 2 and box.started            # both attempts reached T
    text = str(raised.value)
    assert "while scored on T" in text and "call_max" in text
    [failed] = of_kind(state, daily.RUN_FAILED, SYNTH)
    assert failed["detail"]["day"] == SYNTH_DAY.isoformat()
    for key in ("first", "second"):
        assert failed["detail"][key].startswith("DailyError: ")
        assert "call_max" in failed["detail"][key]
    assert of_kind(state, daily.RUN_RETRIED, SYNTH) == []
    assert tree(state, SURVIVORS) == before
    assert len(list((issues / SYNTH).iterdir())) == 1


def test_the_slow_function_fixture_is_the_one_the_call_limit_test_names():
    text = SLOW.read_text(encoding="utf-8")
    assert 'PARAMS = {"loops": 15000000}' in text and "call_max_ms (500 ms)" in text


def test_a_refusal_before_the_day_is_not_retried_and_records_no_run_failed(
        state, config, monkeypatch, capsys):
    calls = fail(monkeypatch, table, "build", times=2)
    before, log = tree(state), health_lines(state)
    # 2019-06-13 has not closed at 23:30 UTC (tests/test_daily.py's refusal).
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", "2019-06-13T23:30:00+00:00", "run-day", "--day",
                 NEXT.isoformat()]) == 1
    assert "has not closed" in capsys.readouterr().err
    assert calls == [] and tree(state) == before and health_lines(state) == log


def test_a_failing_issue_sink_appends_issue_failed_and_still_exits_1(
        state, config, monkeypatch):
    from discotrade import digest

    class Refusing:
        def open(self, title, body, labels):
            raise digest.IssueError("injected: the sink refused")

    fail(monkeypatch, table, "build", times=2)
    clock = FixedClock(datetime.fromisoformat(RAN_AS_OF))
    with pytest.raises(daily.DailyError):
        daily.run_day(state, config, TRACK, clock, NEXT, issues=Refusing())
    assert len(of_kind(state, daily.RUN_FAILED)) == 1
    assert [e["detail"] for e in of_kind(state, daily.ISSUE_FAILED)] == [
        {"title": f"run_failed {TRACK} {NEXT.isoformat()}",
         "error": "injected: the sink refused"}]



# ------------------------------------------------------------- 179 (d): the day's tokens


class Spending:
    """A coordinator with ``begin_day`` whose every write call spends tokens, a different
    count per call, recorded so that the test computes the day's sum itself; the text is
    the scripted form's."""

    def __init__(self, track, spends):
        from discotrade.coordinator import ScriptedCoordinator

        self.scripted = ScriptedCoordinator(track)
        self.spends = list(spends)
        self.days: list[date] = []
        self.spent: list[int] = []
        self.used = 0

    def begin_day(self, day):
        self.days.append(day)
        self.used = 0

    def _spend(self):
        n = self.spends[len(self.spent)]
        self.spent.append(n)
        self.used += n

    def choose_cell(self, cells, registry):
        self._spend()
        return self.scripted.choose_cell(cells, registry)

    def write_digest(self, alerts):
        self._spend()
        return self.scripted.write_digest(alerts)

    def write_runlog_line(self, summary):
        self._spend()
        return self.scripted.write_runlog_line(summary)


def test_begin_day_is_called_once_for_a_retried_day_and_its_tokens_cover_both_attempts(
        state, config, monkeypatch):
    """Decision 179 (d): the day's token sum covers every coordinator call of the run of
    the day, both attempts of item 182 included; ``begin_day`` is called once per day,
    not per attempt. The first attempt fails at the move, after step 7's call spent."""
    from discotrade.journal import Setup

    track = Setup.load(config, TRACK).track
    spender = Spending(track, [300, 500, 700])
    calls = fail(monkeypatch, daily, "_move", times=1)
    clock = FixedClock(datetime.fromisoformat(RAN_AS_OF))
    done = daily.run_day(state, config, TRACK, clock, NEXT, coordinator=spender)
    assert len(calls) == 2 and done.commit is not None
    assert spender.days == [NEXT]
    assert len(spender.spent) == 2                 # one step 7 call per attempt
    rows = [json.loads(x) for x in daily.runlog_path(state, TRACK).read_text(
        encoding="utf-8").splitlines()]
    [row] = [r for r in rows if r["date"] == NEXT.isoformat()]
    assert row["coordinator_tokens"] == sum(spender.spent) == 800
