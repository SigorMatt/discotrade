"""Gate item G3.1: twenty replay days on the null market with the scripted
provider replaying a corpus attributed to three model families yield at least
ten valid candidates that are mutually distinct (DESIGN 18.3 G3.1, 18.2, 12.3,
13.5, 13.6, 16.1 steps 3 to 5, 16.4; decisions 139 (a), 138, 72 and 40 of
meta/decisions/; I-1, I-7, I-11, I-12).

As decision 139 (a) reads it: the twenty trading days ``FIRST`` 2019-07-15 to
``LAST`` 2019-08-09 of the fixture track ``test_synth`` are replayed with the
corpus ``tests/fixtures/worker_corpus/m3/`` on decision 72's gate configuration
(``tests/fixtures/config/`` with ``thresholds_gate.toml`` copied in unchanged,
under the test's temporary directory; its ``models.toml`` is the fixture's), the
child-process backend, the scripted coordinator and ``--provider
scripted:<corpus>``, in-process through ``discotrade.cli.main``. Then
``trials.jsonl`` holds at least ten rows; their models' makers (read from
``models.toml``) are the three of the pool; and for every pair of trials the
absolute Pearson correlation of their position series on W of the later
trial's day, concatenated over the basket in the track's instrument order, is at
most ``corr_max``. Each trial's source is its frozen ``strategy.py`` (under
``approaches/<id>/`` when admitted, else ``trials/<id>/``; its sha256 equal to
the row's ``code_sha256`` and its bytes equal to a strategy file of the
repository, decision 104 (d)). Its positions are taken by running it with the
row's fixed parameters through the child-process backend in ``positions`` jobs: one
job over the span of every trial's W (the first trial's W start to the last W's
end) and one over its own day's W; the targets at its own W's bars from the two
jobs are asserted equal (a strategy's frame at a bar is the last
``history_cap_bars`` bars, whatever the window), and the targets at the bars of
another day's W are the span job's at those bars (matched by open time), so that
a run of 15 trials takes 30 jobs, not 120 (DESIGN 18.2's time). The series on a
W is the held position ``h(u)``, the target of the bar before, 0 at W's first
bar (DESIGN 7.1: a window is scored on its own), and the correlation is
computed here with numpy. A pair in which either series is constant has no
correlation and is not a duplicate (DESIGN 12.3's reading in
``validation.correlation``); the test asserts no trial's series is constant, so
every pair is checked.

Seeds: the synthetic instruments' seeds are their fixture records' (``SEEDS``,
asserted); no other random draw is made. Time comes only from ``--as-of`` of
``init-state`` (``INIT_AS_OF``) and the replay's clock.
"""

import hashlib
from datetime import date

import numpy as np
import pytest
from m3_harness import M3, backend, models_toml, positions, trials, worker_replay

from discotrade import journal
from discotrade.cli import REPO_ROOT
from discotrade.config import DateRange, load_track_config

pytestmark = [pytest.mark.gate, pytest.mark.gate_m3]

TRACK = "test_synth"
SEEDS = {"SYNA": 101, "SYNB": 102, "SYNC": 103, "SYND": 104}
INIT_AS_OF = "2019-06-03T00:00:00+00:00"
FIRST, LAST = date(2019, 7, 15), date(2019, 8, 9)
#: The trading days of the span: the weekdays (synth_week's closure of
#: 2019-07-04 lies before the span).
TRADING_DAYS = 20
MIN_TRIALS = 10
STRATEGY_DIRS = (REPO_ROOT / "tests" / "fixtures" / "worker_corpus" / "strategies",
                 REPO_ROOT / "tests" / "fixtures" / "strategies", REPO_ROOT / "reference")


@pytest.fixture(scope="module")
def replayed(tmp_path_factory):
    state, config, status, out, err = worker_replay(
        tmp_path_factory.mktemp("g31"), M3, TRACK, INIT_AS_OF, FIRST, LAST)
    assert status == 0, err
    return state, config, out


def test_span_seeds_and_configuration(replayed):
    state, config, out = replayed
    assert int(np.busday_count(FIRST, LAST, weekmask="1111100")) + 1 == TRADING_DAYS
    assert len([x for x in out.splitlines() if "journal written" in x]) == TRADING_DAYS
    tc = load_track_config(config, TRACK)
    assert {i.symbol: i.source.get("seed") for i in tc.instruments} == SEEDS
    gate = (REPO_ROOT / "tests" / "fixtures" / "config" / "thresholds_gate.toml").read_bytes()
    assert (config / "thresholds.toml").read_bytes() == gate
    assert (config / "models.toml").read_bytes() == \
        (REPO_ROOT / "tests" / "fixtures" / "config" / "models.toml").read_bytes()


