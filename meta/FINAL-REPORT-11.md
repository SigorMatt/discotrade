VERDICT: mission 11 finished

# FINAL REPORT — mission 11 (roadmap step S2.0b)

Brief: `meta/BUILDER-11-PROMPT.md`. Base c3a3f1d. Decisions:
`meta/decisions/decisions-2026-10-14-m11.md` (83 to 90), with the owner's
O-11 to O-13, O-15, O-16 and O-18. This mission closes no milestone; gate
M1 was run again item by item and gate M0 once, as decision 90 says.

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | 7629de6 | plan, checkpoint, journal; HF-008 (REVIEW-10 note 7, decision 90 (d)) |
| U1 | 93c2f91 | derived exposure records `paper/<track>/unit.parquet` (R_i(D)) and `positions.parquet` (rows, summed position per subject, instrument, date), staged with the day, healed by decision 78's rule; `paper.adjusted` reads them; `journal._empty` no longer called from `paper.py`; staged callers pass `overlay` (decision 84) |
| U2 | 489e749 | lifecycle steps 2 and 3 on the adjusted Sharpe over decision 85's `W`, each subject with its own average positions; `dormant`, `returned`, `displaced` rows carry `adjusted` and `plain` (decisions 85, 87); `ledger.py` gains `FIGURES`/`FIGURE_REASONS` (finding D-010) |
| U3 | 5962663 | admission on `adjusted_t["sharpe"]`, full cell on each live approach's own adjusted series over T; candidates lines require `adjusted_t`; trial rows gain `adjusted_t`, `adjusted_w`; `admitted`/`displaced` rows carry decision 87's keys; all three scenario files gain `adjusted_t`; `ledger.py` `TRIAL_FIGURES` and `cli.py` (track loaded before `--candidates`) noted under D-010 (decisions 86, 87) |
| U4 | 3ff738a | table approach rows gain `adjusted_sharpe`, `adjusted_sharpe_2x`, `avg_position`, `adjusted_admission_score`; `null` for controls and portfolio series; `table.md` labels each figure column adjusted or plain; deflated figures stay plain (decision 88) |
| U5 | 95650a4 | `tests/fixtures/return_readers.toml` (24 entries) and `tests/test_return_readers.py`, the ast audit (decision 89) |
| U6 | 6b61c6e | `tests/gates/test_g1_3_lifecycle.py` on the adjusted measure (decision 90 (a)); no scenario line changed |
| U7 | this commit | this report |

Meta commits between units: db467d8, e80ccb0, 8da0276, bc96cf2, d9332b1,
and the one that closes the mission.

