# REVIEW-14 — cold review of mission 14 (roadmap step S3.1)

Base: c8eddf9 (`review: mission 13`, the last `review:` commit). Range
`c8eddf9..origin/main`, tip 3f4bf4f. Unit commits reviewed, one sub-agent
each, in the foreground and one at a time (so that `./scripts/check` runs did
not overlap on the four-core machine): ad53fad (U1), a0ba5e8 (U2), 1112052
(U3), 7e4c098 (U4), 779c9a4 (U5). Read by me for forbidden edits only:
1267318 (`plan:` kit), 53401fd (`plan:` U0), 819f96c, 4549e57, b23ea0c,
12d69c1, a3734d9, 3f4bf4f (`meta:`), f5f43ee (`report:`).

## Gate

not a closing mission

(The brief says the mission does not close a milestone. FINAL-REPORT-14
records gate M2 and gate M1 G1.1 to G1.4 passing at a3734d9 as a regression
check under decision 109 (b). This review did not run them again. U1's
sub-agent ran `./scripts/gate M2 G2.3` at ad53fad: `G2.3 PASS 8 passed in
4.54s`.)

## Blockers

None.

## Should-fix

1. `src/discotrade/workers/parse.py:98-100`: the description is the first
   non-empty line after the closing fence, whatever that line is. If a fence
   line follows a closed block, it is sanitized into the description. For
   example, `"```python\nx=1\n```\n```python\nB\n"` (a reply cut off in a
   second, unclosed block) parses as source `x=1` with description `python`,
   not as `no_description`. This is a literal reading of decision 117 (c)
   ("the first non-empty line after the closing fence"), so the code does not
   break the decision. The result is still a non-description stored as the
   worker's description, and it would reach the registry of later prompts.
   DESIGN QUESTION in part: decision 117 does not say whether a fence line can
   be a description. Suggested fix: treat a line that matches the opening or
   closing fence pattern as no description, with a test.

## Notes

1. FINAL-REPORT-14 §NOT PROVEN was read against the sub-agents' findings.
   They found nothing the report claims as proven that the disk contradicts.
   The report already states:
   - the content check covers the count and the last close only;
   - G2.3 still judges against the job;
   - the `trusted_hashes` cache misses a rewrite with the same stat key;
   - `BUILTIN_EXCEPTIONS` was checked on 3.14.6 only;
   - the prompt sample's registry state was not recorded.

   Should-fix 1 is not in the report.
2. `./scripts/check` in this review, one run per unit commit, each green, 0
   skipped (`container` tests ran on discotrade-sandbox:3b7d75c39621), with
   `config check: ok, 168 unverified values`:

   | Unit | Commit | Wall time | pytest |
   |---|---|---|---|
   | U1 | ad53fad | 814 s | 2067 collected per `--collect-only`; summary line not captured |
   | U2 | a0ba5e8 | 764 s | `2068 passed, 182 deselected in 762.87s` |
   | U3 | 1112052 | 784 s | `2110 passed, 182 deselected in 782.03s` |
   | U4 | 7e4c098 | 781 s | `2127 passed, 182 deselected in 779.26s` |
   | U5 | 779c9a4 | 795 s | `2152 passed, 182 deselected in 793.44s` |

   All runs are above decision 114's 12-minute target, which is recorded
   under D-013 (open). None is above HF-006's 15 minutes. U2's node-id
   collection was checked at its parent and its commit: 2067 and 2068 ids.
   The only addition is the new cache test, and no assertion moved.
3. `src/discotrade/workers/registry.py:62`, `kept.strip()[:max_chars]`: a cut
   that lands on a space leaves a trailing space (`sanitize('ab cd', 3) ==
   'ab '`). This follows decision 116 (b)'s order ("stripped and cut") and
   does no harm, but a registry line can end in whitespace.
4. `src/discotrade/workers/profile.py:166-169`: the `ProfileError` raised for
   a contract change with no roll record has no test. Disabling it leaves
   all 42 profile tests green. Decision 115 does not ask for that refusal, so
   this is not a missing required test.
