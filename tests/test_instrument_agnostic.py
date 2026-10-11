"""I-9: no file under src/ names an instrument symbol, contract root or venue.

The names are read from the repository's ``config/instruments/``; a file
under ``src/`` that contains one as a whole word (case-insensitive) fails.
"""

import re
import tomllib
from pathlib import Path

from discotrade.cli import REPO_ROOT


def market_names(config: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((config / "instruments").glob("*.toml")):
        with open(path, "rb") as f:
            record = tomllib.load(f)
        names.add(record["symbol"])
        names.add(record["venue"])
        root = record.get("source", {}).get("symbol")
        if root:
            names.add(root.split(".")[0])
    return names


def offences(src: Path, names: set[str]) -> list[str]:
    alternatives = "|".join(re.escape(n) for n in sorted(names))
    pattern = re.compile(rf"(?<![A-Za-z0-9_])({alternatives})(?![A-Za-z0-9_])", re.IGNORECASE)
    found = []
    for path in sorted(src.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        text = path.read_text(errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            for match in pattern.finditer(line):
                found.append(f"{path.relative_to(src)}:{number}: {match.group(0)}")
    return found


def test_config_names_markets():
    names = market_names(REPO_ROOT / "config")
    assert {"MES", "MNQ", "MYM", "M2K", "MGC", "SIL", "MCL", "M6E"} <= names
    assert "CME" in names


def test_no_market_named_under_src():
    assert offences(REPO_ROOT / "src", market_names(REPO_ROOT / "config")) == []


def test_scan_finds_a_planted_name(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text('x = 1\nif venue == "cme":\n    pass\n')
    (tmp_path / "pkg" / "b.py").write_text("cme_globex = 1  # not a whole word\n")
    assert offences(tmp_path, {"CME"}) == ["pkg/a.py:2: cme"]
