"""Mission 10 U2: the code made faster computes what its parent computed (O-3;
decision 2026-10-14 80 (a); DESIGN 7, 9.2, 9.3, 10.1, 16.1).

Each piece of code changed is pinned against the parent's way of computing it
(commit 4bf827d), on cases written here:

- ``state.content_text`` (built a column at a time) against
  ``_parent_content_text``, the parent's row-at-a-time code copied verbatim,
  byte for byte, on a frame written here with every kind of field and on the
  journal rows the tests below compute.
- ``backtest.score`` (shared columns typed once, cost columns as arrays) and
  ``SimExecutor.execute`` (each fill bar's Timestamp made once): the per-bar
  rows of five subjects on a ``SYNA`` window holding its roll of 2019-06-14,
  one carried in from a start, hashed by ``_parent_content_text`` and by the
  rows' dtypes, equal to the digests the parent gave (written here); each
  fill's bar is the next stored bar after its decision bar.
- ``journal._columns`` / ``_rows`` / ``_joined`` (the controls' rows as one
  frame, float columns read in one block): the journal of six days of
  ``test_mixed`` with one approach and every control, across the controls'
  redraw on 2019-07-01, hashed by ``_parent_content_text``, equal to the
  digests the parent gave and to the content hashes the index stores; and
  ``span_rows`` / ``control_span_rows`` over the same days.

``bars fetch`` runs in-process on ``test_mixed`` (production thresholds) into
a pytest temporary state at ``AS_OF``; time comes only from ``--as-of``. The
synthetic sources' seeds are their fixture records' (``SEEDS``); the one other
random draw here has the fixed seed ``RNG_SEED``.
"""

import hashlib
import shutil
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from discotrade import controls, journal, state
from discotrade.backtest import read_window, score
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange
from discotrade.executor import Market, Order, SimExecutor
from discotrade.state import write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-07-04T00:00:00+00:00"
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
RNG_SEED = 20191001
ADMITTED = date(2019, 6, 26)
#: Six journal days; the controls' first draw is on the first, a redraw on 2019-07-01.
DAYS = tuple(date(2019, 6, 27) + timedelta(days=k) for k in range(6))
ROLL_WINDOW = DateRange(date(2019, 6, 10), date(2019, 6, 19))


# ------------------------------------------------------- the parent's content text

def _parent_field(value: Any) -> str:
    if value is None or value is pd.NaT:
        return ""
    if isinstance(value, bool | np.bool_):
        return "true" if value else "false"
    if isinstance(value, float | np.floating):
        return f"{float(value):.17g}"  # identical to "%.17g" % value
    if isinstance(value, int | np.integer):
        return str(int(value))
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert("UTC").tz_localize(None)
        return str(value.value)
    if isinstance(value, np.datetime64):
        return _parent_field(pd.Timestamp(value))
    if value is pd.NA:
        return ""
    text = str(value)
    if "\t" in text or "\n" in text or "\r" in text:
        raise ValueError(f"field {text!r} holds a tab or a newline")
    return text


def _parent_content_text(frame: pd.DataFrame, key) -> str:
    columns = [str(c) for c in frame.columns]
    missing = [k for k in key if k not in columns]
    if missing:
        raise ValueError(f"key columns {missing} are not in the table")
    for name in columns:
        if "\t" in name or "\n" in name:
            raise ValueError(f"column name {name!r} holds a tab or a newline")
    rows = frame.sort_values(list(key), kind="mergesort") if len(key) else frame
    lines = ["\t".join(columns)]
    for row in rows.itertuples(index=False, name=None):
        lines.append("\t".join(_parent_field(v) for v in row))
    return "\n".join(lines) + "\n"


def parent_digest(frame: pd.DataFrame, key) -> str:
    return hashlib.sha256(_parent_content_text(frame, key).encode("utf-8")).hexdigest()


