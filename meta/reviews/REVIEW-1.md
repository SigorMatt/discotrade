# REVIEW-1 — cold review of mission 1 (roadmap step S0.1)

Base 9ed3cd4 (no earlier `review:` commit; the kit commit that added
`meta/BUILDER-1-PROMPT.md`). Range `9ed3cd4..origin/main`, tip 2501359.
Unit commits reviewed by one foreground sub-agent each: f04fab2, 5ddcba4,
f4e0141, 8348743, 3b5439e, e1c3f76. The `plan:`, `meta:` and `report:`
commits (766cf32, 1971775, 815c463, 205fc02, 8054e3e, 7b9952c, 203b002,
0650364, 2501359) were read for forbidden edits: they touch only
`meta/plan.md`, `meta/CHECKPOINT.md`, `meta/journal.md` and
`meta/FINAL-REPORT-1.md`. No file on the CLAUDE.md never-edit list changed
in the range (`git diff 9ed3cd4 origin/main` over DESIGN.md, SPEC.md,
PLAYBOOK.toml, meta/ROADMAP.md, meta/BACKLOG.md, meta/ARCHITECT.md,
meta/REVIEW-PROTOCOL.md, meta/BUILDER-*, .claude/, docs/, templates/ is
empty). `config/` did not exist at the base, so no pre-existing frozen value
could change; f4e0141 only adds to what 5ddcba4 created.

At the tip, run by the reviewer in the foreground: `./scripts/check` three
times in a row, each ending `config check: ok, 168 unverified values` /
`check: green` (271 tests). `./scripts/gate M0` printed the output below and
exited 1, as the brief's acceptance requires.

## Gate

not a closing mission

(For the record, `./scripts/gate M0` at 2501359:

    G0.1 FAIL no gate test (tests/gates/test_g0_1_*.py)
    G0.2 FAIL no gate test (tests/gates/test_g0_2_*.py)
    G0.3 FAIL no gate test (tests/gates/test_g0_3_*.py)
    G0.4 FAIL no gate test (tests/gates/test_g0_4_*.py)
    gate M0: FAIL

exit 1, which is what the mission's acceptance asks for.)

## Blockers

None.

## Should-fix

1. A crash between renaming a month file into place and writing the index
   locks the instrument permanently (`src/discotrade/bars/store.py`
   289-307). The U4 reviewer reproduced it: both `append` and `read_range`
   then refuse the file as "a revised data point", which would raise a
   false `revised_data` health alert, and nothing recovers. FINAL-REPORT-1
   NOT PROVEN says such a crash "is caught by the reader's hash check, not
   prevented". That is true but understates the effect: the instrument
   stays locked out for good. Either a recovery rule (DESIGN is silent, so a
   finding first) or a report line that says so. Lesser points: no `fsync`
   before the rename (`store.py` 167-171), and NaN prices are accepted.
   DESIGN §5.1 is silent on NaN, so that is a finding, not a defect.
2. `src/discotrade/sources/synth.py` 46-54 hard-codes the generator's
   result-moving settings: the hour-of-day volatility and volume shapes,
   `GAP_SCALE`, `RANGE_SCALE`, `VOLUME_MEDIAN` and `VOLUME_SIGMA`. DESIGN
   §4.2 puts "the keys section 17 names" in the instrument's `[source]`
   table, and §17.1 names the hour-of-day pattern and the open gap. The
   commit body records the choice as "DESIGN silent", but later gates
   replay on these bars. Before S0.2 or S0.3 build on them, either file a
   finding asking where they belong or move them into `[source]`. A later
   move is a frozen-config change.
3. I-14's refusal depends on `REPO_ROOT = Path(__file__).resolve().parents[2]`
   (`src/discotrade/cli.py:25`). That is correct only for the editable
   install `uv.lock` gives. Under a wheel install it points into the venv,
   and a state directory inside the repository is silently accepted. Also,
   `--state ""` resolves to the working directory and is accepted, where it
   should be a usage error.
4. The gap check scans all stored history, not history up to `D`
   (`src/discotrade/bars/gaps.py` 115-139). A replay of a past day can
   therefore append to `gaps.jsonl` gaps that lie after `D`, so a replayed
   day does not equal the original run of that day (I-12 / §16.4 spirit).
   The append to `gaps.jsonl` is also not atomic: a torn last line makes
   the next run's `json.loads` (`gaps.py:99`) crash.
5. The provenance of the eight instruments' contract values reads stronger
   than the report. Each `[spec]` table has `checked = "2026-10-12"` and a
   `source` naming a cmegroup.com contract-specification URL "(multiplier,
   tick size)", which implies the page was read that day. FINAL-REPORT-1
   NOT PROVEN says all of them are "from memory of the exchange's public
   contract pages". `verified = false` is set honestly, but `checked` and
   `source` should not suggest a reading that did not happen. Fixing the
   strings is a frozen-config change: file a finding and leave the change
   to the owner. Likewise, `[cost] source = "SPEC.md §17"` covers the
   spread ticks and `slippage_coef = 0.02`, which come from DESIGN §4.2 /
   R-5 and not from SPEC §17.
