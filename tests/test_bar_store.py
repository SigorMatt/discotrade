"""The bar store (DESIGN 5.1, 5.2; I-5, I-12, I-14).

Every test writes into a pytest ``tmp_path`` state directory. "Closed" is
judged against ``available_until``, computed here from a ``FixedClock`` the
way the synthetic source does (``available_until(now) = now``, DESIGN 5.5).
"""

import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from discotrade.bars.store import BarStore, BarStoreError
from discotrade.clock import FixedClock
from discotrade.state import content_hash

HOUR = 3600
SYM = "SYNA"


def _ts(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz="UTC")


def bars(start: str, count: int, contract: str = SYM, base: float = 100.0) -> pd.DataFrame:
    ts = pd.date_range(_ts(start), periods=count, freq="h")
    price = [base + i / 3.0 for i in range(count)]
    return pd.DataFrame(
        {
            "ts": ts,
            "open": price,
            "high": [p + 0.5 for p in price],
            "low": [p - 0.5 for p in price],
            "close": [p + 0.1 for p in price],
            "volume": [10.0 + i for i in range(count)],
            "contract": [contract] * count,
        }
    )


def clock_at(text: str) -> FixedClock:
    return FixedClock(datetime.fromisoformat(text).replace(tzinfo=UTC))


@pytest.fixture
def store(tmp_path):
    return BarStore(tmp_path / "state", "hourly", HOUR)


LATE = clock_at("2027-01-01T00:00:00").now()


def test_appended_bars_read_back(store):
    new = bars("2026-03-02 00:00", 5)
    assert store.append(SYM, new, LATE) == 5
    got = store.read_range(SYM, _ts("2026-03-01"), _ts("2026-04-01"))
    pd.testing.assert_frame_equal(got, new, check_dtype=False)
    assert list(got.columns) == ["ts", "open", "high", "low", "close", "volume", "contract"]
    assert str(got["ts"].dtype) == "datetime64[ns, UTC]"


# --- the writer refuses ------------------------------------------------------


def test_refuses_a_bar_that_has_not_closed(store, tmp_path):
    now = clock_at("2026-03-02T03:30:00").now()
    # The bar opening at 03:00 closes at 04:00, later than now.
    with pytest.raises(BarStoreError, match="not closed"):
        store.append(SYM, bars("2026-03-02 00:00", 4), now)
    assert store.last_ts(SYM) is None
    assert not (tmp_path / "state" / "bars" / "hourly" / SYM).exists()


def test_accepts_a_bar_that_closes_exactly_at_available_until(store):
    now = clock_at("2026-03-02T04:00:00").now()
    assert store.append(SYM, bars("2026-03-02 00:00", 4), now) == 4
    assert store.last_ts(SYM) == _ts("2026-03-02 03:00")


def test_refuses_a_bar_not_later_than_the_last_stored(store):
    store.append(SYM, bars("2026-03-02 00:00", 4), LATE)
    before = store.read_range(SYM, _ts("2026-03-01"), _ts("2026-04-01"))
    for start in ("2026-03-02 03:00", "2026-03-02 01:00", "2026-03-01 00:00"):
        with pytest.raises(BarStoreError, match="not later"):
            store.append(SYM, bars(start, 3), LATE)
    pd.testing.assert_frame_equal(
        store.read_range(SYM, _ts("2026-03-01"), _ts("2026-04-01")), before
    )


def test_refuses_a_duplicate_ts_within_a_batch(store):
    batch = bars("2026-03-02 00:00", 3)
    batch = pd.concat([batch, batch.iloc[[2]]], ignore_index=True)
    with pytest.raises(BarStoreError, match="duplicate"):
        store.append(SYM, batch, LATE)
    assert store.last_ts(SYM) is None


def test_refuses_a_batch_out_of_order(store):
    batch = bars("2026-03-02 00:00", 3).iloc[[0, 2, 1]].reset_index(drop=True)
    with pytest.raises(BarStoreError, match="sorted"):
        store.append(SYM, batch, LATE)


def test_refuses_a_bar_without_schema(store):
    with pytest.raises(BarStoreError, match="columns"):
        store.append(SYM, bars("2026-03-02 00:00", 2).drop(columns=["volume"]), LATE)
    naive = bars("2026-03-02 00:00", 2)
    naive["ts"] = naive["ts"].dt.tz_localize(None)
    with pytest.raises(BarStoreError, match="UTC"):
        store.append(SYM, naive, LATE)


