"""``discotrade doctor`` in step S0.2 (DESIGN 19.3; decision 2026-10-12 15; I-11, I-13).

Offline only: without the key ``--live vendor`` refuses, exits 1 and makes no
request; plain ``doctor`` and every check name not built in this step are usage
errors naming step S5.1. Its live behaviour is run here against the fake client
of ``tests/fakes/`` only, which proves the printing and the arithmetic, not the
real service (that is live check L1 itself).
"""

from datetime import UTC, datetime

import pytest
from fakes.vendor_world import FAKE_KEY, SYMBOL, TRACK, install, make_config, make_vendor

from discotrade.cli import main
from discotrade.sources.vendor import KEY_ENV

AS_OF = "2019-04-01T05:00:00+00:00"


@pytest.fixture
def config(tmp_path):
    return make_config(tmp_path / "config")


def doctor(*args, config=None, track=None):
    argv = ["--as-of", AS_OF]
    if config is not None:
        argv += ["--config", str(config)]
    if track is not None:
        argv += ["--track", track]
    return main([*argv, "doctor", *args])


@pytest.mark.parametrize("key", [None, ""])
def test_live_vendor_without_the_key_refuses_exit_1_and_makes_no_request(monkeypatch, capsys,
                                                                         config, key):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=key)
    assert doctor("--live", "vendor", config=config, track=TRACK) == 1
    err = capsys.readouterr().err
    assert KEY_ENV in err and "no request was made" in err
    assert vendor.calls == [] and vendor.keys == []


def test_live_vendor_without_the_key_refuses_on_the_repository_config(monkeypatch, capsys):
    vendor = make_vendor()
    install(monkeypatch, vendor, key=None)
    assert doctor("--live", "vendor") == 1
    assert KEY_ENV in capsys.readouterr().err
    assert vendor.calls == []


def test_plain_doctor_is_a_usage_error_naming_s5_1(capsys):
    assert doctor() == 2
    assert "S5.1" in capsys.readouterr().err


# "sandbox" (L5) left this list: decision 2026-10-14-m13 103 (d) builds it in step S2.2.
# "workers" (L3) left it: decision 2026-10-16-m15 122 (e) builds its offline behaviour.
@pytest.mark.parametrize("name", ["coordinator", "issues", "costs",
                                  "planted", "nonsense"])
def test_another_check_is_a_usage_error_naming_s5_1(monkeypatch, capsys, name):
    monkeypatch.delenv(KEY_ENV, raising=False)
    assert doctor("--live", name) == 2
    assert "S5.1" in capsys.readouterr().err


def test_live_vendor_with_the_fake_client_reports_each_l1_item(monkeypatch, capsys, config):
    vendor = make_vendor(dataset_end=datetime(2019, 3, 31, 20, tzinfo=UTC))
    install(monkeypatch, vendor)
    assert doctor("--live", "vendor", config=config, track=TRACK) == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith(f"{SYMBOL}: ")]
    assert any("cost estimate for the full history 2019-01-07" in ln and "0.25 USD" in ln
               for ln in lines)
    assert any("delay 9:00:00, within the embargo" in ln for ln in lines)
    assert any("contract resolved" in ln and "SYNA-2019-06" in ln for ln in lines)
    assert any("gap fraction" in ln for ln in lines)
    assert "doctor --live vendor: ok" in out
    assert FAKE_KEY not in out


def test_live_vendor_reports_a_failing_vendor_without_the_key(monkeypatch, capsys, config):
    vendor = make_vendor()
    vendor.fail_with = f"denied for {FAKE_KEY}"
    install(monkeypatch, vendor)
    assert doctor("--live", "vendor", config=config, track=TRACK) == 1
    captured = capsys.readouterr()
    assert f"{SYMBOL}: FAIL" in captured.out and "<redacted>" in captured.out
    assert FAKE_KEY not in captured.out + captured.err


def test_live_sandbox_with_an_empty_path_refuses_naming_no_runtime_and_starts_nothing(
        monkeypatch, capsys, tmp_path):
    """L5 offline (decision 2026-10-14-m13 103 (d)): no container runtime on PATH."""
    import tempfile

    from discotrade.sandbox import container

    def refuse(*args, **kwargs):
        raise AssertionError(f"a process was started: {args}")

    # The two places container.py starts a process: the runtime's commands and a run.
    monkeypatch.setattr(container, "_runtime", refuse)
    monkeypatch.setattr(container.ContainerSandbox, "run_program", refuse)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("PATH", "")
    assert doctor("--live", "sandbox") == 1
    captured = capsys.readouterr()
    assert "no container runtime found" in captured.err
    assert "doctor --live sandbox" in captured.err
    assert "PASS" not in captured.out and list(tmp_path.iterdir()) == []


# --- L3 workers, offline (decision 2026-10-16-m15 122 (e); I-11, I-13) ------------------

FAKE_NEBIUS = "nb-test-key-0123456789abcdef"
MODELS_TOML = """base_url = "{base}"
checked = "2026-10-11"
source = "written by the test"
verified = false

[[model]]
id = "maker-a/model-one"
pool = true

[[model]]
id = "maker-b/model-two"
pool = true
fallback = "maker-b/model-two-small"

[[model]]
id = "maker-b/model-two-small"
pool = false
"""
WORKERS_BASE = "https://worker.example.invalid/v1"


