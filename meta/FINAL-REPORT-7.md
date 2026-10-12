VERDICT: mission 7 finished

# FINAL REPORT — mission 7 (roadmap step S1.1)

Builder prompt: `meta/BUILDER-7-PROMPT.md`. Base c73a695. This mission
builds roadmap step S1.1: the state directory with `discotrade
init-state`, the health log, the approaches' frozen records, the decision
journal, the paper records, `discotrade run-day` (daily steps 1 and 2 on a
synthetic source) with its lock, staging and state commit, and `discotrade
journal recompute`; and it makes the socket backstop hold outside
function-scoped tests (the REVIEW-3 note). It binds
`meta/decisions/decisions-2026-10-12.md` (cited below as "decision N";
items 47 to 57 are new). It does not close a milestone and adds no test
under `tests/gates/`.

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan, checkpoint, journal, HF-007 filed | 057f9d2 | plan: mission 7 plan, checkpoint, HF-007 |
| U1 socket backstop from session start | de2a5b2 | tests: socket backstop holds from session start, in every fixture scope and through _socket |
| U2 state directory, lock, state commit, health log | c8342c4 | state: the state directory, the lock, the state commit and the health log |
| U3 approaches and the decision journal | e44866d | journal: approaches in the state and the decision journal, one day file at a time |
| U4 `run-day` and the paper records | 1fbf800 | daily: run-day steps 1 and 2 with the paper records, one commit per day |
| U5 `journal recompute` | 073a5bd | journal: journal recompute, every pair with --all or a sample seeded with D |
| U6 final report | this commit | report: mission 7 final report |

The `meta:` commits between units (5b0e258, 55ec913, a6e782a, 40131a4,
6aea7c0) are checkpoint, plan and journal bookkeeping. Each unit commit's
body lists its files, the choices made where DESIGN and the decisions are
silent, and the wrong changes made and reverted; those bodies are the
authority for this summary.

Files per unit:
- U0: `meta/plan.md`, `meta/CHECKPOINT.md`, `meta/journal.md`,
  `meta/findings/FINDINGS.md` (HF-007).
- U1: `tests/conftest.py`, `tests/test_offline.py` (new).
- U2: `src/discotrade/state.py`, `src/discotrade/cli.py` (`init-state`),
  `tests/test_state.py` (new), `tests/test_cli.py` (additions only), and
  `tests/test_offline.py` (`SUBPROCESS_FILES` += `state.py`,
  `test_state.py`; its exact-list assertion now compares both sides
  sorted, asserting the same thing).
- U3: `src/discotrade/state.py` (approach writer), `src/discotrade/journal.py`
  (new), `src/discotrade/backtest.py` (`evaluate` gains `start=`, default
  `None` keeps every existing test unchanged), `tests/test_journal.py`
  (new). Its commit body says "18 tests"; there are 17 (15 test functions,
  one of them parametrized over the three reference strategies).
- U4: `src/discotrade/daily.py` (new), `src/discotrade/paper.py` (new),
  `src/discotrade/cli.py` (`run-day` with `--day`; the `bars fetch` and
  `bars gaps` default day now computed by `daily.closed_day`, the same
  decision-19 computation moved, no existing test changed),
  `tests/test_daily.py` (new), `tests/test_paper.py` (new),
  `tests/test_offline.py` (`SUBPROCESS_FILES` += `test_daily.py`).
- U5: `src/discotrade/journal.py`, `src/discotrade/cli.py` (`journal
  recompute` with `--all`), `tests/test_journal_recompute.py` (new).

Tests added: 95 (collected): `test_offline.py` 9, `test_state.py` 31,
`test_journal.py` 17, `test_daily.py` 20, `test_paper.py` 7,
`test_journal_recompute.py` 8, `test_cli.py` 3. `./scripts/check` at
6aea7c0: 1037 passed, 86 deselected.

Assertions of existing tests that changed: only `tests/test_offline.py`'s
exact-list assertion, a file new in this mission (U2, sorted both sides).
No test that existed at c73a695 changed what it asserts.

## M0 still passes

