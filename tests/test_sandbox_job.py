"""The sandbox job built for a window (DESIGN 12.4, 6.2, 5.6, 4.1; decision 95 (a),
(b), (f); decisions 2026-10-12 23, 24, 36, 37; I-2, I-7).

The stores are filled by ``bars fetch`` on the fixture track ``test_synth``
(SYNA rolls quarterly; every instrument on the ``synth_week`` calendar), run
in-process (``discotrade.cli.main``) with the clock given by ``--as-of``, under
a pytest temporary directory. The store's clock is ten days after the day
``D``, so that T's bars and later ones are stored when W's job is built.

Seeds: the test draws nothing at random. The synthetic bars come from the
fixture records' seeds, written here in ``SEEDS`` and checked against them.
"""

import json
import shutil
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_track_config
from discotrade.sandbox.base import (
    JOB_FILE,
    SandboxJob,
    SandboxLimits,
    SandboxRefused,
    build_job,
    write_job,
)
from discotrade.sandbox.inprocess import InProcessSandbox
from discotrade.tradingcal import trading_date

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
HOUR = 3600
#: The seed of each instrument's synthetic source, as its fixture record gives it.
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
#: The day D (a Monday): T is 2019-07-09 to 2019-07-15, W 2019-06-11 to 2019-07-08.
DAY = date(2019, 7, 15)
AS_OF = "2019-07-25T00:00:00+00:00"
LIMITS = SandboxLimits(wall_seconds=60.0, memory_bytes=1 << 30, output_bytes=1 << 22)


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def tc(config):
    return load_track_config(config, TRACK)