5. U3's tests do not tell "adjusted as of W's last bar" from "adjusted as of
   the store's end". Roll gaps are additive, so they cancel in every figure
   built from price differences, which makes the two identical in effect. If
   a later adjustment is not additive, a test that pins the anchor would be
   needed.
6. U3's mean-reversion block uses ddof 1 for "twice W's deviation". This
   matches the common block, but the commit body does not state it. U5's
   parser treats a space between the backticks and `python` ("``` python")
   as no block. The body states this reading, and a test pins it; decision
   117 (c)'s "surrounding spaces allowed" could be read to permit it.
7. `tests/conftest.py:334` (`mixed_ran_template`, new in a0ba5e8): it runs
   `init-state` and `run-day` without the `GIT_ALLOW_PROTOCOL=file`
   environment that `synth_committed_template` (`:305`) sets. The code moved
   from the parent's `ran` fixtures, which had the same omission. The brief
   asks for it on tests that run `git`, and every repository involved is
   local.
8. U4's `registry.lines()` reads every approach in the state directory, like
   the existing journal and lifecycle code. If a state directory ever held
   approaches of more than one track, one whose cell this track lacks would
   raise `RegistryError`. This is a design question for later, not a defect
   of this mission.
9. Frozen config:
   - `git diff c8eddf9 origin/main` shows no change under `config/`,
     `tests/fixtures/config/`, `tests/fixtures/config_frozen.json`,
     `tests/gates/` or `tests/fixtures/rejected/`.
   - `config/models.toml` does not exist.
   - The builder's commits touch none of the files CLAUDE.md lists as not a
     builder's.
   - Of `meta/plan.md` and `meta/CHECKPOINT.md`, only the `plan:` and
     `meta:` commits touch them.
   - The only edits to `meta/ROADMAP.md`, `meta/BACKLOG.md` and
     `meta/decisions/` are in the architect's kit commit 1267318.
10. Every unit commit's body lists every file it touches, `meta/findings/
    FINDINGS.md` included where it appended a D-013 times line (U1, U2, U3).
11. hands: the stale worktrees of HF-010 (`/tmp/rv13-8b9f9be`,
    `/tmp/u5/parent`) are still registered with this repository's `git
    worktree list`. This review's own worktrees were removed.
12. hands: f5f43ee carries the prefix `report:`, which the protocol's skip
    list (`plan:`, `meta:`, `review:`) does not name. This is the same kind of
    issue as HF-011. It was read for forbidden edits: it adds
    `meta/FINAL-REPORT-14.md` and a D-014 line only.
13. hands: the protocol dispatches one sub-agent per unit commit but does not
    say whether they may run concurrently. With `./scripts/check` near 13 to
    14 minutes on four cores and load-dependent call-time limits in the
    `container` tests, running five at once would risk the 20-minute call
    limit and false reds. They were run in sequence, about 83 minutes in
    total (HF-008).

## Per-commit verdicts

### ad53fad (U1)

```
I found no defects in ad53fad. All five points pass and the commit is ready to approve.

1. **Unit:** this is U1 of BUILDER-14. It implements decisions 110, 111 and 112 and claims DESIGN §5.6, §12.4, §16.2 and §19.3 L5, with I-6, I-7 and I-12. The image tag is discotrade-sandbox:3b7d75c39621, as expected; the build found it already present and built nothing.
2. **Test-first: PASS.** With the five product files put back to the parent, all 22 new test cases failed and none passed. That covers 14 probe/judge/store cases (3 of them `container`), 1 container-client, 2 process, 4 runner and 1 daily. The body names all five seen-to-fail changes from the brief. I repeated four of them myself and each turned red:
   - selftest using `expected_mount(job)`: the tampered self-test fails (1 failed).
   - notice written on the re-run: 1 failed, while the written-day notice test still passes.
   - float conversion moved before the try: 3 failed.
   - the `max(0.0, …)` clamp restored and the wait guard removed: 1 failed.

   After `git checkout ad53fad -- .` the status was clean.
