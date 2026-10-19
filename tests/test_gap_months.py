"""The gap check's missing bars kept per complete month (O-26 items 2 and 3 of
meta/decisions/2026-10-18-owner.md; decisions 157 (a), (b) and 158 of
meta/decisions/decisions-2026-10-18-m20.md; decision 2026-10-14 80 (b);
DESIGN 5.4).

``gaps.find_missing`` gives every expected bar of an instrument's checked span
that the store does not hold. It now takes that span month by month (the UTC
months of the store's files) and keeps the missing bars of each month before
the one holding the last stored bar in ``gaps._MONTH_MISSING``, keyed by the
month file's path and index entry (row count and hash), the calendar record,
the bar size and the month's lower bound, for one store at a time. Every month
file of the span is still read through the store, so a revised file is
refused as before. The expected list is computed here as the parent computed
it: ``tradingcal.expected_bars`` over the whole span less the stored times read
from the files.

Every file is written under the test's temporary directory; nothing reads a
clock; the one random draw (the dropped bars) is seeded.
"""

import dataclasses
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from discotrade import state, tradingcal
from discotrade.bars import gaps
from discotrade.bars.store import BarStore, BarStoreError, day_run
from discotrade.cli import REPO_ROOT
from discotrade.config import Closure, load_calendar

CALENDARS = REPO_ROOT / "tests" / "fixtures" / "config" / "calendars"
BAR = 3600
FAR = pd.Timestamp("2030-01-01", tz="UTC")
SEED = 20261018


def calendar(name):
    return load_calendar(CALENDARS / f"{name}.toml")


def bars_at(times) -> pd.DataFrame:
    ts = pd.DatetimeIndex(times).tz_convert("UTC")
    values = [100.0 + k for k in range(len(ts))]
    return pd.DataFrame({"ts": ts, "open": values, "high": values, "low": values,
                         "close": values, "volume": [1.0] * len(ts),
                         "contract": ["C1"] * len(ts)})


def reference(root: Path, track: str, inst, cal, until):
    """The parent's reading: the expected bars of the whole span less the stored."""
    index = json.loads((root / "bars" / track / "index.json").read_text(encoding="utf-8"))
    entry = index.get(inst.symbol)
    if entry is None:
        return []
    first = datetime.fromisoformat(entry["first_ts"]).astimezone(UTC)
    last = datetime.fromisoformat(entry["last_ts"]).astimezone(UTC)
    start = max(first, datetime.combine(inst.trusted_from, datetime.min.time(), tzinfo=UTC))
    end = last + timedelta(seconds=BAR)
    if until is not None:
        end = min(end, until)
    if start >= end:
        return []
    files = sorted((root / "bars" / track / inst.symbol).glob("*.parquet"))
    ts = pd.concat([pd.read_parquet(f)["ts"] for f in files], ignore_index=True)
    ts = ts[(ts >= pd.Timestamp(start)) & (ts < pd.Timestamp(end))]
    if ts.empty:
        return []
    have = {t.to_pydatetime() for t in ts}
    last = ts.iloc[-1].to_pydatetime()
    return [t for t in tradingcal.expected_bars(cal, start, last + timedelta(seconds=1), BAR)
            if t not in have]


def schedule(cal, first: datetime, last: datetime):
    """The calendar's bars in [first, last) with about 3% dropped, seeded."""
    times = tradingcal.expected_bars(cal, first, last, BAR)
    keep = np.random.default_rng(SEED).random(len(times)) >= 0.03
    return [t for t, k in zip(times, keep, strict=True) if k]


def counting(monkeypatch) -> list:
    calls = []
    real = gaps.expected_bars

    def counted(*args, **kw):
        calls.append(args)
        return real(*args, **kw)

    monkeypatch.setattr(gaps, "expected_bars", counted)
    return calls


@pytest.mark.parametrize("name, trusted", [("synth_week", date(2019, 5, 1)),
                                           ("synth_week", date(2019, 6, 17)),
                                           ("always_open", date(2019, 5, 1))])
def test_the_missing_bars_equal_the_whole_span_day_after_day(tmp_path, name, trusted):
    state.clear_caches()
    cal = calendar(name)
    inst = SimpleNamespace(symbol="S", trusted_from=trusted)
    root = tmp_path / "state"
    store = BarStore(root, "t", BAR)
    times = schedule(cal, datetime(2019, 5, 20, tzinfo=UTC), datetime(2019, 9, 10, tzinfo=UTC))
    day, k, checked = date(2019, 5, 21), 0, 0
    while day <= date(2019, 9, 9):
        close = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
        new = [t for t in times[k:] if t < close]
        if new:
            store.append("S", bars_at(new), FAR)
            k += len(new)
        for until in (None, close, close - timedelta(days=3)):
            with day_run():
                got = gaps.find_missing(store, inst, cal, BAR, until)
            assert got == reference(root, "t", inst, cal, until), (day, until)
            checked += bool(got)
        day += timedelta(days=4)
    assert checked > 20                                  # the drops are found


