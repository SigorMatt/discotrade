"""The shared error-text helper of decision 101 (f) (``tests/error_texts.py``):
what it finds and what it lets pass (DESIGN 13.2; decision 95 (e); I-8)."""

import pytest
from error_texts import PATTERN, assert_clean, forbidden_words, offences

WORDS = forbidden_words()


def test_the_words_hold_the_symbols_venues_and_contracts_of_the_records():
    assert {"SYNA", "SYNTH", "MES", "CME"} <= WORDS


@pytest.mark.parametrize("text, found", [
    ("dry_run [raised]: position raised SYNA_close at window bar 0", "SYNA"),
    ("bar of 2019-06-14", "2019-06"),
    ("bar of 20190715", "20190715"),
    ("at 14:00", "14:00"),
    ("a close of 4125.25", "5.2"),
    ("dry_run [raised]: CME", "CME"),
])
def test_the_helper_finds_a_symbol_a_venue_a_date_a_compact_date_a_time_and_a_price(text,
                                                                                     found):
    assert found in offences(text, WORDS)
    with pytest.raises(AssertionError):
        assert_clean([text], WORDS)


def test_the_helper_finds_a_compact_date():
    assert PATTERN.search("20190715")
    assert offences("dry_run [raised]: 20190715", set()) == ["20190715"]


@pytest.mark.parametrize("text", [
    "dry_run [raised]: position raised an exception at window bar 420 (parameter set 1)",
    "load [raised]: the text raised ValueError while loading (parameter set 0)",
    "activity [min_changes_w]: 29 position changes on W summed over the basket; at least "
    "min_changes_w (30) are needed",
])
def test_the_helper_passes_the_texts_the_harness_writes(text):
    assert_clean([text], WORDS)


def test_the_helper_refuses_to_check_nothing():
    with pytest.raises(AssertionError):
        assert_clean([], WORDS)
