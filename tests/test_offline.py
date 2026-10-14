"""The socket backstop outside function-scoped tests, and the subprocess listing.

Decision 47 of meta/decisions/decisions-2026-10-12.md (I-11): from the start of
the session every network connection fails with ``SocketBlocked``, in module-
and session-scoped fixtures as well as in tests, and through ``_socket`` used
directly as well as through ``socket``; a test marked ``network`` or ``live`` is
left alone while it runs. Decision 58 adds ``sendmsg`` with an address on a
socket that is not ``AF_UNIX`` and the lookups ``gethostbyname``,
``gethostbyname_ex``, ``gethostbyaddr`` and ``getnameinfo`` to what fails, in
the same scopes and through both modules. Every file under tests/ and src/ whose text contains
``subprocess`` or ``os.system`` is named in ``SUBPROCESS_FILES`` with what it
launches, so that a new call is classified when it is added.
"""

import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SocketBlocked

REPO = Path(__file__).resolve().parents[1]


def _listener():
    """A loopback listener: a connection to it needs no network outside this host."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server


def _attempt():
    """Try a loopback connection; the exception it raised, or None when it connected."""
    with _listener() as server:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(server.getsockname())
        except Exception as exc:  # noqa: BLE001 - the test inspects what was raised
            return exc
        finally:
            client.close()
    return None


@pytest.fixture(scope="module")
def module_attempt():
    return _attempt()


@pytest.fixture(scope="session")
def session_attempt():
    return _attempt()


def test_a_module_scoped_fixture_cannot_open_a_socket(module_attempt):
    assert isinstance(module_attempt, SocketBlocked), module_attempt
    assert "socket backstop" in str(module_attempt)


def test_a_session_scoped_fixture_cannot_open_a_socket(session_attempt):
    assert isinstance(session_attempt, SocketBlocked), session_attempt
    assert "socket backstop" in str(session_attempt)


def test_the_error_names_the_test_that_set_up_the_fixture(module_attempt):
    # The module fixture is set up by the first test of this file that asks for it.
    assert "test_offline.py::" in str(module_attempt)


def test__socket_used_directly_cannot_open_a_connection():
    import _socket
    with _listener() as server:
        address = server.getsockname()
        raw = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        try:
            with pytest.raises(SocketBlocked, match="socket backstop"):
                raw.connect(address)
            with pytest.raises(SocketBlocked, match="socket backstop"):
                raw.connect_ex(address)
        finally:
            raw.close()
        datagram = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        try:
            with pytest.raises(SocketBlocked, match="socket backstop"):
                datagram.sendto(b"x", address)
        finally:
            datagram.close()
    with pytest.raises(SocketBlocked, match="socket backstop"):
        _socket.getaddrinfo("example.invalid", 443)


def test__socket_unix_domain_stays_open(tmp_path):
    import _socket
    path = str(tmp_path / "s")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(path)
        server.listen(1)
        raw = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        try:
            raw.connect(path)
        finally:
            raw.close()


# --- sendmsg with an address and the name lookups (decision 58) ------------------------

#: Each guarded name lookup with a numeric loopback argument. Every call of them
#: in this module is refused by the backstop before the real function runs (the
#: spy test below shows the real one is not reached). The argument alone would
#: not keep an unguarded ``gethostbyaddr`` from a resolver: a reverse lookup reads
#: the hosts file or asks DNS, so the scratch session's network test does not
#: call it (decision 67).
LOOKUPS = {
    "gethostbyname": ("127.0.0.1",),
    "gethostbyname_ex": ("127.0.0.1",),
    "gethostbyaddr": ("127.0.0.1",),
    "getnameinfo": (("127.0.0.1", 9), socket.NI_NUMERICHOST | socket.NI_NUMERICSERV),
}


def _paths() -> dict[str, object]:
    """Try ``sendmsg`` with an address on an AF_INET datagram socket made through
    ``socket`` and through ``_socket``, and each lookup of ``LOOKUPS`` through both
    modules; what each raised (None when it returned), and under ``"received"``
    whatever the loopback receiver got (None when nothing arrived)."""
    import _socket
    out: dict[str, object] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.setblocking(False)
        address = receiver.getsockname()
        for module in (socket, _socket):
            sender = module.socket(module.AF_INET, module.SOCK_DGRAM)
            try:
                sender.sendmsg([b"x"], [], 0, address)
                out[f"{module.__name__}.sendmsg"] = None
            except Exception as exc:  # noqa: BLE001 - the test inspects what was raised
                out[f"{module.__name__}.sendmsg"] = exc
            finally:
                sender.close()
        try:
            out["received"] = receiver.recv(16)
        except BlockingIOError:
            out["received"] = None
    for module in (socket, _socket):
        for name, args in LOOKUPS.items():
            try:
                getattr(module, name)(*args)
                out[f"{module.__name__}.{name}"] = None
            except Exception as exc:  # noqa: BLE001
                out[f"{module.__name__}.{name}"] = exc
    return out


PATHS = [f"{m}.{n}" for m in ("socket", "_socket") for n in ("sendmsg", *LOOKUPS)]


def _all_blocked(found: dict[str, object]) -> None:
    assert found["received"] is None, found["received"]
    for path in PATHS:
        assert isinstance(found[path], SocketBlocked), (path, found[path])
        assert "socket backstop" in str(found[path]), path


@pytest.fixture(scope="module")
def module_paths():
    return _paths()


@pytest.fixture(scope="session")
def session_paths():
    return _paths()


def test_sendmsg_with_an_address_and_the_lookups_fail_in_a_test():
    _all_blocked(_paths())


def test_sendmsg_with_an_address_and_the_lookups_fail_in_a_module_scoped_fixture(
        module_paths):
    _all_blocked(module_paths)


def test_sendmsg_with_an_address_and_the_lookups_fail_in_a_session_scoped_fixture(
        session_paths):
    _all_blocked(session_paths)


@pytest.mark.parametrize("module_name", ["socket", "_socket"])
@pytest.mark.parametrize("name", ["getaddrinfo", *LOOKUPS])
def test_a_lookup_is_refused_before_the_real_function_runs(monkeypatch, module_name, name):
    # The backstop is put back around a spy standing for the real lookup: the spy
    # is never called, so no query leaves the process.
    import _socket

    import conftest
    module = {"socket": socket, "_socket": _socket}[module_name]
    calls = []

    def spy(*args, **kw):
        calls.append(args)
        return None

    conftest.uninstall_backstop()
    try:
        monkeypatch.setattr(module, name, spy)
        conftest.install_backstop()
        with pytest.raises(SocketBlocked, match="socket backstop"):
            getattr(module, name)("127.0.0.1", 9)
        assert calls == []
    finally:
        conftest.uninstall_backstop()
        monkeypatch.undo()
        conftest.install_backstop()
    assert getattr(module, name) is not spy


def test_sendmsg_without_an_address_on_an_unconnected_socket_is_the_os_error():
    # Only a sendmsg given an address is guarded; one without has nowhere to go.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        with pytest.raises(OSError):
            sender.sendmsg([b"x"])


def test_unix_domain_sendmsg_with_an_address_stays_open(tmp_path):
    import _socket
    path = str(tmp_path / "d")
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
        receiver.bind(path)
        for module in (socket, _socket):
            sender = module.socket(module.AF_UNIX, module.SOCK_DGRAM)
            try:
                assert sender.sendmsg([b"x"], [], 0, path) == 1
            finally:
                sender.close()
            assert receiver.recv(16) == b"x"


# --- a test marked network is left alone (scratch session) -----------------------------

INNER_TESTS = '''
import _socket
import socket
import types

import pytest
from conftest import SocketBlocked
from originals import ORIGINAL


def _listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server


NUMERIC = socket.AI_NUMERICHOST | socket.AI_NUMERICSERV

#: The lookups the network-marked test calls for real (decision 67): each is
#: answered by Python or the C library without a resolver.
#: - getaddrinfo of a numeric address and port with AI_NUMERICHOST and
#:   AI_NUMERICSERV: the flags forbid a host or service lookup; a name that is
#:   not numeric fails instead of being resolved.
#: - getnameinfo with NI_NUMERICHOST | NI_NUMERICSERV: Python first parses the
#:   address with getaddrinfo and AI_NUMERICHOST, and the flags make the C
#:   library format the address and port as numbers instead of looking them up.
#: - gethostbyname of a dotted numeric address: Python parses it with
#:   inet_pton and returns it without calling the C library's lookup.
#: - gethostbyname_ex of a dotted numeric address: Python parses it as above,
#:   and the C library's gethostbyname_r answers a name made of digits and dots
#:   itself, before any hosts file or DNS source is consulted.
#: gethostbyaddr is not among them: a reverse lookup reads the hosts file or asks
#: DNS, whatever its argument.
RESOLVERLESS = {
    "getaddrinfo": ("127.0.0.1", 9, socket.AF_INET, socket.SOCK_STREAM, 0, NUMERIC),
    "gethostbyname": ("127.0.0.1",),
    "gethostbyname_ex": ("127.0.0.1",),
    "getnameinfo": (("127.0.0.1", 9), socket.NI_NUMERICHOST | socket.NI_NUMERICSERV),
}
#: The lookups the unmarked test shows refused again.
REFUSED = {**RESOLVERLESS, "gethostbyaddr": ("127.0.0.1",)}


def _sendmsg(module, address):
    sender = module.socket(module.AF_INET, module.SOCK_DGRAM)
    try:
        return sender.sendmsg([b"x"], [], 0, address)
    finally:
        sender.close()


@pytest.mark.network
def test_marked_network_connects():
    with _listener() as server:
        host, port = server.getsockname()
        for module in (socket, _socket):
            [(family, kind, proto, _, address)] = module.getaddrinfo(
                host, port, module.AF_INET, module.SOCK_STREAM, 0, NUMERIC)
            assert address == (host, port)
            raw = module.socket(family, kind, proto)
            try:
                raw.connect(address)
            finally:
                raw.close()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        for module in (socket, _socket):
            assert _sendmsg(module, receiver.getsockname()) == 1
            assert receiver.recv(16) == b"x"
    for module in (socket, _socket):
        for name, args in RESOLVERLESS.items():
            getattr(module, name)(*args)
        # Left alone, shown by identity and not by a call.
        original = ORIGINAL[module.__name__]
        assert isinstance(original, types.BuiltinFunctionType)
        assert module.gethostbyaddr is original


def test_unmarked_after_network_is_blocked_again():
    with _listener() as server:
        with pytest.raises(SocketBlocked):
            socket.create_connection(server.getsockname(), timeout=5)
    for module in (socket, _socket):
        with pytest.raises(SocketBlocked):
            _sendmsg(module, ("127.0.0.1", 9))
        for name, args in REFUSED.items():
            with pytest.raises(SocketBlocked):
                getattr(module, name)(*args)
        assert module.gethostbyaddr is not ORIGINAL[module.__name__]


def test_unmarked_forgets_its_fake():
    with _listener() as server:
        socket.create_connection(server.getsockname(), timeout=5).close()
'''

#: A plugin the scratch session loads with ``-p`` before tests/conftest.py's
#: ``pytest_configure`` installs the backstop: it keeps the original reverse lookup.
INNER_ORIGINALS = '''
import _socket
import socket

ORIGINAL = {"socket": socket.gethostbyaddr, "_socket": _socket.gethostbyaddr}
'''

INNER_INI = '''[pytest]
addopts = --strict-markers -p no:cacheprovider -p originals
markers =
    network: needs the network
    live: needs a secret
'''


def test_a_test_marked_network_is_left_alone(tmp_path):
    shutil.copy(REPO / "tests" / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "pytest.ini").write_text(INNER_INI, encoding="utf-8")
    (tmp_path / "test_inner.py").write_text(INNER_TESTS, encoding="utf-8")
    (tmp_path / "originals.py").write_text(INNER_ORIGINALS, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-rA", "test_inner.py"],
        cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False,
    )
    out = result.stdout
    assert result.returncode == 1, out + result.stderr
    assert "PASSED test_inner.py::test_marked_network_connects" in out
    assert "PASSED test_inner.py::test_unmarked_after_network_is_blocked_again" in out
    assert "FAILED test_inner.py::test_unmarked_forgets_its_fake" in out
    assert "SocketBlocked" in out
    assert "1 failed, 2 passed" in out


# --- every file that launches a subprocess is classified (decision 47) -----------------

#: Every file under tests/ and src/ whose text contains ``subprocess`` or
#: ``os.system``, with what it launches. Decision 47 allows only git on local
#: paths with GIT_ALLOW_PROTOCOL=file, or a Python program of this repository
#: that opens no connection.
SUBPROCESS_FILES = {
    "src/discotrade/sandbox/container.py":
        "the container runtime's command (docker or podman); every run carries "
        "--network none (decision 102 (f))",
    "src/discotrade/sandbox/process.py":
        "python -I -m discotrade.sandbox.runner, a program of this repository that opens "
        "no connection (decision 96)",
    "src/discotrade/state.py": "git on the local state directory, GIT_ALLOW_PROTOCOL=file",
    "tests/test_cli.py": "the discotrade command; a scratch pytest run of tests/conftest.py",
    "tests/test_config_check.py": "the discotrade command",
    "tests/test_costs.py": "a python -c snippet the test writes",
    "tests/test_daily.py": "git on local state directories, GIT_ALLOW_PROTOCOL=file",
    "tests/gates/m1_harness.py": "git on local state directories, GIT_ALLOW_PROTOCOL=file",
    "tests/test_gate_script.py": "./scripts/gate; scratch pytest runs of tests/conftest.py",
    "tests/test_offline.py": "a scratch pytest run of tests/conftest.py",
    "tests/test_rank_daily.py": "git on local state directories, GIT_ALLOW_PROTOCOL=file",
    "tests/test_replay.py": "git on local state directories, GIT_ALLOW_PROTOCOL=file",
    "tests/test_replay_candidates.py": "git on local state directories, GIT_ALLOW_PROTOCOL=file",
    "tests/test_sandbox_container.py": "a scratch pytest run of tests/conftest.py",
    "tests/test_state.py": "git on a local state directory, GIT_ALLOW_PROTOCOL=file",
    "tests/test_table.py": "git on local state directories, GIT_ALLOW_PROTOCOL=file",
    "tests/test_vendor.py": "python -c snippets the test writes",
}

NEEDLES = (b"subprocess", b"os.system")


def subprocess_files(root: Path) -> list[str]:
    """The files under ``root``'s tests/ and src/ whose text names a subprocess call."""
    found = []
    for top in ("tests", "src"):
        for path in sorted((root / top).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            data = path.read_bytes()
            if any(needle in data for needle in NEEDLES):
                found.append(path.relative_to(root).as_posix())
    return found


def check_listed(root: Path) -> None:
    """Fail, naming each file, when a file that names a subprocess call is not listed."""
    unlisted = [p for p in subprocess_files(root) if p not in SUBPROCESS_FILES]
    assert not unlisted, (
        "files that name subprocess or os.system but are not in SUBPROCESS_FILES "
        "(decision 47): " + ", ".join(unlisted)
    )


def test_every_file_that_launches_a_subprocess_is_listed():
    check_listed(REPO)
    # And the list names no file that no longer launches one.
    assert sorted(SUBPROCESS_FILES) == sorted(subprocess_files(REPO))


@pytest.mark.parametrize("name, text", [
    ("src/discotrade/shell_out.py", "import subprocess\nsubprocess.run(['true'])\n"),
    ("tests/test_shell_out.py", "import os\nos.system('true')\n"),
])
def test_a_new_subprocess_call_fails_the_listing_naming_the_file(tmp_path, name, text):
    for top in ("tests", "src"):
        shutil.copytree(REPO / top, tmp_path / top,
                        ignore=shutil.ignore_patterns("__pycache__"))
    check_listed(tmp_path)  # the scratch copy passes as the tree does
    (tmp_path / name).write_text(text, encoding="utf-8")
    with pytest.raises(AssertionError, match=name):
        check_listed(tmp_path)