6. The frozen-config drift check compares values with Python `==`
   (`src/discotrade/config.py` 690-703). An edit of `5.0` to `5`, or of `1`
   to `true`, is not seen as drift. A removed frozen file always fails, and
   no HISTORY entry can approve the removal (688-690). DESIGN is silent on
   that.
7. `scripts/gate M0 <item>` ends with `gate M0: PASS` when only that item
   passed, which reads as the whole milestone passing. Also, a test marked
   `gate_m0` but not `gate` would run in `./scripts/check` as well as in
   the gate. Nothing enforces that the two markers go together.

## Notes

- D-001 and D-002 are genuine design gaps, filed rather than improvised.
  D-002 has one more case: with no stored bars at all for the track, the
  window fraction is 0.0 (`gaps.py:49`), so generation is never skipped.
  The architect may want this in the same answer.
- DESIGN §18.1 says tests marked `container` skip with a printed reason
  when no runtime is found. The marker exists in `pyproject.toml`, but the
  skip rule is not built. No `container` test exists yet, and
  FINAL-REPORT-1 discloses this. The mission that adds the first
  `container` test must build the rule.
- The U5 "no gap across a closure" test builds its complete store from the
  same `expected_bars` the check uses. It proves the check is consistent
  with the calendar, not that the calendar is right. Calendar correctness
  is U3's tests, whose hypothesis property killed two mutants the U3
  reviewer tried (closures ignored, daily break removed).
- In U6, the "missing bars are exactly the dropped ones" test is not
  independent: `dropped()` shares `_series()` with `fetch()`. The statistics
  seeds (102-106) live in the fixture TOMLs, not in the test file. That is
  acceptable for a unit test; a gate test must write its seeds in the test
  (§18.2).
- Untested and undisclosed in detail: the hour-of-day volatility and volume
  patterns, and the independence of the open gap from the return.
- `config.py:290` bounds `drop_fraction` at 0.5. Neither DESIGN nor the
  commit body names that bound.
- `tradingcal.py:178`: `in_main_session` cannot represent a main session
  that crosses midnight. No current instrument has one.
- `bars gaps` defaults to the day before the UTC date of `--as-of`. This is
  disclosed, but it can lag a trading day that has already closed (for
  example `--as-of` at 22:00Z).
- The test-first evidence for most units is an import-level red, because
  the units add new modules. It shows the tests depend on the code. It does
  not show each test was seen failing on its own.
- hands: the protocol's test-first step (revert the non-test files, expect
  red) gives only a collection-time `ModuleNotFoundError` for any unit that
  adds a module. It cannot tell a meaningful test from a vacuous one. A
  mutation probe, as the U3 sub-agent did on its own initiative, would
  give stronger evidence. The protocol also does not say whether `config/`
  and `tests/fixtures/` count as "non-test files" to revert, and the
  sub-agents chose differently (U2 reverted `config/`, U3 kept it).
- hands: CLAUDE.md's "Which document wins" names `meta/decisions/`, but the
  directory does not exist yet. `config.py`'s frozen check requires a
  decision file there, so the first approved change will create it.

## Per-commit verdicts

### f04fab2 (U1)

f04fab2 (U1, skeleton) passes review with no blocker; there are three should-fix items below. My worktree is removed and the main checkout is clean. I left the other /tmp/rev-* worktrees in place because they are not mine.

