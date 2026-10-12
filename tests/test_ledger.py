"""The three ledgers (DESIGN 10.2; decisions 2026-10-12 4, 52, 62; I-5, I-6).

Every ledger is written under a pytest temporary directory. No random draw,
no clock, no network.
"""

import json
import os
from datetime import date

import pytest

from discotrade import ledger
from discotrade.ledger import CALLS, LIFECYCLE, TRIALS, LedgerError

TRACK = "test_mixed"


def lifecycle_row(k, reason="dormant"):
    return {"date": date(2019, 6, 10 + k).isoformat(), "id": f"a{k:012x}", "from": "live",
            "to": "dormant", "reason": reason}


def call_row(k, outcome="trial"):
    return {"call": f"c{k}", "date": "2019-06-10", "cell": "trend/short", "model": "m",
            "attempt": 1, "tokens_in": 10 + k, "tokens_out": 20, "outcome": outcome,
            "response": f"responses/{TRACK}/2019-06-10/c{k}.json"}


def test_each_row_is_one_sorted_key_json_object_per_line(tmp_path):
    rows = [lifecycle_row(0), lifecycle_row(1)]
    assert ledger.append(tmp_path, TRACK, LIFECYCLE, rows) == rows
    path = tmp_path / "ledger" / TRACK / "lifecycle.jsonl"
    lines = path.read_text(encoding="utf-8").split("\n")
    assert lines[-1] == "" and len(lines) == 3
    for text, row in zip(lines[:-1], rows, strict=True):
        assert json.loads(text) == row
        assert text == json.dumps(row, sort_keys=True, separators=(",", ":"))
        assert list(json.loads(text)) == sorted(row)
    assert ledger.read(tmp_path, TRACK, LIFECYCLE) == rows


def test_earlier_lines_stay_byte_identical_and_a_present_line_is_not_appended(tmp_path):
    ledger.append(tmp_path, TRACK, LIFECYCLE, [lifecycle_row(0)])
    path = ledger.ledger_path(tmp_path, TRACK, LIFECYCLE)
    first = path.read_bytes()
    # A present line, a new one, and the new one again in the same call.
    appended = ledger.append(tmp_path, TRACK, LIFECYCLE,
                             [lifecycle_row(0), lifecycle_row(1), lifecycle_row(1)])
    assert appended == [lifecycle_row(1)]
    data = path.read_bytes()
    assert data.startswith(first) and data.count(b"\n") == 2
    # Nothing new: nothing written, the file untouched.
    stamp = path.stat().st_mtime_ns
    assert ledger.append(tmp_path, TRACK, LIFECYCLE, [lifecycle_row(0), lifecycle_row(1)]) == []
    assert path.read_bytes() == data and path.stat().st_mtime_ns == stamp


def test_an_append_is_atomic(tmp_path, monkeypatch):
    ledger.append(tmp_path, TRACK, LIFECYCLE, [lifecycle_row(0)])
    path = ledger.ledger_path(tmp_path, TRACK, LIFECYCLE)
    before = path.read_bytes()

    def crash(src, dst):
        raise OSError("crash before the rename")

    monkeypatch.setattr(os, "replace", crash)
    with pytest.raises(OSError, match="crash"):
        ledger.append(tmp_path, TRACK, LIFECYCLE, [lifecycle_row(1)])
    assert path.read_bytes() == before        # the old file, whole


def test_a_torn_last_line_is_refused(tmp_path):
    ledger.append(tmp_path, TRACK, LIFECYCLE, [lifecycle_row(0)])
    path = ledger.ledger_path(tmp_path, TRACK, LIFECYCLE)
    torn = path.read_bytes() + b'{"date":"2019-06-11","id"'
    path.write_bytes(torn)
    with pytest.raises(LedgerError, match="torn"):
        ledger.append(tmp_path, TRACK, LIFECYCLE, [lifecycle_row(1)])
    with pytest.raises(LedgerError, match="torn"):
        ledger.read(tmp_path, TRACK, LIFECYCLE)
    assert path.read_bytes() == torn


