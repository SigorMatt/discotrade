"""The coordinator's Claude Code form, its token budget, the process group and the
deny rules (decisions 163 to 166 of meta/decisions/decisions-2026-10-18-m20.md;
DESIGN 14.1 to 14.4, 16.3; SPEC 17; I-8, I-11, I-13).

No test runs the real ``claude`` binary (I-11): every call goes to a fake
executable written by the test under its temporary directory (``FAKE``), named
by ``[coordinator] binary`` or the worker's executable. The fake appends one JSON
line per start to its record (its arguments, its standard input, the names of its
environment, whether the coordinator's key in it equals the test's, and the text of
the file a ``--settings`` argument names) and replies by its mode. The key is a
made-up value set with ``monkeypatch``. The two states that differ only in scores
are ``tests/test_coordinator.py``'s ``states`` fixture (track ``test_mixed``,
numpy generators seeded 1 and 2). The replay runs the fixture track
``test_synth`` from ``init-state`` at 2019-06-03 over 2019-07-15 and 2019-07-16
with the scripted worker provider of ``tests/test_cli_provider.py``'s corpus, on
``tests/fixtures/config/`` copied under tmp with the production thresholds and the
copy's ``run.toml`` ``[coordinator]`` table replaced by one naming the fake. No
socket, no wall clock in a result; the waits for a killed process are bounded
loops of short sleeps.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import signal
import stat
import sys
import time
import tomllib
from datetime import date
from pathlib import Path

import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT
from test_cli_provider import corpus, fresh
from test_coordinator import INERT, INJECTED, setup, states  # noqa: F401 - fixtures

from discotrade import coordinator as co
from discotrade import ledger, state
from discotrade.cli import main
from discotrade.config import (
    ConfigError,
    CoordinatorSettings,
    load_protected_paths,
    load_run,
    load_thresholds,
)
from discotrade.workers import providers as pv
from discotrade.workers import registry as rg

D = date(2019, 4, 1)
FAKE_KEY = "sk-ant-test-0123456789abcdef-not-a-key"
MODEL = "coordinator-test-model"
BUDGET_USD = 0.37
CONFIG = REPO_ROOT / "config"

#: The fake ``claude``. Modes: ``ok`` replies ``reply.json`` beside it; ``first``
#: replies the first offered cell of the prompt with the brief ``BRIEF-MARK``;
#: ``exit3``, ``sleep``, ``garbage`` and ``grandchild`` (starts a sleeping
#: grandchild, writes its pid to ``grandchild.pid``, then sleeps).
FAKE = '''#!{python}
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
stdin = sys.stdin.read()
settings = None
if "--settings" in args:
    with open(args[args.index("--settings") + 1]) as f:
        settings = f.read()
with open(os.path.join(here, "record.jsonl"), "a") as f:
    f.write(json.dumps({{"args": args, "stdin": stdin, "env_keys": sorted(os.environ),
                        "key_ok": os.environ.get({key_env!r}) == {key!r},
                        "settings": settings}}) + "\\n")
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
if mode == "sleep":
    time.sleep(120)
if mode == "exit3":
    sys.exit(3)
if mode == "garbage":
    sys.stdout.write("not json at all")
    sys.exit(0)
if mode == "first":
    line = stdin.split("OFFERED CELLS (JSON):\\n", 1)[1].split("\\n", 1)[0]
    cell = json.loads(line)[0]["cell"]
    reply = {{"type": "result", "is_error": False,
             "result": json.dumps({{"cell": cell, "brief": "BRIEF-MARK: a new rule."}}),
             "usage": {{"input_tokens": 10, "output_tokens": 5}}}}
    sys.stdout.write(json.dumps(reply))
    sys.exit(0)
with open(os.path.join(here, "reply.json")) as f:
    sys.stdout.write(f.read())
'''


def fake_claude(root: Path, mode: str = "ok", reply=None) -> Path:
    folder = root / "fakebin"
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / "claude"
    script.write_text(FAKE.format(python=sys.executable, key_env=co.KEY_ENV, key=FAKE_KEY,
                                  mode=mode), encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    if reply is not None:
        (folder / "reply.json").write_text(
            reply if isinstance(reply, str) else json.dumps(reply), encoding="utf-8")
    return script


def records(script: Path) -> list[dict]:
    path = script.parent / "record.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def output(result, tokens=(30, 12), **extra) -> dict:
    """``claude``'s JSON output whose ``result`` is ``result``."""
    body = {"type": "result", "subtype": "success", "is_error": False,
            "result": result if isinstance(result, str) else json.dumps(result),
            "usage": {"input_tokens": tokens[0], "output_tokens": tokens[1]}}
    body.update(extra)
    return body