`./scripts/gate M0` at 6aea7c0 (`6aea7c088f907c3cdf59a2595eee1e3106e44879`),
the pushed tip after U5, run once in the foreground with a 40-minute
timeout, tree clean and equal to `origin/main`; pasted verbatim. Before
it, `./scripts/check` printed `check: green` three times in a row at
6aea7c0 (orchestrator runs: 1037 passed, 86 deselected; 282.5 s, 290.8 s,
280.9 s). This commit touches only `meta/`.

```
G0.1 PASS 62 passed in 63.16s (0:01:03)
G0.2 PASS 7 passed in 116.42s (0:01:56)
G0.3 PASS 13 passed in 167.57s (0:02:47)
G0.4 PASS 4 passed in 0.25s
gate M0: PASS
```

Exit status 0; wall time 349 s.

## Acceptance checks (at 6aea7c0)

- `git diff c73a695 -- config/ tests/fixtures/config/ tests/fixtures/config_frozen.json`
  is empty: no frozen value, no existing fixture record and no entry of
  `config_frozen.json` changed. No new fixture file was added.
- I-9: `tests/test_instrument_agnostic.py` (`test_config_names_markets`,
  `test_no_market_named_under_src`, `test_scan_finds_a_planted_name`)
  passes (3 passed), and G0.4's
  `test_no_file_under_src_names_a_symbol_root_or_venue` passes in the gate
  run above; both scan `src/` for names collected from `config/`.
- `uv run discotrade init-state --help`, `run-day --help` and `journal
  recompute --help` each exit 0 and each lists `--state`, `--track`,
  `--config` and `--as-of`.

## Decisions 47 to 55: the tests that hold them

- **47 (socket backstop, subprocess listing)** — `tests/test_offline.py`:
  `test_a_module_scoped_fixture_cannot_open_a_socket`,
  `test_a_session_scoped_fixture_cannot_open_a_socket`,
  `test_the_error_names_the_test_that_set_up_the_fixture`,
  `test__socket_used_directly_cannot_open_a_connection`,
  `test__socket_unix_domain_stays_open`,
  `test_a_test_marked_network_is_left_alone`,
  `test_every_file_that_launches_a_subprocess_is_listed`,
  `test_a_new_subprocess_call_fails_the_listing_naming_the_file` (x2);
  `tests/test_state.py`: `test_git_runs_with_only_the_file_protocol`.
- **48 (approaches; in-process only for repository files)** —
  `tests/test_journal.py`: `test_approach_id_is_decision_48s`,
  `test_meta_json_holds_every_field_of_9_1`,
  `test_writing_an_approach_again_changes_nothing_and_a_different_one_is_refused`,
  `test_a_source_that_is_not_a_repository_file_fails_the_day_naming_the_approach`,
  `test_a_test_fixture_source_is_accepted`,
  `test_an_approach_is_journaled_only_after_its_admission_date`;
  `tests/test_daily.py`:
  `test_a_day_failing_in_step_2_moves_nothing_commits_nothing_and_releases_the_lock`.
- **49 (journal row, continuous record)** — `tests/test_journal.py`:
  `test_seeds_are_the_fixture_records`, `test_the_span_holds_the_syna_roll`,
  `test_a_days_rows_have_decision_49s_columns_first_row_and_carry`,
  `test_a_day_file_is_written_once_with_its_index_line`,
  `test_a_day_with_no_subject_writes_an_empty_file_and_its_index_line`,
  `test_journal_equals_the_module_evaluation_over_the_span`
  (`trend_ma.py`, `zscore_reversal.py`, `hour_of_day.py`).
