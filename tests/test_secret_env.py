"""The test environment holds no secret (I-11, I-13; decision 171 (c) of
meta/decisions/decisions-2026-10-19-m21.md).

``tests/conftest.py``'s autouse fixture removes, for every test, each variable
``conftest.secret_env()`` names. One test asserts that each is absent inside a
test; another reads every module under ``src/discotrade/`` as text and asserts
that each string literal shaped like a key's variable name (ending ``_API_KEY``,
``_TOKEN`` or ``_SECRET``) is one of them, so that a key added under a new name
is listed when it is added. Nothing here sets a key, reads the network or a
clock.
"""

import ast
import os
import re
from pathlib import Path

from conftest import REPO_ROOT, secret_env

SRC = REPO_ROOT / "src" / "discotrade"
#: A string literal that names a secret's environment variable.
SECRET_NAME = re.compile(r"[A-Z][A-Z0-9_]*_(API_KEY|TOKEN|SECRET)")


def secret_names_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and SECRET_NAME.fullmatch(node.value)}


def test_the_listed_secrets_are_the_three_keys():
    assert secret_env() == ("ANTHROPIC_API_KEY", "DATABENTO_API_KEY", "NEBIUS_API_KEY")


def test_no_listed_secret_is_set_inside_a_test():
    assert [name for name in secret_env() if name in os.environ] == []


def test_every_secret_name_under_src_is_listed():
    found = {name: sorted(p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py")
                          if name in secret_names_in(p))
             for p in SRC.rglob("*.py") for name in secret_names_in(p)}
    assert set(found) <= set(secret_env()), found
    assert set(found) == set(secret_env())


def test_the_scan_finds_a_new_key_name(tmp_path):
    path = tmp_path / "module.py"
    path.write_text('OTHER_ENV = "EXAMPLE_API_KEY"\nX = "not a key"\n', encoding="utf-8")
    assert secret_names_in(path) == {"EXAMPLE_API_KEY"}
