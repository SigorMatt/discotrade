"""The statistics of DESIGN 11 (11.1 to 11.4; decisions 2026-10-12 30, 59, 60,
61; I-3).

Every paper frame here is written by hand with ``paper.COLUMNS``; every
expected value is computed in the test itself: ranks by counting (ties take
the average rank), the Pearson correlation and the Sharpe with ``math`` and
``statistics.stdev`` (ddof 1), and the normal quantile by bisection on
``math.erf``/``math.erfc`` to 1e-15, never through ``stats.py``. The rules
are tested at their production values, read from ``config/thresholds.toml``
(``alerts.rank_min_population`` 5, ``alerts.persistent_base_percentile``
0.95, ``alerts.false_alerts_per_year`` 0.5, asserted). The block dates come
from the fixture track ``test_mixed``'s ``epoch`` and ``block_days`` and the
trading days from the fixture calendars ``synth_week`` and ``always_open``.
No random draw is made. The tests prove the formulas on these inputs,
nothing about any strategy or market.
"""

import math
import statistics
from datetime import date, timedelta

import pandas as pd
import pytest

from discotrade import paper, stats
from discotrade.cli import REPO_ROOT
from discotrade.config import load_calendar, load_thresholds, load_track

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
THRESHOLDS = load_thresholds(REPO_ROOT / "config" / "thresholds.toml")
TRACK = load_track(FIXTURE_CONFIG / "tracks" / "test_mixed.toml")
WEEK = load_calendar(FIXTURE_CONFIG / "calendars" / "synth_week.toml")
ALWAYS = load_calendar(FIXTURE_CONFIG / "calendars" / "always_open.toml")
BASKET = (WEEK, WEEK, ALWAYS)          # test_mixed: SYNA, SYNL on synth_week, SYNX always open
MIN_POP = THRESHOLDS["alerts.rank_min_population"]
BASE = THRESHOLDS["alerts.persistent_base_percentile"]
FAY = THRESHOLDS["alerts.false_alerts_per_year"]
NAN = float("nan")


def eq(a, b, tol=1e-12) -> bool:
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def test_production_values():
    assert MIN_POP == 5 and BASE == 0.95 and FAY == 0.5
    assert TRACK.epoch == date(2019, 6, 3) and TRACK.block_days == 7


def frame(rows) -> pd.DataFrame:
    """A paper frame from (subject, kind, date, net_1x) rows."""
    out = pd.DataFrame(
        [{"date": d, "subject": s, "kind": k, "gross": x, "net_1x": x, "net_2x": x,
          "trades": 0, "clean": True} for s, k, d, x in rows])
    return out[list(paper.COLUMNS)] if len(out) else pd.DataFrame(columns=paper.COLUMNS)


def days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


# ------------------------------------------------------------------ 11.1 block dates


def test_block_dates_count_block_days_from_the_epoch():
    # decision 59: block k is the block_days calendar days from epoch + k * block_days
    assert stats.block_dates(TRACK.epoch, TRACK.block_days, 0) == (date(2019, 6, 3),
                                                                   date(2019, 6, 9))
    assert stats.block_dates(TRACK.epoch, TRACK.block_days, 1) == (date(2019, 6, 10),
                                                                   date(2019, 6, 16))
    assert stats.block_dates(TRACK.epoch, TRACK.block_days, 5) == (date(2019, 7, 8),
                                                                   date(2019, 7, 14))
    assert stats.block_dates(date(2019, 6, 3), 14, 2) == (date(2019, 7, 1), date(2019, 7, 14))


def test_trading_dates_are_the_union_of_the_subjects_own_calendars():
    first, last = date(2019, 6, 10), date(2019, 6, 16)       # Monday to Sunday
    weekdays = days(date(2019, 6, 10), date(2019, 6, 14))
    assert stats.trading_dates((WEEK,), TRACK.bar_seconds, first, last) == weekdays
    assert stats.trading_dates(BASKET, TRACK.bar_seconds, first, last) == days(first, last)


