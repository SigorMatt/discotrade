"""Step 1 staged (decision 2026-10-19-m22 181; DESIGN 16.2, 5.2, 5.4, 5.6;
decisions 2026-10-12 4, 5, 50, 54; REVIEW-2's note on ``update_rolls``,
REVIEW-7's note on ``revised_data``; I-5).

Everything step 1 writes (the bar month files and their index, the roll
records and ``gaps.jsonl``) goes to the staging directory, is read from there
by the rest of the day, and is moved into place with the day. A day that fails
after step 1 leaves ``bars/`` and ``rolls/`` as they were; run again, it writes
the bytes of a day that never failed. The bar store's refusal of a revised data
point is ``RevisedDataError``, the type the day loop catches.

Every state directory is a copy of conftest's ``mixed_ran_template`` (track
``test_mixed``, SYNA rolls on 2019-06-14, SYNX drops bars) under a pytest
temporary directory; ``run-day`` runs in-process through ``discotrade.cli.main``;
time comes only from ``--as-of``; failures are injected by ``monkeypatch``. The
synthetic sources' seeds are their fixture records'; no other random draw is
made. Every git is on local paths with ``GIT_ALLOW_PROTOCOL=file`` (decision 47).
"""

import shutil
from datetime import date

import pandas as pd
import pytest
from conftest import RAN_AS_OF, copy_template

from discotrade import daily, journal, table
from discotrade.bars.store import BarStore, BarStoreError, RevisedDataError
from discotrade.cli import REPO_ROOT, main
from discotrade.sources.synth import SynthSource
from discotrade.state import STAGING

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
NEXT, ROLL_DAY = date(2019, 6, 13), date(2019, 6, 14)
SYNA_ROLLS = f"rolls/{TRACK}/SYNA.jsonl"
GAPS = f"bars/{TRACK}/gaps.jsonl"
INDEX = f"bars/{TRACK}/index.json"
#: SYNX's bar the source leaves out in the first test, so that ROLL_DAY's gap check
#: finds a new missing bar and appends it to ``gaps.jsonl``.
DROPPED = pd.Timestamp("2019-06-14T10:00:00Z")


def run(state, config, day):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", RAN_AS_OF, "run-day", "--day", day.isoformat()])


