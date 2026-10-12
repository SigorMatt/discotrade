"""The controls (DESIGN 10.1, 7, 8, 9.2, 9.3, 9.4; decisions 2026-10-12 23, 25, 39, 49,
54, 64; I-1, I-5, I-6, I-12).

Every state directory is made by ``init-state`` under a pytest temporary
directory and run with ``run-day`` in-process through ``discotrade.cli.main``
on the fixture track ``test_mixed`` (SYNA rolls on 2019-06-14, SYNL cannot be
shorted, SYNX is always open and drops bars). The synthetic instruments'
seeds are those of their fixture records (``SEEDS``, asserted). The only
other random draws are the controls' own: the pool draws, seeded ``YYYYMM``
(``201906``, ``201907``), which the tests recompute with
``numpy.random.default_rng`` and those seeds, and the per-bar numbers, which
the tests recompute with ``hashlib`` from decision 64's key. Time comes only
from ``--as-of`` (``AS_OF``). No git is run here: a re-run's "no commit" is
seen as an unchanged ``.git/`` directory, file for file.

Two states are run: ``roll`` (production thresholds, no approach) for
2019-06-13 and 2019-06-14, which holds the SYNA roll; and ``month`` (three
reference approaches admitted on 2019-06-27) for 2019-06-28 to 2019-07-01,
across a calendar month, on a configuration copied under the test's temporary
directory whose ``controls.match_window_days`` is 2 (production 30, which
would need 30 days of runs), so that the July draw is matched. The rule of
the matched draw is also tested at the production values on frames the test
builds (``test_measured_pairs_at_the_production_values``).
"""

import hashlib
import json
import math
import shutil
import tomllib
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade import controls, journal, paper
from discotrade.backtest import read_window, score
from discotrade.cli import REPO_ROOT, main
from discotrade.config import DateRange
from discotrade.state import content_hash, write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-07-03T00:00:00+00:00"
#: The seed of every synthetic source these tests depend on.
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}
SYMBOLS = ("SYNA", "SYNL", "SYNX")
ROLL_DAYS = (date(2019, 6, 13), date(2019, 6, 14))
MONTH_DAYS = (date(2019, 6, 28), date(2019, 6, 29), date(2019, 6, 30), date(2019, 7, 1))
ADMITTED = date(2019, 6, 27)
FILES = ("trend_ma.py", "zscore_reversal.py", "hour_of_day.py")
LOW_WINDOW = 2
POOL = 50
#: The production values (config/thresholds.toml), asserted.
PRODUCTION = {"random_pool": 50, "match_window_days": 30, "match_min_live": 3}
LO, HI = 1.0, 48.0          # the bounds of test_mixed's horizons, short [1, 6] and medium [6, 48]
COMPARED = ("p", "h", "gross", "trade", "fee", "spread", "slippage", "roll", "cost",
            "net_1x", "net_2x")
AS_JOURNAL = {"p": "target_next", "h": "position", "roll": "roll_cost"}


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers."""
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


def files(root) -> dict[str, tuple[bytes, int]]:
    """Every file under ``root``, ``.git/`` included, with its bytes and mtime."""
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()}


def run(state, config, d, as_of=AS_OF):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", as_of, "run-day", "--day", d.isoformat()])


def pools(state) -> list[dict]:
    path = state / "controls" / TRACK / "pools.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def rows_of(state, days) -> pd.DataFrame:
    return pd.concat([journal.read_day(state, TRACK, d) for d in days], ignore_index=True)


def hashed(seed, slot, symbol, ts, purpose) -> float:
    """Decision 64's per-bar number, computed here on its own."""
    key = f"{seed}|{slot}|{symbol}|{pd.Timestamp(ts).value}|{purpose}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") / 2.0 ** 64


def own_targets(records, slot, symbol, shorting, stamps, dates) -> list[float]:
    """Decision 64's state machine, computed here on its own from the pool
    records, flat before the first bar."""
    out, state, current = [], 0.0, None
    for ts, d in zip(stamps, dates, strict=True):
        record = [r for r in records if date.fromisoformat(r["day"]) <= d][-1]
        if current is None or record["day"] != current["day"]:
            state, current = 0.0, record
        seed, h, q = record["seed"], record["H"][slot], record["q"][slot]
        if state == 0.0:
            if hashed(seed, slot, symbol, ts, "enter") < q:
                side = hashed(seed, slot, symbol, ts, "side")
                state = 1.0 if (side < 0.5 or not shorting) else -1.0
        elif hashed(seed, slot, symbol, ts, "exit") < 1.0 / h:
            state = 0.0
        out.append(state)
    return out


