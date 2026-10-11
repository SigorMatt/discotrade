"""The bar source interface (DESIGN 5.5).

``fetch`` returns bars in the schema of DESIGN 5.1 for an instrument's
continuous series, with ``ts`` in [start, end); ``fetch_contract`` returns the
bars of one named underlying contract and is used only to measure roll gaps.
``available_until(now)`` is the instant up to which the source's bars are
final; a bar is closed when ``ts + bar_seconds`` is not later than it. A
source reads no clock: ``now`` is the injected clock's (I-12).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

import pandas as pd

from discotrade.config import Instrument


class NotBuiltError(NotImplementedError):
    """A part of the design that a later roadmap step builds."""


@runtime_checkable
class BarSource(Protocol):
    name: str

    def available_until(self, now: datetime) -> datetime: ...

    def fetch(self, instrument: Instrument, start: datetime, end: datetime) -> pd.DataFrame: ...

    def fetch_contract(
        self, instrument: Instrument, contract: str, start: datetime, end: datetime
    ) -> pd.DataFrame: ...
