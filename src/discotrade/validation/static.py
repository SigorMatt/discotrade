"""The static check (DESIGN 12.1; decision 94 of 2026-10-14-m12; R-24; I-10).

Runs on a strategy's source text with :mod:`ast`, before anything executes
it, and returns ``None`` when the text passes or the first failure as a
:class:`Refusal` (a rule name from :data:`RULES` and a message). The rules
are checked in the order 12.1 lists them, which is the order of
:data:`RULES`; within a rule the first offending node in source order is
named (an attribute by where its name begins, decision 101 (d) of
2026-10-14-m13). The numbers come from ``config/thresholds.toml`` (``validation.*``,
I-10). Lines are physical lines (R-24).

Two readings of decision 94 made here, each the simplest that leaves no gap:
a name in ``from numpy import name`` is an attribute of the module, so the
attribute rules apply to it (``from numpy import load`` is ``numpy.load``),
and ``from <module> import *``, which binds names the check cannot see, is
refused by the import rule. A ``PARAMS``, ``GRID`` or ``position`` bound
anywhere else in the text counts as a second assignment.
"""

from __future__ import annotations

import ast
import math
from collections.abc import Iterator
from dataclasses import dataclass

from discotrade.config import Thresholds
from discotrade.strategy import Limits

#: Every rule, in the order of DESIGN 12.1.
RULES: tuple[str, ...] = (
    "parse", "max_lines",
    "params", "max_params", "param_key", "param_value",
    "grid", "grid_value", "grid_key", "grid_max_params", "grid_max_values",
    "position", "import", "construct", "underscore", "forbidden_name",
    "forbidden_attribute",
)

#: The modules a strategy may import (decision 94 (e)).
MODULES: tuple[str, ...] = ("numpy", "pandas", "indicators")

#: The forbidden names of DESIGN 12.1, for every identifier bound or read.
FORBIDDEN_NAMES: tuple[str, ...] = (
    "eval", "exec", "compile", "open", "input", "breakpoint", "globals", "locals", "vars",
    "dir", "getattr", "setattr", "delattr", "type", "object", "super", "memoryview",
    "exit", "quit", "help", "print",
)

#: The forbidden attributes of DESIGN 12.1.
FORBIDDEN_ATTRIBUTES: tuple[str, ...] = (
    "eval", "query", "pipe", "system", "popen", "load", "loads", "save", "savez",
    "loadtxt", "savetxt", "genfromtxt", "fromfile", "tofile", "memmap", "ctypeslib",
    "random", "default_rng", "RandomState", "now", "today", "time", "datetime", "testing",
    "f2py", "distutils",
)

#: Attribute prefixes refused, and the one attribute they spare (DESIGN 12.1).
FORBIDDEN_PREFIXES: tuple[str, ...] = ("read_", "to_")
ALLOWED_PREFIXED: tuple[str, ...] = ("to_numpy",)


@dataclass(frozen=True)
class Refusal:
    """The first rule a text breaks; ``line`` is its line, ``None`` for the whole text."""

    rule: str
    message: str
    line: int | None = None


class _Refused(Exception):
    def __init__(self, rule: str, message: str, node: ast.AST | None = None) -> None:
        line = getattr(node, "lineno", None) if node is not None else None
        text = f"line {line}: {message}" if line is not None else message
        self.refusal = Refusal(rule=rule, message=text, line=line)


def check(source: str, thresholds: Thresholds) -> Refusal | None:
    """``None`` when ``source`` passes every rule of 12.1, else the first :class:`Refusal`."""
    limits = Limits.from_thresholds(thresholds)
    try:
        _check(source, limits)
    except _Refused as refused:
        return refused.refusal
    return None


def physical_lines(source: str) -> int:
    """The number of physical lines of ``source`` (R-24): a last newline ends a line."""
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _check(source: str, limits: Limits) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise _Refused("parse", f"the text does not parse: line {e.lineno}: {e.msg}") from None
    except (ValueError, RecursionError, MemoryError) as e:
        raise _Refused("parse", f"the text does not parse: {e}") from None
    lines = physical_lines(source)
    if lines > limits.max_lines:
        raise _Refused("max_lines", f"the text has {lines} lines; at most {limits.max_lines} "
                                    "are allowed")
    keys = _check_params(tree, limits)
    _check_grid(tree, keys, limits)
    _check_position(tree)
    _check_imports(tree)
    _check_constructs(tree)
    names, attributes = _identifiers(tree)
    for node, name, kind in sorted(names + attributes, key=_order):
        if name.startswith("_"):
            raise _Refused("underscore", f"the {kind} {name!r} begins with an underscore", node)
    for node, name, kind in sorted(names, key=_order):
        if name in FORBIDDEN_NAMES:
            raise _Refused("forbidden_name", f"the {kind} {name!r} is not allowed", node)
    for node, name, kind in sorted(attributes, key=_order):
        if name in FORBIDDEN_ATTRIBUTES or (
            name.startswith(FORBIDDEN_PREFIXES) and name not in ALLOWED_PREFIXED
        ):
            raise _Refused("forbidden_attribute", f"the {kind} {name!r} is not allowed", node)


