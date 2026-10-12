# REVIEW-7 — cold review of mission 7 (step S1.1: state, health log, journal, run-day)

Base 10d6024 (`review: mission 6`, the last `review:` commit), tip
4ae8d43 (`origin/main`). Range, `git log --oneline 10d6024..origin/main`:

```
4ae8d43 meta: mission 7 U6 done, mission finished
853cd12 report: mission 7 final report
6aea7c0 meta: mission 7 U5 done, checkpoint to U6
073a5bd journal: journal recompute, every pair with --all or a sample seeded with D
40131a4 meta: mission 7 U4 done, checkpoint to U5
1fbf800 daily: run-day steps 1 and 2 with the paper records, one commit per day
a6e782a meta: mission 7 U3 done, checkpoint to U4
e44866d journal: approaches in the state and the decision journal, one day file at a time
55ec913 meta: mission 7 U2 done, checkpoint to U3
c8342c4 state: the state directory, the lock, the state commit and the health log
5b0e258 meta: mission 7 U1 done, checkpoint to U2
de2a5b2 tests: socket backstop holds from session start, in every fixture scope and through _socket
057f9d2 plan: mission 7 plan, checkpoint, HF-007
c73a695 plan: mission 7 kit (S1.1, state, health log, journal, run-day)
```

There are five unit commits: de2a5b2, c8342c4, e44866d, 1fbf800 and 073a5bd.
Each one was reviewed by its own foreground sub-agent, in a worktree at
that commit. I read the `plan:`, `meta:` and `report:` commits myself and
looked only for forbidden edits:

- c73a695 is the architect's kit: KIT.md, BACKLOG, ROADMAP, the decisions
  file and BUILDER-7-PROMPT. It is exempt, as in REVIEW-4 to REVIEW-6.
- 057f9d2 touches CHECKPOINT, journal, plan and FINDINGS. Its only
  FINDINGS change is the HF-007 entry, which matches the U0 brief:
  severity low, the named component, status open.
- 5b0e258, 55ec913, a6e782a, 40131a4, 6aea7c0 and 4ae8d43 touch only
  CHECKPOINT, journal and plan. 853cd12 touches only FINAL-REPORT-7.
- No unit commit touches `meta/plan.md`, `meta/CHECKPOINT.md`, `meta/`,
  `config/` or any file CLAUDE.md reserves.
- These diffs are empty:
  - `git diff 10d6024 origin/main -- config/ tests/fixtures/`, so no frozen
    value and no fixture record changed;
  - `pyproject.toml`, `uv.lock`, `scripts/` and `tests/gates/`, so no new
    dependency, script change or gate test.

My own checks at the tip:
- The six new test files plus the `test_cli.py` additions collect 92 + 3 =
  95 tests, as the report says.
- Every test name that the report's "Decisions 47 to 55" section cites
  exists under `tests/`.
- `init-state --help`, `run-day --help` and `journal recompute --help` each
  list `--state`, `--track`, `--config` and `--as-of`. `run-day` also lists
  `--day`, and `journal recompute` lists `--all`.
- No `datetime.now`, `time.time()`, `date.today` or `utcnow` appears in
  `state.py`, `journal.py`, `daily.py`, `paper.py` or `cli.py`.

## Gate

not a closing mission

The brief says the mission "does not close a milestone and adds no test
under `tests/gates/`". The report's `## M0 still passes` section was run by
the builder. As this review's own evidence, U3's sub-agent ran `./scripts/gate
M0 G0.1` at e44866d, the only unit that changed `backtest.py`, and got
`G0.1 PASS 62 passed` and `gate M0 G0.1: PASS`.

## Blockers

None.

## Should-fix

