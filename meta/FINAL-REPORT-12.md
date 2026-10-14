VERDICT: mission 12 finished

# FINAL REPORT — mission 12 (roadmap step S2.1)

Brief: `meta/BUILDER-12-PROMPT.md`. Base c2612a6. Decisions:
`meta/decisions/decisions-2026-10-14-m12.md` (91 to 99), with the owner's
O-17, O-16 and O-18 (O-1 to O-4 and O-11 to O-13 still bind). This mission
closes no milestone; gate M1 was run again item by item and gate M0 once,
as decision 91 says.

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | d250987 | plan, checkpoint, journal; FINDINGS status lines: D-010 answered (item 93), D-006 taken by U3 (item 95) |
| U1 | 52d7fec | the audit reads the six string constants anywhere in a function's own body (decision 92); `cli._backtest_result` registered `display`, `replay._adjusted` `producer`; `ledger.append` refuses a lifecycle row of reason `admitted`, `displaced`, `dormant`, `returned` without both `adjusted` and `plain`, and a trial row without both `adjusted_t` and `adjusted_w` (decision 93, D-010); lines on disk are not read against the check |
| U2 | 92703c9 | `validation/static.py`: the static check of DESIGN §12.1 (decision 94), rules in §12.1's order, thresholds from `config/thresholds.toml`; `tests/test_static_check.py` (365 tests) |
| U3 | fa4b53b | `sandbox/base.py` (protocol, job, result, `build_job`), `sandbox/runner.py` (fresh load per parameter set and instrument, D-006), `sandbox/inprocess.py` (decision 95); the job on disk is `job.json` plus one uncompressed `.npz` per instrument, read without `pyarrow` |
| U4 | d553c35 | `sandbox/process.py`: child process in isolated mode, RLIMIT_AS and RLIMIT_CPU, harness wall-clock kill, output cap, repository-source sha256 check, child environment from an allow-list; `config.py` loads `run.toml`; `config/run.toml` and `tests/fixtures/config/run.toml` (new, same values); `SUBPROCESS_FILES` gains `process.py` (decision 96) |
| U5 | 4c09fd1 | `paper.adjusted_rows` and the shared private `_less_exposure` (and `_window_units`); `validation/sequence.py`: combinations, the dry run and the grid on W fixed on the exposure-adjusted net Sharpe at 1x, both measures recorded (O-17, decision 97); four register entries |
| U6 | 4d77450 | determinism (rerun and reverse sample), activity, the correlation gate (`validation/correlation.py`) and `validate`, the five stages in order (decision 98) |
| U7 | this commit | this report |

Meta commits between units: 8b077cd, f2551e0, 1be3a70, 0ebc8be, 196748d,
054daa1, and the one that closes the mission.

Existing tests changed in what they assert, each under a cited decision
and named in its commit body (U1, 52d7fec): in `tests/test_return_readers.py`
(decision 92) `test_other_shapes_are_not_found` (a dict key and a
comparison inside a function are now found), and the label in
`test_a_parameter_default_is_a_keyword` and
`test_an_unregistered_reader_fails`; in `tests/test_ledger.py` (decision
93) the four-reason and trial-row tests renamed `..._must_carry_...` and
their rows given both figures; in `tests/test_lifecycle.py` (decision 93)
the helper `put()` writes seeded rows of the four reasons with `adjusted`
and `plain` null, which changes the seeded rows of 17 tests, named in the
body; their expected rows are unchanged. U5: every test of
`tests/test_exposure.py` passes unchanged. No file under `tests/gates/`
changed.

## Speed

`./scripts/check` wall time on the builder's machine:

| Where | Runs |
|---|---|
| base (mission 11's tip, per the brief) | about 490 s (mission 11's three: 487, 489, 494 s) |
| U1 (52d7fec) | about 487 s (485-490 s), no added time |
| U2 (92703c9) | about 490 s (+~1 s) |
| U3 (fa4b53b) | about 506 s (+13 s) |
| U4 (d553c35) | 509, 514, 587 s (+~10 s) |
| U5 (4c09fd1) | 624, 616, 604 s |
| U6 (4d77450) | 631, 659, 668 s |
| tip 054daa1 (U7) | 856, 590, 589 s, each `check: green` |

