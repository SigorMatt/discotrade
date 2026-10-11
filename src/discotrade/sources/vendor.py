"""The futures data vendor's adapter (DESIGN 5.5; decision 2026-10-12 11; I-9, I-13).

Hourly (``bar_seconds``) bars of the instrument's continuous contract from the
vendor's historical interface. Everything that names a market comes from the
instrument's ``[source]`` table: ``dataset``, ``symbol`` (the continuous
symbol, whose form carries the roll rule) and ``max_cost_usd`` (default 5.0).
This module names only the vendor's client package and the key variable.

``available_until(now) = now - 24 hours``. The key is read from
``DATABENTO_API_KEY`` when the adapter first talks to the vendor; without it
the adapter refuses before importing the client or making any request. The
client package is imported then too, never when this module is imported.
The key is passed to the client and to nothing else: every error text that
leaves this module has the key replaced by ``<redacted>``, and the client's
own exception is not chained.

Before every request for bars the adapter asks the vendor's cost estimate
for exactly that request and refuses, fetching nothing, when it is above
``max_cost_usd``.

The client calls, which match the vendor's official client as read from its
source (``databento`` 0.87.0, the version ``uv.lock`` pins) and are NOT
PROVEN against the real service until live check L1:

- ``Historical(key=...)``;
- ``.metadata.get_cost(dataset=, symbols=[...], schema=, stype_in=, start=,
  end=)`` returning US dollars as a number;
- ``.timeseries.get_range(dataset=, symbols=[...], schema=, stype_in=,
  start=, end=)`` returning a store whose ``.to_df(price_type="float",
  pretty_ts=True, map_symbols=False)`` is a frame indexed (or with a column)
  ``ts_event``, the bar's open in UTC, with ``open``, ``high``, ``low``,
  ``close``, ``volume`` and ``instrument_id``;
- ``.symbology.resolve(dataset=, symbols=[...], stype_in="instrument_id",
  stype_out="raw_symbol", start_date=, end_date=)`` returning ``{"result":
  {"<id>": [{"d0": date, "d1": date, "s": raw symbol}, ...]}}`` with ``d0``
  inclusive and ``d1`` exclusive UTC dates;
- ``.metadata.get_dataset_range(dataset=)`` returning ``{"end": instant,
  ...}`` (used by live check L1 only).

``contract``: each bar of the continuous series carries the vendor's
instrument id of the contract it came from; the contract is that id's raw
symbol on the bar's UTC date, through the vendor's symbology. A bar whose id
has no raw symbol on its date is refused. ``fetch_contract`` asks for one raw
symbol and labels its bars with it.
"""

from __future__ import annotations

import importlib
import math
import os
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any, TypeVar

import pandas as pd

from discotrade.config import Instrument
from discotrade.sources.base import BAR_VALUES, SourceError, bars_frame

CLIENT_PACKAGE = "databento"
KEY_ENV = "DATABENTO_API_KEY"
DEFAULT_MAX_COST_USD = 5.0
EMBARGO = timedelta(hours=24)
#: The vendor's bar schemas by bar length in seconds.
SCHEMAS = {1: "ohlcv-1s", 60: "ohlcv-1m", 3600: "ohlcv-1h", 86400: "ohlcv-1d"}
CONTINUOUS = "continuous"
RAW_SYMBOL = "raw_symbol"
INSTRUMENT_ID = "instrument_id"
REDACTED = "<redacted>"

T = TypeVar("T")


def key_present() -> bool:
    """Whether the vendor key is set in the environment (its value is not read out)."""
    return bool(os.environ.get(KEY_ENV, "").strip())


def no_key_message() -> str:
    return (f"{KEY_ENV} is not set: the vendor adapter needs the vendor's key in the "
            "environment (I-13); no request was made")


def _aware(instant: datetime, what: str) -> datetime:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError(f"{what} {instant!r} must be timezone-aware")
    return instant.astimezone(UTC)