1. FINAL-REPORT-7's NOT PROVEN list for U1 leaves out two network paths
   that the backstop does not guard.
   - `tests/conftest.py:52` guards only `connect`, `connect_ex` and
     `sendto` on `socket.socket`, plus `getaddrinfo`.
   - U1's sub-agent found that a UDP `socket.sendmsg` to an address
     succeeds under the guard.
   - `gethostbyname` and `gethostbyname_ex` are not guarded either.
   - Decision 47 says "every attempt to open a network connection fails".
     Neither path is in U1's gate, and the base did not guard them, so this
     is not a regression. But the report lists its other unguarded paths
     (`SocketType`, an early `from _socket import socket`, child processes)
     and not these.
   - Fix: list them as not proven, or guard them in the next mission that
     touches `tests/conftest.py`.
2. FINAL-REPORT-7's NOT PROVEN list for U5 does not say what the mismatch
   test cannot distinguish.
   - `test_one_changed_field_exits_1_prints_the_pair_and_appends_one_journal_mismatch`
     changes only `net_1x` of one stored row.
   - So no test separates decision 54's whole-span recompute ("each subject
     evaluated once from its first journaled day to the last") from a
     recompute that chains through the stored `position` and `target_next`
     values.
   - The code is right: `span_rows` starts flat and reads no stored
     position. Only the proof is missing.
   - Fix: list it as not proven, or add a test that corrupts a stored
     `target_next` or `position`.

## Notes

- U3's commit body (e44866d) says "tests/test_journal.py (new, 18
  tests)". The file collects 17: 15 functions, one of them parametrized
  over three strategies. FINAL-REPORT-7 states and corrects this, so it is
  a note, not a blocker.
