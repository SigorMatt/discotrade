"""G1.4: the deflated figures and the tightening function match hand-computed
values for fixed inputs (DESIGN 18.3 G1.4, 11.2, 11.4, 8; decisions 2026-10-12
30, 60, 74).

The inputs are written below: six control-slot paper Sharpes ``SHARPES``, an
approach Sharpe ``S`` and the trial counts ``N`` in 0, 1, 2, 10 and 1000. For
each, ``E(N)`` (``stats.expected_max``), the excess (``stats.excess``),
``p(N)`` at the production thresholds (``stats.tightened_percentile`` with
``alerts.persistent_base_percentile`` and ``alerts.false_alerts_per_year``
read from ``config/thresholds.toml``) and the threshold of 11.4
(``stats.threshold``) equal literal values to 1e-12. Each literal is worked
out in the comments from the formulas of 11.2 and 11.4 and decision 60, and
the test recomputes it with its own normal quantile, found by bisection on
``math.erf`` (decision 60), never through ``stats.py``. ``mu_c`` and ``sd_c``
are also taken from paper rows by ``stats.control_moments``, the frame built
here with pandas, so that the Sharpe list reaches the formula the way the
table's does (decision 60: ddof 1, a slot without a row on every day or with
a Sharpe that is not a number left out, fewer than two slots not a number).

Seeds: the test draws nothing at random. Dates: the paper rows of
``test_control_moments_from_paper_rows`` are dated 2019-06-03 to 2019-06-07.
"""

import math
import tomllib
from datetime import date

import pandas as pd
import pytest

from discotrade import stats
from discotrade.cli import REPO_ROOT

pytestmark = [pytest.mark.gate, pytest.mark.gate_m1]

TOL = 1e-12
G = 0.5772156649015329          # Euler-Mascheroni (decision 60)
BASE, RATE = 0.95, 0.5          # the production alerts thresholds, asserted below

# The fixed inputs.
SHARPES = [0.5, -0.25, 1.0, 0.0, -0.75, 0.25]
S = 1.2
# mu_c = (0.5 - 0.25 + 1.0 + 0.0 - 0.75 + 0.25) / 6 = 0.75 / 6 = 0.125
MU_C = 0.125
# deviations from 0.125: 0.375, -0.375, 0.875, -0.125, -0.875, 0.125; their
# squares 0.140625 + 0.140625 + 0.765625 + 0.015625 + 0.765625 + 0.015625
# = 1.84375; over 6 - 1 = 5 (ddof 1): 0.36875; sd_c = sqrt(0.36875)
SD_C = 0.6072478900745559

# E(N) = mu_c + sd_c * ((1 - g) * z(1 - 1/m) + g * z(1 - 1/(m e))), m = max(N, 2)
#
# N = 0, 1, 2: m = 2. z(1 - 1/2) = z(0.5) = 0. 1 - 1/(2e) = 0.8160602794142788,
#   z(0.8160602794142788) = 0.9004525966377903. The bracket is
#   (1 - g) * 0 + 0.5772156649015329 * 0.9004525966377903 = 0.5197553442805939,
#   E = 0.125 + 0.6072478900745559 * 0.5197553442805939 = 0.4406203361693650,
#   excess = 1.2 - 0.4406203361693650 = 0.7593796638306350.
# N = 10: m = 10. z(0.9) = 1.2815515655446008; 1 - 1/(10e) = 0.9632120558828557,
#   z(0.9632120558828557) = 1.7892417645816279. The bracket is
#   0.42278433509846713 * 1.2815515655446008 + 0.5772156649015329 * 1.7892417645816279
#   = 1.5745983013457500, E = 0.125 + 0.6072478900745559 * 1.5745983013457500
#   = 1.0811714962071866, excess = 1.2 - 1.0811714962071866 = 0.1188285037928134.
# N = 1000: m = 1000. z(0.999) = 3.090232306167813; 1 - 1/(1000e) =
#   0.9996321205588286, z(0.9996321205588286) = 3.375895391061807. The bracket is
#   0.42278433509846713 * 3.090232306167813 + 0.5772156649015329 * 3.375895391061807
#   = 3.255121513652723, E = 0.125 + 0.6072478900745559 * 3.255121513652723
#   = 2.1016656711019106, excess = 1.2 - 2.1016656711019106 = -0.9016656711019106.
E_N = {0: 0.4406203361693650, 1: 0.4406203361693650, 2: 0.4406203361693650,
       10: 1.0811714962071866, 1000: 2.1016656711019106}
