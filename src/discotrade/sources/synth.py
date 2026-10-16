"""Synthetic markets (DESIGN 17): the null market of 17.1, with contracts.

The bars of an instrument are one deterministic series that starts at
midnight UTC of its ``trusted_from`` date and runs over its calendar's
expected bar times (DESIGN 5.3). A request returns the part of that series in
[start, end), so the bars never depend on the requested range and incremental
fetches continue one series. Every setting comes from the instrument's
``[source]`` table (DESIGN 4.2, decision 2026-10-12 10): ``seed``,
``hourly_vol``, ``start_price``, ``drop_fraction``, ``gap_scale``,
``range_scale``, ``volume_median``, ``volume_sigma``, ``hour_vol_amplitude``,
``hour_volume_amplitude``, ``hour_peak_utc``, ``roll_schedule`` and, for a
quarterly schedule, ``roll_day``, ``contract_overlap_bars`` and
``contract_offset_scale``.

The hour-of-day shapes, by UTC hour ``h`` of the bar's open, with ``P =
hour_peak_utc``:

- volatility: ``1 + hour_vol_amplitude * cos(2 pi (h - P) / 24)``, scaled to
  root mean square one over the 24 hours (``vol_by_hour``);
- log-volume offset: ``hour_volume_amplitude * cos(2 pi (h - P) / 24)``
  (``volume_by_hour``).

The underlying series. Per bar ``k`` with UTC hour ``h`` and ``s = hourly_vol
* sqrt(bar_seconds / 3600) * vol_by_hour[h]``:

- the open differs from the previous close (``start_price`` before the first
  bar) by a log gap ``gap_scale * s * z``;
- the log return from open to close is ``s * z``;
- the high is the larger of open and close times ``exp(range_scale * s * |z|)``,
  the low the smaller divided by ``exp(range_scale * s * |z|)``, each with its
  own draw, so highs and lows enclose open and close;
- volume is log-normal: ``volume_median * exp(volume_by_hour[h] +
  volume_sigma * z)``;
- the bar is dropped (never returned, its price path kept) when a uniform draw
  is below ``drop_fraction``.

Each of the six kinds of draw has its own generator seeded with ``[seed,
kind]``, so the draws of bar ``k`` depend only on the seed and ``k``. Every
``z`` is an independent standard normal draw: nothing in the series is
predictable. Prices are not rounded to the tick.

Contracts. With ``roll_schedule = "none"`` the ``contract`` column is the
symbol and the series is the underlying. With ``"quarterly"`` there is one
contract per quarter, named ``<symbol>-YYYY-MM`` for its month (March, June,
September, December). On ``roll_day`` of each of those months at 00:00 UTC
the next contract becomes current, from the first expected bar at or after
that instant (the roll bar). A contract's price is the underlying plus its
constant: ``contract_offset_scale * z`` rounded to the tick, ``z`` a standard
normal draw from a generator seeded with ``[seed, 6, q]``, ``q = 4 * year +
month // 3 - 1`` (``contract_constant``). The continuous series (``fetch``) is
the underlying plus the constant of the contract current at each bar, its
four prices only; volume is the underlying's. A contract has bars (``
fetch_contract``) from ``contract_overlap_bars`` expected bars before the
bar at which it becomes current to as many after the bar at which it stops
being current, so adjacent contracts overlap by that many bars on each side
of a roll (DESIGN 5.6 measures its gap there). Its dropped bars are the
underlying's: a dropped bar time is missing from every contract. The first
contract is the one current at the first bar; earlier ones are unknown.
Whether an instrument can be shorted is a field of its record; its bars are
generated like any other.

Generation (mission 9 U3). A request still generates the series from its
start, ``trusted_from``, since every bar's price depends on every draw
before it; it generates no further than the request's end, and builds the
rows and contract names of the requested range only. The process keeps, per
instrument record, the longest series it has generated and serves every
later request whose end it covers from that series' prefix (a prefix of the
generation is the generation of the prefix: each draw of bar ``k`` depends
only on the seed and ``k``, and the cumulative sum is sequential), so a run
that builds its source once generates each series once.

The series kept for the process (decision 121 of 2026-10-16-m15, finding
D-013). What a source generated is kept for the life of the process, not of
the source, keyed by everything the generation reads: the instrument record's
``[source]`` table (the seed among it), its ``trusted_from``, its calendar
record and the bar length. A record that differs in any of them is generated
from its own settings; an equal record on a new source (each day run builds
its own) is served from what an earlier one kept. A request that ends beyond
the kept series extends it: the expected bar times kept are reused and only
those after them are listed (a bar time's membership depends only on that
time and the calendar), and the underlying is generated again over the
extended times, so it is the generation from ``trusted_from`` exactly as
before. ``clear_cache`` forgets every kept series.
"""

