"""The W profile, version ``p1`` (DESIGN 13.1, 4.1, 5.6, 6.2; decision 115 of
2026-10-15-m14; I-1, I-3, I-9, I-12).

For a track, a trading day ``D`` and a cell, :func:`profile` computes a
JSON-ready document from W's bars of ``D`` (DESIGN 4.1) and nothing else: a
stored bar is W's when its trading date, by its instrument's calendar, lies in
W and its ``ts`` is not before the instrument's ``trusted_from``. No bar before
W or after it is read into a figure (I-3). Closes, highs and lows are adjusted
as of W's last bar (DESIGN 5.6, :func:`discotrade.rolls.adjust`), so no roll
after W moves a figure; a contract change between two W bars with no roll
record is refused (:class:`ProfileError`), as the evaluation refuses it.

Definitions (decision 115). With W's bars ``0 .. n-1`` of one instrument,
the return of bar ``s`` (``1 <= s <= n-1``) is
``r(s) = (Ca(s) - Ca(s-1)) / Cr(s-1)``, ``Ca`` adjusted, ``Cr`` raw; the
returns form the series ``R`` of length ``n-1`` from W's first return
(``R[i]`` is bar ``i+1``'s). "bp" is ``r * 10000``. Hours and weekdays are the
bar's open in its calendar's time zone (UTC when always open), Monday 0, as
DESIGN 6.2 gives them; a return carries its bar ``s``'s.

The common block, per instrument (115 (b)): ``returns`` (``count``,
``mean_bp``, ``std_bp`` with ddof 1, ``skewness`` ``m3 / m2**1.5``,
``excess_kurtosis`` ``m4 / m2**2 - 3`` from central moments, ``quantiles_bp``
at 0.01 to 0.99, numpy's default interpolation); ``std_by_hour`` and
``std_by_weekday`` (``std_bp`` and ``count``, one entry per hour 0..23 or
weekday 0..6); ``autocorrelation`` (Pearson over ``R``, ``value`` and
``count`` at lags 1..48, list position ``lag - 1``); ``volume_share_by_hour``
(the share of W's volume of the bars of each hour, and their ``count``); and
``regimes``: ``rv(s)`` is the sample deviation of the 24 returns ending at
``s``, defined from W's 24th return (``count`` defined bars); ``high`` is
``rv`` above its 75th percentile over W and ``low`` below its 25th, each with
the ``share`` of defined bars, the ``mean_run`` length of their maximal runs
and the count of ``runs``.

The cell block (115 (c)) is ``{"family": ..., "instruments": {...}}``, the
same for every cell of a family (the horizon is not in the document):

- ``trend``: ``k6``, ``k24``, ``k48``: the non-overlapping consecutive k-sums
  of ``R`` from its start (an incomplete last one dropped); over consecutive
  pairs of sums, ``same_sign_share`` (a zero is of neither sign),
  ``autocorrelation`` (lag 1) and ``count`` of pairs.
- ``mean_reversion``: ``events`` are returns with ``|r|`` above twice the
  ``std`` of ``R``; ``k1``, ``k6``, ``k24``: the sum of the k returns after an
  event (an event without k later returns in W dropped): ``opposite_share``,
  ``mean_reversal_bp`` (the sum times minus the event's sign) and ``count``.
- ``breakout``: ``n24``, ``n48``: a bar ``j >= n`` (``eligible``) breaks out up
  (down) when its adjusted close is above the highest (below the lowest) of the
  n closes before it; ``breakout_share`` of eligible bars; ``k1``, ``k6``,
  ``k24``: the sums of the returns of bars ``j+1 .. j+k`` times the direction:
  ``follow_share`` (positive), ``mean_follow_bp`` and ``count``; ``range_bp``,
  the mean over bars ``j >= n-1`` of (highest adjusted high minus lowest
  adjusted low of the n bars ending at ``j``) over ``Cr(j)``, with
  ``range_count``. The raw close is the divisor, as it is of a return (DESIGN
  7.2); decision 115 says "that bar's close", and this is the simplest reading
  that keeps the figure free of the adjustment.
- ``volatility_regime``: ``high`` and ``low`` of the common block, the regime
  of a return being that of ``rv`` at its bar: ``mean_bp``, ``std_bp``,
  ``count``, and ``autocorrelation`` (lag 1) over the ``pairs`` of
  consecutive returns both in the regime.
- ``volume``: an event is a bar ``j >= 24`` (``eligible``) whose volume is
  more than 2 sample deviations above the mean of W's 24 volumes before it;
  ``events``, ``event_share``; ``abs_return_ratio``, the mean ``|r|`` of the
  bar after an event over the mean ``|r|`` of ``R``, with ``ratio_count``;
  ``k1``, ``k6``: the sums of the returns of bars ``j+1 .. j+k`` times the
  sign of the event bar's return: ``follow_share`` (positive),
  ``mean_follow_bp``, ``count``. An event bar whose return is zero has no
  sign: its products are 0, counted and not positive (the decision is silent;
  the simplest reading).
- ``time_of_day``: ``by_hour`` (24) and ``by_weekday`` (7): ``mean_bp``,
  ``positive_share`` (``r > 0``) and ``count``.

A statistic with too few observations to be defined (a mean of none, a
deviation of fewer than 2, a correlation of fewer than 2 pairs or of a
constant series, a moment ratio of a constant series) is ``None`` beside its
count; nothing is filled in (115 (d)). No figure is rounded. The document is
``{"version": "p1", "instruments": [...], "common": {...}, "cell": {...}}``,
instruments in the track's order under their symbols (item 116 replaces them);
it holds no date, timestamp, price, volume or bar index of the store. The
fixed constants of the definitions are part of version ``p1``: changing one
changes :data:`VERSION`. No clock is read (I-12).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade.bars.store import BarStore
from discotrade.config import Calendar, Instrument, Track
from discotrade.rolls import adjust, read_rolls, roll_path
from discotrade.tradingcal import trading_date

VERSION = "p1"
BP = 10_000.0
QUANTILES = (("q01", 0.01), ("q05", 0.05), ("q25", 0.25), ("q50", 0.5), ("q75", 0.75),
             ("q95", 0.95), ("q99", 0.99))
MAX_LAG = 48
RV_BARS = 24
HIGH_PCT, LOW_PCT = 75.0, 25.0
TREND_K = (6, 24, 48)
EVENT_DEVIATIONS = 2.0
REVERSION_K = (1, 6, 24)
BREAKOUT_N = (24, 48)
BREAKOUT_K = (1, 6, 24)
VOLUME_BARS = 24
VOLUME_DEVIATIONS = 2.0
VOLUME_K = (1, 6)
HOURS, WEEKDAYS = 24, 7
#: How far beyond a window's dates its bars can lie in UTC (as in backtest).
_MARGIN = timedelta(days=2)


class ProfileError(ValueError):
    """A profile that cannot be computed: an unknown cell, or a roll with no record."""


@dataclass(frozen=True)
class WBars:
    """W's bars of one instrument: adjusted ``close``, ``high``, ``low`` (as of
    W's last bar), raw ``close_raw``, ``volume``, ``hour`` and ``weekday``."""

    close: np.ndarray
    close_raw: np.ndarray
    high: np.ndarray
    low: np.ndarray
    volume: np.ndarray
    hour: np.ndarray
    weekday: np.ndarray

    @property
    def returns(self) -> np.ndarray:
        """``R``: ``r(s)`` for ``s = 1 .. n-1``."""
        return (self.close[1:] - self.close[:-1]) / self.close_raw[:-1]


