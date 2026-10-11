"""A fake of the vendor's client, with the method shapes the vendor adapter calls
(``src/discotrade/sources/vendor.py`` lists them). That those shapes match the real
client is NOT PROVEN until live check L1.

The fake's market is a synthetic instrument that rolls quarterly (DESIGN 17.1):
the continuous symbol serves the synthetic continuous series, each synthetic
contract name is a raw symbol with its own instrument id, and the symbology maps
each id to its name over any requested dates. ``FakeVendor.module()`` is a stand-in
for the client package, to be placed in ``sys.modules`` under the package's name.
Every call is recorded in ``FakeVendor.calls``; ``FakeVendor.keys`` records each key
a client was made with.
"""

from __future__ import annotations

import types
from datetime import UTC, datetime
from typing import Any

import pandas as pd


class FakeStore:
    def __init__(self, vendor: FakeVendor, frame: pd.DataFrame) -> None:
        self._vendor, self._frame = vendor, frame

    def to_df(self, price_type: str = "float", pretty_ts: bool = True,
              map_symbols: bool = True) -> pd.DataFrame:
        self._vendor.calls.append(("to_df", {"price_type": price_type,
                                             "pretty_ts": pretty_ts,
                                             "map_symbols": map_symbols}))
        return self._frame.copy()


class FakeVendor:
    def __init__(self, synth: Any, instrument: Any, dataset: str, continuous: str,
                 cost: float = 0.25, dataset_end: datetime | None = None) -> None:
        self.synth, self.instrument = synth, instrument
        self.dataset, self.continuous = dataset, continuous
        self.cost = cost
        self.dataset_end = dataset_end
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.keys: list[str] = []
        self.ids: dict[str, int] = {}
        #: When set, every call raises ``RuntimeError(fail_with)``.
        self.fail_with: str | None = None

    # --- the stand-in package ------------------------------------------------------

    def module(self) -> types.ModuleType:
        vendor = self
        module = types.ModuleType("fake_vendor_client")

        class Historical:
            def __init__(self, key: str | None = None) -> None:
                vendor.keys.append(key)
                vendor._record("Historical", {})
                self.metadata = types.SimpleNamespace(get_cost=vendor.get_cost,
                                                      get_dataset_range=vendor.get_dataset_range)
                self.timeseries = types.SimpleNamespace(get_range=vendor.get_range)
                self.symbology = types.SimpleNamespace(resolve=vendor.resolve)

        module.Historical = Historical
        return module

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def _record(self, name: str, kwargs: dict[str, Any]) -> None:
        self.calls.append((name, kwargs))
        if self.fail_with is not None:
            raise RuntimeError(self.fail_with)

    def _id(self, contract: str) -> int:
        return self.ids.setdefault(contract, 1000 + len(self.ids))

    # --- the client's methods --------------------------------------------------------

    def get_cost(self, *, dataset, symbols, schema, stype_in, start, end) -> float:
        self._record("get_cost", dict(dataset=dataset, symbols=symbols, schema=schema,
                                      stype_in=stype_in, start=start, end=end))
        return self.cost

    def get_dataset_range(self, *, dataset) -> dict[str, str]:
        self._record("get_dataset_range", {"dataset": dataset})
        return {"start": "2010-06-06T00:00:00.000000000Z",
                "end": self.dataset_end.astimezone(UTC).isoformat()}

    def get_range(self, *, dataset, symbols, schema, stype_in, start, end) -> FakeStore:
        self._record("get_range", dict(dataset=dataset, symbols=symbols, schema=schema,
                                       stype_in=stype_in, start=start, end=end))
        assert dataset == self.dataset and schema == "ohlcv-1h" and len(symbols) == 1
        lo, hi = datetime.fromisoformat(start), datetime.fromisoformat(end)
        if stype_in == "continuous":
            assert symbols == [self.continuous]
            bars = self.synth.fetch(self.instrument, lo, hi)
        else:
            assert stype_in == "raw_symbol"
            bars = self.synth.fetch_contract(self.instrument, symbols[0], lo, hi)
        frame = pd.DataFrame({
            "rtype": 34, "publisher_id": 1,
            "instrument_id": [self._id(c) for c in bars["contract"]],
            "open": bars["open"].to_numpy(), "high": bars["high"].to_numpy(),
            "low": bars["low"].to_numpy(), "close": bars["close"].to_numpy(),
            "volume": bars["volume"].round().astype("uint64").to_numpy(),
        }, index=pd.DatetimeIndex(bars["ts"], name="ts_event"))
        return FakeStore(self, frame)

    def resolve(self, *, dataset, symbols, stype_in, stype_out, start_date, end_date):
        self._record("resolve", dict(dataset=dataset, symbols=symbols, stype_in=stype_in,
                                     stype_out=stype_out, start_date=start_date,
                                     end_date=end_date))
        assert stype_in == "instrument_id" and stype_out == "raw_symbol"
        names = {str(i): c for c, i in self.ids.items()}
        result = {s: [{"d0": start_date, "d1": end_date, "s": names[s]}]
                  for s in symbols if s in names}
        return {"result": result, "symbols": symbols, "stype_in": stype_in,
                "stype_out": stype_out, "start_date": start_date, "end_date": end_date,
                "partial": [], "not_found": [s for s in symbols if s not in names],
                "message": "OK", "status": 0}
