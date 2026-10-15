"""Rolls and the adjusted series (DESIGN 5.6, 5.5 ``bars fetch``; decision
2026-10-12 16; I-5, I-6, I-12).

SYNA is the fixture instrument that rolls quarterly (track ``test_mixed``):
its continuous series is one gap-free underlying plus the constant of the
contract current at each bar (DESIGN 17.1), so every measured roll gap is the
difference of two constants and the adjusted series as of ``t`` is the
underlying plus the constant of the contract current at ``t``. Every state
directory is a pytest temporary directory; the clock is ``--as-of``.
"""

import json
import os
import shutil
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from conftest import MIXED_TWO_YEARS, copy_template

import discotrade.sources as sources
from discotrade.bars.store import BarStore, BarStoreError
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_instrument
from discotrade.rolls import (
    ROLL_GAP_ESTIMATED,
    adjust,
    adjusted_as_of,
    detect_rolls,
    read_rolls,
    roll_path,
    update_rolls,
)
from discotrade.sources.synth import SynthSource

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
HOUR = 3600
START = datetime(2019, 1, 7, tzinfo=UTC)          # SYNA's trusted_from
TWO_YEARS = "2021-01-07T00:00:00+00:00"
ONE_YEAR = "2020-01-07T00:00:00+00:00"
PRICES = ("open", "high", "low", "close")


def inst(symbol):
    return load_instrument(FIXTURE_CONFIG / "instruments" / f"{symbol}.toml")


def with_params(record, **changes):
    params = tuple((k, changes.get(k, v)) for k, v in record.source.params)
    return replace(record, source=replace(record.source, params=params))


