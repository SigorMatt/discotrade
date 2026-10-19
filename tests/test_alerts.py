"""The rank rows of the day loop on the timing statistic (DESIGN 11.1, 15.1,
16.1 step 6; owner decisions O-4, O-5, O-6, O-24; decisions 2026-10-12 59,
2026-10-17-m19 149).

``alerts.rank_rows`` is called on a state written under the test's tmp
directory by the writers the product uses (``paper.write`` for the paper
records, ``paper.write_exposure`` for the unit and position records), on the
fixture track ``test_synth`` (``epoch`` 2019-06-03, ``block_days`` 7, four
instruments on ``synth_week``, so the trading days of block 0 are 06-03..07
and of block 1 06-10..14), with the fixture configuration and the production
``config/thresholds.toml`` (``alerts.rank_min_population`` 5, asserted).

The values are drawn in the test from ``numpy.random.default_rng(SEED)`` with
the seed written here: each instrument's unit return ``R_i(D)`` per day; six
approaches ``lean0..lean5`` whose position on each instrument leans one way in
block 0 and another in block 1 and moves around that lean each day, their
gross the mean over the instruments of position times unit return plus a
draw, their costs a draw; and one approach ``const`` holding a constant
position on each instrument, its gross the mean of those positions times the
unit returns. Every expected figure is the test's own: ``hbar_i`` of a block
as the summed position over the row count of the block's days, the static
exposure as the mean over the instruments of ``hbar_i * R_i(D)``, the timing
sums with ``math.fsum``, the ranks by counting and the correlation with
``math``. Nothing here calls ``paper.adjusted`` or ``stats.rank_persistence``
for an expected value. The tests prove the rows on these inputs only.

The finding rules ``persistent_approach`` and ``group_edge`` (decision
2026-10-17-m19 151) are tested in the second half of this module, on states of
their own; its section comment says how.
"""

import json
import math
import shutil
import statistics
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from discotrade import alerts, journal, ledger, paper, stats
from discotrade import state as state_mod
from discotrade.cli import REPO_ROOT
from discotrade.config import load_models

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
SEED = 20191017
SYMBOLS = ("SYNA", "SYNB", "SYNC", "SYND")
BLOCK_0 = [date(2019, 6, 3) + timedelta(days=i) for i in range(5)]
BLOCK_1 = [date(2019, 6, 10) + timedelta(days=i) for i in range(5)]
DAYS = BLOCK_0 + BLOCK_1
ROWS = 10                                   # journal rows per subject, instrument and day
CONST = (1.0, -0.5, 0.25, 0.8)              # const's position on each instrument
LEANS = [((1.5, 0.5, -1.0, 0.0), (-1.0, 1.0, 0.5, -0.5)),
         ((-0.5, 1.5, 0.0, 1.0), (1.0, -1.0, 1.5, 0.0)),
         ((0.0, -1.0, 1.0, 1.5), (0.5, 0.5, -1.5, 1.0)),
         ((1.0, 1.0, 1.0, 1.0), (-1.0, -1.0, -1.0, -1.0)),
         ((-1.5, 0.0, 0.5, -0.5), (1.5, 0.0, -0.5, 0.5)),
         ((0.5, -0.5, 1.5, -1.5), (0.0, 1.5, -0.5, 1.0))]
OLD_KEYS = {"block", "first", "last", "previous_first", "previous_last", "subjects", "size",
            "statistic"}


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    config = tmp_path_factory.mktemp("alcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, config)
    shutil.copyfile(REPO_ROOT / "config" / "thresholds.toml", config / "thresholds.toml")
    return journal.Setup.load(config, TRACK)


def test_the_fixture_and_production_values(setup):
    assert tuple(sorted(i.symbol for i in setup.instruments)) == SYMBOLS
    assert setup.track.epoch == date(2019, 6, 3) and setup.track.block_days == 7
    assert int(setup.thresholds["alerts.rank_min_population"]) == 5
    assert all(d.weekday() < 5 for d in DAYS)


def draw():
    """The test's inputs: unit returns, positions and paper rows, all drawn here."""
    rng = np.random.default_rng(SEED)
    unit = {(s, d): float(rng.normal(0.002, 0.01)) for d in DAYS for s in SYMBOLS}
    held = {}                                # (subject, symbol, day) -> position per row
    gross, cost = {}, {}
    for j, (lean_0, lean_1) in enumerate(LEANS):
        name = f"lean{j}"
        for d in DAYS:
            lean = lean_0 if d in BLOCK_0 else lean_1
            for s, h in zip(SYMBOLS, lean, strict=True):
                held[(name, s, d)] = h + float(rng.normal(0.0, 0.3))
            gross[(name, d)] = (math.fsum(held[(name, s, d)] * unit[(s, d)] for s in SYMBOLS)
                                / 4 + float(rng.normal(0.0, 0.004)))
            cost[(name, d)] = float(rng.uniform(0.0, 0.01))
    for d in DAYS:
        for s, h in zip(SYMBOLS, CONST, strict=True):
            held[("const", s, d)] = h
        gross[("const", d)] = math.fsum(h * unit[(s, d)]
                                        for s, h in zip(SYMBOLS, CONST, strict=True)) / 4
        cost[("const", d)] = float(rng.uniform(0.0, 0.01))
    return unit, held, gross, cost


def write_state(root):
    unit, held, gross, cost = draw()
    records = pd.DataFrame([{"date": d, "subject": subject, "kind": paper.APPROACH,
                             "gross": g, "net_1x": g - cost[(subject, d)],
                             "net_2x": g - 2 * cost[(subject, d)], "trades": 1, "clean": True}
                            for (subject, d), g in sorted(gross.items())])
    paper.write(root, TRACK, records)
    units = pd.DataFrame([{"instrument": s, "date": d, "unit": v}
                          for (s, d), v in sorted(unit.items())])
    positions = pd.DataFrame([{"subject": subject, "instrument": s, "date": d, "rows": ROWS,
                               "position": ROWS * h}
                              for (subject, s, d), h in sorted(held.items())])
    paper.write_exposure(root, TRACK, units, positions)
    return unit, held, gross, cost


@pytest.fixture(scope="module")
def state(tmp_path_factory):
    root = tmp_path_factory.mktemp("alstate") / "state"
    return root, write_state(root)


def subjects(setup):
    basket = [setup.calendars[inst.calendar] for inst in setup.instruments]
    return {name: basket for name in ["const"] + [f"lean{j}" for j in range(len(LEANS))]}


def own_ranks(values):
    return [sum(1 for w in values if w < v) + (sum(1 for w in values if w == v) + 1) / 2
            for v in values]


def own_spearman(x, y):
    rx, ry = own_ranks(x), own_ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den


def own_hbar(held, subject, window):
    """``hbar_i`` over ``window``: summed position over the row count."""
    return {s: math.fsum(ROWS * held[(subject, s, d)] for d in window) / (ROWS * len(window))
            for s in SYMBOLS}


def own_timing(unit, held, gross, subject, block, window):
    """The subject's gross timing return on each day of ``block``, its average
    positions taken over ``window`` (the block itself, under O-5)."""
    hbar = own_hbar(held, subject, window)
    return [gross[(subject, d)] - math.fsum(hbar[s] * unit[(s, d)] for s in SYMBOLS) / 4
            for d in block]


def own_statistics(unit, held, gross, cost, names):
    sums = {"timing": ([], []), "one_window": ([], []), "gross": ([], []), "net_1x": ([], [])}
    for name in names:
        for b, block in enumerate((BLOCK_0, BLOCK_1)):
            sums["timing"][b].append(math.fsum(own_timing(unit, held, gross, name, block,
                                                          block)))
            sums["one_window"][b].append(math.fsum(own_timing(unit, held, gross, name, block,
                                                              DAYS)))
            sums["gross"][b].append(math.fsum(gross[(name, d)] for d in block))
            sums["net_1x"][b].append(math.fsum(gross[(name, d)] - cost[(name, d)]
                                               for d in block))
    return {k: own_spearman(*v) for k, v in sums.items()}


def test_a_constant_position_approach_has_a_timing_return_of_zero_on_every_day(setup, state):
    root, _ = state
    frames = []
    alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1],
                     frames=frames)
    [frame] = frames
    mine = frame[frame["subject"] == "const"]
    assert sorted(mine["date"]) == DAYS
    assert all(abs(float(v)) <= 1e-12 for v in mine["timing"])
    # the leaning approaches' timing returns are not zero, so the bound says something
    lean = frame[frame["subject"] == "lean0"]
    assert max(abs(float(v)) for v in lean["timing"]) > 1e-4