def tree(root, *tops) -> dict[str, bytes]:
    """The bytes of every file under ``root`` (under ``tops`` when given), ``.git/`` left out."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts
            and (not tops or p.relative_to(root).parts[0] in tops)}


def step_1_files(root) -> dict[str, bytes]:
    """Every file step 1 writes: under ``bars/`` (month files, index, gaps file) and ``rolls/``."""
    return tree(root, "bars", "rolls")


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("scfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def ran(tmp_path_factory, mixed_ran_template):
    return copy_template(mixed_ran_template, tmp_path_factory.mktemp("sran") / "state")


@pytest.fixture(scope="module")
def at_next(tmp_path_factory, ran, config):
    """``ran`` with 2019-06-13 run: the day before SYNA's roll bar."""
    path = tmp_path_factory.mktemp("snext") / "state"
    shutil.copytree(ran, path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        assert run(path, config, NEXT) == 0
    return path


def drop_one_synx_bar(monkeypatch):
    """The synthetic source without SYNX's bar at ``DROPPED`` (a feed that missed it)."""
    real = SynthSource.fetch

    def fetch(self, instrument, start, end):
        bars = real(self, instrument, start, end)
        if instrument.symbol == "SYNX":
            bars = bars[bars["ts"] != DROPPED].reset_index(drop=True)
        return bars

    monkeypatch.setattr(SynthSource, "fetch", fetch)


@pytest.fixture
def state(tmp_path, at_next):
    path = tmp_path / "state"
    shutil.copytree(at_next, path)
    return path


def test_a_day_failing_after_step_1_leaves_bars_rolls_and_gaps_and_then_writes_a_clean_days_bytes(
        tmp_path, state, at_next, config, monkeypatch):
    drop_one_synx_bar(monkeypatch)
    before = step_1_files(state)
    seen = []

    def failing(*args, **kwargs):
        # Step 1 has run: its writes are in the staging directory, not in place.
        staged = tree(state / STAGING, "bars", "rolls")
        seen.append((sorted(staged), step_1_files(state) == before))
        raise daily.DailyError("injected failure after step 1")

    with monkeypatch.context() as mp:
        mp.setattr(table, "build", failing)
        assert run(state, config, ROLL_DAY) == 1
    # Decision 182 (a): the day is tried twice, each attempt from a clean staging directory.
    assert len(seen) == 2
    for staged_names, untouched_meanwhile in seen:
        assert untouched_meanwhile
        assert INDEX in staged_names and SYNA_ROLLS in staged_names and GAPS in staged_names
        assert any(n.startswith(f"bars/{TRACK}/SYNA/") and n.endswith(".parquet")
                   for n in staged_names)
    assert step_1_files(state) == before
    assert not (state / STAGING).exists()
    assert journal.read_day(state, TRACK, ROLL_DAY) is None

    # The same day run without the failure writes what a never-failed run writes.
    assert run(state, config, ROLL_DAY) == 0
    straight = tmp_path / "straight"
    shutil.copytree(at_next, straight)
    # Decision 182 (c), (f): the failed day's run_failed alert, which its later run's step 6
    # reads, is admitted by giving the never-failed state the same line before its run.
    log = f"health/{TRACK}.jsonl"
    failed = [x for x in (state / log).read_text(encoding="utf-8").splitlines()
              if '"run_failed"' in x]
    assert len(failed) == 1
    (straight / log).parent.mkdir(exist_ok=True)
    with (straight / log).open("a", encoding="utf-8") as f:
        f.write(failed[0] + "\n")
    assert run(straight, config, ROLL_DAY) == 0
    clean = step_1_files(straight)
    assert clean[SYNA_ROLLS] != before[SYNA_ROLLS] and clean[INDEX] != before[INDEX]
    assert clean[GAPS] == before[GAPS] + b'{"symbol": "SYNX", "ts": "2019-06-14T10:00:00+00:00"}\n'
    assert step_1_files(state) == clean
    assert tree(state) == tree(straight)


def test_update_rolls_failing_after_the_bars_were_fetched_leaves_no_new_bar(
        state, config, monkeypatch):
    before = step_1_files(state)
    store = BarStore(state, TRACK, 3600)
    last = {s: store.last_ts(s) for s in ("SYNA", "SYNL", "SYNX")}
    fetched = []

    def failing(state_dir, track, bar_seconds, instrument, source, day):
        fetched.append(BarStore(state_dir, track, bar_seconds).last_ts(instrument.symbol))
        raise daily.DailyError(f"injected fetch_contract failure for {instrument.symbol}")

    monkeypatch.setattr(daily, "update_rolls", failing)
    assert run(state, config, ROLL_DAY) == 1
    # The bars were fetched (the day's reads saw them) before update_rolls failed ...
    assert fetched and fetched[0] > last["SYNA"]
    # ... and none of them is stored.
    assert step_1_files(state) == before
    store = BarStore(state, TRACK, 3600)
    assert {s: store.last_ts(s) for s in last} == last


def test_the_store_refuses_a_revised_data_point_with_its_own_type(state):
    store = BarStore(state, TRACK, 3600)
    month = store.month_path("SYNA", "2019-06")
    original = month.read_bytes()
    frame = pd.read_parquet(month)
    frame.loc[3, "close"] += 0.25
    frame.to_parquet(month, index=False, engine="pyarrow")
    with pytest.raises(RevisedDataError, match="a revised data point"):
        store.last_ts("SYNA")
    assert issubclass(RevisedDataError, BarStoreError)
    # An interrupted append the reader refuses is not a revised data point.
    month.write_bytes(original)
    extra = frame.iloc[-1:].copy()
    extra["ts"] = extra["ts"] + pd.Timedelta(hours=1)
    pd.concat([pd.read_parquet(month), extra], ignore_index=True).to_parquet(
        month, index=False, engine="pyarrow")
    with pytest.raises(BarStoreError, match="interrupted append") as caught:
        store.last_ts("SYNA")
    assert not isinstance(caught.value, RevisedDataError)


def test_the_day_loop_raises_revised_data_by_type_not_by_text(state, config, monkeypatch):
    def plain(*args, **kwargs):
        raise BarStoreError("SYNA 2019-06: a message naming a revised data point; refused")

    monkeypatch.setattr(daily, "check_gaps", plain)
    assert run(state, config, ROLL_DAY) == 1
    log = state / "health" / f"{TRACK}.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    assert [line for line in lines if '"revised_data"' in line] == []
