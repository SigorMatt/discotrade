"""The combined paper portfolio (DESIGN 10.5, 9.3, 11.3; decisions 2026-10-12
53, 61, 63, 64, 69; I-3, I-6).

``paper.portfolio`` is tested on paper records and lifecycle rows the test
writes by hand, so that every case of decision 69 is on a known day: no
member, one member, several members with a clean and an exposed one, a member
made dormant on ``D`` (a member on ``D``, not on ``D + 1``), one admitted on
``D`` (a member from ``D + 1``), one live at the start of a day with no paper
row on it (retired on that day for a failure), and a control row (never a
member). Each expected value is the test's own equal-weight mean of the
members' paper rows, the members read by the test from the lifecycle rows
dated before the day and the admission dates.

``run-day`` then runs in-process through ``discotrade.cli.main`` on the fixture
track ``test_mixed`` (a configuration copied under the test's tmp directory
with the production ``config/thresholds.toml``; a second copy has
``lifecycle.dormant_window_days`` 2 in place of the production 30, so that a
member goes dormant within the few days run, said so where used; the rule is
tested at 30 in ``tests/test_lifecycle.py``), and the stored portfolio rows
are compared with the test's own count from the paper rows and the lifecycle
ledger, and with a rebuild. That rank persistence, the control moments, the
matched draw and the lifecycle's Sharpes take no portfolio row is shown on
frames with portfolio rows of extreme values and, for the draw, on the run
state with those rows changed in a copy. The synthetic instruments' seeds
are those of their fixture records (``SEEDS``, asserted); no other random
draw is made. Time comes only from ``--as-of``.
"""

import math
import shutil
from datetime import date, timedelta

import pandas as pd
import pytest

from discotrade import journal, ledger, lifecycle, paper, stats
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_calendar, load_thresholds
from discotrade.state import Approach, content_hash, read_approaches, write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
AS_OF = "2019-06-26T00:00:00+00:00"
SEEDS = {"SYNA": 101, "SYNL": 105, "SYNX": 106}


def eq(a, b) -> bool:
    """Decision 39's equality for real numbers."""
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


# ------------------------------------------------------------------ by hand

D1, D2, D3, D4, D5, D6 = (date(2020, 1, 6) + timedelta(days=k) for k in range(6))


def approach(aid, admitted):
    return Approach(aid, "", {}, admitted, {"cell": "trend/short", "cutoff": "2019-01-01"})


#: a1, a2, a4 admitted on D1 (members from D2), a3 admitted on D2 (from D3).
APPROACHES = [approach("a1", D1), approach("a2", D1), approach("a3", D2), approach("a4", D1)]
#: a1 goes dormant on D3 (a member on D3, not on D4); a4 is retired for a
#: failure on D3 (no paper row on D3, so not a member though live at its
#: start); a3 goes dormant on D5 (a member on D5, not on D6).
LIFECYCLE = [
    {"date": D3.isoformat(), "id": "a4", "from": "live", "to": "retired",
     "reason": "failure: x"},
    {"date": D3.isoformat(), "id": "a1", "from": "live", "to": "dormant", "reason": "dormant"},
    {"date": D5.isoformat(), "id": "a3", "from": "live", "to": "dormant", "reason": "dormant"},
]
#: (subject, kind, date, gross, net_1x, net_2x, trades, clean)
HAND = [
    ("a1", "approach", D2, 0.010, 0.008, 0.006, 2, True),
    ("a1", "approach", D3, -0.004, -0.005, -0.006, 1, True),
    ("a1", "approach", D4, 0.500, 0.500, 0.500, 9, True),     # dormant: not a member
    ("a1", "approach", D5, 0.500, 0.500, 0.500, 9, True),
    ("a1", "approach", D6, 0.500, 0.500, 0.500, 9, True),
    ("a2", "approach", D2, 0.002, 0.001, 0.000, 1, False),    # exposed
    ("a2", "approach", D3, 0.003, 0.002, 0.001, 0, False),
    ("a2", "approach", D4, -0.002, -0.003, -0.004, 3, True),
    ("a2", "approach", D5, 0.001, 0.000, -0.001, 1, True),
    ("a2", "approach", D6, 0.004, 0.003, 0.002, 2, False),    # one member, exposed
    ("a3", "approach", D3, 0.006, 0.004, 0.002, 4, True),
    ("a3", "approach", D4, 0.001, 0.001, 0.001, 0, False),
    ("a3", "approach", D5, -0.007, -0.008, -0.009, 2, True),
    ("a3", "approach", D6, 0.900, 0.900, 0.900, 9, True),     # dormant on D5
    ("a4", "approach", D2, 0.020, 0.019, 0.018, 1, True),
    ("rc:0", "control_random", D2, 0.300, 0.300, 0.300, 7, True),
    ("rc:0", "control_random", D4, 0.300, 0.300, 0.300, 7, True),
    ("bh:X", "control_bh", D6, 0.300, 0.300, 0.300, 7, True),
]
#: The members the test reads from the rows above, per day.
MEMBERS = {D1: [], D2: ["a1", "a2", "a4"], D3: ["a1", "a2", "a3"], D4: ["a2", "a3"],
           D5: ["a2", "a3"], D6: ["a2"]}