U5 added about 100 s: `tests/test_validation_grid.py` takes about 29 s
alone; the rest is unexplained in its body (`tests/test_exposure.py` with
`tests/test_daily.py` took 104 s at both the parent and U5, so the
`paper.py` change does not explain it). U6 added about 46 s (its two new
test files, mostly the child-process jobs of the correlation and
full-sequence tests). At the tip the first run took 856 s and the next two
590 and 589 s; the first run's extra time is not explained (the load
average was 2.04 over 15 minutes just after it, 1.56 after the third run;
nothing else was profiled). The steady figure, about 590 s, is about
100 s above the base.

Gate M1 item by item and gate M0, wall time:

| Item | mission 11 (6b61c6e) | mission 12 (054daa1) |
|---|---|---|
| G1.1 | 386.80 s | 386 s |
| G1.2 | 171.45 s | 172 s |
| G1.3 | 518.41 s | 575 s |
| G1.4 | 1.07 s | 1 s |
| M0 | 246.32 s | 257 s |

Every M1 item is under 10 minutes (O-3); no finding under decision 91.
G1.3 rose by 57 s with no file under `tests/gates/` changed; it now
stands 25 s under the 10-minute line. The rise was not profiled.

## Gate M1

Each item its own foreground call at tip 054daa1, after `./scripts/check`
was green three times at that tip (856, 590, 589 s).

`./scripts/gate M1 G1.1` — wall 386 s

```
G1.1 PASS 6 passed, 1 warning in 385.46s (0:06:25)
gate M1 G1.1: PASS
```

`./scripts/gate M1 G1.2` — wall 172 s

```
G1.2 PASS 4 passed in 171.28s (0:02:51)
gate M1 G1.2: PASS
```

`./scripts/gate M1 G1.3` — wall 575 s

```
G1.3 PASS 10 passed in 573.61s (0:09:33)
gate M1 G1.3: PASS
```

`./scripts/gate M1 G1.4` — wall 1 s

```
G1.4 PASS 15 passed in 0.60s
gate M1 G1.4: PASS
```

By O-2's rule, gate M1 passes at 054daa1.

## M0 still passes

`./scripts/gate M0` at 054daa1 — wall 257 s

```
G0.1 PASS 62 passed in 58.97s
G0.2 PASS 7 passed in 96.44s (0:01:36)
G0.3 PASS 13 passed in 99.07s (0:01:39)
G0.4 PASS 4 passed in 0.27s
gate M0: PASS
```

## Register

`tests/fixtures/return_readers.toml`, 30 entries (24 at the base): producer
18, adjusted 6 (one pending), display 5, timing_gross 1 (pending),
stage3_money 0. Entries carrying `pending`: 3 (`stats.rank_persistence`,
`stats.control_moments`, `table.build.approach_row`, all `pending =
"S4.1"`), unchanged. No existing entry changed in this mission
(`git diff c2612a6 HEAD -- tests/fixtures/return_readers.toml` adds six
entries and changes none).

| Function | Class | Note | Unit |
|---|---|---|---|
| `discotrade.cli._backtest_result` | display | the backtest command's output: plain DESIGN 8 metrics and per-instrument net_1x, net_2x totals; nothing selects on them (O-18, decision 92) | U1 |
| `discotrade.replay._adjusted` | producer | checks a scripted candidate's adjusted_t figures and avg_position against the track; decides nothing (decision 92) | U1 |
| `discotrade.paper._window_units` | producer | computes the unit-position gross of a window's bars (decision 81 (b)) for unit_bars and window_units; decides nothing | U5 |
| `discotrade.paper.adjusted_rows` | producer | computes the exposure-adjusted series (O-4) on a window from evaluation rows, for the grid on W; decides nothing (decision 97 (c), (f)) | U5 |
| `discotrade.validation.sequence.fix_combination` | adjusted | the grid on W: fixes the combination with the greatest exposure-adjusted Sharpe at 1x, through paper.adjusted_rows (O-17, O-18, decision 97 (d), (f)) | U5 |
| `discotrade.validation.sequence._grid_result` | producer | records each combination's plain and adjusted Sharpe and the fixed one's W figures as decision 97 (e)'s result; selects nothing | U5 |