EXCESS = {0: 0.7593796638306350, 1: 0.7593796638306350, 2: 0.7593796638306350,
          10: 0.1188285037928134, 1000: -0.9016656711019106}

# p(N) = 1 - min(1 - base, rate / max(N, 1)), base 0.95, rate 0.5:
# N = 0, 1: 1 - min(0.05, 0.5) = 0.95; N = 2: 1 - min(0.05, 0.25) = 0.95;
# N = 10: 1 - min(0.05, 0.05) = 0.95; N = 1000: 1 - min(0.05, 0.0005) = 0.9995.
P_N = {0: 0.95, 1: 0.95, 2: 0.95, 10: 0.95, 1000: 0.9995}
# threshold = mu_c + z(p(N)) * sd_c:
# p = 0.95: z = 1.6448536269514722, 0.125 + 1.6448536269514722 * 0.6072478900745559
#   = 1.1238338944477624;
# p = 0.9995: z = 3.2905267314919255, 0.125 + 3.2905267314919255 * 0.6072478900745559
#   = 2.1231654149323966.
THRESHOLD = {0: 1.1238338944477624, 1: 1.1238338944477624, 2: 1.1238338944477624,
             10: 1.1238338944477624, 1000: 2.1231654149323966}
NS = (0, 1, 2, 10, 1000)


def close(a: float, b: float) -> bool:
    """Decision 39's "equal, to 1e-12"."""
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def zq(p: float) -> float:
    """The standard normal quantile by bisection on math.erf, to 1e-15 (decision 60)."""
    lo, hi = -40.0, 40.0
    while hi - lo > 1e-15:
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            break
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def own_e(mu: float, sd: float, n: int) -> float:
    m = max(n, 2)
    return mu + sd * ((1 - G) * zq(1 - 1 / m) + G * zq(1 - 1 / (m * math.e)))


def own_p(n: int) -> float:
    return 1 - min(1 - BASE, RATE / max(n, 1))


def test_production_thresholds_are_the_inputs():
    with open(REPO_ROOT / "config" / "thresholds.toml", "rb") as f:
        alerts = tomllib.load(f)["alerts"]
    assert alerts["persistent_base_percentile"] == BASE
    assert alerts["false_alerts_per_year"] == RATE


def test_published_quantiles_and_constants():
    for p, want in ((0.95, 1.6448536269514722), (0.975, 1.959963984540054),
                    (0.99, 2.3263478740408408)):
        assert close(stats.z(p), want)
        assert close(zq(p), want)
    assert stats.EULER_GAMMA == G


def test_hand_moments_of_the_sharpe_list():
    mu = math.fsum(SHARPES) / len(SHARPES)
    sd = math.sqrt(math.fsum((x - mu) ** 2 for x in SHARPES) / (len(SHARPES) - 1))
    assert close(mu, MU_C) and close(sd, SD_C)


@pytest.mark.parametrize("n", NS)
def test_expected_max_and_excess(n):
    e = stats.expected_max(MU_C, SD_C, n)
    assert close(e, E_N[n]), (n, e, E_N[n])
    assert close(own_e(MU_C, SD_C, n), E_N[n])
    assert close(stats.excess(S, e), EXCESS[n])
    assert close(S - E_N[n], EXCESS[n])


@pytest.mark.parametrize("n", NS)
def test_tightened_percentile_and_threshold(n):
    assert close(stats.tightened_percentile(n, BASE, RATE), P_N[n])
    assert close(own_p(n), P_N[n])
    t = stats.threshold(MU_C, SD_C, n, BASE, RATE)
    assert close(t, THRESHOLD[n]), (n, t, THRESHOLD[n])
    assert close(MU_C + zq(own_p(n)) * SD_C, THRESHOLD[n])


