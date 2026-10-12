"""G0.3: the bar store, the gap check, the adjusted series and the roll cost
(DESIGN 18.3 G0.3, 5.1 to 5.4, 5.6, 7.3, 17.1, 18.2; I-5, I-9; decisions
2026-10-12 3 to 6, 9, 18, 24, 36, 40).

Stores are filled by the ``discotrade`` command run in-process
(``discotrade.cli.main``, the console script's function) with ``bars fetch``
and a clock given by ``--as-of``, or, for the refusals, through the store's
own ``append`` with the synthetic source's ``available_until`` at a
``FixedClock``'s instant. Everything is written under pytest temporary
directories, on the fixture track ``test_mixed`` (SYNA rolls quarterly; SYNA
and SYNL are on the ``synth_week`` calendar, SYNX is always open).

What the test compares against comes from the generator (``SynthSource``:
its dropped bars, its contract constants, and its gap-free underlying series)
and from the fixture TOML, never from the code under test.

Seeds: the test draws nothing at random. The synthetic bars come from the
fixture records' seeds, written here in ``SEEDS`` and checked against them.
"""

import json
import shutil
import tomllib
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from discotrade.backtest import evaluate
from discotrade.bars.store import BarStore, BarStoreError
from discotrade.cli import REPO_ROOT, main
from discotrade.clock import FixedClock
from discotrade.config import DateRange, load_calendar, load_track_config
from discotrade.rolls import adjusted_as_of, read_rolls, roll_path
from discotrade.sources.synth import SynthSource, _generate
from discotrade.spreads import spread_table
from discotrade.state import content_hash
from discotrade.strategy import Strategy
from discotrade.tradingcal import expected_bars

pytestmark = [pytest.mark.gate, pytest.mark.gate_m0]

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
HOUR = 3600
#: The seed of each instrument's synthetic source, as its fixture record gives it.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
#: The clock of the main store: Friday 2019-07-12 20:00 New York, after the
#: week's close, and the end of that UTC date, so that day D is 2019-07-12 on
#: both calendars and the gap check covers every stored bar. The store runs
#: from trusted_from (2019-01-07) and so holds SYNA's rolls of 2019-03-14 and
#: 2019-06-14, every daily break and weekend in between, and the closure of
#: 2019-07-03 13:00 to 2019-07-04 18:00 New York.
AS_OF = pd.Timestamp("2019-07-13 00:00", tz="UTC")
CLOSURE = ("2019-07-03 13:00", "2019-07-04 18:00")
NEW_YORK = ZoneInfo("America/New_York")
#: The window evaluated across SYNA's roll of 2019-06-14.
ROLL_WINDOW = DateRange(date(2019, 6, 10), date(2019, 6, 20))
REL = 1e-9


def close_to(a, b, rel=REL) -> bool:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return bool(np.all(np.abs(a - b) <= rel * np.maximum(1.0, np.maximum(np.abs(a),
                                                                         np.abs(b)))))


# ------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def tc(config):
    return load_track_config(config, TRACK)


@pytest.fixture(scope="module")
def calendars(config):
    return {p.stem: load_calendar(p) for p in sorted((config / "calendars").glob("*.toml"))}


@pytest.fixture(scope="module")
def source(calendars):
    return SynthSource(calendars, HOUR)


def inst_of(tc, symbol):
    return next(i for i in tc.instruments if i.symbol == symbol)


def fetch(state: Path, config: Path, as_of: pd.Timestamp) -> None:
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of.isoformat(), "bars", "fetch"]) == 0


@pytest.fixture(scope="module")
def state(tmp_path_factory, config):
    path = tmp_path_factory.mktemp("state")
    fetch(path, config, AS_OF)
    return path


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file under ``root``, by relative path, with its bytes."""
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def trusted(inst) -> datetime:
    return datetime.combine(inst.trusted_from, time(), tzinfo=UTC)


def test_the_synthetic_seeds_are_the_ones_written_here(tc):
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS


# ------------------------------------------------------------- refusals


def closed_bars(source, inst, until: datetime) -> pd.DataFrame:
    """The source's bars from trusted_from that have closed by ``until``."""
    bars = source.fetch(inst, trusted(inst), until)
    return bars[bars["ts"] + pd.Timedelta(seconds=HOUR) <= pd.Timestamp(until)]