def test_at_least_ten_trials_from_the_three_makers(replayed):
    state, config, _ = replayed
    rows = trials(state, TRACK)
    assert len(rows) >= MIN_TRIALS, [r["id"] for r in rows]
    models = models_toml(config)["model"]
    maker = {m["id"]: m["maker"] for m in models}
    pool_makers = {m["maker"] for m in models if m["pool"]}
    assert len(pool_makers) == 3
    assert {maker[r["model_id"]] for r in rows} == pool_makers
    for r in rows:
        assert FIRST <= date.fromisoformat(r["date"]) <= LAST


def _source(state, row) -> str:
    folder = "approaches" if row["admitted"] else "trials"
    data = (state / folder / row["id"] / "strategy.py").read_bytes()
    assert hashlib.sha256(data).hexdigest() == row["code_sha256"]
    assert any(p.read_bytes() == data for d in STRATEGY_DIRS for p in d.glob("*.py")), \
        f"trial {row['id']}: its source is not a strategy file of the repository"
    return data.decode("utf-8")


def _held(parts) -> np.ndarray:
    """h(u): the target of the bar before, 0 at the window's first bar (DESIGN 7.1),
    per instrument, concatenated in the track's order."""
    out = []
    for p in parts:
        h = np.zeros_like(p)
        h[1:] = p[:-1]
        out.append(h)
    return np.concatenate(out)


def _on(span_targets, w_targets) -> list[np.ndarray]:
    """The span job's targets at the bars of a W, per instrument (matched by open time)."""
    out = []
    for (span_ts, span_p), (ts, _) in zip(span_targets, w_targets, strict=True):
        where = np.searchsorted(span_ts, ts)
        assert np.array_equal(span_ts[where], ts)
        out.append(span_p[where])
    return out


def test_every_pair_of_trials_is_distinct_on_w_of_the_later_day(replayed, tmp_path):
    state, config, _ = replayed
    setup = journal.Setup.load(config, TRACK)
    corr_max = float(setup.thresholds["validation.corr_max"])
    rows = sorted(trials(state, TRACK), key=lambda r: (r["date"], r["id"]))
    assert len({r["date"] for r in rows}) == len(rows)   # one trial a day: "later" is defined
    days = {r["id"]: date.fromisoformat(r["date"]) for r in rows}
    ws = {aid: setup.track.windows(d).w for aid, d in days.items()}
    span = DateRange(min(w.first for w in ws.values()), max(w.last for w in ws.values()))
    checked, worst = 0, 0.0
    with backend(tmp_path / "jobs") as box:
        # One job per trial over every W of the span; each trial's own W also run on
        # its own, and its targets there equal the span job's (a frame is the last
        # history_cap_bars bars, whatever the window).
        targets, own = {}, {}
        for r in rows:
            source = _source(state, r)
            targets[r["id"]] = positions(box, state, config, setup, span, source,
                                         r["params"])
            own[r["id"]] = positions(box, state, config, setup, ws[r["id"]], source,
                                     r["params"])
            for got, (_, want) in zip(_on(targets[r["id"]], own[r["id"]]), own[r["id"]],
                                      strict=True):
                assert np.array_equal(got, want), r["id"]
        for k, later in enumerate(rows):
            w_bars = own[later["id"]]
            mine = _held([p for _, p in w_bars])
            assert np.std(mine) > 0, f"trial {later['id']}: constant on its W"
            for earlier in rows[:k]:
                other = _held(_on(targets[earlier["id"]], w_bars))
                assert len(other) == len(mine)
                assert np.std(other) > 0, (earlier["id"], later["id"])
                r = float(np.corrcoef(mine, other)[0, 1])
                assert abs(r) <= corr_max, (later["id"], earlier["id"], days[later["id"]], r)
                worst = max(worst, abs(r))
                checked += 1
    assert checked == len(rows) * (len(rows) - 1) // 2
    print(f"G3.1: {len(rows)} trials, {checked} pairs, max |corr| {worst:.3f}")
