"""The providers (DESIGN 13.5; decision 2026-10-16-m15 122; I-11, I-13).

No test here opens a socket, calls a real provider, a real model or a real
``claude`` binary: the scripted provider reads a corpus written by the test,
the OpenAI-compatible provider talks to an ``httpx.MockTransport``, and the
Claude worker runs a fake ``claude`` the test writes under its temporary
directory. Every key is a made-up string set by the test; none is read from the
real environment.
"""

import json
import logging
import math
import os
import stat
import sys
from pathlib import Path

import httpx
import pytest

from discotrade.workers import providers as pv

FAKE_NEBIUS = "nb-test-key-0123456789abcdef"
BASE = "https://worker.example.invalid/v1"
MESSAGES = [
    {"role": "system", "content": "You write one Python function."},
    {"role": "user", "content": "Propose a trend rule for cell 3."},
]


# --- ScriptedProvider (decision 122 (b)) ------------------------------------------------

CORPUS = {
    "openai/gpt-oss-120b": ["first a\n", "second a with more text\n", "third a\n"],
    "MiniMaxAI/MiniMax-M3": ["only b\n"],
}


def write_corpus(root: Path) -> Path:
    for model, texts in CORPUS.items():
        folder = root / model.replace("/", "__")
        folder.mkdir(parents=True)
        for n, text in enumerate(texts, start=1):
            (folder / f"{n:04d}.md").write_text(text, encoding="utf-8")
    return root


def test_scripted_lists_the_models_sorted_with_the_slash_restored(tmp_path):
    provider = pv.ScriptedProvider(write_corpus(tmp_path / "corpus"))
    assert provider.list_models() == sorted(CORPUS)


def test_scripted_returns_each_models_files_in_order_from_its_cursor(tmp_path):
    provider = pv.ScriptedProvider(write_corpus(tmp_path / "corpus"))
    a, b = "openai/gpt-oss-120b", "MiniMaxAI/MiniMax-M3"
    got = [provider.complete(a, MESSAGES, 100).text,
           provider.complete(b, MESSAGES, 100).text,
           provider.complete(a, MESSAGES, 100).text,
           provider.complete(a, MESSAGES, 100).text]
    assert got == [CORPUS[a][0], CORPUS[b][0], CORPUS[a][1], CORPUS[a][2]]


def test_scripted_continues_from_a_given_start(tmp_path):
    a = "openai/gpt-oss-120b"
    provider = pv.ScriptedProvider(write_corpus(tmp_path / "corpus"), start={a: 2})
    assert provider.complete(a, MESSAGES, 100).text == CORPUS[a][2]
    # A model the start does not name begins at its first file.
    assert provider.complete("MiniMaxAI/MiniMax-M3", MESSAGES, 100).text == "only b\n"


def test_scripted_counts_tokens_by_characters_over_four_and_reports_scripted(tmp_path):
    a = "openai/gpt-oss-120b"
    provider = pv.ScriptedProvider(write_corpus(tmp_path / "corpus"))
    done = provider.complete(a, MESSAGES, 100)
    chars_in = len(MESSAGES[0]["content"]) + len(MESSAGES[1]["content"])  # 30 + 32 = 62
    assert chars_in == 62
    assert done.tokens_in == 16 == math.ceil(62 / 4)
    assert done.tokens_out == 2 == math.ceil(len("first a\n") / 4)
    assert done.model_version == "scripted"
    json.dumps(done.raw)  # JSON-ready


def test_scripted_raises_provider_error_when_a_models_files_are_used_up(tmp_path):
    b = "MiniMaxAI/MiniMax-M3"
    provider = pv.ScriptedProvider(write_corpus(tmp_path / "corpus"))
    provider.complete(b, MESSAGES, 100)
    with pytest.raises(pv.ProviderError, match="MiniMaxAI/MiniMax-M3"):
        provider.complete(b, MESSAGES, 100)
    resumed = pv.ScriptedProvider(tmp_path / "corpus", start={b: 1})
    with pytest.raises(pv.ProviderError, match="MiniMaxAI/MiniMax-M3"):
        resumed.complete(b, MESSAGES, 100)


