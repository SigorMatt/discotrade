"""Configuration records (DESIGN 4; I-9, I-10).

All configuration is TOML, loaded into frozen dataclasses. An unknown key is
refused, naming it (dotted: ``cost.holding``); so is a missing one. A value
that came from outside the project carries three companions in its table:
``checked`` (ISO date), ``source`` (text) and ``verified`` (boolean). They go
together: one without the others is refused.

Nothing here names a market, a contract or a venue (I-9): those are values
in the records. The threshold schema below names keys and types only; every
threshold value lives in ``config/thresholds.toml`` (I-10).
"""

from __future__ import annotations

import math
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

COMPANIONS = ("checked", "source", "verified")

#: Instrument values that come from outside the project, in the order
#: ``unverified()`` lists them. The top-level keys of the contract specification
#: take their companions from the ``[spec]`` table (the top level cannot hold a
#: ``source`` key beside the ``[source]`` table); the ``[cost]`` values take
#: theirs from ``[cost]``.
TOP_SOURCED = ("multiplier", "tick_size", "trusted_from", "main_session")
COST_SOURCED = (
    "fee_per_side", "fee_bps", "spread_ticks_main", "spread_ticks_off", "slippage_coef",
)

ADAPTERS = ("vendor", "crypto", "synth")
TEST_TRACK_PREFIX = "test_"

#: The result-moving files frozen by ``tests/fixtures/config_frozen.json``
#: (DESIGN 4.3), relative to the repository root.
FROZEN_DIRS = ("config/instruments", "config/tracks", "config/calendars", "config/spreads")
FROZEN_FILES = ("config/models.toml",)
DECISIONS_DIR = "meta/decisions/"


class ConfigError(ValueError):
    """A configuration file is missing, malformed, or holds an invalid value."""


_REQUIRED = object()
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# --- reading helpers -----------------------------------------------------------


def read_toml(path: Path) -> dict[str, Any]:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise ConfigError(f"{path}: no such file") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: not valid TOML: {exc}") from None


