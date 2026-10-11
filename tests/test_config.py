"""Configuration records: tracks, instruments, windows (DESIGN 4.1, 4.2; I-10)."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from discotrade.cli import REPO_ROOT
from discotrade.config import (
    ConfigError,
    load_instrument,
    load_track,
    load_track_config,
)

CONFIG = REPO_ROOT / "config"
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"

HOURLY_SYMBOLS = ["MES", "MNQ", "MYM", "M2K", "MGC", "SIL", "MCL", "M6E"]

# SPEC.md section 17, "Contracts and trading costs at Interactive Brokers".
SPEC_FEES = {
    "MNQ": 0.61, "MES": 0.61, "MYM": 0.61, "MGC": 0.96,
    "M2K": 0.61, "SIL": 1.26, "M6E": 0.40, "MCL": 0.86,
}

VENDOR_INSTRUMENT = """\
symbol = "{symbol}"
venue = "XV"
quote_currency = "USD"
calendar = "cal"
multiplier = 5.0
tick_size = 0.25
shorting = true
test_only = false
trusted_from = "2019-05-06"
main_session = ["09:30", "16:00"]

[spec]
checked = "2026-10-11"
source = "somewhere"
verified = false

[cost]
fee_per_side = 0.61
spread_ticks_main = 1.0
spread_ticks_off = 2.0
slippage_coef = 0.02
checked = "2026-10-11"
source = "SPEC.md"
verified = false

[source]
adapter = "vendor"
dataset = "DS"
symbol = "{symbol}.v.0"
roll_rule = "volume"
"""

SYNTH_INSTRUMENT = """\
symbol = "{symbol}"
venue = "SYNTH"
quote_currency = "USD"
calendar = "cal"
multiplier = 10.0
tick_size = 0.01
shorting = true
test_only = {test_only}
trusted_from = "2019-01-01"
main_session = ["09:30", "16:00"]

[cost]
fee_per_side = 0.5
spread_ticks_main = 1.0
spread_ticks_off = 2.0
slippage_coef = 0.02

[source]
adapter = "synth"
seed = 1
hourly_vol = 0.002
start_price = 100.0
gap_scale = 0.1
range_scale = 0.5
volume_median = 1000.0
volume_sigma = 0.5
hour_vol_amplitude = 0.5
hour_volume_amplitude = 0.5
hour_peak_utc = 15
"""

#: Decision 10: the generator settings every synthetic record carries.
GENERATOR = {"gap_scale": 0.1, "range_scale": 0.5, "volume_median": 1000.0,
             "volume_sigma": 0.5, "hour_vol_amplitude": 0.5,
             "hour_volume_amplitude": 0.5, "hour_peak_utc": 15}
#: DESIGN 17.1: the contract keys a quarterly roll schedule needs.
QUARTERLY = 'roll_schedule = "quarterly"\nroll_day = 14\ncontract_overlap_bars = 48\n' \
            "contract_offset_scale = 20.0\n"

TRACK = """\
name = "{name}"
bar_seconds = 3600
w_days = 90
t_days = 14
history_cap_bars = 1500
block_days = 14
epoch = "2019-06-03"
instruments = {instruments}
families = ["trend", "mean_reversion", "breakout"]
cell_slots = 3

