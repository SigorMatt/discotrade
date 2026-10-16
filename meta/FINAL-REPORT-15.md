VERDICT: mission 15 finished

# FINAL REPORT — mission 15 (roadmap step S3.2a)

Brief: `meta/BUILDER-15-PROMPT.md`. Base 301a5c7 (`plan: mission 15 kit (S3.2a,
providers, pool, coordinator, generation)`). Decisions:
`meta/decisions/decisions-2026-10-16-m15.md` (118 to 126), with the owner's
`meta/decisions/decisions-2026-10-15-owner.md` (O-19, O-20, O-22 bind) and
`meta/decisions/decisions-2026-10-13-owner.md` (O-16 to O-18 bind); items 1 to
117 still bind (117 (c) amended by 119 (a)). This mission does not close a
milestone. At its pushed tip it ran `discotrade sandbox build`, gate M0 in one
call, gate M2 in one call and gate M1 item by item, as decision 118 (b) says.
Container runtime: docker, server Engine 29.1.3 (API 1.52).

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | ccaf429 | plan, checkpoint, journal; HF-010 and HF-011 status lines, HF-012 filed (decision 120) |
| U1 | e404e00 | REVIEW-14 should-fix 1 and notes 3, 4, 7 (decision 119): a fence line after the last block is `no_description`; `registry.sanitize` strips again after the cut; the profile's roll-record refusal tested; `mixed_ran_template` sets `GIT_ALLOW_PROTOCOL=file`. One existing assertion changed as 119 (b) says (the prompt test's brief cap, 40 to 39 and `BRIEF[:40].rstrip()`) |
| U2 | aeed087 | `src/discotrade/sources/synth.py`: the generated series kept for the life of the process, keyed by the `[source]` table with its seed, `trusted_from`, the calendar record and the bar length; `clear_cache()`; an autouse fixture in `tests/conftest.py` clears it per test (decision 121, D-013) |
| U3 | d9acfcd | `src/discotrade/workers/providers.py`: `ScriptedProvider`, `OpenAICompatProvider` (`openai_compat_from_env` the one reader of `NEBIUS_API_KEY`), `ClaudeWorkerProvider`; `doctor --live workers` (L3) (decision 122) |
| U4 | 0260f0c | `config/models.toml` and its fixture copy, `[workers]` in both `run.toml`, one new frozen-map entry, `config.load_models`, `src/discotrade/workers/pool.py` (decisions 123, 124) |
| U5 | 5f5c5c5 | `src/discotrade/coordinator.py`: the interface, `CellStatus`, `ScriptedCoordinator`, `choose` (decision 125) |
| U6 | 41b2670 | `src/discotrade/workers/generate.py`: the day's generation as a function, one call, storage before parsing, validation, one retry, budget; nine fixture responses under `tests/fixtures/responses/` (decision 126) |
| U7 | this commit | this report; a D-013 times line |

Meta commits: the checkpoint commits 624315e (U1 done), 9623799 (U2), 9ddce2a
(U3), d0ecf80 (U4), bfe4e89 (U5), 6259365 (U6). Each unit commit's body lists
its files. Nothing of this mission is called from `run-day` or `replay`
(decision 118 (a)); no trial row is written by it.

## Speed

`./scripts/check` wall time on the builder's machine (four cores):

| Where | Runs |
|---|---|
| base: mission 14's tip a3734d9 (FINAL-REPORT-14) | 830, 785, 784 s |
| U1 e404e00 | about 790 s each (3 runs) |
| U2's parent 624315e | 791 s (one run) |
| U2 aeed087 | 801, 798, 807 s |
| U3 d9acfcd | 797, 797, 793 s |
| U4 0260f0c | 800 to 812 s |
| U5 5f5c5c5 | 797 to 809 s |
| U6 41b2670 | 832, 833, 834 s |
| tip 6259365 (U7) | 848, 828, 838 s, each `check: green` |

At the tip each run printed `2291 passed, 182 deselected` (0 skipped, so the
`container` tests ran on discotrade-sandbox:3b7d75c39621) and `check: green`;
pytest 846.70 s, 826.49 s, 836.61 s. The mission added 139 tests (2152 at
mission 14's tip). Decision 114's 12 minutes (720 s) is missed by 108 to 128 s;
no run is above 15 minutes; the times are appended to D-013 in this commit.

Seconds per replay day, the G1.3 scenario's first 30 calendar days (22 replay
days, decision 80 (d)'s method, U2's body): **1.598 s** at U2's parent 624315e
(35.16 s) and **1.623 s** at U2 aeed087 (35.70 s), the state directories
identical outside `.git/`. U2 gave no speed gain beyond noise: under cProfile
the synthetic fetch fell from 1.49 s to 0.58 s of about 61 s, but a replay
already built one source per run; the time goes to `journal_day` (about 30 s),
the store's verify and append (about 7.4 s) and content hashes (about 4.9 s).

