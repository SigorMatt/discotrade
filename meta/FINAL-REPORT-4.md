VERDICT: mission 4 finished

# FINAL REPORT — mission 4 (roadmap step S0.3, repair)

Builder prompt: `meta/BUILDER-4-PROMPT.md`. Base 9f00d99. This mission
repairs step S0.3: it takes REVIEW-3 blocker 1 and should-fix 1 to 4 and
adds nothing else. It does not close a milestone: the independent
calculation, the cheating strategy and the gate tests are step S0.4,
mission 5 (decision 33). It binds `meta/decisions/decisions-2026-10-12.md`
(cited below as "decision N"; items 30 to 33 are new).

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan files | 593c0ea | plan: mission 4 (S0.3 repair, REVIEW-3 blocker 1 and should-fix 1-4) |
| U1 Sharpe at zero deviation, `trades` test | 836c2ab | metrics: Sharpe not a number at zero deviation by decision 30; trades test |
| U2 `backtest` exit 1 paths | 6445223 | backtest: tests for the exit 1 paths of decision 27 |
| U3 `BarStore.last_ts` refuses | 9c4023b | store: last_ts refuses as a reader; writer and bars fetch use the index helper |
| U4 indicator module text | 300be21 | indicators: module text names ema as seeded; row-0 test over every function |
| U5 final report | this commit | report: mission 4 final report |

The `meta:` commits between units (7ae9965, 12ae295, 6ee68dc, a829c52) are
checkpoint bookkeeping. Each unit commit's body lists its files and the
choices made where DESIGN and the decisions are silent; those bodies are
the authority for this summary. No existing test changed what it asserts
(each unit body says so); U1 added an optional `roll` column, default 0, to
the `rows` helper of `tests/test_metrics.py`, which leaves every existing
frame unchanged. Product code changed in three places: `metrics.sharpe`
(U1), `BarStore.last_ts` with a new private `_indexed_last_ts` used by the
writer and `bars fetch` (U3), and the `indicators` module docstring (U4).
U2 added a `cli.REFERENCE_ROOT` module constant as a test seam, with no
change in behaviour.

## Acceptance checks

