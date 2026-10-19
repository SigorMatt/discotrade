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

import calendar
import math
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path, PurePosixPath
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
#: A synthetic record's generator settings (decision 2026-10-12 10), required.
SYNTH_GENERATOR = (
    "gap_scale", "range_scale", "volume_median", "volume_sigma", "hour_vol_amplitude",
    "hour_volume_amplitude", "hour_peak_utc",
)
#: A synthetic record's contract keys (DESIGN 17.1), required with
#: ``roll_schedule = "quarterly"`` and refused without it.
SYNTH_CONTRACT = ("roll_day", "contract_overlap_bars", "contract_offset_scale")
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
        # The endpoint is configuration (decision 2026-10-12 12).
        t = _Table(path, data, "source.", ("adapter", "base_url", "market"))
        params = [("base_url", t.text("base_url")), ("market", t.text("market"))]
    else:
        t = _Table(path, data, "source.", ("adapter", "seed", "hourly_vol", "start_price",
                                           "drop_fraction", "roll_schedule", *SYNTH_GENERATOR,
                                           *SYNTH_CONTRACT))
        params = [
            ("seed", t.integer("seed", low=0)),
            ("hourly_vol", t.number("hourly_vol", positive=True)),
            ("start_price", t.number("start_price", positive=True)),
            ("drop_fraction", t.number("drop_fraction", low=0.0, high=0.5, default=0.0)),
            ("roll_schedule", t.choice("roll_schedule", ("none", "quarterly"), default="none")),
            # The generator settings (decision 2026-10-12 10), all required.
            ("gap_scale", t.number("gap_scale", low=0.0)),
            ("range_scale", t.number("range_scale", low=0.0)),
            ("volume_median", t.number("volume_median", positive=True)),
            ("volume_sigma", t.number("volume_sigma", low=0.0)),
            ("hour_vol_amplitude", t.number("hour_vol_amplitude", low=0.0)),
            ("hour_volume_amplitude", t.number("hour_volume_amplitude", low=0.0)),
            ("hour_peak_utc", t.integer("hour_peak_utc", low=0)),
        ]
        if dict(params)["hour_vol_amplitude"] >= 1.0:
            t.fail("hour_vol_amplitude", "must be less than 1, so the volatility shape stays "
                   "positive")
        if dict(params)["hour_peak_utc"] > 23:
            t.fail("hour_peak_utc", "must be at most 23")
        if dict(params)["roll_schedule"] == "quarterly":
            # The contract keys of DESIGN 17.1 (decision 2026-10-12 10).
            params += [
                ("roll_day", t.integer("roll_day", low=1)),
                ("contract_overlap_bars", t.integer("contract_overlap_bars", low=24)),
                ("contract_offset_scale", t.number("contract_offset_scale", low=0.0)),
            ]
            if dict(params)["roll_day"] > 28:
                t.fail("roll_day", "must be at most 28")
        else:
            for key in SYNTH_CONTRACT:
                if t.has(key):
                    t.fail(key, 'is a contract key: it needs roll_schedule = "quarterly"')
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


# --- calendars (DESIGN 5.3) ----------------------------------------------------

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
#: Calendar values that come from outside the project; their companions are the
#: record's top-level ``checked``, ``source`` and ``verified``.
CALENDAR_SOURCED = ("week_open", "week_close", "daily_break", "day_rolls_at")
_CALENDAR_KEYS = ("name", "tz", *CALENDAR_SOURCED, "closure", *COMPANIONS)
_LOCAL_MINUTE = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class Closure:
    """The market is shut for the local wall-clock interval [start, end)."""

    start: datetime   # naive, in the calendar's time zone
    end: datetime
    note: str
    provenance: Provenance | None

    def show(self) -> str:
        return f"{self.start.strftime(_LOCAL_MINUTE)} to {self.end.strftime(_LOCAL_MINUTE)}"


