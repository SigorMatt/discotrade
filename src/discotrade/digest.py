"""The digest page and the issue sinks (DESIGN 15.4, 19.3 L6; decisions 2026-10-19-m22
178 and 179 (a), (b); I-8, I-11, I-13).

- ``IssueSink``: ``open(title, body, labels)`` opens one issue and returns where it
  went (DESIGN 15.4).
- ``FileIssueSink(directory, track)``: each issue is one file,
  ``<directory>/<track>/<n>.md``, ``n`` the lowest positive integer whose file does
  not exist, written as four digits; its bytes are ``title: <title>``, ``labels:
  <labels joined by ", ">``, an empty line, then the body ending with one newline.
  ``open`` returns the file's path as text (decision 178 (a)).
- ``GhIssueSink(settings, state_dir)``: ``gh issue create --title <title>
  --body-file <file> --label <label>...`` with the state directory as its working
  directory, so that ``gh`` takes the repository from the state repository's
  remote. The body file lives in a temporary directory outside the state directory
  and is removed afterwards. The child is started in a new session and a timeout
  kills its whole process group (decision 166); its environment is the harness's
  without ``workers.providers.WITHHELD_ENV``, and the sink reads no secret itself.
  An exit status other than 0, a timeout or a start that fails raises ``IssueError``
  naming the cause. ``open`` returns the last non-empty line ``gh`` prints (decision
  178 (b)). The flags are those of the installed ``gh issue create --help`` (gh
  2.92.0): ``-t, --title string``, ``-F, --body-file file`` and ``-l, --label
  name``; ``close`` runs ``gh issue close {<number> | <url>}`` for live check L6.
- ``issue_labels(labels, kind)``: the settings' labels, then the alert's class,
  ``finding`` for ``alerts.FINDING_KINDS`` and ``health`` for every other kind, then
  the kind (decision 178 (c)).
- ``render(track, D, fired, prose, tokens, budget)``: the page of a day on which at
  least one entry fired: ``# <track> <D>``; the coordinator's prose as written; one
  section per fired entry in the fired list's order, ``## <kind> — <subject>``, with
  a two-column table of every key of its payload, sorted, nested objects flattened
  as dotted keys, each value as ``ledger.line`` writes it; then ``Coordinator tokens:
  <sum> of <budget>``. Every number on the page comes from the payloads and the
  budget, rendered here (DESIGN 14.3; decision 179 (a)). The prose is the
  coordinator's ``write_digest`` over ``alert_payloads(fired)``, kind and subject
  only (I-8; decision 179 (b)). Nothing the day calls uses this module yet.
- ``--issues``: ``none``, ``gh`` or ``file:<directory>`` (decision 178 (d));
  ``has_origin`` tells whether a state repository has a remote named ``origin``.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from discotrade import alerts, ledger
from discotrade.config import IssueSettings
from discotrade.coordinator import AlertPayload

#: The values of ``--issues`` (decision 178 (d)): no issue, the ``gh`` sink, or the
#: file sink under ``file:<directory>``.
ISSUES_NONE, ISSUES_GH, FILE_PREFIX = "none", "gh", "file:"
#: The class labels of an issue (decision 178 (c)).
FINDING, HEALTH = "finding", "health"
#: The remote a state repository pushes to and ``gh`` takes the repository from.
ORIGIN = "origin"


class IssueError(Exception):
    """An issue that could not be opened; the text names the cause, never a secret."""


class IssueSink(Protocol):
    def open(self, title: str, body: str, labels: list[str]) -> str: ...


def issue_labels(labels: Sequence[str], kind: str) -> list[str]:
    """``labels``, then ``finding`` or ``health`` (the class of ``kind``), then ``kind``."""
    return [*labels, FINDING if kind in alerts.FINDING_KINDS else HEALTH, kind]


class FileIssueSink:
    """Each issue as one file under ``<directory>/<track>/`` (decision 178 (a))."""

    def __init__(self, directory: Path, track: str) -> None:
        self.directory = Path(directory)
        self.track = track

    def open(self, title: str, body: str, labels: list[str]) -> str:
        folder = self.directory / self.track
        folder.mkdir(parents=True, exist_ok=True)
        text = f"title: {title}\nlabels: {', '.join(labels)}\n\n{body.rstrip(chr(10))}\n"
        n = 1
        while True:
            path = folder / f"{n:04d}.md"
            try:
                with path.open("xb") as f:
                    f.write(text.encode("utf-8"))
            except FileExistsError:
                n += 1
                continue
            return str(path)


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


class GhIssueSink:
    """``gh issue create`` against the state repository's remote (decision 178 (b))."""

    def __init__(self, settings: IssueSettings, state_dir: Path) -> None:
        self.settings = settings
        self.state_dir = Path(state_dir)

    def _gh(self, args: Sequence[str], stdout_only: bool = False) -> str:
        """Run ``gh`` with ``args``; the last non-empty line of its standard output (or,
        unless ``stdout_only``, of its standard error when the output has none)."""
        from discotrade.workers.providers import WITHHELD_ENV, kill_group

        what = f"gh {' '.join(args[:2])}"
        env = {k: v for k, v in os.environ.items() if k not in WITHHELD_ENV}
        try:
            child = subprocess.Popen(
                [self.settings.binary, *args], stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                cwd=self.state_dir, start_new_session=True)
        except OSError as exc:
            raise IssueError(f"{what}: {self.settings.binary!r} could not be started: "
                             f"{type(exc).__name__}") from None
        try:
            out, err = child.communicate(timeout=self.settings.timeout_seconds)
        except subprocess.TimeoutExpired:
            kill_group(child)
            raise IssueError(f"{what}: timeout after {self.settings.timeout_seconds} s; its "
                             "process group was killed") from None
        if child.returncode != 0:
            said = _last_line(err)
            raise IssueError(f"{what}: exit status {child.returncode}"
                             + (f": {said}" if said else ""))
        return _last_line(out) if stdout_only else (_last_line(out) or _last_line(err))

    def open(self, title: str, body: str, labels: list[str]) -> str:
        with tempfile.TemporaryDirectory(prefix="discotrade-issue-") as folder:
            body_file = Path(folder) / "body.md"
            body_file.write_text(body, encoding="utf-8")
            args = ["issue", "create", "--title", title, "--body-file", str(body_file)]
            for label in labels:
                args += ["--label", label]
            address = self._gh(args, stdout_only=True)
        if not address:
            raise IssueError("gh issue create: exit status 0 but no address printed")
        return address

    def close(self, address: str) -> str:
        """Close the issue at ``address`` (live check L6 only)."""
        return self._gh(["issue", "close", address])


