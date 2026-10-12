# REVIEW-4 — mission 4 (roadmap step S0.3, repair)

Base 6b37564 (`review: mission 3`, the last `review:` commit); tip
7264b4d. Brief `meta/BUILDER-4-PROMPT.md`; decisions
`meta/decisions/decisions-2026-10-12.md` (items 30 to 33 new). Unit
commits reviewed, one sub-agent each in its own worktree: 836c2ab (U1),
6445223 (U2), 9c4023b (U3), 300be21 (U4). Read by this session for
forbidden edits only: 9f00d99 (the kit: `KIT.md`, `meta/BACKLOG.md`,
`meta/BUILDER-4-PROMPT.md`, `meta/ROADMAP.md`, the decisions file, which
is the architect's commit and not a builder's), 593c0ea (`plan:`), the
`meta:` commits 7ae9965, 12ae295, 6ee68dc, a829c52, 7264b4d (only
`meta/CHECKPOINT.md`, `meta/journal.md`, `meta/plan.md`), and e740b3b
(only `meta/FINAL-REPORT-4.md`). No unit commit touched a file a builder
may not edit, `meta/plan.md` or `meta/CHECKPOINT.md`.
`git diff 6b37564 origin/main -- config/ tests/fixtures/config_frozen.json
DESIGN.md SPEC.md PLAYBOOK.toml .claude templates docs` is empty.

## Gate

not a closing mission

(The brief says this mission closes no milestone. For the acceptance check
only: `tests/gates/` does not exist, and `./scripts/gate M0` at the tip
printed `G0.1` to `G0.4 FAIL no gate test` and `gate M0: FAIL`, as the
brief expects.)

## Blockers

None.

## Should-fix

1. **The `BarStore` classification test misses a public reader written
   as a property** (9c4023b, `tests/test_bar_store.py`,
   `test_every_public_bar_store_method_is_classified`). The test keeps
   only attributes for which `callable(value)` is true. The U3 sub-agent
   added a public `@property` that reads bars, and the test still
   passed. The brief's stated purpose is "so a reader added later must be
   classified". The report's wording, "every public method", is literally
   true, but the guard can be bypassed. Fix: enumerate every public name
   of the class, properties included.

## Notes

