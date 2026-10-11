"""Thresholds and frozen config with their histories (DESIGN 4.3; I-10)."""

import json
import shutil
import tomllib
from pathlib import Path

import pytest

from discotrade.cli import REPO_ROOT
from discotrade.config import (
    ConfigError,
    frozen_drift,
    frozen_snapshot,
    load_changes,
    load_thresholds,
    threshold_drift,
)

CONFIG = REPO_ROOT / "config"
FIXTURES = REPO_ROOT / "tests" / "fixtures"
THRESHOLDS = CONFIG / "thresholds.toml"
V1 = FIXTURES / "thresholds_v1.toml"
GATE = FIXTURES / "config" / "thresholds_gate.toml"
FROZEN = FIXTURES / "config_frozen.json"

# DESIGN 4.3, written out here so a test fails if the frozen copy is not it.
DESIGN_THRESHOLDS = {
    "validation": {
        "max_params": 5, "max_lines": 60, "grid_max_params": 2, "grid_max_values": 3,
        "call_p95_ms": 50, "call_max_ms": 500, "min_changes_w": 30, "corr_max": 0.7,
        "description_max_chars": 200,
    },
    "admission": {"min_trades_t": 30},
    "lifecycle": {
        "dormant_window_days": 30, "retire_dormant_days": 365, "revival_min_dormant_days": 5,
    },
    "controls": {"random_pool": 50, "match_window_days": 30, "match_min_live": 3},
    "gaps": {"max_fraction": 0.01},
    "journal": {"recompute_sample": 20},
    "alerts": {
        "persistent_min_days": 60, "persistent_base_percentile": 0.95,
        "false_alerts_per_year": 0.5, "group_days": 120, "group_level": 0.05,
        "group_bootstrap": 1000, "rank_blocks": 12, "rank_level": 0.05,
        "rank_min_population": 5, "revival_min_days": 60, "cost_stale_days": 90,
        "min_valid_candidates": 5, "valid_candidates_window_days": 14,
        "no_finding_months": 12,
    },
    "pool": {"fail_window": 20, "fail_rate": 0.5},
    "coordinator": {"brief_max_chars": 600, "weak_window_days": 30},
    "stage_gate": {"min_clean_days": 126},
    "budgets": {
        "worker_tokens_per_day": 60000, "coordinator_tokens_per_day": 40000,
        "worker_max_output_tokens": 8000,
    },
    "history": [{"date": "2026-10-11", "key": "*", "reason": "starting values from SPEC.md v1"}],
}

# DESIGN 18.2: the gate thresholds differ from production in these keys only.
GATE_CHANGES = {
    "validation.min_changes_w": 10,
    "admission.min_trades_t": 10,
    "lifecycle.dormant_window_days": 15,
    "alerts.persistent_min_days": 30,
    "alerts.group_days": 40,
    "alerts.rank_blocks": 6,
    "alerts.revival_min_days": 10,
}


