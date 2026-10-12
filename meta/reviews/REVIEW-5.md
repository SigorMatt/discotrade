# REVIEW-5 — mission 5 (roadmap step S0.4, closes M0)

Base 76b9738 (`review: mission 4`, the last `review:` commit); tip
bf943a4. Brief `meta/BUILDER-5-PROMPT.md`; decisions
`meta/decisions/decisions-2026-10-12.md` (items 34 to 40 are new). Each unit
commit was reviewed by its own sub-agent in its own worktree:

| Sha | Unit |
|---|---|
| 8e8215c | U1 |
| 8d27fe1 | U2 |
| 3be4e9b | U3 |
| de9fc09 | U4 calc fix |
| 2881ee0 | U4 |
| 2c64e8d | U5 |
| 80ffc78 | U6 |

This session read the other commits for forbidden edits only:

- 3854c96, the kit. It touches `KIT.md`, `meta/BACKLOG.md`, `meta/ROADMAP.md`, the decisions file and the builder prompt. It is the architect's commit, exempted as in REVIEW-4.
- 9d2d781, the `plan:` commit.
- The `meta:` commits f7ef9f7, 4d43641, df2cbe4, 481feb5, 16b1fbc, 67025c2, ce5dc10, a296f3f, 62edb14, 55c3f24 and bf943a4. They touch only `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/plan.md` and `meta/findings/FINDINGS.md`.
- dd55021. It touches only `meta/FINAL-REPORT-5.md`.

No unit commit touched a file a builder may not edit, nor `meta/plan.md`
or `meta/CHECKPOINT.md`. Since the kit, no commit touched the protected
`meta/` files. This diff is empty:

    git diff 76b9738 origin/main -- config/ tests/fixtures/config_frozen.json \
      tests/fixtures/config/ DESIGN.md SPEC.md PLAYBOOK.toml .claude templates \
      docs pyproject.toml uv.lock

## Gate

Gate M0: PASS

This session ran `./scripts/gate M0` at bf943a4 in the foreground. It exited
0 and took 5m46s of wall time. Its output, verbatim:

```
G0.1 PASS 41 passed in 52.84s
G0.2 PASS 7 passed in 117.19s (0:01:57)
G0.3 PASS 13 passed in 173.12s (0:02:53)
G0.4 PASS 4 passed in 0.25s
gate M0: PASS
```

Each item of DESIGN §18.3 M0, read against its tests:

- **G0.1** (`test_g0_1_calc_self.py`, `test_g0_1_reference.py`): covered.
  - The run uses `test_mixed` with the three reference strategies. The window is shown to hold a SYNA roll, a clipped negative SYNL target, SYNX's proportional fee and dropped bars on each instrument.
  - Every per-bar field of the 14 columns, both daily series, every §8 metric and the cost totals per subject and per instrument are compared under decision 39's equality, with non-empty row counts.
  - An `ast` test checks the calculation's imports.
  - The calculation's author was a sub-agent of its own, and its commit body says it opened none of the forbidden files. That is the author's statement; no test can check it.
  - Seen to fail on `sigma` with `ddof=0`, on gross without the roll gap, and on a spread floor of a full tick.
  - It does not distinguish a roll cost on `h(u)` from one on `h(u-1)`, nor a half spread without its half-tick floor (finding D-005, open). The item does not name these, so the gate stands, but see should-fix 1.
  - The brief's further clause, that the `--json` figures equal the module's, is not fully asserted (blocker 1). It is not a §18.3 item.
- **G0.2** (`test_g0_2_cheating.py`, `cheat_lookahead.py`): covered.
  - The text does what decision 40 lists and passes the loader. The `ast` check matches §12.1's lists.
  - Truncation invariance is checked at 10 or more `t` per instrument, including the window's first and last bars and the bars on each side of the roll.
  - Rows and every metric are identical on a 29-day window with the store ending at the window or more than a year later.
  - Seen to fail on a slice that ends one bar late and on an `iloc` view of the full frame.
