"""The independent calculation of gate item G0.1 (DESIGN 18.3).

A plain loop written from DESIGN 5.3, 5.6, 6.2, 7 and 8 and from items 22
to 26, 29, 30, 36, 37 and 39 of meta/decisions/decisions-2026-10-12.md
alone. It imports nothing from ``discotrade`` (the standard library,
``numpy``, ``pandas``, ``pyarrow`` and ``tomllib`` only, decision 39): it
reads the stored month Parquet files, the roll records and the track,
instrument, calendar and spread TOML files itself. The strategy reaches it
only as a callable ``position(bars, params)`` and its ``PARAMS``.

``calculate(state, config, track, start, end, position, params)`` returns a
``Result``: per instrument, one row per window bar (``ts``, ``contract``,
``date``, ``p``, ``h``, ``gross``, ``trade``, ``fee``, ``spread``,
``slippage``, ``roll``, ``cost``, ``net_1x``, ``net_2x``); the subject's
trading days and its daily series at 1x and 2x (decision 23); every
metric of DESIGN 8 (decisions 25 and 30); and the cost totals by
component, the subject's (summed over bars, divided by ``N``, decision 38)
and each instrument's undivided sum.

Choices where the documents are silent (the simplest thing):

- ``trusted_from`` is a date; a bar is trusted when its ``ts`` is not
  before that date's midnight UTC.
- A bar is in the main session when its open time, in the calendar's time
  zone, falls on Monday to Friday, outside every closure, at or after the
  session's start and before its end.
- A bar's trading date: the local date of its open time, plus one day when
  the local time of day is at or after ``day_rolls_at``; for an
  ``always_open`` calendar, the UTC date (the calendar's time zone is then
  UTC for ``hour``, ``weekday``, the spread hour and the main session).
- ``max_drawdown`` is the largest ``max(cum[:j+1]) - cum[j]`` over the
  running sum ``cum`` of the daily series (no leading zero), and 0.0 for
  an empty series.
- A position is non-zero when it is not exactly 0.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import tomllib
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

#: DESIGN 8: a bar is a trade when ``trade(u) > TRADE_FLOOR``.
TRADE_FLOOR = 1e-9
#: Decision 30: the relative tolerance under which a deviation is 0.
STD_TOLERANCE = 1e-12
#: DESIGN 7.3: sigma uses the last 24 returns.
SIGMA_RETURNS = 24
#: DESIGN 8: Sharpe is annualised with 252 trading days (R-7).
TRADING_DAYS = 252
MONTH_FILE = re.compile(r"^\d{4}-\d{2}\.parquet$")
COMPONENTS = ("fee", "spread", "slippage", "roll")
NAN = float("nan")


class CalcError(Exception):
    """The evaluation cannot go on (decisions 22, 24, 37)."""


@dataclass
class Result:
    rows: dict[str, list[dict]]
    days: list[dt.date]
    daily_1x: list[float]
    daily_2x: list[float]
    metrics: dict[str, float | int | bool]
    costs: dict[str, float]
    costs_by_instrument: dict[str, dict[str, float]] = field(default_factory=dict)


# ---------------------------------------------------------------- reading


def _toml(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _date(value) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def _hhmm(text: str) -> int:
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


class Calendar:
    """The parts of a DESIGN 5.3 calendar record this calculation needs."""

    def __init__(self, record: dict):
        self.always_open = bool(record.get("always_open", False))
        if self.always_open:
            self.tz = ZoneInfo("UTC")
            self.rolls_at = 0
            self.closures: list[tuple[dt.datetime, dt.datetime]] = []
            return
        self.tz = ZoneInfo(record["tz"])
        self.rolls_at = _hhmm(record["day_rolls_at"])
        self.closures = []
        for closure in record.get("closure", []):
            start = dt.datetime.strptime(closure["start"], "%Y-%m-%d %H:%M")
            end = dt.datetime.strptime(closure["end"], "%Y-%m-%d %H:%M")
            self.closures.append(
                (start.replace(tzinfo=self.tz), end.replace(tzinfo=self.tz))
            )

    def local(self, ts: pd.Timestamp) -> dt.datetime:
        return ts.to_pydatetime().astimezone(self.tz)

    def trading_date(self, ts: pd.Timestamp) -> dt.date:
        local = self.local(ts)
        if self.always_open:
            return local.date()
        if local.hour * 60 + local.minute >= self.rolls_at:
            return local.date() + dt.timedelta(days=1)
        return local.date()

    def closed(self, local: dt.datetime) -> bool:
        return any(start <= local < end for start, end in self.closures)


@dataclass
class Instrument:
    symbol: str
    calendar: Calendar
    shorting: bool
    trusted_from: pd.Timestamp
    tick_size: float
    main_session: tuple[int, int]
    fee_per_side: float | None
    multiplier: float | None
    fee_bps: float | None
    spread_main: float
    spread_off: float
    slippage_coef: float
    spread_table: list[float] | None


def _instrument(config: Path, symbol: str) -> Instrument:
    record = _toml(config / "instruments" / f"{symbol}.toml")
    cost = record["cost"]
    calendar = Calendar(_toml(config / "calendars" / f"{record['calendar']}.toml"))
    spread_file = config / "spreads" / f"{symbol}.toml"
    table = None
    if spread_file.exists():
        table = [float(x) for x in _toml(spread_file)["spread_ticks"]]
        if len(table) != 24:
            raise CalcError(f"{symbol}: spread table has {len(table)} values, not 24")
    trusted = _date(record["trusted_from"])
    return Instrument(
        symbol=symbol,
        calendar=calendar,
        shorting=bool(record["shorting"]),
        trusted_from=pd.Timestamp(trusted.isoformat(), tz="UTC"),
        tick_size=float(record["tick_size"]),
        main_session=(_hhmm(record["main_session"][0]), _hhmm(record["main_session"][1])),
        fee_per_side=float(cost["fee_per_side"]) if "fee_per_side" in cost else None,
        multiplier=float(record["multiplier"]) if "multiplier" in record else None,
        fee_bps=float(cost["fee_bps"]) if "fee_bps" in cost else None,
        spread_main=float(cost["spread_ticks_main"]),
        spread_off=float(cost["spread_ticks_off"]),
        slippage_coef=float(cost["slippage_coef"]),
        spread_table=table,
    )


def _bars(state: Path, track: str, symbol: str) -> pd.DataFrame:
    """Every stored bar of ``symbol``, sorted by ``ts`` (UTC)."""
    folder = state / "bars" / track / symbol
    files = sorted(p for p in folder.glob("*.parquet") if MONTH_FILE.match(p.name))
    columns = ["ts", "open", "high", "low", "close", "volume", "contract"]
    if not files:
        return pd.DataFrame({c: [] for c in columns})
    frames = [pq.read_table(p).to_pandas() for p in files]
    bars = pd.concat(frames, ignore_index=True)[columns]
    bars["ts"] = pd.to_datetime(bars["ts"], utc=True)
    bars = bars.sort_values("ts", kind="stable").reset_index(drop=True)
    if bars["ts"].duplicated().any():
        raise CalcError(f"{symbol}: duplicate ts in the stored bars")
    return bars


def _rolls(state: Path, track: str, symbol: str) -> list[dict]:
    path = state / "rolls" / track / f"{symbol}.jsonl"
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            record["ts"] = pd.Timestamp(record["ts"]).tz_convert("UTC")
            records.append(record)
    return records


# ---------------------------------------------------------------- the loop


def _check_target(value, symbol: str, ts: pd.Timestamp) -> float:
    """Decision 22: a real finite number within [-1, 1], or an error."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (Real, np.integer,
                                                                     np.floating)):
        raise CalcError(f"{symbol} at {ts.isoformat()}: position returned {value!r}, "
                        "not a real number")
    number = float(value)
    if not math.isfinite(number) or number < -1.0 or number > 1.0:
        raise CalcError(f"{symbol} at {ts.isoformat()}: position returned {number!r}, "
                        "not a finite number within [-1, 1]")
    return number


