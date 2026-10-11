"""The injected clock (I-12).

The harness reads time only through a ``Clock``. ``SystemClock`` is the one
place that reads the wall clock; ``FixedClock`` returns one instant, which is
what ``--as-of`` and every test use. Instants are timezone-aware UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime:
        """The current instant, timezone-aware, in UTC."""
        ...


class SystemClock:
    """The real clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock stopped at one instant."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError(f"instant has no timezone: {instant.isoformat()}")
        self._instant = instant.astimezone(UTC)

    def now(self) -> datetime:
        return self._instant

    def __repr__(self) -> str:
        return f"FixedClock({self._instant.isoformat()})"
