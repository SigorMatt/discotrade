"""Anonymization of a worker's prompt (DESIGN 13.2; decision 116 (a) of
2026-10-15-m14; I-8, I-9).

The generator of a call is ``numpy.random.default_rng`` seeded with
:func:`seed`, the first 8 bytes, big-endian, of the sha256 of the call id's
UTF-8 text (never Python's ``hash``, which changes between processes). Its
first draw, ``permutation(n)`` of the track's instruments in the track's
order, is the shuffled order, labelled ``A``, ``B``, ... in that order (a
track of more than 26 instruments is refused); its second,
``uniform(0.5, 2.0, size=n)``, gives one scaling constant per instrument in
label order. The constants are drawn whatever the profile version lists, so
a call's labelling does not depend on it (the decision is silent on the order
of the two draws; this is the simplest one).

:func:`labelling` gives the one mapping every instrument-keyed part of a
prompt uses (the profile's blocks here, the cost lines of item 117), in label
order. :func:`anonymize` replaces the symbol keys of a W profile document
(``workers.profile``) with labels in label order and multiplies the fields of
:data:`SCALED_FIELDS` for its version by each instrument's constant;
:func:`scale` is that multiplication on one block, for a list of dotted
paths. ``p1`` lists no field in price or volume units, so in v1 nothing is
scaled (DESIGN 13.2). Hours of day and weekdays are kept. Nothing here reads a
clock, a file, the network or a secret.
"""

from __future__ import annotations

import copy
import hashlib
import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

#: Labels in order; their count is the most instruments a track can have.
LABELS = tuple(string.ascii_uppercase)
#: The scaling constants' bounds (decision 116 (a)).
SCALE_LOW, SCALE_HIGH = 0.5, 2.0
#: Per profile version, the fields in price or volume units: ``(part, path)``,
#: ``part`` ``"common"`` or ``"cell"``, ``path`` dotted inside an instrument's
#: block. Empty for ``p1``; a version not listed is refused.
SCALED_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {"p1": ()}


class AnonymizeError(ValueError):
    """A labelling or a scaling that cannot be made."""


def seed(call_id: str) -> int:
    """The first 8 bytes, big-endian, of the sha256 of ``call_id``'s UTF-8 text."""
    return int.from_bytes(hashlib.sha256(call_id.encode("utf-8")).digest()[:8], "big")


@dataclass(frozen=True)
class Labelling:
    """A call's mapping: ``labels`` (label, symbol) and ``factors`` (label,
    scaling constant), both in label order."""

    labels: tuple[tuple[str, str], ...]
    factors: tuple[tuple[str, float], ...]

    def label(self, symbol: str) -> str:
        for lab, sym in self.labels:
            if sym == symbol:
                return lab
        raise AnonymizeError(f"{symbol!r} is not an instrument of this labelling")

    def symbol(self, label: str) -> str:
        return dict(self.labels)[label]

    def factor(self, label: str) -> float:
        return dict(self.factors)[label]


def labelling(call_id: str, symbols: Sequence[str]) -> Labelling:
    """The labelling of call ``call_id`` for the track's ``symbols``, in the track's order."""
    symbols = list(symbols)
    if len(symbols) > len(LABELS):
        raise AnonymizeError(f"a track of {len(symbols)} instruments cannot be labelled: "
                             f"at most {len(LABELS)}")
    if len(set(symbols)) != len(symbols):
        raise AnonymizeError("the instruments of a labelling must be distinct")
    rng = np.random.default_rng(seed(call_id))
    order = [symbols[int(i)] for i in rng.permutation(len(symbols))]
    factors = rng.uniform(SCALE_LOW, SCALE_HIGH, size=len(symbols))
    labels = LABELS[:len(symbols)]
    return Labelling(labels=tuple(zip(labels, order, strict=True)),
                     factors=tuple((lab, float(f)) for lab, f in zip(labels, factors, strict=True)))


def scale(block: Mapping[str, Any], factor: float, fields: Sequence[str]) -> dict[str, Any]:
    """A copy of ``block`` with each dotted path of ``fields`` multiplied by
    ``factor``; a ``None`` (not defined) stays ``None``. A path that names
    nothing in ``block`` is refused."""
    out = copy.deepcopy(dict(block))
    for path in fields:
        *parents, last = path.split(".")
        where: Any = out
        for key in parents:
            where = where.get(key) if isinstance(where, dict) else None
        if not isinstance(where, dict) or last not in where:
            raise AnonymizeError(f"the field {path!r} is nowhere in the block")
        if where[last] is not None:
            where[last] = where[last] * factor
    return out


def anonymize(document: Mapping[str, Any], call_id: str,
              fields: Sequence[tuple[str, str]] | None = None) -> dict[str, Any]:
    """The W profile ``document`` for call ``call_id``: keyed by label in label
    order, its fields in price or volume units scaled (``fields``, default
    :data:`SCALED_FIELDS` of its version)."""
    version = document.get("version")
    if fields is None:
        if version not in SCALED_FIELDS:
            raise AnonymizeError(f"profile version {version!r} has no entry in SCALED_FIELDS")
        fields = SCALED_FIELDS[version]
    lab = labelling(call_id, document["instruments"])

    def part(name: str, block: Mapping[str, Any], factor: float) -> dict[str, Any]:
        return scale(block, factor, [p for w, p in fields if w == name])

    common = document["common"]
    cell = document["cell"]
    return {
        **{k: copy.deepcopy(v) for k, v in document.items()
           if k not in ("instruments", "common", "cell")},
        "instruments": [label for label, _ in lab.labels],
        "common": {label: part("common", common[sym], lab.factor(label))
                   for label, sym in lab.labels},
        "cell": {**{k: copy.deepcopy(v) for k, v in cell.items() if k != "instruments"},
                 "instruments": {label: part("cell", cell["instruments"][sym],
                                             lab.factor(label))
                                 for label, sym in lab.labels}},
    }