def _spread_ticks(inst: Instrument, ts: pd.Timestamp) -> float:
    """DESIGN 5.7: the table's value for the local hour, else main or off session."""
    local = inst.calendar.local(ts)
    if inst.spread_table is not None:
        return inst.spread_table[local.hour]
    minute = local.hour * 60 + local.minute
    start, end = inst.main_session
    main = (local.weekday() < 5 and not inst.calendar.closed(local)
            and start <= minute < end)
    return inst.spread_main if main else inst.spread_off


def _evaluate(inst: Instrument, bars: pd.DataFrame, rolls: list[dict],
              start: dt.date, end: dt.date, cap: int, position, params) -> list[dict]:
    symbol = inst.symbol
    # Decision 36: no bar before trusted_from is read for a result.
    bars = bars[bars["ts"] >= inst.trusted_from].reset_index(drop=True)
    n = len(bars)
    ts = list(bars["ts"])
    o = [float(x) for x in bars["open"]]
    hi = [float(x) for x in bars["high"]]
    lo = [float(x) for x in bars["low"]]
    c = [float(x) for x in bars["close"]]
    vol = [float(x) for x in bars["volume"]]
    contract = [str(x) for x in bars["contract"]]
    dates = [inst.calendar.trading_date(t) for t in ts]
    window = [i for i in range(n) if start <= dates[i] <= end]
    if not window:
        return []
    last = window[-1]

    # Rolls (DESIGN 5.6, decisions 24, 37): gap[i] is the gap of the roll at
    # bar i, 0.0 where there is none; cum[i] is the sum of gaps up to bar i.
    gap = [0.0] * n
    is_roll = [False] * n
    for i in range(1, last + 1):
        if contract[i] != contract[i - 1]:
            match = [r for r in rolls if r["ts"] == ts[i]
                     and r["old"] == contract[i - 1] and r["new"] == contract[i]]
            if not match:
                raise CalcError(
                    f"{symbol} at {ts[i].isoformat()}: contract changes from "
                    f"{contract[i - 1]} to {contract[i]} and no roll record matches; "
                    "run bars fetch")
            gap[i] = float(match[0]["gap"])
            is_roll[i] = True
    cum = []
    total = 0.0
    for i in range(n):
        total += gap[i]
        cum.append(total)

    def adjusted(prices: list[float], s: int, t: int) -> float:
        """Price of bar s adjusted as of bar t: plus the gaps of rolls in (s, t]."""
        return prices[s] + (cum[t] - cum[s])

    # Returns r(s) for s >= 1, adjusted as of s, over the raw previous close.
    ret = [NAN] * n
    for s in range(1, n):
        ret[s] = (adjusted(c, s, s) - adjusted(c, s - 1, s)) / c[s - 1]

    def sigma(u: int) -> float:
        recent = [ret[s] for s in range(max(1, u - SIGMA_RETURNS), u)]
        if len(recent) < 2:
            return 0.0
        mean = sum(recent) / len(recent)
        return math.sqrt(sum((x - mean) ** 2 for x in recent) / (len(recent) - 1))

    rows: list[dict] = []
    first = window[0]
    p_prev = 0.0
    h_prev = 0.0
    for u in window:
        # The slice of DESIGN 6.2 ending at u.
        lo_i = max(0, u - cap + 1)
        idx = range(lo_i, u + 1)
        locals_ = [inst.calendar.local(ts[s]) for s in idx]
        frame = pd.DataFrame({
            "open": [adjusted(o, s, u) for s in idx],
            "high": [adjusted(hi, s, u) for s in idx],
            "low": [adjusted(lo, s, u) for s in idx],
            "close": [adjusted(c, s, u) for s in idx],
            "volume": [vol[s] for s in idx],
            "hour": [x.hour for x in locals_],
            "weekday": [x.weekday() for x in locals_],
        })
        try:
            raw = position(frame, dict(params))
        except Exception as exc:  # noqa: BLE001 - decision 22: any raise ends it
            raise CalcError(f"{symbol} at {ts[u].isoformat()}: position raised "
                            f"{type(exc).__name__}: {exc}") from exc
        p = _check_target(raw, symbol, ts[u])
        if p < 0 and not inst.shorting:
            p = 0.0

        h = 0.0 if u == first else p_prev
        if u == first:
            gross = 0.0
            trade = 0.0
            rolled = False
        else:
            oa = adjusted(o, u, u)
            ca = adjusted(c, u, u)
            ca_prev = adjusted(c, u - 1, u)
            gross = (h_prev * (oa - ca_prev) + h * (ca - oa)) / o[u]
            trade = abs(h - h_prev)
            rolled = is_roll[u]
        if inst.fee_bps is not None:
            fee_u = inst.fee_bps / 10000.0
        else:
            fee_u = inst.fee_per_side / (inst.multiplier * o[u])
        half_spread_u = max(_spread_ticks(inst, ts[u]) / 2.0, 0.5) * inst.tick_size / o[u]
        slip_u = inst.slippage_coef * sigma(u)
        c_u = fee_u + half_spread_u + slip_u
        roll_cost = 2.0 * abs(h_prev) * c_u if rolled else 0.0
        fee = trade * fee_u
        spread = trade * half_spread_u
        slippage = trade * slip_u
        cost = fee + spread + slippage + roll_cost
        rows.append({
            "ts": ts[u], "contract": contract[u], "date": dates[u],
            "p": p, "h": h, "gross": gross, "trade": trade,
            "fee": fee, "spread": spread, "slippage": slippage, "roll": roll_cost,
            "cost": cost, "net_1x": gross - cost, "net_2x": gross - 2.0 * cost,
            "rolled_turnover": 2.0 * abs(h_prev) if rolled else 0.0,
        })
        p_prev = p
        h_prev = h
    return rows


