"""Alert rules and alert state (DESIGN 15.1 to 15.3, 16.1 step 6). Built in
step S4.1; this module holds, so far, the rank rows of the day loop.

The rank rows on the timing statistic (DESIGN 11.1, 15.1; owner decisions
O-4, O-5, O-6, O-24; decisions 2026-10-12 59, 2026-10-17-m19 149 (a)):

- ``rank_rows(state_dir, setup, records, subjects, blocks, *, overlay=None,
  exposure=None, frames=None)``: decision 59's row for each block ``k`` of
  ``blocks``, in their order, over the candidate ``subjects`` (each mapped to
  its own instruments' calendars, as ``stats.rank_persistence`` takes them),
  with the track's ``epoch``, ``block_days`` and ``bar_seconds`` and
  ``alerts.rank_min_population`` from ``setup``. For blocks ``k - 1`` and
  ``k``, each candidate's gross timing return per day is
  ``paper.adjusted(..., "gross")`` over that block's trading dates (the
  candidate's own, ``stats.trading_dates``): one call per candidate per block,
  so each block is its own window with its own average positions (O-5). The
  values go into a paper-shaped frame (the candidate's ``subject``, ``kind``
  and ``date`` rows) under the column ``timing``. ``stats.rank_persistence``
  is then called three times with the same candidates and arguments: on
  ``timing``, giving the key ``timing``; on ``gross``, giving the key
  ``gross``; and on the default ``net_1x``, the call the day loop made before,
  giving the row with every key it had. The row is that third row with
  ``timing`` and ``gross`` added: ``statistic`` keeps its meaning, the net 1x
  figure of decision 59 (O-24). Rows of the three calls whose ``subjects``
  differ are a defect and raise ``ValueError``.
  ``records`` are the paper records (the staged ones in the day loop, with
  ``overlay`` the staging directory, as ``paper.adjusted`` takes them);
  ``exposure`` is the pair (unit records, position records) already read,
  handed to ``paper.adjusted`` (decision 147 (d)) so that the files are not
  read once per candidate and block; None reads them once here, ``overlay``'s
  first, and only when some candidate has a paper row in the two blocks.
  ``frames``, when a list, receives the timing frame of each block, in order
  (for inspection; the rows do not depend on it).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from discotrade import journal, paper, stats
from discotrade.config import Calendar

#: The column of the timing frame (decision 2026-10-17-m19 149 (a)).
TIMING = "timing"


def _exposure(state_dir: Path, track: str, overlay: Path | None
              ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The unit and position records, ``overlay``'s first, read once."""
    pair = []
    for reader in (paper.read_unit, paper.read_positions):
        frame = None if overlay is None else reader(overlay, track)
        if frame is None:
            frame = reader(state_dir, track)
        if frame is None:
            raise ValueError(f"{track} has no derived exposure records under "
                             f"{paper.PAPER_DIR}/{track}/")
        pair.append(frame)
    return pair[0], pair[1]


def rank_rows(state_dir: Path, setup: journal.Setup, records: pd.DataFrame,
              subjects: Mapping[str, Sequence[Calendar]], blocks: Iterable[int], *,
              overlay: Path | None = None,
              exposure: tuple[pd.DataFrame, pd.DataFrame] | None = None,
              frames: list[pd.DataFrame] | None = None) -> list[dict[str, Any]]:
    """Decision 2026-10-17-m19 149 (a)'s row of each block of ``blocks``:
    decision 59's net 1x row with ``timing`` and ``gross`` added (O-5, O-24)."""
    track = setup.track
    min_population = int(setup.thresholds["alerts.rank_min_population"])
    out: list[dict[str, Any]] = []
    for k in blocks:
        windows = [stats.block_dates(track.epoch, track.block_days, j) for j in (k - 1, k)]
        span = records[(records["date"] >= windows[0][0]) & (records["date"] <= windows[1][1])
                       & records["subject"].isin(list(subjects))]
        timing: list[pd.DataFrame] = []
        for subject in sorted(set(span["subject"])):
            mine = span[span["subject"] == subject]
            kind = str(mine["kind"].iloc[0])
            for first, last in windows:
                window = stats.trading_dates(subjects[subject], track.bar_seconds, first, last)
                if not window:
                    continue
                if exposure is None:
                    exposure = _exposure(state_dir, track.name, overlay)
                near = (exposure[0][exposure[0]["date"].isin(window)],
                        exposure[1][exposure[1]["date"].isin(window)])
                series = paper.adjusted(state_dir, setup, subject, window, "gross",
                                        records=mine, overlay=overlay, exposure=near)
                timing.append(pd.DataFrame({"subject": subject, "kind": kind,
                                            "date": list(series.index),
                                            TIMING: series.to_numpy(dtype="float64")}))
        frame = (pd.concat(timing, ignore_index=True) if timing
                 else pd.DataFrame(columns=["subject", "kind", "date", TIMING]))
        if frames is not None:
            frames.append(frame)
        kwargs: dict[str, Any] = {"epoch": track.epoch, "block_days": track.block_days,
                                  "bar_seconds": track.bar_seconds, "k": k,
                                  "min_population": min_population}
        on_timing = stats.rank_persistence(frame, subjects, column=TIMING, **kwargs)
        on_gross = stats.rank_persistence(span, subjects, column="gross", **kwargs)
        row = stats.rank_persistence(span, subjects, **kwargs)
        if not on_timing["subjects"] == on_gross["subjects"] == row["subjects"]:
            raise ValueError(f"block {k}: the timing, gross and net_1x rows hold different "
                             f"subjects ({on_timing['subjects']}, {on_gross['subjects']}, "
                             f"{row['subjects']})")
        row[TIMING] = on_timing["statistic"]
        row["gross"] = on_gross["statistic"]
        out.append(row)
    return out