@pytest.fixture(scope="module")
def calendars(config):
    return {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def state(tmp_path_factory, config):
    path = tmp_path_factory.mktemp("state")
    assert main(["--state", str(path), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    return path


@pytest.fixture(scope="module")
def w_job(state, tc, calendars):
    w = tc.track.windows(DAY).w
    return build_job(state, tc.track, tc.instruments, calendars, w,
                     source="PARAMS = {}\n", param_sets=[{}], limits=LIMITS)


def test_the_synthetic_seeds_are_the_ones_written_here(tc):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS


def test_a_w_job_holds_no_bar_after_w_and_the_context_decision_23_gives(
        state, tc, calendars, w_job):
    track = tc.track
    w = track.windows(DAY).w
    assert w.last == date(2019, 7, 8) and w.first == date(2019, 6, 11)
    store = BarStore(state, TRACK, HOUR)
    assert [j.symbol for j in w_job.instruments] == list(track.instruments)
    cap = track.history_cap_bars
    for inst, job_inst in zip(tc.instruments, w_job.instruments, strict=True):
        cal = calendars[inst.calendar]
        bars = job_inst.bars
        dates = [trading_date(cal, t.to_pydatetime()) for t in bars["ts"]]
        # Nothing later than W's last trading day, though the store holds T and more.
        assert max(dates) <= w.last
        stored = store.read_range(inst.symbol, pd.Timestamp("2019-01-01", tz="UTC"),
                                  pd.Timestamp("2019-08-01", tz="UTC"))
        stored_dates = [trading_date(cal, t.to_pydatetime()) for t in stored["ts"]]
        assert max(stored_dates) > DAY
        # The window bars: every stored bar whose trading date is in W, in order.
        want = stored[[d in w for d in stored_dates]].reset_index(drop=True)
        inside = bars.iloc[job_inst.first:].reset_index(drop=True)
        assert list(inside["ts"]) == list(want["ts"])
        assert all(d in w for d in dates[job_inst.first:])
        # The context: the cap - 1 stored bars before the first window bar, so that
        # the slice at the first window bar holds history_cap_bars rows.
        before = stored[stored["ts"] < want["ts"].iloc[0]]
        assert len(before) >= cap
        assert job_inst.first == cap - 1
        assert list(bars["ts"].iloc[:job_inst.first]) == list(before["ts"].iloc[-(cap - 1):])
        for col in ("open", "high", "low", "close", "volume"):
            expect = np.concatenate([before[col].to_numpy()[-(cap - 1):],
                                     want[col].to_numpy()])
            assert np.array_equal(bars[col].to_numpy(), expect), (inst.symbol, col)
        # hour and weekday of each bar's open in the calendar's time zone.
        local = bars["ts"].dt.tz_convert(cal.tz)
        assert np.array_equal(bars["hour"].to_numpy(), local.dt.hour.to_numpy())
        assert np.array_equal(bars["weekday"].to_numpy(), local.dt.weekday.to_numpy())
        assert job_inst.shorting == inst.shorting


def test_the_job_carries_the_roll_gaps_from_the_roll_records(state, tc, calendars):
    # A W whose window holds SYNA's June roll (2019-06-14): D = 2019-06-24.
    w = tc.track.windows(date(2019, 6, 24)).w
    job = build_job(state, tc.track, tc.instruments, calendars, w,
                    source="PARAMS = {}\n", param_sets=[{}], limits=LIMITS)
    syna = job.instruments[0]
    assert syna.symbol == "SYNA"
    rolled = np.flatnonzero(syna.bars["rolled"].to_numpy())
    roll_ts = pd.Timestamp("2019-06-14 00:00", tz="UTC")
    assert roll_ts in set(syna.bars["ts"].iloc[rolled])
    k = list(syna.bars["ts"]).index(roll_ts)
    assert syna.bars["gap"].iloc[k] == 37.5
    assert (syna.bars["gap"].to_numpy()[~syna.bars["rolled"].to_numpy()] == 0.0).all()
    for other in job.instruments[1:]:
        assert not other.bars["rolled"].any()


def test_a_bar_of_t_is_not_in_the_job_written_to_disk(tmp_path, w_job):
    out = write_job(w_job, tmp_path / "job")
    doc = json.loads((out / JOB_FILE).read_text(encoding="utf-8"))
    assert doc["source"] == "PARAMS = {}\n"
    assert doc["params"] == [{}] and doc["mode"] == "positions"
    for job_inst, entry in zip(w_job.instruments, doc["instruments"], strict=True):
        with np.load(out / entry["bars"], allow_pickle=False) as arrays:
            assert len(arrays["close"]) == len(job_inst.bars)
            assert np.array_equal(arrays["close"], job_inst.bars["close"].to_numpy())
        assert entry["first"] == job_inst.first
        assert entry["shorting"] == job_inst.shorting
    # No symbol and no timestamp is written into the job directory (DESIGN 6.2).
    text = (out / JOB_FILE).read_text(encoding="utf-8")
    for symbol in SEEDS:
        assert symbol not in text
    assert "2019" not in text


def test_the_in_process_backend_refuses_a_job_carrying_source_text(w_job):
    with pytest.raises(SandboxRefused, match="source"):
        InProcessSandbox().run(w_job)


def test_a_job_carries_a_text_or_a_function_and_never_both(state, tc, calendars):
    w = tc.track.windows(DAY).w
    with pytest.raises(ValueError, match="exactly one"):
        build_job(state, tc.track, tc.instruments, calendars, w, source="x = 1\n",
                  function=lambda bars, params: 0.0, param_sets=[{}], limits=LIMITS)
    with pytest.raises(ValueError, match="exactly one"):
        build_job(state, tc.track, tc.instruments, calendars, w, param_sets=[{}],
                  limits=LIMITS)


def test_a_job_carrying_a_function_object_is_not_written_to_disk(tmp_path, state, tc,
                                                                  calendars):
    w = tc.track.windows(DAY).w
    job = build_job(state, tc.track, tc.instruments[:1], calendars,
                    type(w)(w.last - timedelta(days=1), w.last),
                    function=lambda bars, params: 0.0, param_sets=[{}], limits=LIMITS)
    assert isinstance(job, SandboxJob) and job.source is None
    with pytest.raises(SandboxRefused, match="function"):
        write_job(job, tmp_path / "job")