def dtypes_digest(frame: pd.DataFrame) -> str:
    text = "\n".join(f"{c}\t{t}" for c, t in frame.dtypes.items())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def every_kind() -> pd.DataFrame:
    """Every kind of field the content text has a rule for, keys with ties."""
    utc = pd.Timestamp("2019-06-14T13:30:00", tz="UTC")
    return pd.DataFrame({
        "k": ["b", "a", "b", "a", "c", "a"],
        "n": np.array([2, 2, 1, 1, 0, 1], dtype=np.int64),
        "f": [1 / 3, -0.0, np.nan, np.inf, -np.inf, 1e-300],
        "f32": np.array([0.1, 2.5, -1.0, 3.0, 0.0, 7.25], dtype=np.float32),
        "u8": np.array([0, 1, 2, 3, 254, 255], dtype=np.uint8),
        "b": [True, False, True, True, False, False],
        "s": pd.Series(["x", None, "y z", "", "é", "q"], dtype="str"),
        "ts": pd.Series([utc, pd.NaT, utc + pd.Timedelta(hours=1), utc, utc, utc]),
        "ts_ny": pd.Series(pd.date_range("2019-06-14 09:30", periods=6, freq="h",
                                         tz="America/New_York")).dt.as_unit("s"),
        "naive_us": pd.Series(pd.date_range("2019-01-01", periods=6, freq="D")
                              ).dt.as_unit("us"),
        "obj": pd.Series([None, pd.NA, date(2019, 7, 1), utc, np.datetime64("2019-01-02"),
                          "text"], dtype=object),
        "mixed": pd.Series([1, 2.5, True, np.int32(4), np.float64(0.1), "s"], dtype=object),
        "nullable": pd.array([1, None, 3, 4, 5, 6], dtype="Int64"),
        "cat": pd.Categorical(["u", "v", "u", "w", "v", "u"]),
    })


# ------------------------------------------------------------------ fixtures

