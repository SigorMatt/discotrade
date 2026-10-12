VERDICT: mission 5 finished

# FINAL REPORT — mission 5 (roadmap step S0.4, closes M0)

Builder prompt: `meta/BUILDER-5-PROMPT.md`. Base 3854c96. This mission
builds step S0.4 and closes milestone M0. It takes REVIEW-4 should-fix 1,
REVIEW-4's note on `gaps.py` and `rolls.py`, and REVIEW-3's three notes
carried to S0.4; then it adds the independent calculation, the cheating
strategy and the gate tests of G0.1 to G0.4. It binds
`meta/decisions/decisions-2026-10-12.md` (cited below as "decision N"; items
34 to 40 are new) and the architect's decision on finding D-004, recorded
in `meta/plan.md` under "Decision on D-004" and to be carried as decision
41.

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan files | 9d2d781 | plan: mission 5 plan (S0.4, closes M0) |
| U1 store readers, index-first callers | 8e8215c | bars: every public BarStore name classified; index-first callers refuse |
| U2 `trusted_from`, roll records, cost labels | 8d27fe1 | rolls: no bar before trusted_from; roll records match on contracts; cost labels |
| U3 independent calculation | 3be4e9b | gates: independent calculation for G0.1, checked against hand values |
| U4 calc fix (D-004) | de9fc09 | gates: independent calc max_drawdown counts the starting 0 as a peak |
| U4 gate G0.1 | 2881ee0 | gates: G0.1 reference strategies against the independent calculation |
| U5 gate G0.2 | 2c64e8d | gates: G0.2 cheating strategy cannot gain on test_mixed |
| U6 gates G0.3, G0.4 | 80ffc78 | gates: G0.3 store, gaps, adjusted series, roll cost; G0.4 config and I-9 |
| U6 gate run | 62edb14 | gate M0 run at this tip (output below; recorded by the meta commit 55c3f24) |
| U7 final report | this commit | report: mission 5 final report |

The `meta:` commits between units are checkpoint, journal, plan and
findings bookkeeping. Each unit commit's body lists its files, the choices
made where DESIGN and the decisions are silent, and the wrong changes made
and reverted; those bodies are the authority for this summary.

Product code changed in U1 (`bars/store.py`: new public reader
`BarStore.index_entry`; `bars/gaps.py` and `rolls.py` read the index entry
through it) and U2 (`rolls.py`: `trusted_start`, roll detection and the gap
measurement start at `trusted_from`, `adjusted_as_of` takes the `Instrument`
record; `backtest.py`: roll records keyed on `(ts, old, new)`; `cli.py`:
the plain-output cost labels). U3 to U6 changed no product code: no gate
test found a defect in it, and the D-004 mismatch was settled in the
independent calculation. `src/discotrade/metrics.py` did not change in this
mission.

Assertions of existing tests that changed, each named in its unit's body:
- U2: the `adjusted_as_of` call sites of `tests/test_rolls.py` pass
  `inst("SYNA")` instead of `"SYNA"` (signature change) and assert nothing
  different. No existing test asserted the old plain-output labels.
- U3 (outside its brief, needed by `./scripts/check`):
  `tests/test_gate_script.py::test_m0_without_gate_tests_fails` asserted
  that M0 has no gate test, which U3 ended; it now asserts the same rule on
  M1 (no gate test, `gate M1: FAIL`, one FAIL line per item).
- U5: `tests/test_gate_script.py::test_one_item_without_gate_tests_fails`
  used G0.2 as its item with no gate test; it now uses M1 G1.2 (and asserts
  no `test_g1_2_*.py` exists), with the same four assertions.
- de9fc09: one hand value of the independent calculation's self-test (the
  two-instrument scenario whose running sum falls from a first-day loss)
  changed from 0.001 to `-sum(d1)`, citing the D-004 decision.

`git diff 3854c96 62edb14 -- config/ tests/fixtures/config_frozen.json
tests/fixtures/config/` is empty: no frozen value and no fixture record
changed. The one new fixture is `tests/fixtures/strategies/cheat_lookahead.py`
(U5).