Existing tests changed in what they assert, each under a cited decision
and named in its commit body: `tests/test_exposure.py::test_nothing_is_stored_for_it`
became `test_nothing_is_stored_for_it_but_the_records` (decision 84
replaces decision 81 (d)'s "nothing stored"); seven step 2/3 tests of
`tests/test_lifecycle.py` gain exposure records and the two figures
(decisions 85, 87; no outcome changed); the admission tests and
`tests/test_replay_candidates.py` row tests gain decision 86 (d) and 87's
keys; decision 79 (b)'s test reads the adjusted Sharpe over T with a new
cell and score (decision 86 (e)); two `tests/test_table.py` tests gain
decision 88's fields; G1.3's expected rows (U6, below).

## Speed

Decision 90 (c): seconds per replay day of the G1.3 scenario's first 30
calendar days (22 replay days), one foreground call each, on the
builder's machine.

| Unit | parent | s/day at parent | s/day at commit |
|---|---|---|---|
| U1 (decision 84) | 7629de6 | 1.341 (29.51 s) | 1.469 (32.33 s) |
| U2 (decision 85) | db467d8 | 1.474 (32.43 s) | 1.486 (32.68 s) |
| U4 (decision 88) | 8da0276 | 1.471 (32.37 s) | 1.546 (34.01 s) |

One `paper.adjusted` call over the whole paper record (21 paper days) of
approach aa1f46fb3c3ee at the end of that replay: 0.3474 s on call at the
parent of U1, 0.0118 s from the records at U1.

Gate M1 item by item, wall time:

| Item | mission 10 (23f245c) | mission 11 (6b61c6e) |
|---|---|---|
| G1.1 | 345 s | 386.80 s |
| G1.2 | 155 s | 171.45 s |
| G1.3 | 450 s | 518.41 s |
| G1.4 | 1 s | 1.07 s |
| M0 | 248 s | 246.32 s |

Every M1 item is under 10 minutes (O-3); no finding under decision 90 (c).

## Gate M1

Each item its own foreground call at tip 6b61c6e, after `./scripts/check`
was green three times at that tip (487, 489, 494 s).

`./scripts/gate M1 G1.1` — wall 386.80 s

```
G1.1 PASS 6 passed, 1 warning in 386.22s (0:06:26)
gate M1 G1.1: PASS
```

`./scripts/gate M1 G1.2` — wall 171.45 s

```
G1.2 PASS 4 passed in 170.88s (0:02:50)
gate M1 G1.2: PASS
```

`./scripts/gate M1 G1.3` — wall 518.41 s

```
G1.3 PASS 10 passed in 517.82s (0:08:37)
gate M1 G1.3: PASS
```

`./scripts/gate M1 G1.4` — wall 1.07 s

```
G1.4 PASS 15 passed in 0.51s
gate M1 G1.4: PASS
```

By O-2's rule, gate M1 passes at 6b61c6e.

## M0 still passes

`./scripts/gate M0` at 6b61c6e — wall 246.32 s

```
G0.1 PASS 62 passed in 57.24s
G0.2 PASS 7 passed in 91.52s (0:01:31)
G0.3 PASS 13 passed in 95.08s (0:01:35)
G0.4 PASS 4 passed in 0.27s
gate M0: PASS
```

## G1.3 on the adjusted measure (U6)

No line of `tests/fixtures/scenarios/g1_lifecycle.jsonl` changed in U6:
every transition occurs on the adjusted measure with the lines U3 gave
`adjusted_t`. Expected lifecycle rows that moved (trend_ma's steps 2 and
3 now read the adjusted Sharpe): dormant 2019-08-14 -> 2019-08-13
(adjusted -0.619, plain +0.163: only the adjusted measure sends it
dormant); dormant 2019-12-02 -> 2019-11-19; returned 2020-03-18 ->
2019-11-26; dormant 2020-03-19 -> 2019-11-29. The lifecycle count after
segment 2 is 10 (was 9); the 08-13 table shows trend_ma dormant. Rows of
`admitted`, `displaced`, `dormant`, `returned` carry `adjusted` and
`plain`, computed in the test from the stored bars, roll records and
journal parquet files, importing nothing from `paper`, `table`, `stats`
or `lifecycle`; trial rows carry `adjusted_t` and `adjusted_w`; the table
checks decision 88's fields.

Transitions and the day each occurs: `free_slot` 2019-06-03, 06-06,
06-07; `not_positive` 06-04; `too_few_trades` 06-05; admission
`displaced` 06-11; retirement on failure 06-13; `dormant` 07-02;
`returned` 08-12; `retired_dormant` 2020-06-10.

Seen to fail: step 2 reading the plain figure (worktree change in
`lifecycle.py`, reverted): `3 failed, 7 passed in 513.34s (0:08:33)`,
`gate M1 G1.3: FAIL`.

## Register

`tests/fixtures/return_readers.toml`, 24 entries: producer 14, display 5,
adjusted 4 (one pending), timing_gross 1 (pending), stage3_money 0.

| Function | Class | Note |
|---|---|---|
| `discotrade.backtest.score` | producer | computes a subject's gross, net_1x and net_2x rows on a window; decides nothing |
| `discotrade.cli._print_backtest` | display | prints the backtest command's plain DESIGN 8 metrics; nothing selects on them |
| `discotrade.journal._columns` | producer | builds the journal row columns gross, net_1x, net_2x for storage; decides nothing |
| `discotrade.lifecycle._sharpe_on` | display | the plain Sharpe of paper net_1x written as `plain` beside the deciding figure (decision 87); selects nothing |
| `discotrade.lifecycle._figures` | adjusted | Sharpe at 1x of paper.adjusted net_1x over the window, the figure steps 2, 3 and admission compare (O-11, O-12) |
| `discotrade.lifecycle.step_rows` | adjusted | dormancy, return and displacement on the adjusted Sharpe via _figures (decision 85, O-11, O-12) |
| `discotrade.lifecycle.admit` | adjusted | admission score adjusted_t sharpe, weakest of the cell via _figures; reads metrics_t sharpe as the plain row figure (decision 86) |
| `discotrade.metrics.daily_series` | producer | sums legs into the daily net_1x and net_2x series; decides nothing |
| `discotrade.metrics._breakeven_cost` | producer | computes breakeven_cost from summed gross over turnover; decides nothing |
| `discotrade.metrics.compute` | producer | computes the DESIGN 8 metrics from net_1x and net_2x; decides nothing |
| `discotrade.metrics.total_return` | producer | computes the sum of a daily return series; decides nothing |
| `discotrade.metrics.sharpe` | producer | computes the annualised Sharpe of a daily return series; decides nothing |
| `discotrade.metrics.max_drawdown` | producer | computes the maximum drawdown of a daily return series; decides nothing |
| `discotrade.paper.unit_bars` | producer | computes an instrument's unit-position gross per bar for the exposure records; decides nothing |
| `discotrade.paper.build` | producer | computes the subjects' paper rows (gross, net_1x, net_2x) from the journal; decides nothing |
| `discotrade.paper._series` | producer | computes one portfolio row as the mean of its members' gross, net_1x, net_2x; decides nothing |
| `discotrade.paper.portfolio` | producer | computes the portfolio and portfolio_clean series from the members' rows; decides nothing |
| `discotrade.paper.adjusted` | producer | computes the exposure-adjusted series (O-4, decision 81) that adjusted readers call; decides nothing |
| `discotrade.replay._candidate` | producer | reads a scripted candidate's metrics_t and adjusted_t into a Candidate; decides nothing |
| `discotrade.stats.rank_persistence` | timing_gross, pending S4.1 | rank persistence sums paper net_1x per block; O-5 moves it to gross timing return in S4.1 (O-10) |
| `discotrade.stats.control_moments` | adjusted, pending S4.1 | moments of the random controls' plain paper net_1x Sharpes; O-7 adjusts it in S4.1 (decision 88, O-10) |
| `discotrade.table._day_sums` | display | sums journal gross and turnover per day for the table's breakeven_cost; nothing selects on it |
| `discotrade.table._record` | display | the table's plain paper record: Sharpe at 1x and 2x and drawdown of paper net_1x, net_2x |
| `discotrade.table.build.approach_row` | adjusted, pending S4.1 | computes S, E_N, excess on plain paper net_1x (O-7 in S4.1); also the display record, admission scores, adjusted columns |

The three `pending = "S4.1"` entries are `stats.rank_persistence`,
`stats.control_moments` and `table.build.approach_row`; step S4.1 removes
them (O-5, O-7, O-10). The audit test holds that set as a literal.
Notation: nested functions are qualified `outer.inner`. Readings of
decision 89 (b) made by U5 and stated in its body: a parameter default
counts as a keyword; `lifecycle`'s import of `paper` as `paper_module`
counts as `paper.adjusted`; the call check reads a function's nested
functions too.

## Decisions 84 to 90: the tests that hold them

- **84** — `tests/test_exposure.py`: `test_nothing_is_stored_for_it_but_the_records`,
  `test_the_stored_records_equal_the_tests_own_over_a_roll_and_a_weekend`,
  `test_hbar_is_the_summed_position_over_the_summed_rows_not_a_mean_of_daily_means`,
  `test_adjusted_from_the_records_equals_the_on_call_computation`,
  `test_a_stored_unit_return_equals_the_one_computed_after_a_later_roll`,
  `test_a_rebuild_from_the_journal_and_the_bars_has_the_same_content_hash`,
  `test_the_records_are_staged_on_a_new_day_only_and_a_rerun_writes_nothing`,
  `test_after_the_next_day_the_records_are_the_tests_own`,
  `test_a_caller_passing_staged_records_and_overlay_reads_the_staged_days_rows`,
  `test_the_next_day_heals_the_records`,
  `test_paper_no_longer_calls_the_private_journal_empty`; and every
  earlier test of the file.
- **85** — `tests/test_lifecycle.py`: `test_step_2_dormant_on_a_negative_adjusted_sharpe_whose_plain_is_positive`,
  `test_step_2_stays_live_on_an_adjusted_sharpe_that_is_not_negative_whose_plain_is`,
  `test_step_2_reads_the_last_window_rows_not_the_whole_paper_record`,
  `test_one_constant_position_neither_goes_dormant_nor_returns`,
  `test_step_3_returns_on_a_positive_adjusted_sharpe_and_not_on_a_positive_plain_one`,
  `test_step_3_displaces_the_lowest_adjusted_sharpe_each_on_its_own_positions`;
  `tests/test_exposure.py::test_run_day_step_2_reads_the_staged_adjusted_series_and_writes_both_figures`.
- **86** — `tests/test_lifecycle.py`: `test_the_score_is_the_adjusted_sharpe_not_the_plain_one`,
  `test_a_positive_adjusted_score_is_admitted_whatever_the_plain_one`,
  `test_the_weakest_of_a_full_cell_is_chosen_on_its_adjusted_sharpe_over_t`,
  `test_returned_on_d_and_displaced_by_d_s_admission_both_rows_stand` (86 (f)),
  `test_rows_written_before_are_not_rewritten_after_a_new_day`;
  `tests/test_replay_candidates.py`: `test_a_line_s_adjusted_t_is_carried_and_null_means_not_a_number`
  and the refused-file cases (no `adjusted_t`, extra key, missing symbol,
  wrong kind), the trial-row tests and decision 79 (b)'s T-days test;
  `tests/test_ledger.py::test_a_trial_row_may_carry_adjusted_t_and_adjusted_w_both_never_one`.
- **87** — `tests/test_lifecycle.py`: `test_a_figure_that_is_not_a_number_is_written_null`,
  `test_retired_dormant_and_failure_rows_carry_neither_figure`, and the
  expected rows of the tests under 85 and 86; `tests/test_ledger.py`:
  `test_a_lifecycle_row_of_four_reasons_may_carry_adjusted_and_plain`,
  `test_a_lifecycle_row_of_another_reason_carries_neither_figure`.
- **88** — `tests/test_table.py`: `test_each_approach_row_holds_its_adjusted_figures_over_all_its_paper_days`,
  `test_avg_position_does_not_follow_the_dormant_window`,
  `test_adjusted_admission_score_is_null_where_the_trial_row_has_no_adjusted_t`,
  `test_table_md_labels_each_figure_column_adjusted_or_plain`,
  `test_a_rerun_of_the_mixed_replay_writes_nothing`.
- **89** — `tests/test_return_readers.py`: `test_the_audit_passes`,
  `test_the_pending_entries_are_the_three_of_decision_89`,
  `test_no_entry_is_stage3_money_yet`, `test_the_register_has_its_form`,
  `test_each_reference_shape_is_found`, `test_a_parameter_default_is_a_keyword`,
  `test_other_shapes_are_not_found`, `test_methods_and_nested_functions_are_qualified`,
  `test_an_unregistered_reader_fails`, `test_a_registered_function_that_no_longer_exists_fails`,
  `test_an_adjusted_entry_calls_paper_adjusted`,
  `test_the_local_function_must_itself_be_registered_adjusted`,
  `test_a_fourth_pending_entry_is_seen`, `test_a_register_of_bad_form_is_seen`.
- **90** — `tests/gates/test_g1_3_lifecycle.py`: `test_every_lifecycle_row_in_full_and_in_order`,
  `test_table_matches_a_hand_count` and the rest of the file; the gate
  runs above.

## What the tests prove

- On `test_mixed` 2019-06-12..16 (a roll and a weekend), the stored
  exposure records equal the test's own computation; `paper.adjusted`
  from them equals the on-call computation within 1e-12 for an approach,
  a random slot and a buy-and-hold control on two windows; a stored
  R_i(D) equals the value after a later roll; a rebuild gives the same
  content hash; a re-run writes nothing; the heal restores a removed day,
  a day removed from one file, an extra date and deleted files.
- At the production `dormant_window_days` (30), on hand-built records:
  dormancy, return and displacement follow the adjusted Sharpe where the
  plain one would decide otherwise, each subject on its own positions over
  the window; a constant position neither goes dormant nor returns. One
  run-day test (window 4 on a copied configuration, said so) sends an
  approach dormant with plain +0.374 and adjusted -9.04.
- Admission scores `adjusted_t["sharpe"]` (null refused `not_positive`);
  the weakest of a full cell is chosen on the adjusted measure over T; a
  malformed `adjusted_t` is refused before any day runs; a ledger line
  written by the parent's code is unchanged after a new day.
- The table's adjusted figures equal the test's own computation over all
  paper days on a 5-day `test_mixed` replay; deflated figures and earlier
  fields unchanged.
- The audit passes and fails on the three wrong changes of decision 89 (b).
- G1.3 shows every transition it listed on the adjusted measure, and its
  expected rows carry decisions 86 and 87's keys; gate M1 items and gate
  M0 pass at 6b61c6e.
- `git diff c3a3f1d` of `config/`, `tests/fixtures/config/` and
  `tests/fixtures/config_frozen.json` is empty; the only file under
  `tests/gates/` changed is `tests/gates/test_g1_3_lifecycle.py`;
  `config/models.toml` does not exist.

## NOT PROVEN

- Rank persistence, the control moments and the deflated figures (`S`,
  `E_N`, `excess`) still read plain returns until step S4.1 (the three
  `pending` entries).
- The audit sees only the reference shapes it scans: a figure passed on
  through a variable, under another name or in a new column, or a shape at
  module or class level, is not seen. Nine registered functions hold no
  scanned shape and are only checked to exist. The classes are the
  builder's reading of O-16 and O-18; the strictest-class rule was applied
  by hand.
- The scripted candidates' adjusted T figures come from a file, not from
  scoring, until step S3.2. In `g1_lifecycle.jsonl` the scripted adjusted
  and plain admission scores are equal (`avg_position` 0), so G1.3 alone
  does not show that admission reads the adjusted measure; the unit tests
  do. G1.3 shows it for dormancy through the 2019-08-13 row.
- The speed figures and gate times are from the builder's machine, one
  call each. G1.3 is now 518 s, nearer 10 minutes than mission 10's
  450 s; per-day cost grows with history; the cost of the exposure
  records over a year's history was not measured separately, and the
  extra per-day time was not profiled. The timed `paper.adjusted`
  approach has an adjusted sum of 0.0 (likely a flat position), so that
  timing says nothing about values.
- Incremental records and a rebuild were shown equal on one 5-6 day case;
  the heal for a process killed between the two record moves is not
  tested (rows were removed by hand).
- Most step 2/3 lifecycle unit tests use hand-built exposure records; only
  the run-day test and G1.3 compute the adjusted figures from journal and
  stored bars. The table tests use `controls.random_pool` 4 from the
  file's configuration copy, not the production 50; at the production
  window of 30 the 5-day replay cannot separate "whole record" from "last
  30 rows" for `avg_position`, which is caught only with the window at 2.
- Decision 79 (b)'s new cell (trend_ma 16/48, 24/64, 12/64) and score
  (0.2) were chosen from a probe replay on `test_synth` and hold for that
  data only.
- No number from outside the project was added in this mission.
- Carried from FINAL-REPORT-10, still open: O-5 to O-9 and O-14 not
  built; a bar file is hashed once per day run; decision 80 (a)'s identity
  shown on one 30-day replay; 80 (c) rests on code and commit bodies; the
  paper heal is on dates only; U4-of-mission-10's equivalence and T-days
  limits; scoring on T is S3.2's; the `cutoff` behind `clean` comes from a
  test or scenario until S3.2; approach sources run in-process until S2.2;
  the replay has no provider, coordinator, issue sink or sandbox; G1.1's
  bounds hold on its seeds and its net rank-persistence warning was not
  read from the output; G1.3's rows are what the fixed seeds produce; the
  socket backstop's blind spots; the table not tested under 900 days; and
  everything carried from FINAL-REPORT-8 and -9 (dormancy and the matched
  draw through `run-day` only at lowered values; step 1's writes not
  staged; retry, `run_failed`, push and catch-up are S4.2's; the weekly
  recomputation not wired; mission 7's items; the half-tick spread floor,
  the G0.1 roll probe and single fixture, D-006 deferred to S2.1, G0.2's
  and G0.3's limits, G0.4's matching, 168 unverified cost values, D-003).
  Taken by this mission and no longer open: the adjusted series read by no
  rule (now read by the lifecycle and the table), nothing stored for it
  (decision 84), and decision 68 (b) with the day's admission displacing
  (86 (f)).

## Findings filed and answered

- **D-010** (filed U2, 489e749; note appended U3, 5962663): decision 87's
  and 86 (d)'s keys need `ledger.py`, which no unit's file list named; U2
  added `FIGURES`/`FIGURE_REASONS`, U3 `TRIAL_FIGURES` (both keys or
  neither, `KEYS` unchanged) and changed `cli.py` so `replay` loads the
  track before reading `--candidates`. Status: open, for the architect.
- **HF-008** (filed U0, 7629de6): concurrent per-commit reviewers push
  `./scripts/check` near the 20-minute cap (REVIEW-10 note 7, decision
  90 (d)). Status: open, for the hands Project.
- No finding under decision 90 (a) or (c): every transition held and
  every item ran under 10 minutes.
- None answered in this mission.

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-10 note 3 (store the derived records; `journal._empty`; `overlay`) | U1, decision 84 | 93c2f91 |
| REVIEW-9 note on decision 68 (b) (day's admission displacing) | U3, decision 86 (f): `test_returned_on_d_and_displaced_by_d_s_admission_both_rows_stand` | 5962663 |
| REVIEW-10 note 7 (hands: concurrent reviewers near the cap) | U0, decision 90 (d): HF-008 | 7629de6 |
| O-11 (lifecycle on the adjusted measure) | U2 decision 85, U3 decision 86 | 489e749, 5962663 |
| O-12 (each subject on its own average positions) | U2 decision 85, U3 decision 86 (c) | 489e749, 5962663 |
| O-13 (both measures recorded) | U2/U3 decision 87, U3 decision 86 (d), U4 decision 88 | 489e749, 5962663, 3ff738a |
| O-15 (G1.3 on the adjusted measure) | U6, decision 90 (a) | 6b61c6e |
| O-16 (the rule for return readers) | U5, decision 89 | 95650a4 |
| O-18 (the register and its audit) | U5, decision 89 | 95650a4 |

VERDICT: mission 11 finished