def test_the_row_holds_timing_and_gross_beside_decision_59s_net_statistic(setup, state):
    root, (unit, held, gross, cost) = state
    [row] = alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1])
    names = sorted(subjects(setup))
    own = own_statistics(unit, held, gross, cost, names)
    # the test's inputs tell the four figures apart, so each wrong reading shows
    for a, b in (("timing", "gross"), ("timing", "net_1x"), ("timing", "one_window"),
                 ("gross", "net_1x")):
        assert abs(own[a] - own[b]) > 1e-3, (a, b, own)
    assert set(row) == OLD_KEYS | {"timing", "gross"}
    assert row["subjects"] == names and row["size"] == len(names)
    assert (row["block"], row["first"], row["last"], row["previous_first"],
            row["previous_last"]) == (1, "2019-06-10", "2019-06-16", "2019-06-03",
                                      "2019-06-09")
    assert abs(row["timing"] - own["timing"]) <= 1e-12
    assert abs(row["gross"] - own["gross"]) <= 1e-12
    assert abs(row["statistic"] - own["net_1x"]) <= 1e-12     # decision 59's, unchanged


def test_exposure_records_passed_give_the_rows_read_from_the_files(setup, state):
    root, _ = state
    records = paper.read(root, TRACK)
    exposure = (paper.read_unit(root, TRACK), paper.read_positions(root, TRACK))
    read = alerts.rank_rows(root, setup, records, subjects(setup), [1])
    given = alerts.rank_rows(root, setup, records, subjects(setup), [1], exposure=exposure)
    assert given == read


def test_rows_appended_again_append_nothing(tmp_path, setup, state):
    root = tmp_path / "state"
    shutil.copytree(state[0], root)
    rows = alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1])
    assert stats.append_rank_rows(root, TRACK, rows) == rows
    before = stats.rank_path(root, TRACK).read_bytes()
    again = alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), [1])
    assert again == rows
    assert stats.append_rank_rows(root, TRACK, again) == []
    assert stats.rank_path(root, TRACK).read_bytes() == before


def test_an_empty_population_gives_every_statistic_null(setup, state):
    root, _ = state
    [row] = alerts.rank_rows(root, setup, paper.read(root, TRACK), {}, [1])
    assert row["size"] == 0 and row["subjects"] == []
    assert row["statistic"] is None and row["timing"] is None and row["gross"] is None


def test_below_the_minimum_population_every_statistic_is_null(setup, state):
    root, _ = state
    few = dict(list(subjects(setup).items())[:4])
    [row] = alerts.rank_rows(root, setup, paper.read(root, TRACK), few, [1])
    assert row["size"] == 4
    assert row["statistic"] is None and row["timing"] is None and row["gross"] is None


def test_no_due_block_gives_no_row(setup, state):
    root, _ = state
    assert alerts.rank_rows(root, setup, paper.read(root, TRACK), subjects(setup), []) == []


# ===================================================================================
# persistent_approach and group_edge on the exposure-adjusted series (DESIGN 15.1,
# 11.2 to 11.4; owner decisions O-7, O-16, O-24; decision 2026-10-17-m19 151).
#
# Each state is written under the test's tmp directory by the product's writers
# (``state.write_approach``, ``ledger.append`` for the trials ledger, ``paper.write``
# with ``paper.portfolio``'s rows, ``paper.write_exposure``), with every value drawn
# here from ``numpy.random.default_rng`` with a seed written here, on the fixture
# track ``test_synth`` and the production ``config/thresholds.toml`` read through
# the config loader (``journal.Setup.load``). The approaches' series are built so
# that the exposure-adjusted figures land where each test needs them, by the test's
# own arithmetic (a shift of a drawn noise series); every expected figure is the
# test's own: ``hbar_i`` as the summed position over the row count of ``W``, the
# static exposure as the mean over the instruments of ``hbar_i * R_i(D)``, Sharpes
# by DESIGN 8 with decision 30 (``own_sharpe``), the normal quantile by bisection on
# ``math.erf`` (decision 60), the bootstrap's draws with the generator the decision
# names and its quantile by numpy's default (linear) rule written out here.
# Nothing here calls ``paper.adjusted``, ``stats`` or ``alerts`` for an expected
# figure. The tests prove the rules on these inputs only.
# ===================================================================================

PERIODS = 252
N_TRIALS = 20                         # the trials ledger's rows: p(N) tightens to 0.975
P_SEED, G_SEED = 151_001, 151_002     # the two states' draws
DRIFT = 0.005                         # the mean unit return: a rising market
P_SLOTS, G_SLOTS = 8, 12
MARGIN = 0.25                         # annualised Sharpe on each side of a threshold
G_MARGIN = 0.01                       # summed return on each side of the quantile


def weekdays(first, n):
    out, d = [], first
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


P_DAYS = weekdays(date(2019, 6, 3), 65)
G_DAYS = weekdays(date(2019, 6, 3), 120)
G_SAT = G_DAYS[-1] + timedelta(days=1)


def own_sharpe(d):
    """DESIGN 8 with decision 30 (not a number with fewer than 2 values, or no deviation)."""
    d = [float(x) for x in d]
    if len(d) < 2 or all(x == d[0] for x in d):
        return math.nan
    sd = statistics.stdev(d)
    if not sd > 1e-12 * max(abs(x) for x in d):
        return math.nan
    return statistics.fmean(d) / sd * math.sqrt(PERIODS)


def z_bisect(p):
    """The standard normal quantile by bisection on math.erf / math.erfc (decision 60)."""
    def below(x):
        if p > 0.5:
            return 0.5 * math.erfc(x / math.sqrt(2.0)) > 1.0 - p
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0))) < p
    lo, hi = -40.0, 40.0
    for _ in range(400):
        mid = (lo + hi) / 2
        if hi - lo <= 1e-15 or mid in (lo, hi):
            break
        lo, hi = (mid, hi) if below(mid) else (lo, mid)
    return (lo + hi) / 2


def own_threshold(mu, sd, n, base, per_year):
    p = 1 - min(1 - base, per_year / max(n, 1))
    return mu + z_bisect(p) * sd, p


def close(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))


def thresholds_of(setup):
    t = setup.thresholds
    return {k: t[k] for k in ("alerts.persistent_min_days", "alerts.persistent_base_percentile",
                              "alerts.false_alerts_per_year", "alerts.group_days",
                              "alerts.group_level", "alerts.group_bootstrap")}


def test_the_rules_read_the_production_thresholds(setup):
    t = thresholds_of(setup)
    assert t == {"alerts.persistent_min_days": 60, "alerts.persistent_base_percentile": 0.95,
                 "alerts.false_alerts_per_year": 0.5, "alerts.group_days": 120,
                 "alerts.group_level": 0.05, "alerts.group_bootstrap": 1000}
    assert set(alerts.THRESHOLD_KEYS[alerts.PERSISTENT]) == {
        "alerts.persistent_min_days", "alerts.persistent_base_percentile",
        "alerts.false_alerts_per_year"}
    assert set(alerts.THRESHOLD_KEYS[alerts.GROUP]) == {
        "alerts.group_days", "alerts.group_level", "alerts.group_bootstrap"}


