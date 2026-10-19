# REVIEW-20 — cold review of mission 20 (step S4.2a)

Base: `9bec52a` (`review: mission 19`, the last `review:` commit). Range
`9bec52a..origin/main`, tip `1e639ec`. Unit commits: U1 `431a82e` `table:`,
U2 `becb570` `alerts:`, U3 `e8d31bb` `bars:`, U4 `9269ad7` `alerts:`, U5
`6833101` `coordinator:`. Read for forbidden edits only: `b6a6c64`, `a277c25`,
`f1b8346`, `ccbeeab`, `4ed47b4`, `3c317f4`, `5ca133c`, `a39bbde`, `786ffb6`,
`d67f708`, `50d935b`, `0d55156`, `78b5535`, `2a614bd`, `5c272ab`, `8dacfe7`,
`1e639ec`. `a277c25` (owner decisions), `f1b8346` (kit) and `a39bbde`
(PLAYBOOK.toml, owner) are the owner's or architect's commits. The builder's
commits touch only `meta/plan.md`, `meta/CHECKPOINT.md`, `meta/journal.md`,
`meta/findings/FINDINGS.md` and `meta/FINAL-REPORT-20.md`.

`git diff 9bec52a origin/main` is empty for: `tests/gates/`,
`tests/fixtures/rejected/`, `tests/fixtures/config_frozen.json`,
`config/thresholds.toml`, `config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/spreads/`, `config/models.toml`,
`pyproject.toml`, `uv.lock`, `DESIGN.md`, `SPEC.md`, `.claude/`,
`templates/`, `docs/`, `meta/ARCHITECT.md` and `meta/REVIEW-PROTOCOL.md`.
`config/run.toml` and `tests/fixtures/config/run.toml` each gain only the
same `[coordinator]` table (decision 163 (b)). `config/protected_paths.toml`
is the one new file under `config/`.

## Gate

not a closing mission

## Blockers

1. DESIGN QUESTION: does decision 2026-10-17-m19 153 (b) 2's `p(N)` on the
   alert-rules panel count as "a recomputation of a rule's figure on the
   page", which decision 160 orders removed? The page still recomputes the
   `persistent_approach` rule's `p(N)` from the thresholds in force and the
   trial count at `src/discotrade/dashboard.py:472`
   (`stats.tightened_percentile`), the same figure the rule computes at
   `src/discotrade/alerts.py:581` and keeps only in its payload. No state
   entry holds it. U4's body says this openly and keeps it under 153 (b) 2.
   But two decisions disagree here, as they did in D-018, and that calls
   for a finding, not a choice made in the code. No finding was filed.
   `meta/FINAL-REPORT-20.md`'s acceptance line ("the page recomputes no
   rule's figure … Met") carries no caveat, and the disk contradicts it.
   Failure scenario: `alerts.persistent_base_percentile` or
   `alerts.false_alerts_per_year` gains a history entry after `D`. The page
   rendered later for `D` then shows a `p(N)` that the rule did not use on
   `D`. This is the defect class of D-018.

## Should-fix

1. U3's ratio holds only in runs picked for low load. At `e8d31bb`, the
   body's own runs at the commit give ratios up to 2.104. Only the quiet
   runs land at or below 1.25 (1.237, 1.234, 1.246; margins 0.004 to
   0.016). The parent's runs themselves span 1.189 to 1.461. Decision 158
   ("above 1.25 at U3's commit, U3 fails") does not say which run counts,
   and the report lists the U3 figure under NOT PROVEN. The tip's runs
   (1.166, 1.177, 1.190) meet it. The measure is load-sensitive enough that
   the 1.25 rule does not decide anything on this machine. The architect
   should fix which figure binds: for example, the median of k runs, CPU
   time, or a stated load bound.
