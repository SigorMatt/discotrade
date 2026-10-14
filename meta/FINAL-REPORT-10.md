VERDICT: mission 10 finished

# FINAL REPORT — mission 10 (roadmap step S2.0a)

Builder prompt: `meta/BUILDER-10-PROMPT.md`. Base 54cac11. This mission
builds roadmap step S2.0a as decisions 76 to 82 cut it: O-3's speed work
(decision 80), REVIEW-9's three should-fix items (decisions 78, 79),
finding D-007 (decision 77), and O-4's exposure-adjusted series as one
producer function read by no rule yet (decision 81). It closes no
milestone; it runs gate M1 again item by item and gate M0 at its pushed
tip (decision 82). It binds `meta/decisions/decisions-2026-10-14.md`
(cited as "decision N"; items 1 to 75 of the earlier files still bind) and
the owner's `meta/decisions/decisions-2026-10-13-owner.md` (cited as
"O-N").

## What changed

| Unit | Sha | What |
|---|---|---|
| U0 | b03a349 | `plan:` the plan, checkpoint and journal; D-007's status line in `meta/findings/FINDINGS.md` (answered by decision 77) |
| U1 | 4bf827d | `bars/store.py`: `day_run()`, each listed month file hashed once per day run (keyed by path and index entry), dropped on exit; `daily.py` holds it around the day; `tests/test_bar_day_run.py` |
| U2 | 164c8ce | `state.content_text` a column at a time (same text); `backtest.score` types shared columns once per window, costs over arrays; `executor._Priced` makes each bar's Timestamp once; `journal` builds the day's control rows as one frame; `tests/test_speed_pins.py` |
| U3 | 0518b34 | `paper.update` rebuilds when the paper file's dates differ from the journal index's dates before D, or the file is absent (decision 78); docstrings of `paper.py` and `daily.py`; three tests in `tests/test_paper.py` |
| U4 | f1a2599 | tests only (decisions 77, 79): two in `tests/test_replay.py`, one in `tests/test_replay_candidates.py`, fixture `tests/fixtures/scenarios/u4_t_days.jsonl`; no `src/` change |
| U5 | 6f8eec8 | `paper.adjusted`, `unit_bars`, `unit_returns`, `average_positions` (O-4, decision 81), computed on call, nothing stored, read by nothing; `tests/test_exposure.py` |
| U6 | — | gate M1 item by item and gate M0 at 23f245c (code 6f8eec8); no code commit; results in `meta/plan.md` and `meta/journal.md` |
| U7 | this commit | this report |

Meta commits between units: 1abf93a, 23f245c.

## Speed

All figures are from the builder's machine. Decision 80 (d)'s method:
a throwaway script outside the repository, state in a temp dir,
`cli.main` in-process, one foreground call each, nothing else running;
"controls" is a controls-only replay of `test_synth` on the gate
configuration, 20 days 2019-06-03..2019-06-28; "G1.3 scenario" is the
scenario's first 30 calendar days, 2019-06-03..2019-07-02 (22 replay days).

| Unit | Measurement | Before | After |
|---|---|---|---|
| U1 (parent b03a349) | controls | 49.20 s, 2.460 s/day | 34.88 s, 1.744 s/day |
| U1 (parent b03a349) | G1.3 scenario | 67.72 s, 3.078 s/day | 45.31 s, 2.059 s/day |
| U2 (parent 4bf827d) | controls | 35.41 s, 1.771 s/day | 20.64 s, 1.032 s/day |
| U2 (parent 4bf827d) | G1.3 scenario | 46.90 s, 2.132 s/day | 30.25 s, 1.375 s/day |

U2's "before" is its parent measured again, so it differs a little from
U1's "after" (1.771 against 1.744, 2.132 against 2.059 s/day).

Profiles (cProfile, one day, cumulative; the commit bodies note cProfile
inflates about 2x), from the commit bodies:

