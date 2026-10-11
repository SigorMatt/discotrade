"""The bar source interface (DESIGN 5.5).

``fetch`` returns bars in the schema of DESIGN 5.1 for an instrument's
continuous series, with ``ts`` in [start, end); ``fetch_contract`` returns the
bars of one named underlying contract and is used only to measure roll gaps.
``available_until(now)`` is the instant up to which the source's bars are
final; a bar is closed when ``ts + bar_seconds`` is not later than it. A
source reads no clock: ``now`` is the injected clock's (I-12).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from discotrade.config import Instrument

#: The columns of a bar (DESIGN 5.1), in order.
BAR_COLUMNS = ("ts", "open", "high", "low", "close", "volume", "contract")
BAR_VALUES = ("open", "high", "low", "close", "volume")


def bars_frame(ts: Any, values: Mapping[str, Any], contract: Any) -> pd.DataFrame:
    """Bars in the schema of DESIGN 5.1: ``ts`` as nanosecond UTC timestamps,
    the five values as float64, ``contract`` as strings."""
    index = pd.DatetimeIndex(ts)
    if index.tz is None:
        if len(index):
            raise ValueError("bar times must be timezone-aware")
        index = index.tz_localize("UTC")
    stamps = pd.Series(index).dt.tz_convert("UTC").astype("datetime64[ns, UTC]")
    out = pd.DataFrame({"ts": stamps.reset_index(drop=True)})
    for name in BAR_VALUES:
        out[name] = pd.Series(values[name]).astype("float64").to_numpy()
    out["contract"] = pd.Series(contract, index=out.index, dtype=object).astype(str)
    return out


class NotBuiltError(NotImplementedError):
    """A part of the design that a later roadmap step builds."""


class SourceError(ValueError):
    """A source refused a request or returned something it cannot vouch for:
    a missing key, a cost above the limit, a malformed response. Its text
    never holds a secret (I-13)."""


@runtime_checkable
class BarSource(Protocol):
    name: str

    def available_until(self, now: datetime) -> datetime: ...

    def fetch(self, instrument: Instrument, start: datetime, end: datetime) -> pd.DataFrame: ...

    def fetch_contract(
        self, instrument: Instrument, contract: str, start: datetime, end: datetime
    ) -> pd.DataFrame: ...