- U2, `src/discotrade/state.py:213-217`: `init_state` is not atomic. A
  failed first commit after `git init` leaves a directory that every later
  run refuses as non-empty. NOT PROVEN covers this ("refused with exit 1,
  not repaired").
- U2: `test_git_runs_with_only_the_file_protocol` checks only the
  environment dict that `state.git_environment()` builds. It does not check
  that `_git` passes that dict to git. The commit-date tests cover the
  passing indirectly.
- U2: U2's sub-agent tested git isolation against a hostile setup: a
  global config with `gpgsign` and a failing pre-commit hook through
  `hooksPath`, plus `GIT_DIR`, `GIT_AUTHOR_NAME` and `GIT_CONFIG_PARAMETERS`
  in the environment. Commits still came out as `discotrade` at the
  clock's instant, unsigned.
- U3, `src/discotrade/journal.py:87`: `REPO_ROOT = parents[2]` finds
  `reference/` and `tests/fixtures/` only from a source checkout. That is
  enough for step S1.1, but step S2.2 or the deployment package (§19.2)
  must decide where trusted sources live when the package is installed.
- U3: the journal shares §7's one implementation by calling
  `backtest.evaluate` once per one-day window with the carried state. The
  equality test compares 12 one-day calls against one call over the whole
  span. Two mutants that U3's sub-agent added each turn 2 of the 3
  strategies red: reverting the boundary `prev_close`, and zeroing the
  boundary `gross`.
- U4, `src/discotrade/daily.py:75, :234`: `revised_data` is detected by
  matching the text "a revised data point" in a `BarStoreError` message.
  NOT PROVEN discloses this. A typed error would be sturdier.
  `daily.py:136` calls the private `store._indexed_last_ts`.
- U4: the trade floor 1e-9 is `metrics.TRADE_FLOOR`, which already existed.
  DESIGN §8 and decision 53 both state it, so this is not an I-10 breach.
- U5: `journal recompute` appends its `journal_mismatch` line to the health
  log and leaves it uncommitted until the next `run-day` commit. This is
  allowed by decision 54 ("writes nothing else"), but `git status` in the
  state directory is not clean after a mismatch.
- U5: the recompute and `run-day` share `evaluate()`, as decision 49
  requires, so a fault inside `evaluate` would show in both and not be
  caught by `journal recompute`. This is inherent to the design.
- The sub-agents ran `./scripts/check` once (U1, U3) or twice (U2, U4, U5).
  Each run was green. The three green runs in a row before each commit
  rest on the builder's statements. The five sub-agents ran concurrently on
  one machine, and no run was red on timing.
- hands: as HF-007 records, step 2 of the protocol is vacuous for
  de2a5b2, which changes only tests. Its sub-agent made the wrong changes
  the body names instead, and also ran the new tests against the parent's
  conftest (4 red). The protocol still does not name this path, and it does
  not say how many `./scripts/check` runs a reviewer owes. HF-007 is open.
- hands: the protocol asks for at most 12 lines per sub-agent report. Some
  reports below run a few lines over because of point-by-point detail.
  They are kept verbatim.

## Per-commit verdicts

### de2a5b2 (U1)

```
Verdict on de2a5b2 (U1, mission 7): PASS. One low-severity gap, not a defect against the gate (4).

1. **Unit:** U1 (REVIEW-3 note; decisions 20 and 47; I-11; DESIGN §18.1). It touches only `tests/conftest.py` and a new `tests/test_offline.py`, which matches the brief.
2. **Test-first: PASS.** The commit changes only tests, so reverting its non-test files is vacuous. I made the wrong changes the body names, uncommitted:
   - Backstop moved into an autouse function-scoped fixture: the module-scoped, session-scoped and error-naming tests went red (3 failed).
   - `_socket.socket` replacement removed: the `_socket` test went red.
   - At the parent's conftest: 4 failed (module, session, names-test, `_socket`). This confirms the body's claim that the base turns the `_socket` test red.
   - Two extra changes also went red: the guard never lifted (the scratch network test failed) and `_socket.getaddrinfo` left unguarded.
   - All changes were restored; the worktree was clean before removal.
3. **`./scripts/check`: PASS.** One run at de2a5b2 ended `config check: ok, 168 unverified values` then `check: green`. Pytest gave `951 passed, 86 deselected`, and `tests/test_offline.py` alone gave 9 passed. No timing reds.
4. **Design: PASS.** The guard is installed in `pytest_configure` and holds in module- and session-scoped fixtures and through `_socket`. Network/live tests are lifted only for their setup, call and teardown, and the scratch session shows this. The subprocess listing equals `SUBPROCESS_FILES` on today's tree and fails naming an added src or test file. The existing tests in `test_cli.py` (decision 20) and `test_gate_script.py` (gate markers, skip-is-failure) are unchanged and pass. I-9, I-10, I-11, I-12 and I-14 hold, and `pyproject.toml` and `uv.lock` are unchanged.
5. **Forbidden edits: PASS.** Nothing touched under `src/`, `config/`, `meta/`, `.claude/`, or the design, spec and playbook files.
6. **Body claims: PASS.** The file list, the 951 count and the seen-to-fail claims all match what I saw on disk.

**Not proven:** the body's three green runs (I ran check once). The `SUBPROCESS_FILES` descriptions of what each file launches were not checked against each call site. The listing only names files; it does not check the git `GIT_ALLOW_PROTOCOL=file` rule.

**Gap (low):** `tests/conftest.py` `install_backstop` does not guard `socket.socket.sendmsg` (a UDP `sendmsg` to an address succeeded under the guard) or `gethostbyname`/`gethostbyname_ex`. Both still let traffic leave the host. The base did not guard them either, and the U1 gate does not require them; the body does not list them in its "where the design is silent" section.
```

### c8342c4 (U2)

```
Commit c8342c4 (U2) passes on every point and I found no blocking defect.

1. **Unit:** U2 of BUILDER-7, step S1.1. It cites DESIGN §3, §9.1, §15.2 and §16.2, decisions 7, 50, 52 and 55 (with 4 and 47), and I-5, I-12 and I-14.
2. **Test-first: pass.** With `state.py` and `cli.py` put back to the parent, `test_state.py` fails at collection (ImportError on StateError). In `test_cli.py` and `test_offline.py`, 4 tests fail: the three init-state help tests and the subprocess-list test. Each of the three named wrong changes turns its named tests red, and nothing else:
   - lock opened without O_EXCL: the second-lock test fails.
   - duplicate check removed: the line-already-present test fails.
   - commit dates not set (wall clock): the init test and the state-commit test fail.
3. **`./scripts/check`: green**, with no timing failures. The final lines were `================ 985 passed, 86 deselected in 474.47s (0:07:54) ================` and then `config check: ok, 168 unverified values` / `check: green`. I ran it twice; both were green.
4. **Design conformance: pass** on every gate item you listed. Git hygiene is good: `git_environment()` drops every inherited `GIT_*` variable and sets GIT_CONFIG_GLOBAL=/dev/null and GIT_CONFIG_NOSYSTEM=1. I probed this with a hostile HOME config (gpgsign on, a failing pre-commit hook through hooksPath, user.name=evil) plus GIT_DIR, GIT_AUTHOR_NAME and GIT_CONFIG_PARAMETERS set in the environment. Both commits still came out as author discotrade, at the clock's instant, unsigned. I-9, I-10 and I-14 hold, there is no wall-clock call in the new code, and no new dependency.
5. **Forbidden edits: none.** Only `state.py`, `cli.py` and three test files changed; nothing under `config/` or `meta/` and no CLAUDE.md-listed file. One small, disclosed scope note: the U2 brief lists only `state.py`, `cli.py`, `test_state.py` and additions to `test_cli.py`, but `tests/test_offline.py` also changed. Decision 47 requires that change. The "sorted both sides" edit keeps the same file-list check; it only drops a check on the order of the scan.
6. **Commit body: accurate.** The file list, the 985 count, the wrong changes and the "design is silent" choices all match the disk. Nothing overreaches.

**Not proven:**
- The held-lock exit 1 through the command line. The lock raises StateError, but turning that into exit 1 belongs to run-day, a later unit.
- The fsync inside `write_atomic` (reused from `bars/store.py`) has no test of its own here.

**Minor findings (not defects against the gate):**
- `src/discotrade/state.py:213-217`: `init_state` is not atomic. If the commit fails after `git init`, the directory is left with `.git` and `.gitignore` but no HEAD, and every later run exits 1 as "not empty".
- `tests/test_state.py`, `test_git_runs_with_only_the_file_protocol`: it only checks the environment dict, not that `_git` passes it to git. The date tests cover that indirectly.
```

### e44866d (U3)

```
e44866d (mission 7, unit U3) passes on points 1 to 5. Its only defect is in the commit body: it says "18 tests" but the file collects 17.

1. **Unit:** U3, approaches and the decision journal. It cites DESIGN §6.2, §7, §9.1, §9.2, decisions 24, 25, 39, 48, 49, 51, and I-5, I-6, I-7. This matches the U3 paragraph of BUILDER-7-PROMPT.
2. **Test-first: PASS.** With the parent's backtest.py and state.py back and journal.py removed, tests/test_journal.py fails at collection (`ImportError: cannot import name 'journal'`). At the commit it gives 17 passed. I made each wrong change the body names and got the same counts it reports:
   - position reset to start (0,0) each day: 4 failed;
   - first row's position taken as its target: 3 failed;
   - re-run writing the file again: 1 failed.
3. **Gates: PASS.**
   - `./scripts/check`: `1002 passed, 86 deselected in 332.27s`, `config check: ok, 168 unverified values`, `check: green`.
   - `./scripts/gate M0 G0.1`: `G0.1 PASS 62 passed in 142.49s (0:02:22)`, `gate M0 G0.1: PASS`.
4. **Design conformance: PASS.**
   - The test computes the approach id independently from decision 48's definition.
   - meta.json holds all 12 §9.1 fields exactly; the cost model is c1 and the config hash is decision 26's.
   - An untrusted source fails the day, naming the approach, before anything is written.
   - The columns equal §9.2 and decision 49 in order. The first row is flat, the carry crosses day boundaries, and fill_price is the raw open.
   - The content hash uses `state.content_hash` sorted on subject, instrument, ts.
   - A day is written once with its index line; an equal re-run leaves bytes, inode and mtime unchanged; an unequal re-run leaves the files and returns `journal_mismatch` naming the day and subject. An empty day writes an empty file and its index line.
   - **backtest.py:** with `start=None`, behaviour is unchanged. The new `prev_close[0]` value only matters when `before[0]` is non-zero, and `gross[0]` is still zeroed.
   - **One implementation of §7:** the journal calls `backtest.evaluate` per one-day window with the carried state, so it shares the loop, executor and cost model rather than copying them.
   - **The equality test is meaningful:** it compares 12 one-day calls against one full-span call, not the same window twice. I added two extra mutants: reverting the boundary `prev_close` turns 2 of the 3 strategies red, and zeroing the boundary `gross` does the same.
   - **Writes:** all go through `write_atomic`, and the index is the old bytes plus one new line (I-5). Writing for U4's staging goes through `into=`.
   - **Invariants and dependencies:** no clock read (I-12), no venue names (I-9), no new dependency, and no edits to pyproject.toml, uv.lock or config.
5. **Forbidden edits: PASS.** The commit touches only backtest.py, journal.py, state.py and tests/test_journal.py.
6. **Commit body: one overclaim.** It says "tests/test_journal.py (new, 18 tests)", but there are 17: 15 functions, one of them run for three strategies. Every other claim held on disk.

**Not proven:**
- Three-in-a-row check is not proven; I ran `./scripts/check` once.
- The staging path (`write_day(..., into=)`) has no test in this unit; it is U4's.
- `journal.py:87` (`REPO_ROOT = parents[2]`) finds `reference/` and `tests/fixtures/` only from the source tree. That is fine for S1.1 but would break in an installed package.
```

### 1fbf800 (U4)

```
1fbf800 (U4, run-day and the paper records): **ACCEPT**, no blocking defect found.

1. **Unit:** U4 of BUILDER-7. The commit claims DESIGN §9.3, §15.2, §16.1 steps 1 and 2, §16.2, §5.4 and §5.6, plus decisions 2, 3, 19, 50–53 and 55 and I-6 and I-12. That matches the brief. It also cites §5.6, which the brief does not list; that is reasonable for rolls. Decision 16 is used implicitly (notices go to the health log).
2. **Test-first: PASS.** With the parent's cli.py and no daily.py or paper.py, the tests are red (2 collection errors). Each wrong change I made, then reverted, gave the count the body claims:
   - a re-run writing a second index line into staging: test_daily 2 failed / 18 passed;
   - the lock taken by hand and removed only on success: 4 failed / 16 passed;
   - paper trades counting `trade > 0`: test_paper 1 failed / 6 passed;
   - test_daily.py removed from SUBPROCESS_FILES: test_offline 3 failed.
3. **./scripts/check: PASS** (ran it twice, green both times). Final lines: `config check: ok, 168 unverified values` / `check: green`; pytest `1029 passed, 86 deselected in 419.83s`.
4. **Design conformance: PASS.**
   - **Staging is real:** the journal file and index go into `state.STAGING` through `journal_day(into=staging)`, and paper through `paper.rebuild(overlay=staging)` then `write(staging)`. `_move` (`os.replace`) runs only after both succeed. The staging directory is removed in `finally`, and the commit happens only when the day is WRITTEN. Step 1 is not staged, which decision 50 allows.
   - **Lock:** held with `with state.lock`, so it is released on success and failure.
   - **Refusals:** a state not made by init-state, a skipped day, and an unclosed or non-trading day are refused before step 1 writes anything.
   - **gaps.max_fraction** is read from `setup.thresholds` (I-10).
   - **The 1e-9 floor** is `metrics.TRADE_FLOOR`, a constant that already existed. DESIGN §8 line 664 states it, and so does decision 53, so it is sanctioned.
   - **cli.py** `_closed_day` is a pure move, identical code.
   - **Invariants:** no wall-clock reads in daily, paper or cli (I-12); no market names in the new files (I-9); pyproject unchanged, so no new dependency.
5. **Forbidden edits: PASS.** Only the 6 files listed were touched; no config/, meta/, or fixture changes.
6. **Commit body: PASS.** The file list matches disk and all four "seen to fail" claims reproduce. The body states no test counts, so there were none to check.

**Minor issues (none blocking):**
- `revised_data` is detected by matching the text `"a revised data point"` (src/discotrade/daily.py:75, :234). This is fragile: it works because all the `BarStoreError` messages at bars/store.py:230, 263 and 304 contain that phrase, but a typed error subclass would be more robust.
- `_fetch` calls the private `store._indexed_last_ts` (daily.py:136).

**Not proven by me:** I did not trace the two-fresh-states equal-hash test (decision 55) or the paper-matches-`daily_series` test beyond them passing.
```

### 073a5bd (U5)

```
**073a5bd, mission 7 U5 (`journal recompute`): PASS. No defect found.**

1. **Unit:** U5 claims decision 54, DESIGN §9.4, §15.2 and §3, and I-6. It also reuses the keys of decision 49 and the health-log append of decision 52; time comes only from `--as-of` (decision 55).
2. **Test-first: PASS.** With the parent's `journal.py` and `cli.py`, 6 of 8 tests fail. The 2 that pass are the seed-fixture test and the "draw seeded otherwise differs" test, which only call numpy. Each wrong change went red, then I reverted it:
   - comparing the stored rows with themselves: 1 fails
   - using the stored rows as the "recomputed" ones: 1 fails
   - seeding with `D.toordinal()`: 2 fail
   - seeding with a constant: 2 fail
   - letting the pool include D itself: 3 fail
3. **`./scripts/check`: green twice.** Run 1 ended `config check: ok, 168 unverified values` / `check: green`. Run 2: `1037 passed, 86 deselected in 427.88s (0:07:07)`.
4. **Design conformance: PASS.**
   - **Sample size:** `journal.recompute_sample` is read from thresholds (cli.py:583), not a literal (I-10).
   - **D:** it is decision 19's `closed_day` at the injected clock (cli.py:582).
   - **Draw:** `default_rng(YYYYMMDD).choice(..., replace=False)` over a pool sorted by (day, subject) and limited to days before D. Results come back in sorted order (journal.py `sample_pairs`).
   - **Lock and writes:** the command holds the run lock and removes it afterwards. It never runs `bars fetch` or a git commit; its only write is the health-log append, which skips duplicates.
   - **Evaluation:** `span_rows` evaluates each subject in one window starting flat (previous=0, no `start`). So it does not depend on the positions carried in stored rows.
   - **Shared code:** it does share `evaluate()` with `run-day`, as decision 49 requires, so a bug inside `evaluate` would not be caught. That is inherent to the design, not a defect.
   - **Invariants:** I-9, I-11, I-12 and I-14 hold. No wall-clock read and no subprocess in `journal.py`. No dependency, lockfile or config change.
5. **Forbidden edits: none.** The commit touches only `cli.py`, `journal.py` and the new test file.
6. **Commit body vs disk: accurate.** The file list is right and both "seen to fail" claims reproduce.

**Not proven:**
- The mismatch test changes only `net_1x`, so it cannot tell a whole-span recompute from one chained through stored positions (a corrupted stored `position` is never tested).
- The appended health line is left uncommitted in the state repo, so the next `run-day` commit will include it. This is allowed by "writes nothing else", but worth knowing.
```
