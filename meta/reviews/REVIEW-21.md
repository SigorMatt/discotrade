# REVIEW-21 — cold review of mission 21 (step S4.2a)

Base: `5ac4d5e` (`review: mission 20`, the last `review:` commit). Range
`5ac4d5e..origin/main`, tip `79888b6`. Unit commits: U1 `558e02a` `alerts:`,
U2 `943a18c` `tests:`, U3 `50341fc` `coordinator:`, U4 `d679adc` `tests:`.
Read for forbidden edits only: `e477f67` (the architect's kit: `KIT.md`,
`meta/BACKLOG.md`, `meta/ROADMAP.md`, `meta/BUILDER-21-PROMPT.md`,
`meta/decisions/decisions-2026-10-19-m21.md`), `e43c77c`, `692b0d5`,
`e0a8cfa`, `d0e424e`, `c36df23`, `2affd42`, `16881ff`, `dec0f84`, `79888b6`.
The builder's commits touch only `meta/plan.md`, `meta/CHECKPOINT.md`,
`meta/journal.md`, `meta/findings/FINDINGS.md` and `meta/FINAL-REPORT-21.md`.

`git diff 5ac4d5e origin/main` is empty for: `tests/gates/`,
`tests/fixtures/rejected/`, `tests/fixtures/config/`,
`tests/fixtures/config_frozen.json`, `tests/fixtures/return_readers.toml`,
`pyproject.toml`, `uv.lock`, and, from the kit commit on, `DESIGN.md`,
`SPEC.md`, `PLAYBOOK.toml`, `CLAUDE.md`, `.claude/`, `docs/`, `templates/`,
`meta/ROADMAP.md`, `meta/BACKLOG.md`, `meta/ARCHITECT.md`,
`meta/REVIEW-PROTOCOL.md`, `meta/BUILDER-*` and `meta/decisions/`. Under
`config/`, only `config/protected_paths.toml` changed (+14 lines, none
removed). Decision 164 (a) says that file is not frozen, and it is not in
DESIGN §4.3's list.

## Gate

not a closing mission

## Blockers

None.

## Should-fix

None.

## Notes

1. Check times. The reviewer's sub-agents ran one at a time (HF-012), and
   each `./scripts/check` stayed under the 20-minute cap: 1138 s at
   `558e02a`, 1063 s at `943a18c`, 1047 s at `50341fc` and 1013 s at
   `d679adc`. All were green, and all were above HF-006's 15 minutes
   (D-013 open). Running the sub-agents one after another removed REVIEW-20
   note 1's killed runs.
2. `meta/FINAL-REPORT-21.md` `## Check` gives the tip runs' pytest times out
   of order: "970.94 s, 985.72 s and 983.86 s" against `real` 16m26.628s,
   16m13.720s and 16m28.507s. In `meta/drafts/m21-u5-check{1,2,3}.txt` they
   are 983.86, 970.94 and 985.72 s in run order. `FINDINGS.md`'s U5 D-013
   line has the right order. The set of figures and every verdict are
   right.
3. U4's commit body (`d679adc`) gives no `./scripts/check` run count or wall
   times. The final report says so and takes the times from `meta/plan.md`
   and the checkpoint. The sub-agent brief asks for them in the sub-agent's
   report, not in the commit body, so this is not a breach.
4. U4's wrong change was tried in parts. Dropping only `hash` turns
   same-rows red and leaves other-rows green. Dropping only `rows` leaves
   both green, because the hash differs in both cases. The brief's wrong
   change (both dropped) turns both red. So `rows` is not guarded on its
   own; a change of row count always changes the hash.
5. U4's docstring says the store cannot replace a complete month in place,
   which `store.py` confirms (append refuses a bar not later than the last
   one). Once a month's index entry is gone, `recover` would also list an
   unlisted month file as an interrupted append. That is a second route, but
   it too needs a direct file write. Delete-then-append leaves both the file
   and its index entry to the writer, so it is a fair stand-in under
   decision 173.
6. U1: an approach's entry gets `N` and `p_N` before the zero-clean-days
   branch of `alerts.persistent_approach`. No test covers an approach with
   zero clean days; this holds by reading the code. The too-few-days case is
   covered by the "short59" fixture. The brief's wrong change turned two
   dashboard tests red. The third, the stored-entries test, stays green under
   it, because in that fixture the ledger's count equals the stored `N`.
   That test is not the one that guards against recomputation.
