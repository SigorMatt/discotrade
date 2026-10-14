"""The replay (DESIGN 16.4; decisions 2026-10-12 19, 51, 55, 72; I-6, I-12).

``replay(state_dir, config_dir, track, first, last)`` runs, for each trading
day ``D`` of the track (decision 51: the union of its instruments' trading
dates) from ``first`` to ``last`` in ascending order, the day function of
``run-day`` (``daily.run_day``) for ``D`` with the injected clock fixed at
``close_instant(D)``: the instant at which the last expected bar of ``D``
among the track's instruments closes. Each day takes and releases the state's
lock as ``run-day`` does; a day that fails stops the replay, the days before
it staying committed. A day already journaled is a re-run and writes nothing
(I-6); a day after a gap in the journal is refused as ``run-day`` refuses it.

Scripted candidates (decision 73; DESIGN 10.3, 16.1 step 5; decisions 48, 63):
``read_candidates(path, symbols)`` reads a JSON lines file whose lines each
hold exactly the keys ``CANDIDATE_KEYS`` (``day``, ``source``, ``params``,
``cell``, ``model_id``, ``model_version``, ``cutoff``, ``description``,
``profile_version``, ``metrics_t`` and ``adjusted_t``), ``source`` being the
path, relative to the repository, of a file under its ``reference/`` or
``tests/fixtures/`` (decision 48). ``adjusted_t`` (decision 2026-10-14 86
(a)) is a JSON object holding exactly ``ADJUSTED_KEYS``: ``sharpe``,
``sharpe_2x``, ``total_return`` and ``total_return_2x``, each a finite number
or ``null`` (not a number), and ``avg_position``, an object mapping exactly
each of ``symbols`` (the track's instrument symbols) to a finite number (a
JSON ``true`` or ``false`` is not a number). A file with two candidates for
one day, a line missing a key (or holding another, or a value of the wrong
kind: the design is silent, the simplest reading of "holds" is "holds
exactly"), or a source outside those directories is refused
(``CandidatesError``) before any day runs. On a day ``D`` with a candidate,
``replay`` hands ``run_day`` a ``lifecycle.Candidate`` whose T trading days
are those DESIGN 4.1 gives for ``D`` (the track's trading dates in
``Track.windows(D).t``), with its ``adjusted_t``, no grid, no W metrics and
no ``adjusted_w``; ``run_day`` admits or refuses it after lifecycle steps 1
to 4 of ``D``. A candidate dated on a day the replay does not run is never
used (the design is silent; nothing reads it).

No wall clock is read (I-12): every instant comes from the calendars.
"""

from __future__ import annotations

import dataclasses
import json
import math
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from discotrade.bars.gaps import day_end
from discotrade.clock import FixedClock
from discotrade.config import Calendar, TrackConfig
from discotrade.daily import DayRun, is_trading_day, run_day
from discotrade.journal import REPO_ROOT, TRUSTED_DIRS
from discotrade.lifecycle import Candidate
from discotrade.stats import trading_dates
from discotrade.tradingcal import expected_bars

#: The keys of a line of a candidates file (decision 2026-10-12 73).
CANDIDATE_KEYS = ("adjusted_t", "cell", "cutoff", "day", "description", "metrics_t",
                  "model_id", "model_version", "params", "profile_version", "source")
#: The keys of a line's ``adjusted_t`` (decision 2026-10-14 86 (a)).
ADJUSTED_FIGURES = ("sharpe", "sharpe_2x", "total_return", "total_return_2x")
ADJUSTED_KEYS = (*ADJUSTED_FIGURES, "avg_position")
_TEXT_KEYS = ("cell", "description", "model_id", "model_version", "profile_version")


class CandidatesError(ValueError):
    """A candidates file refused before any day runs; the command exits 2."""


def _source(where: str, value: Any, root: Path) -> str:
    if not isinstance(value, str) or not value:
        raise CandidatesError(f"{where}: source must be a path under the repository's "
                              f"{' or '.join(d + '/' for d in TRUSTED_DIRS)}")
    path = (root / value).resolve()
    inside = any(path.is_relative_to((root / d).resolve()) for d in TRUSTED_DIRS)
    if not inside or not path.is_file():
        raise CandidatesError(
            f"{where}: source {value} is not a file under the repository's "
            f"{' or '.join(d + '/' for d in TRUSTED_DIRS)} (decision 2026-10-12 48)")
    return path.read_bytes().decode("utf-8")


def _is_number(value: Any) -> bool:
    return (isinstance(value, int | float) and not isinstance(value, bool)
            and math.isfinite(value))


