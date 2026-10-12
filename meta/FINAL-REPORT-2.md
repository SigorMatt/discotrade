VERDICT: mission 2 finished

# FINAL REPORT — mission 2 (roadmap step S0.2)

Builder prompt: `meta/BUILDER-2-PROMPT.md`. Base 1151e55. This mission does
not close a milestone. It binds `meta/decisions/decisions-2026-10-12.md`
(cited below as "decision N").

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan files | 87d4a23 | plan: mission 2 plan (S0.2, units U0-U7) |
| U1 store and gap-check repairs | f3f8c2d | bars: complete interrupted appends, refuse non-finite bars, bound the gap check at D |
| U2 cli, config and gate repairs | 8e423c1 | cli: refuse state in any code repository and blank state; type-strict frozen check; item-only gate verdict |
| U3 synthetic contracts | cb9c21d | synth: quarterly contracts, fetch_contract, generator settings read from [source] |
| U4 rolls, adjusted series | 61e1c59 | rolls: record rolls with measured or estimated gaps; adjusted series as of t |
| U5 vendor and crypto adapters | 5995b92 | sources: vendor and crypto adapters; doctor --live vendor refuses without the key |
| U6 spreads | a5245d0 | spreads: spread rule, spread tables, spreads measure, doctor --live spreads |
| U7 final report | this commit | report: mission 2 final report |

The `meta:` commits between the units (4b9ce9d, f1958d4, b86601c, 70919f0,
fcb9264, c77c5d9, c64b5d6) are checkpoint bookkeeping. Each unit commit's
body lists its files and the choices made where DESIGN and the decisions
are silent; those bodies are the authority for this summary.

## Acceptance checks

Run by the orchestrator at tip c64b5d6 (not re-run by this report beyond
`./scripts/check`):
- `./scripts/check` printed `check: green` three consecutive runs (about
  532 tests).
- `./scripts/gate M0` printed `gate M0: FAIL` and exited 1;
  `./scripts/gate M0 G0.3` ended `gate M0 G0.3: FAIL` (no gate tests exist
  yet; they are S0.3's).
- `uv run discotrade config check` exited 0 on the hourly track
  (`config check: ok, 168 unverified values`).
- `git diff 1151e55 -- config/` is empty, and no existing entry of
  `tests/fixtures/config_frozen.json` changed.
- `bars fetch --track test_mixed --as-of 2019-07-01T12:00:00Z` into a
  temporary state directory, with a copy of `tests/fixtures/config` plus
  the repository's `thresholds.toml` (the fixture config has none, as in
  mission 1), exited 0 and wrote `rolls/test_mixed/SYNA.jsonl` with two
  measured rolls (2019-03-14 gap -60.25, 2019-06-14 gap 37.5).
- A grep of `src/` for venue names found only the env-var name
  `DATABENTO_API_KEY` (allowed by decision 11); the I-9 test passes.

## What the tests prove

Taken from each unit's commit body; on the constructed cases named there.

- U1: a crash after a month file's rename and before the index write (one
  month; three months in one append, onto an existing and a new
  instrument; between two month renames) is completed by the next append,
  by `recover` and by `bars fetch`, with the recovered files
  byte-identical, the index equal to a clean run's, and `store_recovered`
  notices naming the instrument and file. A changed old row, a removed row
  and an inserted earlier row (with and without a crash) stay refused as
  revised, and the reader's error tells the two cases apart. The writer
  refuses NaN and +-inf in each of the five columns and writes nothing;
  `bars fetch` drops such bars, prints the count, and the gap check lists
  them as missing. A replay of a past day after later fetches appends
  nothing beyond the original run, and a first run on a store holding
  later bars appends the same bytes. A stopped feed, an absent instrument
  and an empty store count as missing to the end of D and skip generation;
  window counts start no earlier than `trusted_from`. An append to
  `gaps.jsonl` keeps every earlier byte, and a crash before its rename
  leaves it intact. `fsync` of the file precedes every rename (month files,
  index, `gaps.jsonl`), checked by patching `os.fsync`. `bars gaps` with no
  day picks §16.1's D in four `--as-of` cases, one where the UTC date and
  the trading date differ.
- U2: `--state` inside a temporary directory laid out as a code repository
  (four path forms) and the same via `DISCOTRADE_STATE` exit 2 naming I-14,
  with `REPO_ROOT` unchanged; a directory with only one of the two markers
  is accepted; `--state` "", "  ", "\t" and `DISCOTRADE_STATE` "", " " exit
  2. `frozen_drift` reports 5.0 -> 5, 1 -> true, 1 -> 1.0, "1" -> 1, date ->
  string, [1, 6] -> [1.0, 6] and a table value 2 -> 2.0; a change entry
  approves 5.0 -> 5 only with `new = 5`; the repository still passes.
  `scripts/gate M0 G0.3` ends `gate M0 G0.3: FAIL` and prints no `gate M0:`
  line; with `run_item` replaced in-process, one-item and whole runs print
  the item or milestone verdict respectively. In a scratch suite, a
  `gate_m0` test without `gate`, a `gate`-only or unmarked test under
  `gates/`, and a test with two milestone markers each make the run fail
  naming the test, under no `-m`, `-m "not gate"` and `-m gate_m0`.
