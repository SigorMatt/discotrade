"""The catch-up of missed days with ``day_caught_up`` (decision 183 of
meta/decisions/decisions-2026-10-19-m22.md; DESIGN 16.1, 15.2; SPEC §11; decision
2026-10-12 51, which it replaces).

When the journal holds a day before ``D`` and trading days of the track between the
last journaled day and ``D`` have no journal file, ``run-day`` runs them first,
oldest first, each as its own day (own staging, own retry, own commit), each with a
``day_caught_up`` alert dated that day appended at its start, then ``D``; a missed
day that fails twice ends the run.

Every state directory is a copy of conftest's ``mixed_ran_template`` (track
``test_mixed``, whose instrument SYNX trades every calendar day; ``RAN_DAYS``
2019-06-08 to 2019-06-12 run at ``RAN_AS_OF``) under a pytest temporary directory;
``run-day`` runs in-process through ``discotrade.cli.main`` at ``--as-of``
``RAN_AS_OF``. Failures are injected by ``monkeypatch`` of one step's function. The
synthetic sources' seeds are their fixture records'; no other random draw is made.
Every git is on local paths with ``GIT_ALLOW_PROTOCOL=file`` (decision 47).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
from conftest import FIXTURE_CONFIG, RAN_AS_OF, RAN_DAYS, REPO_ROOT, copy_template

from discotrade import daily, journal, table
from discotrade.cli import main
from discotrade.state import LOCK, STAGING

TRACK = "test_mixed"
#: Three trading days after the last journaled day 2019-06-12: two missed days, then D.
MISSED = (date(2019, 6, 13), date(2019, 6, 14))
D = date(2019, 6, 15)


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def commits(state: Path) -> list[str]:
    return git(state, "log", "--format=%s").splitlines()


def tree(root: Path) -> dict[str, bytes]:
    """The bytes of every file under ``root``, ``.git/`` left out."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and p.relative_to(root).parts[0] != ".git"}


def health_path(state: Path) -> Path:
    return state / "health" / f"{TRACK}.jsonl"


def of_kind(state: Path, kind: str) -> list[dict]:
    path = health_path(state)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    return [e for e in map(json.loads, lines) if e["kind"] == kind]


