# REVIEW-8 — cold review of mission 8 (step S1.2: controls, ledgers, lifecycle, clean flag, statistics of §11)

Base eabcc5b (`review: mission 7`, the last `review:` commit), tip
7bf92bc (`origin/main`). Range, `git log --oneline eabcc5b..origin/main`:

```
7bf92bc meta: mission 8 U5 done, mission finished
37e4d97 report: mission 8 final report
3d620f2 meta: mission 8 U4 done, checkpoint to U5
451471e controls: buy-and-hold and random pool journaled every day, monthly draws
7b88e0b meta: mission 8 U3 done, checkpoint to U4
327c68a lifecycle: the three ledgers, steps 1 to 4 in run-day, and admission
f8e1c40 meta: mission 8 U2 done, checkpoint to U3
abba5d3 stats: rank persistence, deflated scores, tightening; paper clean flag
db1ccf9 meta: mission 8 U1 done, checkpoint to U2
060b5e2 tests: guard sendmsg and the name lookups; recompute reads no stored position
b06c4b2 plan: mission 8 plan, checkpoint and journal (S1.2)
fb1e244 plan: mission 8 kit (S1.2, controls, ledgers, lifecycle, stats)
```

The four unit commits are 060b5e2, abba5d3, 327c68a and 451471e. Each was
reviewed by its own foreground sub-agent in a `git worktree` at that commit.
I read the `plan:`, `meta:` and `report:` commits myself, looking only for
forbidden edits:

- fb1e244 is the architect's kit: KIT.md, BACKLOG, ROADMAP, the decisions
  file and BUILDER-8-PROMPT. It is exempt, as in REVIEW-4 to REVIEW-7.
- b06c4b2, db1ccf9, f8e1c40, 7b88e0b, 3d620f2 and 7bf92bc touch only
  `meta/CHECKPOINT.md`, `meta/journal.md` and `meta/plan.md`. 37e4d97
  touches only `meta/FINAL-REPORT-8.md`.
- No unit commit touches `meta/plan.md`, `meta/CHECKPOINT.md`, anything
  under `meta/`, or any file that CLAUDE.md reserves.
- At the tip, `git diff eabcc5b origin/main` is empty for: `config/`,
  `tests/fixtures/config/`, `tests/fixtures/config_frozen.json`,
  `tests/gates/`, `DESIGN.md`, `SPEC.md`, `PLAYBOOK.toml`, `.claude/`,
  `templates/`, `docs/`, `meta/ARCHITECT.md` and `meta/REVIEW-PROTOCOL.md`.
  `config/models.toml` does not exist.
- No finding was filed: `meta/findings/FINDINGS.md` is unchanged. The
  report says the same.

## Gate

not a closing mission

