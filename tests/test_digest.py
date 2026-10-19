"""The digest module: the issue sinks, ``render``, the ``[issues]`` table and the
``--issues`` option (decisions 178 and 179 (a), (b) of
meta/decisions/decisions-2026-10-19-m22.md; DESIGN 15.4, 19.3 L6; I-8, I-11, I-13).

No test runs the real ``gh`` (I-11): every ``GhIssueSink`` call goes to a fake
executable written by the test under its temporary directory and named by
``IssueSettings.binary``. The fake appends one JSON line per start to its record
(its arguments, its working directory, the names of its environment, and the text
of the file ``--body-file`` names, read while it runs) and acts by its mode:
``ok`` prints two lines, the issue's address and an empty line; ``exit1`` exits 1;
``grandchild`` starts a sleeping grandchild, writes its pid, then sleeps past the
timeout. Issue files, state directories and remotes are written under pytest's
temporary directory only. The payloads ``render`` is given are written by the test
to files and read back; every value the test expects in a table it computes itself
with ``json.dumps``. The prose comes from the scripted coordinator, given one
``AlertPayload`` (kind and subject) per entry. The ``--issues`` tests run the
command in-process through ``discotrade.cli.main`` on ``tests/test_cli_provider.py``'s
copied fixture configuration (track ``test_synth``); every git run is on local paths
with ``GIT_ALLOW_PROTOCOL=file``. No socket, no wall clock in a result; the waits for
a killed process are bounded loops of short sleeps.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT
from test_cli_provider import (  # noqa: F401 - config is a fixture
    DAYS,
    FIRST,
    LAST,
    TRACK,
    call,
    config,
    files,
    fresh,
    run_day,
    run_replay,
)

from discotrade import coordinator as co
from discotrade import digest
from discotrade.config import ConfigError, IssueSettings, load_run, load_track_config
from discotrade.workers import providers as pv

D = date(2019, 7, 15)
ADDRESS = "https://github.example/owner/state/issues/7"

FAKE = '''#!{python}
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
body = None
if "--body-file" in args:
    with open(args[args.index("--body-file") + 1], encoding="utf-8") as f:
        body = f.read()
with open(os.path.join(here, "record.jsonl"), "a") as f:
    f.write(json.dumps({{"args": args, "cwd": os.getcwd(), "env_keys": sorted(os.environ),
                        "body": body}}) + "\\n")
mode = {mode!r}
if mode == "grandchild":
    pid = os.fork()
    if pid == 0:
        os.close(0); os.close(1); os.close(2)
        time.sleep(120)
        os._exit(0)
    with open(os.path.join(here, "grandchild.pid"), "w") as f:
        f.write(str(pid))
    time.sleep(120)
if mode == "exit1":
    sys.stderr.write("could not create the issue\\n")
    sys.exit(1)
sys.stdout.write("Creating issue in owner/state\\n\\n{address}\\n\\n")
'''


def fake_gh(root: Path, mode: str = "ok") -> Path:
    folder = root / "fakebin"
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / "gh"
    script.write_text(FAKE.format(python=sys.executable, mode=mode, address=ADDRESS),
                      encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def records(script: Path) -> list[dict]:
    path = script.parent / "record.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def settings_for(script: Path, timeout: float = 30.0) -> IssueSettings:
    return IssueSettings(binary=str(script), timeout_seconds=timeout, labels=("discotrade",))


def git_init(path: Path, origin: Path | None = None) -> Path:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=env)
    if origin is not None:
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True, env=env)
        subprocess.run(["git", "-C", str(path), "remote", "add", "origin", str(origin)],
                       check=True, env=env)
    return path


@pytest.fixture(autouse=True)
def _git_local(monkeypatch):
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")


# --- the labels (decision 178 (c)) -------------------------------------------------------


@pytest.mark.parametrize("kind, cls", [
    ("persistent_approach", "finding"), ("group_edge", "finding"),
    ("rank_persistence", "finding"), ("revival", "finding"),
    ("cost_stale", "health"), ("run_failed", "health"), ("no_finding", "health"),
])
def test_the_labels_are_the_settings_then_the_class_then_the_kind(kind, cls):
    assert digest.issue_labels(("discotrade",), kind) == ["discotrade", cls, kind]


def test_the_finding_class_is_the_finding_kinds_of_alerts():
    from discotrade import alerts

    assert set(alerts.FINDING_KINDS) == {"persistent_approach", "group_edge",
                                         "rank_persistence", "revival"}


# --- FileIssueSink (decision 178 (a)) ----------------------------------------------------


def test_file_sink_writes_the_bytes_numbers_the_second_and_returns_the_path(tmp_path):
    sink = digest.FileIssueSink(tmp_path / "issues", TRACK)
    first = sink.open("persistent_approach a1 2019-07-15", "Body line one.\nLine two.\n",
                      ["discotrade", "finding", "persistent_approach"])
    second = sink.open("cost_stale SYNA 2019-07-15", "Other body",
                       ["discotrade", "health", "cost_stale"])
    one = tmp_path / "issues" / TRACK / "0001.md"
    two = tmp_path / "issues" / TRACK / "0002.md"
    assert first == str(one) and second == str(two)
    assert one.read_bytes() == (b"title: persistent_approach a1 2019-07-15\n"
                                b"labels: discotrade, finding, persistent_approach\n"
                                b"\nBody line one.\nLine two.\n")
    assert two.read_bytes() == (b"title: cost_stale SYNA 2019-07-15\n"
                                b"labels: discotrade, health, cost_stale\n"
                                b"\nOther body\n")
    assert sorted(p.name for p in (tmp_path / "issues" / TRACK).iterdir()) == \
        ["0001.md", "0002.md"]


def test_file_sink_takes_the_lowest_free_number(tmp_path):
    folder = tmp_path / "issues" / TRACK
    folder.mkdir(parents=True)
    (folder / "0001.md").write_text("held\n", encoding="utf-8")
    (folder / "0003.md").write_text("held\n", encoding="utf-8")
    got = digest.FileIssueSink(tmp_path / "issues", TRACK).open("t", "b", ["discotrade"])
    assert got == str(folder / "0002.md")
    assert (folder / "0001.md").read_text(encoding="utf-8") == "held\n"


# --- GhIssueSink (decision 178 (b)) ------------------------------------------------------


def test_gh_sink_passes_the_title_the_body_file_and_each_label_in_order(tmp_path,
                                                                        monkeypatch):
    script = fake_gh(tmp_path)
    state = git_init(tmp_path / "state")
    monkeypatch.setenv("DATABENTO_API_KEY", "db-test-not-a-key")
    monkeypatch.setenv(pv.KEY_ENV, "or-test-not-a-key")
    sink = digest.GhIssueSink(settings_for(script), state)
    title = "persistent_approach a1 2019-07-15"
    body = "## persistent_approach — a1\n\n| key | value |\n"
    labels = digest.issue_labels(("discotrade",), "persistent_approach")
    assert sink.open(title, body, labels) == ADDRESS
    (rec,) = records(script)
    args = rec["args"]
    assert args[:2] == ["issue", "create"]
    assert args[args.index("--title") + 1] == title
    assert rec["body"] == body
    got = [args[i + 1] for i, a in enumerate(args) if a == "--label"]
    assert got == ["discotrade", "finding", "persistent_approach"]
    assert Path(rec["cwd"]).resolve() == state.resolve()
    for name in pv.WITHHELD_ENV:
        assert name not in rec["env_keys"], name
    body_file = Path(args[args.index("--body-file") + 1])
    assert not body_file.exists()
    assert state.resolve() not in body_file.resolve().parents


def test_gh_sink_labels_of_a_health_kind(tmp_path):
    script = fake_gh(tmp_path)
    sink = digest.GhIssueSink(settings_for(script), git_init(tmp_path / "state"))
    sink.open("cost_stale SYNA 2019-07-15", "b",
              digest.issue_labels(("discotrade",), "cost_stale"))
    args = records(script)[0]["args"]
    assert [args[i + 1] for i, a in enumerate(args) if a == "--label"] == \
        ["discotrade", "health", "cost_stale"]


def test_gh_sink_exit_status_1_raises_issue_error(tmp_path):
    script = fake_gh(tmp_path, mode="exit1")
    sink = digest.GhIssueSink(settings_for(script), git_init(tmp_path / "state"))
    with pytest.raises(digest.IssueError, match="exit status 1"):
        sink.open("t", "b", ["discotrade"])


def test_gh_sink_that_cannot_start_raises_issue_error(tmp_path):
    sink = digest.GhIssueSink(settings_for(tmp_path / "no-such-gh"),
                              git_init(tmp_path / "state"))
    with pytest.raises(digest.IssueError, match="could not be started"):
        sink.open("t", "b", ["discotrade"])


def _gone(pid: int) -> bool:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    except OSError:
        return True
    return fields[0] == "Z"


def test_gh_sink_timeout_raises_and_kills_the_whole_process_group(tmp_path):
    script = fake_gh(tmp_path, mode="grandchild")
    sink = digest.GhIssueSink(settings_for(script, timeout=2.0), git_init(tmp_path / "state"))
    with pytest.raises(digest.IssueError, match="timeout"):
        sink.open("t", "b", ["discotrade"])
    pid = int((script.parent / "grandchild.pid").read_text())
    try:
        gone = False
        for _ in range(100):  # a bounded wait, no clock read
            if _gone(pid):
                gone = True
                break
            time.sleep(0.05)
        assert gone, "the grandchild outlived the timeout"
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


# --- the [issues] table (decision 178 (c)) -----------------------------------------------


@pytest.mark.parametrize("cfg", [REPO_ROOT / "config", FIXTURE_CONFIG],
                         ids=["config", "fixture"])
def test_the_issues_table(cfg):
    issues = load_run(cfg).issues
    assert issues == IssueSettings(binary="gh", timeout_seconds=60.0, labels=("discotrade",))


def test_the_issues_table_refuses_an_unknown_key_and_a_bad_timeout(tmp_path):
    text = (REPO_ROOT / "config" / "run.toml").read_text(encoding="utf-8")
    (tmp_path / "run.toml").write_text(text.replace("timeout_seconds = 60",
                                                    "timeout_seconds = 0"), encoding="utf-8")
    with pytest.raises(ConfigError, match="issues.timeout_seconds"):
        load_run(tmp_path)
    (tmp_path / "run.toml").write_text(text.replace('labels = ["discotrade"]',
                                                    'labels = ["discotrade"]\nrepo = "x"'),
                                       encoding="utf-8")
    with pytest.raises(ConfigError, match="issues.repo"):
        load_run(tmp_path)


# --- render (decision 179 (a), (b)) ------------------------------------------------------


def _flat(prefix: str, value, out: dict) -> None:
    if isinstance(value, dict) and value:
        for k, v in value.items():
            _flat(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = value


def test_render_holds_every_payload_value_and_the_scripted_prose(tmp_path):
    payloads = {
        ("persistent_approach", "a1"): {
            "adjusted_sharpe": 1.2345678901, "N": 14, "p_N": 0.00312,
            "thresholds": {"alpha": 0.05, "min_days": 60},
            "description": "a trend rule | with a bar", "cell": ["trend", "short"],
            "dormant_since": None, "flag": True},
        ("cost_stale", "spreads/SYNA.toml checked"): {
            "checked": "2019-01-02", "days": 194, "thresholds": {"cost_stale_days": 180}},
    }
    fired = []
    for (kind, subject), payload in payloads.items():
        path = tmp_path / "payloads" / f"{kind}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        fired.append({"kind": kind, "subject": subject, "active": True,
                      "payload": json.loads(path.read_text(encoding="utf-8"))})
    track = load_track_config(FIXTURE_CONFIG, TRACK).track
    given = digest.alert_payloads(fired)
    assert [dataclasses.astuple(a) for a in given] == [(e["kind"], e["subject"])
                                                       for e in fired]
    assert [f.name for f in dataclasses.fields(co.AlertPayload)] == ["kind", "subject"]
    prose = co.ScriptedCoordinator(track).write_digest(given)
    page = digest.render(TRACK, D, fired, prose, 37, 20000)

    lines = page.split("\n")
    assert lines[0] == f"# {TRACK} 2019-07-15"
    assert page.index(prose) < page.index("## persistent_approach — a1") \
        < page.index("## cost_stale — spreads/SYNA.toml checked")
    assert lines[-2] == "Coordinator tokens: 37 of 20000" and lines[-1] == ""
    for (kind, subject), payload in payloads.items():
        section = page.split(f"## {kind} — {subject}\n", 1)[1].split("\n## ", 1)[0]
        flat: dict = {}
        _flat("", payload, flat)
        rows = [line for line in section.splitlines() if line.startswith("| ")]
        expected = []
        for key in sorted(flat):
            text = json.dumps(flat[key], separators=(",", ":"), allow_nan=False)
            expected.append(f"| {key.replace('|', chr(92) + '|')} | "
                            f"{text.replace('|', chr(92) + '|')} |")
        assert rows == ["| key | value |", *expected], kind
    assert "| adjusted_sharpe | 1.2345678901 |" in lines
    assert "| thresholds.alpha | 0.05 |" in lines
    assert '| description | "a trend rule \\| with a bar" |' in lines
    for number in ("1.2345678901", "0.00312", "194"):
        assert number not in prose


def test_render_is_deterministic_and_ends_with_one_newline():
    fired = [{"kind": "revival", "subject": "a2", "payload": {"dormant_days": 21}}]
    one = digest.render(TRACK, D, fired, "Prose.", 0, 100)
    assert one == digest.render(TRACK, D, fired, "Prose.", 0, 100)
    assert one.endswith("of 100\n") and not one.endswith("\n\n")


# --- the --issues option (decision 178 (d)) ----------------------------------------------


@pytest.fixture
def state(tmp_path):
    return fresh(tmp_path / "state")


def both(state, cfg, *extra):
    return {"replay": run_replay(state, cfg, FIRST, LAST, *extra),
            "run-day": run_day(state, cfg, *DAYS[0], *extra)}


def refused(results, state, before, status, needle):
    for command, (got, out, err) in results.items():
        assert got == status, (command, err)
        assert out == "", command
        assert len(err.strip().splitlines()) == 1, (command, err)
        assert needle in err, (command, err)
    assert files(state) == before


@pytest.mark.parametrize("value", ["bogus", "file:", "GH", "file"])
def test_an_unknown_issues_value_is_a_usage_error(state, config, value):  # noqa: F811
    before = files(state)
    for command, (got, _, err) in both(state, config, "--issues", value).items():
        assert got == 2, (command, err)
        assert "--issues" in err
    assert files(state) == before


@pytest.mark.parametrize("where", ["state", "state-sub", "repository"])
def test_a_file_directory_in_the_state_or_the_code_repository_is_a_usage_error(
        state, config, where):  # noqa: F811
    directory = {"state": state, "state-sub": state / "issues",
                 "repository": REPO_ROOT / "build" / "issues"}[where]
    before = files(state)
    refused(both(state, config, "--issues", f"file:{directory}"), state, before, 2,
            "--issues")
    assert not (REPO_ROOT / "build" / "issues").exists()


def _issues_config(root: Path, cfg: Path, binary: str) -> Path:
    other = root / "cfg-issues"
    shutil.copytree(cfg, other)
    path = other / "run.toml"
    path.write_text(path.read_text(encoding="utf-8").replace('binary = "gh"',
                                                             f'binary = "{binary}"'),
                    encoding="utf-8")
    assert load_run(other).issues.binary == binary
    return other


def test_gh_with_no_gh_on_path_is_refused_exit_1(state, config, monkeypatch,  # noqa: F811
                                                 tmp_path):
    empty = tmp_path / "empty-path"
    empty.mkdir()
    monkeypatch.setenv("PATH", f"{empty}")
    real_which = shutil.which
    resolved = []

    def which(name, *args, **kw):
        got = real_which(name, *args, **kw)
        resolved.append((name, got))
        return got

    monkeypatch.setattr(shutil, "which", which)
    assert load_run(config).issues.binary == "gh"
    before = files(state)
    # git is not on this PATH either: the refusal comes before any git or day.
    refused(both(state, config, "--issues", "gh"), state, before, 1, "not found on PATH")
    assert ("gh", None) in resolved


def test_gh_with_a_state_without_origin_is_refused_exit_1(state, config,  # noqa: F811
                                                          tmp_path):
    script = fake_gh(tmp_path)
    cfg = _issues_config(tmp_path, config, str(script))
    before = files(state)
    refused(both(state, cfg, "--issues", "gh"), state, before, 1, "origin")
    assert records(script) == []


def test_gh_with_origin_and_a_file_outside_pass_the_refusals(state, config,  # noqa: F811
                                                             tmp_path):
    """With a binary found and ``origin`` present, or a ``file:`` directory outside
    both trees, the option is accepted: ``run-day`` then refuses the Saturday it is
    given as before, naming the day, and nothing is called."""
    script = fake_gh(tmp_path)
    cfg = _issues_config(tmp_path, config, str(script))
    subprocess.run(["git", "init", "-q", "--bare", str(tmp_path / "origin.git")], check=True)
    subprocess.run(["git", "-C", str(state), "remote", "add", "origin",
                    str(tmp_path / "origin.git")], check=True)
    for option in ("gh", f"file:{tmp_path / 'issues'}"):
        got, _, err = call("--state", str(state), "--config", str(cfg), "--track", TRACK,
                           "--as-of", "2019-07-15T21:00:00+00:00", "run-day",
                           "--day", "2019-07-13", "--issues", option)
        assert got == 1, err
        assert "2019-07-13" in err and "--issues" not in err and "origin" not in err
    assert records(script) == []
    assert not (tmp_path / "issues").exists()