def test_refused_batch_writes_nothing_even_when_its_first_bars_are_good(store):
    store.append(SYM, bars("2026-03-02 00:00", 2), LATE)
    index_before = store.index_path.read_text()
    now = clock_at("2026-03-02T04:30:00").now()
    with pytest.raises(BarStoreError, match="not closed"):
        store.append(SYM, bars("2026-03-02 02:00", 5), now)
    assert store.index_path.read_text() == index_before
    assert store.last_ts(SYM) == _ts("2026-03-02 01:00")


# --- append-only -------------------------------------------------------------


def test_append_leaves_every_old_row_identical(store):
    store.append(SYM, bars("2026-03-02 00:00", 6), LATE)
    path = store.month_path(SYM, "2026-03")
    old_file = pd.read_parquet(path)
    old_hash = content_hash(old_file, ["ts"])

    store.append(SYM, bars("2026-03-02 06:00", 4, base=200.0), LATE)
    new_file = pd.read_parquet(path)
    assert len(new_file) == 10
    head = new_file.iloc[: len(old_file)].reset_index(drop=True)
    pd.testing.assert_frame_equal(head, old_file, check_exact=True)
    assert content_hash(head, ["ts"]) == old_hash
    assert new_file["ts"].is_monotonic_increasing
    assert not list(path.parent.glob("*.tmp"))


def test_append_with_nothing_new_writes_nothing(store):
    store.append(SYM, bars("2026-03-02 00:00", 2), LATE)
    index_before = store.index_path.read_text()
    assert store.append(SYM, bars("2026-03-02 00:00", 0), LATE) == 0
    assert store.index_path.read_text() == index_before


# --- month files and the index ------------------------------------------------


def test_month_files_split_on_the_utc_month_of_ts(store, tmp_path):
    # 2026-03-31 22:00 UTC to 2026-04-01 01:00 UTC: four bars, two months.
    store.append(SYM, bars("2026-03-31 22:00", 4), LATE)
    folder = tmp_path / "state" / "bars" / "hourly" / SYM
    assert sorted(p.name for p in folder.iterdir()) == ["2026-03.parquet", "2026-04.parquet"]
    march = pd.read_parquet(folder / "2026-03.parquet")
    april = pd.read_parquet(folder / "2026-04.parquet")
    assert list(march["ts"]) == [_ts("2026-03-31 22:00"), _ts("2026-03-31 23:00")]
    assert list(april["ts"]) == [_ts("2026-04-01 00:00"), _ts("2026-04-01 01:00")]


def test_month_split_ignores_a_non_utc_offset_in_the_input(store):
    batch = bars("2026-03-31 22:00", 4)
    batch["ts"] = batch["ts"].dt.tz_convert("Asia/Tokyo")   # all four read April locally
    store.append(SYM, batch, LATE)
    assert len(pd.read_parquet(store.month_path(SYM, "2026-03"))) == 2
    assert len(pd.read_parquet(store.month_path(SYM, "2026-04"))) == 2


def test_index_records_first_last_rows_and_hashes(store):
    store.append(SYM, bars("2026-03-31 20:00", 6), LATE)
    store.append("SYNB", bars("2026-05-10 00:00", 3, contract="SYNBM6"), LATE)
    store.append(SYM, bars("2026-04-01 02:00", 2), LATE)

    index = json.loads(store.index_path.read_text())
    assert store.index_path == store.root / "index.json"
    assert sorted(index) == ["SYNA", "SYNB"]
    a = index["SYNA"]
    assert a["first_ts"] == "2026-03-31T20:00:00+00:00"
    assert a["last_ts"] == "2026-04-01T03:00:00+00:00"
    assert a["rows"] == 8
    assert sorted(a["months"]) == ["2026-03", "2026-04"]
    for month, rows, first, last in (
        ("2026-03", 4, "2026-03-31T20:00:00+00:00", "2026-03-31T23:00:00+00:00"),
        ("2026-04", 4, "2026-04-01T00:00:00+00:00", "2026-04-01T03:00:00+00:00"),
    ):
        entry = a["months"][month]
        assert entry["rows"] == rows
        assert entry["first_ts"] == first
        assert entry["last_ts"] == last
        on_disk = pd.read_parquet(store.month_path(SYM, month))
        assert entry["hash"] == content_hash(on_disk, ["ts"])
    b = index["SYNB"]
    assert (b["rows"], b["first_ts"], b["last_ts"]) == (
        3, "2026-05-10T00:00:00+00:00", "2026-05-10T02:00:00+00:00"
    )