@dataclass(frozen=True)
class Calendar:
    """A trading calendar record. ``always_open`` records carry nothing else."""

    name: str
    always_open: bool
    tz: str | None = None
    week_open: tuple[str, str] | None = None     # (weekday, "HH:MM") local
    week_close: tuple[str, str] | None = None
    daily_break: tuple[str, str] | None = None   # ("HH:MM", "HH:MM") local
    day_rolls_at: str | None = None              # "HH:MM" local
    closures: tuple[Closure, ...] = ()
    provenance: Provenance | None = None

    def unverified(self) -> list[tuple[str, Any, Provenance]]:
        """Each sourced value whose companions say ``verified = false``."""
        out: list[tuple[str, Any, Provenance]] = []
        if self.provenance is not None and not self.provenance.verified:
            out += [(k, getattr(self, k), self.provenance) for k in CALENDAR_SOURCED]
        for i, c in enumerate(self.closures):
            if c.provenance is not None and not c.provenance.verified:
                out.append((f"closure.{i}", c.show(), c.provenance))
        return out


def _weekly(t: _Table, key: str) -> tuple[str, str]:
    value = t.raw(key)
    if (
        not isinstance(value, list) or len(value) != 2
        or not all(isinstance(v, str) for v in value)
        or value[0] not in WEEKDAYS or not _HHMM.match(value[1])
    ):
        t.fail(key, f'must be ["Day", "HH:MM"] with Day one of {", ".join(WEEKDAYS)}')
    return (value[0], value[1])


def _local_minute(t: _Table, key: str) -> datetime:
    value = t.raw(key)
    try:
        if isinstance(value, str) and len(value) == 16:
            return datetime.strptime(value, _LOCAL_MINUTE)
    except ValueError:
        pass
    t.fail(key, f'must be a local time "YYYY-MM-DD HH:MM", not {value!r}')
    raise AssertionError  # unreachable


def load_calendar(path: Path) -> Calendar:
    """Load one calendar record; the file is named after the calendar."""
    path = Path(path)
    data = read_toml(path)
    if "always_open" in data:
        t = _Table(path, data, "", ("name", "always_open"))
        if t.boolean("always_open") is not True:
            t.fail("always_open", "must be true when present (omit it otherwise)")
        extra = [k for k in data if k not in ("name", "always_open")]
        if extra:
            t.fail("always_open", "allows no other key")
    else:
        t = _Table(path, data, "", _CALENDAR_KEYS)
    name = t.text("name")
    if path.stem != name:
        t.fail("name", f"is {name!r} but the file name says {path.stem!r}")
    if "always_open" in data:
        return Calendar(name=name, always_open=True)

    tz = t.text("tz")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        t.fail("tz", f"names no known time zone: {tz!r}")
    day_rolls_at = t.text("day_rolls_at")
    if not _HHMM.match(day_rolls_at):
        t.fail("day_rolls_at", f'must be "HH:MM", not {day_rolls_at!r}')
    raw_closures = t.raw("closure", [])
    if not isinstance(raw_closures, list):
        t.fail("closure", "must be an array of tables ([[closure]])")
    closures = []
    for entry in raw_closures:
        c = _Table(path, entry, "closure.", ("start", "end", "note", *COMPANIONS))
        start, end = _local_minute(c, "start"), _local_minute(c, "end")
        if end <= start:
            c.fail("end", "must be later than start")
        closures.append(Closure(
            start=start, end=end, note=c.text("note"), provenance=c.provenance(required=False),
        ))
    return Calendar(
        name=name,
        always_open=False,
        tz=tz,
        week_open=_weekly(t, "week_open"),
        week_close=_weekly(t, "week_close"),
        daily_break=_session(t, "daily_break"),
        day_rolls_at=day_rolls_at,
        closures=tuple(closures),
        provenance=t.provenance(required=False),
    )


# --- spread tables (DESIGN 5.7) ------------------------------------------------

