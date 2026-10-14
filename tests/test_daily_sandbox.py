"""Approaches in the day loop behind the sandbox (DESIGN 12.4, 16.1 step 2, 16.4,
9.4; decision 2026-10-14-m13 105; decisions 2026-10-12 23, 44, 48, 49, 63, 72;
I-6, I-7, I-12).

Every state directory is made by ``init-state`` under a pytest temporary
directory, at ``AS_OF``, and its approaches are written with
``state.write_approach`` (decision 48), their fixed parameters written here
(``PARAMS``) so that no test needs the decision-21 loader. Days run on the
fixture track ``test_synth`` (four synthetic instruments, seeds ``SEEDS``,
asserted; no other random draw is made), in-process through
``discotrade.cli.main`` or through the functions it calls, with the
configuration of ``tests/fixtures/config/`` copied under the temporary
directory with the production ``config/thresholds.toml``. Time comes only from
``--as-of`` or the replay's clock (decision 72). ``LIMITED`` is that copy with
a shorter wall-clock limit in its ``run.toml`` (said so where used); the
track holding a non-synthetic instrument is the fixture track ``test_crypto``
of a copy of the same configuration. The test marked ``container`` starts
containers of the image of the current tag (``discotrade sandbox build``, run
beforehand as a setup step), mounts only job directories under its temporary
directory, and leaves none behind.
"""

import contextlib
import io
import shutil
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest

from discotrade import journal, ledger, replay, strategy
from discotrade.backtest import _strategy_targets, read_window
from discotrade.cli import REPO_ROOT, main
from discotrade.clock import FixedClock
from discotrade.config import DateRange, load_track_config
from discotrade.daily import run_day as day_function
from discotrade.sandbox import container
from discotrade.sandbox.base import (
    SandboxChoiceError,
    SandboxResult,
    SandboxUnavailable,
    choose_backend,
)
from discotrade.sandbox.container import ContainerSandbox
from discotrade.sandbox.process import ProcessSandbox
from discotrade.state import LOCK, STAGING, write_approach

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
NON_SYNTHETIC = "test_crypto"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
AS_OF = "2019-06-03T00:00:00+00:00"
ADMITTED = date(2019, 6, 3)
FIRST, LAST = date(2019, 6, 3), date(2019, 6, 6)       # Monday to Thursday
APPROACH_DAYS = (date(2019, 6, 4), date(2019, 6, 5), date(2019, 6, 6))
THURSDAY = date(2019, 6, 6)
#: ``(directory, file, fixed parameters)`` of each approach the replays admit.
TREND = ("reference", "trend_ma.py", {"fast": 24, "slow": 96})
HOURS = ("reference", "hour_of_day.py", {"start_hour": 9, "end_hour": 16})
#: Returns 2.0 at the bar opening at 12:00 local time on a Thursday (its docstring).
BREAKS = ("tests/fixtures/strategies", "breaks_thursday_noon.py", {"weekday": 3, "hour": 12})
#: Never returns (its docstring).
ENDLESS = ("tests/fixtures/strategies", "endless_loop.py", {"step": 1})
#: The wall-clock limit of ``LIMITED``'s run.toml, shorter than the production
#: 1200 s so that the endless loop ends in a test; its CPU-time limit stays far
#: above it, so that the wall clock is the limit reached.
SHORT_WALL = 5.0


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:   # argparse's usage errors
            status = exc.code
    return status, out.getvalue(), err.getvalue()