def raw(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# --- thresholds --------------------------------------------------------------


def test_frozen_copy_is_the_design():
    assert raw(V1) == DESIGN_THRESHOLDS
    assert list(raw(V1)) == list(DESIGN_THRESHOLDS)


def test_production_starts_as_the_design():
    # The production file may drift later, with history; the starting values are
    # pinned by the frozen copy and the history test below.
    assert raw(THRESHOLDS)["history"][0] == DESIGN_THRESHOLDS["history"][0]


def test_thresholds_history():
    """DESIGN 4.3: a value that differs from the frozen copy needs a history entry."""
    assert threshold_drift(load_thresholds(THRESHOLDS), load_thresholds(V1)) == []


def test_threshold_values_typed_and_addressable():
    t = load_thresholds(THRESHOLDS)
    assert t["validation.max_params"] == 5
    assert t["gaps.max_fraction"] == 0.01
    assert len(t.values) == sum(len(v) for k, v in DESIGN_THRESHOLDS.items() if k != "history")
    with pytest.raises(KeyError):
        t["validation.nope"]


V1_TEXT = V1.read_text()


def test_history_check_fails_on_an_unrecorded_change(tmp_path):
    path = write(tmp_path / "t.toml", V1_TEXT.replace("max_params = 5", "max_params = 6"))
    problems = threshold_drift(load_thresholds(path), load_thresholds(V1))
    assert len(problems) == 1 and "validation.max_params" in problems[0]


def test_history_check_accepts_a_recorded_change(tmp_path):
    text = V1_TEXT.replace("max_params = 5", "max_params = 6") + (
        '\n[[history]]\ndate = "2026-11-01"\nkey = "validation.max_params"\n'
        'old = 5\nnew = 6\nreason = "test"\n'
    )
    path = write(tmp_path / "t.toml", text)
    assert threshold_drift(load_thresholds(path), load_thresholds(V1)) == []


def test_history_check_reads_the_last_entry_for_the_key(tmp_path):
    entry = (
        '\n[[history]]\ndate = "{d}"\nkey = "validation.max_params"\n'
        'old = {o}\nnew = {n}\nreason = "test"\n'
    )
    text = (
        V1_TEXT.replace("max_params = 5", "max_params = 6")
        + entry.format(d="2026-11-01", o=5, n=6)
        + entry.format(d="2026-12-01", o=6, n=7)
    )
    path = write(tmp_path / "t.toml", text)
    problems = threshold_drift(load_thresholds(path), load_thresholds(V1))
    assert len(problems) == 1 and "validation.max_params" in problems[0]


@pytest.mark.parametrize(
    "edit, match",
    [
        (lambda s: s.replace("max_params = 5", "max_params = 5\nmax_bars = 9"),
         "unknown key 'validation.max_bars'"),
        (lambda s: s + "\n[extra]\nx = 1\n", "unknown key 'extra'"),
        (lambda s: s.replace("max_lines = 60\n", ""), "missing key 'validation.max_lines'"),
        (lambda s: s.replace("max_lines = 60", 'max_lines = "60"'), "validation.max_lines"),
        (lambda s: s.replace("max_lines = 60", "max_lines = 60.5"), "validation.max_lines"),
        (lambda s: s.replace('key = "*"', 'key = "*"\nwho = "me"'), "unknown key 'history.who'"),
        (lambda s: s + '\n[[history]]\ndate = "2026-11-01"\nkey = "nope.x"\nreason = "r"\n',
         "nope.x"),
        (lambda s: s + '\n[[history]]\ndate = "2026-11-01"\nkey = "gaps.max_fraction"\n'
         'reason = "r"\n', "new"),
    ],
)
def test_threshold_refusals(tmp_path, edit, match):
    path = write(tmp_path / "t.toml", edit(V1_TEXT))
    with pytest.raises(ConfigError, match=match):
        load_thresholds(path)


def test_float_threshold_accepts_an_integer(tmp_path):
    path = write(tmp_path / "t.toml", V1_TEXT.replace("corr_max = 0.7", "corr_max = 1"))
    t = load_thresholds(path)
    assert t["validation.corr_max"] == 1.0 and isinstance(t["validation.corr_max"], float)


def test_gate_thresholds_differ_in_the_listed_keys_only():
    prod = load_thresholds(THRESHOLDS)
    gate = load_thresholds(GATE)
    assert [k for k, _ in prod.values] == [k for k, _ in gate.values]
    differing = {k: gate[k] for k, v in prod.values if gate[k] != v}
    assert differing == GATE_CHANGES
    assert raw(GATE)["history"] == raw(THRESHOLDS)["history"]


# --- the frozen-config map and config/HISTORY.toml ---------------------------


def test_history_file_is_empty():
    assert (CONFIG / "HISTORY.toml").is_file()
    assert load_changes(CONFIG / "HISTORY.toml") == ()


def test_frozen_map_covers_track_and_instruments():
    frozen = json.loads(FROZEN.read_text())
    assert "config/tracks/hourly.toml" in frozen
    for symbol in ("MES", "MNQ", "MYM", "M2K", "MGC", "SIL", "MCL", "M6E"):
        assert frozen[f"config/instruments/{symbol}.toml"]["cost.fee_per_side"] > 0
    assert frozen["config/tracks/hourly.toml"]["horizons.short"] == [1, 6]


def test_frozen_config_matches_map_and_history():
    """DESIGN 4.3: a frozen value that differs from the map needs a change entry."""
    frozen = json.loads(FROZEN.read_text())
    changes = load_changes(CONFIG / "HISTORY.toml")
    assert frozen_drift(REPO_ROOT, frozen, changes) == []


@pytest.fixture
def repo(tmp_path):
    """A copy of the repository's frozen config, its map, and an empty history."""
    shutil.copytree(CONFIG / "instruments", tmp_path / "config" / "instruments")
    shutil.copytree(CONFIG / "tracks", tmp_path / "config" / "tracks")
    (tmp_path / "meta" / "decisions").mkdir(parents=True)
    write(tmp_path / "meta" / "decisions" / "2026-11-01-fee.md", "approved\n")
    return tmp_path, frozen_snapshot(tmp_path)


def change(file, key, new, decision="meta/decisions/2026-11-01-fee.md", old="0.61"):
    new_line = f"new = {new}\n" if new is not None else ""
    return (
        f'[[change]]\ndate = "2026-11-01"\nfile = "{file}"\nkey = "{key}"\nold = {old}\n'
        f'{new_line}reason = "r"\ndecision = "{decision}"\n'
    )


def edit_fee(root):
    path = root / "config" / "instruments" / "MES.toml"
    path.write_text(path.read_text().replace("fee_per_side = 0.61", "fee_per_side = 0.70"))


MES = "config/instruments/MES.toml"


def test_frozen_unrecorded_change_fails(repo):
    root, frozen = repo
    edit_fee(root)
    problems = frozen_drift(root, frozen, ())
    assert len(problems) == 1 and MES in problems[0] and "cost.fee_per_side" in problems[0]


def test_frozen_recorded_change_passes(repo):
    root, frozen = repo
    edit_fee(root)
    path = write(root / "config" / "HISTORY.toml", change(MES, "cost.fee_per_side", 0.70))
    assert frozen_drift(root, frozen, load_changes(path)) == []


def test_frozen_change_with_wrong_new_fails(repo):
    root, frozen = repo
    edit_fee(root)
    path = write(root / "config" / "HISTORY.toml", change(MES, "cost.fee_per_side", 0.80))
    assert len(frozen_drift(root, frozen, load_changes(path))) == 1


def test_frozen_change_without_existing_decision_fails(repo):
    root, frozen = repo
    edit_fee(root)
    text = change(MES, "cost.fee_per_side", 0.70, decision="meta/decisions/missing.md")
    path = write(root / "config" / "HISTORY.toml", text)
    problems = frozen_drift(root, frozen, load_changes(path))
    assert len(problems) == 1 and "decision" in problems[0]


def test_frozen_new_file_needs_an_entry(repo):
    root, frozen = repo
    shutil.copy(root / "config" / "tracks" / "hourly.toml",
                root / "config" / "tracks" / "second.toml")
    problems = frozen_drift(root, frozen, ())
    assert len(problems) == 1 and "config/tracks/second.toml" in problems[0]
    path = write(
        root / "config" / "HISTORY.toml",
        change("config/tracks/second.toml", "*", None, old='"none"'),
    )
    assert frozen_drift(root, frozen, load_changes(path)) == []


def test_frozen_removed_file_fails(repo):
    root, frozen = repo
    (root / "config" / "instruments" / "SIL.toml").unlink()
    problems = frozen_drift(root, frozen, ())
    assert any("config/instruments/SIL.toml" in p for p in problems)


@pytest.mark.parametrize(
    "text, match",
    [
        ('[[change]]\ndate = "2026-11-01"\nfile = "f"\nkey = "k"\nnew = 1\nreason = "r"\n'
         'decision = "d"\nwho = "me"\n', "unknown key 'change.who'"),
        ('[[change]]\ndate = "2026-11-01"\nfile = "f"\nkey = "k"\nnew = 1\nreason = "r"\n',
         "missing key 'change.decision'"),
        ('[other]\nx = 1\n', "unknown key 'other'"),
        ('[[change]]\ndate = "soon"\nfile = "f"\nkey = "k"\nnew = 1\nreason = "r"\n'
         'decision = "d"\n', "change.date"),
    ],
)
def test_history_file_refusals(tmp_path, text, match):
    path = write(tmp_path / "HISTORY.toml", text)
    with pytest.raises(ConfigError, match=match):
        load_changes(path)