def _midnight(day: date) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, time(), tzinfo=UTC))


def read_w(state_dir: Path, track: Track, instrument: Instrument, calendar: Calendar,
           day: date) -> WBars:
    """W's bars of ``day`` of ``instrument`` from the store, adjusted as of W's last bar."""
    window = track.windows(day).w
    trusted = _midnight(instrument.trusted_from)
    store = BarStore(Path(state_dir), track.name, track.bar_seconds)
    lo = max(_midnight(window.first) - _MARGIN, trusted)
    hi = max(_midnight(window.last) + _MARGIN, lo)
    bars = store.read_range(instrument.symbol, lo, hi)
    keep = np.array([trading_date(calendar, t.to_pydatetime()) in window for t in bars["ts"]],
                    dtype=bool)
    keep &= (bars["ts"] >= trusted).to_numpy()
    w = bars[keep].reset_index(drop=True)
    if w.empty:
        return WBars(*(np.zeros(0) for _ in range(5)), np.zeros(0, dtype=np.int64),
                     np.zeros(0, dtype=np.int64))
    path = roll_path(Path(state_dir), track.name, instrument.symbol)
    rolls = read_rolls(path) if path.exists() else []
    records = {(r.ts, r.old, r.new) for r in rolls}
    contracts = w["contract"].to_numpy()
    for k in np.flatnonzero(contracts[1:] != contracts[:-1]) + 1:
        if (w["ts"].iloc[k], contracts[k - 1], contracts[k]) not in records:
            raise ProfileError(f"{instrument.symbol}: a contract change inside W has no roll "
                               f"record in {path}; run `discotrade bars fetch`")
    adjusted = adjust(w, rolls, w["ts"].iloc[-1])
    tz = "UTC" if calendar.always_open else calendar.tz
    local = w["ts"].dt.tz_convert(tz)
    return WBars(
        close=adjusted["close"].to_numpy(dtype=float),
        close_raw=w["close"].to_numpy(dtype=float),
        high=adjusted["high"].to_numpy(dtype=float),
        low=adjusted["low"].to_numpy(dtype=float),
        volume=w["volume"].to_numpy(dtype=float),
        hour=local.dt.hour.to_numpy(dtype=np.int64),
        weekday=local.dt.weekday.to_numpy(dtype=np.int64),
    )


