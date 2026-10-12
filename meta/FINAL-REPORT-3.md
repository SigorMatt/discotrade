VERDICT: mission 3 finished

# FINAL REPORT — mission 3 (roadmap step S0.3)

Builder prompt: `meta/BUILDER-3-PROMPT.md`. Base ef2e9f1. This mission does
not close a milestone: the independent calculation, the cheating strategy
and the gate tests are step S0.4, mission 4 (decision 28). It binds
`meta/decisions/decisions-2026-10-12.md` (cited below as "decision N").

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan files | 02b366c | plan: mission 3 plan, checkpoint and journal (S0.3) |
| U1 reader, fetch default day, socket backstop | a966344 | bars: reader refuses unlisted month files; fetch checks 16.1's D; socket backstop |
| U2 strategy contract, loader, indicators | 542c171 | strategy: contract loader, result check and indicator library |
| U3 evaluation loop and returns | 833aa25, ec1c8a4 | backtest: slice builder, window walk, positions and gross returns per bar; backtest: context never reads bars before trusted_from |
| U4 cost model and executor | 3c24e5f | costs: cost model c1, SimExecutor, and costed per-bar rows |
| U5 metrics | 8cfd390 | metrics: daily series by decision 23 and the metrics of DESIGN 8 |
| U6 reference strategies, `backtest` | efb2b93 | backtest: three reference strategies and the backtest command |
| U7 final report | this commit | report: mission 3 final report |

The `meta:` commits between units (33bf8aa, 0b2f9a3, f4e8847, 3096af4,
bc11c39, 11ca1b7) are checkpoint bookkeeping. U3 has two commits: the
orchestrator sent back 833aa25 because it let context bars come from before
`trusted_from`, which DESIGN §4.2 forbids ("history before this date is
never used"); ec1c8a4 fixes it with a test that failed first. Each unit
commit's body lists its files and the choices made where DESIGN and the
decisions are silent; those bodies are the authority for this summary.

U1 changed one assertion outside its file list: `tests/test_synth.py`
expected `bars fetch`'s old default day (2019-03-31, UTC date of `--as-of`
minus one); decision 19 makes that value wrong, and it now expects §16.1's
D (2019-03-29). Nothing else in that file changed.

## Acceptance checks