def holding(positions) -> list[int]:
    """The lengths of the maximal runs of non-zero position of one sign."""
    runs, run_, prev = [], 0, 0.0
    for x in positions:
        s = np.sign(x)
        if s != 0 and run_ and s == prev:
            run_ += 1
        else:
            if run_:
                runs.append(run_)
            run_ = 1 if s != 0 else 0
        prev = s
    if run_:
        runs.append(run_)
    return runs


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("ccfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def low(tmp_path_factory, config):
    """The configuration with ``controls.match_window_days`` = ``LOW_WINDOW``."""
    path = tmp_path_factory.mktemp("clow") / "config"
    shutil.copytree(config, path)
    text = (path / "thresholds.toml").read_text(encoding="utf-8")
    assert text.count("match_window_days = 30 ") == 1
    (path / "thresholds.toml").write_text(
        text.replace("match_window_days = 30 ", f"match_window_days = {LOW_WINDOW}  "),
        encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


def fresh(path):
    assert main(["init-state", "--state", str(path), "--as-of", AS_OF]) == 0
    return path


@pytest.fixture(scope="module")
def roll(tmp_path_factory, config):
    """No approach; the days of the SYNA roll, at the production thresholds."""
    state = fresh(tmp_path_factory.mktemp("croll") / "state")
    for d in ROLL_DAYS:
        assert run(state, config, d) == 0, d
    return state


@pytest.fixture(scope="module")
def month(tmp_path_factory, low, setup):
    """Three approaches; the days across the June-July boundary."""
    state = fresh(tmp_path_factory.mktemp("cmonth") / "state")
    ids = []
    for name in FILES:
        path = REPO_ROOT / "reference" / name
        strat = load_strategy_file(path, setup.thresholds)
        ids.append(write_approach(
            state, source=path.read_text(encoding="utf-8"), params=strat.params,
            cell="trend/short", model_id="test-model", model_version="test-model-v0",
            cutoff=date(2019, 1, 1), description=name, profile_version="w-test",
            admitted=ADMITTED, instruments=setup.instruments,
            spread_tables=setup.spread_tables))
    for d in MONTH_DAYS:
        assert run(state, low, d) == 0, d
    return state, sorted(ids)


# ------------------------------------------------------------------ the values


def test_seeds_and_production_values(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    with open(REPO_ROOT / "config" / "thresholds.toml", "rb") as fh:
        assert tomllib.load(fh)["controls"] == PRODUCTION
    assert controls.horizon_bounds(setup.track.horizons) == (LO, HI)
    assert {i.symbol: i.shorting for i in setup.instruments} == \
        {"SYNA": True, "SYNL": False, "SYNX": True}


def test_the_per_bar_number_is_decision_64s_hash():
    ts = pd.Timestamp("2019-06-28T13:00:00Z")
    for purpose in ("enter", "side", "exit"):
        assert controls.uniform(201906, 7, "SYNA", ts, purpose) == \
            hashed(201906, 7, "SYNA", ts, purpose)
    assert controls.uniform(201906, 7, "SYNA", ts, "enter") != \
        controls.uniform(201906, 7, "SYNA", ts + pd.Timedelta(hours=1), "enter")


def test_measured_pairs_at_the_production_values():
    window, min_live = PRODUCTION["match_window_days"], PRODUCTION["match_min_live"]
    days = [date(2019, 1, 1) + timedelta(days=k) for k in range(window + 1)]

    def rows(day, positions):
        ts = pd.date_range(day.isoformat(), periods=len(positions), freq="h", tz="UTC")
        pos = np.asarray(positions, dtype=float)
        prev = np.concatenate([[0.0], pos[:-1]])
        return pd.DataFrame({"ts": ts, "instrument": "X", "position": pos,
                             "trade": np.abs(pos - prev)})

    day_rows = {d: rows(d, [0, 1, 1, 0]) for d in days}
    day_rows[days[0]] = rows(days[0], [1, 1, 1, 1])   # outside the last 30 days
    enough = {aid: dict(day_rows) for aid in ("a1", "a2", "a3")}
    short = {d: day_rows[d] for d in days[:window - 1]}
    # Two approaches with 30 days and one with 29: fewer than 3 qualify.
    assert controls.measured_pairs({"a1": enough["a1"], "a2": enough["a2"], "a3": short},
                                   ["a1", "a2", "a3"], window, min_live) is None
    pairs = controls.measured_pairs(enough, ["a1", "a2", "a3"], window, min_live)
    # Over the last 30 days: runs of 2 bars; trades 2 per 4 rows.
    assert [(p.id, p.H, p.q) for p in pairs] == [(a, 2.0, 0.5) for a in ("a1", "a2", "a3")]
    # A pair whose H is not a number (never in a position) is left out.
    flat = {d: rows(d, [0, 0, 0, 0]) for d in days}
    pairs = controls.measured_pairs({**enough, "a4": flat}, ["a1", "a2", "a3", "a4"],
                                    window, min_live)
    assert [p.id for p in pairs] == ["a1", "a2", "a3"]


# ------------------------------------------------------------------ every day


@pytest.mark.parametrize("which", ["roll", "month"])
def test_every_day_journals_bh_and_rc_on_every_instrument(request, which, setup):
    state = request.getfixturevalue(which)
    state = state[0] if which == "month" else state
    days = ROLL_DAYS if which == "roll" else MONTH_DAYS
    rc = {f"rc:{k}" for k in range(POOL)}
    for d in days:
        rows = journal.read_day(state, TRACK, d)
        controls_rows = rows[rows["kind"] != "approach"]
        for symbol in SYMBOLS:
            mine = controls_rows[controls_rows["instrument"] == symbol]
            if mine.empty:          # SYNA and SYNL have no bar on a weekend day
                assert d.weekday() >= 5 and symbol != "SYNX"
                continue
            by_kind = mine.groupby("subject")["kind"].agg(set).to_dict()
            assert by_kind == {f"bh:{symbol}": {"control_bh"},
                               **{s: {"control_random"} for s in rc}}
            counts = mine.groupby("subject").size()
            assert counts.nunique() == 1          # every control has every bar of the day
        assert set(controls_rows["kind"]) == {"control_bh", "control_random"}
        bh = controls_rows[controls_rows["kind"] == "control_bh"]
        assert all(s == f"bh:{i}" for s, i in zip(bh["subject"], bh["instrument"], strict=True))


def test_buy_and_hold_targets_1_starts_flat_and_pays_the_roll(roll):
    rows = rows_of(roll, ROLL_DAYS)
    for symbol in SYMBOLS:
        mine = rows[rows["subject"] == f"bh:{symbol}"].sort_values("ts").reset_index(drop=True)
        assert len(mine) and (mine["instrument"] == symbol).all()
        assert (mine["target_next"] == 1.0).all()
        assert (mine["prev_position"].iloc[0], mine["position"].iloc[0]) == (0.0, 0.0)
        assert mine["date"].iloc[0] == ROLL_DAYS[0]
        assert (mine["position"].iloc[1:] == 1.0).all()
        assert mine["trade"].iloc[1] == 1.0 and (mine["trade"].iloc[2:] == 0.0).all()
    syna = rows[rows["subject"] == "bh:SYNA"]
    rolled = syna[syna["roll"]]
    assert len(rolled) == 1 and rolled["date"].iloc[0] == ROLL_DAYS[1]
    r = rolled.iloc[0]
    assert r["prev_position"] == 1.0 and r["trade"] == 0.0 and r["roll_cost"] > 0.0
    assert eq(r["net_1x"], r["gross"] - r["roll_cost"])
    assert eq(r["net_2x"], r["gross"] - 2 * r["roll_cost"])


# ------------------------------------------------------------------ draws


def test_a_draw_on_the_first_day_and_the_first_trading_day_of_each_later_month(roll, month):
    assert [(p["day"], p["month"], p["seed"]) for p in pools(roll)] == \
        [("2019-06-13", "2019-06", 201906)]
    assert [(p["day"], p["month"], p["seed"]) for p in pools(month[0])] == \
        [("2019-06-28", "2019-06", 201906), ("2019-07-01", "2019-07", 201907)]
    for p in pools(roll) + pools(month[0]):
        assert set(p) == {"month", "day", "seed", "H", "q", "pairs"}
        assert len(p["H"]) == len(p["q"]) == POOL


def test_the_fallback_draw_is_log_uniform_on_the_horizons(roll, month):
    [record] = pools(roll)
    rng = np.random.default_rng(201906)
    expected = [math.exp(rng.uniform(math.log(LO), math.log(HI))) for _ in range(POOL)]
    assert record["H"] == expected
    assert record["q"] == [1.0 / h for h in expected]
    assert all(LO <= h <= HI for h in record["H"])
    assert record["pairs"] == []
    assert pools(month[0])[0] == {**record, "day": "2019-06-28"}   # the same seed, no pairs


def test_the_matched_draw_takes_the_live_approaches_measured_pairs(month):
    state, ids = month
    record = pools(state)[1]
    measured = MONTH_DAYS[1:3]                 # the last 2 paper days before 07-01
    rows = rows_of(state, measured)
    pairs = []
    for aid in ids:
        mine = rows[rows["subject"] == aid]
        runs = [n for _, leg in mine.groupby("instrument")
                for n in holding(leg.sort_values("ts")["position"])]
        assert runs
        pairs.append((aid, sum(runs) / len(runs),
                      int((mine["trade"] > 1e-9).sum()) / len(mine)))
    got = [(p["id"], p["H"], p["q"]) for p in record["pairs"]]
    assert [g[0] for g in got] == ids
    for (a, h, q), (b, gh, gq) in zip(pairs, got, strict=True):
        assert a == b and eq(h, gh) and eq(q, gq)
    rng = np.random.default_rng(201907)
    chosen = [got[int(rng.integers(len(got)))] for _ in range(POOL)]
    assert record["H"] == [c[1] for c in chosen]
    assert record["q"] == [c[2] for c in chosen]
    assert len({c[0] for c in chosen}) > 1


# ------------------------------------------------------------------ the state machine


def test_every_slots_targets_are_decision_64s_state_machine(month, setup):
    state, _ = month
    records = pools(state)
    rows = rows_of(state, MONTH_DAYS)
    shorting = {i.symbol: i.shorting for i in setup.instruments}
    for slot in range(POOL):
        for symbol in SYMBOLS:
            mine = rows[(rows["subject"] == f"rc:{slot}") & (rows["instrument"] == symbol)]
            mine = mine.sort_values("ts")
            own = own_targets(records, slot, symbol, shorting[symbol], list(mine["ts"]),
                              list(mine["date"]))
            assert list(mine["target_next"]) == own, (slot, symbol)
    rc = rows[rows["kind"] == "control_random"]
    synl = rc[rc["instrument"] == "SYNL"]
    assert (synl["target_next"] >= 0).all() and (synl["target_next"] > 0).any()
    for symbol in ("SYNA", "SYNX"):
        assert (rc[rc["instrument"] == symbol]["target_next"] < 0).any()


def test_the_position_carries_across_a_redraw(month):
    state, _ = month
    rows = rows_of(state, MONTH_DAYS)
    rc = rows[rows["kind"] == "control_random"].sort_values("ts")
    carried = 0
    for (_, _), leg in rc.groupby(["subject", "instrument"]):
        leg = leg.reset_index(drop=True)
        k = int(np.flatnonzero((leg["date"] == MONTH_DAYS[-1]).to_numpy())[0])
        assert leg["position"][k] == leg["target_next"][k - 1]
        assert leg["prev_position"][k] == leg["position"][k - 1]
        carried += leg["position"][k] != 0.0
    assert carried > 0


# ------------------------------------------------------------------ one implementation of §7


def test_the_controls_rows_are_the_modules_evaluation_of_their_targets(month, setup):
    state, _ = month
    records = pools(state)
    rows = rows_of(state, MONTH_DAYS)
    window = DateRange(MONTH_DAYS[0], MONTH_DAYS[-1])
    for inst in setup.instruments:
        win = read_window(state, setup.track, inst, setup.calendars[inst.calendar], window,
                          setup.spread_tables[inst.symbol])
        stamps, dates = list(win.inside["ts"]), list(win.dates)
        items = [(f"bh:{inst.symbol}", np.ones(len(stamps)), None)]
        items += [(f"rc:{k}", np.array(own_targets(records, k, inst.symbol, inst.shorting,
                                                   stamps, dates)), None)
                  for k in range(POOL)]
        for (subject, _, _), ev in zip(items, score(win, items), strict=True):
            mine = rows[(rows["subject"] == subject) & (rows["instrument"] == inst.symbol)]
            mine = mine.sort_values("ts").reset_index(drop=True)
            mine["cost"] = mine["fee"] + mine["spread"] + mine["slippage"] + mine["roll_cost"]
            assert len(ev.rows) == len(mine) > 0
            assert list(ev.rows["ts"]) == list(mine["ts"])
            assert list(ev.rows["date"]) == list(mine["date"])
            for field in COMPARED:
                column = AS_JOURNAL.get(field, field)
                for k, (a, b) in enumerate(zip(mine[column], ev.rows[field], strict=True)):
                    assert eq(a, b), f"{subject} {inst.symbol} row {k} {field}: {a!r} != {b!r}"


def test_the_paper_records_hold_the_controls_clean(month):
    state, _ = month
    stored = paper.read(state, TRACK)
    ctrl = stored[stored["kind"] != "approach"]
    assert set(ctrl["subject"]) == {f"bh:{s}" for s in SYMBOLS} | \
        {f"rc:{k}" for k in range(POOL)}
    assert ctrl["clean"].all()
    assert set(ctrl[ctrl["subject"].str.startswith("rc:")]["date"]) == set(MONTH_DAYS)
    rows = rows_of(state, MONTH_DAYS)
    for subject, n in (("bh:SYNA", 1), ("rc:3", 3)):
        for d in MONTH_DAYS:
            mine = rows[(rows["subject"] == subject) & (rows["date"] == d)]
            held = ctrl[(ctrl["subject"] == subject) & (ctrl["date"] == d)]
            if mine.empty:
                assert held.empty
                continue
            assert eq(held["net_1x"].iloc[0], mine["net_1x"].sum() / n)


# ------------------------------------------------------------------ recompute and re-runs


def recompute(state, config):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", AS_OF, "journal", "recompute", "--all"])


def printed(out):
    return [tuple(line.split()[:3]) for line in out.splitlines()
            if line.split() and line.split()[0] in ("equal", "MISMATCH")]


def test_recompute_all_matches_every_control_pair_and_reports_a_changed_row(
        tmp_path, roll, config, capsys):
    state = tmp_path / "state"
    shutil.copytree(roll, state)
    held = sorted((d.isoformat(), s) for d in ROLL_DAYS
                  for s in set(journal.read_day(state, TRACK, d)["subject"]))
    assert len(held) == 2 * POOL + 2 * 3
    assert recompute(state, config) == 0
    assert printed(capsys.readouterr().out) == [("equal", d, s) for d, s in held]
    d, subject = ROLL_DAYS[1], "rc:7"
    path = journal.journal_path(state, TRACK, d)
    rows = pd.read_parquet(path)
    at = rows.index[(rows["subject"] == subject) & (rows["instrument"] == "SYNA")][5]
    rows.loc[at, "net_1x"] = rows.loc[at, "net_1x"] + 1e-6
    rows.to_parquet(path, index=False, engine="pyarrow")
    assert recompute(state, config) == 1
    assert printed(capsys.readouterr().out) == \
        [("MISMATCH" if (x, s) == (d.isoformat(), subject) else "equal", x, s)
         for x, s in held]


def test_a_rerun_of_a_finished_day_writes_nothing(tmp_path, month, low):
    state = tmp_path / "state"
    shutil.copytree(month[0], state)
    before = files(state)
    assert any(k.startswith(".git/") for k in before)
    assert "controls/test_mixed/pools.jsonl" in before
    for d in (MONTH_DAYS[-1], MONTH_DAYS[0], MONTH_DAYS[2]):
        assert run(state, low, d) == 0
    # No file, index line, ledger, pool or health line, and no commit (.git unchanged).
    assert files(state) == before


def test_two_fresh_state_directories_give_equal_journal_paper_and_pools(tmp_path, roll,
                                                                       config):
    other = fresh(tmp_path / "other")
    for d in ROLL_DAYS:
        assert run(other, config, d) == 0
    assert journal.read_index(other, TRACK) == journal.read_index(roll, TRACK)
    assert content_hash(paper.read(other, TRACK), paper.KEY) == \
        content_hash(paper.read(roll, TRACK), paper.KEY)
    path = ("controls", TRACK, "pools.jsonl")
    assert other.joinpath(*path).read_bytes() == roll.joinpath(*path).read_bytes()
