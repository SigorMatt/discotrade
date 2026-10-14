"""The static check (DESIGN 12.1; decision 94 of 2026-10-14-m12; R-24; I-10).

Each rule of 12.1 is shown refused, by name, on a text that breaks only that
rule, at the production thresholds of ``config/thresholds.toml``. One test
uses a configuration copied under its temporary directory with a lower
``max_lines``, and says so.
"""

import itertools
import shutil
from pathlib import Path

import pytest

from discotrade.config import load_thresholds
from discotrade.validation.static import FORBIDDEN_ATTRIBUTES, FORBIDDEN_NAMES, RULES, check

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = ROOT / "config" / "thresholds.toml"
STRATEGIES = Path(__file__).resolve().parent / "fixtures" / "strategies"


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds(THRESHOLDS)


@pytest.fixture(scope="module")
def limits(thresholds):
    return {k: thresholds[f"validation.{k}"]
            for k in ("max_lines", "max_params", "grid_max_params", "grid_max_values")}


PARTS = {
    "head": "import numpy as np",
    "params": 'PARAMS = {"lookback": 24, "entry": 1.5}',
    "grid": 'GRID = {"lookback": [12, 24, 48]}',
    "sig": "def position(bars, params):",
    "extra": "",
}


def text(**parts):
    """The base valid text with some of its parts replaced."""
    p = {**PARTS, **parts}
    body = (
        f"{p['head']}\n\n{p['params']}\n{p['grid']}\n\n\n{p['sig']}\n"
        "    close = bars[\"close\"].to_numpy()\n"
        "    return float(np.sign(close[-1] - close[0]))\n"
    )
    if p["extra"]:
        body += "\n\n" + p["extra"] + "\n"
    return body


def helper(*lines):
    """A module-level helper function whose body is ``lines``."""
    return "def helper(x):\n" + "".join(f"    {line}\n" for line in lines)


def refused(source, thresholds, rule, *words):
    result = check(source, thresholds)
    assert result is not None, f"accepted, expected {rule}:\n{source}"
    assert result.rule == rule, (result, source)
    for word in words:
        assert word in result.message, (word, result.message)
    return result


def test_base_text_passes(thresholds):
    assert check(text(), thresholds) is None


def test_rules_are_in_section_order():
    assert RULES == (
        "parse", "max_lines",
        "params", "max_params", "param_key", "param_value",
        "grid", "grid_value", "grid_key", "grid_max_params", "grid_max_values",
        "position", "import", "construct", "underscore", "forbidden_name",
        "forbidden_attribute",
    )


# --- parse and lines (R-24: physical lines) ---------------------------------------


def test_text_that_does_not_parse(thresholds):
    refused(text(extra="def helper(x)\n    return x"), thresholds, "parse")
    refused("PARAMS = {}\x00\n", thresholds, "parse")


def padded(lines, ending="\n", final=True):
    """The base text padded with comment lines to exactly ``lines`` physical lines."""
    base = text().rstrip("\n").split("\n")
    rows = base + ["# pad"] * (lines - len(base))
    assert len(rows) == lines
    return ending.join(rows) + (ending if final else "")


def test_max_lines_physical_lines(thresholds, limits):
    n = limits["max_lines"]
    assert n == 60
    # A text of exactly max_lines lines passes, with or without a last newline.
    assert check(padded(n), thresholds) is None
    assert check(padded(n, final=False), thresholds) is None
    assert check(padded(n, ending="\r\n"), thresholds) is None
    r = refused(padded(n + 1), thresholds, "max_lines", str(n + 1), str(n))
    assert r.line is None
    refused(padded(n + 1, final=False), thresholds, "max_lines")
    refused(padded(n + 1, ending="\r\n"), thresholds, "max_lines")


def test_max_lines_read_from_configuration(tmp_path, thresholds):
    """A configuration copied under tmp with ``max_lines = 20`` (lower than production)."""
    copied = tmp_path / "thresholds.toml"
    shutil.copy(THRESHOLDS, copied)
    raw = copied.read_text()
    assert "max_lines = 60\n" in raw
    copied.write_text(raw.replace("max_lines = 60\n", "max_lines = 20\n"))
    lowered = load_thresholds(copied)
    assert lowered["validation.max_lines"] == 20
    source = padded(30)
    assert check(source, thresholds) is None
    refused(source, lowered, "max_lines", "30", "20")


# --- PARAMS ------------------------------------------------------------------------


def test_no_params(thresholds):
    refused(text(params=""), thresholds, "params", "PARAMS")
    refused(text(params='PARAMZ = {"lookback": 24, "entry": 1.5}'), thresholds, "params")