@pytest.fixture(scope="module")
def calendars():
    return {p.stem: load_calendar(p) for p in sorted((FIXTURE_CONFIG / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def source(calendars):
    return SynthSource(calendars, HOUR)


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


def fetch(state, config, as_of):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "bars", "fetch"])


def iso(ts):
    return pd.Timestamp(ts).tz_convert("UTC").isoformat()


@pytest.fixture(scope="module")
def long_state(tmp_path_factory, mixed_two_years_template):
    """test_mixed's bars fetched at ``TWO_YEARS``: this module's copy of conftest's
    ``mixed_two_years_template`` (decision 2026-10-15-m14 114)."""
    assert (MIXED_TWO_YEARS, TRACK) == (TWO_YEARS, "test_mixed")
    return copy_template(mixed_two_years_template, tmp_path_factory.mktemp("long") / "state")


@pytest.fixture(scope="module")
def short_state(tmp_path_factory, config):
    state = tmp_path_factory.mktemp("short") / "state"
    assert fetch(state, config, ONE_YEAR) == 0
    return state


@pytest.fixture(scope="module")
def stored(long_state):
    store = BarStore(long_state, TRACK, HOUR)
    return store.read_range("SYNA", START, datetime(2021, 1, 7, tzinfo=UTC))


@pytest.fixture(scope="module")
def underlying(source, stored):
    under = source.fetch(with_params(inst("SYNA"), roll_schedule="none"), START,
                         datetime(2021, 1, 7, tzinfo=UTC))
    assert np.array_equal(under["ts"].to_numpy(), stored["ts"].to_numpy())
    return under


def roll_lines(state):
    path = roll_path(state, TRACK, "SYNA")
    return path.read_bytes() if path.exists() else b""


# --- detection -----------------------------------------------------------------------


def test_a_roll_is_a_bar_whose_contract_differs_from_the_previous_bar():
    assert detect_rolls(["A", "A", "B", "B", "B", "C"]) == [2, 5]
    assert detect_rolls(["A"]) == []
    assert detect_rolls([]) == []


def test_the_scheduled_rolls_are_recorded_with_ts_and_contracts(long_state, stored):
    rolls = read_rolls(roll_path(long_state, TRACK, "SYNA"))
    contract = stored["contract"].to_numpy()
    want = [(stored["ts"].iloc[u], contract[u - 1], contract[u])
            for u in range(1, len(contract)) if contract[u] != contract[u - 1]]
    assert len(want) == 8
    assert [(r.ts, r.old, r.new) for r in rolls] == want


def test_an_instrument_that_does_not_roll_has_no_roll_file(long_state):
    for symbol in ("SYNL", "SYNX"):
        assert not roll_path(long_state, TRACK, symbol).exists()


# --- the gate of U4 ----------------------------------------------------------------


def test_every_recorded_gap_is_the_difference_of_the_contract_constants(long_state, source):
    rec = inst("SYNA")
    rolls = read_rolls(roll_path(long_state, TRACK, "SYNA"))
    assert len(rolls) == 8
    for r in rolls:
        want = source.contract_constant(rec, r.new) - source.contract_constant(rec, r.old)
        assert abs(r.gap - want) <= 1e-9, r
        assert r.estimated is False
        # v is a bar before u, within 24 bars of the continuous series.
        assert r.measured_at is not None and r.measured_at < r.ts


def test_the_adjusted_series_is_the_underlying_plus_the_constant_current_at_t(
        long_state, source, stored, underlying):
    rec = inst("SYNA")
    rolls = read_rolls(roll_path(long_state, TRACK, "SYNA"))
    n = len(stored)
    contract = stored["contract"].to_numpy()
    roll_at = [int(stored["ts"].searchsorted(r.ts)) for r in rolls]
    picks = set(np.linspace(0, n - 1, 200).astype(int).tolist())
    picks |= {k for u in roll_at for k in (u - 1, u, u + 1)}
    assert len(picks) >= 200
    span = stored["ts"].iloc[max(picks)] - stored["ts"].iloc[min(picks)]
    assert span >= pd.Timedelta(days=700)
    for k in sorted(picks):
        t = stored["ts"].iloc[k]
        adj = adjust(stored, rolls, t)
        assert len(adj) == k + 1 and adj["ts"].iloc[-1] == t
        const = source.contract_constant(rec, contract[k])
        for col in PRICES:
            want = underlying[col].to_numpy()[: k + 1] + const
            assert np.abs(adj[col].to_numpy() - want).max() <= 1e-9, (k, col)
            assert adj[col].iloc[-1] == stored[col].iloc[k]          # the last bar is raw
        assert np.array_equal(adj["volume"].to_numpy(), stored["volume"].to_numpy()[: k + 1])
        assert np.array_equal(adj["contract"].to_numpy(), contract[: k + 1])


def test_the_adjusted_series_read_from_the_state_equals_adjust(long_state, stored):
    rolls = read_rolls(roll_path(long_state, TRACK, "SYNA"))
    u = int(stored["ts"].searchsorted(rolls[3].ts))
    for k in (u - 1, u, len(stored) - 1):
        t = stored["ts"].iloc[k]
        got = adjusted_as_of(long_state, TRACK, HOUR, inst("SYNA"), t)
        pd.testing.assert_frame_equal(got, adjust(stored, rolls, t), check_exact=True)


def test_the_adjusted_series_as_of_t_does_not_depend_on_later_bars(long_state, short_state):
    short = BarStore(short_state, TRACK, HOUR)
    end = short.last_ts("SYNA")
    bars = short.read_range("SYNA", START, end + pd.Timedelta(hours=1))
    rolls = read_rolls(roll_path(short_state, TRACK, "SYNA"))
    assert len(rolls) == 4
    u = int(bars["ts"].searchsorted(rolls[-1].ts))
    for t in (bars["ts"].iloc[u - 1], bars["ts"].iloc[u], end):
        a = adjusted_as_of(short_state, TRACK, HOUR, inst("SYNA"), t)
        b = adjusted_as_of(long_state, TRACK, HOUR, inst("SYNA"), t)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
    # The roll file of the shorter store is the start of the longer one's.
    assert roll_lines(long_state).startswith(roll_lines(short_state))
    assert roll_lines(long_state) != roll_lines(short_state)


# --- incremental fetches and re-runs (I-5, I-6) -------------------------------------


def test_a_roll_at_the_first_bar_of_a_fetch_and_two_fetches_give_one_fetchs_file(
        tmp_path, config, source, capsys):
    syna = source.fetch(inst("SYNA"), START, datetime(2019, 4, 1, tzinfo=UTC))
    u = int(np.flatnonzero(syna["contract"].to_numpy() != syna["contract"].iloc[0])[0])
    roll_ts = syna["ts"].iloc[u]
    one, two = tmp_path / "one", tmp_path / "two"
    end = "2019-04-01T00:00:00+00:00"
    assert fetch(one, config, end) == 0
    # The first fetch of ``two`` ends just before the roll bar closes.
    assert fetch(two, config, iso(roll_ts + pd.Timedelta(minutes=59))) == 0
    assert BarStore(two, TRACK, HOUR).last_ts("SYNA") == syna["ts"].iloc[u - 1]
    assert roll_lines(two) == b""
    capsys.readouterr()
    assert fetch(two, config, end) == 0
    out = capsys.readouterr().out
    assert f"roll SYNA {iso(roll_ts)} SYNA-2019-03 -> SYNA-2019-06" in out
    assert roll_lines(two) == roll_lines(one) and roll_lines(one).count(b"\n") == 1


def test_a_second_fetch_with_no_new_bar_appends_no_roll(tmp_path, config, capsys):
    state = tmp_path / "state"
    as_of = "2019-07-01T00:00:00+00:00"
    assert fetch(state, config, as_of) == 0
    before = roll_lines(state)
    assert before.count(b"\n") == 2
    capsys.readouterr()
    assert fetch(state, config, as_of) == 0
    out = capsys.readouterr().out
    assert roll_lines(state) == before
    assert not [ln for ln in out.splitlines() if ln.startswith("roll ")]


def test_a_roll_file_append_keeps_earlier_lines_and_fsyncs_before_rename(
        tmp_path, config, monkeypatch):
    state = tmp_path / "state"
    assert fetch(state, config, "2019-04-01T00:00:00+00:00") == 0
    old = roll_lines(state)
    path = roll_path(state, TRACK, "SYNA")
    log = []
    real_fsync, real_replace = os.fsync, os.replace

    def fsync(fd):
        log.append(("fsync", os.readlink(f"/proc/self/fd/{fd}")))
        return real_fsync(fd)

    def replace_(src, dst):
        log.append(("replace", str(src)))
        return real_replace(src, dst)
    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "replace", replace_)
    assert fetch(state, config, "2019-07-01T00:00:00+00:00") == 0
    tmp = str(path.with_name(path.name + ".tmp"))
    i = log.index(("replace", tmp))
    assert log[i - 1] == ("fsync", tmp) and log[i + 1] == ("fsync", str(path.parent))
    new = roll_lines(state)
    assert new.startswith(old) and new.count(b"\n") == 2
    assert not list(path.parent.glob("*.tmp"))


