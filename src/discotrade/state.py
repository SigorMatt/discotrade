"""The state directory (DESIGN 9.1, 9.2, 15.2). For now: the content hash and
the health event value of DESIGN 15.2 (the health log that stores it is a
later step's).

The content hash of a table (DESIGN 9.2) is the sha256 of its rows, sorted
by the key columns, written as text with every float in ``%.17g``. The text
is fixed here, where the design is silent: a header line of the column
names in the frame's order, then one line per row; fields separated by a
tab, every line ended by a newline, UTF-8. A float is ``%.17g`` (a NaN is
``nan``); a timestamp is its integer nanoseconds since the epoch in UTC; an
integer is decimal; a boolean is ``true`` or ``false``; None, NaT and NA are
empty; any other value is its ``str``. A tab or a newline inside a field is refused,
so that the text has one reading.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd


def _field(value: Any) -> str:
    if value is None or value is pd.NaT:
        return ""
    if isinstance(value, bool | np.bool_):
        return "true" if value else "false"
    if isinstance(value, float | np.floating):
        return f"{float(value):.17g}"  # identical to "%.17g" % value
    if isinstance(value, int | np.integer):
        return str(int(value))
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert("UTC").tz_localize(None)
        return str(value.value)
    if isinstance(value, np.datetime64):
        return _field(pd.Timestamp(value))
    if value is pd.NA:
        return ""
    text = str(value)
    if "\t" in text or "\n" in text or "\r" in text:
        raise ValueError(f"field {text!r} holds a tab or a newline")
    return text


def content_text(frame: pd.DataFrame, key: Sequence[str]) -> str:
    """The text whose sha256 is the content hash of ``frame``."""
    columns = [str(c) for c in frame.columns]
    missing = [k for k in key if k not in columns]
    if missing:
        raise ValueError(f"key columns {missing} are not in the table")
    for name in columns:
        if "\t" in name or "\n" in name:
            raise ValueError(f"column name {name!r} holds a tab or a newline")
    rows = frame.sort_values(list(key), kind="mergesort") if len(key) else frame
    lines = ["\t".join(columns)]
    for row in rows.itertuples(index=False, name=None):
        lines.append("\t".join(_field(v) for v in row))
    return "\n".join(lines) + "\n"


def content_hash(frame: pd.DataFrame, key: Sequence[str]) -> str:
    """The sha256 hex digest of ``content_text(frame, key)`` (DESIGN 9.2)."""
    return hashlib.sha256(content_text(frame, key).encode("utf-8")).hexdigest()


HEALTH_LEVELS = ("alert", "notice")


@dataclass(frozen=True)
class HealthEvent:
    """One health event (DESIGN 15.2): date, level, kind, subject and a detail
    object. The code that detects a condition returns it; the daily run
    appends it to the health log."""

    date: date
    level: str
    kind: str
    subject: str
    detail: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.level not in HEALTH_LEVELS:
            raise ValueError(f"health level must be one of {HEALTH_LEVELS}, not {self.level!r}")

    def to_json(self) -> str:
        """The event as one JSON line (no newline), keys sorted."""
        return json.dumps(
            {"date": self.date.isoformat(), "level": self.level, "kind": self.kind,
             "subject": self.subject, "detail": dict(self.detail)},
            sort_keys=True,
        )
