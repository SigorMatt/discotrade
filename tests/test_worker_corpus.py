"""The worker corpus of the M3 gate (DESIGN 13.4, 13.5, 17.1, 18.3 G3.1 and G3.2;
decisions 138 and 122 (b) of meta/decisions/; HF-009).

A cheap check of ``tests/fixtures/worker_corpus/`` against its ``manifest.toml``,
outside the gate (decision 138 (e)): every listed response file exists and every
file under ``m3/`` and ``m3_pool/`` is listed; every Python block of a response is
byte-identical to the strategy file the manifest names (decision 104 (d): a
backend runs only a text equal to a repository file), and a response that names
no strategy holds no block; every response parses, or fails to parse with the
rule, as the manifest says, with the description it gives; the model
directories are named by decision 122 (b)'s rule (each ``/`` of the id written
``__``) after the pool models of ``tests/fixtures/config/models.toml``, ``m3/``
holding one per pool model; each new strategy is listed with a family and a
horizon of the track ``test_synth``. Two figures of decision 138 (c) and (d)
are checked from the files alone: the injected description holds a backtick
and angle brackets, and the budget response's own token count by the scripted
provider's rule (``ceil(characters / 4)``) plus ``worker_max_output_tokens``
exceeds ``worker_tokens_per_day``, both read from the production
``config/thresholds.toml``. What a replay makes of the corpus (the outcomes,
days and attempts the manifest records) is proven by the M3 gate, not here.

No file is written, no clock is read, no random draw is made and nothing runs a
strategy.
"""

from __future__ import annotations

import math
import tomllib

import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT

from discotrade.config import load_models, load_thresholds, load_track_config
from discotrade.workers import parse
from discotrade.workers.providers import ScriptedProvider
from discotrade.workers.registry import description_cap, sanitize

CORPUS = REPO_ROOT / "tests" / "fixtures" / "worker_corpus"
MANIFEST = CORPUS / "manifest.toml"
NEW_STRATEGIES = CORPUS / "strategies"
OLD_STRATEGIES = REPO_ROOT / "tests" / "fixtures" / "strategies"
PRODUCTION = REPO_ROOT / "config" / "thresholds.toml"
SUBDIRS = ("m3", "m3_pool")
PARSES = ("ok", parse.NO_BLOCK, parse.NO_DESCRIPTION)


@pytest.fixture(scope="module")
def manifest():
    with open(MANIFEST, "rb") as f:
        return tomllib.load(f)


@pytest.fixture(scope="module")
def responses(manifest):
    return manifest["response"]


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds(FIXTURE_CONFIG / "thresholds_gate.toml")


def dir_name(model: str) -> str:
    return model.replace("/", "__")


def test_every_listed_file_exists_and_every_file_is_listed(responses):
    listed = [r["file"] for r in responses]
    assert len(listed) == len(set(listed))
    for name in listed:
        assert (CORPUS / name).is_file(), name
    present = sorted(p.relative_to(CORPUS).as_posix()
                     for sub in SUBDIRS for p in (CORPUS / sub).rglob("*") if p.is_file())
    assert present == sorted(listed)


def test_directories_named_after_the_pool_models(responses):
    pool = [m.id for m in load_models(FIXTURE_CONFIG / "models.toml").pool]
    assert len(pool) == 3
    m3 = sorted(p.name for p in (CORPUS / "m3").iterdir())
    assert m3 == sorted(dir_name(m) for m in pool)
    for sub in SUBDIRS:
        assert set(ScriptedProvider(CORPUS / sub).list_models()) <= set(pool), sub
    assert len(list((CORPUS / "m3_pool").iterdir())) == 1
    for r in responses:
        sub, folder, name = r["file"].split("/")
        assert sub in SUBDIRS and folder == dir_name(r["model"]) and r["model"] in pool, r
        assert len(name) == len("0001.md") and name.endswith(".md") and name[:4].isdigit()
    for sub in SUBDIRS:
        for folder in (CORPUS / sub).iterdir():
            names = sorted(p.name for p in folder.iterdir())
            assert names == [f"{k:04d}.md" for k in range(1, len(names) + 1)], folder


def test_every_block_is_byte_identical_to_its_strategy_file(responses):
    for r in responses:
        text = (CORPUS / r["file"]).read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        found = parse.blocks(text)
        if r["strategy"] == "none":
            assert found == [], r["file"]
            continue
        path = REPO_ROOT / r["strategy"]
        assert path.parent in (NEW_STRATEGIES, OLD_STRATEGIES), r["file"]
        expected = path.read_bytes()
        assert len(found) == 1, r["file"]
        for start, end in found:
            assert "".join(lines[start + 1:end]).encode("utf-8") == expected, r["file"]


def test_every_response_parses_as_the_manifest_says(responses, thresholds):
    for r in responses:
        assert r["parse"] in PARSES, r["file"]
        out = parse.parse((CORPUS / r["file"]).read_text(encoding="utf-8"), thresholds)
        if r["parse"] == "ok":
            assert isinstance(out, parse.Parsed), r["file"]
            assert out.source == (REPO_ROOT / r["strategy"]).read_text(encoding="utf-8")
            assert out.description == sanitize(r["description"], description_cap(thresholds))
        else:
            assert isinstance(out, parse.Failure) and out.rule == r["parse"], r["file"]
            assert r["description"] == ""


def test_strategies_listed_with_a_family_and_horizon_of_the_track(manifest, responses):
    track = load_track_config(FIXTURE_CONFIG, "test_synth").track
    entries = manifest["strategy"]
    files = [s["file"] for s in entries]
    assert sorted(files) == sorted(f"tests/fixtures/worker_corpus/strategies/{p.name}"
                                   for p in NEW_STRATEGIES.glob("*.py"))
    for s in entries:
        assert s["family"] in track.families and s["horizon"] in dict(track.horizons), s
    used = {r["strategy"] for r in responses}
    assert set(files) <= used


def test_the_injected_description_and_the_budget_response(responses):
    injected = [r for r in responses
                if "`" in r["description"] and "<" in r["description"]
                and ">" in r["description"]]
    assert injected and all(r["parse"] == "ok" and r["file"].startswith("m3/")
                            for r in injected)
    production = load_thresholds(PRODUCTION)
    budget = [r for r in responses if r.get("budget")]
    assert len(budget) == 1 and budget[0]["file"].startswith("m3_pool/")
    text = (CORPUS / budget[0]["file"]).read_text(encoding="utf-8")
    prose = text[:text.index("```")]
    assert prose.strip() and "`" not in prose
    tokens_out = math.ceil(len(text) / 4)
    assert tokens_out + int(production["budgets.worker_max_output_tokens"]) > \
        int(production["budgets.worker_tokens_per_day"])
    failing = [r for r in responses
               if r["file"].startswith("m3_pool/") and r["outcome"].startswith("invalid:")]
    assert len(failing) >= int(production["pool.fail_window"])