def settings_for(script: Path, timeout: float = 60.0) -> CoordinatorSettings:
    return CoordinatorSettings(binary=str(script), model=MODEL, max_turns=1,
                               max_budget_usd=BUDGET_USD, timeout_seconds=timeout,
                               propose_fixes=False)


def claude(setup, script, budget=10**9, timeout=60.0):  # noqa: F811 - the fixture's value
    out = co.ClaudeCodeCoordinator(setup.track, settings_for(script, timeout), budget)
    out.begin_day(D)
    return out


def offered_cells(setup):  # noqa: F811
    """Three cells of the track: two with free slots, one weak and full."""
    cells = list(setup.track.cells)
    return [co.CellStatus(cells[0], 1, 2, False), co.CellStatus(cells[1], 0, 3, True),
            co.CellStatus(cells[2], 3, 0, True)]


def name(cell) -> str:
    return f"{cell[0]}/{cell[1]}"


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv(co.KEY_ENV, FAKE_KEY)
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")


# --- decision 163 (a), (d): the flags and the key ------------------------------------------

#: The flags, read from the installed ``claude --help`` (2.1.303), with this test's
#: configured values: --max-turns is not listed there and is not passed.
EXPECTED_ARGS = ["--bare", "-p", "--output-format", "json", "--max-budget-usd", "0.37",
                 "--permission-mode", "dontAsk", "--model", MODEL, "--tools", ""]


def test_the_arguments_hold_each_flag_with_the_configured_values(tmp_path, setup):  # noqa: F811
    script = fake_claude(tmp_path, reply=output({"cell": name(setup.track.cells[1]),
                                                 "brief": "b"}))
    claude(setup, script).choose_cell(offered_cells(setup), [])
    (seen,) = records(script)
    assert seen["args"] == EXPECTED_ARGS
    assert "--max-turns" not in seen["args"]


def test_the_key_reaches_the_child_by_its_environment_only(tmp_path, setup,  # noqa: F811
                                                           monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "nb-other-key")
    script = fake_claude(tmp_path, reply=output({"cell": name(setup.track.cells[1]),
                                                 "brief": "b"}))
    coordinator = claude(setup, script)
    brief = coordinator.choose_cell(offered_cells(setup), ["a registry line"])
    (seen,) = records(script)
    assert co.KEY_ENV in seen["env_keys"] and seen["key_ok"] is True
    assert not any(FAKE_KEY in arg for arg in seen["args"])
    assert FAKE_KEY not in seen["stdin"]
    assert "NEBIUS_API_KEY" not in seen["env_keys"]
    assert FAKE_KEY not in repr(brief) and FAKE_KEY not in repr(coordinator.take_events())


# --- decision 163 (c): the reply and each failure ----------------------------------------


def test_a_valid_reply_gives_its_cell_and_brief(tmp_path, setup):  # noqa: F811
    cell = setup.track.cells[2]
    script = fake_claude(tmp_path, reply=output({"cell": name(cell), "brief": "Try a band."}))
    coordinator = claude(setup, script)
    assert coordinator.choose_cell(offered_cells(setup), []) == co.Brief(cell, "Try a band.")
    assert coordinator.take_events() == []
    assert coordinator.used == 42


def _not_offered(setup):  # noqa: F811
    return name(setup.track.cells[3])