from __future__ import annotations

import bisect
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import numpy as np
import pandas as pd

from discotrade.config import Calendar, Instrument, Source
from discotrade.tradingcal import expected_bars

_HOURS = np.arange(24)
_RETURN, _GAP, _HIGH, _LOW, _VOLUME, _DROP, _CONTRACT = range(7)
_PRICES = ("open", "high", "low", "close")
#: How far past the requested end the schedule looks for roll bars, so that a
#: contract that starts trading before its roll is placed exactly. It holds
#: when the calendar has at least ``contract_overlap_bars`` bars in it.
_LOOKAHEAD = timedelta(days=120)
_NAME = re.compile(r"(\d{4})-(03|06|09|12)")


def vol_by_hour(amplitude: float, peak: int) -> np.ndarray:
    """The volatility multiplier by UTC hour of the bar's open; root mean square one."""
    shape = 1.0 + amplitude * np.cos(2.0 * np.pi * (_HOURS - peak) / 24.0)
    return shape / np.sqrt(np.mean(shape**2))


def volume_by_hour(amplitude: float, peak: int) -> np.ndarray:
    """The log-volume offset by UTC hour of the bar's open."""
    return amplitude * np.cos(2.0 * np.pi * (_HOURS - peak) / 24.0)


def _aware(instant: datetime, what: str) -> datetime:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError(f"{what} {instant!r} must be timezone-aware")
    return instant.astimezone(UTC)


