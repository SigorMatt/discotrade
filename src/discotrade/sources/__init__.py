"""Bar sources (DESIGN 5.5): the interface and the adapters.

``source_for`` gives the adapter an instrument record names in its
``[source]`` table: ``synth``, ``vendor`` or ``crypto``. Each adapter module
is imported only when it is asked for, and the vendor adapter imports the
vendor's client only when it first talks to the vendor. ``sources_for`` gives
each instrument of a run its source, building one source per adapter, so that
``bars fetch`` and the daily run build each instrument's source once per run
and the synthetic source generates each series once per run (mission 9 U3).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from discotrade.config import Calendar, Instrument
from discotrade.sources.base import BarSource, NotBuiltError, SourceError

__all__ = ["BarSource", "NotBuiltError", "SourceError", "source_for", "sources_for"]


def source_for(adapter: str, calendars: Mapping[str, Calendar], bar_seconds: int) -> BarSource:
    """The bar source for ``adapter``; ``calendars`` maps a calendar name to its record."""
    if adapter == "synth":
        from discotrade.sources.synth import SynthSource

        return SynthSource(calendars, bar_seconds)
    if adapter == "vendor":
        from discotrade.sources.vendor import VendorSource

        return VendorSource(bar_seconds)
    if adapter == "crypto":
        from discotrade.sources.crypto import CryptoSource

        return CryptoSource(bar_seconds)
    raise NotBuiltError(f"bar source adapter {adapter!r} is not built")


def sources_for(instruments: Iterable[Instrument], calendars: Mapping[str, Calendar],
                bar_seconds: int) -> dict[str, BarSource]:
    """Each instrument's source by symbol, one ``source_for`` per adapter."""
    built: dict[str, BarSource] = {}
    out = {}
    for inst in instruments:
        adapter = inst.source.adapter
        if adapter not in built:
            built[adapter] = source_for(adapter, calendars, bar_seconds)
        out[inst.symbol] = built[adapter]
    return out
