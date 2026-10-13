"""G1.3: a scripted lifecycle scenario shows each transition of DESIGN 10.3; the
ledgers hold one row per event and are never rewritten; the table and the two
portfolio series match a hand count (DESIGN 18.3 G1.3, 18.2, 10.2 to 10.5, 8,
9.3, 11.2, 11.3; decisions 2026-10-12 25, 30, 39, 41, 48, 60, 62, 63, 69, 71,
72, 73, 74; I-5).

The replay runs on the fixture track ``test_synth`` (four synthetic
instruments on ``synth_week``, ``cell_slots`` 3) and decision 72's gate
configuration (``lifecycle.dormant_window_days`` 15,
``lifecycle.revival_min_dormant_days`` 5, ``lifecycle.retire_dormant_days``
365 calendar days, ``admission.min_trades_t`` 10), in-process through
``discotrade.cli.main``, into a state made by ``init-state`` under the test's
tmp directory at ``INIT_AS_OF``, with the scripted candidates of the new
fixture ``tests/fixtures/scenarios/g1_lifecycle.jsonl`` (one candidate a day,
decision 73), from 2019-06-03 to 2020-06-10, in three segments
(``SEGMENTS``): 2019-06-03 to 06-13, 06-14 to 08-13, 08-14 to 2020-06-10. The
candidates:

- 06-03 ``tests/fixtures/strategies/always_flat.py`` (new fixture, always 0,
  so its paper Sharpe is not a number) into ``trend/short``: ``free_slot``;
- 06-04 ``reference/zscore_reversal.py``, score -0.3: refused ``not_positive``;
- 06-05 ``reference/hour_of_day.py``, score 0.9 with 9 trades: refused
  ``too_few_trades`` (gate ``min_trades_t`` 10);
- 06-06 and 06-07 ``tests/fixtures/strategies/breaks_thursday_noon.py`` at
  12:00 and at 13:00 into ``trend/short``: ``free_slot`` each, the cell full;
- 06-11 ``reference/trend_ma.py`` (``fast`` 6, ``slow`` 24) into the full
  ``trend/short``, score 0.8: admitted ``displaced``, the weakest being the
  always-flat approach (a Sharpe that is not a number is the lowest), which
  goes dormant (``displaced``); its model cutoff 2019-07-31 makes its paper
  rows exposed until then.

Then, as the replay runs: on Thursday 06-13 both breaking approaches are
retired on failure (step 1); trend_ma goes dormant (step 2) and returns
(step 3) as its paper Sharpe over its last 15 rows turns; the always-flat
approach, never able to return, is retired on 2020-06-10, 365 calendar days
after its row to ``dormant`` (step 4). The test lists every trial row and
every lifecycle row, in full and in order.

The ledgers are never rewritten: after each segment, each ledger's earlier
bytes are a prefix of its later bytes. The two portfolio series of the paper
records equal, on every journaled day, the test's own count from the paper
rows and the lifecycle rows (decision 69); ``table.json`` at the end of each
segment (2019-06-13, 2019-08-13 mid-scenario, and the last day 2020-06-10)
equals, row for row and field for field under decision 39's rule, the test's
own count (decision 71), the DESIGN 8 figures computed here with decisions 30
and 41 written below, and the deflated figures with decision 60's formula and
the standard library's normal quantile. The test reads the paper file, the
journal and the ledgers with pyarrow and json directly; no function of
``table.py``, ``stats.py`` or ``paper.py`` computes a count it compares with.

Seeds: the synthetic instruments' seeds are those of their fixture records
(``SEEDS``, asserted); the random pool is seeded by decision 64 with the
month. No other random draw is made. Time comes only from ``--as-of`` and the
replay's clock.
"""

import hashlib
import json
import math
import tomllib
from datetime import date, timedelta
from statistics import NormalDist

import numpy as np
import pyarrow.parquet as pq
import pytest
from m1_harness import gate_config, init_state, read_jsonl, read_paper, replay

from discotrade import costs, journal
from discotrade.cli import REPO_ROOT
from discotrade.config import load_track_config
from discotrade.state import approach_id