def _adjusted(where: str, value: Any, symbols: Sequence[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(ADJUSTED_KEYS):
        raise CandidatesError(f"{where}: adjusted_t must be a JSON object holding exactly "
                              f"{', '.join(ADJUSTED_KEYS)} (decision 2026-10-14 86)")
    for key in ADJUSTED_FIGURES:
        if value[key] is not None and not _is_number(value[key]):
            raise CandidatesError(f"{where}: adjusted_t {key} must be a number or null")
    held = value["avg_position"]
    if not isinstance(held, dict) or set(held) != set(symbols):
        raise CandidatesError(f"{where}: adjusted_t avg_position must be a JSON object "
                              f"mapping exactly the track's symbols {', '.join(symbols)}")
    for symbol in sorted(held):
        if not _is_number(held[symbol]):
            raise CandidatesError(f"{where}: adjusted_t avg_position {symbol} must be a "
                                  f"number")
    return value


def _candidate(where: str, line: Any, root: Path,
               symbols: Sequence[str]) -> tuple[date, Candidate]:
    if not isinstance(line, dict):
        raise CandidatesError(f"{where}: not a JSON object")
    missing = [k for k in CANDIDATE_KEYS if k not in line]
    if missing:
        raise CandidatesError(f"{where}: missing {', '.join(missing)}")
    extra = sorted(set(line) - set(CANDIDATE_KEYS))
    if extra:
        raise CandidatesError(f"{where}: unknown {', '.join(extra)}")
    try:
        day = date.fromisoformat(line["day"])
        cutoff = date.fromisoformat(line["cutoff"])
    except (TypeError, ValueError) as exc:
        raise CandidatesError(f"{where}: day and cutoff must be YYYY-MM-DD: {exc}") from None
    for key in _TEXT_KEYS:
        if not isinstance(line[key], str):
            raise CandidatesError(f"{where}: {key} must be a string")
    if not isinstance(line["params"], dict):
        raise CandidatesError(f"{where}: params must be a JSON object")
    metrics = line["metrics_t"]
    if not (isinstance(metrics, dict) and "sharpe" in metrics and "trades" in metrics):
        raise CandidatesError(f"{where}: metrics_t must be a JSON object holding sharpe "
                              f"and trades")
    adjusted = _adjusted(where, line["adjusted_t"], symbols)
    source = _source(where, line["source"], root)
    return day, Candidate(
        source=source, params=line["params"], cell=line["cell"], model_id=line["model_id"],
        model_version=line["model_version"], cutoff=cutoff, description=line["description"],
        profile_version=line["profile_version"], metrics_t=metrics, adjusted_t=adjusted,
        t_days=())


def read_candidates(path: Path, symbols: Sequence[str],
                    root: Path = REPO_ROOT) -> dict[date, Candidate]:
    """The candidates of a JSON lines file by day (decisions 2026-10-12 73,
    2026-10-14 86), ``symbols`` the track's instrument symbols;
    ``CandidatesError`` for a file that is refused."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CandidatesError(f"{path}: cannot read it: {exc}") from None
    out: dict[date, Candidate] = {}
    for n, raw in enumerate(text.splitlines(), start=1):
        where = f"{path}, line {n}"
        if not raw.strip():
            raise CandidatesError(f"{where}: empty line")
        try:
            line = json.loads(raw)
        except ValueError as exc:
            raise CandidatesError(f"{where}: not JSON: {exc}") from None
        day, candidate = _candidate(where, line, root, symbols)
        if day in out:
            raise CandidatesError(f"{where}: a second candidate for {day.isoformat()}")
        out[day] = candidate
    return out


def t_days(tc: TrackConfig, calendars: Mapping[str, Calendar], day: date) -> tuple[date, ...]:
    """T's trading days for ``day`` (DESIGN 4.1): the track's trading dates in
    the ``t_days`` calendar days ending with ``day``."""
    window = tc.track.windows(day).t
    cals = [calendars[name] for name in sorted({inst.calendar for inst in tc.instruments})]
    return tuple(trading_dates(cals, tc.track.bar_seconds, window.first, window.last))


def close_instant(tc: TrackConfig, calendars: Mapping[str, Calendar], day: date) -> datetime:
    """The instant at which the last expected bar of ``day`` among the
    track's instruments closes (its open plus the bar length)."""
    bar = tc.track.bar_seconds
    closes = []
    for name in sorted({inst.calendar for inst in tc.instruments}):
        cal = calendars[name]
        bars = expected_bars(cal, day_end(cal, day - timedelta(days=1)), day_end(cal, day), bar)
        if bars:
            closes.append(bars[-1] + timedelta(seconds=bar))
    if not closes:
        raise ValueError(f"{day.isoformat()} is not a trading day of {tc.track.name}")
    return max(closes)


def replay_days(tc: TrackConfig, calendars: Mapping[str, Calendar], first: date,
                last: date) -> Iterator[tuple[date, datetime]]:
    """Each trading day of the track from ``first`` to ``last``, both
    included, in ascending order, with its ``close_instant``."""
    d = first
    while d <= last:
        if is_trading_day(tc, calendars, d):
            yield d, close_instant(tc, calendars, d)
        d += timedelta(days=1)


class DayFailed(RuntimeError):
    """A replayed day failed; ``day`` names it and ``__cause__`` says why."""

    def __init__(self, day: date, instant: datetime, cause: Exception) -> None:
        super().__init__(f"{day.isoformat()} (clock {instant.isoformat()}): {cause}")
        self.day = day
        self.instant = instant


def replay(state_dir: Path, config_dir: Path, track: str, tc: TrackConfig,
           calendars: Mapping[str, Calendar], first: date, last: date,
           on_day: Callable[[DayRun, datetime], None],
           failures: tuple[type[Exception], ...],
           candidates: Mapping[date, Candidate] | None = None) -> int:
    """Run every day of ``replay_days``, with its scripted candidate if any;
    call ``on_day`` after each success. An exception of a type in
    ``failures`` stops the replay as ``DayFailed``. Return the number of days
    run."""
    count = 0
    for d, instant in replay_days(tc, calendars, first, last):
        candidate = None if candidates is None else candidates.get(d)
        if candidate is not None:
            candidate = dataclasses.replace(candidate, t_days=t_days(tc, calendars, d))
        try:
            done = run_day(state_dir, config_dir, track, FixedClock(instant), d,
                           candidate=candidate)
        except failures as exc:
            raise DayFailed(d, instant, exc) from exc
        on_day(done, instant)
        count += 1
    return count
