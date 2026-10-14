# REVIEW-12 — cold review of mission 12 (roadmap step S2.1)

Base: 88c32f9 (`review: mission 11`, the last `review:` commit). Range
reviewed: `88c32f9..origin/main` (tip faed629). Unit commits: 52d7fec (U1),
92703c9 (U2), fa4b53b (U3), d553c35 (U4), 4c09fd1 (U5), 4d77450 (U6). Each
was reviewed by one foreground sub-agent in its own `git worktree`. Each ran
`./scripts/check` once at its commit; all were green.

Non-unit commits read for forbidden edits: c2612a6 (the kit: KIT.md,
meta/BACKLOG.md, meta/ROADMAP.md, meta/BUILDER-12-PROMPT.md,
meta/decisions/decisions-2026-10-14-m12.md, which are the architect's
files); d250987 (`plan:`: meta/plan.md, CHECKPOINT, journal, FINDINGS
status lines for D-010 and D-006 as the brief orders); 8b077cd, f2551e0,
1be3a70, 0ebc8be, 196748d, 054daa1 (`meta:`: CHECKPOINT, journal, plan
only); faed629 (`report:`: FINAL-REPORT-12, CHECKPOINT, journal, plan).
None of them touches a builder-forbidden file outside the kit. No unit
commit touches `meta/plan.md` or `meta/CHECKPOINT.md`.

`git diff --name-status 88c32f9 origin/main` over `config/`, `tests/gates/`,
`tests/fixtures/config/`, `tests/fixtures/config_frozen.json`, DESIGN.md,
SPEC.md, PLAYBOOK.toml, `.claude/`, `templates/`, `docs/`, CLAUDE.md,
meta/ARCHITECT.md and meta/REVIEW-PROTOCOL.md prints only
`A config/run.toml` and `A tests/fixtures/config/run.toml`, both new under
decision 96 and not frozen (§4.3). `config/models.toml` does not exist.

## Gate

not a closing mission

(Decision 91 and the brief: mission 12 closes no milestone. The builder's
re-runs of gate M1 item by item and of gate M0 at 054daa1 are in
FINAL-REPORT-12 and were not repeated here.)

## Blockers

None.

## Should-fix

1. **Decision 95 (e): an error text can carry a value the text chose.**
   `sandbox/runner.py` puts `type(exc).__name__` (lines 121 and 206) and
   `type(value).__name__` (line 133) into the error text. A class's name is
   whatever its creator chose. The U3 reviewer ran the runner directly, without
   the static check, on a `position` that raised
   `type("SYNA_close_"+repr(c)+"_2019-06-14", (Exception,), {})()`. It got
   `dry_run [raised]: position raised SYNA_close_4125.25_2019-06-14 at window bar 0 (parameter set 0)`,
   which holds a symbol, a price and a date. Today the static check refuses
   `type` and `class`, so no text that passes stage 1 is known to build such
   a class. But 95 (e) says the text "never holds" one, and §12.1's list is
   only a floor. Fix: name only built-in exception types, by a fixed list,
   and otherwise use a fixed word such as `an exception` or `an object`.
   The commit body's own claim ("named by its type only") is accurate, so
   this is not an overreach.
2. **The runner's result channel can be written by the text.**
   `runner.main` redirects only Python-level `sys.stdout`
   (`contextlib.redirect_stdout`, line 243). A text that writes to file
   descriptor 1 and then calls `os._exit(0)` made
   `python -m discotrade.sandbox.runner` exit 0 with targets the text chose
   (U3 reviewer, run directly). The static check refuses `import os`, and
   the container and hostile suite are S2.2's. Still, the fix is cheap and
   belongs to the runner: duplicate fd 1 before the text loads, point fd 1
   at stderr, and write the result only to the saved descriptor.
   Otherwise, file it for S2.2's hostile suite. The commit's test and claim
   cover `print` only, which is accurate.
