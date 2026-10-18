"""``scripts/speed``, the measurement of O-26 item 4 (meta/decisions/2026-10-18-owner.md;
decision 156 (d) of meta/decisions/decisions-2026-10-18-m20.md; I-12, I-14).

``scripts/speed.py``, the Python ``scripts/speed`` runs, is loaded from its file
and its ``main`` called here, once per process the command would start, over
the three-day span Monday 2019-06-03 to Wednesday 2019-06-05 of the G1.3
scenario, with ``--budget-seconds 15`` and the module's timer replaced by
``FakeClock``, which returns the readings written here, so that the first call
stops after its second day and a second call is needed. The test checks
``days.jsonl`` (each day's seconds from the readings, its process and its
subject count, which the test counts itself from the day's journal file with
pyarrow), the counted days and the two windows' arithmetic, the process
starts, the copy ``before-last`` and the lines printed. The command runs the
last day again in a fresh process of the ``discotrade`` command (no
connection is opened); its wall time comes from the fake readings too. A
work directory inside the code repository is refused.

The work directory is the test's temporary directory; the state it builds is
under it. Time comes only from the replay's clock and the fake readings.
"""

import importlib.util
import json
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from discotrade.cli import REPO_ROOT

TRACK = "test_synth"
DAYS = (date(2019, 6, 3), date(2019, 6, 4), date(2019, 6, 5))


def load_speed():
    path = REPO_ROOT / "scripts" / "speed.py"
    spec = importlib.util.spec_from_file_location("speed_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClock:
    def __init__(self, readings):
        self.readings = list(readings)

    def __call__(self):
        return self.readings.pop(0)


def subjects(state: Path, day: date) -> int:
    path = state / "journal" / TRACK / f"{day.year:04d}" / f"{day.isoformat()}.parquet"
    return len(set(pq.read_table(path).column("subject").to_pylist()))


def test_three_days_in_two_processes(tmp_path, monkeypatch, capsys):
    speed = load_speed()
    work = tmp_path / "work"
    argv = ["--work", str(work), "--from", DAYS[0].isoformat(), "--to", DAYS[-1].isoformat(),
            "--budget-seconds", "15"]

    # Process 1: its start, day 1's end (7 s), the next day's start after the
    # bookkeeping, day 2's end (17 s; 25 s from the start, past the budget).
    first = FakeClock([100.0, 107.0, 108.0, 125.0])
    monkeypatch.setattr(speed, "clock", first)
    assert speed.main(argv) == 0
    assert capsys.readouterr().out.splitlines() == ["speed: continue 2 of 3 days"]
    assert first.readings == []
    assert not (work / "before-last").exists()

    # Process 2: its start, the copy before the last day (3 s, left out), day
    # 3's end (10 s), the fresh process's start and end (5.5 s).
    second = FakeClock([1000.0, 1001.0, 1004.0, 1013.0, 2000.0, 2005.5])
    monkeypatch.setattr(speed, "clock", second)
    assert speed.main(argv) == 0
    out = capsys.readouterr().out.splitlines()
    assert second.readings == []

    state = work / "state"
    counts = [subjects(state, d) for d in DAYS]
    lines = [json.loads(x) for x in (work / "days.jsonl").read_text("utf-8").splitlines()]
    assert lines == [
        {"date": "2019-06-03", "seconds": 7.0, "process": 1, "subjects": counts[0]},
        {"date": "2019-06-04", "seconds": 17.0, "process": 1, "subjects": counts[1]},
        {"date": "2019-06-05", "seconds": 10.0, "process": 2, "subjects": counts[2]},
    ]
    # Counted: 06-04 only (06-03 is the span's first day, 06-05 a process's first).
    figure = 17.0 / counts[1]
    assert out == [
        f"speed first30: {figure:.6f} s per subject-day (1 days counted)",
        f"speed last30: {figure:.6f} s per subject-day (1 days counted)",
        "speed ratio: 1.000",
        "speed fresh last day: 5.500 s",
        "speed process starts: 2019-06-03 2019-06-05",
        "speed: done",
    ]
    before = work / "before-last"
    assert (before / ".git").is_dir()
    index = (before / "journal" / TRACK / "index.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(x)["date"] for x in index] == ["2019-06-03", "2019-06-04"]
    fresh = (work / "fresh" / "journal" / TRACK / "index.jsonl").read_text("utf-8")
    assert [json.loads(x)["date"] for x in fresh.splitlines()] == [d.isoformat() for d in DAYS]
    assert not any((state / name).exists() for name in ("days.jsonl", "before-last"))


def test_window_arithmetic_and_process_starts():
    speed = load_speed()
    days = [{"date": "2019-06-03", "seconds": 9.0, "process": 1, "subjects": 3},
            {"date": "2019-06-04", "seconds": 2.0, "process": 1, "subjects": 4},
            {"date": "2019-06-05", "seconds": 4.0, "process": 1, "subjects": 4},
            {"date": "2019-06-06", "seconds": 8.0, "process": 2, "subjects": 5},
            {"date": "2019-06-07", "seconds": 3.0, "process": 2, "subjects": 2}]
    assert speed.window_figure(days, date(2019, 6, 3), date(2019, 6, 7),
                               date(2019, 6, 3)) == ((2.0 + 4.0 + 3.0) / (4 + 4 + 2), 3)
    assert speed.window_figure(days, date(2019, 6, 5), date(2019, 6, 6),
                               date(2019, 6, 3)) == (4.0 / 4, 1)
    figure, counted = speed.window_figure(days, date(2019, 7, 1), date(2019, 7, 2),
                                          date(2019, 6, 3))
    assert counted == 0 and figure != figure          # nan with no counted day
    assert speed.process_starts(days) == ["2019-06-03", "2019-06-06"]


def test_a_work_directory_inside_the_repository_is_refused(capsys):
    speed = load_speed()
    assert speed.main(["--work", str(REPO_ROOT / "tmp-speed")]) == 2
    assert "inside the code repository" in capsys.readouterr().err
    assert not (REPO_ROOT / "tmp-speed").exists()


@pytest.mark.parametrize("name", ["speed", "speed.py"])
def test_the_command_files_exist(name):
    path = REPO_ROOT / "scripts" / name
    assert path.is_file()
    if name == "speed":
        assert path.stat().st_mode & 0o111
