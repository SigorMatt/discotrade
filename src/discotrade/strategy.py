"""The strategy contract, its loader and the result check (DESIGN 6.1, 6.2; I-1, I-2, I-10).

A strategy is one Python source text defining ``PARAMS``, an optional
``GRID`` and a callable ``position(bars, params)``. In step S0.3 only trusted
texts are loaded (the repository's ``reference/`` files and test fixtures;
decision 21 of meta/decisions/decisions-2026-10-12.md): the loader executes
the text in-process in a fresh namespace where ``indicators`` names
:mod:`discotrade.indicators`, both as a bound name and for ``import
indicators``. Nothing is installed in ``sys.modules``. The static check and
the sandbox (DESIGN 12) are not here.

Every shape limit is read from ``config/thresholds.toml`` (``validation.*``,
I-10); a text that breaks one is refused with a :class:`StrategyError` naming
the rule.

The result check (decision 22): a ``position`` result that is not a real
finite number within [-1, 1], or a call that raises, is a
:class:`ResultError` naming the instrument and the bar's ``ts``; nothing is
clipped or substituted. After the check, a negative result on an instrument
that does not allow shorting is clipped to 0.
"""

from __future__ import annotations

import builtins
import math
import numbers
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from discotrade import indicators
from discotrade.config import Thresholds

#: The name under which a strategy sees the indicator library (DESIGN 6.3).
INDICATORS_NAME = "indicators"


class StrategyError(ValueError):
    """A strategy text breaks a rule of the contract (DESIGN 6.1); ``rule`` names it."""

    def __init__(self, rule: str, message: str) -> None:
        self.rule = rule
        super().__init__(f"strategy refused [{rule}]: {message}")


class ResultError(ValueError):
    """A ``position`` call raised or returned a result outside the contract (decision 22)."""


@dataclass(frozen=True)
class Limits:
    """The shape limits of DESIGN 6.1, read from the thresholds file (I-10)."""

    max_params: int
    max_lines: int
    grid_max_params: int
    grid_max_values: int

    @classmethod
    def from_thresholds(cls, thresholds: Thresholds) -> Limits:
        return cls(
            max_params=thresholds["validation.max_params"],
            max_lines=thresholds["validation.max_lines"],
            grid_max_params=thresholds["validation.grid_max_params"],
            grid_max_values=thresholds["validation.grid_max_values"],
        )


@dataclass(frozen=True)
class Strategy:
    """A loaded strategy: its text, parameters, optional grid and ``position`` function."""

    name: str
    source: str
    params: dict[str, int | float]
    grid: dict[str, list[int | float]] | None
    position: Callable[..., Any]


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)
    )


def _builtins() -> dict[str, Any]:
    """A copy of the builtins whose ``__import__`` resolves ``indicators`` to the library."""
    space = dict(vars(builtins))
    real_import = builtins.__import__

    def strategy_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == INDICATORS_NAME and level == 0:
            return indicators
        return real_import(name, globals, locals, fromlist, level)

    space["__import__"] = strategy_import
    return space


def _check_params(params: Any, limits: Limits) -> dict[str, int | float]:
    if not isinstance(params, dict):
        raise StrategyError("params", "PARAMS must be a dict of parameter names to numbers")
    if len(params) > limits.max_params:
        raise StrategyError(
            "max_params",
            f"PARAMS has {len(params)} parameters; at most {limits.max_params} "
            f"(validation.max_params)",
        )
    for key, value in params.items():
        if not isinstance(key, str):
            raise StrategyError("params", f"PARAMS key {key!r} is not a string")
        if not _is_number(value):
            raise StrategyError(
                "params_numeric",
                f"PARAMS value for {key!r} is {value!r}; every parameter must be a finite "
                f"int or float",
            )
    return dict(params)