def hand_records() -> pd.DataFrame:
    rows = [dict(zip(("subject", "kind", "date", "gross", "net_1x", "net_2x", "trades",
                      "clean"), r, strict=True)) for r in HAND]
    return pd.DataFrame(rows)[list(paper.COLUMNS)]


def own(records, members):
    """The test's own portfolio values over ``members``' rows."""
    mine = [records[(records["subject"] == m)] for m in members]
    if not members:
        return {"gross": 0.0, "net_1x": 0.0, "net_2x": 0.0, "trades": 0, "clean": True}
    out = {k: sum(float(r[k].iloc[0]) for r in mine) / len(mine)
           for k in ("gross", "net_1x", "net_2x")}
    out["trades"] = sum(int(r["trades"].iloc[0]) for r in mine)
    out["clean"] = all(bool(r["clean"].iloc[0]) for r in mine)
    return out


def check(row, want):
    for k in ("gross", "net_1x", "net_2x"):
        assert eq(row[k], want[k]), (row["subject"], row["date"], k)
    assert int(row["trades"]) == want["trades"] and bool(row["clean"]) == want["clean"]


def test_the_portfolio_by_hand_on_each_case():
    records = hand_records()
    days = [D1, D2, D3, D4, D5, D6]
    out = paper.portfolio(records, days, LIFECYCLE, APPROACHES)
    assert tuple(out.columns) == paper.COLUMNS
    assert set(out["kind"]) == {"portfolio"}
    whole = out[out["subject"] == "portfolio"].set_index("date")
    clean = out[out["subject"] == "portfolio_clean"].set_index("date")
    assert list(whole.index) == days                        # every day, from the first
    for d in days:
        today = records[records["date"] == d]
        members = MEMBERS[d]
        row = whole.loc[d].to_dict() | {"subject": "portfolio", "date": d}
        check(row, own(today, members))
        clean_members = [m for m in members
                         if bool(today[today["subject"] == m]["clean"].iloc[0])]
        if clean_members:
            row = clean.loc[d].to_dict() | {"subject": "portfolio_clean", "date": d}
            check(row, own(today, clean_members))
            assert bool(row["clean"])
        else:
            assert d not in clean.index
    # The cases are where the docstring says they are.
    assert MEMBERS[D1] == [] and whole.loc[D1, "net_1x"] == 0.0 and whole.loc[D1, "clean"]
    assert D1 not in clean.index and D6 not in clean.index       # no clean member
    assert not whole.loc[D2, "clean"] and not whole.loc[D6, "clean"]
    assert list(clean.index) == [D2, D3, D4, D5]