## Regression gates

All at tip 6259365d6e9360c8cbdeb7b50d82fe4189cc0f24 (`git rev-parse HEAD` at
the head of each gate's output; nothing committed between the first check run
and the last gate item), each its own foreground call with a 20-minute timeout,
after `./scripts/check` was green three times at that tip. Load average about
1.0, nothing else of this project running.

`uv run discotrade sandbox build` — exit 0, wall 1 s (0.7 s)

```
sandbox build: present, nothing built
discotrade-sandbox:3b7d75c39621
```

`./scripts/gate M0` — exit 0, wall 251 s (mission 13, the last report to run it: 266 s; mission 14 did not run M0)

```
6259365d6e9360c8cbdeb7b50d82fe4189cc0f24
G0.1 PASS 62 passed in 57.99s
G0.2 PASS 7 passed in 95.04s (0:01:35)
G0.3 PASS 13 passed in 94.90s (0:01:34)
G0.4 PASS 4 passed in 0.61s
gate M0: PASS
wall 250.880556702 s
```

`./scripts/gate M2` — exit 0, wall 130 s (mission 14: 135 s)

```
6259365d6e9360c8cbdeb7b50d82fe4189cc0f24
G2.1 PASS 36 passed in 41.19s
G2.2 PASS 3 passed in 23.59s
G2.3 PASS 8 passed in 3.77s
G2.4 PASS 9 passed in 38.91s
G2.5 PASS 5 passed in 19.58s
gate M2: PASS
wall 129.771290338 s
```

`./scripts/gate M1 G1.1` — exit 0, wall 373 s (mission 14: 385 s)

```
6259365d6e9360c8cbdeb7b50d82fe4189cc0f24
G1.1 PASS 6 passed, 1 warning in 372.08s (0:06:12)
gate M1 G1.1: PASS
wall 372.657157318 s
```

`./scripts/gate M1 G1.2` — exit 0, wall 173 s (mission 14: 174 s)

```
6259365d6e9360c8cbdeb7b50d82fe4189cc0f24
G1.2 PASS 4 passed in 172.14s (0:02:52)
gate M1 G1.2: PASS
wall 172.894276776 s
```

`./scripts/gate M1 G1.3` — exit 0, wall 522 s (mission 14: 546 s)

```
6259365d6e9360c8cbdeb7b50d82fe4189cc0f24
G1.3 PASS 10 passed in 521.08s (0:08:41)
gate M1 G1.3: PASS
wall 521.847704244 s
```

`./scripts/gate M1 G1.4` — exit 0, wall 1 s (mission 14: 1 s)

```
6259365d6e9360c8cbdeb7b50d82fe4189cc0f24
G1.4 PASS 15 passed in 0.52s
gate M1 G1.4: PASS
wall 1.123416830 s
```

