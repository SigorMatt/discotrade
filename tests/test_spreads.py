"""Spread tables and their measurement, and live check L2 offline (DESIGN 5.7,
19.3 L2; decisions 2026-10-12 13 to 15; I-10, I-11, I-13).

The quote samples here are synthetic, with a known spread per exchange-local
hour; they prove the computation, not any real spread (that is live check L2).
The vendor's quote shape used by ``vendor quotes`` is the inline fake below and
is NOT PROVEN against the real client.
"""

import shutil
import sys
import tomllib
import types
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
from fakes.vendor_world import FAKE_KEY, SYMBOL, TRACK, install, make_config, make_vendor

from discotrade.cli import REPO_ROOT, main
from discotrade.config import (
    ConfigError,
    check,
    frozen_drift,
    frozen_snapshot,
    load_calendar,
    load_changes,
    load_instrument,
    load_spread_table,
)
from discotrade.sources.vendor import CLIENT_PACKAGE, KEY_ENV
from discotrade.spreads import SpreadError, measure, spread_table, spread_ticks
from discotrade.tradingcal import open_intervals

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "config"
NY = ZoneInfo("America/New_York")
AS_OF = "2019-04-01T05:00:00+00:00"


@pytest.fixture(autouse=True)
def _no_state(monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)


@pytest.fixture
def syna():
    return load_instrument(FIXTURE / "instruments" / "SYNA.toml")


@pytest.fixture
def week():
    return load_calendar(FIXTURE / "calendars" / "synth_week.toml")


@pytest.fixture
def config(tmp_path):
    return make_config(tmp_path / "config")


def utc(*args):
    return datetime(*args, tzinfo=UTC)


# --- the table and the rule (DESIGN 5.7) ---------------------------------------------


def test_fixture_table_loads(syna):
    table = load_spread_table(FIXTURE / "spreads" / "SYNA.toml")
    assert table.symbol == "SYNA" and len(table.ticks) == 24
    assert table.ticks[10] == 1.25 and table.ticks[17] == 3.0
    assert table.provenance.verified is False and table.description
    assert spread_table(FIXTURE, "SYNA") == table
    assert spread_table(FIXTURE, "SYNB") is None


# Across the spring clock change of 2019-03-10 in New York (UTC-5 before, UTC-4
# after): the same UTC hour is a different exchange-local hour on either side.
ACROSS_SPRING = [
    # (bar open in UTC, exchange-local hour, in the main session)
    (utc(2019, 3, 8, 14), 9, False),     # Fri 09:00 EST: before 09:30
    (utc(2019, 3, 8, 15), 10, True),     # Fri 10:00 EST
    (utc(2019, 3, 8, 20), 15, True),     # Fri 15:00 EST
    (utc(2019, 3, 8, 21), 16, False),    # Fri 16:00 EST: the session has ended
    (utc(2019, 3, 8, 2), 21, False),     # Thu 21:00 EST
    (utc(2019, 3, 11, 2), 22, False),    # Sun 22:00 EDT, after the change
    (utc(2019, 3, 11, 14), 10, True),    # Mon 10:00 EDT
    (utc(2019, 3, 11, 15), 11, True),    # Mon 11:00 EDT
    (utc(2019, 3, 11, 19), 15, True),    # Mon 15:00 EDT
    (utc(2019, 3, 11, 20), 16, False),   # Mon 16:00 EDT
    (utc(2019, 3, 11, 13), 9, False),    # Mon 09:00 EDT
]


@pytest.mark.parametrize(("ts", "hour", "main_session"), ACROSS_SPRING)
def test_rule_gives_the_table_value_of_the_local_hour(syna, week, ts, hour, main_session):
    table = load_spread_table(FIXTURE / "spreads" / "SYNA.toml")
    assert spread_ticks(syna, week, table, ts) == table.ticks[hour]


@pytest.mark.parametrize(("ts", "hour", "main_session"), ACROSS_SPRING)
def test_rule_without_a_table_gives_main_or_off(syna, week, ts, hour, main_session):
    expected = syna.cost.spread_ticks_main if main_session else syna.cost.spread_ticks_off
    assert spread_ticks(syna, week, None, ts) == expected