- **50 (state directory, lock, staging, state commit)** —
  `tests/test_state.py`: `test_init_state_creates_a_committed_git_repository`,
  `test_gitignore_ignores_bar_parquet_staging_and_lock` (parametrized),
  `test_init_state_into_an_existing_empty_directory`,
  `test_a_second_init_state_changes_nothing_and_exits_0`,
  `test_a_non_empty_directory_that_is_not_a_state_directory_exits_1` (x3),
  `test_a_path_that_is_a_file_exits_1`,
  `test_init_state_inside_a_code_repository_exits_2`,
  `test_init_state_without_a_state_directory_exits_2`,
  `test_require_state_directory_refuses_one_init_state_did_not_make`,
  `test_a_second_lock_while_one_is_held_fails_naming_it`,
  `test_the_lock_is_released_after_a_failure_inside_it`,
  `test_a_state_commit_has_the_message_author_and_dates_of_the_clock`,
  `test_a_state_commit_ignores_bar_parquet_staging_and_lock`,
  `test_a_commit_with_nothing_changed_is_not_made`,
  `test_git_runs_with_only_the_file_protocol`; `tests/test_daily.py`:
  `test_each_day_has_its_journal_file_index_line_paper_records_and_one_commit`,
  `test_step_1_fetches_bars_to_the_end_of_d_runs_the_gap_check_and_updates_rolls`,
  `test_the_journal_equals_that_of_bars_fetched_at_once`,
  `test_a_day_failing_in_step_2_moves_nothing_commits_nothing_and_releases_the_lock`,
  `test_a_held_lock_exits_1_naming_it`,
  `test_a_directory_init_state_did_not_make_is_refused` (x3);
  `tests/test_cli.py`: `test_init_state_help_exits_0`,
  `test_init_state_help_from_the_console_script`,
  `test_init_state_is_listed_in_help`.
- **51 (which day; skipped day; re-run)** — `tests/test_daily.py`:
  `test_the_default_day_is_decision_19s_d_at_as_of`,
  `test_a_day_not_closed_at_as_of_is_refused`,
  `test_running_a_finished_day_again_writes_nothing_and_makes_no_commit`,
  `test_a_skipped_trading_day_exits_1_naming_it_and_writes_nothing`,
  `test_a_rerun_with_unequal_rows_raises_journal_mismatch_and_moves_nothing`;
  `tests/test_journal.py`: `test_a_rerun_with_equal_rows_writes_nothing`,
  `test_a_rerun_with_unequal_rows_leaves_the_file_and_returns_journal_mismatch`,
  `test_a_skipped_day_fails_the_next_and_writes_nothing`.
- **52 (health log)** — `tests/test_state.py`:
  `test_the_health_log_appends_one_to_json_line_per_event`,
  `test_the_health_log_keeps_every_earlier_line_byte_identical`,
  `test_a_failed_health_append_leaves_the_log_unchanged`,
  `test_the_health_log_does_not_append_a_line_already_present`,
  `test_no_events_write_no_file`,
  `test_a_health_log_with_a_torn_last_line_is_refused`;
  `tests/test_daily.py`: `test_no_data_gaps_at_the_repository_limit`,
  `test_data_gaps_is_appended_when_a_window_is_above_the_limit`,
  `test_the_notices_of_step_1_are_appended_once`,
  `test_a_revised_data_point_fails_the_day_with_revised_data`,
  `test_a_rerun_with_unequal_rows_raises_journal_mismatch_and_moves_nothing`.
- **53 (paper records)** — `tests/test_paper.py`:
  `test_build_is_decision_23s_daily_mean_and_counts_trades_above_the_floor`,
  `test_build_of_no_rows_is_an_empty_table_with_the_columns`,
  `test_build_does_not_depend_on_the_row_order`,
  `test_seeds_are_the_fixture_records`,
  `test_the_stored_paper_records_rebuild_from_the_journal_to_the_same_hash`,
  `test_one_row_per_subject_and_day_from_its_first_journaled_day`,
  `test_paper_is_the_module_daily_series_and_counts_journal_trades`.
- **54 (`journal recompute`)** — `tests/test_journal_recompute.py`:
  `test_seeds_are_the_fixture_records`,
  `test_all_matches_every_pair_exits_0_and_writes_nothing`,
  `test_one_changed_field_exits_1_prints_the_pair_and_appends_one_journal_mismatch`,
  `test_the_sample_is_drawn_with_d_from_days_before_d_the_same_on_every_run`
  (two `--as-of` instants),
  `test_the_sample_differs_from_one_seeded_otherwise`,
  `test_fewer_pairs_than_the_sample_recomputes_every_pair_before_d`,
  `test_journal_recompute_help_exits_0`.