1. **Unit:** U1 (skeleton and the two gate scripts). It claims DESIGN §3, §18.1 and §18.2, plus invariants I-11, I-12 and I-14. The file list in the commit body matches the commit's 13 files.
2. **Test-first: red confirmed.** With the non-test files removed, `test_cli.py` and `test_clock.py` fail at import. Six of the eight tests in `test_gate_script.py` fail because `scripts/gate` is missing. The two that still pass are the conftest skip tests, which is expected since `tests/conftest.py` is itself test code. I ran this in a venv without the main checkout's editable discotrade, so the imports could not leak in. The tree was clean after restoring.
3. **`./scripts/check` at f04fab2: green.** Last lines: `37 passed in 2.29s`, `discotrade 0.1.0`, `check: green`. It never printed a FAIL line. I ran it once, not three times.
4. **Design conformance: PASS, with notes.**
   - §18.1: the order and the `-m "not gate and not network and not live"` filter are correct. Two parts are missing, and the commit body says so: the `config check` smoke step and the container auto-skip.
   - §18.2, probed with throwaway gate files:
     - A passing item prints PASS.
     - A skip prints FAIL.
     - An item with no `gate_m0` test, or with no file, prints FAIL, and the run exits 1.
     - Bad arguments exit 2.
   - §3: the four options and exit status 2 behave as specified.
   - I-9, I-11, I-12 and I-14: no violation found. No dependency was added beyond the allowed list.
5. **Forbidden touches: none.** Nothing under `meta/`, `DESIGN.md`, `SPEC.md`, `PLAYBOOK.toml`, `.claude/`, `docs/`, `templates/` or `config/` changed.
6. **Commit-body claims: not contradicted by the disk, and suitably hedged** ("for the paths tested", "the three forms tested"). The "three times in a row" claim is the builder's own; I did not see it happen.

Should-fix:
- **(a)** `src/discotrade/cli.py:25`: the state-inside-repository refusal depends on `REPO_ROOT = Path(__file__).resolve().parents[2]`. That is right only for an editable install, which `uv.lock` uses. In a wheel install it points into the venv, so the I-14 refusal silently does nothing.
- **(b)** `cli.py` `_context` (around line 96): `--state ""` resolves to the current directory and is accepted outside the repo. An empty `--state` should be a usage error.
- **(c)** `scripts/gate`: a single-item run prints `gate M0: PASS`, which reads as the whole milestone passing. Also, a test marked `gate_m0` without `gate` would run in the gate and also in `./scripts/check`.

Not proven:
- That `./scripts/check` is green three times in a row (I ran it once).
- That the `discotrade --as-of`, `--state` and `--track` options are accepted after a subcommand name, since no subcommand exists yet.
- That a test marked `container` skips when no runtime is found (not implemented yet).

### 5ddcba4 (U2)

5ddcba4 (mission 1 U2, configuration records): no blockers. Verdict: pass, with the should-fix notes below.

1. **Unit and sections:** U2, claiming DESIGN §4, §4.1, §4.2, §4.3, §18.1, §18.2 and I-9/I-10. The files match the U2 brief.
2. **Test-first: red.** I treated `config/` and `src/` as product and reverted them (`config.py` and `config/` deleted; `cli.py` and `scripts/check` set back to the parent), keeping `tests/fixtures/` as fixtures. `test_config.py` and `test_config_history.py` fail at import (`discotrade.config` missing). In the other two files, 6 tests failed and 2 passed: the usage-error test and the planted-name self-test, which don't need the product. After restoring, `git status` was clean.
3. **`./scripts/check`: green.** Last lines: `config check: ok, 64 unverified values` / `check: green`. 64 is 8 instruments × (4 `[spec]` + 4 `[cost]`) values.
4. **Design conformance: pass.**
   - `thresholds.toml` and `thresholds_v1.toml` parse equal to the DESIGN §4.3 block.
   - `thresholds_gate.toml` differs in exactly the seven §18.2 keys, with the right values.
   - `hourly.toml` matches §4.1.
   - All eight instruments carry the SPEC §17 fees, slippage 0.02, `verified=false` and companions; contract specs look right (MYM CBOT, MGC/SIL COMEX, MCL NYMEX).
   - `test_synth` is SYNA–SYND, all shortable, 28/7/480/7. `test_mixed` is SYNA (quarterly roll), SYNL (no short) and SYNX (`fee_bps`, `test_only`), with dropped bars.
   - The history check takes the last entry's `new`. The frozen-config check requires the named decision file under `meta/decisions/` to exist.
   - Unknown keys are refused by dotted name; exactly one fee form; `test_only` only in `test_` tracks.
   - My grep of `src/` for the symbols, venues, CBOT, GLBX, MDP3, Databento and globex found nothing.
   - No wall clock, network, secret, state write or new dependency; no hard-coded threshold values (only key/type schema).
