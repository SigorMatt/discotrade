"""The state directory, the lock, the state commit and the health log
(DESIGN 3, 9.1, 15.2, 16.2; decisions 7, 50, 52, 55 of
meta/decisions/decisions-2026-10-12.md; I-5, I-12, I-14).

Every git this file runs is on local paths with ``GIT_ALLOW_PROTOCOL=file``
(decision 47). Time comes only from a ``FixedClock`` or ``--as-of``.
"""

import os
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from discotrade import state as st
from discotrade.cli import main
from discotrade.clock import FixedClock
from discotrade.state import HealthEvent, StateError

#: An instant far from any wall clock this suite runs under.
INSTANT = datetime(2020, 1, 6, 12, 30, 15, tzinfo=UTC)
AS_OF = INSTANT.isoformat()


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    result = subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                            capture_output=True, text=True)
    return result.stdout


def tree(root: Path) -> dict[str, tuple[bytes, int]]:
    """Every file under ``root`` (``.git`` included) with its bytes and mtime."""
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()}


def init(path: Path) -> int:
    return main(["init-state", "--state", str(path), "--as-of", AS_OF])


# --- init-state ---------------------------------------------------------------------------

def test_init_state_creates_a_committed_git_repository(tmp_path):
    state = tmp_path / "state"
    assert init(state) == 0
    assert (state / ".git").is_dir()
    assert (state / ".gitignore").read_text(encoding="utf-8") == st.GITIGNORE
    assert git(state, "status", "--porcelain") == ""
    assert git(state, "ls-files").split() == [".gitignore"]
    assert git(state, "rev-list", "--count", "HEAD").strip() == "1"
    log = git(state, "log", "-1", "--format=%an <%ae>|%cn <%ce>|%at|%ct")
    stamp = str(int(INSTANT.timestamp()))
    assert log.strip() == f"discotrade <discotrade@invalid>|discotrade <discotrade@invalid>|" \
                          f"{stamp}|{stamp}"
    assert st.is_state_directory(state)


@pytest.mark.parametrize("path, ignored", [
    ("bars/hourly/ES/2026-01.parquet", True),
    ("bars/daily/X/2026-02.parquet", True),
    ("staging/journal/hourly/2026/2026-01-05.parquet", True),
    ("lock", True),
    ("bars/hourly/index.json", False),
    ("health/hourly.jsonl", False),
    ("journal/hourly/2026/2026-01-05.parquet", False),
    ("journal/hourly/index.jsonl", False),
])
def test_gitignore_ignores_bar_parquet_staging_and_lock(tmp_path, path, ignored):
    state = tmp_path / "state"
    assert init(state) == 0
    target = state / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x")
    result = subprocess.run(["git", "-C", str(state), "check-ignore", "-q", path],
                            env={**os.environ, "GIT_ALLOW_PROTOCOL": "file"})
    assert (result.returncode == 0) is ignored