U1's body: the widened audit finds no other unregistered function at
52d7fec; `replay._adjusted` is not found by it (its keys are module
constants, outside any function) and is registered because decision 92
names it, a test asserting it exists. U5's body: `paper.unit_bars` keeps
its `producer` entry, though its `"gross"` read moved into
`_window_units`. U6 added no entry; the audit passes unchanged.

## Validation

`tests/test_validation_sequence.py` on the subprocess backend, on
`test_synth`'s own W of 2019-07-15, at the production thresholds
(`min_changes_w` 30, `corr_max` 0.7), each failing run stopping at its
stage (the recorded jobs show nothing later ran):

| Stage | Fixture that fails it | Test |
|---|---|---|
| `static` | `tests/fixtures/strategies/six_params.py` (rule `max_params`); also a text that does not parse (rule `parse`) | `test_stage_static_fails_and_stops_there`, `test_a_text_that_does_not_parse_fails_stage_static` |
| `dry_run` | `tests/fixtures/strategies/grid_out_of_range.py` (rule `out_of_range`) | `test_stage_dry_run_fails_and_stops_there`; also `tests/test_validation_grid.py::test_a_combination_returning_a_value_out_of_range_fails_the_dry_run` |
| `determinism` | `tests/fixtures/strategies/keeps_state.py` (rule `reverse_sample`) | `test_a_fixture_keeping_state_passes_static_and_fails_determinism_on_the_reverse_sample`; rule `rerun` by `test_the_second_run_is_a_new_job_whose_positions_must_equal_the_first` |
| `activity` | `tests/fixtures/strategies/changes_29.py` (rule `min_changes_w`) | `test_stage_activity_fails_below_min_changes_w_and_stops_there` |
| `correlation` | `tests/fixtures/strategies/trend_ma_flipped.py`, against an approach admitted from `reference/trend_ma.py` | `test_the_sign_flipped_duplicate_fails_stage_correlation_naming_the_approach` |

The fixture passing all five: `tests/fixtures/strategies/changes_30.py`
(exactly 30 changes summed over the basket, none of 30 alone;
`|r| < 0.7` with the live approach): `test_a_valid_fixture_passes_every_stage`,
`test_exactly_min_changes_w_position_changes_pass_the_activity_stage`,
`test_a_fixture_below_corr_max_with_the_approach_passes_the_correlation_gate`,
`test_the_sequence_returns_decision_97_e_s_result`,
`test_the_sequence_writes_nothing_to_the_state_directory`.

## Decisions 92 to 98: the tests that hold them

- **92** — `tests/test_return_readers.py`: `test_a_string_constant_is_found_anywhere_in_a_function_body`
  (eleven shapes: tuple of a generator, list, set, dict key, dict value,
  comparison, list subscript, tuple subscript, call argument, lambda
  default, dict comprehension), `test_a_constant_belongs_to_the_innermost_function`,
  `test_the_readers_review_11_named_are_registered`, `test_other_shapes_are_not_found`,
  `test_a_parameter_default_is_a_keyword`, `test_an_unregistered_reader_fails`,
  `test_the_audit_passes`, `test_the_pending_entries_are_the_three_of_decision_89`.
- **93** — `tests/test_ledger.py`: `test_a_lifecycle_row_of_four_reasons_must_carry_adjusted_and_plain`,
  `test_a_lifecycle_row_of_another_reason_carries_neither_figure`,
  `test_a_trial_row_must_carry_adjusted_t_and_adjusted_w`,
  `test_a_ledger_holding_a_line_written_before_the_figures_is_still_appended_to`,
  `test_earlier_lines_stay_byte_identical_and_a_present_line_is_not_appended`.
