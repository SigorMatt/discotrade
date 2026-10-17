VERDICT: mission 17 finished

# FINAL REPORT — mission 17 (roadmap step S3.2b; closes milestone M3)

Brief: `meta/BUILDER-17-PROMPT.md`. Base af85e55 (`plan: mission 17 kit (S3.2b,
workers in the day, scoring on T, gate M3)`). Decisions:
`meta/decisions/decisions-2026-10-16-m17.md` (132 to 140), with items 1 to 131
and the owner's files (O-11, O-13, O-16 to O-20, O-22) still binding. This
mission closes milestone M3: `./scripts/gate M3` printed `gate M3: PASS`, and
gates M2, M1 (item by item) and M0 were run again as a regression check
(decision 132 (b)). Container runtime: docker; `uv run discotrade sandbox build`
at the tip printed `sandbox build: present, nothing built` and
`discotrade-sandbox:3b7d75c39621`.

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | 1a04ee1 | `plan:` the plan, checkpoint, journal; FINDINGS.md: D-016 status (answered, 134 (e)); HF-010, HF-011, HF-012 status lines (134 (f)) |
| U1 | 014f06a | `src/discotrade/daily.py`: `score_on_t`, a generated candidate scored on T through `validation.sequence.dry_run_and_grid` with a context whose window is T, into a `lifecycle.Candidate`; `tests/fixtures/return_readers.toml`: `discotrade.daily score_on_t` as `producer`; `tests/test_daily_score_t.py` (7 tests) (decision 135) |
| U2 | db29997 | `src/discotrade/daily.py`: steps 3 to 5 in `run_day` with a provider passed in by the caller; `tests/test_daily_generation.py` (11 tests); a D-013 times line (decision 136) |
| U3 | 545e7ec | `src/discotrade/cli.py`, `src/discotrade/replay.py`: `--provider` (`none`, `scripted:<dir>`, `openai`) and `--coordinator scripted` on `run-day` and `replay`, the provider built once per command, the scripted cursor's `start` counted from the stored responses; one docstring sentence of `src/discotrade/workers/providers.py`; `tests/test_cli_provider.py` (17 tests); a D-013 times line (decision 137) |
| U4 | 446b0a8 | `tests/fixtures/worker_corpus/`: 16 strategy files, `m3/` (27 responses over the three pool models), `m3_pool/` (21 responses), `manifest.toml`; `tests/test_worker_corpus.py` (6 tests, under 1 s); a D-013 times line and an HF-006 status line (decision 138) |
| U5 | 8d54f9f | `gate:` `tests/gates/m3_harness.py`, `test_g3_1_candidates.py`, `test_g3_2_pool.py`, `test_g3_3_prompts.py` (18 gate tests); `tests/test_gate_script.py`'s two "without gate tests" cases moved from M3 to M4; FINDINGS.md: D-017, a D-013 and a D-014 times line (decision 139) |
| U6 | this commit | this report; a D-013 times line |

Meta commits: 7e82bf0 (U0 done), 8edae6e (U1), 0de1a6a (U2), d67eedb (U3),
45dc893 (U4), 7f18206 (U5). Each unit commit's body lists its files. Product
files changed in the mission: `src/discotrade/daily.py`, `src/discotrade/cli.py`,
`src/discotrade/replay.py` and one docstring sentence of
`src/discotrade/workers/providers.py`.

## Speed

`./scripts/check` wall time on the builder's machine (four cores, shared), each
run its own foreground call with a 20-minute timeout:

| Where | Runs |
|---|---|
| mission 16's tip ef4548f (FINAL-REPORT-16) | 841, 834, 837 s |
| U1 014f06a | 844, 838, 834 s |
| U2 db29997 | 867, 918, 923 s |
| U3 545e7ec | 925, 928, 963 s |
| U4 446b0a8 | 1281, 1024, 1079 s (the first passed the 20-minute timeout and was moved to the background by the harness; HF-006 status line) |
| U5 (45dc893 + the U5 files, uncommitted) | 1116, 1054, 1180 s (after one red run of 1092 s, fixed in U5) |
| tip 7f18206 (U6, before this commit) | **1021, 1043, 1024 s**, each `check: green` |

