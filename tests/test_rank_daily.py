"""Rank persistence in the day loop (DESIGN 11.1, 16.1 step 6, 16.2; decisions
2026-10-12 59, 62, 63, 69, 70; I-5, I-6).

``discotrade replay`` runs in-process through ``discotrade.cli.main`` on the
fixture track ``test_synth`` (``epoch`` 2019-06-03, ``block_days`` 7, all
instruments on ``synth_week``, so weekends are not trading days), into a
state directory made by ``init-state`` under the test's tmp directory, with
four approaches written by ``state.write_approach`` (decision 48), admitted on
2019-06-07: the three reference strategies and
``tests/fixtures/strategies/breaks_thursday_noon.py``, which breaks the
contract on Thursday 2019-06-13 and is retired that day.

The configuration is ``tests/fixtures/config/`` copied under tmp with the
production ``config/thresholds.toml``, three values lowered in that copy, said
so: ``controls.random_pool`` 4 in place of 50 (fewer control slots, so that
eleven replayed days stay quick; no rule here reads the pool),
``alerts.rank_min_population`` 3 in place of 5 (so that the three approaches
that keep a full paper record give a statistic; the rule is tested at 5 in
``tests/test_stats.py`` and ``tests/test_portfolio.py``) and
``lifecycle.dormant_window_days`` 2 in place of 30 (so that the population
holds dormant approaches; the rule is tested at 30 in
``tests/test_lifecycle.py``).

The first journaled day is Monday 2019-06-10, the first day of block 1
(06-10..16): block 1's previous block, block 0 (06-03..09), starts before it,
so block 1 gets no row; block 2 (06-17..23) ends on a Sunday and its row is
appended on the first new day on or after that, Monday 06-24, and not on
Friday 06-21, its last trading day. Every expected value is computed in the
test: the population from the lifecycle ledger and the paper rows, the
trading days from the journal index (the track's trading days, decision 51),
the ranks by counting, the correlation with ``math``; the row's ``timing``
and ``gross`` (decision 2026-10-17-m19 149) from the paper gross and the
stored unit and position records, ``hbar_i`` per block by the test's own sums
(O-4, O-5). The synthetic
instruments' seeds are those of their fixture records (``SEEDS``, asserted);
no other random draw is made. Time comes only from ``--as-of`` and the
replay's clock. Every git run is on local paths with ``GIT_ALLOW_PROTOCOL=file``
(decision 47).
"""

import json
import math
import os
import shutil
import subprocess
from datetime import date

import pytest

from discotrade import journal, ledger, paper
from discotrade.cli import REPO_ROOT, main
from discotrade.state import read_approaches, write_approach
from discotrade.strategy import load_strategy_file

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_synth"
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
ADMITTED = date(2019, 6, 7)
FIRST = date(2019, 6, 10)                # the first journaled day, block 1's first
FRIDAY = date(2019, 6, 21)               # block 2's last trading day
MONDAY = date(2019, 6, 24)               # the first trading day after block 2's last day
BLOCK_1 = (date(2019, 6, 10), date(2019, 6, 16))
BLOCK_2 = (date(2019, 6, 17), date(2019, 6, 23))
LOWERED = (("random_pool = 50", "random_pool = 4 "),
           ("rank_min_population = 5", "rank_min_population = 3"),
           ("dormant_window_days = 30 ", "dormant_window_days = 2  "))


def git(repo, *args) -> str:
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def files(root) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def rank_path(state):
    return state / "stats" / TRACK / "rank_persistence.jsonl"


