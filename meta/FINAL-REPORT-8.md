VERDICT: mission 8 finished

# FINAL REPORT — mission 8 (roadmap step S1.2)

Builder prompt: `meta/BUILDER-8-PROMPT.md`. Base fb1e244. This mission
builds roadmap step S1.2 as decision 65 cuts it: the buy-and-hold and
random controls of §10.1, journaled every day beside the approaches with
their pool records; the three ledgers of §10.2; the lifecycle of §10.3
(steps 1 to 4 in `run-day`, admission as a function); the `clean` flag of
the paper records (§9.3, §11.3); the statistics of §11 as functions (rank
persistence, deflated scores, tightening); and it closes REVIEW-7's two
should-fix items (decision 58). It binds
`meta/decisions/decisions-2026-10-12.md` (cited below as "decision N";
items 58 to 65 are new). It does not close a milestone and adds no test
under `tests/gates/`.

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan, checkpoint, journal | b06c4b2 | plan: mission 8 plan, checkpoint and journal (S1.2) |
| U1 REVIEW-7 should-fix 1 and 2 | 060b5e2 | tests: guard sendmsg and the name lookups; recompute reads no stored position |
| U2 statistics of §11, `clean` flag | abba5d3 | stats: rank persistence, deflated scores, tightening; paper clean flag |
| U3 ledgers and lifecycle | 327c68a | lifecycle: the three ledgers, steps 1 to 4 in run-day, and admission |
| U4 controls | 451471e | controls: buy-and-hold and random pool journaled every day, monthly draws |
| U5 final report | this commit | report: mission 8 final report |

The `meta:` commits between units (db1ccf9, f8e1c40, 7b88e0b, 3d620f2)
are checkpoint, plan and journal bookkeeping. Each unit commit's body
lists its files, the choices made where DESIGN and the decisions are
silent, and the wrong changes made and reverted; those bodies are the
authority for this summary.

Files per unit:
- U0: `meta/plan.md`, `meta/CHECKPOINT.md`, `meta/journal.md`.
- U1: `tests/conftest.py`, `tests/test_offline.py`,
  `tests/test_journal_recompute.py`. No file under `src/`.
- U2: `src/discotrade/stats.py` (new), `src/discotrade/paper.py`,
  `tests/test_stats.py` (new), `tests/test_paper.py` (clean tests added;
  the three existing `paper.build` calls pass the new cutoffs argument; the
  exact-column assertions compare with `paper.COLUMNS`, which gains `clean`
  as decision 61 requires).
- U3: `src/discotrade/ledger.py` (new), `src/discotrade/lifecycle.py`
  (new), `src/discotrade/state.py` (trial writer),
  `src/discotrade/journal.py`, `src/discotrade/daily.py`,
  `tests/test_ledger.py` (new), `tests/test_lifecycle.py` (new),
  `tests/test_daily.py` (additions; the admit helper gains a `where`
  argument, default unchanged),
  `tests/fixtures/strategies/breaks_thursday_noon.py` (new fixture).
- U4: `src/discotrade/controls.py` (new), `src/discotrade/backtest.py`
  (`evaluate` split into `read_window`, targets and `score`, the one
  implementation of §7 the controls share), `src/discotrade/executor.py`
  (per-bar cost components and decision-bar lookup cached within one call,
  same values), `src/discotrade/journal.py`, `src/discotrade/paper.py`
  (a `control_bh` subject's N is 1), `src/discotrade/daily.py` (docstring
  only), `src/discotrade/cli.py` (one line; see Deviations),
  `tests/test_controls.py` (new), and per decision 64 `tests/test_daily.py`,
  `tests/test_journal.py`, `tests/test_journal_recompute.py` (each changed
  assertion named in the U4 body: approach-only filters on subject counts
  and module-equality checks; the empty-day test now has control rows only;
  recompute expected pairs are the stored journal's, controls included;
  `test_fewer_pairs_than_the_sample...` uses `recompute_sample = 1000` on a
  copy under tmp).

