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
    """A lifecycle row; one of the four reasons of decision 2026-10-14 87
    carries its two figures, required on append (decision 93)."""
    row = {"date": date(2019, 6, 10 + k).isoformat(), "id": f"a{k:012x}", "from": "live",
           "to": "dormant", "reason": reason}
    if reason in ("admitted", "displaced", "dormant", "returned"):
        row.update({"adjusted": -0.5 + k, "plain": 0.25 * k})
    return row


def trial_row(day="2019-06-10"):
    """A trial row with every key of decision 62 and the two figures of
    decision 86 (d), required on append (decision 93)."""
    row = {k: None for k in ledger.KEYS[TRIALS]}
    row.update({"date": day, "adjusted_t": None, "adjusted_w": None})
    return row


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


@pytest.mark.parametrize("reason", ["admitted", "displaced", "dormant", "returned"])
def test_a_lifecycle_row_of_four_reasons_must_carry_adjusted_and_plain(tmp_path, reason):
    # Decisions 2026-10-14 87 and 93: both keys, each a number or null; none,
    # or one alone, refused on append.
    row = {**lifecycle_row(0, reason), "adjusted": -1.25, "plain": None}
    assert ledger.append(tmp_path, TRACK, LIFECYCLE, [row]) == [row]
    assert ledger.read(tmp_path, TRACK, LIFECYCLE) == [row]
    text = ledger.ledger_path(tmp_path, TRACK, LIFECYCLE).read_text(encoding="utf-8")
    assert '"adjusted":-1.25' in text and '"plain":null' in text
    full = lifecycle_row(1, reason)
    for drop in (("adjusted",), ("plain",), ("adjusted", "plain")):
        short = {k: v for k, v in full.items() if k not in drop}
        with pytest.raises(LedgerError, match="keys"):
            ledger.append(tmp_path, TRACK, LIFECYCLE, [short])
    assert ledger.read(tmp_path, TRACK, LIFECYCLE) == [row]


@pytest.mark.parametrize("reason", ["retired_dormant", "failure: boom"])
def test_a_lifecycle_row_of_another_reason_carries_neither_figure(tmp_path, reason):
    row = {**lifecycle_row(0, reason), "adjusted": 1.0, "plain": 1.0}
    with pytest.raises(LedgerError, match="keys"):
        ledger.append(tmp_path, TRACK, LIFECYCLE, [row])
    for half in ({**lifecycle_row(0, reason), "adjusted": 1.0},
                 {**lifecycle_row(0, reason), "plain": 1.0}):
        with pytest.raises(LedgerError, match="keys"):
            ledger.append(tmp_path, TRACK, LIFECYCLE, [half])
    assert not (tmp_path / "ledger").exists()
    assert ledger.append(tmp_path, TRACK, LIFECYCLE, [lifecycle_row(0, reason)]) == \
        [lifecycle_row(0, reason)]


def test_a_trial_row_must_carry_adjusted_t_and_adjusted_w(tmp_path):
    # Decisions 2026-10-14 86 (d) and 93: the trial row's adjusted figures,
    # beside metrics_t and metrics_w; adjusted_w null for a candidate without
    # W; none, or one alone, refused on append.
    assert ledger.TRIAL_FIGURES == ("adjusted_t", "adjusted_w")
    figures = {"sharpe": 0.5, "sharpe_2x": None, "total_return": 0.01,
               "total_return_2x": 0.005, "avg_position": {"SYNA": 0.25}}
    row = {**trial_row(), "adjusted_t": figures}
    assert ledger.append(tmp_path, TRACK, TRIALS, [row]) == [row]
    assert ledger.read(tmp_path, TRACK, TRIALS) == [row]
    full = {**trial_row("2019-06-11"), "adjusted_t": figures}
    for drop in (("adjusted_t",), ("adjusted_w",), ("adjusted_t", "adjusted_w")):
        short = {k: v for k, v in full.items() if k not in drop}
        with pytest.raises(LedgerError, match="keys"):
            ledger.append(tmp_path, TRACK, TRIALS, [short])
    assert ledger.read(tmp_path, TRACK, TRIALS) == [row]


@pytest.mark.parametrize("name, old, new", [
    (LIFECYCLE,
     {"date": "2019-06-07", "id": "a000000000009", "from": "live", "to": "dormant",
      "reason": "dormant"},
     lifecycle_row(0)),
    (TRIALS, {**{k: None for k in ledger.KEYS[TRIALS]}, "date": "2019-06-07"}, trial_row()),
])
def test_a_ledger_holding_a_line_written_before_the_figures_is_still_appended_to(
        tmp_path, name, old, new):
    # Decision 2026-10-14 93 with I-5: the check runs on append only; a line
    # already on disk without the figures is neither read against it nor
    # rewritten.
    path = ledger.ledger_path(tmp_path, TRACK, name)
    path.parent.mkdir(parents=True)
    before = (ledger.line(old) + "\n").encode("utf-8")
    path.write_bytes(before)
    assert ledger.append(tmp_path, TRACK, name, [new]) == [new]
    data = path.read_bytes()
    assert data.startswith(before) and data == before + (ledger.line(new) + "\n").encode()
    assert ledger.read(tmp_path, TRACK, name) == [old, new]


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
    trial = trial_row()
    trial.update({"date": date(2019, 6, 10), "metrics_t": {"sharpe": float("nan"),
                                                           "trades": 3, "x": float("inf")}})
    ledger.append(tmp_path, TRACK, LIFECYCLE, [row])
    ledger.append(tmp_path, TRACK, TRIALS, [trial])
    assert ledger.read(tmp_path, TRACK, LIFECYCLE)[0]["date"] == "2019-06-10"
    held = ledger.read(tmp_path, TRACK, TRIALS)[0]
    assert held["metrics_t"] == {"sharpe": None, "trades": 3, "x": None}
    assert held["grid"] is None and held["date"] == "2019-06-10"