The brief says the mission "does not close a milestone and adds no test
under `tests/gates/`", and `tests/gates/` is unchanged. The `## M0 still
passes` section of the report is the builder's own run. I did not repeat
it.

## Blockers

None.

## Should-fix

1. **U3 (327c68a): no test shows that revival counts *trading* days.**
   Decision 63 (3) and the U3 brief require a dormant approach to wait
   `revival_min_dormant_days` **trading days of the track** before it can
   return. The code counts trading days correctly
   (`src/discotrade/lifecycle.py:210-212`, using `trading_dates` over the
   track's calendars). The tests cannot tell that count from a calendar-day
   count, because `test_mixed` includes SYNX on the `always_open`
   calendar, so every calendar day is a trading day. The U3 sub-agent
   replaced the count with `(day - s.since).days` and all 49 tests in
   `test_lifecycle.py` and `test_daily.py` still passed. FINAL-REPORT-8 says
   "not at 4 trading days, at 5", which is literally true, but its NOT
   PROVEN section does not mention this gap. The fix is a test on a track
   or calendar copy under tmp where a non-trading day falls inside the
   waiting span, seen to fail on the calendar-day count.
2. **U1 (060b5e2): a test comment over-claims that an unguarded lookup
   sends no query.** The comment at `tests/test_offline.py:110-111` says
   every lookup argument "needs no resolver ... so that even an unguarded
   call sends no query". `gethostbyaddr("127.0.0.1")` is a reverse lookup,
   and `NI_NUMERICHOST` protects only `getnameinfo`. The lookup is answered
   from `/etc/hosts` only when the host lists `127.0.0.1` there, with
   nsswitch reading `files` first. The scratch `network`-marked session
   runs that call unguarded, and `./scripts/check` runs that session. On a
   host without the entry, the call can send a DNS PTR query, or raise and
   change the scratch session's outcome, which is an I-11 exposure. Either
   correct the comment and add this case to NOT PROVEN, or choose an
   argument that cannot reach a resolver.

## Notes

- **U4, a reading the commit body does not list (DESIGN QUESTION-adjacent;
  not a blocker).** Decision 64 says a matched draw happens "when at least
  `match_min_live` approaches are live ... and each has at least
  `match_window_days` paper rows". `controls.measured_pairs`
  (`src/discotrade/controls.py:224`) reads this as "at least
  `match_min_live` of the live approaches have enough rows", and it takes
  pairs only from those. The other reading is that every live approach
  must qualify. The docstring states the chosen reading, but the commit
  body's "where the design is silent" list does not. The architect may
  want to confirm it.
- **U3: two transitions for one approach on one day.** In step 3
  (`lifecycle.py:206-227`), an approach that returned earlier on `D` can be
  displaced by a later one on the same `D`. It then has two lifecycle rows
  dated `D`, and its dormancy date resets to `D`. This follows decision
  63's "each approach sees the states the earlier ones left". Neither the
  code nor the commit body discusses it, and no test covers it.
- **U4: `cli.py` was changed outside the brief's file list.** The change
  is one line, so that `journal recompute` passes the setup and control
  pairs are recomputed. The U4 body and the report's Deviations section
  both declare it. It is needed by decision 64's "`journal recompute`
  recomputes control subjects". It is a scope deviation, not a design
  violation.
- **U4, untested paths:**
  - A month whose 1st is a non-trading day on every calendar.
    `test_mixed` trades every day, so this case cannot arise there.
  - A state journaled before controls existed. Its control carry would
    fail `_check_carry` in `journal.py`.

  The report covers the second as "No re-run of a state journaled before
  controls existed", and the first only in part ("No first journaled day
  on the 1st of a month").
- **U2:** no test covers a subject whose calendars have no trading day in
  one block (the `if not dates` branch of the population rule). The brief
  did not ask for it. The test's quantile bisects on `erf` for p ≤ 0.5
  and on `erfc` above that, where decision 60 names `math.erf`. That is a
  difference in wording, not in precision.
- **The report's NOT PROVEN section, checked against the sub-agents'
  findings:** it is otherwise complete and honest. Its Deviations section
  states that the U5 gate ran with a 20-minute timeout instead of the
  brief's 30 minutes, and that U4's three check runs were moved to the
  background by the harness. Every unit commit body lists every file it
  touches.
- **hands:** The brief requires `./scripts/gate` to run with a timeout of
  at least 30 minutes. The Bash tool's foreground maximum is 20 minutes,
  so a builder cannot obey the brief literally. In U4, three chained
  `./scripts/check` runs (about 7 minutes each now, up from about 5) went
  past 20 minutes and were moved to the background by the harness. That
  contradicts CLAUDE.md's no-background rule. Both belong to the open
  HF-006. As the suite grows, the briefs need to say "one check per call".
- **hands:** the per-commit review sub-agents ran `./scripts/check` at
  each commit in 5.5 to 8.5 minutes, two at a time on a 4-core host. All
  runs were green.

## Per-commit verdicts

### 060b5e2 (U1)

```
Review of 060b5e2: PASS on all five points, no defects found.

1. Unit: U1 of mission 8 (REVIEW-7 should-fix 1 and 2; decisions 47, 54, 58). It claims I-11 and DESIGN §9.4 and §18.1. Only tests/conftest.py, tests/test_offline.py and tests/test_journal_recompute.py change.
2. Test-first: PASS. Every "seen to fail" claim in the commit body reproduced:
   - With the base conftest.py, 12 of test_offline.py fail (12 failed, 12 passed).
   - With sendmsg unguarded, 4 fail: the three scope tests and the scratch session test.
   - With gethostbyname unguarded, 6 fail.
   - A recompute that starts each day from the stored previous target_next (I made journal.recompute compare against day_rows(state, setup, d)) fails only the new test, at index 6: ('equal','2019-06-11',…) != ('MISMATCH',…). The other 8 pass.
   - Each change was reverted afterwards and the worktree was clean.
3. ./scripts/check at the commit: green. Last lines: 1053 passed, 86 deselected in 332.20s, config check: ok, 168 unverified values, check: green. I ran it twice, not three times.
4. Decision 58: PASS.
   - (a) is covered in a test, a module-scoped and a session-scoped fixture: through both socket and _socket, an addressed AF_INET sendmsg plus the four lookups raise SocketBlocked, and the loopback receiver gets nothing. A spy test shows each lookup, getaddrinfo included, is refused before the real function runs. AF_UNIX sendmsg still works. The network-marked test in the scratch session is left alone (1 failed, 2 passed).
   - (b) is covered on a 5-day journal: both (D1, s) and (D2, s) are reported, exit 1, two journal_mismatch events, journal files unchanged.
   - No pre-existing assertion was removed or weakened in any of the three files; the diffs only add.
   - I-9, I-10, I-11, I-12 and I-14 hold: tests write only under tmp_path/tmp_path_factory, and pyproject.toml/uv.lock are unchanged.
