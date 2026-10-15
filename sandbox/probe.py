"""The sandbox probe (DESIGN 12.4, 18.3 G2.3, 19.3 L5; decision 2026-10-14-m13 103 (a)).

A trusted program of this repository, copied into the sandbox image (an input of
its tag) and started by the container backend with exactly a job's options and,
as its only mount, the input directory of a real job built for W of a day. It
runs no submission and judges nothing: it writes one JSON document to standard
output reporting what it finds from inside, and the harness judges the report
(``discotrade.sandbox.container.judge``).

It reports: the routes of its network namespace (``/proc/net/route``) and the
interfaces present (``/proc/net/dev``); the outcome of a TCP connection attempt,
with a one-second timeout, to an address of RFC 5737's TEST-NET-1, so that
nothing is reached even if isolation failed; the outcome of creating a file
under ``/``, ``/usr``, ``/home``, the mount and ``/tmp`` (a file it created is
removed at once); its user and group ids and its effective capability set
(``/proc/self/status``); the limits the runtime set, read only and never
attempted (O-22 item 3 of decisions-2026-10-15-owner): the values of its cgroup
(version 2, the directory ``/proc/self/cgroup`` names under ``/sys/fs/cgroup``)
for the process count (``pids.max``), memory (``memory.max`` and
``memory.swap.max``) and CPU (``cpu.max``), each as its file holds it, null when
it cannot be read, and its own CPU-time resource limit (``RLIMIT_CPU``, soft and
hard, null for unlimited); and the files of the mount with, per instrument of
``job.json``, the number of bars each array holds and the latest open time of
the bars when the mount carries one (a ``ts`` array; a job written by
``sandbox.base.write_job`` carries none, so it is then null).

It imports only the standard library (a test reads its imports with ``ast``).
Usage: ``python -I probe.py <mount>``.
"""

import ast
import errno
import json
import os
import resource
import socket
import struct
import sys
import zipfile
from datetime import UTC, datetime, timedelta

#: RFC 5737 TEST-NET-1: documentation addresses, routed nowhere.
TARGET = ("192.0.2.1", 9)
CONNECT_SECONDS = 1.0
#: The directories under which a file is created, the mount's added at run time.
CREATE_UNDER = ("/", "/usr", "/home", "/tmp")
PROBE_FILE = "discotrade-probe"
#: Where the cgroup (version 2) file system is mounted, and the files read there.
CGROUP_ROOT = "/sys/fs/cgroup"
CGROUP_FILES = ("pids.max", "memory.max", "memory.swap.max", "cpu.max")
JOB_FILE = "job.json"
_NPY_MAGIC = b"\x93NUMPY"
_UNITS = {"s": 1, "ms": 10**3, "us": 10**6, "ns": 10**9}


def _error(exc):
    code = getattr(exc, "errno", None)
    if isinstance(code, int) and code in errno.errorcode:
        return errno.errorcode[code]
    return type(exc).__name__


def routes():
    """The routes of ``/proc/net/route`` (header left out), or the error."""
    try:
        with open("/proc/net/route", encoding="ascii") as handle:
            lines = handle.read().splitlines()[1:]
    except OSError as exc:
        return {"routes": None, "routes_error": _error(exc)}
    return {"routes": [" ".join(line.split()) for line in lines if line.strip()]}


def interfaces():
    """The interfaces of ``/proc/net/dev``, sorted, or the error."""
    try:
        with open("/proc/net/dev", encoding="ascii") as handle:
            lines = handle.read().splitlines()[2:]
    except OSError as exc:
        return {"interfaces": None, "interfaces_error": _error(exc)}
    return {"interfaces": sorted(line.split(":", 1)[0].strip() for line in lines
                                 if ":" in line)}


def connect():
    """A TCP connection attempt to TEST-NET-1 with a one-second timeout."""
    try:
        with socket.create_connection(TARGET, timeout=CONNECT_SECONDS):
            return {"target": f"{TARGET[0]}:{TARGET[1]}", "connected": True, "error": None}
    except OSError as exc:
        return {"target": f"{TARGET[0]}:{TARGET[1]}", "connected": False,
                "error": _error(exc)}


def create(directory):
    """Whether a new file could be created under ``directory``, and why not."""
    path = os.path.join(directory, PROBE_FILE)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        return {"under": directory, "created": False, "error": _error(exc)}
    os.close(fd)
    try:
        os.unlink(path)
    except OSError:
        pass
    return {"under": directory, "created": True, "error": None}