def test_complete_months_are_reused_and_the_last_is_computed(tmp_path, monkeypatch):
    state.clear_caches()
    cal = calendar("synth_week")
    inst = SimpleNamespace(symbol="S", trusted_from=date(2019, 5, 1))
    store = BarStore(tmp_path / "state", "t", BAR)
    store.append("S", bars_at(schedule(cal, datetime(2019, 5, 20, tzinfo=UTC),
                                       datetime(2019, 9, 10, tzinfo=UTC))), FAR)
    with day_run():
        want = gaps.find_missing(store, inst, cal, BAR)
    calls = counting(monkeypatch)
    with day_run():
        assert gaps.find_missing(store, inst, cal, BAR) == want
    assert len(calls) == 1                               # 2019-09 only
    shut = dataclasses.replace(cal, closures=cal.closures + (Closure(
        start=datetime(2019, 6, 10, 0, 0), end=datetime(2019, 6, 12, 0, 0), note="test",
        provenance=None),))
    del calls[:]
    with day_run():
        got = gaps.find_missing(store, inst, shut, BAR)
    assert len(calls) == 5                               # another record: every month again
    assert got == reference(tmp_path / "state", "t", inst, shut, None)


def test_a_revised_complete_month_is_refused(tmp_path):
    state.clear_caches()
    cal = calendar("synth_week")
    inst = SimpleNamespace(symbol="S", trusted_from=date(2019, 5, 1))
    store = BarStore(tmp_path / "state", "t", BAR)
    store.append("S", bars_at(schedule(cal, datetime(2019, 5, 20, tzinfo=UTC),
                                       datetime(2019, 8, 10, tzinfo=UTC))), FAR)
    with day_run():
        gaps.find_missing(store, inst, cal, BAR)
    path = store.month_path("S", "2019-06")
    frame = pd.read_parquet(path)
    frame.loc[3, "close"] += 0.25
    frame.to_parquet(path, index=False, engine="pyarrow")
    with day_run():
        with pytest.raises(BarStoreError, match="revised data point"):
            gaps.find_missing(store, inst, cal, BAR)
    with pytest.raises(BarStoreError, match="revised data point"):
        gaps.find_missing(store, inst, cal, BAR)


def test_the_cache_holds_one_store_and_clear_caches_empties_it(tmp_path):
    state.clear_caches()
    cal = calendar("synth_week")
    inst = SimpleNamespace(symbol="S", trusted_from=date(2019, 5, 1))
    for name in ("one", "two"):
        store = BarStore(tmp_path / name, "t", BAR)
        store.append("S", bars_at(schedule(cal, datetime(2019, 5, 20, tzinfo=UTC),
                                           datetime(2019, 8, 10, tzinfo=UTC))), FAR)
        with day_run():
            gaps.find_missing(store, inst, cal, BAR)
        held = gaps.cached_months()
        assert held and all(Path(p).is_relative_to(tmp_path / name) for p in held)
    assert "discotrade.bars.gaps._MONTH_MISSING" in state.clear_caches()
    assert gaps.cached_months() == []


@pytest.mark.parametrize("second", [(4, 11, 18), (6, 13)], ids=["same-rows", "other-rows"])
def test_a_rewritten_complete_month_gives_its_new_missing_bars(tmp_path, second):
    """Decision 173 of meta/decisions/decisions-2026-10-19-m21.md (REVIEW-20
    should-fix 4; decision 157 (a)): the key of ``_MONTH_MISSING`` changes with
    the month file's content.

    The writers cannot replace a complete month in place: ``BarStore.append``
    refuses a bar not later than the last stored one (I-5), and ``recover``
    only completes an interrupted append, also later than the indexed last bar.
    So the test removes the track's store (its index and month files) and
    writes the new content through ``BarStore.append`` again, under the same
    store root: the month file and its index entry are both the writer's, at
    the same path, with other bars missing from 2019-06 and, in the
    ``same-rows`` case, the same row count and another hash; in the
    ``other-rows`` case, another row count. No cache is cleared between the
    two reads. The expected missing bars are computed here from the times
    written. Nothing reads a clock; no random draw is made.
    """
    state.clear_caches()
    cal = calendar("synth_week")
    inst = SimpleNamespace(symbol="S", trusted_from=date(2019, 5, 1))
    root = tmp_path / "state"
    store = BarStore(root, "t", BAR)
    every = tradingcal.expected_bars(cal, datetime(2019, 5, 20, tzinfo=UTC),
                                     datetime(2019, 8, 10, tzinfo=UTC), BAR)
    june = [t for t in every if (t.year, t.month) == (2019, 6)]

    def write(dropped):
        drop = {june[k] for k in dropped}
        times = [t for t in every if t not in drop]
        store.append("S", bars_at(times), FAR)
        have = set(times)
        return [t for t in tradingcal.expected_bars(cal, times[0], times[-1] + timedelta(seconds=1),
                                                    BAR) if t not in have]

    def june_entry():
        return dict(store.index()["S"]["months"]["2019-06"])

    want = write((3, 10, 17))
    before = june_entry()
    with day_run():
        assert gaps.find_missing(store, inst, cal, BAR) == want
    path = str(store.month_path("S", "2019-06"))
    assert path in gaps.cached_months()                  # June is complete and kept

    store_dir = root / "bars" / "t"
    for f in sorted(store_dir.rglob("*.parquet")):
        f.unlink()
    store.index_path.unlink()
    want_again = write(second)
    after = june_entry()
    assert after["hash"] != before["hash"]
    assert (after["rows"] == before["rows"]) == (len(second) == 3)
    assert [t for t in want_again if t.month == 6] != [t for t in want if t.month == 6]
    assert path in gaps.cached_months()                  # nothing was cleared
    with day_run():
        assert gaps.find_missing(store, inst, cal, BAR) == want_again