pytestmark = [pytest.mark.gate, pytest.mark.gate_m1]

TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
SCENARIO = REPO_ROOT / "tests" / "fixtures" / "scenarios" / "g1_lifecycle.jsonl"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
SEGMENTS = [(date(2019, 6, 3), date(2019, 6, 13)), (date(2019, 6, 14), date(2019, 8, 13)),
            (date(2019, 8, 14), date(2020, 6, 10))]
LEDGERS = ("trials.jsonl", "lifecycle.jsonl", "calls.jsonl")
TOL = 1e-12
G = 0.5772156649015329          # Euler-Mascheroni (decision 60)
PERIODS = 252                   # trading days a year (DESIGN 8, R-7)


def scenario() -> list[dict]:
    return [json.loads(x) for x in SCENARIO.read_text(encoding="utf-8").splitlines()]


def cid(line) -> str:
    return approach_id((REPO_ROOT / line["source"]).read_text(encoding="utf-8"),
                       line["params"])


LINES = scenario()
FLAT, ZSCORE, HOUR, BREAK12, BREAK13, TREND = (cid(x) for x in LINES)


def fail(hour_utc: int) -> str:
    return (f"failure: position on SYNA at bar ts 2019-06-13 {hour_utc}:00:00+00:00 "
            f"returned 2.0, outside [-1, 1]")


#: Every lifecycle row the scenario produces, in ledger order.
LIFECYCLE = [
    ("2019-06-03", FLAT, "candidate", "live", "admitted"),
    ("2019-06-06", BREAK12, "candidate", "live", "admitted"),
    ("2019-06-07", BREAK13, "candidate", "live", "admitted"),
    ("2019-06-11", TREND, "candidate", "live", "admitted"),       # displacing the weakest
    ("2019-06-11", FLAT, "live", "dormant", "displaced"),
    ("2019-06-13", BREAK12, "live", "retired", fail(16)),        # 12:00 New York
    ("2019-06-13", BREAK13, "live", "retired", fail(17)),
    ("2019-07-02", TREND, "live", "dormant", "dormant"),          # step 2
    ("2019-08-12", TREND, "dormant", "live", "returned"),         # step 3
    ("2019-08-14", TREND, "live", "dormant", "dormant"),
    ("2019-11-18", TREND, "dormant", "live", "returned"),
    ("2019-12-02", TREND, "live", "dormant", "dormant"),
    ("2020-03-18", TREND, "dormant", "live", "returned"),
    ("2020-03-19", TREND, "live", "dormant", "dormant"),
    ("2020-06-10", FLAT, "dormant", "retired", "retired_dormant"),  # 2019-06-11 + 365 days
]
#: Each candidate's verdict: (admitted, reason, displaced).
VERDICTS = [(True, "free_slot", None), (False, "not_positive", None),
            (False, "too_few_trades", None), (True, "free_slot", None),
            (True, "free_slot", None), (True, "displaced", FLAT)]


# ------------------------------------------------------------------ the replay


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    """The scenario replayed in segments; after each, the ledgers' and the
    table's bytes."""
    root = tmp_path_factory.mktemp("g13")
    config = gate_config(root)
    state = init_state(root / "state", INIT_AS_OF)
    snaps = []
    for first, last in SEGMENTS:
        status, out, err = replay(state, config, TRACK, first, last,
                                  "--candidates", str(SCENARIO))
        assert status == 0, err
        led = state / "ledger" / TRACK
        snaps.append({
            "last": last,
            "ledgers": {n: (led / n).read_bytes() if (led / n).exists() else None
                        for n in LEDGERS},
            "table": json.loads((state / "table" / TRACK / "table.json").read_text("utf-8")),
        })
    return state, config, snaps


@pytest.fixture(scope="module")
def setup(ran):
    return journal.Setup.load(ran[1], TRACK)


@pytest.fixture(scope="module")
def records(ran):
    return read_paper(ran[0], TRACK)


@pytest.fixture(scope="module")
def journal_sums(ran):
    return read_journal_sums(ran[0])


