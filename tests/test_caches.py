"""The caches of the process and the one function that clears them (O-26 item 3
of meta/decisions/2026-10-18-owner.md; decision 157 (a), (b) of
meta/decisions/decisions-2026-10-18-m20.md; decisions 2026-10-14 80 (b),
2026-10-15-m14 114, 2026-10-16-m15 121; DESIGN 10.4).

``state.clear_caches`` empties every cache registered with it: the synthetic
source's series, the trusted hashes, the per-run bar verification, the
table's journal sums and exposure records, and the dashboard's critical t
values. The table's exposure records are kept per file, keyed by its path and
its length and the sha256 of its bytes, for one state directory and track at
a time: a file rewritten with other bytes of the same length is read again,
and a read of another state directory forgets the first one's.

Every file is written here, under the test's temporary directory; nothing
reads a clock and no random draw is made.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from discotrade import dashboard, journal, paper, state, table
from discotrade.bars import store
from discotrade.sources import synth

TRACK = "test_synth"
D1, D2 = date(2019, 6, 3), date(2019, 6, 4)
#: The caches the clearing function must name, each by its module and name.
CACHES = {"discotrade.sources.synth._SERIES", "discotrade.journal._DIGESTS",
          "discotrade.bars.store._RUN", "discotrade.table._DAY_SUMS",
          "discotrade.table._EXPOSURE", "discotrade.dashboard._t_critical",
          "discotrade.alerts._SPLITS"}


def write_exposure(root: Path, position: float) -> tuple[Path, Path]:
    """Unit and position records under ``root`` written without compression or
    dictionary, so that a changed float leaves each file's length as it was."""
    unit = pa.Table.from_pylist(
        [{"instrument": "SYNA", "date": D1, "unit": 0.01},
         {"instrument": "SYNA", "date": D2, "unit": -0.02}], schema=paper.UNIT_SCHEMA)
    positions = pa.Table.from_pylist(
        [{"subject": "rc:0", "instrument": "SYNA", "date": D1, "rows": 2, "position": position},
         {"subject": "rc:0", "instrument": "SYNA", "date": D2, "rows": 1, "position": 0.25},
         {"subject": "rc:1", "instrument": "SYNA", "date": D1, "rows": 2, "position": -1.0}],
        schema=paper.POSITIONS_SCHEMA)
    out = []
    for path, frame in ((paper.unit_path(root, TRACK), unit),
                        (paper.positions_path(root, TRACK), positions)):
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(frame, path, compression="none", use_dictionary=False)
        out.append(path)
    return out[0], out[1]


def test_clear_caches_names_and_empties_every_cache(tmp_path):
    root = tmp_path / "state"
    write_exposure(root, 0.5)
    synth._SERIES[("key",)] = ("value",)
    journal._DIGESTS[tmp_path / "f"] = ((1,), "digest")
    table._DAY_SUMS[(TRACK, D1.isoformat(), "hash")] = {}
    table.exposure_records(root, TRACK)
    dashboard._t_critical(0.95, 10)
    with store.day_run():
        store._RUN[("path", 1, "hash")] = pd.DataFrame()
        assert set(state.registered_caches()) == CACHES
        for name in CACHES:
            assert name in state.clear_caches.__doc__, name
        cleared = state.clear_caches()
        assert set(cleared) == CACHES
        assert store._RUN == {}
    assert synth._SERIES == {}
    assert journal._DIGESTS == {}
    assert table._DAY_SUMS == {}
    assert table.cached_exposure_files() == []
    assert dashboard._t_critical.cache_info().currsize == 0


def test_the_per_run_bar_verification_outside_a_day_run_stays_none():
    assert store._RUN is None
    state.clear_caches()
    assert store._RUN is None


def test_exposure_records_equal_the_files_and_are_split_per_subject(tmp_path):
    root = tmp_path / "state"
    write_exposure(root, 0.5)
    got = table.exposure_records(root, TRACK)
    pd.testing.assert_frame_equal(got.unit, pq.read_table(paper.unit_path(root, TRACK))
                                  .to_pandas())
    whole = pq.read_table(paper.positions_path(root, TRACK)).to_pandas()
    pd.testing.assert_frame_equal(got.positions, whole)
    assert sorted(got.by_subject) == ["rc:0", "rc:1"]
    for subject, mine in got.by_subject.items():
        pd.testing.assert_frame_equal(mine, whole[whole["subject"] == subject])
    again = table.exposure_records(root, TRACK)             # the same bytes: reused
    assert again.unit is got.unit and again.positions is got.positions
    assert again.by_subject is got.by_subject


def test_staged_exposure_records_are_read_first(tmp_path):
    root, staging = tmp_path / "state", tmp_path / "staging"
    write_exposure(root, 0.5)
    write_exposure(staging, 0.75)
    got = table.exposure_records(root, TRACK, into=staging)
    assert float(got.positions["position"].iloc[0]) == 0.75
    with pytest.raises(ValueError, match="no derived exposure records"):
        table.exposure_records(tmp_path / "empty", TRACK)


def test_a_rewritten_file_of_the_same_length_is_read_again(tmp_path):
    root = tmp_path / "state"
    _, positions = write_exposure(root, 0.5)
    before = positions.read_bytes()
    first = table.exposure_records(root, TRACK)
    assert float(first.positions["position"].iloc[0]) == 0.5
    write_exposure(root, 0.125)
    after = positions.read_bytes()
    assert len(after) == len(before) and after != before
    second = table.exposure_records(root, TRACK)
    assert float(second.positions["position"].iloc[0]) == 0.125
    assert float(second.by_subject["rc:0"]["position"].iloc[0]) == 0.125


def test_the_cache_holds_one_state_directory_and_track_at_a_time(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    write_exposure(one, 0.5)
    write_exposure(two, 0.5)
    table.exposure_records(one, TRACK)
    held = table.cached_exposure_files()
    assert held and all(Path(p).is_relative_to(one) for p in held)
    table.exposure_records(two, TRACK)
    held = table.cached_exposure_files()
    assert held and all(Path(p).is_relative_to(two) for p in held)
