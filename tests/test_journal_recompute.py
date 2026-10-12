"""``discotrade journal recompute`` (DESIGN 9.4, 15.2; decision 2026-10-12 54; I-6).

Every state directory is made by ``init-state`` under a pytest temporary
directory, run with ``run-day`` over consecutive days of the fixture track
``test_mixed`` (synthetic sources; their seeds are those of their fixture
records, ``SEEDS``, asserted), and its approaches written with
``state.write_approach`` (decision 48). The command runs in-process through
``discotrade.cli.main``; time comes only from ``--as-of``. The only random
draw is the command's sample, seeded with ``D`` as ``YYYYMMDD``; the test
computes the expected draw with the same seed (``seed_of``). The thresholds
are the repository's, copied into the test's configuration directory; the
sample tests use a copy whose ``journal.recompute_sample`` is ``SAMPLE``,
written under their temporary directory (the frozen file is not changed).
No git is run here.
"""

import json
import shutil
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade import journal
from discotrade.cli import REPO_ROOT, main
from discotrade.state import LOCK, read_approaches, write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-06-26T00:00:00+00:00"
#: The seed of every synthetic source these tests depend on.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
ADMITTED = date(2019, 6, 7)
DAYS = tuple(date(2019, 6, 8) + timedelta(days=k) for k in range(5))   # 06-08 .. 06-12
#: ``--as-of`` instants and decision 19's ``D`` at each (SYNX closes at 00:00Z).
AS_OF_D = {"2019-06-11T00:00:00+00:00": date(2019, 6, 10),
           "2019-06-12T00:00:00+00:00": date(2019, 6, 11)}
SAMPLE = 3


def seed_of(day: date) -> int:
    return int(day.strftime("%Y%m%d"))


def admit(state, setup, name):
    path = REPO_ROOT / "reference" / name
    strat = load_strategy_file(path, setup.thresholds)
    return write_approach(
        state, source=path.read_text(encoding="utf-8"), params=strat.params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description=f"the reference strategy {name}",
        profile_version="w-test", admitted=ADMITTED, instruments=setup.instruments,
        spread_tables=setup.spread_tables)


def files(root) -> dict[str, tuple[bytes, int]]:
    """Every file under ``root``, ``.git/`` included, with its bytes and mtime."""
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()}


def recompute(state, config, *args, as_of=AS_OF):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "journal", "recompute", *args])


def pairs_printed(out: str) -> list[tuple[str, str, str]]:
    """The (verdict, day, subject) of each pair line the command printed."""
    out_pairs = []
    for line in out.splitlines():
        word, *rest = line.split()
        if word in ("equal", "MISMATCH"):
            out_pairs.append((word, rest[0], rest[1]))
    return out_pairs


def health(state) -> list[str]:
    path = state / "health" / f"{TRACK}.jsonl"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("rcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def small(tmp_path_factory, config):
    """The configuration with ``journal.recompute_sample`` = ``SAMPLE``."""
    path = tmp_path_factory.mktemp("rsmall") / "config"
    shutil.copytree(config, path)
    text = (path / "thresholds.toml").read_text(encoding="utf-8")
    assert text.count("recompute_sample = 20\n") == 1
    (path / "thresholds.toml").write_text(
        text.replace("recompute_sample = 20\n", f"recompute_sample = {SAMPLE}\n"),
        encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def ran(tmp_path_factory, config, setup):
    """A state directory run for ``DAYS``; tests copy it and never change it."""
    state = tmp_path_factory.mktemp("rran") / "state"
    assert main(["init-state", "--state", str(state), "--as-of", AS_OF]) == 0
    admit(state, setup, "trend_ma.py")
    admit(state, setup, "hour_of_day.py")
    for d in DAYS:
        assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                     "--as-of", AS_OF, "run-day", "--day", d.isoformat()]) == 0, d
    return state


@pytest.fixture
def state(tmp_path, ran):
    path = tmp_path / "state"
    shutil.copytree(ran, path)
    return path


@pytest.fixture
def subjects(ran):
    return sorted(a.id for a in read_approaches(ran))