def test_rule_distinguishes_the_clock_change(syna, week):
    """The same UTC hour reads different hours of the table on either side."""
    table = load_spread_table(FIXTURE / "spreads" / "SYNA.toml")
    before, after = utc(2019, 3, 8, 15), utc(2019, 3, 11, 15)
    assert spread_ticks(syna, week, table, before) == table.ticks[10] == 1.25
    assert spread_ticks(syna, week, table, after) == table.ticks[11] == 1.0


def test_rule_refuses_a_table_of_another_instrument(week):
    syna_table = load_spread_table(FIXTURE / "spreads" / "SYNA.toml")
    synb = load_instrument(FIXTURE / "instruments" / "SYNB.toml")
    with pytest.raises(ValueError, match="SYNA"):
        spread_ticks(synb, week, syna_table, utc(2019, 3, 8, 15))


@pytest.mark.parametrize(("edit", "match"), [
    (lambda t: t.replace('symbol = "SYNA"', 'symbol = "SYNB"'), "file name"),
    (lambda t: t.replace("1.5, 3.0, 3.0,", "1.5, 3.0,"), "24"),
    (lambda t: t.replace("1.5, 3.0, 3.0,", "1.5, -3.0, 3.0,"), "spread_ticks"),
    (lambda t: t.replace("1.5, 3.0, 3.0,", '1.5, "3", 3.0,'), "spread_ticks"),
    (lambda t: t.replace('source = "invented for tests"\n', ""), "source"),
    (lambda t: t.replace("description =", "note ="), "note"),
])
def test_table_refusals(tmp_path, edit, match):
    path = tmp_path / "SYNA.toml"
    path.write_text(edit((FIXTURE / "spreads" / "SYNA.toml").read_text()))
    with pytest.raises(ConfigError, match=match):
        load_spread_table(path)


# --- the frozen rule (DESIGN 4.3, I-10) ----------------------------------------------


def test_a_new_spread_table_is_a_frozen_file_that_needs_an_entry(tmp_path):
    root = tmp_path
    shutil.copytree(REPO_ROOT / "config" / "instruments", root / "config" / "instruments")
    (root / "meta" / "decisions").mkdir(parents=True)
    (root / "meta" / "decisions" / "d.md").write_text("approved\n")
    frozen = frozen_snapshot(root)
    (root / "config" / "spreads").mkdir()
    shutil.copy(FIXTURE / "spreads" / "SYNA.toml", root / "config" / "spreads" / "SYNA.toml")
    problems = frozen_drift(root, frozen, ())
    assert len(problems) == 1 and "config/spreads/SYNA.toml" in problems[0]
    history = root / "config" / "HISTORY.toml"
    history.write_text('[[change]]\ndate = "2026-11-01"\nfile = "config/spreads/SYNA.toml"\n'
                       'key = "*"\nold = "none"\nreason = "measured"\n'
                       'decision = "meta/decisions/d.md"\n')
    assert frozen_drift(root, frozen, load_changes(history)) == []
    frozen = frozen_snapshot(root)
    path = root / "config" / "spreads" / "SYNA.toml"
    path.write_text(path.read_text().replace("1.5, 1.0, 1.25,", "1.5, 1.0, 1.0,"))
    problems = frozen_drift(root, frozen, load_changes(history))
    assert len(problems) == 1 and "spread_ticks" in problems[0]


# --- config check: the marginal-spread warning (decision 14) -------------------------


def test_config_check_warns_for_a_main_session_hour_above_one_tick(config, capsys):
    assert main(["--config", str(config), "--track", "test_synth", "config", "check"]) == 0
    out = capsys.readouterr().out
    warnings = [ln for ln in out.splitlines() if ln.startswith("warning")]
    assert len(warnings) == 1
    assert "SYNA" in warnings[0] and "10" in warnings[0] and "1.25" in warnings[0]
    assert any(ln.startswith("spread table SYNA:") for ln in out.splitlines())
    assert any(ln.startswith("unverified spreads/SYNA.toml") for ln in out.splitlines())
    assert out.splitlines()[-1].startswith("config check: ok")


