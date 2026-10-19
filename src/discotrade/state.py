"""The state directory (DESIGN 9.1, 9.2, 15.2, 16.2; decisions 50, 52, 55 of
meta/decisions/decisions-2026-10-12.md; I-5, I-12, I-14).

The API, for the units that build on it:

- ``init_state(path, clock)`` makes ``path`` a state directory: a Git
  repository whose one committed file is ``.gitignore`` (``GITIGNORE``:
  the bar Parquet files, the staging directory ``STAGING`` and the lock
  ``LOCK``). On a state directory it changes nothing; on anything else
  that exists and is not an empty directory it raises ``StateError``.
- ``is_state_directory(path)`` / ``require_state_directory(path)``: a state
  directory is one ``init_state`` made, which is read, where the design is
  silent, as: ``.git/`` exists, ``.gitignore`` is exactly ``GITIGNORE``, and
  ``HEAD`` names a commit.
- ``lock(path)``: a context manager that creates ``path/LOCK`` exclusively
  (``O_CREAT | O_EXCL``), raises ``StateError`` naming it when it is held,
  and removes it on leaving, success or failure.
- ``commit(path, track, day, clock)``: stages every change (``.gitignore``
  keeps out what it lists) and commits it as ``run <track> <day>`` with the
  author and committer ``discotrade <discotrade@invalid>`` and both dates the
  clock's instant, returning the commit's sha; with nothing changed it makes
  no commit and returns None.
- ``append_health(path, track, events)``: appends each event's
  ``to_json()`` line to ``health/<track>.jsonl`` atomically (decision 4's
  way: the whole file written beside the old one, every earlier line
  byte-identical, ``fsync``-ed and renamed), skipping a line already in the
  log or earlier in the same call; returns the events appended.

- ``approach_id(source, params)``, ``write_approach(path, ...)`` and
  ``read_approaches(path)``: the approaches the state holds (DESIGN 9.1;
  decision 48), ``approaches/<id>/strategy.py`` and ``meta.json``. The id
  is ``a`` and the first 12 hex digits of the sha256 of the UTF-8 source
  text, a newline and the canonical JSON (keys sorted, no whitespace) of the
  fixed parameters. ``meta.json`` (``META_FIELDS``) is that canonical JSON
  of the fields DESIGN 9.1 lists, with a newline: ``id``, ``cell``,
  ``model_id``, ``model_version``, ``cutoff`` (the model's cutoff date as
  used), ``description``, ``params``, ``code_sha256`` (of the UTF-8 source),
  ``profile_version``, ``cost_model`` and ``config_hash`` (decision 26,
  computed from the instruments and spread tables given) and ``admitted``;
  dates are ISO. Writing an approach that is already there with the same
  two files changes nothing; with other files it raises ``StateError``
  naming it (a recorded approach is never rewritten, I-5).
- ``write_trial(path, ...)``: a trial that was not admitted, under
  ``trials/<id>/`` with the same two files (decision 62), ``admitted`` null.

- ``register_cache(name, clear)``, ``registered_caches()`` and
  ``clear_caches()``: the one function that clears every cache the project
  holds in the process (decision 2026-10-18-m20 157 (b)). Each module that
  keeps a cache registers it here, by its dotted name, when it is imported;
  ``clear_caches`` calls every registered clearing function, so that what
  follows computes from the records as a new process would.

Git runs with ``git_environment()``: ``GIT_ALLOW_PROTOCOL=file`` (decision
50), no global or system configuration (so that no hook, signing or
identity of the machine's user changes a state commit; the design is
silent, this is the simplest reading of I-12 and of a fixed author), and the
author, committer and dates set explicitly. Git records whole seconds: a
commit date is the clock's instant with its fraction of a second dropped.

The content hash of a table (DESIGN 9.2) is the sha256 of its rows, sorted
by the key columns, written as text with every float in ``%.17g``. The text
is fixed here, where the design is silent: a header line of the column
names in the frame's order, then one line per row; fields separated by a
tab, every line ended by a newline, UTF-8. A float is ``%.17g`` (a NaN is
``nan``); a timestamp is its integer nanoseconds since the epoch in UTC; an
integer is decimal; a boolean is ``true`` or ``false``; None, NaT and NA are
empty; any other value is its ``str``. A tab or a newline inside a field is refused,
so that the text has one reading.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from discotrade.clock import Clock

_BOOL = (bool, np.bool_)
_FLOAT = (float, np.floating)
_INT = (int, np.integer)


def _field(value: Any) -> str:
    if type(value) is str:  # the common case, decided as the last branch below would
        if "\t" in value or "\n" in value or "\r" in value:
            raise ValueError(f"field {value!r} holds a tab or a newline")
        return value
    if value is None or value is pd.NaT:
        return ""
    if isinstance(value, _BOOL):
        return "true" if value else "false"
    if isinstance(value, _FLOAT):
        return f"{float(value):.17g}"  # identical to "%.17g" % value
    if isinstance(value, _INT):
        return str(int(value))
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert("UTC").tz_localize(None)
        return str(value.value)
    if isinstance(value, np.datetime64):
        return _field(pd.Timestamp(value))
    if value is pd.NA:
        return ""
    text = str(value)
    if "\t" in text or "\n" in text or "\r" in text:
        raise ValueError(f"field {text!r} holds a tab or a newline")
    return text


_FLOAT_TEXT = "{:.17g}".format


def _column_fields(column: pd.Series) -> list[str]:
    """``_field`` of each value of ``column`` as iterating it yields them (as
    ``itertuples`` does), computed a column at a time: a NumPy float, integer or
    boolean column through ``tolist`` (the same Python scalars ``item`` gives),
    a datetime column from its nanoseconds since the epoch in UTC (what
    ``Timestamp.value`` gives; NaT empty), any other value by ``_field``."""
    values = column._values
    if isinstance(values, np.ndarray):
        kind = values.dtype.kind
        if kind == "f":
            return list(map(_FLOAT_TEXT, values.tolist()))
        if kind in "iu":
            return list(map(str, values.tolist()))
        if kind == "b":
            return ["true" if v else "false" for v in values.tolist()]
    elif isinstance(values, pd.arrays.DatetimeArray):
        nanos = values.as_unit("ns").asi8.tolist()
        missing = values.isna().tolist()
        return ["" if m else str(v) for v, m in zip(nanos, missing, strict=True)]
    return [_field(v) for v in column]


def content_text(frame: pd.DataFrame, key: Sequence[str]) -> str:
    """The text whose sha256 is the content hash of ``frame``. Built a column
    at a time (``_column_fields``); the text is the one a row at a time with
    ``_field`` gives."""
    columns = [str(c) for c in frame.columns]
    missing = [k for k in key if k not in columns]
    if missing:
        raise ValueError(f"key columns {missing} are not in the table")
    for name in columns:
        if "\t" in name or "\n" in name:
            raise ValueError(f"column name {name!r} holds a tab or a newline")
    rows = frame.sort_values(list(key), kind="mergesort") if len(key) else frame
    fields = [_column_fields(rows.iloc[:, k]) for k in range(len(columns))]
    lines = ["\t".join(columns)]
    lines.extend(map("\t".join, zip(*fields, strict=True)))  # no column: no row line
    return "\n".join(lines) + "\n"


def content_hash(frame: pd.DataFrame, key: Sequence[str]) -> str:
    """The sha256 hex digest of ``content_text(frame, key)`` (DESIGN 9.2)."""
    return hashlib.sha256(content_text(frame, key).encode("utf-8")).hexdigest()


HEALTH_LEVELS = ("alert", "notice")


@dataclass(frozen=True)
class HealthEvent:
    """One health event (DESIGN 15.2): date, level, kind, subject and a detail
    object. The code that detects a condition returns it; the daily run
    appends it to the health log."""

    date: date
    level: str
    kind: str
    subject: str
    detail: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.level not in HEALTH_LEVELS:
            raise ValueError(f"health level must be one of {HEALTH_LEVELS}, not {self.level!r}")

    def to_json(self) -> str:
        """The event as one JSON line (no newline), keys sorted."""
        return json.dumps(
            {"date": self.date.isoformat(), "level": self.level, "kind": self.kind,
             "subject": self.subject, "detail": dict(self.detail)},
            sort_keys=True,
        )


# --- the state directory (DESIGN 9.1, 16.2; decision 50) ---------------------------------

#: The staging directory of a day (DESIGN 16.2), relative to the state directory.
STAGING = "staging"
#: The run lock (DESIGN 16.2), relative to the state directory.
LOCK = "lock"
#: The ``.gitignore`` that ``init_state`` writes (decision 50).
GITIGNORE = (
    "# discotrade state directory (DESIGN 9.1, decision 50)\n"
    "bars/**/*.parquet\n"
    f"/{STAGING}/\n"
    f"/{LOCK}\n"
)
AUTHOR_NAME = "discotrade"
AUTHOR_EMAIL = "discotrade@invalid"
#: The message of the commit ``init_state`` makes (the design is silent).
INIT_MESSAGE = "init-state"


class StateError(Exception):
    """A state directory that cannot be used as asked; the command exits 1."""


def git_environment(clock: Clock | None = None) -> dict[str, str]:
    """The environment git runs in: the file protocol only, no global or system
    configuration, the discotrade identity, and with ``clock`` both dates."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": AUTHOR_NAME,
        "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
        "GIT_COMMITTER_NAME": AUTHOR_NAME,
        "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
    })
    if clock is not None:
        stamp = f"@{math.floor(clock.now().timestamp())} +0000"
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    return env