def rank_rows(state):
    path = rank_path(state)
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def replay(state, config, first, last):
    return main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "replay", "--from", first.isoformat(), "--to", last.isoformat()])


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("rkcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    text = (REPO_ROOT / "config" / "thresholds.toml").read_text(encoding="utf-8")
    for old, new in LOWERED:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    (path / "thresholds.toml").write_text(text, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


def admit(state, setup, path):
    strat = load_strategy_file(path, setup.thresholds)
    return write_approach(
        state, source=path.read_text(encoding="utf-8"), params=strat.params,
        cell=f"cell/{path.stem}", model_id="test-model", model_version="test-model-v0",
        cutoff=date(2019, 1, 1), description=path.stem, profile_version="w-test",
        admitted=ADMITTED, instruments=setup.instruments, spread_tables=setup.spread_tables)


@pytest.fixture(scope="module")
def ran(tmp_path_factory, config, setup):
    """Replayed to FRIDAY (the rank file then), then MONDAY; tests copy it."""
    state = tmp_path_factory.mktemp("rkran") / "state"
    assert main(["init-state", "--state", str(state), "--as-of", INIT_AS_OF]) == 0
    for name in ("trend_ma.py", "hour_of_day.py", "zscore_reversal.py"):
        admit(state, setup, REPO_ROOT / "reference" / name)
    breaks = admit(state, setup,
                   REPO_ROOT / "tests" / "fixtures" / "strategies" / "breaks_thursday_noon.py")
    assert replay(state, config, FIRST, date(2019, 6, 17)) == 0
    after_block_1 = rank_rows(state)
    assert replay(state, config, date(2019, 6, 18), FRIDAY) == 0
    by_friday = rank_rows(state)
    assert replay(state, config, MONDAY, MONDAY) == 0
    return state, breaks, after_block_1, by_friday


def test_the_fixture_values(setup):
    assert {i.symbol: i.source.get("seed") for i in setup.instruments} == SEEDS
    assert setup.track.epoch == date(2019, 6, 3) and setup.track.block_days == 7
    assert FIRST.weekday() == 0 and FRIDAY.weekday() == 4 and MONDAY.weekday() == 0


def test_no_row_before_the_blocks_last_calendar_day_nor_for_block_1(ran):
    state, _, after_block_1, by_friday = ran
    assert after_block_1 == []       # block 1's previous block starts before FIRST
    assert by_friday == []           # block 2 has not ended on its last trading day


def own_ranks(values):
    out = []
    for v in values:
        below = sum(1 for w in values if w < v)
        ties = sum(1 for w in values if w == v)
        out.append(below + (ties + 1) / 2)
    return out


def own_spearman(x, y):
    rx, ry = own_ranks(x), own_ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den


def own_gross_and_timing(state, names, blocks):
    """Per block, the subjects' summed paper gross and summed gross timing
    return: gross less the mean over the four instruments of ``hbar_i`` (the
    block's summed position over its row count, 0 with none) times ``R_i(D)``,
    read from the stored ``unit.parquet`` and ``positions.parquet``."""
    held = paper.read(state, TRACK)
    units = paper.read_unit(state, TRACK)
    positions = paper.read_positions(state, TRACK)
    symbols = sorted(SEEDS)
    unit = {(str(s), d): float(v) for s, d, v in zip(units["instrument"], units["date"],
                                                     units["unit"], strict=True)}
    gross_sums, timing_sums = ([], []), ([], [])
    for b, block in enumerate(blocks):
        for name in names:
            mine = held[held["subject"] == name]
            gross = dict(zip(mine["date"], mine["gross"], strict=True))
            pos = positions[(positions["subject"] == name) & positions["date"].isin(block)]
            hbar = {}
            for s in symbols:
                leg = pos[pos["instrument"] == s]
                rows = int(sum(int(x) for x in leg["rows"]))
                hbar[s] = math.fsum(float(x) for x in leg["position"]) / rows if rows else 0.0
            gross_sums[b].append(math.fsum(float(gross[d]) for d in block))
            timing_sums[b].append(math.fsum(
                float(gross[d]) - math.fsum(hbar[s] * unit.get((s, d), 0.0) for s in symbols) / 4
                for d in block))
    return gross_sums, timing_sums


def test_monday_appends_block_2s_row_over_the_live_and_dormant_approaches(ran):
    state, breaks, _, _ = ran
    rows = rank_rows(state)
    assert len(rows) == 1
    [row] = rows
    # O-24, decision 2026-10-17-m19 149 (a): the row gains `timing` and `gross`
    assert set(row) == {"block", "first", "last", "previous_first", "previous_last",
                        "subjects", "size", "statistic", "timing", "gross"}
    assert (row["block"], row["first"], row["last"], row["previous_first"],
            row["previous_last"]) == (2, BLOCK_2[0].isoformat(), BLOCK_2[1].isoformat(),
                                      BLOCK_1[0].isoformat(), BLOCK_1[1].isoformat())
    # The population, by the test's own reading.
    life = ledger.read(state, TRACK, ledger.LIFECYCLE)
    after = {}
    for a in read_approaches(state):
        after[a.id] = "live"
        for r in life:
            if r["id"] == a.id and date.fromisoformat(r["date"]) <= MONDAY:
                after[a.id] = r["to"]
    assert after[breaks] == "retired"
    assert "dormant" in after.values()
    journaled = [date.fromisoformat(e["date"]) for e in journal.read_index(state, TRACK)]
    held = paper.read(state, TRACK)
    sums = {}
    for aid, s in sorted(after.items()):
        if s not in ("live", "dormant"):
            continue
        mine = dict(zip(held[held["subject"] == aid]["date"],
                        held[held["subject"] == aid]["net_1x"], strict=True))
        blocks = [[d for d in journaled if lo <= d <= hi] for lo, hi in (BLOCK_1, BLOCK_2)]
        if all(b and all(d in mine for d in b) for b in blocks):
            sums[aid] = [math.fsum(float(mine[d]) for d in b) for b in blocks]
    assert len(sums) == 3 and breaks not in sums
    assert row["subjects"] == sorted(sums) and row["size"] == 3
    assert "portfolio" not in row["subjects"]
    want = own_spearman([sums[a][0] for a in sorted(sums)], [sums[a][1] for a in sorted(sums)])
    assert abs(row["statistic"] - want) <= 1e-12
    # Decision 2026-10-17-m19 149: `gross` on the summed paper gross, `timing` on
    # the summed gross timing return, each block its own window (O-4, O-5), from
    # the derived exposure records the day loop stored.
    gross_sums, timing_sums = own_gross_and_timing(state, sorted(sums), blocks)
    want_gross = own_spearman(*gross_sums)
    want_timing = own_spearman(*timing_sums)
    assert abs(row["gross"] - want_gross) <= 1e-12
    assert abs(row["timing"] - want_timing) <= 1e-12
    # The line is sorted JSON, staged and committed with Monday's run.
    text = rank_path(state).read_text(encoding="utf-8")
    assert text == ledger.line(row) + "\n"
    changed = git(state, "show", "--name-only", "--format=", "HEAD").split()
    assert f"stats/{TRACK}/rank_persistence.jsonl" in changed
    assert git(state, "log", "-1", "--format=%s").strip() == f"run {TRACK} {MONDAY.isoformat()}"


def test_a_rerun_appends_nothing(tmp_path, ran, config):
    state = tmp_path / "state"
    shutil.copytree(ran[0], state)
    before, head = files(state), git(state, "rev-parse", "HEAD")
    assert replay(state, config, MONDAY, MONDAY) == 0
    assert replay(state, config, FRIDAY, FRIDAY) == 0
    assert main(["--state", str(state), "--config", str(config), "--track", TRACK,
                 "--as-of", "2019-06-25T00:00:00+00:00", "run-day", "--day",
                 date(2019, 6, 19).isoformat()]) == 0
    assert files(state) == before and git(state, "rev-parse", "HEAD") == head