def read_journal_sums(state) -> dict:
    """Per subject, per journal day: the sums of gross, trade and rolled
    turnover (2 * |prev_position| on a row with roll) of its journal rows
    (decision 25)."""
    out = {}
    for line in read_jsonl(state / "journal" / TRACK / "index.jsonl"):
        d = date.fromisoformat(line["date"])
        path = state / "journal" / TRACK / f"{d.year:04d}" / f"{d.isoformat()}.parquet"
        rows = pq.read_table(path, columns=["subject", "gross", "trade", "roll",
                                            "prev_position"]).to_pandas()
        for subject, mine in rows.groupby("subject", sort=True):
            rolled = np.where(mine["roll"].to_numpy(dtype=bool),
                              2.0 * np.abs(mine["prev_position"].to_numpy(dtype=np.float64)),
                              0.0)
            out.setdefault(str(subject), []).append((
                d, math.fsum(mine["gross"].to_numpy(dtype=np.float64)),
                math.fsum(mine["trade"].to_numpy(dtype=np.float64)), math.fsum(rolled)))
    return out


def journal_days(state) -> list[date]:
    return [date.fromisoformat(x["date"])
            for x in read_jsonl(state / "journal" / TRACK / "index.jsonl")]


def metas(state) -> dict[str, dict]:
    return {p.parent.name: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((state / "approaches").glob("*/meta.json"))}


# ------------------------------------------------------------------ hand formulas


def close(a: float, b: float) -> bool:
    """Decision 39's "equal, to 1e-12"."""
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def own_sharpe(d: list[float]) -> float:
    """DESIGN 8 with decision 30: mean / std(ddof 1) * sqrt(252); not a number
    with fewer than 2 days, when every value equals the first, or when the
    deviation is not above 1e-12 times the largest absolute value."""
    if len(d) < 2 or all(x == d[0] for x in d):
        return math.nan
    x = np.asarray(d, dtype=np.float64)
    sd = float(np.std(x, ddof=1))
    if not sd > 1e-12 * float(np.max(np.abs(x))):
        return math.nan
    return float(np.mean(x)) / sd * math.sqrt(PERIODS)


def own_drawdown(d: list[float]) -> float:
    """Decision 41: the largest fall of the running sum from its running peak,
    the starting 0 counting as a peak; 0 with no fall."""
    total = peak = worst = 0.0
    for x in d:
        total += x
        peak = max(peak, total)
        worst = max(worst, peak - total)
    return worst


def own_z(p: float) -> float:
    return NormalDist().inv_cdf(p)


def own_e(mu: float, sd: float, n: int) -> float:
    """Decision 60's E(N), with max(N, 2)."""
    if math.isnan(mu) or math.isnan(sd):
        return math.nan
    m = max(n, 2)
    return mu + sd * ((1 - G) * own_z(1 - 1 / m) + G * own_z(1 - 1 / (m * math.e)))


def state_after(rows, approaches, day) -> dict[str, str]:
    """Decision 63: each approach admitted on or before ``day``, by its last
    lifecycle row dated on or before ``day``, else live."""
    out = {aid: "live" for aid, m in approaches.items()
           if date.fromisoformat(m["admitted"]) <= day}
    for r in rows:
        if date.fromisoformat(r["date"]) <= day and r["id"] in out:
            out[r["id"]] = r["to"]
    return out


def same(a, b) -> bool:
    if isinstance(a, float) and math.isnan(a):
        a = None
    if isinstance(b, float) and math.isnan(b):
        b = None
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) or isinstance(b, float):
        return (not isinstance(a, bool) and not isinstance(b, bool)
                and close(float(a), float(b)))
    return a == b


# ------------------------------------------------------------------ the scenario