def test_scripted_a_model_without_a_directory_is_a_provider_error(tmp_path):
    provider = pv.ScriptedProvider(write_corpus(tmp_path / "corpus"))
    with pytest.raises(pv.ProviderError, match="nobody/none"):
        provider.complete("nobody/none", MESSAGES, 100)


# --- OpenAICompatProvider (decision 122 (c)) --------------------------------------------

def chat_body(model="openai/gpt-oss-120b-2026-08", text="```python\nx=1\n```\nA rule.\n"):
    return {
        "id": "chatcmpl-1",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 412, "completion_tokens": 97, "total_tokens": 509},
    }


class Recorder:
    """A MockTransport handler that records each request and answers with ``reply``."""

    def __init__(self, reply):
        self.reply = reply
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.reply(request)


def provider_with(reply, key=FAKE_NEBIUS):
    recorder = Recorder(reply)
    provider = pv.OpenAICompatProvider(BASE, key, 5.0, transport=httpx.MockTransport(recorder))
    return provider, recorder


def assert_no_key(*texts):
    for text in texts:
        assert FAKE_NEBIUS not in text


def test_openai_compat_sends_model_messages_and_max_tokens_and_reads_the_reply(caplog):
    caplog.set_level(logging.DEBUG)
    provider, rec = provider_with(lambda r: httpx.Response(200, json=chat_body()))
    done = provider.complete("openai/gpt-oss-120b", MESSAGES, 4096)
    [request] = rec.requests
    assert request.method == "POST"
    assert str(request.url) == f"{BASE}/chat/completions"
    assert json.loads(request.content) == {"model": "openai/gpt-oss-120b",
                                           "messages": MESSAGES, "max_tokens": 4096}
    assert request.headers["authorization"] == f"Bearer {FAKE_NEBIUS}"
    assert done.text == "```python\nx=1\n```\nA rule.\n"
    assert (done.tokens_in, done.tokens_out) == (412, 97)
    assert done.model_version == "openai/gpt-oss-120b-2026-08"
    assert done.raw == chat_body()
    # No key in a stored field or a log line.
    assert_no_key(json.dumps(done.raw), repr(done), caplog.text)


def test_openai_compat_lists_the_models():
    body = {"object": "list", "data": [{"id": "b/two"}, {"id": "a/one"}]}
    provider, rec = provider_with(lambda r: httpx.Response(200, json=body))
    assert provider.list_models() == ["b/two", "a/one"]
    [request] = rec.requests
    assert (request.method, str(request.url)) == ("GET", f"{BASE}/models")


def _timeout(request):
    raise httpx.ReadTimeout("timed out", request=request)


def _connect_error(request):
    raise httpx.ConnectError(f"refused, header was Bearer {FAKE_NEBIUS}", request=request)


FAILURES = {
    "status": (lambda r: httpx.Response(401, json={"error": f"bad key {FAKE_NEBIUS}"}),
               "status 401"),
    "not json": (lambda r: httpx.Response(200, text="<html>oops</html>"), "malformed"),
    "no choices": (lambda r: httpx.Response(200, json={"model": "m", "usage": {}}),
                   "malformed"),
    "no usage": (lambda r: httpx.Response(200, json={k: v for k, v in chat_body().items()
                                                      if k != "usage"}), "malformed"),
    "content not text": (lambda r: httpx.Response(200, json=chat_body(text=None)),
                         "malformed"),
    "timeout": (_timeout, "timeout"),
    "transport": (_connect_error, "transport"),
}


@pytest.mark.parametrize("case", sorted(FAILURES))
def test_openai_compat_failures_are_provider_errors_naming_model_and_kind_without_key(
        caplog, case):
    caplog.set_level(logging.DEBUG)
    reply, kind = FAILURES[case]
    provider, _ = provider_with(reply)
    with pytest.raises(pv.ProviderError) as info:
        provider.complete("openai/gpt-oss-120b", MESSAGES, 64)
    text = str(info.value)
    assert "openai/gpt-oss-120b" in text and kind in text
    assert_no_key(text, repr(info.value.args), caplog.text)
    assert info.value.__cause__ is None or FAKE_NEBIUS not in str(info.value.__cause__)