Tests: `./scripts/check` went from 1037 passed (FINAL-REPORT-7's tip) to
1141 passed, 86 deselected, at 3d620f2. New files: `test_stats.py`,
`test_ledger.py`, `test_lifecycle.py`, `test_controls.py` (79 collected
together); additions to `test_offline.py`, `test_journal_recompute.py`,
`test_paper.py`, `test_daily.py`.

Assertions of existing tests that changed: those decision 61 (paper
columns, through `paper.COLUMNS`) and decision 64 (journals hold controls)
change, named in the U2 and U4 bodies. No other existing test changed what
it asserts.

## M0 still passes

`./scripts/gate M0` at 3d620f2 (`3d620f26107b5712202a21e591fd4eaa434c8557`),
the pushed tip after U4, run once in the foreground with a 20-minute Bash
timeout (the tool's maximum; HF-006), tree clean and equal to
`origin/main`; pasted verbatim. Before it, `./scripts/check` printed
`check: green` three times at 3d620f2, each run its own foreground call
(runs 2 and 3: 1141 passed, 86 deselected; run 1's pass count was cut off
by the output tail, its result line `check: green`; wall times 431 s,
438 s, 438 s). This commit touches only `meta/`.

```
G0.1 PASS 62 passed in 60.17s (0:01:00)
G0.2 PASS 7 passed in 111.93s (0:01:51)
G0.3 PASS 13 passed in 168.00s (0:02:47)
G0.4 PASS 4 passed in 0.26s
gate M0: PASS
```

Exit status 0; wall time 342 s.

## Acceptance checks (at 3d620f2)

- `git diff fb1e244 -- config/ tests/fixtures/config/ tests/fixtures/config_frozen.json`
  is empty; `config/models.toml` does not exist; `git diff fb1e244 --
  tests/gates/` is empty.
- The one new fixture file is `tests/fixtures/strategies/breaks_thursday_noon.py`
  (U3).
- I-9: G0.4's `test_no_file_under_src_names_a_symbol_root_or_venue`
  passes in the gate run above.

## Decisions 58 to 64: the tests that hold them

- **58 (a) (backstop: `sendmsg` with an address, the four lookups)** —
  `tests/test_offline.py`:
  `test_sendmsg_with_an_address_and_the_lookups_fail_in_a_test`,
  `test_sendmsg_with_an_address_and_the_lookups_fail_in_a_module_scoped_fixture`,
  `test_sendmsg_with_an_address_and_the_lookups_fail_in_a_session_scoped_fixture`,
  `test_a_lookup_is_refused_before_the_real_function_runs` (x10:
  `getaddrinfo`, `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr`,
  `getnameinfo`, each through `socket` and `_socket`),
  `test_sendmsg_without_an_address_on_an_unconnected_socket_is_the_os_error`,
  `test_unix_domain_sendmsg_with_an_address_stays_open`,
  `test__socket_unix_domain_stays_open`,
  `test_a_test_marked_network_is_left_alone`.
- **58 (b) (recompute reads no stored position)** —
  `tests/test_journal_recompute.py`:
  `test_a_changed_stored_target_next_chained_into_the_next_day_reports_both_days`.
- **59 (rank persistence)** — `tests/test_stats.py`:
  `test_production_values`, `test_block_dates_count_block_days_from_the_epoch`,
  `test_trading_dates_are_the_union_of_the_subjects_own_calendars`,
  `test_the_population_leaves_out_a_subject_missing_one_trading_day`,
  `test_rank_persistence_refuses_block_zero`,
  `test_spearman_is_pearson_of_average_ranks`,
  `test_spearman_function_against_hand_values`,
  `test_statistic_is_missing_below_the_minimum_population`,
  `test_statistic_is_missing_when_a_rank_series_has_zero_deviation`.
- **60 (deflated scores, tightening)** — `tests/test_stats.py`:
  `test_the_published_quantiles`,
  `test_expected_maximum_against_hand_values` (N = 0, 1, 2, 3, 10, 1000,
  250000), `test_n_below_two_is_floored_at_two`,
  `test_a_sharpe_or_moments_not_a_number_give_values_not_a_number`,
  `test_tightened_percentile_at_the_production_thresholds` (N = 0, 1, 10,
  1000), `test_threshold_against_hand_values` (N = 0, 1, 10, 1000),
  `test_control_moments_over_slots_with_a_row_on_each_day`,
  `test_fewer_than_two_slots_give_moments_not_a_number`.
- **61 (`clean` flag)** — `tests/test_paper.py`:
  `test_an_approach_is_clean_only_on_days_after_its_cutoff`,
  `test_a_control_row_is_always_clean`,
  `test_an_approach_without_a_cutoff_is_refused`,
  `test_the_clean_column_follows_each_approachs_recorded_cutoff`,
  `test_the_stored_paper_records_rebuild_from_the_journal_to_the_same_hash`;
  `tests/test_stats.py`: `test_clean_and_exposed_counts`;
  `tests/test_controls.py`: `test_the_paper_records_hold_the_controls_clean`.
- **62 (the three ledgers)** — `tests/test_ledger.py`:
  `test_each_row_is_one_sorted_key_json_object_per_line`,
  `test_earlier_lines_stay_byte_identical_and_a_present_line_is_not_appended`,
  `test_an_append_is_atomic`, `test_a_torn_last_line_is_refused`,
  `test_into_a_staging_directory_writes_only_there`,
  `test_a_row_must_hold_exactly_its_ledgers_keys`,
  `test_the_keys_of_each_ledger`,
  `test_the_call_writer_takes_the_outcomes_of_10_2`,
  `test_a_float_that_is_not_finite_is_written_as_null_and_dates_as_iso`;
  `tests/test_lifecycle.py`:
  `test_a_trial_row_keeps_the_grid_and_w_metrics_it_carries`,
  `test_a_score_that_is_not_positive_is_refused_and_written_under_trials`
  (x3); `tests/test_daily.py`:
  `test_a_day_failing_in_step_2_leaves_every_ledger_untouched`.
- **63 (lifecycle)** — `tests/test_lifecycle.py`:
  `test_the_production_values`,
  `test_the_state_is_the_last_rows_to_and_live_without_a_row`,
  `test_step_1_retires_a_failure_with_its_error_text`,
  `test_step_2_dormancy_at_dormant_window_days_and_not_before`,
  `test_step_2_uses_the_last_window_only_and_not_a_positive_sharpe`,
  `test_step_2_a_sharpe_that_is_not_a_number_is_not_negative`,
  `test_step_3_returns_into_a_free_slot_not_before_revival_min_dormant_days`,
  `test_step_3_a_dormant_approach_with_no_positive_sharpe_stays`,
  `test_step_3_returns_by_displacing_the_weakest`,
  `test_step_3_stays_dormant_when_not_above_the_weakest`,
  `test_step_3_sees_the_slot_step_2_freed`,
  `test_step_4_retires_after_retire_dormant_days_calendar_days`,
  `test_the_weakest_is_the_lowest_sharpe_not_a_number_lowest_ties_to_the_lowest_id`,
  `test_run_steps_again_for_the_same_day_appends_nothing`,
  `test_admission_into_a_free_slot_writes_the_trial_the_approach_and_one_row`,
  `test_a_score_that_is_not_positive_is_refused_and_written_under_trials`
  (0.0, -0.4, nan), `test_too_few_trades_at_min_trades_t_is_refused`,
  `test_admission_displacing_the_weakest_makes_it_dormant`,
  `test_admission_refused_when_not_better_than_the_weakest`,
  `test_admission_displaces_a_sharpe_that_is_not_a_number_and_ties_to_the_lowest_id`,
  `test_admission_counts_the_states_after_the_days_steps`;
  `tests/test_daily.py`: `test_the_breaking_fixture_breaks_only_on_next`,
  `test_a_contract_failure_retires_the_approach_and_the_day_goes_on`,
  `test_a_day_failing_in_step_2_leaves_every_ledger_untouched`,
  `test_an_approach_admitted_on_d_is_first_journaled_on_the_next_trading_day`,
  `test_an_approach_made_dormant_on_d_is_journaled_on_d_plus_1`.
- **64 (controls)** — `tests/test_controls.py`:
  `test_seeds_and_production_values`,
  `test_the_per_bar_number_is_decision_64s_hash`,
  `test_measured_pairs_at_the_production_values`,
  `test_every_day_journals_bh_and_rc_on_every_instrument` (roll, month),
  `test_buy_and_hold_targets_1_starts_flat_and_pays_the_roll`,
  `test_a_draw_on_the_first_day_and_the_first_trading_day_of_each_later_month`,
  `test_the_fallback_draw_is_log_uniform_on_the_horizons`,
  `test_the_matched_draw_takes_the_live_approaches_measured_pairs`,
  `test_every_slots_targets_are_decision_64s_state_machine`,
  `test_the_position_carries_across_a_redraw`,
  `test_the_controls_rows_are_the_modules_evaluation_of_their_targets`,
  `test_the_paper_records_hold_the_controls_clean`,
  `test_recompute_all_matches_every_control_pair_and_reports_a_changed_row`,
  `test_a_rerun_of_a_finished_day_writes_nothing`,
  `test_two_fresh_state_directories_give_equal_journal_paper_and_pools`;
  `tests/test_journal.py`:
  `test_a_day_with_no_subject_writes_an_empty_file_and_its_index_line`
  (control rows only, as decision 64 changes it).

## What the tests prove

Taken from each unit's commit body; on the cases named there. Journal,
paper, lifecycle and control tests through `run-day` run on `test_mixed`
(seeds asserted in each file).

- U1: in a test, a module-scoped and a session-scoped fixture, `sendmsg`
  with an address on an `AF_INET` datagram socket made through `socket`
  and through `_socket`, and each of `gethostbyname`, `gethostbyname_ex`,
  `gethostbyaddr`, `getnameinfo` through both modules, raise
  `SocketBlocked`, and a non-blocking loopback receiver gets no datagram;
  for `getaddrinfo` and the four lookups through both modules, the
  backstop reinstalled around a spy raises without calling the spy; an
  `AF_UNIX` datagram `sendmsg` with an address works through both
  modules; in a scratch pytest session a `network`-marked test sends with
  `sendmsg` and runs the four lookups, and the following unmarked test
  finds them refused again (every base assertion kept). On a 5-day
  journal, the stored `target_next` of the last SYNA row of 2019-06-10
  (D1) of one approach changed 1.0 to 0.0 and that approach's 2019-06-11
  (D2) rows and index line replaced by `day_rows` computed from the
  changed D1: `journal recompute --all` exits 1, prints `MISMATCH` for
  exactly (D1, s) and (D2, s), appends two `journal_mismatch` events, and
  leaves the journal files unchanged. Seen to fail: `sendmsg` left
  unguarded; `gethostbyname` left unguarded; recompute starting each day
  from the stored previous `target_next`.
- U2: block dates from `test_mixed`'s epoch and `block_days`; a subject
  missing one trading day of either block left out, a buy-and-hold
  subject on `synth_week` judged on its weekdays; Spearman against
  test-computed average ranks and Pearson; the statistic null below
  `rank_min_population` (5) and on a zero-deviation rank series; `E(N)`
  and the excess for N = 0, 1, 2, 3, 10, 1000, 250000 and the threshold
  for N = 0, 1, 10, 1000 against a quantile bisected on `erf`/`erfc` in
  the test; the published `z(0.95)`, `z(0.975)`, `z(0.99)` to 1e-12;
  NaN-Sharpe and missing-day slots left out of `mu_c`, `sd_c` (ddof 1);
  fewer than two slots give NaN; `p(N)` at N = 0, 1, 10, 1000 equals 0.95,
  0.95, 0.95, 0.9995 at the production thresholds; an approach clean only
  after its cutoff, exposed on and before it; control-kind rows (built by
  the test) always clean; clean and exposed counts; the stored paper
  records rebuild from the journal to the same hash. Seen to fail: ties
  ranked by position; `sd_c` with ddof 0; N not floored at 2; clean on or
  after the cutoff.
- U3: decision 62's append rules and the trial row's keys, `null` grid
  and W metrics for a candidate without them; admission `free_slot`,
  `displaced` (weakest dormant, reason `displaced`), `not_positive` (0,
  negative, NaN), `too_few_trades` at 29 and admitted at 30,
  `not_better_than_weakest`, each one trial row and, when admitted, the
  approach and its lifecycle row; a refused trial under `trials/<id>/`;
  dormancy at 30 rows not 29, not for a NaN Sharpe; return into a free
  slot and by displacement, not at 4 trading days, at 5; retirement at 365
  calendar days, not 364; the weakest by lowest Sharpe, NaN lowest, ties
  to the lowest id. Through `run-day` on `test_mixed`: the fixture
  breaking on 2019-06-13 retired with `failure: ...`, its rows of that day
  absent, the others journaled, the day committed, not journaled on
  06-14; a re-run appends no ledger line; an approach admitted on D first
  journaled, flat, on D+1; one made dormant on D journaled on D and D+1,
  live on D and dormant from D+1 (with `dormant_window_days` 2 on a copy
  under tmp); a day failing in step 2 leaves both ledgers byte-identical.
  Seen to fail: NaN Sharpe treated as negative in step 2; a change taking
  effect on D; the lifecycle row appended again on a re-run; a contract
  failure failing the whole day.
- U4: through `run-day` on `init-state` states (as-of 2019-07-03), each
  day journals `bh:<symbol>` (`control_bh`, its instrument only) and
  `rc:0` to `rc:49` (`control_random`) on every instrument with bars that
  day, on 06-13/06-14 and 06-28 to 07-01; `bh` targets 1, first row flat,
  SYNA roll on 06-14 pays `roll_cost` with previous position 1; draws on
  06-13 (one state) and on 06-28 and 07-01 (another), seeds 201906 and
  201907, none on 06-29/06-30; the fallback `H`/`q` equal the test's
  `default_rng(201906)` values and lie in [1, 48]; with
  `match_window_days` 2 on a copy under tmp (production 30), the 07-01
  draw's pairs equal those the test computes from the three approaches'
  journal rows of 06-29/06-30, each slot's `H`/`q` the pair the test's
  `default_rng(201907).integers` chooses; the matched-pair rule at
  production values (30, 3) on test-built frames; every slot's targets on
  every instrument over 06-28 to 07-01 equal the test's own hash and state
  machine, SYNL never short; the position carries across the 07-01
  redraw; every control's journal rows equal, field for field under
  decision 39's rule, `backtest.score` of the test's targets over the span
  from the first day; paper holds every control with `clean` true;
  `journal recompute --all` prints every control pair equal and
  `MISMATCH` for one changed `rc:7` row only; re-running 07-01, 06-28,
  06-30 leaves every file including `.git` unchanged; two fresh states
  give equal journal index, paper hash and `pools.jsonl` bytes. Seen to
  fail: per-bar number keyed by the bar's day, not its `ts`; state machine
  not restarted flat at a redraw; the July redraw reusing June's seed; a
  short entry on SYNL.
- The gate run at 3d620f2: `./scripts/check` green three times;
  `./scripts/gate M0` prints `G0.1` to `G0.4 PASS` and `gate M0: PASS`,
  exit 0, in 342 s.

## Deviations

- U4 changed `src/discotrade/cli.py` (one line: `journal recompute` passes
  the setup to `journal_pairs` so control pairs are recomputed), outside
  the brief's file list for U4. Named in the U4 body.
- U4's three chained `./scripts/check` runs went past 20 minutes and were
  moved to the background by the harness (the HF-006 situation); all
  three finished green before the commit. In U5 each of the three runs was
  its own foreground call and none exceeded 20 minutes.
- The gate in U5 ran with a 20-minute Bash timeout, the tool's maximum,
  not the 30 minutes the brief asks for; it finished in 342 s.

## NOT PROVEN

New in this mission:
- The controls and the lifecycle have not run over a long replay; that is
  step S1.3's.
- Rank persistence is not yet written in the day loop
  (`stats/<track>/rank_persistence.jsonl`), and the table and the combined
  portfolio do not exist, until step S1.3.
- Admission is driven only by candidates whose T metrics a test supplies;
  scoring a candidate on T is step S3.2's.
- The `cutoff` behind the `clean` flag is written by a test until step
  S3.2 builds the model pool (`config/models.toml`, R-14).
- Approach sources still run in-process (repository files only, decision
  48) until step S2.2 moves them behind the sandbox.
- What the socket backstop still cannot see: `socket.SocketType` used
  directly; a binding taken (for example `from _socket import socket`)
  before the session starts; child processes (the listing test only
  classifies the files that launch them); a module- or session-scoped
  fixture first set up by a `network`-marked test runs unblocked. The
  lookups are tested only on numeric loopback addresses, and the refusal
  "before the lookup leaves the process" is shown by a stand-in (spy) that
  is never called, not by observing the resolver.
- U3: dormancy through `run-day` is shown only at a lowered window of 2
  (`dormant_window_days` on a copy under tmp); the production value 30 is
  shown in `test_lifecycle.py` on lifecycle functions only.
- U4: the matched draw through `run-day` is shown only at
  `match_window_days` 2 (copy under tmp); production values (30, 3) only on
  test-built frames. No test of the horizons fallback when the matched
  approaches all have NaN holding bars. No re-run of a state journaled
  before controls existed. No first journaled day on the 1st of a month or
  across a year end.
- Run-time cost: `run-day` adds about 1 s for 153 control subjects on
  `test_mixed`; the suite went from about 5 to about 7 minutes
  (431 to 438 s per `./scripts/check` run in U5); the cost over a long
  replay is unmeasured.

Carried from FINAL-REPORT-7, updated:
- The subjects-are-approaches-only item and the `clean` flag item are
  taken by this mission (decisions 61, 64), within the items above.
- Step 1's writes are not staged: after a failed day the bar index, rolls,
  `gaps.jsonl` and the health log stay changed and uncommitted until the
  next good day. Retry, `run_failed`, the push to a remote and catch-up of
  missed days are step S4.2's (decision 50).
- The weekly recomputation (step 6 of §16.1) is not wired into the day;
  `journal recompute` runs only when called (decision 54).
- `run-day` is proven on synthetic sources only (`test_mixed`); no test
  runs it on `test_synth`, a real adapter or the hourly track.
- U2 of mission 7: a directory left by an interrupted `init-state` is
  refused, not repaired; the lock is tested within one process only; no
  fsync or crash behaviour is tested.
- U3 of mission 7: a day file whose bytes changed while its index line did
  not is reported unchanged on a re-run; the carry guard is tested only by
  the skipped-day case; day-by-day equality with the module evaluation is
  shown only on `test_mixed` over short spans (now including controls, U4).
- U4 of mission 7: no estimated-roll-gap notice arises on `test_mixed`;
  `revised_data` is detected by matching the bar store's error text.
- U5 of mission 7: recompute is not tested beyond a few days, nor on
  `test_synth`; it now covers controls (U4) and a chained stored value
  (U1, decision 58 (b)), which closes REVIEW-7 should-fix 2's gap.
- The half-tick spread floor, the G0.1 roll probe, the calculation's
  independence, G0.1's single fixture and window, `test_gate_script.py`'s
  stability under load, D-006 (deferred to S2.1, decision 44), G0.2's and
  G0.3's limits, G0.4's matching, every cost value being unverified
  (`config check` lists 168 unverified values) and D-003, the
  `meta/BACKLOG.md` item on an unlisted month file, and what remains of
  missions 3 and 4's NOT PROVEN: unchanged, as FINAL-REPORT-7 lists them.

## Findings filed and answered

None. `git diff fb1e244 -- meta/findings/FINDINGS.md` is empty: no finding
was filed and none was answered in this mission. HF-006 and HF-007 stay
open; D-003 stays; D-006 stays deferred to S2.1.

## Review items

| Item | Review | Resolution | Sha |
|---|---|---|---|
| REVIEW-7 should-fix 1 | FINAL-REPORT-7's NOT PROVEN left out `sendmsg` to an address and `gethostbyname`/`gethostbyname_ex`, which the backstop did not guard | U1, decision 58 (a): `sendmsg` with an address on a non-`AF_UNIX` socket and `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr`, `getnameinfo` refused in every scope through `socket` and `_socket`; what remains unseen is listed under NOT PROVEN | 060b5e2 |
| REVIEW-7 should-fix 2 | No test separated decision 54's whole-span recompute from one chained through stored `position`/`target_next` | U1, decision 58 (b): `test_a_changed_stored_target_next_chained_into_the_next_day_reports_both_days`; the chained recompute was made, seen red, reverted | 060b5e2 |

VERDICT: mission 8 finished