5. Forbidden touches: PASS. No reserved file, meta/plan.md, meta/CHECKPOINT.md, config/ value or src/ file is touched.

Not proven / notes:
- The comment at tests/test_offline.py:110-111 says the lookup arguments "need no resolver". That is not strictly true for gethostbyaddr("127.0.0.1"), which is a reverse lookup. Here it resolves from /etc/hosts (127.0.0.1 localhost, nsswitch files first), so it sends no query. The only unguarded call is in the scratch network-marked test (INNER_TESTS), which ./scripts/check runs; on a host without that hosts entry it could send a DNS query or fail. This is a low-severity comment inaccuracy.
- What the backstop cannot see (SocketType used directly, bindings taken before the session, child processes) was not checked here; decision 58 leaves it to the report's NOT PROVEN.
```

### abba5d3 (U2)

```
abba5d3: PASS on all five points, no defect found.

1. Unit: PASS. This is U2 of mission 8 (step S1.2): the statistics of §11 and the clean flag. It claims DESIGN §8, §9.3, §11.1 to §11.4, decisions 30, 59, 60, 61 (with 53) and I-3. It touches only src/discotrade/stats.py (new), src/discotrade/paper.py, tests/test_stats.py (new) and tests/test_paper.py, which matches the brief.
2. Test-first: PASS. With the parent's paper.py and no stats.py, the two test files go red: 2 collection errors (cannot import name 'stats'). Each wrong change from the brief goes red and matches the commit body: ties ranked by position 3 failed; sd_c with ddof 0 1 failed; N not floored at 2 in E(N) 3 failed; clean when the day is on or after the cutoff 2 failed. Each was reverted.
3. ./scripts/check: PASS. It was run twice: 1087 passed, 86 deselected in 328.12s (0:05:28), then config check: ok, 168 unverified values, then check: green.
4. Design conformance: PASS. Every item in the checklist matches decisions 59 to 61 in stats.py and paper.py. Trading dates use the same rule as daily.is_trading_day, and the Sharpe is metrics.sharpe (decision 30). The tests compute their expected values without stats.py (counted ranks, their own Pearson, statistics.stdev, their own g constant, bisection on erf/erfc) and assert at least what the brief asks. The existing test_paper.py assertions are unchanged; only the build(..., CUTOFFS) argument was added, and the column set changes through paper.COLUMNS. The rebuild-to-same-hash test is still present and passes. On invariants: no W/T read, no market names, no threshold numbers in src (only g and math.e), no clock or network, no state written, and pyproject.toml and uv.lock are unchanged.
5. Forbidden touches: PASS. Only the 4 files above changed; no reserved file, plan, checkpoint or config value was touched.

Not proven:
- No test covers a subject whose calendars have no trading day in one block, so that branch of the population rule is untested (stats.py, if not dates). The brief did not ask for this test.
- The test quantile bisects on erf for p ≤ 0.5 and erfc for p > 0.5; decision 60 names only math.erf. This is a wording difference only, not a defect.
```

### 327c68a (U3)

```
Review of 327c68a (U3) — verdict: pass, with one test-coverage gap and one note. No defects found in the code.

1. Unit: U3, the ledgers and the lifecycle (mission 8, step S1.2). It claims DESIGN §9.1, §10.2, §10.3 and §16.2, decisions 22, 48, 62 and 63, and invariants I-5 and I-6. The commit body lists all 9 files. Pass.
2. Test-first: with the parent's source and ledger.py/lifecycle.py removed, the new tests fail at collection with an ImportError on ledger; restoring the commit gives 58 passed. Each of the brief's four wrong changes, made and reverted one at a time, turned tests red:
   - NaN Sharpe treated as negative in step 2: 1 red.
   - A change taking effect on D (<= on the row date in states): 2 red; with admission <= as well, 3 red.
   - Ledger dedupe removed, so the row is appended again on a re-run: 5 red.
   - journal_day called without failures, so a contract failure fails the day: 1 red.
   Pass.