class _Table:
    """One TOML table with its file and dotted prefix, for error messages."""

    def __init__(self, path: Path, data: Any, prefix: str, allowed: Iterable[str]) -> None:
        self.path = path
        self.prefix = prefix
        if not isinstance(data, dict):
            raise ConfigError(f"{path}: '{prefix.rstrip('.')}' must be a table")
        allowed = set(allowed)
        unknown = [k for k in data if k not in allowed]
        if unknown:
            names = ", ".join(f"'{prefix}{k}'" for k in unknown)
            raise ConfigError(f"{path}: unknown key {names}")
        self.data: dict[str, Any] = data

    def name(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def fail(self, key: str, why: str) -> None:
        raise ConfigError(f"{self.path}: '{self.name(key)}' {why}")

    def has(self, key: str) -> bool:
        return key in self.data

    def raw(self, key: str, default: Any = _REQUIRED) -> Any:
        if key in self.data:
            return self.data[key]
        if default is _REQUIRED:
            raise ConfigError(f"{self.path}: missing key '{self.name(key)}'")
        return default

    def text(self, key: str, default: Any = _REQUIRED) -> Any:
        value = self.raw(key, default)
        if value is not default and (not isinstance(value, str) or not value):
            self.fail(key, "must be text")
        return value

    def choice(self, key: str, options: Sequence[str], default: Any = _REQUIRED) -> Any:
        value = self.text(key, default)
        if value is not default and value not in options:
            self.fail(key, f"must be one of {', '.join(options)}, not {value!r}")
        return value

    def boolean(self, key: str) -> bool:
        value = self.raw(key)
        if not isinstance(value, bool):
            self.fail(key, "must be true or false")
        return value

    def integer(self, key: str, low: int | None = None, default: Any = _REQUIRED) -> Any:
        value = self.raw(key, default)
        if value is default:
            return value
        if isinstance(value, bool) or not isinstance(value, int):
            self.fail(key, "must be an integer")
        if low is not None and value < low:
            self.fail(key, f"must be at least {low}")
        return value

    def number(
        self, key: str, low: float | None = None, high: float | None = None,
        positive: bool = False, default: Any = _REQUIRED,
    ) -> Any:
        value = self.raw(key, default)
        if value is default:
            return value
        if isinstance(value, bool) or not isinstance(value, int | float):
            self.fail(key, "must be a number")
        value = float(value)
        if not math.isfinite(value):
            self.fail(key, "must be finite")
        if positive and value <= 0:
            self.fail(key, "must be positive")
        if low is not None and value < low:
            self.fail(key, f"must be at least {low}")
        if high is not None and value > high:
            self.fail(key, f"must be at most {high}")
        return value

    def iso_date(self, key: str) -> date:
        value = self.raw(key)
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        self.fail(key, f"must be an ISO date (YYYY-MM-DD), not {value!r}")
        raise AssertionError  # unreachable

    def names(self, key: str) -> tuple[str, ...]:
        value = self.raw(key)
        if (
            not isinstance(value, list) or not value
            or not all(isinstance(v, str) and v for v in value)
        ):
            self.fail(key, "must be a non-empty list of text")
        if len(set(value)) != len(value):
            self.fail(key, "must not repeat a name")
        return tuple(value)

    def provenance(self, required: bool) -> Provenance | None:
        present = [k for k in COMPANIONS if k in self.data]
        if not present:
            if required:
                where = self.prefix.rstrip(".") or "top level"
                raise ConfigError(
                    f"{self.path}: {where}: checked, source and verified are required "
                    "for values from outside the project"
                )
            return None
        for key in COMPANIONS:
            self.raw(key)  # a missing companion is refused by name
        return Provenance(
            checked=self.iso_date("checked"),
            source=self.text("source"),
            verified=self.boolean("verified"),
        )


# --- instruments (DESIGN 4.2) --------------------------------------------------


@dataclass(frozen=True)
class Provenance:
    """The companions of values that came from outside the project."""

    checked: date
    source: str
    verified: bool


@dataclass(frozen=True)
class Cost:
    fee_per_side: float | None      # quote currency per contract per side
    fee_bps: float | None           # basis points of notional per side
    spread_ticks_main: float
    spread_ticks_off: float
    slippage_coef: float
    provenance: Provenance | None


@dataclass(frozen=True)
class Source:
    """Where an instrument's bars come from; the keys depend on the adapter."""

    adapter: str
    params: tuple[tuple[str, Any], ...]

    def get(self, key: str, default: Any = None) -> Any:
        for name, value in self.params:
            if name == key:
                return value
        return default


@dataclass(frozen=True)
class Instrument:
    symbol: str
    venue: str
    quote_currency: str
    calendar: str
    multiplier: float | None
    tick_size: float
    shorting: bool
    test_only: bool
    trusted_from: date
    main_session: tuple[str, str]
    cost: Cost
    source: Source
    provenance: Provenance | None

    def unverified(self) -> list[tuple[str, Any, Provenance]]:
        """Each sourced value whose companions say ``verified = false``."""
        out: list[tuple[str, Any, Provenance]] = []
        if self.provenance is not None and not self.provenance.verified:
            for key in TOP_SOURCED:
                value = getattr(self, key)
                if value is not None:
                    out.append((key, value, self.provenance))
        if self.cost.provenance is not None and not self.cost.provenance.verified:
            for key in COST_SOURCED:
                value = getattr(self.cost, key)
                if value is not None:
                    out.append((f"cost.{key}", value, self.cost.provenance))
        return out


_INSTRUMENT_KEYS = (
    "symbol", "venue", "quote_currency", "calendar", "multiplier", "tick_size", "shorting",
    "test_only", "trusted_from", "main_session", "cost", "source", "spec",
)
_COST_KEYS = (*COST_SOURCED, *COMPANIONS)


def _source(path: Path, data: Any) -> Source:
    head = _Table(path, data, "source.", data.keys() if isinstance(data, dict) else ())
    adapter = head.choice("adapter", ADAPTERS)
    params: list[tuple[str, Any]] = []
    if adapter == "vendor":
        t = _Table(path, data, "source.", ("adapter", "dataset", "symbol", "roll_rule",
                                           "max_cost_usd"))
        params = [
            ("dataset", t.text("dataset")),
            ("symbol", t.text("symbol")),
            ("roll_rule", t.choice("roll_rule", ("volume",))),
            ("max_cost_usd", t.number("max_cost_usd", positive=True, default=5.0)),
        ]
    elif adapter == "crypto":
        t = _Table(path, data, "source.", ("adapter", "symbol"))
        params = [("symbol", t.text("symbol"))]
    else:
        t = _Table(path, data, "source.", ("adapter", "seed", "hourly_vol", "start_price",
                                           "drop_fraction", "roll_schedule"))
        params = [
            ("seed", t.integer("seed", low=0)),
            ("hourly_vol", t.number("hourly_vol", positive=True)),
            ("start_price", t.number("start_price", positive=True)),
            ("drop_fraction", t.number("drop_fraction", low=0.0, high=0.5, default=0.0)),
            ("roll_schedule", t.choice("roll_schedule", ("none", "quarterly"), default="none")),
        ]
    return Source(adapter=adapter, params=tuple(params))


def _session(t: _Table, key: str) -> tuple[str, str]:
    value = t.raw(key)
    if (
        not isinstance(value, list) or len(value) != 2
        or not all(isinstance(v, str) and _HHMM.match(v) for v in value)
    ):
        t.fail(key, 'must be ["HH:MM", "HH:MM"]')
    if value[0] >= value[1]:
        t.fail(key, "must start before it ends")
    return (value[0], value[1])


def load_instrument(path: Path) -> Instrument:
    """Load one instrument record; the file is named after its symbol."""
    path = Path(path)
    data = read_toml(path)
    t = _Table(path, data, "", _INSTRUMENT_KEYS)
    symbol = t.text("symbol")
    if path.stem != symbol:
        t.fail("symbol", f"is {symbol!r} but the file name says {path.stem!r}")
    c = _Table(path, t.raw("cost"), "cost.", _COST_KEYS)
    source = _source(path, t.raw("source"))

    per_contract, proportional, multiplier = (
        c.has("fee_per_side"), c.has("fee_bps"), t.has("multiplier")
    )
    if not ((per_contract and multiplier and not proportional)
            or (proportional and not multiplier and not per_contract)):
        raise ConfigError(
            f"{path}: exactly one fee form: 'cost.fee_per_side' with 'multiplier', "
            "or 'cost.fee_bps' without 'multiplier'"
        )
    sourced = source.adapter != "synth"
    cost = Cost(
        fee_per_side=c.number("fee_per_side", low=0.0, default=None),
        fee_bps=c.number("fee_bps", low=0.0, default=None),
        spread_ticks_main=c.number("spread_ticks_main", low=0.0),
        spread_ticks_off=c.number("spread_ticks_off", low=0.0),
        slippage_coef=c.number("slippage_coef", low=0.0),
        provenance=c.provenance(required=sourced),
    )
    return Instrument(
        symbol=symbol,
        venue=t.text("venue"),
        quote_currency=t.text("quote_currency"),
        calendar=t.text("calendar"),
        multiplier=t.number("multiplier", positive=True, default=None),
        tick_size=t.number("tick_size", positive=True),
        shorting=t.boolean("shorting"),
        test_only=t.boolean("test_only"),
        trusted_from=t.iso_date("trusted_from"),
        main_session=_session(t, "main_session"),
        cost=cost,
        source=source,
        provenance=_Table(path, t.raw("spec", {}), "spec.", COMPANIONS).provenance(
            required=sourced
        ),
    )


# --- tracks and windows (DESIGN 4.1) -------------------------------------------


@dataclass(frozen=True)
class DateRange:
    """Calendar dates from ``first`` to ``last``, both included."""

    first: date
    last: date

    def __contains__(self, day: object) -> bool:
        return isinstance(day, date) and self.first <= day <= self.last

    def days(self) -> int:
        return (self.last - self.first).days + 1

    def select(self, trading_days: Iterable[date]) -> list[date]:
        """The trading days whose date lies in this range, in order."""
        return sorted(d for d in trading_days if d in self)


@dataclass(frozen=True)
class Windows:
    w: DateRange
    t: DateRange


@dataclass(frozen=True)
class Track:
    name: str
    bar_seconds: int
    w_days: int
    t_days: int
    history_cap_bars: int
    block_days: int
    epoch: date
    instruments: tuple[str, ...]
    families: tuple[str, ...]
    cell_slots: int
    horizons: tuple[tuple[str, tuple[int, int]], ...]

    @property
    def cells(self) -> tuple[tuple[str, str], ...]:
        """(family, horizon) pairs, families then horizons: the cell index order."""
        return tuple((f, h) for f in self.families for h, _ in self.horizons)

    def cell_index(self, family: str, horizon: str) -> int:
        return self.cells.index((family, horizon))

    def windows(self, day: date) -> Windows:
        """T: the ``t_days`` calendar days ending with ``day``; W: the ``w_days`` before."""
        t_first = day - timedelta(days=self.t_days - 1)
        w_last = t_first - timedelta(days=1)
        return Windows(
            w=DateRange(w_last - timedelta(days=self.w_days - 1), w_last),
            t=DateRange(t_first, day),
        )


_TRACK_KEYS = (
    "name", "bar_seconds", "w_days", "t_days", "history_cap_bars", "block_days", "epoch",
    "instruments", "families", "cell_slots", "horizons",
)


def load_track(path: Path) -> Track:
    """Load one track record; the file is named after the track."""
    path = Path(path)
    t = _Table(path, read_toml(path), "", _TRACK_KEYS)
    name = t.text("name")
    if path.stem != name:
        t.fail("name", f"is {name!r} but the file name says {path.stem!r}")
    raw_h = t.raw("horizons")
    h = _Table(path, raw_h, "horizons.", raw_h.keys() if isinstance(raw_h, dict) else ())
    if not h.data:
        t.fail("horizons", "must name at least one horizon")
    horizons = []
    for key, bounds in h.data.items():
        if (
            not isinstance(bounds, list) or len(bounds) != 2
            or not all(isinstance(b, int) and not isinstance(b, bool) for b in bounds)
            or not 1 <= bounds[0] <= bounds[1]
        ):
            h.fail(key, "must be [low, high] holding bars with 1 <= low <= high")
        horizons.append((key, (bounds[0], bounds[1])))
    return Track(
        name=name,
        bar_seconds=t.integer("bar_seconds", low=1),
        w_days=t.integer("w_days", low=1),
        t_days=t.integer("t_days", low=1),
        history_cap_bars=t.integer("history_cap_bars", low=1),
        block_days=t.integer("block_days", low=1),
        epoch=t.iso_date("epoch"),
        instruments=t.names("instruments"),
        families=t.names("families"),
        cell_slots=t.integer("cell_slots", low=1),
        horizons=tuple(horizons),
    )


@dataclass(frozen=True)
class TrackConfig:
    """A track with its instrument records, in the track's order."""

    track: Track
    instruments: tuple[Instrument, ...]


def _check_track(track: Track, path: Path, instruments: Mapping[str, Instrument]) -> TrackConfig:
    records = []
    for symbol in track.instruments:
        if symbol not in instruments:
            raise ConfigError(f"{path}: 'instruments' names {symbol!r}, which has no record")
        inst = instruments[symbol]
        if inst.test_only and not track.name.startswith(TEST_TRACK_PREFIX):
            raise ConfigError(
                f"{path}: {symbol!r} is test_only and the track name does not start "
                f"with {TEST_TRACK_PREFIX!r}"
            )
        records.append(inst)
    return TrackConfig(track=track, instruments=tuple(records))


def load_track_config(config_dir: Path, track_name: str) -> TrackConfig:
    """Load ``tracks/<name>.toml`` and the records of its instruments."""
    config_dir = Path(config_dir)
    path = config_dir / "tracks" / f"{track_name}.toml"
    if not path.is_file():
        raise ConfigError(f"{path}: no record for track {track_name!r}")
    track = load_track(path)
    instruments = {}
    for symbol in track.instruments:
        ipath = config_dir / "instruments" / f"{symbol}.toml"
        if ipath.is_file():
            instruments[symbol] = load_instrument(ipath)
    return _check_track(track, path, instruments)


# --- thresholds (DESIGN 4.3) ---------------------------------------------------

#: Every threshold's table, name and type. Values live in the TOML only (I-10).
THRESHOLD_SCHEMA: dict[str, dict[str, type]] = {
    "validation": {
        "max_params": int, "max_lines": int, "grid_max_params": int, "grid_max_values": int,
        "call_p95_ms": int, "call_max_ms": int, "min_changes_w": int, "corr_max": float,
        "description_max_chars": int,
    },
    "admission": {"min_trades_t": int},
    "lifecycle": {
        "dormant_window_days": int, "retire_dormant_days": int,
        "revival_min_dormant_days": int,
    },
    "controls": {"random_pool": int, "match_window_days": int, "match_min_live": int},
    "gaps": {"max_fraction": float},
    "journal": {"recompute_sample": int},
    "alerts": {
        "persistent_min_days": int, "persistent_base_percentile": float,
        "false_alerts_per_year": float, "group_days": int, "group_level": float,
        "group_bootstrap": int, "rank_blocks": int, "rank_level": float,
        "rank_min_population": int, "revival_min_days": int, "cost_stale_days": int,
        "min_valid_candidates": int, "valid_candidates_window_days": int,
        "no_finding_months": int,
    },
    "pool": {"fail_window": int, "fail_rate": float},
    "coordinator": {"brief_max_chars": int, "weak_window_days": int},
    "stage_gate": {"min_clean_days": int},
    "budgets": {
        "worker_tokens_per_day": int, "coordinator_tokens_per_day": int,
        "worker_max_output_tokens": int,
    },
}


@dataclass(frozen=True)
class HistoryEntry:
    """A dated threshold change; ``key`` is ``table.name`` or ``*``."""

    date: date
    key: str
    reason: str
    old: Any = None   # None: not given (TOML has no null)
    new: Any = None


@dataclass(frozen=True)
class Thresholds:
    values: tuple[tuple[str, Any], ...]   # ("table.name", value), schema order
    history: tuple[HistoryEntry, ...]

    def __getitem__(self, key: str) -> Any:
        for name, value in self.values:
            if name == key:
                return value
        raise KeyError(key)


def load_thresholds(path: Path) -> Thresholds:
    path = Path(path)
    top = _Table(path, read_toml(path), "", (*THRESHOLD_SCHEMA, "history"))
    values: list[tuple[str, Any]] = []
    for table, schema in THRESHOLD_SCHEMA.items():
        t = _Table(path, top.raw(table), f"{table}.", schema)
        for key, kind in schema.items():
            low = 0 if kind is int else 0.0
            value = t.integer(key, low=low) if kind is int else t.number(key, low=low)
            values.append((f"{table}.{key}", value))
    keys = {k for k, _ in values}
    history = []
    raw_history = top.raw("history", [])
    if not isinstance(raw_history, list):
        top.fail("history", "must be an array of tables ([[history]])")
    for entry in raw_history:
        h = _Table(path, entry, "history.", ("date", "key", "old", "new", "reason"))
        key = h.text("key")
        if key != "*" and key not in keys:
            h.fail("key", f"names {key!r}, which is not a threshold")
        if key != "*":
            h.raw("new")
            h.raw("old")
        history.append(HistoryEntry(
            date=h.iso_date("date"), key=key, reason=h.text("reason"),
            old=h.raw("old", None), new=h.raw("new", None),
        ))
    return Thresholds(values=tuple(values), history=tuple(history))


def threshold_drift(current: Thresholds, frozen: Thresholds) -> list[str]:
    """Values that differ from the frozen copy without a history entry giving them.

    For each key whose current value differs from the frozen starting value,
    the last history entry for that key must give the current value as ``new``.
    """
    problems = []
    for key, value in current.values:
        if value == frozen[key]:
            continue
        entries = [e for e in current.history if e.key == key]
        if not entries or entries[-1].new != value:
            problems.append(
                f"{key} is {value!r}, frozen {frozen[key]!r}, and the last history "
                f"entry for it does not give {value!r} as new"
            )
    return problems


# --- frozen config and config/HISTORY.toml (DESIGN 4.3) ------------------------


@dataclass(frozen=True)
class Change:
    """One owner-approved change to a frozen value; ``key`` ``*`` is a whole file."""

    date: date
    file: str
    key: str
    reason: str
    decision: str
    old: Any = None   # None: not given
    new: Any = None   # None: not given (a removed key or a new file)


def load_changes(path: Path) -> tuple[Change, ...]:
    path = Path(path)
    top = _Table(path, read_toml(path), "", ("change",))
    raw_changes = top.raw("change", [])
    if not isinstance(raw_changes, list):
        top.fail("change", "must be an array of tables ([[change]])")
    changes = []
    for entry in raw_changes:
        c = _Table(path, entry, "change.",
                   ("date", "file", "key", "old", "new", "reason", "decision"))
        changes.append(Change(
            date=c.iso_date("date"), file=c.text("file"), key=c.text("key"),
            reason=c.text("reason"), decision=c.text("decision"),
            old=c.raw("old", None), new=c.raw("new", None),
        ))
    return tuple(changes)


def flatten(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Dotted keys to values; an array of tables is indexed (``closure.0.start``)."""
    out: dict[str, Any] = {}
    for key, value in data.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, f"{name}."))
        elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            for i, item in enumerate(value):
                out.update(flatten(item, f"{name}.{i}."))
        elif isinstance(value, date):
            out[name] = value.isoformat()
        else:
            out[name] = value
    return out


def frozen_files(root: Path) -> list[str]:
    root = Path(root)
    found = [f for f in FROZEN_FILES if (root / f).is_file()]
    for d in FROZEN_DIRS:
        found += [p.relative_to(root).as_posix() for p in (root / d).glob("*.toml")]
    return sorted(found)


def frozen_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    """The current frozen values: file (relative to ``root``) to dotted key to value."""
    return {f: flatten(read_toml(Path(root) / f)) for f in frozen_files(root)}


def frozen_drift(
    root: Path, frozen: Mapping[str, Mapping[str, Any]], changes: Sequence[Change]
) -> list[str]:
    """Frozen values, and frozen files, that changed without an approved change entry.

    A changed or added key needs a last change entry for (file, key) giving the
    current value as ``new``; a removed key needs one with no ``new``; a new file
    needs an entry for (file, ``*``). Each such entry must name a decisions file
    under ``meta/decisions/`` that exists.
    """
    root = Path(root)
    current = frozen_snapshot(root)
    problems: list[str] = []

    def approved(file: str, key: str, value: Any) -> str | None:
        entries = [c for c in changes if c.file == file and c.key == key]
        if not entries:
            return "no change entry"
        last = entries[-1]
        if last.new != value:
            return f"the last change entry gives new = {last.new!r}"
        if not last.decision.startswith(DECISIONS_DIR) or not (root / last.decision).is_file():
            return f"decision {last.decision!r} is not a file under {DECISIONS_DIR}"
        return None

    for file in sorted(set(current) | set(frozen)):
        if file not in current:
            problems.append(f"{file}: frozen file is missing")
            continue
        if file not in frozen:
            why = approved(file, "*", None)
            if why:
                problems.append(f"{file}: new frozen file, {why}")
            continue
        now, then = current[file], frozen[file]
        for key in sorted(set(now) | set(then)):
            value = now.get(key)
            if key in now and key in then and value == then[key]:
                continue
            why = approved(file, key, value)
            if why:
                was = repr(then[key]) if key in then else "absent"
                is_ = repr(value) if key in now else "absent"
                problems.append(f"{file}: {key} is {is_}, frozen {was}; {why}")
    return problems


# --- config check (DESIGN 4) ---------------------------------------------------


@dataclass(frozen=True)
class CheckReport:
    lines: tuple[str, ...]
    unverified: tuple[str, ...]


def _show(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return repr(list(value))
    return repr(value)


def check(config_dir: Path, track_name: str) -> CheckReport:
    """Load every record under ``config_dir``; raise ``ConfigError`` on the first invalid one."""
    config_dir = Path(config_dir)
    lines: list[str] = []
    unverified: list[str] = []

    instruments: dict[str, Instrument] = {}
    for path in sorted((config_dir / "instruments").glob("*.toml")):
        inst = load_instrument(path)
        instruments[inst.symbol] = inst
        fee = (f"fee {inst.cost.fee_per_side}/side" if inst.cost.fee_per_side is not None
               else f"fee {inst.cost.fee_bps} bps")
        lines.append(
            f"instrument {inst.symbol}: venue {inst.venue}, calendar {inst.calendar}, "
            f"{fee}, adapter {inst.source.adapter}"
            + (", test only" if inst.test_only else "")
        )
        for key, value, prov in inst.unverified():
            unverified.append(
                f"unverified instruments/{path.name} {key} = {_show(value)} "
                f"(checked {prov.checked.isoformat()}; source: {prov.source})"
            )

    track_paths = sorted((config_dir / "tracks").glob("*.toml"))
    names = [p.stem for p in track_paths]
    if track_name not in names:
        raise ConfigError(f"{config_dir / 'tracks'}: no record for track {track_name!r}")
    for path in track_paths:
        tc = _check_track(load_track(path), path, instruments)
        t = tc.track
        lines.append(
            f"track {t.name}: {len(t.instruments)} instruments, {len(t.cells)} cells, "
            f"bar {t.bar_seconds}s, W {t.w_days} days, T {t.t_days} days"
            + (" (selected)" if t.name == track_name else "")
        )

    thresholds = load_thresholds(config_dir / "thresholds.toml")
    lines.append(
        f"thresholds: {len(thresholds.values)} values in {len(THRESHOLD_SCHEMA)} tables, "
        f"{len(thresholds.history)} history entries"
    )
    history = config_dir / "HISTORY.toml"
    changes = load_changes(history) if history.is_file() else ()
    lines.append(f"history: {len(changes)} changes")
    return CheckReport(lines=tuple(lines), unverified=tuple(unverified))