def test_clean_members_are_the_members_portfolio_clean_counts():
    # Decision 2026-10-17-m19 151 (b): the members of portfolio_clean on each day, by
    # the test's own reading of the rows above; a day with none is left out, as
    # portfolio_clean has no row on it.
    records = hand_records()
    days = [D1, D2, D3, D4, D5, D6]
    got = paper.clean_members(records, days, LIFECYCLE, APPROACHES)
    want = {}
    for d in days:
        today = records[records["date"] == d]
        clean = [m for m in MEMBERS[d] if bool(today[today["subject"] == m]["clean"].iloc[0])]
        if clean:
            want[d] = clean
    assert got == want
    assert got == {D2: ["a1", "a4"], D3: ["a1", "a3"], D4: ["a2"], D5: ["a2", "a3"]}
    out = paper.portfolio(records, days, LIFECYCLE, APPROACHES)
    clean_rows = out[out["subject"] == "portfolio_clean"].set_index("date")
    assert list(clean_rows.index) == sorted(got)
    for d, ids in got.items():
        today = records[records["date"] == d]
        assert eq(clean_rows.loc[d, "net_1x"], own(today, ids)["net_1x"])


def test_the_rows_are_sorted_by_the_key_and_do_not_depend_on_the_row_order():
    records = hand_records()
    shuffled = records.sample(frac=1.0, random_state=11).reset_index(drop=True)   # seed 11
    a = paper.portfolio(records, [D1, D2, D3, D4, D5, D6], LIFECYCLE, APPROACHES)
    b = paper.portfolio(shuffled, [D6, D5, D4, D3, D2, D1], LIFECYCLE, APPROACHES)
    assert content_hash(a, paper.KEY) == content_hash(b, paper.KEY)
    assert list(a["subject"]) == sorted(a["subject"])


# ------------------------------------------------------------------ no portfolio row taken


def with_portfolio(records):
    """``records`` with portfolio rows of extreme values on each of their days."""
    extra = []
    for d in sorted(set(records["date"])):
        for subject in ("portfolio", "portfolio_clean"):
            extra.append({"date": d, "subject": subject, "kind": "portfolio",
                          "gross": -50.0 * (d.day % 3 + 1), "net_1x": -50.0 * (d.day % 3 + 1),
                          "net_2x": -50.0, "trades": 99, "clean": True})
    return pd.concat([records, pd.DataFrame(extra)[list(paper.COLUMNS)]], ignore_index=True)


def test_the_control_moments_take_no_portfolio_row():
    span = [D1, D2, D3]
    rows = [{"date": d, "subject": f"rc:{k}", "kind": "control_random", "gross": x,
             "net_1x": x, "net_2x": x, "trades": 0, "clean": True}
            for k, xs in enumerate([[0.01, -0.02, 0.03], [0.002, 0.004, -0.001]])
            for d, x in zip(span, xs, strict=True)]
    records = pd.DataFrame(rows)[list(paper.COLUMNS)]
    assert stats.control_moments(with_portfolio(records), span) == \
        stats.control_moments(records, span)


def test_rank_persistence_takes_no_portfolio_row_even_when_asked_for_approaches():
    epoch = date(2020, 1, 6)
    span = [epoch + timedelta(days=k) for k in range(14)]
    rows = [{"date": d, "subject": s, "kind": "approach", "gross": 0.0,
             "net_1x": 0.001 * (k + 1) * (1 if i < 7 else -1), "net_2x": 0.0, "trades": 0,
             "clean": True}
            for k, s in enumerate(NAMES) for i, d in enumerate(span)]
    records = pd.DataFrame(rows)[list(paper.COLUMNS)]
    always = stats_calendar()
    subjects = {s: [always] for s in NAMES}
    # alerts.rank_min_population at its production value, 5.
    min_population = int(load_thresholds(REPO_ROOT / "config" / "thresholds.toml")
                         ["alerts.rank_min_population"])
    assert min_population == 5
    kwargs = dict(epoch=epoch, block_days=7, bar_seconds=3600, k=1,
                  min_population=min_population)
    got = stats.rank_persistence(with_portfolio(records), subjects, **kwargs)
    assert got == stats.rank_persistence(records, subjects, **kwargs)
    assert got["subjects"] == list(NAMES) and got["statistic"] == -1.0


NAMES = ("a1", "a2", "a3", "a4", "a5")


def stats_calendar():
    return load_calendar(FIXTURE_CONFIG / "calendars" / "always_open.toml")