At the tip each run printed `2364 passed, 200 deselected` (0 skipped, so the
`container` tests ran on discotrade-sandbox:3b7d75c39621), `config check: ok, 173
unverified values` and `check: green`; pytest 1017.75 s, 1040.63 s, 1021.06 s.
Outputs kept in `meta/drafts/m17-tip-check-<n>.txt` (first line
`git rev-parse HEAD`, last line the wall time). The mission added 41 tests to the
check (2323 at mission 16's tip). Every tip run is above HF-006's 15 minutes, so
a D-013 times line is appended by this commit; none passed the 20-minute cap.
The rise is not measured per test: U2's module takes about 36 s alone, U3's
about 50 s, U1's about 12 s; the remainder varied with the shared machine's load
(U4's runs at load about 2.2, the tip's at about 1.5 to 1.9).

## Gate M3

At HEAD 45dc893e8319f5db6b5ae0cf2590c814e421bc87 with U5's four gate files and
`tests/test_gate_script.py` in the working tree uncommitted, after
`./scripts/check` was green three times there. The pushed U5 commit 8d54f9f
differs from what ran only by its `meta/findings/FINDINGS.md` lines; the tip
7f18206 adds to 8d54f9f only `meta/CHECKPOINT.md`, `meta/journal.md` and
`meta/plan.md` (`git diff --stat 45dc893 7f18206` lists, outside `meta/`, only
the five test files that ran). Each call its own foreground call with a
20-minute timeout.

`uv run discotrade sandbox build` — wall 0.7 s

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
sandbox build: present, nothing built
discotrade-sandbox:3b7d75c39621
wall .723189859 s
```

`./scripts/gate M3` — exit 0, wall 555 s (first run of M3; no earlier time)

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
G3.1 PASS 3 passed in 217.73s (0:03:37)
G3.2 PASS 8 passed in 174.56s (0:02:54)
G3.3 PASS 7 passed in 160.68s (0:02:40)
gate M3: PASS
wall 555.311588297 s
```

Each item's time (pytest, as the gate prints it): G3.1 218 s, G3.2 175 s, G3.3
161 s, each under DESIGN §18.2's 15 minutes.

## Gate M2

`./scripts/gate M2` — exit 0, wall 142 s (FINAL-REPORT-15: 130 s)

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
G2.1 PASS 36 passed in 45.76s
G2.2 PASS 3 passed in 25.32s
G2.3 PASS 8 passed in 3.61s
G2.4 PASS 9 passed in 42.86s
G2.5 PASS 5 passed in 21.09s
gate M2: PASS
wall 141.649860501 s
```

## Gate M1

Four calls, one per item (O-2).

`./scripts/gate M1 G1.1` — exit 0, wall 450 s (FINAL-REPORT-15: 373 s)

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
G1.1 PASS 6 passed, 1 warning in 449.77s (0:07:29)
gate M1 G1.1: PASS
wall 450.487838348 s
```

`./scripts/gate M1 G1.2` — exit 0, wall 204 s (FINAL-REPORT-15: 173 s)

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
G1.2 PASS 4 passed in 203.50s (0:03:23)
gate M1 G1.2: PASS
wall 204.365573749 s
```

`./scripts/gate M1 G1.3` — exit 0, wall 542 s (FINAL-REPORT-15: 522 s)

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
G1.3 PASS 10 passed in 541.09s (0:09:01)
gate M1 G1.3: PASS
wall 541.863452386 s
```

`./scripts/gate M1 G1.4` — exit 0, wall 1 s (FINAL-REPORT-15: 1 s)

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
G1.4 PASS 15 passed in 0.58s
gate M1 G1.4: PASS
wall 1.158769346 s
```

No M1 item above 10 minutes; G1.3's time is recorded in a D-014 times line (U5).

## M0 still passes

`./scripts/gate M0` — exit 0, wall 247 s (FINAL-REPORT-15: 251 s)

```
45dc893e8319f5db6b5ae0cf2590c814e421bc87
G0.1 PASS 62 passed in 58.67s
G0.2 PASS 7 passed in 89.55s (0:01:29)
G0.3 PASS 13 passed in 95.74s (0:01:35)
G0.4 PASS 4 passed in 0.73s
gate M0: PASS
wall 247.077789143 s
```

| Gate | FINAL-REPORT-15 | This mission |
|---|---|---|
| M3 (three items, one call) | — | 555 s |
| M2 (five items, one call) | 130 s | 142 s |
| G1.1 | 373 s | 450 s |
| G1.2 | 173 s | 204 s |
| G1.3 | 522 s | 542 s |
| G1.4 | 1 s | 1 s |
| M0 (four items, one call) | 251 s | 247 s |

## Corrections

REVIEW-16 should-fix 1 (decision 133). Commit bodies are not rewritten.

(a) 6e3caa5's body (mission 16 U1) says: "The status and wrong-type cases
already passed before the change; the others were seen to fail first." That is
wider than what was seen. Six of its 22 new tests pass at 6e3caa5's parent:

- the three cases the body names (as REVIEW-16 identifies them):
  `tests/test_workers_providers.py::test_openai_compat_complete_errors_have_no_cause_and_no_context[status]`,
  `tests/test_workers_providers.py::test_openai_compat_list_models_errors_have_no_cause_and_no_context[status]`
  and the wrong-type case
  `tests/test_workers_providers.py::test_openai_compat_complete_errors_have_no_cause_and_no_context[content not text]`;
- `tests/test_doctor.py::test_live_workers_without_a_usable_key_never_calls_the_transport[unset]`;
- `tests/test_doctor.py::test_live_workers_without_a_usable_key_never_calls_the_transport[spaces]`;
- `tests/test_workers_providers.py::test_the_source_test_resolves_a_relative_import_of_key_env`.

None of the last three was seen to fail.

(b) The two doctor cases, run after each wrong change below. Each change was made
alone in a worktree at 7f18206 (`/tmp/m17-u6`, removed afterwards with `git
worktree remove`), not committed, and reverted. Both cases passed at the
unchanged tip.

| Wrong change in `key_present` (`src/discotrade/workers/providers.py`) | `[unset]` | `[spaces]` |
|---|---|---|
| true for any value that is set, blank included (`return KEY_ENV in os.environ`) | passed | passed |
| true always (`return True`) | passed | passed |

Neither case went red under either change. No wrong change was seen to turn
either case red. The reason is a later refusal that gives the same line and
exit status. When `key_present` lets an unset or blank key through,
`live_workers` reads the configuration and calls `openai_compat_from_env`. That
builds `OpenAICompatProvider`, whose `__init__` raises `ProviderError(no_key_message())`
when the key is empty or blank, before any client is made. The doctor catches it
and prints `doctor --live workers: FAIL: <the same no-key message>`. That is one
line on standard error, exit 1, and no transport call. This is exactly what the
two cases assert. So the cases hold the doctor's behaviour (one line, exit 1, no
request), not which check refuses.

(c) `test_the_source_test_resolves_a_relative_import_of_key_env` tests the source
test's own reader (its resolution of a relative `from ... import KEY_ENV`). No
wrong change of product code is meant to turn it red. No test changed for this
item.

## Corpus

Measured by a throwaway replay outside the repository (under `/tmp/m17u6`; the
script imports `tests/gates/m1_harness.py` and
reuses G3.1's computation from `tests/gates/test_g3_1_candidates.py`). The setup
is the gate configuration as `m3_harness.worker_replay` builds it:
`tests/fixtures/config/` copied, `thresholds_gate.toml` unchanged. It runs on
`test_synth` (seeds SYNA 101, SYNB 102, SYNC 103, SYND 104), with `init-state`
at 2019-06-03T00:00:00+00:00, then `replay` 2019-07-15 to 2019-08-09 (20
trading days), `--sandbox process --provider
scripted:/home/msi/git/discotrade/tests/fixtures/worker_corpus/m3 --coordinator
scripted`, in-process. Every response file served, in call-row order:

| day | cell | model | file | attempt | outcome | tokens in | tokens out | trial | admitted |
|---|---|---|---|---|---|---|---|---|---|
| 2019-07-15 | trend/short | nvidia/nemotron-3-super-120b-a12b | 0001.md (the injected description) | 1 | trial | 3463 | 225 | acb5c22a61f50 | yes |
| 2019-07-16 | trend/medium | MiniMaxAI/MiniMax-M3 | 0001.md | 1 | duplicate (of acb5c22a61f50, live) | 3506 | 233 | | |
| 2019-07-16 | trend/medium | MiniMaxAI/MiniMax-M3 | 0002.md | 2 | trial | 3826 | 249 | a4994474d24a8 | no (not_positive) |
| 2019-07-17 | trend/medium | nvidia/nemotron-3-super-120b-a12b | 0002.md | 1 | trial | 3523 | 231 | a1c276745013f | no (not_positive) |
| 2019-07-18 | trend/medium | openai/gpt-oss-120b | 0001.md | 1 | invalid:static | 3510 | 67 | | |
| 2019-07-18 | trend/medium | openai/gpt-oss-120b | 0002.md | 2 | trial | 3647 | 227 | a099d2d66b36e | no (not_positive) |
| 2019-07-19 | trend/medium | MiniMaxAI/MiniMax-M3 | 0003.md | 1 | trial | 3519 | 284 | af259d66912a2 | no (not_positive) |
| 2019-07-22 | trend/medium | nvidia/nemotron-3-super-120b-a12b | 0003.md | 1 | trial | 3517 | 238 | aca2e9f443bca | no (not_positive) |
| 2019-07-23 | trend/medium | openai/gpt-oss-120b | 0003.md | 1 | trial | 3512 | 234 | a46e3afb84da0 | no (too_few_trades) |
| 2019-07-24 | trend/medium | MiniMaxAI/MiniMax-M3 | 0004.md | 1 | trial | 3516 | 238 | a79e84496b76b | no (not_positive) |
| 2019-07-25 | trend/medium | nvidia/nemotron-3-super-120b-a12b | 0004.md | 1 | trial | 3519 | 241 | a10a1328e143e | no (not_positive) |
| 2019-07-26 | trend/medium | openai/gpt-oss-120b | 0004.md | 1 | trial | 3515 | 253 | a416a25613251 | no (not_positive) |
| 2019-07-29 | trend/medium | MiniMaxAI/MiniMax-M3 | 0005.md | 1 | trial | 3514 | 179 | af212b293bb64 | no (not_positive) |
| 2019-07-30 | trend/medium | nvidia/nemotron-3-super-120b-a12b | 0005.md | 1 | trial | 3511 | 210 | a64c9d59cf66a | no (not_positive) |
| 2019-07-31 | trend/medium | openai/gpt-oss-120b | 0005.md | 1 | trial | 3514 | 276 | adea6ff1dbcae | no (not_positive) |
| 2019-08-01 | trend/medium | MiniMaxAI/MiniMax-M3 | 0006.md | 1 | trial | 3506 | 255 | a1dabc87963ef | no (not_positive) |
| 2019-08-02 | trend/medium | nvidia/nemotron-3-super-120b-a12b | 0006.md | 1 | trial | 3508 | 201 | a47a12a570b4b | no (not_positive) |
| 2019-08-05 | trend/medium | openai/gpt-oss-120b | 0006.md | 1 | invalid:parse | 3510 | 48 | | |
| 2019-08-05 | trend/medium | openai/gpt-oss-120b | 0007.md | 2 | invalid:parse | 3652 | 139 | | |
| 2019-08-06 | trend/short | openai/gpt-oss-120b | 0008.md | 1 | invalid:activity | 3509 | 152 | | |
| 2019-08-06 | trend/short | openai/gpt-oss-120b | 0009.md | 2 | invalid:static | 3742 | 52 | | |
| 2019-08-07 | trend/short | MiniMaxAI/MiniMax-M3 | 0007.md | 1 | invalid:static | 3514 | 52 | | |
| 2019-08-07 | trend/short | MiniMaxAI/MiniMax-M3 | 0008.md | 2 | invalid:activity | 3639 | 157 | | |
| 2019-08-08 | trend/short | nvidia/nemotron-3-super-120b-a12b | 0007.md | 1 | invalid:parse | 3513 | 59 | | |
| 2019-08-08 | trend/short | nvidia/nemotron-3-super-120b-a12b | 0008.md | 2 | invalid:parse | 3662 | 45 | | |
| 2019-08-09 | trend/short | openai/gpt-oss-120b | 0010.md | 1 | invalid:static | 3509 | 37 | | |
| 2019-08-09 | trend/short | openai/gpt-oss-120b | 0011.md | 2 | invalid:parse | 3625 | 26 | | |

27 calls, 96001 tokens in and 4608 out in all (the scripted provider's
`ceil(characters / 4)`). Every one of the 27 corpus files of `m3/` is served
once; no `provider_error` row. 15 trials (nemotron 6, MiniMax 5, openai 4); one
admitted (acb5c22a61f50, which goes dormant on 2019-08-05; lifecycle rows
`candidate -> live` 07-15, `live -> dormant` 08-05). This agrees with U4's
measured table (446b0a8).

Pairwise |Pearson correlation| of the trials' held positions on W of the later
trial's day, concatenated over the basket in track order (G3.1's computation;
rows the later trial, columns the earlier, trial index = row order of the table
above). `corr_max` is 0.7.

```
           0     1     2     3     4     5     6     7     8     9    10    11    12    13
 1 07-16 0.035
 2 07-17 0.027 0.125
 3 07-18 0.013 0.240 0.555
 4 07-19 0.002 0.016 0.202 0.141
 5 07-22 0.013 0.004 0.202 0.137 0.276
 6 07-23 0.035 0.379 0.026 0.003 0.049 0.016
 7 07-24 0.086 0.330 0.395 0.510 0.156 0.089 0.028
 8 07-25 0.051 0.453 0.220 0.222 0.035 0.030 0.351 0.313
 9 07-26 0.025 0.037 0.228 0.105 0.023 0.015 0.062 0.080 0.089
10 07-29 0.007 0.005 0.039 0.029 0.014 0.005 0.007 0.067 0.027 0.005
11 07-30 0.002 0.058 0.609 0.394 0.206 0.188 0.005 0.384 0.198 0.205 0.001
12 07-31 0.040 0.150 0.391 0.181 0.014 0.052 0.041 0.119 0.173 0.200 0.019 0.254
13 08-01 0.014 0.038 0.439 0.320 0.411 0.222 0.018 0.219 0.079 0.123 0.006 0.372 0.121
14 08-02 0.022 0.001 0.027 0.057 0.030 0.013 0.003 0.048 0.041 0.027 0.233 0.085 0.002 0.036
```

Maximum 0.609: a64c9d59cf66a (2019-07-30, nemotron 0005.md) against a1c276745013f
(2019-07-17, nemotron 0002.md). 105 pairs.

Budget response of decision 138 (d) (`m3_pool/openai__gpt-oss-120b/0001.md`),
re-derived. The file has 212587 characters, so the scripted count is
`ceil(212587 / 4)` = 53147 tokens out. The production values in
`config/thresholds.toml` are `worker_tokens_per_day = 60000` and
`worker_max_output_tokens = 8000`, the same as `thresholds_gate.toml`. On
2019-07-15 attempt 1 costs tokens_in 3463 + tokens_out 53147 = 56610 (outcome
`invalid:static`). At the retry's check, 56610 + 8000 = 64610 > 60000. So a
`budget` row (attempt 2, no response, 0 tokens) and a `token_budget` alert are
written, and no second call is made. A one-day throwaway replay with `m3_pool/`
under `/tmp` printed exactly these rows: the alert detail was `day_tokens 56610,
max_output_tokens 8000, tokens_per_day 60000`. The removal day (2019-07-29) is
U4's measurement and G3.2's assertion; it was not repeated here.

## Day

Order in `run_day` (`src/discotrade/daily.py`, `_locked`). First: step 1 (fetch,
gap check; its events appended at once), the journal (step 2), the paper record
and exposure, then lifecycle steps 1 to 4, then a scripted `--candidates`
candidate if one was given. Then, only when the journal file was written by this
run, a provider is given, and step 1's gap check did not skip generation
(`_steps_3_to_5`):

1. Step 3: `coordinator.cell_statuses` and `coordinator.offered` for `D`, read
   from the state directory with rows dated before `D` (decision 136 (g)). No
   offered cell: return, with no model list read and no call. Then
   `config.load_models`, `pool.removed_models` over `calls.jsonl` rows before
   `D`, `provider.list_models()` read once (a `ProviderError` gives `None`), and
   `pool.day_pool`. An empty pool: return with no call.
2. Step 4: `coordinator.registry_lines` and `coordinator.choose` (the
   `ScriptedCoordinator` by default). No brief: return.
3. Step 5: `workers.generate.generate` on the day's backend, its call rows into
   staging and its responses stored at once. A candidate goes to `score_on_t`
   and `lifecycle.admit` into staging. Then `pool.day_events` over the staged
   call rows of `D` and before.

After that come rank persistence, the table, the move from staging and the
commit. A re-run of a journaled day runs none of steps 3 to 5.

The health events steps 3 to 5 can raise are appended to the health log as each
step returns them:
- from `pool.day_pool`: `model_skipped` (notice), `model_list_failed` (notice)
  and `pool_empty` (notice);
- from `coordinator.choose`: `coordinator_fallback` (notice);
- from `generate`: `token_budget` (alert);
- from `pool.day_events`: `model_removed` (alert) and `cell_needs_fallback`
  (notice).

Seconds per replay day on G3.1's 20 days, from the throwaway replays above, each
its own foreground call, replay alone timed:

- with `--provider scripted:<m3>`: 132.3 s, **6.62 s per day**;
- with `--provider none`: 28.7 s, **1.44 s per day**.

U4 measured 133 s to 359 s for the same provider replay under heavier load.

## Decisions 135 to 139: the tests that hold them

- **135** (scoring on T) — `tests/test_daily_score_t.py`:
  `test_the_seeds_window_thresholds_and_generated_candidate_are_the_ones_written_here`,
  `test_metrics_t_and_adjusted_t_equal_the_test_s_own_computation`,
  `test_t_is_run_in_one_positions_job_holding_no_bar_after_the_end_of_d`,
  `test_the_candidate_carries_every_field_of_decision_135_c`,
  `test_admit_writes_a_trial_row_and_an_approach_holding_the_model_version_and_cutoff`,
  `test_a_sandbox_error_on_t_is_raised_and_recorded_as_no_worker_outcome`,
  `test_the_scoring_function_is_registered_a_producer`; and the O-18 audit over
  `tests/fixtures/return_readers.toml`.
- **136** (steps 3 to 5 in the day) — `tests/test_daily_generation.py`:
  `test_the_seeds_ordinal_and_thresholds_are_the_ones_written_here`,
  `test_a_day_with_a_valid_response_writes_one_trial_call_one_trial_and_its_lifecycle_row`,
  `test_a_rerun_of_the_journaled_day_writes_nothing_and_makes_no_provider_call`,
  `test_a_day_failed_after_its_response_was_stored_runs_again_with_no_call_and_same_rows`,
  `test_every_health_event_of_steps_3_to_5_is_logged_on_a_day_that_fails_after_them`,
  `test_a_day_with_data_gaps_makes_no_call`,
  `test_a_day_with_no_offered_cell_makes_no_call`,
  `test_a_day_whose_model_list_fails_makes_no_call_and_logs_model_list_failed`,
  `test_a_cell_whose_only_live_approach_goes_dormant_on_d_is_weak_from_the_next_day`
  (136 (g)), `test_a_row_to_dormant_before_the_first_paper_day_flags_the_cell_weak`
  (136 (g)), `test_a_duplicate_on_attempt_1_gives_attempt_2_the_whole_list_of_messages`
  (136 (h)). Without a provider: the existing `tests/test_daily.py`,
  `tests/test_replay.py`, `tests/test_replay_candidates.py`, unchanged.
- **137** (the options and the cursor) — `tests/test_cli_provider.py`:
  `test_the_seeds_and_days_are_the_ones_written_here`,
  `test_a_scripted_replay_calls_the_provider_each_day`,
  `test_the_provider_is_built_once_per_command`,
  `test_two_replays_from_scratch_give_identical_states`,
  `test_a_replay_in_two_calls_equals_one_call`,
  `test_a_split_replay_after_a_day_failed_with_its_response_stored`,
  `test_run_day_continues_the_cursor_from_the_stored_responses`,
  `test_candidates_with_a_provider_is_a_usage_error`,
  `test_a_missing_scripted_directory_is_refused`,
  `test_a_missing_or_refused_models_toml_is_refused` (`missing`, `refused`),
  `test_openai_without_a_usable_key_never_calls_the_transport` (`unset`,
  `spaces`), `test_an_unknown_provider_is_a_usage_error` (`bogus`, `scripted:`,
  `Scripted:x`), `test_an_unknown_coordinator_is_a_usage_error`. With `none`: the
  existing `tests/test_cli.py`, `tests/test_replay.py`,
  `tests/test_replay_candidates.py`, unchanged.
- **138** (the worker corpus) — `tests/test_worker_corpus.py`:
  `test_every_listed_file_exists_and_every_file_is_listed`,
  `test_directories_named_after_the_pool_models`,
  `test_every_block_is_byte_identical_to_its_strategy_file`,
  `test_every_response_parses_as_the_manifest_says`,
  `test_strategies_listed_with_a_family_and_horizon_of_the_track`,
  `test_the_injected_description_and_the_budget_response`; the yield (138 (c), (d))
  is proven by the gate tests of 139.
- **139** (the gate) — `tests/gates/test_g3_1_candidates.py`:
  `test_span_seeds_and_configuration`,
  `test_at_least_ten_trials_from_the_three_makers`,
  `test_every_pair_of_trials_is_distinct_on_w_of_the_later_day`;
  `tests/gates/test_g3_2_pool.py`: `test_span_ordinals_and_seeds`,
  `test_every_call_row_model_is_the_rotation`,
  `test_no_cell_is_always_served_by_one_model`,
  `test_a_retry_carries_the_error_text`, `test_every_response_is_stored_in_full`,
  `test_production_values_of_the_pool_and_budget_keys`,
  `test_a_failing_model_is_removed_after_a_full_window`,
  `test_the_token_budget_ends_generation_and_the_day_is_journaled`;
  `tests/gates/test_g3_3_prompts.py`: `test_seeds_and_span`,
  `test_no_prompt_names_a_symbol_venue_contract_or_date`,
  `test_no_prompt_holds_a_raw_bar_or_a_score`,
  `test_the_labelling_differs_between_prompts`,
  `test_scaling_leaves_returns_and_scales_a_price_unit_field`,
  `test_the_injected_description_arrives_sanitized`,
  `test_a_raw_stored_description_is_sanitized_in_the_registry`; helper
  `tests/gates/m3_harness.py`. `tests/test_gate_script.py`'s
  `test_milestone_without_gate_tests_fails` and
  `test_one_item_without_gate_tests_fails` now use M4 (G4.2).

## What the tests prove

- Scoring on T (U1): on `test_synth` with the child-process backend, `metrics_t`
  (every §8 key) and `adjusted_t` (`ADJUSTED_KEYS`) equal the test's own
  computation from the evaluation's rows and the stored bars, without the
  forbidden helpers. The T job holds no bar after the end of `D`. The candidate
  carries every field of 135 (c). `lifecycle.admit` writes a trial row with
  exactly §10.2's keys, the model id, version `scripted` and the cutoff, and the
  admitted approach's `meta.json` holds them. A sandbox error on T raises and
  writes nothing. Seen to fail (014f06a): T without `h(u0) = 0`, averages over
  W, the cutoff left out.
- The day (U2): the behaviours listed under 136 above, a few days each on
  `test_synth` with the scripted provider. Seen to fail (db29997): steps run on
  a re-run, statuses read with rows dated `D`, call rows outside staging.
- Options and cursor (U3): two scripted replays from scratch give equal files
  and journal hashes. A replay in two calls equals one and serves no corpus file
  twice, also after a day failed with its response stored. The provider is
  built once per command. The usage errors and refusals give exit 2 or 1 with
  one line and write nothing. Seen to fail (545e7ec): the cursor from call rows,
  the provider built per day.
- Corpus (U4): the manifest lists every file and every file exists. Every block
  is byte-identical to its strategy file. Every response parses as listed. The
  directories are the three pool models named by 122 (b). Seen to fail: one
  character of a block.
- Gate M3 (U5): over twenty replay days, at least ten trials from the three
  makers, every pair at most `corr_max` on W of the later day (15 trials, max
  0.609). Every call row follows the rotation, and retries carry the error
  text. Stored responses equal the served corpus files. The failing model is
  removed on 2019-07-29 with one `model_removed` alert and has no call after.
  The budget day writes a `budget` row and a `token_budget` alert and is
  journaled. Prompts hold none of the listed symbols, venues, contract names,
  dates, bar values or scores in the forms G3.3 lists (less D-017's). Labellings
  differ, scaling behaves as stated, and the injected description arrives
  sanitized. Seen to fail (8d54f9f): all seven wrong changes of 139 (d), each
  with the item named there.
- Gates M2, M1 (four items) and M0 pass on the mission's code (above).
- `./scripts/check` green three times at the tip 7f18206, 0 skipped.
- Frozen files: `git diff --stat af85e55 7f18206 -- config tests/fixtures/rejected
  tests/fixtures/config tests/fixtures/config_frozen.json` is empty, and under
  `tests/gates/` the diff is four added files (`git diff --name-status`: `A` for
  `m3_harness.py`, `test_g3_1_candidates.py`, `test_g3_2_pool.py`,
  `test_g3_3_prompts.py`) and no changed one.

## Where the design is silent

As the unit bodies state: U1, a private subclass of `sequence.Context` for T in
place of a change to `sequence.py`. U2, no model list read when no cell is
offered. U3, a `run.toml` without `[workers]` under `--provider openai` refused
like `models.toml` (exit 2), a `ProviderError` building `openai` is exit 1, and
the coordinator is built only with a provider. U5, the positions jobs cut as one
span job and one own-W job per trial, and D-017's reading of the short forms.
U6, the throwaway measurement scripts live outside the repository and are not
committed.

## NOT PROVEN

- No real provider, model or `claude` binary was called: live checks L3 and L4
  are not run. G3.1 proves the pipeline, not the models.
- The twenty replay days with the real pool (the rest of L3) are the owner's.
- The base URL, the model ids and the cutoffs of `config/models.toml` stay
  unverified (`verified = false`); none was read from a primary source here.
- Every observation of a replay over 2019 is exposed under the fixture cutoffs
  (DESIGN §11.3), so nothing here reads a clean day.
- The scripted token counts are an estimate by rule (`ceil(characters / 4)`),
  not a tokenizer. The budget arithmetic above holds on those counts only.
- The corpus was written by the builder and its yield is arranged, not
  discovered: 15 trials, one admission, the duplicate, the retries and the
  injected description are where U4 put them.
- The leak checks of G3.3 cover the forms the test lists and no other spelling.
- `--provider openai` is tested for its refusal only (no key, blank key); no test
  builds it with a key or sends a request.
- The speed figures are from the builder's machine (four cores, shared, varying
  load). `./scripts/check` is 1021 to 1043 s at the tip, above HF-006's 15
  minutes (D-013 open).
- D-017's reading of the two- and four-decimal forms in G3.3 (a form is skipped
  when it is a whole number or exactly what `.4g` writes) awaits the architect.
- The wrong change "registry description passed unsanitized" went red only in
  G3.3's direct test (`test_a_raw_stored_description_is_sanitized_in_the_registry`),
  not in the end-to-end one (`test_the_injected_description_arrives_sanitized`).
  That one stayed green because `workers.parse` sanitizes the description
  before it is stored.
- `tests/test_gate_script.py`'s two "without gate tests" cases moved from M3 to
  M4 in U5, so they now check M4's absence of gate tests, not M3's.
- The gates ran on HEAD 45dc893 with U5's files uncommitted, not on a checkout
  of the pushed commit. The committed files equal what ran only as U5's body and
  the `git diff` above show; the gate was not run again after the commit.
- The `## Corpus` and `## Day` figures are from one throwaway replay each
  (provider and none), plus a one-day `m3_pool/` replay. The removal day was not
  measured again here.
- What remains of FINAL-REPORT-16's NOT PROVEN, item by item:
  1. No real provider, model or `claude` (L3, L4): remains (above).
  2. Base URL, model ids, cutoffs unverified: remains (above).
  3. Nothing of S3.2a called from `run-day` or `replay`: closed by U2 and U3.
     The generation, the pool and the coordinator now run in the day and the
     replay, with the scripted provider only.
  4. The source test's spelling limits (another spelling of the name, attribute
     access to `KEY_ENV`, an alias): remain.
  5. The cache-key removals run only over `tests/test_synth_cache.py` and
     `tests/test_synth.py`: remains.
  6. `__cause__` and `__context__` shown `None` for the failure kinds the tests
     raise: remains as a test claim (REVIEW-16 note 2 found it by inspection at
     every raise site).
  7. Speed figures from the builder's machine; check above 12 minutes: remains,
     now above 15 (above).
  8. FINAL-REPORT-15's carried items: the Claude worker's flags only as the
     builder's `claude --help` gives them; the scripted token counts (above);
     FINAL-REPORT-14 and earlier's items (the profile's statistics, anonymization
     of names and units only, the leak check's scope, G2.3's gate file, the
     prompt sample's registry state, `trusted_hashes`' same-stat rewrite,
     `BUILTIN_EXCEPTIONS` on Python 3.14.6 only, the container a boundary only as
     docker 29.1.3 and this kernel make it, G1.3's margin under 10 minutes
     load-dependent, 542 s here, and the rest as FINAL-REPORT-15 lists them):
     remain. FINAL-REPORT-15's "generation section from one throwaway run" is
     superseded by gate M3 for what G3.1 to G3.3 assert.
  9. The numbers from outside the project in `config/models.toml`: remain not
     proven. This mission added no number from outside the project.
  REVIEW-16 note 9's three additions:
  - the refusal of a `run.toml` without `[workers]` in `doctor --live workers`
    is untested (to step S5.1, decision 134 (b));
  - the doctor tests of mission 16 U1 were never seen to fail, and in this
    mission neither of decision 133 (b)'s wrong changes turned them red
    (`## Corrections`);
  - the builder's check timings were not measured again by the reviewers beyond
    one run per unit. This mission's times are again the builder's own.