# ---------------------------------------------------------------- metrics


def sharpe(d: list[float]) -> float:
    """DESIGN 8 with decision 30: not a number under 2 days or a deviation of 0."""
    if len(d) < 2:
        return NAN
    if all(x == d[0] for x in d):
        return NAN
    mean = sum(d) / len(d)
    std = math.sqrt(sum((x - mean) ** 2 for x in d) / (len(d) - 1))
    if not std > STD_TOLERANCE * max(abs(x) for x in d):
        return NAN
    return mean / std * math.sqrt(TRADING_DAYS)


def max_drawdown(d: list[float]) -> float:
    running = 0.0
    peak = -math.inf
    worst = 0.0
    for x in d:
        running += x
        peak = max(peak, running)
        worst = max(worst, peak - running)
    return worst


def avg_holding_bars(positions: list[list[float]]) -> float:
    runs = []
    for series in positions:
        length = 0
        sign = 0
        for h in series:
            s = (h > 0) - (h < 0)
            if s != 0 and s == sign:
                length += 1
                continue
            if sign != 0:
                runs.append(length)
            sign = s
            length = 1 if s != 0 else 0
        if sign != 0:
            runs.append(length)
    if not runs:
        return NAN
    return sum(runs) / len(runs)


def metrics(rows: dict[str, list[dict]], d1: list[float], d2: list[float]) -> dict:
    total_1x = sum(d1)
    total_2x = sum(d2)
    every = [r for symbol in rows for r in rows[symbol]]
    gross = sum(r["gross"] for r in every)
    turnover = sum(r["trade"] for r in every) + sum(r["rolled_turnover"] for r in every)
    return {
        "total_return": total_1x,
        "total_return_2x": total_2x,
        "sharpe": sharpe(d1),
        "sharpe_2x": sharpe(d2),
        "max_drawdown": max_drawdown(d1),
        "trades": sum(1 for r in every if r["trade"] > TRADE_FLOOR),
        "avg_holding_bars": avg_holding_bars([[r["h"] for r in rows[s]] for s in rows]),
        "breakeven_cost": gross / turnover * 10000.0 if turnover > 0 else NAN,
        "fragile": total_1x > 0 and total_2x < 0,
    }