3. **`./scripts/check`: GREEN.** It ended with `config check: ok, 168 unverified values` and then `check: green`, in 814 s. I did not capture pytest's summary line. A separate `--collect-only` shows `2067/2249 tests collected (182 deselected)`, which matches the body's 2067. `./scripts/gate M2 G2.3` gave `G2.3 PASS 8 passed in 4.54s`.
4. **Design conformance: PASS.**
   - **Decision 110:** the probe adds `last_close` and leaves `latest_open` null. `expected_from_store` reads `BarStore` directly; its context is capped at `history_cap_bars-1`, starts no earlier than `trusted_from`, and matches what `read_window`/`job_instrument` build. `judge` fails on a count mismatch, on W=0 and on an exact last-close mismatch. `expected_mount` keeps its signature. selftest uses the store expectation, and doctor `--live sandbox` goes through selftest.
   - **Decision 111:** a remaining time ≤0 raises TimeoutError before the socket is read, so the job gets `limit [wall_clock]` and the "wait" question stays answerable. `BlockingIOError` is treated as TimeoutError. The float conversion is inside the catch-all; it catches `BaseException`, the same as decision 101(c) for calls. `BUILTIN_EXCEPTIONS` covers builtins, including the two 3.13+ classes taken with getattr. A removal that raises still ends the runtime client.
   - **Decision 112:** the notice is skipped only when the day comes back UNCHANGED; it is still written on a day that is written or fails.
   - **Invariants:** no market names under `src/` (I-9), no new thresholds (I-10), no wall clock in results (I-12), no state in the repo (I-14), no new dependency, and the new tests use no network or secret (I-11).
5. **Forbidden touches: PASS.** The commit changes nothing under `config/`, `tests/fixtures/` (the frozen JSON and `rejected/` included) or `tests/gates/`, and none of `meta/plan.md`, `meta/CHECKPOINT.md` or the builder-protected files. The base-range diffs of those files come from other meta/decisions commits. The body lists all 11 files, `meta/FINDINGS.md` included (the D-013 times).

**Not proven:** the content check compares only the count and the last close, not each mounted row, and G2.3 still judges against the job (both stated in the body). I did not capture pytest's passed/skipped line. I removed the worktree; no containers from my runs were left (only the unrelated `ntfy` is running).
```

### a0ba5e8 (U2)

```
**a0ba5e8**: green, no defects. It closes U2 with the 12-minute target missed, and that miss is recorded under D-013.

1. **Unit:** mission 14 U2, `./scripts/check` under 12 minutes. It claims decision 114, D-013, HF-006, HF-008, DESIGN §18.1 and REVIEW-12 note 4. OK.
2. **Test-first:** OK. With `journal.py` put back to the parent, `test_trusted_hashes_hashes_a_file_again_after_it_changes` fails at tests/test_journal.py:400 ("Left contains 5 more items"). For the brief's seen-to-fail I made `copy_template` hand out the template uncopied, alone: test_daily plus test_journal_recompute still give 36 passed, because each test's function fixture copies again. Adding the body's mutation (test_daily's `state` returns `ran` uncopied) gives 17 failed, 19 passed, the body's 17 exactly. Reverted, tree clean.
3. **`./scripts/check` at a0ba5e8:** green, exit 0, wall 764 s. Final lines: "2068 passed, 182 deselected in 762.87s (0:12:42)", "config check: ok, 168 unverified values", "check: green". Container tests ran with no skips on discotrade-sandbox:3b7d75c39621 (`sandbox build`: "present, nothing built"). Load average about 1.1.
4. **Design conformance:** OK.
   - **(a) Node ids:** 2067/2249 at the parent, 2068/2250 at the commit. The diff of the lists is one added line, the new cache test.
   - **(b) Assertions:** none moved, no span, count or day range shortened, nothing skipped or removed, `tests/gates/` untouched. The removed asserts are setup-only `main(...) == 0` calls, now asserted in conftest `_cli` or in `ran`'s loop. The added asserts tie each template's constants to the module's.
   - **(c) Copies:** each module gets its own `copytree` of a session template. The span fixture in `test_journal.py` and `plain` in `test_cli_backtest.py` are only read. `short` in `test_paper.py` depends on `ran`, so there is no order dependence. The template configs match each module's config (fixture config plus production `thresholds.toml`).
   - **(d) Cache:** `_DIGESTS` is keyed per path on (dev, ino, size, mtime_ns, ctime_ns) and is process-global. Its only caller is the trusted-source check in `sandbox/process.py:118`, not a score path, so I-1 and I-6 hold. A stale entry fails closed (an edited file would be refused). The missed same-key rewrite is acknowledged under Not proven. It stays within REVIEW-12 note 4.
   - **(e) Body figures:** they match where I could reproduce them (counts, 17 red). My single check run (764 s) was faster than the body's 841 to 891 s, under lower load.
   - **Invariants:** I-11, I-9, I-10, I-12 and I-14 hold (templates live under `tmp_path_factory`), and there is no new dependency.
