VERDICT: mission 6 finished

# FINAL REPORT — mission 6 (roadmap step S0.4 repaired, closes M0)

Builder prompt: `meta/BUILDER-6-PROMPT.md`. Base 19196da. This mission
repairs step S0.4 and closes milestone M0. It takes REVIEW-5 blocker 1,
REVIEW-5 should-fix 1 with finding D-005, REVIEW-5's note on D-004 and its
note on `tests/test_gate_script.py`, then runs the M0 gate again. It binds
`meta/decisions/decisions-2026-10-12.md` (cited below as "decision N";
items 41 to 46 are new).

## What changed

| Unit | Sha | Commit |
|---|---|---|
| U0 plan files, D-004..D-006 status lines | cdc031f | plan: mission 6 plan (S0.4 repaired, closes M0) |
| U1 G0.1: every field of `backtest --json` | c1a2100 | gates: G0.1 compares every key of backtest --json |
| U2 calc self-test: a position that changes at the roll | 9ca8575 | gates: G0.1 calc self-test holds a position that changes at the roll |
| U3 roll timing in unit tests and in G0.1 (roll probe) | 9e16050 | gates: G0.1 compares a roll probe whose position changes at the SYNA roll |
| U4 `tests/test_gate_script.py` under load | b268252 | tests: test_gate_script.py runs one-item gate on G0.4, timeout 1200 s |
| U5 gate run | 65718c5 | gate M0 run at this tip (output below; recorded by the meta commit dafd091) |
| U6 final report | this commit | report: mission 6 final report |

The `meta:` commits between units (81f2ae6, 230b4a1, d948c89, 65718c5,
dafd091) are checkpoint, journal and plan bookkeeping. Each unit commit's
body lists its files, the choices made where DESIGN and the decisions are
silent, and the wrong changes made and reverted; those bodies are the
authority for this summary.

No product code changed in this mission: no test of U1 to U4 found a
defect under `src/`, and `tests/gates/independent_calc.py` needed no fix
(U2's new hand cases agreed with it; U3's probe found no mismatch). There
was no fix commit.

Files changed: `tests/gates/test_g0_1_reference.py` (U1, U3),
`tests/gates/test_g0_1_calc_self.py` (U2), `tests/test_executor.py`,
`tests/test_metrics.py`, `tests/fixtures/strategies/roll_probe.py` (new)
(U3), `tests/test_gate_script.py` (U4), and `meta/` files.

Assertions of existing tests that changed, each named in its unit's body:
- U1: `test_backtest_json_equals_the_module` keeps every assertion it had,
  runs over a fourth `--json` case (LOW, below), and also compares
  `trades`, `fragile` and `days` with the independent calculation
  (decision 42). Additions only.
- U3: the per-bar, daily-series, metric and cost-total tests of
  `test_g0_1_reference.py` run over a fourth subject, `roll_probe.py`,
  through the module API (decision 21: `backtest` takes `reference/` files
  only). Additions only.
- U4: `test_one_item_run_never_prints_the_milestone_verdict` runs `M0 G0.4`
  instead of `M0 G0.3`, with the same assertions; the gate subprocess
  timeout goes from 600 s to 1200 s (decision 45).

`git diff 19196da HEAD -- config/ tests/fixtures/config_frozen.json
tests/fixtures/config/` is empty: no frozen value and no fixture record
changed. The one new fixture is `tests/fixtures/strategies/roll_probe.py`.

## Gate

`./scripts/gate M0` at 65718c5 (`65718c5c2c01ef05489c67b49ad9f5ccc8e8d983`),
the pushed tip after U4, run in the foreground with the tree clean and
equal to `origin/main`; pasted verbatim from `meta/drafts/gate-M0-mission6.txt`.
Every commit after 65718c5 (dafd091 and this one) touches only `meta/`.
Before it, `./scripts/check` printed `check: green` three times in a row at
65718c5 (orchestrator runs).

```
G0.1 PASS 62 passed in 63.50s (0:01:03)
G0.2 PASS 7 passed in 119.49s (0:01:59)
G0.3 PASS 13 passed in 171.31s (0:02:51)
G0.4 PASS 4 passed in 0.25s
gate M0: PASS
```