def files(root: Path) -> dict[str, bytes]:
    """Every file under ``root`` but ``.git/``, with its bytes."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def nothing_of_the_day(state, day):
    """What a failed day leaves: the step-1 bars may stay (DESIGN 16.1); no journal
    file or index line of ``day``, no ledger line, no commit, no lock or staging."""
    return {"journal": journal.journal_path(state, TRACK, day).exists(),
            "index": journal.index_path(state, TRACK).read_bytes(),
            "ledger": {k: v for k, v in files(state).items() if k.startswith("ledger/")},
            "head": git_head(state),
            "lock": (state / LOCK).exists(), "staging": (state / STAGING).exists()}


def git_head(state) -> bytes:
    """The commit ``HEAD`` names, read from the files (no git process)."""
    ref = (state / ".git" / "HEAD").read_text(encoding="utf-8").split(":", 1)[1].strip()
    return (state / ".git" / ref).read_bytes()


def copy_config(root, wall_seconds=None):
    path = root / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    if wall_seconds is not None:
        run = path / "run.toml"
        text = run.read_text(encoding="utf-8")
        assert "wall_seconds = 1200.0" in text and "cpu_seconds = 1200.0" in text
        run.write_text(text.replace("wall_seconds = 1200.0", f"wall_seconds = {wall_seconds}"),
                       encoding="utf-8")
    return path


def init(path):
    status, _, err = call("init-state", "--state", str(path), "--as-of", AS_OF)
    assert status == 0, err
    return path


def admit(state, setup, which, source=None):
    where, name, params = which
    text = (REPO_ROOT / where / name).read_text(encoding="utf-8")
    return write_approach(
        state, source=text if source is None else source, params=params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description=f"the fixture {name}", profile_version="w-test",
        admitted=ADMITTED, instruments=setup.instruments, spread_tables=setup.spread_tables)


def common(state, config, track=TRACK):
    return ("--state", str(state), "--config", str(config), "--track", track)


def run_day(state, config, day, *extra):
    return call(*common(state, config), "--as-of", f"{day.isoformat()}T23:00:00+00:00",
                "run-day", "--day", day.isoformat(), *extra)


def replay_cli(state, config, first=FIRST, last=LAST, *extra):
    return call(*common(state, config), "replay", "--from", first.isoformat(),
                "--to", last.isoformat(), *extra)


def approach_rows(state, day):
    rows = journal.read_day(state, TRACK, day)
    return rows[rows["kind"] == journal.KIND_APPROACH]


def no_loader(*_args, **_kwargs):
    raise AssertionError("the decision-21 loader was called on the day loop's path")


def patch_loader(mp):
    """The decision-21 loader made to raise wherever it is reached."""
    mp.setattr(strategy, "load_strategy", no_loader)
    mp.setattr(strategy, "load_strategy_file", no_loader)


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return copy_config(tmp_path_factory.mktemp("dsbcfg"))


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def replayed(tmp_path_factory, config, setup):
    """A replay of FIRST..LAST on the default backend with TREND, HOURS and BREAKS
    admitted on ADMITTED, the decision-21 loader patched to raise throughout."""
    state = init(tmp_path_factory.mktemp("dsbrep") / "state")
    ids = {name: admit(state, setup, which)
           for name, which in (("trend", TREND), ("hours", HOURS), ("breaks", BREAKS))}
    with pytest.MonkeyPatch.context() as mp:
        patch_loader(mp)
        status, out, err = replay_cli(state, config)
    return state, ids, status, out, err


# ------------------------------------------------------------------ fixtures' facts


def test_the_synthetic_seeds_are_the_ones_written_here(config):
    tc = load_track_config(config, TRACK)
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS
    assert {i.source.adapter for i in tc.instruments} == {"synth"}
    crypto = load_track_config(config, NON_SYNTHETIC)
    assert {i.source.adapter for i in crypto.instruments} == {"crypto"}


def test_the_dates_are_the_weekdays_written_here():
    assert [d.weekday() for d in (FIRST, *APPROACH_DAYS)] == [0, 1, 2, 3]
    assert THURSDAY == LAST


# ------------------------------------------------------------------ 105 (b): the backend


def test_the_default_is_process_on_test_synth(config):
    assert choose_backend(load_track_config(config, TRACK).instruments) == "process"
    assert choose_backend(load_track_config(config, TRACK).instruments, "container") \
        == "container"


def test_the_default_is_container_on_a_track_with_a_non_synthetic_source(tmp_path):
    # A configuration copied under the temporary directory; its track test_crypto
    # holds CRYA, read through the crypto adapter.
    config = copy_config(tmp_path)
    instruments = load_track_config(config, NON_SYNTHETIC).instruments
    assert choose_backend(instruments) == "container"
    assert choose_backend(instruments, "container") == "container"
    with pytest.raises(SandboxChoiceError, match=r"DESIGN 12\.4"):
        choose_backend(instruments, "process")


@pytest.mark.parametrize("command", [
    ("--as-of", "2019-06-04T23:00:00+00:00", "run-day", "--day", "2019-06-04"),
    ("replay", "--from", "2019-06-03", "--to", "2019-06-04"),
    ("journal", "recompute", "--all"),
])
def test_process_is_refused_on_a_track_with_a_non_synthetic_source(tmp_path, command):
    # A configuration copied under the temporary directory; test_crypto holds CRYA.
    config = copy_config(tmp_path)
    state = init(tmp_path / "state")
    before, head = files(state), git_head(state)
    status, out, err = call(*common(state, config, NON_SYNTHETIC), *command,
                            "--sandbox", "process")
    assert status == 2
    assert "DESIGN 12.4" in err and "CRYA" in err and "--sandbox process is refused" in err
    assert files(state) == before and git_head(state) == head


def test_run_day_refuses_process_on_that_track_before_reading_the_state(tmp_path):
    config = copy_config(tmp_path)
    missing = tmp_path / "no-state"
    with pytest.raises(SandboxChoiceError, match=r"DESIGN 12\.4"):
        day_function(missing, config, NON_SYNTHETIC, FixedClock(datetime(2019, 6, 5, tzinfo=UTC)),
                     date(2019, 6, 4), sandbox="process")
    assert not missing.exists()


def test_the_sandbox_option_reaches_the_backend_of_each_command(tmp_path, monkeypatch, setup):
    config = copy_config(tmp_path)
    state = init(tmp_path / "state")
    admit(state, setup, TREND)
    opened = []

    def recording(name, scratch, config_dir):
        opened.append(name)
        return ProcessSandbox(scratch, fork_server=True)

    monkeypatch.setattr(journal, "open_backend", recording)
    assert replay_cli(state, config, FIRST, date(2019, 6, 4), "--sandbox", "container")[0] == 0
    assert opened == ["container"]          # 06-03 journals no approach
    assert run_day(state, config, date(2019, 6, 5))[0] == 0
    assert opened == ["container", "process"]
    status, _, err = call(*common(state, config), "--as-of", "2019-06-06T00:00:00+00:00",
                          "journal", "recompute", "--all", "--sandbox", "container")
    assert status == 0, err
    assert opened == ["container", "process", "container"]


# ------------------------------------------------------------------ 105 (a): the day's jobs


def test_a_replay_of_approaches_runs_with_the_decision_21_loader_patched_to_raise(
        replayed, setup):
    state, ids, status, out, err = replayed
    assert status == 0, err
    assert approach_rows(state, FIRST).empty
    for d in APPROACH_DAYS:
        subjects = set(approach_rows(state, d)["subject"])
        expected = {ids["trend"], ids["hours"]} | ({ids["breaks"]} if d < THURSDAY else set())
        assert subjects == expected, d


def test_the_journaled_targets_are_the_in_process_runners_over_the_same_span(replayed, setup):
    # The reference here is the decision-21 loader in the test (not patched), over
    # the approach's days from its first journaled one (DESIGN 7.1: flat start).
    state, ids, *_ = replayed
    for key, which in (("trend", TREND), ("hours", HOURS)):
        where, name, params = which
        strat = strategy.load_strategy((REPO_ROOT / where / name).read_text(encoding="utf-8"),
                                       setup.thresholds, name=name)
        rows = [approach_rows(state, d) for d in APPROACH_DAYS]
        for inst in setup.instruments:
            win = read_window(state, setup.track, inst, setup.calendars[inst.calendar],
                              DateRange(APPROACH_DAYS[0], APPROACH_DAYS[-1]))
            expected = _strategy_targets(win, strat, params)
            got = np.concatenate([
                r[(r["subject"] == ids[key]) & (r["instrument"] == inst.symbol)]
                .sort_values("ts")["target_next"].to_numpy() for r in rows])
            assert len(got) == len(expected) > 0
            assert np.array_equal(got, expected), (name, inst.symbol)


def test_journal_recompute_evaluates_approaches_on_the_sandbox_and_matches(
        replayed, config, tmp_path):
    state = tmp_path / "state"
    shutil.copytree(replayed[0], state)
    with pytest.MonkeyPatch.context() as mp:
        patch_loader(mp)
        status, out, err = call(*common(state, config), "--as-of",
                                "2019-06-07T00:00:00+00:00", "journal", "recompute", "--all",
                                "--sandbox", "process")
    assert status == 0, err
    assert out.splitlines()[-1].endswith(" pairs recomputed, 0 mismatched"), out
    approach_lines = {line for line in out.splitlines()
                      if any(line.endswith(" " + i) for i in replayed[1].values())}
    # trend and hours on each approach day, breaks before its Thursday.
    assert len(approach_lines) == 8
    assert all(line.startswith("equal ") for line in approach_lines), approach_lines


# ------------------------------------------------------------------ 105 (c): errors


def test_a_contract_break_retires_the_approach_with_the_sandboxs_error_text(replayed):
    state, ids, *_ = replayed
    rows = ledger.read(state, TRACK, ledger.LIFECYCLE)
    [row] = [r for r in rows if r["id"] == ids["breaks"]]
    assert {k: row[k] for k in ("date", "from", "to")} == \
        {"date": THURSDAY.isoformat(), "from": "live", "to": "retired"}
    # Decision 101 (a)'s text: the stage, the rule, the window bar, the parameter set;
    # no value the text returned, no time stamp.
    prefix = "failure: dry_run [out_of_range]: position returned a number outside [-1, 1] " \
             "at window bar "
    assert row["reason"].startswith(prefix), row["reason"]
    assert row["reason"].endswith(" (parameter set 0)")
    assert "2.0" not in row["reason"] and "2019" not in row["reason"]
    # The others ran that day.
    assert set(approach_rows(state, THURSDAY)["subject"]) == {ids["trend"], ids["hours"]}


def test_a_limit_error_retires_the_approach_and_the_day_goes_on(tmp_path, setup):
    # LIMITED: the fixture configuration copied under the temporary directory with
    # run.toml's wall_seconds 5.0 in place of 1200.0 (cpu_seconds stays 1200.0).
    config = copy_config(tmp_path, wall_seconds=SHORT_WALL)
    state = init(tmp_path / "state")
    trend, endless = admit(state, setup, TREND), admit(state, setup, ENDLESS)
    day = APPROACH_DAYS[0]
    assert run_day(state, config, FIRST, "--sandbox", "process")[0] == 0
    status, out, err = run_day(state, config, day, "--sandbox", "process")
    assert status == 0, err
    [row] = ledger.read(state, TRACK, ledger.LIFECYCLE)
    assert {k: row[k] for k in ("date", "id", "from", "to", "reason")} == {
        "date": day.isoformat(), "id": endless, "from": "live", "to": "retired",
        "reason": "failure: limit [wall_clock]: the job ran past its wall-clock limit"}
    assert set(approach_rows(state, day)["subject"]) == {trend}


def test_a_source_the_backend_refuses_fails_the_day_and_moves_nothing(tmp_path, setup,
                                                                        config):
    state = init(tmp_path / "state")
    text = (REPO_ROOT / "reference" / "trend_ma.py").read_text(encoding="utf-8")
    foreign = admit(state, setup, TREND, source=text + "\n# no file of the repository\n")
    assert run_day(state, config, FIRST)[0] == 0
    before = nothing_of_the_day(state, APPROACH_DAYS[0])
    status, out, err = run_day(state, config, APPROACH_DAYS[0])
    assert status == 1
    assert foreign in err and "repository_source" in err and "the day fails" in err
    assert nothing_of_the_day(state, APPROACH_DAYS[0]) == before
    assert before["journal"] is False and before["lock"] is False


class Unavailable:
    def run(self, job):
        raise SandboxUnavailable("no container runtime found (a fake)")


class ShortResult:
    """Answers every job with one target too few on its first instrument."""

    def __init__(self, scratch):
        self.inner = ProcessSandbox(scratch)

    def run(self, job):
        result = self.inner.run(job)
        key = (0, job.instruments[0].symbol)
        targets = dict(result.targets)
        targets[key] = targets[key][:-1]
        return SandboxResult(targets=targets, bars=result.bars, call_ms=result.call_ms)


@pytest.mark.parametrize("make, says", [
    (lambda tmp: Unavailable(), "the sandbox could not run it"),
    (lambda tmp: ShortResult(tmp / "scratch"), "does not give one target per window bar"),
])
def test_a_harness_error_fails_the_day_naming_the_approach(tmp_path, setup, config, make,
                                                          says):
    state = init(tmp_path / "state")
    trend = admit(state, setup, TREND)
    assert run_day(state, config, FIRST)[0] == 0
    before = nothing_of_the_day(state, APPROACH_DAYS[0])
    tc = load_track_config(config, TRACK)
    [(d, instant)] = list(replay.replay_days(tc, setup.calendars, APPROACH_DAYS[0],
                                             APPROACH_DAYS[0]))
    with pytest.raises(journal.JournalError) as raised:
        day_function(state, config, TRACK, FixedClock(instant), d, sandbox=make(tmp_path))
    assert trend in str(raised.value) and says in str(raised.value)
    assert nothing_of_the_day(state, APPROACH_DAYS[0]) == before
    assert before["journal"] is False


# ------------------------------------------------------------------ 105 (d): the container


@pytest.mark.container
def test_a_replay_on_the_container_backend_equals_the_process_backends_byte_for_byte(
        tmp_path, replayed, config, setup):
    process_state, ids, status, _, err = replayed
    assert status == 0, err
    state = init(tmp_path / "state")
    assert {name: admit(state, setup, which) for name, which in
            (("trend", TREND), ("hours", HOURS), ("breaks", BREAKS))} == ids
    box = ContainerSandbox(tmp_path / "scratch", config)
    tc = load_track_config(config, TRACK)
    try:
        days = replay.replay(state, config, TRACK, tc, setup.calendars, FIRST, LAST,
                             lambda done, instant: None, (), sandbox=box)
    finally:
        left = [n for n in box.started if container.container_exists(box.runtime(), n)]
        for name in left:
            container.remove(box.runtime(), name)
    assert left == []
    assert days == 4
    # One job per approach and day: 3 approaches on 06-04 and 06-05, 3 on 06-06.
    assert len(box.started) == 9
    assert files(state) == files(process_state)
    assert git_head(state) == git_head(process_state)