def test_seeds_scenario_and_gate_values(ran, setup):
    tc = load_track_config(ran[1], TRACK)
    assert {inst.symbol: inst.source.get("seed") for inst in tc.instruments} == SEEDS
    th = setup.thresholds
    assert int(th["lifecycle.retire_dormant_days"]) == 365
    assert int(th["lifecycle.dormant_window_days"]) == 15
    assert int(th["lifecycle.revival_min_dormant_days"]) == 5
    assert int(th["admission.min_trades_t"]) == 10
    assert int(tc.track.cell_slots) == 3
    assert [x["day"] for x in LINES] == ["2019-06-03", "2019-06-04", "2019-06-05",
                                         "2019-06-06", "2019-06-07", "2019-06-11"]
    assert date(2019, 6, 11) + timedelta(days=365) == SEGMENTS[-1][1]


def test_every_lifecycle_row_in_full_and_in_order(ran):
    rows = read_jsonl(ran[0] / "ledger" / TRACK / "lifecycle.jsonl")
    assert [(r["date"], r["id"], r["from"], r["to"], r["reason"]) for r in rows] == LIFECYCLE
    assert all(set(r) == {"date", "id", "from", "to", "reason"} for r in rows)
    # One row per event: no event twice.
    assert len({json.dumps(r, sort_keys=True) for r in rows}) == len(rows)


def test_each_transition_of_10_3_is_shown():
    reasons = [(frm, to, reason.split(":")[0]) for _, _, frm, to, reason in LIFECYCLE]
    for wanted in [("candidate", "live", "admitted"), ("live", "dormant", "displaced"),
                   ("live", "dormant", "dormant"), ("dormant", "live", "returned"),
                   ("live", "retired", "failure"), ("dormant", "retired", "retired_dormant")]:
        assert wanted in reasons
    assert [v[1] for v in VERDICTS].count("free_slot") == 3
    assert ("not_positive" in [v[1] for v in VERDICTS]
            and "too_few_trades" in [v[1] for v in VERDICTS])


def test_one_trial_row_per_candidate_in_full(ran, setup):
    rows = read_jsonl(ran[0] / "ledger" / TRACK / "trials.jsonl")
    want = []
    for line, (admitted, reason, displaced) in zip(LINES, VERDICTS, strict=True):
        source = (REPO_ROOT / line["source"]).read_text(encoding="utf-8")
        want.append({
            "date": line["day"], "id": cid(line), "cell": line["cell"],
            "model_id": line["model_id"], "model_version": line["model_version"],
            "cutoff": line["cutoff"],
            "code_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "profile_version": line["profile_version"], "cost_model": costs.VERSION,
            "config_hash": costs.config_hash(setup.instruments, setup.spread_tables),
            "grid": None, "params": line["params"], "metrics_w": None,
            "metrics_t": line["metrics_t"], "admitted": admitted, "reason": reason,
            "displaced": displaced})
    assert rows == want


def test_admitted_under_approaches_refused_under_trials(ran):
    state = ran[0]
    for line, (admitted, _, _) in zip(LINES, VERDICTS, strict=True):
        aid = cid(line)
        assert (state / "approaches" / aid).is_dir() == admitted
        assert (state / "trials" / aid).is_dir() == (not admitted)


def test_ledgers_are_never_rewritten(ran):
    snaps = ran[2]
    final = {n: (ran[0] / "ledger" / TRACK / n) for n in LEDGERS}
    for name in LEDGERS:
        seen = [s["ledgers"][name] for s in snaps]
        now = final[name].read_bytes() if final[name].exists() else None
        seen.append(now)
        if name == "calls.jsonl":       # no worker call before step S3.2
            assert all(x is None for x in seen)
            continue
        assert all(x is not None for x in seen)
        for earlier, later in zip(seen, seen[1:], strict=False):
            assert later.startswith(earlier)
    assert len(snaps[0]["ledgers"]["lifecycle.jsonl"].splitlines()) == 7
    assert len(snaps[1]["ledgers"]["lifecycle.jsonl"].splitlines()) == 9
    assert len(snaps[0]["ledgers"]["trials.jsonl"].splitlines()) == 6


# ------------------------------------------------------------------ the portfolio