# ------------------------------------------------------------------ the inputs


def draw_unit(rng, days):
    return {(s, d): float(rng.normal(DRIFT, 0.01)) for d in days for s in SYMBOLS}


def draw_slots(rng, days, unit, count):
    """Random slots ``rc:0..``: each leans its own way (from -0.5 to 0.5) on every
    instrument and moves around that lean each day; its gross the mean over the
    instruments of position times unit return plus a draw. Subject rows map a day
    to (positions, gross, net_1x, net_2x)."""
    out = {}
    for j in range(count):
        lean = -0.5 + j / (count - 1)
        rows = {}
        for d in days:
            h = tuple(lean + float(rng.normal(0.0, 0.5)) for _ in SYMBOLS)
            g = (math.fsum(x * unit[(s, d)] for s, x in zip(SYMBOLS, h, strict=True)) / 4
                 + float(rng.normal(0.0, 0.003)))
            cost = float(rng.uniform(0.0, 0.001))
            rows[d] = (h, g, g - cost, g - 2 * cost)
        out[f"rc:{j}"] = rows
    return out


def own_hbar_of(rows, window):
    return [math.fsum(ROWS * rows[d][0][i] for d in window) / (ROWS * len(window))
            for i in range(len(SYMBOLS))]


def own_exposure(unit, hbar, d):
    return math.fsum(hbar[i] * unit[(s, d)] for i, s in enumerate(SYMBOLS)) / 4


def own_adjusted(unit, rows, window, at=2, days=None):
    """The subject's ``rows[d][at]`` (2 net_1x, 3 net_2x) less its static exposure on
    each day of ``days`` (``window`` by default), ``hbar`` over ``window``."""
    hbar = own_hbar_of(rows, window)
    return [rows[d][at] - own_exposure(unit, hbar, d) for d in (window if days is None
                                                                  else days)]


def own_moments(unit, slots, window, adjusted=True):
    sharpes = [own_sharpe(own_adjusted(unit, rows, window) if adjusted
                          else [rows[d][2] for d in window]) for rows in slots.values()]
    sharpes = [s for s in sharpes if not math.isnan(s)]
    return statistics.fmean(sharpes), statistics.stdev(sharpes)


def make_approach(rng, unit, days, window, lean, t1, t2, outside=0.0):
    """An approach with rows on ``days``, leaning ``lean``, whose adjusted net 1x
    Sharpe over ``window`` is ``t1`` and adjusted net 2x Sharpe ``t2``, by the test's
    own shift of drawn noise; on a day outside ``window`` its value is drawn the same
    way, shifted by the same constant plus ``outside``."""
    held = {d: tuple(lean + float(rng.normal(0.0, 0.5)) for _ in SYMBOLS) for d in days}
    hbar = [math.fsum(held[d][i] for d in window) / len(window) for i in range(len(SYMBOLS))]
    z = {d: float(rng.normal(0.0, 0.01)) for d in days}
    u = {d: float(rng.uniform(0.0, 0.0005)) for d in days}
    zw = [z[d] for d in window]
    c = t1 * statistics.stdev(zw) / math.sqrt(PERIODS) - statistics.fmean(zw)
    diff = [c + z[d] - u[d] for d in window]
    kappa = statistics.fmean(diff) - t2 * statistics.stdev(diff) / math.sqrt(PERIODS)
    assert kappa >= 0.0                       # every cost the test writes is a cost
    rows = {}
    for d in days:
        net = c + z[d] + own_exposure(unit, hbar, d) + (0.0 if d in window else outside)
        cost = kappa + u[d]
        rows[d] = (held[d], net + cost, net, net - cost)
    return rows


def trial_row(k, day):
    return {"date": day.isoformat(), "id": f"t{k:02d}", "cell": "trend/short",
            "model_id": "test-model", "model_version": "test-model-v0", "cutoff": "2019-01-01",
            "code_sha256": "0" * 64, "profile_version": "w-test", "cost_model": "c",
            "config_hash": "0" * 64, "grid": None, "params": {}, "metrics_w": None,
            "metrics_t": None, "admitted": False, "reason": "test", "displaced": None,
            "adjusted_t": None, "adjusted_w": None}


def write_alert_state(root, setup, unit, days, subjects, approaches, *, portfolio=False):
    """``subjects`` maps a name to (kind, rows); ``approaches`` maps an approach name to
    (cutoff, admitted). Returns name -> subject id."""
    ids = {}
    for name, (cutoff, admitted) in approaches.items():
        ids[name] = state_mod.write_approach(
            root, source=f"# approach {name}\n", params={}, cell="trend/short",
            model_id="test-model", model_version="test-model-v0", cutoff=cutoff,
            description=f"the approach {name}", profile_version="w-test", admitted=admitted,
            instruments=setup.instruments, spread_tables=setup.spread_tables)
    for name in subjects:
        ids.setdefault(name, name)
    ledger.append(root, TRACK, ledger.TRIALS, [trial_row(k, days[0]) for k in range(N_TRIALS)])
    records, positions = [], []
    for name, (kind, rows) in subjects.items():
        for d, (h, g, n1, n2) in sorted(rows.items()):
            clean = kind != paper.APPROACH or d > approaches[name][0]
            records.append({"date": d, "subject": ids[name], "kind": kind, "gross": g,
                            "net_1x": n1, "net_2x": n2, "trades": 1, "clean": clean})
            positions += [{"subject": ids[name], "instrument": s, "date": d, "rows": ROWS,
                           "position": ROWS * x} for s, x in zip(SYMBOLS, h, strict=True)]
    frame = pd.DataFrame(records)[list(paper.COLUMNS)]
    if portfolio:
        frame = pd.concat([frame, paper.portfolio(frame, days, [],
                                                  state_mod.read_approaches(root))],
                          ignore_index=True)
    paper.write(root, TRACK, frame.sort_values(list(paper.KEY), kind="stable")
                .reset_index(drop=True))
    units = pd.DataFrame([{"instrument": s, "date": d, "unit": v}
                          for (s, d), v in sorted(unit.items())])
    held = pd.DataFrame(positions).sort_values(list(paper.POSITIONS_KEY), kind="stable")
    paper.write_exposure(root, TRACK, units, held.reset_index(drop=True))
    return ids


# ------------------------------------------------------------ persistent_approach

#: Each approach: (first and last day index of its rows, index of its cutoff day
#: (clean after it), its lean). W60 = days 5..64, W59 = days 6..64.
P_SPEC = {"above": (5, 64, 4, 0.3), "below": (5, 64, 4, -0.3), "costly": (5, 64, 4, 0.2),
          "short59": (6, 64, 5, 0.3), "exposed": (1, 64, 5, -0.2), "long": (5, 64, 4, None)}