Run by the orchestrator at efb2b93 (U6's tip):
- `./scripts/check` printed `check: green` after every unit (one run each
  by the orchestrator; three by each sub-agent before its commit). A run
  takes about 2 min 50 s.
- `uv run discotrade config check --track hourly` exited 0 (`config check:
  ok, 168 unverified values`).
- `git diff ef2e9f1 -- config/ tests/fixtures/config_frozen.json` is empty.
- `tests/gates/` does not exist; `./scripts/gate M0` printed `gate M0:
  FAIL` and exited 1; `./scripts/gate M0 G0.3` ended `gate M0 G0.3: FAIL`.
- In a temporary state directory, with a copy of `tests/fixtures/config`
  plus the repository's `thresholds.toml`, `bars fetch` on `test_mixed` at
  `--as-of 2019-07-02T00:00:00Z` exited 0, and `discotrade backtest` of
  `reference/hour_of_day.py`, `reference/trend_ma.py` and
  `reference/zscore_reversal.py` over 2019-04-01..2019-06-28 each exited 0
  and printed the §8 metrics with net figures at 1x and 2x, the four cost
  totals, `c1` and the config hash.
- The I-9 test passes (U6).

## What the tests prove

Taken from each unit's commit body; on the constructed cases named there.

- U1: `read_range` and `last_n` refuse an unlisted month file that passes
  decision 5's test ("interrupted append") and one that does not ("revised
  data point"), including reads whose range does not cover that month;
  another instrument's reads are unaffected. After `bars fetch` completes
  an interrupted append, the same reads return the rows the crashed append
  wrote. `bars fetch` with no `--day` checks the same D as `bars gaps` in
  four `--as-of` cases, two with a source lagged by 24 hours; in three the
  UTC date of `--as-of` minus one differs from D. A second fetch at the
  same `--as-of`, and a later one with `--day` set to the first run's D,
  append nothing to `gaps.jsonl` (the old default appended 4 lines). An
  unmarked test that connects (socket, `connect`, `connect_ex`,
  `getaddrinfo`, `httpx`) fails with the backstop's error; in a subprocess
  pytest run, tests marked `network` and `live` reach a loopback listener.
- U2: the loader runs a `position` using `indicators` by the bound name and
  by `import indicators`; it refuses, naming the rule, six parameters, a
  non-numeric parameter, a `GRID` key not in `PARAMS`, three `GRID` keys,
  four values for one key, a text one line over `max_lines`, a
  non-callable and a missing `position`; changing the four limits in a
  copied thresholds file flips the outcomes. The result check refuses NaN,
  +-inf, 1.5, -1.0000001, a string, a bool and a raising call, each naming
  the instrument and `ts`; a negative result is clipped to 0 only when
  `shorting = false`. The 13 indicators equal hand values on short fixed
  inputs; a `hypothesis` test (fixed seed) over every public function of
  the module shows no look-ahead on the drawn inputs; each public function
  has a one-line first docstring line.
- U3: the slice has exactly the seven columns, an index from 0, at most
  `history_cap_bars` rows, no date or symbol, prices equal to
  `rolls.adjust` as of its last row on SYNA across a roll, and `hour`,
  `weekday` in the calendar's zone across the 2019 spring change; each call
  gets a fresh copy; `h(u) = p(u-1)`, `h(u0) = 0`, the last target is
  recorded and not traded; window membership follows each instrument's
  calendar (2019-03-13, SYNA vs SYNX); `gross` equals hand values on a
  7-bar store with one roll and one missing bar; on SYNA over two years (8
  rolls) gross equals the gap-free underlying's to 1e-12 for an
  always-long and an alternating strategy; a contract change with no roll
  record raises decision 24's error naming `bars fetch`; positions up to
  `t` on SYNA, SYNL, SYNX are identical for a store ending at `t` and one a
  year later, at three values of `t`; no bar before `trusted_from` is
  window or context.
- U4: hand values of `fee` (SYNA per contract, SYNX `fee_bps`),
  `half_spread` (floor; SYNA's fixture table by local hour, summer and
  winter; main/off without a table), `sigma` (ddof 1, 24 returns adjusted
  as of `s` over the raw previous close, context bars used, untrusted bars
  skipped, 0 below 2 returns), `roll_cost` (carried position pays, flat
  and first window bar do not, an order with no trade can carry it),
  `cost`, `net_1x`, `net_2x` and every decision 25 column on a five-bar
  case; one `Fill` per `Order` with the fill bar, the raw price and
  components summing to `cost`; version `c1`; the config hash equal across
  two subprocesses, changed by a `[cost]` value, `tick_size`, `multiplier`
  and one spread-table value, unchanged by companions; an AST scan finds
  `SimExecutor` the only `Executor` in `src/`.
- U5: on hand-made inputs, `total_return`, `sharpe`, `sharpe_2x`,
  `max_drawdown`, `trades` (roll rows and sub-floor trades not counted),
  `avg_holding_bars` (runs broken by sign change and zero; NaN with no
  run), `breakeven_cost` (bps, rolled turnover in the denominator, NaN
  without turnover) and `fragile`; Sharpe NaN with 0 or 1 day and zero
  deviation, and NaN is neither positive, negative, above nor below any of
  seven tested numbers; the daily series follows decision 23 on three
  instruments (different calendars, one missing a day, one with no window
  bar, N = 3); return metrics equal those of the daily series and differ
  from window-by-window aggregates; no gross figure leaves the module
  without the net totals beside it.
- U6: each reference file passes the loader with the repository's
  thresholds; `backtest` of each over a 64-trading-day window on
  `test_mixed` exits 0 and its `--json` holds the §8 metrics, `sharpe_2x`,
  the 2x total, the four cost totals, `c1` and the hash, `null` where not a
  number; each strategy trades on SYNA, SYNL and SYNX, SYNL's position is
  never negative, at least one pays a non-zero roll cost on SYNA; SYNA's
  spread total uses its fixture table (differs from the main/off rule);
  two runs give byte-identical `--json`; a file outside `reference/` and
  `--from` after `--to` exit 2, a revised bar file exits 1; every plain
  line naming gross or breakeven also names `net_1x` and `net_2x`.

## NOT PROVEN

The calculation:
- No independent calculation has checked the evaluation loop, the gross
  returns, the cost model or the metrics. Every hand value in the tests was
  computed by the same sub-agent that wrote the code it checks. The
  independent calculation (`tests/gates/independent_calc.py`, decision 29)
  and the cheating strategy are mission 4's.
- No gate test exists; gate M0 fails.
- Indicator no-look-ahead is shown only on the inputs `hypothesis` drew;
  slice shape and time-zone columns only on the windows tested; truncation
  invariance at three values of `t` for one strategy; NaN Sharpe's
  comparisons against seven numbers.
- `backtest` exit 1 is tested only for a revised bar file, not for an
  unlisted month file, a missing roll record or a contract-breaking
  strategy (each of those errors is tested at the module level).
- U6's reference tests (`tests/test_reference.py`) were written after the
  strategy files and were not seen to fail first; U6's CLI tests were.
- The socket backstop patches `socket.connect`, `connect_ex`, `sendto` and
  `getaddrinfo`; a C extension opening its own socket would pass it;
  Unix-domain sockets are not blocked.
- `bars fetch`'s lagged-source default day is tested with a wrapped
  synthetic source only, not the vendor.

Values:
- Every cost value is still from SPEC §17 or the DESIGN §4.2 example
  (`fee_per_side`, 1.0 / 2.0 spread ticks, slippage 0.02) or the R-5
  reading, `verified = false`, none measured; no real spread table exists
  (`config/spreads/` is absent); the fixture costs and SYNA's fixture spread
  table are invented.
- The reference strategies' results mean nothing about any market: they
  run on synthetic fixture bars with invented costs, and they are not shown
  to be profitable or sensible.

Choices where DESIGN is silent (in the commit bodies; a reviewer may
disagree): ddof 1 and Wilder smoothing in the indicators; the strategy is
not called at context bars; the evaluation reads at least 25 trusted bars
before the window for `sigma` even when the history cap is smaller;
`evaluate`'s `spread_table` is optional (None = main/off rule; `backtest`
passes the table, tested); `max_drawdown` counts the start as a peak; the
subject's cost totals are per-instrument sums divided by N; the 1e-9 trade
floor and 252 annualisation are module constants from DESIGN §8 / R-7, not
`thresholds.toml` entries; the notice date of `bars fetch` is unchanged
(only the gap-check day moved).