- **G0.3** (`test_g0_3_store.py`): covered at full strength.
  - Bars that are not closed and bars that are not later are refused, and every state file stays byte-identical.
  - Old rows have the same content hashes after an append.
  - The dropped bars come from `SynthSource.dropped`. The checked range contains the break, the weekend and the 29-hour closure.
  - The adjusted series is checked over two rolls to 1e-9 relative.
  - `2 * |h(u-1)| * c(u)` is checked for a carried position, and nothing is charged for a flat one.
  - Seen to fail on five wrong changes.
- **G0.4** (`test_g0_4_config.py`): covered.
  - `config check --track hourly` reports 8 instruments.
  - The names are collected from `config/`, and a whole-word scan of `src/` finds none of them.
  - Seen to fail on `NYMEX`, `mgc` and `SIL` planted under `src/`.

No gate test passes because of a special case in product code. U3 to U6
changed no product code.

## Blockers

1. **The G0.1 `--json` comparison checks less than the brief, and the
   final report claims all of it.**
   - The brief's U4 gate says "the `--json` figures equal the module's", and FINAL-REPORT-5 §G0.1 says "the `--json` figures equal the module's".
   - `test_backtest_json_equals_the_module` (`tests/gates/test_g0_1_reference.py:330-351`) compares only these fields:
     - the subject's metrics and `days`;
     - the cost components, per subject and per instrument;
     - the per-instrument `bars`.
   - It never compares the per-instrument `trades`, `position_min`, `position_max`, `cost`, `net_1x` or `net_2x` that `src/discotrade/cli.py:521-527` emits.
   - The U4 reviewer changed `cli.py` so that `position_max` takes the min, `net_1x` is 999.0 and `trades` is -1. All 22 G0.1 reference tests still passed.
   - The disk contradicts the claim, and the test is missing for those figures.
   - Fix: compare every per-instrument `--json` field with the module's evaluation (and with the calculation where it has the figure). Show the test failing on such a wrong change.

## Should-fix

1. **Nothing in the gate checks the timing of the roll cost (`h(u-1)`
   rather than `h(u)`) or the half-tick spread floor.**
   - D-005 shows that G0.1's fixture data cannot see either.
   - The U3 reviewer found the same in the calculation's own self-test (`tests/gates/test_g0_1_calc_self.py`):
     - its carried roll holds 1→1 (lines 199, 249);
     - its flat roll holds 0→0 (lines 203, 257);
     - TD's roll at k=10 holds 1→1.
   - So moving the calculation's roll cost to `h(u)` (`independent_calc.py:341`) or its rolled turnover to `h(u)` (`:351`) leaves all 18 self-tests green.
   - G0.3's carried positions (1.0, -0.5) do not change at the roll either.
   - Fix: add a self-test hand case where the position changes on the roll bar. The architect should answer D-005 (new fixture data, or accept that unit tests cover it).

## Notes

- U1 (8e8215c):
  - On the parent, 12 of the new or changed tests fail; the body says 11. The failing set is otherwise the one the body describes.
  - `gaps.py:127`: when `start >= end`, `_span` reads nothing, so a listed file whose hash differs is not checked there. This is outside decision 35.
- U2 (8d27fe1):
  - `rolls.py:176` calls `store.last_n` for the 24 bars before `u`, which may include bars before `trusted_from`. Only the first bar's `ts` is used, and it is clipped to `trusted_from` (`:177`), so no price before `trusted_from` reaches a result. Read literally, decision 36 says the roll-gap measurement reads no such stored bar.
  - The context cut in `evaluate` already existed on the parent. This unit only tests it.
