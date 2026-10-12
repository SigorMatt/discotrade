# REVIEW-2 — cold review of mission 2 (roadmap step S0.2)

Base: a73f0bf (`review: mission 1`, the last `review:` commit). Range
`a73f0bf..origin/main` (tip 7d8bbd0). Unit commits reviewed, one sub-agent
each in its own worktree: f3f8c2d (U1), 8e423c1 (U2), cb9c21d (U3), 61e1c59
(U4), 5995b92 (U5), a5245d0 (U6). Read myself for forbidden edits only:
1151e55 (the architect's kit: `meta/BUILDER-2-PROMPT.md`, `meta/decisions/`,
`meta/ROADMAP.md`, `meta/BACKLOG.md`, `KIT.md`, not a builder commit),
87d4a23 (`plan:`), the seven `meta:` checkpoint commits, and 0cf4db1
(`report:`). None of the builder's commits touches a file `CLAUDE.md`
reserves; `meta/plan.md` and `meta/CHECKPOINT.md` are changed only by the
orchestrator's `plan:` and `meta:` commits. `git diff a73f0bf origin/main --
config/ tests/fixtures/config_frozen.json` is empty.

## Gate

not a closing mission

(For the record, acceptance checks run at the tip: `./scripts/gate M0`
printed `G0.2 FAIL no gate test ...`, `G0.3 FAIL ...`, `G0.4 FAIL ...`,
`gate M0: FAIL`; `./scripts/gate M0 G0.3` ended `gate M0 G0.3: FAIL` with no
`gate M0:` line. Both are what the brief expects.)

## Blockers

None.

## Should-fix

1. **The reader does not refuse a month file the index does not list
   (decision 5).** Decision 5 says "the reader does not repair: it refuses
   both cases", and its cases include a month file "that the index does not
   list". `BarStore.read_range` and `last_n` (`src/discotrade/bars/store.py`,
   about lines 256–300) iterate only over `self._months(symbol)`, the
   indexed months, so an unlisted file is skipped without an error. That
   file may be an interrupted append into a new month, or a revised file for
   a past month. The writer and `bars fetch` do detect it through `recover`.
   No test covers the reader on an unlisted file. FINAL-REPORT-2 says "the
   reader's error tells the two cases apart", which is proven only for a
   listed file. Direction: refuse, or report, an unlisted month file on
   read, and test it.
2. **`bars fetch` still defaults its gap-check day to the UTC date of
   `--as-of` minus one, not §16.1's `D`** (`src/discotrade/cli.py`,
   `_gap_day`). Decision 3 sets the default `D` only for `bars gaps`, so this
   does not break the brief, and FINAL-REPORT-2 discloses it. For a source
   with `available_until(now) = now - 24 h` (the vendor), that day can still
   be open at the `--as-of` instant. A later replay of the same day could
   then append to `gaps.jsonl` what the original run did not, which is
   against the intent of decision 3 and I-6/I-12. Direction: use the same
   §16.1 `D` as `bars gaps`, or file a finding if the design means
   otherwise.

## Notes

- U1 test-first: two gate cases pass at the parent too. They are the
  `gaps.jsonl` "earlier lines byte-identical" check (the old plain append
  also kept them) and one of the four `bars gaps` default-day cases. Every
  other U1 gate item has a test that goes red on revert, including the case
  where the UTC date and the trading date differ.
- U1: `recover` reads and hashes every month file of an instrument on every
  append, and `bars fetch` runs it twice per instrument. This is a cost
  only, not wrong.
- U2: the case `"1"` -> `1` was already caught by the old `==`, so it is a
  regression test only. The "package's own location unchanged" check
  asserts only that `cli.REPO_ROOT` is unchanged. A test marked `gate`
  outside `tests/gates/` with no milestone marker is not refused; decision 9
  does not ask for that.
- U3: the hash anchors were recomputed independently at b86601c (SYNA with
  `roll_schedule = "none"`) and match. The adjacent-contract difference is
  checked to 1e-9, not exactly; the continuous series is bit-exact. The
  hour-of-day and open-gap statistics run on SYNB, not SYNA; the brief does
  not clearly tie those items to SYNA. Only `roll_day` is tested for
  "contract key without a schedule". The 120-day roll look-ahead is
  untested on sparse calendars.
- U4: "within 24 bars" is read as bars u-24 to u-1 of the stored continuous
  series, and the body states that reading. If `update_rolls` fails after
  the bars are written, `bars fetch` exits 1 and the next fetch records the
  roll; the gap is then measured from a later source state, which is a
  vendor-only concern.
- U5: `crypto.py` (about lines 65 and 86) uses real `httpx` when no
  transport is injected. Tests stay offline only because each one injects
  `MockTransport` or patches `source_for`; nothing in `tests/conftest.py`
  blocks sockets as a backstop for I-11. `vendor.py` (about line 128)
  passes the key to the client unstripped, while the presence check strips
  it. `uv.lock` gains only databento and its transitive packages, under
  `extra == 'vendor'` (decision 11).
- U6: the marginal-spread warning (`src/discotrade/config.py`, about line
  669) counts every hour that touches the main session, so hour 09 counts,
  while the spread rule treats the 09:00 bar as off-session. The two
  disagree, though erring toward a warning is safe, and the body names it as
  a choice. `doctor --live spreads --days` is not range-checked (0 becomes
  20; a negative value gives an empty-sample error), while `spreads measure`
  refuses values below 1. `spreads.py` (about line 301) uses `vendor.py`'s
  private `_guard`. No test hits an even-count median.
- FINAL-REPORT-2 says "Base 1151e55" (the kit commit). That is the
  mission's start, not the review base; the two differ only by the kit.
  Its NOT PROVEN section matches what the sub-agents found, apart from
  should-fix 1 above.
- `./scripts/check` was green at every unit commit (315, then 479 and 532
  tests at U1, U5 and U6; U2–U4 green, counts not recorded).
- hands: when several sub-agents run in parallel, each one sees the
  others' `/tmp/rv-*` worktrees registered on the repository. The protocol
  does not say where the worktrees go or that they must be removed; all
  were removed here, and `git worktree prune` left only the main tree.

## Per-commit verdicts

**f3f8c2d (U1)**

sha f3f8c2d (mission 2, U1). Verdict: pass. No blocker; two should-fix items below.
1. **Unit:** U1, store and gap-check repairs. It claims DESIGN §5.1, §5.2, §5.4, §15.2 and §16.1, decisions 2–6 and 16, I-5, I-6 and I-12. That matches the brief, which adds §16.1 only through decision 3.
2. **Test-first: red as expected.** With the three src files reverted, 42 of 95 tests in test_bar_store, test_gaps and test_synth fail. Every gate item has a failing test except two that pass at the parent: the gaps.jsonl "earlier lines byte-identical" test (the old code's plain append already kept them) and the default-day case 2019-07-12T20:59 → 07-11 (the old rule also gave that day). The other three default-day cases fail, including 2019-07-11T23:00, where the UTC date and the trading date differ.
3. **`./scripts/check`: green.** Last lines: "All checks passed!", "315 passed in 70.70s", "config check: ok, 168 unverified values", "check: green".
4. **Design: conforms.** Each gate item has a test asserting at least what the brief says, and the code matches decisions 2–6:
   - fsync of the new file comes right before each of the 3 renames, then fsync of its directory; the test patches `os.fsync` and `os.replace`.
   - The window counts run to the end of D, from the later of the window start and `trusted_from`; gaps.jsonl keeps the first definition, bounded at D.
   - `day_end` agrees with `trading_date`.
   No invariant problem found: no network, secret or wall-clock read (the default day uses `ctx.clock`, the notice date uses `available_until`), no market or venue named under src/, numpy is an existing dependency, and nothing is written into the repository.
5. **Forbidden touches: none.** The commit touches only 3 src files and 3 test files, and its body lists all six. No frozen config, no meta/plan.md or meta/CHECKPOINT.md, no file CLAUDE.md reserves.

Should-fix:
- `src/discotrade/bars/store.py` (`read_range`, `_months`): the reader only reads the months the index lists. A month file the index does not list (a crash while appending to a new month) is skipped without an error, while decision 5 says the reader refuses both cases. No test covers this; the reader's error is tested only for a listed file.
- `src/discotrade/cli.py:156` (`_gap_day`): `bars fetch` still defaults to the UTC date of --as-of minus one day, not §16.1's D. That day can be unclosed for a delayed source, so a later replay of it could append more to gaps.jsonl than the original run. The commit body says this was a deliberate choice.

Minor: `recover` reads and hashes every month file of an instrument on every append, and `bars fetch` runs it twice per instrument.

NOT proven: the reader's behaviour for an unlisted month file, a source that lags behind `now` in the default-day logic (only synthetic sources are tested), and directory fsync on non-Linux systems.

**8e423c1 (U2)**

I reviewed commit 8e423c1 and would accept it: I found no blocker and no should-fix defect.

1. **Unit:** this is U2 of mission 2 (REVIEW-1 should-fix 3, 6 and 7; decisions 7, 8 and 9). It claims DESIGN §3, §4.3, §18.1 and §18.2, plus I-10 and I-14. That matches the U2 text in BUILDER-2-PROMPT.
2. **Test-first: red as expected, then restored.**
   - With `cli.py`, `config.py` and `scripts/gate` reverted to the parent, 24 of 110 tests failed. That covers every I-14, blank-state, type-strictness and one-item gate test.
   - I treated `tests/conftest.py` as product code, because it is where decision 9's collection check lives. Reverting it as well made all 15 bad-marker collection cases fail (19 of 31 failed in `test_gate_script.py`).
   - One gate case never went red: `"1"` to `1`. The old `==` already caught it, so it is a no-op regression test, which is acceptable.
3. **`./scripts/check` at the commit:** green, ending `config check: ok, 168 unverified values` and `check: green`.
4. **Design conformance: pass.**
   - **I-14:** a state path is refused when it, or any directory above it, holds both `pyproject.toml` and `src/discotrade/`. The old check against the package's own repository stays. `--state` given as `""`, `"  "` or a tab, and `DISCOTRADE_STATE` given as `""` or `" "`, all exit 2.
   - **Type-strict comparison:** `same_value` compares `type(a) is type(b)`, so a bool never equals an int and 5 never equals 5.0. Arrays and tables are compared element by element.
   - **Dates:** dates are now stored typed as `{"date": iso}`. The calendar's dates are TOML strings, so no frozen entry changes.
   - **`scripts/gate`:** a one-item run prints only `gate M<m> <item>: …`.
   - **Collection check:** the conftest hook runs before `-m` deselection, so it works under `-m "not gate"` too.
   - **Other invariants:** I-9, I-10, I-11 and I-12 are untouched. The new tests use no network or secret.
5. **Forbidden touches: clean.** The commit changes exactly the 7 files its body lists, all inside the brief's file list. Nothing under `config/`, `tests/fixtures/config_frozen.json`, `meta/plan.md`, `meta/CHECKPOINT.md`, or any document builders must not edit.
6. **Not proven:**
   - The "package's own location unchanged" check only asserts that `cli.REPO_ROOT` is the same object before and after. No test installs the package outside the repository.
   - A test marked `gate` outside `tests/gates/` with no milestone marker is not refused. Decision 9 does not require that, so this is a note, not a defect.

**cb9c21d (U3)**

cb9c21d (mission 2, unit U3): **PASS. I found no blocker or should-fix defect.**
1. **Unit:** U3 claims DESIGN §4.2, §5.1, §5.5 and §17.1, decision 2026-10-12 item 10, REVIEW-1 should-fix 2, and I-9, I-10, I-12. It is the synthetic market with quarterly contracts, the `contract` column, `fetch_contract`, and the generator settings read from `[source]`.
2. **Test-first: red.** I reverted `config.py`, `synth.py` and the six `tests/fixtures/config/instruments/SYN*.toml` (treated as product inputs, not tests). `test_synth.py` + `test_config.py` then gave 45 failed, 3 errors, 84 passed. Every gate item has a failing test except two that the old code already met, as expected: the before/after hash test and the open gap being uncorrelated with the return. After restoring, all 132 pass.
3. **`./scripts/check` at cb9c21d: green.** Last lines: `config check: ok, 168 unverified values` / `check: green`. I ran it once.
4. **Design: pass.** All seven decision-10 keys and the contract keys are required from `[source]`, and each missing key is refused by its dotted name. The only literals left in `synth.py` are shape/structure ones (24 hours, the cos form, `3600.0`, the seed-kind indexes), plus `_LOOKAHEAD = 120 days`, which can only move bars on a sparse calendar (the commit body says so).
   - **Hashes are honest:** I recomputed all six at b86601c, SYNA with `roll_schedule="none"`, and got the exact counts and hashes written in the test.
   - **Rolls:** the contract column changes exactly at the 8 scheduled instants; there are ≥24 common bars each side of every roll; continuous = underlying + current constant bit for bit; `bars fetch` on test_mixed stores SYNA with SYNA-2019-03 then -06.
   - **I-9, I-12:** clean (no market names, no wall clock in `synth.py`).
5. **Forbidden touches: none.** No protected file, no `meta/plan.md` or `meta/CHECKPOINT.md`, no `config/`, and `config_frozen.json` is unchanged. The fixture records are outside the frozen map under decision 10. The commit body lists all 10 files.
6. **Tests that assert less than the gate (nits):**
   - The adjacent-contract difference is checked within 1e-9, not "exactly". This is a float effect; the continuous-series check is bit-exact.
   - The hour-of-day and open-gap tests use SYNB with its own seed, not SYNA. The gate does not clearly name SYNA for those items.
   - Only `roll_day` is tested for "contract key refused without a schedule".

NOT proven: other calendars than the fixtures'; the 120-day look-ahead holding on sparse calendars.

**61e1c59 (U4)**

Review of 61e1c59 (mission 2, U4: rolls and the adjusted series). Verdict: approve, with no blocker and no should-fix.

1. **Unit:** This is U4. It claims DESIGN §5.6, §5.5 (`bars fetch` now records rolls), §15.2 (the notice shape), decision 16, and I-5, I-6 and I-12. That matches the gate text in BUILDER-2-PROMPT.md.
2. **Test-first: red, as expected.** With `rolls.py` deleted and `cli.py` at the parent, `tests/test_rolls.py` fails to collect (`ModuleNotFoundError: No module named 'discotrade.rolls'`). With only `cli.py` reverted, the result is "9 failed, 5 passed in 34.56s". The worktree was restored to the commit afterwards.
3. **`./scripts/check` at the commit: green.** The last lines are "config check: ok, 168 unverified values" and "check: green".
4. **Design conformance: pass.**
   - A roll is recorded wherever the contract differs from the previous stored bar's.
   - Detection runs over stored bars starting at the last recorded roll, so a roll at the first bar of a fetch is compared with the last stored bar, and a recorded roll is never measured again (I-6).
   - The gap is `close_new(v) - close_old(v)`, with `v` searched over bars u-24 to u-1. That is the commit's reading of "within 24 bars", and it is stated in the body.
   - When there is no common bar, the record carries `open(u) - close(u-1)` and `estimated=true`, and a §15.2-shaped notice is returned. Its date comes from `--day` or the injected clock, never the wall clock (I-12).
   - The file is append-only through `write_atomic`, and earlier lines stay byte-identical (I-5).
   - `adjust()` adds a gap only to bars strictly before the roll bar, and only for rolls at or before t. So a bar at the roll itself is not adjusted, the last bar is raw, the sign is new minus old, and volume is untouched.
   - I-9 (no market named), I-11, I-12 and I-14 are clean.
   - Every gate item has a test asserting at least what it says: at least 200 bars over at least 700 days to 1e-9; a store ending at t against one a year later (compared at 3 values of t); no common bar giving an estimated gap and a notice; a re-fetch appending nothing; two incremental fetches giving the same file as one.
5. **Forbidden touches: none.** The commit changes only `src/discotrade/rolls.py`, `src/discotrade/cli.py` and `tests/test_rolls.py`, all listed in the body. It touches no frozen config, no file reserved to the owner, and neither `meta/plan.md` nor `meta/CHECKPOINT.md`.

**Not proven:**
- Gap measurement against a real `fetch_contract`: only the synthetic source and a test wrapper that hides bars were exercised. A real adapter is U5's work and live check L1.
- A gap is measured once from whatever the source returns at fetch time. If bars were written but the roll step then failed, the next run would measure from a later source state. With the synthetic source that makes no difference; with a vendor it could, and that is accepted by design.

Minor, not rated: `cli.py`, around line 322. If `update_rolls` fails for one instrument (for example a `fetch_contract` error), `bars fetch` exits 1 even though the bars were already written. The next fetch records the missing rolls, so nothing is lost.

**5995b92 (U5)**

Commit 5995b92 (mission 2, U5) passes all five checks; I found no blockers or should-fix defects.

1. **Unit:** mission 2 U5, vendor and crypto adapters plus live check L1 offline. It claims DESIGN §5.5, §5.1, §3 and §19.3 L1, decisions 11, 12 and 15, and I-9, I-11, I-13. Pass.
2. **Test-first:** red, as expected. With the source reverted (pyproject.toml and uv.lock left as they are), test_vendor, test_crypto and test_doctor fail at collection (SourceError and the vendor module are missing). test_config and test_synth have 2 failures (CRYA.toml's base_url and market are unknown keys; 130 other tests pass). After restoring the commit: pass.
3. **`./scripts/check` at the commit:** green. Last lines: "All checks passed!", "479 passed in 75.80s", "config check: ok, 168 unverified values", "check: green".
4. **Design conformance:** pass.
   - **Vendor:** meets every listed point. Two edge cases are tested: a cost of exactly 5.0 fetches and 5.01 refuses. Redacted errors are unchained.
   - **Doctor:** `doctor --live vendor` without the key exits 1 and makes no call. Plain doctor and other names exit 2 naming S5.1. `--live spreads` exits 2 as "not built yet", which the body discloses; U6 must make it exit 1 without the key (decision 15).
   - **Crypto:** MockTransport, closed hourly bars, contract equals symbol, 11 malformed replies refused, base_url and market from [source], test_only record only under tests/fixtures, available_until = now.
   - **I-9:** src/ is clean. The real endpoint and market are named only in tests/fixtures/config/instruments/CRYA.toml, which decision 12 allows.
   - **I-12:** the only wall-clock read in src/ is clock.py, the injected clock that predates this commit.
   - **Dependencies:** uv.lock gains only databento and its transitive packages, under `extra == 'vendor'`.
   - **Files the brief did not list:** base.py (SourceError, bars_frame), config.py (crypto base_url/market, required by decision 12), test_synth.py and test_config.py (behaviour they tested changed). All are justified and named in the body.
   - **Gate items:** each has a test asserting at least what it says.
5. **Forbidden touches:** none. Nothing changed under meta/ or config/, in config_frozen.json, or in any file builders must not edit. The body lists all 19 changed files.

**NOT PROVEN:** that the real databento 0.87.0 client and service match the shapes the fake implements (L1), and the real crypto endpoint's request/reply shape and its base_url and market. The body declares both.

**Minor (nit):**
- src/discotrade/sources/crypto.py:65,86: with no transport passed, the adapter uses real httpx. The crypto tests stay offline only because they inject MockTransport or monkeypatch `source_for`, and nothing in tests/conftest.py blocks sockets as a backstop for I-11.
- src/discotrade/sources/vendor.py:128: the key is passed to the client unstripped, though the presence check strips it.

**a5245d0 (U6)**

a5245d0: **PASS, nothing blocking.** Two nits below.

1. **Unit:** mission 2 U6, spread tables, `spreads measure` and L2 offline. It claims DESIGN §5.7, §4.3 and §19.3 L2, decisions 13–15, and I-10 and I-13.
2. **Test-first: OK.** With cli.py, config.py and doctor.py at the parent and spreads.py deleted, `tests/test_spreads.py` goes red at collection (`ImportError: cannot import name 'load_spread_table'`). Restored afterwards.
3. **`./scripts/check`: green.** "532 passed in 81.27s", then "config check: ok, 168 unverified values", then "check: green".
4. **Design: conforms, and every gate item has a test.**
   - The rule and the measurement are tested across the 2019-03-10 New York change. Measure uses the median per local hour and refuses to overwrite. An open hour with no quote errors and nothing is written. Hour 17 (the daily break) is filled and listed.
   - Config check warns with exit 0. The code names no instrument (I-9). The frozen rule covers `config/spreads`. L2 without the key exits 1 with no call.
   - `checked` comes from the injected clock (I-12). The key is redacted (I-13).
   - Writing to `<config>/spreads` by default is right: decision 13 says so, and the file is owner-committed frozen config, not run state, so I-14 does not apply.
   - Using vendor.py's private `_guard` (`src/discotrade/spreads.py:301`) is acceptable but brittle; a public name would be cleaner.
   - No DST, hour-mapping, median or tick-rounding bug found. An even count averages the two middle values, which is a plain median but no test hits it.
5. **Forbidden touches: none.** No protected file, meta plan/checkpoint, `config/` value or `config_frozen.json` entry is touched. The body lists all 6 files.

**NOT PROVEN:** that the vendor's real quote calls match the fake (bbo-1m, `get_cost`/`get_range`, `ts_recv`/`bid_px_00`/`ask_px_00`). The commit body says so too.

**Nits (should-fix at most):**
- `src/discotrade/config.py:669`: the warning counts any hour that touches the main session, so hour 09 counts. The spread rule (`in_main_session`) treats the 09:00 bar as off-session. The two definitions disagree; erring towards a warning is the safe side, and the commit flags it as a choice where DESIGN is silent.
- `src/discotrade/doctor.py:152`: `--days` is not checked. 0 silently becomes 20, and a negative value gives an empty-sample error, while `spreads measure` refuses anything below 1.