@pytest.mark.parametrize("case", ["status", "not json", "timeout"])
def test_openai_compat_list_models_failures_are_provider_errors(case):
    reply, kind = FAILURES[case]
    provider, _ = provider_with(reply)
    with pytest.raises(pv.ProviderError) as info:
        provider.list_models()
    assert kind in str(info.value)
    assert_no_key(str(info.value))


def test_openai_compat_list_models_malformed_data_is_a_provider_error():
    provider, _ = provider_with(lambda r: httpx.Response(200, json={"data": [{"name": "x"}]}))
    with pytest.raises(pv.ProviderError, match="malformed"):
        provider.list_models()


def test_openai_compat_holds_the_key_in_no_attribute():
    provider, _ = provider_with(lambda r: httpx.Response(200, json=chat_body()))
    assert_no_key(repr(provider), repr(vars(provider).get("base_url", "")))
    for name, value in vars(provider).items():
        if isinstance(value, str):
            assert FAKE_NEBIUS not in value, name


@pytest.mark.parametrize("key", ["", "   ", None])
def test_openai_compat_without_a_key_is_refused_naming_the_key(key):
    with pytest.raises(pv.ProviderError, match="NEBIUS_API_KEY"):
        pv.OpenAICompatProvider(BASE, key, 5.0, transport=httpx.MockTransport(Recorder(None)))


@pytest.mark.parametrize("base", ["", "  "])
def test_openai_compat_with_an_empty_base_url_is_refused_naming_it(base):
    with pytest.raises(pv.ProviderError, match="base_url"):
        pv.OpenAICompatProvider(base, FAKE_NEBIUS, 5.0)


def test_openai_compat_from_the_environment_reads_the_key_there(monkeypatch):
    monkeypatch.delenv(pv.KEY_ENV, raising=False)
    with pytest.raises(pv.ProviderError, match="NEBIUS_API_KEY"):
        pv.openai_compat_from_env(BASE, 5.0)
    monkeypatch.setenv(pv.KEY_ENV, FAKE_NEBIUS)
    recorder = Recorder(lambda r: httpx.Response(200, json={"data": [{"id": "m"}]}))
    provider = pv.openai_compat_from_env(BASE, 5.0, transport=httpx.MockTransport(recorder))
    assert provider.list_models() == ["m"]
    assert recorder.requests[0].headers["authorization"] == f"Bearer {FAKE_NEBIUS}"


# --- ClaudeWorkerProvider (decision 122 (d)) --------------------------------------------

CLAUDE_MODEL = "claude-worker-test-model"
#: The arguments the fake expects: the flags of the installed claude's help (2.1.300),
#: ``--max-turns`` from SPEC 17's coordinator line (decision 122 (d)).
EXPECTED_ARGS = ["--bare", "-p", "--output-format", "json", "--max-turns", "1",
                 "--tools", "", "--permission-mode", "dontAsk", "--model", CLAUDE_MODEL]
REPLY = {
    "type": "result", "subtype": "success", "is_error": False,
    "result": "```python\nx=1\n```\nA rule.\n",
    "usage": {"input_tokens": 321, "output_tokens": 45},
    "modelUsage": {"claude-worker-test-model-20260901": {"inputTokens": 321}},
}

FAKE = '''#!{python}
import json, os, sys, time
record = {{"args": sys.argv[1:], "stdin": sys.stdin.read(),
          "env_keys": sorted(os.environ)}}
with open({record!r}, "w") as f:
    json.dump(record, f)
mode = {mode!r}
if mode == "sleep":
    time.sleep(30)
if sys.argv[1:] != {expected!r}:
    sys.stderr.write("unexpected arguments\\n")
    sys.exit(64)
if mode == "fail":
    sys.exit(3)
if mode == "garbage":
    sys.stdout.write("not json at all")
    sys.exit(0)
if mode == "error":
    sys.stdout.write(json.dumps({{"type": "result", "is_error": True, "result": "x"}}))
    sys.exit(0)
sys.stdout.write(json.dumps({reply!r}))
'''


