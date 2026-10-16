"""The synthetic source's series kept for the life of the process (decision 121
of meta/decisions/decisions-2026-10-16-m15.md, finding D-013; DESIGN 5.5, 17.1;
I-6).

Every instrument is a fixture record under ``tests/fixtures/config/`` (the gate
track ``test_synth``, SYNA..SYND, seeds 101..104; SYNL, seed 105), or a copy of
it under the test's temporary directory. Every date and seed is written here.
Every state directory is a pytest ``tmp_path``; time comes only from
``--as-of``. ``tests/conftest.py`` clears the cache before every test.
"""

import shutil
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_instrument
from discotrade.sources import synth
from discotrade.sources.synth import SynthSource

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
HOUR = 3600
TRACK = "test_synth"
TRUSTED_FROM = datetime(2019, 1, 7, tzinfo=UTC)     # every fixture's trusted_from
#: SYNA rolls on 2019-03-14; the span crosses it.
FIRST_FETCH = datetime(2019, 3, 7, 21, 30, tzinfo=UTC)
LAST_FETCH = datetime(2019, 3, 21, 21, 30, tzinfo=UTC)
END = datetime(2019, 4, 1, tzinfo=UTC)


def _gate_config(tmp_path):
    """tests/fixtures/config/ copied with thresholds_gate.toml as its thresholds."""
    config = tmp_path / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copy(FIXTURE_CONFIG / "thresholds_gate.toml", config / "thresholds.toml")
    return config


def _fetch_at(state, config, instant):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", instant.isoformat(), "bars", "fetch"])


def _stored(state):
    """Every bar file, the index and every roll record of the track, with its bytes."""
    out = {}
    for sub in ("bars", "rolls"):
        root = state / sub / TRACK
        out.update({f"{sub}/{p.relative_to(root).as_posix()}": p.read_bytes()
                    for p in sorted(root.rglob("*")) if p.is_file()})
    return out


def _origins(monkeypatch):
    """Record the start of every expected-bar list the source builds."""
    starts = []
    real = synth.expected_bars

    def counted(cal, start, end, bar_seconds):
        starts.append(start)
        return real(cal, start, end, bar_seconds)
    monkeypatch.setattr(synth, "expected_bars", counted)
    return starts


def test_a_span_fetched_day_by_day_with_the_cache_stores_what_one_fetch_without_it_stores(
        tmp_path, monkeypatch, capsys):
    config = _gate_config(tmp_path)
    daily, once = tmp_path / "daily", tmp_path / "once"
    starts = _origins(monkeypatch)
    instant, count = FIRST_FETCH, 0
    while instant <= LAST_FETCH:
        # Each `bars fetch` builds its own source; the series lives on in the process.
        assert _fetch_at(daily, config, instant) == 0, instant
        if count == 0:
            assert starts and all(s == TRUSTED_FROM for s in starts)
            starts.clear()
        instant += timedelta(days=1)
        count += 1
    assert count == 15
    # After the first fetch no series was built again from trusted_from.
    assert starts and TRUSTED_FROM not in starts
    synth.clear_cache()
    assert _fetch_at(once, config, LAST_FETCH) == 0
    capsys.readouterr()
    got, want = _stored(daily), _stored(once)
    for symbol in ("SYNA", "SYNB", "SYNC", "SYND"):
        assert {f"bars/{symbol}/2019-01.parquet", f"bars/{symbol}/2019-03.parquet"} <= set(want)
    assert "bars/index.json" in want and "rolls/SYNA.jsonl" in want
    assert "SYNA-2019-06" in want["rolls/SYNA.jsonl"].decode()
    assert sorted(got) == sorted(want)
    for name in want:
        assert got[name] == want[name], name


def test_a_changed_seed_in_a_copied_configuration_gives_another_series_in_the_same_process(
        tmp_path):
    config = _gate_config(tmp_path)
    calendars = {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}
    path = config / "instruments" / "SYNL.toml"
    before = load_instrument(path)
    assert before.source.get("seed") == 105
    first = SynthSource(calendars, HOUR).fetch(before, TRUSTED_FROM, END)
    text = path.read_text(encoding="utf-8")
    assert text.count("seed = 105\n") == 1
    path.write_text(text.replace("seed = 105\n", "seed = 205\n"), encoding="utf-8")
    after = load_instrument(path)
    assert after.source.get("seed") == 205
    second = SynthSource(calendars, HOUR).fetch(after, TRUSTED_FROM, END)
    assert len(first) > 1000
    assert not first["close"].equals(second["close"])
    synth.clear_cache()
    fresh = SynthSource(calendars, HOUR).fetch(after, TRUSTED_FROM, END)
    pd.testing.assert_frame_equal(second, fresh, check_exact=True)
    # The first record is served again from its own settings.
    pd.testing.assert_frame_equal(SynthSource(calendars, HOUR).fetch(before, TRUSTED_FROM, END),
                                  first, check_exact=True)


