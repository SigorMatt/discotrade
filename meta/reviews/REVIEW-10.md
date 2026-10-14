# REVIEW-10 — cold review of mission 10 (roadmap step S2.0a)

Base: 7214fd8 (`review: mission 9`, the last `review:` commit). Range
`7214fd8..origin/main`, tip 7cbb2bb. Unit commits reviewed, one sub-agent
each in a worktree at that commit: 4bf827d (U1), 164c8ce (U2), 0518b34
(U3), f1a2599 (U4), 6f8eec8 (U5). Read for forbidden edits only: 54cac11
(the kit, applied verbatim by the architect's zip: `KIT.md`,
`meta/BACKLOG.md`, `meta/ROADMAP.md`, `meta/BUILDER-10-PROMPT.md`,
`meta/decisions/decisions-2026-10-14.md`), b03a349 (`plan:`; its
`meta/findings/FINDINGS.md` change is D-007's status line only), 1abf93a
and 23f245c (`meta:`, plan, checkpoint and journal), 7cbb2bb (`report:`).

`git diff 7214fd8 origin/main -- config/ tests/gates/ tests/fixtures/config/
tests/fixtures/config_frozen.json DESIGN.md SPEC.md PLAYBOOK.toml .claude
templates docs` is empty; `config/models.toml` does not exist.

## Gate

not a closing mission

(Decision 82: mission 10 closes no milestone. The builder's gate M1 and
M0 runs at 23f245c are reported in `meta/FINAL-REPORT-10.md`; this review
did not run them again.)

## Blockers

None.

## Should-fix

None.

## Notes

1. U1 (4bf827d): a month file changed on disk during a day run, after its
   first verified read in that run, is served from the run's cached frame
   (`src/discotrade/bars/store.py` around the cached-read paths) instead of
   being refused; the next day run's first read refuses it. Decision 80 (b)
   permits exactly this, and FINAL-REPORT-10 §NOT PROVEN states it. No test
   covers a partial append that fails mid-day while the day continues.
2. U2 (164c8ce): `state._column_fields` reads `column._values`, a private
   pandas attribute (`src/discotrade/state.py:124`). It is correct on the
   locked pandas, and `tests/test_speed_pins.py` pins `content_text`
   against the parent's row-at-a-time code on every field kind, so a pandas
   upgrade that changed the branch taken would turn those pins red rather
   than pass silently. `column.array` or `to_numpy()` with a dtype check
   would avoid the private name.
3. U5 (6f8eec8): `paper.py:367` calls the private `journal._empty()`;
   `paper.adjusted(records=...)` reads `hbar` from `state_dir`/`overlay`, so
   a future caller passing staged records must pass `overlay` too
   (mission 11's readers). Nothing in `src/` or `tests/gates/` calls the
   new functions, as decision 81 (e) requires.
4. U3 (0518b34): the heal compares dates only (stated in the docstrings and
   the report). The older non-atomic `_move` still means a death between
   the `journal/` and `ledger/` moves loses that day's lifecycle and rank
   rows; this is outside decision 78 and not a regression.
5. U4 (f1a2599): the Saturday test does not itself assert that SYNX's
   Saturday bars had closed at the refused instant (true from the fixtures);
   the mission 8 equivalence test shares `latest_closed_day` with the code
   under test, so a fault in that helper would not show there.
6. The U2 reviewer independently reproduced decision 80 (a)'s identical
   state at 4bf827d and 164c8ce: `identical` (74 files), state `HEAD`
   f88133f8e2d1a4c35d70394c88449a44bda757aa, tree
   a6f568b6214cd8e59dbe22fc47b5e4d0b6b02c39, 23 commits, as the body says.
   The speed figures (decision 80 (d)) and the gate times were not
   re-measured.
7. hands: with the five per-commit sub-agents running concurrently on a
   4-core machine, `./scripts/check` took 906 to 944 s per run (the builder
   reports about 430 s alone), and one reviewer's single-call run was cut
   off by its own 1150 s timeout and had to be run in parts. That is close
   to the 20-minute tool cap of HF-006; the protocol could say whether
   per-commit reviewers may run concurrently.

## Per-commit verdicts

### 4bf827d (U1)

Review of 4bf827d (U1, "bars: each listed month file hashed once per day run, checked again by the next"). Verdict: pass, no blocker.

1. **Unit:** mission 10 U1. It claims O-3, decision 80 (a)-(d), DESIGN §5.2, §9.2, §16.1, §16.4 and §18.2, and decisions 18, 31 and 35. The brief lists §5.2, §9.2, §16.1 and §18.2; the commit adds §16.4. It changes `src/discotrade/bars/store.py` and `src/discotrade/daily.py` and adds `tests/test_bar_day_run.py`.
2. **Test-first: pass.**
   - With the parent's source, the new test file fails to import (`day_run` does not exist yet).
   - With a do-nothing `day_run` added to the parent, 4 tests fail: both hash-once day tests, the append test and the changed-after-run test. Two stay green: the seeds test, and the replay revised-file test, which guards what the parent already does.
   - Keeping the cache for the whole process turns the changed-after-run test and the replay revised-file test red.
   - Keying the cache by path only turns 13 tests red across `test_bar_day_run` and `test_daily`.
3. **`./scripts/check`: green, but not as one call.** Run whole, it was killed at my 1150 s timeout (machine load about 5.4 on 4 cores). Run as separate steps it was green:
   - ruff: "All checks passed!"
   - pytest in three parts: "428 passed in 502.50s", "412 passed in 371.10s", "388 passed in 164.22s" (1228 tests, about 17 minutes in total).
   - smoke: "discotrade 0.1.0", "config check: ok, 168 unverified values".
4. **Design and invariants: conform.**
   - Every reader still refuses a file whose hash does not match.
   - Cache entries are keyed by absolute path plus the index entry's rows and hash, so a file appended to mid-day is read and hashed again.
   - The cache is cleared in a `finally`, so it goes even when the day fails. Nested `day_run` calls restore the outer cache.
   - Nothing is written to state, no threads or processes are added, and there is no new dependency.
   - No network, secret or wall clock is used, and nothing under `src/` names a market.
   - Frames handed to callers are copies (boolean mask or `concat`), so a caller cannot change a cached frame.
5. **Forbidden touches: none.** The commit touches only those three files and no config. The `meta/plan.md`, `CHECKPOINT.md` and decisions changes since 7214fd8 come from the earlier kit and U0 commits, not this one. The commit body lists every file and gives 80 (a)'s identical-state output and 80 (d)'s before/after times, the profile after, and the one-year time per gate M1 item.

**NOT proven by me:** I did not rerun the identical-state comparison, the timings or the profile. Not tested anywhere: a file changed partway through a day run, such as an append that fails halfway while the day carries on. `store.py` lines ~289 and ~358 serve the cached frame for that entry instead of refusing or recovering the file, as the parent did. Decision 80 (b) allows checking once per day run, so this is a should-fix at most, for a test or a note.

**Defects:** no candidate blockers. One should-fix that is not about this code: `./scripts/check` takes about 17 minutes of pytest under this load, which goes past the 1200 s limit for one command. That is worth a hands finding (HF).

### 164c8ce (U2)

Review of 164c8ce (mission 10 U2: "speed: content hash a column at a time, score and journal rows built once per window"). Verdict: pass, no blocker.

1. **Unit and DESIGN sections:** mission 10 U2, O-3 and decision 80 (a)-(d). It claims DESIGN §7, §9.2, §9.3, §10.4 and §16.1, as the brief does. It changes `src/discotrade/state.py`, `src/discotrade/backtest.py`, `src/discotrade/executor.py` and `src/discotrade/journal.py`, and adds `tests/test_speed_pins.py`. Pass.
2. **Test-first:** with the four `src/` files put back to the parent, `tests/test_speed_pins.py` gives 7 passed. That is expected for a speed refactor whose pins compare against the parent. At the commit, 7 passed. Five of the named wrong changes went red as the body says, each reverted: W2 (3 failed), W3 (1 failed), W4 (3 failed), W6 (1 failed), W9 (3 errors, `JournalError`). Pass.
3. **`./scripts/check` at the commit:** `1235 passed, 121 deselected in 912.01s (0:15:12)`, then `config check: ok, 168 unverified values` and `check: green`. Pass.
4. **Design conformance:** pass.
   - I reproduced 80 (a) myself with my own script outside the repo, using the commit body's command. Each side ran with its own source tree on the path.
   - `diff -r --exclude=.git` printed `identical` (74 files). Both states have HEAD `f88133f8e2d1a4c35d70394c88449a44bda757aa`, tree `a6f568b6214cd8e59dbe22fc47b5e4d0b6b02c39` and 23 commits, the same as the body.
   - Reading the code found no change in meaning: float text is still `.17g`, NaT is still empty, datetimes are UTC nanoseconds, rows are sorted the same way, and `costs.net` over arrays does the same float operations. The journal frame is retyped by the arrow schema in `_frame` either way.
   - No new dependency, no threads or processes, no wall clock, no market name and no config change (I-9 to I-12, I-14, 80 (c)).
5. **Forbidden touches and commit body:** pass. The commit touches only its five files: no protected document, no `meta/plan.md` or `meta/CHECKPOINT.md`, and `git diff 7214fd8 164c8ce -- config/` is empty. The body lists every file, claims only what the tests show, and gives (d)'s two before/after measurements, the profile after and the one-year times (all under 10 minutes).

**Not proven:** I did not re-measure (d)'s times. The one-year figures are estimates, and the M1 gate items themselves were not run.

**Should-fix (minor):** `src/discotrade/state.py` `_column_fields` reads `column._values`, a private pandas attribute. It works on the locked pandas 3.0.6, but a pandas upgrade could quietly change which branch runs. `column.array` or `column.to_numpy()` with a dtype check would avoid that.

My review worktrees are removed. `/tmp/rv10-u1` belongs to another review and I left it in place.

### 0518b34 (U3)

0518b34 (mission 10 U3, REVIEW-9 should-fix 1): **pass**. No blocker and no should-fix found.

1. **Unit:** the commit names U3, decision 78 and DESIGN §9.3 and §16.2. It changes `src/discotrade/paper.py`, `src/discotrade/daily.py` (docstring only) and `tests/test_paper.py`, which is what the brief allows. The body lists every file.
2. **Test-first:** with `paper.py` and `daily.py` put back to the parent, the missing-day and extra-date tests went red (content hash mismatch at `tests/test_paper.py:315`). The absent-file test stayed green, as the body says. With the commit restored, all 15 tests in `tests/test_paper.py` pass. A counting plugin I wrote shows `update` still adds the day without a rebuild on 7 of 12 calls, so the dates check does not force a rebuild every day.
3. **`./scripts/check` at 0518b34:** `All checks passed!` / `=============== 1238 passed, 121 deselected in 943.96s (0:15:43) ===============` / `config check: ok, 168 unverified values` / `check: green`.
4. **Decision 78:** pass.
   - The paper file's dates are compared with the journal index's dates strictly before D (`paper.py:269`, `d < day`), and the staged index is read first. A missing date, an extra date or a missing file triggers a full rebuild.
   - The stored `date32` column reads back as `datetime.date`, so the set comparison works.
   - The rebuild is written only into staging (`daily.py:331`). A re-run of a journaled D never calls `update` and writes nothing (I-6, tested).
   - Both docstrings say "equal to a rebuild" only together with the rule and say that only dates are checked, not row values.
   - The claim that no other derived file is updated incrementally holds. `table.json` is rebuilt every day from the records. Its `_DAY_SUMS` is a cache in memory, not a file. The rank-persistence and lifecycle files are append-only ledgers. Decision 81's records did not exist yet at this commit.
   - I-5, I-9, I-10, I-11, I-12 and I-14 are untouched, and there is no new dependency.
5. **Forbidden files:** the unit commit touches only its three files, and `config/` is unchanged from 7214fd8 to 0518b34. The range does include changes to `meta/plan.md`, `meta/CHECKPOINT.md`, the decisions file, ROADMAP and BACKLOG, but they come from the kit, plan and meta commits, not from U3. The body claims only what the tests show.

**NOT PROVEN:**
- The rule does not detect stale row values for a date the file already holds; the docstring says so.
- No test kills the process during `_move` itself; the tests simulate the damaged file. If the process dies between the `journal/` and `ledger/` moves, the interrupted day's lifecycle and rank rows are still lost. That is the older §16.2 non-atomic move, outside this unit.

The worktree `/tmp/rv10-u3` has been removed; the other `rv10-*` worktrees were left in place.

### f1a2599 (U4)

1. **Commit:** f1a2599, mission 10 U4. It covers REVIEW-9 should-fix 2 and 3 and finding D-007 under decisions 77 and 79. It claims DESIGN §4.1, §10.3, §16.1 and §16.4 and decisions 51, 63, 72 and 73. Verdict: **pass**.

2. **Wrong changes: pass, both red, both reverted.**
   - (a) With `day_end(cal, day - timedelta(days=1))` in `_unclosed` (daily.py:179), the Saturday test fails (`assert status == 1`, got 0). The mission 8 test stays green, as expected on one calendar.
   - (b) With T as the last 7 trading days in `replay.t_days`, the admission test fails at the pinned days, which came out as 06-13..06-21. With that one assertion removed, it fails at the verdict instead: "admitted (displaced)".

3. **`./scripts/check`: pass.** Final lines: `1241 passed, 121 deselected in 943.77s (0:15:43)` / `config check: ok, 168 unverified values` / `check: green`.

4. **Decision 79 conformance: pass.**
   - (a) First test: SYNA is on a fake delayed source, and the test says so. The Saturday is refused at 06-09 00:00, naming SYNA and 06-06, with nothing written. It runs at 01:00.
   - (a) Second test: it compares the real `daily._unclosed` with mission 8's rule, written in the test file. It checks every hour from 06-03 00:00 to 06-17 00:00, which is 337 instants and fully 14 calendar days. At each instant it checks the trading days from 4 days before to 2 days after, and the commit body says it covers only those.
   - (b): it runs on test_synth (t_days 7) and pins T to exactly 06-17..06-21, the five weekdays. The verdict depends on the window: `not_better_than_weakest` over the right T and `displaced` over the wrong one. That is the "reverse" form decision 79 allows.
   - Invariants: no network or secret, and git runs with `GIT_ALLOW_PROTOCOL=file`; both files are already in `SUBPROCESS_FILES`. Dates are fixed, there is no random draw, and state lives in `tmp_path`.

5. **Forbidden touches: pass.** The commit changes only its 3 test and fixture files, and none of them is under config/, tests/gates/, tests/fixtures/config or the never-edited files. The meta/ changes in 7214fd8..f1a2599 come from other commits. The body lists every file and claims no more than the tests prove.

**Not proven:**
- The Saturday test never directly asserts that SYNX's Saturday bars had closed at 06-09 00:00. SYNA comes first in the instrument order, so the refusal naming SYNA does not show it. It is true from the fixtures: SYNX's calendar is always_open on UTC days, and its source's `available_until` is `now`.
- The mission 8 comparison shares `latest_closed_day` with the code under test, so a fault in that helper would not show up there.

**Defects:** none found, neither candidate blocker nor should-fix. The worktree /tmp/rv10-u4 has been removed.

### 6f8eec8 (U5)

6f8eec8 (mission 10 U5). Verdict: **pass**, with no candidate blocker and no should-fix.

1. **Unit:** U5 static exposure, the unit return and the adjusted series. It claims O-4, decision 81 (and 78), DESIGN §7.2, §8, §9.2, §9.3 and decisions 23, 24, 25, 39. The commit touches only `src/discotrade/paper.py` and `tests/test_exposure.py`, and the body lists both.
2. **Test-first:** pass. With the parent's paper.py, `tests/test_exposure.py` gives 10 failed, 3 passed (AttributeError). Each wrong change went red and was reverted:
   - hbar over the whole paper record: 5 failed.
   - Roll gaps zeroed in the unit return: 6 failed.
   - Daily mean over the instruments with a bar on D: 3 failed.
   These match the counts in the commit body.
3. **./scripts/check:** green. Final lines verbatim: `=============== 1254 passed, 121 deselected in 906.95s (0:15:06) ===============` / `config check: ok, 168 unverified values` / `check: green`.
4. **Decision 81 and O-4:** pass.
   - (a) `adjusted(subject, days=W, column)` takes gross, net_1x or net_2x, refuses other columns, and returns the paper column minus exposure on the subject's paper days in W.
   - (b) The unit return comes from `backtest.score` with start (1,1); u-1 is the previous stored bar and gaps apply only at u (prices adjusted as of u). At the first trusted bar only the second term counts, and R_i(D) is summed per trading date.
   - (c) Exposure is Σ_i hbar_i(W)·R_i(D) / N over all N instruments (N=1 for a bh control, matching `build`), with a missing bar counting 0. hbar is the mean journal position over rows in W, 0 with no row.
   - The test's own computation uses only pyarrow, pandas and json and is not a copy of the code. It takes a bar's trading date from the journal rows rather than the calendar, and its docstring says so.
   - Every brief gate item is covered (trend_ma and rc:1, a window with the roll and a weekend, W against W2, the 15 bh windows, constant position with NaN Sharpe, the net/gross identity).
   - Nothing in `src/` or `tests/gates` calls the new functions.
   - Saying 81(d) is vacuous holds: nothing is stored, and the test asserts `paper/test_mixed/` holds only `daily.parquet`.
   - Invariants: no strategy slice is built and only stored (closed) bars are read, so I-2 holds. No venue names (I-9), thresholds (I-10), network, secrets or wall clock (I-11, I-12) appear in `src`, run state stays out of the repo (I-14), and no dependency is added.
5. **Forbidden touches:** none. `config/` is unchanged from 7214fd8 to 6f8eec8. The meta/decisions/plan/checkpoint changes in that range belong to other commits, not this unit. The body states the window, subjects, instruments, seeds and as-of exactly and claims no more than the tests show.

**NOT proven:**
- The function was tested on `test_mixed` only, with W within 2019-06-12..16; the bh windows are limited to those days.
- The case where a journal file for day D holds rows of another date was not exercised. Today a day's journal is evaluated on `DateRange(day, day)`, so it does not arise.

**Notes (not defects):**
- `paper.py:367` calls the private `journal._empty()`.
- `adjusted(records=...)` reads hbar from `state_dir`/`overlay` only, so a caller who passes staged records must also pass `overlay`.

The `/tmp/rv10-u5` worktree is removed. Older review worktrees (`/tmp/rv10-u1`, `/tmp/rv10-u2`, `/tmp/rv10-u2p`) are still registered.
