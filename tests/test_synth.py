"""The null synthetic market (DESIGN 17.1 without contracts) and `bars fetch` (DESIGN 5.5).

Every instrument is a fixture record under ``tests/fixtures/config/``; its
generator parameters come from its ``[source]`` table. Contracts (a
``roll_schedule`` other than ``"none"``) and ``fetch_contract`` are step S0.2
and must raise ``NotBuiltError``. Every state directory is a pytest
``tmp_path``.
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
from discotrade.tradingcal import expected_bars

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
HOUR = 3600
#: The fixture instruments without contracts; SYNA rolls quarterly (S0.2).
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


def with_seed(record, seed):
    params = tuple((k, seed if k == "seed" else v) for k, v in record.source.params)
    return replace(record, source=replace(record.source, params=params))


# --- the interface -----------------------------------------------------------------


def test_synth_is_a_bar_source_available_until_now(source):
    assert isinstance(source, BarSource)
    assert source.name == "synth"
    now = datetime(2019, 3, 1, 12, 30, tzinfo=UTC)
    assert source.available_until(now) == now


def test_source_for_gives_synth_and_refuses_unbuilt_adapters(calendars):
    assert isinstance(source_for("synth", calendars, HOUR), SynthSource)
    for adapter in ("vendor", "crypto"):
        with pytest.raises(NotBuiltError, match=adapter):
            source_for(adapter, calendars, HOUR)


def test_contracts_are_not_built(source):
    with pytest.raises(NotBuiltError, match="S0.2"):
        source.fetch_contract(inst("SYNB"), "SYNB", START, START + timedelta(days=7))
    with pytest.raises(NotBuiltError, match="roll_schedule"):
        source.fetch(inst("SYNA"), START, START + timedelta(days=7))


# --- the bars ----------------------------------------------------------------------


def test_schema_and_contract_column(two_years):
    for symbol, bars in two_years.items():
        assert list(bars.columns) == ["ts", "open", "high", "low", "close", "volume",
                                      "contract"]
        assert str(bars["ts"].dtype) == "datetime64[ns, UTC]"
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
    assert "day 2019-03-31" in out


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


def test_bars_fetch_refuses_a_track_with_contracts_and_writes_nothing(tmp_path, capsys):
    state, config = tmp_path / "state", _cli_config(tmp_path)
    assert main(_argv(state, config, "bars", "fetch", track="test_mixed")) == 1
    assert "not built" in capsys.readouterr().err
    assert not (state / "bars").exists()


def test_bars_fetch_needs_a_state_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)
    config = _cli_config(tmp_path)
    assert main(["--config", str(config), "--track", "test_null", "--as-of", AS_OF,
                 "bars", "fetch"]) == 1
    assert "state directory" in capsys.readouterr().err