# --- the estimated gap -----------------------------------------------------------------


class Hiding:
    """The synthetic source, but ``fetch_contract`` hides the bars of a contract
    whose ``ts`` is in ``hide[contract]``, and asks for a wider range than it is
    given, so that a measurement must itself keep to its 24 bars."""

    name = "hiding"

    def __init__(self, inner, hide):
        self.inner, self.hide = inner, hide

    def available_until(self, now):
        return self.inner.available_until(now)

    def fetch(self, instrument, start, end):
        return self.inner.fetch(instrument, start, end)

    def fetch_contract(self, instrument, contract, start, end):
        bars = self.inner.fetch_contract(instrument, contract, start - timedelta(days=10), end)
        hidden = self.hide.get(contract)
        if hidden is None:
            return bars
        if hidden == "all":
            return bars.iloc[0:0]
        return bars[~bars["ts"].isin(hidden)].reset_index(drop=True)


@pytest.fixture(scope="module")
def first_roll(source):
    syna = source.fetch(inst("SYNA"), START, datetime(2019, 4, 1, tzinfo=UTC))
    u = int(np.flatnonzero(syna["contract"].to_numpy() != syna["contract"].iloc[0])[0])
    return syna, u


def _store_through(state, source, syna):
    store = BarStore(state, TRACK, HOUR)
    store.append("SYNA", syna, datetime(2019, 4, 1, tzinfo=UTC))
    return store


def test_no_common_bar_gives_an_estimated_gap_and_a_notice(tmp_path, source, first_roll):
    syna, u = first_roll
    _store_through(tmp_path, source, syna)
    hiding = Hiding(source, {"SYNA-2019-06": "all"})
    rolls, notices = update_rolls(tmp_path, TRACK, HOUR, inst("SYNA"), hiding, date(2019, 3, 31))
    assert len(rolls) == 1
    r = rolls[0]
    assert r.estimated is True and r.measured_at is None
    assert r.gap == syna["open"].iloc[u] - syna["close"].iloc[u - 1]
    assert [(e.date, e.level, e.kind, e.subject) for e in notices] == [
        (date(2019, 3, 31), "notice", ROLL_GAP_ESTIMATED, "SYNA")]
    assert notices[0].detail["ts"] == iso(syna["ts"].iloc[u])
    assert notices[0].detail["old"] == "SYNA-2019-03"
    assert notices[0].detail["new"] == "SYNA-2019-06"
    assert read_rolls(roll_path(tmp_path, TRACK, "SYNA")) == list(rolls)
    line = json.loads(roll_lines(tmp_path).decode())
    assert line["estimated"] is True
    # A re-run neither appends nor repeats the notice.
    assert update_rolls(tmp_path, TRACK, HOUR, inst("SYNA"), hiding, date(2019, 3, 31)) == ((), ())


