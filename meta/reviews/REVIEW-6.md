# REVIEW-6 — cold review of mission 6 (S0.4 repaired, closes M0)

Base 2c61e49 (`review: mission 5`, the last `review:` commit), tip
e239dee (`origin/main`). Range, `git log --oneline 2c61e49..origin/main`:

```
e239dee report: mission 6 final report
dafd091 meta: mission 6 U5 gate run, gate M0 PASS at 65718c5
65718c5 meta: mission 6 U4 done, checkpoint to U5 gate run
b268252 tests: test_gate_script.py runs one-item gate on G0.4, timeout 1200 s
d948c89 meta: mission 6 U3 done, checkpoint to U4
9e16050 gates: G0.1 compares a roll probe whose position changes at the SYNA roll
230b4a1 meta: mission 6 U2 done, checkpoint to U3
9ca8575 gates: G0.1 calc self-test holds a position that changes at the roll
81f2ae6 meta: mission 6 U1 done, checkpoint to U2
c1a2100 gates: G0.1 compares every key of backtest --json
cdc031f plan: mission 6 plan (S0.4 repaired, closes M0)
19196da plan: mission 6 kit (S0.4, REVIEW-5 blocker, roll timing, M0 gate again)
```

There are four unit commits: c1a2100, 9ca8575, 9e16050 and b268252. Each
was reviewed by its own foreground sub-agent in a worktree at that commit.
I read the `plan:`, `meta:` and `report:` commits myself, looking only for
forbidden edits:

- 19196da is the architect's kit (KIT.md, BACKLOG, ROADMAP, the decisions
  file, the builder prompt). It is exempted as in REVIEW-4 and REVIEW-5.
- cdc031f touches CHECKPOINT, FINDINGS (exactly the three status lines the
  brief gives), journal and plan.
- 81f2ae6, 230b4a1, d948c89, 65718c5, dafd091 and e239dee touch only
  CHECKPOINT, journal, plan and FINAL-REPORT-6.
- No unit commit touches `meta/plan.md` or `meta/CHECKPOINT.md`.
- `git diff 2c61e49 origin/main -- config/ tests/fixtures/config_frozen.json tests/fixtures/config/`
  is empty.
- `git diff --stat 2c61e49 origin/main` over `src/`,
  `tests/gates/independent_calc.py`, the G0.2, G0.3 and G0.4 gate tests,
  `scripts/`, `pyproject.toml` and `uv.lock` is empty. No product code,
  calculation code, script or dependency changed.

## Gate

Gate M0: PASS

This session ran `./scripts/gate M0` at e239dee
(`e239deea0d7811f5bcd6bf9f26a141db39a5b7d8`, equal to `origin/main`,
clean tree), in the foreground with a 30-minute timeout. It exited 0 in
5m53.75s of wall time. Its output, verbatim:

```
G0.1 PASS 62 passed in 65.12s (0:01:05)
G0.2 PASS 7 passed in 118.35s (0:01:58)
G0.3 PASS 13 passed in 167.65s (0:02:47)
G0.4 PASS 4 passed in 0.25s
gate M0: PASS
```

Every item finished well under 15 minutes.

Each item of DESIGN §18.3 M0, read against its tests:

- **G0.1** (`test_g0_1_calc_self.py`, `test_g0_1_reference.py`): covered.
  - Everything REVIEW-5 recorded still holds. The three reference
    strategies run on `test_mixed`, whose window holds a SYNA roll, a
    clipped SYNL short, SYNX's proportional fee and dropped bars. Every
    per-bar field, both daily series, every §8 metric and the cost totals
    by component are compared to 1e-12 under decision 39. An `ast` test
    checks the calculation's imports.
  - Mission 6 adds a fourth subject, `roll_probe.py`, compared through the
    module API (decision 43 (c)). The calculation's self-test gains two
    hand cases in which the position changes at a roll (decision 43 (a)).
  - `backtest --json` is now compared key by key, and the key sets are
    asserted exact (decision 42, REVIEW-5 blocker 1).
  - Seen to fail by this review's sub-agents:
    - REVIEW-5's three `cli.py` changes, plus `position_min` taken from `h`
      only and an added key (4/4/4/1/4 failures).
    - Four changes the builder did not try: `days` off by one, a changed
      `config_hash`, `cost_model` set to `c2`, and wrongly divided cost
      totals (4 failures each).
    - The calculation's roll cost and rolled turnover on `h(u)` (2 failures
      each).
    - discotrade's roll cost on `order.target` (5 unit-test failures, 4 G0.1
      failures).
    - discotrade's rolled turnover on `h` (2 unit-test failures, 1 G0.1
      failure).
  - The calculation's independence still rests on the author's statement,
    as §18.3 allows.
  - The half-tick floor stays unseen by G0.1 (decision 43). It is pinned
    on each side by unit tests.
