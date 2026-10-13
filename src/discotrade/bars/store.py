"""The Parquet bar store (DESIGN 5.1, 5.2; I-5).

Layout: ``<state>/bars/<track>/<symbol>/<YYYY-MM>.parquet``, one file per
instrument per calendar month of ``ts`` in UTC, rows sorted by ``ts`` with no
duplicate, and ``<state>/bars/<track>/index.json``.

The writer only appends. A batch is refused whole when any bar in it has not
closed (``ts + bar_seconds`` later than ``available_until``), has an
``open``, ``high``, ``low``, ``close`` or ``volume`` that is NaN or infinite
(decision 2026-10-12 6), is not later than the last stored bar of its
instrument, or repeats or reorders a ``ts``. An append rewrites each touched
month file atomically (write beside, flush and ``fsync``, rename, then
``fsync`` the directory) with the old rows first and unchanged, then rewrites
the index the same way. ``available_until`` is the caller's: the source's
``available_until`` of the injected clock's ``now`` (DESIGN 5.5, I-12); the
store reads no clock.

The index holds, per instrument, ``first_ts``, ``last_ts`` and ``rows``,
and per month file ``first_ts``, ``last_ts``, ``rows`` and ``hash``, the
content hash of DESIGN 9.2 keyed on ``ts``. Timestamps in the index are ISO
8601 in UTC. Every month file is checked against its hash when read, by the
reader and by the writer before it appends.

A month file that does not match the index, or that the index does not list,
is an interrupted append (decision 2026-10-12 5) when its first ``r`` rows,
``r`` being the row count the index records for it (0 when unlisted), have
exactly the indexed content hash, and every further row is later than the
instrument's indexed last ``ts``; those further rows must also be strictly
increasing with finite values, as the writer writes them (the decision is
silent on this; the simplest reading of "written by the harness"). Any other
mismatch is a revised data point. ``recover`` completes an interrupted
append: it records the file in the index (rows, last ``ts``, content hash),
changes no row, and returns one ``store_recovered`` health notice (DESIGN
15.2, decision 16) per completed file, naming the instrument and the file.
It reads and hashes only the files an interrupted append can leave: the
instrument's month files the index does not list and the file holding its
indexed last bar (mission 9 U3); a listed earlier file that no longer
matches is a revised data point the reader refuses. The writer runs it
before every append, unless it has just run on the same store for that
instrument with nothing written since (``bars fetch`` and step 1 run it
before they fetch, so it runs once per instrument per fetch), and keeps the
notices in ``notices`` for its caller. The reader does not repair: it refuses both
cases, with an error that says which. Every read of an instrument
(``read_range``, ``last_n``, ``last_ts``, decision 2026-10-12 31, and
``index_entry``, decision 2026-10-12 35) first refuses when the
instrument's directory holds a month file the index does not list,
whatever range it asks for (decision 2026-10-12 18): an unlisted file may be
an interrupted append into a new month, which a read would otherwise
silently leave out. The writer and ``bars fetch`` read the indexed
last ``ts`` through ``_indexed_last_ts``, which does not refuse. The date of a
notice is the caller's ``day``; inside ``append`` it is the UTC date of
``available_until``.

Within one day run (``day_run()``, which ``daily.run_day`` holds around a
day; decision 2026-10-14 80 (b), O-3) a listed month file is read and hashed
at most once per index entry: the frame of the first read that matched the
index is kept, keyed by the file's path and the entry's row count and hash,
and every later read of that run with the same entry is served from it, on
every ``BarStore`` of the process. An append changes the entry, so the
appended file is read and checked again. The kept frames are dropped when the
day run ends, so a file changed after it was verified is refused by the next
day run's first read of it. Nothing is written for this; outside a day run
every read checks its file as before.
"""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Callable, Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade.state import HealthEvent, content_hash

COLUMNS = ("ts", "open", "high", "low", "close", "volume", "contract")
FLOATS = ("open", "high", "low", "close", "volume")
KEY = ("ts",)
STORE_RECOVERED = "store_recovered"


class BarStoreError(ValueError):
    """A refused write or read."""


#: The month frames verified in the current day run, keyed by the file's path
#: and the index entry's row count and hash; None outside a day run.
_RUN: dict[tuple[str, int, str], pd.DataFrame] | None = None