- **55 (time through the injected clock)** — `tests/test_daily.py`:
  `test_two_fresh_state_directories_give_equal_content_and_health`;
  `tests/test_state.py`:
  `test_a_state_commit_has_the_message_author_and_dates_of_the_clock`,
  `test_init_state_creates_a_committed_git_repository`,
  `test_init_state_takes_the_common_options`.

## What the tests prove

Taken from each unit's commit body; on the cases named there. Journal,
paper and recompute tests run on `test_mixed` (seeds SYNA 101, SYNL 105,
SYNX 106, asserted in each file).

- U1: a connection attempted in a module-scoped and in a session-scoped
  fixture raises `SocketBlocked`, and the error names the test that set up
  the fixture; `connect`, `connect_ex`, `sendto` and `getaddrinfo` through
  `_socket` directly raise `SocketBlocked`, and an AF_UNIX socket through
  `_socket` still connects; in a scratch pytest session (loopback listener
  only) a `network`-marked test connects through `socket` and `_socket`,
  an unmarked test after it is blocked again, and an unmarked test that
  connects fails; the files under `tests/` and `src/` whose text contains
  `subprocess` or `os.system` equal `SUBPROCESS_FILES` on today's tree, and
  on a scratch copy an added `src` file with `subprocess.run` or an added
  test with `os.system` fails the listing naming that file. Seen to fail:
  the backstop back at function scope; `_socket` left unguarded.
- U2: `init-state` creates a Git repository whose one committed file is a
  `.gitignore` ignoring `bars/**/*.parquet`, the staging directory and the
  lock (checked with `git check-ignore` on sample paths), committed by
  `discotrade <discotrade@invalid>` at the `--as-of` instant; a second run
  leaves every file (`.git` included) byte- and mtime-identical and exits
  0; a non-empty non-state directory (a file, a subdirectory, a bare `git
  init`) and a path that is a file exit 1 unchanged; inside a code
  repository exits 2; a second lock while one is held fails naming the
  lock path; the lock is removed after a failure inside it; a state commit
  has message `run <track> <date>`, that author and committer, and `%at`
  and `%ct` equal to the clock's instant; nothing changed makes no commit;
  the health log appends `HealthEvent.to_json()` lines by rename (inode
  changes), keeps earlier lines byte-identical, is unchanged when the
  rename fails, skips a line already present or repeated in one call, and
  refuses a torn last line. Seen to fail: lock without `O_EXCL`; the
  duplicate check removed; commit dates from the wall clock.
- U3: the approach id equals a value computed in the test from decision
  48's definition; `meta.json` holds exactly the listed fields; a source
  not matching a file under `reference/` or `tests/fixtures/` fails the day
  naming the approach and writes no journal; a day's rows have decision
  49's columns, each instrument's first row flat, every later `position`
  equal to the previous row's `target_next` (with a non-zero target carried
  across a day boundary); a day file is written once with its index line;
  an equal re-run leaves file and index bytes, inode and mtime unchanged;
  an unequal re-run (previous day's last SYNX `target_next` changed by the
  test) returns one `journal_mismatch` naming the day and approach and
  leaves file and index untouched; a day with no subject writes an empty
  file and its index line; a skipped day fails the next and writes
  nothing; for `trend_ma`, `zscore_reversal` and `hour_of_day`, the rows
  journaled day by day over 2019-06-08 to 2019-06-19 (holding the SYNA
  roll of 2019-06-14) equal `backtest.evaluate` over the span field for
  field under decision 39's rule (`p`, `h`, `gross`, `trade`, the four
  components, `cost` as their sum, `net_1x`, `net_2x`), with equal `ts`
  and dates. Seen to fail: position reset each day; first row's position
  as its target; the equal re-run rewriting the file. G0.1 passed after
  `backtest.py` changed.
