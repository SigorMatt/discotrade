VERDICT: mission 1 finished

# FINAL REPORT — mission 1 (roadmap step S0.1)

Builder prompt: `meta/BUILDER-1-PROMPT.md`. Base 9ed3cd4. This mission does
not close a milestone.

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan files | 766cf32 | plan: mission 1 plan, checkpoint and journal |
| U1 skeleton, clock, CLI, scripts | f04fab2 | skeleton: package, injected clock, cli options, scripts/check and scripts/gate |
| U2 configuration records | 5ddcba4 | config: configuration records, hourly track, eight instruments, thresholds, config check |
| U3 trading calendar | f4e0141 | calendar: trading calendar, exchange calendar record, fixture calendars, config check loads calendars |
| U4 bar store | 8348743 | bars: append-only Parquet bar store with month files, index and content hash |
| U5 gap check | 3b5439e | bars: gap check with pooled W and T fractions, gaps.jsonl and data_gaps event |
| U6 null synthetic market | e1c3f76 | sources: null synthetic market, BarSource protocol and `discotrade bars fetch` |
| U7 final report | this commit | report: mission 1 final report |

Each unit commit's body lists its files and the choices made where DESIGN is
silent; those bodies are the authority for this summary.

## What the tests prove

Checked at tip 203b002: `./scripts/check` prints `check: green` (271 tests
pass); `uv run discotrade config check` exits 0; `./scripts/gate M0` prints
`gate M0: FAIL` and exits 1 (no gate tests exist yet; they are S0.3's).

- U1: `--state` inside the repository exits 2 naming I-14, for the path forms
  tested; a temporary state path is accepted. `--as-of` sets a FixedClock in
  UTC for the three forms tested; naive or malformed instants exit 2. Unknown
  options or commands, no command and a missing value exit 2. `scripts/gate M0`
  fails item by item and ends `gate M0: FAIL`. Under `DISCOTRADE_GATE=1` a skip
  fails or errors.
- U2: each tested refusal of the config loader (unknown or missing keys,
  companions, fee forms, `test_only` outside a test track, bad track
  instruments, name mismatch, invalid values); the hourly track and the eight
  instrument records load with SPEC §17 fees, `verified = false`, slippage
  0.02; cells in families-then-horizons order; W and T for 2026-03-13;
  `thresholds_v1.toml` equals DESIGN §4.3 as written in the test;
  `thresholds_gate.toml` differs in exactly the seven §18.2 keys; the history
  and frozen-config drift checks pass on the repository and fail on the
  constructed bad copies; no file under `src/` names a symbol, root or venue
  from `config/instruments/` as a whole word; `config check` exits 0 listing
  the 64 unverified instrument values, and 1 on an invalid value.
- U3: `is_open`, `trading_date`, `expected_bars`, `in_main_session` give the
  stated results on the named weeks (both 2024 clock changes, a weekend, the
  daily break, Christmas 2026, the day after Thanksgiving 2026, the synthetic
  closure); a derandomized hypothesis search over 2019 to 2027, three
  calendars, five bar lengths agrees with an independently written wall-clock
  rule; calendar loader refusals per key; `config check` lists every
  unverified calendar value.
- U4: on the constructed cases, the writer refuses unclosed, non-increasing,
  duplicate and unsorted bars and writes nothing; appends leave old rows
  identical (frame and hash); month split on the UTC month; the index records
  first/last ts, rows and content hash; `read_range` is half-open across a
  month boundary; `last_n` ends inclusive; reader and writer refuse a file
  whose hash no longer matches, and the reader a missing file.
- U5: on `test_synth` over 2019-06-02..2019-07-13, a complete store reports no
  missing bar; removed bars are reported exactly and appended once to
  `gaps.jsonl`; bars outside the checked span are not missing; W and T
  fractions equal pooled missing over expected; generation is skipped with a
  `data_gaps` alert when a window is strictly above the limit and not when
  equal; with 0.01, 4 of 460 T bars is not skipped and 5 is; the CLI prints
  the missing bar, appends it once over two runs and states a skip.
- U6: same seed gives identical bars and seed+1 different (five instruments,
  60 days); a sub-range equals the cut of a longer request; highs and lows
  enclose open and close; bar times are a subset of expected times and the
  missing ones are exactly the dropped bars; return mean and lag-1
  autocorrelation within the stated bounds and hourly volatility within
  0.8x..1.4x of `hourly_vol` for the five fixed seeds; `bars fetch` at
  2019-04-01T10:30Z writes only closed bars equal to the source's and
  `bars gaps` lists exactly the dropped bars; a two-step fetch equals a
  one-step fetch and a rerun leaves `index.json` unchanged; a rolling
  instrument fails with "not built" and writes nothing.

## NOT PROVEN

Externally sourced values (all `verified = false`, none read from a primary
source in this mission):
- Multipliers, tick sizes, listing dates (`trusted_from`) and main sessions of
  all eight instruments are from memory of the exchange's public contract
  pages. Least certain: listing dates MGC 2010-09-27, SIL 2011-12-12, M6E
  2009-03-23, and the main sessions of MGC, SIL, MCL, M6E.
- SPEC §17 fees are unverified.
- Spread (1.0 / 2.0 ticks) and slippage (0.02) copy the DESIGN §4.2 example
  for all eight instruments; they are not measured.
- Every closure date and time in `config/calendars/cme_globex.toml`, and its
  weekly schedule, are from memory. Doubts: Good Friday 2021, 2023, 2026
  modelled as full closures (may have had a short session on payroll days);
  the 2025-01-09 halt time (Carter day of mourning); the Thursday closes
  before observed Christmas in 2021 and 2027; metals, energy and FX holiday
  hours may differ from equity hours, yet one calendar serves all eight
  instruments.

Behaviour not covered by a test:
- U1: state-dir refusal tested only on the listed path forms; no test runs
  `./scripts/check` itself (run by hand) nor checks that `scripts/gate`'s
  item counts match DESIGN §18.3; the DESIGN §18.1 rule that `container`
  tests skip without a runtime is not built; the venv ran CPython 3.14,
  nothing was run on 3.11.
- U2: `config check` does not run on `tests/fixtures/config/` (no
  `thresholds.toml` there).
- U4: atomicity is per file only (a crash mid multi-month append is caught by
  the reader's hash check, not prevented); the store's no-wall-clock check is
  a text scan; tests use hourly bars only.
- U5: the stopped-feed blind spot (D-002) is read from code, not tested.
  Choices not confirmed by DESIGN: `trusted_from` counts from midnight UTC,
  "above" is strictly greater, `bars gaps` defaults to the day before the UTC
  date of `--as-of`; the fixture config lacks `thresholds.toml` (CLI tests
  copy the repository's in).
- U6: SYNA (quarterly roll) is untested, contracts are S0.2; statistics are
  shown for five fixed seeds only; fetch CLI tests cover 2019-01-07..
  2019-04-01 only; the fixture closure is exercised only in the two-year
  source test, not through the CLI; vendor and crypto adapters raise "not
  built"; synthetic volatility and volume shapes are constants in `synth.py`.
- No gate test exists: gate M0 fails (S0.3's work).

## Findings filed

- D-001 (low, DESIGN §4 with §4.2): the instrument record cannot hold
  top-level companions because `source` is already the `[source]` table; U2
  put the contract-specification companions in a `[spec]` table. Status: open.
- D-002 (medium, DESIGN §5.4): the window gap fraction, counted over each
  instrument's checked span, cannot see an instrument whose feed stopped; the
  architect is asked whether missing bars run to the end of the window or a
  stale feed is a separate health condition. Status: open.
- No hands findings (HF) were filed in this mission.

## Review items

No review precedes this mission: it is the first mission of S0.1.

| Item | Review | Resolution | Sha |
|---|---|---|---|