@pytest.fixture(scope="module")
def persistent(tmp_path_factory, setup):
    t = thresholds_of(setup)
    base, per_year = t["alerts.persistent_base_percentile"], t["alerts.false_alerts_per_year"]
    root = tmp_path_factory.mktemp("persist") / "state"
    rng = np.random.default_rng(P_SEED)
    unit = draw_unit(rng, P_DAYS)
    slots = draw_slots(rng, P_DAYS, unit, P_SLOTS)
    windows = {name: P_DAYS[cut + 1:last + 1] for name, (_, last, cut, _) in P_SPEC.items()}
    thr = {}
    for name, w in windows.items():
        thr[name] = own_threshold(*own_moments(unit, slots, w), N_TRIALS, base, per_year)[0]
    targets = {"above": (thr["above"] + MARGIN, 0.5), "below": (thr["below"] - MARGIN, 0.5),
               "costly": (thr["costly"] + MARGIN, -MARGIN),
               "short59": (thr["short59"] + MARGIN, 0.5),
               "exposed": (thr["exposed"] + MARGIN, 0.5)}
    subjects = {k: (stats.CONTROL_RANDOM, rows) for k, rows in slots.items()}
    for name, (t1, t2) in targets.items():
        first, last, _, lean = P_SPEC[name]
        # the exposed approach's 5 exposed days earn 1% a day more than its clean ones
        subjects[name] = (paper.APPROACH, make_approach(
            rng, unit, P_DAYS[first:last + 1], windows[name], lean, t1, t2,
            0.01 if name == "exposed" else 0.0))
    long_rows = {}
    for d in P_DAYS[5:]:
        g = math.fsum(unit[(s, d)] for s in SYMBOLS) / 4
        cost = float(rng.uniform(0.0, 0.0005))
        long_rows[d] = ((1.0,) * 4, g, g - cost, g - 2 * cost)
    subjects["long"] = (paper.APPROACH, long_rows)
    admitted = P_DAYS[0] - timedelta(days=7)
    ids = write_alert_state(root, setup, unit, P_DAYS, subjects,
                            {name: (P_DAYS[cut], admitted)
                             for name, (_, _, cut, _) in P_SPEC.items()})
    day = P_DAYS[-1]
    got = alerts.persistent_approach(root, setup, day, paper.read(root, TRACK))
    by_name = {name: next(e for e in got if e["subject"] == ids[name]) for name in P_SPEC}
    return {"root": root, "unit": unit, "slots": slots, "subjects": subjects, "ids": ids,
            "windows": windows, "got": got, "by_name": by_name, "base": base,
            "per_year": per_year}


def own_persistent(p, name, window=None):
    """The test's own figures and condition for ``name`` over ``window`` (its clean
    days by default)."""
    w = p["windows"][name] if window is None else window
    rows = p["subjects"][name][1]
    mu, sd = own_moments(p["unit"], p["slots"], w)
    thr, p_n = own_threshold(mu, sd, N_TRIALS, p["base"], p["per_year"])
    s1 = own_sharpe(own_adjusted(p["unit"], rows, w, 2))
    s2 = own_sharpe(own_adjusted(p["unit"], rows, w, 3))
    return {"s1": s1, "s2": s2, "plain1": own_sharpe([rows[d][2] for d in w]),
            "plain2": own_sharpe([rows[d][3] for d in w]), "mu": mu, "sd": sd, "thr": thr,
            "p_n": p_n, "days": len(w), "meets": len(w) >= 60 and s2 > 0 and s1 > thr}


def test_persistent_entries_hold_the_tests_own_figures(setup, persistent):
    p = persistent
    approaches = {a.id: a for a in state_mod.read_approaches(p["root"])}
    assert sorted(e["subject"] for e in p["got"]) == sorted(approaches)
    for name, entry in p["by_name"].items():
        own = own_persistent(p, name)
        pay = entry["payload"]
        assert entry["kind"] == alerts.PERSISTENT
        assert close(entry["value"], own["s1"]), name
        assert close(entry["threshold"], own["thr"]), name
        assert close(pay["adjusted_sharpe"], own["s1"]) and close(pay["adjusted_sharpe_2x"],
                                                                   own["s2"]), name
        assert close(pay["sharpe"], own["plain1"]) and close(pay["sharpe_2x"], own["plain2"])
        assert close(pay["mu_c"], own["mu"]) and close(pay["sd_c"], own["sd"]), name
        assert pay["N"] == N_TRIALS and close(pay["p_N"], own["p_n"]) and own["p_n"] == 0.975
        assert close(pay["threshold"], own["thr"])
        first, last, cut, _ = P_SPEC[name]
        assert pay["days"] == own["days"] == last - cut
        assert (pay["clean_days"], pay["exposed_days"]) == (last - cut, cut + 1 - first)
        assert pay["thresholds"] == {k: v for k, v in thresholds_of(setup).items()
                                     if k in alerts.THRESHOLD_KEYS[alerts.PERSISTENT]}
        meta = approaches[entry["subject"]].meta
        assert pay["description"] == meta["description"] == f"the approach {name}"
        assert pay["source"] == f"# approach {name}\n"
        assert (pay["cell"], pay["model_id"], pay["model_version"]) == (
            meta["cell"], meta["model_id"], meta["model_version"])
        assert entry["active"] is own["meets"], name


def test_persistent_day_count_59_and_60(setup, persistent):
    p = persistent
    assert int(setup.thresholds["alerts.persistent_min_days"]) == 60
    above, short = own_persistent(p, "above"), own_persistent(p, "short59")
    assert above["days"] == 60 and short["days"] == 59
    # 59 clean days with both Sharpes on the passing side: not met for the count alone
    assert short["s2"] > 0 and short["s1"] > short["thr"]
    assert p["by_name"]["short59"]["active"] is False
    assert above["s2"] > 0 and above["s1"] > above["thr"]
    assert p["by_name"]["above"]["active"] is True


def test_persistent_2x_sharpe_on_both_sides_of_zero(persistent):
    p = persistent
    above, costly = own_persistent(p, "above"), own_persistent(p, "costly")
    assert costly["days"] == 60 and costly["s1"] > costly["thr"]
    assert costly["s2"] < 0 < above["s2"]
    assert p["by_name"]["costly"]["active"] is False
    assert p["by_name"]["above"]["active"] is True


def test_persistent_1x_threshold_on_both_sides(persistent):
    p = persistent
    above, below = own_persistent(p, "above"), own_persistent(p, "below")
    assert below["days"] == 60 and below["s2"] > 0
    assert below["s1"] < below["thr"] and above["s1"] > above["thr"]
    assert p["by_name"]["below"]["active"] is False
    assert p["by_name"]["above"]["active"] is True


def test_persistent_leaves_exposed_days_out_of_w(persistent):
    p = persistent
    entry = p["by_name"]["exposed"]
    clean = own_persistent(p, "exposed")
    assert clean["days"] == 59 and entry["payload"]["days"] == 59
    assert entry["payload"]["exposed_days"] == 5
    # Counted with its 5 exposed days, W would hold 64 days and meet the condition.
    first, last, _, _ = P_SPEC["exposed"]
    every = own_persistent(p, "exposed", P_DAYS[first:last + 1])
    assert every["days"] == 64 and every["meets"]
    assert entry["active"] is False


def test_a_long_leaning_approach_with_no_timing_does_not_meet_the_adjusted_condition(
        persistent):
    p = persistent
    w = p["windows"]["long"]
    rows = p["subjects"]["long"][1]
    own = own_persistent(p, "long")
    plain_thr, _ = own_threshold(*own_moments(p["unit"], p["slots"], w, adjusted=False),
                                 N_TRIALS, p["base"], p["per_year"])
    # the plain reading would have crossed: 60 clean days, plain 2x positive, plain 1x
    # above the threshold from the slots' plain net 1x
    assert len(w) == 60 and own["plain2"] > 0 and own["plain1"] > plain_thr
    # with no timing, its adjusted series is minus its costs
    assert own["s1"] < 0
    assert all(abs(a + (rows[d][1] - rows[d][2])) <= 1e-12
               for a, d in zip(own_adjusted(p["unit"], rows, w), w, strict=True))
    assert p["by_name"]["long"]["active"] is False


# ------------------------------------------------------------------ group_edge


def own_members(cutoff_r, ids, w):
    return {d: sorted([ids["P"], ids["Q"]] + ([ids["R"]] if d > cutoff_r else [])) for d in w}


def own_quantile(values, q):
    """numpy's default (linear) quantile, written out."""
    x = sorted(values)
    h = (len(x) - 1) * q
    lo = math.floor(h)
    return x[lo] + (h - lo) * (x[min(lo + 1, len(x) - 1)] - x[lo])