- **94** — `tests/test_static_check.py`: `test_rules_are_in_section_order`,
  `test_text_that_does_not_parse`, `test_max_lines_physical_lines`,
  `test_max_lines_read_from_configuration`, `test_no_params`,
  `test_params_assigned_twice`, `test_params_not_a_plain_dict_literal`,
  `test_too_many_params`, `test_param_key_not_a_string`,
  `test_param_value_not_numeric`, `test_param_value_bool`,
  `test_param_value_numeric_accepted`, `test_no_grid_passes`,
  `test_grid_not_a_dict_of_lists`, `test_grid_value_not_numeric`,
  `test_grid_negative_value_accepted`, `test_grid_key_outside_params`,
  `test_grid_too_many_keys`, `test_grid_too_many_values`,
  `test_position_signature`, `test_position_defined_twice_or_rebound`,
  `test_import_accepted`, `test_import_refused`, `test_construct`,
  `test_underscore`, `test_underscore_import_alias_and_from_name`,
  `test_forbidden_lists_are_section_12_1`, `test_forbidden_name_as_name`,
  `test_forbidden_name_as_parameter`, `test_forbidden_name_as_keyword_argument`,
  `test_forbidden_name_as_function_name_and_alias`, `test_forbidden_attribute`,
  `test_forbidden_attribute_through_from_import`, `test_read_and_to_attributes`,
  `test_to_numpy_accepted`, `test_forbidden_attribute_words_are_free_as_names`,
  `test_each_break_breaks_only_its_rule`, `test_two_rules_name_the_earlier`,
  `test_pairs_cover_adjacent_rules`, `test_first_offending_node_in_source_order`,
  `test_order_within_params_and_grid`, `test_reference_has_files`,
  `test_valid_texts_pass`.
- **95** — `tests/test_sandbox_runner.py`: `test_the_runner_imports_only_the_standard_library_numpy_pandas_and_indicators`,
  `test_the_window_holds_a_syna_roll`,
  `test_the_runners_targets_equal_backtest_evaluate_for_two_parameter_sets`,
  `test_the_runners_result_check_agrees_with_strategy_check_result`,
  `test_a_negative_result_is_clipped_where_shorting_is_not_allowed`,
  `test_a_bad_text_gives_its_stage_and_an_error_text`,
  `test_an_error_stops_the_run_at_the_first_bad_result`,
  `test_zz_no_error_text_holds_a_symbol_venue_contract_date_or_price`,
  `test_the_cheating_text_through_the_runner_gives_each_instrument_its_targets_alone` (D-006),
  `test_reverse_sample_gives_for_its_bars_the_targets_of_positions`,
  `test_a_sample_outside_the_window_is_refused`,
  `test_the_in_process_backend_runs_a_function_object`,
  `test_the_in_process_backend_reports_a_bad_result_with_its_stage`,
  `test_the_in_process_backend_refuses_source_text`,
  `test_the_runner_without_a_job_directory_is_a_usage_error`,
  `test_what_the_text_prints_does_not_reach_the_result`;
  `tests/test_sandbox_job.py`: `test_a_w_job_holds_no_bar_after_w_and_the_context_decision_23_gives`,
  `test_the_job_carries_the_roll_gaps_from_the_roll_records`,
  `test_a_bar_of_t_is_not_in_the_job_written_to_disk`,
  `test_the_in_process_backend_refuses_a_job_carrying_source_text`,
  `test_a_job_carries_a_text_or_a_function_and_never_both`,
  `test_a_job_carrying_a_function_object_is_not_written_to_disk`.
- **96** — `tests/test_sandbox_process.py`: `test_run_toml_loads_and_the_fixture_holds_the_values_of_config`,
  `test_run_toml_refuses_an_unknown_key_naming_it`,
  `test_job_building_refuses_a_configuration_without_run_toml`,
  `test_job_building_reads_its_limits_from_run_toml`,
  `test_config_check_still_passes`,
  `test_the_child_is_this_interpreter_in_isolated_mode`,
  `test_trend_ma_gives_the_targets_of_the_in_process_runner`,
  `test_a_source_not_in_the_repository_is_refused_naming_the_rule`,
  `test_a_job_carrying_a_function_object_is_refused`,
  `test_the_child_environment_holds_only_the_allow_list`,
  `test_an_endless_loop_is_killed_at_the_wall_clock_limit`,
  `test_an_output_over_the_cap_returns_limit`,
  `test_a_memory_bomb_returns_limit_or_a_dry_run_error`;
  `tests/test_offline.py::test_every_file_that_launches_a_subprocess_is_listed`.