# --- source order ------------------------------------------------------------------


def _position(node: ast.AST) -> tuple[int, int]:
    return getattr(node, "lineno", 0), getattr(node, "col_offset", 0)


def _walk(tree: ast.AST) -> Iterator[ast.AST]:
    """Every node of ``tree`` in source order (a stable sort of :func:`ast.walk`)."""
    nodes = list(ast.walk(tree))
    order = sorted(range(len(nodes)), key=lambda i: (_position(nodes[i]), i))
    return (nodes[i] for i in order)


def _order(item: tuple[ast.AST, str, str]) -> tuple[int, int]:
    """Where an identifier's name begins: for an attribute, the name after the dot
    (decision 101 (d) of 2026-10-14-m13), so that of a chain such as
    ``np.load(1).to_csv(2)`` the first name in the source is named; for any other
    node, the node's start."""
    node, name, _ = item
    if isinstance(node, ast.Attribute) and node.end_lineno is not None:
        # The name is the node's last token; offsets count UTF-8 bytes.
        return node.end_lineno, (node.end_col_offset or 0) - len(name.encode("utf-8"))
    return _position(node)


# --- PARAMS and GRID ----------------------------------------------------------------


def _bound_names(node: ast.AST) -> list[str]:
    """The names ``node`` binds in its scope."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
        return [node.id]
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return [node.name]
    if isinstance(node, ast.Import):
        return [a.asname or a.name.split(".")[0] for a in node.names]
    if isinstance(node, ast.ImportFrom):
        return [a.asname or a.name for a in node.names]
    if isinstance(node, ast.ExceptHandler | ast.MatchAs | ast.MatchStar) and node.name:
        return [node.name]
    if isinstance(node, ast.MatchMapping) and node.rest:
        return [node.rest]
    if type(node).__name__ in ("TypeVar", "ParamSpec", "TypeVarTuple"):   # Python 3.12
        return [node.name]  # type: ignore[attr-defined]
    return []


def _bindings(tree: ast.Module, name: str) -> list[ast.AST]:
    return [node for node in _walk(tree) if name in _bound_names(node)]


def _literal(tree: ast.Module, name: str, rule: str, required: bool) -> ast.Dict | None:
    """The dict literal of the one plain module-level ``name = {...}``, else a refusal."""
    binds = _bindings(tree, name)
    if not binds:
        if required:
            raise _Refused(rule, f"no module-level {name} dict literal")
        return None
    if len(binds) > 1:
        raise _Refused(rule, f"{name} is assigned {len(binds)} times; it must be assigned "
                             "exactly once", binds[1])
    for stmt in tree.body:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and stmt.targets[0] is binds[0]):
            if not isinstance(stmt.value, ast.Dict):
                raise _Refused(rule, f"{name} is not a dict literal", stmt)
            return stmt.value
    raise _Refused(rule, f"{name} must be assigned once, at module level, by a plain "
                         f"`{name} = {{...}}`", binds[0])


def _numeric(node: ast.expr) -> bool:
    """An int or float literal, or unary minus applied to one; never a bool."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return (isinstance(node, ast.Constant) and type(node.value) in (int, float)
            and math.isfinite(node.value))


def _check_params(tree: ast.Module, limits: Limits) -> list[str]:
    params = _literal(tree, "PARAMS", "params", required=True)
    assert params is not None
    if len(params.keys) > limits.max_params:
        raise _Refused("max_params", f"PARAMS has {len(params.keys)} entries; at most "
                                     f"{limits.max_params} are allowed", params)
    keys: list[str] = []
    for key in params.keys:
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            raise _Refused("param_key", "every PARAMS key must be a string literal",
                           key or params)
        keys.append(key.value)
    for key_name, value in zip(keys, params.values, strict=True):
        if not _numeric(value):
            raise _Refused("param_value", f"PARAMS value for {key_name!r} is not an int or "
                                          "float literal", value)
    return keys