# ------------------------------------------------------------------ 11.1 population


def full(subject, kind, dates, value=0.001):
    return [(subject, kind, d, value) for d in dates]


def test_the_population_leaves_out_a_subject_missing_one_trading_day():
    every = days(date(2019, 6, 3), date(2019, 6, 16))
    weekdays = [d for d in every if d.weekday() < 5]
    rows = (full("a_full", "approach", every)
            + full("a_no_sat", "approach", [d for d in every if d != date(2019, 6, 15)])
            + full("a_no_prev_mon", "approach", every[1:])
            + full("a_weekdays", "approach", weekdays)
            + full("bh_week", "control_bh", weekdays))
    subjects = {"a_full": BASKET, "a_no_sat": BASKET, "a_no_prev_mon": BASKET,
                "a_weekdays": BASKET, "bh_week": (WEEK,)}
    row = stats.rank_persistence(frame(rows), subjects, epoch=TRACK.epoch,
                                 block_days=TRACK.block_days, bar_seconds=TRACK.bar_seconds,
                                 k=1, min_population=MIN_POP)
    # a basket subject trades the always-open instrument's weekend; the buy-and-hold
    # control on synth_week is judged on its own instrument's weekdays only
    assert row["subjects"] == ["a_full", "bh_week"]
    assert row["size"] == 2 and row["statistic"] is None
    assert row["block"] == 1
    assert row["first"] == "2019-06-10" and row["last"] == "2019-06-16"
    assert row["previous_first"] == "2019-06-03" and row["previous_last"] == "2019-06-09"


def test_rank_persistence_refuses_block_zero():
    with pytest.raises(ValueError):
        stats.rank_persistence(frame([]), {}, epoch=TRACK.epoch, block_days=7,
                               bar_seconds=3600, k=0, min_population=MIN_POP)


# ------------------------------------------------------------------ 11.1 Spearman


def ranks_by_counting(values):
    """Each value's rank, 1-based, ties taking the average of the ranks they span."""
    return [sum(1 for w in values if w < v) + (sum(1 for w in values if w == v) + 1) / 2
            for v in values]