2. `tests/test_cli_provider.py::test_an_unknown_coordinator_is_a_usage_error`
   now passes for the wrong reason. Since U5, `claude` is a known
   coordinator, and the test gets exit 2 only through the missing-key
   refusal.
   - With `ANTHROPIC_API_KEY` set and a `claude` on `PATH`, it fails. U5's
     reviewer saw `('replay', '') assert 0 == 2`, and a
     `ClaudeCodeCoordinator` was built around the real
     `/home/msi/.local/bin/claude`. No call was made, because the provider
     was none.
   - Item 146 (c) rightly kept the test unchanged, and the report mentions
     the dependency. But no finding was filed asking for a decisions item to
     correct it. A test that resolves the real binary when a key is present
     is one step from I-11's "never a real `claude`".
3. The fix-session deny rules cover `Edit` only.
   - `coordinator.fix_session_command` (`src/discotrade/coordinator.py:524`)
     starts the session with `--permission-mode acceptEdits` and no tool
     restriction. Bash, and any filesystem command `acceptEdits`
     auto-approves, are not denied, so `Edit(...)` rules alone do not stop
     a protected path from being written.
   - Nothing calls it while `propose_fixes = false`. Still, the report's "every
     path in it is denied by the generated settings" holds only for the
     editing tools.
   - Before G4.4 (S4.3), the command should restrict tools (`--tools`)
     or deny `Bash`, or the claim should be narrowed.
4. `gaps._MONTH_MISSING`'s content identity is not pinned by any test.
   - Decision 157 (a) asks that "a test shows it for each cache".
   - U3's reviewer removed the index entry's `rows` and `hash` from the key
     at `src/discotrade/bars/gaps.py:205-207`, and `test_gap_months` and
     `test_bar_day_run` stayed green (12 passed).
   - It is harmless today: `BarStore.append` writes only after the last
     stored bar, and a revised complete month is refused by verification
     before the cache is read (`test_a_revised_complete_month_is_refused`).
     But the key's only guard is untested.
   - The other caches each have their wrong-key test: `_CARRIED`,
     `_OPEN_DAYS`, `_MONTH_CONTRACTS`, `_SPLITS` and the table's exposure
     cache.

## Notes

1. Checks in this review. Five sub-agents ran at once on 4 cores, so four
   of the five `./scripts/check` runs went past the 20-minute cap and were
   killed in the background. Results:
   - U4 (`9269ad7`): one whole run, `check: green`,
     `2513 passed, 204 deselected in 1119.24s`.
   - U3 (`e8d31bb`): the reviewer re-ran it alone, `check: green`,
     `2504 passed, 204 deselected in 969.53s`, 973 s wall, sandbox
     `discotrade-sandbox:3b7d75c39621`.
   - U1, U2 and U5: green in two parts that together cover the whole suite
     (ruff and a prefix of pytest with no F, E or s, then the rest in the
     foreground: 1182, 1077 and 345 passed, plus the smoke steps). No
     single `check: green` line was seen at those three commits in this
     review. Each builder body reports 3/3 green.
2. D-021 (filed by U3): since U1, `table.adjusted_deflated` with exposure
   gives a different `adjusted_E_N` from the parent for a slot holding two
   paper rows of one date. The parent kept the last row per date. The
   writers never produce such a record, and 157 (d)/(e) show the G1.3
   replay is bit-identical. Decision 158 binds "the inputs a met gate
   gives", so this is a finding for the owner, not a breach. U1's reviewer
   confirmed the byte-identical state on a 2019-06-03..06-21 replay
   (parent vs commit: empty `diff -r`, equal HEAD tree).
3. At `becb570`, O-4's subtraction ran in `alerts._less_exposure_rows`,
   outside `paper.py` (decision 97 (c)). U3 moved it to
   `paper.less_exposure_rows`, so the tip conforms.
