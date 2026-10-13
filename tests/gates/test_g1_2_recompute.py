"""G1.2: the journal recomputes exactly; running the last day again writes
nothing; a second replay from scratch gives the same content hashes (DESIGN
18.3 G1.2, 18.2, 9.2, 9.4, 16.2, 16.4; decisions 2026-10-12 54, 64, 72, 74;
I-5, I-6, I-12).

The scenario of G1.3 (``tests/fixtures/scenarios/g1_lifecycle.jsonl``, decision
73) is replayed on the fixture track ``test_synth`` and decision 72's gate
configuration, in-process through ``discotrade.cli.main``, from ``FIRST``
2019-06-03 (the track's ``epoch``) to ``LAST`` 2019-08-02, 60 calendar days
later, into a state made by ``init-state`` under the test's tmp directory at
``INIT_AS_OF``; the test first asserts that the state then holds approaches,
controls, the draws of three months (June, July and August: two monthly
redraws), completed rank-persistence blocks and lifecycle rows. Then:

- ``journal recompute --all`` (at ``--as-of`` ``RECOMPUTE_AS_OF``) exits 0 and
  prints ``equal`` for every (day, subject) pair of the journal, read here
  from the day files with pyarrow, and their count; it changes no file and
  makes no commit;
- running the last day again (``replay --from LAST --to LAST``) leaves every
  file's bytes and ``HEAD`` unchanged;
- a second replay of the same span with the same options into a fresh state
  directory gives identical bytes for every file outside ``.git/`` and the
  same tree at ``HEAD`` (decision 72's last sentence).

Seeds: the synthetic instruments' seeds are those of their fixture records
(``SEEDS``, asserted); the random pool is seeded by decision 64 with the
month (201906, 201907, 201908, asserted). No other random draw is made. Time
comes only from ``--as-of`` and the replay's clock. Every git run is on local
paths with ``GIT_ALLOW_PROTOCOL=file`` (decision 47, in ``m1_harness``).
"""

import shutil
from datetime import date, timedelta

import pyarrow.parquet as pq
import pytest
from m1_harness import call, files, gate_config, head, init_state, read_jsonl, replay, tree

from discotrade.cli import REPO_ROOT
from discotrade.config import load_track_config

pytestmark = [pytest.mark.gate, pytest.mark.gate_m1]

TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
RECOMPUTE_AS_OF = "2019-08-02T21:00:00+00:00"
SCENARIO = REPO_ROOT / "tests" / "fixtures" / "scenarios" / "g1_lifecycle.jsonl"
FIRST, LAST = date(2019, 6, 3), date(2019, 8, 2)
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
POOL_SEEDS = [201906, 201907, 201908]


def run_scenario(root):
    config = gate_config(root)
    state = init_state(root / "state", INIT_AS_OF)
    status, out, err = replay(state, config, TRACK, FIRST, LAST,
                              "--candidates", str(SCENARIO))
    assert status == 0, err
    return state, config


@pytest.fixture(scope="module")
def first(tmp_path_factory):
    return run_scenario(tmp_path_factory.mktemp("g12a"))


@pytest.fixture(scope="module")
def second(tmp_path_factory):
    return run_scenario(tmp_path_factory.mktemp("g12b"))


def journal_pairs(state) -> set[tuple[str, str]]:
    pairs = set()
    for line in read_jsonl(state / "journal" / TRACK / "index.jsonl"):
        d = date.fromisoformat(line["date"])
        path = state / "journal" / TRACK / f"{d.year:04d}" / f"{d.isoformat()}.parquet"
        subjects = pq.read_table(path, columns=["subject"]).column("subject").to_pylist()
        pairs |= {(d.isoformat(), s) for s in subjects}
    return pairs


def test_span_seeds_and_what_the_state_holds(first):
    state, config = first
    assert (LAST - FIRST).days >= 60
    tc = load_track_config(config, TRACK)
    assert {inst.symbol: inst.source.get("seed") for inst in tc.instruments} == SEEDS
    assert tc.track.epoch == FIRST
    assert len(list((state / "approaches").iterdir())) >= 1
    pools = read_jsonl(state / "controls" / TRACK / "pools.jsonl")
    assert [p["seed"] for p in pools] == POOL_SEEDS
    assert len(read_jsonl(state / "stats" / TRACK / "rank_persistence.jsonl")) >= 1
    assert len(read_jsonl(state / "ledger" / TRACK / "lifecycle.jsonl")) >= 1
    subjects = {s for _, s in journal_pairs(state)}
    assert any(s.startswith("rc:") for s in subjects)
    assert any(s.startswith("bh:") for s in subjects)
    assert any(s.startswith("a") for s in subjects)
    days = read_jsonl(state / "journal" / TRACK / "index.jsonl")
    assert days[0]["date"] == FIRST.isoformat() and days[-1]["date"] == LAST.isoformat()


def test_journal_recompute_all_matches_every_pair(first, tmp_path):
    state = tmp_path / "state"
    shutil.copytree(first[0], state, symlinks=True)
    before, sha = files(state), head(state)
    status, out, err = call("--state", str(state), "--config", str(first[1]), "--track", TRACK,
                            "--as-of", RECOMPUTE_AS_OF, "journal", "recompute", "--all")
    assert status == 0, err
    pairs = journal_pairs(state)
    lines = out.splitlines()
    assert lines[-1] == f"journal recompute: {TRACK}: {len(pairs)} pairs recomputed, 0 mismatched"
    reported = [tuple(x.split(" ")) for x in lines[:-1]]
    assert all(r[0] == "equal" and len(r) == 3 for r in reported)
    assert len(reported) == len(pairs)
    assert {(r[1], r[2]) for r in reported} == pairs
    assert files(state) == before and head(state) == sha


def test_running_the_last_day_again_writes_nothing(first, tmp_path):
    state = tmp_path / "state"
    shutil.copytree(first[0], state, symlinks=True)
    before, sha = files(state), head(state)
    status, out, err = replay(state, first[1], TRACK, LAST, LAST)
    assert status == 0, err
    assert "already journaled with equal rows; nothing written" in out
    assert files(state) == before
    assert head(state) == sha


def test_a_second_replay_from_scratch_gives_the_same_state(first, second):
    a, b = files(first[0]), files(second[0])
    assert sorted(a) == sorted(b)
    for name in a:
        assert a[name] == b[name], name
    assert tree(first[0]) == tree(second[0])
    assert LAST - timedelta(days=60) == FIRST