Exit status 0; wall time 5 min 57 s. Each item finished well under 15
minutes. Every gate test carries the markers `gate` and `gate_m0`, writes
state only under a pytest temporary directory, runs `discotrade`
in-process through `discotrade.cli.main` or the module API, and launches
no subprocess.

### G0.1 — `tests/gates/test_g0_1_calc_self.py`, `tests/gates/test_g0_1_reference.py`

DESIGN §18.3: the three reference strategies, run on `test_mixed` (one
instrument that rolls, one that cannot be shorted, one with a proportional
fee, with dropped bars), give per-bar gross and net at 1x and 2x, every
cost component and every §8 metric equal, to 1e-12, to an independent
calculation that imports nothing from `discotrade`, written by a sub-agent
of its own told not to open the modules it checks.

- `test_g0_1_calc_self.py`: everything listed in FINAL-REPORT-5, plus
  (U2, decision 43 (a)) scenario E, two hand cases with their derivation
  in comments: a carried position changing sign at a roll (gap +10,
  `h(u-1) = 1`, `h(u) = -0.5`) and a flat position opening at a roll
  (gap -5, `h(u-1) = 0`, `h(u) = 0.5`). Each checks every row field, the
  roll bar's `roll`, `cost`, `net_1x` and `net_2x`, both daily series,
  `trades`, the roll cost total and `breakeven_cost` with its rolled
  turnover `2 * |h(u-1)|`. The calculation's roll cost on `h(u)` and its
  rolled turnover on `h(u)` each fail both cases (made and reverted).
- `test_g0_1_reference.py`: everything listed in FINAL-REPORT-5, plus:
  - (U1, decision 42) for each reference strategy, and for LOW
    (`zscore_reversal.py` over 2019-03-23 to 2019-03-24, where SYNX's
    last-bar target is below every earlier position and SYNA and SYNL have
    no window bar), the keys of the `backtest --json` object, of its cost
    map and of each per-instrument map are exactly the compared keys; the
    metrics with `days`, the subject's cost totals and the descriptive keys
    (`strategy`, `params`, `track`, `from`, `to`, `cost_model`,
    `config_hash`) equal their sources; each instrument's `bars`, `trades`,
    `position_min`, `position_max`, `fee`, `spread`, `slippage`, `roll`,
    `cost`, `net_1x`, `net_2x` equal the figures computed in the test from
    the module's per-bar rows and from the independent calculation's rows
    (counts exactly, reals by decision 39).
  - (U3, decision 43 (c)) `roll_probe.py` is compared with the independent
    calculation on the same window and fields as the reference strategies
    (every per-bar field, both daily series, every §8 metric, the cost
    totals by component, decision 39), and a test asserts that at the SYNA
    roll bar 2019-06-14T00:00Z of the window `h(u-1) = 1.0` and
    `h(u) = -0.5` in both discotrade's and the calculation's rows.

### G0.2 — `tests/gates/test_g0_2_cheating.py`