## Gate

`./scripts/gate M0` at 62edb14, pasted verbatim from the U6 gate run
(`meta/drafts/gate-M0.txt`). Every commit after 62edb14 (55c3f24 and this
one) touches only `meta/`.

```
sha: 62edb142cff245f80153b2f145c9c8b7b160870f
git status --short: clean; ## main...origin/main (up to date)

./scripts/check run 1: rc=0, wall 365s, 936 passed, 65 deselected in 364.35s; ruff All checks passed!; config check: ok, 168 unverified values; check: green
./scripts/check run 2: rc=0, wall 364s, 936 passed, 65 deselected in 363.35s; ruff All checks passed!; config check: ok, 168 unverified values; check: green
./scripts/check run 3: rc=0, wall 361s, 936 passed, 65 deselected in 360.72s; ruff All checks passed!; config check: ok, 168 unverified values; check: green

./scripts/gate M0: exit status 0, wall 343s
--- stdout verbatim ---
G0.1 PASS 41 passed in 52.92s
G0.2 PASS 7 passed in 117.43s (0:01:57)
G0.3 PASS 13 passed in 170.18s (0:02:50)
G0.4 PASS 4 passed in 0.24s
gate M0: PASS
--- stderr: (empty) ---
```

Each item finished well under 15 minutes. Every gate test carries the
markers `gate` and `gate_m0`, writes state only under a pytest temporary
directory, runs `discotrade` in-process through `discotrade.cli.main`, and
launches no subprocess; the synthetic seeds it relies on (SYNA 101, SYNL
105, SYNX 106) are written in the test file and checked against the fixture
records.

### G0.1 — `tests/gates/test_g0_1_calc_self.py`, `tests/gates/test_g0_1_reference.py`

DESIGN §18.3: the three reference strategies, run on `test_mixed` (one
instrument that rolls, one that cannot be shorted, one with a proportional
fee, with dropped bars), give per-bar gross and net at 1x and 2x, every
cost component and every §8 metric equal, to 1e-12, to an independent
calculation that imports nothing from `discotrade` (a test checks its
imports), written by a sub-agent of its own told not to open the modules
it checks.

- `test_g0_1_calc_self.py` (19 tests): an `ast` read of
  `tests/gates/independent_calc.py` finds no import of `discotrade` or
  `importlib` and no module outside the standard library, `numpy`,
  `pandas`, `pyarrow` (decision 39). On hand-built stores of 5 to 30 bars,
  the calculation equals hand values, derived in comments, to 1e-12: a
  carried roll and a flat roll, a missing bar, bars either side of a daily
  break, a pre-`trusted_from` bar, a non-shortable instrument clipping,
  `fee_bps`, the spread table by local hour with the half-tick floor, main
  and off session, `sigma` with 0, 1, 2 and 27 returns, two calendars in
  one subject, the §6.2 slice, the error cases of decisions 22 and 37,
  Sharpe not a number by decision 30, and `max_drawdown` with a first-day
  loss under the D-004 decision.
- `test_g0_1_reference.py` (22 tests): `bars fetch` on `test_mixed` at
  2019-08-05T00:00Z into a temporary state directory; the window
  2019-06-03 to 2019-07-31 (at least eight weeks) is asserted to hold a
  SYNA roll with its roll record, the `synth_week` closure of 2019-07-03 to
  2019-07-04, a negative raw SYNL target clipped to 0, SYNX's proportional
  fee on traded bars, and dropped bars of each instrument (from the
  generator). For `reference/trend_ma.py`, `reference/zscore_reversal.py`
  and `reference/hour_of_day.py`, discotrade's evaluation (the module, and
  `backtest --json` in-process) equals the independent calculation under
  decision 39's equality: every per-bar field and the row count of every
  instrument, both daily series, every §8 metric, and the cost totals by
  component per subject and per instrument; the `--json` figures equal the
  module's.