5. **Forbidden touches:** OK. The commit's 19 files match the body's Files list, `meta/findings/FINDINGS.md` included. It touches no frozen config, `tests/gates/`, `tests/fixtures/rejected/`, `plan.md`/`CHECKPOINT.md` or any builder-forbidden file. The changes since c8eddf9 to `plan.md`, `CHECKPOINT.md`, ROADMAP, BACKLOG and decisions come from earlier commits, not this one.

**Note:** `mixed_ran_template` (tests/conftest.py, near line 335) runs `init-state` and `run-day` without `GIT_ALLOW_PROTOCOL=file`, as the parent's `ran` fixtures already did. The brief's git-test rule asks for it.

**NOT proven:** the parent's wall time and `--durations=20` (I did not run them); the body's byte-equality comparison of templates against fresh builds; a same-key rewrite going unhashed; the run being under 12 minutes (it is not, as recorded). Worktrees removed and no containers left. `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are not mine and were left alone.
```

### 1112052 (U3)

```
Commit 1112052 passes on points 1–5: no defects and no blockers. I removed my worktree /tmp/rv14-1112052, and my runs left no containers. The other worktrees still listed (/tmp/rv13-8b9f9be, /tmp/u5/parent) were not created by me, so I left them alone.

1. **Unit:** mission 14 U3, the W profile `p1`. It implements decision 115 (DESIGN §13.1, §4.1, §5.6, §6.2; I-1, I-3, I-9, I-12).
2. **Test-first: PASS.**
   - With `src/discotrade/workers/` removed, `tests/test_workers_profile.py` fails to collect (`ModuleNotFoundError`). After restoring, the tree was clean.
   - Each brief mutation, made and reverted by me: (a) a return across W's first bar fails 23 tests; (b) one bar of T fails 17; (c) the horizon in the cell block fails 4. These counts match what the body says.
3. **`./scripts/check`: green** (one run, as asked). Final lines verbatim: `=============== 2110 passed, 182 deselected in 782.03s (0:13:02) ===============` and `check: green`. Wall time 784 s, 0 skipped. Container tests ran on discotrade-sandbox:3b7d75c39621.
4. **Design conformance: PASS.**
   - **Returns and hours, 115 (a):** `profile.py:139` and `:155-180` match the decision.
   - **Common block, 115 (b):** every statistic matches, including ddof 1, numpy's default quantiles, the moment ratios, pairwise Pearson ACF, and rv(s) defined from W's 24th return.
   - **Cell blocks, 115 (c):** all six match, with correct index alignment in breakout, the volume event bar's sign and the bar after an event.
   - **Nulls, 115 (d):** undefined figures become null beside their count, and nothing is filled in.
   - **Interpretations the body discloses:** the breakout range is divided by the raw close; a volume event bar with zero return gets products of 0.
   - **Interpretation not stated in the body:** mean_reversion uses ddof 1 for "W's deviation". This is consistent with the common block.
   - **Document contents:** the document holds no date, price, volume or index; symbols appear only as instrument keys.
   - **Tests:** they compute expected figures from the Parquet files and roll records with their own reading of W, trading date and adjustment, and call nothing in profile.py. They cover both tracks, the 1e-9 scale test and the W-only test.
   - **Invariants:** I-3, I-9, I-11, I-12 and I-14 hold. There is no network import, no wall clock and no new dependency. I-10: the constants (24, 48, 2 sd, percentiles) are fine as module constants, because decision 115 fixes them as the profile's definition, versioned by `p1`.
5. **Forbidden touches: none.** No frozen config, gates, rejected fixtures, plan, checkpoint or protected document was touched. The body lists all four files, including the FINDINGS.md D-013 times line.

**Not proven:**
- The `ProfileError` raised for a contract change with no roll record (`profile.py:166-169`) has no test; disabling it leaves 42 passed.
- Adjusting as of the end of the store instead of W's last bar also leaves all tests green. This is not a defect: roll gaps are additive, so they cancel in every figure, which is built from price differences.
```