HOURS = 24
#: SPEC decision 14 (decision 2026-10-12 14): an instrument whose measured spread
#: table has a main-session hour above this many ticks is reported by ``config
#: check`` as marginal. A fixed rule of the spec, not a tunable threshold.
MARGINAL_SPREAD_TICKS = 1.0
_SPREAD_KEYS = ("symbol", "spread_ticks", "description", *COMPANIONS)


@dataclass(frozen=True)
class SpreadTable:
    """A measured spread table: ticks per exchange-local hour of day, index 0 to 23."""

    symbol: str
    ticks: tuple[float, ...]
    description: str
    provenance: Provenance

    def main_session_hours(self, main_session: tuple[str, str]) -> tuple[int, ...]:
        """The hours of day whose hour [h:00, h+1:00) overlaps ``main_session``."""
        start, end = (int(t[:2]) * 60 + int(t[3:]) for t in main_session)
        return tuple(h for h in range(HOURS) if h * 60 < end and (h + 1) * 60 > start)

    def marginal(self, main_session: tuple[str, str]) -> list[tuple[int, float]]:
        """The main-session hours above ``MARGINAL_SPREAD_TICKS``, with their spread."""
        return [(h, self.ticks[h]) for h in self.main_session_hours(main_session)
                if self.ticks[h] > MARGINAL_SPREAD_TICKS]


def load_spread_table(path: Path) -> SpreadTable:
    """Load ``spreads/<symbol>.toml``: 24 spreads in ticks, a description and companions."""
    path = Path(path)
    t = _Table(path, read_toml(path), "", _SPREAD_KEYS)
    symbol = t.text("symbol")
    if path.stem != symbol:
        t.fail("symbol", f"is {symbol!r} but the file name says {path.stem!r}")
    values = t.raw("spread_ticks")
    if (
        not isinstance(values, list) or len(values) != HOURS
        or not all(isinstance(v, int | float) and not isinstance(v, bool) for v in values)
    ):
        t.fail("spread_ticks", f"must be a list of {HOURS} numbers, one per exchange-local "
               "hour of day")
    ticks = tuple(float(v) for v in values)
    if not all(math.isfinite(v) and v >= 0 for v in ticks):
        t.fail("spread_ticks", "must hold finite numbers of at least 0")
    provenance = t.provenance(required=True)
    assert provenance is not None
    return SpreadTable(symbol=symbol, ticks=ticks, description=t.text("description"),
                       provenance=provenance)


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


# --- run settings (DESIGN 3, 12.4; decision 2026-10-14-m12 96) -----------------

#: The run-settings file of a configuration directory. Not frozen (DESIGN 4.3):
#: it holds how the harness runs, not a value that moves a result.
RUN_FILE = "run.toml"
_SANDBOX_KEYS = ("wall_seconds", "cpu_seconds", "memory_bytes", "output_bytes", "image",
                 "pids", "cpus", "tmpfs_bytes", "runtime")
_WORKERS_KEYS = ("claude_fallback", "request_timeout_seconds")
_COORDINATOR_KEYS = ("binary", "model", "max_turns", "max_budget_usd", "timeout_seconds",
                     "propose_fixes")
#: The container runtimes ``sandbox.runtime`` may name (DESIGN 12.4; decision 102 (a)).
RUNTIMES = ("docker", "podman")
#: An image repository name without a tag or digest (decision 102 (d), (e): the tag
#: is the hash of the image's inputs, added by the harness).
_IMAGE_NAME = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*")