### G0.2 — `tests/gates/test_g0_2_cheating.py` (with `tests/fixtures/strategies/cheat_lookahead.py`)

DESIGN §18.3: a cheating strategy (keeps references to earlier frames,
inspects the index, tries to reach later rows) cannot gain: its positions
pass truncation invariance, and its score on a window is the same whether
or not later bars exist in the store.

- The text passes discotrade's loader with `config/thresholds.toml`; an
  `ast` walk finds no name, argument or attribute beginning with an
  underscore and none of the imports, names or attributes §12.1 rejects,
  and finds the attributes `iloc`, `loc`, `values`, `to_numpy`, `base`,
  `attrs`, `index` (decision 40).
- Called directly, the text goes long (short) when a later higher (lower)
  close is reachable through the `base` of an `iloc` view, through `attrs`,
  or through an earlier kept frame.
- On `test_mixed`, window 2019-06-03 to 2019-07-01 (29 days, holding
  SYNA's 2019-06-14 roll): for SYNA, SYNL and SYNX, per-bar rows (`p`
  included) up to `t` are exactly equal between a store ending at `t` and
  one ending 2020-07-15, for at least ten window bars `t` each, including
  the window's first and last bars and, for SYNA, the bars before, at and
  after the roll. Per-bar rows and every metric are identical, per
  instrument and for the three-leg subject, between a store ending at the
  window's last bar and the long store.
- Control: the same text, given at each bar a frame that also holds the
  next bar's close, gives different `p` on all three instruments, a higher
  gross sum on all three, and a higher `total_return` on SYNA, SYNX and the
  three-leg subject.

### G0.3 — `tests/gates/test_g0_3_store.py` (13 tests)

DESIGN §18.3: the store refuses a bar that is not closed and a bar not
later than the last; old rows are unchanged by an append; the gap check
finds exactly the dropped bars and none across the daily break, the weekend
or a closure; the adjusted synthetic series as of each bar equals the
gap-free underlying plus the current contract's constant (§17.1); a carried
position pays the roll cost and a flat one does not.

- For SYNA, SYNL and SYNX, `BarStore.append` refuses a bar not closed at the
  synthetic source's `available_until` of a fixed clock instant (and takes
  it at its close), and a batch whose first bar equals or precedes the last
  stored bar (five cases); each refusal leaves every file of the state
  directory byte-identical.
- After a second fetch, every old row of every month file of the three
  instruments has the same content hash and values as before.
- From a fetch at 2019-07-13T00:00Z, `gaps.jsonl` holds exactly the bars
  `SynthSource.dropped` reports (taken from the generator, not the gap
  check); on SYNA and SYNL (`synth_week`) no reported bar falls in a daily
  break, a weekend or the closure, and the range contains weekday breaks,
  weekends and all 29 hours of the 2019-07-03/04 closure.
- For SYNA over 2019-01-07 to 2019-07-12 (rolls 2019-03-14 and 2019-06-14),
  `adjusted_as_of` at every stored bar equals, for every earlier bar, the
  generator's underlying plus the constant of the contract current at that
  bar, four prices to 1e-9 relative, volume unadjusted.
- Holding 1.0 and -0.5 through the 2019-06-14 roll, the roll bar's `roll`
  and `cost` equal `2 * |h(u-1)| * c(u)` to 1e-12, with `c(u)` computed in
  the test from the fixture TOML, the SYNA spread table, the stored bars and
  the roll records; no other bar pays a roll; holding 0 pays none.

### G0.4 — `tests/gates/test_g0_4_config.py` (4 tests)

DESIGN §18.3: `discotrade config check` passes on the `hourly` track with
its eight instruments, and no file under `src/` contains, as a whole word,
an instrument symbol, contract root or venue named in `config/` (I-9).

- `discotrade config check --track hourly` on `config/` exits 0, says
  `track hourly: 8 instruments` and lists exactly the eight instruments of
  `config/tracks/hourly.toml`.