Run at a829c52 (U4's tip plus its checkpoint commit) before this commit:
- `./scripts/check` printed `check: green` on three consecutive runs (910
  passed; about 3 min each).
- `uv run discotrade config check --track hourly` exited 0 (`track hourly:
  8 instruments`, `config check: ok, 168 unverified values`).
- `git diff 9f00d99 -- config/ tests/fixtures/config_frozen.json` is empty.
- `tests/gates/` does not exist; `./scripts/gate M0` printed `G0.1` to
  `G0.4 FAIL no gate test` and `gate M0: FAIL`, exit 1; `./scripts/gate M0
  G0.3` ended `gate M0 G0.3: FAIL`, exit 1.
- In a temporary state directory under `/tmp` (`DISCOTRADE_STATE`), with a
  copy of `tests/fixtures/config` plus the repository's `thresholds.toml`,
  `bars fetch` on `test_mixed` at `--as-of 2019-07-02T00:00:00Z` exited 0
  (two SYNA rolls recorded), and `discotrade backtest` of
  `reference/hour_of_day.py`, `reference/trend_ma.py` and
  `reference/zscore_reversal.py` over 2019-04-01..2019-06-28 each exited 0
  and printed the §8 metrics with `net_1x` and `net_2x` totals, `sharpe`
  and `sharpe_2x`, the four cost totals, `c1` and the config hash.
- A grep of `src/` for the eight instrument roots, the fixture symbols and
  the venue names (CME, NYMEX, COMEX, CBOT, Globex) finds nothing; the I-9
  test passes in `./scripts/check`.

## What the tests prove

Taken from each unit's commit body; on the constructed cases named there.

- U1: `sharpe` is not a number for `[0.1]*3`, `[0.03]*10`, `[0.01]*3`,
  `[1/3]*10`, `[0.07]*10`, `[-0.05]*5`, `[0.0]*4`, `[1e-6]*20`, and for a
  series one ulp off constant; for each, `positive`, `negative`, `above(s,
  x)` and `above(x, s)` are false for ten listed `x` (including +-inf,
  +-1e17 and NaN). Five of those constants gave a finite Sharpe (about
  1e16 to 1e17) on the parent. `compute` on a ten-day hand case with a
  constant non-zero daily net (0.07 at 1x, 0.03 at 2x) gives `sharpe` and
  `sharpe_2x` not a number. `[0.1, 0.1, 0.1 + 1e-9]` still gives a finite
  Sharpe equal to its hand value (rel 1e-6). `trades`: a rolled bar with
  `trade` 0.5 is counted and a rolled bar with `trade` 0 and roll cost
  0.0004 is not; the test fails both for a `trades` that drops every
  rolled row (1, not 2) and for one that counts a non-zero roll cost (3,
  not 2), each a wrong change made and reverted.
- U2: after `bars fetch` on `test_mixed` into a temporary state directory,
  `backtest` exits 1 with an error naming the cause when SYNA's roll
  record is missing for the 2019-06-14 roll (in the window) and for the
  2019-03-14 roll (in the context); when the strategy returns 2.0 at one
  bar and when it raises there (the error names the instrument and `ts`);
  when the loader refuses a text with six parameters (names `max_params`);
  and when SYNX's directory holds a month file the index does not list
  (interrupted-append case). Strategy texts live in a pytest temporary
  directory, reached by pointing `cli.REFERENCE_ROOT` at it in-process.
  Each test fails when its path is changed to exit 2 (wrong change made and
  reverted).
- U3: `last_ts` refuses with the interrupted-append error for an unlisted
  month file passing decision 5's test with `r = 0` (index unchanged), and
  with the revised-data-point error for an unlisted file failing it and for
  a listed file with a changed row; after a `bars fetch` that crashed
  before its index write, `last_ts` refuses, and after the next `bars
  fetch` it returns the crashed file's last `ts`. Every public method of
  `BarStore` is classified as a reader (`read_range`, `last_n`, `last_ts`)
  or not (`append`, `recover`, `month_path`, `index`); each reader refuses
  both unlisted cases; an added unclassified method (`first_ts`, made and
  reverted) fails the test.
- U4: for the 13 public functions of `indicators`, windows 2, 3 and 12 and
  inputs of 1, 2 and 25 rows, `ema` is the only function with a number at
  row 0 in every returned column, every other is NaN at row 0, and the
  module docstring names `ema` as seeded at the first value. The test
  fails when `ema` gets `min_periods=window` and when `sma` gets
  `min_periods=1` (wrong changes made and reverted).

## Corrections to FINAL-REPORT-3

REVIEW-3 found two claims of `meta/FINAL-REPORT-3.md` (§What the tests
prove, U5) overreaching what the code did. As the code now does them:

1. FINAL-REPORT-3 said "Sharpe NaN with 0 or 1 day and zero deviation". At
   8cfd390 that held only for constants whose floating-point deviation
   rounds to exactly 0 (the one tested case, `[0.01]*3`); `[0.1]*3` gave
   about 9.3e16. Since 836c2ab (decision 30), `sharpe`, and through it
   `sharpe_2x`, is not a number with fewer than 2 days, when every daily
   value equals the first, or when `std(d, ddof=1)` is not above `1e-12`
   times the largest absolute value in `d`; tested on the eight constants
   and the one-ulp series listed under U1 above.
2. FINAL-REPORT-3 said `trades` had "roll rows ... not counted". The code
   never dropped rows with a roll: it counts rows with `trade > 1e-9`, and
   roll turnover never enters `trade`. Correctly stated: roll trades are
   not counted; a bar with a roll and a real trade is. 836c2ab adds the
   test that tells this from both wrong readings; `trades` itself is
   unchanged.

## NOT PROVEN

The calculation:
- No independent calculation has checked the evaluation loop, the gross
  returns, the cost model or the metrics. Every hand value in the tests was
  computed by the same sub-agent that wrote or repaired the code it
  checks. The independent calculation (`tests/gates/independent_calc.py`,
  decisions 29 and 30) and the cheating strategy are mission 5's (step
  S0.4, decision 33).
- No gate test exists; gate M0 fails.
- The zero-deviation rule is shown on eight constants, one one-ulp series
  and one hand `compute` case; the tolerance is shown not to swallow one
  series with a 1e-9 deviation. Comparisons of a NaN Sharpe are shown
  against ten numbers, not every number.
- U2: an unlisted month file classed as a revised data point is not run
  through `backtest` (the revised listed bar file of mission 3 is); loader
  rules other than `max_params`, and strategy results other than 2.0 and a
  raise (NaN, inf, a non-number), are tested at the module level only, not
  through the command.
- U3: `last_ts` now reads and hashes every listed month file of the
  instrument; its cost is not measured. `index()` is classed as not a bar
  reader (a choice; decision 31 is silent on it).
- U4: the row-0 test covers three windows and three input lengths; "NaN
  until the window is full" beyond row 0 rests on the existing hand-value
  tests, not on the new test.