@dataclass(frozen=True)
class SandboxSettings:
    """``[sandbox]`` of ``run.toml``: the limits a sandbox job carries (DESIGN 12.4).
    ``wall_seconds`` is enforced by the harness, which kills the child;
    ``cpu_seconds`` and ``memory_bytes`` (address space) are set in the child;
    ``output_bytes`` caps the result read from its standard output. The container
    backend's keys (decision 102 (d)): ``image``, the image's repository name
    (its tag is the hash of its inputs); ``pids``, the process limit; ``cpus``,
    the CPU limit; ``tmpfs_bytes``, the size of the ``tmpfs`` at ``/tmp``; and
    ``runtime``, ``docker`` or ``podman``, None when absent (the first found on
    ``PATH``)."""

    wall_seconds: float
    cpu_seconds: float
    memory_bytes: int
    output_bytes: int
    image: str
    pids: int
    cpus: float
    tmpfs_bytes: int
    runtime: str | None = None


@dataclass(frozen=True)
class WorkerSettings:
    """``[workers]`` of ``run.toml`` (DESIGN 13.6; decision 2026-10-16-m15 123 (d)):
    ``claude_fallback``, whether a failing cell is served by the Claude worker (R-21,
    off in v1), and ``request_timeout_seconds``, a worker provider request's timeout."""

    claude_fallback: bool
    request_timeout_seconds: float


@dataclass(frozen=True)
class CoordinatorSettings:
    """``[coordinator]`` of ``run.toml`` (DESIGN 3, 14.2, 14.4; decision 2026-10-18-m20
    163 (b)): ``binary``, the ``claude`` executable (default ``claude``, found on
    ``PATH``); ``model``, the explicit model; ``max_turns``, read but not passed (the
    installed ``claude --help`` lists no ``--max-turns``); ``max_budget_usd``, the
    spending limit of one call; ``timeout_seconds``, after which the call's process
    group is killed; ``propose_fixes``, whether fix sessions run (off in v1)."""

    binary: str
    model: str
    max_turns: int
    max_budget_usd: float
    timeout_seconds: float
    propose_fixes: bool


@dataclass(frozen=True)
class RunConfig:
    sandbox: SandboxSettings
    #: None when ``run.toml`` has no ``[workers]`` table: only the code that builds a
    #: worker provider or the day's pool needs it, as only job building needs ``[sandbox]``.
    workers: WorkerSettings | None = None
    #: None when ``run.toml`` has no ``[coordinator]`` table: only ``--coordinator
    #: claude`` and ``doctor --live coordinator`` need it (decision 163 (e), (f)).
    coordinator: CoordinatorSettings | None = None


def load_run(config_dir: Path) -> RunConfig:
    """Load ``<config_dir>/run.toml``. Only the code that builds a sandbox job
    requires it (decision 96); its absence is refused naming the file."""
    path = Path(config_dir) / RUN_FILE
    if not path.is_file():
        raise ConfigError(f"{path}: no such file; a sandbox job takes its limits from "
                          f"{RUN_FILE} (DESIGN 3, 12.4)")
    top = _Table(path, read_toml(path), "", ("sandbox", "workers", "coordinator"))
    s = _Table(path, top.raw("sandbox"), "sandbox.", _SANDBOX_KEYS)
    workers = None
    if top.has("workers"):
        w = _Table(path, top.raw("workers"), "workers.", _WORKERS_KEYS)
        workers = WorkerSettings(
            claude_fallback=w.boolean("claude_fallback"),
            request_timeout_seconds=w.number("request_timeout_seconds", positive=True),
        )
    coordinator = None
    if top.has("coordinator"):
        c = _Table(path, top.raw("coordinator"), "coordinator.", _COORDINATOR_KEYS)
        coordinator = CoordinatorSettings(
            binary=c.text("binary", "claude"),
            model=c.text("model"),
            max_turns=c.integer("max_turns", low=1),
            max_budget_usd=c.number("max_budget_usd", positive=True),
            timeout_seconds=c.number("timeout_seconds", positive=True),
            propose_fixes=c.boolean("propose_fixes"),
        )
    return RunConfig(workers=workers, coordinator=coordinator, sandbox=SandboxSettings(
        wall_seconds=s.number("wall_seconds", positive=True),
        cpu_seconds=s.number("cpu_seconds", positive=True),
        memory_bytes=s.integer("memory_bytes", low=1),
        output_bytes=s.integer("output_bytes", low=1),
        image=_image_name(s),
        pids=s.integer("pids", low=1),
        cpus=s.number("cpus", positive=True),
        tmpfs_bytes=s.integer("tmpfs_bytes", low=1),
        runtime=s.choice("runtime", RUNTIMES, default=None),
    ))