- U1 before: controls 2019-06-28 4.64 s, of it bar-file verification
  (`_matches`) 1.56 s over 91 reads of 24 files; G1.3 2019-07-02 5.72 s,
  `_matches` 1.86 s over 143.
- U1 after: controls 2019-06-28 3.37 s: `journal_day` 2.03 (`_day_rows`
  1.69, `control_evaluations` 1.03, `backtest.score` 0.96 over 4,
  `journal._rows` 0.58); step 1 0.99 (`_fetch` 0.73 of which
  `_verify_stored` 0.40; `check_gaps` 0.23); `content_hash` 0.83 over 33
  (bar-file verification 0.46 over 28, once per file; the rest journal row
  hashing); `executor.execute` 0.40; `journal.write_day` 0.34;
  `paper.update` 0.20. G1.3 2019-07-02 3.99 s: `journal_day` 2.59
  (`_day_rows` 2.22, `backtest.score` 1.13 over 12, `control_evaluations`
  1.02, `subject_rows` 0.53); step 1 0.94 (`_verify_stored` 0.48);
  `content_hash` 0.77 over 37 (bar files 0.43 over 32);
  `executor.execute` 0.55.
- U2 after: controls 2019-06-28 1.94 s: `journal_day` 0.84 (`_day_rows`
  0.73, `control_evaluations` 0.44, `score` 0.37 over 4, `_columns` 0.24
  over 204); step 1 0.73 (`_fetch` 0.51, `append` 0.24 of which fsync 0.17,
  `_verify_stored` 0.16, `check_gaps` 0.20); `content_hash` 0.23 over 33
  (was 0.83); `paper.update` 0.20; `write_day` 0.12; `executor.execute`
  0.11 (was 0.40). G1.3 2019-07-02 2.48 s: `journal_day` 1.36 (`_day_rows`
  1.25, `score` 0.52 over 12, `subject_rows` 0.51 of which
  `_strategy_targets` 0.24, `control_evaluations` 0.44, `_columns` 0.26);
  step 1 0.67 (`_verify_stored` 0.20); `content_hash` 0.23 over 37;
  `executor.execute` 0.23; `paper.update` 0.21; `table.build` 0.17.

Decision 80 (a), identical state, in each speed unit: the G1.3 scenario on
`test_synth` with the gate configuration (`init-state --as-of
2019-06-03T00:00:00+00:00`, then `replay --from 2019-06-03 --to 2019-07-02
--candidates tests/fixtures/scenarios/g1_lifecycle.jsonl`, 30 calendar
days, 22 replay days), run with `PYTHONPATH` at the parent's worktree and
at the commit's:

- U1 (parent b03a349 against 4bf827d): `diff -r --exclude=.git` printed
  nothing, `identical` (74 files outside `.git/`); state `HEAD`
  f88133f8e2d1a4c35d70394c88449a44bda757aa, tree
  a6f568b6214cd8e59dbe22fc47b5e4d0b6b02c39, 23 commits, the same at both.
- U2 (parent 4bf827d against 164c8ce): the same: `identical` (74 files),
  the same `HEAD`, tree and count of 23.

Gate times, mission 9 (at b62f5f0) and this mission (U6, at 23f245c, code
6f8eec8); pytest's time as `./scripts/gate` prints it, and the call's wall
time:

| Item | Mission 9 pytest | Mission 9 wall | Mission 10 pytest | Mission 10 wall |
|---|---|---|---|---|
| G1.1 | 891.52 s | 892 s | 345.34 s | 345.94 s |
| G1.2 | 323.44 s | 324 s | 155.31 s | 155.88 s |
| G1.3 | 1083.24 s | 1083 s | 449.56 s | 450.15 s |
| G1.4 | 0.51 s | 1 s | 0.51 s | 1.05 s |
| M1 total | about 2298 s (38 min) | | 950.72 s | 953.02 s (about 16 min) |
| M0 | | 342 s | | 247.77 s |

