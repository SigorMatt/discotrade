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
"""

import _socket
import os
import socket
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