- Symbols, contract roots (the part of each `[source]` `symbol` before its
  first `.`) and venues are collected from every TOML file under `config/`,
  not from a list in the test; none appears as a whole word
  (case-insensitive) in any file under `src/`. A control finds a name
  planted in a copy; U6 also saw the test fail with `# M2K` and `comex`
  added to `src/discotrade/clock.py` (made and reverted).

## Mismatches U4 found and how they were settled

One mismatch; no other.

- `max_drawdown`, `reference/zscore_reversal.py` on `test_mixed`, window
  2019-06-03 to 2019-07-31 (module and `backtest --json`): discotrade
  0.22244801873145578, the independent calculation 0.21593456441431036.
  The daily series starts at -0.006513454317145457 and the running sum
  never returns above it. DESIGN §8 says only "the largest peak-to-trough
  fall of the running sum of `d`" and no decision settled whether the
  starting 0 is a peak, so U4 stopped and filed finding D-004; the mission
  asked `VERDICT: question`. The phone architect answered: the running sum
  starts at 0 before the first day and that 0 counts as a peak (every
  subject starts flat, so a first-day loss is a drawdown); to be carried as
  decision 41. `src/discotrade/metrics.py` already did this and did not
  change. A fresh sub-agent under U3's rules and words, working from that
  decision and DESIGN §8 only, fixed `independent_calc.py` and added a
  hand-value self-test (seen to fail before the fix) at de9fc09. U4 then
  landed at 2881ee0 with every comparison equal for all three strategies.

## What the tests prove

Taken from each unit's commit body; on the cases named there and above.

- U1: `find_missing`, `check_gaps`, `update_rolls` and `adjusted_as_of`
  refuse with decision 18's interrupted-append error when the instrument has
  no index entry and its directory holds unlisted month files passing
  decision 5's test with `r = 0`, and with the revised-data-point error when
  one does not; with no month file they report no stored bar; after a crash
  before the first index write, a second `bars fetch` recovers and the four
  return what they return on a clean store. The `BarStore` classification
  test enumerates every public name of the class through its MRO and the
  public instance attributes, and fails for an added public property that
  reads bars and for an added public method (both made and reverted). On
  the parent, `check_gaps` alone already refused.
- U2: with bars written before a test-local `trusted_from`, the roll gap
  measurement asks `fetch_contract` for nothing before it and estimates when
  the only common bars lie before it; a contract change across
  `trusted_from` is not recorded as a roll on either path; `adjusted_as_of`
  for five starts and three `t` returns no earlier bar; `evaluate` on a
  store with pre-trusted bars equals `evaluate` on the trusted bars only
  (rows, slices, `sigma`), for three `trusted_from` dates. A roll record
  with the right `ts` and a wrong old or new contract is a missing record
  (`evaluate` error, `backtest` exit 1). The plain output labels the
  subject's cost line as divided by `N` and each instrument line as its
  undivided sum, with the `--json` figures unchanged.
- U3, calc fix, U4: the G0.1 statements above. U4 saw its test fail on
  four wrong changes in product code: `sigma` with `ddof=0` (15 of 22),
  gross without the roll gap in `Ca(u-1)` (8 of 22), the spread floor
  raised to a full tick (15 of 22), `max_drawdown` without the leading 0
  (2 of 22).
- U5: the G0.2 statements above, seen to fail on a slice ending one bar
  late and on a slice that is an `iloc` view of a frame holding later rows
  (both made and reverted).
- U6: the G0.3 and G0.4 statements above; G0.3 also seen to fail (6 of 13)
  under a roll cost factor of 1, a store accepting a bar equal to the last,
  and an adjustment adding a gap to the roll bar itself (made and reverted).
- The gate run at 62edb14: `./scripts/check` green three times (936
  passed), `./scripts/gate M0` prints `G0.1` to `G0.4 PASS` and `gate M0:
  PASS`, exit 0, in 343 s.

## NOT PROVEN