def has_origin(state_dir: Path) -> bool:
    """Whether the Git repository at ``state_dir`` has a remote named ``origin``."""
    from discotrade.state import git_environment

    try:
        done = subprocess.run(["git", "-C", str(state_dir), "remote", "get-url", ORIGIN],
                              env=git_environment(), capture_output=True, text=True,
                              check=False)
    except OSError:
        return False
    return done.returncode == 0


# --- the page (decision 179 (a), (b)) ------------------------------------------------------


def alert_payloads(fired: Sequence[Mapping[str, Any]]) -> list[AlertPayload]:
    """One ``AlertPayload`` per fired entry, its kind and subject only (I-8)."""
    return [AlertPayload(str(e["kind"]), str(e["subject"])) for e in fired]


def _flatten(prefix: str, value: Any, out: dict[str, Any]) -> None:
    if isinstance(value, Mapping) and value:
        for key, inner in value.items():
            _flatten(f"{prefix}.{key}", inner, out)
    else:
        out[prefix] = value


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _value(value: Any) -> str:
    """``value`` as ``ledger.line`` writes it inside a row."""
    row = ledger.line({"v": value})
    return row[len('{"v":'):-1]


def render(track: str, day: date, fired: Sequence[Mapping[str, Any]], prose: str,
           tokens: int, budget: int) -> str:
    """The digest page of ``day`` (decision 179 (a)), ending with one newline."""
    parts = [f"# {track} {day.isoformat()}", prose]
    for e in fired:
        flat: dict[str, Any] = {}
        for key, value in (e["payload"] or {}).items():
            _flatten(str(key), value, flat)
        rows = ["| key | value |", "|---|---|"]
        rows += [f"| {_cell(key)} | {_cell(_value(flat[key]))} |" for key in sorted(flat)]
        parts.append(f"## {e['kind']} — {e['subject']}\n\n" + "\n".join(rows))
    parts.append(f"Coordinator tokens: {tokens} of {budget}")
    return "\n\n".join(parts) + "\n"