- **97** — `tests/test_validation_grid.py`: `test_the_combinations_come_in_decision_97_a_order_for_a_grid_of_two_keys`,
  `test_the_grid_runs_its_combinations_in_that_order`,
  `test_a_combination_returning_a_value_out_of_range_fails_the_dry_run`,
  `test_a_text_that_fails_to_load_fails_the_dry_run`,
  `test_the_grid_fixes_the_greatest_adjusted_sharpe_where_the_plain_would_fix_another`,
  `test_a_tie_fixes_the_first_in_order`,
  `test_a_grid_whose_figures_are_all_not_a_number_fixes_the_first`,
  `test_the_result_has_decision_97_e_shapes_and_the_test_s_values`,
  `test_the_child_process_backend_does_not_enforce_the_call_time_limits`,
  `test_the_in_process_backend_does_not_enforce_the_call_time_limits`,
  `test_a_backend_that_enforces_the_call_time_limits_fails_a_slow_run`,
  `test_at_the_limits_a_run_passes`,
  `test_zz_no_error_text_holds_a_symbol_venue_contract_or_date`,
  `test_the_grid_s_function_is_registered_adjusted_and_adjusted_rows_producer`,
  `test_adjusted_and_adjusted_rows_subtract_through_one_private_function`,
  `test_the_harness_reads_params_and_grid_without_running_the_text`;
  `tests/test_return_readers.py::test_a_call_of_paper_adjusted_rows_is_the_call_o18_asks_for`,
  `test_an_adjusted_entry_calls_paper_adjusted`; every test of
  `tests/test_exposure.py`, unchanged.
- **98** — `tests/test_validation_sequence.py`: every test of the
  `## Validation` table, and `test_the_reverse_sample_is_drawn_as_decision_98_a_says`,
  `test_a_retired_approach_is_not_compared_and_a_flat_one_is_not_a_duplicate`,
  `test_a_dormant_approach_is_compared_and_of_two_over_the_limit_the_larger_is_named`,
  `test_zz_no_error_text_holds_a_symbol_venue_contract_or_date`;
  `tests/test_correlation.py`: `test_corr_max_is_the_production_value`,
  `test_pearson_is_the_pearson_correlation`,
  `test_a_series_with_zero_deviation_gives_no_correlation`,
  `test_a_pair_with_zero_deviation_is_not_a_duplicate`,
  `test_a_strong_negative_correlation_is_a_duplicate`,
  `test_only_an_absolute_correlation_above_corr_max_is_a_duplicate`,
  `test_of_two_over_the_limit_the_larger_absolute_correlation_is_named_lowest_id_on_a_tie`,
  `test_the_position_series_is_h_concatenated_in_the_order_given`,
  `test_live_and_dormant_approaches_are_compared_and_retired_ones_are_not`,
  `test_without_approaches_nothing_is_compared`.

## What the tests prove

- The audit finds a listed column constant in each of eleven shapes inside
  a function and passes on `src/` with the register; the wrong changes
  (the `cli._backtest_result` entry removed; a `"net_1x"` held only in a
  tuple of a generator) fail it.
- `ledger.append` refuses, on the four reasons and on trial rows, no
  figure or one figure, and a figure on `retired_dormant` and `failure`
  rows; a ledger holding a line written without the figures is appended
  to, its earlier bytes a prefix of the new file.
- At the production thresholds (60, 5, 2, 3) each rule of §12.1 refuses a
  text that breaks only it, naming it; every mergeable pair of breaking
  texts is refused naming the earlier rule; the first offending node in
  source order is named; every file under `reference/` and the four named
  fixtures pass; a copied configuration with `max_lines` 20 refuses a
  30-line text the production value accepts.