def test_a_common_bar_beyond_24_bars_is_not_used(tmp_path, source, first_roll):
    syna, u = first_roll
    _store_through(tmp_path, source, syna)
    within = list(syna["ts"].iloc[u - 24:u])
    hiding = Hiding(source, {"SYNA-2019-03": within})
    rolls, notices = update_rolls(tmp_path, TRACK, HOUR, inst("SYNA"), hiding, date(2019, 3, 31))
    assert rolls[0].estimated is True and len(notices) == 1


def test_the_24th_bar_before_the_roll_is_used(tmp_path, source, first_roll):
    syna, u = first_roll
    _store_through(tmp_path, source, syna)
    hiding = Hiding(source, {"SYNA-2019-03": list(syna["ts"].iloc[u - 23:u])})
    rolls, notices = update_rolls(tmp_path, TRACK, HOUR, inst("SYNA"), hiding, date(2019, 3, 31))
    rec = inst("SYNA")
    assert rolls[0].estimated is False and notices == ()
    assert rolls[0].measured_at == syna["ts"].iloc[u - 24]
    want = source.contract_constant(rec, "SYNA-2019-06") - source.contract_constant(
        rec, "SYNA-2019-03")
    assert abs(rolls[0].gap - want) <= 1e-9


def test_bars_fetch_prints_the_estimated_gap_notice(tmp_path, config, source, monkeypatch,
                                                    capsys):
    real = sources.source_for

    def source_for(adapter, calendars, bar_seconds):
        return Hiding(real(adapter, calendars, bar_seconds), {"SYNA-2019-03": "all"})
    monkeypatch.setattr(sources, "source_for", source_for)
    state = tmp_path / "state"
    assert fetch(state, config, "2019-04-01T00:00:00+00:00") == 0
    out = capsys.readouterr().out
    notices = [json.loads(ln[len("notice "):]) for ln in out.splitlines()
               if ln.startswith("notice ")]
    assert [(n["level"], n["kind"], n["subject"], n["date"]) for n in notices] == [
        ("notice", ROLL_GAP_ESTIMATED, "SYNA", "2019-03-31")]
    assert any(ln.startswith("roll SYNA ") and ln.endswith("(estimated)")
               for ln in out.splitlines())
    assert read_rolls(roll_path(state, TRACK, "SYNA"))[0].estimated is True


# --- an instrument with no index entry (decision 35) --------------------------------


def _unlisted_first_append(state, first_roll, revised=False):
    """SYNA's first append crashed before its index write: its directory holds
    month files (January to March, through its first roll) the index does not
    list. With ``revised`` the March file fails decision 5's test with
    ``r = 0`` (its rows are not in increasing ``ts`` order, which the writer
    never writes)."""
    syna, _ = first_roll
    store = BarStore(state, TRACK, HOUR)
    months = syna["ts"].dt.strftime("%Y-%m")
    for month in sorted(months.unique()):
        rows = syna[months == month].reset_index(drop=True)
        if revised and month == "2019-03":
            rows = rows.iloc[::-1].reset_index(drop=True)
        path = store.month_path("SYNA", month)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows.to_parquet(path, index=False)
    assert "SYNA" not in store.index()
    return store


@pytest.mark.parametrize("revised, case, other", [
    (False, "interrupted append", "revised"), (True, "revised data point", "interrupted")])
def test_update_rolls_and_adjusted_as_of_refuse_an_unlisted_file_with_no_entry(
        tmp_path, source, first_roll, revised, case, other):
    syna, u = first_roll
    _unlisted_first_append(tmp_path, first_roll, revised)
    month = "2019-03" if revised else "2019-01"
    for call in (lambda: update_rolls(tmp_path, TRACK, HOUR, inst("SYNA"), source,
                                      date(2019, 3, 31)),
                 lambda: adjusted_as_of(tmp_path, TRACK, HOUR, inst("SYNA"), syna["ts"].iloc[u]),
                 lambda: adjusted_as_of(tmp_path, TRACK, HOUR, inst("SYNA"), syna["ts"].iloc[u],
                                        start=syna["ts"].iloc[0])):
        with pytest.raises(BarStoreError, match=f"SYNA .*{month}.*{case}") as err:
            call()
        assert other not in str(err.value)
    assert not roll_path(tmp_path, TRACK, "SYNA").exists()