3. **Decision 94 (a): within a rule, a chained attribute names the last
   offender, not the first in source order.** Confirmed at the tip with
   `check(...)` on production thresholds:
   - `x = np.load("f").eval` names `eval`, not `load`.
   - `x = np.zz._a._b` names `_b`, not `_a`.
   - `x = np.load(1).to_csv(2)` names `to_csv`, not `load`.

   `_order` sorts by the chain's start position, and ties go to the outer
   node. The rule refused is right; only the node named is wrong. Fix: order
   attribute nodes by the position of the attribute name (`end_col_offset`
   minus `len(attr)`, or the inner value's end), and add these texts to
   `test_first_offending_node_in_source_order`.
4. **Decision 98 (a): determinism does not check that the reverse job
   called the bars it was given.** `sequence.determinism` (around line 418)
   takes `called` from the backend's result and zips it with the returned
   targets. It never compares `called` with the `samples` it built. A
   backend, or a future container runner, that called fewer bars or other
   bars would pass the stage. Fix: assert that `called` equals the
   requested sample per instrument, in descending order, and add a test with a
   fake backend that drops a bar.

## Notes

1. Every unit was seen to be test-first. The tests the commit added went
   red with the product files at the parent. Every wrong change the brief
   names, made in a worktree and reverted, turned at least one test red.
   U5's `sequence.py` was not written test-first, as its body and
   FINAL-REPORT-12 say; its four wrong changes were reproduced by the
   reviewer with the same red counts the body gives.
2. `test_zz_no_error_text_holds_...` in `tests/test_sandbox_runner.py`,
   `tests/test_validation_grid.py` and `tests/test_validation_sequence.py`
   reads a module-level `ERROR_TEXTS` filled by earlier tests. Run alone,
   with `-k`, or in random order, it fails (it asserts a minimum count), so
   it never passes vacuously, but it is order-dependent. Its date pattern
   (`\d{4}-\d{2}`) would miss `20190715`, and nothing in it catches a
   whole-number price. Both points are within FINAL-REPORT-12's NOT PROVEN
   on the error-text check.
3. U3's runner lets a `BaseException` that is not an `Exception`
   (`KeyboardInterrupt`, `SystemExit`) escape `execute`, so no error
   document is written. The subprocess backend then sees a bad exit. Worth
   a stage-`dry_run` mapping when the hostile suite is built (S2.2).
4. U4 (`process.py`): the wall-clock kill is `killpg(SIGKILL)` on the
   child's session, followed by `wait()`. The output cap is enforced while
   reading, and stderr goes to DEVNULL. Three things are untested:
   - If the child exits cleanly while a forked grandchild still runs, the
     grandchild is not killed.
   - Neither the `cpu_time` (SIGXCPU) branch nor the memory-bomb `limit`
     branch is shown firing; only the `dry_run` `MemoryError` path was seen.
     FINAL-REPORT-12 says this for the CPU limit.
   - `build_job` still accepts an explicit `limits=` and so does not
     strictly require `run.toml`, though no `src/` caller uses that path.

   `trusted_hashes` re-hashes every file under `reference/` and
   `tests/fixtures/` on every run.
5. U6: a worker-written approach source under `approaches/<id>/` will raise
   `ValidationError` in the correlation stage on the subprocess backend
   (its sha256 matches no repository file), until S2.2's container backend.
   Nothing calls `validate` from the day loop in this step (decision 98
   (d)), so nothing is affected yet. S2.2 should carry it.
6. `discotrade/__init__.py` calls `importlib.metadata.version`, so the
   runner's `import discotrade.indicators` needs the package installed.
   S2.2's image must install it or import the indicators otherwise.
7. `./scripts/check` measured by the reviewers, one run each:
   - U5: 656 s (`1830 passed, 121 deselected in 654.71s`).
   - U6: 666 s (`1857 passed, 121 deselected in 664.52s`).

   Both ran with no other reviewer running concurrently. The U1–U4
   reviewers ran in pairs. This matches FINAL-REPORT-12's figures of
   about 590–670 s, about 100 s above the base.
8. FINAL-REPORT-12's NOT PROVEN agrees with what the sub-agents found. It
   names: the subprocess backend not being a boundary; the static list
   being a floor; call-time limits not enforced; the CPU limit never shown
   firing; the error-text check being over the fixtures' texts only; and
   `sequence.py` not being written test-first. Should-fix 1 and 2 are
   concrete instances of the first two items.
9. Decision 98 (c) reading: approaches compared are those live or dormant
   in the state after day D (`states(..., D+1)`), the reading
   `lifecycle.admit` makes. `|r| == corr_max` passes (strict `>`), and a
   test pins it. A submission given as a function object skips stage 1 and
   is seeded from the empty text. These are builder choices stated in the
   bodies.
10. hands: concurrent reviewer sub-agents. Two ran at a time for U1–U4, and
   each pair took 13–17 minutes per agent with one `./scripts/check` each.
   At U5/U6's ~660 s single-run check, two concurrent reviewers would come
   near the 20-minute call cap (HF-008, still open). U5 and U6 were
   therefore reviewed one at a time. A reviewer's endless-loop mutant also
   left an orphaned runner child, which it had to kill by hand.
   The protocol could say to run per-commit sub-agents one at a time
   once check exceeds about 10 minutes.

## Per-commit verdicts

### 52d7fec (U1)

```
Review of 52d7fec (mission 12 U1): the commit passes all five points, with nothing found to fix.

1. **Unit:** mission 12 U1, the widened audit and finding D-010. It claims decisions 92 and 93 (and 62, 87, 89), DESIGN 10.2 and DESIGN 2 (I-5).
2. **Test-first (red, as expected):**
   - **Parent `ledger.py` and register restored:** 7 failed, 90 passed. The failures were `test_ledger.py::test_a_lifecycle_row_of_four_reasons_must_carry_adjusted_and_plain[admitted|displaced|dormant|returned]`, `test_a_trial_row_must_carry_adjusted_t_and_adjusted_w`, `test_return_readers.py::test_the_audit_passes` and `test_the_readers_review_11_named_are_registered`.
   - **Brief's named wrong changes:**
     - Removing only the `cli._backtest_result` entry fails those last two audit tests.
     - Letting `ledger.append` accept a `dormant` row without `plain` fails only `test_a_lifecycle_row_of_four_reasons_must_carry_adjusted_and_plain[dormant]`.
     - A `_probe` in `metrics.py` holding `"net_1x"` only in a generator's tuple fails `test_the_audit_passes` ("unregistered: discotrade.metrics._probe holds "net_1x" constant").
   - **Old audit logic put back into the test file:** 11 failed, all 9 new shape cases except call-argument and lambda-default, plus `test_a_constant_belongs_to_the_innermost_function` and the registration test. Those two shapes were already found under decision 89, so passing there is expected. The worktree was restored clean afterwards.
3. **`./scripts/check`:** green on one run. Last lines: "config check: ok, 168 unverified values" / "check: green".
4. **Design conformance:** conforms.
   - **Decision 92:** the audit now matches any of the six string constants anywhere in a function's own body, with nested functions attributed to the innermost one. Both required entries are registered with notes, and no other unregistered function is found.
   - **Decision 93:** `_check` now requires both figures on the four reasons and on trial rows. Another reason with any figure is still refused. The check runs on append only, and old lines stay a byte prefix of the new file (tested), so I-5 holds.
   - **Production writers:** every call in `lifecycle.py` that writes the four reasons or a trial row already passes both figures.
   - **Other invariants:** no network or secret use (I-11), no market name (I-9), no new number outside `config/` (I-10), no wall clock (I-12), no state in the repo (I-14), no new dependency.
   - **Bugs:** none found in the diff.
5. **Forbidden edits:** none. The commit touches only `src/discotrade/ledger.py`, `tests/fixtures/return_readers.toml`, `tests/test_ledger.py`, `tests/test_lifecycle.py` and `tests/test_return_readers.py`, and the body lists all five. It touches no config, `tests/gates/`, `meta/plan.md`, `meta/CHECKPOINT.md` or other protected file; the `meta/` changes since 88c32f9 come from separate meta commits.

**Not proven:**
- The commit body's "green 3/3": I ran check once, not three times.
- Whether the audit sees every way a column can be named in `src/`. Module-level constants are not seen (`replay._adjusted` shows this), as the body itself states and decision 92 accepts.
```

### 92703c9 (U2)

```
I reviewed 92703c9, mission 12 U2 "validation: the static check of DESIGN 12.1". It passes all five points with one minor bug: in chained attributes it can name the wrong offending part.

1. **Unit:** U2, claiming decision 94, DESIGN 12.1 and 6.1, R-24 and I-10. It adds `src/discotrade/validation/__init__.py`, `src/discotrade/validation/static.py` and `tests/test_static_check.py` (365 tests). PASS.
2. **Test-first:** PASS. With the validation package deleted, collection fails (`ModuleNotFoundError: No module named 'discotrade.validation'`); restored, 365 pass. The brief's three wrong changes, each made and reverted, go red: underscore rule on names only, 5 failed; `from numpy.random import default_rng` accepted, 2 failed; lines counted with `len(source.split("\n"))`, 3 failed. These match the counts in the commit body.
3. **`./scripts/check`:** green on one run, last lines `config check: ok, 168 unverified values` / `check: green`.
4. **Design conformance:** PASS, apart from the bug below.
   - The rules run in 12.1's order and the four limits come from `thresholds.toml` through `strategy.Limits`, with no hard-coded threshold.
   - Forbidden names and the underscore rule cover names, parameters, function names, import aliases, keyword arguments, lambda parameters, walrus targets, `except` names, match names and type parameters. The underscore rule also covers attributes.
   - The construct rule catches `async def`, `async for`, `async with`, async comprehensions and `yield from`.
   - `from numpy import random` and `from numpy import load as ld` are refused as forbidden attributes, and `from numpy import *` is refused by the import rule.
   - Star-args in a call (`max(*[1,2], **{})`) are accepted, which 12.1 permits.
   - I-9, I-11, I-12 and I-14 hold, and there is no new dependency.
5. **Forbidden edits:** PASS. The commit touches only the three files, all listed in the body, with no `config/`, `tests/gates/`, `meta/` or protected documents.

**Bug (minor, decision 94 (a)):** within a rule, chained attributes are ordered by the chain's start column, and ties go to the outer attribute. So the check names the last offender in the chain instead of the first in source order:
- `x = np.load("f").eval` names `eval`, not `load`
- `x = np._a._b` names `_b`, not `_a`
- `x = np.load(1).to_csv(2)` names `to_csv`, not `load`

The rule is still right; only the node named is wrong. Ordering attributes by the position of the attribute name, not the chain's start, would fix it.

**NOT proven:**
- That `check` is green three times in a row: I ran it once.
- Plain `type X = int` (the Python 3.12 soft keyword) is accepted. It is outside 12.1's list and looks harmless.
- Parse runs before the line count, so a huge text is parsed before being refused. The body states this as a choice.
```

### fa4b53b (U3)

```
fa4b53b (mission 12 U3, sandbox job, runner and in-process backend): **pass with two should-fix bugs.** The commit claims decision 95 (a)-(f) of decisions-2026-10-14-m12, decisions 22, 23, 24, 36, 37 and 44, DESIGN 12.4, 6.2, 5.6 and 4.1, I-2, I-7 and D-006.

1. **Unit and claims:** the commit body names all of the above and lists all 6 files the commit adds (4 under `src/discotrade/sandbox/`, 2 tests).
2. **Test-first:** red without `src/discotrade/sandbox/` (2 collection errors), 80 passed when restored.
   - (a) Prices adjusted as of the job's last bar: the cheat test and the in-process test go red.
   - (b) Text loaded once per job: the cheat test goes red (1 failed). Loaded once per parameter set and shared across instruments: the cheat test goes red too.
   - (c) Window read one day long, so a bar of T is in the W job: 6 red, including the W-job test and the 3 `evaluate`-equality tests.
   - `test_zz_...` depends on test order and fails when run alone (`len(ERROR_TEXTS) >= 9`). It does not pass vacuously.
3. **`./scripts/check`:** last lines `config check: ok, 168 unverified values` / `check: green` (1 run).
4. **Conformance:** passes except for the 2 bugs below.
   - The runner imports only the stdlib, numpy, pandas and `discotrade.indicators`. pandas loads pyarrow on its own if it is installed, which is harmless.
   - `frame_at` matches `backtest._strategy_targets` line for line, and `check` matches `strategy.check_result`, including clipping negatives when shorting is not allowed.
   - The text is loaded fresh per parameter set and instrument, and the in-process backend refuses a job carrying source text.
   - I-9, I-10, I-11, I-12 and I-14 hold, and there is no new dependency.
5. **Forbidden edits:** none. No change under `meta/`, `config/`, `tests/gates/`, `DESIGN.md`, `SPEC.md`, `pyproject.toml` or `uv.lock`.

Bugs found, both confirmed by running them:
- **Error text can carry a price or date (breaks 95(e)).** `execute` puts `type(exc).__name__` and `type(value).__name__` into the text, and the text can name those types itself, built from the data. A `position` raising `type("SYNA_close_"+repr(c)+"_2019-06-14",(Exception,),{})()` gave `dry_run [raised]: position raised SYNA_close_4125.25_2019-06-14 at window bar 0 (parameter set 0)`. Returning an object of a class named `"price 4125.25"` leaks the same way under `not_a_number`. Fix: use a fixed text, or only the names of built-in exception types.
- **The text can forge the runner's result.** `contextlib.redirect_stdout` only redirects at the Python level. A text that runs `os.write(1, b'{"ok": true, "results": [...]}')` and then `os._exit(0)` made `python -m discotrade.sandbox.runner` exit 0 with targets the text chose. That breaks the commit's claim that the text "cannot reach the result", and goes against I-1. Fix in the runner or U4: redirect at the file-descriptor level, or return the result over a channel the text cannot write to.
- **Minor:** a text raising `KeyboardInterrupt` (or another `BaseException`) escapes `execute`, so the run ends with no error document.

Not proven:
- `discotrade/__init__.py` calls `importlib.metadata.version("discotrade")`. In the step S2.2 image the runner's `import discotrade` fails unless the package is installed there. That is U4/S2.2's to settle.
- The date check in the error-text test (`\d{4}-\d{2}`) would not catch other date formats or whole-number prices.
- The bar index that 95(e) allows still lets a text pass a little information through the error, and decision 95 accepts that.
```

Reviewer's annotation: the commit body claims only that what the text
*prints* does not reach the result, and its test covers `print`. That claim
holds. Both bugs need a text that gets past the static check's refusal of
`type`, `class` and `import os`, so they are should-fix 1 and 2, not
blockers.

### d553c35 (U4)

```
Verdict on d553c35 (mission 12 U4, "sandbox: the child-process backend and config/run.toml"): accept, with minor notes. No blockers.

1. **Unit:** the body claims U4, decision 96 (m12), DESIGN §12.4, §12.2 and §3, I-7/11/12/13, and decisions 47 and 48 of 2026-10-12. It lists every changed file, and it says openly that `sandbox/base.py` is outside the brief's file list (`build_job` gains `config_dir`; `SandboxLimits` gains `cpu_seconds`). OK.
2. **Test-first:** I reverted `config.py` and `base.py` to the parent and deleted `process.py` and `config/run.toml`. I kept `tests/fixtures/config/run.toml`, because it is a test fixture. Both test files went red: `test_sandbox_process.py` failed to import `load_run`, and `test_offline.py::test_every_file_that_launches_a_subprocess_is_listed` failed. Each of the brief's three wrong changes, made one at a time, turned a test red:
   - (a) sha256 check removed: one test failed, the repository-source refusal test.
   - (b) `env=None`: `test_the_child_environment_holds_only_the_allow_list` failed.
   - (c) deadline pushed out by 10**6 s: the endless-loop test failed at its own 120 s bound ("did not return within 120.0 s").

   OK.
3. **`./scripts/check`:** last lines were "config check: ok, 168 unverified values" and then "check: green" (one run).
4. **Decision 96:** conforms. The child is `sys.executable -I -m discotrade.sandbox.runner`, its cwd a scratch `work/` dir. RLIMIT_AS, RLIMIT_CPU and RLIMIT_CORE=0 are set in the child. The harness enforces the wall clock with a monotonic deadline, `killpg(SIGKILL)` on the child's own session, then `wait()`, so there are no zombies and children the strategy forks are killed with it. The output cap is enforced while reading, so at most cap + 64 KiB is held. stderr goes to DEVNULL, so there is no pipe deadlock. The sha256 check runs before anything is written. The child's environment is a fixed allow-list with nothing taken from the parent (I-13). `load_run` gives frozen dataclasses, refuses unknown keys naming them, and refuses a missing file naming `run.toml`. `config check` only reads `run.toml` when it is there. `process.py` is in `SUBPROCESS_FILES`. Invariants:
   - I-12: the only clock read is the kill deadline, and the tests assert stage and rule, never a time.
   - I-14: job dirs go under a scratch dir the caller passes, and are removed after each run.
   - I-10: the `run.toml` values are runtime limits, not score or alert thresholds.
   - No new dependency.
5. **Forbidden edits:** none. No DESIGN, SPEC, meta, `.claude` or `tests/gates/` changes, and no existing frozen config changed. `config/run.toml` is new and not frozen per decision 96.
6. **Minor notes, not blockers:**
   - (i) If the child exits cleanly while a forked grandchild that has already closed stdout is still running, no `killpg` happens and the grandchild is left orphaned. This is unlikely, since only repository sources run.
   - (ii) `build_job` still accepts explicit `limits=`, so job building does not strictly require `run.toml`. No `src/` caller uses that path yet.
   - (iii) `trusted_hashes` re-hashes every file under `reference/` and `tests/fixtures/` on every run, which is slow but correct.
   - (iv) `preexec_fn` is used, and the tests call the backend from a thread.

**Not proven:** the memory-bomb `limit` branch (only the `dry_run` MemoryError path was seen), the `cpu_time` (SIGXCPU) branch, which no test exercises, and the forked-grandchild kill, which no test covers.
```

### 4c09fd1 (U5)

```
I approve commit 4c09fd1 (mission 12, unit U5), with no blockers. I found no real bugs. The worktree is removed, no processes are left behind, and the main checkout is clean.

1. **Unit:** U5, the dry run and the grid on W, judged on the exposure-adjusted measure. The body cites O-17, O-4 and O-18; decisions 97, 81, 86 (a), 89, 23, 25, 30 and 39; DESIGN §12.2 stage 2, §4.1 and §8; and R-23. **PASS.**
2. **Test-first: PASS.** With `paper.py` put back to the parent and `sequence.py` removed, `tests/test_validation_grid.py` fails to import (red), and in `tests/test_return_readers.py` 1 test fails (the audit reports 4 unregistered entries). `tests/test_exposure.py` is not touched by the commit and passes before and after it. My four reproductions of the wrong changes, each reverted:
   - (a) choosing on the plain Sharpe: 2 fail (`grid_fixes_the_greatest_adjusted…`, `result_has_decision_97_e_shapes…`).
   - (b) hbar padded with zeros over the context bars: the same 2 fail.
   - (c) a tie going to the last (`>=` in `first_greatest`): 2 fail (`grid_fixes…`, `a_tie_fixes_the_first_in_order`).
   - (d) the subtraction inlined in `paper.adjusted`: 1 fails (the ast test); the exposure tests stay green.
   All four match the body's counts. As the body admits, `sequence.py` itself was not written test-first.
3. **`./scripts/check`: PASS.** It ended with "1830 passed, 121 deselected in 654.71s", "config check: ok, 168 unverified values" and "check: green" (exit 0, 656 s wall). That is slightly slower than the body's 604–624 s.
4. **Conformance with decision 97: PASS.**
   - (a) Combinations come from `itertools.product` in declaration order, the first key varying slowest. A value out of range fails `dry_run` with the runner's text ("…at window bar 0 (parameter set 1)"); load and limit errors are prefixed "dry_run: ".
   - (b) Scoring happens outside the sandbox through `backtest.score`. hbar is taken over the evaluation rows, which are window bars only. R_i(D) sums the unit returns per date, with start (1,1) and the gap handled. The daily value is the mean over the N instruments, minus the mean of hbar times R.
   - (d) The NaN and tie rules are correct.
   - (e) The result shapes are correct.
   - The call-time limits are enforced only through the `enforces_call_limits` flag, with `call_p95_ms` and `call_max_ms` read from thresholds.
   - (c, f) The register entries are as required, and the audit accepts `paper.adjusted` or `paper.adjusted_rows`; the new case shows an entry calling neither failing.
   - The test's own figures use `backtest.evaluate` rows, the Parquet bars and the roll JSON, and call none of the forbidden paper functions. "Production thresholds" is real: `config/thresholds.toml` is copied in and 50 and 500 are asserted.
   - Invariants: no wall clock, symbol or state-directory write in `sequence.py` (I-12, I-9, I-14). The tests use no network (I-11). I-4 holds (1x and 2x). There is no new dependency.
5. **Forbidden edits: PASS.** Nothing changed under config/, tests/gates/, meta/, the design and spec documents, .claude/ or the dependency files. The body lists all 9 files. The only test lines removed are in the audit, widened as decision 97 (c) orders.

**Not proven:**
- No real backend enforces the call-time limits.
- The plain-versus-adjusted disagreement holds on one W and one set of seeds only.
- `test_zz_no_error_text…` depends on file order and the module-level `ERROR_TEXTS` list, so it fails if run alone or with `-k`.

**Minor, not a bug:** a `GRID = {}` would come back as `{}` rather than `null` in `grid.grid`. The static check limits GRID's form, so this is unlikely to arise.
```

### 4d77450 (U6)

```
**Review of 4d77450** (mission 12, unit U6): **PASS, no blockers.** The worktree is removed, no child processes are left, and the main checkout is clean.

1. **Unit:** U6 claims decision 98 (a)-(d), decisions 25, 63 and 95 (e), DESIGN §12.2 stages 1 and 3-5, §12.3, and R-1. It matches the brief.
2. **Test-first: PASS.**
   - With the parent's `sequence.py` and no `correlation.py`, both new test files go red (ImportError). Restored, all 27 pass in about 50 s.
   - (a) No absolute value: 6 red, including the sign-flipped duplicate, the dormant-vs-two-over-limit test, `test_correlation`'s negative-correlation, threshold and largest-|r| tests, and `test_zz`.
   - (b) Retired approaches compared: 2 red, `test_a_retired_approach_is_not_compared...` and `test_live_and_dormant_approaches_are_compared_and_retired_ones_are_not`.
   - (c) Second run reusing the first result: 7 red, including `test_the_second_run_is_a_new_job...`, `keeps_state` and the pinned-sample test.
   - (d) Per-instrument max instead of sum: 7 red, including exactly-30-passes, the valid-fixture pass and the 97 (e) result.
3. **`./scripts/check`: green.** One call, wall time 666 s. Last lines are "1857 passed, 121 deselected in 664.52s", "All checks passed!", "config check: ok, 168 unverified values" and "check: green".
4. **Design conformance: PASS.**
   - The reverse sample follows 98 (a): seed is the int of the first 16 hex of sha256, one `default_rng`, `choice` without replacement, min(20, n) per instrument in track order, and the runner calls them in descending order. The second run is a new job of the same backend.
   - Activity is summed `trade > TRADE_FLOOR` (1e-9) against `min_changes_w` from config.
   - The correlation series is `h` over W's window bars in track order. Zero deviation gives nan, which is not a duplicate. The test is strict `>`, so a value exactly at `corr_max` passes, and there is a test for it. The lowest id wins a tie (sorted iteration, replaced only on strictly larger |r|).
   - "Compared" uses the state after D (`states(..., D+1)`). That is the same reading `lifecycle.admit` makes and is consistent with decision 63.
   - Stage order is static, dry_run, determinism, activity, correlation, stopping at the first failure.
   - Tests run at production thresholds (30 / 0.7, copied from `config/thresholds.toml` and asserted).
   - The state bytes, `.git` and HEAD are unchanged.
   - Invariants: no error text carries a score or r value (I-8); the activity text gives only counts (29 / 30). Nothing new for I-10, I-11, I-12 or I-14, and no new dependency.
   - A submission given as a function object skips the static stage and seeds from the empty text. That is the stated silent-design reading and is in-process for unit tests only.
5. **Forbidden edits: none.** The commit touches 8 files, all listed in the body. No existing test, config, `tests/gates/`, `meta/` or protected file changed.

**Not proven:**
- The three green check runs the commit body claims (I ran it once).
- That `ValidationError` texts (approach run failed) never reach a worker. They embed the runner's text, which is harness-side today.

**Concerns (none blocking):**
- `test_zz_no_error_text...` depends on file order: it needs at least 8 texts collected by earlier tests. It fails rather than passing silently if run alone or in random order.
- Its date regex (`\d{4}-\d{2}`) would miss forms like `20190715`.
- `determinism()` never checks that the reverse job's returned bars equal the requested sample (`zip(strict=True)` over the returned bars only). A backend that called fewer bars would pass.
- The subprocess backend accepts only sources whose sha256 matches a repo or fixture file. Worker-written approach sources under `approaches/<id>/` will therefore raise `ValidationError` in stage 5 until step S2.2's backend.
```