def _git(path: Path, *args: str, clock: Clock | None = None,
         check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(path), *args], env=git_environment(clock),
        capture_output=True, text=True, check=False,
    )
    if check and result.returncode != 0:
        raise StateError(f"git {' '.join(args)} in {path} failed: {result.stderr.strip()}")
    return result


def is_state_directory(path: Path) -> bool:
    """True when ``path`` is a state directory ``init_state`` made."""
    path = Path(path)
    gitignore = path / ".gitignore"
    if not (path / ".git").is_dir() or not gitignore.is_file():
        return False
    if gitignore.read_bytes() != GITIGNORE.encode("utf-8"):
        return False
    return _git(path, "rev-parse", "--verify", "-q", "HEAD^{commit}", check=False).returncode == 0


def require_state_directory(path: Path) -> None:
    """Raise ``StateError`` unless ``path`` is a state directory (decision 50)."""
    if not is_state_directory(path):
        raise StateError(f"{path} is not a state directory; create one with "
                         "`discotrade init-state --state <dir>`")


def init_state(path: Path, clock: Clock) -> bool:
    """Make ``path`` a state directory and commit its ``.gitignore`` with the
    clock's instant. Returns True when it created one, False when ``path``
    already was one (nothing is changed). Raises ``StateError`` for a path
    that exists and is neither a state directory nor an empty directory."""
    path = Path(path)
    if path.exists():
        if is_state_directory(path):
            return False
        if not path.is_dir() or any(path.iterdir()):
            raise StateError(f"{path} is not empty and is not a state directory")
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    (path / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    _git(path, "add", ".gitignore")
    _git(path, "commit", "-q", "-m", INIT_MESSAGE, clock=clock)
    return True


@contextmanager
def lock(path: Path) -> Iterator[Path]:
    """Hold the run lock of the state directory ``path`` (DESIGN 16.2).

    The lock file is created exclusively; a lock that is already held raises
    ``StateError`` naming it and leaves it in place. The lock is removed on
    leaving the block, whether the block succeeded or raised."""
    target = Path(path) / LOCK
    try:
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        raise StateError(f"the state directory is locked: {target} exists (another run "
                         "holds it, or a run died; remove it once no run is going)") from None
    os.close(fd)
    try:
        yield target
    finally:
        target.unlink(missing_ok=True)


def commit(path: Path, track: str, day: date, clock: Clock) -> str | None:
    """Commit every change in the state directory as ``run <track> <day>``
    with both dates the clock's instant; None, and no commit, when nothing
    changed."""
    path = Path(path)
    _git(path, "add", "--all")
    if _git(path, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return None
    _git(path, "commit", "-q", "-m", f"run {track} {day.isoformat()}", clock=clock)
    return _git(path, "rev-parse", "HEAD").stdout.strip()


# --- the health log (DESIGN 15.2; decisions 4, 52) ---------------------------------------

def health_path(path: Path, track: str) -> Path:
    """``health/<track>.jsonl`` under the state directory ``path``."""
    return Path(path) / "health" / f"{track}.jsonl"


def append_health(path: Path, track: str, events: Iterable[HealthEvent]) -> list[HealthEvent]:
    """Append each event's ``to_json()`` line that the log does not already
    hold; return the events appended, in order. Nothing to append writes
    nothing. A log whose last line has no newline is refused."""
    from discotrade.bars.store import write_atomic  # bars.store imports this module

    log = health_path(path, track)
    old = log.read_bytes() if log.exists() else b""
    if old and not old.endswith(b"\n"):
        raise StateError(f"{log} does not end with a newline; its last line is torn")
    present = set(old.decode("utf-8").splitlines())
    appended: list[HealthEvent] = []
    lines: list[str] = []
    for item in events:
        line = item.to_json()
        if line in present:
            continue
        present.add(line)
        appended.append(item)
        lines.append(line + "\n")
    if lines:
        data = old + "".join(lines).encode("utf-8")
        write_atomic(log, lambda p: p.write_bytes(data))
    return appended


# --- approaches (DESIGN 9.1; decision 48) ------------------------------------------------

APPROACHES = "approaches"
TRIALS = "trials"
SOURCE_FILE = "strategy.py"
META_FILE = "meta.json"
META_FIELDS = ("admitted", "cell", "code_sha256", "config_hash", "cost_model", "cutoff",
               "description", "id", "model_id", "model_version", "params",
               "profile_version")


def canonical_json(value: Any) -> str:
    """JSON with keys sorted and no whitespace; a value that is not finite is refused."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def approach_id(source: str, params: Mapping[str, Any]) -> str:
    """``a`` and the first 12 hex digits of the sha256 of the UTF-8 ``source``, a
    newline and the canonical JSON of ``params`` (decision 48)."""
    text = source + "\n" + canonical_json(dict(params))
    return "a" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Approach:
    """An approach the state holds: its id, frozen source, fixed parameters,
    admission date and the whole ``meta.json``."""

    id: str
    source: str
    params: Mapping[str, Any]
    admitted: date
    meta: Mapping[str, Any]


def approach_dir(path: Path, aid: str) -> Path:
    return Path(path) / APPROACHES / aid


def write_approach(path: Path, *, source: str, params: Mapping[str, Any], cell: str,
                   model_id: str, model_version: str, cutoff: date, description: str,
                   profile_version: str, admitted: date, instruments: Iterable[Any],
                   spread_tables: Mapping[str, Any]) -> str:
    """Write ``approaches/<id>/strategy.py`` and ``meta.json`` under the state
    directory ``path`` and return the id (decision 48). ``instruments`` and
    ``spread_tables`` are the track's, for the cost config hash (decision 26)."""
    return _write_frozen(path, APPROACHES, source=source, params=params, cell=cell,
                         model_id=model_id, model_version=model_version, cutoff=cutoff,
                         description=description, profile_version=profile_version,
                         admitted=admitted, instruments=instruments,
                         spread_tables=spread_tables)


def write_trial(path: Path, *, source: str, params: Mapping[str, Any], cell: str,
                model_id: str, model_version: str, cutoff: date, description: str,
                profile_version: str, instruments: Iterable[Any],
                spread_tables: Mapping[str, Any]) -> str:
    """Write a trial that was not admitted, ``trials/<id>/strategy.py`` and
    ``meta.json`` (DESIGN 9.1; decision 62), as ``write_approach`` writes an
    approach, its ``admitted`` being ``null`` (it was not admitted; the design
    is silent, the date of the trial is its ledger row's)."""
    return _write_frozen(path, TRIALS, source=source, params=params, cell=cell,
                         model_id=model_id, model_version=model_version, cutoff=cutoff,
                         description=description, profile_version=profile_version,
                         admitted=None, instruments=instruments,
                         spread_tables=spread_tables)


def trial_dir(path: Path, aid: str) -> Path:
    return Path(path) / TRIALS / aid


def _write_frozen(path: Path, root: str, *, source: str, params: Mapping[str, Any], cell: str,
                  model_id: str, model_version: str, cutoff: date, description: str,
                  profile_version: str, admitted: date | None, instruments: Iterable[Any],
                  spread_tables: Mapping[str, Any]) -> str:
    from discotrade import costs  # costs reads config, which this module need not load
    from discotrade.bars.store import write_atomic

    aid = approach_id(source, params)
    meta = {
        "id": aid, "cell": cell, "model_id": model_id, "model_version": model_version,
        "cutoff": cutoff.isoformat(), "description": description, "params": dict(params),
        "code_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "profile_version": profile_version, "cost_model": costs.VERSION,
        "config_hash": costs.config_hash(instruments, spread_tables),
        "admitted": None if admitted is None else admitted.isoformat(),
    }
    files = {SOURCE_FILE: source.encode("utf-8"),
             META_FILE: (canonical_json(meta) + "\n").encode("utf-8")}
    where = Path(path) / root / aid
    kind = "approach" if root == APPROACHES else "trial"
    if where.exists():
        held = {name: (where / name).read_bytes() if (where / name).is_file() else None
                for name in files}
        if held == files:
            return aid
        raise StateError(f"{kind} {aid} is already in {where} with other files; a "
                         f"recorded {kind} is never rewritten")
    for name, data in files.items():
        write_atomic(where / name, lambda p, data=data: p.write_bytes(data))
    return aid


def read_approaches(path: Path) -> list[Approach]:
    """Every approach under ``approaches/`` of the state directory ``path``, by id.
    An approach whose files do not give back its id is refused (``StateError``)."""
    root = Path(path) / APPROACHES
    if not root.is_dir():
        return []
    out = []
    for where in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            source = (where / SOURCE_FILE).read_bytes().decode("utf-8")
            meta = json.loads((where / META_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StateError(f"approach {where.name}: cannot read it: {exc}") from exc
        if not isinstance(meta, dict) or set(meta) != set(META_FIELDS):
            raise StateError(f"approach {where.name}: {where / META_FILE} does not hold "
                             f"exactly the fields {list(META_FIELDS)}")
        aid = approach_id(source, meta["params"])
        if aid != where.name or meta["id"] != aid:
            raise StateError(f"approach {where.name}: its source and parameters give the "
                             f"id {aid}")
        out.append(Approach(aid, source, meta["params"], date.fromisoformat(meta["admitted"]),
                            meta))
    return out


# --- the caches of the process (decision 2026-10-18-m20 157 (b)) -----------------------

#: Each cache the project holds in the process, by its dotted name, and the
#: function that empties it.
_CACHES: dict[str, Callable[[], None]] = {}


def register_cache(name: str, clear: Callable[[], None]) -> None:
    """Register the cache ``name`` (its module's dotted name and its own) with
    ``clear_caches``; ``clear`` empties it."""
    _CACHES[name] = clear


def registered_caches() -> list[str]:
    """The names of the caches registered, sorted."""
    return sorted(_CACHES)


def clear_caches() -> list[str]:
    """Empty every cache the project holds in the process and return their
    names, sorted (decision 2026-10-18-m20 157 (b)). The caches, each
    registered by its module when it is imported:

    - ``discotrade.sources.synth._SERIES``: the synthetic source's generated
      series (decision 2026-10-16-m15 121);
    - ``discotrade.journal._DIGESTS``: the sha256 of each trusted file, against
      its stat key (decision 2026-10-15-m14 114);
    - ``discotrade.bars.store._RUN``: the month frames verified in the current
      day run (decision 2026-10-14 80 (b)); emptied, and left None outside a
      day run;
    - ``discotrade.table._DAY_SUMS``: the table's journal sums per journal day;
    - ``discotrade.table._EXPOSURE``: the table's unit and position records,
      per file, keyed by its path, length and sha256 (decision 157 (a));
    - ``discotrade.dashboard._t_critical``: the critical t values of the
      dashboard's rank panel;
    - ``discotrade.alerts._SPLITS``: step 6's paper, unit and position records
      split per subject, per role keyed by the content of the columns it reads
      (decision 157 (a));
    - ``discotrade.bars.store._CARRIED``: the bar month frames verified in an
      earlier day run, keyed by path and index entry, served only to the same
      bytes (length and sha256; decision 157 (a));
    - ``discotrade.stats._OPEN_DAYS``: per calendar record and bar size, whether
      the calendar expects a bar on each date already decided;
    - ``discotrade.bars.gaps._MONTH_MISSING``: the gap check's missing bars of
      each complete month, keyed by the month file's path and index entry, the
      calendar record, the bar size and the lower bound;
    - ``discotrade.rolls._MONTH_CONTRACTS``: the distinct contracts of each
      month file that lay wholly inside a roll scan, keyed by its path and index
      entry.
    """
    for name in sorted(_CACHES):
        _CACHES[name]()
    return sorted(_CACHES)