@pytest.mark.parametrize("make_dir", [False, True])
def test_with_no_month_file_update_rolls_and_adjusted_as_of_report_no_stored_bar(
        tmp_path, source, make_dir):
    store = BarStore(tmp_path, TRACK, HOUR)
    if make_dir:
        store.month_path("SYNA", "x").parent.mkdir(parents=True)
    assert update_rolls(tmp_path, TRACK, HOUR, inst("SYNA"), source, date(2019, 3, 31)) == (
        (), ())
    with pytest.raises(BarStoreError, match="SYNA: no stored bar"):
        adjusted_as_of(tmp_path, TRACK, HOUR, inst("SYNA"), START)


def test_rolls_after_bars_fetch_completes_an_interrupted_first_append(
        tmp_path, config, source, monkeypatch, capsys):
    as_of = "2019-04-01T00:00:00+00:00"
    state, clean = tmp_path / "state", tmp_path / "clean"
    # The first fetch crashes before any index write: SYNA's month files are
    # renamed into place, unlisted, and pass decision 5's test with r = 0.
    with monkeypatch.context() as m:
        def crash(self, index):
            raise OSError("simulated crash before the index write")
        m.setattr(BarStore, "_write_index", crash)
        assert fetch(state, config, as_of) == 1
    store = BarStore(state, TRACK, HOUR)
    assert list(store.month_path("SYNA", "x").parent.glob("*.parquet"))
    assert not store.index_path.exists()
    t = pd.Timestamp(read_parquet_last(store))
    for call in (lambda: update_rolls(state, TRACK, HOUR, inst("SYNA"), source,
                                      date(2019, 3, 31)),
                 lambda: adjusted_as_of(state, TRACK, HOUR, inst("SYNA"), t)):
        with pytest.raises(BarStoreError, match="SYNA .*interrupted append") as err:
            call()
        assert "revised" not in str(err.value)
    assert roll_lines(state) == b""

    capsys.readouterr()
    assert fetch(state, config, as_of) == 0
    assert "store_recovered" in capsys.readouterr().out
    assert fetch(clean, config, as_of) == 0
    assert roll_lines(state) == roll_lines(clean) != b""
    for s in (state, clean):
        assert update_rolls(s, TRACK, HOUR, inst("SYNA"), source, date(2019, 3, 31)) == ((), ())
    pd.testing.assert_frame_equal(adjusted_as_of(state, TRACK, HOUR, inst("SYNA"), t),
                                  adjusted_as_of(clean, TRACK, HOUR, inst("SYNA"), t))
    assert roll_lines(state) == roll_lines(clean)


def read_parquet_last(store):
    files = sorted(store.month_path("SYNA", "x").parent.glob("*.parquet"))
    return pd.read_parquet(files[-1])["ts"].iloc[-1]


# --- no bar before trusted_from (decision 2026-10-12 36) ------------------------------
#
# Each test writes SYNA's synthetic bars from its fixture trusted_from (2019-01-07)
# through the store's writer, then uses a test-local copy of the record whose
# trusted_from is later than the first stored bar. The first roll is at
# 2019-03-14 00:00 UTC, the 24 stored bars before it reach back to 2019-03-12
# 23:00 (21:00 is the daily break), and the June roll is at 2019-06-14 00:00.

ROLL_1 = pd.Timestamp("2019-03-14 00:00", tz="UTC")


def trusted_at(day):
    return replace(inst("SYNA"), trusted_from=day), pd.Timestamp(day, tz="UTC")


class Asking:
    """A source holding the fixture record's data, from before the test-local
    ``trusted_from`` too (as a vendor does; the synthetic source would start its
    series at the record's ``trusted_from``), recording the ``start`` of every
    ``fetch_contract``."""

    name = "asking"

    def __init__(self, inner):
        self.inner, self.starts, self.record = inner, [], inst("SYNA")

    def available_until(self, now):
        return self.inner.available_until(now)

    def fetch(self, instrument, start, end):
        return self.inner.fetch(self.record, start, end)

    def fetch_contract(self, instrument, contract, start, end):
        self.starts.append(pd.Timestamp(start))
        return self.inner.fetch_contract(self.record, contract, start, end)