- **G0.2** (`test_g0_2_cheating.py`): unchanged since REVIEW-5, which read
  it as covered. It passes at the tip.
- **G0.3** (`test_g0_3_store.py`): unchanged since REVIEW-5, which read it
  as covered at full strength. It passes at the tip.
- **G0.4** (`test_g0_4_config.py`): unchanged since REVIEW-5, which read it
  as covered. It passes at the tip.

No gate test passes because of a special case in product code: `src/` is
unchanged in this mission.

By DESIGN §18.2, milestone M0 is met if this review records no blocker.
It records none.

## Blockers

None.

## Should-fix

1. **FINAL-REPORT-6 describes the probe test as asserting more than it
   does.**
   - Under G0.1 the report says "a test asserts that at the SYNA roll bar
     2019-06-14T00:00Z of the window `h(u-1) = 1.0` and `h(u) = -0.5` in
     both discotrade's and the calculation's rows."
   - The test is `test_probe_changes_position_at_the_syna_roll`
     (`tests/gates/test_g0_1_reference.py:292-308`). It pins neither the bar
     nor those values. At every SYNA roll bar of the window it asserts that
     a roll exists and that, in both sets of rows, `h(u-1) != h(u)`,
     `h(u-1) != 0`, `|h(u-1)| != |h(u)|`, and roll and trade are positive.
   - I printed the values at the tip: one roll bar, 2019-06-14 00:00Z,
     with `h(u-1) = 1.0` and `h(u) = -0.5` in both sets of rows. The stated
     facts are therefore true, and decision 43 (c) requires only
     `h(u-1) != h(u)`, which is asserted.
   - I record this as should-fix rather than blocker because nothing the
     brief or the decisions require is missing. Only the report's
     description of the assertion is loose.
   - Fix: in the next report, say the values were observed rather than
     asserted, or add the two equalities and the bar to the test.

## Notes

- The NOT PROVEN section of FINAL-REPORT-6, checked against the
  sub-agents' findings:
  - It lists what they found: the half-tick floor outside G0.1, the probe
    on one roll bar, the U2 independence statement, the definition of
    `position_min`/`position_max`, the 120 s scratch timeouts in U4, and
    D-006 deferred.
  - Every count the report gives was reproduced, as were the absence of
    product changes, the empty frozen-config diff and the review-items
    table.
  - The report's §Correction of FINAL-REPORT-5 matches REVIEW-5 blocker 1
    and what U1 now holds.
- U1 (c1a2100): the test writes the trade threshold `1e-9` as a literal
  instead of reading it from product code or config. This is a test
  constant, not a threshold that an alert, score or gate decides on, so
  I-10 is not broken. If that floor ever moves, this test has to change
  with it.
- U2 (9ca8575): the U2 reviewer checked the hand values by hand against
  DESIGN, not only against the calculation (TE turnover 5 against 4 with
  the mistake; TF 1 against 2). The UTC-date grouping of the always-open
  calendar in those cases was not read against §5.3.
- U3 (9e16050): the 13 lines removed from `test_g0_1_reference.py` are
  restructuring only (parametrize over `COMPARED`, a dict moved). No
  assertion was weakened. `roll_probe.py` reads only
  `bars["hour"].iloc[-1]`.
- U4 (b268252):
  - A one-item run that prints the milestone verdict, and an exit status
    stuck at 1, are each caught (4 and 3 failures).
  - The G0.4 subprocess run shows only the PASS path. The FAIL path is
    covered in-process and by `M1 G1.2`.
  - The file ran in 20.4 s on a quiet machine.