### 7e4c098 (U4)

```
Review of 7e4c098 (U4, decision 116). Verdict: passes all five points, no blocker. Done in the worktree /tmp/rv14-7e4c098, now removed; my runs left no containers. Two older worktrees, /tmp/rv13-8b9f9be and /tmp/u5/parent, are not from this review and I left them alone.

1. **Unit:** U4, anonymization and the registry. It claims DESIGN §13.2, §13.3, §10.3, §4.1, §4.3 and I-8, I-10, and adds `src/discotrade/workers/{anonymize,registry}.py` plus two test files. The body lists all four files.
2. **Test-first: PASS.** With the two src files removed, both test files fail with an ImportError; after restoring, the tree was clean and all 17 tests pass. Each brief mutation turned the tests red with the counts the body states: (a) Python's `hash` for the seed, 6 failed; (b) `RETIRED` allowed in the registry, 1 failed; (c) angle brackets kept by the sanitizer, 3 failed.
3. **`./scripts/check`: green, one run, 781 s wall.** Final lines: `2127 passed, 182 deselected in 779.26s (0:12:59)`, `config check: ok, 168 unverified values`, `check: green`. Sandbox tag was discotrade-sandbox:3b7d75c39621 (already built). Log is at /tmp/rv14-7e4c098-check.log.
4. **Design conformance: PASS.**
   - **Anonymization:** the seed is the first 8 bytes of sha256, big-endian, fed to `default_rng`. The generator shuffles, then labels A, B, ... in shuffled order, and refuses more than 26 instruments. One mapping serves every part in label order. `SCALED_FIELDS["p1"]` is empty. The scale constants come from the same generator on [0.5, 2.0], and hours and weekdays are kept.
   - **Registry:** it uses `lifecycle.states` directly rather than re-deriving the state logic. It keeps live or dormant approaches sharing the family or the horizon, the cell itself included, ordered by cell index then id. The line format, intro line, delimiters and `(none)` match the decision. The cap comes from `validation.description_max_chars` (200).
   - **Line breaks:** whitespace is joined before characters are removed, so a line break becomes a space and is not deleted. Tabs,   and \x85 are also handled.
   - **I-8:** the registry reads only approach meta and the lifecycle ledger, no score.
   - **Tests:** the test computes the seed itself, and every test 116 (c) lists is present.
   - **Invariants:** nothing new for I-9 or I-11, I-12, I-14. There is no new dependency and no network import under `workers/`. For I-10, no threshold literal is in src; `SCALE_LOW`/`SCALE_HIGH` are constants that decision 116 fixes itself.
5. **Forbidden touches: PASS.** `git diff 7e4c098~1 7e4c098` shows nothing under `config/`, `tests/fixtures/`, `tests/gates/`, `meta/` (so not `plan.md` or `CHECKPOINT.md`), the protected docs, `.claude/`, `pyproject.toml` or `uv.lock`.

Minor defect, not blocking: `src/discotrade/workers/registry.py:62`, `kept.strip()[:max_chars]`. The cut happens after the strip, so a cut that lands on a space leaves a trailing space: `sanitize('ab cd', 3) == 'ab '`. That follows the decision's wording ("stripped and cut"), but the registry line can then end in whitespace.

Observation: like the existing journal and lifecycle code, `lines()` reads every approach in the state directory. If one state directory ever holds approaches from more than one track, an approach whose cell this track lacks makes it raise `RegistryError`. This is a design question, not a defect in this commit.

NOT proven: the body's "green 3/3" and its 862/845/882 s timings (I ran one check). That `Track.cell_index` matches DESIGN §4.1's cell order (I trusted the existing config code).
```