def test_a_gap_is_measured_on_no_bar_before_trusted_from(tmp_path, source, first_roll):
    syna, u = first_roll
    assert syna["ts"].iloc[u] == ROLL_1 and syna["ts"].iloc[u - 24] < ROLL_1 - pd.Timedelta(days=1)
    _store_through(tmp_path, source, syna)
    rec, trusted = trusted_at(date(2019, 3, 13))
    assert syna["ts"].iloc[0] < trusted
    # The old contract's bars at or after trusted_from are hidden, so the only
    # common bars within 24 stored bars lie before it: none may be used.
    hide = list(syna["ts"][(syna["ts"] >= trusted) & (syna["ts"] < ROLL_1)])
    asking = Asking(Hiding(source, {"SYNA-2019-03": hide}))
    rolls, notices = update_rolls(tmp_path, TRACK, HOUR, rec, asking, date(2019, 3, 31))
    assert [(r.ts, r.old, r.new) for r in rolls] == [(ROLL_1, "SYNA-2019-03", "SYNA-2019-06")]
    assert rolls[0].estimated is True and rolls[0].measured_at is None and len(notices) == 1
    assert asking.starts and min(asking.starts) >= trusted
    # With them shown, v is the last common bar, at or after trusted_from.
    clean = tmp_path / "clean"
    _store_through(clean, source, syna)
    asking = Asking(source)
    rolls, _ = update_rolls(clean, TRACK, HOUR, rec, asking, date(2019, 3, 31))
    assert rolls[0].estimated is False and rolls[0].measured_at >= trusted
    assert min(asking.starts) >= trusted


@pytest.mark.parametrize("hide", [{}, {"SYNA-2019-06": "all"}])   # measured, estimated
def test_a_contract_change_across_trusted_from_is_not_a_roll(tmp_path, source, hide):
    syna = source.fetch(inst("SYNA"), START, datetime(2019, 7, 1, tzinfo=UTC))
    BarStore(tmp_path, TRACK, HOUR).append("SYNA", syna, datetime(2019, 7, 1, tzinfo=UTC))
    # trusted_from is the date of the March roll bar: the bar before it is untrusted.
    rec, trusted = trusted_at(date(2019, 3, 14))
    assert trusted == ROLL_1
    asking = Asking(Hiding(source, hide))
    rolls, notices = update_rolls(tmp_path, TRACK, HOUR, rec, asking, date(2019, 6, 30))
    assert [(r.ts, r.old, r.new) for r in rolls] == [
        (pd.Timestamp("2019-06-14 00:00", tz="UTC"), "SYNA-2019-06", "SYNA-2019-09")]
    assert all(r.ts >= trusted for r in read_rolls(roll_path(tmp_path, TRACK, "SYNA")))
    assert all(e.detail["ts"] != iso(ROLL_1) for e in notices)
    # Every bar stored before trusted_from gives no roll at all.
    other = tmp_path / "other"
    march = syna[syna["ts"] < pd.Timestamp("2019-04-01", tz="UTC")]
    BarStore(other, TRACK, HOUR).append("SYNA", march, datetime(2019, 4, 1, tzinfo=UTC))
    assert min(asking.starts) >= trusted
    assert update_rolls(other, TRACK, HOUR, rec, Asking(Hiding(source, hide)),
                        date(2019, 3, 31)) == ((), ())
    assert not roll_path(other, TRACK, "SYNA").exists()


def test_adjusted_as_of_reads_no_bar_before_trusted_from_for_any_start(
        tmp_path, source, first_roll):
    syna, u = first_roll
    _store_through(tmp_path, source, syna)
    rec, trusted = trusted_at(date(2019, 3, 13))
    assert update_rolls(tmp_path, TRACK, HOUR, rec, Asking(source), date(2019, 3, 31))[0]
    rolls = read_rolls(roll_path(tmp_path, TRACK, "SYNA"))
    trusted_bars = syna[syna["ts"] >= trusted].reset_index(drop=True)
    for k in (u - 1, u, len(syna) - 1):
        t = syna["ts"].iloc[k]
        for start in (None, syna["ts"].iloc[0], trusted - pd.Timedelta(hours=1), trusted,
                      trusted + pd.Timedelta(hours=5)):
            got = adjusted_as_of(tmp_path, TRACK, HOUR, rec, t, start=start)
            assert (got["ts"] >= trusted).all(), (k, start)
            lo = trusted if start is None or start <= trusted else start
            want = adjust(trusted_bars[trusted_bars["ts"] >= lo].reset_index(drop=True),
                          rolls, t)
            pd.testing.assert_frame_equal(got, want, check_exact=True)
    # A bar t before trusted_from has nothing trusted up to it.
    assert adjusted_as_of(tmp_path, TRACK, HOUR, rec, syna["ts"].iloc[10]).empty