Every M1 item is under O-3's 10 minutes on this machine (the longest,
G1.3, 449.56 s). Against U2's estimates from the 30-day figures: G1.1
345 s within 268 to 374 s; G1.3 450 s within 367 to 484 s; G1.2 155 s
above both estimates (122 and 145 s). The M1 total is still above §18.2's
15 minutes, which O-2 waives for M1 only.

## Gate M1

Run at 23f245c (code 6f8eec8, the pushed tip when U6 ran), item by item as
O-2 and decision 82 rule: each `./scripts/gate M1 G1.<n>` its own
foreground call with a 20-minute timeout. Verbatim, with the wall time
the wrapper recorded:

```
G1.1 PASS 6 passed, 1 warning in 345.34s (0:05:45)
gate M1 G1.1: PASS
wall 345.94 s
```
```
G1.2 PASS 4 passed in 155.31s (0:02:35)
gate M1 G1.2: PASS
wall 155.88 s
```
```
G1.3 PASS 10 passed in 449.56s (0:07:29)
gate M1 G1.3: PASS
wall 450.15 s
```
```
G1.4 PASS 15 passed in 0.51s
gate M1 G1.4: PASS
wall 1.05 s
```

All four items print PASS. The one warning of G1.1 is O-1's net-return
rank-persistence statistic; `scripts/gate` prints only pytest's last line,
so its value is not in this output. No file under `tests/gates/` changed
in this mission.

## M0 still passes

At 23f245c (code 6f8eec8), `./scripts/gate M0`, one foreground call,
verbatim:

```
G0.1 PASS 62 passed in 57.13s
G0.2 PASS 7 passed in 93.14s (0:01:33)
G0.3 PASS 13 passed in 95.01s (0:01:35)
G0.4 PASS 4 passed in 0.27s
gate M0: PASS
wall 247.77 s
```

## Acceptance checks

- `./scripts/check` green three consecutive runs at 23f245c, whose code
  is 6f8eec8's: `1254 passed, 121 deselected` each, `check: green`, wall
  426.00, 431.66 and 428.55 s. Each unit commit was green 3 of 3 before it
  was made (its body says so).
- Gate M1 item by item, all PASS, and gate M0 PASS, above; no item above
  10 minutes, so no decision 80 (e) finding.
- `git diff 54cac11 -- config/ tests/gates/ tests/fixtures/config/` is
  empty; `git diff 54cac11 -- tests/fixtures/config_frozen.json` is empty
  (no entry changed, none added); `config/models.toml` does not exist.
  Checked at 23f245c when this report was drafted.
- Files changed since 54cac11 (`git diff --stat 54cac11 HEAD`): the four
  meta files, seven files under `src/discotrade/` (`backtest.py`,
  `bars/store.py`, `daily.py`, `executor.py`, `journal.py`, `paper.py`,
  `state.py`), one new fixture and six test files, each listed in its unit
  commit's body; U0 is `plan:`.
- Decision 80 (a)'s identical state for U1 and U2, above.

## Decisions 77 to 81: the tests that hold them