@pytest.mark.parametrize("symbol", ["SYNL", "SYNA", "SYNX"])
def test_the_store_refuses_a_bar_that_is_not_closed_and_writes_nothing(
        tmp_path, tc, source, symbol):
    inst = inst_of(tc, symbol)
    store = BarStore(tmp_path, TRACK, HOUR)
    # Tuesday 2019-03-05 12:30 UTC: the 12:00 bar is open, the 11:00 bar closed at 12:00.
    clock = FixedClock(datetime(2019, 3, 5, 12, 30, tzinfo=UTC))
    until = source.available_until(clock.now())
    assert until == clock.now()
    first = closed_bars(source, inst, datetime(2019, 3, 1, tzinfo=UTC))
    assert store.append(symbol, first, until) == len(first) > 0
    before = snapshot(tmp_path)

    later = source.fetch(inst, datetime(2019, 3, 1, tzinfo=UTC), until)
    open_bar = pd.Timestamp("2019-03-05 12:00", tz="UTC")
    assert later["ts"].iloc[-1] == open_bar          # the batch ends with the open bar
    assert (later["ts"].iloc[:-1] + pd.Timedelta(seconds=HOUR) <= until).all()
    with pytest.raises(BarStoreError, match="not closed"):
        store.append(symbol, later, until)
    assert snapshot(tmp_path) == before
    with pytest.raises(BarStoreError, match="not closed"):
        store.append(symbol, later.iloc[[-1]], until)
    assert snapshot(tmp_path) == before

    # The same bar is refused one microsecond before its close and taken at it.
    at_close = open_bar + pd.Timedelta(seconds=HOUR)
    almost = source.available_until(FixedClock(
        (at_close - pd.Timedelta(microseconds=1)).to_pydatetime()).now())
    with pytest.raises(BarStoreError, match="not closed"):
        store.append(symbol, later, almost)
    assert snapshot(tmp_path) == before
    until = source.available_until(FixedClock(at_close.to_pydatetime()).now())
    assert store.append(symbol, later, until) == len(later)
    assert store.last_ts(symbol) == open_bar


@pytest.mark.parametrize("symbol", ["SYNL", "SYNA", "SYNX"])
def test_the_store_refuses_a_bar_not_later_than_the_last_and_writes_nothing(
        tmp_path, tc, source, symbol):
    inst = inst_of(tc, symbol)
    store = BarStore(tmp_path, TRACK, HOUR)
    until = source.available_until(FixedClock(datetime(2019, 3, 5, 12, 30, tzinfo=UTC)).now())
    bars = closed_bars(source, inst, until)
    cut = pd.Timestamp("2019-03-01", tz="UTC")
    head, tail = bars[bars["ts"] < cut], bars[bars["ts"] >= cut]
    assert store.append(symbol, head, until) == len(head) > 2
    last = store.last_ts(symbol)
    assert last == head["ts"].iloc[-1]
    before = snapshot(tmp_path)
    attempts = {
        "the last bar again": head.iloc[[-1]],
        "an earlier bar": head.iloc[[-2]],
        "the first stored bar": head.iloc[[0]],
        "the last bar, then later ones": pd.concat([head.iloc[[-1]], tail]),
        "an earlier bar, then later ones": pd.concat([head.iloc[[-3]], tail]),
    }
    for what, batch in attempts.items():
        with pytest.raises(BarStoreError, match="not later than the last stored bar"):
            store.append(symbol, batch, until)
        assert snapshot(tmp_path) == before, what
    assert store.append(symbol, tail, until) == len(tail) > 0


# ------------------------------------------------------- old rows unchanged


def test_an_append_leaves_every_old_row_of_every_month_file_unchanged(
        tmp_path, config, tc):
    # A first store ends mid-March; a second fetch appends to March and adds
    # April and May.
    fetch(tmp_path, config, pd.Timestamp("2019-03-20 12:30", tz="UTC"))
    bars_dir = tmp_path / "bars" / TRACK
    old_index = BarStore(tmp_path, TRACK, HOUR).index()
    old = {p: pd.read_parquet(p) for p in sorted(bars_dir.rglob("*.parquet"))}
    assert {p.stem for p in old} == {"2019-01", "2019-02", "2019-03"}
    assert len(old) == 3 * len(tc.instruments)

    fetch(tmp_path, config, pd.Timestamp("2019-05-10 12:30", tz="UTC"))
    new_index = BarStore(tmp_path, TRACK, HOUR).index()
    grew = 0
    for path, frame in old.items():
        symbol, month = path.parent.name, path.stem
        after = pd.read_parquet(path)
        r = len(frame)
        assert len(after) >= r
        assert content_hash(after.iloc[:r], ("ts",)) == content_hash(frame, ("ts",))
        assert content_hash(frame, ("ts",)) == old_index[symbol]["months"][month]["hash"]
        pd.testing.assert_frame_equal(after.iloc[:r].reset_index(drop=True), frame,
                                      check_exact=True)
        if month != "2019-03":
            assert new_index[symbol]["months"][month] == old_index[symbol]["months"][month]
        grew += len(after) > r
    assert grew == len(tc.instruments)       # every March file was appended to
    for symbol in tc.track.instruments:
        assert {"2019-04", "2019-05"} <= set(new_index[symbol]["months"])