Unchanged in this mission; what it asserts against DESIGN §18.3 ("a
cheating strategy ... cannot gain: its positions pass truncation
invariance, and its score on a window is the same whether or not later
bars exist in the store") is as FINAL-REPORT-5 states: the text passes the
loader and reaches later rows through kept frames, `iloc` views' `base`
and `attrs` when called directly; on `test_mixed` its per-bar rows up to
`t` are equal between a store ending at `t` and a long store for at least
ten `t` per instrument, and its rows and metrics are identical with and
without later bars; a control given the next close gains.

### G0.3 — `tests/gates/test_g0_3_store.py`

Unchanged in this mission; as FINAL-REPORT-5 states: the store refuses a
bar not closed and a bar not later than the last, leaving the state
directory byte-identical; old rows unchanged by an append; `gaps.jsonl`
holds exactly the generator's dropped bars and none in a daily break,
weekend or closure; the SYNA adjusted series as of each bar equals the
underlying plus the current contract's constant (§17.1); a carried
position pays `2 * |h(u-1)| * c(u)` at the roll and a flat one pays none.

### G0.4 — `tests/gates/test_g0_4_config.py`

Unchanged in this mission; as FINAL-REPORT-5 states: `discotrade config
check --track hourly` exits 0 and lists exactly the eight instruments of
the track; no file under `src/` contains, as a whole word, a symbol,
contract root or venue collected from `config/` (I-9).

## Correction of FINAL-REPORT-5

FINAL-REPORT-5 states, under G0.1, that "the `--json` figures equal the
module's". That claim was not held by its test at bf943a4: REVIEW-5
blocker 1 showed that `test_backtest_json_equals_the_module` compared the
metrics and the subject's cost totals but not the per-instrument maps'
`trades`, `position_min`, `position_max` or `net_1x`/`net_2x`, nor that no
other key was present, so a `cli.py` that took `position_max` as the min,
set `net_1x` to 999.0 or `trades` to -1 passed. The claim is held from
c1a2100 on: U1 compares every key decision 42 lists and asserts the key
sets are exactly those, and each of those three changes, `position_min`
taken from `h` only, and an extra per-instrument key fails the test (made
and reverted).

## Mismatches found and how they were settled

None. U2's new hand cases agreed with `independent_calc.py`; U3's probe
gave equal figures from discotrade and the calculation on every compared
field; no test found a product defect. The mismatch rule of U3 was not
invoked.

## What the tests prove

Taken from each unit's commit body; on the cases named there and above.

- U1: the G0.1 `--json` statements above. Seen to fail (made in `cli.py`
  and reverted): `position_max` taking the min (4 failures), `net_1x` set
  to 999.0 (4), `trades` set to -1 (4), `position_min` from `h` only (1,
  on LOW only), an extra key in each per-instrument map (4).
  `./scripts/gate M0 G0.1` passed (55 tests).
- U2: on its two constructed stores the calculation charges the roll cost
  and counts the rolled turnover on `h(u-1)`; with either on `h(u)` (made
  and reverted at `independent_calc.py:342` and `:352`) both new cases
  fail. Existing self-test cases unchanged.
- U3: in `tests/test_executor.py` an order at a roll bar pays roll
  `2 * |h(u-1)| * c(u)` for a carried position changing (-0.5 to 1.0) and
  0 for a flat one opening (0 to 1.0), in the order and in the per-bar
  rows; in `tests/test_metrics.py` `breakeven_cost` adds rolled turnover
  `2 * |h(u-1)|` (1.0 and 0 for the two cases). Seen to fail (made and
  reverted in product code): the roll cost on `order.target` in
  `executor.py` fails the four new executor cases, one existing executor
  test, and the probe's G0.1 per-bar rows (SYNA 2019-06-14T00:00Z roll
  1.117e-4 against 2.234e-4), daily series, metrics and cost totals; the
  rolled turnover on `h` in `metrics._breakeven_cost` fails both new
  metrics cases and the probe's G0.1 `breakeven_cost` (-0.41151 against
  -0.41142). G0.1 passed (62 tests).
- U4: no `./scripts/gate` subprocess of `tests/test_gate_script.py` runs a
  minutes-long item, and none has a timeout below 1200 s; the file ran in
  180.20 s before and 11.26 s after on the same machine; with
  `scripts/gate` made to print PASS for every item (made and reverted) the
  file fails (3 tests).
- The gate run at 65718c5: `./scripts/check` green three times;
  `./scripts/gate M0` prints `G0.1` to `G0.4 PASS` and `gate M0: PASS`,
  exit 0, in 357 s.

## NOT PROVEN

New in this mission:
- The half-tick spread floor is proven by unit tests on each side (the
  product's unit tests and the calculation's self-test), not through
  G0.1: every fixture spread of `test_mixed` is at least one tick
  (decision 43).
- The roll timing is shown through G0.1 by a test-only probe
  (`roll_probe.py`, target by hour parity) on one roll bar
  (SYNA 2019-06-14T00:00Z) of one window; the reference strategies still
  hold the same position across both SYNA rolls. The probe is compared
  through the module API, not `backtest --json` (decision 21). Slippage
  at a roll bar is not separately checked in U2's hand cases (slippage 0).
- The calculation's independence for U2 rests on its sub-agent's
  statement in the 9ca8575 body that it opened none of the forbidden
  files; no test checks that.