- The runner's targets equal `backtest.evaluate`'s bit for bit for the
  three reference strategies on SYNA, SYNL and SYNX of `test_mixed` over
  2019-06-11..2019-06-18 (SYNA's 2019-06-14 roll), for two parameter sets
  in one job; its result check agrees with `strategy.check_result` on 24
  values; `cheat_lookahead.py` through the runner gives each instrument
  and parameter set the targets of the text loaded afresh and evaluated
  on that instrument alone; a W job of D = 2019-07-15 on `test_synth`
  holds no bar after W's last day.
- On the subprocess backend: `trend_ma` targets equal the in-process
  runner's; a source with one added comment is refused
  (`repository_source`); a fake key set in the parent does not reach the
  child; an endless loop returns `limit`/`wall_clock` and the backend then
  runs a good job; a 1000-byte cap returns `limit`/`output`; a memory bomb
  returns `limit` or `dry_run` (seen: `dry_run`, `MemoryError`).
- On `test_synth`'s W of 2019-07-15 at the production thresholds,
  `grid_lean.py` fixes bias 0.5 (greatest adjusted Sharpe at 1x) where
  the plain Sharpe at 1x picks bias -0.5, both figures computed in the
  test; a tie and an all-not-a-number grid fix the first; the result's
  values equal the test's own computation; a fake backend that says it
  enforces the call-time limits fails `call_p95` and `call_max` at the
  production 50 and 500 ms; `paper.adjusted` and `paper.adjusted_rows`
  subtract only through `_less_exposure`.
- Each of the five stages fails on its fixture and stops there; the
  passing sequence leaves every byte of the state directory, `.git`
  included, and `HEAD` unchanged; no error text the fixtures produce holds
  a symbol, venue or contract of `config/` or `tests/fixtures/config/` or
  matches a date pattern.
- Gate M1 items and gate M0 pass at 054daa1.
- `git diff c2612a6 HEAD` of `tests/gates`, `config/instruments`,
  `config/tracks`, `config/calendars`, `config/thresholds.toml`,
  `tests/fixtures/config` and `tests/fixtures/config_frozen.json` holds
  only the new `tests/fixtures/config/run.toml`; `config/models.toml` does
  not exist.

## NOT PROVEN

- The subprocess backend is not a security boundary: it runs only sources
  whose sha256 is that of a repository file, with an allow-listed
  environment and RLIMIT_AS/RLIMIT_CPU, but nothing stops a hostile text
  from reading files or opening a socket. The container backend, its
  image, the probe and the hostile suite are step S2.2's. The CPU-time
  limit was set but no test shows it firing.
- The static check's list is a floor (§12.1): it was checked against the
  rules as written and the builder's own breaking texts; it is pinned
  against attacks only by step S2.2's hostile suite.
- Call-time limits are enforced only by the container backend (step
  S2.2), so no call time was enforced in this mission; only a fake backend
  carrying `enforces_call_limits` shows the rule failing.
- The grid's adjusted figure on W discards a steady-position edge, as
  O-4's "Known and not proven" says. `grid_lean.py`'s plain/adjusted
  disagreement holds on this one W and these seeds only.
- The audit sees only the shapes it scans: a string constant at module or
  class level (as `replay._adjusted` shows), a figure passed through a
  variable or under another name, or a new column, is not seen.
  `replay._adjusted` is registered by name only. REVIEW-11 note 7's
  remaining items (the module-wide name match, the one-hop call through
  `_figures`, an uncalled nested function) are carried in
  `meta/BACKLOG.md` to step S4.1 (decision 92). The classes are the
  builder's reading of O-16 and O-18.
- Approaches still run in-process in the day loop until step S2.2
  (decision 48); `discotrade backtest` (`cli.py`, unchanged) still loads a
  strategy once for a subject's instruments, so D-006 is closed for the
  sandbox runner only; G0.2 does not drive the cheating text through the
  `backtest` command. Nothing calls `validate` from `run-day` or `replay`;
  the grid, determinism, activity and correlation results reach no ledger
  until step S3.2.
- The speed figures are from the builder's machine, one call per gate
  item. `./scripts/check` rose from about 490 s to about 590 s steady
  (856 s on the tip's first run, unexplained); of U5's ~100 s, ~71 s is
  unattributed. G1.3 rose from 518 s to 575 s with no gate file changed;
  the cause was not profiled, and the item now stands 25 s under 10
  minutes.
- Unit-level choices where the design is silent, stated in the bodies:
  `config/run.toml`'s values (wall 1200 s, CPU 1200 s, memory 2 GiB,
  output 64 MiB) are the builder's, no outside number; `REVERSE_SAMPLE` is
  20; a submission carrying a function object skips the static stage and
  is seeded from the empty text; an approach whose own run on W fails
  raises `ValidationError` (a harness failure, not a rejection); the
  approaches compared are those live or dormant after day D; the job keeps
  `history_cap_bars - 1` context bars; a raised exception is named by type
  only; `from <m> import *` and non-finite literals are refused; a GRID
  list must be non-empty. U5's `sequence.py` was written with its tests,
  not test first; four wrong changes stand in for that.
- The error-text check compares against the symbols, venues and contracts
  of `config/` and `tests/fixtures/config/` and a date pattern, over the
  error texts the mission's fixtures produce only.
- Decision 98's correlation, activity and determinism tests run on one W
  (2019-07-15 on `test_synth`) and one admitted approach configuration.
- No number from outside the project was added in this mission.
- Carried from FINAL-REPORT-11, still open: rank persistence, the control
  moments and the deflated figures read plain returns until step S4.1
  (the three `pending` entries); the scripted candidates' adjusted T
  figures come from a file until step S3.2, and in `g1_lifecycle.jsonl`
  the scripted adjusted and plain admission scores are equal, so G1.3
  alone does not show admission reading the adjusted measure; incremental
  exposure records and a rebuild shown equal on one 5-6 day case, the
  heal for a process killed between record moves not tested; most step
  2/3 lifecycle unit tests on hand-built records, the table tests at
  `random_pool` 4; decision 79 (b)'s cell and score from one probe replay;
  and everything carried from FINAL-REPORT-10 (O-5 to O-9 and O-14 not
  built; a bar file hashed once per day run; decision 80 (a)'s identity
  on one 30-day replay; 80 (c) on code and commit bodies; the paper heal
  on dates only; scoring on T is S3.2's; the `cutoff` behind `clean` from
  a test or scenario until S3.2; the replay has no provider, coordinator,
  issue sink or sandbox; G1.1's bounds on its seeds and its net
  rank-persistence warning not read; G1.3's rows are what the fixed seeds
  produce; the socket backstop's blind spots; the table not tested under
  900 days) and from FINAL-REPORT-8 and -9 (dormancy and the matched draw
  through `run-day` only at lowered values; step 1's writes not staged;
  retry, `run_failed`, push and catch-up are S4.2's; the weekly
  recomputation not wired; mission 7's items; the half-tick spread floor,
  the G0.1 roll probe and single fixture, G0.2's and G0.3's limits,
  G0.4's matching, 168 unverified cost values, D-003). Taken by this
  mission and no longer open: D-006 deferred to S2.1 (for the runner, as
  above), and FINAL-REPORT-11's known miss `cli._backtest_result`.

## Findings filed and answered

- **D-010** (filed mission 11 U2): answered by
  `meta/decisions/decisions-2026-10-14-m12.md` item 93; status line
  appended in U0 (d250987); built in U1 (52d7fec).
- **D-006** (filed mission 5 U5, deferred to S2.1 by decision 44): taken
  by mission 12 U3 (fa4b53b) under item 95; status line appended in U0
  (d250987).
- No finding filed in this mission: no reference file failed the static
  check, no O-16 `adjusted` reader was found unregistered, every gate item
  passed, and every item ran under 10 minutes (decision 91).
- HF-008 (concurrent reviewers near the 20-minute cap) remains open for
  the hands Project.

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-11 should-fix 1 (`cli._backtest_result` unregistered) | U1, decision 92: registered `display`; the audit reads the constants anywhere in a function | 52d7fec |
| REVIEW-11 note 7 (the list subscript; `replay._adjusted`) | U1, decision 92: a list subscript is among the eleven shapes found; `replay._adjusted` registered `producer`; the rest of note 7 carried to S4.1 in `meta/BACKLOG.md` | 52d7fec |
| Finding D-010 (figures on new ledger rows) | U1, decision 93: required on append; earlier lines untouched | d250987 (status), 52d7fec |
| Finding D-006 (one loaded strategy across instruments) | U3, decisions 44 and 95 (c): the runner loads the text afresh per parameter set and instrument | d250987 (status), fa4b53b |
| Owner decision O-17 (the grid on W on the adjusted measure) | U5, decision 97: `fix_combination` on the adjusted Sharpe at 1x, both measures recorded | 4c09fd1 |

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip 054daa1, three
  consecutive runs (856, 590, 589 s). Met.
- `./scripts/gate M1 G1.1` to `G1.4`, each its own call at 054daa1, print
  their PASS lines; `./scripts/gate M0` prints `G0.1` to `G0.4 PASS` and
  `gate M0: PASS`; outputs and times above beside mission 11's; no item
  above 10 minutes. Met.
- Static check refuses each rule of §12.1 naming it, in §12.1's order, at
  the production thresholds, and passes every reference strategy:
  `tests/test_static_check.py` (decision 94 above). Met.
- Runner targets equal `backtest.evaluate`'s on the reference strategies;
  fresh text per instrument and parameter set (D-006); a W job holds no
  later bar; error texts hold no symbol, venue, contract, date or
  timestamp: `tests/test_sandbox_runner.py`, `tests/test_sandbox_job.py`,
  and the `test_zz_...` error-text tests of the grid and sequence files.
  Met.
- Subprocess backend accepts only repository sources, enforces the
  wall-clock limit and the output cap, passes no key to the child:
  `tests/test_sandbox_process.py`. Met.
- The grid fixes on the adjusted net Sharpe at 1x on W, records both
  measures for every combination, its function is registered `adjusted`
  and calls `paper.adjusted_rows`; `paper.adjusted` returns what it
  returned before (every test of `tests/test_exposure.py` unchanged and
  passing): `tests/test_validation_grid.py`. Met.
- Each of the five stages fails on its fixture with its stage and an error
  text, a valid fixture passes all five, the sequence writes nothing to
  the state directory: `## Validation` above. Met.
- `tests/fixtures/return_readers.toml` registers every function the
  widened audit finds, `cli._backtest_result` included; the audit passes;
  exactly three entries carry `pending` (counted: 3). Met.
- `ledger.append` requires decision 87's and 86 (d)'s figures on new rows;
  no earlier ledger line is rewritten: `tests/test_ledger.py` (decision 93
  above). Met.
- No file under `tests/gates/` changed; no frozen value changed;
  `git diff --stat c2612a6 HEAD -- tests/gates config/instruments
  config/tracks config/calendars config/thresholds.toml
  tests/fixtures/config tests/fixtures/config_frozen.json` prints only
  `tests/fixtures/config/run.toml | 9 +++++++++` (a new file);
  `git diff --name-status c2612a6 HEAD -- config tests/fixtures/config`
  prints `A config/run.toml` and `A tests/fixtures/config/run.toml` only;
  `ls config/models.toml` reports no such file. Met.
- Every unit commit's body lists every file it touches (checked: each path
  of `git show --name-only` for d250987, 52d7fec, 92703c9, fa4b53b,
  d553c35, 4c09fd1, 4d77450 appears in its body); U0 is `plan:`. Met.
- No test uses the network, a secret or the wall clock (the socket
  backstop of `tests/test_offline.py` under `./scripts/check`; no
  `datetime.now`, `time.time()` or `date.today` in the mission's new test
  files); no state or job directory is written inside the repository
  (`git status --short` clean after the three check runs and five gate
  runs); no file under `src/` names a market, a contract root or a venue
  (`tests/test_instrument_agnostic.py::test_no_market_named_under_src`,
  green). Met.
- `meta/FINAL-REPORT-12.md` exists with `## Gate M1`, `## M0 still
  passes`, `## Register`, `## Validation`, NOT PROVEN and the review-items
  table: this file, moved in from `meta/drafts/` by the closing commit.

VERDICT: mission 12 finished