Values:
- Every cost value is still from SPEC §17, the DESIGN §4.2 example
  (`fee_per_side`, 1.0 / 2.0 spread ticks) or the R-5 reading (slippage
  0.02), `verified = false`, none measured; no real spread table exists
  (`config/spreads/` is absent); the fixture costs and SYNA's fixture
  spread table are invented.
- The reference strategies' results mean nothing about any market: they
  run on synthetic fixture bars with invented costs, and they are not shown
  to be profitable or sensible.

REVIEW-3 notes this mission does not take (decision 33: it adds nothing
beyond blocker 1 and should-fix 1 to 4), carried by `meta/BACKLOG.md`:
- To step S0.4 (mission 5): whether `rolls.py`'s `last_n` while measuring a
  roll gap, or `adjusted_as_of`'s default start, can read bars before
  `trusted_from` (DESIGN §4.2); `MissingRollError` is tested for a `ts`
  mismatch only, not for a record with the right `ts` and the wrong
  contracts; the `backtest` plain output's `costs at 1x` line (subject
  totals divided by N) and the per-instrument lines (undivided sums) are
  not labelled (unchanged; seen again in this report's acceptance run).
- To step S0.4 at the latest if its gate tests launch subprocesses,
  otherwise S1.1 (I-11): the socket backstop is a function-scoped autouse
  fixture, so module-scoped fixtures (`test_gaps.py`, `test_rolls.py`) and
  subprocesses launched by tests run outside it, and `_socket` used
  directly passes.
- Not carried as work: the I-4 plain-output test is weak in that nothing
  printed contains the word "gross"; `tests/test_backtest.py:186`'s
  near-tautological weekday assertion and `:372`'s mislabelling comment;
  the two hands notes (HF-006, a brief exempting assertions a decision
  changes, which this mission's brief now does).

What remains of mission 3's NOT PROVEN: no independent calculation and gate
M0 failing (above); indicator no-look-ahead shown only on the inputs
`hypothesis` drew; slice shape and time-zone columns only on the windows
tested; truncation invariance at three values of `t` for one strategy;
`tests/test_reference.py` not seen to fail first; the socket backstop does
not stop a C extension's own socket, and Unix-domain sockets are not
blocked; `bars fetch`'s lagged-source default day is tested with a wrapped
synthetic source only; cost values and reference results as above; and
mission 2's list carried there (vendor and crypto clients tested against
fakes only, L1 and L2 never run; no real roll gap measured; SYNA's contract
keys and the generator bounds are the project's inventions; crashes
simulated, not killed processes; calendars other than the fixtures'
untested; every externally sourced value of the eight instrument records
and of `config/calendars/cme_globex.toml` from memory, `verified = false`,
finding D-003; `config check` does not run on `tests/fixtures/config/`;
nothing run on Python 3.11). Resolved by this mission: `backtest` exit 1
for an unlisted month file, a missing roll record, a contract-breaking
strategy and a loader refusal (U2, 6445223).

## Findings filed

- None. `git diff 9f00d99 -- meta/findings/FINDINGS.md` is empty: no design
  finding (D-###) and no hands finding (HF-###) was filed by a unit of this
  mission or by this report. HF-006 (filed by mission 3) stays open; no run
  of this report's acceptance checks was moved to the background.

## Review items

REVIEW-3 (`meta/reviews/REVIEW-3.md`), `## Blockers` and `## Should-fix`.

| Item | Review | Resolution | Sha |
|---|---|---|---|
| Blocker 1 | `metrics.sharpe` returns a huge finite Sharpe for a series whose deviation is zero | U1, decision 30 (all values equal the first, or `std(d, ddof=1)` not above `1e-12` times max abs value: not a number; eight constants tested) | 836c2ab |
| Should-fix 1 | The `trades` test cannot tell a correct implementation from a wrong one; "roll rows" worded wrongly | U1, decision 25 (rolled bar with a real trade counted, roll with trade 0 not; fails both wrong changes); wording corrected above | 836c2ab |
| Should-fix 2 | `backtest` exit 1 paths of decision 27 have no test | U2, decisions 18, 21, 22, 24, 27 (six tests: two missing roll records, result 2.0, a raise, loader refusal, unlisted month file) | 6445223 |
| Should-fix 3 | `BarStore.last_ts()` skips decision 18's refusal | U3, decision 31 (`last_ts` refuses as `read_range` and `last_n`; writer and `bars fetch` use private `_indexed_last_ts`) | 9c4023b |
| Should-fix 4 | The indicators module docstring is false for `ema` | U4, decision 32 (docstring names `ema` as seeded at the first value; row-0 test over every public function) | 300be21 |

VERDICT: mission 4 finished