7. U3: two new tests use subset checks
   (`test_the_protected_paths_file_holds_decision_172s_entries`, and the
   deny check in `test_a_fix_session_is_offered_the_file_tools_only`). Exact
   equality of the deny list is held by the builder test. That an `Edit(...)`
   rule also covers `Write` comes from the permissions page and is not
   checkable offline. It is under NOT PROVEN with L4. The installed
   `claude --version` (`2.1.303 (Claude Code)`) and its `--tools` help line
   match U3's body.
8. U2: `tests/test_secret_env.py:43` holds a `<=` assertion that the `==`
   on the next line makes redundant. The secret scan's name pattern
   (`*_API_KEY`, `*_TOKEN`, `*_SECRET`, string literals only) and the
   fixture's function scope are disclosed under NOT PROVEN. A grep of `src/`
   finds no other secret variable today.
9. The final report's NOT PROVEN agrees with what the sub-agents found. The
   reviewer did not re-run U1's G1.3 time, the speed measurements at U1 or
   at the tip, or the U5 regression gates. Those figures are the builder's
   (drafts present under `meta/drafts/`).
10. hands: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered
    worktrees (HF-010, open). This review's own worktrees
    (`/tmp/rv21-<sha>`) were removed.
11. hands: the protocol still does not say how many per-commit sub-agents
    run at once (HF-012). Running them one at a time kept every check under
    the cap, at about 20 minutes a sub-agent.

## Per-commit verdicts

The sub-agents' final reports, as returned.

### 558e02a — U1 `alerts:`

558e02a ("alerts: persistent_approach's N and p(N) in the alert state, read by the page"): I found no defect, and every point passes.

1. **Unit: PASS.** It is mission 21 U1 (REVIEW-20 blocker 1, finding D-022, decision 169 (a) to (f), plus the speed figures decision 170 asks for). It claims DESIGN 15.1, 15.3, 15.5 and 11.4, and invariants I-6 and I-12.
2. **Test-first: PASS.** With `alerts.py` and `dashboard.py` put back to the parent, exactly the 5 new tests fail (`5 failed, 76 passed`): 2 in `tests/test_alerts.py` and 3 in `tests/test_dashboard.py`, as the commit body says. After restoring, `git status` was clean.
3. **`./scripts/check`: PASS.** It ended `2565 passed, 204 deselected in 1138.23s (0:18:58)`, then `config check: ok, 173 unverified values`, then `check: green`. The test count matches the body; my run was slower than its 976–995 s.
4. **Design conformance: PASS.**
   - **State entries:** `alerts.py:624` sets `N` and `p_N` from the same `n` and `p_n` as the payload, for every live or dormant approach. That includes ones with too few days or no clean days, and the "short59" fixture covers the too-few-days case.
   - **No crash on None:** `_held_shown` cannot crash on None, because `_n(None)` gives "-".
   - **Keys:** `transition` adds the keys only for persistent_approach, `ENTRY_KEYS` still has four keys, and no literal `"p"` is left except the `RANK_P = "p"` definition.
   - **Page:** `dashboard.py` no longer calls `tightened_percentile` or `in_force`. The 169 (c) list is complete and accurate for stats, alerts, table and paper; the other `alerts.*` matches are configuration key strings.
   - **Test formula:** both new test files compute p(N) with their own `own_p_n`, written from §11.4's formula, not from `stats.tightened_percentile`.
   - **Wrong change:** I made the page compute N and p(N) with `stats.tightened_percentile` instead of reading the entry. The two tests the body names went red; the third stays green because in that fixture the ledger count equals the stored N. Then I reverted it.
   - **Invariants and body claims:** no new number or dependency in src, and nothing touching the network, wall clock or state directory. The file list matches the disk, and the diff changes no existing test.
5. **Forbidden touches: PASS.** Only the two source files and two test files changed: nothing in tests/gates/, frozen config, meta/plan.md, meta/CHECKPOINT.md or any file CLAUDE.md lists as never edited.
6. The worktree is removed; the main worktree is untouched. Two worktrees from earlier reviews are still registered (`/tmp/rv13-8b9f9be`, `/tmp/u5/parent`); I left them alone.

**Not proven:**
- I did not re-run the body's G1.3 gate time (462 s) or its three speed replays (median ratio 1.116).
- No test covers an approach with zero clean days. It passes by reading the code (N and p_N are set before that branch), not by a test.

