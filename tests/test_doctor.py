"""``discotrade doctor`` in step S0.2 (DESIGN 19.3; decision 2026-10-12 15; I-11, I-13).

Offline only: without the key ``--live vendor`` refuses, exits 1 and makes no
request; plain ``doctor`` and every check name not built in this step are usage
errors naming step S5.1. Its live behaviour is run here against the fake client
of ``tests/fakes/`` only, which proves the printing and the arithmetic, not the
real service (that is live check L1 itself).
"""

from datetime import UTC, datetime

import pytest
from fakes.vendor_world import FAKE_KEY, SYMBOL, TRACK, install, make_config, make_vendor

from discotrade.cli import main
from discotrade.sources.vendor import KEY_ENV

AS_OF = "2019-04-01T05:00:00+00:00"


@pytest.fixture
def config(tmp_path):
    return make_config(tmp_path / "config")


def doctor(*args, config=None, track=None):
    argv = ["--as-of", AS_OF]
    if config is not None:
        argv += ["--config", str(config)]
    if track is not None:
        argv += ["--track", track]
    return main([*argv, "doctor", *args])


@pytest.mark.parametrize("key", [None, ""])
def test_live_vendor_without_the_key_refuses_exit_1_and_makes_no_request(monkeypatch, capsys,
                                                                         config, key):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=key)
    assert doctor("--live", "vendor", config=config, track=TRACK) == 1
    err = capsys.readouterr().err
    assert KEY_ENV in err and "no request was made" in err
    assert vendor.calls == [] and vendor.keys == []


def test_live_vendor_without_the_key_refuses_on_the_repository_config(monkeypatch, capsys):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=None)
    assert doctor("--live", "vendor") == 1
    assert KEY_ENV in capsys.readouterr().err
    assert vendor.calls == []


def test_plain_doctor_is_a_usage_error_naming_s5_1(capsys):
    assert doctor() == 2
    assert "S5.1" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["workers", "coordinator", "sandbox", "issues", "costs",
                                  "planted", "nonsense"])
def test_another_check_is_a_usage_error_naming_s5_1(monkeypatch, capsys, name):
    monkeypatch.delenv(KEY_ENV, raising=False)
    assert doctor("--live", name) == 2
    assert "S5.1" in capsys.readouterr().err


def test_live_vendor_with_the_fake_client_reports_each_l1_item(monkeypatch, capsys, config):
    vendor = make_vendor(dataset_end=datetime(2019, 3, 31, 20, tzinfo=UTC))
    install(monkeypatch, vendor)
    assert doctor("--live", "vendor", config=config, track=TRACK) == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith(f"{SYMBOL}: ")]
    assert any("cost estimate for the full history 2019-01-07" in ln and "0.25 USD" in ln
               for ln in lines)
    assert any("delay 9:00:00, within the embargo" in ln for ln in lines)
    assert any("contract resolved" in ln and "SYNA-2019-06" in ln for ln in lines)
    assert any("gap fraction" in ln for ln in lines)
    assert "doctor --live vendor: ok" in out
    assert FAKE_KEY not in out


def test_live_vendor_reports_a_failing_vendor_without_the_key(monkeypatch, capsys, config):
    vendor = make_vendor()
    vendor.fail_with = f"denied for {FAKE_KEY}"
    install(monkeypatch, vendor)
    assert doctor("--live", "vendor", config=config, track=TRACK) == 1
    captured = capsys.readouterr()
    assert f"{SYMBOL}: FAIL" in captured.out and "<redacted>" in captured.out
    assert FAKE_KEY not in captured.out + captured.err
