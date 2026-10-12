"""Metrics (DESIGN 8; decisions 2026-10-12 23, 25, 30; R-7; I-4).

Every input is a hand-made per-bar frame with decision 25's columns and the
roll flags of its bars; every expected value is computed by hand from the
formulas of DESIGN 8 as decisions 23 and 25 clarify them. They prove the
formulas as written, nothing about any strategy.
"""

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from discotrade import metrics
from discotrade.backtest import ROW_COLUMNS, Evaluation, daily
from discotrade.metrics import Leg, Metrics, above, compute, daily_series, positive

NAN = float("nan")
D1, D2, D3, D4 = date(2024, 1, 5), date(2024, 1, 6), date(2024, 1, 7), date(2024, 1, 8)


def rows(dates, net_1x=None, net_2x=None, h=None, gross=None, trade=None, roll=None):
    """A per-bar frame with decision 25's columns; unspecified numbers are 0."""
    n = len(dates)

    def col(values):
        return np.zeros(n) if values is None else np.asarray(values, dtype=float)

    frame = pd.DataFrame({
        "ts": pd.date_range("2024-01-05", periods=n, freq="h", tz="UTC"),
        "contract": ["C"] * n,
        "date": list(dates),
        "p": np.zeros(n),
        "h": col(h),
        "gross": col(gross),
        "trade": col(trade),
        "fee": np.zeros(n),
        "spread": np.zeros(n),
        "slippage": np.zeros(n),
        "roll": col(roll),
        "cost": col(roll),
        "net_1x": col(net_1x),
        "net_2x": col(net_2x),
    })
    return frame[list(ROW_COLUMNS)]


def leg(dates, rolled=None, **cols):
    frame = rows(dates, **cols)
    flags = np.zeros(len(frame), dtype=bool) if rolled is None else np.asarray(rolled)
    return Leg(frame, flags)


def one_day_legs(d1x, d2x=None):
    """One instrument, one bar per day, with the given daily nets."""
    d2x = d1x if d2x is None else d2x
    days = [date(2024, 2, 1 + i) for i in range(len(d1x))]
    return [leg(days, net_1x=d1x, net_2x=d2x)]


# --- the daily series (decision 23) ---------------------------------------------

def test_daily_series_follows_decision_23_with_three_instruments():
    # A: a weekday-like calendar, two bars on D1, one on D2, one on D3.
    a = leg([D1, D1, D2, D3], net_1x=[0.01, 0.02, -0.03, 0.06],
            net_2x=[0.005, 0.01, -0.04, 0.05])
    # B: another calendar, no bar on D2, a bar on D4 that A does not trade.
    b = leg([D1, D3, D3, D4], net_1x=[0.03, 0.01, 0.02, -0.09],
            net_2x=[0.02, 0.0, 0.01, -0.12])
    # C: no window bar at all; it still counts in N.
    c = leg([])
    d = daily_series([a, b, c])
    assert list(d.columns) == ["date", "net_1x", "net_2x"]
    assert list(d["date"]) == [D1, D2, D3, D4]
    assert d["net_1x"].tolist() == pytest.approx(
        [(0.03 + 0.03) / 3, -0.03 / 3, (0.06 + 0.03) / 3, -0.09 / 3])
    assert d["net_2x"].tolist() == pytest.approx(
        [(0.015 + 0.02) / 3, -0.04 / 3, (0.05 + 0.01) / 3, -0.12 / 3])


def test_daily_series_is_sorted_by_date_whatever_the_leg_order():
    a = leg([D3, D3], net_1x=[0.1, 0.2])
    b = leg([D1], net_1x=[0.3])
    d = daily_series([a, b])
    assert list(d["date"]) == [D1, D3]
    assert d["net_1x"].tolist() == pytest.approx([0.15, 0.15])


def test_daily_series_of_a_subject_with_no_instrument_is_an_error():
    with pytest.raises(ValueError):
        daily_series([])


def test_backtest_daily_builds_the_series_from_evaluations():
    def evaluation(symbol, frame, rolled_window, context=2):
        n = context + len(frame)
        flags = np.zeros(n, dtype=bool)
        flags[context:] = rolled_window
        return Evaluation(symbol, frame, pd.DataFrame(), context, np.zeros(n), flags)

    a = evaluation("A", rows([D1, D2], net_1x=[0.03, 0.06], net_2x=[0.0, 0.03]),
                   [False, False])
    b = evaluation("B", rows([D2], net_1x=[0.09], net_2x=[0.06]), [False])
    empty = Evaluation("C", rows([]), pd.DataFrame(), 0, np.zeros(0),
                       np.zeros(0, dtype=bool))
    d = daily([a, b, empty])
    assert list(d["date"]) == [D1, D2]
    assert d["net_1x"].tolist() == pytest.approx([0.01, 0.05])
    assert d["net_2x"].tolist() == pytest.approx([0.0, 0.03])