def identity():
    """User and group ids, and the effective capability set from /proc/self/status."""
    out = {"uid": os.getuid(), "euid": os.geteuid(), "gid": os.getgid(),
           "egid": os.getegid(), "cap_eff": None}
    try:
        with open("/proc/self/status", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("CapEff:"):
                    out["cap_eff"] = line.split(":", 1)[1].strip()
    except OSError as exc:
        out["cap_eff_error"] = _error(exc)
    return out


def _cgroup_dir():
    """The directory of this process's cgroup (version 2): the path of the ``0::``
    line of ``/proc/self/cgroup`` under :data:`CGROUP_ROOT`."""
    with open("/proc/self/cgroup", encoding="ascii") as handle:
        for line in handle:
            if line.startswith("0::"):
                return os.path.join(CGROUP_ROOT, line[3:].strip().lstrip("/"))
    raise ValueError("no cgroup version 2 line")


def _rlimit(value):
    return None if value == resource.RLIM_INFINITY else value


def limits():
    """The limits the runtime set, read from inside; nothing is attempted against one."""
    out = {"cgroup": None, **{name: None for name in CGROUP_FILES}, "rlimit_cpu": None,
           "errors": {}}
    try:
        directory = _cgroup_dir()
    except (OSError, ValueError) as exc:
        out["errors"]["cgroup"] = _error(exc)
    else:
        out["cgroup"] = directory
        for name in CGROUP_FILES:
            try:
                with open(os.path.join(directory, name), encoding="ascii") as handle:
                    out[name] = handle.read().strip()
            except OSError as exc:
                out["errors"][name] = _error(exc)
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    out["rlimit_cpu"] = [_rlimit(soft), _rlimit(hard)]
    return out


def _npy(data):
    """``(shape, descr, offset)`` of an ``.npy`` document's header."""
    if not data.startswith(_NPY_MAGIC):
        raise ValueError("not an npy document")
    major = data[6]
    if major == 1:
        (size,) = struct.unpack("<H", data[8:10])
        start = 10
    else:
        (size,) = struct.unpack("<I", data[8:12])
        start = 12
    header = ast.literal_eval(data[start:start + size].decode("latin1"))
    return tuple(header["shape"]), header["descr"], start + size


def _latest_open(data):
    """The latest value of a ``ts`` array of int64 datetimes, as an ISO instant."""
    shape, descr, offset = _npy(data)
    if not shape or shape[0] == 0:
        return None
    unit = descr[descr.index("[") + 1:-1] if "[" in descr else "ns"
    if descr[1:3] not in ("M8", "i8") or unit not in _UNITS:
        return None
    fmt = "<q" if descr[0] in "<|=" else ">q"
    values = struct.iter_unpack(fmt, data[offset:offset + 8 * shape[0]])
    last = max(v for (v,) in values)
    per = _UNITS[unit]
    instant = datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=last // per,
                                                           microseconds=(last % per) * 10**6
                                                           // per)
    return instant.isoformat()


def instrument(mount, index, meta):
    """One instrument of ``job.json``: its bars file, the length of each array, the
    bar count (the common length) and the latest open time when a ``ts`` is there."""
    name = meta.get("bars") if isinstance(meta, dict) else None
    out = {"index": index, "file": name, "arrays": {}, "count": None, "latest_open": None}
    try:
        with zipfile.ZipFile(os.path.join(mount, str(name))) as archive:
            for member in sorted(archive.namelist()):
                data = archive.read(member)
                key = member[:-4] if member.endswith(".npy") else member
                shape = _npy(data)[0]
                out["arrays"][key] = shape[0] if shape else None
                if key == "ts":
                    out["latest_open"] = _latest_open(data)
    except (OSError, ValueError, KeyError, SyntaxError, zipfile.BadZipFile) as exc:
        out["error"] = _error(exc)
        return out
    lengths = set(out["arrays"].values())
    out["count"] = lengths.pop() if len(lengths) == 1 else None
    return out


def mount_report(mount):
    """The files of the mount and, per instrument of its ``job.json``, its bars."""
    out = {"path": mount, "files": [], "instruments": None}
    try:
        for directory, _dirs, files in os.walk(mount):
            for name in files:
                path = os.path.join(directory, name)
                out["files"].append({"name": os.path.relpath(path, mount),
                                     "bytes": os.path.getsize(path)})
        out["files"].sort(key=lambda f: f["name"])
        with open(os.path.join(mount, JOB_FILE), encoding="utf-8") as handle:
            job = json.load(handle)
        out["instruments"] = [instrument(mount, i, meta)
                              for i, meta in enumerate(job.get("instruments", []))]
    except (OSError, ValueError, AttributeError) as exc:
        out["error"] = _error(exc)
    return out


def report(mount):
    net = {}
    net.update(routes())
    net.update(interfaces())
    net["connect"] = connect()
    under = (*CREATE_UNDER[:-1], mount, CREATE_UNDER[-1])
    return {
        "probe": 1,
        "network": net,
        "creates": [create(d) for d in under],
        "identity": identity(),
        "limits": limits(),
        "mount": mount_report(mount),
    }


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: probe.py <mount>\n")
        return 2
    sys.stdout.write(json.dumps(report(argv[1]), sort_keys=True) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
