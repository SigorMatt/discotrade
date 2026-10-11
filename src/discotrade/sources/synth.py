"""Synthetic markets (DESIGN 17): the null market of 17.1, without contracts.

The bars of an instrument are one deterministic series that starts at
midnight UTC of its ``trusted_from`` date and runs over its calendar's
expected bar times (DESIGN 5.3). A request returns the part of that series in
[start, end), so the bars never depend on the requested range and incremental
fetches continue one series. Parameters come from the instrument's
``[source]`` table: ``seed``, ``hourly_vol``, ``start_price``,
``drop_fraction`` and ``roll_schedule``.

Per bar ``k`` with UTC hour ``h`` and ``s = hourly_vol * sqrt(bar_seconds /
3600) * VOL_BY_HOUR[h]``:

- the open differs from the previous close (``start_price`` before the first
  bar) by a log gap ``GAP_SCALE * s * z``;
- the log return from open to close is ``s * z``;
- the high is the larger of open and close times ``exp(RANGE_SCALE * s * |z|)``,
  the low the smaller divided by ``exp(RANGE_SCALE * s * |z|)``, each with its
  own draw, so highs and lows enclose open and close;
- volume is log-normal: ``VOLUME_MEDIAN * exp(VOLUME_BY_HOUR[h] +
  VOLUME_SIGMA * z)``;
- the bar is dropped (never returned, its price path kept) when a uniform draw
  is below ``drop_fraction``.

Each of the six kinds of draw has its own generator seeded with ``[seed,
kind]``, so the draws of bar ``k`` depend only on the seed and ``k``. Every
``z`` is an independent standard normal draw: nothing in the series is
predictable. The hour-of-day patterns are fixed shapes chosen by the project
(their root mean square is one); prices are not rounded to the tick. The
``contract`` column is the symbol. An instrument whose ``roll_schedule`` is
not ``"none"`` and ``fetch_contract`` are DESIGN 17.1's contracts, roadmap
step S0.2, and raise ``NotBuiltError``. Whether an instrument can be shorted
is a field of its record; its bars are generated like any other.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, time
from typing import Any

import numpy as np
import pandas as pd

from discotrade.config import Calendar, Instrument
from discotrade.sources.base import NotBuiltError
from discotrade.tradingcal import expected_bars

_HOURS = np.arange(24)
_SHAPE = 1.0 + 0.5 * np.cos(2.0 * np.pi * (_HOURS - 15) / 24.0)
#: Volatility multiplier by UTC hour of the bar's open; root mean square one.
VOL_BY_HOUR = _SHAPE / np.sqrt(np.mean(_SHAPE**2))
#: Log-volume offset by UTC hour of the bar's open.
VOLUME_BY_HOUR = 0.5 * np.cos(2.0 * np.pi * (_HOURS - 15) / 24.0)
GAP_SCALE = 0.1
RANGE_SCALE = 0.5
VOLUME_MEDIAN = 1000.0
VOLUME_SIGMA = 0.5

_RETURN, _GAP, _HIGH, _LOW, _VOLUME, _DROP = range(6)


def _aware(instant: datetime, what: str) -> datetime:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError(f"{what} {instant!r} must be timezone-aware")
    return instant.astimezone(UTC)


class SynthSource:
    """The null synthetic market. ``available_until(now) = now`` (DESIGN 5.5)."""

    name = "synth"

    def __init__(self, calendars: Mapping[str, Calendar], bar_seconds: int) -> None:
        if isinstance(bar_seconds, bool) or not isinstance(bar_seconds, int) or bar_seconds < 1:
            raise ValueError(f"bar_seconds must be a positive integer, not {bar_seconds!r}")
        self.calendars = dict(calendars)
        self.bar_seconds = bar_seconds

    def available_until(self, now: datetime) -> datetime:
        return _aware(now, "now")

    def fetch_contract(
        self, instrument: Instrument, contract: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        raise NotBuiltError(
            "synth: per-contract bars (fetch_contract, DESIGN 17.1) are roadmap step S0.2, "
            "not built yet"
        )

    def fetch(self, instrument: Instrument, start: datetime, end: datetime) -> pd.DataFrame:
        """The instrument's bars with ``ts`` in [start, end), dropped bars left out."""
        bars, dropped = self._series(instrument, start, end)
        return bars[~dropped].reset_index(drop=True)

    def dropped(self, instrument: Instrument, start: datetime, end: datetime) -> list[datetime]:
        """The expected bar times in [start, end) that the generator drops."""
        bars, dropped = self._series(instrument, start, end)
        return [t.to_pydatetime() for t in bars.loc[dropped, "ts"]]

    def _series(
        self, instrument: Instrument, start: datetime, end: datetime
    ) -> tuple[pd.DataFrame, np.ndarray]:
        start, end = _aware(start, "start"), _aware(end, "end")
        src = instrument.source
        if src.adapter != "synth":
            raise ValueError(f"{instrument.symbol}: source adapter is {src.adapter!r}, "
                             f"not 'synth'")
        roll = src.get("roll_schedule", "none")
        if roll != "none":
            raise NotBuiltError(
                f"synth: {instrument.symbol} has roll_schedule {roll!r}; contracts "
                "(DESIGN 17.1) are roadmap step S0.2, not built yet"
            )
        if instrument.calendar not in self.calendars:
            raise ValueError(f"{instrument.symbol}: no calendar record {instrument.calendar!r}")
        origin = datetime.combine(instrument.trusted_from, time(), tzinfo=UTC)
        times = expected_bars(self.calendars[instrument.calendar], origin,
                              max(origin, end), self.bar_seconds)
        frame, dropped = _generate(times, src.get("seed"), src.get("hourly_vol"),
                                   src.get("start_price"), src.get("drop_fraction", 0.0),
                                   self.bar_seconds, instrument.symbol)
        keep = ((frame["ts"] >= pd.Timestamp(start)).to_numpy()
                & (frame["ts"] < pd.Timestamp(end)).to_numpy())
        return frame[keep].reset_index(drop=True), dropped[keep]