def test_portfolio_series_match_a_hand_count(ran, records):
    """Decision 69: members of D are the approaches live at the start of D
    (lifecycle rows dated before D) with a paper row on D; equal-weight means
    of gross, net_1x and net_2x, trades summed; portfolio on every journaled
    day (0 with no member), portfolio_clean only with a clean member."""
    state = ran[0]
    approaches = metas(state)
    life = read_jsonl(state / "ledger" / TRACK / "lifecycle.jsonl")
    days = journal_days(state)
    rows = {(str(r["subject"]), r["date"]): r for r in records.to_dict("records")}
    got = {s: {r["date"]: r for r in records[records["subject"] == s].to_dict("records")}
           for s in ("portfolio", "portfolio_clean")}
    assert sorted(got["portfolio"]) == days
    want_clean_days = []
    counted = {"members": 0, "empty": 0}
    for d in days:
        start = state_after(life, approaches, d - timedelta(days=1))
        members = [rows[(aid, d)] for aid in sorted(start)
                   if start[aid] == "live" and (aid, d) in rows]
        counted["members" if members else "empty"] += 1
        clean = [m for m in members if bool(m["clean"])]
        for subject, mine in (("portfolio", members), ("portfolio_clean", clean)):
            if subject == "portfolio_clean" and not mine:
                assert d not in got[subject], d
                continue
            row = got[subject][d]
            n = len(mine)
            for col in ("gross", "net_1x", "net_2x"):
                want = math.fsum(float(m[col]) for m in mine) / n if n else 0.0
                assert close(float(row[col]), want), (subject, d, col)
            assert int(row["trades"]) == sum(int(m["trades"]) for m in mine)
            assert bool(row["clean"]) == all(bool(m["clean"]) for m in mine)
            assert row["kind"] == "portfolio"
        if clean:
            want_clean_days.append(d)
    assert sorted(got["portfolio_clean"]) == want_clean_days
    # The scenario has days with members, days with none, and days whose
    # members are all exposed (trend_ma before its cutoff 2019-07-31).
    assert counted["members"] > 0 and counted["empty"] > 0
    assert len(want_clean_days) < counted["members"]


# ------------------------------------------------------------------ the table