def test_params_assigned_twice(thresholds):
    twice = 'PARAMS = {"lookback": 24, "entry": 1.5}\nPARAMS = {"lookback": 24, "entry": 1.5}'
    refused(text(params=twice), thresholds, "params", "once")
    refused(text(extra='PARAMS = {"lookback": 24, "entry": 1.5}'), thresholds, "params")
    refused(text(extra=helper("PARAMS = x", "return x")), thresholds, "params")


def test_params_not_a_plain_dict_literal(thresholds):
    refused(text(params="PARAMS = dict(lookback=24, entry=1.5)"), thresholds, "params")
    refused(text(params='PARAMS: dict = {"lookback": 24, "entry": 1.5}'), thresholds, "params")
    refused(text(params='PARAMS = Q = {"lookback": 24, "entry": 1.5}'), thresholds, "params")
    refused(text(params='if True:\n    PARAMS = {"lookback": 24, "entry": 1.5}'),
            thresholds, "params")


def test_too_many_params(thresholds, limits):
    m = limits["max_params"]
    assert m == 5
    keys = ["lookback", "entry"] + [f"p{i}" for i in range(m - 2)]
    at_max = "PARAMS = {" + ", ".join(f'"{k}": 1' for k in keys) + "}"
    assert check(text(params=at_max), thresholds) is None
    over = "PARAMS = {" + ", ".join(f'"{k}": 1' for k in keys + ["extra"]) + "}"
    refused(text(params=over), thresholds, "max_params", str(m + 1), str(m))


def test_param_key_not_a_string(thresholds):
    refused(text(params='PARAMS = {"lookback": 24, "entry": 1.5, 3: 1}'), thresholds,
            "param_key")
    refused(text(params='PARAMS = {"lookback": 24, "entry": 1.5, **OTHER}'), thresholds,
            "param_key")


@pytest.mark.parametrize("value", ['"x"', "None", "1 + 2", "+1", "--1", "1j", "x", "1e999",
                                   "[1]"])
def test_param_value_not_numeric(thresholds, value):
    refused(text(params=f'PARAMS = {{"lookback": 24, "entry": {value}}}'), thresholds,
            "param_value", "entry")


@pytest.mark.parametrize("value", ["True", "False"])
def test_param_value_bool(thresholds, value):
    refused(text(params=f'PARAMS = {{"lookback": 24, "entry": {value}}}'), thresholds,
            "param_value")


@pytest.mark.parametrize("value", ["-1.5", "-1", "0", "2.5", "7"])
def test_param_value_numeric_accepted(thresholds, value):
    assert check(text(params=f'PARAMS = {{"lookback": 24, "entry": {value}}}'),
                 thresholds) is None


# --- GRID --------------------------------------------------------------------------


def test_no_grid_passes(thresholds):
    assert check(text(grid=""), thresholds) is None


@pytest.mark.parametrize("grid", [
    "GRID = [12, 24]",
    'GRID = {"lookback": (12, 24)}',
    'GRID = {"lookback": 12}',
    'GRID = {"lookback": []}',
    'GRID = dict(lookback=[12, 24])',
    'GRID = {"lookback": [12, 24]}\nGRID = {"lookback": [12, 24]}',
    'GRID: dict = {"lookback": [12, 24]}',
])
def test_grid_not_a_dict_of_lists(thresholds, grid):
    refused(text(grid=grid), thresholds, "grid", "GRID")


@pytest.mark.parametrize("value", ['"a"', "True", "None", "x", "1 + 1"])
def test_grid_value_not_numeric(thresholds, value):
    refused(text(grid=f'GRID = {{"lookback": [12, {value}]}}'), thresholds, "grid_value")


def test_grid_negative_value_accepted(thresholds):
    assert check(text(grid='GRID = {"entry": [-1.5, 1.5]}'), thresholds) is None


def test_grid_key_outside_params(thresholds):
    refused(text(grid='GRID = {"window": [12, 24]}'), thresholds, "grid_key", "window")
    refused(text(grid='GRID = {3: [12, 24]}'), thresholds, "grid_key")


def test_grid_too_many_keys(thresholds, limits):
    g = limits["grid_max_params"]
    assert g == 2
    keys = [f"p{i}" for i in range(g + 1)]
    params = "PARAMS = {" + ", ".join(f'"{k}": 1' for k in keys) + "}"
    at_max = "GRID = {" + ", ".join(f'"{k}": [1, 2]' for k in keys[:g]) + "}"
    assert check(text(params=params, grid=at_max), thresholds) is None
    over = "GRID = {" + ", ".join(f'"{k}": [1, 2]' for k in keys) + "}"
    refused(text(params=params, grid=over), thresholds, "grid_max_params", str(g + 1))