### 779c9a4 (U5)

```
Review of 779c9a4 ("workers: the prompt builder and the response parser"), unit U5 of mission 14, decision 117. **Verdict: pass on all five points; one should-fix in the parser, no blockers.**

1. **Unit and sections: pass.** The body names U5, decision 117 of 2026-10-15-m14, DESIGN 13.4, 6, 7.3, 12.1, 12.2, 13.2, and I-8, I-10, I-13.
2. **Test-first: pass.** With `prompt.py` and `parse.py` removed, both test files fail at collection (ImportError, red). Restoring the commit's tree left the worktree clean. I made the brief's three mutations myself, one at a time, and reverted each:
   - (a) symbol in place of the label in the cost line: 3 tests fail.
   - (b) `max_lines = 60` as a literal: 1 test fails.
   - (c) the parser taking `found[0]`: 1 test fails.
   The body names all three, with the same failure counts.
3. **`./scripts/check`: green**, one run, 795 s wall time. It ends `2152 passed, 182 deselected in 793.44s (0:13:13)`, `config check: ok, 168 unverified values`, `check: green`. Nothing skipped, so the container tests ran, using `discotrade-sandbox:3b7d75c39621`. Log: `/tmp/rv14-779c9a4-check.log`.
4. **Design conformance: pass, with one should-fix.**
   - Everything decision 117 asks for is there: the five parts and headings in 13.4's order, the brief cut to `brief_max_chars`, the profile rendering, the caps, the static tables and the indicator list. The cost lines are in label order through the one labelling and match `executor.py`'s cost code, over W only.
   - The rendering is valid JSON in my probes: -0.0 gives `-0`, 1e+300, 5e-324, nested lists, ints kept whole.
   - The contract text matches §6, §7.3 and §12.2 (frame columns, shorting clipped to 0, half a tick minimum, two extra trades at a roll, net at 1x and 2x). It says the grid uses the "exposure-adjusted" Sharpe, while §12.2 says net Sharpe; that matches decision 97 and `sequence.fix_combination`.
   - The cost-line test's computation is independent: it does not call `costs.py` and uses its own sigma, roll gaps and spread lookup.
   - Decision 92: neither new module holds a reference shape, so "no reader found" is right, and `test_return_readers` passes.
   - Invariants I-8 to I-14: nothing found (no score, T or P in the prompt; no literal cap; no environment, clock, network or new dependency).
   - **Should-fix, `src/discotrade/workers/parse.py:100`:** if a closed block is followed by a later fence line, that fence becomes the description. My probe `"```python\nx=1\n```\n```python\nB\n"` gives `description='python'`. This is a realistic case: a reply cut off mid-way through a second block. It is a literal reading of "first non-empty line", but a fence line should not count as a description.
   - **Note:** "``` python" (a space before the info string) counts as no block, and a test pins that. The decision's "surrounding spaces allowed" could be read to permit it. The body states this reading.
5. **Forbidden touches: pass.** The commit adds exactly four files, all listed in the body. Nothing changes under `config/`, `tests/fixtures/`, `tests/gates/`, `meta/`, `.claude/`, `pyproject.toml` or `uv.lock`, and none of the files CLAUDE.md forbids is touched.

**NOT proven:**
- The body's 3/3 green runs and their times (880, 895, 892 s). I ran one, at 795 s.
- That `FINAL-REPORT-14.md`'s sample prompt is byte-identical to this commit's output. I compared its text with the code and the design, but did not rebuild it.

My worktree is removed and no containers were left. Two other worktrees, `/tmp/rv13-8b9f9be` and `/tmp/u5/parent`, were already there; I left them alone.
```
