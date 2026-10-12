"""G0.4: the production configuration checks, and no file under ``src/`` names a
market (DESIGN 18.3 G0.4, 4, 18.2; I-9, I-10; decisions 2026-10-12 9, 40).

``discotrade config check`` is run in-process (``discotrade.cli.main``, the
console script's function) on the repository's ``config/`` and the ``hourly``
track. The names I-9 forbids are collected from the files under ``config/``,
not from a list written here: every instrument symbol, every contract root
(the part of a ``[source]`` ``symbol`` before its first ``.``) and every venue,
from every TOML file under ``config/`` that holds them. A file under ``src/``
contains one when it appears as a whole word, compared without regard to case
(DESIGN 18.3 does not say; this is the stricter reading). Python's bytecode
caches (``__pycache__``) are build output, not files of the repository, and
are not read.

Seeds: the test draws nothing at random.
"""

import re
import tomllib
from pathlib import Path

import pytest

from discotrade.cli import REPO_ROOT, main

pytestmark = [pytest.mark.gate, pytest.mark.gate_m0]

CONFIG = REPO_ROOT / "config"
SRC = REPO_ROOT / "src"
TRACK = "hourly"


def config_records() -> dict[Path, dict]:
    records = {}
    for path in sorted(CONFIG.rglob("*.toml")):
        with open(path, "rb") as f:
            records[path] = tomllib.load(f)
    return records


def market_names() -> dict[str, set[str]]:
    """Every instrument symbol, contract root and venue named in ``config/``."""
    names: dict[str, set[str]] = {"symbol": set(), "root": set(), "venue": set()}
    for record in config_records().values():
        for key in ("symbol", "venue"):
            if isinstance(record.get(key), str):
                names[key].add(record[key])
        source = record.get("source")
        if isinstance(source, dict) and isinstance(source.get("symbol"), str):
            names["root"].add(source["symbol"].split(".")[0])
    return names


def offences(root: Path, names: set[str]) -> list[str]:
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(n) for n in sorted(names))
        + r")(?![A-Za-z0-9_])", re.IGNORECASE)
    found = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        text = path.read_bytes().decode("utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            found += [f"{path.relative_to(root)}:{number}: {m.group(0)}"
                      for m in pattern.finditer(line)]
    return found


def hourly_instruments() -> list[str]:
    with open(CONFIG / "tracks" / f"{TRACK}.toml", "rb") as f:
        return list(tomllib.load(f)["instruments"])


def test_config_check_passes_on_the_hourly_track_with_its_eight_instruments(capsys):
    assert main(["--config", str(CONFIG), "--track", TRACK, "config", "check"]) == 0
    out = capsys.readouterr().out.splitlines()
    instruments = hourly_instruments()
    assert len(instruments) == len(set(instruments)) == 8
    assert f"track {TRACK}: 8 instruments" in "\n".join(out)
    track_line = next(line for line in out if line.startswith(f"track {TRACK}:"))
    assert track_line.startswith(f"track {TRACK}: 8 instruments,"), track_line
    reported = sorted(line.split()[1].rstrip(":") for line in out
                      if line.startswith("instrument "))
    assert reported == sorted(instruments)
    assert out[-1].startswith("config check: ok"), out[-1]


def test_the_names_come_from_config():
    names = market_names()
    # Every instrument of the hourly track is a record under config/ with a
    # venue and a contract root, so each list is filled from the files.
    assert set(hourly_instruments()) <= names["symbol"]
    assert len(names["symbol"]) >= 8 and len(names["root"]) >= 8 and names["venue"]
    for path, record in config_records().items():
        if path.parent.name == "instruments":
            assert record["symbol"] in names["symbol"] and record["venue"] in names["venue"]


def test_no_file_under_src_names_a_symbol_root_or_venue():
    names = set().union(*market_names().values())
    files = [p for p in SRC.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    assert len(files) > 10
    assert offences(SRC, names) == []


def test_control_the_scan_finds_a_name_planted_in_a_copy(tmp_path):
    names = market_names()
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    for kind, found in names.items():
        name = sorted(found)[0]
        (pkg / f"{kind}.py").write_text(f"x = 1\n# reads {name.lower()} here\n",
                                        encoding="utf-8")
        (pkg / f"{kind}_part.py").write_text(f"{name}_x = 1\nx{name} = 2\n",
                                             encoding="utf-8")
    hits = offences(tmp_path, set().union(*names.values()))
    assert sorted(h.split(":")[0] for h in hits) == sorted(f"pkg/{k}.py" for k in names)