def test_grid_too_many_values(thresholds, limits):
    v = limits["grid_max_values"]
    assert v == 3
    at_max = 'GRID = {"lookback": [' + ", ".join(str(12 * (i + 1)) for i in range(v)) + "]}"
    assert check(text(grid=at_max), thresholds) is None
    over = 'GRID = {"lookback": [' + ", ".join(str(12 * (i + 1)) for i in range(v + 1)) + "]}"
    refused(text(grid=over), thresholds, "grid_max_values", "lookback", str(v + 1))


# --- position ----------------------------------------------------------------------


@pytest.mark.parametrize("sig", [
    "def positions(bars, params):",
    "def position(bars, params=None):",
    "def position(bars, params, extra):",
    "def position(*args):",
    "def position(bars, *args):",
    "def position(bars, params, **kwargs):",
    "def position(bars, params, *, extra):",
    "def position(bars, params, /):",
    "def position(b, p):",
])
def test_position_signature(thresholds, sig):
    refused(text(sig=sig), thresholds, "position")


def test_position_defined_twice_or_rebound(thresholds):
    refused(text(extra="def position(bars, params):\n    return 0.0"), thresholds, "position")
    refused(text(extra="position = None"), thresholds, "position")


# --- imports (decision 94 (e)) -----------------------------------------------------


@pytest.mark.parametrize("head", [
    "import numpy", "import numpy as np\nimport pandas", "import numpy as np\nimport pandas as pd",
    "import numpy as np\nimport indicators", "import numpy as np\nimport indicators as ind",
    "import numpy as np, pandas", "import numpy as np\nfrom numpy import sign",
    "import numpy as np\nfrom numpy import sign as sgn, abs",
    "import numpy as np\nfrom pandas import Series",
    "import numpy as np\nfrom indicators import sma",
])
def test_import_accepted(thresholds, head):
    source = text(head=head)
    if "as np" not in head:
        source = source.replace("np.sign", "numpy.sign")
    assert check(source, thresholds) is None


@pytest.mark.parametrize("line", [
    "import os", "import numpy.random", "import numpy.random as npr", "import pandas.io",
    "import numpy, os", "import scipy", "import indicators.sma",
    "from numpy.random import default_rng", "from pandas.io import parsers",
    "from os import path", "from . import indicators", "from .numpy import sign",
    "from .. import x", "from numpy import *",
])
def test_import_refused(thresholds, line):
    refused(text(head="import numpy as np\n" + line), thresholds, "import")


# --- constructs --------------------------------------------------------------------


@pytest.mark.parametrize("extra,word", [
    ("class Helper:\n    pass", "class"),
    ("def deco(f):\n    return f\n\n\n@deco\ndef helper(x):\n    return x", "decorator"),
    ("def helper(x):\n    global COUNT\n    return x", "global"),
    ("def helper(x):\n    y = x\n\n    def inner():\n        nonlocal y\n        return y\n"
     "    return inner()", "nonlocal"),
    ("async def helper(x):\n    return x", "async"),
    (helper("return [y async for y in x]"), "async"),
    (helper("return await x"), "await"),
    (helper("yield x"), "yield"),
    (helper("yield from x"), "yield from"),
    (helper("with x:", "    return 1"), "with"),
])
def test_construct(thresholds, extra, word):
    refused(text(extra=extra), thresholds, "construct", word)


# --- underscores -------------------------------------------------------------------


@pytest.mark.parametrize("extra,word", [
    (helper("_y = x", "return _y"), "_y"),                      # a name
    (helper("return x.__class__"), "__class__"),                # an attribute
    ("def helper(_x):\n    return 0", "_x"),                    # a parameter
    ("def _helper(x):\n    return x", "_helper"),               # a function name
    (helper("return x.clip(_lower=1)"), "_lower"),              # a keyword argument
    (helper("return (lambda _z: _z)(x)"), "_z"),                # a lambda parameter
    (helper("return __builtins__"), "__builtins__"),
    (helper("try:", "    return x", "except Exception as _e:", "    return 0"), "_e"),
])
def test_underscore(thresholds, extra, word):
    refused(text(extra=extra), thresholds, "underscore", word)


def test_underscore_import_alias_and_from_name(thresholds):
    refused(text(head="import numpy as _np").replace("np.sign", "_np.sign"), thresholds,
            "underscore", "_np")
    refused(text(head="import numpy as np\nfrom numpy import _core"), thresholds, "underscore",
            "_core")


# --- forbidden names and attributes ------------------------------------------------


