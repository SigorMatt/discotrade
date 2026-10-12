"""``discotrade replay`` (DESIGN 16.4, 16.1, 3; decisions 2026-10-12 19, 51, 55, 72;
I-6, I-12).

Every state directory is made by ``init-state`` under a pytest temporary
directory at ``INIT_AS_OF``, with one approach written by
``state.write_approach`` (decision 48). The commands run in-process through
``discotrade.cli.main``. Two fixture tracks:

- ``test_mixed`` on a configuration copied under tmp with the production
  ``config/thresholds.toml``, replayed from 2019-06-07 (a Friday) to
  2019-06-10 (a Monday): its SYNX is always open, so the Saturday and the
  Sunday are trading days of the track (decision 51);
- ``test_synth`` on the gate configuration (decision 72: a copy of
  ``tests/fixtures/config/`` under tmp with
  ``tests/fixtures/config/thresholds_gate.toml`` copied in unchanged as its
  ``thresholds.toml``), replayed from 2019-06-06 (a Thursday) to 2019-06-11
  (a Tuesday): all its instruments are on ``synth_week``, so the weekend is
  not.

The synthetic instruments' seeds are those of their fixture records
(``SEEDS``, asserted); no other random draw is made. Time comes only from
``--as-of`` and the replay's clock; the instants each day is expected to run
at are written below, worked out from the calendars by hand (``synth_week``'s
day rolls at 17:00 New York, 21:00 UTC in June, its last bar opening at 16:00
New York; ``always_open``'s day is the UTC date, its last bar opening at
23:00 UTC). Every git run here is on local paths with
``GIT_ALLOW_PROTOCOL=file`` (decision 47).
"""

import contextlib
import io
import os
import shutil
import subprocess
from datetime import date, datetime

import pytest

from discotrade import journal
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_track_config
from discotrade.replay import replay_days
from discotrade.state import write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104, "SYNL": 105, "SYNX": 106}

#: Per track: the span, the admission date of its approach, and every trading
#: day of the span with the close of its last expected bar among the track's
#: instruments.
CASES = {
    "test_mixed": {
        "span": (date(2019, 6, 7), date(2019, 6, 10)),
        "admitted": date(2019, 6, 6),
        "days": [
            # Fri: SYNA/SYNL close 21:00 UTC, SYNX at midnight UTC.
            (date(2019, 6, 7), "2019-06-08T00:00:00+00:00"),
            (date(2019, 6, 8), "2019-06-09T00:00:00+00:00"),   # Sat: SYNX only
            (date(2019, 6, 9), "2019-06-10T00:00:00+00:00"),   # Sun: SYNX only
            (date(2019, 6, 10), "2019-06-11T00:00:00+00:00"),
        ],
    },
    "test_synth": {
        "span": (date(2019, 6, 6), date(2019, 6, 11)),
        "admitted": date(2019, 6, 5),
        "days": [
            (date(2019, 6, 6), "2019-06-06T21:00:00+00:00"),
            (date(2019, 6, 7), "2019-06-07T21:00:00+00:00"),
            # Sat and Sun are not trading days: Sunday 18:00 New York opens Monday.
            (date(2019, 6, 10), "2019-06-10T21:00:00+00:00"),
            (date(2019, 6, 11), "2019-06-11T21:00:00+00:00"),
        ],
    },
}
TRACKS = tuple(CASES)


def git(repo, *args) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def files(root) -> dict[str, bytes]:
    """Every file under ``root`` but ``.git/``, with its bytes."""
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def head(state) -> str:
    return git(state, "rev-parse", "HEAD").strip()


def tree(state) -> str:
    return git(state, "rev-parse", "HEAD^{tree}").strip()