# ------------------------------------------------------------- gap check


def local_interval(ts: datetime) -> tuple[datetime, datetime]:
    return ts.astimezone(NEW_YORK), (ts + timedelta(seconds=HOUR)).astimezone(NEW_YORK)


def overlaps_break(ts: datetime) -> bool:
    lo, hi = local_interval(ts)
    day = lo.date()
    for d in (day, day + timedelta(days=1)):
        b0 = datetime.combine(d, time(17), tzinfo=NEW_YORK)
        b1 = datetime.combine(d, time(18), tzinfo=NEW_YORK)
        if lo < b1 and b0 < hi:
            return True
    return False


def overlaps_weekend(ts: datetime) -> bool:
    lo, hi = local_interval(ts)
    friday = lo.date() - timedelta(days=(lo.weekday() - 4) % 7)
    w0 = datetime.combine(friday, time(17), tzinfo=NEW_YORK)
    w1 = datetime.combine(friday + timedelta(days=2), time(18), tzinfo=NEW_YORK)
    return lo < w1 and w0 < hi


def overlaps_closure(ts: datetime) -> bool:
    lo, hi = local_interval(ts)
    c0, c1 = (datetime.fromisoformat(s).replace(tzinfo=NEW_YORK) for s in CLOSURE)
    return lo < c1 and c0 < hi


def test_the_gap_check_finds_exactly_the_dropped_bars(state, tc, source, calendars):
    lines = (state / "bars" / TRACK / "gaps.jsonl").read_text(encoding="utf-8").splitlines()
    found: dict[str, set[datetime]] = {s: set() for s in tc.track.instruments}
    for line in lines:
        row = json.loads(line)
        found[row["symbol"]].add(datetime.fromisoformat(row["ts"]).astimezone(UTC))
    assert len(lines) == sum(len(v) for v in found.values())   # no line twice
    store = BarStore(state, TRACK, HOUR)
    synth_week = [i for i in tc.instruments if i.calendar == "synth_week"]
    assert {i.symbol for i in synth_week} == {"SYNA", "SYNL"}
    for inst in tc.instruments:
        stored = store.read_range(inst.symbol, trusted(inst), AS_OF)["ts"]
        first, last = stored.iloc[0].to_pydatetime(), stored.iloc[-1].to_pydatetime()
        dropped = {t for t in source.dropped(inst, trusted(inst), AS_OF.to_pydatetime())
                   if first <= t <= last}
        assert dropped, inst.symbol             # the generator dropped some bars here
        assert found[inst.symbol] == dropped, inst.symbol
        assert not dropped & {t.to_pydatetime() for t in stored}

    for inst in synth_week:
        stored = {t.to_pydatetime()
                  for t in store.read_range(inst.symbol, trusted(inst), AS_OF)["ts"]}
        # The range holds every closed interval the item names: hourly instants
        # inside the stored span with no stored bar, each in a break, a weekend
        # or the closure, none of which the gap check reports.
        span = pd.date_range(min(stored), max(stored), freq="h").to_pydatetime()
        absent = [t for t in span if t not in stored and t not in found[inst.symbol]]
        assert any(overlaps_break(t) and not overlaps_weekend(t) for t in absent)
        assert any(overlaps_weekend(t) for t in absent)
        closure = [t for t in absent if overlaps_closure(t)]
        # 13:00 on the 3rd to 18:00 on the 4th, New York.
        assert len(closure) == 29, (inst.symbol, len(closure))
        assert all(overlaps_break(t) or overlaps_weekend(t) or overlaps_closure(t)
                   for t in absent), inst.symbol
        for t in found[inst.symbol]:
            assert not (overlaps_break(t) or overlaps_weekend(t) or overlaps_closure(t)), t


# ------------------------------------------------------- adjusted series