- 77 (D-007's refusal confirmed), held by decision 79 (a)'s tests:
  `tests/test_replay.py::test_a_saturday_waits_for_a_weekday_instrument_s_friday`,
  `tests/test_replay.py::test_on_one_calendar_the_refusal_is_mission_8_s`.
- 78 (the paper update heals an interrupted day):
  `tests/test_paper.py::test_a_journaled_day_missing_from_the_paper_file_is_back_after_the_next_day`,
  `::test_a_date_the_journal_does_not_hold_is_dropped_from_the_paper_file_by_the_next_day`,
  `::test_an_absent_paper_file_is_rebuilt_by_the_next_day`; the existing
  `::test_after_every_day_the_paper_file_equals_a_full_rebuild` still
  passes.
- 79 (a): the two `tests/test_replay.py` tests under 77. 79 (b):
  `tests/test_replay_candidates.py::test_admission_reads_t_s_trading_days_for_a_weekend_window`,
  with `tests/fixtures/scenarios/u4_t_days.jsonl`.
- 80 (speed): (b) in `tests/test_bar_day_run.py`:
  `test_each_listed_month_file_is_hashed_at_most_once_in_a_day_run`
  (parametrized on 0 and 2 approaches),
  `test_a_file_appended_to_in_the_day_run_is_read_again`,
  `test_a_file_changed_after_a_day_run_is_refused_by_the_next`,
  `test_a_file_revised_between_two_days_of_a_replay_fails_the_next_day`,
  `test_seeds_are_the_fixture_records`. (a) at function level, in
  `tests/test_speed_pins.py`: `test_content_text_every_kind_equals_the_parents`,
  `test_content_text_still_refuses_a_tab_or_a_newline`,
  `test_content_text_of_journal_and_bar_rows_equals_the_parents`,
  `test_score_rows_equal_the_parents`, `test_each_fill_bar_is_the_next_stored_bar`,
  `test_journal_days_equal_the_parents`, `test_span_rows_equal_the_parents`;
  (a) on the whole state: the diff in each speed unit's body (a command,
  not a test). (c) and (d): no test; by the commit bodies and the code.
- 81 (O-4), in `tests/test_exposure.py`: `test_seeds_are_the_fixture_records`,
  `test_the_window_holds_a_roll_and_a_weekend`,
  `test_unit_returns_equal_the_journal_gross_of_buy_and_hold_rows_on_the_same_bars`,
  `test_the_roll_gap_is_not_a_return`,
  `test_at_an_instruments_first_stored_bar_only_the_second_term_counts`,
  `test_hbar_exposure_and_the_adjusted_series_equal_the_tests_own`
  (parametrized on W and W2),
  `test_the_average_positions_change_with_w_and_the_function_uses_the_w_given`,
  `test_a_buy_and_hold_controls_gross_timing_return_is_zero`,
  `test_a_constant_position_has_an_adjusted_series_of_zeros_with_no_sharpe`,
  `test_net_minus_adjusted_equals_gross_minus_timing_on_every_day`,
  `test_nothing_is_stored_for_it`,
  `test_a_column_that_is_not_a_paper_value_is_refused`.

## What the tests prove

- Bar files (U1): on `test_mixed` days 2019-06-08 and 2019-06-09, with
  controls alone and with two approaches, no index entry is verified twice
  in a day run although month files are read more than once; a file
  appended to in a day run is read again (once per entry) and returns its
  new rows, equal to a read outside the run; a file revised after a day run
  is refused as revised data by the next day run's read; in a `test_synth`
  replay of 2019-06-03..04 with SYNB 2019-05 revised before the second day,
  the replay exits 1 naming 2019-06-04 with one `revised_data` alert and
  only 2019-06-03 journaled. Seen red: the parent behaviour, the result
  kept for the whole process, the result keyed by path only.
- Speed pins (U2): `content_text` equals the parent's row-at-a-time code
  byte for byte on a frame of every field kind written in the test, on six
  journal days and on a bar frame, and still refuses a tab or newline;
  `score`'s rows for five subjects on SYNA 2019-06-10..19 (with the roll)
  have the parent's digests and dtypes; each fill's bar is the next stored
  bar; six journal days across the 2019-07-01 redraw and the span rows
  equal the parent's. Nine named wrong changes (W1 to W9) were seen red.
  These pins hold on the cases they write; the whole-state identity holds
  on the 30-day replay of decision 80 (a).
- Paper heal (U3): on a three-day `test_mixed` run, a journaled day's
  paper rows removed, an extra date before the first journaled day, and
  the file absent each give a full rebuild's content hash after the next
  day; in the first two a re-run of the healed day changes no file. The
  first two were red against the parent's fallback; the absent-file test
  passed at the parent too.