@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("pcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def bars_state(tmp_path_factory, config, setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    path = tmp_path_factory.mktemp("pbars") / "state"
    assert main(["--state", str(path), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "bars", "fetch"]) == 0
    return path


@pytest.fixture(scope="module")
def journaled(tmp_path_factory, bars_state, setup):
    path = tmp_path_factory.mktemp("pjournal") / "state"
    shutil.copytree(bars_state, path)
    src = REPO_ROOT / "reference" / "trend_ma.py"
    strat = load_strategy_file(src, setup.thresholds)
    aid = write_approach(
        path, source=src.read_text(encoding="utf-8"), params=strat.params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description="the reference strategy trend_ma.py",
        profile_version="w-test", admitted=ADMITTED, instruments=setup.instruments,
        spread_tables=setup.spread_tables)
    approach = next(a for a in state.read_approaches(path) if a.id == aid)
    results = [journal.journal_day(path, setup, d) for d in DAYS]
    assert [r.status for r in results] == [journal.WRITTEN] * len(DAYS)
    return path, approach


# ------------------------------------------------------------------ content text

def test_content_text_every_kind_equals_the_parents():
    frame = every_kind()
    for key in (("k", "n"), ("k",), ("ts",), ()):
        assert state.content_text(frame, key) == _parent_content_text(frame, key)
    assert state.content_text(frame.iloc[:0], ("k",)) == _parent_content_text(
        frame.iloc[:0], ("k",))
    no_columns = pd.DataFrame(index=range(3))
    assert state.content_text(no_columns, ()) == _parent_content_text(no_columns, ())


def test_content_text_still_refuses_a_tab_or_a_newline():
    for bad in ("a\tb", "a\nb", "a\rb"):
        with pytest.raises(ValueError, match="holds a tab or a newline"):
            state.content_text(pd.DataFrame({"s": ["ok", bad]}), ("s",))


def test_content_text_of_journal_and_bar_rows_equals_the_parents(journaled, setup):
    path, _ = journaled
    for d in DAYS:
        rows = journal.read_day(path, TRACK, d)
        assert len(rows) > 0
        assert state.content_text(rows, journal.KEY) == _parent_content_text(
            rows, journal.KEY)
    bars = read_window(path, setup.track, setup.instruments[0],
                       setup.calendars[setup.instruments[0].calendar], ROLL_WINDOW).bars
    assert state.content_text(bars, ("ts",)) == _parent_content_text(bars, ("ts",))


# ------------------------------------------------------------------ score and executor

#: The parent's (4bf827d) score rows on ROLL_WINDOW of SYNA: content digest of
#: each subject's rows on ``ts`` by ``_parent_content_text``, and of their dtypes.
SCORE_DIGESTS = {
    "flat": "5eaa2a5254867b7ba032fc13b9aca7da87ad7044c648936fadc1f279ab02d2e9",
    "long": "60a85065cae1d82961b4a5de24b776fe225a46a02a20271b87a9d9b95109b8bc",
    "short": "eaedd8c3d730cb1a3feea39ee3ba6ba65d2798e8e394d4c3bfdb5f0ccfa2d10a",
    "random": "23ef165751bc34a2e7075d8e6e3aced322fe03c754c838b56c04ed47c064b61c",
    "carried": "ce867090bf41a1f6a3d64b4fed4b1f4a28b078bf8f4116a3584b99a8c0a122e8",
}
SCORE_DTYPES = "a25795d031ca554a299f2beebb26535ef9fd0871b47d8d2c2f030ae251f89488"


def score_subjects(win):
    n = len(win.inside)
    rng = np.random.default_rng(RNG_SEED)
    return [
        ("flat", np.zeros(n), None),
        ("long", np.ones(n), None),
        ("short", -np.ones(n), None),
        ("random", rng.choice([-1.0, 0.0, 0.5, 1.0], size=n), None),
        ("carried", rng.choice([-1.0, 1.0], size=n), (0.5, -1.0)),
    ]


def test_score_rows_equal_the_parents(bars_state, setup):
    inst = next(i for i in setup.instruments if i.symbol == "SYNA")
    win = read_window(bars_state, setup.track, inst, setup.calendars[inst.calendar],
                      ROLL_WINDOW, setup.spread_tables[inst.symbol])
    assert win.rolled[win.first:].any()  # the window holds the roll of 2019-06-14
    subjects = score_subjects(win)
    evs = score(win, subjects)
    got = {name: parent_digest(ev.rows, ("ts",))
           for (name, _, _), ev in zip(subjects, evs, strict=True)}
    assert got == SCORE_DIGESTS
    assert {dtypes_digest(ev.rows) for ev in evs} == {SCORE_DTYPES}
    for ev in evs:
        assert list(ev.rows.index) == list(win.inside.index)


def test_each_fill_bar_is_the_next_stored_bar(bars_state, setup):
    inst = next(i for i in setup.instruments if i.symbol == "SYNA")
    win = read_window(bars_state, setup.track, inst, setup.calendars[inst.calendar],
                      ROLL_WINDOW, setup.spread_tables[inst.symbol])
    stamps = list(win.bars["ts"])
    orders = [Order("x", inst.symbol, stamps[k - 1] if k else None, 0.0, 1.0)
              for k in range(len(stamps))]
    market = Market(inst, win.calendar, win.spread_table, win.bars, win.gaps, win.rolled)
    fills = SimExecutor().execute(orders, {inst.symbol: market})
    assert [f.bar for f in fills] == stamps
    assert all(isinstance(f.bar, pd.Timestamp) for f in fills)


# ------------------------------------------------------------------ journal rows

#: The parent's journal of DAYS: digest of each day's stored rows on KEY by
#: ``_parent_content_text`` (the index's content hash at the parent).
JOURNAL_DIGESTS = {
    "2019-06-27": "2c0ed1075816b16e3ba77087f2f8e65f4106e31019d8320c9043bb4955c14af0",
    "2019-06-28": "19051ac3308ad9368655eecc418b4ac14ba9c14c7a8c948477b9a9a664d81d6e",
    "2019-06-29": "0aa7836eac1ac79cca33772de1cfaabc42878a64f9921b2b63794a1f63c235a1",
    "2019-06-30": "2dfe35b59822fd90fb47a44192ba2a486b9dd2d07867cd7bc78ae4858e8edc2c",
    "2019-07-01": "6c29bc0a141b460130c76cca7a128e76a157657e1921bbf05761c507b5b09f50",
    "2019-07-02": "16ea5f118908cc44cfd8ece760482858daaa76b7521342db55af11afd67cacfa",
}
#: The parent's span rows over DAYS (approach) and of rc:0 and bh:SYNX.
SPAN_DIGESTS = {
    "approach": "6033f4cf49c805046a0c7ddeadf2b19177552400b94114f56d1e4dde9f0226a0",
    "rc:0": "4affda7d505e40d1adc1a33bb44a1ab97a887d666de1548697594b77c55b7f94",
    "bh:SYNX": "b9bde6d967d690709bf5a26747c0a89acb02eac3f9e60204e956df2f90d98b58",
}


def test_journal_days_equal_the_parents(journaled):
    path, _ = journaled
    index = {e["date"]: e for e in journal.read_index(path, TRACK)}
    got = {}
    for d in DAYS:
        rows = journal.read_day(path, TRACK, d)
        got[d.isoformat()] = parent_digest(rows, journal.KEY)
        assert index[d.isoformat()]["content_hash"] == got[d.isoformat()]
        assert index[d.isoformat()]["rows"] == len(rows)
    assert got == JOURNAL_DIGESTS
    # The controls drew on the first day and again on 2019-07-01.
    assert [d.day for d in controls.read_draws(path, TRACK)] == [DAYS[0], date(2019, 7, 1)]


def test_span_rows_equal_the_parents(journaled, setup):
    path, approach = journaled
    got = {"approach": parent_digest(
        journal.span_rows(path, setup, approach, DAYS[0], DAYS[-1]), journal.KEY)}
    spans = journal.control_span_rows(path, setup, DAYS[0], DAYS[-1], ["rc:0", "bh:SYNX"])
    got.update({name: parent_digest(rows, journal.KEY) for name, rows in spans.items()})
    assert got == SPAN_DIGESTS