def _check_grid(tree: ast.Module, keys: list[str], limits: Limits) -> None:
    grid = _literal(tree, "GRID", "grid", required=False)
    if grid is None:
        return
    for value in grid.values:
        if not (isinstance(value, ast.List) and value.elts):
            raise _Refused("grid", "every GRID value must be a non-empty list literal", value)
    for value in grid.values:
        assert isinstance(value, ast.List)
        for element in value.elts:
            if not _numeric(element):
                raise _Refused("grid_value", "every GRID value must be an int or float literal",
                               element)
    names: list[str] = []
    for key in grid.keys:
        if not (isinstance(key, ast.Constant) and key.value in keys):
            shown = repr(key.value) if isinstance(key, ast.Constant) else "a key"
            raise _Refused("grid_key", f"GRID names {shown}, which is not a key of PARAMS",
                           key or grid)
        names.append(key.value)
    if len(grid.keys) > limits.grid_max_params:
        raise _Refused("grid_max_params", f"GRID has {len(grid.keys)} parameters; at most "
                                          f"{limits.grid_max_params} are allowed", grid)
    for key_name, value in zip(names, grid.values, strict=True):
        assert isinstance(value, ast.List)
        if len(value.elts) > limits.grid_max_values:
            raise _Refused("grid_max_values", f"GRID gives {key_name!r} {len(value.elts)} "
                                              f"values; at most {limits.grid_max_values} are "
                                              "allowed", value)


# --- position, imports, constructs -------------------------------------------------


def _check_position(tree: ast.Module) -> None:
    binds = _bindings(tree, "position")
    defs = [s for s in tree.body if isinstance(s, ast.FunctionDef) and s.name == "position"]
    if len(binds) != 1 or len(defs) != 1 or binds[0] is not defs[0]:
        raise _Refused("position", "the text must define `position` exactly once, as a "
                                   "module-level def position(bars, params)",
                       binds[1] if len(binds) > 1 else None)
    a = defs[0].args
    if (a.posonlyargs or a.vararg or a.kwarg or a.kwonlyargs or a.defaults
            or [p.arg for p in a.args] != ["bars", "params"]):
        raise _Refused("position", "position must be def position(bars, params): two "
                                   "parameters, no default, no *args or **kwargs", defs[0])


def _check_imports(tree: ast.Module) -> None:
    allowed = ", ".join(MODULES)
    for node in _walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in MODULES:
                    raise _Refused("import", f"import {alias.name} is refused; only {allowed} "
                                             "may be imported", node)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            if node.level or node.module not in MODULES:
                raise _Refused("import", f"from {module} import is refused; only from "
                                         f"{allowed} may names be imported", node)
            if any(alias.name == "*" for alias in node.names):
                raise _Refused("import", f"from {module} import * is refused", node)


def _constructs(tree: ast.Module) -> Iterator[tuple[ast.AST, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield node, "class"
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            for decorator in node.decorator_list:
                yield decorator, "decorator"
        if isinstance(node, ast.comprehension) and node.is_async:
            yield node.target, "async"
        word = {
            ast.Global: "global", ast.Nonlocal: "nonlocal", ast.AsyncFunctionDef: "async",
            ast.AsyncFor: "async", ast.AsyncWith: "async", ast.Await: "await",
            ast.Yield: "yield", ast.YieldFrom: "yield from", ast.With: "with",
        }.get(type(node))
        if word:
            yield node, word


def _check_constructs(tree: ast.Module) -> None:
    found = sorted(_constructs(tree), key=lambda item: _position(item[0]))
    if found:
        node, word = found[0]
        raise _Refused("construct", f"`{word}` is not allowed", node)


# --- identifiers and attributes ----------------------------------------------------


def _identifiers(
    tree: ast.Module,
) -> tuple[list[tuple[ast.AST, str, str]], list[tuple[ast.AST, str, str]]]:
    """Every identifier the text binds or reads, and every attribute it names."""
    names: list[tuple[ast.AST, str, str]] = []
    attributes: list[tuple[ast.AST, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append((node, node.id, "name"))
        elif isinstance(node, ast.arg):
            names.append((node, node.arg, "parameter"))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.append((node, node.name, "function name"))
        elif isinstance(node, ast.keyword) and node.arg is not None:
            names.append((node, node.arg, "keyword argument"))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.append((alias, alias.asname or alias.name.split(".")[0], "import name"))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    attributes.append((alias, alias.name, "imported attribute"))
                    names.append((alias, alias.asname or alias.name, "import name"))
        elif isinstance(node, ast.Global | ast.Nonlocal):
            names.extend((node, name, "name") for name in node.names)
        elif isinstance(node, ast.Attribute):
            attributes.append((node, node.attr, "attribute"))
        elif isinstance(node, ast.MatchClass):
            attributes.extend((node, name, "attribute") for name in node.kwd_attrs)
        else:
            names.extend((node, name, "name") for name in _bound_names(node))
    return names, attributes
