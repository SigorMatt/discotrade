"""The command line skeleton (DESIGN 3; I-12, I-14)."""

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from discotrade import __version__
from discotrade.cli import REPO_ROOT, main, parse
from discotrade.clock import FixedClock, SystemClock

DISCOTRADE = Path(sys.executable).parent / "discotrade"


def test_repo_root_is_this_repository():
    assert (REPO_ROOT / "pyproject.toml").is_file()
    assert (REPO_ROOT / "src" / "discotrade" / "cli.py").is_file()


@pytest.mark.parametrize("inside", [".", "state", "meta/state", "src/discotrade"])
def test_state_inside_repository_is_refused(inside, capsys):
    with pytest.raises(SystemExit) as exc:
        parse(["--state", str(REPO_ROOT / inside)])
    assert exc.value.code == 2
    assert "inside the code repository" in capsys.readouterr().err


def test_relative_state_inside_repository_is_refused(monkeypatch, capsys):
    monkeypatch.chdir(REPO_ROOT)
    with pytest.raises(SystemExit) as exc:
        parse(["--state", "some-state"])
    assert exc.value.code == 2
    assert "inside the code repository" in capsys.readouterr().err


def test_state_from_environment_inside_repository_is_refused(monkeypatch, capsys):
    monkeypatch.setenv("DISCOTRADE_STATE", str(REPO_ROOT / "state"))
    with pytest.raises(SystemExit) as exc:
        parse([])
    assert exc.value.code == 2
    assert "inside the code repository" in capsys.readouterr().err