@contextlib.contextmanager
def day_run() -> Iterator[None]:
    """The scope of one day run (decision 2026-10-14 80 (b)): inside it, each
    listed month file is hashed once per index entry and the verified frame
    serves every later read; on exit, success or failure, everything kept is
    dropped. One process, no threads (80 (c))."""
    global _RUN
    outer = _RUN
    _RUN = {}
    try:
        yield
    finally:
        _RUN = outer


def _run_key(path: Path, entry: dict[str, Any]) -> tuple[str, int, str]:
    return (os.path.abspath(path), int(entry["rows"]), str(entry["hash"]))


def _iso(ts: pd.Timestamp) -> str:
    return ts.tz_convert("UTC").isoformat()


def _utc(instant: datetime | pd.Timestamp, what: str) -> pd.Timestamp:
    stamp = pd.Timestamp(instant)
    if stamp.tzinfo is None:
        raise BarStoreError(f"{what} {stamp} has no time zone; expected UTC")
    return stamp.tz_convert("UTC")


def _fsync_path(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_atomic(path: Path, write: Callable[[Path], Any]) -> None:
    """Write ``path`` beside itself, ``fsync`` it, rename it into place and
    ``fsync`` its directory. A crash before the rename leaves the old file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    _fsync_path(tmp)
    os.replace(tmp, path)
    _fsync_path(path.parent)


def finite_rows(bars: pd.DataFrame) -> np.ndarray:
    """A mask of the bars whose five values are all finite."""
    values = bars[list(FLOATS)].astype("float64").to_numpy()
    return np.isfinite(values).all(axis=1)


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
        #: Health notices of the interrupted appends the writer completed.
        self.notices: list[HealthEvent] = []
        # Symbols ``recover`` has checked with nothing written since, and the
        # month frames it verified against the index, for the append that
        # follows it on this store (mission 9 U3: recovery once per fetch).
        self._checked: set[str] = set()
        self._verified: dict[tuple[str, str], tuple[str, pd.DataFrame]] = {}

    # --- paths and the index ---------------------------------------------------

    def month_path(self, symbol: str, month: str) -> Path:
        if not symbol or "/" in symbol or "\\" in symbol or symbol.startswith("."):
            raise BarStoreError(f"bad symbol {symbol!r}")
        return self.root / symbol / f"{month}.parquet"

    def index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def index_entry(self, symbol: str) -> dict[str, Any] | None:
        """The index entry of ``symbol``, or None when nothing is stored.

        A reader entry point for code that consults the index before it reads
        (decision 2026-10-12 35): it refuses, as ``read_range`` does and with
        the same errors, when the instrument's directory holds a month file the
        index does not list, so None means the directory holds no month file
        and the index has no entry. A listed file is checked against its hash
        by the read that follows."""
        self._months(symbol)
        return self.index().get(symbol)

    def last_ts(self, symbol: str) -> pd.Timestamp | None:
        """The last stored ``ts`` of ``symbol``, or None when none is stored.

        A reader entry point (decision 2026-10-12 31): it refuses, as
        ``read_range`` and ``last_n`` do and with the same errors, when the
        instrument's directory holds a month file the index does not list or a
        listed file that does not match the index."""
        for month, entry in sorted(self._months(symbol).items()):
            self._read_month(symbol, month, entry)
        return self._indexed_last_ts(symbol)

    def _indexed_last_ts(self, symbol: str) -> pd.Timestamp | None:
        """The last ``ts`` the index records for ``symbol``, checking no file.
        For the writer's and ``bars fetch``'s own use (decision 2026-10-12 31)."""
        entry = self.index().get(symbol)
        return None if entry is None else pd.Timestamp(entry["last_ts"]).tz_convert("UTC")

    def _write_index(self, index: dict[str, Any]) -> None:
        text = json.dumps(index, indent=2, sort_keys=True) + "\n"
        write_atomic(self.index_path, lambda p: p.write_text(text, encoding="utf-8"))

    # --- matching a month file against the index ---------------------------------

    @staticmethod
    def _interrupted(frame: pd.DataFrame, month_entry: dict[str, Any] | None,
                     last: pd.Timestamp | None) -> bool:
        """Whether a file that does not match the index is an interrupted append."""
        r = 0 if month_entry is None else month_entry["rows"]
        if len(frame) <= r:
            return False
        if r and content_hash(frame.iloc[:r], KEY) != month_entry["hash"]:  # type: ignore[index]
            return False
        try:
            extra = _normalize(frame.iloc[r:])
        except BarStoreError:
            return False
        ts = extra["ts"]
        if last is not None and not (ts > last).all():
            return False
        if r and not ts.iloc[0] > frame["ts"].iloc[r - 1]:
            return False
        return bool(ts.is_monotonic_increasing and not ts.duplicated().any()
                    and finite_rows(extra).all())

    @staticmethod
    def _matches(frame: pd.DataFrame, month_entry: dict[str, Any]) -> bool:
        return len(frame) == month_entry["rows"] and content_hash(frame, KEY) == month_entry["hash"]

    def recover(self, symbol: str, day: date) -> tuple[HealthEvent, ...]:
        """Complete an interrupted append of ``symbol`` (decision 2026-10-12 5).

        Reads and hashes only the files an interrupted append can leave: the
        month file holding the indexed last bar and the month files the index
        does not list (an append adds only rows later than the indexed last
        bar and writes the index after every month file). Returns one
        ``store_recovered`` notice dated ``day`` per completed file; refuses a
        revised data point among those files; writes nothing when nothing is
        to complete. A listed earlier file that no longer matches the index is
        left to the reader, which refuses it (decisions 18, 31).
        """
        folder = self.month_path(symbol, "x").parent
        index = self.index()
        entry = index.get(symbol)
        months: dict[str, Any] = {} if entry is None else entry["months"]
        last = None if entry is None else pd.Timestamp(entry["last_ts"]).tz_convert("UTC")
        on_disk = sorted(p.stem for p in folder.glob("*.parquet")) if folder.is_dir() else []
        candidates = {m for m in on_disk if m not in months}
        if months:
            candidates.add(max(months))          # the file holding the indexed last bar
        self._checked.discard(symbol)
        completed: dict[str, dict[str, Any]] = {}
        verified: dict[str, tuple[str, pd.DataFrame]] = {}
        for month in sorted(candidates):
            listed = months.get(month)
            path = self.month_path(symbol, month)
            if not path.exists():
                raise BarStoreError(f"{symbol} {month}: month file missing, listed in the "
                                    f"index (a revised data point); refused")
            run = _RUN
            key = None if listed is None or run is None else _run_key(path, listed)
            if run is not None and key in run:
                verified[month] = (listed["hash"], run[key])  # verified in this day run
                continue
            frame = pd.read_parquet(path)
            if listed is not None and self._matches(frame, listed):
                verified[month] = (listed["hash"], frame)
                if run is not None and key is not None:
                    run[key] = frame
                continue
            if not self._interrupted(frame, listed, last):
                raise BarStoreError(self._revised(symbol, month))
            completed[month] = {
                "first_ts": _iso(frame["ts"].iloc[0]),
                "last_ts": _iso(frame["ts"].iloc[-1]),
                "rows": len(frame),
                "hash": content_hash(frame, KEY),
                "before": 0 if listed is None else listed["rows"],
            }
            verified[month] = (completed[month]["hash"], frame)
        events = []
        if completed:
            entry = entry if entry is not None else {"months": {}}
            for month, done in completed.items():
                before = done.pop("before")
                entry["months"][month] = done
                events.append(HealthEvent(
                    date=day, level="notice", kind=STORE_RECOVERED, subject=symbol,
                    detail={"file": f"{symbol}/{month}.parquet", "rows_before": before,
                            "rows": done["rows"], "last_ts": done["last_ts"]},
                ))
            self._summarize(entry)
            index[symbol] = entry
            self._write_index(index)
        self._checked.add(symbol)
        for month, done_frame in verified.items():
            self._verified[(symbol, month)] = done_frame
        return tuple(events)

    def _verify_stored(self, symbol: str) -> None:
        """Check every stored month file of ``symbol`` against the index, as a
        reader does and with its errors, reading again no file ``recover`` has
        just verified on this store. ``bars fetch`` and step 1 call it after
        ``recover`` and before they write, so that a revised data point in any
        file stops them with nothing written (recover reads only the files an
        interrupted append can leave)."""
        for month, listed in sorted(self._months(symbol).items()):
            seen = self._verified.get((symbol, month))
            if seen is None or seen[0] != listed["hash"]:
                self._read_month(symbol, month, listed)

    @staticmethod
    def _revised(symbol: str, month: str) -> str:
        return (f"{symbol} {month}: content no longer matches the index "
                f"(a revised data point); refused")

    @staticmethod
    def _summarize(entry: dict[str, Any]) -> None:
        listed = sorted(entry["months"].items())
        entry["first_ts"] = listed[0][1]["first_ts"]
        entry["last_ts"] = listed[-1][1]["last_ts"]
        entry["rows"] = sum(m["rows"] for _, m in listed)

    # --- reading -----------------------------------------------------------------

    def _read_month(self, symbol: str, month: str, entry: dict[str, Any]) -> pd.DataFrame:
        path = self.month_path(symbol, month)
        run = _RUN
        key = _run_key(path, entry)
        if run is not None and key in run:
            return run[key]                   # verified in this day run
        if not path.exists():
            raise BarStoreError(f"{symbol} {month}: month file missing, listed in the index")
        frame = pd.read_parquet(path)
        if not self._matches(frame, entry):
            last = self._indexed_last_ts(symbol)
            if self._interrupted(frame, entry, last):
                raise BarStoreError(
                    f"{symbol} {month}: file holds an interrupted append not yet in the "
                    f"index; refused until the next append or bars fetch completes it"
                )
            raise BarStoreError(self._revised(symbol, month))
        if run is not None:
            run[key] = frame
        return frame

    def _months(self, symbol: str) -> dict[str, Any]:
        """The indexed months of ``symbol``, after refusing an unlisted month file
        (decision 2026-10-12 18). Every reader entry point goes through here."""
        entry = self.index().get(symbol)
        months: dict[str, Any] = {} if entry is None else entry["months"]
        folder = self.month_path(symbol, "x").parent
        unlisted = (sorted(p.stem for p in folder.glob("*.parquet") if p.stem not in months)
                    if folder.is_dir() else [])
        if unlisted:
            last = None if entry is None else pd.Timestamp(entry["last_ts"]).tz_convert("UTC")
            for month in unlisted:
                frame = pd.read_parquet(self.month_path(symbol, month))
                if not self._interrupted(frame, None, last):
                    raise BarStoreError(
                        f"{symbol} {month}: month file not listed in the index "
                        f"(a revised data point); refused")
            raise BarStoreError(
                f"{symbol} {', '.join(unlisted)}: month file not listed in the index holds "
                f"an interrupted append; refused until the next append or bars fetch "
                f"completes it")
        return months

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
        finite = finite_rows(new)
        if not finite.all():
            raise BarStoreError(f"{symbol}: bar {_iso(ts[~finite].iloc[0])} has a value that "
                                f"is not finite (NaN or infinite); nothing written")
        # Decision 5's check before the append, unless ``recover`` has just run
        # on this store for ``symbol`` with nothing written since (``bars fetch``
        # and step 1 run it before they fetch), so that it runs once per fetch.
        if symbol not in self._checked:
            self.notices.extend(self.recover(symbol, until.date()))
        try:
            return self._append_checked(symbol, new, ts)
        finally:
            self._checked.discard(symbol)
            self._verified = {k: v for k, v in self._verified.items() if k[0] != symbol}

    def _append_checked(self, symbol: str, new: pd.DataFrame, ts: pd.Series) -> int:
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
                listed = entry["months"][month]
                seen = self._verified.get((symbol, month))
                old[month] = (seen[1] if seen is not None and seen[0] == listed["hash"]
                              else self._read_month(symbol, month, listed))
            elif path.exists():   # recover() has just listed every completable file
                raise BarStoreError(f"{symbol} {month}: month file exists but is not in the "
                                    f"index; refused")

        for month, rows in groups:
            frame = rows if month not in old else pd.concat([old[month], rows])
            frame = frame.reset_index(drop=True)
            write_atomic(
                self.month_path(symbol, month),
                lambda p, f=frame: f.to_parquet(p, index=False, engine="pyarrow"),
            )
            entry["months"][month] = {
                "first_ts": _iso(frame["ts"].iloc[0]),
                "last_ts": _iso(frame["ts"].iloc[-1]),
                "rows": len(frame),
                "hash": content_hash(frame, KEY),
            }
        self._summarize(entry)
        index[symbol] = entry
        self._write_index(index)
        return len(new)