@pytest.mark.parametrize("mode, reply, reason", [
    ("exit3", None, "exit status 3"),
    ("sleep", None, "timeout"),
    ("garbage", None, "not a JSON object"),
    ("ok", output("x", is_error=True), "is_error"),
    ("ok", output("Here is my choice: trend."), "the reply is not"),
    ("ok", output({"cell": "x", "brief": "b", "extra": 1}), "the reply is not"),
    ("ok", output({"cell": "x"}), "the reply is not"),
    ("ok", output({"cell": 3, "brief": "b"}), "the reply is not"),
    ("ok", "not-offered", "the cell is not offered"),
    ("missing", None, "could not start"),
])
def test_each_failure_gives_the_scripted_choice_and_the_notice(tmp_path, setup,  # noqa: F811
                                                               mode, reply, reason):
    if reply == "not-offered":
        reply = output({"cell": _not_offered(setup), "brief": "b"})
    script = fake_claude(tmp_path, mode="ok" if mode == "missing" else mode, reply=reply)
    if mode == "missing":
        script = tmp_path / "no-such-dir" / "claude"
    coordinator = claude(setup, script, timeout=1.0 if mode == "sleep" else 60.0)
    cells = offered_cells(setup)
    got = coordinator.choose_cell(cells, [])
    assert got == co.ScriptedCoordinator(setup.track).choose_cell(cells, [])
    (event,) = coordinator.take_events()
    assert (event.date, event.level, event.kind, event.subject) == \
        (D, "notice", "coordinator_fallback", "coordinator")
    assert reason in event.detail["reason"] and event.detail["task"] == "choose_cell"


def test_the_fallback_notice_reaches_the_days_events_through_choose(tmp_path,
                                                                    setup):  # noqa: F811
    script = fake_claude(tmp_path, mode="exit3")
    cells = offered_cells(setup)
    brief, events = co.choose(claude(setup, script), cells, [], setup.track,
                              setup.thresholds, D)
    assert brief.cell == co.ScriptedCoordinator(setup.track).choose_cell(cells, []).cell
    assert [(e.kind, e.detail["reason"]) for e in events] == \
        [("coordinator_fallback", "exit status 3")]


def test_the_brief_is_capped_and_sanitised(tmp_path, setup):  # noqa: F811
    cell = setup.track.cells[1]
    cap = setup.thresholds["coordinator.brief_max_chars"]
    assert cap == 600
    script = fake_claude(tmp_path, reply=output({"cell": name(cell), "brief": INJECTED}))
    brief, _ = co.choose(claude(setup, script), offered_cells(setup), [], setup.track,
                         setup.thresholds, D)
    assert brief == co.Brief(cell, INERT)
    (tmp_path / "fakebin" / "reply.json").write_text(
        json.dumps(output({"cell": name(cell), "brief": "word " * 400})), encoding="utf-8")
    brief, _ = co.choose(claude(setup, script), offered_cells(setup), [], setup.track,
                         setup.thresholds, D)
    assert len(brief.text) <= cap and brief.text == ("word " * 400)[:cap].strip()


def test_digest_and_run_log_line_return_the_replys_text(tmp_path, setup):  # noqa: F811
    script = fake_claude(tmp_path, reply=output("Two alerts fired today."))
    coordinator = claude(setup, script)
    assert coordinator.write_digest([co.AlertPayload("rank_persistence", "a1")]) == \
        "Two alerts fired today."
    assert coordinator.write_runlog_line(co.RunSummary("t", None)) == \
        "Two alerts fired today."
    first, second = records(script)
    assert '"kind": "rank_persistence"' in first["stdin"] and '"track": "t"' in \
        second["stdin"]


# --- DESIGN 14.1, I-8: no score reaches the prompt ---------------------------------------


