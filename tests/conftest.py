"""Shared test configuration.

Under ``DISCOTRADE_GATE=1`` (set by ``scripts/gate``) a test that would skip
fails instead: a gate never passes by skipping (DESIGN 18.2).

A test that lives under ``tests/gates/`` or carries a ``gate_m0`` to
``gate_m5`` marker must carry ``gate`` and exactly one milestone marker;
collection fails otherwise, naming the test (DESIGN 18.1; decision 9 of
meta/decisions/decisions-2026-10-12.md). The check runs before ``-m``
deselects anything, so it holds under every selection.

A test not marked ``network`` or ``live`` cannot open a network connection
(decision 20 of meta/decisions/decisions-2026-10-12.md, I-11). From the start of
the session (decision 47) ``socket.socket.connect``, ``connect_ex`` and
``sendto``, and ``sendmsg`` given an address (decision 58), on any address
family but ``AF_UNIX``, the same four methods of a socket made through
``_socket`` directly, and the name lookups ``getaddrinfo``, ``gethostbyname``,
``gethostbyname_ex``, ``gethostbyaddr`` and ``getnameinfo`` of ``socket`` and
of ``_socket`` (decision 58), raise ``SocketBlocked`` before the real call is
made, which names the test that was
running (or being set up, for a module- or session-scoped fixture). It holds in
fixtures of every scope, not only in function-scoped tests. It is a
``RuntimeError``, not an ``OSError``, so that no client code takes it for an
ordinary connection failure. A Unix-domain socket stays open to every test: it
never leaves the host. A test marked ``network`` or ``live`` is left alone while
it runs (its setup, call and teardown); then the lookups of ``socket`` and
``_socket`` are the original functions, and the guarded ones are put back after
it (decision 67).

A test marked ``container`` skips, printing its reason, when no container
runtime is found or the sandbox image of the current tag is not present (the
reason then names ``discotrade sandbox build``), as
:func:`discotrade.sandbox.container.unavailable` finds for the repository's
``config/run.toml`` (DESIGN 18.1; decision 102 (g) of 2026-10-14-m13). Under
``DISCOTRADE_GATE=1`` that skip is a failure, like every other.

State templates (decision 114 of meta/decisions/decisions-2026-10-15-m14.md,
finding D-013): a state directory that several test modules build the same way
is built once per session by a session-scoped fixture below, from
``tests/fixtures/config/`` with the production ``config/thresholds.toml`` copied
under the session's temporary directory, with the commands, seeds, dates and
clocks those modules used. No test is given a template itself: each module
fixture copies it with :func:`copy_template` into its own temporary directory,
so that a test writing into its module's state never reaches the template or
another module's copy.
"""

import _socket
import os
import shutil
import socket
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

GATE_ENV = "DISCOTRADE_GATE"
GATES_DIR = Path(__file__).resolve().parent / "gates"
MILESTONES = tuple(f"gate_m{n}" for n in range(6))
#: The markers under which a test may open a network connection (I-11).
NETWORK_MARKERS = ("network", "live")


class SocketBlocked(RuntimeError):
    """A test not marked network or live tried to open a network connection."""


def network_allowed(item) -> bool:
    """Whether ``item`` may open a network connection: it is marked network or live."""
    return any(item.get_closest_marker(name) is not None for name in NETWORK_MARKERS)


#: What the backstop knows of the running test: its node id, and whether it may
#: open a network connection. Outside any test (collection) nothing may.
_BACKSTOP = {"nodeid": "outside any test", "allowed": False}
_GUARDED_METHODS = ("connect", "connect_ex", "sendto", "sendmsg")
#: The name lookups guarded in ``socket`` and in ``_socket`` (decisions 47 and 58).
_GUARDED_LOOKUPS = ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr",
                    "getnameinfo")
#: ``sendmsg(buffers, ancdata, flags, address)``: only a call given an address is
#: guarded; one without sends on a connected socket, whose connect was guarded.
_SENDMSG_ADDRESS = 3
_ORIGINALS: dict = {}


def _refuse(target):
    raise SocketBlocked(
        f"socket backstop (I-11, decisions 20 and 47): {_BACKSTOP['nodeid']} tried to "
        f"reach {target!r}; inject a fake, or mark the test network or live"
    )


def _guarded_method(real):
    def method(self, *args):
        if _BACKSTOP["allowed"] or self.family == getattr(socket, "AF_UNIX", None):
            return real(self, *args)
        if real.__name__ == "sendmsg":
            if len(args) <= _SENDMSG_ADDRESS:
                return real(self, *args)
            return _refuse(args[_SENDMSG_ADDRESS])
        return _refuse(args[-1] if args else None)
    method.__name__ = real.__name__
    return method