#: The protected paths of a configuration directory (DESIGN 14.4; decision
#: 2026-10-18-m20 164 (a)). Not frozen.
PROTECTED_FILE = "protected_paths.toml"


@dataclass(frozen=True)
class ProtectedPaths:
    """``protected_paths.toml``: ``code``, paths relative to the code repository, and
    ``state``, paths relative to the state directory; a path ending in ``/`` is a
    directory (DESIGN 14.4; decision 164 (a))."""

    code: tuple[str, ...]
    state: tuple[str, ...]


def load_protected_paths(path: Path) -> ProtectedPaths:
    """Load ``protected_paths.toml``; refuse an empty list, a path that is not
    relative text, that is absolute, or that holds a ``..`` part (decision 164 (c))."""
    path = Path(path)
    top = _Table(path, read_toml(path), "", ("code", "state"))
    lists: dict[str, tuple[str, ...]] = {}
    for key in ("code", "state"):
        value = top.raw(key)
        if not isinstance(value, list) or not value:
            top.fail(key, "must be a non-empty array of relative paths")
        for item in value:
            if not isinstance(item, str) or not item.strip("/"):
                top.fail(key, f"holds {item!r}, which is not a path")
            if item.startswith(("/", "~")) or PurePosixPath(item).is_absolute():
                top.fail(key, f"holds {item!r}, an absolute path; give it relative")
            if ".." in PurePosixPath(item).parts or "\\" in item:
                top.fail(key, f"holds {item!r}, which holds '..' or a backslash")
        if len(set(value)) != len(value):
            top.fail(key, "holds a path twice")
        lists[key] = tuple(value)
    return ProtectedPaths(code=lists["code"], state=lists["state"])


def _image_name(table: _Table) -> str:
    value = table.text("image")
    if not _IMAGE_NAME.fullmatch(value):
        table.fail("image", "must be an image repository name, lower case, with no tag "
                   f"or digest (the harness adds the tag), not {value!r}")
    return value


# --- the model pool (DESIGN 13.6, 11.3; R-14; decision 2026-10-16-m15 123) -------

#: The model-pool file of a configuration directory; frozen (DESIGN 4.3).
MODELS_FILE = "models.toml"
#: ``cutoff_basis``: a stated training-cutoff month (``"YYYY-MM"``), or a release
#: date (``"YYYY-MM-DD"``) for a maker that states none (DESIGN 11.3).
CUTOFF_BASES = ("stated", "release")
_MODEL_KEYS = ("id", "maker", "cutoff", "cutoff_basis", "pool", "fallback", *COMPANIONS)
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True)
class Model:
    """One ``[[model]]`` of ``models.toml``. ``pool`` is true for a rotating pool
    model, false for a fallback only; ``fallback`` names a ``pool = false`` model
    of the same maker, or is None."""

    id: str
    maker: str
    cutoff: str                 # as written
    cutoff_basis: str
    pool: bool
    fallback: str | None
    provenance: Provenance

    @property
    def cutoff_date(self) -> date:
        """The cutoff date as used (DESIGN 11.3; R-14): the last day of a stated
        month, or the release date as is (decision 123 (a), (c))."""
        if self.cutoff_basis == "stated":
            year, month = (int(x) for x in self.cutoff.split("-"))
            return date(year, month, calendar.monthrange(year, month)[1])
        return date.fromisoformat(self.cutoff)