def test_a_changed_trusted_from_in_a_copied_configuration_gives_another_series(tmp_path):
    config = _gate_config(tmp_path)
    calendars = {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}
    path = config / "instruments" / "SYNL.toml"
    before = load_instrument(path)
    first = SynthSource(calendars, HOUR).fetch(before, TRUSTED_FROM, END)
    text = path.read_text(encoding="utf-8")
    assert text.count('trusted_from = "2019-01-07"\n') == 1
    path.write_text(text.replace('trusted_from = "2019-01-07"\n', 'trusted_from = "2019-01-14"\n'),
                    encoding="utf-8")
    after = load_instrument(path)
    assert after.trusted_from == date(2019, 1, 14)
    second = SynthSource(calendars, HOUR).fetch(after, TRUSTED_FROM, END)
    assert second["ts"].min() >= pd.Timestamp("2019-01-14", tz="UTC")
    synth.clear_cache()
    pd.testing.assert_frame_equal(SynthSource(calendars, HOUR).fetch(after, TRUSTED_FROM, END),
                                  second, check_exact=True)
    assert not first[first["ts"] >= second["ts"].min()].reset_index(drop=True)["close"].equals(
        second["close"])


def test_an_equal_record_on_a_new_source_is_served_without_building_the_series_again(
        tmp_path, monkeypatch):
    config = _gate_config(tmp_path)
    calendars = {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}
    rec = load_instrument(config / "instruments" / "SYNA.toml")
    starts = _origins(monkeypatch)
    want = SynthSource(calendars, HOUR).fetch(rec, TRUSTED_FROM, END)
    assert starts == [TRUSTED_FROM]
    again = load_instrument(config / "instruments" / "SYNA.toml")
    got = SynthSource(calendars, HOUR).fetch(again, TRUSTED_FROM, END)
    assert starts == [TRUSTED_FROM]
    pd.testing.assert_frame_equal(got, want, check_exact=True)


#: The closure the calendar test adds to the copied ``synth_week`` record, in
#: America/New_York time: 2019-02-12 09:00 to 2019-02-13 12:00, that is
#: 2019-02-12 14:00 to 2019-02-13 17:00 UTC, inside [TRUSTED_FROM, END).
ADDED_CLOSURE = ('\n[[closure]]\nstart = "2019-02-12 09:00"\nend = "2019-02-13 12:00"\n'
                 'note = "closure added by the cache test"\n')
CLOSED_FROM = datetime(2019, 2, 12, 14, tzinfo=UTC)
CLOSED_UNTIL = datetime(2019, 2, 13, 17, tzinfo=UTC)
#: The other bar length: 30 minutes. Every open, close, break and closure time
#: of ``synth_week`` falls on a half hour, so its bars tile the open time.
HALF_HOUR = 1800


def _calendars(config):
    return {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}


def _inside(frame, lo, hi):
    return frame[(frame["ts"] >= pd.Timestamp(lo)) & (frame["ts"] < pd.Timestamp(hi))]


def test_a_changed_calendar_record_in_a_copied_configuration_gives_another_series(tmp_path):
    config = _gate_config(tmp_path)
    rec = load_instrument(config / "instruments" / "SYNL.toml")
    assert rec.calendar == "synth_week" and rec.trusted_from == date(2019, 1, 7)
    before = _calendars(config)
    first = SynthSource(before, HOUR).fetch(rec, TRUSTED_FROM, END)
    # The span 2019-02-12 14:00 to 2019-02-13 17:00 UTC is 27 hours of open
    # market under the copied record (a Tuesday 09:00 to a Wednesday 12:00 New
    # York, with the 17:00-18:00 break), less any dropped bars.
    assert len(_inside(first, CLOSED_FROM, CLOSED_UNTIL)) > 20
    path = config / "calendars" / "synth_week.toml"
    path.write_text(path.read_text(encoding="utf-8") + ADDED_CLOSURE, encoding="utf-8")
    after = _calendars(config)
    assert after["synth_week"] != before["synth_week"]
    assert len(after["synth_week"].closures) == len(before["synth_week"].closures) + 1
    second = SynthSource(after, HOUR).fetch(rec, TRUSTED_FROM, END)
    # Differs from the first: no bar in the closure, and so fewer bars.
    assert len(_inside(second, CLOSED_FROM, CLOSED_UNTIL)) == 0
    assert len(second) < len(first)
    assert not second["ts"].equals(first["ts"])
    # Equals the series generated for the changed record with the cache cleared.
    synth.clear_cache()
    fresh = SynthSource(after, HOUR).fetch(rec, TRUSTED_FROM, END)
    pd.testing.assert_frame_equal(second, fresh, check_exact=True)


def test_the_same_instrument_at_another_bar_length_gives_another_series(tmp_path):
    config = _gate_config(tmp_path)
    calendars = _calendars(config)
    rec = load_instrument(config / "instruments" / "SYNL.toml")
    first = SynthSource(calendars, HOUR).fetch(rec, TRUSTED_FROM, END)
    assert len(first) > 1000
    assert set(first["ts"].dt.minute) == {0}
    second = SynthSource(calendars, HALF_HOUR).fetch(rec, TRUSTED_FROM, END)
    # Differs from the first: half-hour bars, so bars opening at :30 and more bars.
    assert set(second["ts"].dt.minute) == {0, 30}
    assert len(second) > len(first)
    # Equals the series generated at that bar length with the cache cleared.
    synth.clear_cache()
    fresh = SynthSource(calendars, HALF_HOUR).fetch(rec, TRUSTED_FROM, END)
    pd.testing.assert_frame_equal(second, fresh, check_exact=True)
