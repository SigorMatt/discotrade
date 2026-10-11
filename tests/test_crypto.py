"""The crypto adapter (DESIGN 5.5, 5.1; decision 2026-10-12 12; I-9, I-11).

Driven by ``httpx.MockTransport`` only: no request leaves the process. The mock
endpoint serves an invented hourly series in the shape the adapter documents
(that the real endpoint has that shape is NOT PROVEN). The instrument is the
fixture record ``CRYA`` (track ``test_crypto``).
"""

import shutil
from datetime import UTC, datetime, timedelta

import httpx
import numpy as np
import pandas as pd
import pytest

import discotrade.sources as sources
from discotrade.bars.store import BarStore
from discotrade.cli import REPO_ROOT, main
from discotrade.config import ConfigError, load_instrument, load_track_config
from discotrade.sources import SourceError, source_for
from discotrade.sources.base import BAR_COLUMNS
from discotrade.sources.crypto import LIMIT, CryptoSource

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
HOUR = 3600
HOUR_MS = HOUR * 1000
ORIGIN = datetime(2024, 1, 1, tzinfo=UTC)
#: The mock endpoint's series: 60 days of hourly bars from ORIGIN.
N_BARS = 60 * 24


def crya():
    return load_instrument(FIXTURE_CONFIG / "instruments" / "CRYA.toml")


def series_row(k):
    t = int(ORIGIN.timestamp() * 1000) + k * HOUR_MS
    rng = np.random.default_rng([7, k])                   # fixed seed per bar
    o, c = 40000 + rng.normal(0, 50, 2)
    return [t, f"{o:.2f}", f"{max(o, c) + 5:.2f}", f"{min(o, c) - 5:.2f}", f"{c:.2f}",
            f"{abs(rng.normal(10, 2)):.5f}", t + HOUR_MS - 1, "0", 100, "0", "0", "0"]


class Endpoint:
    """The mock endpoint: answers like the documented shape and records each request."""

    def __init__(self, rows=None, reply=None):
        self.rows = rows if rows is not None else [series_row(k) for k in range(N_BARS)]
        self.reply = reply
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if self.reply is not None:
            return self.reply(request)
        q = request.url.params
        lo, hi, limit = int(q["startTime"]), int(q["endTime"]), int(q["limit"])
        rows = [r for r in self.rows if lo <= r[0] <= hi][:limit]
        return httpx.Response(200, json=rows)

    def source(self):
        return CryptoSource(HOUR, transport=httpx.MockTransport(self))


def at(k):
    return ORIGIN + timedelta(hours=k)


# --- configuration and selection ------------------------------------------------------


def test_the_crypto_fixture_record_and_track_load():
    inst = crya()
    assert inst.test_only and inst.source.adapter == "crypto"
    assert inst.source.get("base_url").startswith("https://")
    assert inst.source.get("market")
    tc = load_track_config(FIXTURE_CONFIG, "test_crypto")
    assert [i.symbol for i in tc.instruments] == ["CRYA"]


def test_a_crypto_record_without_its_endpoint_is_refused(tmp_path):
    text = (FIXTURE_CONFIG / "instruments" / "CRYA.toml").read_text()
    for key in ("base_url", "market"):
        line = next(ln for ln in text.splitlines() if ln.startswith(f"{key} = "))
        path = tmp_path / key / "CRYA.toml"
        path.parent.mkdir()
        path.write_text(text.replace(line + "\n", ""))
        with pytest.raises(ConfigError, match=f"source.{key}"):
            load_instrument(path)


def test_source_for_gives_the_crypto_adapter_available_until_now():
    source = source_for("crypto", {}, HOUR)
    assert isinstance(source, CryptoSource) and source.name == "crypto"
    now = datetime(2024, 1, 5, 10, 30, tzinfo=UTC)
    assert source.available_until(now) == now


def test_a_bar_length_other_than_an_hour_is_refused():
    with pytest.raises(ValueError, match="hourly"):
        CryptoSource(60)


# --- fetch ------------------------------------------------------------------------------------


def test_fetch_returns_closed_hourly_bars_in_the_5_1_schema():
    endpoint = Endpoint()
    now = at(50) + timedelta(minutes=30)                 # bar 50 is still open
    bars = endpoint.source().fetch(crya(), at(10), now)
    assert tuple(bars.columns) == BAR_COLUMNS
    assert str(bars["ts"].dtype) == "datetime64[ns, UTC]"
    for col in ("open", "high", "low", "close", "volume"):
        assert bars[col].dtype == "float64", col
    assert bars["ts"].tolist() == [pd.Timestamp(at(k)) for k in range(10, 50)]
    assert (bars["ts"] + pd.Timedelta(hours=1) <= pd.Timestamp(now)).all()
    assert set(bars["contract"]) == {"CRYA"}
    assert bars["close"].iloc[0] == float(series_row(10)[4])
    assert bars["volume"].iloc[-1] == float(series_row(49)[5])