5. **Forbidden touches: none.** `FINDINGS.md` is append-only except that the "(none yet)" placeholder line was replaced by D-001 (cosmetic).
6. **Claims:** the commit body matches the disk; I found no overreach.

Should-fix (none blocker-grade):
- `src/discotrade/config.py:688-690`: a removed frozen file always fails, and no HISTORY entry can approve its removal. DESIGN is silent here.
- `tests/test_instrument_agnostic.py:28-29`: if `config/instruments` is empty, the pattern becomes empty and flags every line of `src/`. It fails safe, but with noise.
- `config.py:290`: `drop_fraction` has an upper bound of 0.5 that isn't in DESIGN or the commit body.
- `config.py:690-703`: values are compared with Python `==`, so a change from 5.0 to 5 or 1 to true would not register as drift.

Not proven: the multipliers, tick sizes, listing dates and main sessions are from memory, and the SPEC §17 fees are unverified. The commit body already says so. I ran `./scripts/check` once, not three times. The temporary worktree is removed; the other `/tmp/rev-*` worktrees from other reviews were left alone.

### f4e0141 (U3)

I found no blocker in f4e0141 (mission 1, U3), and nothing I'd call a should-fix: every point passes, with two minor notes and the unverified closure data listed below. Worktree /tmp/rev-f4e0141 has been removed and the main checkout is untouched (clean on 2501359).

1. **Unit and sections:** mission 1 U3, the trading calendar. The body cites DESIGN §5.3, §4.3, §4 and §2 (I-9, I-10, I-11, I-12), which matches the U3 text in BUILDER-1-PROMPT.
2. **Test-first: RED as expected.** I reverted `src/discotrade/config.py` to its parent and deleted `tradingcal.py`, keeping `config/` and the test fixtures at the commit's version (data, not code). `test_tradingcal.py` failed at collection with an ImportError on `load_calendar`. The config_check and config_history tests gave 3 failed, 34 passed. Restoring gave a clean tree.
3. **`./scripts/check`: GREEN.** Last lines were `config check: ok, 168 unverified values` and `check: green`. pytest alone gave `214 passed`.
4. **Design conformance: PASS.**
   - All four §5.3 functions are pure functions of the record. Expected bars are epoch-aligned UTC bars whose interval overlaps open time.
   - Times are converted to UTC on each local date, so clock changes are handled. Tests cover the spring week (2024-03-10), the week before it, the autumn week (2024-11-03), a weekend, the daily break, Christmas 2026, the day after Thanksgiving 2026 and the synthetic closure.
   - `always_open` refuses any other key and its trading day is the UTC date. Every closure carries checked, source and verified (false).
   - The 609 calendar keys are in `config_frozen.json`, and `config check` loads calendars and refuses an instrument whose calendar has no record.
   - The hypothesis tests are derandomized and compare against a separate wall-clock rule written in the test. They are not weak: two mutants I tried (closures ignored, daily break removed) both failed them.
5. **Invariants: PASS.**
   - I-9: no cme, globex, nymex, comex, cbot, chicago or new_york anywhere under `src/`.
   - I-12: no wall clock.
   - I-11 and I-14: tests are offline and write no state.
   - No new dependency: the commit does not touch pyproject or uv.lock. tzdata in uv.lock is a pre-existing pandas dependency for win32/emscripten only.
6. **Forbidden touches: none.** No meta, CLAUDE.md, DESIGN, SPEC or `.claude` files changed. Diffing 5ddcba4 against f4e0141 over `config/` and `config_frozen.json` shows additions only (+1439, no removed lines), so no earlier frozen value changed.

**Commit body claims:** they match the disk (100 closures, 2019 to 2027 covered, all unverified). I found no overreach.

**Not proven, as the body says:** every closure date and time in `cme_globex.toml` and the weekly schedule were recalled, not read from the exchange. The doubts it lists are Good Friday in payroll years, the 2025-01-09 halt, the 2021 and 2027 Christmas closes, and holiday hours for non-equity products. This must stay in the mission's NOT PROVEN list.

**Minor notes, not defects:**
- `src/discotrade/tradingcal.py:178`: `in_main_session` cannot handle a main session that crosses midnight. No current instrument has one.
- In the same function, DESIGN's "weekday that is not closed" is read as "open at the bar's open time". The body states this choice and it is reasonable.

### 8348743 (U4)

**8348743** (mission 1, unit U4, the bar store). Verdict: pass, no blocker. I removed my worktree; the main checkout is unchanged.