The calculation's independence:
- The independent calculation's authors (U3's sub-agent and the de9fc09
  fix's) did not open `src/discotrade/` or the named tests, as their commit
  bodies state; that is their statement, not something a test checks.
  They read DESIGN and the decisions, which were written while the code
  existed and partly in answer to reviews of it, so a misreading shared by
  the text and the code would be shared by both sides. The D-004 answer
  itself was settled after both readings were seen.
- The calculation shares with the code it checks the synthetic bars `bars
  fetch` wrote, the roll records `bars fetch` wrote, and the strategy
  callable obtained with discotrade's loader; a defect in the synthetic
  source, the store, roll detection or the loader is common to both sides
  and G0.1 cannot see it.
- The U3 author learned the roll record's keys (`ts`, `old`, `new`, `gap`)
  and the bar schema from the files `bars fetch` wrote, which DESIGN does
  not name.
- Where DESIGN is silent the U3 author chose (documented in the module):
  `trusted_from` as midnight UTC of its date, the main-session rule, the
  trading date rule; agreement on these with the code is shown on
  `test_mixed` only.

G0.1:
- Shown on one fixture track (`test_mixed`) and one window (2019-06-03 to
  2019-07-31), for the three reference strategies.
- Finding D-005: a roll cost on `h(u)` instead of `h(u-1)` and a half
  spread without its half-tick floor both pass G0.1 on the fixture data
  (`h(u-1) == h(u)` at both SYNA rolls for every reference strategy; no
  spread below one tick). G0.1 does not distinguish them. G0.3 covers a
  carried versus flat roll cost; the floor is in the calculation's
  self-test only.

G0.2:
- It covers what §12.1 lets a strategy text reach (kept frames, the index,
  `iloc`, `loc`, `values`, `to_numpy()`, `base`, `attrs`), not escapes
  through the interpreter (caller frames, the garbage collector, `sys`),
  which are G2.1's (decision 40).
- Finding D-006: the `backtest` command loads a strategy once and evaluates
  every instrument of the subject with it, so a text keeping module-level
  frames could read an earlier instrument's later bars. G0.2 loads the
  text afresh per evaluation and does not exercise this; the U5 sub-agent
  reported it and the orchestrator did not reproduce it.
- The control shows a higher net `total_return` on SYNA, SYNX and the
  subject, but on SYNL only a higher gross: SYNL's one-tick spread exceeds
  one hourly bar's move, so the control does not show a net gain there.
- Truncation invariance is shown for at least ten `t` per instrument on
  one 29-day window and one long store end (2020-07-15).

G0.3, G0.4:
- G0.3's underlying series comes from `synth._generate` and the dropped
  bars from `SynthSource.dropped`, both product code of the synthetic
  source; the test does not check the generator itself.
- G0.4's whole-word match is case-insensitive and skips `__pycache__`
  (choices where DESIGN is silent); it scans names found in `config/` only.

Values and results:
- Every cost value is still from SPEC §17, the DESIGN §4.2 example or the
  R-5 reading (slippage 0.02), `verified = false`, none measured; no real
  spread table exists; the fixture costs and SYNA's fixture spread table
  are invented.
- The reference strategies' results mean nothing about any market: they
  run on synthetic fixture bars with invented costs.

Sub-agents' own items, from their commit bodies:
- U1: the public instance attributes (`root`, `bar_seconds`, `index_path`,
  `notices`) are classified as not readers, a choice beyond decision 34's
  class names.
- U2: the label wording and the `adjusted_as_of` signature (taking the
  `Instrument` record) are the sub-agent's choices; the `backtest` exit-1
  test for a wrong-contract record passed on the parent and was seen to
  fail only by a wrong change (matching on `ts` alone).
- U3: the self-test does not prove agreement with discotrade (U4 does, on
  the one track and window above).
- U3 edited `tests/test_gate_script.py` outside its brief (the M0
  no-gate-test case moved to M1) and U5 moved the one-item case to G1.2;
  both kept the assertions (above).