def test_two_states_differing_only_in_scores_give_byte_identical_prompts(
        tmp_path, states, setup):  # noqa: F811
    th = setup.thresholds
    prompts = []
    for which in ("a", "b"):
        root, _ = states[which]
        cells = co.offered(co.cell_statuses(root, setup.track, th, D))
        lines = co.registry_lines(root, setup.track, th, D)
        assert lines  # the registry is not empty
        folder = tmp_path / which
        script = fake_claude(folder, reply=output({"cell": name(cells[0].cell),
                                                   "brief": "b"}))
        claude(setup, script).choose_cell(cells, lines)
        (seen,) = records(script)
        assert all(line in seen["stdin"] or json.dumps(line)[1:-1] in seen["stdin"]
                   for line in lines)
        prompts.append(seen["stdin"].encode("utf-8"))
    assert prompts[0] == prompts[1]


# --- decision 165: the day's token budget --------------------------------------------------


def test_a_reply_reaching_the_budget_sends_the_later_tasks_to_the_scripted_form(
        tmp_path, setup):  # noqa: F811
    cell = setup.track.cells[1]
    script = fake_claude(tmp_path, reply=output({"cell": name(cell), "brief": "b"},
                                                tokens=(700, 300)))
    coordinator = claude(setup, script, budget=1000)
    cells = offered_cells(setup)
    brief, events = co.choose(coordinator, cells, [], setup.track, setup.thresholds, D)
    assert brief.cell == cell and events == []  # the paid reply is used as it is
    alerts = [co.AlertPayload("group_edge", "trend/short")]
    assert coordinator.write_digest(alerts) == \
        co.ScriptedCoordinator(setup.track).write_digest(alerts)
    summary = co.RunSummary(setup.track.name, cell)
    assert coordinator.write_runlog_line(summary) == \
        co.ScriptedCoordinator(setup.track).write_runlog_line(summary)
    assert len(records(script)) == 1
    (event,) = coordinator.take_events()  # raised once
    assert (event.date, event.level, event.kind, event.subject) == \
        (D, "alert", "token_budget", "coordinator")
    assert event.detail == {"day_tokens": 1000, "tokens_per_day": 1000}
    # A new run of a day starts its sum at 0.
    coordinator.begin_day(date(2019, 4, 2))
    assert coordinator.choose_cell(cells, []).cell == cell
    assert len(records(script)) == 2


def test_the_budget_alert_reaches_the_days_events_through_choose(tmp_path,
                                                                setup):  # noqa: F811
    cell = setup.track.cells[1]
    script = fake_claude(tmp_path, reply=output({"cell": name(cell), "brief": "b"},
                                                tokens=(900, 200)))
    coordinator = claude(setup, script, budget=1000)
    cells = offered_cells(setup)
    co.choose(coordinator, cells, [], setup.track, setup.thresholds, D)
    brief, events = co.choose(coordinator, cells, [], setup.track, setup.thresholds, D)
    assert brief.cell == co.ScriptedCoordinator(setup.track).choose_cell(cells, []).cell
    assert [(e.kind, e.detail) for e in events] == \
        [("token_budget", {"day_tokens": 1100, "tokens_per_day": 1000})]


def test_the_budget_is_the_thresholds_value(tmp_path, setup):  # noqa: F811
    from discotrade.replay import make_coordinator

    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copy(CONFIG / "thresholds.toml", config / "thresholds.toml")
    script = fake_claude(tmp_path, reply=output("x"))
    set_coordinator_table(config, script)
    expected = tomllib.loads((CONFIG / "thresholds.toml").read_text(encoding="utf-8"))[
        "budgets"]["coordinator_tokens_per_day"]
    made = make_coordinator("claude", setup.track, config)
    assert isinstance(made, co.ClaudeCodeCoordinator) and made.budget == expected


# --- decision 166: the child's process group -----------------------------------------------


