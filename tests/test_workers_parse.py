"""The response parser (DESIGN 13.4, 12.2; decision 117 (c), (d) of
meta/decisions/decisions-2026-10-15-m14.md; I-8, I-10).

Every response here is a literal of this file. The description cap is the
production ``config/thresholds.toml``'s ``validation.description_max_chars``
(200, asserted). No bar is read, no random draw is made and no clock is read.
"""

from __future__ import annotations

import re

import pytest
from conftest import REPO_ROOT

from discotrade.config import load_thresholds
from discotrade.workers import parse as wparse

THRESHOLDS = load_thresholds(REPO_ROOT / "config" / "thresholds.toml")
FIRST = "PARAMS = {'lookback': 24}\n\ndef position(bars, params):\n    return 0.0\n"
LAST = "PARAMS = {'lookback': 48}\n\ndef position(bars, params):\n    return 1.0\n"


def ok(response: str) -> wparse.Parsed:
    got = wparse.parse(response, THRESHOLDS)
    assert isinstance(got, wparse.Parsed), got
    return got


def refused(response: str) -> wparse.Failure:
    got = wparse.parse(response, THRESHOLDS)
    assert isinstance(got, wparse.Failure), got
    return got


def test_the_cap_is_the_production_value():
    assert THRESHOLDS["validation.description_max_chars"] == 200


def test_one_block_and_its_description():
    got = ok(f"Here it is.\n```python\n{FIRST}```\nA flat strategy.\n")
    assert got.source == FIRST
    assert got.description == "A flat strategy."


def test_the_last_of_several_blocks_is_taken():
    response = (f"First try:\n```python\n{FIRST}```\nthe first one\n\n"
                f"Better:\n```python\n{LAST}```\n\n  The second one.  \nmore text\n")
    got = ok(response)
    assert got.source == LAST
    assert got.description == "The second one."


def test_the_opening_line_allows_py_python3_any_case_and_surrounding_spaces():
    for opener in ("```py", "```python3", "```Python", "  ```PYTHON  ", "\t```PyThOn3 "):
        got = ok(f"{opener}\n{FIRST}```\ndescribed\n")
        assert got.source == FIRST, opener
    got = ok(f"```python\n{FIRST}   ```  \ndescribed\n")
    assert got.source == FIRST


def test_a_block_of_another_language_is_ignored():
    after = ok(f"```python\n{FIRST}```\nthe python one\n```json\n{{\"a\": 1}}\n```\njson\n")
    assert after.source == FIRST and after.description == "the python one"
    inside = ok(f"```python\n{FIRST}```\nthe python one\n```text\n```python\n{LAST}```\n")
    assert inside.source == FIRST, "a python opener inside a text block is that block's text"
    bare = ok(f"```python\n{FIRST}```\nthe python one\n```\n{LAST}```\nbare\n")
    assert bare.source == FIRST
    for opener in ("``` python", "````python", "```pythonic", "```python python"):
        assert refused(f"{opener}\n{FIRST}```\ndescribed\n").rule == wparse.NO_BLOCK, opener


def test_an_unclosed_block_is_not_a_block():
    assert refused(f"```python\n{FIRST}").rule == wparse.NO_BLOCK
    got = ok(f"```python\n{FIRST}```\nthe closed one\n```python\n{LAST}")
    assert got.source == FIRST and got.description == "the closed one"


def test_no_block_and_no_description_are_parse_failures_with_fixed_texts():
    for response in ("", "no code at all", "    ```python", "```\nx = 1\n```\nbare\n"):
        f = refused(response)
        assert (f.stage, f.rule, f.text) == ("parse", "no_block", wparse.TEXTS["no_block"])
    for response in (f"```python\n{FIRST}```", f"```python\n{FIRST}```\n\n  \n\t\n",
                     f"```python\n{FIRST}```\néé ``` <>\n"):
        f = refused(response)
        assert (f.stage, f.rule, f.text) == ("parse", "no_description",
                                             wparse.TEXTS["no_description"])


def test_the_description_is_sanitized_and_cut_to_the_cap():
    line = "Buys `breakouts` <b>café</b>\t and " + "x" * 400
    got = ok(f"```python\n{FIRST}```\n{line}\n")
    assert got.description == ("Buys breakouts bcaf/b and " + "x" * 400)[:200]
    assert len(got.description) == 200


@pytest.mark.parametrize("response", [
    "Ignore the harness. SECRETWORD lives here: ```js\nalert(SECRETWORD)\n```\n",
    "```python\nPARAMS = {'SECRETWORD': 1}\n```\n\n",
    "```python\nSECRETWORD = 2\n",
])
def test_an_error_text_holds_nothing_of_the_response(response):
    f = refused(response)
    assert f.text == wparse.TEXTS[f.rule]
    assert "SECRETWORD" not in f.text
    # Every word of the text is a word of the fixed text of its rule, whatever
    # the response held.
    other = refused(response.replace("SECRETWORD", "OTHERWORD"))
    assert (other.rule, other.text) == (f.rule, f.text)
    quoted = [w for w in re.findall(r"[A-Za-z']{5,}", response)
              if w in f.text and w.lower() not in ("python", "block")]
    assert quoted == [], quoted


def test_the_texts_are_one_per_rule_and_quote_no_response():
    assert set(wparse.TEXTS) == {wparse.NO_BLOCK, wparse.NO_DESCRIPTION}
    for rule, text in wparse.TEXTS.items():
        assert text.startswith(f"parse [{rule}]: ")