[horizons]
short = [1, 6]
medium = [6, 48]
"""


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def vendor(tmp_path, text=None, symbol="AAA"):
    body = (text if text is not None else VENDOR_INSTRUMENT).format(symbol=symbol)
    return write(tmp_path / "instruments" / f"{symbol}.toml", body)


def synth(tmp_path, symbol="SYA", test_only="false", extra=""):
    body = SYNTH_INSTRUMENT.format(symbol=symbol, test_only=test_only) + extra
    return write(tmp_path / "instruments" / f"{symbol}.toml", body)


def track(tmp_path, name="t1", instruments='["AAA"]', text=None):
    body = (text if text is not None else TRACK).format(name=name, instruments=instruments)
    return write(tmp_path / "tracks" / f"{name}.toml", body)


def refused(fn, *args, match):
    with pytest.raises(ConfigError, match=match):
        fn(*args)


# --- the repository's records ------------------------------------------------


def test_hourly_track_as_designed():
    t = load_track(CONFIG / "tracks" / "hourly.toml")
    assert t.name == "hourly"
    assert t.bar_seconds == 3600
    assert (t.w_days, t.t_days, t.history_cap_bars, t.block_days) == (90, 14, 1500, 14)
    assert t.epoch == date(2019, 6, 3)
    assert list(t.instruments) == HOURLY_SYMBOLS
    assert list(t.families) == [
        "trend", "mean_reversion", "breakout", "volatility_regime", "volume", "time_of_day",
    ]
    assert t.cell_slots == 3
    assert t.horizons == (("short", (1, 6)), ("medium", (6, 48)))


def test_hourly_loads_with_its_eight_instruments():
    tc = load_track_config(CONFIG, "hourly")
    assert [i.symbol for i in tc.instruments] == HOURLY_SYMBOLS


@pytest.mark.parametrize("symbol", HOURLY_SYMBOLS)
def test_instrument_records_carry_spec_costs_unverified(symbol):
    inst = load_instrument(CONFIG / "instruments" / f"{symbol}.toml")
    assert inst.symbol == symbol
    assert inst.cost.fee_per_side == SPEC_FEES[symbol]
    assert inst.cost.fee_bps is None
    assert inst.cost.slippage_coef == 0.02
    assert inst.cost.provenance.verified is False
    assert inst.cost.provenance.source == "SPEC.md §17"
    assert inst.provenance.verified is False
    assert "http" in inst.provenance.source
    assert inst.multiplier > 0 and inst.tick_size > 0
    assert inst.test_only is False
    assert inst.shorting is True
    assert inst.source.adapter == "vendor"
    assert inst.source.get("symbol") == f"{symbol}.v.0"
    assert inst.source.get("roll_rule") == "volume"


def test_cells_are_families_then_horizons():
    t = load_track(CONFIG / "tracks" / "hourly.toml")
    assert len(t.cells) == len(t.families) * len(t.horizons) == 12
    assert t.cells[:3] == (("trend", "short"), ("trend", "medium"), ("mean_reversion", "short"))
    assert t.cells[-1] == ("time_of_day", "medium")
    for index, (family, horizon) in enumerate(t.cells):
        assert t.cell_index(family, horizon) == index
        assert index == t.families.index(family) * 2 + [h for h, _ in t.horizons].index(horizon)


# --- windows (DESIGN 4.1), as date ranges ------------------------------------


def test_windows_for_a_day():
    t = load_track(CONFIG / "tracks" / "hourly.toml")
    w = t.windows(date(2026, 3, 13))
    assert (w.t.first, w.t.last) == (date(2026, 2, 28), date(2026, 3, 13))
    assert (w.w.first, w.w.last) == (date(2025, 11, 30), date(2026, 2, 27))
    assert w.t.days() == 14 and w.w.days() == 90


def test_windows_select_trading_days_from_a_stub_calendar():
    t = load_track(CONFIG / "tracks" / "hourly.toml")
    start = date(2025, 9, 1)
    weekdays = [start + timedelta(n) for n in range(250) if (start + timedelta(n)).weekday() < 5]
    w = t.windows(date(2026, 3, 13))
    t_days = w.t.select(weekdays)
    assert t_days == [date(2026, 3, d) for d in (2, 3, 4, 5, 6, 9, 10, 11, 12, 13)]
    w_days = w.w.select(weekdays)
    assert w_days[0] == date(2025, 12, 1) and w_days[-1] == date(2026, 2, 27)
    assert set(w_days).isdisjoint(t_days)


def test_fixture_track_windows():
    t = load_track(FIXTURE_CONFIG / "tracks" / "test_synth.toml")
    w = t.windows(date(2026, 1, 31))
    assert (w.t.first, w.t.last) == (date(2026, 1, 25), date(2026, 1, 31))
    assert (w.w.first, w.w.last) == (date(2025, 12, 28), date(2026, 1, 24))


# --- the fixture configuration (DESIGN 18.2, 18.3) ---------------------------


def test_fixture_test_synth():
    tc = load_track_config(FIXTURE_CONFIG, "test_synth")
    t = tc.track
    assert (t.w_days, t.t_days, t.history_cap_bars, t.block_days) == (28, 7, 480, 7)
    assert len(tc.instruments) == 4
    for inst in tc.instruments:
        assert inst.shorting and inst.cost.fee_per_side is not None
        assert inst.source.adapter == "synth"


def test_fixture_test_mixed():
    synth4 = {i.symbol for i in load_track_config(FIXTURE_CONFIG, "test_synth").instruments}
    mixed = load_track_config(FIXTURE_CONFIG, "test_mixed").instruments
    assert len(mixed) == 3
    assert len([i for i in mixed if i.symbol in synth4]) == 1
    others = [i for i in mixed if i.symbol not in synth4]
    assert any(not i.shorting and i.cost.fee_per_side is not None for i in others)
    assert any(i.cost.fee_bps is not None and i.multiplier is None for i in others)
    assert any(i.source.get("roll_schedule") not in (None, "none") for i in mixed)
    assert all(i.source.get("drop_fraction") > 0 for i in mixed)


def test_fixture_has_six_synthetic_instruments_and_one_crypto():
    files = sorted((FIXTURE_CONFIG / "instruments").glob("*.toml"))
    adapters = {path.stem: load_instrument(path).source.adapter for path in files}
    assert sorted(s for s, a in adapters.items() if a == "synth") == [
        "SYNA", "SYNB", "SYNC", "SYND", "SYNL", "SYNX"]
    assert {s: a for s, a in adapters.items() if a != "synth"} == {"CRYA": "crypto"}


# --- refusals ------------------------------------------------------------------


def test_valid_temporary_records_load(tmp_path):
    vendor(tmp_path)
    track(tmp_path)
    tc = load_track_config(tmp_path, "t1")
    assert tc.instruments[0].symbol == "AAA"


@pytest.mark.parametrize(
    "old, new, name",
    [
        ('venue = "XV"\n', 'venue = "XV"\ncolour = "red"\n', "colour"),
        ("slippage_coef = 0.02\n", "slippage_coef = 0.02\nholding = 1.0\n", "cost.holding"),
        ('roll_rule = "volume"\n', 'roll_rule = "volume"\nfoo = 1\n', "source.foo"),
        ("", "[extra]\nx = 1\n", "extra"),
    ],
)
def test_instrument_unknown_key_refused_by_name(tmp_path, old, new, name):
    text = VENDOR_INSTRUMENT.replace(old, new, 1) if old else VENDOR_INSTRUMENT + new
    path = vendor(tmp_path, text)
    refused(load_instrument, path, match=f"unknown key '{name}'")


def test_track_unknown_key_refused_by_name(tmp_path):
    path = track(tmp_path, text=TRACK + "\n[extra]\nfoo = 1\n")
    refused(load_track, path, match="unknown key 'extra'")
    path = track(tmp_path, text=TRACK.replace("cell_slots = 3", "cell_slots = 3\nbar_size = 1"))
    refused(load_track, path, match="unknown key 'bar_size'")


@pytest.mark.parametrize(
    "key", ["symbol", "venue", "tick_size", "shorting", "trusted_from", "main_session"]
)
def test_instrument_missing_key_refused(tmp_path, key):
    lines = [ln for ln in VENDOR_INSTRUMENT.splitlines() if not ln.startswith(f"{key} =")]
    path = vendor(tmp_path, "\n".join(lines) + "\n")
    refused(load_instrument, path, match=f"missing key '{key}'")


COST_COMPANIONS = 'checked = "2026-10-11"\nsource = "SPEC.md"\nverified = false\n'


@pytest.mark.parametrize("key", ["checked", "source", "verified"])
def test_cost_companions_go_together(tmp_path, key):
    kept = "".join(ln + "\n" for ln in COST_COMPANIONS.splitlines() if not ln.startswith(key))
    path = vendor(tmp_path, VENDOR_INSTRUMENT.replace(COST_COMPANIONS, kept, 1))
    refused(load_instrument, path, match=f"missing key 'cost.{key}'")


def test_top_level_companions_go_together(tmp_path):
    text = VENDOR_INSTRUMENT.replace('source = "somewhere"\n', "", 1)
    refused(load_instrument, vendor(tmp_path, text), match="missing key 'spec.source'")


@pytest.mark.parametrize(
    "old, new, match",
    [
        ('checked = "2026-10-11"\nsource = "SPEC.md"',
         'checked = "11 Oct"\nsource = "SPEC.md"', "cost.checked"),
        ("verified = false\n\n[source]", 'verified = "no"\n\n[source]', "cost.verified"),
        ('source = "somewhere"', "source = 3", "'spec.source'"),
    ],
)
def test_companion_types_refused(tmp_path, old, new, match):
    path = vendor(tmp_path, VENDOR_INSTRUMENT.replace(old, new, 1))
    refused(load_instrument, path, match=match)


def test_sourced_instrument_needs_companions(tmp_path):
    text = VENDOR_INSTRUMENT.replace(
        '[spec]\nchecked = "2026-10-11"\nsource = "somewhere"\nverified = false\n', "", 1
    )
    refused(load_instrument, vendor(tmp_path, text), match="spec: checked, source and verified")
    text = VENDOR_INSTRUMENT.replace(COST_COMPANIONS, "", 1)
    refused(load_instrument, vendor(tmp_path, text), match=r"cost: checked, source and verified")


def test_synthetic_instrument_needs_no_companions(tmp_path):
    inst = load_instrument(synth(tmp_path))
    assert inst.provenance is None and inst.cost.provenance is None
    assert inst.unverified() == []


def test_unverified_lists_every_sourced_value(tmp_path):
    inst = load_instrument(vendor(tmp_path))
    keys = [key for key, _value, _prov in inst.unverified()]
    assert keys == [
        "multiplier", "tick_size", "trusted_from", "main_session",
        "cost.fee_per_side", "cost.spread_ticks_main", "cost.spread_ticks_off",
        "cost.slippage_coef",
    ]


@pytest.mark.parametrize(
    "edit, match",
    [
        # both forms
        (lambda s: s.replace("fee_per_side = 0.61", "fee_per_side = 0.61\nfee_bps = 1.0"),
         "exactly one fee form"),
        # neither
        (lambda s: s.replace("fee_per_side = 0.61\n", ""), "exactly one fee form"),
        # fee_bps with a multiplier
        (lambda s: s.replace("fee_per_side = 0.61", "fee_bps = 1.0"), "exactly one fee form"),
        # fee_per_side without a multiplier
        (lambda s: s.replace("multiplier = 5.0\n", ""), "exactly one fee form"),
    ],
)
def test_exactly_one_fee_form(tmp_path, edit, match):
    refused(load_instrument, vendor(tmp_path, edit(VENDOR_INSTRUMENT)), match=match)


def test_fee_bps_form_loads(tmp_path):
    text = VENDOR_INSTRUMENT.replace("multiplier = 5.0\n", "").replace(
        "fee_per_side = 0.61", "fee_bps = 1.0"
    )
    inst = load_instrument(vendor(tmp_path, text))
    assert inst.multiplier is None and inst.cost.fee_bps == 1.0
    assert inst.cost.fee_per_side is None


@pytest.mark.parametrize(
    "old, new, match",
    [
        ("tick_size = 0.25", "tick_size = 0.0", "tick_size"),
        ("tick_size = 0.25", 'tick_size = "0.25"', "tick_size"),
        ("shorting = true", "shorting = 1", "shorting"),
        ('trusted_from = "2019-05-06"', 'trusted_from = "May 2019"', "trusted_from"),
        ('main_session = ["09:30", "16:00"]', 'main_session = ["16:00", "09:30"]',
         "main_session"),
        ('main_session = ["09:30", "16:00"]', 'main_session = ["9h", "16:00"]', "main_session"),
        ("slippage_coef = 0.02", "slippage_coef = -0.1", "slippage_coef"),
        ('adapter = "vendor"', 'adapter = "ftp"', "adapter"),
        ('roll_rule = "volume"', 'roll_rule = "calendar"', "roll_rule"),
    ],
)
def test_invalid_instrument_value_refused(tmp_path, old, new, match):
    path = vendor(tmp_path, VENDOR_INSTRUMENT.replace(old, new, 1))
    refused(load_instrument, path, match=match)


def test_symbol_must_match_file_name(tmp_path):
    path = write(tmp_path / "instruments" / "BBB.toml", VENDOR_INSTRUMENT.format(symbol="AAA"))
    refused(load_instrument, path, match="file name")


def test_track_name_must_match_file_name(tmp_path):
    path = write(tmp_path / "tracks" / "other.toml", TRACK.format(name="t1", instruments="[]"))
    refused(load_track, path, match="file name")


@pytest.mark.parametrize(
    "old, new, match",
    [
        ("w_days = 90", "w_days = 0", "w_days"),
        ("bar_seconds = 3600", 'bar_seconds = "1h"', "bar_seconds"),
        ("short = [1, 6]", "short = [7, 6]", "horizons.short"),
        ("short = [1, 6]", "short = [0, 6]", "horizons.short"),
        ('epoch = "2019-06-03"', 'epoch = "June"', "epoch"),
        ('families = ["trend", "mean_reversion", "breakout"]',
         'families = ["trend", "trend"]', "families"),
        ("[horizons]\nshort = [1, 6]\nmedium = [6, 48]\n", "[horizons]\n", "horizons"),
    ],
)
def test_invalid_track_value_refused(tmp_path, old, new, match):
    path = track(tmp_path, text=TRACK.replace(old, new, 1))
    refused(load_track, path, match=match)


def test_track_with_duplicate_or_missing_instrument_refused(tmp_path):
    vendor(tmp_path)
    track(tmp_path, instruments='["AAA", "AAA"]')
    refused(load_track_config, tmp_path, "t1", match="instruments")
    track(tmp_path, instruments='["AAA", "ZZZ"]')
    refused(load_track_config, tmp_path, "t1", match="ZZZ")


def test_missing_track_refused(tmp_path):
    refused(load_track_config, tmp_path, "nope", match="nope")


def test_test_only_instrument_refused_outside_a_test_track(tmp_path):
    synth(tmp_path, "SYA", test_only="true")
    track(tmp_path, name="live", instruments='["SYA"]')
    refused(load_track_config, tmp_path, "live", match="test_only")
    track(tmp_path, name="test_x", instruments='["SYA"]')
    assert load_track_config(tmp_path, "test_x").instruments[0].test_only is True


def test_synth_source_keys(tmp_path):
    inst = load_instrument(synth(tmp_path))
    assert inst.source.get("seed") == 1
    assert inst.source.get("drop_fraction") == 0.0
    refused(
        load_instrument,
        synth(tmp_path, "SYB", extra="drop_fraction = 1.5\n"),
        match="drop_fraction",
    )


@pytest.mark.parametrize("key", sorted(GENERATOR))
def test_synth_generator_key_missing_refused_by_name(tmp_path, key):
    """Decision 10: every generator setting is a required [source] key."""
    body = SYNTH_INSTRUMENT.format(symbol="SYA", test_only="false")
    line = next(ln for ln in body.splitlines() if ln.startswith(f"{key} = "))
    path = write(tmp_path / "instruments" / "SYA.toml", body.replace(line + "\n", ""))
    refused(load_instrument, path, match=f"missing key 'source.{key}'")


def test_synth_generator_keys_are_read():
    inst = load_instrument(FIXTURE_CONFIG / "instruments" / "SYNB.toml")
    for key, value in GENERATOR.items():
        got = inst.source.get(key)
        assert got == value and type(got) is type(value), key


def test_every_fixture_record_carries_the_mission_1_generator_settings():
    for path in sorted((FIXTURE_CONFIG / "instruments").glob("*.toml")):
        inst = load_instrument(path)
        if inst.source.adapter != "synth":
            continue
        assert {k: inst.source.get(k) for k in GENERATOR} == GENERATOR, path.name


@pytest.mark.parametrize(("key", "value", "match"), [
    ("gap_scale", "-0.1", "at least 0"),
    ("range_scale", "-0.5", "at least 0"),
    ("volume_median", "0.0", "positive"),
    ("volume_sigma", "-1.0", "at least 0"),
    ("hour_vol_amplitude", "1.0", "less than 1"),
    ("hour_vol_amplitude", "-0.1", "at least 0"),
    ("hour_volume_amplitude", "-0.1", "at least 0"),
    ("hour_peak_utc", "24", "at most 23"),
    ("hour_peak_utc", "15.0", "integer"),
])
def test_synth_generator_value_refused(tmp_path, key, value, match):
    body = SYNTH_INSTRUMENT.format(symbol="SYA", test_only="false")
    line = next(ln for ln in body.splitlines() if ln.startswith(f"{key} = "))
    path = write(tmp_path / "instruments" / "SYA.toml", body.replace(line, f"{key} = {value}"))
    refused(load_instrument, path, match=f"source.{key}.*{match}")


def test_synth_quarterly_contract_keys(tmp_path):
    inst = load_instrument(synth(tmp_path, extra=QUARTERLY))
    assert inst.source.get("roll_schedule") == "quarterly"
    assert inst.source.get("roll_day") == 14
    assert inst.source.get("contract_overlap_bars") == 48
    assert inst.source.get("contract_offset_scale") == 20.0
    syna = load_instrument(FIXTURE_CONFIG / "instruments" / "SYNA.toml")
    assert syna.source.get("roll_schedule") == "quarterly"
    assert syna.source.get("contract_overlap_bars") >= 24


@pytest.mark.parametrize("key", ["roll_day", "contract_overlap_bars", "contract_offset_scale"])
def test_synth_quarterly_contract_key_missing_refused_by_name(tmp_path, key):
    extra = "".join(ln + "\n" for ln in QUARTERLY.splitlines() if not ln.startswith(key))
    refused(load_instrument, synth(tmp_path, extra=extra), match=f"missing key 'source.{key}'")


@pytest.mark.parametrize(("key", "value", "match"), [
    ("roll_day", "0", "at least 1"),
    ("roll_day", "29", "at most 28"),
    ("contract_overlap_bars", "23", "at least 24"),
    ("contract_offset_scale", "-1.0", "at least 0"),
])
def test_synth_quarterly_contract_value_refused(tmp_path, key, value, match):
    extra = "".join((f"{key} = {value}" if ln.startswith(key) else ln) + "\n"
                    for ln in QUARTERLY.splitlines())
    refused(load_instrument, synth(tmp_path, extra=extra), match=f"source.{key}.*{match}")


def test_synth_contract_keys_refused_without_a_roll_schedule(tmp_path):
    refused(load_instrument, synth(tmp_path, extra="roll_day = 14\n"),
            match="source.roll_day.*roll_schedule")


def test_not_toml_refused(tmp_path):
    path = write(tmp_path / "instruments" / "AAA.toml", "symbol = \n")
    refused(load_instrument, path, match="TOML")


def test_records_are_frozen():
    inst = load_instrument(CONFIG / "instruments" / "MES.toml")
    with pytest.raises(AttributeError):
        inst.tick_size = 1.0  # type: ignore[misc]
    hash(inst)
