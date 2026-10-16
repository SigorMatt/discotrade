"""Anonymization of a worker's prompt (DESIGN 13.2; decision 116 (a), (c) of
meta/decisions/decisions-2026-10-15-m14.md; I-8, I-9).

The seed rule is checked by this file's own computation: the first 8 bytes,
big-endian, of the sha256 of the call id's UTF-8 text seed
``numpy.random.default_rng``; its ``permutation`` of the track's instruments
(in the track's order) is the label order ``A``, ``B``, ...; then its
``uniform(0.5, 2.0, size=n)`` gives the scaling constants in label order.
The documents are hand-built in the ``p1`` shape (``version``,
``instruments``, ``common``, ``cell``) over the fixture tracks' instruments
(``tests/fixtures/config/tracks/``): no bar is read, no clock is read, and
every random draw is the call id's.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
from conftest import FIXTURE_CONFIG

from discotrade.config import load_track_config
from discotrade.workers import anonymize as an

CALL_1 = "2019-07-15/test_synth/trend/short/0"
CALL_2 = "2019-07-15/test_synth/trend/short/1"


def symbols(track):
    return list(load_track_config(FIXTURE_CONFIG, track).track.instruments)


def own_rng(call_id):
    digest = hashlib.sha256(call_id.encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def own_labelling(call_id, syms):
    """(label -> symbol, label -> factor), by this file's own reading of 116 (a)."""
    rng = own_rng(call_id)
    order = [syms[i] for i in rng.permutation(len(syms))]
    factors = rng.uniform(0.5, 2.0, size=len(syms))
    labels = [chr(ord("A") + k) for k in range(len(syms))]
    return (dict(zip(labels, order, strict=True)),
            dict(zip(labels, map(float, factors), strict=True)))


def document(syms):
    """A ``p1``-shaped document whose blocks name their own symbol, with an
    hour-of-day list and a weekday list."""
    def common(s):
        return {"returns": {"mean_bp": float(len(s)), "std_bp": 2.5},
                "std_by_hour": [{"std_bp": float(h), "count": h} for h in range(24)],
                "std_by_weekday": [{"std_bp": float(d), "count": d} for d in range(7)],
                "who": s}

    return {"version": "p1", "instruments": list(syms),
            "common": {s: common(s) for s in syms},
            "cell": {"family": "trend",
                     "instruments": {s: {"k6": {"count": 3}, "who": s} for s in syms}}}


def test_the_seed_is_the_first_8_bytes_big_endian_of_the_sha256_of_the_call_id():
    for call_id in (CALL_1, CALL_2, "x", "é"):
        digest = hashlib.sha256(call_id.encode("utf-8")).digest()
        assert an.seed(call_id) == int.from_bytes(digest[:8], "big")


@pytest.mark.parametrize("track", ["test_synth", "test_mixed"])
def test_the_labelling_is_the_call_ids_shuffle_in_label_order(track):
    syms = symbols(track)
    for call_id in (CALL_1, CALL_2):
        labels, _ = own_labelling(call_id, syms)
        got = an.labelling(call_id, syms)
        assert got.labels == tuple(labels.items())
        assert [got.label(s) for s in labels.values()] == list(labels)
        assert [got.symbol(lab) for lab in labels] == list(labels.values())


def test_one_call_id_gives_the_same_labelling_twice_and_two_call_ids_differ():
    syms = symbols("test_synth")
    first, again = an.labelling(CALL_1, syms), an.labelling(CALL_1, syms)
    other = an.labelling(CALL_2, syms)
    assert first == again
    assert first.labels != other.labels
    assert own_labelling(CALL_1, syms)[0] != own_labelling(CALL_2, syms)[0]


def test_a_track_of_more_than_26_instruments_is_refused():
    many = [f"I{k:02d}" for k in range(27)]
    with pytest.raises(an.AnonymizeError, match="26"):
        an.labelling(CALL_1, many)
    assert len(an.labelling(CALL_1, many[:26]).labels) == 26


@pytest.mark.parametrize("track", ["test_synth", "test_mixed"])
def test_the_document_is_keyed_by_label_in_label_order_and_names_no_symbol(track):
    syms = symbols(track)
    doc = document(syms)
    labels, _ = own_labelling(CALL_1, syms)
    out = an.anonymize(doc, CALL_1)
    assert out["version"] == "p1"
    assert out["instruments"] == list(labels)
    assert list(out["common"]) == list(labels)
    assert list(out["cell"]["instruments"]) == list(labels)
    assert out["cell"]["family"] == "trend"
    for lab, sym in labels.items():
        # one mapping for every instrument-keyed part (the blocks carry their symbol)
        assert out["common"][lab]["who"] == sym
        assert out["cell"]["instruments"][lab]["who"] == sym
        # returns, hours of day and weekdays are kept as they are (p1 scales nothing)
        assert out["common"][lab]["returns"] == doc["common"][sym]["returns"]
        assert out["common"][lab]["std_by_hour"] == doc["common"][sym]["std_by_hour"]
        assert out["common"][lab]["std_by_weekday"] == doc["common"][sym]["std_by_weekday"]
    keys = set(out["instruments"]) | set(out["common"]) | set(out["cell"]["instruments"])
    assert not keys & set(syms)
    plain = document(syms)
    for s in syms:                                     # a document whose blocks hold no symbol
        del plain["common"][s]["who"], plain["cell"]["instruments"][s]["who"]
    text = json.dumps(an.anonymize(plain, CALL_1))
    assert not any(s in text for s in syms)
    assert doc == document(syms)                       # the input is not changed


def test_p1_lists_no_field_in_price_or_volume_units():
    assert an.SCALED_FIELDS == {"p1": ()}
    with pytest.raises(an.AnonymizeError, match="p9"):
        an.anonymize({**document(["S1"]), "version": "p9"}, CALL_1)


def test_the_scaling_function_scales_a_listed_field_and_leaves_returns_unchanged():
    block = {"returns": {"mean_bp": 1.5, "std_bp": 3.0}, "range_price": 10.0,
             "volume": {"mean_units": 400.0, "none": None, "count": 7}}
    fields = ("range_price", "volume.mean_units", "volume.none")
    out = an.scale(block, 1.25, fields)
    assert out["range_price"] == 10.0 * 1.25
    assert out["volume"]["mean_units"] == 400.0 * 1.25
    assert out["volume"]["none"] is None                 # not defined stays not defined
    assert out["volume"]["count"] == 7
    assert out["returns"] == {"mean_bp": 1.5, "std_bp": 3.0}
    assert block["range_price"] == 10.0                  # the input is not changed
    with pytest.raises(an.AnonymizeError, match="nowhere"):
        an.scale(block, 1.25, ("nowhere",))


def test_each_instrument_is_scaled_by_its_own_draw_on_0_5_to_2_0():
    syms = symbols("test_synth")
    doc = document(syms)
    for s in syms:
        doc["common"][s]["range_price"] = 10.0
        doc["cell"]["instruments"][s]["move_price"] = 3.0
    fields = (("common", "range_price"), ("cell", "move_price"))
    labels, factors = own_labelling(CALL_2, syms)
    out = an.anonymize(doc, CALL_2, fields=fields)
    assert len(set(factors.values())) == len(syms)
    for lab in labels:
        assert 0.5 <= factors[lab] <= 2.0
        assert out["common"][lab]["range_price"] == 10.0 * factors[lab]
        assert out["cell"]["instruments"][lab]["move_price"] == 3.0 * factors[lab]
        assert out["common"][lab]["returns"] == doc["common"][labels[lab]]["returns"]
    assert an.labelling(CALL_2, syms).factors == tuple(factors.items())
