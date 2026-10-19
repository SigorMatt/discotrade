"""The chat providers (DESIGN 13.5; decision 2026-10-16-m15 122; I-11, I-13).

A provider turns a list of chat messages into one :class:`Completion`. Three
exist: :class:`ScriptedProvider` replays a directory of canned responses (tests,
gates and replays), :class:`OpenAICompatProvider` talks ``httpx`` to an
OpenAI-compatible endpoint, and :class:`ClaudeWorkerProvider` runs one headless
Claude Code call with every tool denied. Every failure is one exception class,
:class:`ProviderError`, whose text names the model and the kind of failure and
holds no key.

This is the only module under ``discotrade.workers`` that imports ``httpx`` or
starts a process (decision 122 (f)). The worker key (decision 2026-10-16-m16
128 (b)): under ``src/``, the name ``NEBIUS_API_KEY`` appears only in this
module. Here, :func:`openai_compat_from_env` is the one function that reads the
key's value, and it reads it to build the provider. :func:`key_present` only
tests whether the key is set. :class:`ClaudeWorkerProvider` leaves the key out of
its child's environment. ``run-day`` and ``replay`` build a provider through
``discotrade.replay.make_provider`` (decision 2026-10-16-m17 137).
"""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

#: The environment variable that holds the worker provider's key (DESIGN 13.5).
KEY_ENV = "NEBIUS_API_KEY"
#: Keys of the harness that never reach a Claude worker's process (I-13).
WITHHELD_ENV = (KEY_ENV, "DATABENTO_API_KEY")
#: The version string of a scripted completion (decision 122 (b)).
SCRIPTED_VERSION = "scripted"
#: Characters per token of the scripted provider's count (decision 122 (b)).
CHARS_PER_TOKEN = 4

Message = Mapping[str, str]


class ProviderError(Exception):
    """A provider call failed; the text names the model and the kind, never a key."""


@dataclass(frozen=True)
class Completion:
    """One completion (decision 122 (a)); ``raw`` is the response body only."""

    text: str
    tokens_in: int
    tokens_out: int
    model_version: str
    raw: Mapping[str, Any]


class ChatProvider(Protocol):
    """DESIGN 13.5."""

    def list_models(self) -> list[str]: ...

    def complete(self, model: str, messages: Sequence[Message],
                 max_tokens: int) -> Completion: ...


# --- ScriptedProvider -------------------------------------------------------------------

def _tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


class ScriptedProvider:
    """Replays ``<directory>/<model with / as __>/0001.md, 0002.md, ...`` per model."""

    def __init__(self, directory: Path | str, start: Mapping[str, int] | None = None) -> None:
        self.directory = Path(directory)
        self._cursor: dict[str, int] = dict(start or {})

    def list_models(self) -> list[str]:
        if not self.directory.is_dir():
            raise ProviderError(f"scripted corpus {self.directory} is not a directory")
        return sorted(p.name.replace("__", "/") for p in self.directory.iterdir()
                      if p.is_dir())

    def complete(self, model: str, messages: Sequence[Message],
                 max_tokens: int) -> Completion:
        folder = self.directory / model.replace("/", "__")
        if not folder.is_dir():
            raise ProviderError(f"model {model}: no scripted responses in {folder}")
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == ".md")
        used = self._cursor.get(model, 0)
        if used >= len(files):
            raise ProviderError(f"model {model}: scripted responses used up "
                                f"({used} of {len(files)} files)")
        path = files[used]
        text = path.read_text(encoding="utf-8")
        self._cursor[model] = used + 1
        chars_in = "".join(m["content"] for m in messages)
        return Completion(text=text, tokens_in=_tokens(chars_in), tokens_out=_tokens(text),
                          model_version=SCRIPTED_VERSION,
                          raw={"file": path.name, "text": text})


# --- OpenAICompatProvider ---------------------------------------------------------------

def key_present() -> bool:
    """Whether the worker key is set and not blank; nothing of its value is returned."""
    return bool(os.environ.get(KEY_ENV, "").strip())


def no_key_message() -> str:
    return (f"{KEY_ENV} is not set: the worker provider needs its key in the environment "
            "(I-13); no request was made")


def _field(body: Any, *path: str | int) -> Any:
    """``body[path[0]][path[1]]...``; ``KeyError`` naming the path when one is missing."""
    here = body
    for step in path:
        try:
            here = here[step]
        except (KeyError, IndexError, TypeError):
            raise KeyError(".".join(str(s) for s in path)) from None
    return here


