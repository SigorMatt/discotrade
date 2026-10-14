"""The shared check of the error texts sent back to a worker (DESIGN 13.2, 12.2;
decision 95 (e) of 2026-10-14-m12; decision 101 (f) of 2026-10-14-m13; I-8).

Each test that produces an error text checks the texts it produced itself,
through :func:`assert_clean`, so that it passes alone (``-k``) and in any
order; nothing here keeps a list across tests.

A text may hold none of: an instrument symbol, a venue or a contract named in
``config/`` or ``tests/fixtures/config/`` (and, given a state directory, a
contract of the stored bars), nor anything :data:`PATTERN` matches: a date
(``2019-07``), a compact date (eight consecutive digits, ``20190715``), a time
of day (``14:00``) or a decimal number (``4125.25``). A whole-number price is
not detectable by pattern and stays unproven (decision 101 (f)).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOTS = (REPO_ROOT / "config", REPO_ROOT / "tests" / "fixtures" / "config")
#: A date, a compact date, a time of day or a decimal number.
PATTERN = re.compile(r"\d{4}-\d{2}|\d{8}|\d{1,2}:\d{2}|\d\.\d")


def forbidden_words(state: Path | None = None, track: str | None = None,
                    symbols: Iterable[str] = ()) -> set[str]:
    """Every symbol, venue and contract in the instrument records of ``config/``
    and ``tests/fixtures/config/``, and, given ``state`` and ``track``, every
    contract of ``symbols``' stored bars."""
    words: set[str] = set()
    for root in CONFIG_ROOTS:
        for path in sorted((root / "instruments").glob("*.toml")):
            record = tomllib.loads(path.read_text(encoding="utf-8"))
            words |= {record["symbol"], record["venue"]}
            words |= {str(v) for k, v in record.get("source", {}).items()
                      if "contract" in k or k in ("dataset", "symbol")}
    if state is not None and track is not None:
        for symbol in symbols:
            for f in sorted((Path(state) / "bars" / track / symbol).glob("*.parquet")):
                words |= {str(c) for c in pq.read_table(f).column("contract").to_pylist()}
    return {w for w in words if w}


def offences(text: str, words: Iterable[str]) -> list[str]:
    """What in ``text`` an error text may not hold: each word found, each match."""
    found = [w for w in sorted(words) if w in text]
    return found + [m.group(0) for m in PATTERN.finditer(text)]


def assert_clean(texts: Iterable[str], words: Iterable[str]) -> None:
    """Every one of ``texts`` (at least one) holds no word and no pattern match."""
    texts = list(texts)
    words = set(words)
    assert texts, "no error text to check"
    for text in texts:
        assert isinstance(text, str) and text, text
        assert not offences(text, words), (offences(text, words), text)