- Every sub-agent's `./scripts/check` at its commit printed `check: green`.
  Under the shared load these runs took 6m25s, 12m22s and 7m04s; one run's
  time was not reported. None went red, so the 600 s problem REVIEW-5
  noted did not recur.
- hands:
  - The protocol's step 2 (revert the non-test files and expect red) is
    vacuous when a unit commit changes only tests, as all four did here.
    Every sub-agent made the named wrong changes instead, as the brief
    allows. The protocol could name that path.
  - Each sub-agent ran `./scripts/check` once, not three times.
  - The kit commit again falls inside the reviewed range.
  - HF-006 was not reproduced: no run was moved to the background.

## Per-commit verdicts

### c1a2100 (U1)

Review of c1a2100 (mission 6, U1, "gates: G0.1 compares every key of backtest --json"). Overall verdict: PASS, no blockers.

1. **PASS. Unit and sections:** the commit is U1 of mission 6 and cites REVIEW-5 blocker 1, decisions 27, 39 and 42, and DESIGN §3, §8, §18.2 and §18.3 G0.1. These match the U1 brief in BUILDER-6-PROMPT.
2. **PASS. Test-first:** the commit touches only `tests/gates/test_g0_1_reference.py`, so reverting the non-test files proves nothing. I reproduced the five mutations from the commit body in `cli.py` and ran the 17 json/low tests each time. All went red with the counts the body gives: `position_max` taking the min 4/17 failed; `net_1x`=999.0 4/17; `trades`=-1 4/17; `position_min` from `h` only 1/17 (LOW case only); an extra key in each instrument map 4/17. Four changes the body did not try were also caught, 4 failures each: `days` off by one, `config_hash` altered, `cost_model`="c2", and the cost totals divided by n-1. The tree was restored after each one; the unmutated run was 17 passed, and the whole file was 36 passed.
3. **PASS.** `./scripts/check` exited 0 in 6m25s. Last line: `check: green`.
4. **PASS. Design conformance:** every key decision 42 lists is compared.
   - The per-instrument figures are computed in the test from the module's rows (`instrument_figures`), not through cli's helper. All of them are also checked against the independent calculation's rows, including the three decision 42 says to compute "the same way".
   - Counts are exact (with an `int` type check). Reals use the decision 39 1e-12 rule. A position is null exactly when the instrument has no window bar.
   - The key sets of the object, the costs map, the instruments list and each instrument map are asserted exact. No existing assertion was removed and nothing is looser than decision 42.
   - Test rules hold: markers `gate` and `gate_m0`, no subprocess, run in-process through `main`, files only under tmp, no skip or xfail, seeds kept in the file.
   - Invariants hold: `src/` is unchanged, no new dependency, no wall clock, no network or secret, no state in the repo.
5. **PASS. Forbidden touches:** the only file changed is the test file. No protected document, `meta/plan.md`, `meta/CHECKPOINT.md`, `config/` or `tests/fixtures/config*` was edited.

**NOT proven:**
- I did not run `./scripts/gate M0 G0.1` (the body claims 55 passed); I ran the gate test file directly.
- I ran `./scripts/check` once, not three times.
- The test hardcodes the trade threshold 1e-9 rather than reading `metrics.TRADE_FLOOR`. It is a test constant, so the threshold-in-config invariant (I-10) is not broken, but if that value ever changes this test will fail.

The worktree `/tmp/rev6-u1` is removed and the main checkout was not touched.

### 9ca8575 (U2)

Review of commit 9ca8575 (mission 6, U2): **PASS on all six points.** Only gaps: the forbidden-reads claim and the date grouping, both below.