def _iso(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat()


class VendorSource:
    """The vendor adapter. ``available_until(now) = now - 24 hours`` (DESIGN 5.5)."""

    name = "vendor"

    def __init__(self, bar_seconds: int) -> None:
        if bar_seconds not in SCHEMAS or isinstance(bar_seconds, bool):
            raise ValueError(f"the vendor adapter serves bars of {sorted(SCHEMAS)} seconds, "
                             f"not {bar_seconds!r}")
        self.bar_seconds = bar_seconds
        self.schema = SCHEMAS[bar_seconds]
        self._client: Any = None
        self._key = ""

    # --- the client, the key and errors ---------------------------------------------

    def _redact(self, text: str) -> str:
        return text.replace(self._key, REDACTED) if self._key else text

    def _guard(self, what: str, call: Callable[[], T]) -> T:
        """``call()``, with any error turned into a ``SourceError`` that holds no key."""
        try:
            return call()
        except SourceError as exc:
            raise SourceError(self._redact(str(exc))) from None
        except Exception as exc:  # the client's errors are its own; none may leak the key
            raise SourceError(self._redact(f"vendor {what}: {type(exc).__name__}: {exc}")
                              ) from None

    def client(self) -> Any:
        """The vendor's client, made on first use; refuses without the key."""
        if self._client is not None:
            return self._client
        key = os.environ.get(KEY_ENV, "")
        if not key.strip():
            raise SourceError(no_key_message())
        try:
            module = importlib.import_module(CLIENT_PACKAGE)
        except ImportError:
            raise SourceError(f"the vendor's client package {CLIENT_PACKAGE!r} is not "
                              "installed; install the 'vendor' extra (uv sync --extra "
                              "vendor)") from None
        self._key = key
        self._client = self._guard("client", lambda: module.Historical(key=key))
        return self._client

    # --- the interface -----------------------------------------------------------------

    def available_until(self, now: datetime) -> datetime:
        return _aware(now, "now") - EMBARGO

    def fetch(self, instrument: Instrument, start: datetime, end: datetime) -> pd.DataFrame:
        """The continuous series' bars with ``ts`` in [start, end), ``contract`` resolved."""
        dataset, symbol = self._source(instrument)
        start, end = _aware(start, "start"), _aware(end, "end")
        if start >= end:
            return _empty()
        raw = self._bars(instrument, dataset, symbol, CONTINUOUS, start, end, ids=True)
        if raw.empty:
            return _empty()
        return bars_frame(raw["ts"], raw, self._contracts(dataset, raw))

    def fetch_contract(
        self, instrument: Instrument, contract: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """The bars of one underlying contract (a raw symbol) with ``ts`` in [start, end)."""
        dataset, _ = self._source(instrument)
        start, end = _aware(start, "start"), _aware(end, "end")
        if not isinstance(contract, str) or not contract.strip():
            raise SourceError(f"{instrument.symbol}: contract must be a non-empty string")
        if start >= end:
            return _empty()
        raw = self._bars(instrument, dataset, contract, RAW_SYMBOL, start, end, ids=False)
        return bars_frame(raw["ts"], raw, [contract] * len(raw))

    # --- the parts --------------------------------------------------------------------------

    def cost(self, instrument: Instrument, symbol: str, stype: str, start: datetime,
             end: datetime) -> float:
        """The vendor's cost estimate, in US dollars, of one request for bars."""
        dataset, _ = self._source(instrument)
        client = self.client()
        value = self._guard("cost estimate", lambda: client.metadata.get_cost(
            dataset=dataset, symbols=[symbol], schema=self.schema, stype_in=stype,
            start=_iso(start), end=_iso(end)))
        if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(
                value) or value < 0:
            raise SourceError(f"{instrument.symbol}: the vendor's cost estimate is not a "
                              f"non-negative number: {value!r}")
        return float(value)

    def dataset_end(self, instrument: Instrument) -> datetime:
        """The end of the instrument's dataset as the vendor reports it (live check L1)."""
        dataset, _ = self._source(instrument)
        client = self.client()
        reply = self._guard("dataset range",
                            lambda: client.metadata.get_dataset_range(dataset=dataset))
        try:
            end = pd.Timestamp(reply["end"])
        except (KeyError, TypeError, ValueError):
            raise SourceError(f"{instrument.symbol}: the vendor's dataset range has no "
                              "readable 'end'") from None
        if end.tzinfo is None:
            end = end.tz_localize("UTC")
        return end.to_pydatetime().astimezone(UTC)

    def _source(self, instrument: Instrument) -> tuple[str, str]:
        src = instrument.source
        if src.adapter != "vendor":
            raise ValueError(f"{instrument.symbol}: source adapter is {src.adapter!r}, "
                             "not 'vendor'")
        return src.get("dataset"), src.get("symbol")

    def _bars(self, instrument: Instrument, dataset: str, symbol: str, stype: str,
              start: datetime, end: datetime, ids: bool) -> pd.DataFrame:
        limit = instrument.source.get("max_cost_usd", DEFAULT_MAX_COST_USD)
        estimate = self.cost(instrument, symbol, stype, start, end)
        if estimate > limit:
            raise SourceError(
                f"{instrument.symbol}: the vendor's cost estimate {estimate:.2f} USD for "
                f"{_iso(start)} to {_iso(end)} is above max_cost_usd {limit:g}; nothing "
                "was fetched")
        client = self.client()

        def get() -> Any:
            store = client.timeseries.get_range(
                dataset=dataset, symbols=[symbol], schema=self.schema, stype_in=stype,
                start=_iso(start), end=_iso(end))
            return store.to_df(price_type="float", pretty_ts=True, map_symbols=False)

        frame = self._guard("bars", get)
        return self._checked(instrument, frame, start, end, ids)

    def _checked(self, instrument: Instrument, frame: Any, start: datetime, end: datetime,
                 ids: bool) -> pd.DataFrame:
        where = f"{instrument.symbol}: the vendor's bars"
        if not isinstance(frame, pd.DataFrame):
            raise SourceError(f"{where} are not a table")
        if frame.index.name == "ts_event":
            frame = frame.reset_index()
        need = ["ts_event", *BAR_VALUES, *([INSTRUMENT_ID] if ids else [])]
        missing = [c for c in need if c not in frame.columns]
        if missing:
            raise SourceError(f"{where} lack the columns {missing}")
        try:
            ts = pd.DatetimeIndex(frame["ts_event"])
            values = frame[list(BAR_VALUES)].astype("float64")
        except (TypeError, ValueError) as exc:
            raise SourceError(f"{where} are malformed: {exc}") from None
        if ts.tz is None:
            if len(ts):
                raise SourceError(f"{where} have times without a time zone")
            ts = ts.tz_localize("UTC")
        ts = ts.tz_convert("UTC").astype("datetime64[ns, UTC]")
        out = values.reset_index(drop=True)
        out.insert(0, "ts", pd.Series(ts))
        if ids:
            out[INSTRUMENT_ID] = frame[INSTRUMENT_ID].to_numpy()
        nanos = ts.asi8 % (self.bar_seconds * 1_000_000_000)
        off_grid = pd.Series(nanos != 0)
        if off_grid.any():
            raise SourceError(f"{where} include a bar time off the {self.bar_seconds}-second "
                              f"grid: {out['ts'][off_grid].iloc[0].isoformat()}")
        out = out.sort_values("ts", kind="mergesort").reset_index(drop=True)
        if out["ts"].duplicated().any():
            raise SourceError(f"{where} repeat a bar time")
        keep = (out["ts"] >= pd.Timestamp(start)) & (out["ts"] < pd.Timestamp(end))
        return out[keep].reset_index(drop=True)

    def _contracts(self, dataset: str, raw: pd.DataFrame) -> list[str]:
        """Each bar's contract: its instrument id's raw symbol on the bar's UTC date."""
        ids = sorted({str(i) for i in raw[INSTRUMENT_ID]})
        days = raw["ts"].dt.date
        first, last = days.min(), days.max() + timedelta(days=1)
        client = self.client()
        reply = self._guard("symbology", lambda: client.symbology.resolve(
            dataset=dataset, symbols=ids, stype_in=INSTRUMENT_ID, stype_out=RAW_SYMBOL,
            start_date=first.isoformat(), end_date=last.isoformat()))
        try:
            result = reply["result"]
            spans = {i: [(date.fromisoformat(str(m["d0"])), date.fromisoformat(str(m["d1"])),
                          str(m["s"])) for m in result.get(i, [])] for i in ids}
        except (KeyError, TypeError, ValueError, AttributeError):
            raise SourceError("the vendor's symbology reply is malformed") from None
        contracts = []
        for i, day in zip(raw[INSTRUMENT_ID], days, strict=True):
            name = next((s for d0, d1, s in spans[str(i)] if d0 <= day < d1 and s.strip()),
                        None)
            if name is None:
                raise SourceError(f"the vendor's symbology gives no contract for instrument "
                                  f"id {i} on {day.isoformat()}")
            contracts.append(name)
        return contracts


def _empty() -> pd.DataFrame:
    return bars_frame([], {name: [] for name in BAR_VALUES}, [])
