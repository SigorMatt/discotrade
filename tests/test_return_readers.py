"""O-16 and O-18: the register of return readers and its audit (decision
2026-10-14 89).

The register is ``tests/fixtures/return_readers.toml``: one ``[[reader]]``
table per function, with ``module`` (dotted, under ``discotrade``),
``function``, ``class`` (one of O-18's five) and ``note`` (one line). The
form admits ``pending``, which decision 89 (c) put on three entries until step
S4.1; since step S4.1 no entry carries it (O-24, decision 2026-10-17-m19
147 (c)).

Notation of ``function``: the names of the enclosing ``def`` and ``class``
statements from the module down, joined by ``.``: a module function
``admit``, a method ``Class.method``, a function nested in a function
``build.approach_row`` (Python's ``__qualname__`` without ``<locals>``).

The audit walks every ``.py`` file under ``src/discotrade/`` with ``ast`` and
finds every function, method and nested function whose own body holds one
of decision 89 (b)'s reference shapes:

- one of the string constants ``REFERENCE_STRINGS`` anywhere in the body:
  in a tuple, list, set or dict literal, a comparison, a subscript of any
  kind, a default, an argument, a generator or a comprehension (decision
  2026-10-14 92, widening decision 89 (b)'s subscript, keyword and call
  argument after REVIEW-11 should-fix 1);
- the attribute ``sharpe``, ``total_return`` or ``max_drawdown`` of the
  module ``discotrade.metrics`` (``metrics.sharpe`` under the name the
  module imports it by), or one of those names read where the module
  imports it from ``discotrade.metrics`` (and, in ``metrics.py``, its own);
- an attribute access ``.gross``, ``.net_1x`` or ``.net_2x`` on anything.

A shape belongs to the innermost function that holds it: a nested function
is found, and registered, on its own; a shape at module or class level is in
no function and is not scanned. It fails when a found function is not
registered, when a registered function does not exist, or when an
``adjusted`` or ``timing_gross`` entry without ``pending`` does not call
``paper.adjusted`` in its body (the body including its nested functions):
a call of ``adjusted`` on a name bound to ``discotrade.paper``, a call of
the name ``adjusted`` imported from it (or, in ``paper.py``, its own), or a
call of a module function of the same module that the register marks
``adjusted`` and whose body calls ``paper.adjusted`` so. A call of
``paper.adjusted_rows`` in any of these forms counts as one of
``paper.adjusted`` (decision 2026-10-14-m12 97 (c)).
"""

import ast
import tomllib
from pathlib import Path
from typing import Any

import pytest

from discotrade.cli import REPO_ROOT

SRC = REPO_ROOT / "src" / "discotrade"
REGISTER = REPO_ROOT / "tests" / "fixtures" / "return_readers.toml"

CLASSES = ("producer", "display", "stage3_money", "adjusted", "timing_gross")
CALLERS = frozenset(("adjusted", "timing_gross"))
#: The functions of ``discotrade.paper`` an ``adjusted`` entry may call: O-4's
#: series from the stored records, or from evaluation rows (decision
#: 2026-10-14-m12 97 (c)).
PAPER_ADJUSTED = frozenset(("adjusted", "adjusted_rows"))
REFERENCE_STRINGS = frozenset(("gross", "net_1x", "net_2x", "sharpe", "total_return",
                               "max_drawdown"))
METRIC_NAMES = frozenset(("sharpe", "total_return", "max_drawdown"))
COLUMN_ATTRIBUTES = frozenset(("gross", "net_1x", "net_2x"))
KEYS = frozenset(("module", "function", "class", "note"))

#: The entries carrying ``pending``: none since step S4.1 (O-24, decision
#: 2026-10-17-m19 147 (c), which removed decision 89 (c)'s three).
PENDING: set[tuple[str, str, str, str]] = set()

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