def every_pair(subjects, before=None):
    return [(d.isoformat(), s) for d in DAYS for s in subjects
            if before is None or d < before]


# ------------------------------------------------------------------ --all


def test_seeds_are_the_fixture_records(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS


def test_all_matches_every_pair_exits_0_and_writes_nothing(state, config, subjects, capsys):
    assert len(subjects) == 2
    before = files(state)
    assert recompute(state, config, "--all") == 0
    out = capsys.readouterr().out
    assert pairs_printed(out) == [("equal", d, s) for d, s in every_pair(subjects)]
    assert files(state) == before
    assert not (state / LOCK).exists()


def test_one_changed_field_exits_1_prints_the_pair_and_appends_one_journal_mismatch(
        state, config, subjects, capsys):
    changed, subject = DAYS[2], subjects[1]
    path = journal.journal_path(state, TRACK, changed)
    rows = pd.read_parquet(path)
    row = rows.index[rows["subject"] == subject][3]
    rows.loc[row, "net_1x"] = rows.loc[row, "net_1x"] + 1e-6
    rows.to_parquet(path, index=False, engine="pyarrow")
    journal_dir = state / "journal"
    before, log = files(journal_dir), health(state)

    assert recompute(state, config, "--all") == 1
    out = capsys.readouterr().out
    expected = [("MISMATCH" if (d, s) == (changed.isoformat(), subject) else "equal", d, s)
                for d, s in every_pair(subjects)]
    assert pairs_printed(out) == expected
    after = health(state)
    assert after[:len(log)] == log and len(after) == len(log) + 1
    event = json.loads(after[-1])
    assert (event["kind"], event["level"], event["date"], event["subject"]) == \
        ("journal_mismatch", "alert", changed.isoformat(), subject)
    assert files(journal_dir) == before
    assert not (state / LOCK).exists()


# ------------------------------------------------------------------ the sample


def expected_sample(subjects, d, n, seed):
    pool = every_pair(subjects, before=d)
    if len(pool) <= n:
        return pool
    picks = np.random.default_rng(seed).choice(len(pool), size=n, replace=False)
    return [pool[k] for k in sorted(int(k) for k in picks)]


@pytest.mark.parametrize("as_of", sorted(AS_OF_D))
def test_the_sample_is_drawn_with_d_from_days_before_d_the_same_on_every_run(
        state, small, subjects, capsys, as_of):
    d = AS_OF_D[as_of]
    before = files(state)
    printed = []
    for _ in range(2):
        assert recompute(state, small, as_of=as_of) == 0
        printed.append(pairs_printed(capsys.readouterr().out))
    assert printed[0] == printed[1]
    got = [(day, s) for _, day, s in printed[0]]
    assert len(got) == SAMPLE
    assert all(date.fromisoformat(day) < d for day, _ in got)
    assert got == expected_sample(subjects, d, SAMPLE, seed_of(d))
    assert files(state) == before


def test_the_sample_differs_from_one_seeded_otherwise(subjects):
    # The pool of D = 06-11 has 6 pairs; a draw seeded with anything but D
    # gives another sample, so the test above tells the seeds apart.
    d = date(2019, 6, 11)
    mine = expected_sample(subjects, d, SAMPLE, seed_of(d))
    for other in (d.toordinal(), seed_of(d.replace(year=2018)), 0):
        assert expected_sample(subjects, d, SAMPLE, other) != mine


def test_fewer_pairs_than_the_sample_recomputes_every_pair_before_d(state, config, subjects,
                                                                     capsys):
    as_of = "2019-06-12T00:00:00+00:00"
    d = AS_OF_D[as_of]
    assert recompute(state, config, as_of=as_of) == 0
    got = [(day, s) for _, day, s in pairs_printed(capsys.readouterr().out)]
    assert got == every_pair(subjects, before=d)
    assert len(got) < 20


def test_journal_recompute_help_exits_0(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["journal", "recompute", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for option in ("--all", "--state", "--track", "--config", "--as-of"):
        assert option in out
