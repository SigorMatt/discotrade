"""Shared set-up of the vendor tests: a fixture configuration with one vendor
instrument whose fake vendor serves the synthetic SYNA market (tests/fakes/).

The vendor record and its track are written into a temporary copy of
``tests/fixtures/config/``; every value in them is invented for the tests.
"""

import shutil
import sys
from datetime import UTC, datetime

from discotrade.cli import REPO_ROOT
from discotrade.config import load_calendar, load_instrument
from discotrade.sources.synth import SynthSource
from discotrade.sources.vendor import CLIENT_PACKAGE, KEY_ENV
from fakes.vendor_client import FakeVendor

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
HOUR = 3600
SYMBOL = "VENA"
TRACK = "test_vendor"
DATASET = "FAKE.DATASET"
CONTINUOUS = "VENA.v.0"
FAKE_KEY = "fake-key-q7Zt93kXw2"

VENDOR_RECORD = """\
# Vendor fixture instrument for tests: every value is invented.
symbol = "VENA"
venue = "TESTVENUE"
quote_currency = "USD"
calendar = "synth_week"
multiplier = 10.0
tick_size = 0.25
shorting = true
test_only = false
trusted_from = "2019-01-07"
main_session = ["09:30", "16:00"]

[spec]
checked = "2026-10-12"
source = "invented for tests"
verified = false

[cost]
fee_per_side = 0.5
spread_ticks_main = 1.0
spread_ticks_off = 2.0
slippage_coef = 0.02
checked = "2026-10-12"
source = "invented for tests"
verified = false

[source]
adapter = "vendor"
dataset = "FAKE.DATASET"
symbol = "VENA.v.0"
roll_rule = "volume"
{extra}
"""

VENDOR_TRACK = """\
name = "test_vendor"
bar_seconds = 3600
w_days = 28
t_days = 7
history_cap_bars = 480
block_days = 7
epoch = "2019-06-03"
instruments = ["VENA"]
families = ["trend", "mean_reversion", "breakout", "volatility_regime",
            "volume", "time_of_day"]
cell_slots = 3

[horizons]
short = [1, 6]
medium = [6, 48]
"""


def make_config(path, extra=""):
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    (path / "instruments" / f"{SYMBOL}.toml").write_text(VENDOR_RECORD.format(extra=extra))
    (path / "tracks" / f"{TRACK}.toml").write_text(VENDOR_TRACK)
    return path


def vendor_instrument(config):
    return load_instrument(config / "instruments" / f"{SYMBOL}.toml")


def make_vendor(**kwargs):
    calendars = {p.stem: load_calendar(p)
                 for p in sorted((FIXTURE_CONFIG / "calendars").glob("*.toml"))}
    synth = SynthSource(calendars, HOUR)
    syna = load_instrument(FIXTURE_CONFIG / "instruments" / "SYNA.toml")
    kwargs.setdefault("dataset_end", datetime(2019, 3, 31, 20, tzinfo=UTC))
    return FakeVendor(synth, syna, DATASET, CONTINUOUS, **kwargs)


def install(monkeypatch, vendor, key=FAKE_KEY):
    """Put the fake client package in place and set (or unset) the key."""
    monkeypatch.setitem(sys.modules, CLIENT_PACKAGE, vendor.module())
    if key is None:
        monkeypatch.delenv(KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(KEY_ENV, key)
