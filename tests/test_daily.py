"""``discotrade run-day`` (DESIGN 16.1 steps 1 and 2, 16.2, 9.2, 9.3, 15.2, 5.4,
5.6; decisions 2026-10-12 2, 3, 19, 50 to 53, 55; I-6, I-12).

Every state directory is made by ``init-state`` under a pytest temporary
directory, and its approaches are written with ``state.write_approach``
(decision 48: the function tests call in place of admission). ``run-day``
runs in-process through ``discotrade.cli.main`` on the fixture track
``test_mixed`` (SYNA rolls on 2019-06-14; SYNX drops bars). The synthetic
instruments' seeds are those of their fixture records (``SEEDS``, asserted);
no other random draw is made. Time comes only from ``--as-of``. Every git this
file runs is on local paths with ``GIT_ALLOW_PROTOCOL=file`` (decision 47).
"""

import io
import json
import os
import shutil
import subprocess
from datetime import date, timedelta

import pandas as pd
import pytest

from discotrade import journal, ledger, lifecycle, paper
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_track_config
from discotrade.sources import source_for
from discotrade.state import LOCK, STAGING, content_hash, read_approaches, write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-06-26T00:00:00+00:00"
#: The seed of every random draw these tests depend on: the synthetic sources'.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
ADMITTED = date(2019, 6, 7)
DAYS = tuple(date(2019, 6, 8) + timedelta(days=k) for k in range(5))   # 06-08 .. 06-12
NEXT = date(2019, 6, 13)


def git(repo, *args) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def show(repo, spec) -> bytes:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), "show", spec], env=env, check=True,
                          capture_output=True).stdout


def commits(state) -> list[str]:
    return git(state, "log", "--format=%s").splitlines()


def files(root) -> dict[str, tuple[bytes, int]]:
    """Every file under ``root`` but ``.git/``, with its bytes and mtime."""
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def run(state, config, *args, as_of=AS_OF):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "run-day", *args])


def run_days(state, config, days):
    for d in days:
        assert run(state, config, "--day", d.isoformat()) == 0, d


def health(state) -> list[dict]:
    path = state / "health" / f"{TRACK}.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def health_bytes(state) -> bytes | None:
    path = state / "health" / f"{TRACK}.jsonl"
    return path.read_bytes() if path.exists() else None


def admit(state, setup, name="trend_ma.py", source=None, admitted=ADMITTED, where="reference"):
    path = REPO_ROOT / where / name
    strat = load_strategy_file(path, setup.thresholds)
    return write_approach(
        state, source=path.read_text(encoding="utf-8") if source is None else source,
        params=strat.params, cell="trend/short", model_id="test-model",
        model_version="test-model-v0", cutoff=date(2019, 1, 1),
        description=f"the reference strategy {name}", profile_version="w-test",
        admitted=admitted, instruments=setup.instruments, spread_tables=setup.spread_tables)