def _guarded_lookup(real):
    def lookup(target, *rest, **kw):
        if _BACKSTOP["allowed"]:
            return real(target, *rest, **kw)
        return _refuse(target)
    lookup.__name__ = real.__name__
    return lookup


def install_backstop() -> None:
    """Guard ``socket`` and ``_socket`` for the rest of the session."""
    if _ORIGINALS:
        return
    _ORIGINALS["socket.socket"] = {n: socket.socket.__dict__.get(n) for n in _GUARDED_METHODS}
    _ORIGINALS["_socket.socket"] = _socket.socket
    for module in (socket, _socket):
        _ORIGINALS[module.__name__ + ".lookups"] = {
            n: getattr(module, n) for n in _GUARDED_LOOKUPS}
    for name in _GUARDED_METHODS:
        setattr(socket.socket, name, _guarded_method(getattr(socket.socket, name)))
    # ``_socket.socket`` is an immutable built-in type, so a socket made through it
    # directly is guarded by a subclass put in its place. It defines no __init__,
    # so ``socket.socket.__init__``'s call of ``_socket.socket.__init__`` still works.
    base = _socket.socket
    _socket.socket = type("socket", (base,), {
        name: _guarded_method(getattr(base, name)) for name in _GUARDED_METHODS
    })
    for module in (socket, _socket):
        guards = {n: _guarded_lookup(getattr(module, n)) for n in _GUARDED_LOOKUPS}
        _ORIGINALS[module.__name__ + ".guards"] = guards
        for name, guard in guards.items():
            setattr(module, name, guard)


def _put_lookups(original: bool) -> None:
    """Put the original lookups of ``socket`` and ``_socket`` in place, or the
    guarded ones back; nothing when the backstop is not installed."""
    if not _ORIGINALS:
        return
    for module in (socket, _socket):
        which = ".lookups" if original else ".guards"
        for name, function in _ORIGINALS[module.__name__ + which].items():
            setattr(module, name, function)


def uninstall_backstop() -> None:
    """Put back what ``install_backstop`` replaced."""
    if not _ORIGINALS:
        return
    for name, real in _ORIGINALS["socket.socket"].items():
        if real is None:
            delattr(socket.socket, name)
        else:
            setattr(socket.socket, name, real)
    _socket.socket = _ORIGINALS["_socket.socket"]
    for module in (socket, _socket):
        for name, real in _ORIGINALS[module.__name__ + ".lookups"].items():
            setattr(module, name, real)
    _ORIGINALS.clear()


def pytest_configure(config):
    install_backstop()


def pytest_unconfigure(config):
    uninstall_backstop()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Name the running test to the backstop, and lift it for network and live tests."""
    allowed = network_allowed(item)
    _BACKSTOP.update(nodeid=item.nodeid, allowed=allowed)
    lifted = allowed and bool(_ORIGINALS)
    if lifted:
        _put_lookups(original=True)
    try:
        yield
    finally:
        _BACKSTOP.update(nodeid="outside any test", allowed=False)
        if lifted:
            _put_lookups(original=False)


#: The marker of a test that starts a container (DESIGN 18.1).
CONTAINER_MARKER = "container"


def pytest_runtest_setup(item):
    """Skip a ``container`` test, with its reason, when no container can run."""
    if item.get_closest_marker(CONTAINER_MARKER) is None:
        return
    from discotrade.sandbox.container import unavailable

    reason = unavailable()
    if reason is not None:
        pytest.skip(f"container test: {reason}")


def gate_marker_problem(item) -> str | None:
    """Why ``item``'s gate markers are wrong, or None when they are right."""
    names = {mark.name for mark in item.iter_markers()}
    milestones = sorted(names.intersection(MILESTONES))
    under_gates = GATES_DIR in Path(item.path).resolve().parents
    if not under_gates and not milestones:
        return None
    if "gate" not in names:
        return "has no 'gate' marker"
    if len(milestones) != 1:
        found = ", ".join(milestones) or "none"
        return f"needs exactly one milestone marker gate_m0..gate_m5 (found: {found})"
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    problems = [
        f"{item.nodeid}: {why}" for item in items if (why := gate_marker_problem(item))
    ]
    if problems:
        raise pytest.UsageError(
            "gate markers: a test under tests/gates/ or marked gate_m<n> must carry "
            "'gate' and exactly one milestone marker:\n  " + "\n  ".join(problems)
        )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if os.environ.get(GATE_ENV) == "1" and report.skipped:
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else report.longrepr
        report.outcome = "failed"
        report.longrepr = f"skipped under {GATE_ENV}=1, which is a failure: {reason}"