def test_forbidden_lists_are_section_12_1():
    assert FORBIDDEN_NAMES == (
        "eval", "exec", "compile", "open", "input", "breakpoint", "globals", "locals", "vars",
        "dir", "getattr", "setattr", "delattr", "type", "object", "super", "memoryview",
        "exit", "quit", "help", "print",
    )
    assert FORBIDDEN_ATTRIBUTES == (
        "eval", "query", "pipe", "system", "popen", "load", "loads", "save", "savez",
        "loadtxt", "savetxt", "genfromtxt", "fromfile", "tofile", "memmap", "ctypeslib",
        "random", "default_rng", "RandomState", "now", "today", "time", "datetime", "testing",
        "f2py", "distutils",
    )


FORBIDDEN_NAMES_12_1 = (
    "eval exec compile open input breakpoint globals locals vars dir getattr setattr delattr "
    "type object super memoryview exit quit help print"
).split()

FORBIDDEN_ATTRIBUTES_12_1 = (
    "eval query pipe system popen load loads save savez loadtxt savetxt genfromtxt fromfile "
    "tofile memmap ctypeslib random default_rng RandomState now today time datetime testing "
    "f2py distutils"
).split()


@pytest.mark.parametrize("name", FORBIDDEN_NAMES_12_1)
def test_forbidden_name_as_name(thresholds, name):
    refused(text(extra=helper(f"return {name}")), thresholds, "forbidden_name", name)


@pytest.mark.parametrize("name", FORBIDDEN_NAMES_12_1)
def test_forbidden_name_as_parameter(thresholds, name):
    refused(text(extra=f"def helper({name}):\n    return 0"), thresholds, "forbidden_name", name)


@pytest.mark.parametrize("name", FORBIDDEN_NAMES_12_1)
def test_forbidden_name_as_keyword_argument(thresholds, name):
    refused(text(extra=helper(f"return x.clip({name}=1)")), thresholds, "forbidden_name", name)


@pytest.mark.parametrize("name", FORBIDDEN_NAMES_12_1)
def test_forbidden_name_as_function_name_and_alias(thresholds, name):
    refused(text(extra=f"def {name}(x):\n    return x"), thresholds, "forbidden_name", name)
    refused(text(head=f"import numpy as np\nimport pandas as {name}"), thresholds,
            "forbidden_name", name)


@pytest.mark.parametrize("attr", FORBIDDEN_ATTRIBUTES_12_1)
def test_forbidden_attribute(thresholds, attr):
    refused(text(extra=helper(f"return x.{attr}")), thresholds, "forbidden_attribute", attr)


@pytest.mark.parametrize("attr", ["load", "random", "fromfile"])
def test_forbidden_attribute_through_from_import(thresholds, attr):
    """``from numpy import load`` is the attribute ``numpy.load`` (decision 94 (f))."""
    refused(text(head=f"import numpy as np\nfrom numpy import {attr} as thing"), thresholds,
            "forbidden_attribute", attr)


@pytest.mark.parametrize("attr", ["read_csv", "read_parquet", "to_csv", "to_pickle", "to_"])
def test_read_and_to_attributes(thresholds, attr):
    refused(text(extra=helper(f"return x.{attr}")), thresholds, "forbidden_attribute", attr)


def test_to_numpy_accepted(thresholds):
    assert check(text(extra=helper("return x.to_numpy()")), thresholds) is None


@pytest.mark.parametrize("name", ["read_csv", "to_csv", "random", "now", "load"])
def test_forbidden_attribute_words_are_free_as_names(thresholds, name):
    """The attribute list applies to attribute access, not to plain names (12.1)."""
    assert check(text(extra=helper(f"{name} = x", f"return {name}")), thresholds) is None


# --- order -------------------------------------------------------------------------


#: One text change per rule, each breaking only that rule; mergeable pairwise.
BREAKS = {
    "parse": {"extra": "def broken(x)\n    return x"},
    "max_lines": {"extra": "\n".join(["# pad"] * 60)},
    "params": {"params": ""},
    "max_params": {"params": 'PARAMS = {"lookback": 1, "entry": 1, "a": 1, "b": 1, "c": 1, '
                             '"d": 1}'},
    "param_key": {"params": 'PARAMS = {"lookback": 24, "entry": 1.5, 3: 1}'},
    "param_value": {"params": 'PARAMS = {"lookback": 24, "entry": "x"}'},
    "grid": {"grid": "GRID = [12, 24]"},
    "grid_value": {"grid": 'GRID = {"lookback": [12, "a"]}'},
    "grid_key": {"grid": 'GRID = {"window": [12, 24]}'},
    "grid_max_params": {"params": 'PARAMS = {"lookback": 24, "entry": 1.5, "c": 1}',
                        "grid": 'GRID = {"lookback": [1], "entry": [1], "c": [1]}'},
    "grid_max_values": {"grid": 'GRID = {"lookback": [1, 2, 3, 4]}'},
    "position": {"sig": "def position(bars, params, extra):"},
    "import": {"head": "import numpy as np\nimport os"},
    "construct": {"extra": "class Helper:\n    pass"},
    "underscore": {"extra": helper("return x.__class__")},
    "forbidden_name": {"extra": helper("return eval")},
    "forbidden_attribute": {"extra": helper("return x.read_csv")},
}