def test_leg_takes_the_roll_flags_of_the_window_bars_only():
    flags = np.array([True, False, False, True])
    e = Evaluation("A", rows([D1, D2]), pd.DataFrame(), 2, np.zeros(4), flags)
    assert metrics.leg(e).rolled.tolist() == [False, True]


# --- return metrics from the daily series ---------------------------------------

def test_total_return_is_the_plain_sum():
    d = pd.Series([0.1, -0.05, 0.2])
    assert metrics.total_return(d) == pytest.approx(0.25)
    assert metrics.total_return(pd.Series([], dtype=float)) == 0.0


def test_sharpe_by_hand():
    d = pd.Series([0.01, 0.03, -0.01, 0.05])
    mean = 0.02
    sd = math.sqrt(((-0.01) ** 2 + 0.01 ** 2 + 0.03 ** 2 + 0.03 ** 2) / 3)
    assert metrics.sharpe(d) == pytest.approx(mean / sd * math.sqrt(252))


@pytest.mark.parametrize("d", [[0.02], [0.01, 0.01, 0.01], []])
def test_sharpe_is_not_a_number_with_one_day_or_no_deviation(d):
    assert math.isnan(metrics.sharpe(pd.Series(d, dtype=float)))


CONSTANT_SERIES = [[0.1] * 3, [0.03] * 10, [0.01] * 3, [1 / 3] * 10, [0.07] * 10,
                   [-0.05] * 5, [0.0] * 4, [1e-6] * 20]
OTHERS = [-math.inf, -1e17, -1e9, -1.0, 0.0, 1.0, 1e9, 1e17, math.inf, NAN]


@pytest.mark.parametrize("d", CONSTANT_SERIES)
def test_sharpe_of_a_constant_series_is_not_a_number(d):
    # Decision 30: every value equals the first, so the deviation is 0,
    # whatever rounding residue the floating-point std leaves.
    assert math.isnan(metrics.sharpe(pd.Series(d, dtype=float)))


@pytest.mark.parametrize("d", CONSTANT_SERIES)
def test_sharpe_of_a_constant_series_is_never_positive_negative_nor_above(d):
    s = metrics.sharpe(pd.Series(d, dtype=float))
    assert positive(s) is False
    assert metrics.negative(s) is False
    for other in OTHERS:
        assert above(s, other) is False
        assert above(other, s) is False


def test_sharpe_is_not_a_number_when_the_deviation_is_a_rounding_residue():
    # Decision 30's second clause: std(d, ddof=1) not above 1e-12 * max|d|.
    # The values differ in their last bits only, so the first clause misses.
    d = pd.Series([0.1, 0.1 + 2 ** -56, 0.1])
    assert len(set(d)) == 2
    assert math.isnan(metrics.sharpe(d))


def test_a_small_real_deviation_still_gives_its_sharpe():
    # [0.1, 0.1, 0.1 + 1e-9]: mean 0.1 + 1e-9/3, std(ddof=1) 1e-9/sqrt(3).
    d = pd.Series([0.1, 0.1, 0.1 + 1e-9])
    expected = (0.1 + 1e-9 / 3) / (1e-9 / math.sqrt(3)) * math.sqrt(252)
    s = metrics.sharpe(d)
    assert math.isfinite(s)
    assert s == pytest.approx(expected, rel=1e-6)


def test_compute_gives_no_sharpe_for_a_constant_non_zero_daily_net_at_1x_and_2x():
    # Ten days, one bar a day, net 0.07 at 1x and 0.03 at 2x every day: the
    # daily net is constant and non-zero at both multiples, and the
    # floating-point std of each is a rounding residue above 0.
    a = one_day_legs([0.07] * 10, [0.03] * 10)[0]
    m = compute([a])
    d = daily_series([a])
    assert len(set(d["net_1x"])) == 1 and d["net_1x"].iloc[0] != 0
    assert len(set(d["net_2x"])) == 1 and d["net_2x"].iloc[0] != 0
    assert math.isnan(m.sharpe)
    assert math.isnan(m.sharpe_2x)
    for s in (m.sharpe, m.sharpe_2x):
        assert positive(s) is False and metrics.negative(s) is False
        for other in OTHERS:
            assert above(s, other) is False and above(other, s) is False


@pytest.mark.parametrize("other", [-math.inf, -1e9, -1.0, 0.0, 1.0, math.inf, NAN])
def test_a_sharpe_that_is_not_a_number_is_never_positive_nor_above(other):
    s = metrics.sharpe(pd.Series([0.02]))
    assert math.isnan(s)
    assert positive(s) is False
    assert above(s, other) is False
    assert above(other, s) is False
    assert metrics.negative(s) is False