def _roll_instant(quarter: int, roll_day: int) -> datetime:
    return datetime(quarter // 4, (quarter % 4 + 1) * 3, roll_day, tzinfo=UTC)


def _contract_name(symbol: str, quarter: int) -> str:
    return f"{symbol}-{quarter // 4:04d}-{(quarter % 4 + 1) * 3:02d}"


#: The series kept for the process: per (``[source]`` table, ``trusted_from``,
#: calendar record, bar length), the end it was generated to, the expected bar
#: times to that end plus the look-ahead, and the underlying before that end.
_SERIES: dict[tuple[Source, date, Calendar, int],
              tuple[datetime, list[datetime], pd.DataFrame, np.ndarray]] = {}


def clear_cache() -> None:
    """Forget every series kept for the process."""
    _SERIES.clear()


class SynthSource:
    """The synthetic market. ``available_until(now) = now`` (DESIGN 5.5)."""

    name = "synth"

    def __init__(self, calendars: Mapping[str, Calendar], bar_seconds: int) -> None:
        if isinstance(bar_seconds, bool) or not isinstance(bar_seconds, int) or bar_seconds < 1:
            raise ValueError(f"bar_seconds must be a positive integer, not {bar_seconds!r}")
        self.calendars = dict(calendars)
        self.bar_seconds = bar_seconds

    def available_until(self, now: datetime) -> datetime:
        return _aware(now, "now")

    def fetch(self, instrument: Instrument, start: datetime, end: datetime) -> pd.DataFrame:
        """The instrument's continuous bars with ``ts`` in [start, end), dropped bars left out."""
        bars, dropped = self._series(instrument, start, end, None)
        return bars[~dropped].reset_index(drop=True)

    def fetch_contract(
        self, instrument: Instrument, contract: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """The bars of one contract with ``ts`` in [start, end), dropped bars left out."""
        bars, dropped = self._series(instrument, start, end, contract)
        return bars[~dropped].reset_index(drop=True)

    def dropped(self, instrument: Instrument, start: datetime, end: datetime) -> list[datetime]:
        """The expected bar times in [start, end) that the generator drops."""
        bars, dropped = self._series(instrument, start, end, None)
        return [t.to_pydatetime() for t in bars.loc[dropped, "ts"]]

    def contract_constant(self, instrument: Instrument, contract: str) -> float:
        """What ``contract``'s prices add to the underlying's (0 when the instrument
        does not roll and ``contract`` is its symbol)."""
        src = self._checked(instrument)
        if src.get("roll_schedule", "none") == "none":
            if contract != instrument.symbol:
                raise ValueError(f"{instrument.symbol}: no contract {contract!r}; the "
                                 "instrument does not roll")
            return 0.0
        return _constant(src, instrument.tick_size, self._quarter(instrument, contract))

    def _checked(self, instrument: Instrument) -> Source:
        src = instrument.source
        if src.adapter != "synth":
            raise ValueError(f"{instrument.symbol}: source adapter is {src.adapter!r}, "
                             f"not 'synth'")
        if instrument.calendar not in self.calendars:
            raise ValueError(f"{instrument.symbol}: no calendar record {instrument.calendar!r}")
        return src

    @staticmethod
    def _quarter(instrument: Instrument, contract: str) -> int:
        prefix = f"{instrument.symbol}-"
        match = _NAME.fullmatch(contract[len(prefix):]) if contract.startswith(prefix) else None
        if match is None:
            raise ValueError(f"{instrument.symbol}: no contract {contract!r}; contracts are "
                             f"named {prefix}YYYY-MM for March, June, September, December")
        return 4 * int(match.group(1)) + int(match.group(2)) // 3 - 1

    def _underlying(self, instrument: Instrument, src: Source, cal: Calendar,
                    origin: datetime, stop: datetime
                    ) -> tuple[list[datetime], pd.DataFrame, np.ndarray]:
        """The expected bar times from ``origin`` to ``stop`` plus the look-ahead,
        and the underlying series over those before ``stop``, from the series
        kept for the process for the record when it reaches ``stop``."""
        key = (src, instrument.trusted_from, cal, self.bar_seconds)
        cached = _SERIES.get(key)
        if cached is None or cached[0] < stop:
            if cached is None:
                ahead = expected_bars(cal, origin, stop + _LOOKAHEAD, self.bar_seconds)
            else:
                # The times kept end before the kept stop plus the look-ahead.
                ahead = cached[1] + expected_bars(cal, cached[0] + _LOOKAHEAD,
                                                  stop + _LOOKAHEAD, self.bar_seconds)
            frame, dropped = _generate(ahead[:bisect.bisect_left(ahead, stop)], src,
                                       self.bar_seconds)
            cached = (stop, ahead, frame, dropped)
            _SERIES[key] = cached
        _, ahead, frame, dropped = cached
        ahead = ahead[:bisect.bisect_left(ahead, stop + _LOOKAHEAD)]
        n = bisect.bisect_left(ahead, stop)
        return ahead, frame.iloc[:n], dropped[:n]

    def _series(
        self, instrument: Instrument, start: datetime, end: datetime, contract: str | None
    ) -> tuple[pd.DataFrame, np.ndarray]:
        start, end = _aware(start, "start"), _aware(end, "end")
        src = self._checked(instrument)
        symbol = instrument.symbol
        cal = self.calendars[instrument.calendar]
        origin = datetime.combine(instrument.trusted_from, time(), tzinfo=UTC)
        stop = max(origin, end)
        ahead, frame, dropped = self._underlying(instrument, src, cal, origin, stop)
        n = len(frame)
        lo = min(n, bisect.bisect_left(ahead, start))      # the first bar at or after start
        if src.get("roll_schedule", "none") == "none":
            if contract is not None and contract != symbol:
                raise ValueError(f"{symbol}: no contract {contract!r}; the instrument does "
                                 "not roll")
            out = frame.iloc[lo:].reset_index(drop=True)
            out["contract"] = _names([symbol] * len(out))
            return out, dropped[lo:]
        if contract is None:
            return _contracts(frame, dropped, ahead, src, instrument, None, lo)
        frame, dropped = _contracts(frame, dropped, ahead, src, instrument,
                                    self._quarter(instrument, contract))
        keep = ((frame["ts"] >= pd.Timestamp(start)).to_numpy()
                & (frame["ts"] < pd.Timestamp(end)).to_numpy())
        return frame[keep].reset_index(drop=True), dropped[keep]


def _names(names: list[str]) -> Any:
    """The contract column of ``names``, in the type a column of names takes even
    when ``names`` is empty (as a slice of a longer column of names keeps it)."""
    return pd.array(names, dtype=pd.Series(["x"]).dtype)


def _constant(src: Source, tick: float, quarter: int) -> float:
    z = np.random.default_rng([src.get("seed"), _CONTRACT, quarter]).standard_normal()
    return float(np.round(src.get("contract_offset_scale") * z / tick) * tick)


def _contracts(frame: pd.DataFrame, dropped: np.ndarray, ahead: list[datetime], src: Source,
               instrument: Instrument, quarter: int | None,
               lo: int = 0) -> tuple[pd.DataFrame, np.ndarray]:
    """The continuous series from bar ``lo`` on (``quarter`` None) or one
    contract's bars, from the underlying ``frame`` over ``ahead[:len(frame)]``."""
    n, roll_day = len(frame), src.get("roll_day")
    overlap = src.get("contract_overlap_bars")
    if not ahead:                            # no expected bar at all
        out = frame.copy()
        out["contract"] = pd.Series([], dtype=object)
        return out, dropped
    # The first contract: the one current at the first bar.
    first = 4 * ahead[0].year + (ahead[0].month - 1) // 3 - 1
    while _roll_instant(first, roll_day) <= ahead[0]:
        first += 1
    # rolls[i]: the index of the bar at which contract first + i stops being current.
    rolls: list[int] = []
    while not rolls or rolls[-1] < n:
        rolls.append(bisect.bisect_left(ahead, _roll_instant(first + len(rolls), roll_day)))
    if quarter is None:
        current = first + np.searchsorted(np.array(rolls), np.arange(lo, n), side="right")
        constants = {q: _constant(src, instrument.tick_size, q) for q in set(current.tolist())}
        add = np.array([constants[q] for q in current], dtype=float)
        out = frame.iloc[lo:].reset_index(drop=True)
        for col in _PRICES:
            out[col] = frame[col].to_numpy()[lo:] + add
        names = {q: _contract_name(instrument.symbol, q) for q in constants}
        out["contract"] = _names([names[q] for q in current])
        return out, dropped[lo:]
    if quarter < first:
        raise ValueError(f"{instrument.symbol}: no contract "
                         f"{_contract_name(instrument.symbol, quarter)!r}; it was current "
                         "only before the series starts")
    i = quarter - first
    while len(rolls) <= i:
        rolls.append(bisect.bisect_left(ahead, _roll_instant(first + len(rolls), roll_day)))
    begins = 0 if i == 0 else rolls[i - 1]
    if begins >= len(ahead):                 # becomes current beyond the look-ahead
        lo = hi = n
    else:
        lo, hi = max(0, begins - overlap), min(n, rolls[i] + overlap)
    lo = min(lo, n)
    out = frame.iloc[lo:hi].copy()
    const = _constant(src, instrument.tick_size, quarter)
    for col in _PRICES:
        out[col] = out[col].to_numpy() + const
    out["contract"] = [_contract_name(instrument.symbol, quarter)] * len(out)
    return out.reset_index(drop=True), dropped[lo:hi]


def _generate(times: list[datetime], src: Source,
              bar_seconds: int) -> tuple[pd.DataFrame, np.ndarray]:
    """The underlying series over ``times``, without its ``contract`` column."""
    n = len(times)
    seed = src.get("seed")
    hourly_vol, start_price = src.get("hourly_vol"), src.get("start_price")
    gap_scale, range_scale = src.get("gap_scale"), src.get("range_scale")
    volume_median, volume_sigma = src.get("volume_median"), src.get("volume_sigma")
    peak = src.get("hour_peak_utc")

    def draws(kind: int) -> Any:
        return np.random.default_rng([seed, kind])

    ts = pd.DatetimeIndex(times, dtype="datetime64[ns, UTC]")
    hours = ts.hour.to_numpy()
    s = hourly_vol * np.sqrt(bar_seconds / 3600.0) * vol_by_hour(
        src.get("hour_vol_amplitude"), peak)[hours]
    ret = s * draws(_RETURN).standard_normal(n)
    gap = gap_scale * s * draws(_GAP).standard_normal(n)
    log_close = np.log(start_price) + np.cumsum(gap + ret)
    close = np.exp(log_close)
    open_ = np.exp(log_close - ret)
    top, bottom = np.maximum(open_, close), np.minimum(open_, close)
    high = np.maximum(top, top * np.exp(range_scale * s * np.abs(
        draws(_HIGH).standard_normal(n))))
    low = np.minimum(bottom, bottom / np.exp(range_scale * s * np.abs(
        draws(_LOW).standard_normal(n))))
    volume = volume_median * np.exp(volume_by_hour(src.get("hour_volume_amplitude"), peak)[hours]
                                    + volume_sigma * draws(_VOLUME).standard_normal(n))
    dropped = draws(_DROP).random(n) < src.get("drop_fraction", 0.0)
    frame = pd.DataFrame({
        "ts": pd.Series(ts), "open": open_, "high": high, "low": low, "close": close,
        "volume": volume,
    })
    return frame, dropped