What remains of mission 2's NOT PROVEN (not revisited): the vendor and
crypto client and endpoint shapes are tested against fakes only (L1, L2
never run); no real roll gap measured; SYNA's contract keys and the
generator bounds are the project's inventions; crashes are simulated, not
killed processes; calendars other than the fixtures' untested; every
externally sourced value of the eight instrument records and of
`config/calendars/cme_globex.toml` is from memory, `verified = false`
(finding D-003); `config check` does not run on `tests/fixtures/config/`;
nothing was run on Python 3.11. Resolved by this mission: the reader's
unlisted month file and `bars fetch`'s default day (U1).

## Findings filed

- HF-006 (low, hands): long foreground `./scripts/check` runs of a
  sub-agent were moved to the background by the harness (U6 reported it;
  the sub-agent waited for all three before committing). Filed by this
  commit. Status: open.
- No design finding (D-###) was filed by a unit of this mission.

## Review items

REVIEW-2 (`meta/reviews/REVIEW-2.md`), `## Should-fix`.

| Item | Review | Resolution | Sha |
|---|---|---|---|
| 1 | The reader does not refuse a month file the index does not list | U1, decision 18 (every read refuses; error says interrupted append or revised data point) | a966344 |
| 2 | `bars fetch` defaults its gap-check day to UTC `--as-of` minus one, not §16.1's D | U1, decision 19 (same D and same function as `bars gaps`) | a966344 |

The REVIEW-2 note on U5 (no socket backstop) is resolved by U1, decision
20, a966344.