def test_comparisons_on_numbers():
    assert positive(0.1) and not positive(0.0) and not positive(-0.1)
    assert metrics.negative(-0.1) and not metrics.negative(0.0)
    assert above(1.0, 0.5) and not above(0.5, 0.5) and not above(0.4, 0.5)


def test_max_drawdown_by_hand():
    # running sum: 0.1, 0.3, 0.1, 0.0, 0.25, 0.05 -> peak 0.3, trough 0.0
    d = pd.Series([0.1, 0.2, -0.2, -0.1, 0.25, -0.2])
    assert metrics.max_drawdown(d) == pytest.approx(0.3)
    assert metrics.max_drawdown(pd.Series([0.1, 0.2])) == 0.0
    assert metrics.max_drawdown(pd.Series([], dtype=float)) == 0.0


def test_max_drawdown_counts_a_fall_from_the_start():
    assert metrics.max_drawdown(pd.Series([-0.1, 0.05, -0.2])) == pytest.approx(0.25)


def test_fragile():
    assert metrics.fragile(0.1, -0.1) is True
    assert metrics.fragile(0.1, 0.0) is False
    assert metrics.fragile(0.0, -0.1) is False
    assert metrics.fragile(-0.1, -0.2) is False
    assert metrics.fragile(0.1, 0.05) is False


def test_compute_return_metrics_at_1x_and_2x():
    m = compute(one_day_legs([0.01, 0.03, -0.01, 0.05], [0.0, 0.02, -0.03, 0.03]))
    assert m.days == 4
    assert m.total_return == pytest.approx(0.08)
    assert m.total_return_2x == pytest.approx(0.02)
    assert m.sharpe == pytest.approx(metrics.sharpe(pd.Series([0.01, 0.03, -0.01, 0.05])))
    assert m.sharpe_2x == pytest.approx(metrics.sharpe(pd.Series([0.0, 0.02, -0.03, 0.03])))
    assert m.max_drawdown == pytest.approx(0.01)
    assert m.fragile is False


def test_compute_flags_fragile():
    m = compute(one_day_legs([0.02, 0.01], [-0.01, -0.02]))
    assert m.total_return > 0 > m.total_return_2x
    assert m.fragile is True


# --- every metric from the daily series, none from window scores ----------------

def test_return_metrics_are_those_of_the_daily_series():
    a = leg([D1, D1, D2, D3], net_1x=[0.01, 0.02, -0.03, 0.06],
            net_2x=[0.0, 0.01, -0.05, 0.04])
    b = leg([D1, D3, D4], net_1x=[0.03, 0.01, -0.09], net_2x=[0.02, 0.0, -0.1])
    legs = [a, b, leg([])]
    d = daily_series(legs)
    m = compute(legs)
    assert m.days == len(d)
    assert m.total_return == metrics.total_return(d["net_1x"])
    assert m.total_return_2x == metrics.total_return(d["net_2x"])
    assert m.sharpe == metrics.sharpe(d["net_1x"])
    assert m.sharpe_2x == metrics.sharpe(d["net_2x"])
    assert m.max_drawdown == metrics.max_drawdown(d["net_1x"])


def test_metrics_of_two_windows_are_those_of_the_joined_series_not_of_the_scores():
    first = [0.03, -0.01, -0.02]
    second = [-0.02, 0.05, -0.03, 0.01]
    days1 = [date(2024, 3, 1 + i) for i in range(3)]
    days2 = [date(2024, 3, 10 + i) for i in range(4)]
    joined_rows = pd.concat([rows(days1, net_1x=first), rows(days2, net_1x=second)],
                            ignore_index=True)
    m = compute([Leg(joined_rows, np.zeros(7, dtype=bool))])
    d = pd.Series(first + second)
    assert m.sharpe == pytest.approx(metrics.sharpe(d))
    assert m.max_drawdown == pytest.approx(metrics.max_drawdown(d))
    window_scores = [metrics.sharpe(pd.Series(first)), metrics.sharpe(pd.Series(second))]
    assert m.sharpe != pytest.approx(sum(window_scores) / 2)
    worst_window = max(metrics.max_drawdown(pd.Series(first)),
                       metrics.max_drawdown(pd.Series(second)))
    assert m.max_drawdown != pytest.approx(worst_window)


# --- metrics from the per-bar rows (decision 25) --------------------------------

def test_trades_counts_rows_above_the_floor_and_not_roll_trades():
    a = leg([D1] * 5, h=[0, 1, 1, 0.5, 0.5], trade=[0, 1, 0, 0.5, 1e-10],
            rolled=[False, False, True, False, False])
    b = leg([D2] * 3, h=[0, -1, -1], trade=[0, 1, 0], rolled=[False, False, True])
    assert metrics.trades([a, b]) == 3
    assert metrics.trades([leg([])]) == 0


