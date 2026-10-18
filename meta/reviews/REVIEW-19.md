# REVIEW-19 — cold review of mission 19 (roadmap step S4.1)

Base: 885b124 (`review: mission 18`, the last `review:` commit). Range reviewed:
`885b124..origin/main` = c98a972 .. ad3576c (21 commits). Unit commits, one
sub-agent each, in sequence: 27a83b9 (U1), a7854da (U2), efc35de (U3), 3ee67d3 (U4),
a21beb7 (U5). Read by the reviewer for forbidden edits only: c98a972, 32f99ea
(`journal:`), 24e5d0d (`plan:` the owner's file), 031f5e4 (`plan:` the architect's
kit), e0d19df (`plan:` U0), and the `meta:` commits 8abeb5c, bca3f6a, f3dd7a0,
067405a, 36009f6, ef9359f, d1f4b81, e2bde18, 8837eed, ad3576c.

## Gate

not a closing mission

Under O-25 and decision 146 (a) the met gates whose tests read a function this
mission changed were run again. The builder's runs at ef9359f are in
FINAL-REPORT-19 `## Gate`. The reviewer ran them again at the pushed tip
ad3576c6372d7c133ba9992851042bf8428353a5, with nothing uncommitted. The tip
differs from a21beb7 (U5) only under `meta/`. Each run was a foreground call with
a 20-minute timeout, after `discotrade sandbox build` (`sandbox build: present,
nothing built`, `discotrade-sandbox:3b7d75c39621`). Load average was 0.5 to 1.7
at the start.

```
G1.1 PASS 6 passed, 1 warning in 382.69s (0:06:22)
gate M1 G1.1: PASS
rc=0 wall=383s
G1.2 PASS 4 passed in 288.91s (0:04:48)
gate M1 G1.2: PASS
rc=0 wall=290s
G1.3 PASS 10 passed in 1085.65s (0:18:05)
gate M1 G1.3: PASS
rc=0 wall=1087s
G1.4 PASS 15 passed in 0.64s
gate M1 G1.4: PASS
rc=0 wall=1s
G3.1 PASS 3 passed in 212.80s (0:03:32)
G3.2 PASS 9 passed in 164.25s (0:02:44)
G3.3 PASS 10 passed in 172.78s (0:02:52)
gate M3: PASS
rc=0 wall=552s
G2.1 PASS 36 passed in 41.71s
G2.2 PASS 3 passed in 27.24s
G2.3 PASS 8 passed in 4.58s
G2.4 PASS 9 passed in 45.33s
G2.5 PASS 5 passed in 21.50s
gate M2: PASS
rc=0 wall=144s
G0.1 PASS 62 passed in 66.35s (0:01:06)
G0.2 PASS 7 passed in 101.36s (0:01:41)
G0.3 PASS 13 passed in 110.74s (0:01:50)
G0.4 PASS 4 passed in 0.78s
gate M0: PASS
rc=0 wall=282s
```

| Item | mission 17 U5 | builder at ef9359f | reviewer at ad3576c |
|---|---|---|---|
| G1.1 | 450 s | 411 s | 383 s |
| G1.2 | 204 s | 280 s | 290 s |
| G1.3 | 542 s | 1049 s | 1087 s |
| G1.4 | 1 s | 1 s | 1 s |
| M3 | — | 547 s | 552 s |
| M2 | — | 130 s | 144 s |
| M0 | — | 245 s | 282 s |

The only change under `tests/gates/` in the range is decision 148 (d)'s one line,
`tests/gates/test_g1_3_lifecycle.py:643`, exactly as the item writes it (97
characters with its indent). `git diff 885b124 origin/main -- tests/gates` shows
nothing else. All regression gates pass unchanged. G1.3 is above O-3's 10 minutes
(D-014) and finishes 113 s inside its 20-minute call (Notes 1).

## Blockers

None.

## Should-fix

1. `src/discotrade/dashboard.py:393` `_rank_p` computes the `rank_persistence` rule's
   `p` on the page, from the state's `value` and `threshold` and the current
   `alerts.rank_blocks` and `alerts.rank_level`. Decision 152 (a) says the dashboard
   "reads the rules' figures from this file and never recomputes them". Decision 153
   (b) 1 asks for the rule's `p` "from the alert state", but 152 (a)'s entry has no
   `p` (`alerts.ENTRY_KEYS`), so the two items conflict. U5's body files this under
   "Where the design is silent", but the design is not silent: two of its items
   disagree. By CLAUDE.md, that is a finding (the next free `D-###`), not a choice
   made in the code. The derived figure is exact while the thresholds are unchanged
   (t = t_crit · mean / critical mean). It can differ from the rule's own `p` (which
   is in the payload) if `rank_blocks` or `rank_level` changes after the state was
   written.