@pytest.mark.parametrize("rule", list(BREAKS))
def test_each_break_breaks_only_its_rule(thresholds, rule):
    refused(text(**BREAKS[rule]), thresholds, rule)


def merge(a, b):
    out = dict(a)
    for key, value in b.items():
        out[key] = out[key] + "\n\n" + value if key in out and key == "extra" else value
    return out


PAIRS = [(a, b) for a, b in itertools.combinations(RULES, 2)
         if not (set(BREAKS[a]) & set(BREAKS[b]) - {"extra"})]


@pytest.mark.parametrize("first,second", PAIRS)
def test_two_rules_name_the_earlier(thresholds, first, second):
    if "max_lines" not in (first, second):
        assert len(text(**merge(BREAKS[first], BREAKS[second])).split("\n")) < 60
    refused(text(**merge(BREAKS[first], BREAKS[second])), thresholds, first)
    refused(text(**merge(BREAKS[second], BREAKS[first])), thresholds, first)


def test_pairs_cover_adjacent_rules():
    adjacent = set(zip(RULES, RULES[1:], strict=False))
    covered = set(PAIRS)
    # Rules that change the same part of the text cannot be merged; every other
    # adjacent pair is tested.
    missing = adjacent - covered
    assert missing <= {("params", "max_params"), ("max_params", "param_key"),
                       ("param_key", "param_value"), ("grid", "grid_value"),
                       ("grid_value", "grid_key"), ("grid_key", "grid_max_params"),
                       ("grid_max_params", "grid_max_values")}


def test_first_offending_node_in_source_order(thresholds):
    two = helper("y = x.__class__", "return x._b")
    r = refused(text(extra=two), thresholds, "underscore", "__class__")
    assert "_b" not in r.message
    two = helper("y = x.query", "return x.eval")
    assert "eval" not in refused(text(extra=two), thresholds, "forbidden_attribute").message
    # REVIEW-12 should-fix 3 (decision 101 (d)): within a chain, the attribute whose
    # name comes first in the source is named, not the outer node.
    for extra, rule, first, later in (
        ('x = np.load("f").eval', "forbidden_attribute", "'load'", "'eval'"),
        ("x = np.zz._a._b", "underscore", "'_a'", "'_b'"),
        ("x = np.load(1).to_csv(2)", "forbidden_attribute", "'load'", "'to_csv'"),
    ):
        r = refused(text(extra=extra), thresholds, rule, first)
        assert later not in r.message, (extra, r.message)


def test_order_within_params_and_grid(thresholds):
    """Rules sharing PARAMS or GRID, which the pairwise test cannot merge."""
    six = '"lookback": 1, "entry": 1, "a": 1, "b": 1, "c": True'
    refused(text(params=f"PARAMS = {{{six}, 3: 1}}"), thresholds, "max_params")
    refused(text(params='PARAMS = {"lookback": 1, 3: "x"}'), thresholds, "param_key")
    refused(text(grid='GRID = {"lookback": [1, "a"], "entry": 2}'), thresholds, "grid")
    refused(text(grid='GRID = {"window": [1, "a"]}'), thresholds, "grid_value")
    refused(text(grid='GRID = {"window": [1], "entry": [1], "lookback": [1]}'), thresholds,
            "grid_key")
    refused(text(params='PARAMS = {"lookback": 24, "entry": 1.5, "c": 1}',
                 grid='GRID = {"lookback": [1, 2, 3, 4], "entry": [1], "c": [1]}'),
            thresholds, "grid_max_params")


# --- valid texts -------------------------------------------------------------------


VALID = sorted((ROOT / "reference").glob("*.py")) + [
    STRATEGIES / name for name in
    ("cheat_lookahead.py", "roll_probe.py", "valid_bound.py", "valid_import.py")
]


def test_reference_has_files():
    assert len(list((ROOT / "reference").glob("*.py"))) >= 3


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_texts_pass(thresholds, path):
    assert check(path.read_text(), thresholds) is None
