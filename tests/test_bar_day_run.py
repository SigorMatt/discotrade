"""Each listed month file hashed once per day run (O-3; decision 2026-10-14 80
(b); DESIGN 5.2, 16.1, 16.4; decisions 2026-10-12 18, 31, 35).

Within one day run (``bars.store.day_run()``, held by ``daily.run_day``) a
listed month file is read and hashed at most once per index entry, whatever
the number of subjects that read it; a file appended to in the day has a new
entry and is checked again; a file whose bytes change between two days of one
``replay`` is refused by the next day's first read of it, the day failing as a
revised data point does (``revised_data``).

Day-running tests use the fixture tracks ``test_mixed`` (production
thresholds) and ``test_synth`` (decision 72's gate configuration,
``thresholds_gate.toml`` copied in unchanged), each state directory made by
``init-state`` under a pytest temporary directory. The only random draws are
the synthetic sources', seeded by their fixture records (``SEEDS``, asserted).
``discotrade`` runs in-process through ``discotrade.cli.main``; time comes
only from ``--as-of`` and the replay's clock. No git is run by this file.
"""

import contextlib
import io
import json
import shutil
from collections import Counter
from datetime import date

import pandas as pd
import pytest

from discotrade import replay as replay_module
from discotrade.bars import store as store_module
from discotrade.bars.store import BarStore, BarStoreError, day_run
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_track_config
from discotrade.state import write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104, "SYNL": 105, "SYNX": 106}

MIXED = "test_mixed"
MIXED_AS_OF = "2019-06-26T00:00:00+00:00"
ADMITTED = date(2019, 6, 7)
MIXED_DAYS = (date(2019, 6, 8), date(2019, 6, 9))   # the second is counted

SYNTH = "test_synth"
SYNTH_AS_OF = "2019-06-03T00:00:00+00:00"
SYNTH_DAYS = (date(2019, 6, 3), date(2019, 6, 4))
REVISED = ("SYNB", "2019-05")


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(list(argv))
    return status, out.getvalue(), err.getvalue()


def health(state, track) -> list[dict]:
    path = state / "health" / f"{track}.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def revise(month_path) -> None:
    frame = pd.read_parquet(month_path)
    frame.loc[3, "close"] += 0.25
    frame.to_parquet(month_path, index=False, engine="pyarrow")


