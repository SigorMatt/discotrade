"""`discotrade config check` (DESIGN 4, 18.1)."""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from discotrade.cli import REPO_ROOT, main

DISCOTRADE = Path(sys.executable).parent / "discotrade"
CONFIG = REPO_ROOT / "config"

TOP_SOURCED = ("multiplier", "tick_size", "trusted_from", "main_session")
COST_SOURCED = ("fee_per_side", "fee_bps", "spread_ticks_main", "spread_ticks_off",
                "slippage_coef")


def expected_unverified(config: Path) -> set[str]:
    """Every sourced value whose group says verified = false, read from the TOML."""
    out = set()
    for path in sorted((config / "instruments").glob("*.toml")):
        with open(path, "rb") as f:
            rec = tomllib.load(f)
        name = f"instruments/{path.name}"
        if rec["spec"]["verified"] is False:
            out |= {f"{name} {k}" for k in TOP_SOURCED if k in rec}
        if rec["cost"].get("verified") is False:
            out |= {f"{name} cost.{k}" for k in COST_SOURCED if k in rec["cost"]}
    return out


CALENDAR_SOURCED = ("week_open", "week_close", "daily_break", "day_rolls_at")


def expected_unverified_calendars(config: Path) -> set[str]:
    """Every calendar value and closure whose companions say verified = false."""
    out = set()
    for path in sorted((config / "calendars").glob("*.toml")):
        with open(path, "rb") as f:
            rec = tomllib.load(f)
        name = f"calendars/{path.name}"
        if rec.get("verified") is False:
            out |= {f"{name} {k}" for k in CALENDAR_SOURCED if k in rec}
        for i, closure in enumerate(rec.get("closure", [])):
            if closure.get("verified") is False:
                out.add(f"{name} closure.{i}")
    return out


def expected_unverified_models(config: Path) -> set[str]:
    """base_url and each model's cutoff, when their companions say verified = false
    (decision 2026-10-16-m15 123 (c))."""
    with open(config / "models.toml", "rb") as f:
        rec = tomllib.load(f)
    out = {"models.toml base_url"} if rec["verified"] is False else set()
    return out | {f"models.toml model.{m['id']}.cutoff" for m in rec["model"]
                  if m["verified"] is False}


@pytest.fixture(autouse=True)
def _no_state(monkeypatch):
    monkeypatch.delenv("DISCOTRADE_STATE", raising=False)


