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