class OpenAICompatProvider:
    """``httpx`` against an OpenAI-compatible endpoint (decision 122 (c))."""

    def __init__(self, base_url: str, key: str | None, timeout: float,
                 transport: httpx.BaseTransport | None = None) -> None:
        if not (key or "").strip():
            raise ProviderError(no_key_message())
        if not (base_url or "").strip():
            raise ProviderError("the worker provider's base_url is empty: it is set in "
                                "config/models.toml; no request was made")
        self.base_url = base_url.strip().rstrip("/")
        self.timeout = timeout
        # The key lives only in the client's request headers, never in a field of its own.
        self._client = httpx.Client(headers={"Authorization": f"Bearer {key.strip()}"},
                                    timeout=timeout, transport=transport)

    def __repr__(self) -> str:
        return f"OpenAICompatProvider({self.base_url!r}, timeout={self.timeout!r})"

    def _call(self, model: str, method: str, path: str, payload: Any = None) -> Any:
        """The JSON body of one request; every failure a ``ProviderError`` without the key.

        Each ``ProviderError`` is raised after its ``except`` block has ended, so that
        neither ``__cause__`` nor ``__context__`` holds the httpx exception or its
        request (decision 2026-10-16-m16 128 (e)).
        """
        url = f"{self.base_url}{path}"
        failure = ""
        try:
            response = self._client.request(method, url, json=payload)
        except httpx.TimeoutException:
            failure = f"timeout after {self.timeout} s on {method} {path}"
        except httpx.HTTPError as exc:
            # Only the exception's type: its text is the transport's and is not repeated.
            failure = f"transport error on {method} {path}: {type(exc).__name__}"
        if failure:
            raise ProviderError(f"model {model}: {failure}")
        if not response.is_success:
            raise ProviderError(f"model {model}: status {response.status_code} on "
                                f"{method} {path}")
        body: Any = None
        try:
            body = response.json()
        except ValueError:
            failure = f"malformed body on {method} {path}: not JSON"
        if failure:
            raise ProviderError(f"model {model}: {failure}")
        return body

    def list_models(self) -> list[str]:
        body = self._call("(model list)", "GET", "/models")
        missing = ""
        ids: list[Any] = []
        try:
            data = _field(body, "data")
            ids = [_field(entry, "id") for entry in data]
            if not isinstance(data, list) or not all(isinstance(i, str) for i in ids):
                raise KeyError("data[].id")
        except (KeyError, TypeError) as exc:
            missing = str(exc)
        if missing:  # raised outside the except block: no context (decision 128 (e))
            raise ProviderError(f"model (model list): malformed body: no {missing}")
        return ids

    def complete(self, model: str, messages: Sequence[Message],
                 max_tokens: int) -> Completion:
        payload = {"model": model, "messages": [dict(m) for m in messages],
                   "max_tokens": max_tokens}
        body = self._call(model, "POST", "/chat/completions", payload)
        missing = ""
        text = tokens_in = tokens_out = version = None
        try:
            text = _field(body, "choices", 0, "message", "content")
            tokens_in = _field(body, "usage", "prompt_tokens")
            tokens_out = _field(body, "usage", "completion_tokens")
            version = _field(body, "model")
        except KeyError as exc:
            missing = str(exc)
        if missing:  # raised outside the except block: no context (decision 128 (e))
            raise ProviderError(f"model {model}: malformed body: no {missing}")
        if not isinstance(text, str) or not isinstance(version, str) or not all(
                isinstance(n, int) and not isinstance(n, bool) for n in (tokens_in, tokens_out)):
            raise ProviderError(f"model {model}: malformed body: a field of the wrong type")
        return Completion(text=text, tokens_in=tokens_in, tokens_out=tokens_out,
                          model_version=version, raw=body)


def openai_compat_from_env(base_url: str, timeout: float,
                           transport: httpx.BaseTransport | None = None
                           ) -> OpenAICompatProvider:
    """The provider, built with the key's value read from ``NEBIUS_API_KEY``.

    Decision 2026-10-16-m16 128 (b): under ``src/``, the name ``NEBIUS_API_KEY``
    appears only in this module. Here, this is the one function that reads the
    key's value, and it reads it to build the provider. :func:`key_present` only
    tests whether the key is set. :class:`ClaudeWorkerProvider` leaves the key out
    of its child's environment.
    """
    return OpenAICompatProvider(base_url, os.environ.get(KEY_ENV, ""), timeout,
                                transport=transport)