def own_group_figure(unit, subjects, members, w):
    by_id = {}
    for m in sorted({m for ms in members.values() for m in ms}):
        days = [d for d in w if m in members[d]]
        by_id[m] = dict(zip(days, own_adjusted(unit, subjects[m][1], days), strict=True))
    return math.fsum(math.fsum(by_id[m][d] for m in members[d]) / len(members[d]) for d in w)


def own_bootstrap(unit, slots, w, k, seed, count, level):
    series = [own_adjusted(unit, slots[f"rc:{j}"], w) for j in range(len(slots))]
    rng = np.random.default_rng(seed)
    figures = []
    for _ in range(count):
        pick = [int(j) for j in rng.choice(len(series), size=k, replace=False)]
        figures.append(math.fsum(math.fsum(series[j][t] for j in pick) / k
                                 for t in range(len(w))))
    return own_quantile(figures, 1 - level)


def seed(day):
    return int(day.strftime("%Y%m%d"))


#: Each group state: R's cutoff day index (R clean after it) and the side of the
#: quantile its figure is put on. R clean on 60 of 120 days: mean count 2.5, k 3;
#: on 59: 299 / 120, k 2.
G_SPEC = {"k3_above": (59, 1), "k3_below": (59, -1), "k2_above": (60, 1)}


@pytest.fixture(scope="module")
def group(tmp_path_factory, setup):
    t = thresholds_of(setup)
    count, level = int(t["alerts.group_bootstrap"]), float(t["alerts.group_level"])
    out = {}
    for name, (cut, side) in G_SPEC.items():
        root = tmp_path_factory.mktemp(f"group_{name}") / "state"
        rng = np.random.default_rng(G_SEED)
        unit = draw_unit(rng, G_DAYS)
        slots = draw_slots(rng, G_DAYS, unit, G_SLOTS)
        cutoff_r = G_DAYS[cut]
        k = 3 if cut == 59 else 2
        thr = [own_bootstrap(unit, slots, G_DAYS, k, seed(d), count, level)
               for d in (G_DAYS[-1], G_SAT)]
        target = max(thr) + G_MARGIN if side > 0 else min(thr) - G_MARGIN
        held, z = {}, {}
        for m in ("P", "Q", "R"):
            held[m] = {d: tuple(0.4 + float(rng.normal(0.0, 0.5)) for _ in SYMBOLS)
                       for d in G_DAYS}
            z[m] = {d: float(rng.normal(0.0, 0.004)) for d in G_DAYS}
        members = {d: ["P", "Q"] + (["R"] if d > cutoff_r else []) for d in G_DAYS}
        f0 = math.fsum(math.fsum(z[m][d] for m in members[d]) / len(members[d]) for d in G_DAYS)
        c = (target - f0) / len(G_DAYS)
        subjects = {k_: (stats.CONTROL_RANDOM, rows) for k_, rows in slots.items()}
        for m in ("P", "Q", "R"):
            mine = [d for d in G_DAYS if m in members[d]]
            hbar = [math.fsum(held[m][d][i] for d in mine) / len(mine)
                    for i in range(len(SYMBOLS))]
            rows = {}
            for d in G_DAYS:
                net = c + z[m][d] + own_exposure(unit, hbar, d)
                cost = 0.0005
                rows[d] = (held[m][d], net + cost, net, net - cost)
            subjects[m] = (paper.APPROACH, rows)
        before = G_DAYS[0] - timedelta(days=1)
        admitted = G_DAYS[0] - timedelta(days=7)
        ids = write_alert_state(root, setup, unit, G_DAYS, subjects,
                                {"P": (before, admitted), "Q": (before, admitted),
                                 "R": (cutoff_r, admitted)}, portfolio=True)
        named = {ids.get(n, n): s for n, s in subjects.items()}
        out[name] = {"root": root, "unit": unit, "slots": slots, "ids": ids, "k": k,
                     "subjects": named, "cutoff_r": cutoff_r, "count": count, "level": level,
                     "records": paper.read(root, TRACK)}
    return out


def run_group(g, setup, day):
    return alerts.group_edge(g["root"], setup, day, g["records"])


def own_group(g, day):
    w = G_DAYS
    members = own_members(g["cutoff_r"], g["ids"], w)
    mean = sum(len(v) for v in members.values()) / len(w)
    k = max(1, math.floor(mean + 0.5))
    return {"figure": own_group_figure(g["unit"], g["subjects"], members, w), "k": k,
            "mean": mean,
            "thr": own_bootstrap(g["unit"], g["slots"], w, k, seed(day), g["count"], g["level"]),
            "members": sorted({m for v in members.values() for m in v})}


def test_group_days_119_and_120_dates(setup, group):
    g = group["k3_above"]
    assert int(setup.thresholds["alerts.group_days"]) == 120
    clean = g["records"][g["records"]["subject"] == paper.PORTFOLIO_CLEAN]
    assert sorted(clean["date"]) == G_DAYS
    early = run_group(g, setup, G_DAYS[-2])                 # 119 dates on or before D
    assert (early["active"], early["value"], early["threshold"]) == (False, None, None)
    late = run_group(g, setup, G_DAYS[-1])                  # 120 dates
    own = own_group(g, G_DAYS[-1])
    assert close(late["value"], own["figure"], 1e-12) and close(late["threshold"], own["thr"],
                                                                 1e-12)
    assert own["figure"] > own["thr"] and late["active"] is True


def test_group_edge_holds_the_tests_own_figure_bootstrap_and_payload(setup, group):
    g = group["k3_above"]
    got = run_group(g, setup, G_SAT)                        # D after W's last date
    own = own_group(g, G_SAT)
    pay = got["payload"]
    assert got["kind"] == alerts.GROUP and got["subject"] == TRACK
    assert close(got["value"], own["figure"], 1e-12) and close(pay["figure"], own["figure"],
                                                                1e-12)
    assert close(got["threshold"], own["thr"], 1e-12) and close(pay["threshold"], own["thr"],
                                                                 1e-12)
    # the date's seed matters: W's last date or another day's would give another quantile
    for other in (G_DAYS[-1], G_DAYS[0]):
        assert abs(own_bootstrap(g["unit"], g["slots"], G_DAYS, own["k"], seed(other),
                                 g["count"], g["level"]) - own["thr"]) > 1e-6
    assert pay["seed"] == 20191116 == seed(G_SAT)
    assert (pay["k"], pay["bootstrap"]) == (own["k"], 1000)
    assert pay["members"] == own["members"]
    clean = g["records"][g["records"]["subject"] == paper.PORTFOLIO_CLEAN]
    assert close(pay["plain"], math.fsum(float(x) for x in clean["net_1x"]), 1e-12)
    assert abs(pay["plain"] - pay["figure"]) > 1e-3        # the plain figure is not the rule's
    assert (pay["first"], pay["last"], pay["days"]) == (G_DAYS[0].isoformat(),
                                                        G_DAYS[-1].isoformat(), 120)
    assert pay["thresholds"] == {k: v for k, v in thresholds_of(setup).items()
                                 if k in alerts.THRESHOLD_KEYS[alerts.GROUP]}
    assert got["active"] is True


def test_group_quantile_on_both_sides(setup, group):
    for name, side in (("k3_above", True), ("k3_below", False)):
        g = group[name]
        got = run_group(g, setup, G_SAT)
        own = own_group(g, G_SAT)
        assert close(got["value"], own["figure"], 1e-12)
        assert close(got["threshold"], own["thr"], 1e-12)
        assert (own["figure"] > own["thr"]) is side
        assert got["active"] is side, name