- U1: `position_min`/`position_max` are tested as the lowest and highest
  of every window `p` and `h`, as `cli.py` computes them; decision 42
  names the keys without defining them. `position_min` from `h` only is
  seen only through the added LOW case, not on the G0.1 window. Wrong
  changes to top-level keys other than an added key were not tried.
- U4: that `tests/test_gate_script.py` stays green under any given load
  is not proven; its scratch-pytest helper subprocesses (not
  `./scripts/gate`) keep 120 s timeouts, outside decision 45.
- Finding D-006 (`backtest` shares one loaded strategy across a subject's
  instruments) is deferred to S2.1 (decision 44) and not exercised.

Carried from FINAL-REPORT-5, updated:
- The calculation's authors (mission 5 U3, de9fc09, mission 6 U2) worked
  from DESIGN and the decisions, which were written while the code existed;
  a misreading shared by the text and the code would be shared by both
  sides. The calculation shares with the code the synthetic bars, roll
  records and the strategy callable from discotrade's loader; a defect
  there is common to both and G0.1 cannot see it. The U3 author's choices
  where DESIGN is silent (`trusted_from` as midnight UTC, the main-session
  and trading-date rules) agree with the code on `test_mixed` only.
- G0.1 is shown on one fixture track and one window (plus U1's LOW
  window for `--json`). D-005's roll-timing half is now resolved as above;
  its half-tick floor half stays as stated.
- G0.2 covers what §12.1 lets a text reach, not interpreter escapes
  (G2.1's, decision 40); SYNL's control shows only a higher gross;
  truncation invariance at ten or more `t` per instrument on one 29-day
  window.
- G0.3 takes the underlying series and dropped bars from product code of
  the synthetic source; G0.4's whole-word match is case-insensitive,
  skips `__pycache__`, and scans names found in `config/` only.
- Every cost value is from SPEC §17, the DESIGN §4.2 example or the R-5
  reading, `verified = false`, none measured; fixture costs and SYNA's
  spread table are invented; the reference strategies' and the probe's
  results mean nothing about any market. `config check` reports 168
  unverified values; finding D-003 stays.
- Carried by `meta/BACKLOG.md`: the I-11 socket backstop's scope (to
  S1.1); an unlisted month file inside the window not driven through
  `backtest`.
- What remains of mission 4's and mission 3's NOT PROVEN, as listed in
  FINAL-REPORT-5, is unchanged by this mission.

Resolved by this mission: the `--json` figures equal the module's on every
key (from c1a2100); the roll cost and rolled-turnover timing on `h(u-1)`
is shown in the calculation's self-test, the product's unit tests and G0.1.

## Findings filed and answered

- D-004: answered, decision 41 (status line appended in U0, cdc031f).
- D-005: answered, decision 43 (status line in U0); carried out by U2 and U3.
- D-006: deferred to S2.1, decision 44 (status line in U0).
- No new finding was filed. No hands finding was filed; HF-006 stays open
  (every `./scripts/check` and `./scripts/gate` run of this mission was in
  the foreground with a timeout of at least 20 minutes, and no unit
  reported a run moved to the background).

## Review items

| Item | Review | Resolution | Sha |
|---|---|---|---|
| REVIEW-5 blocker 1 | G0.1's `backtest --json` test did not compare every field the object carries | U1, decision 42 (every key of the object and of each per-instrument map compared, key sets asserted exact; REVIEW-5's three `cli.py` changes, `position_min` from `h` and an extra key fail) | c1a2100 |
| REVIEW-5 should-fix 1 (with D-005) | The roll cost's timing on `h(u-1)` is not visible to the calculation's self-test, the unit tests or G0.1 | U2 (self-test hand cases, decision 43 (a)) and U3 (unit tests and `roll_probe.py` in G0.1, decision 43 (b), (c)) | 9ca8575, 9e16050 |
| REVIEW-5 note on D-004 | `max_drawdown`'s starting 0 as a peak | Recorded answered, decision 41; already held by `metrics.py` and the calculation (de9fc09) | cdc031f |
| REVIEW-5 note on `tests/test_gate_script.py` | Its one-item gate subprocess ran a minutes-long item under a 600 s timeout and could turn `./scripts/check` red under load | U4, decision 45 (runs `M0 G0.4`, timeout 1200 s, file 180 s to 11 s) | b268252 |

VERDICT: mission 6 finished