@dataclass(frozen=True)
class ModelsConfig:
    """``models.toml``: the provider's ``base_url`` with its companions, and the
    models in file order, which is the pool's order."""

    base_url: str
    provenance: Provenance
    models: tuple[Model, ...]

    @property
    def pool(self) -> tuple[Model, ...]:
        """The ``pool = true`` models, in file order."""
        return tuple(m for m in self.models if m.pool)

    def get(self, model_id: str) -> Model:
        for m in self.models:
            if m.id == model_id:
                return m
        raise KeyError(model_id)

    def unverified(self) -> list[tuple[str, Any, Provenance]]:
        """``base_url`` and each model's ``cutoff`` whose companions say unverified."""
        out: list[tuple[str, Any, Provenance]] = []
        if not self.provenance.verified:
            out.append(("base_url", self.base_url, self.provenance))
        out += [(f"model.{m.id}.cutoff", m.cutoff, m.provenance)
                for m in self.models if not m.provenance.verified]
        return out


def _cutoff(t: _Table, basis: str) -> str:
    value = t.text("cutoff")
    if basis == "stated":
        match = _MONTH.match(value)
        if not match or not 1 <= int(match.group(2)) <= 12:
            t.fail("cutoff", f'must be "YYYY-MM" for a stated cutoff month, not {value!r}')
    else:
        try:
            if len(value) != 10:
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            t.fail("cutoff", f'must be "YYYY-MM-DD" for a release date, not {value!r}')
    return value


def load_models(path: Path) -> ModelsConfig:
    """Load ``models.toml`` (decision 2026-10-16-m15 123 (a), (c)). Refused: an
    unknown key, a missing key or companion, a cutoff not of its basis's form, a
    duplicate id, a fallback that names no ``pool = false`` model of the same maker
    (or that a ``pool = false`` model carries), and an empty pool."""
    path = Path(path)
    top = _Table(path, read_toml(path), "", ("base_url", "model", *COMPANIONS))
    base_url = top.raw("base_url")
    if not isinstance(base_url, str):
        top.fail("base_url", "must be text (the empty string when it is not known)")
    provenance = top.provenance(required=True)
    assert provenance is not None
    raw_models = top.raw("model", [])
    if not isinstance(raw_models, list):
        top.fail("model", "must be an array of tables ([[model]])")
    models: list[Model] = []
    for entry in raw_models:
        t = _Table(path, entry, "model.", _MODEL_KEYS)
        model_id = t.text("id")
        if any(m.id == model_id for m in models):
            t.fail("id", f"{model_id!r} is a duplicate id")
        basis = t.choice("cutoff_basis", CUTOFF_BASES)
        prov = t.provenance(required=True)
        assert prov is not None
        models.append(Model(
            id=model_id, maker=t.text("maker"), cutoff=_cutoff(t, basis), cutoff_basis=basis,
            pool=t.boolean("pool"), fallback=t.text("fallback", None), provenance=prov,
        ))
    for m in models:
        if m.fallback is None:
            continue
        where = f"{path}: 'model.fallback' of {m.id!r}"
        if not m.pool:
            raise ConfigError(f"{where}: a pool = false model has no fallback")
        target = next((x for x in models if x.id == m.fallback), None)
        if target is None or target.pool or target.maker != m.maker:
            raise ConfigError(f"{where} names {m.fallback!r}, which is not a pool = false "
                              f"model of the same maker ({m.maker!r})")
    if not any(m.pool for m in models):
        raise ConfigError(f"{path}: empty pool: no [[model]] has pool = true")
    return ModelsConfig(base_url=base_url, provenance=provenance, models=tuple(models))


# --- the owner's stage-gate flags (DESIGN 3, 15.5; SPEC 14; decision 2026-10-17-m19 153) --

#: The owner's two manual stage-3 conditions, read by the dashboard only. Not
#: frozen and holding no number: no result moves with it (decision 153 (b)).
GATES_FILE = "gates.toml"
GATES_TABLE = "stage3"
GATE_FLAGS = ("stage2_fills_match", "tax_confirmed")