def test_k_is_the_mean_member_count_rounded_half_up(setup, group):
    for name, mean, k in (("k3_above", 2.5, 3), ("k2_above", 299 / 120, 2)):
        g = group[name]
        own = own_group(g, G_SAT)
        assert own["mean"] == mean and own["k"] == k == g["k"]
        got = run_group(g, setup, G_SAT)
        assert got["payload"]["k"] == k, name
        assert close(got["threshold"], own["thr"], 1e-12), name
        assert got["active"] is True, name


# ===================================================================================
# The alert state, the firing, the payloads, the ``rank_persistence`` and ``revival``
# rules, the health alerts and the detectors (DESIGN 15.1 to 15.3; decision
# 2026-10-17-m19 152).
#
# Each state is written under the test's tmp directory by the product's writers
# (``stats.append_rank_rows``, ``ledger.append``, ``state.write_approach``,
# ``state.append_health``, ``paper.write``), with every value and seed written here,
# on the fixture track ``test_synth`` (trading days Monday to Friday, the one closure
# 2019-07-04 avoided) and the production ``config/thresholds.toml`` read through the
# config loader. Every expected figure is the test's own: the mean, the sample
# deviation and t with ``math`` and ``statistics``, the one-sided 5% critical value
# at 11 degrees of freedom written as the literal 1.795884819, trading days counted
# as weekdays. The tests prove these functions on these inputs only.
# ===================================================================================

T_CRIT_11 = 1.795884819               # the one-sided 5% critical value of t at 11 df
R_SEED = 152_001
HEALTH_KINDS = ("data_gaps", "run_failed", "day_caught_up", "journal_mismatch",
                "model_removed", "few_valid_candidates", "token_budget", "cost_stale",
                "revised_data", "no_finding")       # DESIGN 15.2's alert kinds


def test_the_new_rules_read_the_production_thresholds(setup):
    t = setup.thresholds
    assert (t["alerts.rank_blocks"], t["alerts.rank_level"], t["alerts.revival_min_days"],
            t["alerts.cost_stale_days"], t["alerts.min_valid_candidates"],
            t["alerts.valid_candidates_window_days"], t["alerts.no_finding_months"]) == (
        12, 0.05, 60, 90, 5, 14, 12)
    keys = alerts.THRESHOLD_KEYS
    assert set(keys[alerts.RANK]) >= {"alerts.rank_blocks", "alerts.rank_level"}
    assert keys[alerts.REVIVAL] == ("alerts.revival_min_days",)
    assert set(keys[alerts.FEW_VALID]) == {"alerts.min_valid_candidates",
                                           "alerts.valid_candidates_window_days"}
    assert keys[alerts.COST_STALE] == ("alerts.cost_stale_days",)
    assert keys[alerts.NO_FINDING] == ("alerts.no_finding_months",)


# ------------------------------------------------------------ rank_persistence


def rank_row(block, timing, statistic, gross):
    first = date(2019, 6, 3) + timedelta(days=7 * block)
    row = {"block": block, "first": first.isoformat(),
           "last": (first + timedelta(days=6)).isoformat(),
           "previous_first": (first - timedelta(days=7)).isoformat(),
           "previous_last": (first - timedelta(days=1)).isoformat(),
           "subjects": ["a1", "a2", "a3", "a4", "a5"], "size": 5, "statistic": statistic}
    if timing is not False:                 # False: a row written before mission 19
        row["timing"], row["gross"] = timing, gross
    return row


def timing_values(shift):
    """Twelve drawn values, demeaned, then moved so that t = T_CRIT_11 + shift."""
    rng = np.random.default_rng(R_SEED)
    e = [float(x) for x in rng.normal(0.0, 0.3, 12)]
    m = math.fsum(e) / 12
    e = [x - m for x in e]
    s = statistics.stdev(e)
    return [x + (T_CRIT_11 + shift) * s / math.sqrt(12) for x in e]


def write_rank_state(root, values, extra_null=False):
    """Block 1 a row without ``timing`` (before mission 19); then one row per value,
    ``statistic`` the value's negative and ``gross`` a third figure; with
    ``extra_null`` a row whose ``timing`` is null after them."""
    rows = [rank_row(1, False, 0.9, None)]
    for j, v in enumerate(values):
        rows.append(rank_row(2 + j, v, -v, 0.5 - v))
    if extra_null:
        rows.append(rank_row(2 + len(values), None, None, None))
    stats.append_rank_rows(root, TRACK, rows)
    return rows


def own_t(values):
    n = len(values)
    mean = math.fsum(values) / n
    s = statistics.stdev(values)
    return mean, s, mean / (s / math.sqrt(n))


@pytest.mark.parametrize("shift, side", [(0.05, True), (-0.05, False)])
def test_rank_persistence_twelve_blocks_on_both_sides_of_the_critical_value(
        tmp_path, setup, shift, side):
    values = timing_values(shift)
    write_rank_state(tmp_path, values)
    mean, s, t = own_t(values)
    assert abs(t - (T_CRIT_11 + shift)) < 1e-9
    entry = alerts.rank_persistence(tmp_path, setup, date(2019, 9, 2))
    assert (entry["kind"], entry["subject"]) == (alerts.RANK, TRACK)
    assert entry["active"] is side
    assert close(entry["value"], mean, 1e-12)
    assert close(entry["threshold"], T_CRIT_11 * s / math.sqrt(12), 1e-7)
    pay = entry["payload"]
    assert close(pay["t"], t, 1e-12) and close(pay["sd"], s, 1e-12) and pay["n"] == 12
    assert (pay["p"] < 0.05) is side and abs(pay["p"] - 0.05) < 0.01
    assert pay["blocks"] == list(range(2, 14))
    assert pay["thresholds"]["alerts.rank_blocks"] == 12
    assert pay["thresholds"]["alerts.rank_level"] == 0.05


def test_rank_persistence_reads_timing_not_the_net_statistic(tmp_path, setup):
    values = timing_values(0.05)
    write_rank_state(tmp_path, values)
    # On ``statistic`` (each value's negative) t would be negative: not met.
    assert own_t([-v for v in values])[2] < 0
    assert alerts.rank_persistence(tmp_path, setup, date(2019, 9, 2))["active"] is True


def test_rank_persistence_takes_the_last_twelve_non_missing_blocks(tmp_path, setup):
    values = [-5.0] + timing_values(0.05)             # an older, far lower block first
    write_rank_state(tmp_path, values, extra_null=True)
    entry = alerts.rank_persistence(tmp_path, setup, date(2019, 9, 2))
    assert entry["payload"]["blocks"] == list(range(3, 15))
    assert close(entry["value"], own_t(values[1:])[0], 1e-12)
    assert entry["active"] is True


def test_rank_persistence_is_not_evaluated_with_eleven_blocks(tmp_path, setup):
    write_rank_state(tmp_path, timing_values(3.0)[:11], extra_null=True)
    entry = alerts.rank_persistence(tmp_path, setup, date(2019, 9, 2))
    assert entry == {"kind": alerts.RANK, "subject": TRACK, "active": False, "value": None,
                     "threshold": None, "p": None, "payload": None}


def own_t_sf(t, df, steps=4000):
    """The one-sided upper tail of Student's t at ``df`` degrees of freedom, by
    Simpson's rule on the density after ``x = sqrt(df) tan(theta)``:
    ``c * sqrt(df) * cos(theta) ** (df - 1)`` over ``(atan(t / sqrt(df)), pi / 2)``."""
    c = math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2))
    a, b = math.atan(t / math.sqrt(df)), math.pi / 2
    h = (b - a) / steps
    total = 0.0
    for k in range(steps + 1):
        w = 1 if k in (0, steps) else (4 if k % 2 else 2)
        total += w * math.cos(a + k * h) ** (df - 1)
    return c * math.sqrt(df) * total * h / 3


