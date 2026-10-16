"""The response parser (DESIGN 13.4, 12.2; decision 117 (c) of 2026-10-15-m14;
I-8, I-10).

A worker's response is read line by line (``str.splitlines``). Outside a
block, a line that is three backticks followed by an info string, with
spaces or tabs allowed before and after (nothing between the backticks and
the info string), opens a block; inside a block, the first line that is three
backticks alone, spaces or tabs around, closes it. A block whose info string
is ``python``, ``py`` or ``python3`` in any case is a Python block; a block
of another or of no language is skipped whole, so an opening line inside it
opens nothing. A block never closed is not a block.

:func:`parse` takes the last Python block: its source is the text between
the two fence lines exactly as the response holds it, the fences excluded.
Its description is the first non-empty line after the closing fence,
sanitized and cut by :func:`discotrade.workers.registry.sanitize` to
``validation.description_max_chars`` (I-10). When that line, after leading
spaces and tabs, begins with three backticks (an opening fence of any
language, a bare fence or a closing fence), there is no description and the
next line is not tried (decision 119 (a) of 2026-10-16-m15, amending 117 (c)).
No Python block is the failure ``no_block``; no non-empty line after it, a
fence line there, or a line that sanitizes to nothing (the decision is
silent; an empty description is no description), is ``no_description``. A
failure is of stage ``parse`` and carries the fixed error text of its rule,
which quotes nothing of the response (DESIGN 12.2's error text, fit to send
back). Nothing here reads a clock, a file, the network or a secret.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from discotrade.config import Thresholds
from discotrade.workers.registry import description_cap, sanitize

STAGE = "parse"
NO_BLOCK, NO_DESCRIPTION = "no_block", "no_description"
#: The fixed error text of each rule.
TEXTS = {
    NO_BLOCK: ("parse [no_block]: the response holds no closed fenced Python block; give "
               "one block opened by a line of three backticks and python, closed by a line "
               "of three backticks"),
    NO_DESCRIPTION: ("parse [no_description]: no description follows the last Python "
                     "block; give a one-sentence description on the next non-empty line "
                     "after its closing fence"),
}
PYTHON = frozenset(("python", "py", "python3"))
FENCE = "```"
_OPEN = re.compile(r"[ \t]*```([^`\s]*)[ \t]*")
_CLOSE = re.compile(r"[ \t]*```[ \t]*")


@dataclass(frozen=True)
class Parsed:
    """The source text of the last Python block and its description."""

    source: str
    description: str


@dataclass(frozen=True)
class Failure:
    """A validation failure of stage ``parse``: its rule and fixed error text."""

    rule: str
    text: str
    stage: str = STAGE


def _fail(rule: str) -> Failure:
    return Failure(rule=rule, text=TEXTS[rule])


def blocks(response: str) -> list[tuple[int, int]]:
    """The closed Python blocks of ``response``: for each, the index of its
    opening and of its closing line in ``response.splitlines()``."""
    lines = response.splitlines()
    out = []
    k = 0
    while k < len(lines):
        opening = _OPEN.fullmatch(lines[k])
        if opening is None:
            k += 1
            continue
        end = next((j for j in range(k + 1, len(lines)) if _CLOSE.fullmatch(lines[j])), None)
        if end is None:
            break
        if opening.group(1).lower() in PYTHON:
            out.append((k, end))
        k = end + 1
    return out


def parse(response: str, thresholds: Thresholds) -> Parsed | Failure:
    """The last Python block of ``response`` and its description, or the failure."""
    found = blocks(response)
    if not found:
        return _fail(NO_BLOCK)
    start, end = found[-1]
    raw = response.splitlines(keepends=True)
    source = "".join(raw[start + 1:end])
    after = (line for line in response.splitlines()[end + 1:] if line.strip())
    line = next(after, "")
    if line.lstrip(" \t").startswith(FENCE):
        return _fail(NO_DESCRIPTION)
    description = sanitize(line, description_cap(thresholds))
    if not description:
        return _fail(NO_DESCRIPTION)
    return Parsed(source=source, description=description)
