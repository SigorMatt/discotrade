"""What a warm process writes equals a full recompute with every cache cleared
(O-26 items 3 and 5 of meta/decisions/2026-10-18-owner.md; decision 157 (c) of
meta/decisions/decisions-2026-10-18-m20.md; DESIGN 10.4, 15.3, 15.5, 16.4;
I-6, I-12).

A scripted replay runs on the fixture track ``test_synth`` with decision 72's
gate configuration (``tests/fixtures/config/`` copied under the test's
temporary directory with ``thresholds_gate.toml`` copied in, unchanged, as its
``thresholds.toml``) and the candidates file of gate G1.3,
``tests/fixtures/scenarios/g1_lifecycle.jsonl``, over Monday 2019-06-03 to
Friday 2019-06-07 (``DAYS``), twice, from ``init-state`` at ``INIT_AS_OF``,
in this one process, through ``discotrade.cli.main``:

- warm: every cache cleared once (as a new process starts), then one
  ``replay`` over the span, so that each day reuses what the days before it
  kept in the process;
- cold: ``state.clear_caches`` called before every day, each day its own
  ``replay``, so that each day computes everything from the records.

Inside the span the scenario admits ``always_flat`` on 2019-06-03 (``FIRST``,
a lifecycle row to ``live``), refuses two candidates, and admits
``breaks_thursday_noon`` at 12:00 on 2019-06-06 (``CHANGE``, a lifecycle row
to ``live`` on a day with an approach already live) and at 13:00 on
2019-06-07 (``LAST``). For every day, the tree of the state repository's
commit ``run test_synth <D>`` is the same in both states. On ``FIRST``,
``CHANGE`` and ``LAST`` the test also reads, at that day's commit of each
state, ``table/<track>/table.json``, ``table.md``, ``alerts/<track>/state.json``,
every file under ``alerts/<track>/payloads/<D>/`` and
``dashboard/<track>/index.html``, and asserts them byte for byte: the same
blob (git's hash of the bytes) and the same text.

The synthetic instruments' seeds are their fixture records'; no other random
draw is made. Time comes only from ``--as-of`` and the replay's clock. Git
runs through ``state._git``, on local paths with ``GIT_ALLOW_PROTOCOL=file``
(decision 47).
"""

import contextlib
import io
import json
import shutil
from datetime import date

from discotrade import state as state_mod
from discotrade.cli import REPO_ROOT, main

TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
SCENARIO = REPO_ROOT / "tests" / "fixtures" / "scenarios" / "g1_lifecycle.jsonl"
FIRST, CHANGE, LAST = date(2019, 6, 3), date(2019, 6, 6), date(2019, 6, 7)
DAYS = (date(2019, 6, 3), date(2019, 6, 4), date(2019, 6, 5), date(2019, 6, 6),
        date(2019, 6, 7))
NAMED = (f"table/{TRACK}/table.json", f"table/{TRACK}/table.md",
         f"alerts/{TRACK}/state.json", f"dashboard/{TRACK}/index.html")


def call(*argv: str) -> int:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(list(argv))
    assert status == 0, err.getvalue()
    return status


def git(repo, *args: str) -> str:
    return state_mod._git(repo, *args).stdout


def replay(state, config, first: date, last: date) -> None:
    call("--state", str(state), "--config", str(config), "--track", TRACK, "replay",
         "--from", first.isoformat(), "--to", last.isoformat(), "--candidates", str(SCENARIO))


def commits(state) -> dict[str, str]:
    """``run test_synth <D>`` -> its commit's sha, from the log."""
    out = {}
    for line in git(state, "log", "--format=%H %s").splitlines():
        sha, subject = line.split(" ", 1)
        out[subject] = sha
    return out


def tree(state, sha: str) -> str:
    return git(state, "rev-parse", f"{sha}^{{tree}}").strip()


def files_at(state, sha: str, day: date) -> dict[str, tuple[str, str]]:
    """The named files and the day's payloads at commit ``sha``: each one's blob
    and text."""
    listed = git(state, "ls-tree", "-r", "--name-only", sha).splitlines()
    payloads = f"alerts/{TRACK}/payloads/{day.isoformat()}/"
    names = [n for n in listed if n in NAMED or n.startswith(payloads)]
    return {n: (git(state, "rev-parse", f"{sha}:{n}").strip(),
                git(state, "show", f"{sha}:{n}")) for n in sorted(names)}


def test_a_warm_replay_writes_what_a_cold_recompute_writes_on_every_day(tmp_path):
    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copyfile(FIXTURE_CONFIG / "thresholds_gate.toml", config / "thresholds.toml")
    warm, cold = tmp_path / "warm", tmp_path / "cold"
    for where in (warm, cold):
        call("init-state", "--state", str(where), "--as-of", INIT_AS_OF)

    state_mod.clear_caches()
    replay(warm, config, DAYS[0], DAYS[-1])
    for d in DAYS:
        state_mod.clear_caches()
        replay(cold, config, d, d)

    lifecycle = [json.loads(x) for x in
                 (warm / "ledger" / TRACK / "lifecycle.jsonl").read_text("utf-8").splitlines()]
    assert {r["date"] for r in lifecycle} == {FIRST.isoformat(), CHANGE.isoformat(),
                                               LAST.isoformat()}
    assert FIRST == DAYS[0] and LAST == DAYS[-1] and FIRST < CHANGE < LAST

    w, c = commits(warm), commits(cold)
    for d in DAYS:
        message = f"run {TRACK} {d.isoformat()}"
        assert message in w and message in c, d
        assert tree(warm, w[message]) == tree(cold, c[message]), d

    for d in (FIRST, CHANGE, LAST):
        message = f"run {TRACK} {d.isoformat()}"
        mine, theirs = files_at(warm, w[message], d), files_at(cold, c[message], d)
        assert set(NAMED) <= set(mine), (d, sorted(mine))
        assert mine == theirs, d