def test_own_t_sf_gives_the_written_critical_value():
    assert abs(own_t_sf(T_CRIT_11, 11) - 0.05) < 1e-9


@pytest.mark.parametrize("shift", [0.05, -0.05, 0.8])
def test_the_alert_step_writes_the_rank_rules_p_into_its_state_entry(tmp_path, setup, shift):
    # decision 2026-10-18-m20 160: the state's rank_persistence entry holds the
    # rule's own p on D, computed here from the rows this test writes.
    values = timing_values(shift)
    write_rank_state(tmp_path, values)
    want = own_t_sf(own_t(values)[2], 11)
    d = date(2019, 9, 2)
    records = pd.DataFrame(columns=list(paper.COLUMNS))
    new, _ = alerts.step(tmp_path, setup, d, records, into=tmp_path / "staging")
    held = alerts.read_state(tmp_path / "staging", TRACK)
    assert held == new
    got = held["alerts"][f"rank_persistence|{TRACK}"]
    assert set(got) == {*alerts.ENTRY_KEYS, "p"}
    assert close(got["p"], want, 1e-8)
    assert got["active"] is (want < 0.05)
    others = [k for k in held["alerts"] if not k.startswith("rank_persistence|")]
    assert all(set(held["alerts"][k]) == set(alerts.ENTRY_KEYS) for k in others)


def test_the_rank_entry_holds_p_null_where_the_rule_was_not_evaluated(tmp_path, setup):
    write_rank_state(tmp_path, timing_values(3.0)[:11], extra_null=True)
    records = pd.DataFrame(columns=list(paper.COLUMNS))
    new, _ = alerts.step(tmp_path, setup, date(2019, 9, 2), records,
                         into=tmp_path / "staging")
    assert new["alerts"][f"rank_persistence|{TRACK}"] == {
        "active": False, "since": None, "value": None, "threshold": None, "p": None}


# ------------------------------------------------------------------- revival


def weekdays_between(after, through):
    """Weekdays in (after, through]: the trading days of synth_week away from 07-04."""
    d, n = after + timedelta(days=1), 0
    while d <= through:
        n += d.weekday() < 5
        d += timedelta(days=1)
    return n


def back_weekdays(day, n):
    """The weekday ``x`` before ``day`` with ``n`` weekdays in (x, day]."""
    x = day
    while weekdays_between(x, day) < n:
        x -= timedelta(days=1)
    while x.weekday() >= 5:
        x -= timedelta(days=1)
    return x


REVIVAL_DAY = date(2019, 12, 20)          # a Friday; 60 weekdays back stay after 07-04


def write_revival_state(root, setup):
    ids = {}
    for name in ("sixty", "fiftynine", "yesterday"):
        ids[name] = state_mod.write_approach(
            root, source=f"# approach {name}\n", params={}, cell="trend/short",
            model_id="test-model", model_version="test-model-v0", cutoff=date(2019, 1, 1),
            description=f"the approach {name}", profile_version="w-test",
            admitted=date(2019, 7, 15), instruments=setup.instruments,
            spread_tables=setup.spread_tables)
    went = {"sixty": back_weekdays(REVIVAL_DAY, 60), "fiftynine": back_weekdays(REVIVAL_DAY, 59),
            "yesterday": back_weekdays(REVIVAL_DAY, 70)}
    back = {"sixty": REVIVAL_DAY, "fiftynine": REVIVAL_DAY,
            "yesterday": REVIVAL_DAY - timedelta(days=1)}
    rows = []
    for name, aid in ids.items():
        rows.append({"date": went[name].isoformat(), "id": aid, "from": "live", "to": "dormant",
                     "reason": "dormant", "adjusted": -0.5, "plain": -0.4})
        rows.append({"date": back[name].isoformat(), "id": aid, "from": "dormant", "to": "live",
                     "reason": "returned", "adjusted": 0.5, "plain": 0.4})
    ledger.append(root, TRACK, ledger.LIFECYCLE, sorted(rows, key=lambda r: r["date"]))
    records = pd.DataFrame([{"date": date(2019, 7, 15) + timedelta(days=j), "subject": aid,
                             "kind": paper.APPROACH, "gross": 0.0, "net_1x": 0.0, "net_2x": 0.0,
                             "trades": 0, "clean": j % 3 != 0}
                            for aid in ids.values() for j in range(9)])
    return ids, went, records


def test_revival_59_and_60_dormant_trading_days(tmp_path, setup):
    ids, went, records = write_revival_state(tmp_path, setup)
    assert weekdays_between(went["sixty"], REVIVAL_DAY) == 60
    assert weekdays_between(went["fiftynine"], REVIVAL_DAY) == 59
    got = {e["subject"]: e for e in alerts.revival(tmp_path, setup, REVIVAL_DAY, records)}
    # only the rows dated D from dormant to live are evaluated
    assert set(got) == {ids["sixty"], ids["fiftynine"]}
    sixty, short = got[ids["sixty"]], got[ids["fiftynine"]]
    assert (sixty["kind"], sixty["active"], sixty["value"], sixty["threshold"]) == (
        alerts.REVIVAL, True, 60, 60)
    assert (short["active"], short["value"], short["threshold"]) == (False, 59, 60)
    pay = sixty["payload"]
    assert (pay["dormant_days"], pay["dormant_since"]) == (60, went["sixty"].isoformat())
    assert (pay["clean_days"], pay["exposed_days"]) == (6, 3)
    assert pay["thresholds"] == {"alerts.revival_min_days": 60}
    assert (pay["description"], pay["source"], pay["cell"], pay["model_id"],
            pay["model_version"]) == ("the approach sixty", "# approach sixty\n", "trend/short",
                                      "test-model", "test-model-v0")


# ------------------------------------------------------------- the transitions


def entry(kind, subject, active, value=None, threshold=None, payload=None):
    return {"kind": kind, "subject": subject, "active": active, "value": value,
            "threshold": threshold, "payload": payload}


def test_an_alert_fires_once_while_true_and_again_after_it_was_false():
    days = [date(2019, 9, 2) + timedelta(days=j) for j in range(5)]
    actives = [True, True, False, True, True]
    previous, fired_on, sinces = None, [], []
    for d, on in zip(days, actives, strict=True):
        new, fired = alerts.transition(previous, d, [entry(alerts.REVIVAL, "a1", on, 60, 60,
                                                           {"x": 1})])
        assert new["date"] == d.isoformat()
        if fired:
            fired_on.append(d)
        sinces.append(new["alerts"]["revival|a1"]["since"])
        previous = new
    assert fired_on == [days[0], days[3]]
    assert sinces == [days[0].isoformat()] * 3 + [days[3].isoformat()] * 2
    assert previous["alerts"]["revival|a1"] == {"active": True, "since": days[3].isoformat(),
                                                "value": 60, "threshold": 60}


def test_an_entry_absent_the_day_before_fires_and_an_inactive_one_has_no_since():
    d = date(2019, 9, 3)
    previous = {"date": "2019-09-02", "alerts": {
        "revival|old": {"active": True, "since": "2019-09-02", "value": 61, "threshold": 60}}}
    new, fired = alerts.transition(previous, d, [entry(alerts.REVIVAL, "new", True, 70, 60),
                                                 entry(alerts.RANK, TRACK, False)])
    assert [(e["kind"], e["subject"]) for e in fired] == [(alerts.REVIVAL, "new")]
    assert new == {"date": "2019-09-03", "alerts": {
        "rank_persistence|test_synth": {"active": False, "since": None, "value": None,
                                        "threshold": None, "p": None},
        "revival|new": {"active": True, "since": "2019-09-03", "value": 70, "threshold": 60}}}


