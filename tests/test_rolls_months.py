"""The roll scan's contracts kept per whole month (O-26 items 2 and 3 of
meta/decisions/2026-10-18-owner.md; decisions 157 (a), (b) and 158 of
meta/decisions/decisions-2026-10-18-m20.md; decision 2026-10-14 80 (b);
DESIGN 5.6).

``rolls.update_rolls`` scans an instrument's stored bars from its last
recorded roll (or its first trusted bar). It now reads the scan's month files
through the store first, each verified, and when every bar of the scan holds
one contract it returns no roll without building the scan's frame: the
distinct contracts of each month file lying wholly inside the scan are kept in
``rolls._MONTH_CONTRACTS``, keyed by its path and index entry (row count and
content hash), for one store at a time. Otherwise it scans as before. The
expected rolls are computed here from the stored contracts.

Every file is written under the test's temporary directory; nothing reads a
clock and no random draw is made.
"""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from discotrade import rolls, state
from discotrade.bars.store import BarStore, BarStoreError, day_run

TRACK, HOUR = "t", 3600
FAR = pd.Timestamp("2030-01-01", tz="UTC")
INST = SimpleNamespace(symbol="S", trusted_from=date(2019, 5, 1))
DAY = date(2019, 9, 1)


class NoContract:
    """A source that holds no contract's bars, so every roll gap is estimated."""

    def fetch_contract(self, instrument, contract, start, end):
        return pd.DataFrame({"ts": pd.Series([], dtype="datetime64[ns, UTC]"),
                             "close": pd.Series([], dtype="float64")})


def bars(start: str, n: int, contract: str, base: float = 100.0) -> pd.DataFrame:
    ts = pd.date_range(start, periods=n, freq="h", tz="UTC")
    values = [base + k for k in range(n)]
    return pd.DataFrame({"ts": ts, "open": values, "high": values, "low": values,
                         "close": values, "volume": [1.0] * n, "contract": [contract] * n})


def expected_rolls(store: BarStore) -> list[tuple[pd.Timestamp, str, str]]:
    frames = [pd.read_parquet(p) for p in sorted((store.root / "S").glob("*.parquet"))]
    whole = pd.concat(frames, ignore_index=True)
    c = whole["contract"].tolist()
    return [(whole["ts"].iloc[u], c[u - 1], c[u]) for u in range(1, len(c)) if c[u] != c[u - 1]]


def test_one_contract_gives_no_roll_and_a_later_change_is_found(tmp_path):
    state.clear_caches()
    root = tmp_path / "state"
    store = BarStore(root, TRACK, HOUR)
    store.append("S", bars("2019-05-01 00:00", 24 * 80, "S-A"), FAR)    # May to July
    for _ in range(2):
        with day_run():
            assert rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY) == ((), ())
    assert not rolls.roll_path(root, TRACK, "S").exists()
    assert rolls.cached_months()
    store.append("S", bars("2019-07-20 00:00", 24 * 20, "S-B", 50.0), FAR)
    with day_run():
        found, notices = rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY)
    assert [(r.ts, r.old, r.new) for r in found] == expected_rolls(store)
    assert len(found) == 1 and found[0].estimated and len(notices) == 1
    assert rolls.read_rolls(rolls.roll_path(root, TRACK, "S")) == list(found)
    with day_run():
        assert rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY) == ((), ())


def test_a_change_appended_to_a_kept_month_file_is_found(tmp_path):
    state.clear_caches()
    root = tmp_path / "state"
    store = BarStore(root, TRACK, HOUR)
    store.append("S", bars("2019-05-01 00:00", 24 * 70, "S-A"), FAR)    # to 2019-07-09
    with day_run():
        assert rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY) == ((), ())
    held = rolls.cached_months()
    assert any(p.endswith("2019-07.parquet") for p in held)              # kept as a whole month
    store.append("S", bars("2019-07-20 00:00", 24 * 5, "S-B", 50.0), FAR)   # the same file
    with day_run():
        found, _ = rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY)
    assert [(r.ts, r.old, r.new) for r in found] == expected_rolls(store)
    assert found[0].ts == pd.Timestamp("2019-07-20 00:00", tz="UTC")


def test_a_change_inside_a_whole_month_is_found(tmp_path):
    state.clear_caches()
    root = tmp_path / "state"
    store = BarStore(root, TRACK, HOUR)
    store.append("S", bars("2019-05-01 00:00", 24 * 40, "S-A"), FAR)
    store.append("S", bars("2019-06-10 00:00", 24 * 40, "S-B", 50.0), FAR)
    with day_run():
        found, _ = rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY)
    assert [(r.ts, r.old, r.new) for r in found] == expected_rolls(store)
    assert found[0].ts == pd.Timestamp("2019-06-10 00:00", tz="UTC")


def test_a_revised_whole_month_is_refused(tmp_path):
    state.clear_caches()
    root = tmp_path / "state"
    store = BarStore(root, TRACK, HOUR)
    store.append("S", bars("2019-05-01 00:00", 24 * 80, "S-A"), FAR)
    with day_run():
        rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY)
    path = store.month_path("S", "2019-06")
    frame = pd.read_parquet(path)
    frame.loc[5, "contract"] = "S-Z"
    frame.to_parquet(path, index=False, engine="pyarrow")
    for scope in (day_run, None):
        with pytest.raises(BarStoreError, match="revised data point"):
            if scope is None:
                rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY)
            else:
                with scope():
                    rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY)


def test_the_cache_holds_one_store_and_clear_caches_empties_it(tmp_path):
    state.clear_caches()
    for name in ("one", "two"):
        root = tmp_path / name
        BarStore(root, TRACK, HOUR).append("S", bars("2019-05-01 00:00", 24 * 80, "S-A"), FAR)
        with day_run():
            rolls.update_rolls(root, TRACK, HOUR, INST, NoContract(), DAY)
        held = rolls.cached_months()
        assert held and all(Path(p).is_relative_to(root) for p in held)
    assert "discotrade.rolls._MONTH_CONTRACTS" in state.clear_caches()
    assert rolls.cached_months() == []