def fake_claude(tmp_path: Path, mode="ok", expected=None) -> tuple[Path, Path]:
    record = tmp_path / "record.json"
    script = tmp_path / "bin" / "claude"
    script.parent.mkdir(exist_ok=True)
    script.write_text(FAKE.format(python=sys.executable, record=str(record), mode=mode,
                                  expected=EXPECTED_ARGS if expected is None else expected,
                                  reply=REPLY), encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script, record


def test_claude_worker_passes_the_flags_the_prompt_on_stdin_and_no_worker_key(
        tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", FAKE_NEBIUS)
    monkeypatch.setenv("DATABENTO_API_KEY", "db-test-key")
    script, record = fake_claude(tmp_path)
    provider = pv.ClaudeWorkerProvider(script, CLAUDE_MODEL, 60.0)
    done = provider.complete(CLAUDE_MODEL, [MESSAGES[1]], 4096)
    seen = json.loads(record.read_text(encoding="utf-8"))
    assert seen["args"] == EXPECTED_ARGS
    assert seen["stdin"] == MESSAGES[1]["content"]
    assert "NEBIUS_API_KEY" not in seen["env_keys"]
    assert "DATABENTO_API_KEY" not in seen["env_keys"]
    assert "PATH" in seen["env_keys"]  # the rest of the harness's environment is passed
    assert done.text == REPLY["result"]
    assert (done.tokens_in, done.tokens_out) == (321, 45)
    assert done.model_version == "claude-worker-test-model-20260901"
    assert done.raw == REPLY
    assert provider.list_models() == [CLAUDE_MODEL]
    # The harness's own environment is untouched.
    assert os.environ["NEBIUS_API_KEY"] == FAKE_NEBIUS


def test_claude_worker_sends_several_messages_as_one_labelled_prompt(tmp_path):
    script, record = fake_claude(tmp_path)
    provider = pv.ClaudeWorkerProvider(script, CLAUDE_MODEL, 60.0)
    provider.complete(CLAUDE_MODEL, MESSAGES, 4096)
    seen = json.loads(record.read_text(encoding="utf-8"))
    assert seen["stdin"] == ("SYSTEM:\nYou write one Python function.\n\n"
                             "USER:\nPropose a trend rule for cell 3.")


@pytest.mark.parametrize("mode, kind", [("fail", "exit status 3"), ("garbage", "not JSON"),
                                        ("error", "error reply")])
def test_claude_worker_failures_are_provider_errors(tmp_path, mode, kind):
    script, _ = fake_claude(tmp_path, mode=mode)
    provider = pv.ClaudeWorkerProvider(script, CLAUDE_MODEL, 60.0)
    with pytest.raises(pv.ProviderError) as info:
        provider.complete(CLAUDE_MODEL, [MESSAGES[1]], 4096)
    assert CLAUDE_MODEL in str(info.value) and kind in str(info.value)


def test_claude_worker_timeout_is_a_provider_error(tmp_path):
    script, _ = fake_claude(tmp_path, mode="sleep")
    provider = pv.ClaudeWorkerProvider(script, CLAUDE_MODEL, 1.0)
    with pytest.raises(pv.ProviderError, match="timeout"):
        provider.complete(CLAUDE_MODEL, [MESSAGES[1]], 4096)


def test_claude_worker_another_model_is_a_provider_error(tmp_path):
    script, record = fake_claude(tmp_path)
    provider = pv.ClaudeWorkerProvider(script, CLAUDE_MODEL, 60.0)
    with pytest.raises(pv.ProviderError, match="other-model"):
        provider.complete("other-model", [MESSAGES[1]], 4096)
    assert not record.exists()


# --- decision 122 (f) --------------------------------------------------------------------

#: What reaches the network or starts a process; spelt in pieces so that this file
#: itself names no process call (tests/test_offline.py's listing).
REACHING = ("httpx", "sub" + "process", "os." + "system", "socket")


def test_only_providers_imports_httpx_or_starts_a_process_under_workers():
    root = Path(pv.__file__).resolve().parent
    reaching = sorted(p.name for p in root.glob("*.py")
                      if any(n in p.read_text(encoding="utf-8")
                             for n in REACHING))
    assert reaching == ["providers.py"]
