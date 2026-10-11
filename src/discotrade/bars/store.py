"""The Parquet bar store (DESIGN 5.1, 5.2; I-5).

Layout: ``<state>/bars/<track>/<symbol>/<YYYY-MM>.parquet``, one file per
instrument per calendar month of ``ts`` in UTC, rows sorted by ``ts`` with no
duplicate, and ``<state>/bars/<track>/index.json``.

The writer only appends. A batch is refused whole when any bar in it has not
closed (``ts + bar_seconds`` later than ``available_until``), is not later
than the last stored bar of its instrument, or repeats or reorders a ``ts``.
An append rewrites each touched month file atomically (write beside, then
rename) with the old rows first and unchanged, then rewrites the index the
same way. ``available_until`` is the caller's: the source's
``available_until`` of the injected clock's ``now`` (DESIGN 5.5, I-12); the
store reads no clock.

The index holds, per instrument, ``first_ts``, ``last_ts`` and ``rows``,
and per month file ``first_ts``, ``last_ts``, ``rows`` and ``hash``, the
content hash of DESIGN 9.2 keyed on ``ts``. Timestamps in the index are ISO
8601 in UTC. Every month file is checked against its hash when read, by the
reader and by the writer before it appends; a file that no longer matches is
a revised data point and is refused.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from discotrade.state import content_hash

COLUMNS = ("ts", "open", "high", "low", "close", "volume", "contract")
FLOATS = ("open", "high", "low", "close", "volume")
KEY = ("ts",)


class BarStoreError(ValueError):
    """A refused write or read."""


def _iso(ts: pd.Timestamp) -> str:
    return ts.tz_convert("UTC").isoformat()


def _utc(instant: datetime | pd.Timestamp, what: str) -> pd.Timestamp:
    stamp = pd.Timestamp(instant)
    if stamp.tzinfo is None:
        raise BarStoreError(f"{what} {stamp} has no time zone; expected UTC")
    return stamp.tz_convert("UTC")


def _normalize(bars: pd.DataFrame) -> pd.DataFrame:
    """The bars in the schema of DESIGN 5.1, in column order, or a refusal."""
    if set(bars.columns) != set(COLUMNS) or len(bars.columns) != len(COLUMNS):
        raise BarStoreError(f"bars must have exactly the columns {list(COLUMNS)}, "
                            f"got {list(bars.columns)}")
    ts = bars["ts"]
    if not isinstance(ts.dtype, pd.DatetimeTZDtype):
        raise BarStoreError(f"ts must be timezone-aware UTC, got dtype {ts.dtype}")
    out = pd.DataFrame(
        {"ts": ts.dt.tz_convert("UTC").astype("datetime64[ns, UTC]").reset_index(drop=True)}
    )
    for name in FLOATS:
        out[name] = bars[name].astype("float64").to_numpy()
    if bars["contract"].isna().any():
        raise BarStoreError("contract must be filled on every bar")
    out["contract"] = bars["contract"].astype(str).to_numpy()
    return out


class BarStore:
    """The bar store of one track in one state directory."""

    def __init__(self, state_dir: Path, track: str, bar_seconds: int) -> None:
        if bar_seconds < 1:
            raise BarStoreError(f"bar_seconds must be positive, got {bar_seconds}")
        self.root = Path(state_dir) / "bars" / track
        self.bar_seconds = bar_seconds
        self.index_path = self.root / "index.json"

    # --- paths and the index ---------------------------------------------------

    def month_path(self, symbol: str, month: str) -> Path:
        if not symbol or "/" in symbol or "\\" in symbol or symbol.startswith("."):
            raise BarStoreError(f"bad symbol {symbol!r}")
        return self.root / symbol / f"{month}.parquet"

    def index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def last_ts(self, symbol: str) -> pd.Timestamp | None:
        entry = self.index().get(symbol)
        return None if entry is None else pd.Timestamp(entry["last_ts"]).tz_convert("UTC")

    @staticmethod
    def _write_atomic(path: Path, write: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        write(tmp)
        os.replace(tmp, path)

    def _write_index(self, index: dict[str, Any]) -> None:
        text = json.dumps(index, indent=2, sort_keys=True) + "\n"
        self._write_atomic(self.index_path, lambda p: p.write_text(text, encoding="utf-8"))

    # --- reading -----------------------------------------------------------------

    def _read_month(self, symbol: str, month: str, entry: dict[str, Any]) -> pd.DataFrame:
        path = self.month_path(symbol, month)
        if not path.exists():
            raise BarStoreError(f"{symbol} {month}: month file missing, listed in the index")
        frame = pd.read_parquet(path)
        if content_hash(frame, KEY) != entry["hash"] or len(frame) != entry["rows"]:
            raise BarStoreError(
                f"{symbol} {month}: content no longer matches the index "
                f"(a revised data point); refused"
            )
        return frame

    def _months(self, symbol: str) -> dict[str, Any]:
        entry = self.index().get(symbol)
        return {} if entry is None else entry["months"]

    def read_range(
        self, symbol: str, start: datetime | pd.Timestamp, end: datetime | pd.Timestamp
    ) -> pd.DataFrame:
        """The stored bars of ``symbol`` with ``start <= ts < end``."""
        lo, hi = _utc(start, "start"), _utc(end, "end")
        frames = []
        for month, entry in sorted(self._months(symbol).items()):
            first = pd.Timestamp(entry["first_ts"])
            last = pd.Timestamp(entry["last_ts"])
            if last < lo or first >= hi:
                continue
            frame = self._read_month(symbol, month, entry)
            frames.append(frame[(frame["ts"] >= lo) & (frame["ts"] < hi)])
        return self._concat(frames)

    def last_n(self, symbol: str, at: datetime | pd.Timestamp, n: int) -> pd.DataFrame:
        """The last ``n`` stored bars of ``symbol`` ending at the stored bar ``at``,
        inclusive; fewer when fewer are stored."""
        if n < 1:
            raise BarStoreError(f"n must be at least 1, got {n}")
        end = _utc(at, "bar")
        frames: list[pd.DataFrame] = []
        count = 0
        found = False
        for month, entry in sorted(self._months(symbol).items(), reverse=True):
            if pd.Timestamp(entry["first_ts"]) > end:
                continue
            frame = self._read_month(symbol, month, entry)
            if not found:
                if not (frame["ts"] == end).any():
                    break
                found = True
            frame = frame[frame["ts"] <= end]
            frames.insert(0, frame.iloc[max(0, len(frame) - (n - count)):])
            count += len(frames[0])
            if count >= n:
                break
        if not found:
            raise BarStoreError(f"{symbol}: no stored bar at {end.isoformat()}")
        return self._concat(frames)

    @staticmethod
    def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return _normalize(pd.DataFrame({
                "ts": pd.Series([], dtype="datetime64[ns, UTC]"),
                **{name: pd.Series([], dtype="float64") for name in FLOATS},
                "contract": pd.Series([], dtype=str),
            }))
        return pd.concat(frames, ignore_index=True)

    # --- writing -----------------------------------------------------------------

    def append(
        self, symbol: str, bars: pd.DataFrame, available_until: datetime | pd.Timestamp
    ) -> int:
        """Append closed bars of ``symbol``; return how many were written."""
        new = _normalize(bars)
        if new.empty:
            return 0
        until = _utc(available_until, "available_until")
        ts = new["ts"]
        if ts.duplicated().any():
            raise BarStoreError(f"{symbol}: duplicate ts in the batch: "
                                f"{_iso(ts[ts.duplicated()].iloc[0])}")
        if not ts.is_monotonic_increasing:
            raise BarStoreError(f"{symbol}: batch is not sorted by ts")
        closes = ts + pd.Timedelta(seconds=self.bar_seconds)
        if (closes > until).any():
            bad = ts[closes > until].iloc[0]
            raise BarStoreError(f"{symbol}: bar {_iso(bad)} has not closed by "
                                f"{_iso(until)}")
        index = self.index()
        entry = index.get(symbol)
        if entry is not None:
            last = pd.Timestamp(entry["last_ts"])
            if ts.iloc[0] <= last:
                raise BarStoreError(f"{symbol}: bar {_iso(ts.iloc[0])} is not later than "
                                    f"the last stored bar {_iso(last)}")
        else:
            entry = {"months": {}}

        months = ts.dt.tz_convert("UTC").dt.strftime("%Y-%m")
        groups = [(m, new[months == m]) for m in sorted(months.unique())]
        # Check every existing month file before anything is written.
        old: dict[str, pd.DataFrame] = {}
        for month, _ in groups:
            path = self.month_path(symbol, month)
            if month in entry["months"]:
                old[month] = self._read_month(symbol, month, entry["months"][month])
            elif path.exists():
                raise BarStoreError(f"{symbol} {month}: month file exists but is not in the "
                                    f"index; refused")

        for month, rows in groups:
            frame = rows if month not in old else pd.concat([old[month], rows])
            frame = frame.reset_index(drop=True)
            self._write_atomic(
                self.month_path(symbol, month),
                lambda p, f=frame: f.to_parquet(p, index=False, engine="pyarrow"),
            )
            entry["months"][month] = {
                "first_ts": _iso(frame["ts"].iloc[0]),
                "last_ts": _iso(frame["ts"].iloc[-1]),
                "rows": len(frame),
                "hash": content_hash(frame, KEY),
            }
        listed = sorted(entry["months"].items())
        entry["first_ts"] = listed[0][1]["first_ts"]
        entry["last_ts"] = listed[-1][1]["last_ts"]
        entry["rows"] = sum(m["rows"] for _, m in listed)
        index[symbol] = entry
        self._write_index(index)
        return len(new)