- Refusal and T days (U4): a Saturday on `test_mixed` is refused while
  SYNA's Friday last bar has not closed under a delayed fake source, naming
  SYNA and the Friday, writing nothing, and runs an hour later; on
  `test_synth` at each of 337 hourly instants from 2019-06-03 to
  2019-06-17, over trading days from four calendar days before each
  instant's date to two after, `_unclosed` refuses exactly the days
  mission 8's rule (written in the test) refuses. `replay` passes
  2019-06-17..21 as T for a candidate on 2019-06-21, and the candidate is
  refused `not_better_than_weakest`, a verdict that the last seven trading
  days would have changed. Seen red: the refusal narrowed to D's own bars;
  T as the last `t_days` trading days; `_unclosed` refusing only days after
  last + 1 day.
- Adjusted series (U5): on `test_mixed` 2019-06-12..16 with windows W (a
  roll and a weekend) and W2, unit returns equal the journal gross of the
  buy-and-hold rows bar by bar and the test's own computation; the roll
  gap is not a return; at an instrument's first stored bar only the second
  term counts; `hbar`, the gross timing return and the adjusted `net_1x`
  and `net_2x` equal the test's own computation (importing nothing from
  `discotrade`) for `trend_ma` and `rc:1` on W and W2; `hbar` depends on
  the W given; buy-and-hold controls have gross timing return within 1e-12
  of 0 on every day of 15 windows not holding the first journaled day; a
  constant-1 position has gross timing return 0 and NaN Sharpe on W; net
  minus adjusted equals gross minus timing on every day of W for five
  subjects; `paper/test_mixed/` holds `daily.parquet` only; a non-paper
  column is refused. Seen red: `hbar` over the whole record, unit return
  on raw prices across a roll, the daily mean over instruments with a bar
  only.
- Gates: M1's four items and M0's four items pass at 23f245c, as above.

## NOT PROVEN

- The exposure-adjusted series (`paper.adjusted`) is read by no lifecycle
  rule, statistic, table field, alert or gate; its readers and O-18's
  register are step S2.0b's. It is tested only on `test_mixed`
  2019-06-12..16 with the two windows and subjects above.
- O-5 to O-9 and O-14 are not built.
- The speed figures and gate times are from the builder's machine, one
  call each; the per-day cost still grows with the history, so the
  per-day figures from 20 or 22 days are lower bounds for a year, and G1.2
  ran above both of U2's estimates. A slower machine or more history can
  put an M1 item over 10 minutes again.
- A stored bar file is now hashed once per day run, not on every read: a
  file changed on disk during a day run, after its first verified read in
  that run, is not refused by that run; the next day run's first read
  refuses it (decision 80 (b)), which the tests show.
- Decision 80 (a)'s identity was shown on one 30-day replay of the G1.3
  scenario on `test_synth`, not on `test_mixed` nor over a year; the pins
  of `tests/test_speed_pins.py` hold on the frames and days they write.
- Decision 80 (c) (one process, no threads) rests on the code and the
  commit bodies; no test asserts it.