def run(state: Path, config: Path, day: date, *extra: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(["--state", str(state), "--config", str(config), "--track", TRACK,
                       "--as-of", RAN_AS_OF, "run-day", "--day", day.isoformat(), *extra])
    return status, out.getvalue(), err.getvalue()


def journaled(state: Path) -> list[str]:
    return [e["date"] for e in journal.read_index(state, TRACK)]


@pytest.fixture(autouse=True)
def _git_local(monkeypatch):
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("ccfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def ran(tmp_path_factory, mixed_ran_template):
    assert RAN_DAYS[-1] == date(2019, 6, 12)
    return copy_template(mixed_ran_template, tmp_path_factory.mktemp("cran") / "state")


def test_the_missed_days_and_d_are_trading_days_of_the_track(config):
    setup = journal.Setup.load(config, TRACK)
    from discotrade.config import load_track_config

    tc = load_track_config(config, TRACK)
    assert all(daily.is_trading_day(tc, setup.calendars, d) for d in (*MISSED, D))


def test_missed_days_run_first_oldest_first_each_committed_with_day_caught_up(
        tmp_path, ran, config):
    state = copy_template(ran, tmp_path / "state")
    head = commits(state)
    issues = tmp_path / "issues"
    status, out, err = run(state, config, D, "--issues", f"file:{issues}")
    assert status == 0, err
    # The two missed days, then D, journaled in order, three commits.
    assert journaled(state) == [d.isoformat() for d in (*RAN_DAYS, *MISSED, D)]
    assert commits(state) == [f"run {TRACK} {d.isoformat()}" for d in (D, *MISSED[::-1])] \
        + head
    assert git(state, "status", "--porcelain") == ""
    assert not (state / LOCK).exists() and not (state / STAGING).exists()
    # Two day_caught_up alerts, each dated its day, naming the day and D.
    caught = [{"date": d.isoformat(), "level": "alert", "kind": "day_caught_up",
               "subject": TRACK, "detail": {"day": d.isoformat(), "run_for": D.isoformat()}}
              for d in MISSED]
    assert of_kind(state, daily.DAY_CAUGHT_UP) == caught
    # The command prints each caught-up day's lines before D's.
    lines = out.splitlines()
    done = [k for k, x in enumerate(lines) if x.startswith(f"run-day: {TRACK} ")]
    assert [lines[k].split()[2] for k in done] == \
        [f"{d.isoformat()}:" for d in (*MISSED, D)]
    assert f"alert {json.dumps(caught[0], sort_keys=True)}" in lines[:done[0]]
    assert f"alert {json.dumps(caught[1], sort_keys=True)}" in lines[done[0]:done[1]]
    # The first caught-up day's step 6 sees its alert and its step 8 opens its issue.
    first = (issues / TRACK / "0001.md").read_text(encoding="utf-8")
    assert first.startswith(f"title: day_caught_up {TRACK} {MISSED[0].isoformat()}\n"
                            f"labels: discotrade, health, day_caught_up\n")
    # The days run one by one, each given the same day_caught_up line before it,
    # give the same files: the catch-up differs from them only by those alerts.
    straight = copy_template(ran, tmp_path / "straight")
    by_day = {e["date"]: json.dumps(e, sort_keys=True) for e in caught}
    for d in (*MISSED, D):
        if d.isoformat() in by_day:
            health_path(straight).parent.mkdir(exist_ok=True)
            with health_path(straight).open("a", encoding="utf-8") as f:
                f.write(by_day[d.isoformat()] + "\n")
        assert run(straight, config, d)[0] == 0, d
    assert tree(state) == tree(straight)


def test_a_missed_day_failing_twice_ends_the_run_and_leaves_d_unrun(
        tmp_path, ran, config, monkeypatch):
    state = copy_template(ran, tmp_path / "state")
    real = table.build
    bad = MISSED[1]

    def build(state_dir, setup, day, *args, **kwargs):
        if day == bad:
            raise daily.DailyError(f"injected failure on {day.isoformat()}")
        return real(state_dir, setup, day, *args, **kwargs)

    monkeypatch.setattr(table, "build", build)
    status, out, err = run(state, config, D)
    assert status == 1
    assert f"injected failure on {bad.isoformat()}" in err
    assert journaled(state) == [d.isoformat() for d in (*RAN_DAYS, MISSED[0])]
    assert commits(state)[0] == f"run {TRACK} {MISSED[0].isoformat()}"
    assert journal.read_day(state, TRACK, bad) is None
    assert journal.read_day(state, TRACK, D) is None
    [failed] = of_kind(state, daily.RUN_FAILED)
    assert (failed["date"], failed["detail"]["day"]) == (bad.isoformat(), bad.isoformat())
    assert [e["date"] for e in of_kind(state, daily.DAY_CAUGHT_UP)] == \
        [d.isoformat() for d in MISSED]
    assert not (state / LOCK).exists() and not (state / STAGING).exists()


def test_the_default_d_catches_up_too(tmp_path, ran, config):
    """Decision 19's ``D`` at 2019-06-15 00:30 UTC is 2019-06-14 (SYNX's last bar of
    06-14 closes at 06-15 00:00 UTC, SYNA's at 06-14 20:00 UTC): the missed day
    2019-06-13 runs first, as with ``--day``."""
    state = copy_template(ran, tmp_path / "state")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(["--state", str(state), "--config", str(config), "--track", TRACK,
                       "--as-of", "2019-06-15T00:30:00+00:00", "run-day"])
    assert status == 0, err.getvalue()
    assert journaled(state) == [d.isoformat() for d in (*RAN_DAYS, *MISSED)]
    assert [(e["date"], e["detail"]["run_for"]) for e in of_kind(state, daily.DAY_CAUGHT_UP)] \
        == [(MISSED[0].isoformat(), MISSED[1].isoformat())]