# --- one headless claude process (decision 2026-10-18-m20 166) -------------------------

@dataclass(frozen=True)
class ClaudeRun:
    """What one ``claude`` process gave: its exit status and its two streams."""

    returncode: int
    stdout: str
    stderr: str


class ClaudeTimeout(Exception):
    """The ``claude`` process ran past its timeout; its whole process group was killed."""


def kill_group(child: subprocess.Popen[str]) -> None:
    """SIGKILL to the child's whole process group (the child leads it: it was started in
    a new session), then reap the child (REVIEW-15 note 3; decision 166)."""
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.communicate()


def run_claude(argv: Sequence[str], prompt: str, env: Mapping[str, str],
               timeout: float) -> ClaudeRun:
    """Run ``argv`` with ``prompt`` on standard input in a new session
    (``start_new_session``), so that on a timeout every process it started is killed
    with it (decision 166). ``ClaudeTimeout`` on a timeout; ``OSError`` when it cannot
    be started. Used by :class:`ClaudeWorkerProvider` and by the coordinator's Claude
    Code form alike."""
    child = subprocess.Popen(list(argv), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=dict(env),
                             start_new_session=True)
    try:
        out, err = child.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(child)
        raise ClaudeTimeout(f"timeout after {timeout} s") from None
    return ClaudeRun(child.returncode, out, err)


# --- ClaudeWorkerProvider ---------------------------------------------------------------

def claude_arguments(model: str) -> list[str]:
    """The flags of one headless worker call (decision 122 (d)).

    Read from the installed ``claude --help`` (Claude Code 2.1.300): ``--bare``,
    ``-p``, ``--output-format json``, ``--tools ""`` (no tool available),
    ``--permission-mode dontAsk`` and ``--model``. ``--max-turns 1`` is not in that
    help; it is taken from SPEC 17's coordinator line.
    """
    return ["--bare", "-p", "--output-format", "json", "--max-turns", "1",
            "--tools", "", "--permission-mode", "dontAsk", "--model", model]


def render_prompt(messages: Sequence[Message]) -> str:
    """One message is sent as its content; several as role-labelled blocks."""
    if len(messages) == 1:
        return messages[0]["content"]
    return "\n\n".join(f"{m['role'].upper()}:\n{m['content']}" for m in messages)


class ClaudeWorkerProvider:
    """One headless Claude Code call per ``complete`` (decision 122 (d))."""

    def __init__(self, executable: Path | str, model: str, timeout: float) -> None:
        self.executable = str(executable)
        self.model = model
        self.timeout = timeout

    def list_models(self) -> list[str]:
        return [self.model]

    def complete(self, model: str, messages: Sequence[Message],
                 max_tokens: int) -> Completion:
        if model != self.model:
            raise ProviderError(f"model {model}: this Claude worker serves {self.model} only")
        env = {k: v for k, v in os.environ.items() if k not in WITHHELD_ENV}
        try:
            done = run_claude([self.executable, *claude_arguments(model)],
                              render_prompt(messages), env, self.timeout)
        except ClaudeTimeout:
            raise ProviderError(f"model {model}: timeout after {self.timeout} s") from None
        except OSError as exc:
            raise ProviderError(f"model {model}: could not start the Claude worker: "
                                f"{type(exc).__name__}") from None
        if done.returncode != 0:
            raise ProviderError(f"model {model}: the Claude worker ended with exit status "
                                f"{done.returncode}")
        try:
            body = json.loads(done.stdout)
        except ValueError:
            raise ProviderError(f"model {model}: the Claude worker's reply is not JSON"
                                ) from None
        if not isinstance(body, dict) or body.get("is_error"):
            raise ProviderError(f"model {model}: the Claude worker gave an error reply")
        try:
            text = _field(body, "result")
            tokens_in = _field(body, "usage", "input_tokens")
            tokens_out = _field(body, "usage", "output_tokens")
            used = _field(body, "modelUsage")
        except KeyError as exc:
            raise ProviderError(f"model {model}: malformed reply: no {exc}") from None
        if not isinstance(text, str) or not isinstance(used, dict) or not used or not all(
                isinstance(n, int) and not isinstance(n, bool) for n in (tokens_in, tokens_out)):
            raise ProviderError(f"model {model}: malformed reply: a field of the wrong type")
        return Completion(text=text, tokens_in=tokens_in, tokens_out=tokens_out,
                          model_version=",".join(sorted(used)), raw=body)