1. **Unit and sections:** the commit claims DESIGN §5.1, §5.2, §9.2 (content hash) and §2 (I-5, I-12, I-14), which matches the U4 text in the builder prompt. All five files are new: `state.py`, `bars/__init__.py`, `bars/store.py` and two test files.
2. **Test first:** with the three source files deleted, both new test files go red with `ModuleNotFoundError: No module named 'discotrade.state'` (2 collection errors). Restoring them left the tree clean. This only shows the tests depend on the new modules, not that each test was seen failing on its own.
3. **`./scripts/check`:** green. It ended `config check: ok, 168 unverified values` / `check: green`, and pytest reported `240 passed`.
4. **Design conformance:** pass.
   - The month path, the UTC-month split, the closed-bar rule, the refusals, the atomic write-then-rename, the index contents, the hash check on read, the half-open range and `last_n` all match DESIGN.
   - The hash really is sha256 over rows sorted by `ts`, with floats in `%.17g` and `ts` as integer UTC nanoseconds (`state.py:24-60`). Parquet round-trips the hash, which I confirmed by probe.
   - The schema is enforced at `store.py:56-72`: tz-naive `ts` is refused and `ts` is converted to ns UTC.
   - `available_until` is passed in by the caller and the store reads no clock (I-12). I-5, I-9, I-11 and I-14 hold, and no dependency was added.
5. **Forbidden touches:** none. Nothing changed under config/, meta/, DESIGN, SPEC, CLAUDE.md, pyproject or uv.lock.
6. **Commit body claims:** accurate against the code and tests. No overreach found.

**Should-fix:**
- `store.py:289-307`: if the process dies after a month file is renamed into place but before the index is written, the symbol is stuck for good. I reproduced it: both `append` and `read_range` then refuse with "a revised data point", which would raise a false health alert, and there is no recovery path. The commit body admits the crash case but not the permanent lock-out.
- No `fsync` before the rename at `store.py:167-171`, so a rewrite is atomic but not durable across a power loss.
- NaN prices are accepted (`high=nan` was stored). DESIGN is silent here, so this is worth a finding rather than a defect.

**Not proven:** atomicity under a real crash (only simulated by patching `_write_index`), and behaviour when the same symbol is written concurrently (there is no lock).

### 3b5439e (U5)

**3b5439e: mission 1, U5 gap check. Verdict: pass, nothing blocks it.**

1. **Unit and sections:** it is mission 1 U5 and claims DESIGN §5.4, §4.1 windows, §15.2, §3 `bars gaps` and §2 (I-5, I-6, I-12, I-14). This matches the U5 text in the prompt.
2. **Test-first:** pass. The only test file is the new `tests/test_gaps.py`. With the source files reverted to the parent, it goes red (`ModuleNotFoundError: discotrade.bars.gaps`). After restoring, the worktree was clean.
3. **`./scripts/check`:** green 3 times in a row. Each run ended `config check: ok, 168 unverified values` / `check: green`.
4. **Design conformance:** pass.
   - The span runs from the later of trusted_from and the first stored bar to the last stored bar. Nothing is interpolated, and each missing bar is written to `gaps.jsonl` only once; a re-run appends nothing (tested), so I-6 holds.
   - The fraction is pooled across instruments. W and T match §4.1 (`config.py` `Track.windows`), and "above" is strictly greater.
   - The event value has date, level, kind, subject and detail.
   - The limit is passed in, never hardcoded. The CLI reads it from `<config>/thresholds.toml`, and one test pins the repository's 0.01 (4 of 460 T bars runs, 5 skips), so I-10 holds.
   - The default day comes from `ctx.clock` (the injected clock, which defaults to now per §3), so I-12 holds.
   - The closure test does include the closure (2019-07-04 12:00Z, asserted not open, inside the stored span). But the "complete" bars are built with the same `expected_bars` the check uses, so the test proves consistency with the calendar, not the calendar itself.
   - `state.py` adds only the `HealthEvent` the unit needs; no health-log writer.
   - I-5, I-9, I-11 and I-14 hold, and there is no new dependency.
5. **D-002:** a genuine design gap, correctly filed instead of improvised. It also covers a case it doesn't spell out: with no stored bars at all, `fraction` is 0.0 (`gaps.py:49`), so generation is never skipped.
6. **Forbidden touches:** none. The commit touches no config, `pyproject.toml`, `meta/plan.md`, `meta/CHECKPOINT.md` or never-edit file, and its `FINDINGS.md` change is additions only.
7. **Commit body claims:** accurate against the disk; no overreach found.

