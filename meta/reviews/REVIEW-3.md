# REVIEW-3 — cold review of mission 3 (roadmap step S0.3)

Base: 6e88bbb (`review: mission 2`, the last `review:` commit). Range
`6e88bbb..origin/main` (tip f2e45f1). Unit commits reviewed, one sub-agent
each in its own worktree: a966344 (U1), 542c171 (U2), 833aa25 (U3), ec1c8a4
(U3 follow-up), 3c24e5f (U4), 8cfd390 (U5), efb2b93 (U6). Read myself for
forbidden edits only: ef2e9f1 (the architect's kit: `KIT.md`,
`meta/BUILDER-3-PROMPT.md`, `meta/decisions/decisions-2026-10-12.md`,
`meta/ROADMAP.md`, `meta/BACKLOG.md`, not a builder commit), 02b366c
(`plan:`), the six `meta:` checkpoint commits and f2e45f1, and a3cd937
(`report:`, `meta/FINAL-REPORT-3.md` and HF-006 in
`meta/findings/FINDINGS.md`). No builder commit touches a file `CLAUDE.md`
reserves; `meta/plan.md` and `meta/CHECKPOINT.md` change only in the
orchestrator's `plan:` and `meta:` commits. `git diff 6e88bbb origin/main --
config/ tests/fixtures/config_frozen.json` is empty. `tests/gates/` does not
exist.

## Gate

not a closing mission

(For the record, at the tip: `./scripts/gate M0` printed `G0.1 FAIL no gate
test (tests/gates/test_g0_1_*.py)` and the same for G0.2, G0.3, G0.4, then
`gate M0: FAIL`; `./scripts/gate M0 G0.3` ended `gate M0 G0.3: FAIL` with no
`gate M0:` line. Both are what the brief's acceptance expects.)

## Blockers

1. **`metrics.sharpe` returns a huge finite Sharpe for a series whose
   deviation is zero** (8cfd390, `src/discotrade/metrics.py:116-119`). DESIGN
   §8: Sharpe is "not a number when there are fewer than 2 days or the
   deviation is 0", and such a value is "never above anything". The code
   tests `not sd > 0` on the floating-point `np.std(x, ddof=1)`, which for a
   constant non-zero series is a rounding residue, not 0. Reproduced at the
   tip: `sharpe([0.1]*3) = 9.34e16`, `sharpe([0.03]*10) = 6.51e16`;
   `sharpe([0.01]*3)` is NaN only because that value happens to round to an
   exact 0, and that is the one case `tests/test_metrics.py` uses. A
   constant series therefore yields a Sharpe that is positive and above
   every threshold, the opposite of §8's rule, and the brief's item ("not a
   number ... with zero deviation") is tested on a lucky input only. The
   report's claim "Sharpe NaN with 0 or 1 day and zero deviation" overreaches
   what the code does. Fix: treat a series whose values are all equal (or
   whose deviation is not above a relative tolerance of its mean's scale)
   as zero deviation, and test it on several constants including 0.1.

## Should-fix

1. **The `trades` test cannot tell a correct implementation from a wrong
   one, and the claim about it is worded wrongly** (8cfd390,
   `tests/test_metrics.py:230-235`). Both rolled rows in the test have
   `trade = 0`; a sub-agent changed `trades()` to drop every rolled row and
   all 34 metric tests still passed. The code is right (it counts rows with
   `trade > 1e-9`; roll turnover never enters `trade`, so a bar with a real
   trade and a roll is counted, as DESIGN §8 and decision 25 require), but
   the commit body ("trades skips roll rows") and FINAL-REPORT-3 ("roll rows
   ... not counted") describe the wrong behaviour. Add a rolled row with a
   real trade that must count, and say "roll trades", not "roll rows".
2. **`backtest` exit 1 paths of decision 27 have no test** (efb2b93,
   `tests/test_cli_backtest.py`). A missing roll record and a strategy that
   breaks its contract (decision 22), and a loader refusal, all exit 1 when
   run by hand, but only the refused bar file is tested. The brief's gate
   text names only the bar file, and FINAL-REPORT-3 lists this under NOT
   PROVEN, so it is disclosed; decision 27 still names each case.
3. **`BarStore.last_ts()` skips decision 18's refusal** (a966344,
   `src/discotrade/bars/store.py:149-151`). Decision 18 covers "any other
   reader entry point"; `last_ts` returns the indexed last `ts` even when an
   unlisted interrupted month holds later bars. Its only callers today run
   after `recover()` (`cli.py`) or inside the store, so nothing is wrong
   now; a later caller would silently miss the refusal. Either route it
   through the same check or document it as index-only, not a bar read.
4. **The indicators module docstring is false for `ema`** (542c171,
   `src/discotrade/indicators.py:7`). It says "A row with too little
   history for the window is NaN"; `ema` (`ewm(span=window, adjust=False)`,
   no `min_periods`) returns a value from row 0. The commit body discloses
   the seeding; the module text that describes every function does not.
   DESIGN §13.4 builds the workers' function list from this module, so its
   text should be true.

## Notes

- U1 changed one assertion in `tests/test_synth.py` (the default day of
  `bars fetch`, 2019-03-31 to 2019-03-29), outside its file list and against
  the brief's "every existing test unchanged in what it asserts". Decision
  19 forces the new value and the commit body and report disclose it; not a
  defect.
- U4 widened the context read in `backtest.py` to `max(cap, 26)` trusted
  bars, beyond the brief's literal "only the call that turns positions into
  orders". Decision 24 (`sigma` uses bars before the window) requires it;
  the strategy's slice stays capped. A side effect: a contract change with
  no roll record inside that extra context now stops the evaluation.
- 833aa25 admitted context bars before `trusted_from` (DESIGN §4.2); the
  orchestrator sent it back and ec1c8a4 fixes it, with a test that fails on
  the parent. Not checked: whether `rolls.py`'s `last_n` while measuring a
  roll gap, or `adjusted_as_of`'s default start, can read bars before
  `trusted_from`.
- `backtest` plain output: the `costs at 1x` line shows subject totals
  (divided by N) while the per-instrument lines show undivided sums, and
  neither is labelled. The I-4 plain-output test is weak in that nothing
  printed contains the word "gross".
- The socket backstop is a function-scoped autouse fixture: module-scoped
  fixtures (`test_gaps.py`, `test_rolls.py`) and subprocesses launched by
  tests run outside it, and `_socket` used directly passes. None of them
  touches the network today. FINAL-REPORT-3's NOT PROVEN mentions C
  extensions and Unix sockets but not the fixture scope.
- Small test nits: `tests/test_backtest.py:186` asserts a literal weekday
  close to a tautology (the main loop covers the item);
  `tests/test_backtest.py:372`'s comment mislabels one of two instruments.
  `MissingRollError` is tested for a `ts` mismatch only, not for a record
  with the right `ts` and the wrong contracts.
- FINAL-REPORT-3 §NOT PROVEN against the sub-agents: everything they could
  not prove is listed there (no independent calculation, gate M0 failing,
  property-test coverage limited to drawn inputs, untested `backtest` exit
  1 paths, `test_reference.py` not seen to fail first, cost values
  unmeasured, reference results meaningless), except blocker 1 and the
  backstop's fixture scope above. Its acceptance checks cite `git diff
  ef2e9f1`; from this review's base 6e88bbb the config diff is also empty.
- hands: HF-006 (long foreground `./scripts/check` moved to the background
  by the harness) is filed and open. Each sub-agent of this review ran
  `./scripts/check` in the foreground with an explicit 20-minute timeout;
  none reported being moved, with seven sub-agents running in parallel.
- hands: the brief's U1 gate ("every existing test unchanged in what it
  asserts") could not be met together with decision 19, which the same
  brief cites; a brief should exempt the assertions a decision changes.

## Per-commit verdicts

**a966344 (U1)**

SHA a966344: verdict **pass**. No blockers and one minor should-fix. I verified every point in a throwaway worktree, which I have since removed; the main repo is clean.

1. **Unit:** U1 "Reader, `bars fetch` default day and socket backstop". It claims DESIGN §5.2, §5.4 and §16.1, decisions 3, 5, 18, 19 and 20, and invariants I-5, I-6, I-11 and I-12. That matches the brief.
2. **Test-first: pass.**
   - With `store.py` and `cli.py` reverted to the parent, 15 tests fail: the 8 parametrized reader-refusal tests, the reader-repairs-nothing test, 3 of the 4 default-day cases, the replay test, the fetch-completes-interrupted-append test, and `test_synth`'s default-day assertion. The fourth default-day case passes on the old code too, because there --as-of minus one equals D.
   - With only `tests/conftest.py` reverted, all 3 backstop tests fail (the subprocess run then shows "4 passed"). After restoring, `git status` was clean.
3. **`./scripts/check`: green.** It ends with "config check: ok, 168 unverified values" and then "check: green".
4. **Design conformance: pass.**
   - **Reader refusal:** `read_range` and `last_n` both go through `_months`. The refusal holds whatever the range, the errors name interrupted append or revised data point, and the reader repairs nothing.
   - **Callers:** `gaps._span`/`_window`, `rolls.update_rolls` and `adjusted_as_of` all read through `read_range`, so they inherit the refusal.
   - **Default day:** `bars fetch` uses `_closed_day`, the same function `bars gaps` uses, as decision 19 requires.
   - **Backstop:** it is autouse and function-scoped. It blocks `connect`, `connect_ex` and `sendto` on every family except AF_UNIX, plus `getaddrinfo`. `get_closest_marker` exempts `network` and `live` at function, class or module level. The subprocess pytest run proves the unmarked test fails while the `network`, `live` and Unix-socket tests pass.
   - Every gate item has a test. The commit body's claims match the tests. I-9, I-10, I-12 and I-14 are not touched, and there is no new dependency.
5. **Forbidden edits: pass.** Only `src/` and `tests/` files changed, and nothing under `config/`, `meta/` or `tests/gates/`.

**The `test_synth.py` change is justified by decision 19.** The test is the same: the default day `bars fetch` prints. Only its expected value moves, from 2019-03-31 (a Sunday, --as-of minus one) to 2019-03-29 (§16.1's D). The literal "unchanged in what it asserts" is broken, but the brief's own decision 19 forces this, and the commit body and final report disclose it. I would not call it a defect.

**SHOULD-FIX (minor):** `src/discotrade/bars/store.py:149`. `BarStore.last_ts()` is a public reader entry point that skips the `_months` refusal. Decision 18 says "any other reader entry point", and `last_ts()` returns the indexed last `ts` even when an unlisted interrupted file holds later bars. Today its only callers are `cli.py:306`, which runs after `recover()`, and `_read_month`, so nothing is affected now.

**NOT PROVEN:**
- Module-scoped fixtures (in `test_gaps.py` and `test_rolls.py`) and subprocesses that tests launch run outside the function-scoped backstop. None of them touches the network today, but the backstop would not stop them if one did.
- The backstop does not cover sockets made directly through `_socket`.

**542c171 (U2)**

SHA 542c171: PASS, with no blockers and one should-fix.
1. **Unit:** mission 3 U2 ("Strategy contract, loader and indicator library"). It claims DESIGN §6.1, §6.2 (the result check), §6.3, decisions 21 and 22, and I-1, I-2, I-10. That matches the brief.
2. **Test-first: OK.** With `strategy.py` and `indicators.py` removed, both new test files fail at collection (ModuleNotFoundError). Restored, and `git status` was clean. As an extra check I added a `peek` function that reads the next row. Without any test edit, the property test failed on it, so a function added later really is covered.
3. **`./scripts/check`: green.** Last lines: "config check: ok, 168 unverified values" / "check: green".
4. **Conformance: OK.** Every gate item has a test that asserts at least what the item says.
   - **Property test:** it finds functions with `inspect.getmembers` (public, defined in that module). `arguments()` fails loudly on a parameter it cannot build. It compares row i of the full input against the input cut at i, so NaN counts as equal.
   - **Hand values:** they are literals or plain arithmetic, plus a `sample_std` helper inside the test. None comes from the function under test.
   - **Limits:** all four are read through `Limits.from_thresholds` (`validation.*`), with nothing hard-coded. A copied thresholds file with `max_lines` raised or lowered flips the result, and raising each of the other three limits does too.
   - **`check_result`:** I probed it directly. It refuses bool, `np.bool_`, NaN, ±inf (also as float32), strings, Decimal and arrays. It accepts `np.float64`, `np.int64` and float32, and clips only when shorting is false.
   - **Docstrings:** the test requires a non-empty first line ending in "." and a blank or missing second line.
   - **Invariants:** no network, no secret, no wall clock, no market names in `src/`, no new dependency.
5. **Forbidden edits: none.** The commit adds only the two `src` files, two test files and the strategy fixtures. No config or `tests/gates/` change.

**SHOULD-FIX:** `src/discotrade/indicators.py:7` (module docstring) says "A row with too little history for the window is NaN", but `ema` (line 37, `ewm(span=window, adjust=False)` with no `min_periods`) returns a value from row 0. The commit body discloses the seeding, but the docstring is false for `ema`. Either the docstring or `ema` should change.

**Not proven:** no-lookahead holds only for the cases tried (60 derandomized examples per function, one row i each, as the commit body says), not for every input. Getting a 0-d numpy array refused is a choice; DESIGN does not decide it.

**833aa25 (U3)**

sha 833aa25: U3 Evaluation loop and returns. Verdict: pass (no blocker), with 1 SHOULD-FIX (already fixed by ec1c8a4) and 1 nit.
1. Unit and sections: the commit claims U3 and DESIGN §6.2, §7.1, §7.2, §5.6, decisions 22–24, R-20, I-2, I-12. It changes only `src/discotrade/backtest.py` (new) and `tests/test_backtest.py` (new). OK.
2. Test-first: with `backtest.py` deleted the test file fails at collection (ModuleNotFoundError). Restoring it left `git status` clean. I also tried two mutations. Dropping the gap from Ca(u-1) failed 3 tests, including the hand-value and 1e-12 tests. Dropping the slice adjustment failed 2 tests, the as-of-last-row and hand-slice checks. OK.
3. `./scripts/check` at 833aa25 ended with "config check: ok, 168 unverified values / check: green". On its own the file ran 16 passed in 106 s.
4. Conformance: OK. gross matches §7.2. `backtest.py:203` uses Ca(u-1) = raw previous close plus the gap of a roll at u, the denominator is raw Or(u), and u-1 is the previous stored bar. The slice offset (`:184-185`) is adjusted as of its last row, the same as `rolls.adjust`. Hour and weekday use the calendar's tz (UTC when always open, and the always_open calendar has no tz). Each call builds fresh arrays. h(u0)=0 and gross(u0)=0. MissingRollError checks ts, old and new. I checked the hand values by hand: 0, 1/101, 1/102, -1.5/112, 0.5/110. The 1e-12 test compares against the SynthSource underlying fetched with roll_schedule="none", which is independent of the backtest. It covers all 8 rolls, with h(u-1)≠0 there for both strategies. Truncation invariance compares `fetch --as-of t` with a store ending 2021-01-07 (≥365 days later) on all of track.instruments (SYNA, SYNL, SYNX), at 3 values of t, using exact frame equality on p, h and gross. No network, secret, wall clock, venue name, config number or in-repo state.
5. Forbidden edits: none.
SHOULD-FIX (this commit's state, fixed later by ec1c8a4): context bars could come from before `trusted_from`. At `backtest.py:166-167`, `store.last_n` has no trusted_from cut, so pre-trusted bars entered slices and `Evaluation.bars`, which the cost model reads for sigma. The commit body states this choice, and `tests/test_backtest.py:349-357` asserts it (frames[0] has 3 rows, including 2020-01-05 bars before trusted_from 2020-01-06). That conflicts with DESIGN 4.2, "history before this date is never used".
Nit: `tests/test_backtest.py:186` has a "hand point" assertion that is close to a tautology. The weekday is the literal 4, and the EDT side of the point is never asserted. The test's main loop already covers the requirement.
NOT proven: MissingRollError on a record with a matching ts but a wrong old/new contract (only a ts mismatch is tested).

**ec1c8a4 (U3 follow-up)**

ec1c8a4: **verdict ACCEPT**. Steps 1–5 pass; I found no BLOCKER and no SHOULD-FIX.

1. **Unit:** a mission 3 follow-up to U3 (evaluation loop). The context bars that `last_n` reads are now cut to `ts >= midnight UTC of trusted_from`. It cites DESIGN §4.2 ("history before this date is never used"), decision 23, and DESIGN §6.2 and §7.1.
2. **Test-first: pass.** With `src/discotrade/backtest.py` put back to its parent version, `test_no_bar_before_trusted_from_is_window_or_context` fails at `tests/test_backtest.py:359` (`ev.first == 2`, not 0); the other 15 tests pass. After restoring, `git status` is clean.
3. **`./scripts/check`: green.** Last lines: `config check: ok, 168 unverified values` / `check: green`.
4. **Design conformance: pass.**
   - **The cut:** `backtest.py:169` uses the same `_midnight(instrument.trusted_from)` with `>=` as window membership (`backtest.py:111` and `:118`), which matches decision 23's "ts not before trusted_from". A bar at exactly 00:00 UTC on `trusted_from` is kept, and the test checks that.
   - **Slicing:** the window's first bar `u0` always survives the filter, so `context.iloc[:-1]` and `first = len(context) - 1` stay correct.
   - **Invariants:** no network, secret, wall clock, venue name, threshold or new dependency.
   - **Commit body:** each claim (slices 1–5 rows; with a cap of 3, 1,2,3,3,3; the two bars come back when `trusted_from` is a day earlier) matches an assertion in the test.
5. **Forbidden edits: pass.** The commit touches only `src/discotrade/backtest.py` and `tests/test_backtest.py`.

**The replaced test:** the old one checked two things. "Window bars start at `trusted_from`" is still required and is kept (`rows["ts"].iloc[0] == trusted`). "Bars before `trusted_from` are context" (`len(frames[0]) == 3`) contradicts DESIGN §4.2, so dropping it is right. `test_gross_equals_hand_values…` still covers context bars that are after `trusted_from` (default SYNX `trusted_from` is 2019-01-07).

**Nit:** the comment at `tests/test_backtest.py:372` says "starts the day after `trusted_from`", but it labels both cases. The `later` instrument (`trusted_from` = window start) gives 1 row, `late` (`trusted_from` a day earlier) gives 3. `later` is a redundant copy of `inst`. Cosmetic only.

**NOT proven:** `rolls.py:155` (`last_n` while measuring roll gaps) and `adjusted_as_of` (which defaults to the first stored bar) can still read bars from before `trusted_from`. That code isn't part of this unit, and I didn't check whether it is reachable.

The worktree `/tmp/rv3/wt-ec1c8a4` has been removed.

**3c24e5f (U4)**

sha 3c24e5f — verdict: PASS. I found no BLOCKER and no SHOULD-FIX.

1. **Unit:** mission 3 U4, Cost model and executor. It claims DESIGN §7.3, §7.4 and the spread rule of §5.7, with decisions 24, 25, 26, R-3, R-5, I-4 and I-15.
2. **Test-first: PASS.** With `backtest.py` put back to the parent version and `costs.py`/`executor.py` deleted, both new test files fail to collect (ImportError). Putting back only the wiring in `backtest.py` gives 5 failed, 5 passed in `test_executor.py` (KeyError 'trade'). After restoring, `git status` was clean.
3. **`./scripts/check`: green.** Last lines: "config check: ok, 168 unverified values" / "check: green".
4. **Design conformance: PASS.** Each formula in `costs.py` matches §7.3:
   - **fee:** `fee_bps/10000`, otherwise `fee_per_side/(multiplier*Or)`.
   - **half_spread:** `max(t/2, 0.5)*tick/Or`. The spread ticks come from the existing `spreads.spread_ticks`: the table by exchange-local hour, otherwise main/off by the main session.
   - **sigma:** `r(s) = (C(s) - (C(s-1) + gap(s))) / C(s-1)`, ddof=1, over `r[max(1, u-24):u]`, and 0 for u < 3.
   - **roll and net:** `roll = 2|h(u-1)|·c(u)`, and it is 0 at u0 because `before[0] = 0`. Cost and net match too.
   - **config hash:** follows decision 26 (keys sorted, `separators=(",",":")`, companions excluded, multiplier only when present, 24 values or null).
   - **Constants from config (I-10):** `slippage_coef`, the fees, the spread ticks and `tick_size` are read from config.
   - **Constants in code:** `SIGMA_RETURNS = 24` and `HALF_TICK = 0.5` are written in code. They are fixed constants of the §7.3 formula, which the version string c1 covers, and are not SPEC thresholds.
   - **Gate and claims:** every gate item has a test asserting at least what the item says, including the AST scan with a planted-executor check. The commit body's claims match the tests. No market or venue name under `src/`, no clock, network or secret use, and no new dependency.
5. **Forbidden edits: PASS.** The commit touches only `backtest.py`, `costs.py`, `executor.py` and the two new test files.

**Scope note on `backtest.py`:** besides the order/fill wiring, the commit changes the context read to `max(cap, SIGMA_RETURNS + 2)`. That goes past the brief's literal allowance, but decision 24 requires it (sigma uses stored bars before the window). The strategy's slice is still capped (`j0 = max(0, k-cap+1)`), and real tracks set `history_cap_bars` to 1500 or 480, so nothing changes in practice. One small side effect: a contract change inside that extra context with no roll record now stops with decision 24's error. I judge the change acceptable.

**NOT PROVEN:** that any cost value is realistic (the commit says so itself). I did not separately test that reverting only the context-read change makes `test_sigma_reaches_context_beyond_a_small_history_cap` fail.

The worktree `/tmp/rv3/wt-3c24e5f` is removed. I left the other reviewers' worktrees in place.

**8cfd390 (U5)**

Review of 8cfd390 (U5 Metrics): **pass, with 2 should-fix items and no blockers.** The worktree is removed and nothing in the repo was edited.

1. **Unit and sections:** this is mission 3 U5 Metrics. The commit claims DESIGN §8, decisions 23 and 25, R-7 and I-4. Pass.
2. **Test-first:** pass. With `metrics.py` deleted and `backtest.py` put back to its parent version, `tests/test_metrics.py` goes red (ImportError at collection). After restoring, `git status` is clean.
3. **`./scripts/check`:** green. Last lines: "config check: ok, 168 unverified values" / "check: green".
4. **Design conformance:** pass apart from the two items below.
   - The daily series follows decision 23 exactly: sorted union of dates, each instrument's bars summed per day, divided by N, and an instrument with no window bar still counts in N.
   - Sharpe uses ddof=1 and 252, and is NaN with fewer than 2 days.
   - NaN is never true in `positive`, `negative`, `above` or `fragile`.
   - `max_drawdown` is correct, and counts the start (0) as a peak.
   - `avg_holding_bars` runs are correct.
   - `breakeven_cost` = sum gross / (sum trade + 2|h(u-1)| at each roll) × 10000. Here h(u-1) matches the backtest's own previous position, and is 0 at an instrument's first window bar.
   - On "roll rows": the code does not exclude rows that have a roll. It counts every row with `trade > 1e-9`, and since a roll's turnover never goes into the `trade` column, roll trades are left out. A row with a real trade and a roll is therefore counted, which is correct. The commit body's wording "trades skips roll rows" overstates this.
   - The only gross figure, `breakeven_cost`, is private and is returned only inside `Metrics`, beside the net figures at 1x and 2x (I-4).
   - The `backtest.py` change is only `daily()` plus its imports.
   - I-10: 1e-9 and 252 come from DESIGN §8 and R-7, not from SPEC §2/5/8/9/13, so module constants are acceptable.
   - No network, secret, wall clock, venue name or new dependency.
5. **Forbidden edits:** pass. The commit touches only `src/discotrade/metrics.py`, `src/discotrade/backtest.py` and `tests/test_metrics.py`.

**SHOULD-FIX 1:** `src/discotrade/metrics.py` `sharpe` uses the test `not sd > 0`. A constant non-zero daily series has a mathematical deviation of 0, but floating-point error leaves a tiny positive value. For example, `[0.1]*3` gives Sharpe 9.3e16 instead of NaN; I also confirmed this for 0.01, 0.03, 1/3 and 0.07 over 10 days. DESIGN §8 says NaN at zero deviation, and a value like this would beat every Sharpe comparison. The test only passes because `[0.01]*3` happens to give exactly 0.

**SHOULD-FIX 2:** `tests/test_metrics.py::test_trades_counts_rows_above_the_floor_and_not_roll_trades` cannot tell the right behaviour from a wrong one, because both rolled rows have `trade=0`. I changed `trades()` to drop rolled rows and all 34 tests still passed. The test needs a rolled row with a real trade that must be counted, and a non-zero roll that must not be.

**NOT PROVEN:** anything about real `evaluate()` output feeding `compute`. Every test uses hand-made frames, except `backtest.daily`, which runs on hand-made Evaluations.

(Reviewer's classification: SHOULD-FIX 1 above is raised to Blocker 1 in this review, as a design violation of DESIGN §8 confirmed at the tip.)

**efb2b93 (U6)**

I found no blockers in efb2b93 (U6). Points 1–5 pass, with one should-fix: three exit-1 paths from decision 27 have no test.

1. **Unit:** U6, reference strategies and the `backtest` command. The commit body claims DESIGN §3, §6.1, §18.3 G0.1's strategy list and §8, decisions 21, 22, 24 and 27, and I-4 and I-9. Its file list matches the diff (3 files under `reference/`, `src/discotrade/cli.py`, 2 test files).
2. **Test-first: PASS.** With the product files reverted, the two test files gave 16 failed, 12 errors and 1 passed. The one that passed is `test_window_holds_at_least_sixty_trading_days`, which does not depend on the product. All of `test_reference.py` was red, but only because the reference files did not exist. After restoring, `git status` was clean.
3. **`./scripts/check`: PASS.** The last lines were `config check: ok, 168 unverified values` and `check: green`.
4. **Conformance: PASS.**
   - `--json` carries every §8 metric, `sharpe_2x`, `total_return_2x`, the four cost totals, `c1`, and the decision 26 config hash checked against `costs.config_hash`. Any non-finite value becomes `null`, tested through a one-day window, and the output uses `allow_nan=False`.
   - Exit 2 for a file outside `reference/` (also via `..`) and for `--from` after `--to`, both tested. Exit 1 for a refused bar file, tested.
   - The plain output prints no gross total; `breakeven_cost` sits on the line with `net_1x` and `net_2x`, as do the Sharpe line and each per-instrument line (I-4).
   - The three strategies match their docstrings. `zscore` uses the sample standard deviation (`ddof=1`), and the hour rule states its "next bar is one hour later" assumption.
   - No market symbol or venue appears in `src/` (I-9). No new dependency.
   - Cost totals as "sum per instrument divided by N" is a defensible simplest choice: it follows decision 23's daily-net definition, so `total_return` equals summed gross over N minus the four totals, and a test proves that identity.
5. **Forbidden edits: PASS.** Nothing under DESIGN, SPEC, meta, config, `.claude`, templates or `tests/gates` was touched.

**What I ran by hand (not in the tests):** a missing roll record gives exit 1, a strategy returning 2.0 gives exit 1, a loader refusal (`StrategyError`) gives exit 1, a missing `--state` gives exit 1, and a nonexistent file under `reference/` gives exit 2.
- Decision 27 says nothing about a missing `--state` or a loader refusal; exit 1 matches how `bars fetch` and `bars gaps` treat a missing state.
- The commit body names the missing `--state`, nonexistent-file and loader-refusal choices; it does not cite decision 21 for the nonexistent-file exit 2.

**SHOULD-FIX:**
- `tests/test_cli_backtest.py` has no test for decision 27's exit 1 on a missing roll record or a contract-breaking strategy, and none for a loader refusal. The behaviour is correct by hand, but no test proves it. The brief's gate text names only the refused bar file, so this is a gap against decision 27, not against the gate.
- `cli.py` `_print_backtest`: the "costs at 1x" line shows subject totals (divided by N), while the per-instrument lines show the undivided sums. Neither is labelled, so a reader can misread the line.

**NOT PROVEN:** whether the metrics and cost values are correct, since no independent calculation exists yet (that is mission 4). The plain-output I-4 test is weak because nothing printed contains the word "gross".

The worktree is removed. The temporary files I created in it (two strategies under `reference/` and a state directory) were deleted first.
