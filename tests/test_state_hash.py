"""The content hash of a table (DESIGN 9.2)."""

import hashlib

import numpy as np
import pandas as pd
import pytest

from discotrade.state import content_hash, content_text


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts": pd.to_datetime([3_600_000_000_000, 0], unit="ns", utc=True),
            "close": [0.1, 1.0 / 3.0],
            "contract": ["B", "A"],
            "n": np.array([2, 1], dtype="int64"),
        }
    )


def test_text_sorts_by_key_and_writes_floats_in_17g():
    text = content_text(_frame(), ["ts"])
    assert text == (
        "ts\tclose\tcontract\tn\n"
        f"0\t{1.0 / 3.0:.17g}\tA\t1\n"
        f"3600000000000\t{0.1:.17g}\tB\t2\n"
    )
    assert "0.10000000000000001" in text


def test_hash_is_sha256_of_text():
    frame = _frame()
    expected = hashlib.sha256(content_text(frame, ["ts"]).encode("utf-8")).hexdigest()
    assert content_hash(frame, ["ts"]) == expected


def test_hash_ignores_row_order_and_index():
    frame = _frame()
    shuffled = frame.iloc[::-1].reset_index(drop=True)
    shuffled.index = [7, 9]
    assert content_hash(frame, ["ts"]) == content_hash(shuffled, ["ts"])


def test_hash_sees_the_last_bit_of_a_float():
    frame = _frame()
    other = frame.copy()
    other.loc[0, "close"] = np.nextafter(other.loc[0, "close"], 1.0)
    assert content_hash(frame, ["ts"]) != content_hash(other, ["ts"])


def test_unknown_key_column_is_refused():
    with pytest.raises(ValueError):
        content_hash(_frame(), ["missing"])


def test_text_with_a_separator_is_refused():
    frame = _frame()
    frame.loc[0, "contract"] = "a\tb"
    with pytest.raises(ValueError):
        content_hash(frame, ["ts"])