def pearson(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def two_blocks(prev_sums, cur_sums, n_days=7):
    """Paper rows over blocks 0 and 1 of test_mixed for basket subjects s0..: each
    day of a block holds the block's sum divided by the day count."""
    prev = days(date(2019, 6, 3), date(2019, 6, 9))
    cur = days(date(2019, 6, 10), date(2019, 6, 16))
    rows, subjects = [], {}
    for i, (p, c) in enumerate(zip(prev_sums, cur_sums, strict=True)):
        name = f"s{i}"
        subjects[name] = BASKET
        rows += [(name, "approach", d, p / n_days) for d in prev]
        rows += [(name, "approach", d, c / n_days) for d in cur]
    return frame(rows), subjects


def persistence(paper_frame, subjects, min_population=MIN_POP):
    return stats.rank_persistence(paper_frame, subjects, epoch=TRACK.epoch,
                                  block_days=TRACK.block_days, bar_seconds=TRACK.bar_seconds,
                                  k=1, min_population=min_population)


PREV = [0.07, 0.014, 0.014, -0.021, 0.035, 0.014]      # three tied
CUR = [0.028, -0.007, 0.049, 0.007, 0.028, -0.014]      # two tied


def test_spearman_is_pearson_of_average_ranks():
    paper_frame, subjects = two_blocks(PREV, CUR)
    row = persistence(paper_frame, subjects)
    # the sums the module sees are the sums of seven equal parts: the test's sums
    sums_prev = [sum([p / 7] * 7) for p in PREV]
    sums_cur = [sum([c / 7] * 7) for c in CUR]
    expected = pearson(ranks_by_counting(sums_prev), ranks_by_counting(sums_cur))
    assert ranks_by_counting(sums_prev) == [6.0, 3.0, 3.0, 1.0, 5.0, 3.0]
    assert row["size"] == 6 and row["subjects"] == [f"s{i}" for i in range(6)]
    assert eq(row["statistic"], expected)
    # ranking ties by position would give another number on these inputs
    by_position = pearson([1 + sorted(range(6), key=lambda i: sums_prev[i]).index(i)
                           for i in range(6)],
                          [1 + sorted(range(6), key=lambda i: sums_cur[i]).index(i)
                           for i in range(6)])
    assert not eq(by_position, expected)


def test_spearman_function_against_hand_values():
    x = [3.0, 1.0, 1.0, 4.0, 2.0]
    y = [10.0, 20.0, 20.0, 20.0, 5.0]
    assert eq(stats.spearman(x, y), pearson(ranks_by_counting(x), ranks_by_counting(y)))
    assert stats.average_ranks(x).tolist() == [4.0, 1.5, 1.5, 5.0, 3.0]


def test_statistic_is_missing_below_the_minimum_population():
    paper_frame, subjects = two_blocks(PREV[:4], CUR[:4])
    row = persistence(paper_frame, subjects)
    assert row["size"] == 4 == MIN_POP - 1 and row["statistic"] is None
    paper_frame, subjects = two_blocks(PREV[:5], CUR[:5])
    row = persistence(paper_frame, subjects)
    assert row["size"] == MIN_POP and row["statistic"] is not None


def test_statistic_is_missing_when_a_rank_series_has_zero_deviation():
    paper_frame, subjects = two_blocks([0.01] * 6, CUR)
    assert persistence(paper_frame, subjects)["statistic"] is None
    paper_frame, subjects = two_blocks(PREV, [-0.02] * 6)
    assert persistence(paper_frame, subjects)["statistic"] is None
    assert stats.spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


# ------------------------------------------------------------------ the quantile


def z_bisect(p: float) -> float:
    """The standard normal quantile by bisection on math.erf / math.erfc to 1e-15."""
    def below(x):        # whether Phi(x) < p, the upper tail compared through erfc
        if p > 0.5:
            return 0.5 * math.erfc(x / math.sqrt(2.0)) > 1.0 - p
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0))) < p
    lo, hi = -40.0, 40.0
    for _ in range(400):
        if hi - lo <= 1e-15:
            break
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            break
        if below(mid):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def test_the_published_quantiles():
    for p, value in ((0.95, 1.6448536269514722), (0.975, 1.959963984540054),
                     (0.99, 2.3263478740408408)):
        assert abs(stats.z(p) - value) <= 1e-12
        assert abs(z_bisect(p) - value) <= 1e-12


# ------------------------------------------------------------------ 11.2 E(N), excess


G = 0.5772156649015329


def expected_by_hand(mu, sd, n):
    m = max(n, 2)
    return mu + sd * ((1 - G) * z_bisect(1 - 1 / m) + G * z_bisect(1 - 1 / (m * math.e)))


@pytest.mark.parametrize("n", [0, 1, 2, 3, 10, 1000, 250000])
def test_expected_maximum_against_hand_values(n):
    mu, sd = 0.3, 1.1
    assert eq(stats.expected_max(mu, sd, n), expected_by_hand(mu, sd, n))
    s = 2.4
    assert eq(stats.excess(s, stats.expected_max(mu, sd, n)), s - expected_by_hand(mu, sd, n))


def test_n_below_two_is_floored_at_two():
    two = expected_by_hand(0.3, 1.1, 2)
    assert eq(stats.expected_max(0.3, 1.1, 0), two) and eq(stats.expected_max(0.3, 1.1, 1), two)
    assert not eq(stats.expected_max(0.3, 1.1, 3), two)


def test_a_sharpe_or_moments_not_a_number_give_values_not_a_number():
    assert math.isnan(stats.excess(NAN, stats.expected_max(0.3, 1.1, 10)))
    assert math.isnan(stats.expected_max(NAN, NAN, 10))
    assert math.isnan(stats.excess(1.0, stats.expected_max(NAN, NAN, 10)))
    assert math.isnan(stats.threshold(NAN, NAN, 10, BASE, FAY))