## Findings filed and answered

- **D-016** (6e3caa5's two text lines outside 127 (a)'s list): **answered**,
  decision 134 (e); status line at U0, 1a04ee1.
- **D-017** (filed U5, 8d54f9f): G3.3's two- and four-decimal forms collide with
  the prompt's `.4g` statistics on SYNA. The test skips a whole number or a
  form equal to its `.4g` text. Open, for the architect.
- **D-013** (`./scripts/check` time): times lines at U2 (db29997: 867, 918,
  923 s), U3 (545e7ec: 925, 928, 963 s), U4 (446b0a8: 1281, 1024, 1079 s), U5
  (8d54f9f: 1116, 1054, 1180 s, after a red 1092 s run) and U6 (this commit:
  1021, 1043, 1024 s at the tip). **Open** (decisions 121 (c), 134 (g), 140).
- **D-014** (G1.3 against O-3's 10 minutes): times line at U5, 8d54f9f (G1.3
  542 s; G1.1 450, G1.2 204, G1.4 1 s; M3 555, M2 142, M0 247 s). Open, for the
  owner.
- **HF-006** (long runs moved to the background): status line at U4, 446b0a8
  (the first U4 check run, 1281 s, passed the 20-minute timeout and was moved to
  the background; the sub-agent waited for it). No tip run passed the cap in
  U6. Open.