def test_the_lifecycle_sharpes_take_no_portfolio_row(tmp_path, setup):
    """A live approach with a positive Sharpe over its last 30 rows (the
    production ``dormant_window_days``) stays live with or without portfolio
    rows of large negative values on its days."""
    th = setup.thresholds
    n = th["lifecycle.dormant_window_days"]
    assert n == 30
    start = date(2019, 1, 1)
    aid = write_approach(
        tmp_path, source="# a\nPARAMS = {}\n", params={"k": 1}, cell="trend/short",
        model_id="m", model_version="v", cutoff=date(2018, 1, 1), description="a",
        profile_version="w", admitted=start - timedelta(days=1),
        instruments=setup.instruments, spread_tables=setup.spread_tables)
    rows = [{"date": start + timedelta(days=k), "subject": aid, "kind": "approach",
             "gross": 0.0, "net_1x": 0.002 + (0.01 if k % 2 else -0.01), "net_2x": 0.0,
             "trades": 1, "clean": True} for k in range(n)]
    records = pd.DataFrame(rows)[list(paper.COLUMNS)]
    day = start + timedelta(days=n - 1)
    approaches = read_approaches(tmp_path)
    # Step 2 reads the adjusted series (decision 2026-10-14 85), from the derived
    # exposure records (decision 84): written here with every R_i(D) 0 and no
    # position, so that it is the plain series.
    unit = pd.DataFrame([{"instrument": i.symbol, "date": d, "unit": 0.0}
                         for i in setup.instruments for d in records["date"]])
    held = pd.DataFrame(columns=["subject", "instrument", "date", "rows", "position"])
    paper.write_exposure(tmp_path, setup.track.name, unit, held)
    plain = lifecycle.step_rows(setup, day, [], approaches, records, {}, state_dir=tmp_path)
    mixed = lifecycle.step_rows(setup, day, [], approaches, with_portfolio(records), {},
                                state_dir=tmp_path)
    assert plain == mixed == []