**Should-fix (not blockers):**
- `gaps.py:110`: the append to `gaps.jsonl` isn't atomic. A torn last line would make the next run's `json.loads` (`gaps.py:99`) crash.
- `gaps.py:115-139`: the check scans all stored history, not history up to `day`. A replay of a past day can append gaps found after D.
- `cli.py:170`: defaulting to "UTC date minus one" can lag a trading day that has already closed (e.g. `--as-of` at 22:00Z). This is disclosed as the simplest choice.

**Not proven:** whether `expected_bars` is correct for closures (it belongs to an earlier unit), and the CLI's exit 1 on a store error (not tested).

The `/tmp/rev-3b5439e` worktree is removed and the main checkout is unchanged. An unrelated worktree, `/tmp/rev-e1c3f76`, was already there and I left it alone.

### e1c3f76 (U6)

**e1c3f76: PASS, no blocker. Two should-fix items and two coverage gaps.**

1. **Unit:** mission 1 U6, the null synthetic market. The body cites DESIGN 5.5 (interface) and 17.1 without contracts, plus 5.1, 5.4, the §3 command line, I-5 and I-12. That matches the U6 brief.
2. **Test-first:** the tests do fail without the code. With all source files reverted, `tests/test_synth.py` errors at collection with `ModuleNotFoundError: discotrade.sources`. With only `cli.py` reverted, 5 failed and 12 passed (`invalid choice: 'fetch'`). After restoring, the worktree was clean.
3. **`./scripts/check` in the worktree:** green. Last lines: `All checks passed!` / `271 passed in 12.30s` / `config check: ok, 168 unverified values` / `check: green`.
4. **Design conformance:** all of 17.1 without contracts is present:
   - normal hourly log returns with an hour-of-day pattern, and an independent open gap;
   - highs and lows enclose open and close; log-normal volume with an hour-of-day pattern;
   - the dropped-bar option and the no-short instrument (SYNL);
   - a roll schedule or `fetch_contract` raises `NotBuiltError` naming S0.2.

   Each draw kind has its own generator seeded `[seed, kind]` over one series from `trusted_from`, so a sub-range equals the cut of a longer request (tested). The statistical test uses 2019-01-07..2021-01-07 (two years). It bounds the mean at 4×SE (sample sd/√n) and lag-1 autocorrelation at 4/√n, which is 4 SE. The seeds are in the fixture TOMLs (102–106), not in the test file; this is a unit test, not a gate, so not a blocker. The `BarSource` protocol shape and `available_until(now)=now` match 5.5. `bars fetch` starts from the last stored bar (or `trusted_from`), ends at `available_until(clock.now())`, filters to closed bars, writes through the store (which re-checks closure and append-only), then runs the gap check. I-9, I-11, I-12, I-14 and I-15 hold. There is no new dependency, and `seed`, `hourly_vol`, `start_price` and `drop_fraction` are validated in `config.py:282-288`.
5. **Forbidden touches:** none. The commit touches only `src/discotrade/sources/*`, `src/discotrade/cli.py` and `tests/test_synth.py`; no `config/`, `meta/` or never-edit file.
6. **Body claims:** they match the disk. I found no overreach.

**Should-fix (I-10 / §4.2):** `src/discotrade/sources/synth.py:46-54` hardcodes the generator settings: the hour-of-day vol and volume shapes, `GAP_SCALE=0.1`, `RANGE_SCALE=0.5`, `VOLUME_MEDIAN=1000`, `VOLUME_SIGMA=0.5`. §4.2 puts "the keys section 17 names" in the `[source]` table, and 17.1 names the hour-of-day pattern and the gap. These numbers move synthetic results (high/low ranges, gaps), and later gates replay on those results. The body records them as "DESIGN silent", but they belong in `[source]` or need a filed finding.

**Should-fix (small):** `cli.py` `_bars_fetch` builds a new `source_for(...)` for every instrument, and `synth.py` regenerates the whole series from `trusted_from` on every fetch. Both are only performance costs, not wrong results.

**Not proven by any test:**
- the hour-of-day volatility pattern and the volume distribution or its pattern;
- that the gap is independent of the return;
- that the "missing bars are exactly the dropped ones" test is independent, since `dropped()` shares `_series()` with `fetch()`.

The worktree is removed, and the main checkout is unchanged and clean.