2. The health panel's failure counts are untested. `dashboard.py:575` reads
   `pool.fail_window` and uses it to cut each model's calls. U5's reviewer replaced
   it with the literal `window = 20` and all 21 tests in `tests/test_dashboard.py`
   stayed green. Decision 153 (d)'s wrong change "a threshold written as a literal in
   `dashboard.py`" is therefore caught only where the value is shown or decides a
   verdict, not where it moves a figure on the page. A test of the per-model
   failures over the last `pool.fail_window` counted calls, computed by the test,
   would close this.
3. FINAL-REPORT-19 `## Speed` gives no figure at mission 18's tip. The U7 brief asks
   for "the seconds per replay day of the G1.3 scenario at mission 18's tip and after
   each of U2, U4 and U5". The report says plainly that no such figure was measured.
   That is honest, but the item is missing rather than carried. Measure it at
   d8a129a or 031f5e4 by decision 80 (d)'s method, or list it under NOT PROVEN as
   owed.

## Notes

1. G1.3 took 855 s (U1), 962 s (U4), 1049 s (builder at the tip) and 1087 s
   (reviewer at the tip), against mission 17 U5's 542 s. Under O-2, an item that
   does not finish within its 20-minute call is FAIL. The margin is now under 2
   minutes on a lightly loaded machine, so the next step that adds day-loop cost
   (S4.2's digest and issues) will probably push G1.3 past the cap. D-014 is open for
   the owner. It needs a ruling before mission 20, not after.
2. `./scripts/check` at the reviewers' units: U2 1036 s, U3 1088 s, U4 1125 s
   (`2435 passed, 204 deselected in 1121.40s`), U5 1158 s (`2458 passed, 204
   deselected in 1154.89s`). All were `check: green` and all were above HF-006's 15
   minutes. U5's run, whose code is identical to the tip's, was 42 s inside the
   20-minute cap. U1's reviewer could not finish one `./scripts/check` run: under
   outside load (load average about 7.6 on 4 cores, from another project's
   sessions) the run passed the cap and was cut off. The reviewer then ran the
   check's steps separately: ruff green, the smoke steps green, pytest in three parts
   941 + 268 + 1161 = 2370 passed (the count U1's body gives). So `check: green` at
   27a83b9 was not seen as one line by the reviewer. D-013 stays open.
3. U2's body says the two-sided `t_sf` wrong change turned "all 15 `t_sf` tests"
   red. U2's reviewer doubled only the positive branch's tail. That left the 7
   `t_sf(-t) = 1 - t_sf(t)` cases green, because `stats.py` builds the negative side
   as `1 - tail`. A fully two-sided `t_sf` (the same value for `t` and `-t`) does
   break those cases too, so the claim holds for that form. The body does not say
   which form was used.
4. `alerts.group_edge` (`src/discotrade/alerts.py:415`) raises `ValueError` when
   `portfolio_clean`'s dates and `paper.clean_members` disagree. Since U4 wires the
   rule into step 6, such an inconsistency fails the day rather than skipping the
   rule. This is a consistency check on the system's own records and U3 disclosed
   it. It is recorded here so S4.2's run-failure handling knows about it.
5. `alerts.revival` counts dormant days with the same `stats.trading_dates` call
   that lifecycle step 3 makes (`lifecycle.py:266`), but as a copy of the call, not
   a shared helper. Decision 152 (d)'s "by the same function" holds for now, but the
   two could drift apart.
6. The detectors' events are appended to the health log in the state directory
   before staging is moved (`daily.py`, step 6), as the loop's other health events
   are. If the day then fails, its retry appends them again. `alerts.health` copes
   with the duplicates. This is the same family as REVIEW-17 note 4, which goes to
   step S4.2.
7. `alerts.health` keeps an inactive entry in `state.json` for every (kind, subject)
   ever raised, so the file only grows. This fits 152 (a)'s wording.
8. `dashboard.BAND = (0.05, 0.95)` is a number in `src/`. It is the display band
   decision 153 (b) 3 fixes, and no alert, score or gate reads it, so it is not an
   I-10 threshold.
9. Forbidden edits: none. Every builder commit in the range leaves alone `DESIGN.md`,
   `SPEC.md`, `PLAYBOOK.toml`, `meta/ROADMAP.md`, `meta/BACKLOG.md`,
   `meta/ARCHITECT.md`, `meta/REVIEW-PROTOCOL.md`, `meta/BUILDER-*-PROMPT.md`,
   `meta/decisions/`, `.claude/`, `docs/ARCHITECT-HANDBOOK.md` and `templates/`. The
   kit (031f5e4) and the owner's file (24e5d0d) are the architect's and the owner's
   commits. Only `meta:`/`plan:` commits touch `meta/plan.md` and
   `meta/CHECKPOINT.md`, never a unit commit. Under `config/`, the only change is the
   new `config/gates.toml`: two `false` flags, no number, not frozen. Nothing under
   `tests/fixtures/rejected/`, `tests/fixtures/config/` or
   `tests/fixtures/config_frozen.json` changed. No dependency was added.
10. FINAL-REPORT-19's NOT PROVEN matches what the reviewers found. The figures U5
    does not assert (the O-14 adjusted sum and positions, the band, the running mean,
    the significance band, the derived `p`) are listed. So are the unit-level gaps.
    Each reviewer re-made a subset of the wrong changes, and every one went red:
    U1's revert; U2's `statistic`-for-timing and two-sided `t_sf`; U3's `k`
    truncation, exposed days in W, the shifted seed and plain Sharpes; U4's
    every-true-day firing, `date.today()` and the read on `statistic`; and all three
    of U5's. The rest are the builder's claims.
11. hands: U1's sub-agent was told to run in the foreground only. When its check run
    passed the cap, it moved work to a background task with a Monitor and then
    stopped waiting for a notice that never came. It had to be resumed twice, and
    U1's review took about 50 minutes. The sub-agent brief needs to say what to do
    when a foreground run hits the 20-minute cap (HF-006).
12. hands: another project's sessions on the same machine raised the load to about
    7.6 during U1's review. The protocol cannot control outside load, but it decides
    whether a check run fits the cap (HF-006, HF-012). The reviewers here ran in
    sequence, about 2 h for the five, plus about 40 min of regression gates.
13. hands: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered as
    worktrees (HF-010). This review's worktrees were all removed.
14. hands: every sub-agent report below runs past the protocol's 12-line limit
    (HF-013). They are recorded as returned.
15. hands: the reviewer's harness refused a `sleep` followed by other commands and
    pointed to Monitor or background tasks instead. Those are the very tools the
    project's `no_background` rule forbids. A reviewer waiting on a sub-agent has no
    sanctioned way to wait.

## Per-commit verdicts

### 27a83b9 (U1)

**27a83b9: PASS** with no defects. The one gap is that `./scripts/check` never completed as a single run; I ran its steps in pieces and all of them were green.

1. **Unit and sections:** mission 19 U1. It implements DESIGN §10.4 and §11.2 under O-23 and O-24 and decisions 147 (a), (c), (d) and 148 (a)–(e). The commit body lists all 9 files.
2. **Test-first: red as expected.** With the three `src/` files put back to their parent, the 6 new tests, the 2 changed `test_table` tests and the register audit failed: 9 failed, 33 passed. The errors were TypeError on `column` and `exposure`, KeyError `adjusted_S`, the md headings, and the register showing `adjusted_deflated` as an unregistered function. Restoring the tree left it clean.
3. **`./scripts/check`: not proven as one run.** My single run went past the 20-minute cap, was moved to the background and was killed before printing anything. An unrelated spanweave job was loading the machine. I then ran the check's steps separately in the foreground: ruff "All checks passed!", the smoke steps ending "config check: ok, 173 unverified values", and pytest in three parts: 941 passed in 1323 s, 268 passed in 214 s, 1161 passed in 304 s. That is 2370 passed, the same count the commit reports. The line "check: green" itself was never seen.
4. **Conformance: OK.**
   - No config values, dependencies, network, secrets, wall clock or in-repo state added. I-9: the new `src/` lines name no market, contract or venue.
   - O-25 holds: `control_moments` defaults to `net_1x`, `exposure` defaults to None, and `S`, `E_N`, `excess` are unchanged.
   - The 148 (e) figures are computed by the test itself (`own_adjusted_deflated` / `own_slot_series` work from the journal, not from `table.py`). The tests also assert that the three new fields differ from the plain ones, that `adjusted_S` equals `adjusted_sharpe`, the nulls on controls and portfolio rows, and the `(adjusted)` headings.
   - Register classes match 147 (c) and 148 (b), and `PENDING` is the empty set.
   - The `tests/gates/` change is exactly 148 (d)'s one line (89 characters), and the body quotes O-23.
5. **Forbidden touches: none.** No changes under `config/`, `meta/`, DESIGN, SPEC, `.claude`, `templates` or `docs`, and no new dependency.

**Not proven:**
- The three wrong changes "seen to fail" in the body: I did not redo them.
- The body's timings (check about 1125 s, G1.3 855 s) and the gate passes: I did not run the gates.

The worktree is removed. Two other leftover worktrees remain from earlier work, `/tmp/rv13-8b9f9be` and `/tmp/u5/parent`; I did not touch them.

### a7854da (U2)

Commit a7854da (mission 19, U2): PASS, with one small inaccuracy in the commit body.

1. **Unit and sections: PASS.** The body names mission 19 U2, decisions 149 and 150 (with O-5, O-6, O-24), and DESIGN §11.1, §15.1 and §16.1 step 6. That matches the U2 brief.
2. **Test-first: PASS.** With the src files put back to a7854da~1 and alerts.py removed, `tests/test_alerts.py` fails to collect (ImportError, no alerts module). The other three files give 17 failed, 68 passed: all 15 t_sf tests, the changed `test_monday_appends_block_2s_row...` and `test_return_readers::test_the_audit_passes`. Replacing `statistic` with the timing figure turns 2 tests red (`test_the_row_holds_timing_and_gross...` and the Monday test). Returning `2*tail` (the two-sided figure) turns 8 of the 15 t_sf tests red. The tree was restored and `git status` was clean.
3. **check: PASS.** `./scripts/check` run once: last lines `config check: ok, 173 unverified values` / `check: green`, 1036 s wall.
4. **Conformance: PASS.**
   - **149 (a)–(d):** met. `alerts.rank_rows` makes one `paper.adjusted(...,"gross")` call per subject per block, calls `rank_persistence` on timing, gross and net_1x, keeps `statistic` as the net 1x figure, and raises ValueError when `subjects` differ. `daily._rank_persistence` calls it, and the tests 149 (d) asks for are present.
   - **150:** met. Every literal test is there with its stated tolerance (1e-12, and 1e-6 at the critical values). t_sf uses only `math` and no dependency was added.
   - **rank_persistence and the register:** `stats.rank_persistence` is unchanged (the stats.py diff only adds lines). The register entry `alerts.rank_rows` is `timing_gross`.
   - **Invariants:** I-9, I-10, I-11, I-12 and I-14 hold. No market names, no threshold literal in src (it reads `alerts.rank_min_population` from setup), no wall clock, and tests run in temporary directories.
   - **Existing test:** the only change admits `timing` and `gross` and adds asserts; nothing is loosened.
5. **Forbidden touches: PASS.** The commit changes nothing under `config/`, `tests/gates/`, `meta/`, `.claude/`, the protected documents, `pyproject.toml` or `uv.lock`.

**Not proven by me:** the other two wrong changes of 149 (d) (one window spanning both blocks, `timing` filled from plain gross), the G1.1 gate result (424 s), the speed figures and the three check runs, all as claimed in the body.

**Defect (minor, commit body only):** the body says the two-sided mutation turned "red all 15 t_sf tests". With the `2*tail` form I tried, the 7 `test_t_sf_of_minus_t_is_one_minus_t_sf_of_t` cases stay green. That test can't catch it: `src/discotrade/stats.py` (last line of `t_sf`) computes the negative side as `1 - tail` by construction. The overclaim holds unless the builder used a different, unstated mutation. The code itself is fine.

### efc35de (U3)

efc35de: **PASS**. I found no blocking defect.

1. **Unit and sections: PASS.** Mission 19, U3, "persistent_approach and group_edge on the exposure-adjusted series". It claims DESIGN §15.1 and §11.2 to §11.4, O-7, O-16, O-24 and decision 151.
2. **Test-first: PASS.**
   - With alerts.py and paper.py put back to efc35de~1, the three test files went red: 7 failed, 6 errors, 50 passed (AttributeError, plus the register audit reporting the four missing readers). At efc35de they pass, 63 of 63.
   - Four wrong changes, each made alone and reverted, each turned tests red:
     - `k` truncated instead of rounded: 4 failed.
     - exposed days counted in W: 2 failed.
     - bootstrap seed changed to `seed_of(D)+1`: 4 failed.
     - plain Sharpes in persistent_approach: 3 failed.
   - The tree was clean after `git checkout efc35de -- .`.
3. **Check: PASS.** One `./scripts/check` run ended with `config check: ok, 173 unverified values` / `check: green`, wall time 18m7.9s. My tail cut off the pytest summary line, so the pass count of 2405 is the commit's claim, not something I read.
4. **Conformance: PASS.**
   - The W definitions, the three-part condition, `N` from the trials ledger, `k = max(1, floor(x+0.5))`, the seed as YYYYMMDD of D with `rng.choice` without replacement in slot order, `np.quantile(..., 1-level)` and the payload fields all match 151 (a) and (b).
   - Tests read the production config/thresholds.toml through `journal.Setup.load` and assert 60 and 120. They cover both sides of 59/60 days, the 2x Sharpe, the 1x threshold, 119/120 dates, the quantile and the rounding of `k`. Expected figures come from the tests' own arithmetic, not from `alerts`, `stats` or `paper.adjusted`.
   - `paper.portfolio` is unchanged; only `clean_members` was added (O-25). The four register entries are `adjusted` with notes citing O-7, O-24 and 151.
   - Invariants: alerts.py has no threshold literal outside docstrings (I-10) and no wall clock or network use (I-11, I-12). Tests write only under tmp (I-14) and I saw no market name in the new code (I-9). No new dependency. The commit body lists all five files and claims only what the tests show.
5. **Forbidden touches: PASS.** The diff touches nothing under config/, tests/gates/, meta/, DESIGN.md, SPEC.md, PLAYBOOK.toml, .claude/, docs/, templates/, pyproject.toml or uv.lock.

**NOT proven:**
- That either rule fires on any replay; the day loop does not call them yet (U4 wires them).
- The bootstrap and normal quantiles are checked only against the test's own computation, not an outside package.
- I did not run the "one average position shared by all slots" wrong change.

**Findings (not defects):**
- `src/discotrade/alerts.py:353` raises ValueError when portfolio_clean's dates and `clean_members` disagree. Once U4 wires the rules in, this could abort a day loop on inconsistent records. The commit discloses it as a design choice.
- `slot_series` drops any slot without a row on every day of W, for persistent_approach too. Decision 151 (a) does not say this; (b) says it only for the bootstrap. If no slot covers W, `mu_c` is not a number and the rule cannot fire.

The worktree at /tmp/rv19-efc35de has been removed, and /home/msi/git/discotrade was not modified.

(Reviewer: the second remark is not a defect. `stats.control_moments` already takes
only slots with a row on each day of its window, as 151 (a)'s `(mu_c, sd_c)` cites
it, so dropping them in `slot_series` changes nothing. At the tip the `ValueError`
is at `alerts.py:415`, Notes 4.)

### 3ee67d3 (U4)

Commit 3ee67d3 passes on all five points. I found no defect that breaks an invariant, only two minor notes.

1. **Unit and sections: PASS.** It is mission 19 U4. It claims decisions 152 and 149 (c), DESIGN §15.1 to §15.3, §16.1 step 6 and §16.2, and I-5, I-6, I-10 and I-12. The body lists all four files.
2. **Test-first: PASS.** With alerts.py and daily.py reverted to the parent, the 18 new tests (30 cases once parametrized) give "30 failed". Each wrong change, made alone and reverted, turned tests red:
   - firing on every true day: 1 failed;
   - cost_stale counting from `date.today()`: 1 failed;
   - rank_persistence read on `statistic`: 5 failed.
   The tree was clean afterwards.
3. **./scripts/check: PASS, run once.** It ended `config check: ok, 173 unverified values` / `check: green`, with pytest at "2435 passed, 204 deselected in 1121.40s". Wall time was 18m44.8s, under the 20-minute cap.
4. **Conformance to 152 (a)-(g): PASS.**
   - State and payloads are written with `ledger.line`, atomically, into staging, on a new day only. `quote(subject, safe="")` is used and payloads are never rewritten.
   - The firing rule and `since` match 152 (b). Every threshold goes through `in_force`, which reads `setup.thresholds`. `THRESHOLD_KEYS` names every key the rules read, plus `alerts.rank_min_population`.
   - rank_persistence reads `timing`, uses 12 blocks and skips evaluation with fewer than 12 or with s=0.
   - The detector windows are right and cost_stale counts from D, so no wall clock.
   - The day loop does not call no_finding, and the step 6 order matches 152 (f).
   - On revival: it calls the same `stats.trading_dates` that lifecycle step 3 calls, over the same window. But it is a copy of the call at alerts.py:~530, not a helper shared with lifecycle.py:266, so the two could drift apart later.
5. **Forbidden touches: PASS.** `git diff` shows nothing under `config/`, `tests/gates/`, `meta/`, `.claude/`, DESIGN or SPEC, and there is no new dependency. The only removed test line is an import rewrapped in tests/test_daily.py.

Minor notes:
- **Health events written directly (daily.py:548).** Detector events go straight into the state directory's health log, not staging. That matches how the other health events in this loop are handled. But if alerts.step or the table then fails, the events stay, and the retry appends them again for D. `health()` copes with the duplicates, so this does no harm.
- **Old health subjects never leave the state (alerts.py `health`).** Every subject ever raised stays in state.json as an inactive entry, so the file only grows. This fits 152 (a)'s wording.

I did not rerun the gates (G1.2 and G1.3), the speed figures or the replay comparison; those are the builder's claims only. I ran check once, not three times.

The worktree /tmp/rv19-3ee67d3 is removed. The /tmp/rv13-8b9f9be and /tmp/u5/parent worktrees were already there, and I left them alone.

### a21beb7 (U5)

a21beb7 (mission 19 U5): I'd accept it. One deviation should be filed as a finding, and two things are not proven. The repository is unchanged, and my worktree is removed.
1. Unit and sections: PASS. It is U5, the dashboard. The body cites decision 153, O-6/14/16/18, DESIGN §15.5, §3 and §16.1 step 7, SPEC §13/§14, and I-6/10/12/14.
2. Test-first: PASS. With the source files reverted, `test_dashboard.py` fails to import (no module `dashboard`), and 3 tests in `test_cli.py`/`test_return_readers.py` fail (both new CLI tests and `test_the_audit_passes`). Each of 153 (d)'s wrong changes went red on its own and was reverted: literal 126 for `min_clean_days`, a hand-written marked threshold, `<script>`, and `portfolio` in place of `portfolio_clean` (3 cases red). `git status` was clean afterwards.
3. Check: PASS, one run. Last lines: "2458 passed, 204 deselected in 1154.89s", "config check: ok, 173 unverified values", "check: green". Wall time was 19m17.8s, close to the 20-minute cap.
4. Conformance: PASS except the items below. No script, link, external URL, `@import` or `url(`; viewport present; one max-width column; no wall clock, the page names D; 8 panels in SPEC §13 order with the contents 153 (b) lists; all `THRESHOLD_KEYS` shown, marked and equal to `in_force`. `--out` inside the state is refused, step 7 runs only on a written day, and `gates.toml` holds two false flags and is not frozen. The register has exactly one `stage3_money` entry plus 5 display entries. `BAND` (0.05, 0.95) is fixed by 153 (b) 3 and is display only, so it is not an I-10 threshold. I-9, I-11 and I-14 are respected, and there is no new dependency. The body lists all 9 files.
5. Forbidden touches: PASS. The only change under `config/` or `tests/gates/` is the permitted new `config/gates.toml`, and no protected file is touched.
- Deviation, needs a finding: `src/discotrade/dashboard.py:395-404` (`_rank_p`) works out the rank rule's `p` from the state's mean and critical mean. 152 (a) says the dashboard never recomputes the rules' figures, but the state cannot hold `p` (`alerts.py` `ENTRY_KEYS`). The body calls the design "silent" here, but this is a conflict with 152 (a), and no D-### was filed. It also uses the current thresholds, not the ones the state was written under.
- Test gap: a literal used only in a calculation is not caught. `window = 20` at `dashboard.py:575` in place of `pool.fail_window` left all 21 tests green, so 153 (d)'s literal case is covered only for shown values and verdicts.
- NOT proven: the figures `_rank_p`, `p(N)`, `exposure_part`'s adjusted figure and positions, and the band, running mean and significance band, which no test computes independently (the body says so). Readability on a phone.