- U1 (836c2ab): `sharpe` now applies decision 30 (`src/discotrade/metrics.py:123`).
  - On the parent, 12 tests fail, among them five of the eight constants.
  - Both wrong `trades` changes were reproduced: one gave 1 instead of 2, the other 3 instead of 2.
  - The sub-agent recomputed the hand value of `[0.1, 0.1, 0.1 + 1e-9]` in exact fractions: 2749545426.14, against 2749545427.59 in float (relative error about 5e-10, inside the test's 1e-6).
  - The test helper sets `cost = roll`. That is right only because fee, spread and slippage are 0 there.
- U2 (6445223): the decision 18 test puts the unlisted month after the window. An unlisted file inside the window is not driven through `backtest`. FINAL-REPORT-4's NOT PROVEN omits this; it is minor.
- U3 (9c4023b):
  - `cli.py:313` calls the private `_indexed_last_ts` from outside its module, which decision 31 permits.
  - Found during this review, and older than this mission (61e1c59, mission 2): `bars/gaps.py:115`, `rolls.py:141` (`update_rolls`) and `rolls.py:195` (`adjusted_as_of`) return or raise "no stored bar" when the index has no entry for the instrument, before any `read_range` call. So if the very first append of an instrument crashes before its index write, those callers report "no bars" (or nothing) instead of refusing with the interrupted-append error of decision 18. `bars fetch` runs `recover()` first, so nothing is wrong today. This belongs with the S0.4 roll and `trusted_from` checks already in `meta/BACKLOG.md`.
- U4 (300be21):
  - The docstring's "`ema` ... has no leading NaN" holds only when row 0 is finite: `ema([nan, 1, 2], 3)` gives `[nan, 1.0, 1.5]`.
  - The module's "takes a Series or array and a window" was already loose before this mission, because `atr` and `donchian` take several series.
  - Neither point is false of finite inputs, so neither is a defect.
- FINAL-REPORT-4 §NOT PROVEN against the sub-agents: everything they could not prove is listed, except the U2 in-window gap and should-fix 1 above. Its claims checked out:
  - the eight constants and the `compute` case;
  - the wrong changes and their counts (U1 1 and 3; U4 9 and 18 failures);
  - the `REFERENCE_ROOT` seam, which equals the old inline path, so behaviour is unchanged;
  - no test writes into the working tree;
  - the existing assertions are unchanged in every unit;
  - no new dependency;
  - `config/` and the frozen fixture are unchanged since this review's base, not only since 9f00d99;
  - the review-items table matches the shas.
- Step S0.3 can be ticked under decision 33: this review records no blocker.
- hands: the protocol's base, the last `review:` commit, puts the architect's kit commit (9f00d99) inside the reviewed range. It edits files a builder may not touch (`meta/ROADMAP.md`, `meta/BACKLOG.md`, `meta/decisions/`, the builder prompt). The protocol does not say that a kit commit is exempt from the forbidden-touch check; this review exempted it as the architect's.
- hands: each sub-agent ran `./scripts/check` once, not three times, in the foreground with a 20-minute timeout. Each run took about 6 minutes with four running at once, and none reported being moved to the background (HF-006 stays open, not reproduced).

## Per-commit verdicts

### 836c2ab — U1 (sub-agent report, verbatim)

```
Review of 836c2ab (mission 4 U1): passes on all six points, no defects found.

1. **Unit and sections: PASS.** The body names mission 4 U1 (REVIEW-3 blocker 1 and should-fix 1), DESIGN §8 and §2 (I-4), decisions 25 and 30, and R-7, as the brief asks.
2. **Test-first: PASS.** With the parent's `metrics.py`, 12 tests fail and 42 pass. Five constant series fail in both parametrised tests ([0.1]*3, [0.03]*10, [1/3]*10, [0.07]*10, [1e-6]*20), and so do the one-ulp test and the `compute` test. That matches the body. I made both wrong `trades` changes myself:
   - dropping every rolled row: the new test fails with `assert 1 == 2`
   - also counting a row with a nonzero roll cost: it fails with `assert 3 == 2`

   The old trades test passes under both, as the body says.
3. **`./scripts/check`: GREEN.** Last lines: `All checks passed!` / `774 passed in 346.17s (0:05:46)` / `config check: ok, 168 unverified values` / `check: green`. I ran the full check once, not three times.
4. **Design conformance: PASS.**
   - `src/discotrade/metrics.py:123` returns not-a-number when every value equals the first, or when `not sd > 1e-12*max|x|`. The fewer-than-2-days case is kept, and `sharpe_2x` goes through the same function.
   - All 8 constant series, the `compute` hand case (0.07 at 1x, 0.03 at 2x, ten days) and the [0.1, 0.1, 0.1+1e-9] case are tested.
   - The not-a-number value is checked against all three comparisons in `__all__` (`positive`, `negative`, `above` both ways) over 10 values.
   - I worked out the hand value myself with exact fractions: 2749545426.1387. The float computation gives 2749545427.586, a relative gap of about 5e-10, inside the test's tolerance of 1e-6.
   - The body contains the required sentence "roll trades are not counted; a bar with a roll and a real trade is".
   - No existing test assertion changed. The only removed lines are the docstring and the `rows` helper, whose new `roll`/`cost` columns default to zeros.
   - Invariants I-9, I-10, I-11, I-12 and I-14 hold: the 1e-12 constant is in the module as decision 30 allows, there is no market name in src, and no network, secret, clock or state path appears. `pyproject.toml`, `uv.lock` and `config/` are unchanged.
5. **Forbidden files: PASS.** Only `src/discotrade/metrics.py` and `tests/test_metrics.py` changed.
6. **Commit body: PASS.** It lists both files and its claims match what I observed.

**Not proven by me:** the body's "green three times" (I ran the check once), and the parent's failing value of 7.3e16, which I did not read back.

**Cosmetic, not a defect:** in the test helper, `cost` is set to `roll`. That is correct only because fee, spread and slippage are zero there.
```

### 6445223 — U2 (sub-agent report, verbatim)

```
**6445223 (mission 4, U2): PASS, no defects found.**

1. **Unit and sections: PASS.** The body names U2, `backtest` exit 1 paths (REVIEW-3 should-fix 2), DESIGN §3 (exit status) and §6.2, and decisions 18, 21, 22, 24 and 27.
2. **Test first: PASS.**
   - With the parent `cli.py`: 22 passed, 3 errors. The three strategy tests error at the monkeypatch because `REFERENCE_ROOT` does not exist. The roll and unlisted-month tests pass, since that behaviour already existed.
   - Mutation check: I changed the except clause in `src/discotrade/cli.py` (~l.628-629) to return 2 for one path at a time. Each change failed exactly its own test(s) and nothing else in the file: MissingRollError (both roll cases), ResultError "outside", ResultError "raised", StrategyError (loader), BarStoreError "not listed". All changes reverted.
3. **`./scripts/check` at 6445223: green.** Last lines: `config check: ok, 168 unverified values` / `check: green`.
4. **Design conformance: PASS.**
   - Every new test asserts exit 1 and checks that the message names the cause:
     - SYNA, the roll ts, "no record of that roll" and `bars fetch`, for a roll inside the window (06-14) and in the context before it (03-14).
     - For 2.0 and for a raise: `position on {symbol} at bar ts {ts}`, plus "outside [-1, 1]" or RuntimeError and its message.
     - For six PARAMS: max_params and "6 parameters".
     - For the unlisted file: SYNX, the month and "not listed in the index".
   - The seam (`src/discotrade/cli.py:32`, `REFERENCE_ROOT = REPO_ROOT / "reference"`) is the same path as the old inline value, so it changes no behaviour.
   - The tests mutate copies of state in tmp_path and write strategy texts to tmp_path. After the tests, `git status` showed only the ignored `.hypothesis/`, and nothing was added under `reference/`.
   - The diff only adds lines after l.207, so the existing exit 2 and refused-bar-file tests are unchanged.
   - Invariants I-11, I-9, I-10, I-12 and I-14 hold, and there is no new dependency.
5. **Forbidden touches: PASS.** Only `src/discotrade/cli.py` and `tests/test_cli_backtest.py` changed.
6. **Commit body: PASS.** It lists both files, names the monkeypatch-on-tmp_path seam, and its claims match what I reproduced. Its own NOT PROVEN list is accurate.

**Not proven:** an unlisted month file classed as a revised data point, loader rules other than max_params, and results like NaN, inf or non-numbers through the command. One more small gap: the decision 18 test uses a month after the window, so an unlisted file inside the window is not exercised.
```

### 9c4023b — U3 (sub-agent report, verbatim)

```
Review of 9c4023b (mission 4, unit U3). **Verdict: pass, no blocker.** Worktree /tmp/rv4-u3 is removed; nothing in the repo was edited.

1. **Unit:** U3, "`BarStore.last_ts` refuses as a reader". It claims DESIGN §5.2, decisions 2026-10-12 items 5, 18 and 31, REVIEW-3 should-fix 3, and I-5 and I-6. Pass.
2. **Test-first:** pass. With the parent's store.py and cli.py, the new tests in tests/test_bar_store.py gave 7 failed, 5 passed. The 7 failures are the five `last_ts` tests (including the bars fetch one) and the two `last_ts` cases of `test_every_reader_refuses_an_unlisted_month_file`.
3. **`./scripts/check`:** green. Last lines: "792 passed in 350.75s", "config check: ok, 168 unverified values", "check: green".
4. **Decisions 31 and 18:** pass.
   - Public `last_ts` (src/discotrade/bars/store.py:151) goes through `_months` and then `_read_month` on every listed month, so it gives the same interrupted-append and revised-data-point errors as `read_range` and `last_n`. All three cases are tested: unlisted and interrupted, unlisted and revised, listed with a changed hash.
   - The private `_indexed_last_ts` (store.py:162) is used only by `_read_month` (store.py:267) and by bars fetch after `recover()` (src/discotrade/cli.py:313). `append` reads the index directly after `recover`. The test shows `last_ts` refuses before the second bars fetch and returns the completed last ts after it.
   - There are no other `last_ts` callers in src/. Every caller in tests runs on a clean store.
   - Classing `index()` as a non-reader is reasonable: its callers in gaps.py:115 and rolls.py:141 and :195 read bars through `read_range`, which refuses.
   - The classification test fails for an unclassified method: I added a public `first_ts` and it failed.
   - Existing tests are unchanged (115 lines added, 0 removed). No new dependency, and I-5, I-6, I-9, I-11, I-12 and I-14 are untouched.
5. **Forbidden touches:** pass. Only store.py, cli.py and tests/test_bar_store.py changed.
6. **Commit body:** pass. It lists all three files, and what it says the tests prove matches what I saw.

**Defects (minor, not blocking):**
- The classification test (tests/test_bar_store.py, `test_every_public_bar_store_method_is_classified`) keeps only names where `callable(value)` is true. A public `@property` reader is therefore never caught: I added one and the test still passed.
- Already present before this commit, outside U3: gaps.py:115 and rolls.py:141 return early when the instrument has no index entry, before calling `read_range`. A first-ever append that crashed before the index write (only unlisted files) is then reported as "no bars" instead of refused.
- Style: cli.py:313 calls a private method of `BarStore` from outside its module. Decision 31 allows this.

**NOT proven:**
- The refusal for a listed file whose hash differs is tested in this commit only for `last_ts`. I did not re-check that the older tests cover it for `read_range` and `last_n`.
- I ran check once, not three times.
```

### 300be21 — U4 (sub-agent report, verbatim)

```
**Verdict: pass** for 300be21 (mission 4, U4 "Indicator module text"). No blockers.

1. **Unit:** U4. The commit claims REVIEW-3 should-fix 4, decision 32, DESIGN §6.3 and §13.4, and I-2. That matches the brief.
2. **Test-first:** pass. With the parent's docstring restored, the new tests went red: 10 failed, 108 passed. With `ema` given `min_periods=window`, 9 failed. With `sma` given `min_periods=1`, 18 failed (sma and bollinger). All three counts match the commit body, and every change was reverted.
3. **`./scripts/check`:** green. Last lines: `config check: ok, 168 unverified values` then `check: green`. Pytest was `910 passed in 349.69s`.
4. **Design conformance:** pass.
   - The only change in `src/` is the module docstring. No function's code changed.
   - The test enumerates functions with the same `public_functions()` the property test uses, so a later function cannot be missed. It runs windows 2, 3 and 12 on inputs of 1, 2 and 25 rows, and checks every returned column of row 0 (NaN, or a number for the functions the docstring names as seeded).
   - The new text is true of `returns`, `rsi`, `atr`, `realized_vol`, `bollinger`, `donchian`, `zscore` and `volume_zscore`.
   - No per-function docstring contradicts its function, and the first lines used for the §13.4 worker list are unchanged.
   - I-2, I-9 and I-11 hold, and there is no new dependency.
5. **Forbidden touches:** none. The commit touches only `src/discotrade/indicators.py` and `tests/test_indicators.py`.
6. **Commit body:** lists both files. It states what the tests prove, and openly says the tests do not prove "NaN until the window is full" beyond row 0.

**Minor notes, not defects:**
- `src/discotrade/indicators.py:9-10`: "it has no leading NaN" holds only for input that is finite at row 0. `ema([nan, 1, 2], 3)` returns `[nan, 1.0, 1.5]`.
- `src/discotrade/indicators.py:4`: "takes a Series or array and a window" was already inaccurate before this commit, since `atr` and `donchian` take several series.

**Not proven:** "NaN until the window is full" beyond row 0, which rests on the older hand-value tests. Window 1 is not exercised, though the docstring limits its claim to windows above 1.
```