### 943a18c — U2 `tests:`

I found no defects in 943a18c (mission 21 U2). All five points pass.

1. **Unit:** mission 21 U2 (REVIEW-20 should-fix 2, decision 171 (a)-(d)). It claims DESIGN §14.2 and §19.3 L4, and invariants I-11 and I-13. Only three files change: `tests/conftest.py`, `tests/test_cli_provider.py` and the new `tests/test_secret_env.py`. Nothing under `src/` changes.
2. **Test-first, PASS.**
   - **Fixture dropped:** with the fixture's loop removed and `ANTHROPIC_API_KEY=sk-dummy-not-a-key` set, `test_no_listed_secret_is_set_inside_a_test` goes red ("1 failed, 3 passed"). After restoring, the worktree was clean.
   - **Touched tests, three runs:** the six files the commit body names gave "201 passed" each time: with no keys set, with dummy values for all three keys, and with a dummy key plus a fake `claude` first on PATH.
   - **Unknown-coordinator test:** it is parametrized over `bogus`, `Claude` and `scripted:`, and keeps exit 2, `--coordinator` in the error, and no file changed.
   - **Claude-off-PATH test:** it sets a dummy key and PATH to an empty temp dir. It asserts one line, exit 1, no file changed, both `shutil.which` calls returning None, and no `ClaudeCodeCoordinator` built.
3. **`./scripts/check`, PASS:** `2572 passed, 204 deselected in 1063.08s (0:17:43)`, `check: green`, exit code 0.
4. **Design conformance, PASS.**
   - **Fixture source:** `secret_env()` builds its list from the module constants `coordinator.KEY_ENV`, `providers.KEY_ENV`, `providers.WITHHELD_ENV` and `vendor.KEY_ENV`, as 171 (c) asks.
   - **Completeness:** grepping `src/` for `os.environ`/`getenv` finds only those three keys plus `DISCOTRADE_STATE` (`cli.py:34`), the container's `RUNTIME_ENV_NAMES` (`container.py:150`) and the `GIT_*` filter in `state.py:224`. None of these is a secret, and no notification token exists in `src/`.
   - **171 (d) list:** my own grep of `tests/` matches the body's list exactly. Nothing under `tests/gates/` touches claude, no test names `~/.local/bin/claude`, and the only bare `"claude"` (fixture `run.toml`) is resolved only under the empty-PATH test.
   - **Invariants:** I-11, I-12, I-13 and I-14 hold, with no new dependency.
5. **Forbidden touches, PASS:** none of CLAUDE.md's protected files, `meta/plan.md`, `meta/CHECKPOINT.md`, `tests/gates/` or frozen config is touched.
6. **Cleanup:** the worktree `/tmp/rv21-943a18c` is removed and `/home/msi/git/discotrade` is untouched.

**Not proven:**
- The secret scan only catches names written whole as string literals ending in `_API_KEY`, `_TOKEN` or `_SECRET`. A secret name built at runtime or shaped differently (e.g. `*_PASSWORD`) would slip past it. None exists in `src/` today, so this is a limit, not a defect.
- The fixture covers each test but not module- or session-scoped fixtures. The body says so, as the simplest reading where 171 is silent.
- I did not re-run the body's other three "seen to fail" checks (`which` check disabled, coordinator type mapping, `PUSHOVER_TOKEN` constant).

Minor nit: `tests/test_secret_env.py:43` has a `<=` assertion that the `==` on the next line makes redundant.

### 50341fc — U3 `coordinator:`

Review of 50341fc (mission 21 U3, coordinator fix session). Verdict: accept, no defect found.

1. **Unit:** pass. It names mission 21 U3, REVIEW-20 should-fix 3 and note 5, decision 172, DESIGN §14.4 and I-8, and matches the brief's file list and its `coordinator:` prefix.
2. **Test-first:** pass, matching the body exactly.
   - With the parent's `coordinator.py` and `protected_paths.toml`, 4 tests failed.
   - With `--tools` dropped, 1 failed (`test_a_fix_session_is_offered_the_file_tools_only`).
   - With `Bash` dropped from `DENIED_TOOLS`, 3 failed (`test_every_path_is_denied_for_every_editing_tool`, `..._through_the_builder_receives_exactly_those_rules`, `..._offered_the_file_tools_only`).
   - The tree was clean after each revert.