def test_config_check_passes_and_lists_every_unverified_value(tmp_path):
    proc = subprocess.run(
        [str(DISCOTRADE), "config", "check"],
        capture_output=True, text=True, cwd=tmp_path, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    listed = {" ".join(ln.split()[1:3]) for ln in lines if ln.startswith("unverified ")}
    expected = expected_unverified(CONFIG)
    assert len(expected) == 8 * 8
    calendars = expected_unverified_calendars(CONFIG)
    assert len(calendars) > 4
    models = expected_unverified_models(CONFIG)
    assert len(models) == 1 + 4
    assert listed == expected | calendars | models
    for model in ("openai/gpt-oss-120b", "MiniMaxAI/MiniMax-M3",
                  "nvidia/nemotron-3-super-120b-a12b", "nvidia/Nemotron-3_5-Lightning"):
        assert any(ln.startswith(f"model {model}:") for ln in lines)
    assert any(ln.startswith("run: workers claude_fallback false") for ln in lines)
    assert any(ln.startswith("calendar cme_globex:") for ln in lines)
    assert any(ln.startswith("track hourly:") for ln in lines)
    for symbol in ("MES", "MNQ", "MYM", "M2K", "MGC", "SIL", "MCL", "M6E"):
        assert any(ln.startswith(f"instrument {symbol}:") for ln in lines)
    assert any(ln.startswith("thresholds:") for ln in lines)
    assert any(ln.startswith("history:") for ln in lines)
    assert lines[-1].startswith("config check: ok")


def test_config_check_fails_on_an_invalid_value(tmp_path, capsys):
    config = tmp_path / "config"
    shutil.copytree(CONFIG, config)
    path = config / "instruments" / "MES.toml"
    path.write_text(path.read_text().replace("tick_size = 0.25", "tick_size = -1.0"))
    assert main(["--config", str(config), "config", "check"]) == 1
    err = capsys.readouterr().err
    assert "MES.toml" in err and "tick_size" in err


def test_config_check_fails_on_an_invalid_calendar(tmp_path, capsys):
    config = tmp_path / "config"
    shutil.copytree(CONFIG, config)
    path = config / "calendars" / "cme_globex.toml"
    path.write_text(path.read_text().replace('day_rolls_at = "17:00"', 'day_rolls_at = "5pm"'))
    assert main(["--config", str(config), "config", "check"]) == 1
    err = capsys.readouterr().err
    assert "cme_globex.toml" in err and "day_rolls_at" in err


def test_config_check_fails_when_a_named_calendar_has_no_record(tmp_path, capsys):
    config = tmp_path / "config"
    shutil.copytree(CONFIG, config)
    (config / "calendars" / "cme_globex.toml").unlink()
    assert main(["--config", str(config), "config", "check"]) == 1
    err = capsys.readouterr().err
    assert "has no record" in err and "cme_globex" in err


def test_config_check_fails_on_an_unknown_key(tmp_path, capsys):
    config = tmp_path / "config"
    shutil.copytree(CONFIG, config)
    path = config / "thresholds.toml"
    path.write_text(path.read_text().replace("[gaps]", "[gaps]\nmax_bars = 3"))
    assert main(["--config", str(config), "config", "check"]) == 1
    assert "unknown key 'gaps.max_bars'" in capsys.readouterr().err


def test_config_check_fails_on_a_missing_track(capsys):
    assert main(["--track", "nope", "config", "check"]) == 1
    assert "nope" in capsys.readouterr().err


def test_config_without_an_action_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        main(["config"])
    assert exc.value.code == 2


def test_config_check_lists_the_models_cutoff_dates(capsys):
    # R-14 by hand: the last day of each stated month (SPEC 17: June 2024, January,
    # February and May 2026).
    assert main(["config", "check"]) == 0
    out = capsys.readouterr().out
    for model, cutoff in (("openai/gpt-oss-120b", "2024-06-30"),
                          ("MiniMaxAI/MiniMax-M3", "2026-01-31"),
                          ("nvidia/nemotron-3-super-120b-a12b", "2026-02-28"),
                          ("nvidia/Nemotron-3_5-Lightning", "2026-05-31")):
        line = next(ln for ln in out.splitlines() if ln.startswith(f"model {model}:"))
        assert f"cutoff date {cutoff}" in line


@pytest.mark.parametrize(
    "edit, match",
    [
        (lambda s: s.replace('maker = "OpenAI"', 'maker = "OpenAI"\nprice = 0.15'),
         "unknown key 'model.price'"),
        (lambda s: s.replace('fallback = "nvidia/Nemotron-3_5-Lightning"',
                             'fallback = "nvidia/none"'), "fallback"),
        (lambda s: s.replace('id = "MiniMaxAI/MiniMax-M3"', 'id = "openai/gpt-oss-120b"'),
         "duplicate"),
        (lambda s: s.replace("pool = true", "pool = false").replace(
            'fallback = "nvidia/Nemotron-3_5-Lightning"\n', ""), "empty pool"),
    ],
    ids=["unknown key", "bad fallback", "duplicate id", "empty pool"],
)
def test_config_check_fails_on_a_bad_models_file(tmp_path, capsys, edit, match):
    config = tmp_path / "config"
    shutil.copytree(CONFIG, config)
    path = config / "models.toml"
    path.write_text(edit(path.read_text()))
    assert main(["--config", str(config), "config", "check"]) == 1
    err = capsys.readouterr().err
    assert "models.toml" in err and match in err


def test_config_check_refuses_claude_fallback_without_a_claude_worker(tmp_path, capsys):
    # Decision 123 (d): no Claude worker can be configured in this step, so true is refused.
    config = tmp_path / "config"
    shutil.copytree(CONFIG, config)
    path = config / "run.toml"
    path.write_text(path.read_text().replace("claude_fallback = false",
                                             "claude_fallback = true"))
    assert main(["--config", str(config), "config", "check"]) == 1
    err = capsys.readouterr().err
    assert "claude_fallback" in err and "Claude worker" in err
