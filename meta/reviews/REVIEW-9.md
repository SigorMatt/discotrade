# REVIEW-9 — cold review of mission 9 (roadmap step S1.3, closes M1)

Base: 1c82dab (`review: mission 8`, the last `review:` commit). Reviewed:
`git log --oneline 1c82dab..origin/main`, tip 342107b. Unit commits
(one sub-agent each): 94e1294 (U1), 15754e9 (U2), d65964f (U3), 04aee87
(U4), 33cfe7a (U5), 984cc0c (U6), ae7158b and b62f5f0 (U7). Read by the
reviewer for forbidden edits only: 974b700 and 3c0b023 (`plan:`), 5acec56
(`plan:`, the owner's decisions file, the only file it touches, as O-file
preamble requires), 6163568 (`findings:`, `meta/findings/FINDINGS.md`
only), the `meta:` commits 0dc513e, 8ea9e0b, 6383f99, cd346c6, eec3025,
41e66c2, 768cb1c, 33414b8, 77f2ea3 (only `meta/CHECKPOINT.md`,
`meta/journal.md`, `meta/plan.md`, `meta/findings/FINDINGS.md`), and
342107b (`report:`). No forbidden file was touched. `git diff 1c82dab
origin/main` of `config/`, `tests/fixtures/config/`,
`tests/fixtures/config_frozen.json`, `DESIGN.md`, `SPEC.md`,
`PLAYBOOK.toml`, `.claude/`, `templates/`, `docs/`, `meta/ARCHITECT.md`,
`meta/REVIEW-PROTOCOL.md`, `pyproject.toml` and `uv.lock` is empty, and
`config/models.toml` does not exist.

## Gate

Gate M1: PASS