- U3 (3be4e9b): the `ast` import check catches `import`/`from discotrade`, `importlib` and a bare `__import__`. It does not catch `builtins.__import__`, `getattr(__builtins__, "__import__")`, `sys.modules[...]` or `runpy`. This is enough for honest code but is not a guard against evasion.
- U4 (2881ee0): discotrade's cost totals are recomputed in the test from row sums. The product's own totals are checked only through `--json`.
- U5 (2c64e8d):
  - The control shows a higher net `total_return` on SYNA, SYNX and the subject, but on SYNL only a higher gross. The report says so.
  - The cheating text uses `index[-1] + 1` but never reads the index's length directly.
  - D-006 (one loaded strategy shared across a subject's instruments in `backtest`) is open and not exercised.
- U6 (80ffc78):
  - G0.3 builds the "gap-free underlying" with `synth._generate` over the product's `tradingcal.expected_bars`. A calendar defect shared by the generator and the gap check would not be seen.
  - The `c(u)` helper reads bars and roll records through product readers.
  - Every contract root in `config/` equals a symbol today, so only the planted control proves that roots are collected.
- de9fc09: the D-004 decision governs this commit and the G0.1 `max_drawdown` agreement. It exists only in `meta/plan.md` ("to be carried as decision 41") and in a status line in FINDINGS. `meta/decisions/` has no item 41. The architect should carry it in the next kit. The fix's hand value (0.026) and the changed value (`-sum(d1)`) were recomputed and are right.
- FINAL-REPORT-5 §NOT PROVEN, checked against the sub-agents' findings:
  - It lists D-005, D-006, the limits of the calculation's independence, the SYNL control and the generator dependence.
  - It omits two things: should-fix 1's finding that the self-test cannot see the roll-cost timing either, and the gap of blocker 1.
  - The other claims it makes checked out: the wrong changes and their counts, the frozen-config diff, the review-items table and the shas.
- hands:
  - The kit commit again falls inside the reviewed range, and was exempted as in REVIEW-4.
  - Under load, `tests/test_gate_script.py`'s 600 s subprocess timeout on `scripts/gate M0 G0.3` turned one reviewer's `./scripts/check` red when five checks shared 4 CPUs. Its rerun on a quiet machine was green. Two other reviewers' check runs exceeded their own outer timeouts on a first try.
  - Each sub-agent ran `./scripts/check` once, not three times.
  - None of these runs was moved to the background (HF-006 not reproduced).
- Milestone M0 is not yet met by DESIGN §18.2's definition: the gate passes at the tip, but this review records a blocker.

## Per-commit verdicts

### 8e8215c — U1 (sub-agent report, verbatim)

```
8e8215c (mission 5 U1) passes all five points. I found no real defects, only two nitpicks.

1. **Unit and sections: PASS.** The body names mission 5 U1 (REVIEW-4 should-fix 1 and its note on U3), decisions 5, 18, 31, 34 and 35, DESIGN 5.2, 5.4 and 5.6, and I-5 and I-6. It lists all six files it changes.
2. **Test-first: PASS.** With the parent's `store.py`, `gaps.py` and `rolls.py`, 12 tests fail and 120 pass. The failures are the classification test, the 5 `index_entry` items (2 from the parametrized refusal test, 3 new), the gaps refusal test (2) and its after-fetch test, and the rolls refusal test (2) and its after-fetch test. The body says 11. That count is off by one, but the failing set matches what the body describes. I made both wrong changes myself and each failed the classification test on `'first_bars'`, then I reverted them:
   - a public `@property first_bars` that reads a parquet file;
   - a public method `first_bars(symbol)`.
3. **`./scripts/check` at 8e8215c: GREEN.** Last lines: `All checks passed!` / `925 passed in 549.58s (0:09:09)` / `config check: ok, 168 unverified values` / `check: green`. I ran it once.
4. **Design: PASS.**
   - `index_entry` goes through `_months`, so it gives decision 18's interrupted-append or revised-data-point error and returns None only when there is no month file. The three index-first callers (`gaps.py:118`, `rolls.py:146` and `rolls.py:200`) now use it. Nothing else in `src/` reads `first_ts`, `last_ts` or `months` from the index; the only outside use is `cli.py:313` calling `_indexed_last_ts`, which decision 31 permits.
   - Each point of the brief's gate has a test: both errors, with no `gaps.jsonl` and no roll file written; no stored bar both with no directory and with an empty one; and after recovery by `bars fetch`, `check_gaps`, the roll file, `update_rolls` and `adjusted_as_of` all equal a clean store's.
   - The classification test covers every name in `vars()` of each class in the MRO (`object` excluded), plus the public instance attributes.
   - The diff touches nothing for I-9, I-10, I-11, I-12 or I-14. There is no new dependency. The only lines removed from tests are the old classification test and the unused `inspect` import; no other assertion changed.
5. **Forbidden touches: PASS.** Only the six listed files changed. The diff from 76b9738 to 8e8215c is empty for `config/`, `tests/fixtures/config_frozen.json`, `tests/fixtures/config/`, `pyproject.toml` and `uv.lock`.

**Nitpicks:**
- The failing count in the body is wrong (11 against 12).
- At `gaps.py:127`, when `start >= end` (for example `trusted_from` after the last bar), `_span` returns without reading anything. So in that case a listed file whose hash differs is not checked. Decision 35 covers only an instrument with no index entry, so this is outside its scope.

**Not proven by me:** the body's "green three times" (I ran the check once).
```

### 8d27fe1 — U2 (sub-agent report, verbatim)

```
8d27fe1 passes review: **ACCEPT**, no real defects. Worktree `/tmp/rev5-8d27fe1` is removed and the main repo is untouched.

1. **Unit and claims: OK.** Mission 5 U2. The body cites decisions 23, 24, 27, 36, 37, 38, DESIGN §4.2, §5.6, §7.1, §7.3, and I-4. It changes 3 files in `src/` (`rolls.py`, `backtest.py`, `cli.py`) and 3 test files.
2. **Test-first: OK.** With the parent's `src/`, 15 of 71 tests fail.
   - Eight of them, including every new rolls test, fail as the body says.
   - The other 7 are existing `test_rolls.py` tests. They fail only because `adjusted_as_of` now takes the Instrument record instead of the symbol (TypeError). The new `adjusted_as_of` test also fails that way on the parent.
   - The backtest exit-1 test passes on the parent, as the body says.
   - I reproduced the wrong changes, each in turn reverted:
     - Matching on ts alone fails both exit-1 cases and the evaluate shared-ts test (3 failed).
     - Dropping the `adjusted_as_of` bound fails its test, so that test also fails on behaviour alone.
     - Starting the span at u-24 fails the measurement test.
     - Starting detection at the first stored bar gives 4 failures.
     - Dropping evaluate's context cut gives 4 failures, including slippage. That cut was already in the parent; this commit did not add it.
3. **`./scripts/check`: green.** "All checks passed!", "936 passed in 417.10s", "config check: ok, 168 unverified values", "check: green".
4. **Design conformance: OK.**
   - Decision 36: roll detection starts at the later of the first bar and `trusted_from`, and the measurement span is clipped to it (`rolls.py:164,177`). The estimated fallback only uses bars at or after `trusted_from`. `adjusted_as_of` reads from the later of `start` and `trusted_from`. Evaluate's context and `sigma` are cut at `trusted_from` (`backtest.py:192`).
   - Decision 37: roll records are keyed on (ts, old, new).
   - Decision 38: the labels match. Figures and `--json` are unchanged, and the test checks the figures against the `--json` fixture.
   - Existing tests changed only the argument passed to `adjusted_as_of`; what they assert is the same.
   - Invariants: no network, secret, wall clock, market name, threshold number or new dependency in the diff.
5. **Forbidden touches: OK.** The commit touches only those 6 files. The `meta/` and decisions differences between 76b9738 and 8d27fe1 come from earlier commits in the series, not this unit. There is no change under `config/` or `tests/fixtures/`.

Nitpick: `rolls.py:176` still reads up to 24 stored bars before u with `store.last_n`, which can include bars before `trusted_from`. Only the first bar's ts is used, and it is then clipped to `trusted_from`, so no price before it reaches a result. Read literally, decision 36 says "read no stored bar".

Not proven: the commit says the label wording is the builder's own.
```

### 3be4e9b — U3 (sub-agent report, verbatim)

```
**3be4e9b: PASS on points 1, 3 and 5. Point 2 is weak and point 4 is a pass with gaps: one real test-strength defect.**

1. **Unit: PASS.** This is mission 5 U3, the independent calculation for G0.1. It claims DESIGN §18.3 G0.1, §5.3, §5.6, §6.2, §7 and §8, and decisions 22-26, 29, 30, 36, 37 and 39. It touches 3 files: `tests/gates/independent_calc.py`, `tests/gates/test_g0_1_calc_self.py` and `tests/test_gate_script.py`.
2. **Self-test is real: WEAK.** Of 10 wrong changes I made and reverted, 8 turned it red: no half-tick floor, sigma with ddof 0, a 25-return sigma window, no `trusted_from` filter, roll match on `ts` only, no Sharpe tolerance, raw `Ca(u-1)` in gross, spread hour in UTC (plus a few more). The 2 that stayed green (18 passed) were roll cost on `h(u)` instead of `h(u-1)` (`independent_calc.py:341`) and rolled turnover on `h(u)` (`:351`). `./scripts/gate M0 G0.1` printed `G0.1 PASS 18 passed in 8.01s` and `gate M0 G0.1: PASS`, exit 0. It still passes because `test_g0_1_calc_self.py` already matches the item's files; the later file `test_g0_1_reference.py` isn't needed for that.
3. **`./scripts/check`: GREEN.** Last lines: `config check: ok, 168 unverified values` then `check: green`, exit 0.
4. **Design conformance: PASS with gaps.**
   - The calculation imports only stdlib, numpy, pandas, pyarrow and tomllib, nothing from discotrade.
   - The ast check catches `from discotrade…`, `import discotrade`, `import importlib` and a bare `__import__(...)`; a relative import breaks collection, so the test still goes red. It misses `builtins.__import__(...)`, `getattr(__builtins__, "__import__")`, `sys.modules[...]` and `runpy` (I tried each; all passed).
   - Every case the brief lists is covered, and I re-derived these by hand correctly: bars 1, 2 and 3 of scenario A, both daily values, and sigma at bars 3 and 28.
   - The commit body states the sub-agent opened none of the forbidden files. Markers, temp dirs, no subprocess, no skip, no clock, I-9/10/11/12/14 and no new dependency all hold.
   - The `test_gate_script.py` edit is outside the brief's file list but keeps the same assertions, moved from M0 to M1. The body explains why.
5. **Forbidden touches: PASS.** The commit touches only the 3 files above, and the diff of frozen config against 76b9738 is empty.

**Real defect:** neither roll in `test_g0_1_calc_self.py` can tell `h(u-1)` from `h(u)`. The carried roll at bar 2 has h 1→1 (lines 199, 249), the flat roll at bar 5 has 0→0 (lines 203, 257), and TD's roll at k=10 is also 1→1. A roll where the position changes at the roll bar would pin it. The brief names this exact mistake as the one U4's product test must catch.

**Nitpicks:** the import check isn't hardened against deliberate evasion (enough for honest code). `max_drawdown` without the starting 0 as a peak was later found to disagree with the product (D-004) and was fixed in de9fc09. The roll-record check runs over all context bars, not just the capped slice; no fixture reaches that edge.
```

### de9fc09 — U4 calc fix (sub-agent report, verbatim)

```
Verdict on de9fc09: **PASS**, with no real defects.

1. **Unit and claim:** this is the separate fix commit the D-004 decision asked for (mission 5 U4's mismatch rule). It cites DESIGN §8 (`max_drawdown`) as settled by the "Decision on D-004" in `meta/plan.md` (ce5dc10). It changes 2 files: `tests/gates/independent_calc.py` and `tests/gates/test_g0_1_calc_self.py`. PASS.
2. **Test-first:** with the parent's `independent_calc.py` put back, the self-test gave "2 failed, 17 passed". The new test failed with "AssertionError: max_drawdown: 0.020000000000000004 != 0.026" (the body says it "got 0.02"), and the two-instrument test with the adjusted value also failed. With the commit restored: "19 passed". PASS.
3. **`./scripts/check`:** green. It ended "config check: ok, 168 unverified values / check: green" after 14m57s in one foreground run. My first try only stopped because my own `timeout 1100` wrapper cut it off, not because the check failed. PASS.
4. **Design conformance:** PASS.
   - The calc's peak now starts at 0.0 (`independent_calc.py:377`), which is §8 read with D-004. It returns 0 when there is no fall and for an empty series.
   - I recomputed the hand value: running sums are -0.01, -0.006, -0.026 against a peak of 0, giving 0.026. The [-0.01], no-fall and empty cases are also right.
   - The change of 0.001 to -sum(d1) is justified. d1[0] < 0 and d1[1] = d1[2] = -0.0005, so the peak is now the starting 0 and the drawdown is -sum(d1). The body names this change and the comment derives it.
   - The body states the independence words, covering the U3 list plus `FINDINGS.md` and `plan.md`.
   - The calc still imports only the standard library plus numpy, pandas and pyarrow, nothing from discotrade. There is no new dependency and I-9..I-14 are not touched.
5. **Forbidden touches:** none. The commit edits no file builders must never edit, and not `meta/plan.md` or `meta/CHECKPOINT.md`. `git diff 76b9738 de9fc09 -- config/ tests/fixtures/config_frozen.json tests/fixtures/config/` is empty. PASS.

**Governance note:** the governing decision exists only in `meta/plan.md` (and the D-004 status line in `FINDINGS.md`). `meta/decisions/decisions-2026-10-12.md` has no item 41, so the commit cites a decision "to be decision 41" that does not exist yet. This needs the architect to carry it in the next kit; it is not a fault of this commit.

**Not proven:** the sub-agent's independence is only its own statement in the commit body; I cannot verify what it opened. The body also doesn't say it worked "from this paragraph and DESIGN §8 only", as the decision asked (nitpick).
```

### 2881ee0 — U4 (sub-agent report, verbatim)

```
**Review of 2881ee0** (mission 5 U4, "gates: G0.1 reference strategies against the independent calculation"): **pass, with one real defect.**

1. **Unit and claims: correct.** U4 claims DESIGN §18.3 G0.1, §5.6, §7, §8, §18.1 and §18.2, plus decisions 9, 23–27, 39 and 40. The only file it adds is `tests/gates/test_g0_1_reference.py`; no product code changed.
2. **Wrong changes: reproduced exactly as the commit body says.**
   - sigma with ddof=0: 15 of 22 failed.
   - gross without the roll gap: 8 of 22 failed.
   - spread floor raised to a full tick: 15 of 22 failed.
   - Roll cost on h(u) instead of h(u-1): all 22 passed.
   - Half spread without its half-tick floor: all 22 passed.
   G0.1 does not prove those last two; the commit says so and D-005 records it, so it is disclosed, not hidden.
3. **Gates: green.** `./scripts/check` ended `936 passed, 65 deselected in 358.81s` and `check: green`. My first run was red: `tests/test_gate_script.py` hit its 600 s subprocess timeout on `scripts/gate M0 G0.3` while five review runs shared 4 CPUs. The rerun on a quiet machine was green. `./scripts/gate M0 G0.1` printed `G0.1 PASS 41 passed in 53.28s` and `gate M0 G0.1: PASS`. The plain gate test passed 22 of 22 in 61 s.
4. **Design conformance: met, except the defect below.**
   - Setup matches the brief: `bars fetch` on `test_mixed` into a temp state dir at 2019-08-05, window 2019-06-03 to 2019-07-31.
   - The window checks are all present: the SYNA roll with its roll record, the 07-03/04 closure, SYNL's clipped negative target (count must be above 0), SYNX's proportional fee, and dropped bars taken from the generator.
   - The comparison follows decision 39: exact `eq`, all 14 row columns, row counts with a check that rows are not empty, both daily series, all 9 metrics plus `days`, and cost totals per subject and per instrument.
   - Independence holds: only discotrade's loader feeds the independent calculation. The gate rules hold: both markers, temp dirs only, in-process, no subprocess, no skip, seeds written in the file and asserted. No invariant breach and no new dependency.
5. **Forbidden touches: none.** No change to `config/`, `config_frozen.json` or `tests/fixtures/config/`. U4 did not edit `independent_calc.py` (its only edits are 3be4e9b and de9fc09), nor plan, checkpoint or protected docs.

**Real defect (asserts less than the brief):** the brief says the `--json` figures must equal the module's, but `test_backtest_json_equals_the_module` (`tests/gates/test_g0_1_reference.py:330-351`) compares only the top-level metrics, `days`, the cost components and per-instrument `bars`. Per instrument it never checks `trades`, `position_min`, `position_max`, `cost`, `net_1x` or `net_2x` (built at `src/discotrade/cli.py:521-527`). To confirm, I made `position_max` use min, `net_1x` 999.0 and `trades` -1 in `cli.py`, and all 22 tests still passed.

**Nitpicks:**
- Discotrade's cost totals are recomputed in the test from row sums (`discotrade_costs`, around lines 318-322); the product's own totals are checked only through `--json`.
- The SYNL raw-target capture depends on the independent calculation calling instruments in track order. The call-count assertion guards against a change.

**Not proven by G0.1:** roll cost on h(u-1) versus h(u), and the half-tick spread floor (D-005 is still open).
```

### 2c64e8d — U5 (sub-agent report, verbatim)

```
2c64e8d, mission 5 U5 (G0.2: the cheating strategy cannot gain). It claims DESIGN §18.3 G0.2, §6.2, §7.1, §12.1, §18.1, §18.2, I-2 and decisions 9 and 40. Overall: **pass, no real defects**, with two notes on the control and the index use.

1. **Scope: PASS.** Only three files changed: `cheat_lookahead.py` and `test_g0_2_cheating.py` (both new), plus `tests/test_gate_script.py`. No product code changed.
2. **Test-first: PASS.** Before any change the file gave 7 passed in 432 s. With the slice ending one bar late in `evaluate` it went red: 2 failed, 5 passed. With the frame as an `.iloc` view of a frame holding all later rows it went red again: 2 failed, 5 passed, including p differing at line 320. I reverted with `git checkout` and the tree was clean.
3. **Gates: PASS.** `./scripts/check` ended `936 passed, 25 deselected in 427.62s`, then `config check: ok, 168 unverified values`, then `check: green`. `./scripts/gate M0 G0.2` printed `G0.2 PASS 7 passed in 176.35s` and `gate M0 G0.2: PASS`.
4. **Design conformance: PASS with two notes.**
   - The text matches decision 40: it keeps frames in a module-level `SEEN` list and reads them again, tries rows past the end through `iloc`, `loc`, `values`, `to_numpy()`, their `base` chain and `attrs`, goes long when a later higher close turns up, and passes the loader at 60 lines, the maximum.
   - The ast check matches §12.1's lists word for word.
   - Truncation is checked for at least 10 bars per instrument, including the window's first and last bars and the SYNA bars at roll−1, roll and roll+1. The long store ends more than 365 days later. Rows and every metric match per instrument and for the three-leg subject on a 29-day window.
   - Markers, temporary directories, in-process `main`, no subprocess, no skip, and seeds written in the file are all as the rules ask.
   - The `test_gate_script.py` edit is needed and keeps the same four assertions, now on M1 G1.2, plus a check that no G1.2 file exists.
   - No invariant from I-9 to I-14 is touched and no dependency was added.
5. **Forbidden touches: PASS.** No protected file, `meta/plan.md` or `meta/CHECKPOINT.md` was touched, and the frozen-config diff from 76b9738 to 2c64e8d is empty.

Nitpicks, not defects:
- **Control is weaker than the brief's words:** `tests/gates/test_g0_2_cheating.py:324` asserts a higher `total_return` only for SYNA, SYNX and the three-leg subject, not every instrument. SYNL is checked on gross only, which the commit body states. The brief's sentence can be read as the subject, so the test meets it on that reading. A leak of more than one bar would likely show a net gain on SYNL too. That is my guess; I didn't run it.
- **Index use is thin:** `cheat_lookahead.py:42` uses `index[-1] + 1`, so the last label and arithmetic on it, but never reads the length directly. The ast test only checks that `index` appears.

Not proven: G0.2 doesn't run the multi-instrument `backtest` path, where one loaded text is shared across instruments. This is disclosed and filed as finding D-006, still open.
```

### 80ffc78 — U6 (sub-agent report, verbatim)

```
80ffc78 (mission 5 U6) **passes on every point. I found no real defects, only three nitpicks.** The worktree is removed and the main checkout is clean (I did not touch the other reviewer's /tmp/rev5-2881ee0).

1. **Unit:** U6 adds the G0.3 and G0.4 gate tests. It cites DESIGN §18.3 G0.3/G0.4, §18.2, §5.1–5.4, §5.6, §7.3, §17.1, I-5, I-9 and decisions 3–6, 9, 18, 24, 36, 40, which matches the brief. It adds only `tests/gates/test_g0_3_store.py` and `tests/gates/test_g0_4_config.py`, with no product code.
2. **Test-first: PASS.** Each wrong change turned the tests red, and each was reverted:
   - store takes a bar equal to the last: 3 of 3 refusal tests failed
   - closed check without `bar_seconds`: 3 of 3 failed
   - roll cost factor 1 instead of 2: 2 of 13 failed (the two carried positions)
   - gap check over every hour, breaks included: the gap test failed
   - adjusted series adding the gap to the roll bar itself: the adjusted test failed
   - G0.4: "NYMEX" in `costs.py`, "mgc" in `tradingcal.py` and "SIL" in a new `.txt` under `src/` each made the scan test fail (1 of 4 each time)
3. **Gates:** `./scripts/check` ended "936 passed, 42 deselected in 850.72s", "config check: ok, 168 unverified values", "check: green". My first run hit my 1190 s outer timeout under load and printed no verdict; the second run was green. `./scripts/gate M0 G0.3` gave "G0.3 PASS 13 passed in 171.25s" and "gate M0 G0.3: PASS". `./scripts/gate M0 G0.4` gave "G0.4 PASS 4 passed in 0.23s" and "gate M0 G0.4: PASS".
4. **Conformance: PASS.** Every G0.3/G0.4 clause is asserted at full strength (refusals with all state files byte-identical, old rows by content hash plus exact frame equality, dropped bars from `SynthSource.dropped` with break/weekend/29-hour closure checked in New York time, ≥2 rolls at 1e-9 relative, roll cost recomputed from the fixture TOML, eight hourly instruments, names collected from `config/`). Markers, temp dirs, in-process `main`, no subprocess, no skip, seeds 101/105/106 written in the file; no new dependency.
5. **Forbidden touches: none.** The commit changes no file under `config/`, `tests/fixtures/`, `meta/` or any never-edit file.

Nitpicks (NOT PROVEN):
- `test_g0_3_store.py:313`: the "gap-free underlying" is `synth._generate` over the product's own `tradingcal.expected_bars`, so a calendar bug shared by the generator and the gap check would not be seen.
- `test_g0_4_config.py:47-55`: only top-level `symbol`/`venue` keys and `[source].symbol` are read, and every root today equals a symbol, so root collection is proved only by the planted control test.
- The `unit_cost_at` helper at `test_g0_3_store.py:351` reads bars and gaps through the product's `BarStore.last_n` and `read_rolls`; only the c(u) formula is independent.
```
