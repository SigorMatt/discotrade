"""The vendor adapter (DESIGN 5.5, 5.1; decision 2026-10-12 11; I-9, I-11, I-13).

Driven by the fake client of ``tests/fakes/vendor_client.py``, whose market is the
synthetic SYNA (it rolls quarterly). The real client is never installed or
imported: the fake stands in for its package in ``sys.modules``. No network, no
real key, no wall clock; every state directory is a pytest temporary directory.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from fakes.vendor_world import (
    CONTINUOUS,
    DATASET,
    FAKE_KEY,
    HOUR,
    SYMBOL,
    TRACK,
    install,
    make_config,
    make_vendor,
    vendor_instrument,
)

from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.rolls import read_rolls, roll_path
from discotrade.sources import SourceError, source_for
from discotrade.sources.base import BAR_COLUMNS
from discotrade.sources.vendor import CLIENT_PACKAGE, KEY_ENV, VendorSource

START = datetime(2019, 3, 1, tzinfo=UTC)
END = datetime(2019, 3, 20, tzinfo=UTC)     # spans SYNA's roll of 2019-03-14


@pytest.fixture
def config(tmp_path):
    return make_config(tmp_path / "config")


@pytest.fixture
def vendor(monkeypatch):
    vendor = make_vendor()
    install(monkeypatch, vendor)
    return vendor


def fetch_cli(state, config, as_of):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "bars", "fetch"])


# --- import and selection -------------------------------------------------------------


def test_importing_the_adapter_does_not_import_the_client_package(tmp_path):
    # A stand-in package that leaves a mark when it is imported.
    package = tmp_path / "pkgs" / CLIENT_PACKAGE
    package.mkdir(parents=True)
    mark = tmp_path / "imported"
    (package / "__init__.py").write_text(f"open({str(mark)!r}, 'w').close()\n")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(tmp_path / "pkgs"), str(REPO_ROOT / "src")])}
    code = ("import sys, discotrade.sources, discotrade.sources.vendor\n"
            f"print({CLIENT_PACKAGE!r} in sys.modules)\n")
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
                            text=True, timeout=60, check=True)
    assert result.stdout.strip() == "False"
    assert not mark.exists()
    # The stand-in is importable, so the probe would have seen an import.
    code = f"import {CLIENT_PACKAGE}\n"
    subprocess.run([sys.executable, "-c", code], env=env, timeout=60, check=True)
    assert mark.exists()


def test_source_for_gives_the_vendor_adapter():
    source = source_for("vendor", {}, HOUR)
    assert isinstance(source, VendorSource) and source.name == "vendor"


def test_a_bar_length_without_a_vendor_schema_is_refused():
    with pytest.raises(ValueError, match="7200"):
        VendorSource(7200)


def test_available_until_is_now_minus_24_hours():
    now = datetime(2019, 3, 20, 12, 30, tzinfo=UTC)
    assert VendorSource(HOUR).available_until(now) == now - timedelta(hours=24)
    with pytest.raises(ValueError, match="timezone"):
        VendorSource(HOUR).available_until(datetime(2019, 3, 20))


# --- fetch ----------------------------------------------------------------------------------


def test_fetch_returns_bars_in_the_5_1_schema_with_contract_resolved(vendor, config):
    bars = VendorSource(HOUR).fetch(vendor_instrument(config), START, END)
    assert tuple(bars.columns) == BAR_COLUMNS
    assert str(bars["ts"].dtype) == "datetime64[ns, UTC]"
    for col in ("open", "high", "low", "close", "volume"):
        assert bars[col].dtype == "float64", col
    expected = vendor.synth.fetch(vendor.instrument, START, END)
    assert len(bars) == len(expected) > 200
    assert (bars["ts"].to_numpy() == expected["ts"].to_numpy()).all()
    for col in ("open", "high", "low", "close"):
        assert (bars[col].to_numpy() == expected[col].to_numpy()).all(), col
    # contract is the underlying contract, through the vendor's symbology.
    assert bars["contract"].tolist() == expected["contract"].tolist()
    assert set(bars["contract"]) == {"SYNA-2019-03", "SYNA-2019-06"}
    assert CONTINUOUS not in set(bars["contract"])


def test_the_cost_estimate_is_asked_first_for_exactly_the_request(vendor, config):
    VendorSource(HOUR).fetch(vendor_instrument(config), START, END)
    names = vendor.names()
    assert names[:3] == ["Historical", "get_cost", "get_range"]
    assert names.index("get_cost") < names.index("get_range")
    cost, rng = dict(vendor.calls)["get_cost"], dict(vendor.calls)["get_range"]
    assert cost == rng
    assert cost == {"dataset": DATASET, "symbols": [CONTINUOUS], "schema": "ohlcv-1h",
                    "stype_in": "continuous", "start": START.isoformat(),
                    "end": END.isoformat()}
    resolve = dict(vendor.calls)["resolve"]
    assert (resolve["stype_in"], resolve["stype_out"]) == ("instrument_id", "raw_symbol")
    assert vendor.keys == [FAKE_KEY]


def test_a_cost_above_the_default_limit_refuses_and_fetches_nothing(monkeypatch, config):
    vendor = make_vendor(cost=5.01)
    install(monkeypatch, vendor)
    with pytest.raises(SourceError, match=r"5\.01 USD.*above max_cost_usd 5"):
        VendorSource(HOUR).fetch(vendor_instrument(config), START, END)
    assert vendor.names() == ["Historical", "get_cost"]


def test_a_cost_at_the_default_limit_is_fetched(monkeypatch, config):
    vendor = make_vendor(cost=5.0)
    install(monkeypatch, vendor)
    assert len(VendorSource(HOUR).fetch(vendor_instrument(config), START, END)) > 0


def test_the_limit_is_the_records_max_cost_usd(monkeypatch, tmp_path):
    config = make_config(tmp_path / "config", extra="max_cost_usd = 0.1")
    vendor = make_vendor(cost=0.25)
    install(monkeypatch, vendor)
    with pytest.raises(SourceError, match="above max_cost_usd 0.1"):
        VendorSource(HOUR).fetch(vendor_instrument(config), START, END)
    assert "get_range" not in vendor.names()


def test_fetch_contract_returns_one_contracts_bars(vendor, config):
    bars = VendorSource(HOUR).fetch_contract(vendor_instrument(config), "SYNA-2019-06",
                                             START, END)
    expected = vendor.synth.fetch_contract(vendor.instrument, "SYNA-2019-06", START, END)
    assert tuple(bars.columns) == BAR_COLUMNS and len(bars) == len(expected) > 0
    assert (bars["close"].to_numpy() == expected["close"].to_numpy()).all()
    assert set(bars["contract"]) == {"SYNA-2019-06"}
    assert vendor.names()[:3] == ["Historical", "get_cost", "get_range"]
    assert dict(vendor.calls)["get_cost"]["stype_in"] == "raw_symbol"
    assert dict(vendor.calls)["get_cost"]["symbols"] == ["SYNA-2019-06"]


def test_an_empty_range_makes_no_call(vendor, config):
    bars = VendorSource(HOUR).fetch(vendor_instrument(config), END, END)
    assert tuple(bars.columns) == BAR_COLUMNS and bars.empty
    assert vendor.calls == []


def test_bars_without_a_needed_column_are_refused(vendor, config, monkeypatch):
    real = vendor.get_range

    def get_range(**kwargs):
        store = real(**kwargs)
        store._frame = store._frame.drop(columns=["instrument_id"])
        return store
    vendor.get_range = get_range
    install(monkeypatch, vendor)
    with pytest.raises(SourceError, match="instrument_id"):
        VendorSource(HOUR).fetch(vendor_instrument(config), START, END)


def test_a_bar_with_no_contract_in_the_symbology_is_refused(vendor, config, monkeypatch):
    def resolve(**kwargs):
        return {"result": {}}
    vendor.resolve = resolve
    install(monkeypatch, vendor)
    with pytest.raises(SourceError, match="no contract for instrument id"):
        VendorSource(HOUR).fetch(vendor_instrument(config), START, END)


# --- the key (I-13) -------------------------------------------------------------------------


@pytest.mark.parametrize("key", [None, "", "   "])
def test_without_the_key_the_adapter_refuses_and_makes_no_call(monkeypatch, config, key):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=key)
    with pytest.raises(SourceError, match=f"{KEY_ENV} is not set.*no request was made"):
        VendorSource(HOUR).fetch(vendor_instrument(config), START, END)
    assert vendor.calls == [] and vendor.keys == []


def test_without_the_key_bars_fetch_refuses_exit_1_and_writes_no_bar(monkeypatch, config,
                                                                     tmp_path, capsys):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=None)
    state = tmp_path / "state"
    assert fetch_cli(state, config, "2019-04-01T00:00:00+00:00") == 1
    assert KEY_ENV in capsys.readouterr().err
    assert vendor.calls == []
    assert BarStore(state, TRACK, HOUR).last_ts(SYMBOL) is None


def test_without_the_client_package_the_adapter_refuses(monkeypatch, config):
    monkeypatch.setitem(sys.modules, CLIENT_PACKAGE, None)    # import raises ImportError
    monkeypatch.setenv(KEY_ENV, FAKE_KEY)
    with pytest.raises(SourceError, match="'vendor' extra") as caught:
        VendorSource(HOUR).fetch(vendor_instrument(config), START, END)
    assert FAKE_KEY not in str(caught.value)


def test_a_client_error_that_holds_the_key_is_redacted(vendor, config):
    vendor.fail_with = f"401 unauthorized for key {FAKE_KEY} (was {FAKE_KEY})"
    with pytest.raises(SourceError) as caught:
        VendorSource(HOUR).fetch(vendor_instrument(config), START, END)
    text = str(caught.value)
    assert FAKE_KEY not in text and "<redacted>" in text and "401 unauthorized" in text
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_the_key_appears_in_no_output_error_or_written_file(monkeypatch, config, tmp_path,
                                                             capsys):
    vendor = make_vendor()
    install(monkeypatch, vendor)
    state = tmp_path / "state"
    assert fetch_cli(state, config, "2019-04-01T00:00:00+00:00") == 0
    vendor.fail_with = f"server error, key={FAKE_KEY}"
    assert fetch_cli(state, config, "2019-04-03T00:00:00+00:00") == 1
    out = capsys.readouterr()
    assert "<redacted>" in out.err
    files = [p for p in state.rglob("*") if p.is_file()]
    assert files
    leaks = [str(p) for p in files if FAKE_KEY.encode() in p.read_bytes()]
    assert leaks == []
    assert FAKE_KEY not in out.out and FAKE_KEY not in out.err


# --- bars fetch on a vendor track -----------------------------------------------------------


def test_bars_fetch_on_a_vendor_track_writes_closed_bars_and_rolls(vendor, config, tmp_path,
                                                                    capsys):
    state = tmp_path / "state"
    as_of = datetime(2019, 4, 1, 5, tzinfo=UTC)
    assert fetch_cli(state, config, as_of.isoformat()) == 0
    out = capsys.readouterr().out
    until = as_of - timedelta(hours=24)                  # the embargo
    assert f"available until {until.isoformat()}" in out
    stored = BarStore(state, TRACK, HOUR).read_range(
        SYMBOL, datetime(2019, 1, 7, tzinfo=UTC), as_of)
    assert len(stored) > 1000
    # Only closed bars, and none inside the embargo.
    assert (stored["ts"] + pd.Timedelta(hours=1) <= pd.Timestamp(until)).all()
    expected = vendor.synth.fetch(vendor.instrument, datetime(2019, 1, 7, tzinfo=UTC), until)
    expected = expected[expected["ts"] + pd.Timedelta(hours=1) <= pd.Timestamp(until)]
    assert stored["ts"].tolist() == expected["ts"].tolist()
    assert stored["contract"].tolist() == expected["contract"].tolist()
    # The roll of 2019-03-14 is recorded and measured through fetch_contract.
    rolls = read_rolls(roll_path(state, TRACK, SYMBOL))
    assert [(r.old, r.new, r.estimated) for r in rolls] == [
        ("SYNA-2019-03", "SYNA-2019-06", False)]
    assert rolls[0].ts == pd.Timestamp("2019-03-14T00:00:00Z")
    assert f"roll {SYMBOL} " in out
    raw = [kw for name, kw in vendor.calls if name == "get_range"]
    assert any(kw["stype_in"] == "raw_symbol" for kw in raw)


def test_a_cost_above_the_limit_stops_bars_fetch_before_any_write(monkeypatch, config,
                                                                  tmp_path, capsys):
    vendor = make_vendor(cost=12.5)
    install(monkeypatch, vendor)
    state = tmp_path / "state"
    assert fetch_cli(state, config, "2019-04-01T00:00:00+00:00") == 1
    assert "above max_cost_usd" in capsys.readouterr().err
    assert "get_range" not in vendor.names()
    assert BarStore(state, TRACK, HOUR).last_ts(SYMBOL) is None