def test_the_request_names_the_configured_endpoint_and_market():
    endpoint = Endpoint()
    endpoint.source().fetch(crya(), at(0), at(5))
    (request,) = endpoint.requests
    inst = crya()
    assert str(request.url.copy_with(query=None)) == inst.source.get("base_url")
    q = request.url.params
    assert q["symbol"] == inst.source.get("market") and q["interval"] == "1h"
    assert int(q["startTime"]) == int(at(0).timestamp() * 1000)
    assert int(q["endTime"]) == int(at(5).timestamp() * 1000) - 1


def test_a_start_between_bar_times_begins_at_the_next_bar():
    bars = Endpoint().source().fetch(crya(), at(3) + timedelta(minutes=1), at(6))
    assert bars["ts"].tolist() == [pd.Timestamp(at(4)), pd.Timestamp(at(5))]


def test_a_long_range_is_read_page_by_page():
    endpoint = Endpoint()
    bars = endpoint.source().fetch(crya(), at(0), at(N_BARS))
    assert len(bars) == N_BARS > LIMIT
    assert len(endpoint.requests) == 2
    assert bars["ts"].is_monotonic_increasing and not bars["ts"].duplicated().any()


def test_an_empty_reply_gives_no_bars():
    bars = Endpoint(rows=[]).source().fetch(crya(), at(0), at(10))
    assert tuple(bars.columns) == BAR_COLUMNS and bars.empty


def test_fetch_contract_is_the_series_and_refuses_another_contract():
    endpoint = Endpoint()
    pd.testing.assert_frame_equal(endpoint.source().fetch_contract(crya(), "CRYA", at(0), at(9)),
                                  endpoint.source().fetch(crya(), at(0), at(9)))
    with pytest.raises(ValueError, match="does not roll"):
        endpoint.source().fetch_contract(crya(), "CRYA-2024-03", at(0), at(9))


# --- malformed replies ------------------------------------------------------------------------


def good(k=0):
    return series_row(k)


@pytest.mark.parametrize(("reply", "match"), [
    (lambda r: httpx.Response(500, json=[]), "status 500"),
    (lambda r: httpx.Response(200, content=b"<html>"), "not JSON"),
    (lambda r: httpx.Response(200, json={"code": -1121, "msg": "Invalid symbol."}),
     "not an array"),
    (lambda r: httpx.Response(200, json=[[good()[0], "1", "2", "0.5"]]), "six items"),
    (lambda r: httpx.Response(200, json=[[str(good()[0]), *good()[1:]]]), "open time"),
    (lambda r: httpx.Response(200, json=[[good()[0] + 1, *good()[1:]]]), "open time"),
    (lambda r: httpx.Response(200, json=[[good()[0], "abc", *good()[2:]]]), "not a number"),
    (lambda r: httpx.Response(200, json=[[good()[0], None, *good()[2:]]]), "not a number"),
    (lambda r: httpx.Response(200, json=[good(1), good(0)]), "out of order"),
    (lambda r: httpx.Response(200, json=[good(0), good(0)]), "out of order"),
    (lambda r: httpx.Response(200, json=["row"]), "six items"),
])
def test_a_malformed_reply_is_refused(reply, match):
    with pytest.raises(SourceError, match=match):
        Endpoint(reply=reply).source().fetch(crya(), at(0), at(10))


def test_a_reply_that_does_not_move_forward_is_refused():
    full = [good(k) for k in range(LIMIT)]
    with pytest.raises(SourceError, match="move forward"):
        Endpoint(reply=lambda r: httpx.Response(200, json=full)).source().fetch(
            crya(), at(0), at(N_BARS))


def test_an_unreachable_endpoint_is_refused():
    def reply(request):
        raise httpx.ConnectError("no route", request=request)
    with pytest.raises(SourceError, match="could not be reached"):
        Endpoint(reply=reply).source().fetch(crya(), at(0), at(10))


# --- bars fetch on the crypto fixture track ---------------------------------------------------


def test_bars_fetch_on_the_crypto_track_writes_closed_bars(tmp_path, monkeypatch, capsys):
    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    endpoint = Endpoint()
    real = sources.source_for

    def source_for_mock(adapter, calendars, bar_seconds):
        if adapter == "crypto":
            return endpoint.source()
        return real(adapter, calendars, bar_seconds)
    monkeypatch.setattr(sources, "source_for", source_for_mock)
    state = tmp_path / "state"
    now = at(30 * 24) + timedelta(minutes=20)
    assert main(["--state", str(state), "--config", str(config), "--track", "test_crypto",
                 "--as-of", now.isoformat(), "bars", "fetch"]) == 0
    assert "fetched CRYA: 720 bars written" in capsys.readouterr().out
    stored = BarStore(state, "test_crypto", HOUR).read_range("CRYA", ORIGIN, now)
    assert stored["ts"].tolist() == [pd.Timestamp(at(k)) for k in range(720)]
    assert set(stored["contract"]) == {"CRYA"}
    assert stored["close"].iloc[0] == float(series_row(0)[4])
