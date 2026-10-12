"""The socket backstop outside function-scoped tests, and the subprocess listing.

Decision 47 of meta/decisions/decisions-2026-10-12.md (I-11): from the start of
the session every network connection fails with ``SocketBlocked``, in module-
and session-scoped fixtures as well as in tests, and through ``_socket`` used
directly as well as through ``socket``; a test marked ``network`` or ``live`` is
left alone while it runs. Every file under tests/ and src/ whose text contains
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


# --- a test marked network is left alone (scratch session) -----------------------------

INNER_TESTS = '''
import _socket
import socket

import pytest
from conftest import SocketBlocked


def _listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server


@pytest.mark.network
def test_marked_network_connects():
    with _listener() as server:
        socket.create_connection(server.getsockname(), timeout=5).close()
        raw = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        try:
            raw.connect(server.getsockname())
        finally:
            raw.close()


def test_unmarked_after_network_is_blocked_again():
    with _listener() as server:
        with pytest.raises(SocketBlocked):
            socket.create_connection(server.getsockname(), timeout=5)


def test_unmarked_forgets_its_fake():
    with _listener() as server:
        socket.create_connection(server.getsockname(), timeout=5).close()
'''

INNER_INI = '''[pytest]
addopts = --strict-markers -p no:cacheprovider
markers =
    network: needs the network
    live: needs a secret
'''


def test_a_test_marked_network_is_left_alone(tmp_path):
    shutil.copy(REPO / "tests" / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "pytest.ini").write_text(INNER_INI, encoding="utf-8")
    (tmp_path / "test_inner.py").write_text(INNER_TESTS, encoding="utf-8")
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
    "src/discotrade/state.py": "git on the local state directory, GIT_ALLOW_PROTOCOL=file",
    "tests/test_cli.py": "the discotrade command; a scratch pytest run of tests/conftest.py",
    "tests/test_config_check.py": "the discotrade command",
    "tests/test_costs.py": "a python -c snippet the test writes",
    "tests/test_gate_script.py": "./scripts/gate; scratch pytest runs of tests/conftest.py",
    "tests/test_offline.py": "a scratch pytest run of tests/conftest.py",
    "tests/test_state.py": "git on a local state directory, GIT_ALLOW_PROTOCOL=file",
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
