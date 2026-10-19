"""Verified bar month files carried from one day run to the next by the
identity of their bytes (O-26 items 2 and 3 of
meta/decisions/2026-10-18-owner.md; decisions 157 (a), (b) and 158 of
meta/decisions/decisions-2026-10-18-m20.md; decision 2026-10-14 80 (b);
DESIGN 5.2, 9.2).

Inside a day run, a listed month file whose frame matched its index entry is
kept in ``bars.store._CARRIED``, keyed by its path and the entry's row count
and hash, with the length and sha256 of the bytes it was parsed from. A later
day run reads the file's bytes again: the same bytes under the same entry are
served the kept frame without hashing its content again; any other bytes are
parsed and checked against the index, so a file changed after it was verified
is refused by the next day run's first read of it, also when its length is
unchanged. Outside a day run nothing is kept or served. The cache holds one
store (state directory and track) at a time, and ``state.clear_caches``
empties it.

Every file is written here, under the test's temporary directory; nothing
reads a clock and no random draw is made.
"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from discotrade import state
from discotrade.bars import store as store_module
from discotrade.bars.store import BarStore, BarStoreError, day_run

UNTIL = pd.Timestamp("2019-07-01", tz="UTC")
LO, HI = pd.Timestamp("2019-05-01", tz="UTC"), UNTIL


def bars_frame(start: str, n: int) -> pd.DataFrame:
    ts = pd.date_range(start, periods=n, freq="h", tz="UTC")
    values = [100.0 + k for k in range(n)]
    return pd.DataFrame({"ts": ts, "open": values, "high": values, "low": values,
                         "close": values, "volume": [1.0] * n, "contract": ["C1"] * n})


def make_store(root: Path) -> BarStore:
    store = BarStore(root, "t", 3600)
    store.append("S", bars_frame("2019-05-30 00:00", 72), UNTIL)   # 2019-05 and 2019-06
    return store


def rewrite(path: Path, close_delta: float = 0.0) -> bytes:
    """Rewrite a month file uncompressed, without dictionary or statistics, so that
    a changed float leaves the file's length as it was."""
    table = pq.read_table(path)
    frame = table.to_pandas()
    frame.loc[3, "close"] += close_delta
    pq.write_table(pa.Table.from_pandas(frame, schema=table.schema, preserve_index=False),
                   path, compression="none", use_dictionary=False, write_statistics=False)
    return path.read_bytes()


def counting(monkeypatch) -> list:
    hashed = []
    real = BarStore._matches

    def matches(frame, entry):
        hashed.append((entry["rows"], entry["hash"]))
        return real(frame, entry)

    monkeypatch.setattr(BarStore, "_matches", staticmethod(matches))
    return hashed


def test_equal_bytes_are_served_in_the_next_day_run_without_hashing_again(
        tmp_path, monkeypatch):
    state.clear_caches()
    store = make_store(tmp_path / "state")
    whole = store.read_range("S", LO, HI)
    hashed = counting(monkeypatch)
    with day_run():
        first = store.read_range("S", LO, HI)
    assert len(hashed) == 2                               # both month files verified
    del hashed[:]
    with day_run():
        second = store.read_range("S", LO, HI)
        assert len(BarStore(tmp_path / "state", "t", 3600).last_n(
            "S", second["ts"].iloc[-1], 100)) == 72
    assert hashed == []
    pd.testing.assert_frame_equal(first, whole)
    pd.testing.assert_frame_equal(second, whole)


def test_a_rewritten_file_of_the_same_length_is_refused_by_the_next_day_run(tmp_path):
    state.clear_caches()
    store = make_store(tmp_path / "state")
    path = store.month_path("S", "2019-05")
    same = rewrite(path)                     # other bytes, the same content: still verified
    with day_run():
        assert len(store.read_range("S", LO, HI)) == 72
    changed = rewrite(path, 0.25)
    assert len(changed) == len(same) and changed != same
    with day_run():
        with pytest.raises(BarStoreError, match="revised data point"):
            store.read_range("S", LO, HI)
    with day_run():
        with pytest.raises(BarStoreError, match="revised data point"):
            store._verify_stored("S")


def test_other_bytes_of_the_same_content_are_hashed_and_served(tmp_path, monkeypatch):
    state.clear_caches()
    store = make_store(tmp_path / "state")
    with day_run():
        before = store.read_range("S", LO, HI)
    rewrite(store.month_path("S", "2019-05"))
    hashed = counting(monkeypatch)
    with day_run():
        after = store.read_range("S", LO, HI)
    assert len(hashed) == 1                                # only the rewritten file
    pd.testing.assert_frame_equal(before, after)


def test_nothing_is_kept_or_served_outside_a_day_run(tmp_path, monkeypatch):
    state.clear_caches()
    store = make_store(tmp_path / "state")
    hashed = counting(monkeypatch)
    store.read_range("S", LO, HI)
    store.read_range("S", LO, HI)
    assert len(hashed) == 4
    assert store_module.carried_files() == []
    with day_run():
        store.read_range("S", LO, HI)
    del hashed[:]
    store.read_range("S", LO, HI)
    assert len(hashed) == 2


def test_the_cache_holds_one_store_at_a_time(tmp_path):
    state.clear_caches()
    one, two = make_store(tmp_path / "one"), make_store(tmp_path / "two")
    with day_run():
        one.read_range("S", LO, HI)
    held = store_module.carried_files()
    assert len(held) == 2 and all(Path(p).is_relative_to(tmp_path / "one") for p in held)
    with day_run():
        two.read_range("S", LO, HI)
    held = store_module.carried_files()
    assert len(held) == 2 and all(Path(p).is_relative_to(tmp_path / "two") for p in held)


def test_clear_caches_empties_the_carried_files(tmp_path):
    store = make_store(tmp_path / "state")
    with day_run():
        store.read_range("S", LO, HI)
    assert store_module.carried_files()
    assert "discotrade.bars.store._CARRIED" in state.clear_caches()
    assert store_module.carried_files() == []