# ---------------------------------------------------------------- entry


def calculate(state, config, track: str, start, end, position, params) -> Result:
    """Evaluate ``position`` with ``params`` on every instrument of ``track``."""
    state = Path(state)
    config = Path(config)
    start = _date(start)
    end = _date(end)
    track_record = _toml(config / "tracks" / f"{track}.toml")
    cap = int(track_record["history_cap_bars"])
    symbols = list(track_record["instruments"])
    rows: dict[str, list[dict]] = {}
    for symbol in symbols:
        inst = _instrument(config, symbol)
        rows[symbol] = _evaluate(inst, _bars(state, track, symbol),
                                 _rolls(state, track, symbol), start, end, cap, position, params)

    n = len(symbols)
    days = sorted({r["date"] for symbol in symbols for r in rows[symbol]})
    d1 = []
    d2 = []
    for day in days:
        s1 = 0.0
        s2 = 0.0
        for symbol in symbols:
            s1 += sum(r["net_1x"] for r in rows[symbol] if r["date"] == day)
            s2 += sum(r["net_2x"] for r in rows[symbol] if r["date"] == day)
        d1.append(s1 / n)
        d2.append(s2 / n)

    by_instrument = {
        symbol: {k: sum(r[k] for r in rows[symbol]) for k in COMPONENTS}
        for symbol in symbols
    }
    costs = {k: sum(by_instrument[s][k] for s in symbols) / n for k in COMPONENTS}
    return Result(rows=rows, days=days, daily_1x=d1, daily_2x=d2,
                  metrics=metrics(rows, d1, d2), costs=costs,
                  costs_by_instrument=by_instrument)