# ------------------------------------------------------------------ 11.4 p(N), threshold


@pytest.mark.parametrize("n,hand", [(0, 0.95), (1, 0.95), (10, 0.95), (1000, 0.9995)])
def test_tightened_percentile_at_the_production_thresholds(n, hand):
    # 1 - min(1 - 0.95, 0.5 / max(N, 1)): 0.05 for N <= 10, 0.0005 at N = 1000
    assert eq(stats.tightened_percentile(n, BASE, FAY), hand)


@pytest.mark.parametrize("n,hand", [(0, 0.95), (1, 0.95), (10, 0.95), (1000, 0.9995)])
def test_threshold_against_hand_values(n, hand):
    mu, sd = -0.2, 0.8
    assert eq(stats.threshold(mu, sd, n, BASE, FAY), mu + z_bisect(hand) * sd)


# ------------------------------------------------------------------ 11.2 mu_c, sd_c


def sharpe_by_hand(xs):
    return statistics.mean(xs) / statistics.stdev(xs) * math.sqrt(252)


def test_control_moments_over_slots_with_a_row_on_each_day():
    span = days(date(2020, 1, 6), date(2020, 1, 10))
    series = {
        "r1": [0.01, -0.02, 0.03, 0.005, 0.0],
        "r2": [0.002, 0.004, -0.001, 0.003, 0.001],
        "r3": [-0.01, 0.02, -0.03, 0.01, -0.004],
        "r_const": [0.001] * 5,                       # Sharpe not a number: left out
        "r_short": [0.05, 0.05, -0.01, 0.02],         # misses a day: left out
    }
    rows = []
    for name, xs in series.items():
        rows += [(name, "control_random", d, x) for d, x in zip(span, xs, strict=False)]
    rows += [("a1", "approach", d, 0.1 * (i + 1)) for i, d in enumerate(span)]
    rows += [("bh", "control_bh", d, 0.01 * (-1) ** i) for i, d in enumerate(span)]
    mu, sd = stats.control_moments(frame(rows), span)
    sharpes = [sharpe_by_hand(series[k]) for k in ("r1", "r2", "r3")]
    assert eq(mu, statistics.mean(sharpes))
    assert eq(sd, statistics.stdev(sharpes))          # ddof 1
    assert not eq(sd, statistics.pstdev(sharpes))


def test_fewer_than_two_slots_give_moments_not_a_number():
    span = days(date(2020, 1, 6), date(2020, 1, 8))
    rows = [("r1", "control_random", d, x) for d, x in zip(span, [0.01, -0.02, 0.03],
                                                            strict=True)]
    rows += [("r2", "control_random", d, 0.002) for d in span]       # Sharpe not a number
    mu, sd = stats.control_moments(frame(rows), span)
    assert math.isnan(mu) and math.isnan(sd)
    mu, sd = stats.control_moments(frame(rows[:3]), span)
    assert math.isnan(mu) and math.isnan(sd)
    assert math.isnan(stats.expected_max(mu, sd, 10))
    assert math.isnan(stats.threshold(mu, sd, 10, BASE, FAY))


# ------------------------------------------------------------------ 11.3 counts


def test_clean_and_exposed_counts():
    out = frame([("a1", "approach", date(2020, 1, d), 0.0) for d in (6, 7, 8, 9)]
                + [("r1", "control_random", date(2020, 1, 6), 0.0)])
    out.loc[out["date"] <= date(2020, 1, 7), "clean"] = False
    out.loc[out["subject"] == "r1", "clean"] = True
    assert stats.clean_counts(out, "a1") == (2, 2)
    assert stats.clean_counts(out, "r1") == (1, 0)
    assert stats.clean_counts(out, "nobody") == (0, 0)