1. **Unit and sections (PASS):** It names U2 of mission 6 (REVIEW-5 should-fix 1, D-005), decisions 24, 25, 39 and 43(a), and DESIGN §5.6, §7.3 and §8. It changes one file, `tests/gates/test_g0_1_calc_self.py`: 149 lines added, none removed. That matches the U2 brief.
2. **Test-first (PASS):** No non-test file changed, so reverting the commit proves nothing on its own. Instead I made both mutations in `independent_calc.py`, uncommitted: baseline was `21 passed`; roll cost on `abs(h)` gave `2 failed, 19 passed`; rolled turnover on `abs(h)` gave `2 failed, 19 passed`. In both runs the two failures were exactly the new tests (`test_carried_position_changes_sign_at_the_roll` and `test_flat_position_opens_at_the_roll`). I restored with `git checkout 9ca8575 -- .` and the tree was clean.
3. **Hand values (PASS, they match DESIGN, not just the calculation):**
   - TE (gap +10, position 1 to -0.5): the price before the roll adjusts to 112. gross = -0.5/111, trade 1.5, fee 0.0015, spread 0.375/111, roll = 2·1·(0.001+0.25/111) = 0.002+0.5/111, cost = 0.0035+0.875/111, net_1x = -0.5/111 - cost, net_2x = -0.5/111 - 2·cost. Turnover is 3+2 = 5, against 4 under the mistake, so breakeven_cost = gross/5·1e4.
   - TF (gap -5, position 0 to 0.5): the price before the roll adjusts to 96. gross = 1/96, trade 0.5, fee 0.0005, spread 0.125/96, roll 0, cost = 0.0005+0.125/96. Turnover is 1, against 2 under the mistake.
   - The other bars, trade counts (3 and 2), daily series and roll totals also check out. No existing assertion changed.
4. **`./scripts/check` (PASS):** last line `check: green` (one run).
5. **Design conformance and independence (PASS):** `independent_calc.py` imports only the standard library, numpy, pandas and pyarrow. The new tests import nothing from discotrade. The file has `gate` and `gate_m0` markers and no subprocess, skip, random draw or wall clock (none needed, as its docstring says). It writes only under `tmp_path`, names only invented symbols, uses no network and adds no dependency, so I-9, I-10, I-11, I-12 and I-14 hold. The commit body's claim that it opened none of the forbidden files can't be checked from disk.
6. **Forbidden files (PASS):** none of CLAUDE.md's forbidden files, `meta/plan.md`, `meta/CHECKPOINT.md`, `config/` or `tests/fixtures/config*` is touched.

**NOT proven:**
- The commit's claims that it never opened the forbidden files, that `./scripts/gate M0 G0.1` passed, and that check was green 3 of 3 runs. I ran check once and did not run `./scripts/gate`.
- That the always-open calendar groups these bars on 2019-01-07 by UTC date. The `res.days == [D7]` assertions pass, but I did not read DESIGN §5.3.

The worktree `/tmp/rev6-u2` is removed. `/tmp/rev6-u1` and `/tmp/rev6-u3` are other reviewers' and I left them.

### 9e16050 (U3)

I found no blocker in 9e16050. The unit is mission 6 U3, and every claimed mutation fails both the unit tests and the probe's G0.1 comparison.

1. **Claim: pass.** The commit names U3, finding D-005, decisions 21, 24, 25, 39, 43 (b) and (c), and DESIGN §5.6, §7.3, §8 and §18.3 G0.1. It touches only four files, all under `tests/`.

2. **Test-first: pass.** Reverting non-test files would prove nothing, because no `src/` file changed. I made both mutations in the worktree instead.
   - (a) Roll cost on `order.target` (executor.py:136). Unit tests: `5 failed, 65 passed`, the 4 new executor cases plus the existing `test_one_fill_per_order_with_fill_bar_raw_price_and_components`. G0.1: `4 failed, 37 passed`, the probe's per-bar, daily-series, metrics and cost-totals tests.
   - (b) Rolled turnover on `np.abs(h)` (metrics.py:190). Unit tests: `2 failed, 68 passed`, both new `breakeven_cost` tests. G0.1: `1 failed, 40 passed`, `test_metrics_are_equal[roll_probe.py]`.
   - Both match the commit body. I restored with `git checkout 9e16050 -- .` and the tree was clean after each.

3. **`./scripts/check`: green.** Last line: `check: green` (12m22s).