class ModelList:
    """A MockTransport handler answering ``GET /models`` with ``ids``; records requests."""

    def __init__(self, ids):
        self.ids = ids
        self.requests = []

    def __call__(self, request):
        import httpx
        self.requests.append(request)
        return httpx.Response(200, json={"data": [{"id": i} for i in self.ids]})


@pytest.fixture
def no_request(monkeypatch):
    """Any request through httpx fails the test; the doctor's transport is a recorder."""
    import httpx

    from discotrade import doctor as doc

    def refuse(*args, **kwargs):
        raise AssertionError("a request was made")

    monkeypatch.setattr(httpx.Client, "send", refuse)
    recorder = ModelList([])
    monkeypatch.setattr(doc, "WORKERS_TRANSPORT", httpx.MockTransport(recorder))
    return recorder


def workers_config(tmp_path, base=WORKERS_BASE, models=True):
    config = make_config(tmp_path / "config")
    if models:
        (config / "models.toml").write_text(MODELS_TOML.format(base=base), encoding="utf-8")
    else:  # the fixture configuration holds models.toml since decision 123 (b)
        (config / "models.toml").unlink(missing_ok=True)
    return config


@pytest.mark.parametrize("key", [None, ""])
@pytest.mark.parametrize("on", ["repository", "copy"])
def test_live_workers_without_the_key_prints_one_line_exits_1_no_request(
        monkeypatch, capsys, tmp_path, no_request, key, on):
    if key is None:
        monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    else:
        monkeypatch.setenv("NEBIUS_API_KEY", key)
    config = workers_config(tmp_path) if on == "copy" else None
    assert doctor("--live", "workers", config=config,
                  track=TRACK if config else None) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1, lines
    assert "doctor --live workers: FAIL" in lines[0]
    assert "NEBIUS_API_KEY" in lines[0] and "no request was made" in lines[0]
    assert no_request.requests == []


def test_live_workers_without_models_toml_prints_one_line_exits_1_no_request(
        monkeypatch, capsys, tmp_path, no_request):
    monkeypatch.setenv("NEBIUS_API_KEY", FAKE_NEBIUS)
    config = workers_config(tmp_path, models=False)
    assert doctor("--live", "workers", config=config, track=TRACK) == 1
    captured = capsys.readouterr()
    lines = captured.err.splitlines()
    assert len(lines) == 1 and "models.toml" in lines[0], lines
    assert captured.out == "" and no_request.requests == []
    assert FAKE_NEBIUS not in captured.err


def test_live_workers_with_an_empty_base_url_prints_one_line_exits_1_no_request(
        monkeypatch, capsys, tmp_path, no_request):
    monkeypatch.setenv("NEBIUS_API_KEY", FAKE_NEBIUS)
    config = workers_config(tmp_path, base="")
    assert doctor("--live", "workers", config=config, track=TRACK) == 1
    captured = capsys.readouterr()
    lines = captured.err.splitlines()
    assert len(lines) == 1 and "base_url" in lines[0], lines
    assert no_request.requests == []


def _with_list(monkeypatch, ids):
    import httpx

    from discotrade import doctor as doc
    recorder = ModelList(ids)
    monkeypatch.setattr(doc, "WORKERS_TRANSPORT", httpx.MockTransport(recorder))
    monkeypatch.setenv("NEBIUS_API_KEY", FAKE_NEBIUS)
    return recorder


def test_live_workers_prints_the_pool_against_the_providers_list(monkeypatch, capsys,
                                                                 tmp_path):
    recorder = _with_list(monkeypatch, ["maker-b/model-two-small", "maker-a/model-one",
                                        "maker-b/model-two", "maker-c/other"])
    config = workers_config(tmp_path)
    assert doctor("--live", "workers", config=config, track=TRACK) == 0
    out = capsys.readouterr().out
    [request] = recorder.requests
    assert str(request.url) == f"{WORKERS_BASE}/models"
    assert "maker-a/model-one (pool): listed" in out
    assert "maker-b/model-two (pool): listed" in out
    assert "maker-b/model-two-small (fallback): listed" in out
    assert "doctor --live workers: ok" in out
    assert FAKE_NEBIUS not in out


def test_live_workers_reports_a_model_the_provider_does_not_list(monkeypatch, capsys,
                                                                 tmp_path):
    _with_list(monkeypatch, ["maker-a/model-one", "maker-b/model-two-small"])
    config = workers_config(tmp_path)
    assert doctor("--live", "workers", config=config, track=TRACK) == 1
    out = capsys.readouterr().out
    assert "maker-b/model-two (pool): NOT listed" in out
    assert "doctor --live workers: FAIL, 1 of 3 configured models not listed" in out


@pytest.mark.parametrize("key", [None, "   "], ids=["unset", "spaces"])
def test_live_workers_without_a_usable_key_never_calls_the_transport(monkeypatch, capsys,
                                                                     tmp_path, key):
    """Decision 2026-10-16-m16 128 (a), (c): the key check is ``providers.key_present``."""
    import httpx

    from discotrade import doctor as doc

    def fail(request):
        pytest.fail(f"the transport was called: {request.method} {request.url}")

    monkeypatch.setattr(doc, "WORKERS_TRANSPORT", httpx.MockTransport(fail))
    if key is None:
        monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    else:
        monkeypatch.setenv("NEBIUS_API_KEY", key)
    config = workers_config(tmp_path)
    assert doctor("--live", "workers", config=config, track=TRACK) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1, lines
    assert lines[0].startswith("doctor --live workers: FAIL:")
    assert "no request was made" in lines[0]