@dataclass(frozen=True)
class OwnerGates:
    """``[stage3]`` of ``gates.toml``: SPEC 14's two conditions only the owner can
    meet (stage-2 fills match the cost model; tax treatment confirmed)."""

    stage2_fills_match: bool = False
    tax_confirmed: bool = False


def load_gates(config_dir: Path) -> OwnerGates:
    """``<config_dir>/gates.toml``'s two flags, both required booleans. A
    configuration without the file has neither condition met (both false; the
    design is silent on a missing file, and not met is the simplest safe
    reading)."""
    path = Path(config_dir) / GATES_FILE
    if not path.is_file():
        return OwnerGates()
    top = _Table(path, read_toml(path), "", (GATES_TABLE,))
    t = _Table(path, top.raw(GATES_TABLE), f"{GATES_TABLE}.", GATE_FLAGS)
    return OwnerGates(**{flag: t.boolean(flag) for flag in GATE_FLAGS})


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


def frozen_value(value: Any) -> Any:
    """A TOML value as the frozen map (JSON) stores it, keeping its TOML type.

    Booleans, integers, floats and strings are themselves; a date, a time or a
    date-time becomes ``{"date": iso}``, ``{"time": iso}`` or ``{"datetime": iso}``
    so that it never equals the string it prints as; arrays and tables are
    converted element by element.
    """
    if isinstance(value, datetime):
        return {"datetime": value.isoformat()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, time):
        return {"time": value.isoformat()}
    if isinstance(value, list | tuple):
        return [frozen_value(v) for v in value]
    if isinstance(value, dict):
        return {k: frozen_value(v) for k, v in value.items()}
    return value