3. **./scripts/check:** pass. "2574 passed, 204 deselected in 1046.97s (0:17:26)", then `check: green`.
4. **Design conformance:** pass.
   - The installed `claude` prints `2.1.303 (Claude Code)`, and its `--tools <tools...>` help line matches the body's quote. `--tools Read,Glob,Grep,Edit,Write` is passed as one argument, the comma form the help gives.
   - The settings deny `Bash`, `WebFetch` and `WebSearch` before every `Edit(//...)` rule. Directories get `/**` (`meta/**`, `.claude/**`, `templates/**`), and all 10 new paths exist.
   - `protected_paths.toml` gained exactly decision 172 (b)'s entries and lost none. The parser and the ordinary coordinator call are unchanged; only `fix_session_command` uses `session_settings`. The file is not frozen config (decision 164 (a), and it is not in CLAUDE.md's frozen list).
   - The tests run a fake `claude` and read the path list from the file. Exact equality is checked in the builder test.
   - No invariant (I-8 to I-14) is touched and no dependency was added. The body overclaims nothing: enforcement is left under NOT PROVEN as live check L4.
5. **Forbidden touches:** none. Nothing under the never-edited files, `meta/plan.md`, `meta/CHECKPOINT.md`, `tests/gates/`, frozen config, `pyproject.toml` or `uv.lock` changed. The worktree is removed and the main worktree was not touched.

**Not proven:**
- That Claude Code actually enforces `--tools` and the deny rules (live check L4).
- That an `Edit(...)` rule also covers `Write`. The body doesn't make this claim; it sits only in an older test comment and can't be checked offline.

**Minor:** two of the new tests use subset checks rather than equality: `test_the_protected_paths_file_holds_decision_172s_entries` and the deny check in `test_a_fix_session_is_offered_the_file_tools_only`. The exact deny list is still asserted by the builder test, and the diff shows no entry removed.

### d679adc — U4 `tests:`

Commit d679adc passes all five points. I found no defects, only two small notes.

1. **Unit:** mission 21 U4 (REVIEW-20 should-fix 4, decisions m21 173 and m20 157 (a)). It claims DESIGN 5.4 and 5.2. The only file changed is `tests/test_gap_months.py`, which adds one test with two cases, same-rows and other-rows. **PASS**
2. **Wrong change:** with both `rows` and `hash` dropped from the `_MONTH_MISSING` key, both cases fail at the second `find_missing` read (`tests/test_gap_months.py:240`). Dropping only `hash` fails same-rows and passes other-rows. Dropping only `rows` passes both cases, because the hash changes in both, so the hash alone carries the guard. Reverted; the worktree was clean afterwards. **PASS**
3. **`./scripts/check`, one run:** `2576 passed, 204 deselected in 1012.62s (0:16:52)`, then `check: green` (16m56s). **PASS**
4. **Decision 173:** **PASS, with notes**
   - All the decision's conditions hold: one store root; writes through `BarStore.append`; reads through `gaps.find_missing`; month file and index entry rewritten through append with other bars missing (asserted: same rows and another hash, or other rows); no cache cleared, and the test asserts the path is still cached; expected bars computed from the written times via `tradingcal.expected_bars`, not `find_missing`; only `tmp_path`, no clock, no network, no random draw.
   - The docstring's claim about the writers holds against `src/discotrade/bars/store.py`: append refuses a bar not later than the last stored one (around :573).
   - Note: its claim about `recover` is incomplete. Once the index entry is gone, `recover` takes any unlisted month file as an interrupted append (`_interrupted` with no entry and no last bar). So a real recovery-path route existed: delete the index, hand-write the June file, let append's `recover` list it. It also needs a direct file write, and the test's delete-then-append leaves both file and index entry to the writer, which is closer to "through the writers". I judge it a fair stand-in, not a defect.
   - The commit body is accurate and lists its one file. It states no number of green `./scripts/check` runs and no wall times; I did not check the meta commits for them.
5. **Forbidden touches:** none. Nothing in `src/`, the never-edited files, `meta/plan.md`, `meta/CHECKPOINT.md`, `tests/gates/` or frozen config changed. **PASS**

**NOT proven:** the commit's own caveat, that no future writer path could change a complete month without changing its index rows or hash. I also did not verify how many green check runs the builder had before committing.

**Cleanup:** `/tmp/rv21-d679adc` is removed. Two other worktrees I did not create remain: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent`.