4. U3 left `dashboard.py` unchanged on a profile of one early and one late
   day (render 0.093/0.041 s at the parent). It met the "dashboard cache not
   cleared" wrong change by removing `_t_critical`'s registration. The brief
   allows both ("or as U3 says"; decision 158's "the measurement shows
   growing").
5. `config/protected_paths.toml` holds decision 164's minimum plus
   `src/discotrade/coordinator.py`. It does not hold `config.py` (which
   loads the file), `workers/providers.py` (which filters the child's
   environment), or any of CLAUDE.md's never-edited documents. Decision
   164 does not require them. The architect may extend the list before
   G4.4.
6. Minor:
   - `alerts.py:746` and `:763` write the literal `"p"` rather than
     `RANK_P`.
   - `scripts/speed.py`'s day seconds leave out its own bookkeeping, where
     156 (b) says "from the end of the previous day". The U1 body calls the
     design silent there.
   - `max_turns` is read but not passed, because the installed help has no
     `--max-turns`. The body and the run.toml comment say so, as 163 (a)
     asks.
7. The mission stopped at U2 (HF-016) and resumed under §R. The owner traced
   the stop to `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`, not the hook.
8. hands: this reviewer's sub-agents met HF-015 again. The harness refused
   the lone `sleep 240` that decision 159 (d) prescribes, and each waited
   with a foreground poll loop instead.
9. hands: the protocol's "one sub-agent per unit commit" run five at once on
   a 4-core machine pushes every ~18-minute check past the 20-minute cap
   (HF-006, HF-012). The protocol says nothing about how many run at once.
10. hands: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered
    worktrees (HF-010). This review's own worktrees were removed.

## Per-commit verdicts

### 431a82e (U1, `table:`)

I found no blocking defect in 431a82e (mission 20 U1). The one gap is that I could not get `./scripts/check` to finish as a single run, so it is green only across two runs that together cover the whole suite.

1. **Unit: PASS.** It is U1 `table:` and claims DESIGN 10.4, 11.2 and 16.4, invariants I-6, I-12 and I-14, and decisions 156, 157 and 158.
2. **Test-first: PASS.**
   - With the product files put back to the parent, the 12 new tests are all red (`clear_caches` is missing, `speed.py` is gone).
   - Keying the table cache by path only turns `test_a_rewritten_file_of_the_same_length_is_read_again` red, and the equality test too: the 2019-06-05 replay fails with "the exposure records … hold no 2019-06-05".
   - Dropping the table caches' registration turns `test_clear_caches_names_and_empties_every_cache` red. The equality test stays green, as the commit body says.
   - `tests/test_speed_equality.py` does what 157 (c) asks: warm vs cold (caches cleared before every day), all 5 day trees compared, and the named files byte-equal on 06-03, 06-06 and 06-07. It only compares the new code with itself, though, so it cannot show the new `adjusted_deflated` path equals the parent's. That is 157 (e)'s job, so I checked it myself: a 2019-06-03..06-21 replay (admit, displaced, retired) at the parent and at the commit gave an empty `diff -r` and equal HEAD tree and per-day trees (f2285f7e…), with non-null E_N and adjusted_E_N figures.
3. **Check: PASS (split, with a caveat).**
   - The sandbox image was already present (discotrade-sandbox:3b7d75c39621).
   - The full `./scripts/check` passed ruff and every test file through `test_rolls` with no failure or skip. Partway through `test_sandbox_container` the harness moved it to the background and then killed it at its time limit; other reviewers' check runs were loading the machine.
   - The harness also refused the brief's lone `sleep 240` wait, so I waited with a foreground poll loop instead.
   - The rest of the suite, from `test_sandbox_container` on, ran as one foreground call: `1182 passed in 388.45s`, 0 skipped. The three smoke commands passed (`discotrade 0.1.0`, `config check: ok`).
4. **Design: PASS.**
   - **Cache key:** the exposure cache reads every byte each time, keys on resolved path + (length, sha256), and parses the bytes it hashed, so it cannot serve stale figures. It holds one state dir and track at a time, and `staging/` is a fixed path, so it does not grow.
   - **Invariants:** the cached frames are only filtered, never mutated. No network, secret or market name, no wall clock in results (`scripts/speed` uses `perf_counter` only), it refuses a work dir inside the repo, and pyproject.toml and uv.lock are unchanged.
   - **Minor:** in the new `table.py` `adjusted_deflated` slot branch (around line 385), a slot with two paper rows of one date would give a different Sharpe from the parent: the parent's `control_moments` kept the last row per date, the new code feeds every row. `_by_subject` in `build` guards against this and the slot branch does not. It is not reachable unless paper records repeat a (subject, date).
   - **Minor:** `days.jsonl` seconds leave out the per-day bookkeeping and the before-last copy, while 156 (b) says "from the end of the previous day". The body calls the design "silent" there, which slightly overstates it.
5. **Forbidden touches: PASS.** The commit touches only its 14 files, all listed in the body. Nothing under `tests/gates/`, the fixtures or `config/`, and no plan or checkpoint file. It needs no `return_readers.toml` entry; `adjusted_deflated` still calls `paper.adjusted`, and the audit passed.

**Not proven:** the full 267-day 157 (d) and (e) comparisons, the speed figures and G1.3's 898 s are the builder's numbers, which I did not rerun.

### becb570 (U2, `alerts:`)

becb570 (mission 20 U2, `alerts:`). Verdict: PASS on all five points, with one caveat: I could not run `./scripts/check` as one uninterrupted call. Worktree `/tmp/rv20/wt-becb570` is removed.

1. **PASS.** The unit is U2, "Step 6 without growth" (O-26 items 2, 3 and 5, O-27 item 2; decisions 157 to 159). It claims DESIGN §15.1 to §15.3 and §16.1 step 6, and touches I-6 and I-12.
2. **PASS.** With `alerts.py` and `state.py` reverted to the parent, 7 tests fail and 7 pass: 6 of the 8 new tests, plus `test_caches`' names test. The audit also goes red because `slot_moments` no longer exists. The two that stay green are the two-rows-of-one-date test and the missing-unit-day test, as the body says.
   - Wrong change from the brief (dropping `state.register_cache("discotrade.alerts._SPLITS", …)`): `test_clear_caches_empties_the_split_cache` and `test_clear_caches_names_and_empties_every_cache` go red, and `test_speed_equality` stays green, matching the body.
   - My own extra wrong change (cache key reduced to the row count, no hash): `test_a_changed_value_of_the_same_length_is_split_again` goes red.
3. **PASS, but in two parts.** `sandbox build` gave `discotrade-sandbox:3b7d75c39621` (present, nothing built). The single `./scripts/check` call passed the 20-minute cap and was moved to the background. The harness refused a lone `sleep 240`, so I waited with a foreground poll loop instead, and the harness then killed the run at its background limit. By then it had passed ruff and reached about 56% of pytest (into `test_sandbox_process.py`) with no F, E or s. Another reviewer's check was running on the machine at the same time.
   - I then ran every remaining test file from `test_sandbox_process.py` on: `1077 passed in 323.28s`, 324 s wall.
   - ruff gave "All checks passed!", and the smoke steps passed (`discotrade 0.1.0`, `config check: ok, 173 unverified values`).
   - **NOT PROVEN:** one uninterrupted `check: green`, its total wall time, and the combined skipped count. The container tests did run in the second part.
4. **PASS.** No network, secret, wall clock, writes into the repo, market names or new dependency (pyarrow was already a runtime dependency).
   - **Stale-cache question:** I found no path that serves stale splits. Each split depends only on the columns that are hashed. The key is per role and per (resolved state dir, track), and takes the row count plus a length-prefixed sha256 of the column name and bytes. Text is NUL-joined with a lengths array, so the encoding is injective. Values not exactly `str` or `date` take the fallback. The `memo` matches by object identity and lives for one `persistent_approach` call, over frames that call does not change. The `nears` dict in `rank_rows` lives for one block, over a fixed exposure.
   - **Equivalence with `paper.adjusted`:** the fast path does the same operations in the same order. That covers the frame-order pairwise sum in `hbar`, the `0.0 +` accumulation, later unit rows replacing earlier ones, and the missing-day message.
   - **Edge (not a defect for records the writers produce):** `_column(..., "int")` casts `rows` to int64, so a fractional or NaN `rows` would truncate or raise where `paper.hbar` would not.
5. **PASS.**
   - The commit touches nothing forbidden: no `config/`, gates, rejected fixtures, `tests/fixtures/config`, `config_frozen.json`, `plan.md`/`CHECKPOINT.md` or `pyproject`/`uv.lock`. Those last two meta files do differ between 9bec52a and becb570, but only through the builder's own `meta:` commits, not this one.
   - The body lists all 6 files.
   - **`return_readers.toml` vs `tests/test_return_readers.py`:**
     - `slot_moments` is added as `producer`, matching `stats.control_moments`, which is also `producer`.
     - `slot_series` stays `adjusted` with a changed note, and the audit passes. It only passes because `slot_series` still calls `paper.adjusted` on its fallback path.
     - **Design note:** the fast path now does O-4's subtraction itself in `alerts._less_exposure_rows`, outside `paper.py`. That works around decision 97 (c)'s rule that adjusted series compute through `paper._less_exposure`. It may be worth a reviewer note.
     - `rank_rows` and `persistent_approach` were changed but were already registered, and their notes still hold.

### e8d31bb (U3, `bars:`)

sha e8d31bb (mission 20 U3, `bars:`). Verdict: the code is sound, with one test gap; the check run did not finish; the ratio claim is weak.

1. **PASS:** the unit is U3 (O-26 items 2 and 4, decisions 157, 158, 159). It claims DESIGN 5.2, 5.4, 5.6, 10.4, 11.1, 15.5, 16.1 and 80 (b). Leaving dashboard.py unchanged is allowed: decision 158 limits U3 to modules "the measurement shows growing", and the body's profile has render flat (parent 0.093/0.041 s, commit 0.133/0.042 s). That evidence is only one day early and one day late. The `bars:` area is allowed ("or as U3 says"). The dashboard wrong change was met by removing the existing `_t_critical` registration.
2. **PASS:** with the parent's src/, 16 of the 32 tests in the six new or changed files fail: bar_carry 5, gap_months 2, rolls_months 3, trading_dates 5, caches 1. test_table_slots passes there, as the body says (it pins the parent). Wrong change "_MONTH_CONTRACTS registration removed": 2 red. Wrong change "rolls key without the index entry": 2 red. **Gap:** dropping rows and hash from the `_MONTH_MISSING` key (src/discotrade/bars/gaps.py:205-207) stays green (gap_months and bar_day_run, 12 passed). It is harmless today, because a complete month cannot change once a later bar is stored. Still, 157 (a)'s "a test shows it for each cache" is unmet for this key.
3. **NOT PROVEN:** sandbox build gave `discotrade-sandbox:3b7d75c39621` (present). `./scripts/check` passed ruff and was at 61% with no F or E when it was killed. The 20-minute foreground cap moved it to the background, and the background time limit killed it, so no pytest summary line or exit code exists (my parallel revert runs added load).
4. **PASS:** each cache can serve a stale value only if its inputs change without detection, and none can:
   - `_CARRIED` serves a frame only when the path, index rows/hash and the file's length and sha256 all match again; mutated or same-length rewritten bytes are re-parsed and refused.
   - `_MONTH_MISSING` and `_MONTH_CONTRACTS` read every month file through `month_frames` (verified) before the cache is used. The content hash covers all 7 columns, so a contract edit changes the key.
   - `_OPEN_DAYS` is keyed by the whole frozen Calendar record and bar size, so a changed record is decided again.
   - All four are cleared per store root and by `state.clear_caches`.
5. **PASS, equivalence:** the one-contract shortcut gives the same result as the full scan (0 or 1 distinct contracts means `detect_rolls` finds nothing; same reads, same refusals). Splitting `find_missing` by month is exact because `expected_bars` is a filter on [start, end). In the table batch, `mine` is sorted by date and uses the same IEEE order.
6. **PASS, invariants:** no wall clock, network, secret, I-9 name, new dependency or state written in the repo.
7. **PASS:** forbidden files are untouched by this commit (config/, tests/gates, tests/fixtures, pyproject.toml/uv.lock, DESIGN/SPEC, plan/CHECKPOINT). The return_readers.toml change in 9bec52a..tip comes from other commits. The body lists every file. No register change is needed: `adjusted_deflated` is already registered as adjusted, and the new functions hold no reference shape.
8. **Not proven, ratio:** 7 of the 9 commit runs were above 1.25 (up to 2.104). Only the two quiet-load runs c7 and c9 (1.234, 1.246) pass, so the result is selected by load. The parent's own runs range from 1.189 to 1.461. The gate's "retry once then blocked" rule is met only by this selection; I did not re-measure.

Both worktrees are removed.

(Reviewer's addition: point 3 re-run by the reviewer alone at e8d31bb after the sub-agent ended: `check: green`, `2504 passed, 204 deselected in 969.53s (0:16:09)`, 973 s wall, sandbox `discotrade-sandbox:3b7d75c39621`.)

### 9269ad7 (U4, `alerts:`)

9269ad7 (mission 20 U4, `alerts:`): it mostly passes, but the dashboard still recomputes one rule's figure, `persistent_approach`'s p(N), so the acceptance line "the dashboard recomputes no rule's figure" is not met as written.

1. **PASS:** the unit is REVIEW-19 should-fix 1 and 2 (decisions 160 and 161, finding D-018). It cites DESIGN 15.3 and 15.5, and decisions m19 152 (a) and 153 (b) 1 and 7. The change matches decision 160's reading: `p` is added to the `rank_persistence` entry only, and `ENTRY_KEYS` still has four keys.
2. **PASS:** with alerts.py and dashboard.py put back to the parent, 9 of the commit's new or changed tests in test_alerts.py and test_dashboard.py went red (67 passed). The health-panel test stays green there, as it should: decision 161 only adds a test. Both wrong changes went red:
   - `window = 20` at dashboard.py:580: 1 failed.
   - The page computing p from `t_crit*value/threshold`: 2 failed (the held-p test and the no-p test).
3. **PASS:** sandbox build said `present, nothing built`, tag `discotrade-sandbox:3b7d75c39621`, so the container tests ran. `./scripts/check` printed `check: green`, `2513 passed, 204 deselected in 1119.24s`, no skips, 1122 s wall. My first attempt (output piped to `tail`) passed the 20-minute cap, went to the background, and the harness killed it. The lone `sleep 240` the brief prescribes was refused by this harness (HF-015). I ran it again in the foreground, logging to a file, and that run is the one quoted.
4. **PASS, with one defect:** I found no breach of I-9, I-10, I-11, I-12 or I-14, and pyproject.toml and uv.lock are unchanged. The two pre-existing tests changed only by adding `"p": None` and are still exact equalities, so nothing was loosened (146 (c)). The defect:
   - dashboard.py:472 still computes `stats.tightened_percentile(n, base, per_year)`. That is the same p(N) that `persistent_approach` computes at alerts.py:581 and keeps only in its payload.
   - This goes against decision 160's "every other recomputation of a rule's figure on the page are removed" and the acceptance line.
   - The body says this openly and defends it with 153 (b) 2, but where two decisions conflict that is a finding to file, not a choice made in code (as with D-018).
   - Failure scenario: `alerts.persistent_base_percentile` or `alerts.false_alerts_per_year` changes with history after D. The page then shows a p(N) the rule did not use on D.
   - The rank chart's band (dashboard.py:268) is an expanding-window display figure, not the rule's last-`rank_blocks` threshold, so it is not a recomputation.
   - Minor: alerts.py:746 and :763 write the key as the literal `"p"` instead of `RANK_P`.
5. **PASS:** the commit touches 4 files and the body lists all of them. Nothing changed under tests/gates/, tests/fixtures/ or config/ between 9bec52a and the commit. `return_readers.toml` changed in that range only through earlier units. U4 adds no function with a reference shape, and the audit passed inside the check. The body gives G1.3 (534 s, `10 passed in 532.18s`) and speed (ratio 1.177, at most 1.25) with load.

**NOT PROVEN:** I did not re-run G1.3 or `./scripts/speed`, so the body's figures are unverified. I did not re-run test_speed_equality on its own; it was only inside the green check. The worktree is removed.

### 6833101 (U5, `coordinator:`)

I reviewed 6833101 (mission 20 U5, `coordinator:`). It passes on points 1, 2 and 5, but point 3 and three parts of point 4 are not fully met, so the unit is not clean.

1. **PASS.** The unit is U5, the Claude Code form of the coordinator. It claims DESIGN §14.1–14.4, §16.3 and §19.3 L4, SPEC §17, decisions 163–166, and I-8, I-11 and I-13.
2. **PASS.** With the product files reverted, `tests/test_coordinator_claude.py` fails at collection (38 tests) and `tests/test_cli.py` plus `tests/test_doctor.py` give 15 failed, 70 passed. I made four of the wrong changes alone and reverted each; all went red:
   - skipping the offered-cell check: 1 failed;
   - dropping `ledger/` from the generated rules: 2 failed;
   - killing only the child (`child.kill()` instead of `os.killpg`): both process-group tests failed;
   - passing the key as `--api-key <value>`: 3 failed.
   I did not try the score-in-prompt change.
3. **NOT PROVEN, no failure seen.** The sandbox `discotrade-sandbox:3b7d75c39621` was present. `./scripts/check` passed ruff, then the harness moved it to the background and killed it at the 86% mark (`test_synth_cache.py`) on a machine shared with other reviewers. There was no F or E up to that point. I ran the remaining 345 tests in the foreground: 345 passed in 260 s, and the smoke steps passed (`config check: ok, 173 unverified values`). I have no single green `check: green` line. The brief's lone `sleep 240` was refused by the harness, so I waited with a foreground until-loop instead.
4. **FAIL.**
   - **I-11 (tests depend on the environment):** `tests/test_cli_provider.py:372` `test_an_unknown_coordinator_is_a_usage_error` only passes when `ANTHROPIC_API_KEY` is unset. With a dummy key and any `claude` on PATH it fails (`('replay','') assert 0 == 2`). The fixture's `binary = "claude"` resolves through `shutil.which`, and a real one exists at `/home/msi/.local/bin/claude`. A `ClaudeCodeCoordinator` was built, but no call was made because the provider is none. The body's "unchanged and passes" claim depends on the environment.
   - **Missing protected paths:** `config/protected_paths.toml` holds decision 164's minimum plus `coordinator.py`, but none of CLAUDE.md's never-edited list: DESIGN.md, SPEC.md, PLAYBOOK.toml, meta/ROADMAP.md, meta/BACKLOG.md, meta/ARCHITECT.md, meta/REVIEW-PROTOCOL.md, meta/BUILDER-*-PROMPT.md, meta/decisions/, .claude/, docs/ARCHITECT-HANDBOOK.md, templates/. Also missing: `src/discotrade/config.py`, which loads the file, and `workers/providers.py`, which filters the env. That is the same reasoning the builder gave for adding `coordinator.py`. Frozen config is covered by `config/`.
   - **Fix-session deny rules can be bypassed:** `coordinator.py` `fix_session_command` runs with `acceptEdits` and without `--tools ""`, so Bash stays available. The only rules are `Edit(...)`, and Bash can still write protected files. Nothing calls this while `propose_fixes = false`.
   - **The rest of point 4 is OK:**
     - I-8: the prompt is built from cells and registry lines only.
     - I-13: the key goes to the child by environment only.
     - `scripted` stays the default.
     - I-9, I-12 and I-14 are not touched.
     - No new dependency was added.
5. **PASS.** No forbidden file is touched and no frozen value changed. `tests/fixtures/config/run.toml` gains only the `[coordinator]` table. The body names all 13 files. There is no `return_readers` entry, and the audit was green.

Not proven: no real `claude` was run, so the flag help text, the `--max-turns` absence and the deny-rule enforcement are taken from the body only. The worktree is removed.

(Reviewer's reading of point 4: decision 164 (a) sets a minimum ("at least"), which the file meets, so the missing paths are Note 5, not a blocker. The I-11 item is Should-fix 2 (the check runs without the key, and no call is made). The fix-session item is Should-fix 3.)