- U4: on a state made by `init-state` with two approaches, `run-day` over
  2019-06-08 to 06-12 writes each day's journal file, index line and paper
  file in one commit `run test_mixed <date>` each, `git status` clean, no
  lock or staging left; bars end at the last bar of `D` per calendar; the
  journal equals that of a state whose bars were fetched at once; the
  default day is decision 19's `D`; re-running 06-12 and 06-09 leaves every
  file, the health log and the commit list unchanged; a skipped 06-13 exits
  1 naming it and changes no file; a non-repository source fails the day
  naming it, changes no journal or paper byte, makes no commit and leaves
  no lock or staging; a held lock exits 1 naming it; a missing, empty or
  plain directory is refused naming `init-state`; `data_gaps` is absent at
  the repository limit 0.01 and appended once with `max_fraction` 0.002 (a
  configuration copied under the test's temporary directory); a
  `store_recovered` notice is appended once; a revised SYNA bar fails the
  day with one `revised_data` alert; two fresh state directories give
  equal index lines, paper content hashes, health logs and commit
  author/date/message lists; the paper file rebuilds from the journal to
  the same content hash, equals the module's daily series under decision
  39's rule, and counts rows with `trade > 1e-9` (a hand-made frame holds
  5e-10 and 1e-9). Seen to fail: a second index line on re-run; the lock
  removed only on success; paper `trades` counting `trade > 0`;
  `test_daily.py` absent from `SUBPROCESS_FILES`.