def test_state_outside_repository_is_accepted(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    ctx, _ = parse(["--state", str(tmp_path / "state")])
    assert ctx.state == (tmp_path / "state").resolve()


def test_state_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCOTRADE_STATE", str(tmp_path))
    ctx, _ = parse([])
    assert ctx.state == tmp_path.resolve()


def test_no_built_in_state_default(monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    ctx, _ = parse([])
    assert ctx.state is None


def test_defaults(monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    ctx, _ = parse([])
    assert ctx.track == "hourly"
    assert ctx.config == REPO_ROOT / "config"
    assert isinstance(ctx.clock, SystemClock)


def test_track_and_config(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    ctx, _ = parse(["--track", "test_synth", "--config", str(tmp_path)])
    assert ctx.track == "test_synth"
    assert ctx.config == tmp_path.resolve()


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2026-03-02T14:00:00+00:00", datetime(2026, 3, 2, 14, 0, tzinfo=UTC)),
        ("2026-03-02T14:00:00Z", datetime(2026, 3, 2, 14, 0, tzinfo=UTC)),
        ("2026-03-02T09:00:00-05:00", datetime(2026, 3, 2, 14, 0, tzinfo=UTC)),
    ],
)
def test_as_of_sets_the_clock(text, expected, monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    ctx, _ = parse(["--as-of", text])
    assert isinstance(ctx.clock, FixedClock)
    assert ctx.clock.now() == expected
    assert ctx.clock.now().utcoffset().total_seconds() == 0


@pytest.mark.parametrize("text", ["yesterday", "2026-03-02T14:00:00", "2026-13-01T00:00Z"])
def test_bad_as_of_is_a_usage_error(text, capsys, monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    with pytest.raises(SystemExit) as exc:
        parse(["--as-of", text])
    assert exc.value.code == 2
    assert "--as-of" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv", [["--no-such-option"], ["no-such-command"], [], ["--track"]]
)
def test_usage_error_exits_2(argv, monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_usage_error_exits_2_from_the_console_script(tmp_path):
    proc = subprocess.run(
        [str(DISCOTRADE), "--no-such-option"],
        capture_output=True, text=True, cwd=tmp_path, timeout=60,
    )
    assert proc.returncode == 2
    assert "usage: discotrade" in proc.stderr


def test_help_from_the_console_script(tmp_path):
    proc = subprocess.run(
        [str(DISCOTRADE), "--help"], capture_output=True, text=True, cwd=tmp_path, timeout=60
    )
    assert proc.returncode == 0
    for option in ("--state", "--track", "--config", "--as-of", "--version"):
        assert option in proc.stdout


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"discotrade {__version__}"


# --- decision 7 (REVIEW-1 should-fix 3): the refusal does not depend on the install


def _code_repository(root: Path) -> Path:
    """A directory laid out as a discotrade code repository."""
    (root / "src" / "discotrade").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nname = "discotrade"\n')
    return root


@pytest.mark.parametrize("inside", [".", "state", "meta/state/deep", "src/discotrade"])
def test_state_inside_any_code_repository_is_refused(inside, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    other = _code_repository(tmp_path / "checkout")
    before = REPO_ROOT
    with pytest.raises(SystemExit) as exc:
        parse(["--state", str(other / inside)])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "I-14" in err and "code repository" in err
    # The refusal comes from the layout, not from where the package lives.
    from discotrade import cli
    assert cli.REPO_ROOT == before
    assert not _inside(other.resolve(), REPO_ROOT)


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def test_state_inside_code_repository_from_environment_is_refused(tmp_path, monkeypatch, capsys):
    other = _code_repository(tmp_path / "checkout")
    monkeypatch.setenv("DISCOTRADE_STATE", str(other / "state"))
    with pytest.raises(SystemExit) as exc:
        parse([])
    assert exc.value.code == 2
    assert "I-14" in capsys.readouterr().err


@pytest.mark.parametrize("partial", ["pyproject.toml", "src/discotrade"])
def test_half_a_code_repository_is_not_one(partial, tmp_path, monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    root = tmp_path / "half"
    if partial == "pyproject.toml":
        root.mkdir()
        (root / "pyproject.toml").write_text("")
    else:
        (root / "src" / "discotrade").mkdir(parents=True)
    ctx, _ = parse(["--state", str(root / "state")])
    assert ctx.state == (root / "state").resolve()


@pytest.mark.parametrize("text", ["", "  ", "\t"])
def test_blank_state_is_a_usage_error(text, tmp_path, monkeypatch, capsys):
    # Outside any code repository, so that only the blank value can be refused.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    with pytest.raises(SystemExit) as exc:
        parse(["--state", text])
    assert exc.value.code == 2
    assert "--state is empty" in capsys.readouterr().err


@pytest.mark.parametrize("text", ["", " "])
def test_empty_state_environment_is_a_usage_error(text, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOTRADE_STATE", text)
    with pytest.raises(SystemExit) as exc:
        parse([])
    assert exc.value.code == 2
    assert "DISCOTRADE_STATE is empty" in capsys.readouterr().err


def test_blank_state_from_the_console_script_exits_2(tmp_path):
    proc = subprocess.run(
        [str(DISCOTRADE), "--state", "", "config", "check"],
        capture_output=True, text=True, cwd=tmp_path, timeout=60,
    )
    assert proc.returncode == 2
    assert "--state is empty" in proc.stderr


# --- the socket backstop (decision 20, I-11) ------------------------------------------


def _listener():
    """A loopback listener: a connection to it needs no network outside this host."""
    import socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server


def test_an_unmarked_test_cannot_open_a_socket():
    import socket
    with _listener() as server:
        with pytest.raises(RuntimeError, match="socket backstop"):
            socket.create_connection(server.getsockname(), timeout=5)
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(RuntimeError, match="socket backstop"):
                raw.connect(server.getsockname())
            with pytest.raises(RuntimeError, match="socket backstop"):
                raw.connect_ex(server.getsockname())
        finally:
            raw.close()
    with pytest.raises(RuntimeError, match="socket backstop"):
        socket.getaddrinfo("example.invalid", 443)


def test_an_unmarked_test_cannot_reach_a_server_through_httpx():
    import httpx
    with _listener() as server:
        host, port = server.getsockname()
        with pytest.raises(RuntimeError, match="socket backstop"):
            httpx.get(f"http://{host}:{port}/", timeout=5)


INNER_TESTS = '''
import socket

import pytest


def _listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server


def test_unmarked_forgets_its_fake():
    with _listener() as server:
        socket.create_connection(server.getsockname(), timeout=5).close()


@pytest.mark.network
def test_marked_network():
    with _listener() as server:
        socket.create_connection(server.getsockname(), timeout=5).close()


@pytest.mark.live
def test_marked_live():
    with _listener() as server:
        socket.create_connection(server.getsockname(), timeout=5).close()


def test_unix_socket_is_not_a_network_connection(tmp_path):
    path = str(tmp_path / "s")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(path)
        server.listen(1)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(path)
'''

INNER_INI = '''[pytest]
addopts = --strict-markers -p no:cacheprovider
markers =
    network: needs the network
    live: needs a secret
'''


def test_the_backstop_fails_an_unmarked_test_and_leaves_network_and_live_alone(tmp_path):
    (tmp_path / "conftest.py").write_text(
        (REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "pytest.ini").write_text(INNER_INI, encoding="utf-8")
    (tmp_path / "test_inner.py").write_text(INNER_TESTS, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-rA", "test_inner.py"], cwd=tmp_path,
        capture_output=True, text=True, timeout=120, check=False,
    )
    out = result.stdout
    assert result.returncode == 1, out + result.stderr
    assert "FAILED test_inner.py::test_unmarked_forgets_its_fake" in out
    assert "socket backstop" in out
    for name in ("test_marked_network", "test_marked_live",
                 "test_unix_socket_is_not_a_network_connection"):
        assert f"PASSED test_inner.py::{name}" in out
    assert "1 failed, 3 passed" in out


# --- init-state (DESIGN 3, 9.1; decision 50) ------------------------------------------------

def test_init_state_help_exits_0(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["init-state", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for option in ("--state", "--track", "--config", "--as-of"):
        assert option in out


def test_init_state_help_from_the_console_script(tmp_path):
    proc = subprocess.run(
        [str(DISCOTRADE), "init-state", "--help"], capture_output=True, text=True,
        cwd=tmp_path, timeout=60,
    )
    assert proc.returncode == 0
    assert "init-state" in proc.stdout


def test_init_state_is_listed_in_help(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "init-state" in capsys.readouterr().out


# --- dashboard (DESIGN 3, 15.5; decision 2026-10-17-m19 153 (a)) ---------------------------

def test_dashboard_is_listed_in_help_and_takes_out(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "dashboard" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main(["dashboard", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for option in ("--out", "--state", "--track", "--config", "--as-of"):
        assert option in out


def test_dashboard_without_a_state_is_a_usage_error(monkeypatch, capsys):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    assert main(["dashboard"]) == 2
    assert "--state" in capsys.readouterr().err


# --- --coordinator claude, refused before any day (decision 2026-10-18-m20 163 (e)) -------


def _coordinator_config(tmp_path, table):
    """``tests/fixtures/config/`` copied under tmp with the production thresholds,
    its run.toml's ``[coordinator]`` table replaced by ``table`` (none when None)."""
    import shutil

    from conftest import FIXTURE_CONFIG

    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    path = config / "run.toml"  # the fixture's own [coordinator] table removed
    text = path.read_text(encoding="utf-8")
    text = text[:text.index("\n# The coordinator's Claude Code form")] + "\n"
    path.write_text(text if table is None else text + "\n[coordinator]\n" + table,
                    encoding="utf-8")
    return config


def _coordinator_table(binary):
    return (f'binary = "{binary}"\nmodel = "m"\nmax_turns = 1\nmax_budget_usd = 0.1\n'
            "timeout_seconds = 10.0\npropose_fixes = false\n")


def _state_files(state):
    return sorted(p.relative_to(state).as_posix() for p in state.rglob("*")
                  if p.is_file() and ".git" not in p.relative_to(state).parts)


@pytest.mark.parametrize("command", ["run-day", "replay"])
@pytest.mark.parametrize("case, status, needle", [
    ("no table", 2, "[coordinator]"),
    ("no key", 2, "ANTHROPIC_API_KEY"),
    ("no binary", 1, "not found on PATH"),
])
def test_coordinator_claude_is_refused_before_any_day(tmp_path, monkeypatch, capsys,
                                                      command, case, status, needle):
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-key")
    fake = tmp_path / "claude"
    fake.write_text(f"#!{sys.executable}\nraise SystemExit(9)\n", encoding="utf-8")
    fake.chmod(0o755)
    table = {"no table": None, "no key": _coordinator_table(fake),
             "no binary": _coordinator_table(tmp_path / "missing" / "claude")}[case]
    if case == "no key":
        monkeypatch.delenv("ANTHROPIC_API_KEY")
    config = _coordinator_config(tmp_path, table)
    state = tmp_path / "state"
    assert main(["init-state", "--state", str(state),
                 "--as-of", "2019-06-03T00:00:00+00:00"]) == 0
    capsys.readouterr()
    before = _state_files(state)
    common = ["--state", str(state), "--config", str(config), "--track", "test_synth"]
    if command == "run-day":
        argv = [*common, "--as-of", "2019-07-15T21:00:00+00:00", "run-day", "--day",
                "2019-07-15"]
    else:
        argv = [*common, "replay", "--from", "2019-07-15", "--to", "2019-07-15"]
    assert main([*argv, "--coordinator", "claude"]) == status
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.strip().splitlines()
    assert len(lines) == 1, lines
    assert needle in lines[0] and "--coordinator claude" in lines[0]
    assert "sk-test-not-a-key" not in captured.err
    assert _state_files(state) == before


def test_coordinator_scripted_stays_the_default():
    from discotrade.replay import COORDINATORS

    _, args = parse(["--state", "/tmp/x", "run-day"])
    assert args.coordinator == "scripted" == COORDINATORS[0]
    assert "claude" in COORDINATORS