def test_the_adjusted_series_is_the_underlying_plus_the_current_constant(
        state, tc, source, calendars):
    inst = inst_of(tc, "SYNA")
    cal = calendars[inst.calendar]
    # The generator's gap-free underlying series (DESIGN 17.1): every expected
    # bar from trusted_from, dropped ones included, with no contract constant.
    times = expected_bars(cal, trusted(inst), AS_OF.to_pydatetime(), HOUR)
    underlying = _generate(times, inst.source, HOUR)[0].set_index("ts")
    continuous = source.fetch(inst, trusted(inst), AS_OF.to_pydatetime()).set_index("ts")
    constant = {c: source.contract_constant(inst, c) for c in continuous["contract"].unique()}

    stored = BarStore(state, TRACK, HOUR).read_range("SYNA", trusted(inst), AS_OF)
    contracts = stored["contract"].tolist()
    rolls = [k for k in range(1, len(contracts)) if contracts[k] != contracts[k - 1]]
    assert len(rolls) >= 2
    assert len(read_rolls(roll_path(state, TRACK, "SYNA"))) == len(rolls)
    assert len(set(constant.values())) == len(constant)    # every roll moves the price
    under = underlying.loc[stored["ts"]]
    prices = ("open", "high", "low", "close")
    base = {col: under[col].to_numpy() for col in prices}

    for k, t in enumerate(stored["ts"]):
        current = continuous.loc[t, "contract"]
        assert current == contracts[k]
        adj = adjusted_as_of(state, TRACK, HOUR, inst, t)
        assert list(adj["ts"]) == list(stored["ts"].iloc[:k + 1]), t
        for col in prices:
            want = base[col][:k + 1] + constant[current]
            assert close_to(adj[col].to_numpy(), want), (t, col)
        assert np.array_equal(adj["volume"].to_numpy(), stored["volume"].to_numpy()[:k + 1])


# ------------------------------------------------------------- roll cost


def constant_strategy(value: float) -> Strategy:
    return Strategy(name=f"hold_{value:g}", source="", params={}, grid=None,
                    position=lambda bars, params: value)


def unit_cost_at(state, inst, config, calendar, u_ts) -> float:
    """``c(u)`` of DESIGN 7.3 at the bar opening at ``u_ts``, from the stored bars,
    the roll records and the fixture TOML."""
    store = BarStore(state, TRACK, HOUR)
    bars = store.last_n(inst.symbol, u_ts, 26)
    assert bars["ts"].iloc[-1] == u_ts and len(bars) == 26
    gaps = {r.ts: r.gap for r in read_rolls(roll_path(state, TRACK, inst.symbol))}
    close = bars["close"].to_numpy()
    r = [(close[s] - (close[s - 1] + gaps.get(bars["ts"].iloc[s], 0.0))) / close[s - 1]
         for s in range(len(bars) - 25, len(bars) - 1)]
    assert len(r) == 24
    sigma = float(np.std(r, ddof=1))
    with open(config / "instruments" / f"{inst.symbol}.toml", "rb") as f:
        record = tomllib.load(f)
    with open(config / "spreads" / f"{inst.symbol}.toml", "rb") as f:
        ticks = tomllib.load(f)["spread_ticks"][u_ts.tz_convert(calendar.tz).hour]
    o = bars["open"].iloc[-1]
    cost = record["cost"]
    fee = cost["fee_per_side"] / (record["multiplier"] * o)
    half = max(ticks / 2.0, 0.5) * record["tick_size"] / o
    return fee + half + cost["slippage_coef"] * sigma


@pytest.mark.parametrize("hold", [1.0, -0.5, 0.0])
def test_a_carried_position_pays_the_roll_cost_and_a_flat_one_none(
        state, tc, calendars, config, hold):
    inst = inst_of(tc, "SYNA")
    cal = calendars[inst.calendar]
    ev = evaluate(state, tc.track, inst, cal, constant_strategy(hold), ROLL_WINDOW,
                  spread_table=spread_table(config, "SYNA"))
    rows = ev.rows
    contract = rows["contract"].tolist()
    at = [k for k in range(1, len(rows)) if contract[k] != contract[k - 1]]
    assert len(at) == 1
    u = at[0]
    u_ts = rows["ts"].iloc[u]
    assert u_ts == pd.Timestamp("2019-06-14 00:00", tz="UTC")
    assert rows["h"].iloc[u - 1] == rows["h"].iloc[u] == hold      # carried through
    assert rows["trade"].iloc[u] == 0.0
    c = unit_cost_at(state, inst, config, cal, u_ts)
    want = 2.0 * abs(hold) * c
    assert close_to(rows["roll"].iloc[u], want, 1e-12), (rows["roll"].iloc[u], want)
    assert close_to(rows["cost"].iloc[u], want, 1e-12)
    others = rows.drop(index=u)
    assert (others["roll"] == 0.0).all()
    if hold == 0.0:
        assert rows["roll"].iloc[u] == 0.0 and (rows["cost"] == 0.0).all()
    else:
        assert rows["roll"].iloc[u] > 0.0
