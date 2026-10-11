"""Bar sources (DESIGN 5.5): the interface and the adapters.

``source_for`` gives the adapter an instrument record names in its
``[source]`` table. Only ``synth`` is built; ``vendor`` and ``crypto`` raise
``NotBuiltError``.
"""

from __future__ import annotations

from collections.abc import Mapping

from discotrade.config import Calendar
from discotrade.sources.base import BarSource, NotBuiltError

__all__ = ["BarSource", "NotBuiltError", "source_for"]


def source_for(adapter: str, calendars: Mapping[str, Calendar], bar_seconds: int) -> BarSource:
    """The bar source for ``adapter``; ``calendars`` maps a calendar name to its record."""
    if adapter == "synth":
        from discotrade.sources.synth import SynthSource

        return SynthSource(calendars, bar_seconds)
    raise NotBuiltError(f"bar source adapter {adapter!r} is not built yet")