def test_roll_trades_are_not_counted_and_a_bar_with_a_roll_and_a_real_trade_is():
    # Bar 1: an ordinary trade (counted). Bar 2: a roll and a real trade of
    # 0.5 > 1e-9 (counted). Bar 3: a roll with trade 0 and a roll cost of
    # 0.0004 (not counted: its turnover is the roll, not a trade).
    a = leg([D1] * 4, h=[0, 1, 0.5, 0.5], trade=[0, 1, 0.5, 0],
            roll=[0, 0, 0.0002, 0.0004], rolled=[False, False, True, True])
    assert metrics.trades([a]) == 2


def test_avg_holding_bars_runs_broken_by_sign_change_and_by_zero():
    # runs: [1, 1] (2), [-1] (1, sign change), [0.5] (1, broken by 0), [0.2, 0.3] (2)
    a = leg([D1] * 7, h=[1, 1, -1, 0, 0.5, 0, 0])
    b = leg([D2] * 3, h=[0.2, 0.3, 0])
    assert metrics.avg_holding_bars([a, b]) == pytest.approx((2 + 1 + 1 + 2) / 4)


def test_avg_holding_bars_runs_do_not_join_across_instruments():
    a = leg([D1] * 2, h=[0, 1])
    b = leg([D2] * 2, h=[1, 0])
    assert metrics.avg_holding_bars([a, b]) == pytest.approx(1.0)


def test_avg_holding_bars_is_not_a_number_with_no_run():
    assert math.isnan(metrics.avg_holding_bars([leg([D1] * 3), leg([])]))


def test_breakeven_cost_in_basis_points_with_rolled_turnover():
    # A: trade turnover 1 + 0.5; a roll at bar 2 with h(u-1) = 1 adds 2;
    # B: trade turnover 1; a roll at its bar 1 with h(u-1) = -1 adds 2.
    a = leg([D1] * 4, h=[0, 1, 1, 0.5], trade=[0, 1, 0, 0.5],
            gross=[0.0, 0.004, 0.003, -0.001], rolled=[False, False, True, False])
    b = leg([D2] * 3, h=[-1, -1, 0], trade=[1, 0, 1], gross=[0.0, 0.002, 0.0],
            rolled=[False, True, False])
    turnover = 1.5 + 2 + 2 + 2
    m = compute([a, b])
    assert m.breakeven_cost == pytest.approx(0.008 / turnover * 10000)


def test_a_roll_at_the_first_window_bar_adds_no_turnover():
    a = leg([D1] * 2, h=[0, 1], trade=[0, 1], gross=[0.0, 0.01], rolled=[True, False])
    assert compute([a]).breakeven_cost == pytest.approx(100.0)


def test_breakeven_cost_is_not_a_number_without_turnover():
    a = leg([D1] * 3, gross=[0.0, 0.0, 0.0], rolled=[False, True, False])
    assert math.isnan(compute([a, leg([])]).breakeven_cost)


def test_compute_carries_the_bar_metrics():
    a = leg([D1, D1, D2], h=[0, 1, 1], trade=[0, 1, 0], gross=[0, 0.002, 0.001],
            net_1x=[0, 0.001, 0.001], net_2x=[0, 0.0, 0.001],
            rolled=[False, False, True])
    m = compute([a])
    assert m.trades == 1
    assert m.avg_holding_bars == pytest.approx(2.0)
    assert m.breakeven_cost == pytest.approx(0.003 / 3 * 10000)


# --- I-4: no gross figure without the net ones beside it ------------------------

def test_no_gross_figure_without_its_net_figures():
    a = leg([D1, D2], h=[0, 1], trade=[0, 1], gross=[0.0, 0.01],
            net_1x=[0.0, 0.008], net_2x=[0.0, 0.006])
    # The daily series is net only.
    assert "gross" not in daily_series([a]).columns
    # The one result that reads gross, breakeven_cost, comes only inside a
    # Metrics, beside the net totals and Sharpes at 1x and 2x.
    m = compute([a])
    assert m.breakeven_cost == pytest.approx(100.0)
    assert m.total_return == pytest.approx(0.008)
    assert m.total_return_2x == pytest.approx(0.006)
    assert {"sharpe", "sharpe_2x"} <= set(Metrics.__dataclass_fields__)
    assert set(metrics.__all__) == {
        "Leg", "Metrics", "leg", "daily_series", "compute", "total_return", "sharpe",
        "max_drawdown", "trades", "avg_holding_bars", "fragile", "positive",
        "negative", "above", "TRADE_FLOOR", "PERIODS_PER_YEAR"}
    # Every other public function that takes per-bar rows works without a
    # gross column, so none of them returns a gross figure.
    bare = Leg(a.rows.drop(columns=["gross"]), a.rolled)
    assert "date" in daily_series([bare]).columns
    assert metrics.trades([bare]) == 1
    assert metrics.avg_holding_bars([bare]) == pytest.approx(1.0)