# ------------------------------------------------------------------ state templates

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
#: test_synth's day D 2019-07-15 (W 2019-06-11..07-08, T 07-09..07-15) and the
#: ``--as-of`` its bars are fetched at; test_mixed's ``--as-of`` instants.
SYNTH_AS_OF = "2019-07-25T00:00:00+00:00"
SYNTH_DAY = date(2019, 7, 15)
MIXED_AS_OF = "2019-06-21T00:00:00+00:00"
MIXED_TWO_YEARS = "2021-01-07T00:00:00+00:00"
#: The run of ``mixed_ran_template``: two reference approaches admitted 2019-06-07,
#: run-day over 2019-06-08..06-12 at ``--as-of`` 2019-06-26.
RAN_AS_OF = "2019-06-26T00:00:00+00:00"
RAN_ADMITTED = date(2019, 6, 7)
RAN_DAYS = tuple(date(2019, 6, 8 + k) for k in range(5))
RAN_FILES = ("trend_ma.py", "hour_of_day.py")


def copy_template(template: Path, dest: Path) -> Path:
    """A copy of ``template`` at ``dest`` (which may exist, empty), for one module."""
    shutil.copytree(template, dest, symlinks=True, dirs_exist_ok=True)
    return dest


def _cli(*argv: str) -> None:
    from discotrade.cli import main

    assert main(list(argv)) == 0, argv


def _fetch(state: Path, config: Path, track: str, as_of: str) -> None:
    _cli("--state", str(state), "--config", str(config), "--track", track, "--as-of", as_of,
         "bars", "fetch")


@pytest.fixture(scope="session")
def template_config(tmp_path_factory):
    """The configuration the templates are built with; no test is given it."""
    path = tmp_path_factory.mktemp("template-cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="session")
def synth_bars_template(tmp_path_factory, template_config):
    """test_synth's bars fetched at ``SYNTH_AS_OF``; no state repository."""
    path = tmp_path_factory.mktemp("template-synth-bars") / "state"
    path.mkdir()
    _fetch(path, template_config, "test_synth", SYNTH_AS_OF)
    return path


@pytest.fixture(scope="session")
def synth_committed_template(tmp_path_factory, template_config):
    """init-state at ``SYNTH_AS_OF``, test_synth's bars fetched at it, committed for
    ``SYNTH_DAY`` with the clock at ``SYNTH_AS_OF``."""
    from discotrade import state as state_mod
    from discotrade.clock import FixedClock

    path = tmp_path_factory.mktemp("template-synth-committed") / "state"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        _cli("init-state", "--state", str(path), "--as-of", SYNTH_AS_OF)
        _fetch(path, template_config, "test_synth", SYNTH_AS_OF)
        state_mod.commit(path, "test_synth", SYNTH_DAY,
                         FixedClock(datetime(2019, 7, 25, tzinfo=UTC)))
    return path


@pytest.fixture(scope="session")
def mixed_bars_template(tmp_path_factory, template_config):
    """test_mixed's bars fetched at ``MIXED_AS_OF``; no state repository."""
    path = tmp_path_factory.mktemp("template-mixed-bars") / "state"
    path.mkdir()
    _fetch(path, template_config, "test_mixed", MIXED_AS_OF)
    return path


@pytest.fixture(scope="session")
def mixed_two_years_template(tmp_path_factory, template_config):
    """test_mixed's bars fetched at ``MIXED_TWO_YEARS``; no state repository."""
    path = tmp_path_factory.mktemp("template-mixed-two-years") / "state"
    _fetch(path, template_config, "test_mixed", MIXED_TWO_YEARS)
    return path


@pytest.fixture(scope="session")
def mixed_ran_template(tmp_path_factory, template_config):
    """init-state at ``RAN_AS_OF``, ``RAN_FILES`` from reference/ written admitted
    ``RAN_ADMITTED`` (decision 48), and run-day over ``RAN_DAYS`` on test_mixed."""
    from discotrade import journal
    from discotrade.state import write_approach
    from discotrade.strategy import load_strategy_file

    setup = journal.Setup.load(template_config, "test_mixed")
    path = tmp_path_factory.mktemp("template-mixed-ran") / "state"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_ALLOW_PROTOCOL", "file")
        _cli("init-state", "--state", str(path), "--as-of", RAN_AS_OF)
        for name in RAN_FILES:
            source = REPO_ROOT / "reference" / name
            strat = load_strategy_file(source, setup.thresholds)
            write_approach(
                path, source=source.read_text(encoding="utf-8"), params=strat.params,
                cell="trend/short", model_id="test-model", model_version="test-model-v0",
                cutoff=date(2019, 1, 1), description=f"the reference strategy {name}",
                profile_version="w-test", admitted=RAN_ADMITTED,
                instruments=setup.instruments, spread_tables=setup.spread_tables)
        for d in RAN_DAYS:
            _cli("--state", str(path), "--config", str(template_config), "--track",
                 "test_mixed", "--as-of", RAN_AS_OF, "run-day", "--day", d.isoformat())
    return path
