"""The digest page, the run log and step 8 in the day (decisions 179 and 180 of
meta/decisions/decisions-2026-10-19-m22.md; DESIGN 14.1, 14.3, 15.4, 16.1 steps 7 and
8, 16.2; I-6, I-8, I-11).

Every state directory is made by ``init-state`` at ``INIT_AS_OF`` under a pytest
temporary directory, and every day runs in-process through ``discotrade.cli.main``
(``run-day`` at ``--as-of`` the close of ``D``'s last bar, or ``replay`` with its
clock), on the fixture track ``test_synth`` (no approach; the synthetic sources'
fixed seeds are the only random draws) over ``tests/fixtures/config/`` copied under
tmp with the production ``config/thresholds.toml`` copied in unchanged. A test that
runs the day function with a coordinator object calls ``daily.run_day`` with the
replay's clock.

The fired entries are made by the test: ``alerts.detectors`` is replaced
(``monkeypatch``) by one that returns two alert-level events dated ``D`` whose details
the test writes (``DETAILS``, numbers and a nested table), so that step 6's health
entries fire with those details as payloads. Every value the test expects in a table
it computes itself from the payload files the day wrote, with ``json.dumps``.

No real ``claude`` or ``gh`` runs (I-11): the coordinator's Claude Code form calls a
fake ``claude`` (tests/test_coordinator_claude.py's), the ``gh`` sink a fake ``gh``
(tests/test_digest.py's), each written by the test under its temporary directory.
Origins are bare repositories under tmp, or a path that does not exist; every git
run is on local paths with ``GIT_ALLOW_PROTOCOL=file`` (decision 47). No socket, no
wall clock.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import quote

import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT
from test_coordinator_claude import fake_claude, output, settings_for
from test_coordinator_claude import records as claude_records
from test_digest import fake_gh
from test_digest import records as gh_records

from discotrade import alerts, daily, journal
from discotrade import coordinator as co
from discotrade.cli import main
from discotrade.clock import FixedClock
from discotrade.state import HealthEvent

TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
D = date(2019, 7, 15)
D_AS_OF = "2019-07-15T21:00:00+00:00"
D_CLOSE = datetime(2019, 7, 15, 21, tzinfo=UTC)
#: The two alert-level events the replaced detectors return on ``D``: kind, subject
#: and detail (the fired entry's payload).
DETAILS = (
    ("cost_stale", "spreads/SYNA.toml checked",
     {"checked": "2019-01-02", "days": 194, "thresholds": {"alerts.cost_stale_days": 180}}),
    ("few_valid_candidates", TRACK,
     {"trials": 3, "first": "2019-06-16", "last": "2019-07-15", "since": "2019-06-03",
      "ratio": 0.123456789, "thresholds": {"alerts.min_valid_candidates": 10,
                                           "alerts.valid_candidates_window_days": 30}}),
)
PAGE = f"digests/{TRACK}/{D.isoformat()}.md"


# ------------------------------------------------------------- helpers


def call(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:   # argparse's usage errors
            status = exc.code
    return status, out.getvalue(), err.getvalue()


def run_day(state: Path, config: Path, *extra: str) -> tuple[int, str, str]:
    return call("--state", str(state), "--config", str(config), "--track", TRACK,
                "--as-of", D_AS_OF, "run-day", "--day", D.isoformat(), *extra)


def run_replay(state: Path, config: Path, *extra: str) -> tuple[int, str, str]:
    return call("--state", str(state), "--config", str(config), "--track", TRACK,
                "replay", "--from", D.isoformat(), "--to", D.isoformat(), *extra)


def fresh(path: Path) -> Path:
    status, _, err = call("init-state", "--state", str(path), "--as-of", INIT_AS_OF)
    assert status == 0, err
    return path


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def with_origin(state: Path, origin: Path, bare: bool = True) -> Path:
    if bare:
        env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], env=env,
                       check=True, capture_output=True)
    git(state, "remote", "add", "origin", str(origin))
    return origin


def files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(Path(root).rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def health(state: Path) -> list[dict]:
    path = state / "health" / f"{TRACK}.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] \
        if path.exists() else []


def runlog(state: Path) -> list[dict]:
    path = state / "runlog" / f"{TRACK}.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def payload(state: Path, kind: str, subject: str) -> dict:
    path = (state / "alerts" / TRACK / "payloads" / D.isoformat() / kind
            / f"{quote(subject, safe='')}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def flat(prefix: str, value, out: dict) -> None:
    if isinstance(value, dict) and value:
        for k, v in value.items():
            flat(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = value


def expected_section(kind: str, subject: str, values: dict) -> str:
    """The section of one entry, computed here from its payload."""
    out: dict = {}
    flat("", values, out)
    rows = ["| key | value |", "|---|---|"]
    for key in sorted(out):
        text = json.dumps(out[key], separators=(",", ":"), allow_nan=False)
        rows.append(f"| {key.replace('|', chr(92) + '|')} | {text.replace('|', chr(92) + '|')} |")
    return f"## {kind} — {subject}\n\n" + "\n".join(rows)


def fire(monkeypatch, details=DETAILS) -> None:
    """Replace the detectors by two alert-level events on ``D`` with ``details``."""
    def detectors(state_dir, setup, day, **_):
        if day != D:
            return []
        return [HealthEvent(day, "alert", kind, subject, dict(detail))
                for kind, subject, detail in details]
    monkeypatch.setattr(alerts, "detectors", detectors)


def scores_changed(details=DETAILS) -> tuple:
    """``details`` with every number changed and nothing else."""
    def change(value):
        if isinstance(value, dict):
            return {k: change(v) for k, v in value.items()}
        if isinstance(value, bool) or not isinstance(value, int | float):
            return value
        return value * 3 + 1
    return tuple((kind, subject, change(detail)) for kind, subject, detail in details)


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


# --- decision 179 (a), (c), (e): the page and the run log line ---------------------------


def test_a_day_with_two_fired_entries_writes_the_page_and_a_run_log_line(
        tmp_path, config, setup, monkeypatch):
    fire(monkeypatch)
    state = fresh(tmp_path / "state")
    status, out, err = run_day(state, config)
    assert status == 0, err
    page = (state / PAGE).read_text(encoding="utf-8")
    prose = co.ScriptedCoordinator(setup.track).write_digest(
        [co.AlertPayload(kind, subject) for kind, subject, _ in DETAILS])
    budget = setup.thresholds["budgets.coordinator_tokens_per_day"]
    sections = [expected_section(kind, subject, payload(state, kind, subject))
                for kind, subject, _ in DETAILS]
    assert page == "\n\n".join([f"# {TRACK} {D.isoformat()}", prose, *sections,
                                f"Coordinator tokens: 0 of {budget}"]) + "\n"
    # Each value of each payload is in its table, as the test writes it.
    for kind, subject, detail in DETAILS:
        assert payload(state, kind, subject) == detail
    assert "| ratio | 0.123456789 |" in page.splitlines()
    assert '| thresholds.alerts.cost_stale_days | 180 |' in page.splitlines()
    (line,) = runlog(state)
    assert line == {"date": D.isoformat(), "mode": "live",
                    "alerts": sorted(f"{k}|{s}" for k, s, _ in DETAILS),
                    "digest": PAGE, "line": None, "coordinator_tokens": 0}
    # Both are committed with the day.
    assert git(state, "status", "--porcelain") == ""
    assert PAGE in git(state, "ls-tree", "-r", "--name-only", "HEAD").splitlines()


def test_a_day_with_no_fired_entry_writes_the_scripted_sentence_and_no_page(
        tmp_path, config, setup):
    state = fresh(tmp_path / "state")
    status, out, err = run_replay(state, config)
    assert status == 0, err
    assert not (state / "digests").exists()
    (line,) = runlog(state)
    assert line == {"date": D.isoformat(), "mode": "replay", "alerts": [], "digest": None,
                    "line": f"Track {TRACK}: no alert, no generation.",
                    "coordinator_tokens": 0}
    assert line["line"] == co.ScriptedCoordinator(setup.track).write_runlog_line(
        co.RunSummary(TRACK, None))


def test_the_replay_writes_mode_replay_on_a_digest_day(tmp_path, config, monkeypatch):
    fire(monkeypatch)
    state = fresh(tmp_path / "state")
    status, _, err = run_replay(state, config)
    assert status == 0, err
    (line,) = runlog(state)
    assert (line["mode"], line["digest"], line["line"]) == ("replay", PAGE, None)
    assert (state / PAGE).is_file()


def test_a_re_run_writes_neither_the_page_nor_a_run_log_line(tmp_path, config, monkeypatch):
    fire(monkeypatch)
    state = fresh(tmp_path / "state")
    assert run_day(state, config)[0] == 0
    before, head = files(state), git(state, "rev-parse", "HEAD")
    status, out, err = run_day(state, config)
    assert status == 0, err
    assert "already journaled with equal rows; nothing written" in out
    assert files(state) == before and git(state, "rev-parse", "HEAD") == head


# --- decision 179 (b), (d): the coordinator's prose -------------------------------------


def claude_day(state: Path, config: Path, setup, script: Path) -> daily.DayRun:
    coordinator = co.ClaudeCodeCoordinator(setup.track, settings_for(script), 10**9)
    return daily.run_day(state, config, TRACK, FixedClock(D_CLOSE), D,
                         coordinator=coordinator)


def test_the_claude_forms_prose_is_stored_as_written_and_its_tokens_counted(
        tmp_path, config, setup, monkeypatch):
    fire(monkeypatch)
    script = fake_claude(tmp_path / "claude", reply=output("Two alerts fired.",
                                                           tokens=(30, 12)))
    state = fresh(tmp_path / "state")
    done = claude_day(state, config, setup, script)
    assert done.commit is not None
    (seen,) = claude_records(script)
    assert "ALERTS (JSON):" in seen["stdin"]
    page = (state / PAGE).read_text(encoding="utf-8")
    assert page.split("\n\n")[1] == "Two alerts fired."
    budget = setup.thresholds["budgets.coordinator_tokens_per_day"]
    assert page.endswith(f"\n\nCoordinator tokens: 42 of {budget}\n")
    assert runlog(state)[0]["coordinator_tokens"] == 42


def test_a_failing_digest_call_gives_the_scripted_prose_and_the_notice(
        tmp_path, config, setup, monkeypatch):
    fire(monkeypatch)
    script = fake_claude(tmp_path / "claude", mode="exit3")
    state = fresh(tmp_path / "state")
    claude_day(state, config, setup, script)
    assert len(claude_records(script)) == 1
    prose = co.ScriptedCoordinator(setup.track).write_digest(
        [co.AlertPayload(kind, subject) for kind, subject, _ in DETAILS])
    assert (state / PAGE).read_text(encoding="utf-8").split("\n\n")[1] == prose
    notices = [(e["kind"], e["subject"], e["detail"]) for e in health(state)
               if e["level"] == "notice"]
    assert notices == [("coordinator_fallback", "coordinator",
                        {"reason": "exit status 3", "task": "write_digest"})]


def test_a_coordinator_that_raises_gives_the_scripted_sentence_and_the_notice(
        tmp_path, config, setup):
    class Raising(co.ScriptedCoordinator):
        def write_runlog_line(self, summary):
            raise RuntimeError("no sentence today")

    state = fresh(tmp_path / "state")
    daily.run_day(state, config, TRACK, FixedClock(D_CLOSE), D,
                  coordinator=Raising(setup.track))
    assert runlog(state)[0]["line"] == f"Track {TRACK}: no alert, no generation."
    assert [(e["kind"], e["detail"]) for e in health(state)] == [
        ("coordinator_fallback", {"reason": "the call raised RuntimeError",
                                  "task": "write_runlog_line"})]


def test_two_states_differing_only_in_scores_give_byte_identical_digest_prompts(
        tmp_path, config, setup, monkeypatch):
    prompts, pages = [], []
    for which, details in (("a", DETAILS), ("b", scores_changed())):
        fire(monkeypatch, details)
        script = fake_claude(tmp_path / which / "claude", reply=output("Prose."))
        state = fresh(tmp_path / which / "state")
        claude_day(state, config, setup, script)
        (seen,) = claude_records(script)
        prompts.append(seen["stdin"].encode("utf-8"))
        pages.append((state / PAGE).read_text(encoding="utf-8"))
    assert pages[0] != pages[1]  # the states differ in their scores, on the page
    assert prompts[0] == prompts[1]
    for _, _, detail in DETAILS + scores_changed():
        out: dict = {}
        flat("", detail, out)
        for value in out.values():
            if isinstance(value, int | float) and not isinstance(value, bool):
                assert json.dumps(value) not in prompts[0].decode("utf-8").split(
                    "ALERTS (JSON):", 1)[1]


# --- decision 180: the push and the issues ----------------------------------------------


def test_the_day_is_pushed_to_a_local_bare_origin(tmp_path, config):
    state = fresh(tmp_path / "state")
    origin = with_origin(state, tmp_path / "origin.git")
    status, out, err = run_day(state, config)
    assert status == 0, err
    head = git(state, "rev-parse", "HEAD").strip()
    assert git(state, "log", "-1", "--format=%s").strip() == f"run {TRACK} {D.isoformat()}"
    assert git(origin, "rev-parse", "refs/heads/main").strip() == head
    assert [e["kind"] for e in health(state)] == []


def test_an_origin_that_does_not_exist_gives_push_failed_and_exit_0(tmp_path, config):
    state = fresh(tmp_path / "state")
    with_origin(state, tmp_path / "nowhere.git", bare=False)
    status, out, err = run_day(state, config)
    assert status == 0, err
    assert git(state, "log", "-1", "--format=%s").strip() == f"run {TRACK} {D.isoformat()}"
    (event,) = health(state)
    assert (event["date"], event["level"], event["kind"], event["subject"]) == \
        (D.isoformat(), "notice", "push_failed", TRACK)
    assert event["detail"]["day"] == D.isoformat() and event["detail"]["error"]
    assert "push_failed" in out
    # Written after the commit: uncommitted until the next day's commit (180 (c)).
    assert git(state, "status", "--porcelain").strip() == "?? health/"
    # A re-run pushes nothing and appends nothing.
    before = files(state)
    assert run_day(state, config)[0] == 0
    assert files(state) == before


def test_each_fired_entry_opens_one_file_issue(tmp_path, config, monkeypatch):
    fire(monkeypatch)
    state = fresh(tmp_path / "state")
    issues = tmp_path / "issues"
    status, out, err = run_day(state, config, "--issues", f"file:{issues}")
    assert status == 0, err
    folder = issues / TRACK
    assert sorted(p.name for p in folder.iterdir()) == ["0001.md", "0002.md"]
    for n, (kind, subject, _) in enumerate(DETAILS, start=1):
        section = expected_section(kind, subject, payload(state, kind, subject))
        want = (f"title: {kind} {subject} {D.isoformat()}\n"
                f"labels: discotrade, health, {kind}\n\n"
                f"{section}\n\nDigest page: {PAGE}\n")
        assert (folder / f"{n:04d}.md").read_text(encoding="utf-8") == want
    # The page's sections are the issues' sections.
    page = (state / PAGE).read_text(encoding="utf-8")
    assert all(expected_section(k, s, payload(state, k, s)) in page for k, s, _ in DETAILS)
    # A re-run opens nothing.
    assert run_day(state, config, "--issues", f"file:{issues}")[0] == 0
    assert sorted(p.name for p in folder.iterdir()) == ["0001.md", "0002.md"]


def test_no_issue_is_opened_with_issues_none(tmp_path, config, monkeypatch):
    fire(monkeypatch)
    opened = []
    monkeypatch.setattr("discotrade.digest.FileIssueSink.open",
                        lambda self, *a: opened.append(a) or "x")
    state = fresh(tmp_path / "state")
    assert run_day(state, config, "--issues", "none")[0] == 0
    assert opened == [] and (state / PAGE).is_file()


def test_a_gh_that_exits_1_gives_issue_failed_and_exit_0(tmp_path, config, monkeypatch):
    fire(monkeypatch)
    cfg = tmp_path / "config"
    shutil.copytree(config, cfg)
    script = fake_gh(tmp_path / "gh", mode="exit1")
    run_toml = cfg / "run.toml"
    text = run_toml.read_text(encoding="utf-8")
    assert text.count('binary = "gh"') == 1
    run_toml.write_text(text.replace('binary = "gh"', f'binary = "{script}"'),
                        encoding="utf-8")
    state = fresh(tmp_path / "state")
    origin = with_origin(state, tmp_path / "origin.git")
    status, out, err = run_day(state, cfg, "--issues", "gh")
    assert status == 0, err
    seen = gh_records(script)
    assert [s["args"][:4] for s in seen] == [
        ["issue", "create", "--title", f"{kind} {subject} {D.isoformat()}"]
        for kind, subject, _ in DETAILS]
    failed = [e for e in health(state) if e["kind"] == "issue_failed"]
    assert [(e["level"], e["subject"], e["detail"]["title"]) for e in failed] == [
        ("notice", TRACK, f"{kind} {subject} {D.isoformat()}") for kind, subject, _ in DETAILS]
    assert all("exit status 1" in e["detail"]["error"] for e in failed)
    head = git(state, "rev-parse", "HEAD").strip()
    assert git(origin, "rev-parse", "refs/heads/main").strip() == head
    # A re-run pushes and opens nothing.
    assert run_day(state, cfg, "--issues", "gh")[0] == 0
    assert len(gh_records(script)) == len(DETAILS)


@pytest.mark.parametrize("cfg", [REPO_ROOT / "config", FIXTURE_CONFIG],
                         ids=["config", "fixture"])
def test_the_state_table(cfg):
    from discotrade.config import StateSettings, load_run

    assert load_run(cfg).state == StateSettings(push_timeout_seconds=120.0)


def test_the_state_table_refuses_an_unknown_key_and_a_bad_timeout(tmp_path):
    from discotrade.config import ConfigError, load_run

    text = (REPO_ROOT / "config" / "run.toml").read_text(encoding="utf-8")
    assert text.count("push_timeout_seconds = 120") == 1
    (tmp_path / "run.toml").write_text(text.replace("push_timeout_seconds = 120",
                                                    "push_timeout_seconds = 0"),
                                       encoding="utf-8")
    with pytest.raises(ConfigError, match="state.push_timeout_seconds"):
        load_run(tmp_path)
    (tmp_path / "run.toml").write_text(text.replace("push_timeout_seconds = 120",
                                                    "push_timeout_seconds = 120\nremote = 1"),
                                       encoding="utf-8")
    with pytest.raises(ConfigError, match="state.remote"):
        load_run(tmp_path)