The brief says `This mission closes milestone M1`. Owner decision O-2
(`meta/decisions/decisions-2026-10-13-owner.md`) says how M1's gate is run:
`./scripts/gate M1 G1.1` to `G1.4`, each its own foreground call with a
20-minute timeout, all at the same pushed commit; PASS when all four print
their item PASS line. The reviewer ran them that way at 342107b (= origin/main;
its code is b62f5f0's, since every later commit touches `meta/` only), each
wrapped in `timeout 1190`, verbatim:

```
G1.3 PASS 10 passed in 1061.51s (0:17:41)
gate M1 G1.3: PASS
```
(exit 0; the call's own wall clock was mis-measured by the reviewer's
shell, pytest's 1061.5 s is the figure)

```
G1.1 PASS 6 passed, 1 warning in 877.14s (0:14:37)
gate M1 G1.1: PASS
exit 0 wall: 877 s
```
```
G1.2 PASS 4 passed in 321.46s (0:05:21)
gate M1 G1.2: PASS
exit 0 wall: 322 s
```
```
G1.4 PASS 15 passed in 0.51s
gate M1 G1.4: PASS
exit 0 wall: 2 s
```

The four items together come to about 38 minutes. O-2 waives §18.2's
15 minutes for M1 only.

Item by item, the gate tests against DESIGN §18.3 M1 and decision 74 (with O-1):

- **G1.1** (`tests/gates/test_g1_1_null_controls.py`): a one-year controls-only
  replay of `test_synth` on the gate configuration, 2019-06-03 to 2020-06-01,
  in-process. The four statistical clauses are asserted as written:
  - the mean summed gross is within 4 SE of 0 (ddof 1, over the 50 slots);
  - the mean summed cost is positive;
  - the mean summed `net_1x` is within 4 SE of minus the cost;
  - rank persistence over blocks 1 to 51 has at least 40 values not missing, with a mean within 4 SE of 0. It reads `gross`, as O-1 replaces `net_1x`. The net statistic is reported in a warning and asserts nothing, as O-1 says.

  `rank_persistence.jsonl` holds blocks 1 to 51. The seeds are asserted
  (instrument seeds 101 to 104, pool seeds 201906 to 202006), and the dates
  are written in the file. The test asserts no less than its item.
- **G1.2** (`test_g1_2_recompute.py`): the G1.3 scenario replayed from
  2019-06-03 to 2019-08-02, 60 calendar days. The state is asserted to hold approaches, controls, three monthly draws, blocks and lifecycle rows. Then:
  - `journal recompute --all` exits 0, and its pair count equals the pairs read from the day files by pyarrow;
  - a re-run of the last day leaves every file's bytes and `HEAD` unchanged;
  - a fresh second replay gives identical bytes and the same `HEAD` tree.

  The test asserts no less than its item.
- **G1.3** (`test_g1_3_lifecycle.py`): the scenario
  `tests/fixtures/scenarios/g1_lifecycle.jsonl`, replayed 2019-06-03 to 2020-06-10 in three segments. Every transition of §10.3 appears in the 15 lifecycle rows and 6 trial rows, which the test lists in full and in order:
  - admission into a free slot;
  - displacement of the weakest;
  - refusal for `not_positive` and for `too_few_trades`;
  - dormancy;
  - return;
  - retirement on failure, and after the dormant limit (365 calendar days).

  It also shows:
  - one row per event;
  - each ledger's earlier bytes are a prefix of its later bytes;
  - the portfolio series on every journaled day equal the test's own count;
  - `table.json` on three days equals the test's own count field by field, with Sharpe, drawdown, breakeven and E(N) computed in the test from pyarrow and json reads, not through `table.py`, `stats.py` or `paper.py`.

  The test asserts no less than its item. A minor gap: the random pool's seeds are not asserted as literals here, though G1.1 and G1.2 assert them (Notes).
- **G1.4** (`test_g1_4_deflation.py`): `E(N)`, the excess, `p(N)` at the production thresholds (asserted from `config/thresholds.toml`) and the §11.4 threshold, for N in 0, 1, 2, 10 and 1000. Each equals a literal worked out in the comments, to 1e-12 under decision 39's rule. The test re-derives the literals with its own bisection quantile, and asserts the published quantiles. The test asserts no less than its item.

No special case in product code serves a gate test. The U7 sub-agent
grepped `src/` and found none.

The wrong changes were seen to fail through the gate by the U7 sub-agent:
`E(N)` without the floor (`G1.4: FAIL`), and a recompute skipping
controls (`G1.2: FAIL`, `1 failed, 3 passed`). For zero costs (G1.1) and
step 4 in trading days (G1.3), the reviewer's side read the assertions
but did not run the gate. The builder reports both red (FINAL-REPORT-9).

## Blockers

None.

## Should-fix

1. **U3 (d65964f): the per-day paper update no longer heals an interrupted day, and the docstring claims more than the tests show.**
   - **The claim:** `src/discotrade/daily.py:41-42` (and the commit body) says `paper.update` is "equal to a rebuild from the whole journal". The test (`tests/test_daily.py`) shows that only for uninterrupted runs.
   - **The failure:** `_move` (`src/discotrade/daily.py:235`) moves staged files one by one in path order, so `journal/` lands before `paper/`. If the process dies between those moves, the re-run of that day reports "already journaled" and leaves the stale paper file. The next day's `paper.update` (`src/discotrade/paper.py:229-244`) only falls back to `rebuild` when the stored max date is on or after the new day. So it appends the new day, and the interrupted day's records and portfolio rows are lost from the derived file until something rebuilds it. Before U3, the per-day rebuild repaired this on the next day.
   - **The fix:** fall back to `rebuild` whenever the stored dates are not exactly the journal index's dates before `D`, with a test that removes a day's paper rows and runs the next day. Or narrow the docstring and the claim to uninterrupted runs.
   - **Context:** the move not being atomic is older than this mission (§16.2; FINAL-REPORT-8 carries the interrupted-run items). This item is only about what U3 removed.
2. **U2 (15754e9): no test covers the part of the new not-closed refusal that protects I-2.**
   - `_unclosed` (`src/discotrade/daily.py:158-173`) refuses `D` when any instrument has an unclosed expected bar of any trading day on or before `D`.
   - The U2 sub-agent narrowed it to `D`'s own bars (`day_end(cal, day - timedelta(days=1))`), and all 45 tests of `tests/test_replay.py` and `tests/test_daily.py` stayed green.
   - The only refusal test (`tests/test_replay.py:318`) refuses on SYNX's own bar of `D`. No test covers an instrument that does not trade on `D` but has an earlier day still unclosed: for example, SYNA's Friday under a delayed source while SYNX's Saturday has closed. That is the case in which `run-day` would otherwise run a day before all its bars have closed.
   - The commit body's "for a track on one calendar this refuses exactly the days the old check refused" is reasoning only; no test enumerates it.
   - Add the missing case as a test. The rule itself still waits on D-007's answer.
3. **U6 (984cc0c): decision 73's "T's trading days those §4.1 gives for D" is stated in the commit body but untested.**
   - No test asserts the days `replay.t_days` (`src/discotrade/replay.py:127-132`) passes to the admission function.
   - With a candidate dated `D`, a wrong window would change the weakest live approach's Sharpe on T, and so the `displaced` / `not_better_than_weakest` verdict. In G1.3 the displaced approach has a Sharpe that is not a number, so any window gives the same verdict.
   - Add a test that pins the T days for a `D` whose 7-day window holds a weekend, and an admission whose verdict depends on them.

## Notes

- **Re-run checks.** Three sub-agents (U5, U6, U7's b62f5f0) could not finish `./scripts/check` within 1180 s, nor could ae7158b's, because four ran at once on a 4-CPU machine. The reviewer re-ran each one alone, in a worktree at the commit, in the foreground, each its own call:
  - 342107b (code = b62f5f0): `check: green`, 630 s;
  - ae7158b: `1221 passed, 121 deselected`, `check: green`, 651 s;
  - 984cc0c: `1221 passed, 86 deselected`, `check: green`, 638 s;
  - 33cfe7a: `1205 passed, 86 deselected`, `check: green`, 611 s.

  Every unit commit is therefore green at least once. No reviewer run reproduced the builders' "three in a row".
- **Gate M1 at ae7158b:** U7's first commit was pushed with G1.1's rank-persistence test red (D-008), which its body says openly. The owner answered with O-1, and b62f5f0 turned it green. Gate M1 passes at the tip, not at ae7158b.
- **Margin on G1.3:** 1061 s here and 1083 s for the builder, against the 1190 s `timeout` and the 1200 s tool limit. A slower machine or any added per-day cost turns it into "did not finish", which is a FAIL under O-2. O-3's speed work in the next mission is what keeps it passing.
- **The net statistic O-1 asks G1.1 to report** goes into a pytest warning. `scripts/gate` prints only pytest's last line, so a gate run shows "1 warning" and never the value. To be readable, it needs `-rw` or a line of its own.
- **D-007 is still open** (`run-day`'s refusal with decision 72's clock). The architect should confirm it together with should-fix 2.
- **Unit commit bodies.** These are minor overreaches, and none is a blocker:
  - U1 says "Every other assertion of the three files is unchanged". `create_connection` was dropped from the scratch `network` test as decision 67 requires, and the body says so under that file.
  - U4 says "hand and run-day tests red" for the members-after-D change, but the run-day count test stayed green; only the rebuild-hash test (which goes through `run-day`) went red.
  - U6's "four cases" of a refused source are four of six parametrised cases.
- **Coverage gaps that are not required by the brief:**
  - U4: a block row due on a weekend day (`test_synth` trades weekdays only).
  - U6: the source-confinement refusal of a symlink and of a `..` path is right by hand-check, but no test covers it.
  - U1: decision 68 (b) with the day's admission doing the displacing. FINAL-REPORT-9 lists this under NOT PROVEN.
- **G1.3 does not assert the pool seeds** (201906 onward) as literals, as G1.1 and G1.2 do. Its docstring cites decision 64's month rule instead. These seeds are a deterministic rule, not chosen values, so the item still holds.
- **The FINAL-REPORT-9 base is 974b700** (the kit), and this review's is 1c82dab (the last `review:`). Between them lies only the kit commit, which is the owner's.
- **FINAL-REPORT-9 NOT PROVEN against the sub-agents' findings.** Everything the sub-agents found unproven is either listed there or added above, except:
  - should-fix 1 (the paper update after an interrupted move), which is not listed;
  - should-fix 2's untested branch, which is not listed;
  - should-fix 3, which is not listed.
- **hands:**
  - `.claude/hooks/no_background.py` refuses an `Agent` call whose `run_in_background` is omitted. The protocol says "in the foreground" but not that the flag must be passed as `false`. The first dispatch of four sub-agents was refused for this.
  - The protocol's one-sub-agent-per-commit with `./scripts/check` (about 10.5 minutes alone) does not fit in a 20-minute call when four sub-agents share a 4-CPU machine. Three timed out twice. The U4 sub-agent reported that its over-limit check was moved to the background by the harness and finished there, which the no-background rule is meant to prevent. The protocol could say to dispatch the sub-agents one or two at a time, or have the reviewer run each commit's check alone.
  - The protocol's `## Gate` text assumes one `./scripts/gate <M>` call; O-2 changes that for M1 only. A protocol line for items run one by one would help the next long gate.

## Per-commit verdicts

### 94e1294 (U1)

```
**Review of 94e1294 (mission 9 U1): pass, one minor wording issue in the commit body.**

1. **Unit:** mission 9 U1, which takes REVIEW-8 should-fix 1 and 2 and decision 68 (b). It cites decisions 63, 66, 67 and 68, I-11, and DESIGN §10.3 and §18.1, which matches the brief. Only the three allowed test files change; `src/` is untouched.
2. **Test-first: red as required.** Switching revival in `src/discotrade/lifecycle.py:210-212` to calendar days (`(day - s.since).days < revival`) fails the new test at `tests/test_lifecycle.py:204`, which returns on 2019-06-11 (1 failed, 25 passed). Wrapping `gethostbyaddr` in a pass-through lambda inside conftest's `_put_lookups` fails the scratch test, and so does leaving it guarded. Both changes were restored. I worked out by hand that the 68(b) test catches counting dormancy from the first dormant row (it would return 4 days after D); I did not run that change.
   - **Removed lines:** the marked network test no longer calls `socket.create_connection`, and it no longer calls `gethostbyaddr`. Both removals are required by decision 67. Connecting through `socket.socket` and `_socket.socket` is still shown, now using a numeric `getaddrinfo` result. No other assertion was weakened.
3. **`./scripts/check`: green.** Last lines: `config check: ok, 168 unverified values` / `check: green`, with pytest at `1143 passed, 86 deselected in 926.42s`. I ran it once.
4. **Design conformance: pass.** The scratch test touches only loopback, its `getaddrinfo` uses `AI_NUMERICHOST|AI_NUMERICSERV`, and nothing reads a secret (I-11). No `src/` change (I-9). Thresholds are read from `config/thresholds.toml` and the test asserts revival is 5 (I-10). No wall clock (I-12). Writes go only to pytest tmp directories (I-14). No new dependency.
5. **Forbidden files: none touched.** The commit changes only `tests/conftest.py`, `tests/test_lifecycle.py` and `tests/test_offline.py`; no `config/` value changes.
6. **Commit body:** it lists all 3 files, and the wrong changes it says it saw fail are the ones the brief names. One overreach: "Every other assertion of the three files is unchanged" is not literally true, because `create_connection` in `test_marked_network_connects` (in `test_offline.py`) was replaced, though the body says so under that file. It should read "kept, except as decision 67 requires".

**Not proven:**
- The 68(b) test covers displacement by another approach's return, not by the day's admission. The brief only asks for "displaced later on D".
- `./scripts/check` was run once here, not three times; I did not verify the body's "green 3 of 3".
- That decision 67's lookups never reach a resolver comes from the code comments and C-library behaviour; no test proves it.

The worktree `/tmp/rv9-94e1294` is removed. Three other `rv9-*` worktrees are still in `/tmp` and are not mine, so I left them.
```

### 15754e9 (U2)

```
Review of 15754e9 (mission 9 U2, the replay command). It passes with one should-fix: the refusal change in daily.py is correct but no test pins the part of it that protects I-2.

1. **Unit and sections:** U2, step S1.3. It claims DESIGN §16.4, §16.1 and §3, decisions 2026-10-12 items 19, 51, 55 and 72, and I-6 and I-12. That matches the brief.
2. **Test-first: pass.** With replay.py removed and cli.py and daily.py put back to the parent, tests/test_replay.py fails at collection (`ModuleNotFoundError: discotrade.replay`). Reverting only daily.py gives 7 failed, 38 passed. The two named wrong changes both fail: `while d < last` gives 11 failed, 9 passed, and a clock at midnight UTC at the start of the day gives 15 failed, 5 passed.
3. **`./scripts/check`: green** (one run). Last lines: `config check: ok, 168 unverified values` then `check: green`.
4. **Design conformance: pass, with one gap in the daily.py change.**
   - Replay itself matches decision 72 and §16.4. I-9, I-11, I-12 and I-14 hold, and there is no new dependency.
   - The daily.py change is correct and safe for I-2, and decision 72 justifies it. `_unclosed` (src/discotrade/daily.py:128-143) refuses D whenever any instrument has an unclosed expected bar of a trading day on or before D. Since `last` is that instrument's latest closed day, the bars from `day_end(last)` to `day_end(D)` are exactly the unclosed ones. So run-day cannot run a day before all its bars have closed. D-007 records that this departs from the brief's "unchanged in what it does", and its status is open.
   - **Should-fix (the gap):** I narrowed the check to D's own bars only (`day_end(cal, day - timedelta(days=1))` at daily.py:141). Under that change all 45 tests in test_replay.py and test_daily.py still pass. The one refusal test (tests/test_replay.py:318) refuses because of SYNX's own Monday bar. No test covers the case where an instrument not trading on D still has an earlier day unclosed, for example SYNA's Friday under a delayed source while SYNX's Saturday has closed. That is the exact case that keeps I-2 safe, and it is unpinned.
5. **Forbidden files: pass.** The commit touches only src/discotrade/cli.py, src/discotrade/daily.py, src/discotrade/replay.py, tests/test_offline.py and tests/test_replay.py. No config or fixture values change.
6. **Commit body: pass, with one minor overreach.** It lists every file, the counts for the two wrong changes match what I got, and the gate claims are backed by the tests. It says "for a track on one calendar this refuses exactly the days the old check refused". The reasoning holds, but no test proves it; it rests only on the existing tests staying green.

**Not proven:** the case above (an instrument not trading on D with an unclosed earlier day), and the one-calendar equivalence claim. I ran `./scripts/check` once, not three times.

The worktree is removed and the main repository was not touched.
```

### d65964f (U3)

```
Review of **d65964f** (mission 9 U3). Verdict: pass with one should-fix. The worktree is removed and nothing in the repo changed. The `/tmp/rv9-15754e9` worktree still listed is not mine.

1. **Unit:** pass. It is mission 9 U3, the backlog items REVIEW-1 should-fix U6 and REVIEW-2 note U1. It claims DESIGN 5.2, 5.5, 9.3, 16.1 step 1 and 18.2, and decisions 4, 5, 18, 31 and 35.
2. **Test-first:** pass. Against the parent's source, 8 of 170 tests fail: the recover-scope, append-reads-once and once-per-run tests. The synth slice, day-by-day store and per-day paper tests stay green on the old code, which is fine for a pure performance change. The two named wrong changes both turn tests red:
   - Starting generation at the fetch's start (`origin = max(origin, start)`): 10 tests in `test_synth` fail.
   - Recover skipping unlisted files (`candidates = set()`): 8 tests in `test_bar_store` fail.
3. **`./scripts/check`:** green. Last lines: `config check: ok, 168 unverified values` / `check: green`.
4. **Design conformance:** pass, with one defect.
   - Readers are unchanged. `read_range` and `last_n` still hash every listed file they read and refuse unlisted files. `last_ts` hashes every listed file. Recover now reads fewer files, but `_verify_stored` (`store.py:286`) hashes every listed file before any write. `bars fetch` (`cli.py:304`) and step 1 (`daily.py:182`) are the only callers of `append`, so a revised earlier month cannot slip past.
   - Residual: `append` on its own no longer refuses a revised earlier month that the new rows don't touch. No current caller reaches it, and readers still refuse it.
   - I-5, I-6, I-9, I-10, I-11, I-12 and I-14 hold, and there is no new dependency.
   - **Defect: the per-day paper update is not identical to a full rebuild after a crash** (`paper.py:158`). `_move` (`daily.py:219`) moves files in path order, so `journal/` lands before `paper/`. If the run crashes between those two moves, the re-run of that day is "already journaled" and keeps the stale paper file. The next day then calls `update`, whose fallback only checks `max(stored date) >= day`. It keeps the stale records and the missing day is lost for good. The old per-day `rebuild` repaired this on the next day.
   - Possible fix: fall back to `rebuild` when the stored dates don't match the journal index before D.
   - Risk for U4: `update` is only valid while each day's records depend on that day's rows alone. That is true of `build` today, but portfolio rows built across days would break it.
5. **Forbidden files:** pass. Only `src/` and 4 test files changed, with no config or fixture values and no lines removed from tests. The `cli.py` change is justified: `bars fetch` lives in `_bars_fetch` there, and the brief requires `bars fetch` to build one source per run.
6. **Commit body:** pass with one overreach. Every file is listed, and the per-day timing is 3.702 s before and 2.480 s after, which is reported as not fitting 15 minutes. The overreach is the statement in the `daily.py:39` docstring and the commit body that `paper.update` is "equal to a rebuild from the whole journal". The 6-day test only proves this for uninterrupted runs.

**Not proven:** that the paper file matches a rebuild after an interrupted move (no test covers it); the per-day timing over a full year; that M1 fits in 15 minutes (the commit's own figures say it doesn't).
```

### 04aee87 (U4)

```
Review of 04aee87: **PASS**. I found no defects; there are two minor notes on the commit body. The worktree /tmp/rv9-04aee87 is removed. Two other worktrees from earlier reviews are still there and were not touched: /tmp/rv9-15754e9 and /tmp/rv9-d65964f.

1. **Unit:** mission 9 U4. The commit claims DESIGN 10.5, 9.3, 11.1, 16.1 steps 2 and 6, 16.2, and decisions 59, 62, 63, 69 and 70. That matches the brief. PASS.
2. **Test-first:** PASS.
   - **Parent source restored:** 5 of the 13 new tests went red, covering the hand-written cases, row order, the run-day count, the rebuild hash and the Monday block row. The no-portfolio-row tests, the no-early-row test and the re-run test passed on the parent source too, since there is nothing for them to catch there.
   - **Members taken after D's steps:** the hand-written test and the rebuild-hash test went red. The run-day count test stayed green, so the body's "hand and run-day tests red" is loose. Only the rebuild-hash test, which also runs through run-day, failed among those.
   - **Block row two days early:** the no-early-row test and the Monday test went red.
   - **Re-run appending again:** test_a_rerun_appends_nothing went red.
3. **`./scripts/check`:** it went over the 1200 s foreground timeout and the harness moved it to the background, where it finished with exit 0. Last lines: `config check: ok, 168 unverified values` / `check: green`. PASS.
4. **Design conformance:** matches decisions 69 and 70 exactly. PASS.
   - Members are approaches live from lifecycle rows dated before D with a paper row on D (`lifecycle.states(..., day)`). Means use `math.fsum` divided by the count, and trades are summed.
   - There is a portfolio row with zeros on every journaled day. The `clean` column follows `all()`, and there is no portfolio_clean row without a clean member.
   - The population after D's steps is states at D+1, live or dormant, with the lifecycle read from staging.
   - In `due_blocks` the last-day formula and the "block k-1 starts on or after the first journaled day" lower bound are both correct. The row is staged with the day and skipped on a re-run.
   - I-5, I-6, I-9, I-10, I-11, I-12 and I-14 hold. Test threshold changes are made on temporary copies. No new dependency.
5. **Forbidden files:** none touched, no change under config/ or tests/fixtures/config/, and no change to pyproject or uv.lock. PASS.
6. **Commit body:** lists all 8 files. The test_controls.py and test_paper.py changes only filter out the portfolio rows. In test_paper.py the filter is on a clean check, not a "subjects equal the journal's" check, but decision 69's clean rule justifies it. PASS, apart from the loose "run-day tests red" claim in point 2.

**NOT proven:**
- A portfolio row for an approach admitted on D, driven through the day loop: covered only by the hand-written test.
- A due-day off-by-one that lands on a weekend: test_synth only runs weekdays, so a block row written on Saturday would not be caught.
- The commit's "green three times" claim: I ran `./scripts/check` once.
```

### 33cfe7a (U5)

```
Review of commit 33cfe7a (mission 9 U5, the table). It passes on points 1, 2 and 4–6, but point 3 is not proven: both `./scripts/check` runs timed out on the shared machine.

1. **Unit and sections:** the unit is named correctly. The commit claims DESIGN §10.4, §8, §11.2 and §16.2, and decisions 25, 30, 41, 60, 62, 63 and 71.
2. **Test-first and seen-to-fail: PASS.**
   - With `daily.py` put back to its parent version and `table.py` removed, `tests/test_table.py` goes red (ImportError when the tests load). With the commit restored, all 8 tests pass.
   - Dormant listed before live: 2 tests fail.
   - Deflated figures over every track day instead of the subject's paper days: 2 fail.
   - Table written outside the new-day branch: 1 fails (the re-run test).
   - Each change was restored after it was tested.
3. **`./scripts/check`: NOT PROVEN.**
   - Run 1: `Exit code 143 / Terminated`.
   - Run 2: `exit=124`. The last line was `tests/test_synth.py ..............................................` with no failure up to 87%; ruff printed `All checks passed!`.
   - To cover the rest, I ran the remaining files and the smoke commands by hand, all green: `test_synth` 47 passed; `test_table`, `test_tradingcal`, `test_vendor` and `test_offline` 123 passed; `--version` and `config check: ok` worked.
   - The full script never reached `check: green`.
4. **Design conformance: PASS, every field of decision 71.**
   - Row order, section values, `retired` absent, `N` (trials row count) and `admission_score` (`metrics_t` Sharpe) match.
   - The paper record covers all paper days. The deflated figures use `stats.control_moments` over the subject's own paper days.
   - The nulls are where decision 71 puts them: approach fields and deflated figures for controls and portfolio, `breakeven_cost` for portfolio.
   - `ledger.line` sorts keys with `allow_nan=False`, so non-finite floats become null. `table.md` has four decimals, `-` for null, and no time of day.
   - `breakeven_cost` sums every journal row, not only the paper days' rows (table.py `journal_sums`). This is equivalent, because `paper.build` writes a row for every (subject, date) in the journal. The test uses the same reading, so it does not check this separately.
   - The test computes its expectations independently: its own Sharpe (decision 30), drawdown (decision 41), quantile by bisection, journal sums from the parquet files and states from the lifecycle ledger. It uses discotrade only to read stored rows; `table.build` is called only in the 50-slot listing test.
   - Invariants: I-6 holds (the table is built only when `result.status == WRITTEN`, `daily.py:321-324`). I-9, I-12 (no wall clock) and I-14 hold. I-11 holds (`test_table.py` added to `SUBPROCESS_FILES`). No new dependency.
5. **Forbidden files: PASS.** Nothing under `config/`, `tests/fixtures/`, `meta/`, `.claude/`, `templates/`, `DESIGN.md`, `SPEC.md` or `PLAYBOOK.toml` was touched. The test lowers `random_pool` only in a tmp copy.
6. **Commit body: PASS.** It lists all 4 files and states the readings it chose where the design is silent. Every claim I could verify held; I found no overreach.

Nothing in `/home/msi/git/discotrade` was changed, and the worktree `/tmp/rv9-33cfe7a` was removed.
```

Reviewer, alone at 33cfe7a in a worktree: `1205 passed, 86 deselected in 609.42s` / `config check: ok, 168 unverified values` / `check: green`.

### 984cc0c (U6)

```
984cc0c (mission 9 U6, scripted candidates in the replay): **pass on all points, with two things not proven.** `./scripts/check` did not finish within the time limit, and nothing tests T's trading days or the `displaced` path.

1. **Unit and sections:** M9 U6, as claimed. It cites decisions 48, 62, 63 and 73, and DESIGN §10.2, §10.3, §16.1 step 5 and §16.2. This matches the brief.
2. **Test-first: confirmed.** With the parent's cli.py, daily.py and replay.py, `tests/test_replay_candidates.py` gave 6 failed, 9 errors, 1 passed (red). Moving admission before `run_steps` turned 3 tests red, including the ledger-order test at tests/test_replay_candidates.py:228. Admitting on a re-run turned the re-run test red (:273). Each change was reverted afterwards.
3. **`./scripts/check`: not proven.** Both runs of `timeout 1180 ./scripts/check` were killed at the limit ("Exit code 143 / Terminated", no check output), on a machine shared with other reviewers. Separately, the 16 new tests passed against the commit itself (seen during both wrong-change runs).
4. **Design conformance: pass.**
   - Decision 73: a line must hold exactly the ten keys, and two candidates for one day are refused with exit 2 before any day runs.
   - Source confinement: `resolve()` plus `is_relative_to`. I checked by hand that a symlink in tests/fixtures/ pointing to /etc, `tests/fixtures/../../etc/x`, a deep `../`, an absolute path and a directory are all refused.
   - T days come from `Track.windows(D).t`, as §4.1 says.
   - Order in the day: admission runs after `run_steps` and before rank persistence and the table, only on a new day (src/discotrade/daily.py:326-331), so a re-run writes nothing (I-6).
   - Staging: `lifecycle.admit(into=staging)` writes the trial row, the approach or trial files, and the lifecycle rows only into staging, and they move into place only when the day commits.
   - I-5, I-9, I-10, I-11, I-12 and I-14 hold. No new dependency.
5. **Forbidden files: none touched.** The commit changes only src/discotrade/{cli,daily,replay}.py, tests/test_replay_candidates.py, tests/test_offline.py and a new fixture, tests/fixtures/scenarios/u6_candidates.jsonl. No config value changed.
6. **Commit body: accurate.** It lists all 6 files and its claims match the tests. One small overreach: "with T's trading days of DESIGN 4.1" is stated but not tested, and the "four cases" of a refused source are in fact four of six parametrised refusal cases.

**Not proven:**
- `./scripts/check` green at this commit (both runs timed out).
- `replay.t_days` and the `displaced` / `not_better_than_weakest` admission paths, which no candidate in the fixture reaches.
- Symlink and path-traversal refusal is not tested in the suite; I only checked it by hand.

The worktree /tmp/rv9-984cc0c has been removed.
```

Reviewer, alone at 984cc0c in a worktree: `1221 passed, 86 deselected in 635.83s` / `config check: ok, 168 unverified values` / `check: green`. The `displaced` path is driven through the replay by gate G1.3, which passed.

### ae7158b (U7)

```
Commit ae7158b: no blocker found, but I could not prove `./scripts/check` because both runs timed out.

1. **Unit:** mission 9 U7, the M1 gate tests. It claims decisions 2026-10-12 items 9, 59, 60 and 69 to 74, plus DESIGN §18.2 and §18.3 M1. This is correct.
2. **Seen to fail:** two of the four wrong changes were run, and both went red as expected.
   - (a) `E(N)` without the floor (`m = n`): `./scripts/gate M1 G1.4` gave `2 failed, 13 passed`, then `gate M1 G1.4: FAIL`.
   - (b) a recompute that skips control subjects (the `journal.py:612` `journal_pairs` setup branch disabled): `./scripts/gate M1 G1.2` gave `1 failed, 3 passed in 342.67s`, then `gate M1 G1.2: FAIL`. The test's final-line assertion on the pair count caught it.
   - (c) zero costs, NOT run: the change would turn `test_mean_summed_cost_is_positive` red (`cost > 0`, `test_g1_1_null_controls.py:121`).
   - (d) step 4 counting trading days, NOT run: the change would turn the `LIFECYCLE` row `2020-06-10 … retired_dormant` red, because 365 trading days ends after the replay's last day. `FLAT not in sections` in segment 2 would also go red.
3. **`./scripts/check`:** NOT proven. Both foreground runs hit the 1180 s limit on the loaded machine. The first ended `Exit code 143 / Terminated`. The second ran 19m40s, and its last lines were `tests/test_replay.py .................... [ 70%]` and `tests/test_replay_candidates.py ........exit=124`. Nothing had failed up to that point. The commit body says the check was green 3/3.
4. **Gate tests against §18.3 and decision 74:** no test asserts less than its item.
   - The bounds are 4 SE with ddof 1 and at least 40 values.
   - G1.4's 1e-12 follows decision 39's relative rule. Its literals are re-derived by bisection on `erf`, not through `stats.py`.
   - G1.3's hand counts (Sharpe, drawdown, breakeven, moments, portfolio and table) use only pyarrow and json. The table is checked on 06-13, 08-13 and the last day.
   - All seeds and dates are written in the test files, and every test file is marked `gate` and `gate_m1`.
   - No `src/` file has a branch for the tests.
   - The `test_gate_script.py` change is only the M1→M2 / G1.2→G2.2 rename.
   - I-11, I-12 and I-14 hold: the tests are offline, git uses local paths with `GIT_ALLOW_PROTOCOL=file`, time comes only from `--as-of`, and state lives under `tmp_path`.
   - Minor: G1.3 does not assert the pool seeds as literals the way G1.1 and G1.2 do (its docstring cites decision 64 by month).
5. **Forbidden files:** none touched. The commit changes only `tests/gates/*`, the two new fixtures, `tests/test_gate_script.py` and `tests/test_offline.py`, and no config value.
6. **Commit body:** it lists all 9 files. It openly says G1.1's rank-persistence test (`test_g1_1_null_controls.py:138`, net_1x) was RED at this commit, so this unit was pushed with a failing gate item; b62f5f0 later changes that clause. The timings are as measured (G1.3 at 1069 s is over §18.2's 15 minutes). Nothing in the body claims more than the tests prove.

**Not proven by me:** `./scripts/check` green at ae7158b, wrong changes (c) and (d), and G1.1/G1.3 at this commit. The worktree has been removed.
```

Reviewer, alone at ae7158b in a worktree: `1221 passed, 121 deselected in 649.34s` / `config check: ok, 168 unverified values` / `check: green`.

### b62f5f0 (U7, O-1)

```
b62f5f0: no defects found, but `./scripts/check` is not proven at this commit because it timed out twice.

1. **Unit:** mission 9 U7, resumed under owner decision O-1 (answers D-008). It cites DESIGN §11.1 (decision 59) and §18.3 G1.1 (decision 74), and correctly does not claim to close M1.
2. **Test-first: confirmed.** With the parent's `stats.py` put back, `test_the_column_parameter_chooses_the_paper_column_summed` fails with `TypeError: unexpected keyword argument 'column'`. The G1.1 file still collects (6 tests), so it can only fail when run, as expected. With the wrong change (`mine[column]` replaced by `mine["net_1x"]`), the test fails at `tests/test_stats.py` on `eq(at(column="gross"), 0.8)`. Restored cleanly afterwards.
3. **`./scripts/check`: NOT PROVEN.** Both foreground runs hit `timeout 1180` and ended with exit 143, printing only `Terminated`; load average was about 5 on the shared machine. Partial evidence at the commit: ruff "All checks passed!", `tests/test_stats.py` "31 passed in 0.87s", and `discotrade config check` "ok, 168 unverified values". The full pytest run is unverified, and so is the commit body's "green 3/3".
4. **Design conformance: pass.**
   - The only production caller, `src/discotrade/daily.py:261`, passes no `column`, so it keeps the `net_1x` default, and so does `rank_persistence.jsonl`.
   - The gate file is identical between ae7158b and b62f5f0~1. The commit only adds `column=` and splits out `rank_values`. `MIN_VALUES = 40` (line 60) and `abs(mean) <= 4 * se` are kept, and no other assertion changed.
   - The net statistic is only reported through `warnings.warn`, with no assertion on it.
   - I-4: no production path reports a gross number, and the gate prints the net statistic next to the gross one.
   - I-11, I-12, I-14: no network, wall clock or state-directory use was added.
5. **Forbidden files: clean.** The commit touches only `src/discotrade/stats.py`, `tests/test_stats.py` and `tests/gates/test_g1_1_null_controls.py`, and no config.
6. **Commit body: accurate.** It lists all three files, and the TypeError and wrong-change claims match what I reproduced. Two things I did not re-check: "green 3/3" (see point 3), and the claim that `scripts/gate` shows "1 warning" on a pass, because the G1.1 gate run was skipped as instructed.

The worktree `/tmp/rv9-b62f5f0` has been removed.
```

Reviewer, alone at 342107b (code identical to b62f5f0; `git diff b62f5f0 342107b` outside `meta/` is empty): `config check: ok, 168 unverified values` / `check: green` (630 s). The gate run shows "1 warning" at G1.1, as the commit body says.