Carried by `meta/BACKLOG.md`:
- I-11, to step S1.1: the socket backstop is a function-scoped autouse
  fixture, so module-scoped fixtures (`test_gaps.py`, `test_rolls.py`) and
  subprocesses launched by tests run outside it, and `_socket` used
  directly passes. No gate test of this mission launches a subprocess
  (decision 40).
- REVIEW-4 note: an unlisted month file inside the window is not driven
  through `backtest` (the decision 18 test puts it after the window).

What remains of mission 4's NOT PROVEN: the zero-deviation Sharpe rule
shown on eight constants, one one-ulp series and one `compute` case, and
NaN comparisons against ten numbers; an unlisted month file classed as a
revised data point not run through `backtest`; loader rules other than
`max_params`, and results other than 2.0 and a raise, tested at the module
level only; `last_ts`'s cost of reading and hashing every listed month file
not measured, and `index()` classed as not a reader; "NaN until the window
is full" beyond row 0 resting on the older hand-value tests; and mission 3's
list carried there (indicator no-look-ahead shown on the inputs
`hypothesis` drew; slice shape and time-zone columns on the windows tested;
the socket backstop does not stop a C extension's own socket and
Unix-domain sockets are not blocked; `bars fetch`'s lagged-source default
day tested with a wrapped synthetic source only; vendor and crypto clients
tested against fakes only, L1 and L2 never run; no real roll gap measured;
SYNA's contract keys and the generator bounds are the project's inventions;
crashes simulated, not killed processes; calendars other than the fixtures'
untested; every externally sourced value of the eight instrument records
and of `config/calendars/cme_globex.toml` from memory, `verified = false`,
finding D-003; `config check` does not run on `tests/fixtures/config/`;
nothing run on Python 3.11). Resolved by this mission: an independent
calculation now checks the evaluation loop, costs, rolls and metrics on
`test_mixed`, and gate M0 passes; truncation invariance is now shown for a
cheating text at ten or more `t` per instrument (beyond mission 3's three
values for one strategy); the reference strategies are now compared with
the independent calculation.

## Findings filed

- D-004 (U4): `max_drawdown`, does the starting 0 of the running sum count
  as a peak. Answered by the phone architect (it does), recorded in
  `meta/plan.md`, to be carried as decision 41; settled by de9fc09.
- D-005 (U4): G0.1's data cannot see a roll cost on `h(u)` nor the
  half-tick spread floor. Open for the architect.
- D-006 (U5): `backtest` shares one loaded strategy across a subject's
  instruments. Open for the architect.
- No hands finding was filed. HF-006 stays open; no unit reported a
  `./scripts/check` or `./scripts/gate` run moved to the background.

## Review items

| Item | Review | Resolution | Sha |
|---|---|---|---|
| REVIEW-4 should-fix 1 | The `BarStore` classification test misses a public reader written as a property | U1, decision 34 (every public name through the MRO, properties included, plus public instance attributes; fails for an added property reader and method) | 8e8215c |
| REVIEW-4 note on U3 | `bars/gaps.py`, `rolls.py` (`update_rolls`, `adjusted_as_of`) look at the index before the reader, so an interrupted first append reads as "no bars" | U1, decision 35 (they read the entry through the refusing reader `BarStore.index_entry`; refuse with decision 18's errors; "no stored bar" only with no month file) | 8e8215c |
| REVIEW-3 note carried to S0.4 | Reads before `trusted_from` (roll gap, `adjusted_as_of`'s start) | U2, decision 36 (roll gap both paths, `adjusted_as_of` for any start, evaluation context and `sigma` read nothing before `trusted_from`; no roll across it) | 8d27fe1 |
| REVIEW-3 note carried to S0.4 | `MissingRollError` for a record with the right `ts` and the wrong contracts | U2, decision 37 (records matched on `ts`, old and new contract; exit 1 from `backtest`) | 8d27fe1 |
| REVIEW-3 note carried to S0.4 | Unlabelled cost lines of the `backtest` plain output | U2, decision 38 (subject line labelled as divided by `N`, instrument lines as undivided sums; figures and `--json` unchanged) | 8d27fe1 |

VERDICT: mission 5 finished