def test_config_check_does_not_warn_for_off_session_hours(config, capsys):
    path = config / "spreads" / "SYNA.toml"
    path.write_text(path.read_text().replace("1.5, 1.0, 1.25,", "1.0, 1.0, 1.0,")
                    .replace("1.5, 3.0, 3.0,", "1.0, 3.0, 3.0,"))
    assert main(["--config", str(config), "--track", "test_synth", "config", "check"]) == 0
    out = capsys.readouterr().out
    assert not [ln for ln in out.splitlines() if ln.startswith("warning")]


def test_main_session_hours_are_those_that_overlap_it(config):
    """09:30 to 16:00 overlaps the hours 09 to 15; hour 09 above one tick warns."""
    path = config / "spreads" / "SYNA.toml"
    path.write_text(path.read_text().replace("1.5, 1.0, 1.25,", "1.5, 1.5, 1.0,"))
    report = check(config, "test_synth")
    assert len(report.warnings) == 1 and "09" in report.warnings[0]
    path.write_text(path.read_text().replace("1.5, 1.5, 1.0,", "1.5, 1.0, 1.0,"))
    assert check(config, "test_synth").warnings == ()


def test_config_check_fails_on_a_table_without_an_instrument(config, capsys):
    shutil.copy(config / "spreads" / "SYNA.toml", config / "spreads" / "NOPE.toml")
    path = config / "spreads" / "NOPE.toml"
    path.write_text(path.read_text().replace('symbol = "SYNA"', 'symbol = "NOPE"'))
    assert main(["--config", str(config), "--track", "test_synth", "config", "check"]) == 1
    assert "NOPE" in capsys.readouterr().err


def test_repository_config_has_no_spread_warning():
    report = check(REPO_ROOT / "config", "hourly")
    assert report.warnings == ()


# --- spreads measure (decision 13) ---------------------------------------------------

#: The known spread, in ticks, of each exchange-local hour of the sample.
KNOWN = [1.0 + (h % 4) * 0.5 for h in range(24)]
SAMPLE_START, SAMPLE_END = utc(2019, 3, 3, 23), utc(2019, 3, 15, 22)   # Sun 18:00 to Fri 17:00


