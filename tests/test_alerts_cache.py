"""Step 6's split cache (mission 20 U2; O-26 items 2 and 3 of
meta/decisions/2026-10-18-owner.md; decisions 157 (a), (b) and 158 of
meta/decisions/decisions-2026-10-18-m20.md; DESIGN 15.1, 16.1 step 6).

``alerts.slot_series`` computes each random slot's series from the paper, unit
and position records split per subject once per content (``alerts._SPLITS``).
These tests show, on records written here by the product's writers and read
back by its readers:

- each slot's series is ``paper.adjusted``'s for that slot, value for value
  and bit for bit, the slots those with a row on every day of ``W`` in slot
  order, also where a slot holds two rows of one date (then each series is
  ``paper.adjusted``'s own);
- ``alerts.slot_moments`` gives ``stats.control_moments`` of the slot frame
  exactly;
- a value changed in a frame of the same length is split again, equal content
  is served from the cache, the cache holds one state directory and track at
  a time, and ``state.clear_caches`` empties it;
- a day of ``W`` the unit records lack is refused with ``paper.adjusted``'s own
  message.

The expected series come from ``paper.adjusted``, the function the parent
called once per slot, not from ``slot_series``. The values are drawn from
``numpy.random.default_rng(SEED)`` with the seed written here; nothing reads a
clock.
"""