def fresh(path, setup):
    assert main(["init-state", "--state", str(path), "--as-of", AS_OF]) == 0
    admit(path, setup, "trend_ma.py")
    admit(path, setup, "hour_of_day.py")
    return path


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("dcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def ran(tmp_path_factory, config, setup):
    """A state directory run for ``DAYS``; tests copy it and never change it."""
    state = fresh(tmp_path_factory.mktemp("dran") / "state", setup)
    run_days(state, config, DAYS)
    return state


@pytest.fixture
def state(tmp_path, ran):
    path = tmp_path / "state"
    shutil.copytree(ran, path)
    return path


# ------------------------------------------------------------------ consecutive days


def test_seeds_are_the_fixture_records(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS


def test_each_day_has_its_journal_file_index_line_paper_records_and_one_commit(ran):
    assert commits(ran) == [f"run {TRACK} {d.isoformat()}" for d in reversed(DAYS)] \
        + ["init-state"]
    assert git(ran, "status", "--porcelain") == ""
    index = journal.read_index(ran, TRACK)
    assert [e["date"] for e in index] == [d.isoformat() for d in DAYS]
    shas = git(ran, "log", "--format=%H").split()[:len(DAYS)][::-1]
    for d, sha, entry in zip(DAYS, shas, index, strict=True):
        rows = journal.read_day(ran, TRACK, d)
        assert rows is not None and len(rows) == entry["rows"] > 0
        assert entry["content_hash"] == content_hash(rows, journal.KEY)
        changed = git(ran, "show", "--name-only", "--format=", sha).split()
        day_file = f"journal/{TRACK}/{d.year:04d}/{d.isoformat()}.parquet"
        assert day_file in changed
        assert f"journal/{TRACK}/index.jsonl" in changed
        assert f"paper/{TRACK}/daily.parquet" in changed
        held = pd.read_parquet(io.BytesIO(show(ran, f"{sha}:paper/{TRACK}/daily.parquet")))
        assert sorted(set(held["date"])) == [x for x in DAYS if x <= d]
    for name in (LOCK, STAGING):
        assert not (ran / name).exists()


def test_step_1_fetches_bars_to_the_end_of_d_runs_the_gap_check_and_updates_rolls(
        state, config, setup):
    store = BarStore(state, TRACK, setup.track.bar_seconds)
    # Each instrument's bars end at the last bar of 06-12 by its own calendar.
    assert store.last_ts("SYNX") == pd.Timestamp("2019-06-12T23:00:00Z")
    assert store.last_ts("SYNA") == pd.Timestamp("2019-06-12T20:00:00Z")   # 16:00 New York
    gaps = (state / "bars" / TRACK / "gaps.jsonl").read_text(encoding="utf-8").splitlines()
    assert gaps and all(pd.Timestamp(json.loads(x)["ts"]) < pd.Timestamp("2019-06-13T00:00Z")
                        for x in gaps)
    rolls = state / "rolls" / TRACK / "SYNA.jsonl"
    before = [json.loads(x)["ts"] for x in rolls.read_text(encoding="utf-8").splitlines()]
    assert "2019-06-14T00:00:00+00:00" not in before
    run_days(state, config, [NEXT, NEXT + timedelta(days=1)])
    after = [json.loads(x)["ts"] for x in rolls.read_text(encoding="utf-8").splitlines()]
    assert after == before + ["2019-06-14T00:00:00+00:00"]
    rows = journal.read_day(state, TRACK, NEXT + timedelta(days=1))
    assert rows[rows["instrument"] == "SYNA"]["roll"].any()


def test_the_journal_equals_that_of_bars_fetched_at_once(tmp_path, ran, config, setup):
    bulk = tmp_path / "bulk"
    assert main(["--state", str(bulk), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    admit(bulk, setup, "trend_ma.py")
    admit(bulk, setup, "hour_of_day.py")
    for d in DAYS:
        journal.journal_day(bulk, setup, d)
    assert journal.read_index(bulk, TRACK) == journal.read_index(ran, TRACK)


def test_the_default_day_is_decision_19s_d_at_as_of(state, config):
    # SYNX's 06-13 closes at 06-14 00:00Z, SYNA's at 06-13 21:00Z.
    assert run(state, config, as_of="2019-06-14T00:30:00+00:00") == 0
    assert journal.read_index(state, TRACK)[-1]["date"] == NEXT.isoformat()
    assert commits(state)[0] == f"run {TRACK} {NEXT.isoformat()}"


def test_a_day_not_closed_at_as_of_is_refused(state, config, capsys):
    before = files(state)
    assert run(state, config, "--day", NEXT.isoformat(),
               as_of="2019-06-13T23:30:00+00:00") == 1
    assert "2019-06-13" in capsys.readouterr().err
    assert files(state) == before


# ------------------------------------------------------------------ re-runs and refusals


def test_running_a_finished_day_again_writes_nothing_and_makes_no_commit(state, config):
    before, log, head = files(state), health_bytes(state), commits(state)
    for d in (DAYS[-1], DAYS[1]):
        assert run(state, config, "--day", d.isoformat()) == 0
    assert files(state) == before
    assert health_bytes(state) == log
    assert commits(state) == head
    assert git(state, "status", "--porcelain") == ""
    assert len(journal.read_index(state, TRACK)) == len(DAYS)


def test_a_skipped_trading_day_exits_1_naming_it_and_writes_nothing(state, config, capsys):
    before, head = files(state), commits(state)
    assert run(state, config, "--day", (NEXT + timedelta(days=2)).isoformat()) == 1
    assert "2019-06-13" in capsys.readouterr().err
    assert files(state) == before and commits(state) == head
    assert git(state, "status", "--porcelain") == ""


def test_a_day_failing_in_step_2_moves_nothing_commits_nothing_and_releases_the_lock(
        state, config, setup, capsys):
    source = (REPO_ROOT / "reference" / "trend_ma.py").read_text(encoding="utf-8")
    bad = admit(state, setup, source=source + "# not a repository file\n")
    kept = {k: v for k, v in files(state).items()
            if k.startswith(("journal/", "paper/"))}
    head = commits(state)
    assert run(state, config, "--day", NEXT.isoformat()) == 1
    err = capsys.readouterr().err
    assert bad in err and "locked" not in err
    assert {k: v for k, v in files(state).items() if k.startswith(("journal/", "paper/"))} \
        == kept
    assert commits(state) == head
    assert not (state / LOCK).exists() and not (state / STAGING).exists()
    # The lock is free: the next run gets past it and fails for the same reason.
    assert run(state, config, "--day", NEXT.isoformat()) == 1
    assert "locked" not in capsys.readouterr().err


def test_a_held_lock_exits_1_naming_it(state, config, capsys):
    (state / LOCK).write_text("", encoding="utf-8")
    before = files(state)
    assert run(state, config, "--day", NEXT.isoformat()) == 1
    assert str(state / LOCK) in capsys.readouterr().err
    assert files(state) == before


@pytest.mark.parametrize("make", ["missing", "empty", "plain"])
def test_a_directory_init_state_did_not_make_is_refused(tmp_path, config, capsys, make):
    path = tmp_path / "notstate"
    if make != "missing":
        path.mkdir()
    if make == "plain":
        (path / "file.txt").write_text("x", encoding="utf-8")
    assert run(path, config, "--day", DAYS[0].isoformat()) == 1
    assert "init-state" in capsys.readouterr().err
    if make == "missing":
        assert not path.exists()
    else:
        assert [p.name for p in path.iterdir()] == ([] if make == "empty" else ["file.txt"])


def test_a_rerun_with_unequal_rows_raises_journal_mismatch_and_moves_nothing(state, config):
    # The test changes the stored previous day's last target_next of one
    # approach on SYNX, which the re-run of the last day starts from.
    source = (REPO_ROOT / "reference" / "trend_ma.py").read_text(encoding="utf-8")
    aid = next(a.id for a in read_approaches(state) if a.source == source)
    previous = journal.journal_path(state, TRACK, DAYS[-2])
    rows = pd.read_parquet(previous)
    mine = rows.index[(rows["subject"] == aid) & (rows["instrument"] == "SYNX")]
    last = rows.loc[mine, "ts"].idxmax()
    rows.loc[last, "target_next"] = 0.375 if rows.loc[last, "target_next"] != 0.375 else -0.375
    rows.to_parquet(previous, index=False, engine="pyarrow")
    day_file = journal.journal_path(state, TRACK, DAYS[-1])
    before, index, head = (day_file.read_bytes(), journal.index_path(state, TRACK).read_bytes(),
                           commits(state))
    assert run(state, config, "--day", DAYS[-1].isoformat()) == 1
    events = [e for e in health(state) if e["kind"] == "journal_mismatch"]
    assert [(e["subject"], e["date"], e["level"]) for e in events] == \
        [(aid, DAYS[-1].isoformat(), "alert")]
    assert day_file.read_bytes() == before
    assert journal.index_path(state, TRACK).read_bytes() == index
    assert commits(state) == head
    assert not (state / LOCK).exists() and not (state / STAGING).exists()


# ------------------------------------------------------------------ the health log


def test_no_data_gaps_at_the_repository_limit(ran):
    assert not [e for e in health(ran) if e["kind"] == "data_gaps"]


def test_data_gaps_is_appended_when_a_window_is_above_the_limit(tmp_path, config, setup):
    strict = tmp_path / "config"
    shutil.copytree(config, strict)
    text = (strict / "thresholds.toml").read_text(encoding="utf-8")
    assert "max_fraction = 0.01\n" in text
    (strict / "thresholds.toml").write_text(
        text.replace("max_fraction = 0.01\n", "max_fraction = 0.002\n"), encoding="utf-8")
    state = fresh(tmp_path / "state", setup)
    run_days(state, strict, DAYS[:3])
    events = [e for e in health(state) if e["kind"] == "data_gaps"]
    assert events and all(e["level"] == "alert" and e["subject"] == TRACK for e in events)
    for e in events:
        windows = e["detail"]["windows"]
        assert e["detail"]["over"] and e["detail"]["max_fraction"] == 0.002
        assert all(windows[w]["fraction"] > 0.002 for w in e["detail"]["over"])
        assert all(windows[w]["fraction"] <= 0.002 for w in ("W", "T")
                   if w not in e["detail"]["over"])
    log = health_bytes(state)
    run_days(state, strict, DAYS[:3])
    assert health_bytes(state) == log


def test_the_notices_of_step_1_are_appended_once(state, ran, config, setup):
    # An interrupted append (decision 5): SYNX's June file holds the next bar,
    # its index line does not.
    tc = load_track_config(config, TRACK)
    calendars = {n: load_calendar(config / "calendars" / f"{n}.toml")
                 for n in sorted({i.calendar for i in tc.instruments})}
    synx = next(i for i in tc.instruments if i.symbol == "SYNX")
    store = BarStore(state, TRACK, tc.track.bar_seconds)
    last = store.last_ts("SYNX")
    month = store.month_path("SYNX", "2019-06")
    extra = source_for("synth", calendars, tc.track.bar_seconds).fetch(
        synx, (last + pd.Timedelta(hours=1)).to_pydatetime(),
        (last + pd.Timedelta(hours=2)).to_pydatetime())
    assert len(extra) == 1
    pd.concat([pd.read_parquet(month), extra], ignore_index=True).to_parquet(
        month, index=False, engine="pyarrow")
    assert run(state, config, "--day", NEXT.isoformat()) == 0
    notices = [e for e in health(state) if e["level"] == "notice"]
    assert [(e["kind"], e["subject"], e["date"]) for e in notices] == \
        [("store_recovered", "SYNX", NEXT.isoformat())]
    log = health_bytes(state)
    assert run(state, config, "--day", NEXT.isoformat()) == 0
    assert health_bytes(state) == log
    # The completed append gives the journal of a run that was not interrupted.
    straight = state.parent / "straight"
    shutil.copytree(ran, straight)
    assert run(straight, config, "--day", NEXT.isoformat()) == 0
    assert journal.read_index(straight, TRACK) == journal.read_index(state, TRACK)


def test_a_revised_data_point_fails_the_day_with_revised_data(state, config, setup):
    month = BarStore(state, TRACK, setup.track.bar_seconds).month_path("SYNA", "2019-06")
    frame = pd.read_parquet(month)
    frame.loc[3, "close"] += 0.25
    frame.to_parquet(month, index=False, engine="pyarrow")
    head = commits(state)
    assert run(state, config, "--day", NEXT.isoformat()) == 1
    events = [e for e in health(state) if e["kind"] == "revised_data"]
    assert len(events) == 1 and events[0]["level"] == "alert"
    assert events[0]["date"] == NEXT.isoformat()
    assert journal.read_day(state, TRACK, NEXT) is None and commits(state) == head


# ------------------------------------------------------------------ time (decision 55)


def test_two_fresh_state_directories_give_equal_content_and_health(tmp_path, ran, config,
                                                                   setup):
    other = fresh(tmp_path / "other", setup)
    run_days(other, config, DAYS)
    assert journal.read_index(other, TRACK) == journal.read_index(ran, TRACK)
    assert content_hash(paper.read(other, TRACK), paper.KEY) == \
        content_hash(paper.read(ran, TRACK), paper.KEY)
    assert health_bytes(other) == health_bytes(ran)
    assert git(other, "log", "--format=%an <%ae> %at %ct %s") == \
        git(ran, "log", "--format=%an <%ae> %at %ct %s")


def test_run_day_help_exits_0(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run-day", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for option in ("--day", "--state", "--track", "--config", "--as-of"):
        assert option in out


# ------------------------------------------------------------------ the lifecycle (decision 63)
#
# ``breaks_thursday_noon.py`` (a fixture under tests/fixtures/strategies/) returns
# 2.0, outside [-1, 1], at the bar opening at 12:00 local time on a Thursday:
# the first such bar after ADMITTED is on NEXT (2019-06-13, a Thursday).

BREAKS = "breaks_thursday_noon.py"
STRATEGIES = "tests/fixtures/strategies"


def lifecycle_bytes(state) -> bytes | None:
    path = ledger.ledger_path(state, TRACK, ledger.LIFECYCLE)
    return path.read_bytes() if path.exists() else None


def ledgers(state) -> dict[str, tuple[bytes, int]]:
    return {k: v for k, v in files(state).items() if k.startswith("ledger/")}


def subjects(state, d) -> set[str]:
    """The approaches journaled on ``d`` (the controls are journaled every day,
    decision 64)."""
    rows = journal.read_day(state, TRACK, d)
    return set(rows[rows["kind"] == "approach"]["subject"])


@pytest.fixture(scope="module")
def before_break(tmp_path_factory, setup, config):
    """A state run for ``DAYS`` with two reference approaches and the one that
    breaks the contract on NEXT; tests copy it."""
    state = fresh(tmp_path_factory.mktemp("dbrk") / "state", setup)
    admit(state, setup, BREAKS, where=STRATEGIES)
    run_days(state, config, DAYS)
    return state


def test_the_breaking_fixture_breaks_only_on_next(setup):
    assert NEXT.weekday() == 3 and all(d.weekday() != 3 for d in DAYS)


def test_a_contract_failure_retires_the_approach_and_the_day_goes_on(
        tmp_path, before_break, config, setup, capsys):
    state = tmp_path / "state"
    shutil.copytree(before_break, state)
    bad = next(a.id for a in read_approaches(state) if a.params == {"weekday": 3, "hour": 12})
    others = {a.id for a in read_approaches(state)} - {bad}
    assert subjects(state, DAYS[-1]) == others | {bad}
    head = commits(state)
    assert run(state, config, "--day", NEXT.isoformat()) == 0
    out = capsys.readouterr().out
    assert commits(state) == [f"run {TRACK} {NEXT.isoformat()}"] + head
    assert git(state, "status", "--porcelain") == ""
    # Its rows of NEXT are not journaled; the others' are.
    assert subjects(state, NEXT) == others
    [row] = ledger.read(state, TRACK, ledger.LIFECYCLE)
    assert {k: row[k] for k in ("date", "id", "from", "to")} == \
        {"date": NEXT.isoformat(), "id": bad, "from": "live", "to": "retired"}
    assert row["reason"].startswith("failure: position on ")
    assert "returned 2.0, outside [-1, 1]" in row["reason"]
    assert f"lifecycle {ledger.line(row)}" in out
    changed = git(state, "show", "--name-only", "--format=", "HEAD").split()
    assert f"ledger/{TRACK}/lifecycle.jsonl" in changed
    # A re-run of NEXT appends no ledger line and writes nothing.
    before, log = files(state), lifecycle_bytes(state)
    assert run(state, config, "--day", NEXT.isoformat()) == 0
    assert files(state) == before and lifecycle_bytes(state) == log
    assert commits(state)[0] == f"run {TRACK} {NEXT.isoformat()}"
    # The retired approach is not journaled on the next day.
    following = NEXT + timedelta(days=1)
    assert run(state, config, "--day", following.isoformat()) == 0
    assert subjects(state, following) == others
    assert lifecycle_bytes(state) == log
    # The recomputation asks for no pair the journal does not hold, and matches.
    pairs = journal.journal_pairs(state, TRACK)
    assert (NEXT, bad) not in pairs and (following, bad) not in pairs
    assert (DAYS[-1], bad) in pairs
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "journal", "recompute", "--all"]) == 0


def test_a_day_failing_in_step_2_leaves_every_ledger_untouched(
        tmp_path, before_break, config, setup, capsys):
    state = tmp_path / "state"
    shutil.copytree(before_break, state)
    # A candidate admitted on the last day whose source is not a repository file:
    # its trial row, its approach and its lifecycle row are in the ledgers.
    source = (REPO_ROOT / "reference" / "zscore_reversal.py").read_text(encoding="utf-8")
    done = lifecycle.admit(state, setup, lifecycle.Candidate(
        source=source + "# not a repository file\n", params={"k": 1},
        cell="mean_reversion/short", model_id="test-model", model_version="v0",
        cutoff=date(2019, 1, 1), description="untrusted", profile_version="w-test",
        metrics_t={"sharpe": 1.0, "trades": 30}, t_days=DAYS), DAYS[-1])
    assert done.admitted
    held = ledgers(state)
    assert set(held) == {f"ledger/{TRACK}/trials.jsonl", f"ledger/{TRACK}/lifecycle.jsonl"}
    kept = {k: v for k, v in files(state).items() if k.startswith(("journal/", "paper/"))}
    head = commits(state)
    # NEXT would retire the breaking approach; the untrusted source fails the day first.
    assert run(state, config, "--day", NEXT.isoformat()) == 1
    assert done.id in capsys.readouterr().err
    assert ledgers(state) == held
    assert {k: v for k, v in files(state).items() if k.startswith(("journal/", "paper/"))} \
        == kept
    assert commits(state) == head
    assert not (state / LOCK).exists() and not (state / STAGING).exists()


def test_an_approach_admitted_on_d_is_first_journaled_on_the_next_trading_day(
        state, config, setup):
    d = DAYS[-1]
    path = REPO_ROOT / "reference" / "zscore_reversal.py"
    strat = load_strategy_file(path, setup.thresholds)
    done = lifecycle.admit(state, setup, lifecycle.Candidate(
        source=path.read_text(encoding="utf-8"), params=strat.params,
        cell="mean_reversion/short", model_id="test-model", model_version="v0",
        cutoff=date(2019, 1, 1), description="zscore", profile_version="w-test",
        metrics_t={"sharpe": 1.0, "trades": 30}, t_days=DAYS), d)
    assert (done.admitted, done.reason) == (True, "free_slot")
    # A re-run of D does not journal it: the journal of D is unchanged.
    before = {k: v for k, v in files(state).items() if k.startswith(("journal/", "paper/"))}
    assert run(state, config, "--day", d.isoformat()) == 0
    assert {k: v for k, v in files(state).items() if k.startswith(("journal/", "paper/"))} \
        == before
    assert done.id not in subjects(state, d)
    assert run(state, config, "--day", NEXT.isoformat()) == 0
    rows = journal.read_day(state, TRACK, NEXT)
    mine = rows[rows["subject"] == done.id]
    assert len(mine) and set(mine["instrument"]) == {i.symbol for i in setup.instruments}
    # Its first row on each instrument is the first bar of NEXT, flat (DESIGN 9.2).
    for _, leg in mine.groupby("instrument"):
        first = leg.loc[leg["ts"].idxmin()]
        assert first["prev_position"] == 0.0 and first["position"] == 0.0


def test_an_approach_made_dormant_on_d_is_journaled_on_d_plus_1(tmp_path, config, setup):
    # dormant_window_days 2 on a configuration copied under the test's tmp
    # directory (the production value 30 would need 30 days of runs; the rule
    # is tested at 30 in tests/test_lifecycle.py).
    low = tmp_path / "config"
    shutil.copytree(config, low)
    text = (low / "thresholds.toml").read_text(encoding="utf-8")
    assert "dormant_window_days = 30 " in text
    (low / "thresholds.toml").write_text(
        text.replace("dormant_window_days = 30 ", "dormant_window_days = 2  "), encoding="utf-8")
    state = fresh(tmp_path / "state", setup)
    run_days(state, low, DAYS[:4])
    rows = ledger.read(state, TRACK, ledger.LIFECYCLE)
    assert rows and all(r["to"] == "dormant" and r["reason"] == "dormant" for r in rows)
    first = rows[0]
    d, aid = date.fromisoformat(first["date"]), first["id"]
    assert d < DAYS[3]
    approaches = read_approaches(state)
    assert lifecycle.states(rows, approaches, d)[aid].state == "live"
    assert lifecycle.states(rows, approaches, d + timedelta(days=1))[aid].state == "dormant"
    assert aid in subjects(state, d) and aid in subjects(state, d + timedelta(days=1))
    # A re-run of D writes nothing and appends no ledger line.
    before = files(state)
    assert run(state, low, "--day", d.isoformat()) == 0
    assert files(state) == before


# ------------------------------------------------------------ step 1, once per run (mission 9 U3)


def test_a_day_builds_one_source_and_recovers_and_generates_once_per_instrument(
        state, config, setup, monkeypatch):
    import discotrade.sources as sources
    from discotrade.sources import synth

    built, recovered, generated = [], [], []
    real_for, real_recover, real_generate = sources.source_for, BarStore.recover, synth._generate

    def counted_for(adapter, calendars, bar_seconds):
        built.append(adapter)
        return real_for(adapter, calendars, bar_seconds)

    def counted_recover(self, symbol, day):
        recovered.append(symbol)
        return real_recover(self, symbol, day)

    def counted_generate(times, src, bar_seconds):
        generated.append(src.get("seed"))
        return real_generate(times, src, bar_seconds)
    monkeypatch.setattr(sources, "source_for", counted_for)
    monkeypatch.setattr(BarStore, "recover", counted_recover)
    monkeypatch.setattr(synth, "_generate", counted_generate)
    # NEXT is 2019-06-13, the day before SYNA's roll of 2019-06-14; the day
    # after it measures the roll's gap from the contracts' bars.
    for d in (NEXT, NEXT + timedelta(days=1)):
        built.clear(), recovered.clear(), generated.clear()
        assert run(state, config, "--day", d.isoformat()) == 0
        assert built == ["synth"]
        assert sorted(recovered) == sorted(SEEDS)
        assert sorted(generated) == sorted(SEEDS.values())
    rolls = [json.loads(line) for line in
             (state / "rolls" / TRACK / "SYNA.jsonl").read_text().splitlines()]
    assert [(r["old"], r["new"]) for r in rolls][-1] == ("SYNA-2019-06", "SYNA-2019-09")


def test_a_revised_earlier_month_fails_the_day_before_any_bar_is_written(state, config, setup):
    """recover reads only the files an interrupted append can leave; step 1
    still checks every stored file before it writes, so a revised data point
    in an earlier month fails the day with revised_data and no bar written."""
    store = BarStore(state, TRACK, setup.track.bar_seconds)
    month = store.month_path("SYNL", "2019-05")
    assert month.exists() and max(store.index()["SYNL"]["months"]) == "2019-06"
    frame = pd.read_parquet(month)
    frame.loc[3, "close"] += 0.25
    frame.to_parquet(month, index=False, engine="pyarrow")
    bars_before = {p: p.read_bytes() for p in sorted((state / "bars").rglob("*"))
                   if p.is_file()}
    head = commits(state)
    assert run(state, config, "--day", NEXT.isoformat()) == 1
    events = [e for e in health(state) if e["kind"] == "revised_data"]
    assert len(events) == 1 and "SYNL 2019-05" in events[0]["detail"]["error"]
    assert {p: p.read_bytes() for p in sorted((state / "bars").rglob("*"))
            if p.is_file()} == bars_before
    assert journal.read_day(state, TRACK, NEXT) is None and commits(state) == head