def _generate(times: list[datetime], seed: int, hourly_vol: float, start_price: float,
              drop_fraction: float, bar_seconds: int,
              symbol: str) -> tuple[pd.DataFrame, np.ndarray]:
    n = len(times)

    def draws(kind: int) -> Any:
        return np.random.default_rng([seed, kind])

    ts = pd.DatetimeIndex(times).tz_convert("UTC").astype("datetime64[ns, UTC]")
    hours = ts.hour.to_numpy()
    s = hourly_vol * np.sqrt(bar_seconds / 3600.0) * VOL_BY_HOUR[hours]
    ret = s * draws(_RETURN).standard_normal(n)
    gap = GAP_SCALE * s * draws(_GAP).standard_normal(n)
    log_close = np.log(start_price) + np.cumsum(gap + ret)
    close = np.exp(log_close)
    open_ = np.exp(log_close - ret)
    top, bottom = np.maximum(open_, close), np.minimum(open_, close)
    high = np.maximum(top, top * np.exp(RANGE_SCALE * s * np.abs(
        draws(_HIGH).standard_normal(n))))
    low = np.minimum(bottom, bottom / np.exp(RANGE_SCALE * s * np.abs(
        draws(_LOW).standard_normal(n))))
    volume = VOLUME_MEDIAN * np.exp(VOLUME_BY_HOUR[hours]
                                    + VOLUME_SIGMA * draws(_VOLUME).standard_normal(n))
    dropped = draws(_DROP).random(n) < drop_fraction
    frame = pd.DataFrame({
        "ts": pd.Series(ts), "open": open_, "high": high, "low": low, "close": close,
        "volume": volume, "contract": [symbol] * n,
    })
    return frame, dropped