3. ./scripts/check (one run), last lines verbatim: unverified instruments/SIL.toml cost.slippage_coef = 0.02 (checked 2026-10-11; source: SPEC.md §17) / config check: ok, 168 unverified values / check: green. Pass.
4. Conformance with decisions 62 and 63: pass. Everything in the checklist matches the code, including that admission is not wired into run-day. The existing tests/test_daily.py assertions are unchanged (the only removed lines are the import and the helper's signature). I-9, I-10 and I-12: no venue name, no hard-coded threshold and no clock read in the new src files. No new dependency.
   - Not proven (test gap): nothing shows step 3 counts trading days rather than calendar days. test_mixed includes SYNX on the always_open calendar, so every day is a trading day. I swapped the count at src/discotrade/lifecycle.py:210-212 for (day - s.since).days and all 49 tests in test_lifecycle.py and test_daily.py still passed. The code itself is correct.
   - Note (design silent, not a defect): in step 3 (lifecycle.py:206-227), an approach that returned earlier on the same day can be displaced by a later one, giving two rows for it on D and resetting its dormancy date to D. That matches decision 63's "sees the states the earlier ones left" read literally, but neither the code nor the commit body addresses it.
5. Forbidden touches: none. The diff touches no config, meta, CLAUDE.md-reserved files, existing tests/fixtures/config/ records, pyproject.toml or uv.lock; the only new fixture is tests/fixtures/strategies/breaks_thursday_noon.py. Pass.
```

### 451471e (U4)

```
Review of 451471e (U4, mission 8, the controls)

1. Unit: PASS. The commit claims U4: decisions 23, 25, 39, 49, 54, 64; DESIGN §7, §9.2, §9.3, §9.4, §10.1; I-1, I-5, I-6, I-12. The brief lists §7, §9.2, §9.4, §10.1; the body adds §9.3.
2. Test-first: PASS. With the parent's source files, tests/test_controls.py fails at collection (ImportError). The changed existing tests give 3 red, 48 green: test_journal.py::test_a_day_with_no_subject_writes_an_empty_file_and_its_index_line and, in test_journal_recompute.py, test_all_matches_every_pair_exits_0_and_writes_nothing and test_fewer_pairs_than_the_sample_recomputes_every_pair_before_d. The other edits only filter to approach rows, so they also pass on the parent. Each of the brief's four wrong changes, made alone in src/discotrade/controls.py, turned test_controls.py red:
   - per-bar number keyed by the bar's date instead of its ts: 3 failed;
   - state machine not reset flat at a redraw: 2 failed;
   - July reusing June's seed 201906: 2 failed;
   - short entry allowed on the no-short instrument: 2 failed.
   All restored afterwards (test_controls.py alone: 16 passed).
3. ./scripts/check: PASS (one run, 8m34s). Last lines: config check: ok, 168 unverified values / check: green.
4. Design conformance: PASS.
   - §7 shared: the diff of tests/test_backtest*.py and tests/test_executor*.py is empty. The executor cache is keyed by fill bar, and fee, spread and slip depend only on that bar, so no value changes. The ts dtype unit is preserved.
   - Draws: seed year*100+month; per slot one integers or one uniform(ln lo, ln hi) call, q = 1/H. The hash key <seed>|<slot number>|<symbol>|<Timestamp.value ns>|<purpose> is right (DESIGN §10.1 writes rc:<slot>, so <slot> is the number). The state resets flat when the draw in force (by the bar's trading date) changes; the carried state is the last row's target_next.
   - Draw day: found from the union of trading dates from the 1st to the day before, so a month whose 1st is not a trading day works.
   - Matched pairs: "live at start of day" uses lifecycle rows dated before the day; paper days are counted strictly before the day; the threshold is trade > 1e-9; NaN-H pairs are dropped.
   - pools.jsonl: staged with the day (the staging commit copies every file under it), never appended twice.
   - Recompute: uses only pools.jsonl and the stored bars, from the journal's first day.
   - Paper: control_bh N=1 matches decision 23 (N = the subject's instruments).
   - Changed tests: every changed existing assertion is named in the body and justified by decision 64.
   - cli.py (one line, outside the file list): declared, and needed for the gate's recompute --all of control pairs. A minor scope deviation, not a design violation.
   - Invariants: no hard-coded threshold in src (0.5 and 2**64 come from decision 64), no new dependency, no clock read.
5. Forbidden touches: PASS. Only the 11 listed files changed. No reserved file, meta/plan.md, meta/CHECKPOINT.md, config value or tests/fixtures/config record was touched.

NOT proven / readings (no defect found):
- Matched-branch reading: in controls.py:224, the matched branch counts the live approaches that have ≥window paper rows (a subset). Decision 64's "each has" could also mean every live approach must qualify. This reading is in the docstring but not in the body's "simplest choice" list.
- Untested: a month whose 1st is a non-trading day for every calendar (the test track trades on weekends), and a state that had journal days before U4 (its controls would fail the carry check in _check_carry, journal.py ~l.335).
```