def quote_sample(calendar, tick=0.25, seed=7, skip_hour=None):
    """Quotes every ten minutes of open time, across the spring clock change.

    In each exchange-local hour ``h`` four quotes in five are exactly
    ``KNOWN[h]`` ticks wide and the fifth is one tick wider (the order drawn
    with a fixed seed), so the median of every hour is ``KNOWN[h]``.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for a, b in open_intervals(calendar, SAMPLE_START, SAMPLE_END):
        t = a
        while t < b:
            hour = t.astimezone(NY).hour
            if hour != skip_hour:
                ticks = KNOWN[hour] + (1.0 if rng.random() < 0.2 else 0.0)
                bid = 4000.0 + float(rng.integers(-40, 40)) * tick
                rows.append((t, bid, bid + ticks * tick))
            t += timedelta(minutes=10)
    ts, bid, ask = zip(*rows, strict=True)
    return pd.DataFrame({"ts": pd.DatetimeIndex(ts).astype("datetime64[ns, UTC]"),
                         "bid": bid, "ask": ask})


def test_sample_spans_the_clock_change(week):
    q = quote_sample(week)
    offsets = {t.astimezone(NY).utcoffset() for t in q["ts"]}
    assert offsets == {timedelta(hours=-5), timedelta(hours=-4)}


def test_measure_gives_the_known_median_per_local_hour(syna, week):
    result = measure(quote_sample(week), syna, week)
    expected = [KNOWN[h] for h in range(24)]
    expected[17] = max(KNOWN[h] for h in range(24) if h != 17)   # the daily break
    assert list(result.ticks) == pytest.approx(expected)
    assert result.filled == (17,)


def test_measure_errors_on_an_open_hour_without_a_quote(syna, week):
    with pytest.raises(SpreadError, match=r"\b03\b"):
        measure(quote_sample(week, skip_hour=3), syna, week)


def test_measure_errors_on_an_empty_sample(syna, week):
    empty = quote_sample(week).iloc[:0]
    with pytest.raises(SpreadError, match="no quote"):
        measure(empty, syna, week)


def write_sample(path, frame):
    frame.to_parquet(path, index=False)
    return path


def measure_cli(config, symbol, quotes):
    return main(["--config", str(config), "--as-of", AS_OF, "spreads", "measure",
                 "--symbol", symbol, "--quotes", str(quotes)])


def test_spreads_measure_writes_the_table(tmp_path, config, week, capsys):
    quotes = write_sample(tmp_path / "q.parquet", quote_sample(week))
    assert measure_cli(config, "SYNB", quotes) == 0
    out = capsys.readouterr().out
    path = config / "spreads" / "SYNB.toml"
    assert str(path) in out and "HISTORY.toml" in out and "decisions" in out
    with open(path, "rb") as f:
        rec = tomllib.load(f)
    expected = list(KNOWN)
    expected[17] = max(KNOWN[h] for h in range(24) if h != 17)
    assert rec["spread_ticks"] == pytest.approx(expected)
    assert rec["symbol"] == "SYNB" and rec["verified"] is False
    assert rec["checked"] == "2019-04-01" and "q.parquet" in rec["source"]
    desc = rec["description"]
    assert "2019-03-03" in desc and "2019-03-15" in desc and "America/New_York" in desc
    assert str(len(quote_sample(week))) in desc and "17" in desc
    table = load_spread_table(path)
    assert table.ticks == tuple(rec["spread_ticks"])
    # The new table is read by the rule and by config check.
    synb = load_instrument(config / "instruments" / "SYNB.toml")
    assert spread_ticks(synb, week, spread_table(config, "SYNB"),
                        utc(2019, 3, 8, 15)) == KNOWN[10]
    assert main(["--config", str(config), "--track", "test_synth", "config", "check"]) == 0


def test_spreads_measure_refuses_to_overwrite(tmp_path, config, week, capsys):
    quotes = write_sample(tmp_path / "q.parquet", quote_sample(week))
    path = config / "spreads" / "SYNA.toml"
    before = path.read_bytes()
    assert measure_cli(config, "SYNA", quotes) == 1
    assert "exists" in capsys.readouterr().err
    assert path.read_bytes() == before


def test_spreads_measure_writes_nothing_on_an_open_hour_without_a_quote(tmp_path, config,
                                                                        week, capsys):
    quotes = write_sample(tmp_path / "q.parquet", quote_sample(week, skip_hour=3))
    assert measure_cli(config, "SYNB", quotes) == 1
    err = capsys.readouterr().err
    assert "03" in err
    assert not (config / "spreads" / "SYNB.toml").exists()


def test_spreads_measure_refuses_a_malformed_sample(tmp_path, config, week, capsys):
    quotes = write_sample(tmp_path / "q.parquet", quote_sample(week).drop(columns=["ask"]))
    assert measure_cli(config, "SYNB", quotes) == 1
    assert "ask" in capsys.readouterr().err
    assert not (config / "spreads" / "SYNB.toml").exists()


def test_spreads_measure_needs_a_symbol():
    with pytest.raises(SystemExit) as exc:
        main(["spreads", "measure"])
    assert exc.value.code == 2


# --- the vendor's quotes, and live check L2 offline (decision 15) --------------------


@pytest.mark.parametrize("key", [None, ""])
def test_spreads_measure_from_the_vendor_without_the_key_refuses(monkeypatch, capsys, config,
                                                                 key):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=key)
    assert main(["--config", str(config), "--as-of", AS_OF, "spreads", "measure",
                 "--symbol", SYMBOL]) == 1
    assert KEY_ENV in capsys.readouterr().err
    assert vendor.calls == [] and vendor.keys == []
    assert not (config / "spreads" / f"{SYMBOL}.toml").exists()


@pytest.mark.parametrize("key", [None, ""])
def test_live_spreads_without_the_key_refuses_exit_1_and_makes_no_request(monkeypatch, capsys,
                                                                          config, key):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=key)
    assert main(["--config", str(config), "--track", TRACK, "--as-of", AS_OF,
                 "doctor", "--live", "spreads"]) == 1
    err = capsys.readouterr().err
    assert KEY_ENV in err and "no request was made" in err
    assert vendor.calls == [] and vendor.keys == []
    assert not (config / "spreads" / f"{SYMBOL}.toml").exists()


def test_live_spreads_without_the_key_refuses_on_the_repository_config(monkeypatch, capsys):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=None)
    assert main(["--as-of", AS_OF, "doctor", "--live", "spreads"]) == 1
    assert KEY_ENV in capsys.readouterr().err
    assert vendor.calls == []
    assert not (REPO_ROOT / "config" / "spreads").exists()


class QuoteVendor:
    """A fake of the vendor client's quote calls, in the shape ``spreads.py``
    documents (NOT PROVEN against the real client)."""

    def __init__(self, frame, cost=0.5):
        self.frame, self.cost, self.calls = frame, cost, []

    def module(self):
        vendor = self
        module = types.ModuleType("fake_quote_client")

        class Historical:
            def __init__(self, key=None):
                vendor.calls.append(("Historical", {"key": key}))
                self.metadata = types.SimpleNamespace(get_cost=vendor.get_cost)
                self.timeseries = types.SimpleNamespace(get_range=vendor.get_range)

        module.Historical = Historical
        return module

    def get_cost(self, **kwargs):
        self.calls.append(("get_cost", kwargs))
        return self.cost

    def get_range(self, **kwargs):
        self.calls.append(("get_range", kwargs))
        lo, hi = pd.Timestamp(kwargs["start"]), pd.Timestamp(kwargs["end"])
        f = self.frame[(self.frame["ts"] >= lo) & (self.frame["ts"] < hi)]
        out = pd.DataFrame({"bid_px_00": f["bid"].to_numpy(), "ask_px_00": f["ask"].to_numpy(),
                            "instrument_id": 1000},
                           index=pd.DatetimeIndex(f["ts"], name="ts_recv"))
        return types.SimpleNamespace(to_df=lambda **kw: out.copy())


def test_live_spreads_with_a_fake_client_writes_and_reports(monkeypatch, capsys, config, week):
    vendor = QuoteVendor(quote_sample(week))
    monkeypatch.setitem(sys.modules, CLIENT_PACKAGE, vendor.module())
    monkeypatch.setenv(KEY_ENV, FAKE_KEY)
    # The sample ends at available_until = as-of less 24 hours (DESIGN 5.5).
    assert main(["--config", str(config), "--track", TRACK, "--as-of",
                 "2019-03-16T22:00:00+00:00", "doctor", "--live", "spreads",
                 "--days", "13"]) == 0
    out = capsys.readouterr().out
    path = config / "spreads" / f"{SYMBOL}.toml"
    table = load_spread_table(path)
    expected = list(KNOWN)
    expected[17] = max(KNOWN[h] for h in range(24) if h != 17)
    assert list(table.ticks) == pytest.approx(expected)
    # KNOWN puts 2.5 ticks on hour 11, 1.5 on 9 and 13, 2.0 on 10 and 14.
    assert f"{SYMBOL}: marginal" in out and "doctor --live spreads: ok" in out
    assert FAKE_KEY not in out
    names = [n for n, _ in vendor.calls]
    assert names.index("get_cost") < names.index("get_range")
    # A second run refuses to overwrite the table.
    assert main(["--config", str(config), "--track", TRACK, "--as-of",
                 "2019-03-16T22:00:00+00:00", "doctor", "--live", "spreads",
                 "--days", "13"]) == 1
    assert "exists" in capsys.readouterr().out


def test_vendor_quotes_refused_above_the_cost_limit(monkeypatch, capsys, config, week):
    vendor = QuoteVendor(quote_sample(week), cost=50.0)
    monkeypatch.setitem(sys.modules, CLIENT_PACKAGE, vendor.module())
    monkeypatch.setenv(KEY_ENV, FAKE_KEY)
    assert main(["--config", str(config), "--as-of", "2019-03-16T22:00:00+00:00", "spreads",
                 "measure", "--symbol", SYMBOL, "--days", "13"]) == 1
    assert "max_cost_usd" in capsys.readouterr().err
    assert "get_range" not in [n for n, _ in vendor.calls]
    assert not (config / "spreads" / f"{SYMBOL}.toml").exists()