def call(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:   # argparse's usage errors
            status = exc.code
    return status, out.getvalue(), err.getvalue()


def replay(state, config, track, first, last, *extra):
    return call("--state", str(state), "--config", str(config), "--track", track,
                "replay", "--from", first.isoformat(), "--to", last.isoformat(), *extra)


def fresh(path, config, track):
    """A state directory made by init-state with the track's one approach."""
    assert main(["init-state", "--state", str(path), "--as-of", INIT_AS_OF]) == 0
    setup = journal.Setup.load(config, track)
    src = REPO_ROOT / "reference" / "trend_ma.py"
    strat = load_strategy_file(src, setup.thresholds)
    write_approach(
        path, source=src.read_text(encoding="utf-8"), params=strat.params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description="the reference strategy trend_ma.py",
        profile_version="w-test", admitted=CASES[track]["admitted"],
        instruments=setup.instruments, spread_tables=setup.spread_tables)
    return path


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def configs(tmp_path_factory):
    """test_mixed: the fixtures with the production thresholds; test_synth: the
    gate configuration (decision 72), thresholds_gate.toml copied unchanged."""
    root = tmp_path_factory.mktemp("rcfg")
    mixed = root / "mixed"
    shutil.copytree(FIXTURE_CONFIG, mixed)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", mixed / "thresholds.toml")
    gate = root / "gate"
    shutil.copytree(FIXTURE_CONFIG, gate)
    shutil.copy(FIXTURE_CONFIG / "thresholds_gate.toml", gate / "thresholds.toml")
    assert (gate / "thresholds.toml").read_bytes() == \
        (FIXTURE_CONFIG / "thresholds_gate.toml").read_bytes()
    return {"test_mixed": mixed, "test_synth": gate}


@pytest.fixture(scope="module")
def replayed(tmp_path_factory, configs):
    """Per track: a state replayed over its span, with the command's output."""
    done = {}
    for track in TRACKS:
        state = fresh(tmp_path_factory.mktemp("rrep") / "state", configs[track], track)
        done[track] = (state, *replay(state, configs[track], track, *CASES[track]["span"]))
    return done


@pytest.fixture
def copied(tmp_path, replayed):
    """Per track: a copy of the replayed state, for a test that changes it."""
    out = {}
    for track in TRACKS:
        path = tmp_path / track
        shutil.copytree(replayed[track][0], path)
        out[track] = path
    return out


# ------------------------------------------------------------------ the days


def test_seeds_are_the_fixture_records(configs):
    for track in TRACKS:
        tc = load_track_config(configs[track], track)
        for inst in tc.instruments:
            assert inst.source.get("seed") == SEEDS[inst.symbol]


@pytest.mark.parametrize("track", TRACKS)
def test_days_are_the_track_trading_days_with_their_close(configs, track):
    """Every trading day from A to B, both included, ascending, each with the
    close of its last expected bar."""
    setup = journal.Setup.load(configs[track], track)
    tc = load_track_config(configs[track], track)
    got = list(replay_days(tc, dict(setup.calendars), *CASES[track]["span"]))
    assert got == [(d, datetime.fromisoformat(t)) for d, t in CASES[track]["days"]]
    first, last = CASES[track]["span"]
    assert list(replay_days(tc, dict(setup.calendars), last, last)) == [got[-1]]
    assert list(replay_days(tc, dict(setup.calendars), last, first)) == []


@pytest.mark.parametrize("track", TRACKS)
def test_replay_prints_one_line_per_day_and_exits_0(replayed, track):
    _, status, out, err = replayed[track]
    assert status == 0, err
    lines = out.splitlines()
    assert len(lines) == len(CASES[track]["days"])
    for line, (d, instant) in zip(lines, CASES[track]["days"], strict=True):
        assert line.startswith(f"replay: {track} {d.isoformat()} at {instant}: journal written,")


@pytest.mark.parametrize("track", TRACKS)
def test_each_day_runs_at_its_close_in_order(replayed, track):
    """The commits of the replay, oldest first: one per day, in ascending
    order, each dated by the clock it ran with (decision 50)."""
    state = replayed[track][0]
    log = git(state, "log", "--reverse", "--format=%s|%aI|%cI").splitlines()
    assert log[0].startswith("init")
    want = [f"run {track} {d.isoformat()}|{t}|{t}" for d, t in CASES[track]["days"]]
    assert [x.replace("Z", "+00:00") for x in log[1:]] == want
    index = [e["date"] for e in journal.read_index(state, track)]
    assert index == [d.isoformat() for d, _ in CASES[track]["days"]]


@pytest.mark.parametrize("track", TRACKS)
def test_replay_equals_run_day_day_by_day(tmp_path, configs, replayed, track):
    """The same days run one by one through run-day with those --as-of
    instants give the same files, byte for byte outside .git/, and tree."""
    state = fresh(tmp_path / "state", configs[track], track)
    for d, instant in CASES[track]["days"]:
        status, _, err = call("--state", str(state), "--config", str(configs[track]),
                              "--track", track, "--as-of", instant, "run-day",
                              "--day", d.isoformat())
        assert status == 0, (d, err)
    rep = replayed[track][0]
    assert files(state) == files(rep)
    assert tree(state) == tree(rep)
    assert head(state) == head(rep)


@pytest.mark.parametrize("track", TRACKS)
def test_two_replays_into_fresh_states_are_identical(tmp_path, configs, replayed, track):
    state = fresh(tmp_path / "state", configs[track], track)
    status, _, err = replay(state, configs[track], track, *CASES[track]["span"])
    assert status == 0, err
    rep = replayed[track][0]
    assert files(state) == files(rep)
    assert tree(state) == tree(rep)


@pytest.mark.parametrize("track", TRACKS)
def test_replaying_a_journaled_span_writes_nothing(copied, configs, track):
    state = copied[track]
    before, sha = files(state), head(state)
    status, out, err = replay(state, configs[track], track, *CASES[track]["span"])
    assert status == 0, err
    assert files(state) == before
    assert head(state) == sha
    lines = out.splitlines()
    assert len(lines) == len(CASES[track]["days"])
    assert all("already journaled with equal rows; nothing written" in x for x in lines)


# ------------------------------------------------------------------ failures


@pytest.mark.parametrize("track", TRACKS)
def test_a_failing_day_stops_the_replay_naming_it(tmp_path, configs, monkeypatch, track):
    """The third day fails (a journal error injected for that day only): exit
    1 naming it, the two days before committed, nothing of it or after."""
    days = CASES[track]["days"]
    bad = days[2][0]
    real = journal.journal_day

    def failing(state_dir, setup, d, **kw):
        if d == bad:
            raise journal.JournalError("injected failure")
        return real(state_dir, setup, d, **kw)

    monkeypatch.setattr(journal, "journal_day", failing)
    state = fresh(tmp_path / "state", configs[track], track)
    status, out, err = replay(state, configs[track], track, *CASES[track]["span"])
    assert status == 1
    assert f"{track} {bad.isoformat()}" in err and "injected failure" in err
    assert len(out.splitlines()) == 2
    subjects = git(state, "log", "--reverse", "--format=%s").splitlines()[1:]
    assert subjects == [f"run {track} {d.isoformat()}" for d, _ in days[:2]]
    assert [e["date"] for e in journal.read_index(state, track)] == \
        [d.isoformat() for d, _ in days[:2]]


@pytest.mark.parametrize("track", TRACKS)
def test_from_after_to_is_a_usage_error(copied, configs, track):
    state = copied[track]
    before, sha = files(state), head(state)
    first, last = CASES[track]["span"]
    status, out, err = replay(state, configs[track], track, last, first)
    assert status == 2
    assert out == "" and "is after --to" in err
    assert files(state) == before and head(state) == sha


def test_as_of_and_unknown_options_are_refused(copied, configs):
    state, track = copied["test_synth"], "test_synth"
    before, sha = files(state), head(state)
    first, last = CASES[track]["span"]
    assert call("--state", str(state), "--config", str(configs[track]), "--track", track,
                "--as-of", "2019-06-30T00:00:00+00:00", "replay", "--from",
                first.isoformat(), "--to", last.isoformat())[0] == 2
    assert replay(state, configs[track], track, first, last, "--provider", "x")[0] == 2
    assert files(state) == before and head(state) == sha


def test_a_day_after_a_gap_is_refused_as_run_day_refuses_it(copied, configs):
    """Journal ends 2019-06-11; a replay from 2019-06-13 leaves 06-12 out."""
    state, track = copied["test_synth"], "test_synth"
    before, sha = files(state), head(state)
    status, out, err = replay(state, configs[track], track, date(2019, 6, 13),
                              date(2019, 6, 13))
    assert status == 1
    assert "2019-06-13" in err and "2019-06-12 is a trading day" in err
    assert out == ""
    assert files(state) == before and head(state) == sha


def test_run_day_takes_a_day_one_instrument_does_not_trade_at_its_close(tmp_path, configs):
    """test_mixed's Saturday 2019-06-08 runs at its close, 2019-06-09 00:00 UTC
    (SYNA and SYNL closed Friday); a day with a bar still open is refused: at
    2019-06-10 22:00 UTC, SYNA's Monday has closed, SYNX's has not."""
    track, config = "test_mixed", configs["test_mixed"]
    state = fresh(tmp_path / "state", config, track)

    def run_day(as_of, day):
        return call("--state", str(state), "--config", str(config), "--track", track,
                    "--as-of", as_of, "run-day", "--day", day)

    assert run_day("2019-06-08T00:00:00+00:00", "2019-06-07")[0] == 0
    assert run_day("2019-06-09T00:00:00+00:00", "2019-06-08")[0] == 0
    assert run_day("2019-06-10T00:00:00+00:00", "2019-06-09")[0] == 0
    sha = head(state)
    status, _, err = run_day("2019-06-10T22:00:00+00:00", "2019-06-10")
    assert status == 1
    assert "2019-06-10 has not closed" in err and "SYNX" in err
    assert head(state) == sha