# ------------------------------------------------------------------ statistics


def _num(x: float | None) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if np.isfinite(x) else None


def _mean(x: np.ndarray, scale: float = 1.0) -> float | None:
    return _num(x.mean() * scale) if len(x) else None


def _std(x: np.ndarray, scale: float = 1.0) -> float | None:
    return _num(np.std(x, ddof=1) * scale) if len(x) >= 2 else None


def _share(flags: np.ndarray) -> float | None:
    return _num(flags.mean()) if len(flags) else None


def _corr(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 2:
        return None
    a, b = a - a.mean(), b - b.mean()
    den = float((a * a).sum()) * float((b * b).sum())
    return _num((a * b).sum() / np.sqrt(den)) if den > 0 else None


def _runs(flags: np.ndarray) -> list[int]:
    runs, n = [], 0
    for f in flags:
        if f:
            n += 1
        elif n:
            runs.append(n)
            n = 0
    if n:
        runs.append(n)
    return runs


def _regimes(r: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """The defined returns and their high and low flags, or None when no ``rv``."""
    if len(r) < RV_BARS:
        return None
    rv = np.std(np.lib.stride_tricks.sliding_window_view(r, RV_BARS), axis=1, ddof=1)
    return r[RV_BARS - 1:], rv > np.percentile(rv, HIGH_PCT), rv < np.percentile(rv, LOW_PCT)


def _by(values: np.ndarray, labels: np.ndarray, size: int,
        stat: Callable[[np.ndarray], float | None]) -> tuple[list, list]:
    groups = [values[labels == x] for x in range(size)]
    return [stat(g) for g in groups], [len(g) for g in groups]


def _follow(r: np.ndarray, starts: Sequence[int], signs: Sequence[float], k: int
            ) -> dict[str, Any]:
    """The sums of ``R[j : j+k]`` (bars ``j+1 .. j+k``) times the sign, for each
    start ``j`` with k returns after it in W."""
    kept = [(j, s) for j, s in zip(starts, signs, strict=True) if j + k <= len(r)]
    sums = np.array([r[j:j + k].sum() * s for j, s in kept])
    return {"follow_share": _share(sums > 0), "mean_follow_bp": _mean(sums, BP),
            "count": len(kept)}


def common_block(w: WBars) -> dict[str, Any]:
    """The common block of one instrument (115 (b))."""
    r = w.returns
    rh, rw = w.hour[1:], w.weekday[1:]
    d = r - r.mean() if len(r) else r
    m2 = float((d ** 2).mean()) if len(r) else 0.0
    moments = len(r) >= 2 and m2 > 0
    hour_std = _by(r, rh, HOURS, lambda g: _std(g, BP))
    day_std = _by(r, rw, WEEKDAYS, lambda g: _std(g, BP))
    lags = range(1, MAX_LAG + 1)
    total = float(w.volume.sum())
    share = [(_num(w.volume[w.hour == h].sum() / total) if total > 0 else None)
             for h in range(HOURS)]
    reg = _regimes(r)
    regimes: dict[str, Any] = {"count": 0 if reg is None else len(reg[0])}
    for i, name in ((1, "high"), (2, "low")):
        runs = [] if reg is None else _runs(reg[i])
        regimes[name] = {"share": None if reg is None else _share(reg[i]),
                         "mean_run": _num(np.mean(runs)) if runs else None,
                         "runs": len(runs)}
    return {
        "returns": {
            "count": len(r),
            "mean_bp": _mean(r, BP),
            "std_bp": _std(r, BP),
            "skewness": _num(float((d ** 3).mean()) / m2 ** 1.5) if moments else None,
            "excess_kurtosis": _num(float((d ** 4).mean()) / m2 ** 2 - 3) if moments else None,
            "quantiles_bp": {key: (_num(np.quantile(r, q) * BP) if len(r) else None)
                             for key, q in QUANTILES},
        },
        "std_by_hour": {"std_bp": hour_std[0], "count": hour_std[1]},
        "std_by_weekday": {"std_bp": day_std[0], "count": day_std[1]},
        "autocorrelation": {
            "value": [_corr(r[:-k], r[k:]) if len(r) > k else None for k in lags],
            "count": [max(len(r) - k, 0) for k in lags],
        },
        "volume_share_by_hour": {"share": share,
                                 "count": [int((w.hour == h).sum()) for h in range(HOURS)]},
        "regimes": regimes,
    }


def _trend(w: WBars) -> dict[str, Any]:
    r = w.returns
    out = {}
    for k in TREND_K:
        m = len(r) // k
        sums = r[:m * k].reshape(m, k).sum(axis=1) if m else np.zeros(0)
        a, b = sums[:-1], sums[1:]
        same = ((a > 0) & (b > 0)) | ((a < 0) & (b < 0))
        out[f"k{k}"] = {"same_sign_share": _share(same), "autocorrelation": _corr(a, b),
                        "count": len(a)}
    return out


def _mean_reversion(w: WBars) -> dict[str, Any]:
    r = w.returns
    dev = _std(r)
    events = [] if dev is None else np.flatnonzero(np.abs(r) > EVENT_DEVIATIONS * dev).tolist()
    out: dict[str, Any] = {"events": len(events)}
    for k in REVERSION_K:
        kept = [i for i in events if i + k <= len(r) - 1]
        rev = np.array([-r[i + 1:i + 1 + k].sum() * np.sign(r[i]) for i in kept])
        out[f"k{k}"] = {"opposite_share": _share(rev > 0), "mean_reversal_bp": _mean(rev, BP),
                        "count": len(kept)}
    return out


def _breakout(w: WBars) -> dict[str, Any]:
    c, r = w.close, w.returns
    out = {}
    for n in BREAKOUT_N:
        block: dict[str, Any] = {}
        if len(c) > n:
            before = np.lib.stride_tricks.sliding_window_view(c[:-1], n)
            now = c[n:]
            direction = np.where(now > before.max(axis=1), 1.0,
                                 np.where(now < before.min(axis=1), -1.0, 0.0))
        else:
            direction = np.zeros(0)
        block["eligible"] = len(direction)
        block["breakout_share"] = _share(direction != 0)
        outs = np.flatnonzero(direction)
        starts, signs = (outs + n).tolist(), direction[outs].tolist()
        for k in BREAKOUT_K:
            block[f"k{k}"] = _follow(r, starts, signs, k)
        if len(c) >= n:
            hi = np.lib.stride_tricks.sliding_window_view(w.high, n).max(axis=1)
            lo = np.lib.stride_tricks.sliding_window_view(w.low, n).min(axis=1)
            ranges = (hi - lo) / w.close_raw[n - 1:]
        else:
            ranges = np.zeros(0)
        block["range_bp"] = _mean(ranges, BP)
        block["range_count"] = len(ranges)
        out[f"n{n}"] = block
    return out


def _volatility_regime(w: WBars) -> dict[str, Any]:
    reg = _regimes(w.returns)
    out = {}
    for i, name in ((1, "high"), (2, "low")):
        if reg is None:
            sel, both, a, b = np.zeros(0), np.zeros(0, dtype=bool), np.zeros(0), np.zeros(0)
        else:
            flags = reg[i]
            sel = reg[0][flags]
            both = flags[:-1] & flags[1:]
            a, b = reg[0][:-1][both], reg[0][1:][both]
        out[name] = {"mean_bp": _mean(sel, BP), "std_bp": _std(sel, BP), "count": len(sel),
                     "autocorrelation": _corr(a, b), "pairs": int(both.sum())}
    return out


def _volume(w: WBars) -> dict[str, Any]:
    v, r = w.volume, w.returns
    if len(v) > VOLUME_BARS:
        before = np.lib.stride_tricks.sliding_window_view(v[:-1], VOLUME_BARS)
        limit = before.mean(axis=1) + VOLUME_DEVIATIONS * np.std(before, axis=1, ddof=1)
        events = (np.flatnonzero(v[VOLUME_BARS:] > limit) + VOLUME_BARS).tolist()
        eligible = len(v) - VOLUME_BARS
    else:
        events, eligible = [], 0
    nxt = [j for j in events if j <= len(v) - 2]
    mean_abs = float(np.abs(r).mean()) if len(r) else 0.0
    ratio = (_num(float(np.abs(r[nxt]).mean()) / mean_abs) if nxt and mean_abs > 0
             else None)
    out: dict[str, Any] = {"eligible": eligible, "events": len(events),
                           "event_share": (len(events) / eligible) if eligible else None,
                           "abs_return_ratio": ratio, "ratio_count": len(nxt)}
    signs = [float(np.sign(r[j - 1])) for j in events]
    for k in VOLUME_K:
        out[f"k{k}"] = _follow(r, events, signs, k)
    return out


def _time_of_day(w: WBars) -> dict[str, Any]:
    r = w.returns
    out = {}
    for key, labels, size in (("by_hour", w.hour[1:], HOURS),
                              ("by_weekday", w.weekday[1:], WEEKDAYS)):
        means, counts = _by(r, labels, size, lambda g: _mean(g, BP))
        shares, _ = _by(r, labels, size, lambda g: _share(g > 0))
        out[key] = {"mean_bp": means, "positive_share": shares, "count": counts}
    return out


#: The cell block of each family (115 (c)).
CELL_BLOCKS: Mapping[str, Callable[[WBars], dict[str, Any]]] = {
    "trend": _trend,
    "mean_reversion": _mean_reversion,
    "breakout": _breakout,
    "volatility_regime": _volatility_regime,
    "volume": _volume,
    "time_of_day": _time_of_day,
}


def cell_block(family: str, w: WBars) -> dict[str, Any]:
    """The cell block of ``family`` for one instrument."""
    if family not in CELL_BLOCKS:
        raise ProfileError(f"no W profile cell block for family {family!r}")
    return CELL_BLOCKS[family](w)


def document(track: Track, cell: tuple[str, str], series: Mapping[str, WBars]
             ) -> dict[str, Any]:
    """The ``p1`` document of ``cell`` from W's bars of each of the track's instruments."""
    if tuple(cell) not in track.cells:
        raise ProfileError(f"{tuple(cell)!r} is not a cell of track {track.name!r}")
    family = cell[0]
    symbols = list(track.instruments)
    return {
        "version": VERSION,
        "instruments": symbols,
        "common": {s: common_block(series[s]) for s in symbols},
        "cell": {"family": family,
                 "instruments": {s: cell_block(family, series[s]) for s in symbols}},
    }


def profile(state_dir: Path, track: Track, instruments: Sequence[Instrument],
            calendars: Mapping[str, Calendar], day: date, cell: tuple[str, str]
            ) -> dict[str, Any]:
    """The W profile ``p1`` of ``cell`` for trading day ``day`` of ``track``."""
    if tuple(cell) not in track.cells:
        raise ProfileError(f"{tuple(cell)!r} is not a cell of track {track.name!r}")
    by_symbol = {i.symbol: i for i in instruments}
    series = {s: read_w(state_dir, track, by_symbol[s], calendars[by_symbol[s].calendar], day)
              for s in track.instruments}
    return document(track, cell, series)