def same_value(a: Any, b: Any) -> bool:
    """Type-strict equality: same TOML type and same value (decision 8, 2026-10-12).

    ``5`` is not ``5.0``, ``true`` is not ``1`` and ``"1"`` is not ``1``; arrays
    and tables compare element by element under the same rule.
    """
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(same_value(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same_value(a[k], b[k]) for k in a)
    return bool(a == b)


def flatten(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Dotted keys to frozen values; an array of tables is indexed (``closure.0.start``)."""
    out: dict[str, Any] = {}
    for key, value in data.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, f"{name}."))
        elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            for i, item in enumerate(value):
                out.update(flatten(item, f"{name}.{i}."))
        else:
            out[name] = frozen_value(value)
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

    Values compare type-strictly (``same_value``). A changed or added key needs a
    last change entry for (file, key) giving the current value as ``new``; a
    removed key needs one with no ``new``; a new file needs an entry for (file,
    ``*``). Each such entry must name a decisions file under ``meta/decisions/``
    that exists.
    """
    root = Path(root)
    current = frozen_snapshot(root)
    problems: list[str] = []

    def approved(file: str, key: str, value: Any) -> str | None:
        entries = [c for c in changes if c.file == file and c.key == key]
        if not entries:
            return "no change entry"
        last = entries[-1]
        if not same_value(frozen_value(last.new), value):
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
            if key in now and key in then and same_value(value, then[key]):
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
    warnings: tuple[str, ...] = ()


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

    calendars: dict[str, Calendar] = {}
    for path in sorted((config_dir / "calendars").glob("*.toml")):
        cal = load_calendar(path)
        calendars[cal.name] = cal
        if cal.always_open:
            lines.append(f"calendar {cal.name}: always open")
        else:
            span = (f", {cal.closures[0].start.date()} to {cal.closures[-1].end.date()}"
                    if cal.closures else "")
            lines.append(
                f"calendar {cal.name}: tz {cal.tz}, week {' '.join(cal.week_open or ())} to "
                f"{' '.join(cal.week_close or ())}, break {'-'.join(cal.daily_break or ())}, "
                f"{len(cal.closures)} closures{span}"
            )
        for key, value, prov in cal.unverified():
            unverified.append(
                f"unverified calendars/{path.name} {key} = {_show(value)} "
                f"(checked {prov.checked.isoformat()}; source: {prov.source})"
            )

    instruments: dict[str, Instrument] = {}
    for path in sorted((config_dir / "instruments").glob("*.toml")):
        inst = load_instrument(path)
        if inst.calendar not in calendars:
            raise ConfigError(
                f"{path}: 'calendar' names {inst.calendar!r}, which has no record "
                f"under {config_dir / 'calendars'}"
            )
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

    # Measured spread tables (DESIGN 5.7) and the marginal-spread warning
    # (decision 2026-10-12 14): a warning, never a failure.
    warnings: list[str] = []
    for path in sorted((config_dir / "spreads").glob("*.toml")):
        table = load_spread_table(path)
        if table.symbol not in instruments:
            raise ConfigError(f"{path}: 'symbol' names {table.symbol!r}, which has no "
                              f"instrument record under {config_dir / 'instruments'}")
        lines.append(f"spread table {table.symbol}: {HOURS} hours, {min(table.ticks):g} to "
                     f"{max(table.ticks):g} ticks")
        prov = table.provenance
        if not prov.verified:
            unverified.append(
                f"unverified spreads/{path.name} spread_ticks = {list(table.ticks)!r} "
                f"(checked {prov.checked.isoformat()}; source: {prov.source})"
            )
        over = table.marginal(instruments[table.symbol].main_session)
        if over:
            hours = ", ".join(f"hour {h:02d} {v:g} ticks" for h, v in over)
            warnings.append(
                f"warning: spreads/{path.name}: {table.symbol} has a main-session spread "
                f"above {MARGINAL_SPREAD_TICKS:g} tick ({hours}); SPEC decision 14 applies"
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
    if (config_dir / MODELS_FILE).is_file():  # checked when present
        models = load_models(config_dir / MODELS_FILE)
        lines.append(f"models: base_url {models.base_url!r}, {len(models.pool)} pool models, "
                     f"{len(models.models) - len(models.pool)} fallback only")
        for m in models.models:
            lines.append(
                f"model {m.id}: maker {m.maker}, cutoff {m.cutoff} ({m.cutoff_basis}), "
                f"cutoff date {m.cutoff_date.isoformat()}, "
                + ("pool" if m.pool else "fallback only")
                + (f", fallback {m.fallback}" if m.fallback else "")
            )
        for key, value, prov in models.unverified():
            unverified.append(
                f"unverified {MODELS_FILE} {key} = {_show(value)} "
                f"(checked {prov.checked.isoformat()}; source: {prov.source})"
            )
    if (config_dir / RUN_FILE).is_file():  # checked when present; only job building needs it
        run = load_run(config_dir)
        s = run.sandbox
        lines.append(
            f"run: sandbox wall {s.wall_seconds:g} s, cpu {s.cpu_seconds:g} s, "
            f"memory {s.memory_bytes} bytes, output {s.output_bytes} bytes"
        )
        lines.append(
            f"run: container image {s.image}, pids {s.pids}, cpus {s.cpus:g}, "
            f"tmpfs {s.tmpfs_bytes} bytes, runtime {s.runtime or 'docker or podman on PATH'}"
        )
        if run.workers is not None:
            w = run.workers
            if w.claude_fallback:
                # Decision 123 (d): no Claude worker can be configured in this step.
                raise ConfigError(
                    f"{config_dir / RUN_FILE}: 'workers.claude_fallback' is true, but no "
                    "Claude worker is configured (decision 2026-10-16-m15 123 (d))")
            lines.append(f"run: workers claude_fallback {str(w.claude_fallback).lower()}, "
                         f"request timeout {w.request_timeout_seconds:g} s")
    history = config_dir / "HISTORY.toml"
    changes = load_changes(history) if history.is_file() else ()
    lines.append(f"history: {len(changes)} changes")
    return CheckReport(lines=tuple(lines), unverified=tuple(unverified),
                       warnings=tuple(warnings))