- U3 heals on dates only: a paper file holding the right dates with wrong
  row values is not detected or rebuilt (the commit body says so). The
  heal is tested on the paper file only; no other incrementally updated
  derived file was found (U3's body).
- U5 stores nothing (decision 81 (d) left the shape to the builder), so
  decision 78's heal rule and 81 (d)'s rebuild, re-run and staging checks
  are vacuous for it; the series is recomputed on every call, and its cost
  over a year's history is not measured.
- U4's equivalence with mission 8's rule (79 (a), second test) holds at
  the 337 hourly instants and the days around each that it covers, on one
  calendar; the Saturday refusal uses a fake delayed source, not a real
  one.
- U4's T-days verdict depends on a score (0.3) and parameter sets chosen by
  a scratch search so that the window changes the verdict; it shows the
  `not_better_than_weakest` direction only.
- No number from outside the project was added in this mission.
- Carried from FINAL-REPORT-9, still open: admission is driven only by
  scripted candidates whose T metrics a file supplies (scoring on T is step
  S3.2's); the `cutoff` behind `clean` comes from a test or a scenario file
  until S3.2; approach sources still run in-process until S2.2; the replay
  has no provider, coordinator, issue sink or sandbox option; G1.1's
  statistical bounds hold on the seeds the test writes, and the net-return
  rank-persistence figure it reports as a warning was again not read from
  the gate's output; G1.3's dormancy and return rows are what the fixed
  seeds produce, not designed in; what the socket backstop cannot see
  (`socket.SocketType` used directly, a binding taken before the session
  starts, child processes, a module- or session-scoped fixture first set up
  by a `network` test), glibc's `gethostbyname_ex` behaviour, and the
  scratch `network` test's resolver use; decision 68 (b) with the day's
  admission doing the displacing; the table not tested under 900 days.
  Carried from FINAL-REPORT-8 through FINAL-REPORT-9, unchanged: dormancy
  and the matched draw through `run-day` only at lowered values; step 1's
  writes not staged; retry, `run_failed`, the push to a remote and catch-up
  are step S4.2's; the weekly recomputation not wired into the day;
  mission 7's items on interrupted `init-state`, the lock, the carry guard,
  roll-gap notices, `revised_data` by error text; the half-tick spread
  floor, the G0.1 roll probe, G0.1's single fixture, D-006 (deferred to
  S2.1), G0.2's and G0.3's limits, G0.4's matching, 168 unverified cost
  values and D-003. Taken by this mission and no longer open: G1.3 near its
  budget (now 450 s) and U3's 2.48 s per day as the speed figure
  (superseded by U1 and U2's measurements); the interrupted-day paper file
  (REVIEW-9 should-fix 1), the untested branch of the refusal and the
  untested T days (should-fix 2 and 3) are now tested, within the limits
  above.

## Findings filed and answered

- D-007 (filed in mission 9 U2): answered by decision 77; its status line
  was appended in U0 (b03a349); decision 79's tests that hold it are U4's
  (f1a2599).
- No new finding filed: every gate M1 item ran under 10 minutes, so
  decision 80 (e)'s finding was not needed. `git diff 54cac11 --
  meta/findings/FINDINGS.md` shows only D-007's status line.
- HF-006 and HF-007 stay open; D-003 stays; D-006 stays deferred to S2.1.

## Review items

| Item | Review | Resolution | Sha |
|---|---|---|---|
| REVIEW-9 should-fix 1 | The per-day paper update no longer healed an interrupted day; the docstring claimed more than the tests showed | U3, decision 78: rebuild when the paper file's dates differ from the journal index's before D or the file is absent; three tests; docstrings narrowed | 0518b34 |
| REVIEW-9 should-fix 2 | No test covered the part of the not-closed refusal that protects I-2 | U4, decision 79 (a): the mixed-calendar Saturday test and the one-calendar equivalence with mission 8's rule; the reviewer's narrowing seen red | f1a2599 |
| REVIEW-9 should-fix 3 | The T days `replay` passes to admission were untested | U4, decision 79 (b): T pinned to 2019-06-17..21 for a weekend window, with a verdict that depends on it; last `t_days` trading days seen red | f1a2599 |
| Finding D-007 | `run-day`'s refusal with decision 72's clock on a mixed-calendar track | U0 status line, decision 77 (rule confirmed); held by U4's tests, decision 79 | b03a349, f1a2599 |
| Owner decision O-3 | The day loop's speed: each gate M1 item under 10 minutes | U1 and U2, decision 80: state identical at parent and commit; gate M1 at U6 (23f245c): G1.1 345 s, G1.2 155 s, G1.3 450 s, G1.4 1 s | 4bf827d, 164c8ce |

VERDICT: mission 10 finished