def test_the_state_and_payloads_are_written_where_and_as_the_decision_says(tmp_path):
    d = date(2019, 9, 3)
    subject = "instruments/SYNA.toml cost.checked"
    new, fired = alerts.transition(None, d, [
        entry(alerts.COST_STALE, subject, True, payload={"checked": "2019-01-01", "days": 245}),
        entry(alerts.RANK, TRACK, True, 0.25, 0.125, {"mean": 0.25, "p": 0.01}),
        entry(alerts.REVIVAL, "a1", False, 59, 60, {"dormant_days": 59})])
    staging, stored = tmp_path / "staging", tmp_path / "state"
    stored.mkdir()
    written = alerts.write(staging, stored, TRACK, d, new, fired)
    base = staging / "alerts" / TRACK
    assert (base / "state.json").read_text(encoding="utf-8") == ledger.line(new) + "\n"
    quoted = "instruments%2FSYNA.toml%20cost.checked"
    assert (base / "payloads" / "2019-09-03" / "cost_stale" / f"{quoted}.json").read_text(
        encoding="utf-8") == ledger.line({"checked": "2019-01-01", "days": 245}) + "\n"
    assert (base / "payloads" / "2019-09-03" / "rank_persistence" / f"{TRACK}.json").read_text(
        encoding="utf-8") == ledger.line({"mean": 0.25, "p": 0.01}) + "\n"
    assert not (base / "payloads" / "2019-09-03" / "revival").exists()
    assert sorted(written) == sorted([
        f"alerts/{TRACK}/state.json",
        f"alerts/{TRACK}/payloads/2019-09-03/cost_stale/{quoted}.json",
        f"alerts/{TRACK}/payloads/2019-09-03/rank_persistence/{TRACK}.json"])
    assert ledger.line(new) == json_line(new)


def json_line(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def test_a_payload_is_never_rewritten(tmp_path):
    d = date(2019, 9, 3)
    new, fired = alerts.transition(None, d, [entry(alerts.RANK, TRACK, True, 1.0, 0.5,
                                                   {"mean": 1.0})])
    stored = tmp_path / "state"
    alerts.write(stored, stored, TRACK, d, new, fired)
    other = [dict(fired[0], payload={"mean": 2.0})]
    with pytest.raises(state_mod.StateError):
        alerts.write(tmp_path / "staging", stored, TRACK, d, new, other)


# --------------------------------------------------------------- health alerts


@pytest.mark.parametrize("kind", HEALTH_KINDS)
def test_each_health_kind_fires_from_its_event(tmp_path, kind):
    d = date(2019, 9, 3)
    state_mod.append_health(tmp_path, TRACK, [
        state_mod.HealthEvent(d - timedelta(days=1), "alert", kind, "old", {"n": 1}),
        state_mod.HealthEvent(d, "alert", kind, "subj", {"n": 2}),
        state_mod.HealthEvent(d, "notice", kind, "quiet", {"n": 3}),
        state_mod.HealthEvent(d + timedelta(days=1), "alert", kind, "later", {"n": 4})])
    got = alerts.health(tmp_path, TRACK, d)
    assert got == [entry(kind, "old", False), entry(kind, "subj", True, payload={"n": 2})]
    previous = {"date": "2019-09-02", "alerts": {
        f"{kind}|old": {"active": True, "since": "2019-09-02", "value": None,
                        "threshold": None}}}
    new, fired = alerts.transition(previous, d, got)
    assert [(e["kind"], e["subject"], e["payload"]) for e in fired] == [(kind, "subj", {"n": 2})]
    assert new["alerts"][f"{kind}|old"] == {"active": False, "since": "2019-09-02",
                                            "value": None, "threshold": None}


# ------------------------------------------------------------------ detectors


def call_row(day, k):
    return {"date": day.isoformat(), "call": f"c{k}", "attempt": 1, "cell": "trend/short",
            "model": "m", "outcome": "trial", "response": None, "tokens_in": 1, "tokens_out": 1}


FIRST_CALL = date(2019, 9, 2)


@pytest.mark.parametrize("offset, trials, raised", [
    (13, 0, False),       # 13 days since the first step-5 day: not yet
    (14, 4, True),        # 14 days: 4 trials in the 14 calendar days ending D
    (14, 5, False),       # 5 trials: enough
])
def test_few_valid_candidates_at_its_thresholds(tmp_path, setup, offset, trials, raised):
    d = FIRST_CALL + timedelta(days=offset)
    ledger.append(tmp_path, TRACK, ledger.CALLS, [call_row(FIRST_CALL, 0), call_row(d, 1)])
    start = d - timedelta(days=13)
    # one trial the day before the window, never counted; the others in it
    rows = [trial_row(99, start - timedelta(days=1))]
    rows += [trial_row(k, start + timedelta(days=k % 14)) for k in range(trials)]
    ledger.append(tmp_path, TRACK, ledger.TRIALS, rows)
    got = alerts.few_valid_candidates(tmp_path, setup, d)
    if not raised:
        assert got == []
        return
    [event] = got
    assert (event.date, event.level, event.kind, event.subject) == (
        d, "alert", alerts.FEW_VALID, TRACK)
    assert event.detail["trials"] == trials
    assert event.detail["thresholds"] == {"alerts.min_valid_candidates": 5,
                                          "alerts.valid_candidates_window_days": 14}


def test_few_valid_candidates_needs_a_step_5_day(tmp_path, setup):
    # a controls-only state has no call row: never raised
    ledger.append(tmp_path, TRACK, ledger.TRIALS, [trial_row(1, date(2019, 6, 3))])
    assert alerts.few_valid_candidates(tmp_path, setup, date(2020, 6, 3)) == []


def test_cost_stale_counts_calendar_days_before_d(setup):
    models = load_models(FIXTURE_CONFIG / "models.toml")
    pool = sorted(m.id for m in models.models if m.pool)
    assert {m.provenance.checked for m in models.models if m.pool} == {date(2026, 10, 11)}
    assert setup.spread_tables["SYNA"].provenance.checked == date(2026, 10, 12)
    assert all(i.cost.provenance is None for i in setup.instruments)
    # 2027-01-09 is 90 days after 2026-10-11: nothing is stale
    assert alerts.cost_stale(setup, date(2027, 1, 9), models) == []
    on_10 = alerts.cost_stale(setup, date(2027, 1, 10), models)       # 91 and 90 days
    assert sorted(e.subject for e in on_10) == sorted(f"models.toml model.{m}.checked"
                                                      for m in pool)
    on_11 = alerts.cost_stale(setup, date(2027, 1, 11), models)       # 92 and 91 days
    assert sorted(e.subject for e in on_11) == sorted(
        [f"models.toml model.{m}.checked" for m in pool] + ["spreads/SYNA.toml checked"])
    spread = next(e for e in on_11 if e.subject.startswith("spreads/"))
    assert (spread.date, spread.level, spread.kind) == (date(2027, 1, 11), "alert",
                                                        alerts.COST_STALE)
    assert spread.detail == {"checked": "2026-10-12", "days": 91,
                             "thresholds": {"alerts.cost_stale_days": 90}}
    # without the model records only the spread table is read
    assert [e.subject for e in alerts.cost_stale(setup, date(2027, 1, 11))] == [
        "spreads/SYNA.toml checked"]


def test_no_finding_at_twelve_months(setup):
    d = date(2020, 9, 15)
    since = date(2019, 9, 15)                       # twelve months before D
    [event] = alerts.no_finding(setup, d, since, [date(2019, 9, 15)])
    assert (event.date, event.level, event.kind, event.subject) == (
        d, "alert", alerts.NO_FINDING, TRACK)
    assert event.detail["thresholds"] == {"alerts.no_finding_months": 12}
    # live running one day shorter than twelve months: not raised
    assert alerts.no_finding(setup, d, since + timedelta(days=1), []) == []
    # a finding alert inside the twelve months: not raised
    assert alerts.no_finding(setup, d, since, [date(2019, 9, 16)]) == []