class Module:
    """One parsed module: its functions by qualified name, and the names it
    binds to ``discotrade.metrics``, its three figures, ``discotrade.paper``
    and ``paper.adjusted``."""

    def __init__(self, name: str, tree: ast.Module) -> None:
        self.name = name
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.top: set[str] = set()
        self.metrics_modules: set[str] = set()
        self.metric_names: set[str] = set(METRIC_NAMES) if name == "discotrade.metrics" else set()
        self.paper_modules: set[str] = set()
        self.adjusted_names: set[str] = (set(PAPER_ADJUSTED) if name == "discotrade.paper"
                                         else set())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                for alias in node.names:
                    bound = alias.asname or alias.name
                    if node.module == "discotrade" and alias.name == "metrics":
                        self.metrics_modules.add(bound)
                    if node.module == "discotrade" and alias.name == "paper":
                        self.paper_modules.add(bound)
                    if node.module == "discotrade.metrics" and alias.name in METRIC_NAMES:
                        self.metric_names.add(bound)
                    if node.module == "discotrade.paper" and alias.name in PAPER_ADJUSTED:
                        self.adjusted_names.add(bound)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname and alias.name == "discotrade.metrics":
                        self.metrics_modules.add(alias.asname)
                    if alias.asname and alias.name == "discotrade.paper":
                        self.paper_modules.add(alias.asname)
        self._collect(tree, [])
        self.top = {n.name for n in tree.body if isinstance(n, _FUNCTIONS)}

    def _collect(self, node: ast.AST, path: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPES):
                inner = path + [child.name]
                if isinstance(child, _FUNCTIONS):
                    self.functions[".".join(inner)] = child
                self._collect(child, inner)
            else:
                self._collect(child, path)

    def shapes(self, node: ast.AST) -> list[str]:
        """The reference shapes ``node`` itself is (not its children)."""
        found: list[str] = []
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and node.value in REFERENCE_STRINGS):
            found.append(f'"{node.value}" constant')
        if isinstance(node, ast.Attribute):
            if node.attr in COLUMN_ATTRIBUTES:
                found.append(f".{node.attr}")
            if (node.attr in METRIC_NAMES and isinstance(node.value, ast.Name)
                    and node.value.id in self.metrics_modules):
                found.append(f"metrics.{node.attr}")
        if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                and node.id in self.metric_names):
            found.append(f"metrics.{node.id}")
        return found

    def own_nodes(self, function: ast.AST) -> list[ast.AST]:
        """The nodes of ``function``'s own body (its parameter defaults
        included), without the functions and classes defined in it."""
        out: list[ast.AST] = []

        def walk(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, _SCOPES):
                    continue
                out.append(child)
                walk(child)

        walk(function)
        return out

    def readers(self) -> dict[str, list[str]]:
        """Every function holding a reference shape in its own body (its own
        parameter defaults included), with the shapes."""
        out: dict[str, list[str]] = {}
        for qual, function in self.functions.items():
            found = [s for n in self.own_nodes(function) for s in self.shapes(n)]
            if found:
                out[qual] = sorted(set(found))
        return out

    def calls_adjusted(self, qual: str) -> bool:
        """``qual``'s body, nested functions included, calls ``paper.adjusted``
        or ``paper.adjusted_rows`` by name."""
        for node in ast.walk(self.functions[qual]):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr in PAPER_ADJUSTED
                    and isinstance(f.value, ast.Name) and f.value.id in self.paper_modules):
                return True
            if isinstance(f, ast.Name) and f.id in self.adjusted_names:
                return True
        return False

    def called_names(self, qual: str) -> set[str]:
        return {node.func.id for node in ast.walk(self.functions[qual])
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}


def modules(src: Path, package: str = "discotrade") -> dict[str, Module]:
    out = {}
    for path in sorted(src.rglob("*.py")):
        parts = path.relative_to(src).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        name = ".".join((package, *parts))
        out[name] = Module(name, ast.parse(path.read_text(), filename=str(path)))
    return out


def read_register(path: Path) -> list[dict[str, Any]]:
    with open(path, "rb") as f:
        return tomllib.load(f)["reader"]