- U3: fixed fetches over [2019-01-07, 2019-07-08) of all six fixture
  instruments have the content hashes computed at b86601c before the
  change (SYNA's taken with `roll_schedule = "none"` and tied to the rolled
  series by the next point). Changing any one of the seven generator
  settings changes SYNB's bars. Each missing generator or contract key is
  refused by its dotted name; out-of-range values and contract keys without
  a schedule are refused. On SYNA over two years the contract changes at
  exactly the first bar at or after each of the 8 scheduled instants;
  `fetch_contract` gives at least 24 common bars each side of a roll, with
  a nonzero price difference equal to the difference of the constants to
  1e-9; the continuous series and each contract's bars equal the
  underlying plus the constant bit for bit. On SYNB with a fixed seed over
  two years, the hour-of-day volatility ratio, the log-volume difference
  and the open-gap correlation are within 4 standard errors of the
  configured shapes. `bars fetch` on `test_mixed` stores SYNA's bars with
  contracts SYNA-2019-03 then SYNA-2019-06. Two mutants each failed a test.
- U4: the 8 scheduled SYNA rolls in two years are recorded with the right
  ts and contracts, every gap equal to the difference of the constants to
  1e-9, none estimated; SYNL and SYNX get no roll file. The adjusted
  series as of each of 216 bars over 700 days (every roll bar and its
  neighbours) equals the underlying plus the constant of the contract
  current at t to 1e-9, its last bar raw, volume and contract unadjusted.
  The adjusted series as of three bars of a one-year store equals that of
  the two-year store, whose roll file has the one-year file as prefix. A
  roll at the first bar of a second fetch gives the same file as one fetch;
  a re-fetch with no new bar appends no roll; an append keeps earlier lines
  byte-identical with `fsync` before the rename and of the directory after.
  No common bar, or one only beyond the 24 bars, gives an estimated gap
  open(u) - close(u-1) and one notice, printed by `bars fetch` in the §15.2
  shape.
- U5 (fake client, `httpx.MockTransport`, no network, no key): vendor fetch
  returns bars in the §5.1 schema equal to the fake's market with contracts
  resolved; `get_cost` is asked first with the same arguments as
  `get_range`; a cost of 5.01 (default limit) or above a record's
  `max_cost_usd` refuses before `get_range`, and 5.0 is fetched;
  `available_until` is now - 24 h. Importing `discotrade.sources.vendor`
  does not import the client package. Without `DATABENTO_API_KEY` (unset,
  empty, blank) the adapter, `bars fetch` and `doctor --live vendor` refuse,
  exit 1 and never construct the fake client; without the client package
  the adapter refuses naming the extra. With a known fake key, client
  errors containing it are redacted and unchained, and the key is in no
  output or state file after a successful and a failing `bars fetch`, nor
  in doctor output. `bars fetch` on the vendor track writes only bars
  closed before as-of - 24 h and records the 2019-03-14 roll measured
  through `fetch_contract`; an over-limit cost stops it before any write.
  The crypto adapter returns closed hourly bars with contract = symbol,
  asks the configured URL and market, pages beyond 1000 rows, refuses 11
  malformed replies, a reply that does not move forward and an unreachable
  endpoint; `bars fetch` on `test_crypto` writes 720 closed bars. Plain
  `doctor` and seven other check names exit 2 naming S5.1.
- U6: the spread rule gives the table's value per local hour, and the
  main/off values without a table, at eleven bars on either side of the
  2019-03-10 New York clock change. `spreads measure` on a synthetic
  sample (seed 7) across that change writes 24 values equal to the known
  medians, with companions and the sample description, and fills hour 17
  (daily break) with the largest median; it refuses to overwrite (file
  unchanged); an open hour with no quote errors naming it and writes
  nothing. `config check` warns and exits 0 for the fixture table, not for
  off-session values. A new or changed spread table is caught by the
  frozen-config check. `doctor --live spreads` and vendor-sourced
  `spreads measure` without the key exit 1 with no call to the fake client;
  with an inline fake quote client the L2 path writes the table and
  reports the marginal instrument.

## NOT PROVEN

Vendor and crypto (no live run; L1 and L2 were never run):
- The vendor client's method shapes (U5): `Historical(key=)`,
  `metadata.get_cost`, `timeseries.get_range` -> `to_df(price_type="float",
  pretty_ts=True, map_symbols=False)` indexed by `ts_event`,
  `symbology.resolve(...)` and `metadata.get_dataset_range` were read from
  the databento 0.87.0 wheel source, never installed, imported or
  exercised; the fake has exactly those shapes, so tests prove agreement
  with the fake only.
- The vendor quote calls (U6): schema `bbo-1m`, the `get_cost`/`get_range`
  keywords, `to_df` indexed by `ts_recv` with `bid_px_00`/`ask_px_00`, are
  tested only against a fake.
- The crypto endpoint's request and response shape (U5) are documented in
  `crypto.py` and recalled, not read from the endpoint's documentation;
  tests use `httpx.MockTransport`.