def _check_grid(grid: Any, params: Mapping[str, Any], limits: Limits) -> dict[str, list]:
    if not isinstance(grid, dict):
        raise StrategyError("grid", "GRID must be a dict of PARAMS names to lists of values")
    unknown = [key for key in grid if key not in params]
    if unknown:
        raise StrategyError(
            "grid_keys", f"GRID names {unknown[0]!r}, which is not a key of PARAMS"
        )
    if len(grid) > limits.grid_max_params:
        raise StrategyError(
            "grid_max_params",
            f"GRID has {len(grid)} parameters; at most {limits.grid_max_params} "
            f"(validation.grid_max_params)",
        )
    out = {}
    for key, values in grid.items():
        if not isinstance(values, list | tuple) or not values:
            raise StrategyError(
                "grid_values", f"GRID value for {key!r} must be a non-empty list of numbers"
            )
        if len(values) > limits.grid_max_values:
            raise StrategyError(
                "grid_max_values",
                f"GRID gives {key!r} {len(values)} values; at most {limits.grid_max_values} "
                f"(validation.grid_max_values)",
            )
        bad = [v for v in values if not _is_number(v)]
        if bad:
            raise StrategyError(
                "params_numeric",
                f"GRID value {bad[0]!r} for {key!r} is not a finite int or float",
            )
        out[key] = list(values)
    return out


def load_strategy(source: str, thresholds: Thresholds, name: str = "<strategy>") -> Strategy:
    """Check ``source`` against DESIGN 6.1 and execute it in a fresh namespace."""
    limits = Limits.from_thresholds(thresholds)
    lines = len(source.splitlines())
    if lines > limits.max_lines:
        raise StrategyError(
            "max_lines",
            f"{name} has {lines} lines; at most {limits.max_lines} (validation.max_lines)",
        )
    try:
        code = compile(source, name, "exec")
    except SyntaxError as exc:
        raise StrategyError("syntax", f"{name} does not parse: {exc}") from exc
    namespace: dict[str, Any] = {
        "__builtins__": _builtins(),
        "__name__": "strategy",
        INDICATORS_NAME: indicators,
    }
    try:
        exec(code, namespace)
    except Exception as exc:
        raise StrategyError(
            "load", f"{name} raised while loading: {type(exc).__name__}: {exc}"
        ) from exc
    if "PARAMS" not in namespace:
        raise StrategyError("params", f"{name} defines no PARAMS")
    params = _check_params(namespace["PARAMS"], limits)
    grid = _check_grid(namespace["GRID"], params, limits) if "GRID" in namespace else None
    position = namespace.get("position")
    if not callable(position):
        raise StrategyError("position", f"{name} defines no callable position(bars, params)")
    return Strategy(name=name, source=source, params=params, grid=grid, position=position)


def load_strategy_file(path: Path, thresholds: Thresholds) -> Strategy:
    """Read a strategy text from ``path`` and load it with :func:`load_strategy`."""
    path = Path(path)
    return load_strategy(path.read_text(encoding="utf-8"), thresholds, name=str(path))


def check_result(value: Any, *, instrument: str, ts: Any, shorting: bool) -> float:
    """Return ``value`` as a float if it meets DESIGN 6.2, clipped to 0 if short and not allowed."""
    where = f"position on {instrument} at bar ts {ts}"
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ResultError(f"{where} returned {value!r}, which is not a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ResultError(f"{where} returned {result!r}, which is not finite")
    if not -1.0 <= result <= 1.0:
        raise ResultError(f"{where} returned {result!r}, outside [-1, 1]")
    if result < 0.0 and not shorting:
        return 0.0
    return result


def call_position(
    position: Callable[..., Any], bars: Any, params: Mapping[str, Any], *,
    instrument: str, ts: Any, shorting: bool,
) -> float:
    """Call ``position`` with a copy of ``params`` and check its result (decision 22)."""
    try:
        value = position(bars, dict(params))
    except Exception as exc:
        raise ResultError(
            f"position on {instrument} at bar ts {ts} raised {type(exc).__name__}: {exc}"
        ) from exc
    return check_result(value, instrument=instrument, ts=ts, shorting=shorting)
