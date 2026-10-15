VERDICT: mission 13 finished

# FINAL REPORT — mission 13 (roadmap step S2.2)

Brief: `meta/BUILDER-13-PROMPT.md`. Base 9db93b8. Decisions:
`meta/decisions/decisions-2026-10-14-m13.md` (100 to 108), with the owner's
`meta/decisions/decisions-2026-10-15-owner.md` (O-19, O-20, O-22), which wins
over 104, 105 (e), 106 (b) and DESIGN §12.5, §18.3 G2.1; O-1 to O-4, O-11 to
O-13 and O-16 to O-18 still bind. This mission closes milestone M2. Gate M1
was run again item by item and gate M0 once at the tip, as decision 100 (b)
says. Container runtime: docker, server Engine 29.1.3 (API 1.52).

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | 2a216eb | plan, checkpoint, journal; HF-008 status line citing REVIEW-12 note 10 (decision 108) |
| U1 | 6372322 | REVIEW-12 should-fix 1 to 4, notes 2 and 3 (decision 101): error texts name a type only from fixed built-in/`numpy` tuples by identity; the runner writes its result to a private descriptor, fd 1 pointed at fd 2, `dry_run [no_result]` for a child that writes none; `BaseException` caught at load and call; the static check orders attribute nodes by the name's position; determinism checks the bars the reverse job called; shared error-text helper `tests/error_texts.py` |
| U2 | c702fc4 | `sandbox/container.py` (one function, `run_command`, builds every container's options), `sandbox/Dockerfile`, `sandbox/requirements.txt`, `discotrade sandbox build`, the `[sandbox]` keys `image`, `pids`, `cpus`, `tmpfs_bytes` in both `run.toml` (decision 102) |
| U3 | 0823a2d | `sandbox/probe.py` (standard library only), `container.judge`, `discotrade sandbox selftest`, `discotrade doctor --live sandbox` (decision 103) |
| U4 | ad1b588 | the rejection suite `tests/fixtures/rejected/` and `manifest.toml` (29 entries), `tests/test_rejected_suite.py`; the subprocess backend leaves `tests/fixtures/rejected/` out of the sources it accepts (decision 104 (a), (b), (d) as O-22 narrows it) |
| U5 | bb27c90 | approaches in the day loop, the replay and `journal recompute` run through a sandbox job, `--sandbox container\|process`, `process` the default on all-synthetic tracks and refused elsewhere; job errors retire, harness errors fail the day; a fork server (decision 105); findings D-011, D-012 |
| U5b | 8b9f9be | one fork server per harness process, restarted after it dies with a `sandbox_restarted` health notice (O-20) |
| U5c | 8b923fd | the probe's limit findings (pids, memory, cpu, cpu_time); the G2.5 trusted fixtures `wall_wait.py`, `output_fixed.py`, `memory_fixed.py` and `tests/test_sandbox_limits.py`; the output-cap overrun fixed; `scripts/gate` counts five items for M2 (O-22 items 3, 4); finding D-013 |
| U6 | 42cea0f | G1.3's two expected retire reasons become the sandbox's text (O-19) |
| U6 | 68bee5f | the M2 gate tests `tests/gates/test_g2_1_rejected.py` to `test_g2_5_limits.py`, `tests/gates/m2_harness.py`; `tests/test_gate_script.py` (decision 106, O-22) |
| U7 | this commit | this report |

Plan and meta commits: 47ebf8d (`plan: decisions 2026-10-15 (owner)`), d248b6b
(mission resumed under the owner's file, U4 open), and the checkpoint commits
6e12834, cb2063e, 40fc911, 10142a7, eff2dff, 8bae433, fe5ac3c, 6e18b74,
a44581f, 13b2631.

Existing tests changed in what they assert, each under a cited decision and
named in its body: U1 (decision 101 (f)) removed the three `test_zz_*`
error-text tests that read a module-level list, each error-text test now
checking its own texts; U3 (decision 103) the image-inputs and tag tests
list the probe, and `sandbox` left the usage-error check names of
`tests/test_doctor.py`; U5 (decision 105 (c)) the two reason assertions of
`tests/test_daily.py::test_a_contract_failure_retires_the_approach_and_the_day_goes_on`;
U6 (O-19) the two reasons of `tests/gates/test_g1_3_lifecycle.py`, and in
`tests/test_gate_script.py` the two "no gate tests" cases moved from M2 to M3.

## Decisions applied

- **O-19** (D-011): G1.3's two expected reasons of 2019-06-13 are the
  sandbox's texts, `failure: dry_run [out_of_range]: position returned a
  number outside [-1, 1] at window bar 18 (parameter set 0)` and the same
  with `bar 19`, as literals; nothing else in the file changed (42cea0f,
  O-19 quoted in its body).
- **O-20** (D-012): the fork server lives for the whole harness process
  (`replay`, `run-day`, `journal recompute`, a test process), stopped by
  `atexit` and the backend's close, restarted after it dies (8b9f9be). O-3's
  10-minute target was kept and measured at U6: G1.3 576 s.
- **O-22**: G2.1 narrowed to the rejection suite under
  `tests/fixtures/rejected/` (the name `hostile` retired); G2.3 extended to
  the limits read from inside the container; G2.5 added; `scripts/gate`
  counts five M2 items. **Decision 104 (c), the containment pass, was dropped
  by O-22.** What proves the boundary instead (O-22 item 5) is G2.3 as
  extended, G2.5, and the owner's live check L5 on the server.
- Decisions 100 to 108 otherwise as written; 104 (a), (b), (d), 105 (e) and
  106 (b) as O-22 and O-20 change them. Decision 48's in-process path in the
  day loop is replaced by 105 (U5).

## Speed

`./scripts/check` wall time on the builder's machine (four cores):

| Where | Runs |
|---|---|
| base 9db93b8 (mission 12's tip, per the brief) | about 590 s (mission 12's 590, 589 s steady) |
| U1 6372322 | 699, 674, 677 s |
| U2 c702fc4 | 712 to 737 s (+~55 s, `tests/test_sandbox_container.py`) |
| U3 0823a2d | 738, 735, 697 s |
| U5 bb27c90 | 1134, 1422, 970 s (load average 2 to 4 from other projects) |
| U4 ad1b588 | 1141, 1204, 1051 s |
| U5b 8b9f9be | 881, 878, 858 s |
| U5c 8b923fd | 877, 910, 881 s (D-013) |
| U6 42cea0f | 895, 880, 884 s |
| tip 68bee5f (U6) | 814, 885, 887 s, each `check: green` |

The tip's steady figure, about 870 s, is about 280 s above the base. The
largest share came with U5 (approaches run as child-process jobs in every
day-running test: fourteen such files took 476 s at U5's parent and 843 s at
U5, back to back, under rising load), partly recovered by U5b's one server
per process. U5 and U4 ran above 15 minutes (D-012); U5c's 910 s run is
D-013. Gate tests are not in the check, so U6's second commit added nothing.

Gate items, wall time:

| Item | mission 12 (054daa1) | mission 13 (68bee5f) |
|---|---|---|
| G1.1 | 386 s | 457 s |
| G1.2 | 172 s | 200 s |
| G1.3 | 575 s | 576 s |
| G1.4 | 1 s | 1 s |
| M0 | 257 s | 266 s |
| M2 (five items, one call) | — | 157 s |

Every M1 item and every M2 item is under 10 minutes (O-3); the M2 run is
under §18.2's 15 minutes. No finding was due under decisions 100 (b) and
106 (f). G1.1 rose by 71 s and G1.2 by 28 s; neither was profiled.

## Gate M2

`./scripts/gate M2` at tip 68bee5f8ebb616fb24183faee186fbafd78ec284
(origin/main), one foreground call, after `discotrade sandbox build`
(exit 0, wall 0 s):

```
sandbox build: present, nothing built
discotrade-sandbox:1edd0f8558cb
```

`./scripts/gate M2` — exit 0, wall 157 s

```
G2.1 PASS 36 passed in 49.20s
G2.2 PASS 3 passed in 29.65s
G2.3 PASS 8 passed in 5.15s
G2.4 PASS 9 passed in 47.86s
G2.5 PASS 5 passed in 21.83s
gate M2: PASS
```

## Gate M1

Each item its own foreground call at tip 68bee5f, after `./scripts/check`
was green three times at that tip (814, 885, 887 s).

`./scripts/gate M1 G1.1` — wall 457 s (mission 12: 386 s)

```
G1.1 PASS 6 passed, 1 warning in 456.02s (0:07:36)
gate M1 G1.1: PASS
```

`./scripts/gate M1 G1.2` — wall 200 s (mission 12: 172 s)

```
G1.2 PASS 4 passed in 198.74s (0:03:18)
gate M1 G1.2: PASS
```

`./scripts/gate M1 G1.3` — wall 576 s (mission 12: 575 s)

```
G1.3 PASS 10 passed in 574.81s (0:09:34)
gate M1 G1.3: PASS
```

`./scripts/gate M1 G1.4` — wall 1 s (mission 12: 1 s)

```
G1.4 PASS 15 passed in 0.53s
gate M1 G1.4: PASS
```

By O-2's rule, gate M1 passes at 68bee5f.

## M0 still passes

`./scripts/gate M0` at 68bee5f — wall 266 s (mission 12: 257 s)

```
G0.1 PASS 62 passed in 57.75s
G0.2 PASS 7 passed in 94.59s (0:01:34)
G0.3 PASS 13 passed in 110.89s (0:01:50)
G0.4 PASS 4 passed in 0.33s
gate M0: PASS
```

## Image

- Runtime: `Docker version 29.1.3, build 29.1.3-0ubuntu3~24.04.2` (server
  Engine 29.1.3, API 1.52, minimum 1.44; containerd 2.2.1; runc
  1.3.4-0ubuntu1~24.04.1), linux/amd64.
- Base image: `python:3.14.6-slim@sha256:7bec7ddcddeff7975d6ba9b4be7dd6f6b2f55e7491539145e2978f7f97ce9144`
  (index digest), the minor version of the host interpreter (3.14.6).
- Packages, pinned in `sandbox/requirements.txt` by `uv.lock`'s wheel
  hashes: `numpy==2.5.4` (`uv.lock`: 2.5.4 for Python >= 3.12; it also holds
  2.4.6 for older interpreters), `pandas==3.0.6` (`uv.lock`: 3.0.6), and
  pandas' dependencies `python-dateutil==2.9.0.post0`, `six==1.17.0` at
  `uv.lock`'s versions; pip uninstalled after. No `pyarrow`, `httpx` or pip
  in the image (`test_the_image_holds_numpy_and_pandas_at_the_locked_versions_and_no_pyarrow_or_httpx`).
- `import discotrade.indicators` resolves because `indicators.py` and
  `runner.py` are copied into `site-packages/discotrade/` (and
  `discotrade/sandbox/`) with a docstring-only `__init__` (REVIEW-12 note 6).
- Tag the gate ran with: `discotrade-sandbox:1edd0f8558cb` (12 hex digits of
  a sha256 over the Dockerfile, the pins, the runner, the library, the
  probe and the package file), left built on the machine. Earlier tags of
  the mission: 20fa1f2225a3 (U2), edeee6d2120e (U3, still present locally).

## Rejection suite (the brief's "Hostile suite")

O-22 retires the name "hostile" and drops decision 104 (c), the containment
pass: the texts it needed were not written, and the boundary is proven by
G2.3, G2.5 and L5 instead, so this table has no containment column.

`tests/fixtures/rejected/manifest.toml`, 29 entries: 25 texts under
`tests/fixtures/rejected/` (counted with `ls`; U4's body says 24) and 4
existing texts of `tests/fixtures/strategies/` named by path. Each was run
through `validation.sequence.validate` on the container backend, on
`test_synth`'s W of 2019-07-15 at the production thresholds, and rejected at
its manifest stage (U4's pass and G2.1 at 68bee5f). The endless loop ran
with `wall_seconds` 10 and the memory bomb with 256 MiB from a `run.toml`
copied under tmp; all else under `tests/fixtures/config/run.toml`. For
run-time entries the rule is what the run returned.

| Entry | File | Stage [rule] |
|---|---|---|
| network access | rejected/network_access.py | static [import] |
| writing a file | rejected/writing_a_file.py | static [forbidden_attribute] |
| reading a file outside the mount | rejected/reading_outside_the_mount.py | static [forbidden_name] |
| reading the mounted bars directly | rejected/reading_the_mounted_bars.py | static [forbidden_attribute] |
| a fork bomb | rejected/fork_bomb.py | static [import] |
| an endless loop | strategies/endless_loop.py | dry_run (limit wall_clock) |
| a memory bomb | strategies/memory_bomb.py | dry_run (limit abnormal_exit) |
| forbidden imports | rejected/forbidden_import.py | static [import] |
| `__import__` | rejected/dunder_import.py | static [underscore] |
| an attribute walk from a literal to object | rejected/attribute_walk.py | static [underscore] |
| eval | rejected/eval_name.py | static [forbidden_name] |
| exec | rejected/exec_name.py | static [forbidden_name] |
| state kept by a module-level cache | strategies/keeps_state.py | determinism (reverse_sample) |
| state kept by a mutable default argument | rejected/mutable_default.py | determinism (reverse_sample) |
| randomness | rejected/randomness.py | static [forbidden_attribute] |
| the clock | rejected/the_clock.py | static [forbidden_attribute] |
| too many lines | rejected/too_many_lines.py | static [max_lines] |
| too many parameters | rejected/too_many_params.py | static [max_params] |
| a non-numeric parameter | rejected/nonnumeric_param.py | static [param_value] |
| a result that is not a number | rejected/not_a_number.py | dry_run (not_a_number) |
| a result that is not finite | rejected/not_finite.py | dry_run (not_finite) |
| a result out of range | strategies/grid_out_of_range.py | dry_run (out_of_range) |
| a huge output | rejected/huge_output.py | static [forbidden_name] |
| changing bars in place | rejected/changes_bars_in_place.py | activity (min_changes_w) |
| the IO functions of numpy | rejected/numpy_io.py | static [forbidden_attribute] |
| the IO functions of pandas | rejected/pandas_io.py | static [forbidden_attribute] |
| a slow function | rejected/slow_function.py | dry_run (call_max) |
| a class named from the data (REVIEW-12) | rejected/class_named_from_the_data.py | static [construct] |
| a forged result written to descriptor 1 (REVIEW-12) | rejected/forged_result_on_descriptor_1.py | static [import] |

Tests, for every row: `tests/test_rejected_suite.py::test_each_entry_is_rejected_at_its_manifest_stage`
(container) and `::test_each_static_text_is_refused_at_its_rule_and_each_run_time_text_passes_the_check`;
at the gate, `tests/gates/test_g2_1_rejected.py::test_each_text_is_rejected_at_its_manifest_stage_on_the_container_backend`.
Around them, in both files: the manifest equals §12.5's literal list plus
REVIEW-12's two, one file each; every error text passes decision 101 (f)'s
check; state bytes, `HEAD`, ledgers and `trials/` unchanged; a sentinel tree
unchanged; no container remains (18 started in U4's pass); `changes_30.py`
then validates to a pass in the same process. No entry reached a later stage
than its manifest stage; no static rule was added (O-22 item 2).
`tests/test_sandbox_process.py::test_a_text_of_the_rejection_suite_is_refused_though_it_is_under_tests_fixtures`
shows the subprocess backend refusing every text of the directory (104 (d)).

## Probe

The gate's output gives only G2.3's pass count (8 passed). G2.3
(`tests/gates/test_g2_3_probe.py`) asserts, on one probe run on the job of
`test_synth`'s W of 2019-07-15 (W 2019-06-11 to 2019-07-08), that `judge`
returns these 19 findings in this order, all PASS, and that `sandbox
selftest` prints one PASS line per finding and exits 0; its limit test
asserts `pids.max` = `run.toml`'s `pids` (64), `memory.max` =
`memory_bytes` (2147483648), `memory.swap.max` = `0`, `cpu.max` quota =
`cpus` x period, and `RLIMIT_CPU` = [1200, 1201]. Since the gate prints no
values, the same self-test was run once more for this report at 13b2631
(code identical to 68bee5f; a state under /tmp built by `bars fetch` at
2019-07-25 from a copy of `tests/fixtures/config` with the production
`thresholds.toml`, as G2.3's harness builds it), exit 0, wall 1.44 s, no
container left:

```
sandbox selftest: track test_synth, day 2019-07-15, W 2019-06-11 to 2019-07-08, image discotrade-sandbox:1edd0f8558cb
PASS network.routes: no route in the routing table
PASS network.interfaces: interfaces present: ['lo']
PASS network.connect: connection to 192.0.2.1:9 failed (ENETUNREACH)
PASS create /: create failed: read-only file system
PASS create /usr: create failed: read-only file system
PASS create /home: create failed: read-only file system
PASS create /job: create failed: read-only file system
PASS create /tmp: create succeeded
PASS user.uid: user id 10001, effective 10001
PASS user.capabilities: effective capability set 0000000000000000 (empty)
PASS limits.pids: pids.max '64', required at most 64
PASS limits.memory: memory.max '2147483648', memory.swap.max '0', required at most 2147483648 with no swap
PASS limits.cpu: cpu.max '100000 100000', required at most 1 CPU
PASS limits.cpu_time: RLIMIT_CPU [1200, 1201] s, required at most [1200, 1201]
PASS mount.instruments: 4 instruments mounted, the job has 4
PASS mount.SYNA: 912 bars mounted (433 of W, 479 of context), none after W's last day
PASS mount.SYNB: 912 bars mounted (433 of W, 479 of context), none after W's last day
PASS mount.SYNC: 912 bars mounted (433 of W, 479 of context), none after W's last day
PASS mount.SYND: 912 bars mounted (433 of W, 479 of context), none after W's last day
sandbox selftest: ok, 0 of 19 findings failed
```

The limit values match those U5c recorded at 8b923fd. G2.3 compares the
mount's counts with the store itself, which holds bars after W.

G2.5 (`tests/gates/test_g2_5_limits.py`, 5 passed, 21.83 s at the gate), on
`test_mixed` through the container backend, each under a `run.toml` copied
under tmp with one short limit and again under the production limits:

- wall clock: `wall_wait.py` (sleeps `WAIT_SECONDS` 10.0 once) under
  `wall_seconds` 3.0 ends with `limit [wall_clock]` after between 3 s and
  3 s + `KILL_GRACE` (5 s), measured with `time.monotonic` around the run,
  and no container remains; under production it passes.
- output cap: `output_fixed.py` (returns `POSITION` 0.12345678901234568 at
  every bar) under `output_bytes` 4096 ends with `limit [output]` and the
  bytes read are at most 4096; under production it passes with a result
  longer than 4096 bytes.
- memory: `memory_fixed.py` (allocates `ALLOCATE_BYTES` 512 MiB once) under
  `memory_bytes` 256 MiB ends with a `limit` or `dry_run` error, not a
  raise, and the harness's peak resident size (`VmHWM`, reset through
  `/proc/self/clear_refs`) grows by less than 64 MiB; under production it
  passes.
- process count and CPU: proven by G2.3's inspection, not by attempt; a
  test asserts G2.3 compares those limits.

The gate run does not print the measured durations, byte counts or which of
`limit`/`dry_run` the memory run returned.

## Day loop

- Backend defaults (decision 105 (b)): `run-day`, `replay` and `journal
  recompute` take `--sandbox container|process`; `process` is the default
  when every instrument of the track has `adapter = "synth"`, `container`
  otherwise; `process` on a track with any other source exits 2 naming
  DESIGN §12.4, before anything is read or written.
- Seconds per replay day, decision 80 (d)'s method (the G1.3 scenario's first
  30 calendar days, 22 replay days, `test_synth`, gate configuration):
  U5's parent 10142a7 1.561 s (34.34 s); U5 bb27c90 2.204 s with the fork
  server (48.48 s; 2.539 s without it); U5b's parent fe5ac3c 2.466 s
  (54.25 s; a second run 2.425 s); U5b 8b9f9be 1.885 s (41.47 s). The two
  pairs ran under different machine load (U5's under load average 2 to 4
  from other projects, U5b's near 2), so U5's 2.204 s and U5b's parent's
  2.466 s measure the same code under different load; only the ratio within
  a pair compares (U5b/parent 0.764).
- Fork server: built (U5) and, under O-20, one per harness process (U5b):
  started on the first job, lives for the whole `replay`, `run-day`,
  `journal recompute` or test process, stopped by `atexit` and the backend's
  close; a dead server is replaced on the next job and the day appends a
  `sandbox_restarted` notice. It imports only the runner's modules, never
  runs a text, and forks one fresh child per job with the limits set in the
  child.
- Journal: the 30-day replay is byte-identical to U5's parent except the two
  retire reasons of 2019-06-13, which 105 (c) changes (bb27c90); U5b's
  30-day replay is byte-identical to its parent, `HEAD`'s tree d278d9471f41
  at both (8b9f9be).
- G1.3 measured at 68bee5f: 576 s, against O-3's 10 minutes (24 s under).

## Decisions 101 to 106: the tests that hold them

- **101** — `tests/test_sandbox_runner.py`: `test_an_error_text_names_only_a_built_in_type_never_a_name_the_text_chose`,
  `test_the_names_the_runner_may_print_are_the_built_in_and_numpy_types_by_identity`,
  `test_a_base_exception_while_loading_or_in_a_call_is_an_error_of_its_stage`,
  `test_the_in_process_backend_reports_a_bad_result_with_its_stage`,
  `test_what_the_text_writes_to_descriptor_1_does_not_reach_the_result`;
  `tests/test_sandbox_process.py`: `test_a_text_that_forges_a_result_on_descriptor_1_and_exits_gives_no_result`,
  `test_what_a_text_writes_to_descriptor_1_or_prints_never_reaches_the_result`;
  `tests/test_static_check.py::test_first_offending_node_in_source_order`
  (REVIEW-12's three texts added);
  `tests/test_validation_sequence.py::test_a_reverse_job_that_did_not_call_its_sample_is_a_harness_error`;
  `tests/test_error_texts.py`: `test_the_words_hold_the_symbols_venues_and_contracts_of_the_records`,
  `test_the_helper_finds_a_symbol_a_venue_a_date_a_compact_date_a_time_and_a_price`,
  `test_the_helper_finds_a_compact_date`, `test_the_helper_passes_the_texts_the_harness_writes`,
  `test_the_helper_refuses_to_check_nothing`; the error-text tests of
  `tests/test_validation_sequence.py` and `tests/test_validation_grid.py`
  through `tests/error_texts.py` (101 (f)).
- **102** — `tests/test_sandbox_container.py`: `test_the_tag_is_the_image_name_and_12_hex_digits_of_the_inputs_hash`,
  `test_the_tag_changes_when_the_copied_runner_changes_and_no_build_is_made`,
  `test_the_image_inputs_are_the_definition_the_pins_the_runner_and_the_library`,
  `test_the_base_image_is_pinned_by_digest_at_the_projects_minor_version`,
  `test_numpy_and_pandas_are_pinned_to_the_versions_uv_lock_holds`,
  `test_one_function_builds_the_options_of_decision_102_b`,
  `test_the_runtime_command_gets_no_key_from_the_harness`,
  `test_the_runtime_is_the_named_one_or_the_first_of_docker_and_podman`,
  `test_with_no_runtime_found_the_backend_raises_the_harness_error`,
  `test_sandbox_build_with_no_runtime_exits_1_naming_it`,
  `test_a_job_carrying_a_function_object_is_refused`,
  `test_the_backend_says_it_enforces_the_call_time_limits`,
  `test_a_container_test_skips_printing_its_reason_when_no_runtime_is_found`,
  `test_under_discotrade_gate_that_skip_is_a_failure`,
  `test_the_skip_reason_names_sandbox_build_when_the_image_is_absent`,
  `test_sandbox_build_prints_the_present_tag_and_builds_nothing`,
  `test_the_image_holds_numpy_and_pandas_at_the_locked_versions_and_no_pyarrow_or_httpx`,
  `test_the_reference_strategies_give_the_in_process_runners_targets`,
  `test_a_source_text_that_is_not_a_repository_file_runs`,
  `test_a_fake_key_set_in_the_parent_is_absent_in_the_container`,
  `test_the_container_has_no_network_a_read_only_root_and_a_non_root_user`,
  `test_an_endless_loop_returns_limit_at_the_wall_clock_and_leaves_no_container`,
  `test_an_output_over_the_cap_returns_limit`,
  `test_a_memory_bomb_returns_limit_or_a_dry_run_error`,
  `test_the_production_call_time_thresholds_are_the_ones_written_here`,
  `test_a_slow_fixture_fails_the_dry_run_on_call_p95_at_the_production_value`,
  `test_one_call_above_call_max_ms_fails_on_call_max_at_the_production_value`,
  `test_the_correlation_stage_runs_an_approach_whose_frozen_source_is_no_repository_file`;
  `tests/test_sandbox_process.py`: `test_run_toml_loads_the_container_keys_of_decision_102_d`,
  `test_run_toml_refuses_a_bad_container_value_naming_it`,
  `test_run_toml_accepts_a_named_runtime`;
  `tests/test_offline.py::test_every_file_that_launches_a_subprocess_is_listed`
  (`container.py` in `SUBPROCESS_FILES`); `tests/test_sandbox_limits.py`
  (102 (b)'s limits under O-22 item 4): `test_a_wait_past_the_short_wall_limit_ends_with_limit_wall_clock_in_time`,
  `test_an_output_over_the_short_cap_ends_with_limit_output_and_reads_no_more`,
  `test_an_allocation_over_the_short_memory_limit_ends_with_limit_or_dry_run`.
- **103** — `tests/test_sandbox_probe.py`: `test_the_probe_imports_only_the_standard_library`,
  `test_the_probe_is_an_input_of_the_image_and_copied_into_it`,
  `test_on_a_good_report_every_finding_passes`,
  `test_narrower_limits_than_required_pass`,
  `test_the_required_limits_are_those_of_run_toml_as_run_command_sets_them`,
  `test_the_judgement_fails_exactly_the_finding_a_report_has_wrong`,
  `test_a_job_bar_after_w_fails_the_instrument_even_when_the_mount_matches_the_job`,
  `test_a_report_missing_a_part_fails_its_findings_and_never_raises`,
  `test_selftest_with_an_empty_path_exits_1_naming_no_runtime_and_starts_nothing`,
  `test_selftest_without_the_image_exits_1_naming_it_and_starts_nothing`,
  `test_a_probe_run_on_ws_job_reports_the_isolation_and_ws_bars_only`,
  `test_sandbox_selftest_prints_one_pass_line_per_finding_and_exits_0`,
  `test_selftest_needs_a_state_directory`,
  `test_the_probe_runs_on_the_host_and_reports_a_json_document`;
  `tests/test_doctor.py::test_live_sandbox_with_an_empty_path_refuses_naming_no_runtime_and_starts_nothing`.
- **104** (as O-22 narrows it) — `tests/test_rejected_suite.py`: `test_the_manifest_has_one_file_per_entry_of_the_list_and_review_12s_two`,
  `test_each_manifest_entry_names_a_file_a_stage_and_for_static_a_rule_and_no_more`,
  `test_every_text_under_the_suite_directory_is_named_by_the_manifest`,
  `test_the_production_thresholds_are_the_ones_the_suite_is_written_for`,
  `test_each_static_text_is_refused_at_its_rule_and_each_run_time_text_passes_the_check`,
  `test_each_entry_is_rejected_at_its_manifest_stage`,
  `test_every_error_text_of_the_pass_passes_decision_101_f`,
  `test_the_state_directory_and_head_are_unchanged_and_no_ledger_or_trial_is_written`,
  `test_the_sentinel_tree_is_unchanged`, `test_no_container_of_the_suite_remains`,
  `test_after_the_suite_the_same_process_validates_a_valid_fixture_to_a_pass`;
  `tests/test_sandbox_process.py::test_a_text_of_the_rejection_suite_is_refused_though_it_is_under_tests_fixtures`
  (104 (d)). 104 (c): no test (dropped by O-22).
- **105** — `tests/test_daily_sandbox.py`: `test_the_default_is_process_on_test_synth`,
  `test_the_default_is_container_on_a_track_with_a_non_synthetic_source`,
  `test_process_is_refused_on_a_track_with_a_non_synthetic_source`,
  `test_run_day_refuses_process_on_that_track_before_reading_the_state`,
  `test_the_sandbox_option_reaches_the_backend_of_each_command`,
  `test_a_replay_of_approaches_runs_with_the_decision_21_loader_patched_to_raise`,
  `test_the_journaled_targets_are_the_in_process_runners_over_the_same_span`,
  `test_journal_recompute_evaluates_approaches_on_the_sandbox_and_matches`,
  `test_a_contract_break_retires_the_approach_with_the_sandboxs_error_text`,
  `test_a_limit_error_retires_the_approach_and_the_day_goes_on`,
  `test_a_source_the_backend_refuses_fails_the_day_and_moves_nothing`,
  `test_a_harness_error_fails_the_day_naming_the_approach`,
  `test_a_replay_over_several_days_starts_the_fork_server_once` (O-20),
  `test_a_job_after_the_server_died_gets_a_fresh_one_with_a_health_notice` (O-20),
  `test_a_replay_on_the_container_backend_equals_the_process_backends_byte_for_byte`;
  `tests/test_daily.py::test_a_contract_failure_retires_the_approach_and_the_day_goes_on`;
  every other existing test of the day, the replay and the recompute,
  unchanged; `tests/gates/test_g1_3_lifecycle.py` (O-19).
- **106** — `tests/gates/test_g2_1_rejected.py`: `test_the_facts_written_here`,
  `test_the_manifest_covers_exactly_the_list_one_file_each_at_a_stage_of_the_sequence`,
  `test_each_text_is_rejected_at_its_manifest_stage_on_the_container_backend`,
  `test_every_error_text_of_the_pass_passes_decision_101_f`,
  `test_the_state_directory_and_head_are_unchanged_and_no_trial_or_ledger_exists`,
  `test_the_sentinel_tree_outside_the_job_directories_is_unchanged`,
  `test_no_container_of_the_pass_remains`,
  `test_afterwards_the_same_process_validates_a_valid_fixture_to_a_pass`;
  `tests/gates/test_g2_2_duplicate.py`: `test_the_facts_written_here`,
  `test_the_sign_flipped_duplicate_fails_stage_correlation_naming_the_approach`,
  `test_a_submission_correlated_below_the_limit_passes`;
  `tests/gates/test_g2_3_probe.py`: `test_the_facts_written_here`,
  `test_the_probe_reports_no_route_to_the_network`,
  `test_the_probe_reports_a_read_only_root_and_a_writable_tmp`,
  `test_the_probe_reports_a_non_root_user_without_capabilities`,
  `test_the_mount_holds_the_w_bars_and_their_context_and_no_later_bar`,
  `test_the_limits_read_from_inside_are_those_run_toml_and_decision_102_b_require`,
  `test_the_harness_judges_every_finding_of_the_probe_run_a_pass`,
  `test_sandbox_selftest_prints_one_pass_line_per_finding_and_exits_0`;
  `tests/gates/test_g2_4_sequence.py`: `test_the_facts_written_here`,
  `test_the_grid_fixes_the_combination_with_the_greatest_adjusted_sharpe_on_w`,
  `test_a_valid_fixture_passes_determinism_and_activity_and_every_stage`,
  `test_each_stage_fails_on_its_fixture_and_stops_there_with_an_error_text`,
  `test_no_container_of_the_item_remains`;
  `tests/gates/test_g2_5_limits.py`: `test_the_facts_written_here`,
  `test_a_wait_past_the_short_wall_limit_ends_with_limit_wall_clock_within_the_grace`,
  `test_an_output_over_the_short_cap_ends_with_limit_output_and_reads_no_more`,
  `test_an_allocation_over_the_short_memory_limit_ends_with_limit_or_dry_run`,
  `test_process_count_and_cpu_are_proven_by_g2_3s_inspection_not_by_attempt`;
  `tests/test_gate_script.py::test_m2_counts_five_items`.

## What the tests prove

- Run past the static check, a text raising a class named from the data, or
  returning an object of a class named like a price, gives an error text
  naming `an exception` / `an object`, holding neither name; a class named
  `ValueError` that is not the built-in is `an exception`. `SystemExit`,
  `KeyboardInterrupt` and `GeneratorExit` at load or call give stage `load`
  or `dry_run`. A text that writes a forged result to fd 1 and calls
  `os._exit(0)` gives `dry_run [no_result]`, not the forged targets. The
  three texts of REVIEW-12 should-fix 3 name `load`, `_a`, `load`. A reverse
  job that dropped a sampled bar makes the sequence raise `ValidationError`.
  Each of the 21 error-text tests passed alone with `-k` and in reverse order
  (U1).
- On the container backend: the three reference strategies, two parameter
  sets in one job, on every instrument of `test_mixed` over 2019-06-11..18,
  give targets byte-identical to the in-process runner's; a non-repository
  text runs; a fake key set in the parent is absent inside; an endless loop,
  an output over the cap and a memory bomb end in `limit` (or `dry_run` for
  memory) and leave no container; a slow fixture fails `call_p95` and one
  call over 500 ms fails `call_max` at the production values; the
  correlation stage compares with an approach whose frozen source is no
  repository file; the image holds `numpy` 2.5.4 and `pandas` 3.0.6 and no
  `pyarrow`, `httpx` or pip; the tag changes when a copied input changes;
  under `DISCOTRADE_GATE=1` a `container` skip is a failure.
- The probe, through the container backend with a job's exact options,
  reports no route, loopback only, a failed connection, EROFS outside
  `/tmp`, uid 10001, empty capabilities, the limits above, and per
  instrument the W bars plus context counted from a store that holds later
  bars; `judge` fails exactly the finding a hand-written report gets wrong;
  `sandbox selftest` and `doctor --live sandbox` with an empty `PATH` exit 1
  naming no runtime and start nothing.
- Each of the 29 rejection-suite texts is rejected at its manifest stage on
  the container backend with no state, ledger, sentinel or container left
  changed, and a valid fixture passes afterwards; the subprocess backend
  refuses every text under `tests/fixtures/rejected/`.
- The day loop, the replay and `journal recompute` run approaches only
  through a sandbox backend: a replay passes with the decision-21 loader
  patched to raise; journaled targets equal the in-process runner's; a
  contract break or a limit error retires the approach with the sandbox's
  text and the day goes on; a harness error fails the day and moves nothing;
  the container backend's 4-day replay is byte-identical to the process
  backend's; a replay starts one fork server; after the server is killed,
  the next day starts a fresh one and appends one `sandbox_restarted` notice.
- The G2.5 limits as listed under `## Probe`.
- Gate M2, gate M1 item by item and gate M0 pass at 68bee5f.
- `git diff --stat 9db93b8 HEAD` of `config/instruments`, `config/tracks`,
  `config/calendars`, `config/thresholds.toml`, `tests/fixtures/config` and
  `tests/fixtures/config_frozen.json` shows only `tests/fixtures/config/run.toml`
  (+7, the new keys of 102 (d)); under `tests/gates/` the only existing file
  changed is `test_g1_3_lifecycle.py` (8 lines, O-19), the rest are new;
  `config/models.toml` does not exist.

## NOT PROVEN

- The container is a boundary only as the runtime (docker 29.1.3), its
  configuration and the kernel of the builder's machine make it, shown on
  that machine only, and on the server only by the owner's live check L5.
- The rejection suite is a floor, and the static list with it: 29 texts,
  each rejected at its stage, not every text that could break a rule.
- No containment pass was run (decision 104 (c), dropped by O-22): no text
  was run past the static check to attempt network, file, fork or IO access
  inside the container. Process count and CPU are proven only by inspection
  (G2.3 reads `pids.max`, `cpu.max` and `RLIMIT_CPU`); nothing tries to
  exhaust them, and no test shows the CPU-time limit firing.
- The call-time limits are measured inside the container and depend on
  machine load, so a validation verdict on them can differ between runs;
  `slow_function.py`'s loop beats `call_max_ms` on this machine only.
- The base image and the two packages (with `python-dateutil` and `six`)
  were fetched by their pins (digest; `uv.lock`'s wheel hashes) and not
  otherwise verified.
- A whole-number price in an error text is not detected by pattern; the
  error-text check covers only the texts the tests produce.
- The subprocess backend is not a boundary and runs only repository
  sources (minus `tests/fixtures/rejected/`). Its children are forked from
  a long-lived server that holds `pyarrow`'s jemalloc thread; fork safety is
  shown only by the runs made (no hang seen).
- The grid's adjusted figure on W discards a steady-position edge, as O-4's
  "Known and not proven" says.
- Nothing calls the validation sequence from the day loop until step S3.2.
- The speed figures are from the builder's machine, under varying load
  (other projects' test runs); the seconds per replay day are one run per
  side; G1.1's and G1.2's rises since mission 12 were not profiled.
- G2.5's 5 s kill grace is the builder's own bound; the design names none.
- The probe reads cgroup v2 only; on a cgroup v1 host the limit findings
  fail.
- G2.5's memory test shows the harness's peak resident size growing by
  less than 64 MiB, not that it is strictly unchanged.
- `doctor --live sandbox` is covered with a runtime present only through
  the self-test function it shares with `sandbox selftest`; its own test is
  the empty-`PATH` refusal.
- A self-test on a state holding no bars passes its `mount.<symbol>`
  findings with 0 bars mounted (seen once while preparing this report, with
  a state whose `bars fetch` had failed); L5's mount findings mean what they
  say only on a state that holds W's bars.
- `atexit` stopping the fork server is not shown for every way the harness
  ends (a SIGKILLed harness leaves the server to end when its socket closes;
  not tested); a server dying in the middle of a job was not run (its path
  is shared with the tested dead-before-job case).
- A re-run of a journaled day may append a `sandbox_restarted` health
  notice (an operational event, not the day's content; I-6 holds for the
  day's records, not for that notice).
- G1.3 is 24 s under 10 minutes (576 s); a slower machine or load could
  take it over.
- A container day loop on a non-synthetic track was not run (its sources
  need the network); the container replay was shown on `test_synth` for
  4 days only.
- What remains of FINAL-REPORT-12's NOT PROVEN: the static list a floor
  (above); the grid's adjusted figure (above); the audit's blind shapes and
  REVIEW-11 note 7's rest, carried to S4.1; `discotrade backtest` still loads
  a strategy once for a subject's instruments (decision 107), so D-006 is
  closed for the runner only, and G0.2 does not drive the cheating text
  through `backtest`; nothing calls `validate` from `run-day` or `replay`
  and its results reach no ledger until S3.2; the unit-level choices of
  mission 12's units (run.toml's values, `REVERSE_SAMPLE` 20, and the rest
  listed there); the error-text check on produced texts only; decision 98's
  tests on one W and one admitted approach configuration; and everything
  carried from FINAL-REPORT-11, -10, -9 and -8 as FINAL-REPORT-12 lists it.
  Closed by this mission: the container backend, image, probe and suite now
  exist; call-time limits are enforced on the container backend (U2's
  `call_p95` and `call_max` tests); approaches no longer run in-process in
  the day loop (U5).
- No number from outside the project was added; `run.toml`'s new values
  (`pids` 64, `cpus` 1.0, `tmpfs_bytes` 64 MiB) are the project's own choice.

## Findings filed and answered

- **D-011** (filed U5, bb27c90): G1.3 expected the in-process loader's
  retire reason. Decided by O-19; built in U6 (42cea0f).
- **D-012** (filed U5, bb27c90): G1.3 projected at about 812 s and check
  runs above 15 minutes. Decided by O-20; built in U5b (8b9f9be); G1.3
  measured 576 s at U6.
- **D-013** (filed U5c, 8b923fd): a `./scripts/check` run took 910 s, above
  15 minutes. Open.
- **HF-009** (recorded d248b6b under O-22): a sub-agent cannot be assumed to
  write whatever a unit asks (U4's first attempts stopped before writing
  any file). Resolved for this project by O-22; open for the hands Project.
- HF-008 remains open (status line appended in U0, 2a216eb, decision 108).

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-12 should-fix 1 (error text names a type the submission chose) | U1, decision 101 (a): types named only from fixed built-in/`numpy` tuples by identity | 6372322 |
| REVIEW-12 should-fix 2 (result writable by the text) | U1, decision 101 (b): private result descriptor, fd 1 to fd 2, `dry_run [no_result]` | 6372322 |
| REVIEW-12 should-fix 3 (static check's first offender) | U1, decision 101 (d): attribute nodes ordered by the name's position | 6372322 |
| REVIEW-12 should-fix 4 (determinism's sample) | U1, decision 101 (e): the called bars compared with the sample; a difference is a harness error | 6372322 |
| REVIEW-12 note 2 (error-text tests order-dependent; compact dates) | U1, decision 101 (f): shared helper `tests/error_texts.py`, eight-digit dates matched | 6372322 |
| REVIEW-12 note 3 (`BaseException`) | U1, decision 101 (c): caught at load and call | 6372322 |
| REVIEW-12 note 5 (correlation with a non-repository frozen source) | U2, decision 102 (g): `test_the_correlation_stage_runs_an_approach_whose_frozen_source_is_no_repository_file` | c702fc4 |
| REVIEW-12 note 6 (`import discotrade.indicators` in the image) | U2, decision 102 (e): files copied into `site-packages/discotrade/` with a docstring-only `__init__` | c702fc4 |
| REVIEW-1 note on the `container` marker | U2, decision 102 (g): skip with reason outside a gate, failure under `DISCOTRADE_GATE=1` (`tests/conftest.py`) | c702fc4 |
| Decision 48's in-process path in the day loop | U5, decision 105 (with O-20 in U5b): approaches run through sandbox jobs | bb27c90, 8b9f9be |

## Acceptance

- `./scripts/check` green three times at the pushed tip 68bee5f (814, 885,
  887 s), with the `container` tests run (image present). Met.
- `./scripts/gate M2` at 68bee5f prints `G2.1` to `G2.5 PASS` and `gate M2:
  PASS` (157 s). Met.
- Gate M1 G1.1 to G1.4, each its own call, and gate M0 pass at 68bee5f,
  times above beside mission 12's; no item above 10 minutes. Met.
- REVIEW-12 should-fix 1 to 4, notes 2 and 3: decision 101's tests. Met.
- Container backend options, limits, mount, environment, removal, call-time
  limits, targets, image contents and tag: decision 102's tests and G2.3,
  G2.5. Met.
- Probe findings and the refusals without a runtime: decision 103's tests
  and G2.3. Met.
- Every entry of §12.5 with REVIEW-12's two is rejected at its manifest
  stage on the container backend with nothing changed and the harness going
  on; the subprocess backend refuses the suite's texts. Met as O-22 narrows
  it; the containment half of this item was dropped by O-22.
- The day loop, the replay and `journal recompute` run approaches only
  through a sandbox backend; journal byte-identical on the G1.3 scenario's
  first 30 days except the two reasons 105 (c) changes; job error retires,
  harness error fails the day. Met.
- Frozen files unchanged; `tests/gates/` changed only in G1.3's two
  reasons, approved by O-19, plus the new M2 files; `run.toml` changed
  only by 102 (d)'s keys; no `config/models.toml`. Met with the O-19
  exception.
- Every unit commit's body lists its files; U0 is `plan:`. Met.
- No test uses the network, a secret or the wall clock (G2.5's
  `time.monotonic` decides an assertion only, I-12); no state or job
  directory inside the repository (`git status` clean after the runs); no
  test builds the image. Met.
- This file has `## Gate M2`, `## Gate M1`, `## M0 still passes`, `## Image`,
  `## Rejection suite (the brief's "Hostile suite")`, `## Probe`, `## Day
  loop`, NOT PROVEN and the review-items table.

VERDICT: mission 13 finished