# ------------------------------------------------------------------ as run-day writes it


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("pfcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def low(tmp_path_factory, config):
    """``lifecycle.dormant_window_days`` 2 in place of 30, on a copy under tmp."""
    path = tmp_path_factory.mktemp("pflow") / "config"
    shutil.copytree(config, path)
    text = (path / "thresholds.toml").read_text(encoding="utf-8")
    assert "dormant_window_days = 30 " in text
    (path / "thresholds.toml").write_text(
        text.replace("dormant_window_days = 30 ", "dormant_window_days = 2  "),
        encoding="utf-8")
    return path


FIRST = date(2019, 6, 8)        # trend_ma and hour_of_day admitted: members from 06-09
LATER = date(2019, 6, 10)       # zscore_reversal admitted: a member from 06-11
DAYS = tuple(date(2019, 6, 8) + timedelta(days=k) for k in range(5))   # 06-08 .. 06-12
#: hour_of_day's model cutoff: its rows up to it are exposed.
EXPOSED_TO = date(2019, 6, 10)


def admit(state, setup, name, admitted, cutoff=date(2019, 1, 1)):
    path = REPO_ROOT / "reference" / name
    strat = load_strategy_file(path, setup.thresholds)
    return write_approach(
        state, source=path.read_text(encoding="utf-8"), params=strat.params,
        cell="trend/short", model_id="test-model", model_version="test-model-v0",
        cutoff=cutoff, description=f"the reference strategy {name}",
        profile_version="w-test", admitted=admitted, instruments=setup.instruments,
        spread_tables=setup.spread_tables)


@pytest.fixture(scope="module")
def ran(tmp_path_factory, setup, low):
    state = tmp_path_factory.mktemp("pfran") / "state"
    assert main(["init-state", "--state", str(state), "--as-of", AS_OF]) == 0
    admit(state, setup, "trend_ma.py", FIRST)
    admit(state, setup, "hour_of_day.py", FIRST, cutoff=EXPOSED_TO)
    admit(state, setup, "zscore_reversal.py", LATER)
    for d in DAYS:
        assert main(["--state", str(state), "--config", str(low), "--track", TRACK,
                     "--as-of", AS_OF, "run-day", "--day", d.isoformat()]) == 0
    return state


def test_seeds_are_the_fixture_records(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS


def own_members(state, d):
    """The approaches live at the start of ``d`` by the test's own reading: the
    ``to`` of the last lifecycle row dated before ``d``, else live when
    admitted before ``d``; with a paper row on ``d``."""
    rows = ledger.read(state, TRACK, ledger.LIFECYCLE)
    held = paper.read(state, TRACK)
    out = []
    for a in read_approaches(state):
        if a.admitted >= d:
            continue
        to = "live"
        for r in rows:
            if r["id"] == a.id and date.fromisoformat(r["date"]) < d:
                to = r["to"]
        mine = held[(held["subject"] == a.id) & (held["date"] == d)]
        if to == "live" and len(mine):
            out.append(a.id)
    return sorted(out)


def test_run_day_writes_the_portfolio_rows_the_test_counts(ran):
    state = ran
    held = paper.read(state, TRACK)
    whole = held[held["subject"] == "portfolio"]
    clean = held[held["subject"] == "portfolio_clean"]
    assert list(whole["date"]) == list(DAYS)
    assert set(whole["kind"]) | set(clean["kind"]) == {"portfolio"}
    seen = {"none": False, "several_mixed": False, "dormant_on_d": False}
    rows = ledger.read(state, TRACK, ledger.LIFECYCLE)
    for d in DAYS:
        today = held[held["date"] == d]
        members = own_members(state, d)
        row = whole[whole["date"] == d].iloc[0].to_dict()
        check(row, own(today, members))
        clean_members = [m for m in members
                         if bool(today[today["subject"] == m]["clean"].iloc[0])]
        mine = clean[clean["date"] == d]
        if clean_members:
            check(mine.iloc[0].to_dict(), own(today, clean_members))
        else:
            assert mine.empty
        seen["none"] |= not members
        seen["several_mixed"] |= 0 < len(clean_members) < len(members)
        went = [r["id"] for r in rows if r["date"] == d.isoformat() and r["to"] == "dormant"]
        if went and d < DAYS[-1]:
            nxt = d + timedelta(days=1)
            assert all(a in members for a in went)
            assert all(a not in own_members(state, nxt) for a in went)
            assert all(len(held[(held["subject"] == a) & (held["date"] == nxt)]) for a in went)
            seen["dormant_on_d"] = True
    assert all(seen.values()), seen
    later = next(a.id for a in read_approaches(state) if a.admitted == LATER)
    assert later not in own_members(state, LATER) and \
        later in own_members(state, LATER + timedelta(days=1))


def test_the_stored_records_rebuild_to_the_same_content_hash(ran, setup):
    stored = paper.read(ran, TRACK)
    rebuilt = paper.rebuild(ran, TRACK, len(setup.instruments))
    assert content_hash(rebuilt, paper.KEY) == content_hash(stored, paper.KEY)
    assert {"portfolio", "portfolio_clean"} <= set(rebuilt["subject"])


def test_the_matched_draw_takes_no_portfolio_row(tmp_path, ran, low):
    """The draw made on 2019-06-10, matched on the two approaches live at its
    start (``controls.match_window_days`` 1 and ``controls.match_min_live`` 2 in
    place of 30 and 3, on a copy of ``low`` under tmp, so that one paper day
    before it suffices), is the same when the paper file's portfolio rows are
    changed."""
    cfg = tmp_path / "config"
    shutil.copytree(low, cfg)
    text = (cfg / "thresholds.toml").read_text(encoding="utf-8")
    for old, new in (("match_window_days = 30 ", "match_window_days = 1  "),
                     ("match_min_live = 3", "match_min_live = 2")):
        assert old in text
        text = text.replace(old, new)
    (cfg / "thresholds.toml").write_text(text, encoding="utf-8")
    setup = journal.Setup.load(cfg, TRACK)
    day = DAYS[2]
    before = journal.new_draw(ran, setup, day)
    assert sorted(p.id for p in before.pairs) == own_members(ran, day)
    assert len(before.pairs) == 2
    copy = tmp_path / "state"
    shutil.copytree(ran, copy)
    held = paper.read(copy, TRACK)
    port = held["kind"] == "portfolio"
    held.loc[port, ["gross", "net_1x", "net_2x"]] = 7.0
    held.loc[port, "trades"] = 1000
    paper.write(copy, TRACK, held)
    assert journal.new_draw(copy, setup, day) == before