def test_into_a_staging_directory_writes_only_there(tmp_path):
    state, staging = tmp_path / "state", tmp_path / "staging"
    ledger.append(state, TRACK, LIFECYCLE, [lifecycle_row(0)])
    held = ledger.ledger_path(state, TRACK, LIFECYCLE).read_bytes()
    ledger.append(state, TRACK, LIFECYCLE, [lifecycle_row(0), lifecycle_row(1)], into=staging)
    ledger.append(state, TRACK, LIFECYCLE, [lifecycle_row(2)], into=staging)
    assert ledger.ledger_path(state, TRACK, LIFECYCLE).read_bytes() == held
    staged = ledger.ledger_path(staging, TRACK, LIFECYCLE).read_bytes()
    assert staged.startswith(held)
    assert ledger.read(state, TRACK, LIFECYCLE, into=staging) == \
        [lifecycle_row(0), lifecycle_row(1), lifecycle_row(2)]
    assert not ledger.ledger_path(staging, TRACK, TRIALS).exists()


def test_a_row_must_hold_exactly_its_ledgers_keys(tmp_path):
    row = lifecycle_row(0)
    with pytest.raises(LedgerError, match="keys"):
        ledger.append(tmp_path, TRACK, LIFECYCLE, [{**row, "extra": 1}])
    del row["reason"]
    with pytest.raises(LedgerError, match="keys"):
        ledger.append(tmp_path, TRACK, LIFECYCLE, [row])
    with pytest.raises(LedgerError, match="keys"):
        ledger.append(tmp_path, TRACK, TRIALS, [lifecycle_row(0)])
    assert not (tmp_path / "ledger").exists()


def test_the_keys_of_each_ledger(tmp_path):
    assert set(ledger.KEYS[TRIALS]) == {
        "date", "id", "cell", "model_id", "model_version", "cutoff", "code_sha256",
        "profile_version", "cost_model", "config_hash", "grid", "params", "metrics_w",
        "metrics_t", "admitted", "reason", "displaced"}
    assert set(ledger.KEYS[LIFECYCLE]) == {"date", "id", "from", "to", "reason"}
    assert set(ledger.KEYS[CALLS]) == {"call", "date", "cell", "model", "attempt",
                                       "tokens_in", "tokens_out", "outcome", "response"}


def test_the_call_writer_takes_the_outcomes_of_10_2(tmp_path):
    rows = [call_row(0), call_row(1, "duplicate"), call_row(2, "invalid:static"),
            call_row(3, "provider_error"), call_row(4, "budget")]
    assert ledger.append_calls(tmp_path, TRACK, rows) == rows
    assert ledger.read(tmp_path, TRACK, CALLS) == rows
    for bad in ("invalid:", "ok", None):
        with pytest.raises(LedgerError, match="outcome"):
            ledger.append_calls(tmp_path, TRACK, [call_row(9, bad)])
    assert ledger.read(tmp_path, TRACK, CALLS) == rows


def test_a_float_that_is_not_finite_is_written_as_null_and_dates_as_iso(tmp_path):
    row = {**lifecycle_row(0), "date": date(2019, 6, 10)}
    trial = {k: None for k in ledger.KEYS[TRIALS]}
    trial.update({"date": date(2019, 6, 10), "metrics_t": {"sharpe": float("nan"),
                                                           "trades": 3, "x": float("inf")}})
    ledger.append(tmp_path, TRACK, LIFECYCLE, [row])
    ledger.append(tmp_path, TRACK, TRIALS, [trial])
    assert ledger.read(tmp_path, TRACK, LIFECYCLE)[0]["date"] == "2019-06-10"
    held = ledger.read(tmp_path, TRACK, TRIALS)[0]
    assert held["metrics_t"] == {"sharpe": None, "trades": 3, "x": None}
    assert held["grid"] is None and held["date"] == "2019-06-10"