def test_init_state_into_an_existing_empty_directory(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    assert init(state) == 0
    assert st.is_state_directory(state)


def test_a_second_init_state_changes_nothing_and_exits_0(tmp_path, capsys):
    state = tmp_path / "state"
    assert init(state) == 0
    before = tree(state)
    head = git(state, "rev-parse", "HEAD")
    later = datetime(2021, 5, 5, tzinfo=UTC).isoformat()
    assert main(["init-state", "--state", str(state), "--as-of", later]) == 0
    assert tree(state) == before
    assert git(state, "rev-parse", "HEAD") == head
    assert "already" in capsys.readouterr().out


@pytest.mark.parametrize("content", ["file", "dir", "git-only"])
def test_a_non_empty_directory_that_is_not_a_state_directory_exits_1(tmp_path, content, capsys):
    state = tmp_path / "state"
    state.mkdir()
    if content == "file":
        (state / "notes.txt").write_text("mine", encoding="utf-8")
    elif content == "dir":
        (state / "sub").mkdir()
    else:
        git(state, "init", "-q")
    before = tree(state)
    assert init(state) == 1
    assert tree(state) == before
    assert "not a state directory" in capsys.readouterr().err


def test_a_path_that_is_a_file_exits_1(tmp_path):
    path = tmp_path / "state"
    path.write_text("x", encoding="utf-8")
    assert init(path) == 1
    assert path.read_text(encoding="utf-8") == "x"


def test_init_state_inside_a_code_repository_exits_2(tmp_path, capsys):
    repo = tmp_path / "code"
    (repo / "src" / "discotrade").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        init(repo / "state")
    assert exc.value.code == 2
    assert "I-14" in capsys.readouterr().err
    assert not (repo / "state").exists()


def test_init_state_without_a_state_directory_exits_2(monkeypatch, capsys):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    assert main(["init-state", "--as-of", AS_OF]) == 2
    assert "--state" in capsys.readouterr().err


def test_init_state_takes_the_common_options(tmp_path):
    state = tmp_path / "state"
    assert main(["init-state", "--state", str(state), "--track", "test_synth",
                 "--config", str(tmp_path), "--as-of", AS_OF]) == 0
    assert st.is_state_directory(state)


def test_require_state_directory_refuses_one_init_state_did_not_make(tmp_path):
    with pytest.raises(StateError, match="not a state directory"):
        st.require_state_directory(tmp_path)
    st.init_state(tmp_path / "s", FixedClock(INSTANT))
    st.require_state_directory(tmp_path / "s")


# --- the lock -----------------------------------------------------------------------------

def test_a_second_lock_while_one_is_held_fails_naming_it(tmp_path):
    with st.lock(tmp_path):
        assert (tmp_path / st.LOCK).exists()
        with pytest.raises(StateError) as exc:
            with st.lock(tmp_path):
                pass  # pragma: no cover
        assert str(tmp_path / st.LOCK) in str(exc.value)
        assert (tmp_path / st.LOCK).exists()  # the failed attempt left the held lock
    assert not (tmp_path / st.LOCK).exists()


def test_the_lock_is_released_after_a_failure_inside_it(tmp_path):
    with pytest.raises(RuntimeError, match="boom"):
        with st.lock(tmp_path):
            raise RuntimeError("boom")
    assert not (tmp_path / st.LOCK).exists()
    with st.lock(tmp_path):
        pass


# --- the state commit ---------------------------------------------------------------------

def test_a_state_commit_has_the_message_author_and_dates_of_the_clock(tmp_path):
    state = tmp_path / "state"
    st.init_state(state, FixedClock(datetime(2019, 3, 4, tzinfo=UTC)))
    (state / "health").mkdir()
    (state / "health" / "hourly.jsonl").write_text("{}\n", encoding="utf-8")
    sha = st.commit(state, "hourly", date(2020, 1, 6), FixedClock(INSTANT))
    assert sha == git(state, "rev-parse", "HEAD").strip()
    out = git(state, "log", "-1", "--format=%s|%an <%ae>|%cn <%ce>|%at|%ct")
    stamp = str(int(INSTANT.timestamp()))
    assert out.strip().split("|") == [
        "run hourly 2020-01-06", "discotrade <discotrade@invalid>",
        "discotrade <discotrade@invalid>", stamp, stamp,
    ]
    assert git(state, "status", "--porcelain") == ""


def test_a_state_commit_ignores_bar_parquet_staging_and_lock(tmp_path):
    state = tmp_path / "state"
    st.init_state(state, FixedClock(INSTANT))
    for path in ("bars/hourly/ES/2020-01.parquet", "staging/x", "lock"):
        (state / path).parent.mkdir(parents=True, exist_ok=True)
        (state / path).write_bytes(b"x")
    (state / "bars" / "hourly" / "index.json").write_text("{}", encoding="utf-8")
    assert st.commit(state, "hourly", date(2020, 1, 6), FixedClock(INSTANT)) is not None
    assert sorted(git(state, "ls-files").split()) == [".gitignore", "bars/hourly/index.json"]


def test_a_commit_with_nothing_changed_is_not_made(tmp_path):
    state = tmp_path / "state"
    st.init_state(state, FixedClock(INSTANT))
    head = git(state, "rev-parse", "HEAD")
    assert st.commit(state, "hourly", date(2020, 1, 6), FixedClock(INSTANT)) is None
    assert git(state, "rev-parse", "HEAD") == head
    assert git(state, "rev-list", "--count", "HEAD").strip() == "1"


def test_git_runs_with_only_the_file_protocol(tmp_path):
    assert st.git_environment()["GIT_ALLOW_PROTOCOL"] == "file"


# --- the health log -----------------------------------------------------------------------

def event(kind: str = "data_gaps", subject: str = "ES", **detail) -> HealthEvent:
    return HealthEvent(date=date(2020, 1, 6), level="notice", kind=kind, subject=subject,
                       detail=detail)


def test_the_health_log_appends_one_to_json_line_per_event(tmp_path):
    events = [event("a", n=1), event("b", n=2)]
    assert st.append_health(tmp_path, "hourly", events) == events
    path = st.health_path(tmp_path, "hourly")
    assert path == tmp_path / "health" / "hourly.jsonl"
    assert path.read_text(encoding="utf-8") == "".join(e.to_json() + "\n" for e in events)


def test_the_health_log_keeps_every_earlier_line_byte_identical(tmp_path):
    path = st.health_path(tmp_path, "hourly")
    path.parent.mkdir(parents=True)
    earlier = (b'{"an": "earlier line, not in to_json form"}\n'
               + event("x").to_json().encode() + b"\n")
    path.write_bytes(earlier)
    inode = path.stat().st_ino
    new = event("y", why="z")
    assert st.append_health(tmp_path, "hourly", [new]) == [new]
    data = path.read_bytes()
    assert data == earlier + new.to_json().encode() + b"\n"
    # Written beside and renamed into place, not appended in place (decision 4).
    assert path.stat().st_ino != inode
    assert not path.with_name(path.name + ".tmp").exists()


def test_a_failed_health_append_leaves_the_log_unchanged(tmp_path, monkeypatch):
    st.append_health(tmp_path, "hourly", [event("x")])
    path = st.health_path(tmp_path, "hourly")
    before = path.read_bytes()

    def boom(*args, **kwargs):
        raise OSError("disk gone")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="disk gone"):
        st.append_health(tmp_path, "hourly", [event("y")])
    assert path.read_bytes() == before


def test_the_health_log_does_not_append_a_line_already_present(tmp_path):
    first = [event("a"), event("b")]
    st.append_health(tmp_path, "hourly", first)
    path = st.health_path(tmp_path, "hourly")
    before = (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_ino)
    assert st.append_health(tmp_path, "hourly", [event("b"), event("a")]) == []
    assert (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_ino) == before
    # Within one call, an event given twice is appended once; a new one still is.
    again = [event("c"), event("c"), event("a")]
    assert st.append_health(tmp_path, "hourly", again) == [event("c")]
    assert path.read_text(encoding="utf-8").splitlines() == [
        event("a").to_json(), event("b").to_json(), event("c").to_json()]


def test_no_events_write_no_file(tmp_path):
    assert st.append_health(tmp_path, "hourly", []) == []
    assert not st.health_path(tmp_path, "hourly").exists()


def test_a_health_log_with_a_torn_last_line_is_refused(tmp_path):
    path = st.health_path(tmp_path, "hourly")
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"torn"')
    with pytest.raises(StateError, match="newline"):
        st.append_health(tmp_path, "hourly", [event("a")])
    assert path.read_bytes() == b'{"torn"'