def hand_table(state, setup_toml, records, sums, day) -> dict:
    """Decision 71's table of ``day``, counted here."""
    life = [r for r in read_jsonl(state / "ledger" / TRACK / "lifecycle.jsonl")
            if date.fromisoformat(r["date"]) <= day]
    trials = [r for r in read_jsonl(state / "ledger" / TRACK / "trials.jsonl")
              if date.fromisoformat(r["date"]) <= day]
    n = len(trials)
    approaches = {aid: m for aid, m in metas(state).items()
                  if date.fromisoformat(m["admitted"]) <= day}
    after = state_after(life, approaches, day)
    paper = records[records["date"] <= day]
    by_subject = {str(s): g.sort_values("date", kind="mergesort")
                  for s, g in paper.groupby("subject", sort=False)}
    slots = [f"rc:{k}" for k in range(setup_toml["random_pool"])]

    def record(subject):
        mine = by_subject.get(subject)
        d1 = [] if mine is None else [float(x) for x in mine["net_1x"]]
        d2 = [] if mine is None else [float(x) for x in mine["net_2x"]]
        return {"days": len(d1),
                "clean_days": 0 if mine is None else int(sum(bool(x) for x in mine["clean"])),
                "sharpe": own_sharpe(d1), "sharpe_2x": own_sharpe(d2),
                "trades": 0 if mine is None else int(sum(int(x) for x in mine["trades"])),
                "max_drawdown": own_drawdown(d1)}

    def breakeven(subject):
        mine = [v for d, *v in sums.get(subject, []) if d <= day]
        gross = math.fsum(v[0] for v in mine)
        turnover = math.fsum(v[1] for v in mine) + math.fsum(v[2] for v in mine)
        return gross / turnover * 10000.0 if turnover > 0 else math.nan

    def moments(days):
        sharpes = []
        for slot in slots:
            mine = by_subject.get(slot)
            held = {} if mine is None else dict(zip(mine["date"], mine["net_1x"], strict=True))
            if not days or any(d not in held for d in days):
                continue
            s = own_sharpe([float(held[d]) for d in days])
            if not math.isnan(s):
                sharpes.append(s)
        if len(sharpes) < 2:
            return math.nan, math.nan
        mu = math.fsum(sharpes) / len(sharpes)
        sd = math.sqrt(math.fsum((x - mu) ** 2 for x in sharpes) / (len(sharpes) - 1))
        return mu, sd

    def approach(section, aid):
        meta = approaches[aid]
        rec = record(aid)
        admitted = [t for t in trials if t["id"] == aid and t["admitted"]]
        mine = by_subject.get(aid)
        days = [] if mine is None else sorted(mine["date"])
        e = own_e(*moments(days), n)
        return {"section": section, "subject": aid, "cell": meta["cell"],
                "description": meta["description"], "model_id": meta["model_id"],
                "model_version": meta["model_version"], "admitted": meta["admitted"],
                "admission_score": admitted[-1]["metrics_t"]["sharpe"] if admitted else None,
                **rec, "breakeven_cost": breakeven(aid), "S": rec["sharpe"], "E_N": e,
                "excess": rec["sharpe"] - e,
                "state_history": [{"date": r["date"], "from": r["from"], "to": r["to"],
                                   "reason": r["reason"]} for r in life if r["id"] == aid]}

    def other(section, subject):
        return {"section": section, "subject": subject,
                **dict.fromkeys(("cell", "description", "model_id", "model_version",
                                 "admitted", "admission_score", "S", "E_N", "excess",
                                 "state_history")),
                **record(subject),
                "breakeven_cost": breakeven(subject) if section == "control" else None}

    live = sorted((approaches[a]["cell"], a) for a, s in after.items() if s == "live")
    dormant = sorted(a for a, s in after.items() if s == "dormant")
    rows = ([approach("live", a) for _, a in live]
            + [approach("dormant", a) for a in dormant]
            + [other("control", f"bh:{sym}") for sym in setup_toml["instruments"]]
            + [other("control", s) for s in slots]
            + [other("portfolio", s) for s in ("portfolio", "portfolio_clean")])
    return {"track": TRACK, "date": day.isoformat(), "N": n, "rows": rows}


@pytest.fixture(scope="module")
def setup_toml(ran):
    return read_setup_toml(ran[1])


def read_setup_toml(config) -> dict:
    with open(config / "tracks" / f"{TRACK}.toml", "rb") as f:
        track = tomllib.load(f)
    with open(config / "thresholds.toml", "rb") as f:
        th = tomllib.load(f)
    return {"instruments": track["instruments"], "random_pool": th["controls"]["random_pool"]}


@pytest.mark.parametrize("segment", [0, 1, 2])
def test_table_matches_a_hand_count(ran, records, journal_sums, setup_toml, segment):
    state, _, snaps = ran
    day = snaps[segment]["last"]
    got = snaps[segment]["table"]
    want = hand_table(state, setup_toml, records, journal_sums, day)
    assert {k: got[k] for k in ("track", "date", "N")} == {
        k: want[k] for k in ("track", "date", "N")}
    assert [(r["section"], r["subject"]) for r in got["rows"]] == [
        (r["section"], r["subject"]) for r in want["rows"]]
    for g, w in zip(got["rows"], want["rows"], strict=True):
        assert set(g) == set(w), g["subject"]
        for key in w:
            assert same(g[key], w[key]), (day, g["subject"], key, g[key], w[key])
    # What each table shows, by the scenario: 06-13 trend_ma live, the flat
    # one dormant, the two breaking ones retired and not listed; 08-13 the
    # same after trend_ma's return; the last day trend_ma dormant only.
    sections = {r["subject"]: r["section"] for r in got["rows"]}
    assert BREAK12 not in sections and BREAK13 not in sections
    if segment < 2:
        assert (sections[TREND], sections[FLAT]) == ("live", "dormant")
    else:
        assert sections[TREND] == "dormant" and FLAT not in sections
    assert len(got["rows"]) == len(want["rows"]) == {0: 2, 1: 2, 2: 1}[segment] + 4 + 50 + 2
