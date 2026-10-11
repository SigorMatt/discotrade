"""The public exchange adapter, for ``test_only`` instruments (DESIGN 5.5; decision
2026-10-12 12; I-9).

Hourly bars from a public endpoint that needs no key. It exists to exercise a
real HTTP source during development; no gate depends on it. The endpoint is
configuration: the instrument's ``[source]`` table gives ``base_url`` (the
URL of the bars endpoint) and ``market`` (the market's name at the
endpoint); this module names neither.

``available_until(now) = now``. ``fetch`` returns the closed bars with ``ts``
in [start, end): a bar is returned when ``ts >= start`` and ``ts + 1 hour <=
end``, so with ``end = available_until(now)`` the bar still open at ``now``
is never returned. ``contract`` is the instrument's symbol (the instrument
does not roll).

The request and response shape, NOT PROVEN against the real endpoint (tests
use ``httpx.MockTransport``): ``GET <base_url>?symbol=<market>&interval=1h
&startTime=<ms>&endTime=<ms>&limit=1000``, ``endTime`` inclusive, answered
with a JSON array of rows, each an array whose first six items are the bar's
open time in milliseconds since the epoch (an integer) and its open, high,
low, close and volume (numbers or decimal strings), at most ``limit`` rows in
ascending time. The adapter asks again from the bar after the last one
returned until a reply is shorter than ``limit``.

Anything else is refused with a ``SourceError`` and nothing is returned: a
status other than 200, a body that is not JSON, a row that is not an array of
at least six items, an open time that is not an integer or is off the hour,
a value that is not a number, rows out of order or repeated, a reply that
does not move forward. A value that parses to NaN or infinity is returned
as it is; ``bars fetch`` drops such bars (decision 2026-10-12 6).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pandas as pd

from discotrade.config import Instrument
from discotrade.sources.base import BAR_VALUES, SourceError, bars_frame

BAR_SECONDS = 3600
INTERVAL = "1h"
LIMIT = 1000
TIMEOUT_SECONDS = 30.0


def _aware(instant: datetime, what: str) -> datetime:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError(f"{what} {instant!r} must be timezone-aware")
    return instant.astimezone(UTC)


def _ms(instant: datetime) -> int:
    return int(instant.timestamp() * 1000)


class CryptoSource:
    """The public exchange adapter. ``available_until(now) = now`` (DESIGN 5.5)."""

    name = "crypto"

    def __init__(self, bar_seconds: int, transport: httpx.BaseTransport | None = None) -> None:
        if bar_seconds != BAR_SECONDS or isinstance(bar_seconds, bool):
            raise ValueError(f"the crypto adapter serves hourly bars ({BAR_SECONDS} seconds), "
                             f"not {bar_seconds!r}")
        self.bar_seconds = bar_seconds
        self._transport = transport

    def available_until(self, now: datetime) -> datetime:
        return _aware(now, "now")

    def fetch(self, instrument: Instrument, start: datetime, end: datetime) -> pd.DataFrame:
        """The closed hourly bars with ``ts`` in [start, end); ``contract`` is the symbol."""
        src = instrument.source
        if src.adapter != "crypto":
            raise ValueError(f"{instrument.symbol}: source adapter is {src.adapter!r}, "
                             "not 'crypto'")
        start, end = _aware(start, "start"), _aware(end, "end")
        step = self.bar_seconds * 1000
        lo, hi = _ms(start), _ms(end)
        first = -(-lo // step) * step                      # the first bar time at or after start
        rows: list[tuple[int, list[float]]] = []
        with httpx.Client(transport=self._transport, timeout=TIMEOUT_SECONDS) as client:
            cursor = first
            while cursor + step <= hi:
                page = self._page(client, instrument, cursor, hi - 1)
                if not page:
                    break
                if page[0][0] < cursor or (rows and page[0][0] <= rows[-1][0]):
                    raise SourceError(f"{instrument.symbol}: the endpoint's reply does not "
                                      "move forward")
                rows.extend(page)
                if len(page) < LIMIT:
                    break
                cursor = page[-1][0] + step
        kept = [(t, v) for t, v in rows if t >= lo and t + step <= hi]
        ts = pd.to_datetime([t for t, _ in kept], unit="ms", utc=True)
        values = {name: [v[i] for _, v in kept] for i, name in enumerate(BAR_VALUES)}
        return bars_frame(ts, values, [instrument.symbol] * len(kept))

    def fetch_contract(
        self, instrument: Instrument, contract: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """The instrument does not roll: its one contract is its symbol."""
        if contract != instrument.symbol:
            raise ValueError(f"{instrument.symbol}: no contract {contract!r}; the instrument "
                             "does not roll")
        return self.fetch(instrument, start, end)

    def _page(self, client: httpx.Client, instrument: Instrument, start_ms: int,
              end_ms: int) -> list[tuple[int, list[float]]]:
        where = f"{instrument.symbol}: the endpoint"
        params: dict[str, str | int] = {
            "symbol": instrument.source.get("market"), "interval": INTERVAL,
            "startTime": start_ms, "endTime": end_ms, "limit": LIMIT,
        }
        try:
            response = client.get(instrument.source.get("base_url"), params=params)
        except httpx.HTTPError as exc:
            raise SourceError(f"{where} could not be reached: {type(exc).__name__}: "
                              f"{exc}") from None
        if response.status_code != 200:
            raise SourceError(f"{where} answered status {response.status_code}")
        try:
            body: Any = response.json()
        except ValueError:
            raise SourceError(f"{where} answered with a body that is not JSON") from None
        if not isinstance(body, list):
            raise SourceError(f"{where} answered with {type(body).__name__}, not an array "
                              "of rows")
        step = self.bar_seconds * 1000
        out: list[tuple[int, list[float]]] = []
        for n, row in enumerate(body):
            if not isinstance(row, list) or len(row) < 6:
                raise SourceError(f"{where}: row {n} is not an array of at least six items")
            t = row[0]
            if isinstance(t, bool) or not isinstance(t, int) or t % step:
                raise SourceError(f"{where}: row {n} has open time {t!r}, not an integer "
                                  f"multiple of {step} milliseconds")
            values = [_number(v, f"{where}: row {n}") for v in row[1:6]]
            if out and t <= out[-1][0]:
                raise SourceError(f"{where}: row {n} is out of order or repeated")
            out.append((t, values))
        return out


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise SourceError(f"{where} has a value that is not a number: {value!r}")
    try:
        number = float(value)
    except ValueError:
        raise SourceError(f"{where} has a value that is not a number: {value!r}") from None
    return number