4. **Design conformance: pass.**
   - The unit tests cover carried-and-changing (-0.5 to 1.0) and flat-then-opening (0 to 1.0). They assert roll = `2*|h(u-1)|*c(u)` per fill and per row, and rolled turnover `2*|h(u-1)|` in `breakeven_cost`.
   - `roll_probe.py` passes the loader and has no imports. It reads only `bars["hour"].iloc[-1]` of the slice, so there is no lookahead (I-2) and it names no market.
   - The probe goes through the module API only, with no backtest CLI, per decision 21. It gets the same four comparisons as the reference files: every FLOATS field plus ts/contract/date, both daily series, every METRICS key and cost totals by subject and instrument, all under decision 39's `assert_eq`. The new test asserts `h(u-1) != h(u)` at every SYNA roll in both rows, and that a roll exists.
   - The 13 removed lines in `test_g0_1_reference.py` are a restructure only: the docstring, the loop header, a moved `out[name]` dict with `json` assigned afterwards, and 4 parametrize lines widened from `FILES` to `COMPARED`. No assertion was removed or weakened. The JSON and LOW-case tests still iterate over `FILES`.
   - `test_executor.py` and `test_metrics.py` gain only additions.
   - Gate rules hold: `pytestmark = [gate, gate_m0]`, no subprocess or skip, seeds in the file, state under `tmp_path_factory`.
   - Invariants hold: no wall clock or network, no `src/` change (I-9), no new dependency, no config change (I-10).

5. **Forbidden touches: none.** The diff against config, src, meta, the root docs, `tests/fixtures/config*`, `independent_calc.py`, its self-test, `pyproject.toml` and `uv.lock` is empty.

**Not proven:** I did not run `./scripts/gate M0 G0.1` as a whole, only the `gate_m0` marker on the reference test file, which passed 41 of 41 unmutated. I ran the check once, not three times. The worktree is removed. `/tmp/rev6-u1` is another reviewer's and I left it alone.

### b268252 (U4)

Review of b268252 (mission 6 U4): it passes on every point, with no defects found. The `/tmp/rev6-u4` worktree is removed, and nothing was edited or committed in the main checkout.

1. **Unit: PASS.** The commit claims mission 6 U4 ("test_gate_script.py under load"), DESIGN §18.2 and decision 45 (REVIEW-5 note). The body lists the item each gate test ran before and after, and the file's run time before and after (180.20s, then 11.26s), as the brief asks.
2. **Test-first: PASS.** The commit changes only `tests/test_gate_script.py`, so reverting non-test files proves nothing. I made each change below to `scripts/gate` without committing it, then restored with `git checkout b268252 -- .` and confirmed a clean tree.
   - Item line always prints PASS: **3 failed, 28 passed**, which matches the body. The failures were `milestone_without_gate_tests_fails`, `one_item_without_gate_tests_fails` and `one_item_verdict_follows_the_item[False]`.
   - A one-item run also prints `gate M0: …`: 4 failed, 27 passed, including the G0.4 subprocess test.
   - A one-item run ends with the milestone verdict instead: 4 failed, 27 passed.
   - Exit status is always 1: 3 failed, 28 passed, including the G0.4 subprocess test.
3. **Gates: GREEN.** `./scripts/check` exited 0 with `942 passed, 86 deselected in 422.25s` (424 s wall, load about 3.7 with other reviewers running). Its last line was `check: green`. The file alone took 31 passed in 20.42s (22.0 s wall, load about 0.6).
4. **Design conformance (decision 45): PASS.**
   - No assertion is removed or weakened; only G0.3 becomes G0.4 in four places.
   - The `./scripts/gate` subprocesses run M1 and M1 G1.2 (no gate test), four usage errors (no item runs) and M0 G0.4 (`4 passed in 0.49s`). None takes minutes, and the timeout went from 600 s to 1200 s.
   - The G0.4 run still proves what the G0.3 run did: the last line is the one-item verdict, the milestone verdict is never printed, and the exit status matches. Mutations 2 to 4 show this.
   - The scratch pytest helpers keep 120 s timeouts. They run tiny suites that took about a second each here, so the load risk is low, but they are not covered by the 1200 s rule.
   - I-11 (no network or secret) and I-12 (no wall clock) hold.
   - I-14 holds: after the runs, only ignored files appeared in the tree (`.venv`, `__pycache__`, including `scripts/__pycache__` from loading the gate script as a module, which was already the case before this commit).
   - No new dependency.
5. **Forbidden touches: PASS.** The diff is exactly `tests/test_gate_script.py`.

**Not proven:**
- That the file stays green under heavy load; I ran `./scripts/check` once, not three times.
- The G0.4 subprocess run only exercises the PASS path. The FAIL path of a one-item run is covered by the in-process monkeypatch tests and by M1 G1.2, as it was at the parent.