import math
import shutil
import struct
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade import alerts, journal, paper, state, stats
from discotrade.cli import REPO_ROOT

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
SEED = 20261018
SYMBOLS = ("SYNA", "SYNB", "SYNC", "SYND")
DAYS = [date(2019, 6, 3) + timedelta(days=i) for i in range(12)]
W = DAYS[2:10]
SLOTS = 12
#: Slots missing a day of ``W`` (not in ``slot_series``) and one missing a day outside.
GAPS = {"rc:3": DAYS[5], "rc:7": DAYS[9], "rc:10": DAYS[0]}


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    config = tmp_path_factory.mktemp("accfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copyfile(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    return journal.Setup.load(config, TRACK)


def write_records(root, rng, *, twice=None):
    """Paper, unit and position records under ``root``: ``SLOTS`` random slots, one
    approach and one buy-and-hold control, every subject on ``DAYS`` but ``GAPS``;
    ``twice`` a slot given a second row on ``W[3]``. Returned as the readers read them."""
    records, positions, units = [], [], []
    subjects = [(f"rc:{j}", stats.CONTROL_RANDOM) for j in range(SLOTS)]
    subjects += [("a-1", paper.APPROACH), ("bh:SYNA", paper.BH)]
    for d in DAYS:
        units += [{"instrument": s, "date": d, "unit": float(rng.normal(0.0, 0.01))}
                  for s in SYMBOLS]
    for subject, kind in subjects:
        for d in DAYS:
            if GAPS.get(subject) == d:
                continue
            g = float(rng.normal(0.0, 0.01))
            cost = float(rng.uniform(0.0, 0.001))
            for _ in range(2 if (subject == twice and d == W[3]) else 1):
                records.append({"date": d, "subject": subject, "kind": kind, "gross": g,
                                "net_1x": g - cost, "net_2x": g - 2 * cost, "trades": 1,
                                "clean": True})
            for s in (SYMBOLS[:1] if kind == paper.BH else SYMBOLS):
                rows = int(rng.integers(1, 8))
                positions.append({"subject": subject, "instrument": s, "date": d, "rows": rows,
                                  "position": float(rng.normal(0.0, 1.0)) * rows})
    frame = pd.DataFrame(records).sort_values(list(paper.KEY), kind="stable")
    paper.write(root, TRACK, frame.reset_index(drop=True))
    paper.write_exposure(
        root, TRACK,
        pd.DataFrame(units).sort_values(list(paper.UNIT_KEY), kind="stable")
        .reset_index(drop=True),
        pd.DataFrame(positions).sort_values(list(paper.POSITIONS_KEY), kind="stable")
        .reset_index(drop=True))
    return (paper.read(root, TRACK),
            (paper.read_unit(root, TRACK), paper.read_positions(root, TRACK)))


@pytest.fixture
def written(tmp_path):
    state.clear_caches()
    root = tmp_path / "state"
    records, exposure = write_records(root, np.random.default_rng(SEED))
    yield root, records, exposure
    state.clear_caches()


def bits(series):
    return series.to_numpy(dtype=np.float64).tobytes()


def parent_series(root, setup, records, exposure, days):
    """What the parent's ``slot_series`` gave: ``paper.adjusted`` of each slot with a
    row on every day of ``days``, in slot order (the slots counted here)."""
    wanted = set(days)
    out = {}
    for j in range(SLOTS):
        slot = f"rc:{j}"
        mine = records[(records["subject"] == slot) & records["date"].isin(wanted)]
        if set(mine["date"]) == wanted:
            out[slot] = paper.adjusted(root, setup, slot, sorted(wanted), "net_1x",
                                       records=mine, exposure=exposure)
    return out


def assert_same(got, want):
    assert list(got) == list(want)
    for slot in want:
        assert list(got[slot].index) == list(want[slot].index), slot
        assert bits(got[slot]) == bits(want[slot]), slot
        assert got[slot].name == want[slot].name and got[slot].dtype == want[slot].dtype


def test_each_slot_series_is_paper_adjusted_of_the_slot(setup, written):
    root, records, exposure = written
    got = alerts.slot_series(root, setup, W, records, exposure=exposure)
    want = parent_series(root, setup, records, exposure, W)
    assert sorted(want, key=lambda s: int(s[3:])) == list(want)
    assert set(want) == {f"rc:{j}" for j in range(SLOTS)} - {"rc:3", "rc:7"}
    assert_same(got, want)
    assert set(alerts.cached_splits()) == {"slots", "unit", "positions"}
    # the same call with the exposure records read here gives the same series
    assert_same(alerts.slot_series(root, setup, W, records), want)


def test_a_slot_with_two_rows_of_one_date_is_paper_adjusted_s_own(setup, tmp_path):
    state.clear_caches()
    root = tmp_path / "state"
    records, exposure = write_records(root, np.random.default_rng(SEED), twice="rc:5")
    assert (records["subject"] == "rc:5").sum() == len(DAYS) + 1
    got = alerts.slot_series(root, setup, W, records, exposure=exposure)
    assert len(got["rc:5"]) == len(W) + 1
    assert_same(got, parent_series(root, setup, records, exposure, W))
    state.clear_caches()


def test_a_changed_value_of_the_same_length_is_split_again(setup, written):
    root, records, exposure = written
    first = alerts.slot_series(root, setup, W, records, exposure=exposure)
    held = alerts.cached_splits()
    changed = records.copy()
    at = changed.index[(changed["subject"] == "rc:1") & (changed["date"] == W[4])][0]
    changed.loc[at, "net_1x"] = float(changed.loc[at, "net_1x"]) + 0.5
    assert len(changed) == len(records)
    got = alerts.slot_series(root, setup, W, changed, exposure=exposure)
    assert alerts.cached_splits()["slots"] != held["slots"]
    assert got["rc:1"][W[4]] != first["rc:1"][W[4]]
    assert_same(got, parent_series(root, setup, changed, exposure, W))
    moved = exposure[1].copy()
    at = moved.index[(moved["subject"] == "rc:2") & (moved["date"] == W[0])][0]
    moved.loc[at, "position"] = float(moved.loc[at, "position"]) + 3.0
    again = alerts.slot_series(root, setup, W, changed, exposure=(exposure[0], moved))
    assert alerts.cached_splits()["positions"] != held["positions"]
    assert bits(again["rc:2"]) != bits(got["rc:2"])
    assert_same(again, parent_series(root, setup, changed, (exposure[0], moved), W))


def test_equal_content_is_served_from_the_cache(setup, written):
    root, records, exposure = written
    alerts.slot_series(root, setup, W, records, exposure=exposure)
    held = dict(alerts._SPLITS["held"])
    alerts.slot_series(root, setup, W, records.copy(deep=True),
                       exposure=(exposure[0].copy(deep=True), exposure[1].copy(deep=True)))
    for role in ("slots", "unit", "positions"):
        assert alerts._SPLITS["held"][role][1] is held[role][1], role


def test_the_cache_holds_one_state_directory_and_track_at_a_time(setup, written, tmp_path):
    root, records, exposure = written
    other = tmp_path / "other"
    shutil.copytree(root, other)
    alerts.slot_series(root, setup, W, records, exposure=exposure)
    assert alerts._SPLITS["scope"] == (str(root.resolve()), TRACK)
    split = alerts._SPLITS["held"]["slots"][1]
    alerts.slot_series(other, setup, W, records, exposure=exposure)
    assert alerts._SPLITS["scope"] == (str(other.resolve()), TRACK)
    assert alerts._SPLITS["held"]["slots"][1] is not split


def test_clear_caches_empties_the_split_cache(setup, written):
    root, records, exposure = written
    alerts.slot_series(root, setup, W, records, exposure=exposure)
    assert alerts.cached_splits() and alerts._SPLITS["scope"] is not None
    cleared = state.clear_caches()
    assert "discotrade.alerts._SPLITS" in cleared
    assert alerts.cached_splits() == {}
    assert alerts._SPLITS["scope"] is None


def same_float(a, b):
    return struct.pack("<d", a) == struct.pack("<d", b) or (math.isnan(a) and math.isnan(b))


def test_slot_moments_equal_control_moments_on_the_slot_frame(setup, written):
    root, records, exposure = written
    for days in (W, DAYS[:2], [W[0], W[0], W[1]]):
        slots = alerts.slot_series(root, setup, days, records, exposure=exposure)
        want = stats.control_moments(alerts._slot_frame(slots), days,
                                     column=alerts.SLOT_COLUMN)
        got = alerts.slot_moments(slots, days)
        assert all(same_float(g, w) for g, w in zip(got, want, strict=True)), days
    assert not math.isnan(alerts.slot_moments(
        alerts.slot_series(root, setup, W, records, exposure=exposure), W)[0])
    # a series not indexed by every day of W once goes through the slot frame
    slots = alerts.slot_series(root, setup, W, records, exposure=exposure)
    slots["rc:0"] = slots["rc:0"].iloc[1:]
    want = stats.control_moments(alerts._slot_frame(slots), W, column=alerts.SLOT_COLUMN)
    got = alerts.slot_moments(slots, W)
    assert all(same_float(g, w) for g, w in zip(got, want, strict=True))


def test_a_day_the_unit_records_lack_is_refused_as_paper_adjusted_refuses_it(setup, written):
    root, records, exposure = written
    unit = exposure[0][exposure[0]["date"] != W[2]]
    with pytest.raises(ValueError) as want:
        paper.adjusted(root, setup, "rc:0", W, "net_1x", records=records,
                       exposure=(unit, exposure[1]))
    with pytest.raises(ValueError) as got:
        alerts.slot_series(root, setup, W, records, exposure=(unit, exposure[1]))
    assert str(got.value) == str(want.value)