- U5: after `run-day` over 2019-06-08 to 06-12 with two approaches,
  `journal recompute --all` reports every pair equal, exits 0, and leaves
  every file of the state directory (`.git` included) byte- and
  mtime-identical; with `net_1x` of one row of one stored day file changed
  by the test it exits 1, prints that pair as `MISMATCH`, appends exactly
  one `journal_mismatch` naming it, and changes no journal file; without
  `--all` and `journal.recompute_sample = 3` (configuration copy under the
  test's temporary directory) it recomputes 3 pairs, all of days before
  `D`, the same on two runs and equal to the draw of
  `numpy.random.default_rng(YYYYMMDD)`, for two `--as-of` instants; with
  the repository's value 20 and 6 pairs before `D` it recomputes all 6.
  Seen to fail: comparing stored rows with themselves; the sample seeded
  with `D.toordinal()`.
- The gate run at 6aea7c0: `./scripts/check` green three times;
  `./scripts/gate M0` prints `G0.1` to `G0.4 PASS` and `gate M0: PASS`,
  exit 0, in 349 s.

## Correction of FINAL-REPORT-6

FINAL-REPORT-6 says, under G0.1, that "a test asserts that at the SYNA
roll bar 2019-06-14T00:00Z of the window `h(u-1) = 1.0` and `h(u) = -0.5`
in both discotrade's and the calculation's rows." That overstates the
test (REVIEW-6 should-fix 1). The test
`test_probe_changes_position_at_the_syna_roll`
(`tests/gates/test_g0_1_reference.py`) asserts, at every SYNA roll bar of
the window, that a roll exists and that `h(u-1) != h(u)`, `h(u-1) != 0`,
`|h(u-1)| != |h(u)|` and roll and trade are positive, in both sets of rows.
The bar 2019-06-14T00:00Z and the values `h(u-1) = 1.0`, `h(u) = -0.5`
were observed by the reviewer, not asserted. Decision 43 (c) requires only
`h(u-1) != h(u)`, which the test asserts; only the report overstated it.
No test changed (decision 56).

## NOT PROVEN

New in this mission:
- The subjects are approaches only until step S1.2 adds the controls of
  §10.1 and the lifecycle; every approach in the state is journaled from
  its first day after admission (decision 48).
- Approach sources run in-process, and only when their sha256 equals that
  of a file under `reference/` or `tests/fixtures/`, until step S2.2 moves
  them behind the sandbox (decision 48).
- Step 1's writes are not staged: after a failed day the bar index, rolls,
  `gaps.jsonl` and the health log stay changed and uncommitted until the
  next good day. The retry from a clean staging directory, `run_failed`,
  the push to a remote and the catch-up of missed days are step S4.2's
  (decision 50).
- The weekly recomputation (step 6 of §16.1) is not yet wired into the
  day; `journal recompute` runs only when called (decision 54).
- `run-day` is proven on synthetic sources only (`test_mixed`); no test
  runs it on `test_synth`, a real adapter or the hourly track.
- The `clean` flag of the paper records is step S1.2's (decision 53).
- U1: `socket.SocketType` used directly is not blocked; a binding taken
  with `from _socket import socket` before the session starts is not
  blocked; a module- or session-scoped fixture first set up by a
  `network`-marked test runs unblocked; child processes are not blocked
  (the listing test only classifies the files that launch them).
- U2: a directory left by an interrupted `init-state` is refused with exit
  1, not repaired; the lock is tested only within one process; no fsync
  or crash behaviour is tested.
- U3: a day file whose bytes changed while its index line did not is
  reported unchanged on a re-run (it is left to `journal recompute`); the
  carry guard is tested only by the skipped-day case; the day-by-day
  equality with the module evaluation is shown only on `test_mixed` over
  one 12-day span.
- U4: no estimated-roll-gap notice arises on `test_mixed`, so "the notices
  of step 1 are appended once" is shown with `store_recovered` only;
  `revised_data` is detected by matching the bar store's error text ("a
  revised data point").
- U5: not tested beyond 5 days and 2 approaches, without controls, and not
  on `test_synth`; that a whole-span recompute equals day-by-day journaling
  is shown on this fixture only.

Carried from FINAL-REPORT-6, updated:
- The half-tick spread floor is proven by unit tests on each side, not
  through G0.1 (decision 43). The roll timing through G0.1 rests on a
  test-only probe on one roll bar of one window, compared through the
  module API (decision 21); see the correction above for what its test
  asserts. Slippage at a roll bar is not checked in the hand cases.
- The calculation's independence (mission 5 U3, mission 6 U2) rests on its
  authors' statements; it shares synthetic bars, roll records and the
  loader with the code, and the choices made where DESIGN is silent agree
  with the code on `test_mixed` only.
- G0.1 is shown on one fixture track and one window (plus the LOW window
  for `--json`); `position_min`/`position_max` are tested as `cli.py`
  computes them; wrong changes to top-level keys other than an added key
  were not tried.
- `tests/test_gate_script.py`'s stability under any given load is not
  proven; its scratch-pytest helpers keep 120 s timeouts.
- D-006 (`backtest` shares one loaded strategy across a subject's
  instruments) stays deferred to S2.1 (decision 44) and not exercised.
- G0.2 covers what §12.1 lets a text reach, not interpreter escapes
  (G2.1's, decision 40); truncation invariance at ten or more `t` per
  instrument on one 29-day window.
- G0.3 takes the underlying series and dropped bars from product code of
  the synthetic source; G0.4's whole-word match is case-insensitive, skips
  `__pycache__`, and scans names found in `config/` only.
- Every cost value is from SPEC §17, the DESIGN §4.2 example or the R-5
  reading, `verified = false`, none measured; fixture costs and SYNA's
  spread table are invented; no result means anything about a market.
  Finding D-003 stays.
- Carried by `meta/BACKLOG.md`: an unlisted month file inside the window
  not driven through `backtest`. The I-11 socket backstop's scope item is
  taken by U1 (decision 47), within U1's NOT PROVEN above.
- What remains of mission 4's and mission 3's NOT PROVEN, as listed in
  FINAL-REPORT-5, is unchanged by this mission.

## Findings filed and answered

- HF-007 (hands finding: the review protocol's step 2 proves nothing on a
  tests-only unit commit; review sub-agents ran `./scripts/check` once):
  filed in U0 (057f9d2), status open.
- No other finding was filed in this mission (`git diff c73a695 --
  meta/findings/FINDINGS.md` adds HF-007 only). None was answered in this
  mission. HF-006 stays open: every `./scripts/check` and `./scripts/gate`
  run reported was in the foreground with a timeout of at least 20
  minutes. D-003 stays; D-006 stays deferred to S2.1.

## Review items

| Item | Review | Resolution | Sha |
|---|---|---|---|
| REVIEW-6 should-fix 1 | FINAL-REPORT-6 describes the roll-probe test as asserting a bar and two values that it does not assert | U6, decision 56 (the `## Correction of FINAL-REPORT-6` section above; no test changed) | this commit |
| REVIEW-3 note on the socket backstop (I-11, `meta/BACKLOG.md`) | The backstop held only in function-scoped tests | U1, decision 47 (guard from session start in every fixture scope and through `_socket`; `network`/`live` tests left alone; subprocess listing test) | de2a5b2 |

VERDICT: mission 7 finished