@pytest.fixture(scope="module")
def mixed_config(tmp_path_factory):
    path = tmp_path_factory.mktemp("hcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def gate_config(tmp_path_factory):
    path = tmp_path_factory.mktemp("gcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copyfile(FIXTURE_CONFIG / "thresholds_gate.toml", path / "thresholds.toml")
    assert (path / "thresholds.toml").read_bytes() == \
        (FIXTURE_CONFIG / "thresholds_gate.toml").read_bytes()
    return path


def test_seeds_are_the_fixture_records(mixed_config):
    for track in (MIXED, SYNTH):
        for inst in load_track_config(mixed_config, track).instruments:
            assert inst.source.get("seed") == SEEDS[inst.symbol]


# ------------------------------------------------------------------ once per day run


def counting(monkeypatch):
    """Count the hashes that verify a read month file, per index entry (rows,
    hash), and the month reads of every reader entry point, per file."""
    hashed: Counter = Counter()
    reads: Counter = Counter()
    real_matches = BarStore._matches
    real_read = BarStore._read_month

    def matches(frame, entry):
        hashed[(entry["rows"], entry["hash"])] += 1
        return real_matches(frame, entry)

    def read_month(self, symbol, month, entry):
        reads[(symbol, month)] += 1
        return real_read(self, symbol, month, entry)

    monkeypatch.setattr(BarStore, "_matches", staticmethod(matches))
    monkeypatch.setattr(BarStore, "_read_month", read_month)
    return hashed, reads


@pytest.mark.parametrize("approaches", [0, 2])
def test_each_listed_month_file_is_hashed_at_most_once_in_a_day_run(
        tmp_path, mixed_config, monkeypatch, approaches):
    """test_mixed, the second of two days, with the controls alone and with
    two approaches too: no index entry is verified twice, although the day
    reads month files many times; only the files the day appends to are
    verified a second time, under their new entry."""
    from discotrade import journal

    state = tmp_path / "state"
    assert main(["init-state", "--state", str(state), "--as-of", MIXED_AS_OF]) == 0
    setup = journal.Setup.load(mixed_config, MIXED)
    for name in ("trend_ma.py", "hour_of_day.py")[:approaches]:
        path = REPO_ROOT / "reference" / name
        strat = load_strategy_file(path, setup.thresholds)
        write_approach(state, source=path.read_text(encoding="utf-8"), params=strat.params,
                       cell="trend/short", model_id="test-model",
                       model_version="test-model-v0", cutoff=date(2019, 1, 1),
                       description=f"the reference strategy {name}",
                       profile_version="w-test", admitted=ADMITTED,
                       instruments=setup.instruments, spread_tables=setup.spread_tables)
    argv = ["--state", str(state), "--config", str(mixed_config), "--track", MIXED,
            "--as-of", MIXED_AS_OF, "run-day", "--day"]
    assert main([*argv, MIXED_DAYS[0].isoformat()]) == 0
    store = BarStore(state, MIXED, 3600)
    before = store.index()
    hashed, reads = counting(monkeypatch)
    assert main([*argv, MIXED_DAYS[1].isoformat()]) == 0
    after = store.index()

    assert hashed and max(hashed.values()) == 1, hashed.most_common(3)
    assert max(reads.values()) > 1          # files are read by more than one reader
    for symbol, entry in after.items():
        for month, listed in entry["months"].items():
            old = before.get(symbol, {"months": {}})["months"].get(month)
            entries = {(listed["rows"], listed["hash"])}
            if old is not None:
                entries.add((old["rows"], old["hash"]))
            assert sum(hashed[e] for e in entries) <= (1 if old == listed else 2), \
                (symbol, month)


def bars_frame(start: str, n: int, contract: str = "C1") -> pd.DataFrame:
    ts = pd.date_range(start, periods=n, freq="h", tz="UTC")
    values = [100.0 + k for k in range(n)]
    return pd.DataFrame({"ts": ts, "open": values, "high": values, "low": values,
                         "close": values, "volume": [1.0] * n, "contract": [contract] * n})


def test_a_file_appended_to_in_the_day_run_is_read_again(tmp_path, monkeypatch):
    """Inside one day run, a month file read, then appended to, is read with
    its new rows, verified once under its new entry."""
    store = BarStore(tmp_path / "state", "t", 3600)
    until = pd.Timestamp("2019-07-01", tz="UTC")
    store.append("S", bars_frame("2019-06-03 00:00", 3), until)
    hashed, _ = counting(monkeypatch)
    with day_run():
        lo, hi = pd.Timestamp("2019-06-01", tz="UTC"), until
        assert len(store.read_range("S", lo, hi)) == 3
        assert len(BarStore(tmp_path / "state", "t", 3600).read_range("S", lo, hi)) == 3
        store.append("S", bars_frame("2019-06-03 03:00", 2), until)
        got = store.read_range("S", lo, hi)
        assert len(got) == 5
        assert len(BarStore(tmp_path / "state", "t", 3600).last_n(
            "S", got["ts"].iloc[-1], 10)) == 5
    assert max(hashed.values()) == 1
    pd.testing.assert_frame_equal(got, store.read_range("S", lo, hi))


def test_a_file_changed_after_a_day_run_is_refused_by_the_next(tmp_path):
    store = BarStore(tmp_path / "state", "t", 3600)
    until = pd.Timestamp("2019-07-01", tz="UTC")
    store.append("S", bars_frame("2019-05-30 00:00", 72), until)
    lo, hi = pd.Timestamp("2019-05-01", tz="UTC"), until
    with day_run():
        assert len(store.read_range("S", lo, hi)) == 72
    revise(store.month_path("S", "2019-05"))
    with day_run():
        with pytest.raises(BarStoreError, match="revised data point"):
            store.read_range("S", lo, hi)
    assert store_module._RUN is None


def test_a_file_revised_between_two_days_of_a_replay_fails_the_next_day(
        tmp_path, gate_config, monkeypatch):
    """test_synth on the gate configuration: SYNB's 2019-05 file, verified by
    the first day, is revised before the second day of the same ``replay``;
    the second day fails with ``revised_data`` naming it, the first stays."""
    from discotrade import journal

    state = tmp_path / "state"
    assert main(["init-state", "--state", str(state), "--as-of", SYNTH_AS_OF]) == 0
    real = replay_module.run_day
    seen = []

    def run_day(state_dir, config_dir, track, clock, day, **kw):
        if day == SYNTH_DAYS[1]:
            path = BarStore(state_dir, track, 3600).month_path(*REVISED)
            assert path.exists()
            revise(path)
        seen.append(day)
        return real(state_dir, config_dir, track, clock, day, **kw)

    monkeypatch.setattr(replay_module, "run_day", run_day)
    status, out, err = call("--state", str(state), "--config", str(gate_config), "--track",
                            SYNTH, "replay", "--from", SYNTH_DAYS[0].isoformat(),
                            "--to", SYNTH_DAYS[1].isoformat())
    assert status == 1, (out, err)
    assert seen == list(SYNTH_DAYS)
    assert SYNTH_DAYS[1].isoformat() in err and "revised data point" in err
    events = [e for e in health(state, SYNTH) if e["kind"] == "revised_data"]
    assert len(events) == 1 and events[0]["level"] == "alert"
    assert events[0]["date"] == SYNTH_DAYS[1].isoformat()
    assert " ".join(REVISED) in events[0]["detail"]["error"]
    assert [e["date"] for e in journal.read_index(state, SYNTH)] == \
        [SYNTH_DAYS[0].isoformat()]