(The first line of each block is `git rev-parse HEAD` and the last the wall
time, written by the capturing command around the gate's own output.)

| Item | mission 14 (a3734d9) | mission 15 (6259365) |
|---|---|---|
| M0 (four items, one call) | not run (mission 13, 68bee5f: 266 s) | 251 s |
| M2 (five items, one call) | 135 s | 130 s |
| G1.1 | 385 s | 373 s |
| G1.2 | 174 s | 173 s |
| G1.3 | 546 s | 522 s |
| G1.4 | 1 s | 1 s |

No item printed FAIL; no M1 item is above 10 minutes, so no D-014 line was due
(decision 118 (b)). The synthetic source changed by U2 is read by every replay
and by the M0 store items; all pass on it.

## Models

`config/models.toml` as written (U4, 0260f0c; `tests/fixtures/config/models.toml`
the same bytes):

```toml
base_url = "https://api.tokenfactory.nebius.com/v1/"
checked = "2026-10-16"
source = "Nebius Token Factory quickstart, https://docs.tokenfactory.nebius.com/quickstart (the base_url its OpenAI client sample sets), read on 2026-10-16"
verified = false

[[model]]
id = "openai/gpt-oss-120b"
maker = "OpenAI"
cutoff = "2024-06"
cutoff_basis = "stated"
pool = true
checked = "2026-10-11"
source = "SPEC.md section 17 (Worker models on Nebius Token Factory), from the provider's catalog https://tokenfactory.nebius.com/api/public/models_info"
verified = false

[[model]]
id = "MiniMaxAI/MiniMax-M3"
maker = "MiniMax"
cutoff = "2026-01"
cutoff_basis = "stated"
pool = true
checked = "2026-10-11"
source = "SPEC.md section 17 (Worker models on Nebius Token Factory), from the provider's catalog https://tokenfactory.nebius.com/api/public/models_info"
verified = false

[[model]]
id = "nvidia/nemotron-3-super-120b-a12b"
maker = "NVIDIA"
cutoff = "2026-02"
cutoff_basis = "stated"
pool = true
fallback = "nvidia/Nemotron-3_5-Lightning"
checked = "2026-10-11"
source = "SPEC.md section 17 (Worker models on Nebius Token Factory; the post-training cutoff), from the provider's catalog https://tokenfactory.nebius.com/api/public/models_info"
verified = false

[[model]]
id = "nvidia/Nemotron-3_5-Lightning"
maker = "NVIDIA"
cutoff = "2026-05"
cutoff_basis = "stated"
pool = false
checked = "2026-10-11"
source = "SPEC.md section 17 (Worker models on Nebius Token Factory; the post-training cutoff), from the provider's catalog https://tokenfactory.nebius.com/api/public/models_info"
verified = false
```

(The file's header comment is omitted above.) The cutoff date each gives, by
R-14 (a stated month's last day), as `config check` prints it and as
`tests/test_config.py::test_models_are_spec_17s_records_unverified` computes
it on its own:

| Model | Maker | Pool | cutoff | Cutoff date |
|---|---|---|---|---|
| openai/gpt-oss-120b | OpenAI | yes | 2024-06 | 2024-06-30 |
| MiniMaxAI/MiniMax-M3 | MiniMax | yes | 2026-01 | 2026-01-31 |
| nvidia/nemotron-3-super-120b-a12b | NVIDIA | yes, fallback Nemotron-3_5-Lightning | 2026-02 | 2026-02-28 |
| nvidia/Nemotron-3_5-Lightning | NVIDIA | no (fallback only) | 2026-05 | 2026-05-31 |

Where `base_url` came from: the provider's quickstart page
https://docs.tokenfactory.nebius.com/quickstart, read on 2026-10-16 by U4 (the
base URL its OpenAI client sample sets), `verified = false`. No code holds a
default base URL; `OpenAICompatProvider` takes it from its caller and refuses
an empty one. The model ids, makers and cutoffs are SPEC §17's, which cites the
provider's catalog; none was read from the catalog in this mission. `config
check` lists `base_url` and the four cutoffs among its 173 unverified values.
`config/run.toml` `[workers]`: `claude_fallback = false`,
`request_timeout_seconds = 300.0` (the project's own choices).

## Claude worker flags

`ClaudeWorkerProvider` (`src/discotrade/workers/providers.py`,
`claude_arguments`) runs the configured executable with:

```
--bare -p --output-format json --max-turns 1 --tools "" --permission-mode dontAsk --model <model>
```

the prompt on standard input, and an environment without `NEBIUS_API_KEY`
(and without `DATABENTO_API_KEY`). Where they were read (U3's body): every
flag but `--max-turns` from the builder's installed `claude --help`, Claude
Code 2.1.300 (`claude --version` prints `2.1.300 (Claude Code)` at this tip);
`--max-turns 1` is not in that help and is taken from SPEC §17's coordinator
line. The reply fields it reads (`result`, `usage.input_tokens`,
`usage.output_tokens`, the keys of `modelUsage` as the version string,
`is_error`) were not read from that binary. The tests run it only against a
fake `claude` written by the test.

## Generation

One fixture day on `test_synth`, produced for this report by a throwaway script
under /tmp (not committed) that does what `tests/test_workers_generate.py`
does: a copy of `tests/fixtures/config` with the production
`config/thresholds.toml`, `bars fetch` in-process at `--as-of
2019-07-25T00:00:00+00:00` into a state directory under /tmp, the fixture
pool with every model listed, the trading ordinal 29 for 2019-07-15 (so
`pool[(29 + 0) mod 3]`, `nvidia/nemotron-3-super-120b-a12b`), cell
trend/short, the test file's brief, `ScriptedProvider` over
`tests/fixtures/responses/<scenario>`, the child-process backend with its fork
server; no network, no real provider, no key.

Scenario `valid` — `ledger/test_synth/calls.jsonl`, verbatim:

```
{"attempt":1,"call":"cbe1f010c3ef5","cell":"trend/short","date":"2019-07-15","model":"nvidia/nemotron-3-super-120b-a12b","outcome":"trial","response":"responses/test_synth/2019-07-15/cbe1f010c3ef5.json","tokens_in":3463,"tokens_out":219}
```

Scenario `invalid_then_valid` (a fresh state) — `calls.jsonl`, verbatim:

```
{"attempt":1,"call":"cbe1f010c3ef5","cell":"trend/short","date":"2019-07-15","model":"nvidia/nemotron-3-super-120b-a12b","outcome":"invalid:activity","response":"responses/test_synth/2019-07-15/cbe1f010c3ef5.json","tokens_in":3463,"tokens_out":222}
{"attempt":2,"call":"cb2842315233c","cell":"trend/short","date":"2019-07-15","model":"nvidia/nemotron-3-super-120b-a12b","outcome":"trial","response":"responses/test_synth/2019-07-15/cb2842315233c.json","tokens_in":3765,"tokens_out":219}
```

The stored response file (`responses/test_synth/2019-07-15/cbe1f010c3ef5.json`
of `valid`, 16,432 bytes) has the keys `attempt`, `call`, `cell`, `date`,
`messages`, `model`, `model_version`, `raw`, `text`, `tokens_in`,
`tokens_out` (decision 126 (c)'s eleven); `messages` is the one prompt
message, `model_version` is `scripted`, `raw` is the scripted provider's
`{"file": "0001.md", "text": ...}`. Each call row has decision 62's nine keys.
In both runs the generation returned a candidate.

## Decisions 119 and 121 to 126: the tests that hold them

- **119** (REVIEW-14 should-fix 1, notes 3, 4, 7) — (a)
  `tests/test_workers_parse.py::test_a_fence_line_after_the_last_block_is_no_description`,
  with every existing parser test unchanged; (b)
  `tests/test_workers_registry.py::test_a_cut_on_a_space_leaves_no_trailing_space`
  and the changed `tests/test_workers_prompt.py::test_the_brief_is_sanitized_and_cut_at_the_production_cap`;
  (c) `tests/test_workers_profile.py::test_a_contract_change_with_no_roll_record_is_refused`;
  (d) no test: `tests/conftest.py`'s `mixed_ran_template` (e404e00).
- **121** (the synthetic source's cache) — `tests/test_synth_cache.py`:
  `test_a_span_fetched_day_by_day_with_the_cache_stores_what_one_fetch_without_it_stores`,
  `test_a_changed_seed_in_a_copied_configuration_gives_another_series_in_the_same_process`,
  `test_a_changed_trusted_from_in_a_copied_configuration_gives_another_series`,
  `test_an_equal_record_on_a_new_source_is_served_without_building_the_series_again`;
  and every existing test unchanged, gate M0 and the M1 items above.
- **122** (the providers, L3 offline) — `tests/test_workers_providers.py`:
  `test_scripted_lists_the_models_sorted_with_the_slash_restored`,
  `test_scripted_returns_each_models_files_in_order_from_its_cursor`,
  `test_scripted_continues_from_a_given_start`,
  `test_scripted_counts_tokens_by_characters_over_four_and_reports_scripted`,
  `test_scripted_raises_provider_error_when_a_models_files_are_used_up`,
  `test_scripted_a_model_without_a_directory_is_a_provider_error`,
  `test_openai_compat_sends_model_messages_and_max_tokens_and_reads_the_reply`,
  `test_openai_compat_lists_the_models`,
  `test_openai_compat_failures_are_provider_errors_naming_model_and_kind_without_key`,
  `test_openai_compat_list_models_failures_are_provider_errors`,
  `test_openai_compat_list_models_malformed_data_is_a_provider_error`,
  `test_openai_compat_holds_the_key_in_no_attribute`,
  `test_openai_compat_without_a_key_is_refused_naming_the_key`,
  `test_openai_compat_with_an_empty_base_url_is_refused_naming_it`,
  `test_openai_compat_from_the_environment_reads_the_key_there`,
  `test_claude_worker_passes_the_flags_the_prompt_on_stdin_and_no_worker_key`,
  `test_claude_worker_sends_several_messages_as_one_labelled_prompt`,
  `test_claude_worker_failures_are_provider_errors`,
  `test_claude_worker_timeout_is_a_provider_error`,
  `test_claude_worker_another_model_is_a_provider_error`,
  `test_only_providers_imports_httpx_or_starts_a_process_under_workers`;
  `tests/test_doctor.py`:
  `test_live_workers_without_the_key_prints_one_line_exits_1_no_request`,
  `test_live_workers_without_models_toml_prints_one_line_exits_1_no_request`,
  `test_live_workers_with_an_empty_base_url_prints_one_line_exits_1_no_request`,
  `test_live_workers_prints_the_pool_against_the_providers_list`,
  `test_live_workers_reports_a_model_the_provider_does_not_list`;
  `tests/test_offline.py` (`SUBPROCESS_FILES` lists `providers.py`).
- **123** (`config/models.toml`, `[workers]`) — `tests/test_config.py`:
  `test_last_day_of_month_reading`, `test_models_are_spec_17s_records_unverified`,
  `test_fixture_models_hold_the_same_records`, `test_models_refusals`,
  `test_models_empty_pool_refused`, `test_models_release_date_is_used_as_is`,
  `test_models_empty_base_url_loads`,
  `test_models_unverified_lists_base_url_and_each_cutoff`,
  `test_models_records_are_frozen`, `test_run_workers_table`,
  `test_run_without_a_workers_table_still_loads`, `test_run_workers_refusals`;
  `tests/test_config_check.py`: `test_config_check_lists_the_models_cutoff_dates`,
  `test_config_check_fails_on_a_bad_models_file`,
  `test_config_check_refuses_claude_fallback_without_a_claude_worker` (and the
  changed listing test); `tests/test_config_history.py::test_frozen_map_covers_models`.
- **124** (the pool) — `tests/test_workers_pool.py`:
  `test_production_thresholds_as_read`, `test_the_fixture_pool_is_the_configs`,
  `test_trading_ordinal_counts_trading_days_from_the_epoch`,
  `test_rotation_over_three_models_for_20_trading_days`,
  `test_a_missing_model_is_replaced_by_its_fallback`,
  `test_a_missing_model_without_a_fallback_is_skipped_with_the_notice`,
  `test_a_missing_model_whose_fallback_is_missing_too_is_skipped`,
  `test_a_failed_list_read_makes_no_call`, `test_an_empty_pool_makes_no_call`,
  `test_a_model_above_the_rate_over_a_full_window_is_removed_for_good`,
  `test_at_the_rate_is_not_above_it`, `test_a_window_not_yet_full_removes_nothing`,
  `test_provider_error_and_budget_rows_are_not_counted`,
  `test_a_duplicate_is_counted_and_is_not_a_failure`,
  `test_a_removed_fallback_is_not_used`, `test_a_copied_fail_window_changes_the_outcome`,
  `test_a_copied_fail_rate_changes_the_outcome`,
  `test_the_cell_rule_with_the_flag_false_logs_the_notice_once`,
  `test_the_cell_rule_with_the_flag_true_serves_the_cell_by_claude_from_the_next_day`,
  `test_the_same_rows_give_the_same_answers_twice`,
  `test_pool_imports_nothing_that_reaches_the_network_or_a_secret`.
- **125** (the coordinator) — `tests/test_coordinator.py`:
  `test_the_thresholds_are_the_production_values`,
  `test_cell_status_has_a_cell_counts_and_one_flag_only`,
  `test_two_states_differing_only_in_scores_give_identical_inputs`,
  `test_the_registry_is_every_live_and_dormant_line_by_cell_then_id`,
  `test_the_cell_statuses_and_the_weak_flag`,
  `test_the_window_edge_is_the_thresholds_value`,
  `test_the_offered_cells_are_those_with_a_free_slot_or_weak_in_cell_order`,
  `test_an_empty_state_offers_every_cell_weak`,
  `test_the_scripted_choice_is_the_fewest_live`,
  `test_a_tie_goes_to_the_lowest_cell_index`,
  `test_the_scripted_brief_names_the_cell_and_asks_for_a_new_approach`,
  `test_the_scripted_digest_and_run_log_line_are_templates_of_their_inputs`,
  `test_an_offered_choice_is_kept`,
  `test_a_choice_not_offered_falls_back_to_the_scripted_one_with_a_notice`,
  `test_a_cell_the_track_does_not_have_falls_back_too`,
  `test_no_offered_cell_means_no_generation_and_no_call`,
  `test_the_brief_arrives_sanitized_and_capped`,
  `test_the_cap_is_read_from_the_thresholds`.
- **126** (the day's generation) — `tests/test_workers_generate.py`:
  `test_the_seeds_day_pool_and_thresholds_are_the_ones_written_here`,
  `test_each_fixture_response_s_block_is_a_strategy_file_byte_for_byte`,
  `test_the_call_id_is_c_and_twelve_hex_digits_of_the_sha256_of_track_day_attempt`,
  `test_generate_imports_nothing_that_reaches_the_network_or_a_secret`,
  `test_a_valid_response_gives_a_candidate_and_one_trial_row`,
  `test_rows_go_to_the_ledger_location_given_and_no_trial_is_written`,
  `test_the_response_file_read_back_is_what_the_provider_returned`,
  `test_an_invalid_then_a_valid_response_give_two_rows_and_the_retry_holds_the_error`,
  `test_a_duplicate_then_a_second_failure_give_two_rows_and_the_retry_names_the_approach`,
  `test_a_parse_failure_is_stored_in_full_before_it_is_refused`,
  `test_a_budget_reached_makes_no_call_and_writes_a_budget_row_and_the_event`,
  `test_the_budget_counts_the_day_s_earlier_tokens_staged_rows_and_attempt_1_included`,
  `test_a_day_whose_response_files_exist_makes_no_provider_call_and_gives_the_same_rows`,
  `test_a_provider_error_writes_one_row_and_no_retry`,
  `test_the_same_inputs_give_the_same_bytes_twice`,
  `test_an_empty_pool_makes_no_call`,
  `test_one_fixture_response_runs_through_the_container_backend` (container);
  `tests/test_return_readers.py` (decision 92's audit finds no reader in
  `generate.py`).

## What the tests prove

- Parser and sanitizer (U1): REVIEW-14's example and a block followed by a
  fence line of another language, a bare fence, an indented fence and a
  four-backtick line parse to `no_description`, the next line not tried; a
  line with backticks not at its start is still a description;
  `sanitize('ab cd', 3) == 'ab'`; a store built in the test with SYNA's roll
  record inside W removed, or naming another contract, raises `ProfileError`.
- Synthetic cache (U2): on `test_synth`, 15 day-by-day fetches across a roll
  store bar files, index and roll records byte-identical to one fetch with the
  cache cleared; a changed seed or `trusted_from` in a copied configuration
  gives another series in the same process; a 22-day replay's state is
  identical outside `.git/` at the parent and at U2.
- Providers (U3): the scripted corpus's order, cursor, start, token rule
  (`ceil(characters / 4)`) and exhaustion; `OpenAICompatProvider` through
  `httpx.MockTransport` only: request body, reply fields, model list, each
  failure kind a `ProviderError` with no key in any error text, `raw`, repr,
  string attribute or DEBUG log record; refusals without a key or base URL;
  `ClaudeWorkerProvider` against a fake `claude`: the flags above, the prompt
  on stdin, no worker key in its environment, each failure kind; under
  `src/discotrade/workers/` only `providers.py` names `httpx`, a process call
  or a socket; `doctor --live workers` without the key prints one line, exits
  1 and makes no request.
- Models and pool (U4): the four records in both files and their cutoff dates
  by the test's own R-14 reading; the refusals listed above; rotation over 20
  `test_synth` trading days equals `pool[(ordinal + c) mod 3]` computed by the
  test; fallback, skip and the notices; 11 of 20 failures remove a model for
  good with one `model_removed` alert, 10 of 20 do not; `provider_error` and
  `budget` rows not counted; thresholds read at production values and changed
  by copies; windows built from a `calls.jsonl` the test writes.
- Coordinator (U5): two states differing only in scores give identical
  inputs, registry lines and scripted briefs; `CellStatus` has exactly
  `cell`, `live`, `free`, `weak`; the weak flag's window edge from the
  thresholds; the fewest-live choice and the lowest-index tie; a choice not
  offered falls back with one notice; the brief sanitized and capped.
- Generation (U6): on `test_synth` 2019-07-15 trend/short, a valid response
  gives a candidate and one row; invalid then valid and duplicate then
  invalid give two rows and the retry's messages; a parse failure is stored
  in full before parsing; the budget stops a call with a `budget` row and a
  `token_budget` event, counting the day's earlier tokens; a day whose
  response files exist is replayed without a call to the same bytes; a
  provider error writes one row and no retry; every row has decision 62's
  keys; one response runs through the container backend.
- Regression: gates M0, M2 and M1 G1.1 to G1.4 pass at 6259365;
  `./scripts/check` green three times there.
- Frozen files: `git diff --stat 301a5c7 6259365` of `config/instruments`,
  `config/tracks`, `config/calendars`, `config/thresholds.toml`,
  `config/run.toml`, `tests/fixtures/config_frozen.json`,
  `tests/fixtures/config`, `tests/gates` and `tests/fixtures/rejected` shows
  only `config/run.toml` (+6, the `[workers]` table),
  `tests/fixtures/config/run.toml` (+6, the same), the new
  `tests/fixtures/config/models.toml` (+54) and
  `tests/fixtures/config_frozen.json` (+39, the new `config/models.toml`
  entry); every line is an addition.

## NOT PROVEN

- No real provider, model or `claude` binary was called: live checks L3 (the
  pool listed by the provider) and L4 are not run. Every test uses the
  scripted corpus, `httpx.MockTransport` or a fake `claude`.
- The base URL, the model ids and the cutoffs are from SPEC §17 and public
  pages (the provider's quickstart, read 2026-10-16; the catalog SPEC §17
  cites, not read here), not verified: every value of `config/models.toml` is
  `verified = false`.
- The Claude worker's flags are those of the builder's installed `claude`
  (Claude Code 2.1.300, `claude --help`), and `--max-turns 1` is SPEC §17's;
  they match a real binary only as far as that, and the JSON reply fields
  read are not taken from that binary.
- The scripted provider's token counts are an estimate by rule
  (`ceil(characters / 4)`), not a tokenizer; the budget tests prove the
  budget arithmetic on those counts only.
- Nothing of this mission is called from `run-day` or `replay`, so retry,
  storage and budget inside a day, the pool's windows over real call rows and
  the coordinator in the day are step S3.2b's to prove.
- The speed figures are from the builder's machine (four cores, varying
  load). U2's cache gave no speed gain beyond noise (1.598 vs 1.623 s per
  replay day); `./scripts/check` is above decision 114's 12 minutes at the tip
  (828 to 848 s; D-013 open). U2's byte identity is shown on the spans and
  records its tests and the 22-day replay cover.
- The generation section above is from one throwaway run per scenario on one
  day, cell and track; the script was not committed.
- What remains of FINAL-REPORT-14's NOT PROVEN: the profile's statistics are
  decision 115's choice, their use to a worker not tested; anonymization hides
  names and units only, not a distinctive path; the leak check covers the
  symbols, venues, contract names and date patterns it lists and the prompts
  the tests build, and a description's content is not checked; no prompt has
  been sent to a model (now step S3.2b's and L3's); G2.3's gate file still
  judges the mount against the job, the content check against the store
  (count and last close only) proven outside the gate until the owner rules;
  the prompt sample of FINAL-REPORT-14 has no recorded registry state;
  `trusted_hashes`' cache does not hash again a same-stat rewrite;
  `BUILTIN_EXCEPTIONS` checked on Python 3.14.6 only; and everything
  FINAL-REPORT-14 carried from FINAL-REPORT-13 and earlier (the container a
  boundary only as docker 29.1.3 and this kernel make it; the rejection suite
  and static list a floor; process count and CPU by inspection only; call-time
  limits load-dependent; base image and packages by their pins; error-text
  checks on produced texts only; the subprocess backend no boundary; the
  grid's adjusted figure (O-4); G2.5's kill grace and memory bound; cgroup v2
  only; `atexit` not shown for every exit; G1.3's margin under 10 minutes
  load-dependent (522 s here; D-014); no container day loop on a non-synthetic
  track; the audit's blind shapes and REVIEW-11 note 7's rest, to S4.1;
  `backtest` loading a strategy once per subject, decision 107; decision 98's
  tests on one W). Closed by this mission: a fence line is no longer taken as
  a description (119 (a)); a sanitized text no longer ends in a space (119
  (b)); the profile's roll-record refusal is tested (119 (c)).
- Numbers from outside the project added in this mission: the four model
  records and `base_url` of `config/models.toml` (U4), each with `checked`,
  `source` and `verified = false`; not proven from a primary source.

## Findings filed and answered

- **HF-010** (stale worktrees): status line appended at U0, ccaf429 (REVIEW-14
  note 11, decision 120 (a)). Open, for the hands Project.
- **HF-011** (prefixes missing from the review protocol's skip list): status
  line appended at U0, ccaf429, naming `report:` of f5f43ee (REVIEW-14 note 12,
  decision 120 (b)). Open, for the hands Project. This report's commit carries
  the same `report:` prefix as f5f43ee.
- **HF-012** (filed U0, ccaf429; decision 120 (c)): the review protocol does not
  say whether per-commit reviewers may run at once. Open, for the hands
  Project.
- **D-013** (`./scripts/check` time): taken by U2 under decision 121; times
  line at U2 (aeed087: 791 s parent, 801 to 807 s commit, 1.598 vs 1.623 s per
  replay day) and at U7 (this commit: 848, 828, 838 s at the tip). The cache
  did not cut the time. **Open** (decision 121: until a mission's check is
  under 12 minutes three times).
- **D-014** (G1.3 against O-3's 10 minutes): no line due; G1.3 took 522 s at
  the tip. Open, for the owner.
- D-015, HF-008 and HF-009 remain open as FINAL-REPORT-14 left them. No other
  finding was filed in this mission.

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-14 should-fix 1 (a fence line after the last block taken as the description) | U1, decision 119 (a): the first non-empty line after the last block beginning with three backticks gives `no_description`, the next line not tried | e404e00 |
| REVIEW-14 note 3 (`sanitize` can leave a trailing space) | U1, decision 119 (b): stripped again after the cut; the prompt test's cap assertion changed as 119 (b) says | e404e00 |
| REVIEW-14 note 4 (the profile's roll-record refusal untested) | U1, decision 119 (c): `test_a_contract_change_with_no_roll_record_is_refused` | e404e00 |
| REVIEW-14 note 7 (`mixed_ran_template` without `GIT_ALLOW_PROTOCOL=file`) | U1, decision 119 (d): set in a `MonkeyPatch` context, as `synth_committed_template` does | e404e00 |
| REVIEW-14 note 11 (stale worktrees still registered) | U0, decision 120 (a): HF-010 status line | ccaf429 |
| REVIEW-14 note 12 (`report:` prefix not in the skip list) | U0, decision 120 (b): HF-011 status line | ccaf429 |
| REVIEW-14 note 13 (concurrency of per-commit reviewers) | U0, decision 120 (c): HF-012 filed | ccaf429 |
| Finding D-013 (the synthetic source's per-day cost) | U2, decision 121: the process cache, byte-identical stores, no speed gain; times lines at U2 and U7; D-013 open | aeed087, this commit |

## Acceptance

- `./scripts/check` green three times at the pushed tip 6259365 (848, 828,
  838 s; mission 14's tip 784 to 830 s), 0 skipped, so the `container` tests
  ran. Met.
- `./scripts/gate M0`, `./scripts/gate M2` and `./scripts/gate M1 G1.1` to
  `G1.4` at 6259365 print their PASS lines; outputs and times above beside
  mission 14's; no M1 item above 10 minutes, so nothing due under D-014. Met.
- A fence line after the last block is no description; a sanitized text ends
  in no whitespace. Met (U1).
- The synthetic source stores byte-identical files with its cache, and a
  changed record generates again. Met (U2).
- Three providers behind one protocol, tested with a scripted corpus, a mock
  transport and a fake `claude`; no key in any error text, stored field or
  log line the tests read. Met (U3).
- `config/models.toml` holds SPEC §17's three pool models and the NVIDIA
  fallback with `verified = false`, in the frozen map; the pool rotates by
  trading-day ordinal plus cell index, falls back per maker, removes a failing
  model for good with a `model_removed` event, and derives its windows from
  `calls.jsonl`. Met (U4).
- The coordinator's input has no score (the property test), the scripted
  choice and the out-of-list fallback behave, the brief is sanitized and
  capped. Met (U5).
- The day's generation makes at most two calls, stores every response before
  parsing, replays a stored response without a call, stops at the token budget
  with a `budget` row and a `token_budget` event, and writes one call row per
  attempt with decision 62's keys. Met (U6).
- No file under `tests/gates/` or `tests/fixtures/rejected/` changed; the
  frozen files' diff against the base is additions only (above). Met.
- Every unit commit's body lists its files; U0 is `plan:`. Met.
- No test uses the network, a secret or the wall clock; no state or job
  directory inside the repository (`git status` clean after the runs but for
  this commit's files); no test builds the image. Met as the units' tests and
  the check show.
- This file has `## Regression gates`, `## Models`, `## Claude worker flags`,
  `## Generation`, NOT PROVEN and the review-items table.

VERDICT: mission 15 finished