def _gone(pid: int) -> bool:
    """Whether ``pid`` has ended (no such process, or a zombie not yet reaped)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    except OSError:
        return True
    return fields[0] == "Z"


def _grandchild_gone_after(run, script: Path) -> bool:
    pid_file = script.parent / "grandchild.pid"
    run()
    pid = int(pid_file.read_text())
    try:
        for _ in range(100):  # a bounded wait, no clock read
            if _gone(pid):
                return True
            time.sleep(0.05)
        return False
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


def test_a_coordinator_timeout_kills_the_whole_process_group(tmp_path, setup):  # noqa: F811
    script = fake_claude(tmp_path, mode="grandchild")
    coordinator = claude(setup, script, timeout=2.0)

    def run():
        coordinator.choose_cell(offered_cells(setup), [])
        (event,) = coordinator.take_events()
        assert "timeout" in event.detail["reason"]

    assert _grandchild_gone_after(run, script)


def test_a_claude_worker_timeout_kills_the_whole_process_group(tmp_path):
    script = fake_claude(tmp_path, mode="grandchild")
    provider = pv.ClaudeWorkerProvider(script, MODEL, 2.0)

    def run():
        with pytest.raises(pv.ProviderError, match="timeout"):
            provider.complete(MODEL, [{"role": "user", "content": "x"}], 100)

    assert _grandchild_gone_after(run, script)


# --- decision 164: config/protected_paths.toml and the deny rules -------------------------

#: Decision 164 (a)'s lists, at least.
REQUIRED_CODE = [f"src/discotrade/{m}.py" for m in (
    "backtest", "costs", "executor", "metrics", "paper", "controls", "ledger", "lifecycle",
    "journal", "stats", "table", "alerts")] + [
    "src/discotrade/validation/", "src/discotrade/sandbox/", "config/", "reference/",
    "tests/gates/"]
REQUIRED_STATE = ["bars/", "rolls/", "approaches/", "trials/", "journal/", "paper/",
                  "controls/", "ledger/", "responses/", "stats/", "table/", "alerts/",
                  "dashboard/", "health/"]
#: The editing tools, as the installed Claude Code's permissions page gives them: "Edit
#: rules apply to all built-in tools that edit files".
EDIT_TOOLS = ["Edit"]
#: Decision 2026-10-19-m21 172 (b)'s entries, added to the ``code`` list.
REQUIRED_CODE_172 = ["src/discotrade/config.py", "src/discotrade/workers/providers.py",
                     "CLAUDE.md", "DESIGN.md", "SPEC.md", "PLAYBOOK.toml", "meta/", ".claude/",
                     "docs/ARCHITECT-HANDBOOK.md", "templates/"]
#: Decision 172 (a): the tools a fix session is offered, and the tools its settings deny
#: whole.
FIX_TOOLS = ["Read", "Glob", "Grep", "Edit", "Write"]
WHOLE_TOOL_DENIES = ["Bash", "WebFetch", "WebSearch"]


def protected_file() -> dict:
    return tomllib.loads((CONFIG / "protected_paths.toml").read_text(encoding="utf-8"))


def expected_rules(code_root: Path, state_dir: Path) -> list[str]:
    """Every path of both lists, as ``Edit(//<absolute>)``, ``/**`` after a directory,
    computed here from the file."""
    raw = protected_file()
    out = []
    for root, paths in ((code_root, raw["code"]), (state_dir, raw["state"])):
        for p in paths:
            absolute = (Path(root).resolve() / p.rstrip("/")).as_posix()
            pattern = "//" + absolute.lstrip("/") + ("/**" if p.endswith("/") else "")
            out += [f"{tool}({pattern})" for tool in EDIT_TOOLS]
    return out


def test_the_protected_paths_file_holds_the_decisions_paths():
    raw = protected_file()
    assert set(REQUIRED_CODE) <= set(raw["code"])
    assert set(REQUIRED_STATE) <= set(raw["state"])
    assert "digests/" not in raw["state"] and "runlog/" not in raw["state"]
    loaded = load_protected_paths(CONFIG / "protected_paths.toml")
    assert list(loaded.code) == raw["code"] and list(loaded.state) == raw["state"]


def test_every_path_is_denied_for_every_editing_tool(tmp_path):
    protected = load_protected_paths(CONFIG / "protected_paths.toml")
    state_dir = tmp_path / "state"
    rules = co.deny_rules(protected, REPO_ROOT, state_dir)
    expected = expected_rules(REPO_ROOT, state_dir)
    assert len(expected) == len(protected_file()["code"]) + len(protected_file()["state"])
    assert sorted(rules) == sorted(expected)
    assert co.session_settings(protected, REPO_ROOT, state_dir) == \
        {"permissions": {"deny": WHOLE_TOOL_DENIES + rules}}


def test_a_fix_session_started_through_the_builder_receives_exactly_those_rules(tmp_path):
    protected = load_protected_paths(CONFIG / "protected_paths.toml")
    state_dir = tmp_path / "state"
    work = tmp_path / "work"
    work.mkdir()
    script = fake_claude(tmp_path, reply=output("no fix"))
    argv = co.fix_session_command(settings_for(script), protected, REPO_ROOT, state_dir, work)
    env = {k: v for k, v in os.environ.items() if k not in pv.WITHHELD_ENV}
    done = pv.run_claude(argv, "propose a fix", env, 60.0)
    assert done.returncode == 0
    (seen,) = records(script)
    received = json.loads(seen["settings"])
    assert sorted(received) == ["permissions"] and sorted(received["permissions"]) == ["deny"]
    assert sorted(received["permissions"]["deny"]) == sorted(
        WHOLE_TOOL_DENIES + expected_rules(REPO_ROOT, state_dir))
    assert seen["args"][seen["args"].index("--settings") + 1] == str(work / "settings.json")


def test_the_protected_paths_file_holds_decision_172s_entries():
    raw = protected_file()
    assert set(REQUIRED_CODE_172) <= set(raw["code"])
    loaded = load_protected_paths(CONFIG / "protected_paths.toml")
    assert set(REQUIRED_CODE_172) <= set(loaded.code)


def test_a_fix_session_is_offered_the_file_tools_only(tmp_path):
    """Decision 172 (a): ``--tools`` once, naming exactly the five file tools in the
    installed help's comma-separated form ("Bash,Edit,Read"), and no flag that allows
    another tool; the fake receives that argument list and settings that deny Bash,
    WebFetch and WebSearch whole."""
    protected = load_protected_paths(CONFIG / "protected_paths.toml")
    work = tmp_path / "work"
    work.mkdir()
    script = fake_claude(tmp_path, reply=output("no fix"))
    argv = co.fix_session_command(settings_for(script), protected, REPO_ROOT,
                                  tmp_path / "state", work)
    env = {k: v for k, v in os.environ.items() if k not in pv.WITHHELD_ENV}
    assert pv.run_claude(argv, "propose a fix", env, 60.0).returncode == 0
    (seen,) = records(script)
    args = seen["args"]
    assert args.count("--tools") == 1
    assert args[args.index("--tools") + 1] == ",".join(FIX_TOOLS)
    assert not {"--allowedTools", "--allowed-tools"} & set(args)
    deny = json.loads(seen["settings"])["permissions"]["deny"]
    assert set(WHOLE_TOOL_DENIES) <= set(deny)


def test_nothing_calls_the_fix_session_builder():
    """``coordinator.propose_fixes`` is false (DESIGN 14.4): no module but the one
    that defines it names the builder."""
    naming = sorted(p.relative_to(REPO_ROOT).as_posix()
                    for p in (REPO_ROOT / "src").rglob("*.py")
                    if "fix_session_command" in p.read_text(encoding="utf-8"))
    assert naming == ["src/discotrade/coordinator.py"]
    assert load_run(CONFIG).coordinator.propose_fixes is False


@pytest.mark.parametrize("text, match", [
    ('code = ["/etc/passwd"]\nstate = ["bars/"]\n', "absolute"),
    ('code = ["~/x"]\nstate = ["bars/"]\n', "absolute"),
    ('code = ["src/../x.py"]\nstate = ["bars/"]\n', r"'\.\.'"),
    ('code = ["config/"]\nstate = [".."]\n', r"'\.\.'"),
    ('code = ["config/"]\nstate = []\n', "non-empty"),
    ('code = ["config/"]\n', "missing key 'state'"),
    ('code = ["config/"]\nstate = ["bars/"]\nother = 1\n', "unknown key"),
])
def test_the_file_refuses_an_absolute_or_escaping_path(tmp_path, text, match):
    path = tmp_path / "protected_paths.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match=match):
        load_protected_paths(path)


# --- decision 163 (b): the [coordinator] table ---------------------------------------------


def test_the_coordinator_table_of_run_toml():
    c = load_run(CONFIG).coordinator
    assert c is not None
    assert (c.binary, c.model, c.max_turns, c.max_budget_usd, c.timeout_seconds,
            c.propose_fixes) == ("claude", "sonnet", 1, 0.10, 300.0, False)


def test_the_coordinator_table_refuses_an_unknown_key(tmp_path):
    text = (CONFIG / "run.toml").read_text(encoding="utf-8")
    (tmp_path / "run.toml").write_text(text.replace("propose_fixes = false",
                                                    "propose_fixes = false\nturns = 2"),
                                       encoding="utf-8")
    with pytest.raises(ConfigError, match=r"unknown key 'coordinator\.turns'"):
        load_run(tmp_path)


# --- decision 163 (g): a replay of two days runs step 4 through the fake -----------------


#: Where the fixture run.toml's own [coordinator] table begins (decision 163 (b)).
TABLE_MARK = "\n# The coordinator's Claude Code form"


def set_coordinator_table(config: Path, script: Path) -> None:
    """The copied ``run.toml`` with its ``[coordinator]`` table replaced by one whose
    ``binary`` is the fake."""
    path = config / "run.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text[:text.index(TABLE_MARK)] + "\n" + coordinator_table(script),
                    encoding="utf-8")


def coordinator_table(script: Path) -> str:
    return ("\n[coordinator]\n"
            f"binary = {json.dumps(str(script))}\n"
            f'model = "{MODEL}"\nmax_turns = 1\nmax_budget_usd = {BUDGET_USD}\n'
            "timeout_seconds = 60.0\npropose_fixes = false\n")


def call(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(list(argv))
    return status, out.getvalue(), err.getvalue()


def test_a_replay_with_the_claude_coordinator_runs_step_4_through_the_fake(tmp_path):
    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copy(CONFIG / "thresholds.toml", config / "thresholds.toml")
    script = fake_claude(tmp_path, mode="first")
    set_coordinator_table(config, script)
    scripted = "scripted:" + str(corpus(tmp_path / "corpus"))
    st = fresh(tmp_path / "state")
    status, out, err = call("--state", str(st), "--config", str(config), "--track",
                            "test_synth", "replay", "--from", "2019-07-15", "--to",
                            "2019-07-16", "--provider", scripted, "--coordinator", "claude")
    assert status == 0, err
    seen = records(script)
    assert len(seen) == 2  # one choose_cell call on each day
    assert all(s["args"][-6:] == ["--permission-mode", "dontAsk", "--model", MODEL,
                                  "--tools", ""] for s in seen)
    rows = ledger.read(st, "test_synth", ledger.CALLS)
    days = sorted({r["date"] for r in rows})
    assert days == ["2019-07-15", "2019-07-16"]
    sent = [json.loads(p.read_text(encoding="utf-8"))
            for p in (st / "responses" / "test_synth").glob("*/*.json")]
    first_prompts = [d["messages"][0]["content"] for d in sent if d["attempt"] == 1]
    assert len(first_prompts) == 2 and all("BRIEF-MARK" in p for p in first_prompts)
    health = state.health_path(st, "test_synth")
    kinds = [json.loads(line)["kind"] for line in
             health.read_text(encoding="utf-8").splitlines()] if health.exists() else []
    assert "coordinator_fallback" not in kinds and "token_budget" not in kinds
    assert FAKE_KEY not in "".join(p.read_text(encoding="utf-8", errors="replace")
                                   for p in st.rglob("*") if p.is_file()
                                   and ".git" not in p.parts)


def test_registry_sanitize_is_the_brief_rule():
    # The brief rule of DESIGN 14.3 is the registry description's (decision 116 (b)).
    assert rg.sanitize(INJECTED, 600) == INERT


def test_the_production_budget_key_exists():
    th = load_thresholds(CONFIG / "thresholds.toml")
    assert th[co.BUDGET_KEY] > 0