- **HF-010** (stale worktrees): status line at U0, 1a04ee1 (REVIEW-16 note 10).
  `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered at this
  report. This unit's worktree `/tmp/m17-u6` was removed. Open, for the hands
  Project.
- **HF-011** (`report:` prefix not in the review protocol's skip list): status
  line at U0, 1a04ee1 (REVIEW-16 note 11). This report's commit carries
  `report:` again, as the brief names it. Open.
- **HF-012** (reviewer concurrency): status line at U0, 1a04ee1 (REVIEW-16
  note 12). Open.
- D-015, HF-008 and HF-009 remain open as FINAL-REPORT-16 left them. No other
  finding was filed in this mission.

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-16 should-fix 1 (6e3caa5's body overstates its test history) | U6, decision 133 (a) to (c): `## Corrections` above | this commit |
| REVIEW-16 note 1 (`key_present` and the docstrings as built) | no action (observation) | — |
| REVIEW-16 note 2 (every `ProviderError` raise site outside an `except`) | no action (observation) | — |
| REVIEW-16 note 3 (decision 128 (b)'s "reads the key's value" and `ClaudeWorkerProvider`) | stands, read as "reads it to use it", decision 134 (a) | — |
| REVIEW-16 note 4 (finding D-016) | D-016 answered, decision 134 (e); U0 status line | 1a04ee1 |
| REVIEW-16 note 5 (U2's `config check` comparison is real) | no action (observation) | — |
| REVIEW-16 note 6 (no test of a `run.toml` without `[workers]`; a directory as `models.toml`) | to step S5.1, decision 134 (b); carried in NOT PROVEN | — |
| REVIEW-16 note 7 (cache-key row that understates; the "27 hours" comment) | stands, decision 134 (c) | — |
| REVIEW-16 note 8 (check times above 12 minutes) | D-013 stays open, decision 134 (g); times lines U2 to U6 | db29997, 545e7ec, 446b0a8, 8d54f9f, this commit |
| REVIEW-16 note 9 (FINAL-REPORT-16's NOT PROVEN and three additions) | U6, decision 134 (d): NOT PROVEN above | this commit |
| REVIEW-16 note 10 (stale worktrees, HF-010) | U0 findings line, decision 134 (f) | 1a04ee1 |
| REVIEW-16 note 11 (`report:` prefix, HF-011) | U0 findings line, decision 134 (f) | 1a04ee1 |
| REVIEW-16 note 12 (sequential reviewers, HF-012) | U0 findings line, decision 134 (f) | 1a04ee1 |
| REVIEW-15 note 2 (weak flag dated D; paper day 0 untested) | U2, decision 136 (g) (131 (b)): states in force on `D`; the two weak-flag tests | db29997 |
| REVIEW-15 note 4 (duplicate retry messages; indirect imports) | U2, decision 136 (h) (131 (c)): the whole attempt-2 message list on a duplicate; the indirect imports stand (131 (c)) | db29997 |

## Acceptance

- `./scripts/check` green three times at the pushed tip 7f18206 (1021, 1043,
  1024 s; mission 16's tip 834 to 841 s), 0 skipped, so the `container` tests
  ran. Met.
- `./scripts/gate M3` prints `G3.1` to `G3.3 PASS` and `gate M3: PASS` (555 s).
  Met, on HEAD 45dc893 with U5's files uncommitted. Those files are the ones
  8d54f9f committed, and the tip differs from what ran only under `meta/` (see
  `## Gate M3`).
- `./scripts/gate M2` PASS; `G1.1` to `G1.4` each PASS on its own; `./scripts/gate
  M0` PASS; outputs and times above. Met, on the same tree.
- Steps 3 to 5 with a provider as decision 136 says; without one the parent's
  state; a re-run writes nothing and makes no call. Met (U2; the 136 tests).
- A generated candidate scored on T in the day's backend with both measures; its
  trial row holds every key of §10.2 with model, version and cutoff. Met (U1).
- The scripted cursor from the stored responses; a split replay equals one.
  Met (U3).
- The corpus attributed to the three pool models, every block byte-identical
  to a trusted strategy file, the manifest listing every file. Met (U4).
- REVIEW-16 should-fix 1 corrected in `## Corrections` as decision 133 says.
  Met.
- No file under `config/` or `tests/fixtures/rejected/`, no existing file under
  `tests/gates/`, no record under `tests/fixtures/config/` and no entry of
  `tests/fixtures/config_frozen.json` changed. Met (the diffs above).
- Every unit commit's body lists every file; U0 is `plan:`; U5 is `gate:`. Met.
- No test uses the network, a secret or the wall clock; no state or job
  directory inside the repository (`git status` clean after the three tip runs
  and the throwaway replays); no file under `src/` names a market, contract root
  or venue; no test builds the image. Met as the units' tests and the check
  show.
- This file has `## Gate M3`, `## Gate M2`, `## Gate M1`, `## M0 still passes`,
  `## Corrections`, `## Corpus`, `## Day`, NOT PROVEN and the review-items
  table. Met.

VERDICT: mission 17 finished