- The crypto record `tests/fixtures/config/instruments/CRYA.toml` is a
  fixture only (`test_only`): its `base_url` and `market` are recalled, and
  its tick size, session and costs are invented for tests. No crypto record
  exists under `config/instruments/`.
- `uv lock` resolved the `vendor` extra with the network; `./scripts/check`
  does not install it.

Values not measured yet:
- No real spread is measured (L2 not run): `config/spreads/` does not exist (no
  table), and every instrument still uses the DESIGN §4.2 example spreads
  (1.0 / 2.0 ticks) and slippage 0.02. The fixture table
  `tests/fixtures/config/spreads/SYNA.toml` is invented.
- No real roll gap is measured; the measured rolls above are synthetic.
- SYNA's contract keys (`roll_day` 14, `contract_overlap_bars` 48,
  `contract_offset_scale` 20.0) and the bounds on the generator and
  contract keys are invented by the project or the builder's choice.

Choices and gaps the tests do not settle:
- `bars fetch`'s default `--day` is still the day before the UTC date of
  `--as-of`, while `bars gaps` now uses §16.1's D (U1 changed only `bars
  gaps`): the two defaults differ.
- U4 reads DESIGN §5.6's "within 24 bars" as the 24 stored bars of the
  continuous series before the roll, no calendar used; that reading is the
  builder's.
- U6's `spreads.py` uses `vendor.py`'s private `_guard`.
- Crashes (U1, U4) are simulated by patching or by constructed files only;
  no process was killed mid-write.
- U3: calendars other than the fixtures' are not tested; the roll
  look-ahead (120 days past the request) assumes at least
  `contract_overlap_bars` expected bars in it.
- U3/U4 statistics and roll checks use the fixed seeds named in the tests.

What remains of mission 1's NOT PROVEN (not revisited by this mission):
- Every externally sourced value of the eight instrument records
  (multipliers, tick sizes, listing dates, main sessions; SPEC §17 fees)
  and every closure date and time in `config/calendars/cme_globex.toml`
  are from memory, `verified = false`; the doubts listed in
  FINAL-REPORT-1 stand. Their provenance strings are finding D-003.
- The state-directory refusal is tested on the listed path forms only; no
  test runs `./scripts/check` itself or checks that `scripts/gate`'s item
  counts match DESIGN §18.3; the §18.1 rule that `container` tests skip
  without a runtime is not built; nothing was run on Python 3.11.
- `config check` does not run on `tests/fixtures/config/` (still no
  `thresholds.toml` there; CLI tests copy the repository's in).
- The store's no-wall-clock check is a text scan; store tests use hourly
  bars only.
- `trusted_from` counts from midnight UTC; "above" the gap limit is
  strictly greater.
- No gate test exists: gate M0 fails (S0.3's work).

Resolved from mission 1's list by this mission: the multi-month crash
lock-out (U1, decision 5), the stopped-feed blind spot D-002 (U1, decision
2, now tested), SYNA's quarterly roll (U3, U4), the vendor and crypto
adapters (U5, at the fake level above), and the generator constants (U3,
decision 10).

## Findings filed

- D-003 (low, `config/instruments/*.toml` `[spec]` and `[cost]` companions,
  DESIGN §4 and §4.2): filed in U0 from REVIEW-1 should-fix 5; the
  provenance strings read stronger than what was done; the change is a
  frozen-config change and the owner's (decision 17). Status: open.
- D-001 and D-002: status lines appended in U0, answered by
  `meta/decisions/decisions-2026-10-12.md` (decisions 1 and 2).
- No other finding and no hands finding (HF) was filed by a unit of this
  mission (`git log 1151e55..HEAD -- meta/findings/FINDINGS.md` shows U0
  only).

## Review items

REVIEW-1 (`meta/reviews/REVIEW-1.md`), `## Should-fix`.

| Item | Review | Resolution | Sha |
|---|---|---|---|
| 1 | Crash between month-file rename and index write locks the instrument; no `fsync`; NaN accepted | U1, decisions 5 and 6 (interrupted append completed, `store_recovered` notice per decision 16, `fsync` file and directory, non-finite bars refused) | f3f8c2d |
| 2 | `synth.py` hard-codes result-moving generator settings | U3, decision 10 (seven `[source]` keys, mission 1's values in the fixtures) | cb9c21d |
| 3 | I-14 refusal depends on the editable install; `--state ""` accepted | U2, decision 7 | 8e423c1 |
| 4 | Gap check scans history past D; `gaps.jsonl` append not atomic | U1, decisions 3 and 4 (with decision 2 for the window fraction) | f3f8c2d |
| 5 | Provenance strings of the eight instrument records read stronger than the report | finding D-003, owner's (decision 17) | 87d4a23 |
| 6 | Frozen-config drift check compares with Python `==`; removal unapprovable | U2, decision 8 | 8e423c1 |
| 7 | `scripts/gate M0 <item>` prints `gate M0: PASS`; `gate_m0` without `gate` unenforced | U2, decision 9 | 8e423c1 |