def test_not_a_number_propagates():
    """An S that is not a number gives an excess that is not a number; with
    moments that are not numbers E(N) and the threshold are not numbers."""
    assert math.isnan(stats.excess(math.nan, E_N[10]))
    assert math.isnan(stats.expected_max(math.nan, math.nan, 10))
    assert math.isnan(stats.threshold(math.nan, math.nan, 10, BASE, RATE))


# Paper rows whose control slots have the Sharpes of ``SHARPES`` (to 1e-12,
# asserted): each slot's daily net_1x over the five days is a mean plus 0.01
# times BASIS / sqrt(2.5), a series of sample deviation 0.01 (BASIS has mean 0
# and ddof-1 variance 10 / 4 = 2.5), the mean being 0.01 * s / sqrt(252).
DAYS = [date(2019, 6, d) for d in (3, 4, 5, 6, 7)]
BASIS = [-2.0, -1.0, 0.0, 1.0, 2.0]


def series_with_sharpe(s: float) -> list[float]:
    """Five daily values whose Sharpe is ``s``: mean 0.01 * s / sqrt(252) over a
    sample deviation of 0.01; a Sharpe of 0 is a mean of 0."""
    mean = 0.01 * s / math.sqrt(252)
    return [mean + 0.01 * b / math.sqrt(2.5) for b in BASIS]


def paper_frame() -> pd.DataFrame:
    rows = []
    for slot, s in enumerate(SHARPES):
        for d, x in zip(DAYS, series_with_sharpe(s), strict=True):
            rows.append({"date": d, "subject": f"rc:{slot}", "kind": "control_random",
                         "gross": x, "net_1x": x, "net_2x": x, "trades": 1, "clean": True})
    # rc:6 has no row on the last day (left out); rc:7 is constant (a Sharpe that
    # is not a number, decision 30: left out); bh:SYNA is not a random slot.
    for d in DAYS[:-1]:
        rows.append({"date": d, "subject": "rc:6", "kind": "control_random", "gross": 0.5,
                     "net_1x": 0.5, "net_2x": 0.5, "trades": 1, "clean": True})
    for d in DAYS:
        rows.append({"date": d, "subject": "rc:7", "kind": "control_random", "gross": 0.001,
                     "net_1x": 0.001, "net_2x": 0.001, "trades": 1, "clean": True})
        rows.append({"date": d, "subject": "bh:SYNA", "kind": "control_bh", "gross": 9.0,
                     "net_1x": 9.0 + d.day, "net_2x": 9.0, "trades": 1, "clean": True})
    return pd.DataFrame(rows)


def test_control_moments_from_paper_rows():
    for s in SHARPES:
        x = series_with_sharpe(s)
        mean = math.fsum(x) / 5
        sd = math.sqrt(math.fsum((v - mean) ** 2 for v in x) / 4)
        assert close(mean / sd * math.sqrt(252), s)
    mu, sd = stats.control_moments(paper_frame(), DAYS)
    assert close(mu, MU_C) and close(sd, SD_C)
    e = stats.expected_max(mu, sd, 10)
    assert close(e, E_N[10])
    assert close(stats.excess(S, e), EXCESS[10])
    # Two slots only: still numbers; one slot: not numbers (decision 60).
    two = paper_frame()
    two = two[two["subject"].isin(["rc:0", "rc:1", "rc:7"])]
    mu2, sd2 = stats.control_moments(two, DAYS)
    # rc:0 Sharpe 0.5, rc:1 Sharpe -0.25: mean 0.125, sd |0.75| / sqrt(2) = 0.5303300858899106
    assert close(mu2, 0.125) and close(sd2, 0.5303300858899106)
    one = two[two["subject"].isin(["rc:0", "rc:7"])]
    assert all(math.isnan(v) for v in stats.control_moments(one, DAYS))