def register_errors(entries: list[dict[str, Any]]) -> list[str]:
    """The register's own form (decision 89 (a))."""
    errors = []
    seen = set()
    for entry in entries:
        key = (entry.get("module"), entry.get("function"))
        keys = set(entry)
        if not (KEYS <= keys <= KEYS | {"pending"}):
            errors.append(f"{key}: keys {sorted(keys)}")
        if entry.get("class") not in CLASSES:
            errors.append(f"{key}: class {entry.get('class')!r} is not one of O-18's five")
        note = entry.get("note")
        if not isinstance(note, str) or not note.strip() or "\n" in note:
            errors.append(f"{key}: note is not one line")
        if key in seen:
            errors.append(f"{key}: registered twice")
        seen.add(key)
    return errors


def pending(entries: list[dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    return {(e["module"], e["function"], e["class"], e["pending"])
            for e in entries if "pending" in e}


def audit(src: Path, entries: list[dict[str, Any]]) -> list[str]:
    """Decision 89 (b)'s three failures, one line each."""
    found = modules(src)
    errors = []
    registered = {(e["module"], e["function"]): e for e in entries}
    for name, module in found.items():
        for qual, shapes in module.readers().items():
            if (name, qual) not in registered:
                errors.append(f"unregistered: {name}.{qual} holds {', '.join(shapes)}")
    for (name, qual) in registered:
        if name not in found or qual not in found[name].functions:
            errors.append(f"no longer exists: {name}.{qual}")
    for (name, qual), entry in registered.items():
        if entry["class"] not in CALLERS or "pending" in entry:
            continue
        if name not in found or qual not in found[name].functions:
            continue
        module = found[name]
        if module.calls_adjusted(qual):
            continue
        local = {f for f in module.called_names(qual) & module.top
                 if registered.get((name, f), {}).get("class") == "adjusted"
                 and module.calls_adjusted(f)}
        if not local:
            errors.append(f"does not call paper.adjusted: {name}.{qual} ({entry['class']})")
    return errors


# ---------------------------------------------------------------- the register


def test_the_register_has_its_form():
    entries = read_register(REGISTER)
    assert entries
    assert register_errors(entries) == []


def test_no_entry_carries_pending():
    assert pending(read_register(REGISTER)) == PENDING


def test_the_one_stage3_money_entry_is_the_dashboards():
    # Decision 2026-10-17-m19 153 (c): exactly one stage3_money entry, the
    # dashboard's reader of the money condition; paper.portfolio and paper._series
    # stay producer (REVIEW-11 note 8).
    entries = read_register(REGISTER)
    money = [(e["module"], e["function"]) for e in entries if e["class"] == "stage3_money"]
    assert money == [("discotrade.dashboard", "stage3_money")]
    classes = {(e["module"], e["function"]): e["class"] for e in entries}
    assert classes[("discotrade.paper", "portfolio")] == "producer"
    assert classes[("discotrade.paper", "_series")] == "producer"


def test_the_audit_passes():
    assert audit(SRC, read_register(REGISTER)) == []


# ------------------------------------------------------------ the audit itself


def _entry(module: str, function: str, cls: str, **extra: str) -> dict[str, str]:
    return {"module": module, "function": function, "class": cls, "note": "n", **extra}


def _plant(tmp_path: Path, files: dict[str, str]) -> Path:
    src = tmp_path / "discotrade"
    src.mkdir()
    for name, text in files.items():
        (src / name).write_text(text)
    return src


@pytest.mark.parametrize("body", [
    'x = frame["net_1x"]',
    'x = f(column="gross")',
    'x = f("max_drawdown")',
    "x = frame.net_2x",
    "x = metrics.sharpe(d)",
    "x = sharpe(d)",
    "x = tr(d)",
])
def test_each_reference_shape_is_found(tmp_path, body):
    src = _plant(tmp_path, {"a.py": "from discotrade import metrics\n"
                                    "from discotrade.metrics import sharpe\n"
                                    "from discotrade.metrics import total_return as tr\n"
                                    f"def f(frame, d):\n    {body}\n"})
    assert list(modules(src)["discotrade.a"].readers()) == ["f"]


def test_a_parameter_default_is_a_keyword(tmp_path):
    src = _plant(tmp_path, {"a.py": 'def f(paper, *, column="net_1x"):\n    return paper\n'})
    # Decision 2026-10-14 92: one label for a constant wherever it stands.
    assert modules(src)["discotrade.a"].readers() == {"f": ['"net_1x" constant']}


@pytest.mark.parametrize("body", [
    'x = sum(r[c] for c in ("net_1x", "net_2x"))',     # a tuple of a generator (REVIEW-11)
    'x = [r[c] for c in ["gross"]]',                   # a list, a comprehension
    'x = {c for c in {"max_drawdown"}}',               # a set
    'x = {"sharpe": 1}',                               # a dict key
    'x = {"k": "total_return"}',                       # a dict value
    'x = "sharpe" in r',                               # a comparison
    'x = r[["net_1x", "net_2x"]]',                     # a list subscript (REVIEW-11 note 7)
    'x = r[0, "gross"]',                               # a tuple subscript
    'x = r.get("sharpe")',                             # a call argument
    'x = lambda c="net_2x": c',                        # a lambda's default
    'x = {c: r for c in ("gross",)}',                  # a dict comprehension
])
def test_a_string_constant_is_found_anywhere_in_a_function_body(tmp_path, body):
    # Decision 2026-10-14 92: the six constants anywhere in a function's body.
    src = _plant(tmp_path, {"a.py": f"def f(r):\n    {body}\n    return x\n"})
    assert list(modules(src)["discotrade.a"].readers()) == ["f"]


def test_other_shapes_are_not_found(tmp_path):
    # Decision 2026-10-14 92 changes this test: ``{"sharpe": 1}`` and
    # ``"sharpe" in m`` inside a function are now found; a constant at module
    # or class level is in no function, and ``m.sharpe`` on anything but the
    # metrics module, another string, and a function named ``sharpe`` are not
    # reference shapes.
    src = _plant(tmp_path, {"a.py": 'NAMES = ("net_1x",)\n'
                                    'class K:\n    COLS = ["gross", "net_2x"]\n'
                                    'def f(m):\n'
                                    '    d = {"sharpe_2x": 1, "net": "gross_x"}\n'
                                    '    return "Sharpe" in m, m.sharpe, d, NAMES\n'
                                    'def sharpe(d):\n    return d\n'})
    assert modules(src)["discotrade.a"].readers() == {}


def test_a_constant_belongs_to_the_innermost_function(tmp_path):
    src = _plant(tmp_path, {"a.py": "def outer(r):\n"
                                    "    def inner():\n"
                                    "        return [r[c] for c in ('net_1x',)]\n"
                                    "    return inner\n"})
    assert modules(src)["discotrade.a"].readers() == {"outer.inner": ['"net_1x" constant']}


def test_the_readers_review_11_named_are_registered():
    # REVIEW-11 should-fix 1 and note 7; decision 2026-10-14 92 (O-18).
    classes = {(e["module"], e["function"]): e["class"] for e in read_register(REGISTER)}
    assert classes[("discotrade.cli", "_backtest_result")] == "display"
    assert classes[("discotrade.replay", "_adjusted")] == "producer"
    found = modules(SRC)
    assert "_backtest_result" in found["discotrade.cli"].readers()
    # ``replay._adjusted`` names its keys through module constants, which no
    # function holds, so the audit does not find it; decision 92 registers it.
    assert "_adjusted" in found["discotrade.replay"].functions


def test_methods_and_nested_functions_are_qualified(tmp_path):
    src = _plant(tmp_path, {"a.py": "class C:\n"
                                    "    def m(self, r):\n        return r.gross\n"
                                    "def outer(r):\n"
                                    "    def inner():\n        return r.net_1x\n"
                                    "    return inner\n"})
    assert sorted(modules(src)["discotrade.a"].readers()) == ["C.m", "outer.inner"]


def test_an_unregistered_reader_fails(tmp_path):
    src = _plant(tmp_path, {"a.py": 'def f(frame):\n    return frame["net_1x"]\n'})
    assert audit(src, []) == ['unregistered: discotrade.a.f holds "net_1x" constant']
    assert audit(src, [_entry("discotrade.a", "f", "producer")]) == []


def test_a_registered_function_that_no_longer_exists_fails(tmp_path):
    src = _plant(tmp_path, {"a.py": "def f():\n    return 1\n"})
    assert audit(src, [_entry("discotrade.a", "g", "display")]) == [
        "no longer exists: discotrade.a.g"]


def test_an_adjusted_entry_calls_paper_adjusted(tmp_path):
    files = {
        "paper.py": "def adjusted(*a):\n    return a\n",
        "a.py": "from discotrade import paper as p\n"
                "def direct(r):\n    return p.adjusted(r)\n"
                "def through(r):\n    return direct(r)\n"
                "def outer(r):\n"
                "    def inner():\n        return direct(r)\n"
                "    return inner()\n"
                "def plain(r):\n    return r.net_1x\n"
                "def via_plain(r):\n    return plain(r)\n",
    }
    src = _plant(tmp_path, files)
    ok = [_entry("discotrade.a", f, "adjusted") for f in ("direct", "through", "outer")]
    ok.append(_entry("discotrade.a", "plain", "display"))
    assert audit(src, ok) == []
    wrong = ok + [_entry("discotrade.a", "via_plain", "timing_gross")]
    assert audit(src, wrong) == [
        "does not call paper.adjusted: discotrade.a.via_plain (timing_gross)"]
    as_pending = ok + [_entry("discotrade.a", "via_plain", "adjusted", pending="S4.1")]
    assert audit(src, as_pending) == []


def test_the_local_function_must_itself_be_registered_adjusted(tmp_path):
    src = _plant(tmp_path, {
        "a.py": "from discotrade import paper\n"
                "def direct(r):\n    return paper.adjusted(r)\n"
                "def through(r):\n    return direct(r)\n"})
    entries = [_entry("discotrade.a", "direct", "producer"),
               _entry("discotrade.a", "through", "adjusted")]
    assert audit(src, entries) == [
        "does not call paper.adjusted: discotrade.a.through (adjusted)"]


def test_a_fourth_pending_entry_is_seen():
    entries = read_register(REGISTER) + [
        _entry("discotrade.lifecycle", "admit", "adjusted", pending="S4.1")]
    assert pending(entries) != PENDING


def test_a_register_of_bad_form_is_seen():
    entries = [_entry("discotrade.a", "f", "plain"),
               {"module": "discotrade.a", "function": "g", "class": "display",
                "note": "two\nlines"},
               _entry("discotrade.a", "h", "display", extra="x"),
               _entry("discotrade.a", "h", "display")]
    assert len(register_errors(entries)) == 4


def test_a_call_of_paper_adjusted_rows_is_the_call_o18_asks_for(tmp_path):
    # Decision 2026-10-14-m12 97 (c): ``paper.adjusted_rows`` builds O-4's
    # series from evaluation rows, so a call of it counts as a call of
    # ``paper.adjusted``; an ``adjusted`` entry that calls neither fails.
    files = {
        "paper.py": "def adjusted(*a):\n    return a\n"
                    "def adjusted_rows(*a):\n    return a\n"
                    "def window_units(*a):\n    return a\n"
                    "def own(r):\n    return adjusted_rows(r)\n",
        "a.py": "from discotrade import paper\n"
                "from discotrade.paper import adjusted_rows as rows\n"
                "def by_module(r):\n    return paper.adjusted_rows(r)\n"
                "def by_name(r):\n    return rows(r)\n"
                "def through(r):\n    return by_module(r)\n"
                "def neither(r):\n    return paper.window_units(r)\n",
    }
    src = _plant(tmp_path, files)
    ok = [_entry("discotrade.a", f, "adjusted") for f in ("by_module", "by_name", "through")]
    ok.append(_entry("discotrade.paper", "own", "adjusted"))
    assert audit(src, ok) == []
    assert audit(src, ok + [_entry("discotrade.a", "neither", "adjusted")]) == [
        "does not call paper.adjusted: discotrade.a.neither (adjusted)"]