# --- the reader --------------------------------------------------------------


def test_read_range_is_half_open_across_months(store):
    store.append(SYM, bars("2026-03-31 20:00", 10), LATE)
    got = store.read_range(SYM, _ts("2026-03-31 22:00"), _ts("2026-04-01 02:00"))
    assert list(got["ts"]) == list(pd.date_range(_ts("2026-03-31 22:00"), periods=4, freq="h"))
    assert got.index.tolist() == [0, 1, 2, 3]
    assert store.read_range(SYM, _ts("2026-03-31 22:00"), _ts("2026-03-31 22:00")).empty
    assert store.read_range(SYM, _ts("2026-01-01"), _ts("2026-02-01")).empty
    assert store.read_range("NONE", _ts("2026-01-01"), _ts("2027-01-01")).empty


def test_last_n_ends_at_the_given_bar_inclusive(store):
    store.append(SYM, bars("2026-03-31 20:00", 10), LATE)
    got = store.last_n(SYM, _ts("2026-04-01 01:00"), 4)
    assert list(got["ts"]) == list(pd.date_range(_ts("2026-03-31 22:00"), periods=4, freq="h"))
    assert got.index.tolist() == [0, 1, 2, 3]
    # Fewer bars stored than asked: every stored bar up to the given one.
    assert len(store.last_n(SYM, _ts("2026-03-31 21:00"), 5)) == 2


def test_last_n_refuses_a_bar_that_is_not_stored(store):
    store.append(SYM, bars("2026-03-02 00:00", 4), LATE)
    with pytest.raises(BarStoreError, match="no stored bar"):
        store.last_n(SYM, _ts("2026-03-02 00:30"), 2)
    with pytest.raises(BarStoreError):
        store.last_n(SYM, _ts("2026-03-02 01:00"), 0)


def test_reader_refuses_a_month_file_that_no_longer_matches_the_index(store):
    store.append(SYM, bars("2026-03-31 20:00", 8), LATE)
    path = store.month_path(SYM, "2026-03")
    revised = pd.read_parquet(path)
    revised.loc[1, "close"] = revised.loc[1, "close"] + 1e-9
    revised.to_parquet(path, index=False)

    with pytest.raises(BarStoreError, match="2026-03.*index"):
        store.read_range(SYM, _ts("2026-03-31"), _ts("2026-04-02"))
    with pytest.raises(BarStoreError, match="index"):
        store.last_n(SYM, _ts("2026-04-01 01:00"), 5)
    # The untouched month still reads.
    assert len(store.read_range(SYM, _ts("2026-04-01"), _ts("2026-04-02"))) == 4


def test_writer_refuses_to_append_onto_a_revised_month_file(store):
    store.append(SYM, bars("2026-04-01 00:00", 3), LATE)
    path = store.month_path(SYM, "2026-04")
    revised = pd.read_parquet(path)
    revised.loc[0, "volume"] = 0.0
    revised.to_parquet(path, index=False)
    with pytest.raises(BarStoreError, match="index"):
        store.append(SYM, bars("2026-04-01 03:00", 1), LATE)
    pd.testing.assert_frame_equal(pd.read_parquet(path), revised)


def test_reader_refuses_a_missing_month_file(store):
    store.append(SYM, bars("2026-03-31 20:00", 8), LATE)
    store.month_path(SYM, "2026-04").unlink()
    with pytest.raises(BarStoreError, match="missing"):
        store.read_range(SYM, _ts("2026-04-01"), _ts("2026-04-02"))


def test_store_never_reads_the_wall_clock():
    import discotrade.bars.store as module

    source = open(module.__file__, encoding="utf-8").read()
    for call in ("now(", "today(", "time.time", "utcnow"):
        assert call not in source
