"""The synthetic market (DESIGN 17.1) and `bars fetch` (DESIGN 5.5).

Every instrument is a fixture record under ``tests/fixtures/config/``; its
generator settings and its contract keys come from its ``[source]`` table
(decision 2026-10-12 10). SYNA rolls quarterly; the others have no contracts.
Every statistical test writes its seed here, in the test. Every state
directory is a pytest ``tmp_path``.
"""

import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_instrument
from discotrade.sources import BarSource, NotBuiltError, source_for
from discotrade.sources.synth import SynthSource
from discotrade.state import content_hash
from discotrade.tradingcal import expected_bars

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
HOUR = 3600
#: The fixture instruments without contracts; SYNA rolls quarterly.
NULL = ("SYNB", "SYNC", "SYND", "SYNL", "SYNX")
START = datetime(2019, 1, 7, tzinfo=UTC)   # every fixture's trusted_from
TWO_YEARS = datetime(2021, 1, 7, tzinfo=UTC)


def inst(symbol):
    return load_instrument(FIXTURE_CONFIG / "instruments" / f"{symbol}.toml")


@pytest.fixture(scope="module")
def calendars():
    return {p.stem: load_calendar(p) for p in sorted((FIXTURE_CONFIG / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def source(calendars):
    return SynthSource(calendars, HOUR)


@pytest.fixture(scope="module")
def two_years(source):
    return {s: source.fetch(inst(s), START, TWO_YEARS) for s in NULL}


def with_params(record, **changes):
    params = tuple((k, changes.get(k, v)) for k, v in record.source.params)
    return replace(record, source=replace(record.source, params=params))


def with_seed(record, seed):
    return with_params(record, seed=seed)


# --- the interface -----------------------------------------------------------------


def test_synth_is_a_bar_source_available_until_now(source):
    assert isinstance(source, BarSource)
    assert source.name == "synth"
    now = datetime(2019, 3, 1, 12, 30, tzinfo=UTC)
    assert source.available_until(now) == now


def test_source_for_gives_synth_and_refuses_an_unknown_adapter(calendars):
    assert isinstance(source_for("synth", calendars, HOUR), SynthSource)
    with pytest.raises(NotBuiltError, match="carrier_pigeon"):
        source_for("carrier_pigeon", calendars, HOUR)


def test_fetch_contract_of_an_instrument_that_does_not_roll_is_its_series(source):
    """DESIGN 5.1: ``contract`` equals the symbol where an instrument does not roll."""
    end = START + timedelta(days=30)
    for symbol in NULL:
        pd.testing.assert_frame_equal(source.fetch_contract(inst(symbol), symbol, START, end),
                                      source.fetch(inst(symbol), START, end), check_exact=True)
        with pytest.raises(ValueError, match="SYNA-2019-03"):
            source.fetch_contract(inst(symbol), "SYNA-2019-03", START, end)


# --- moving the generator settings into [source] changed no bar (decision 10) -------

#: Content hashes (DESIGN 9.2, key ``ts``, all seven columns) of the fetch of
#: each fixture instrument over [2019-01-07, 2019-07-08), computed at b86601c,
#: before this unit, when the settings were constants of synth.py. SYNA
#: could not be fetched with contracts then, so its line is SYNA with
#: ``roll_schedule = "none"``: the gap-free underlying series, contract = symbol.
BEFORE = {
    "SYNA": (2960, "affaf9e0002bf74c4b933c3467c02a8dc6287339014be4de4b204c9961a7cdb8"),
    "SYNB": (2964, "9c759c6387100a02177644e3a320b5cd4b03f7bdaf475264236224bdda3b008c"),
    "SYNC": (2964, "9b1d4aa7dac16d541195ba278b6d64544989c10d7ffd74d4004d103bf5b196c2"),
    "SYND": (2964, "51f5da8c3fc20125e3be34fad31f8c80d5889a739d35d9faa2f8e14bab1ebf1a"),
    "SYNL": (2959, "e203987ed2e0b305305c7ecb159716576920bce5655a16db904c799012b0bbc5"),
    "SYNX": (4361, "44a9b321fdefaff254936f1cd5dc9ee51ebe4643d70d257f84a36a8e76048d86"),
}
HASH_END = datetime(2019, 7, 8, tzinfo=UTC)


def test_fixed_fetches_are_identical_to_those_made_before_the_settings_moved(source):
    for symbol, (rows, digest) in BEFORE.items():
        rec = inst(symbol)
        if symbol == "SYNA":
            rec = with_params(rec, roll_schedule="none")
        bars = source.fetch(rec, START, HASH_END)
        assert (len(bars), content_hash(bars, ["ts"])) == (rows, digest), symbol


#: A value for each generator setting other than the fixtures' own.
OTHER_SETTINGS = {"gap_scale": 0.2, "range_scale": 0.7, "volume_median": 900.0,
                  "volume_sigma": 0.4, "hour_vol_amplitude": 0.3,
                  "hour_volume_amplitude": 0.2, "hour_peak_utc": 9}


@pytest.mark.parametrize("key", sorted(OTHER_SETTINGS))
def test_every_generator_setting_is_read_from_the_record(source, key):
    end = START + timedelta(days=14)
    a = source.fetch(inst("SYNB"), START, end)
    b = source.fetch(with_params(inst("SYNB"), **{key: OTHER_SETTINGS[key]}), START, end)
    assert len(a) == len(b)
    assert not a[["open", "high", "low", "close", "volume"]].equals(
        b[["open", "high", "low", "close", "volume"]])


# --- the bars ----------------------------------------------------------------------


def test_schema_and_contract_column(two_years, source):
    syna = source.fetch(inst("SYNA"), START, TWO_YEARS)
    assert syna["contract"].str.startswith("SYNA-").all()
    for symbol, bars in {**two_years, "SYNA": syna}.items():
        assert list(bars.columns) == ["ts", "open", "high", "low", "close", "volume",
                                      "contract"]
        assert str(bars["ts"].dtype) == "datetime64[ns, UTC]"
        if symbol != "SYNA":
            assert (bars["contract"] == symbol).all()
        assert bars["ts"].is_monotonic_increasing and not bars["ts"].duplicated().any()
        assert (bars["volume"] > 0).all()


def test_same_seed_same_bars_and_different_seed_different_bars(calendars):
    end = START + timedelta(days=60)
    for symbol in NULL:
        a = SynthSource(calendars, HOUR).fetch(inst(symbol), START, end)
        b = SynthSource(calendars, HOUR).fetch(inst(symbol), START, end)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        rec = inst(symbol)
        c = SynthSource(calendars, HOUR).fetch(with_seed(rec, rec.source.get("seed") + 1),
                                               START, end)
        assert not np.array_equal(a["close"].to_numpy()[:100], c["close"].to_numpy()[:100])


def test_bars_do_not_depend_on_the_requested_range(source):
    """A later or shorter request gives the same bars where the ranges overlap,
    so incremental fetches continue one series."""
    for symbol in NULL:
        whole = source.fetch(inst(symbol), START, START + timedelta(days=90))
        mid = START + timedelta(days=30, hours=5)
        part = source.fetch(inst(symbol), mid, START + timedelta(days=60))
        want = whole[(whole["ts"] >= mid) & (whole["ts"] < START + timedelta(days=60))]
        pd.testing.assert_frame_equal(part.reset_index(drop=True),
                                      want.reset_index(drop=True), check_exact=True)


def test_highs_and_lows_enclose_open_and_close(two_years):
    for bars in two_years.values():
        hi, lo = bars["high"], bars["low"]
        assert (hi >= bars["open"]).all() and (hi >= bars["close"]).all()
        assert (lo <= bars["open"]).all() and (lo <= bars["close"]).all()
        assert (lo > 0).all()


def test_bars_exist_only_at_expected_times(two_years, source, calendars):
    for symbol, bars in two_years.items():
        rec = inst(symbol)
        expected = expected_bars(calendars[rec.calendar], START, TWO_YEARS, HOUR)
        got = [t.to_pydatetime() for t in bars["ts"]]
        assert set(got) <= set(expected)
        dropped = source.dropped(rec, START, TWO_YEARS)
        assert sorted(set(expected) - set(got)) == dropped
        if rec.source.get("drop_fraction") > 0:
            assert dropped
        else:
            assert dropped == []


def test_dropped_fraction_matches_the_record(two_years, source):
    for symbol in NULL:
        rec = inst(symbol)
        frac = rec.source.get("drop_fraction")
        k = len(source.dropped(rec, START, TWO_YEARS))
        n = len(two_years[symbol]) + k
        assert abs(k - frac * n) <= 4 * np.sqrt(n * frac * (1 - frac))


def test_two_years_of_hourly_returns_have_no_mean_and_no_lag1_autocorrelation(two_years):
    for symbol, bars in two_years.items():
        close = bars["close"].to_numpy()
        for r in (np.diff(np.log(close)), close[1:] / close[:-1] - 1.0):
            n = len(r)
            assert n > 10_000
            se_mean = r.std(ddof=1) / np.sqrt(n)
            assert abs(r.mean()) <= 4 * se_mean, symbol
            d = r - r.mean()
            rho = float(np.dot(d[1:], d[:-1]) / np.dot(d, d))
            assert abs(rho) <= 4 / np.sqrt(n), symbol


def test_hourly_volatility_follows_the_record(two_years):
    for symbol, bars in two_years.items():
        r = np.diff(np.log(bars["close"].to_numpy()))
        vol = inst(symbol).source.get("hourly_vol")
        assert 0.8 * vol < r.std() < 1.4 * vol, symbol


# --- contracts (DESIGN 17.1, 5.1, 5.5) -----------------------------------------------


@pytest.fixture(scope="module")
def syna(source):
    return source.fetch(inst("SYNA"), START, TWO_YEARS)


def _changes(bars):
    contract = bars["contract"].to_numpy()
    return [i for i in range(1, len(contract)) if contract[i] != contract[i - 1]]


def test_the_contract_column_changes_exactly_at_the_scheduled_rolls(syna):
    """The schedule, from the record: on ``roll_day`` of March, June, September
    and December at 00:00 UTC the next quarterly contract becomes current, at
    the first bar at or after that instant."""
    day = inst("SYNA").source.get("roll_day")
    instants = [datetime(y, m, day, tzinfo=UTC) for y in (2019, 2020) for m in (3, 6, 9, 12)]
    assert all(START < t < TWO_YEARS for t in instants)
    changes = _changes(syna)
    assert changes == [int(syna["ts"].searchsorted(pd.Timestamp(t))) for t in instants]
    contract = syna["contract"].to_numpy()
    assert [contract[0], *(contract[i] for i in changes)] == [
        f"SYNA-{t.year}-{t.month:02d}" for t in instants] + ["SYNA-2021-03"]


def test_adjacent_contracts_differ_by_the_difference_of_their_constants(source, syna):
    rec = inst("SYNA")
    contract, tick = syna["contract"].to_numpy(), rec.tick_size
    for i in _changes(syna):
        old, new, u = contract[i - 1], contract[i], syna["ts"].iloc[i]
        a = source.fetch_contract(rec, old, START, TWO_YEARS)
        b = source.fetch_contract(rec, new, START, TWO_YEARS)
        assert (a["contract"] == old).all() and (b["contract"] == new).all()
        common = a.merge(b, on="ts", suffixes=("_old", "_new"))
        # The contracts overlap around the roll by at least 24 bars each way (5.6).
        assert (common["ts"] < u).sum() >= 24 and (common["ts"] >= u).sum() >= 24
        c_old, c_new = source.contract_constant(rec, old), source.contract_constant(rec, new)
        assert c_old / tick == round(c_old / tick) and c_new / tick == round(c_new / tick)
        assert c_new != c_old
        for col in ("open", "high", "low", "close"):
            diff = (common[f"{col}_new"] - common[f"{col}_old"]).to_numpy()
            assert np.abs(diff - (c_new - c_old)).max() <= 1e-9, (old, new, col)
        assert np.array_equal(common["volume_new"], common["volume_old"])


def test_the_continuous_series_is_the_underlying_plus_the_current_contracts_constant(
        source, syna):
    rec = inst("SYNA")
    under = source.fetch(with_params(rec, roll_schedule="none"), START, TWO_YEARS)
    assert np.array_equal(under["ts"].to_numpy(), syna["ts"].to_numpy())
    const = np.array([source.contract_constant(rec, c) for c in syna["contract"]])
    for col in ("open", "high", "low", "close"):
        assert np.array_equal(syna[col].to_numpy(), under[col].to_numpy() + const), col
    assert np.array_equal(syna["volume"].to_numpy(), under["volume"].to_numpy())
    # Each contract's own bars are the underlying plus that contract's constant.
    by_ts = under.set_index("ts")
    for name in dict.fromkeys(syna["contract"]):
        bars = source.fetch_contract(rec, name, START, TWO_YEARS)
        base = by_ts.loc[bars["ts"]]
        for col in ("open", "high", "low", "close"):
            assert np.array_equal(bars[col].to_numpy(),
                                  base[col].to_numpy() + source.contract_constant(rec, name))


def test_contract_bars_do_not_depend_on_the_requested_range(source):
    rec = inst("SYNA")
    end = START + timedelta(days=200)
    mid = datetime(2019, 3, 10, 7, tzinfo=UTC)
    for fetch in (lambda a, b: source.fetch(rec, a, b),
                  lambda a, b: source.fetch_contract(rec, "SYNA-2019-06", a, b)):
        whole, part = fetch(START, end), fetch(mid, datetime(2019, 3, 20, tzinfo=UTC))
        want = whole[(whole["ts"] >= mid) & (whole["ts"] < datetime(2019, 3, 20, tzinfo=UTC))]
        assert len(part) > 0
        pd.testing.assert_frame_equal(part.reset_index(drop=True),
                                      want.reset_index(drop=True), check_exact=True)


def test_a_range_before_trusted_from_gives_no_bars(source):
    a, b = datetime(2019, 1, 1, tzinfo=UTC), datetime(2019, 1, 2, tzinfo=UTC)
    for symbol in ("SYNA", *NULL):
        bars = source.fetch(inst(symbol), a, b)
        assert len(bars) == 0
        assert list(bars.columns) == ["ts", "open", "high", "low", "close", "volume",
                                      "contract"]
    assert len(source.fetch_contract(inst("SYNA"), "SYNA-2019-03", a, b)) == 0


def test_an_unknown_contract_is_refused_by_name(source):
    rec = inst("SYNA")
    for name in ("SYNA-2019-04", "SYNA-2018-12", "SYNB-2019-03", "SYNA"):
        with pytest.raises(ValueError, match=name):
            source.fetch_contract(rec, name, START, TWO_YEARS)


# --- the hour-of-day patterns and the open gap (DESIGN 17.1) --------------------------

#: The seed of every statistical test below (DESIGN 18.2: seeds live in the test).
PATTERN_SEED = 20261012


@pytest.fixture(scope="module")
def pattern_bars(source):
    """Two synthetic years of SYNB with its own settings and a seed written here,
    without dropped bars, so consecutive rows are consecutive bars."""
    rec = with_params(inst("SYNB"), seed=PATTERN_SEED, drop_fraction=0.0)
    return rec, source.fetch(rec, START, TWO_YEARS)


def _peak_and_trough(rec, bars):
    peak = rec.source.get("hour_peak_utc")
    trough = (peak + 12) % 24
    hours = bars["ts"].dt.hour.to_numpy()
    return hours == peak, hours == trough


def test_the_hour_of_day_volatility_pattern_is_visible(pattern_bars):
    """The ratio of the deviation of hourly returns at the peak hour to that at
    the trough hour is within four standard errors of the configured shape's
    ratio, (1 + a) / (1 - a) for amplitude a."""
    rec, bars = pattern_bars
    a = rec.source.get("hour_vol_amplitude")
    want = (1 + a) / (1 - a)
    r = np.log(bars["close"].to_numpy() / bars["open"].to_numpy())
    peak, trough = _peak_and_trough(rec, bars)
    n1, n2 = int(peak.sum()), int(trough.sum())
    assert min(n1, n2) > 400
    ratio = r[peak].std(ddof=1) / r[trough].std(ddof=1)
    se = ratio * np.sqrt(1 / (2 * (n1 - 1)) + 1 / (2 * (n2 - 1)))
    assert abs(ratio - want) <= 4 * se, (ratio, want, se)
    assert ratio > 1 + 8 * se          # the pattern is there, not merely allowed


def test_the_hour_of_day_volume_pattern_is_visible(pattern_bars):
    """Mean log volume at the peak hour less that at the trough hour is within
    four standard errors of the configured shape's 2 * amplitude."""
    rec, bars = pattern_bars
    want = 2 * rec.source.get("hour_volume_amplitude")
    v = np.log(bars["volume"].to_numpy())
    peak, trough = _peak_and_trough(rec, bars)
    diff = v[peak].mean() - v[trough].mean()
    se = np.sqrt(v[peak].var(ddof=1) / peak.sum() + v[trough].var(ddof=1) / trough.sum())
    assert abs(diff - want) <= 4 * se, (diff, want, se)
    assert diff > 8 * se
    assert abs(np.median(v) - np.log(rec.source.get("volume_median"))) < 0.1


def test_the_open_gap_is_uncorrelated_with_the_same_bars_return(pattern_bars):
    rec, bars = pattern_bars
    o, c = np.log(bars["open"].to_numpy()), np.log(bars["close"].to_numpy())
    gap, ret = o[1:] - c[:-1], c[1:] - o[1:]
    n = len(gap)
    assert n > 10_000 and gap.std() > 0
    rho = float(np.corrcoef(gap, ret)[0, 1])
    assert abs(rho) <= 4 / np.sqrt(n), rho


def test_the_instrument_that_cannot_be_shorted_is_generated_like_any_other(two_years):
    assert inst("SYNL").shorting is False
    assert len(two_years["SYNL"]) > 10_000


# --- discotrade bars fetch ---------------------------------------------------------

AS_OF = "2019-04-01T10:30:00+00:00"
UNTIL = datetime(2019, 4, 1, 10, 30, tzinfo=UTC)
NULL_TRACK = ("SYNB", "SYNL", "SYNX")


def _cli_config(tmp_path):
    """The fixture config plus the repository's thresholds and a track without
    contracts (the fixture tracks both hold SYNA, which rolls)."""
    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    track = (FIXTURE_CONFIG / "tracks" / "test_mixed.toml").read_text(encoding="utf-8")
    track = track.replace('name = "test_mixed"', 'name = "test_null"').replace(
        'instruments = ["SYNA", "SYNL", "SYNX"]',
        "instruments = [" + ", ".join(f'"{s}"' for s in NULL_TRACK) + "]")
    (config / "tracks" / "test_null.toml").write_text(track, encoding="utf-8")
    return config


def _argv(state, config, *rest, as_of=AS_OF, track="test_null"):
    return ["--state", str(state), "--config", str(config), "--track", track,
            "--as-of", as_of, *rest]


def test_bars_fetch_then_gaps_reports_exactly_the_dropped_bars(tmp_path, source, capsys):
    state, config = tmp_path / "state", _cli_config(tmp_path)
    assert main(_argv(state, config, "bars", "fetch")) == 0
    capsys.readouterr()
    store = BarStore(state, "test_null", HOUR)
    want = []
    for symbol in NULL_TRACK:
        rec = inst(symbol)
        bars = store.read_range(symbol, START, UNTIL)
        assert (bars["ts"] + pd.Timedelta(seconds=HOUR) <= UNTIL).all()   # only closed bars
        pd.testing.assert_frame_equal(
            bars.reset_index(drop=True),
            source.fetch(rec, START, UNTIL - timedelta(minutes=30)).reset_index(drop=True),
            check_exact=True)
        want += [f"missing {symbol} {t.isoformat()}"
                 for t in source.dropped(rec, START, UNTIL - timedelta(minutes=30))]
    assert len(want) >= 3

    assert main(_argv(state, config, "bars", "gaps")) == 0
    out = capsys.readouterr().out
    assert [ln for ln in out.splitlines() if ln.startswith("missing ")] == want
    lines = (state / "bars" / "test_null" / "gaps.jsonl").read_text().splitlines()
    assert [f"missing {r['symbol']} {r['ts']}" for r in map(json.loads, lines)] == want


def test_bars_fetch_runs_the_gap_check_and_says_what_it_wrote(tmp_path, capsys):
    state, config = tmp_path / "state", _cli_config(tmp_path)
    assert main(_argv(state, config, "bars", "fetch")) == 0
    out = capsys.readouterr().out
    for symbol in NULL_TRACK:
        assert any(ln.startswith(f"fetched {symbol}: ") for ln in out.splitlines())
    assert "missing SYNL " in out
    assert (state / "bars" / "test_null" / "gaps.jsonl").exists()
    # DESIGN 16.1's D at --as-of Monday 2019-04-01 10:30 UTC is Friday 03-29
    # (decision 2026-10-12 19), no longer the UTC date minus one, Sunday 03-31.
    assert "day 2019-03-29" in out


def test_bars_fetch_is_incremental_and_rerunning_writes_nothing(tmp_path, capsys):
    one, two, config = tmp_path / "one", tmp_path / "two", _cli_config(tmp_path)
    assert main(_argv(one, config, "bars", "fetch")) == 0
    assert main(_argv(two, config, "bars", "fetch", as_of="2019-02-15T00:00:00+00:00")) == 0
    assert main(_argv(two, config, "bars", "fetch")) == 0
    index = (two / "bars" / "test_null" / "index.json").read_text()
    assert main(_argv(two, config, "bars", "fetch")) == 0
    assert (two / "bars" / "test_null" / "index.json").read_text() == index
    capsys.readouterr()
    for symbol in NULL_TRACK:
        a = BarStore(one, "test_null", HOUR).read_range(symbol, START, UNTIL)
        b = BarStore(two, "test_null", HOUR).read_range(symbol, START, UNTIL)
        pd.testing.assert_frame_equal(a, b, check_exact=True)


def test_bars_fetch_on_test_mixed_writes_syna_bars_with_their_contracts(tmp_path, source,
                                                                        capsys):
    state, config = tmp_path / "state", _cli_config(tmp_path)
    assert main(_argv(state, config, "bars", "fetch", track="test_mixed")) == 0
    capsys.readouterr()
    stored = BarStore(state, "test_mixed", HOUR).read_range("SYNA", START, UNTIL)
    want = source.fetch(inst("SYNA"), START, UNTIL - timedelta(minutes=30))
    pd.testing.assert_frame_equal(stored.reset_index(drop=True), want.reset_index(drop=True),
                                  check_exact=True)
    assert list(dict.fromkeys(stored["contract"])) == ["SYNA-2019-03", "SYNA-2019-06"]


def test_bars_fetch_needs_a_state_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    config = _cli_config(tmp_path)
    assert main(["--config", str(config), "--track", "test_null", "--as-of", AS_OF,
                 "bars", "fetch"]) == 1
    assert "state directory" in capsys.readouterr().err



# --- bars fetch: an interrupted append and bars that are not finite (decisions 5, 6) --


class Crash(OSError):
    """A simulated crash."""


def _parquet_bytes(state):
    root = state / "bars" / "test_null"
    return {p.relative_to(root): p.read_bytes() for p in sorted(root.rglob("*.parquet"))}


def test_bars_fetch_completes_an_interrupted_append_of_several_months(tmp_path, monkeypatch,
                                                                      capsys):
    clean, state, config = tmp_path / "clean", tmp_path / "state", _cli_config(tmp_path)
    assert main(_argv(clean, config, "bars", "fetch")) == 0
    early = "2019-02-15T00:00:00+00:00"
    assert main(_argv(state, config, "bars", "fetch", as_of=early)) == 0
    index_before = (state / "bars" / "test_null" / "index.json").read_text()
    # The next fetch (February to April for each instrument) crashes after
    # the first instrument's month files are renamed, before its index write.
    with monkeypatch.context() as m:
        def crash(self, index):
            raise Crash("simulated crash before the index write")
        m.setattr(BarStore, "_write_index", crash)
        assert main(_argv(state, config, "bars", "fetch")) == 1
    assert (state / "bars" / "test_null" / "index.json").read_text() == index_before
    crashed = {k: v for k, v in _parquet_bytes(state).items() if k.parts[0] == "SYNB"}
    capsys.readouterr()
    # The reader refuses the file as an interrupted append, not a revised point.
    assert main(_argv(state, config, "bars", "gaps", "--day", "2019-02-14")) == 1
    err = capsys.readouterr().err
    assert "interrupted append" in err and "revised" not in err

    assert main(_argv(state, config, "bars", "fetch")) == 0
    out = capsys.readouterr().out
    notices = [json.loads(ln.split(" ", 1)[1]) for ln in out.splitlines()
               if ln.startswith("notice ")]
    assert [(n["level"], n["kind"], n["subject"], n["detail"]["file"]) for n in notices] == [
        ("notice", "store_recovered", "SYNB", f"SYNB/{month}.parquet")
        for month in ("2019-02", "2019-03", "2019-04")]
    assert all(n["date"] == "2019-03-31" for n in notices)
    after = _parquet_bytes(state)
    # The recovered files are byte-identical: no row changed.
    assert {k: after[k] for k in crashed} == crashed
    assert (state / "bars" / "test_null" / "index.json").read_text() == (
        clean / "bars" / "test_null" / "index.json").read_text()
    for symbol in NULL_TRACK:
        pd.testing.assert_frame_equal(
            BarStore(state, "test_null", HOUR).read_range(symbol, START, UNTIL),
            BarStore(clean, "test_null", HOUR).read_range(symbol, START, UNTIL),
            check_exact=True)


def test_bars_fetch_refuses_a_revised_file_and_writes_nothing(tmp_path, capsys):
    state, config = tmp_path / "state", _cli_config(tmp_path)
    assert main(_argv(state, config, "bars", "fetch", as_of="2019-02-15T00:00:00+00:00")) == 0
    path = state / "bars" / "test_null" / "SYNL" / "2019-01.parquet"
    revised = pd.read_parquet(path)
    revised.loc[3, "close"] = revised.loc[3, "close"] + 1.0
    revised.to_parquet(path, index=False)
    before = _parquet_bytes(state)
    index = (state / "bars" / "test_null" / "index.json").read_text()
    capsys.readouterr()
    assert main(_argv(state, config, "bars", "fetch")) == 1
    assert "revised data point" in capsys.readouterr().err
    assert _parquet_bytes(state) == before
    assert (state / "bars" / "test_null" / "index.json").read_text() == index


def test_bars_fetch_drops_bars_that_are_not_finite_and_the_gap_check_lists_them(
        tmp_path, monkeypatch, capsys):
    state, config = tmp_path / "state", _cli_config(tmp_path)
    real = SynthSource.fetch
    poisoned = {}

    def fetch(self, instrument, start, end):
        bars = real(self, instrument, start, end)
        if instrument.symbol == "SYNB":
            bars = bars.copy()
            for row, column, value in ((100, "close", np.nan), (101, "open", np.inf),
                                       (500, "volume", -np.inf)):
                bars.loc[row, column] = value
                poisoned[bars.loc[row, "ts"].to_pydatetime()] = column
        return bars
    monkeypatch.setattr(SynthSource, "fetch", fetch)
    assert main(_argv(state, config, "bars", "fetch")) == 0
    out = capsys.readouterr().out.splitlines()
    fetched = {ln.split(":")[0]: ln for ln in out if ln.startswith("fetched ")}
    assert "3 dropped as not finite" in fetched["fetched SYNB"]
    assert "0 dropped as not finite" in fetched["fetched SYNL"]
    stored = BarStore(state, "test_null", HOUR).read_range("SYNB", START, UNTIL)
    assert not set(stored["ts"].dt.to_pydatetime()) & set(poisoned)
    assert np.isfinite(stored[["open", "high", "low", "close", "volume"]].to_numpy()).all()
    missing = {ln.split(" ", 2)[2] for ln in out if ln.startswith("missing SYNB ")}
    assert {t.isoformat() for t in poisoned} <= missing
