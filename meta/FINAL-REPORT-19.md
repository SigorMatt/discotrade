VERDICT: mission 19 finished

# FINAL REPORT — mission 19 (roadmap step S4.1: alert rules, alert state and the dashboard, under O-23 to O-25)

Brief: `meta/BUILDER-19-PROMPT.md`. Base 031f5e4 (`plan: mission 19 kit (S4.1,
alerts and dashboard under O-23 to O-25)`). Owner's rulings:
`meta/decisions/2026-10-17-owner.md` (O-23 to O-25). Decisions:
`meta/decisions/decisions-2026-10-17-m19.md` (146 to 154), with items 1 to 145 and
the owner's earlier files still binding. This mission closes no milestone and moves
no gate of M4 (decision 146). Under O-25 the met gates whose tests read a function
this mission changed were run again at the pushed tip ef9359f, nothing uncommitted
but the git-ignored drafts: gate M1 item by item, then M3, M2 and M0. All passed.
G1.3 took 1049 s, above O-3's 10 minutes. That is recorded in the D-014 times line
(d1f4b81) and no test was weakened. Container runtime: docker. Image:
`discotrade-sandbox:3b7d75c39621` (present, nothing built, at every unit and at the tip).

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | e0d19df | `plan:` the plan, checkpoint and journal. FINDINGS.md gains the HF-006, HF-012 and HF-010 status lines and the new HF-013 and HF-014 (decision 154 (b)) |
| U1 | 27a83b9 | `table:` `stats.control_moments(paper, days, column="net_1x")` (147 (a)). `paper.adjusted` gains the optional `exposure` (147 (d)). New `table.adjusted_deflated`: `adjusted_S`, `adjusted_E_N` and `adjusted_excess` on every row, null on control and portfolio rows, with `table.md` columns labelled adjusted (148). Register: the three `pending` entries are settled and `table.adjusted_deflated` is added (147 (c)). `tests/test_return_readers.py`: `PENDING` empty, test renamed. G1.3: decision 148 (d)'s one line |
| U2 | a7854da | `stats:` new `src/discotrade/alerts.py` with `rank_rows`, which gives each rank row `timing` and `gross` beside decision 59's `statistic` (149 (a)). `daily._rank_persistence` calls it (149 (b)). `stats.t_sf`, the one-sided upper tail of Student's t (150). Register: `alerts.rank_rows`, `timing_gross` |
| U3 | efc35de | `alerts:` `persistent_approach`, `group_edge`, `bootstrap` and `slot_series` on the exposure-adjusted series (151). `paper.clean_members` (151 (b)); `paper.portfolio` is unchanged. Register: four entries, `adjusted`. Finished from the earlier session's tree under §R |
| U4 | 3ee67d3 | `alerts:` the alert state, firing and payloads (152 (a), (b)); the `rank_persistence` rule on `timing` (152 (c)) and the `revival` rule (152 (d)); the health alerts, the `few_valid_candidates` and `cost_stale` detectors, and `no_finding`, which the day loop does not call (152 (e)); step 6 in `daily.py` on a new day only (152 (f)). No register entry |
| U5 | a21beb7 | `dashboard:` new `src/discotrade/dashboard.py`. Step 7 writes `dashboard/<track>/index.html` into staging on a new day only. `discotrade dashboard [--out PATH]`. `config.load_gates`. New `config/gates.toml`, both owner flags `false` (153 (b)). Register: one `stage3_money` entry and five `display` entries. `test_no_entry_is_stage3_money_yet` becomes `test_the_one_stage3_money_entry_is_the_dashboards` (153 (c)) |
| U6 | d1f4b81 | `meta:` the regression gates at the pushed tip ef9359f; a D-013 times line and a D-014 times line in FINDINGS.md (154 (c), (d)) |
| U7 | this commit | this report |

Meta commits: 8abeb5c (U0 done), bca3f6a (U1 done), f3dd7a0 (U2 done), 067405a (U3
done), 36009f6 (U4 done), ef9359f (U5 done), e2bde18 (U6 done). Each unit commit's
body lists its files.

Files changed in the mission outside `meta/` (`git diff --name-status 031f5e4 e2bde18`):
- new: `config/gates.toml`, `src/discotrade/alerts.py`, `src/discotrade/dashboard.py`,
  `tests/test_alerts.py`, `tests/test_dashboard.py`;
- changed: `src/discotrade/cli.py`, `config.py`, `daily.py`, `paper.py`, `stats.py`,
  `table.py`; `tests/fixtures/return_readers.toml`, `tests/gates/test_g1_3_lifecycle.py`
  (one line), `tests/test_cli.py`, `test_daily.py`, `test_paper.py`,
  `test_portfolio.py`, `test_rank_daily.py`, `test_return_readers.py`,
  `test_stats.py`, `test_table.py`.

Tests the check runs went from 2364 to 2458 (+94; 204 gate tests deselected, as at
mission 18).

## Check

`./scripts/check` wall times on the builder's machine (four cores, shared). Each run
was its own foreground call with a 20-minute timeout.

| Where | Runs |
|---|---|
| mission 18's tip d8a129a (FINAL-REPORT-18) | 919, 922, 931 s (pushed tip e9076d5: 917, 921, 926 s) |
| U1 27a83b9 | 1121, 1128, 1125 s |
| U2 a7854da | 1153, 1072, 1185 s |
| U3 efc35de | 1019, 1000, 997 s |
| U4 3ee67d3 | 1069, 1058, 1055 s |
| U5 a21beb7 | 1060, 1060, 1061 s |
| **tip ef9359f (U6)** | **1066, 1079, 1131 s**, each `check: green` |

Every tip run printed `2458 passed, 204 deselected`, with 0 skipped, so the
`container` tests ran on discotrade-sandbox:3b7d75c39621. Each also printed
`config check: ok, 173 unverified values` and `check: green`. Pytest took 1063.69 s,
1075.34 s and 1127.53 s. Outputs are in `meta/drafts/u6-check-<n>.txt`; each file's
first line is `HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6` and it ends with
`rc=0` and the wall time.

No run passed the 20-minute cap and none was moved to the background. All three are
above HF-006's 15 minutes (D-013 open), and 135 to 214 s above mission 18's tip runs.
Mission 19 added 94 tests to the check. U1's body credits about +195 s to the
table's `paper.adjusted` calls, but does not prove it (NOT PROVEN). Load average was
about 1.2 to 2.2 (D-013 times line).

## Gate

Regression gates under O-25 (decisions 146 (a), 154 (d)). Every run was at the pushed
tip ef9359f4ce54cde1efa1982090da5c6fb1950ef6 (U5 done), with no uncommitted file but
the git-ignored drafts, after `./scripts/check` was green three times there. Each
was its own foreground call with a 20-minute timeout. The tip differs from a21beb7
(U5's commit) only by `meta/CHECKPOINT.md`, `meta/journal.md` and `meta/plan.md`.
This report's parent e2bde18 differs from ef9359f only by those three files and
`meta/findings/FINDINGS.md`.

`uv run discotrade sandbox build` (`meta/drafts/u6-sandbox-build.txt`, verbatim):

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
sandbox build: present, nothing built
discotrade-sandbox:3b7d75c39621
rc=0
wall=0s
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6 (step 3, after the checks)
sandbox build: present, nothing built
discotrade-sandbox:3b7d75c39621
rc=0
wall=1s
```

### Gate M1

Item by item (O-2). Each output below is verbatim from `meta/drafts/u6-gate-M1-<item>.txt`.

`./scripts/gate M1 G1.1`: wall 411 s (mission 17 U5: 450 s)

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
G1.1 PASS 6 passed, 1 warning in 410.20s (0:06:50)
gate M1 G1.1: PASS
rc=0
wall=411s
```

`./scripts/gate M1 G1.2`: wall 280 s (mission 17 U5: 204 s)

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
G1.2 PASS 4 passed in 278.60s (0:04:38)
gate M1 G1.2: PASS
rc=0
wall=280s
```

`./scripts/gate M1 G1.3`: wall 1049 s (mission 17 U5: 542 s)

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
G1.3 PASS 10 passed in 1048.60s (0:17:28)
gate M1 G1.3: PASS
rc=0
wall=1049s
```

`./scripts/gate M1 G1.4`: wall 1 s (mission 17 U5: 1 s)

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
G1.4 PASS 15 passed in 0.52s
gate M1 G1.4: PASS
rc=0
wall=1s
```

| Item | mission 17 U5 | the units' own runs | tip ef9359f |
|---|---|---|---|
| G1.1 | 450 s | U2 a7854da: 424 s (`6 passed, 1 warning in 423.55s`) | 411 s |
| G1.2 | 204 s | U4 3ee67d3: 260 s (`4 passed in 258.99s`) | 280 s |
| G1.3 | 542 s | U1 27a83b9: 855 s (`10 passed in 854.22s`); U4 3ee67d3: 962 s (`10 passed in 960.49s`) | 1049 s |
| G1.4 | 1 s | U1 27a83b9: 1 s (`15 passed in 0.62s`) | 1 s |

G1.3 is above O-3's 10 minutes at U1, U4 and the tip. It finished within its
20-minute call, so it is PASS under O-2. It is recorded in the D-014 times line
(d1f4b81) and no test was weakened (decision 154 (c)). Why it doubled was not
measured per test (NOT PROVEN).

### Gate M3

`./scripts/gate M3` at ef9359f: wall 547 s (mission 18 at e9076d5: 513.94 s)
(`meta/drafts/u6-gate-M3.txt`, verbatim):

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
G3.1 PASS 3 passed in 212.89s (0:03:32)
G3.2 PASS 9 passed in 165.95s (0:02:45)
G3.3 PASS 10 passed in 166.07s (0:02:46)
gate M3: PASS
rc=0
wall=547s
```

### Gate M2

`./scripts/gate M2` at ef9359f: wall 130 s (`meta/drafts/u6-gate-M2.txt`, verbatim):

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
G2.1 PASS 36 passed in 41.19s
G2.2 PASS 3 passed in 24.06s
G2.3 PASS 8 passed in 3.56s
G2.4 PASS 9 passed in 39.06s
G2.5 PASS 5 passed in 19.60s
gate M2: PASS
rc=0
wall=130s
```

### Gate M0

`./scripts/gate M0` at ef9359f: wall 245 s (`meta/drafts/u6-gate-M0.txt`, verbatim):

```
HEAD ef9359f4ce54cde1efa1982090da5c6fb1950ef6
G0.1 PASS 62 passed in 57.18s
G0.2 PASS 7 passed in 88.91s (0:01:28)
G0.3 PASS 13 passed in 95.16s (0:01:35)
G0.4 PASS 4 passed in 0.69s
gate M0: PASS
rc=0
wall=245s
```

No M3, M2 or M0 item took above 15 minutes. (`meta/drafts/` also holds older
`u6-G1.*.txt` and `u6-M0.txt` files dated 2026-10-14, run at 23f245c. They belong to
an earlier mission's U6 and are not this mission's.)

## Owner rulings applied

### O-23: the table keeps its plain deflated figures and gains adjusted ones

What was built (U1, 27a83b9):
- `table.adjusted_deflated` adds `adjusted_S`, `adjusted_E_N` and `adjusted_excess`
  to every approach row: the Sharpe of the approach's `paper.adjusted` net 1x
  series over its paper days, `E(N)` from `stats.control_moments(..., column=...)`
  over the random slots' adjusted series (each slot with its own average positions),
  and their difference. All three are null on control and portfolio rows.
- `S`, `E_N` and `excess` are unchanged.
- `table.md` heads the new columns adjusted.

The tests that hold it:
- `tests/test_table.py`:
  - `::test_the_adjusted_deflated_figures_are_the_tests_own_and_differ_from_the_plain`
  - `::test_adjusted_s_is_the_rows_adjusted_sharpe`
  - `::test_the_adjusted_deflated_figures_are_null_on_controls_and_portfolio_rows`
  - `::test_table_md_heads_the_adjusted_deflated_columns_adjusted`
  - `::test_each_approach_row_holds_its_adjusted_figures_over_all_its_paper_days`
- G1.3's `tests/gates/test_g1_3_lifecycle.py::test_table_matches_a_hand_count`
  still compares every field it lists, `S`, `E_N` and `excess` included, at their
  old values. G1.3 PASS at the tip.

The G1.3 line, `tests/gates/test_g1_3_lifecycle.py` line 643, is the only change
under `tests/gates/` (`git diff 031f5e4 HEAD -- tests/gates/`).

Before (031f5e4):

```
        assert set(g) == set(w), g["subject"]
```

After (27a83b9):

```
        assert set(g) == set(w) | {"adjusted_S", "adjusted_E_N", "adjusted_excess"}, g["subject"]
```

27a83b9's body quotes O-23's sentence that permits it.

### O-24: the two pending readers are not changed; the rules get their own functions

What was built:
- U1, 27a83b9: `stats.control_moments` gains `column`, default `net_1x`.
- U2, a7854da: `alerts.rank_rows` calls the unchanged `stats.rank_persistence`
  three times, on a frame whose `timing` column holds each candidate's
  `paper.adjusted` gross per day (each block its own window), on `gross`, and on
  the default `net_1x`. Each rank row is decision 59's net row with `timing` and
  `gross` added.
- U3, efc35de: the `adjusted` rule functions.
- U4, 3ee67d3: the `rank_persistence` rule reads `timing`.
- `git diff 031f5e4 HEAD -- src/discotrade/stats.py` shows no line of
  `rank_persistence` changed.

The tests that hold it:
- `tests/test_stats.py::test_control_moments_read_net_1x_by_default_and_the_named_column_when_given`
  (U1).
- `tests/test_return_readers.py::test_no_entry_carries_pending` and
  `::test_the_audit_passes` (U1, and every unit after).
- `tests/test_alerts.py::test_the_row_holds_timing_and_gross_beside_decision_59s_net_statistic`
  and `::test_a_constant_position_approach_has_a_timing_return_of_zero_on_every_day`
  (U2).
- `tests/test_rank_daily.py::test_monday_appends_block_2s_row_over_the_live_and_dormant_approaches`
  (U2; its exact key set admits `timing` and `gross`, and it asserts both values).
- `tests/test_alerts.py::test_rank_persistence_reads_timing_not_the_net_statistic`
  (U4).
- G1.1 and G1.4 PASS, unedited, at the tip.

Register entries, before (031f5e4), the three `pending = "S4.1"` entries:

| Entry | class at 031f5e4 | class at e2bde18 |
|---|---|---|
| `discotrade.stats.rank_persistence` | `timing_gross`, pending S4.1 | `producer`, no pending |
| `discotrade.stats.control_moments` | `adjusted`, pending S4.1 | `producer`, no pending |
| `discotrade.table.build.approach_row` | `adjusted`, pending S4.1 | `display`, no pending (note: the plain `S`, `E_N`, `excess`) |

After, the classified readers O-24 names: `discotrade.table.adjusted_deflated`
`adjusted` (U1); `discotrade.alerts.rank_rows` `timing_gross` (U2);
`discotrade.alerts.persistent_approach`, `group_edge`, `bootstrap` and
`slot_series` `adjusted` (U3). The register's header sentence now reads "No entry
carries pending since step S4.1".

The rank row's keys (`rank_persistence.jsonl`):
- before (031f5e4, `stats.rank_persistence`'s row as `daily._rank_persistence`
  appended it): `block`, `first`, `last`, `previous_first`, `previous_last`,
  `subjects`, `size`, `statistic`;
- after (a7854da onward, `alerts.rank_rows`): the same eight, plus `timing` and
  `gross`. `statistic` keeps its meaning (net 1x, decision 59).

### O-25: add, never replace; met gates run again

What was built: every unit added a parameter, a field or a function:
- `control_moments`'s `column` and `paper.adjusted`'s `exposure`, each with
  today's result by default;
- three table fields; two rank-row keys;
- new `alerts` and `dashboard` modules;
- `paper.clean_members` with `paper.portfolio` unchanged.

No test of a met gate was edited but decision 148 (d)'s line, and no unit stopped
under decision 146 (b). U6 (d1f4b81) ran gate M1 item by item, then M3, M2 and M0,
at the pushed tip ef9359f (`## Gate`).

The tests that hold it:
- the gates themselves, unedited;
- `tests/test_stats.py::test_control_moments_read_net_1x_by_default_and_the_named_column_when_given`
  (default unchanged);
- `tests/test_paper.py::test_adjusted_given_the_exposure_records_already_read_equals_the_call_without`
  (147 (d));
- `tests/test_portfolio.py::test_clean_members_are_the_members_portfolio_clean_counts`.

## Register

Every entry of `tests/fixtures/return_readers.toml` added or changed by this mission
(`git diff 031f5e4 HEAD -- tests/fixtures/return_readers.toml`):

| Entry | Class | Unit | Change |
|---|---|---|---|
| `discotrade.stats.rank_persistence` | `producer` | U1 27a83b9 | changed: was `timing_gross`, pending S4.1 |
| `discotrade.stats.control_moments` | `producer` | U1 27a83b9 | changed: was `adjusted`, pending S4.1 |
| `discotrade.table.build.approach_row` | `display` | U1 27a83b9 | changed: was `adjusted`, pending S4.1 |
| `discotrade.table.adjusted_deflated` | `adjusted` | U1 27a83b9 | new |
| `discotrade.alerts.rank_rows` | `timing_gross` | U2 a7854da | new |
| `discotrade.alerts.slot_series` | `adjusted` | U3 efc35de | new |
| `discotrade.alerts.persistent_approach` | `adjusted` | U3 efc35de | new |
| `discotrade.alerts.group_edge` | `adjusted` | U3 efc35de | new |
| `discotrade.alerts.bootstrap` | `adjusted` | U3 efc35de | new |
| `discotrade.dashboard.stage3_money` | `stage3_money` | U5 a21beb7 | new (the only `stage3_money` entry) |
| `discotrade.dashboard.exposure_part` | `display` | U5 a21beb7 | new (O-14) |
| `discotrade.dashboard.portfolio_chart` | `display` | U5 a21beb7 | new |
| `discotrade.dashboard._portfolio_panel` | `display` | U5 a21beb7 | new |
| `discotrade.dashboard.rank_chart` | `display` | U5 a21beb7 | new (O-6) |
| `discotrade.dashboard._rank_panel` | `display` | U5 a21beb7 | new (O-6) |

U1 also changed the header comment: "No entry carries pending since step S4.1".

U4 added and changed no entry. Its body says the new functions hold none of the
audit's reference shapes (`test_the_audit_passes` green). The `rank_persistence` rule
reads the rows' `timing`, whose series binding is `alerts.rank_rows`.

`paper.portfolio` and `paper._series` stay `producer` (decision 153 (c)).
`tests/test_return_readers.py::test_the_one_stage3_money_entry_is_the_dashboards`
asserts exactly one `stage3_money` entry and that both stay `producer`.

## Speed

Seconds per replay day of the G1.3 scenario's first 30 calendar days, by decision
80 (d)'s method:
- init-state, then replay `test_synth` 2019-06-03..2019-07-02 with
  `g1_lifecycle.jsonl` on the gate config;
- in-process, foreground, one call each;
- 22 replay days.

Figures are as each unit's body gives them:

| Unit | parent (sha) | at the parent | at the commit |
|---|---|---|---|
| U2 a7854da | bca3f6a (U1's tip) | 56.18 s, **2.554** s per day | 53.28 s, **2.422** s per day |
| U4 3ee67d3 | 067405a (U3's tip) | 47.63 s, **2.165** s per day | 55.43 s, **2.519** s per day |
| U5 a21beb7 | 36009f6 (U4's tip) | 56.39 s, **2.563** s per day | 55.99 s, **2.545** s per day |

Mission 18's tip: no figure. No measurement of seconds per replay day at mission 18's
tip (d8a129a, or the base 031f5e4) was made. FINAL-REPORT-18, the findings and the
decisions hold none for it. The earliest figure of this mission is U2's parent:
2.554 s per day at bca3f6a, U1's tip.

The figures are as measured, and they are not smoothed. Each pair was measured in a
separate session on a shared machine, and the parents' figures differ from the
figures of the commits before them:
- U4's parent 067405a gave 2.165 s, against U2's commit's 2.422 s. U3 between them
  added rules that the day loop does not call.
- U5's parent 36009f6 gave 2.563 s, against U4's commit's 2.519 s, with no code
  between them.

The run-to-run spread is therefore at least about 0.25 to 0.4 s per day, the size
of the differences measured.

Each body also reports:
- U2: the state directories differ only in `rank_persistence.jsonl`'s two added keys.
- U4: step 6 is about 15% of the day, almost all in `persistent_approach`'s
  `slot_series`; the state directories differ only by `alerts/test_synth/state.json`.
- U5: one render is 0.07 s; the state directories differ only by `dashboard/`.

## What the tests prove

Only what the tests assert, on their inputs. Every expected figure is computed by the
test. Rule tests run at the production thresholds read from `config/thresholds.toml`
through the loader.

U1 (27a83b9):
- `control_moments` gives today's result by default and the named column's moments
  when given.
- `paper.adjusted` with `exposure` equals the call without, for the subjects,
  columns and windows the test enumerates.
- On `test_mixed`, every approach row's `adjusted_S`, `adjusted_E_N` and
  `adjusted_excess` equal the test's own figures from the journal, bars and rolls,
  and differ from the plain ones.
- `adjusted_S` equals the row's adjusted Sharpe.
- The three fields are null on control and portfolio rows, and `table.md` heads
  them adjusted.
- Seen to fail, each made alone and reverted (148 (e)), each turning three tests
  red: slot moments on plain `net_1x`; one average position shared by all slots;
  `adjusted_excess` against the plain `E_N`.

U2 (a7854da):
- A constant-position approach's timing is within 1e-12 of 0 on every day.
- With six leaning approaches, `timing`, `gross` and `statistic` equal the test's
  Spearman figures to 1e-12.
- A re-append appends nothing.
- Empty and below-minimum populations give all three null.
- `t_sf` holds at the df 1, 2 and 3 closed forms, at the one-sided 5% critical
  values at df 5 and 11 to 1e-6, and in `t_sf(-t) = 1 - t_sf(t)`.
- Seen to fail: one window spanning both blocks; `timing` from plain gross;
  `statistic` replaced by timing; a two-sided `t_sf` (all 15 `t_sf` tests red).

U3 (efc35de):
- `persistent_approach`'s figures, threshold, `mu_c`, `sd_c`, `N`, `p(N)` and
  payload equal the test's.
- Each of these decides the condition: 59 against 60 clean days, the 2x Sharpe on
  either side of 0, and the 1x Sharpe on either side of the threshold.
- Exposed days are left out of W.
- A long-leaning approach with no timing does not meet the condition.
- `group_edge` is not evaluated at 119 dates and is evaluated at 120. Its figure,
  bootstrap quantile, seed, `k`, members and plain sum equal the test's. The
  quantile decides both sides. `k` is 3 at a mean of 2.5 and 2 at 299/120.
- `clean_members` equals the test's reading.
- Seen to fail: the five wrong changes of 151 (c).

U4 (3ee67d3):
- `rank_persistence`:
  - with 12 blocks at t = 1.795884819 ± 0.05, it is active only above, and its
    value and threshold match the test's to 1e-7;
  - it reads `timing`, not `statistic`;
  - with 11 blocks it is not evaluated.
- `revival` is active at 60 dormant weekdays and not at 59.
- An alert fires once while its condition stays true and again after it was false.
- The state's and payloads' paths and bytes match the test's, and a payload is
  never rewritten.
- Each of DESIGN §15.2's ten kinds fires from its event dated D.
- `few_valid_candidates` is tested at 13/14 days and 4/5 trials, `cost_stale` at
  90/91 days, and `no_finding` at twelve months, each at the function.
- The day loop writes `alerts/<track>/state.json` on each new day. A re-run of a
  finished day leaves its inode, mtime, every file and the commits as they were.
- Seen to fail: the four wrong changes of 152 (g).

U5 (a21beb7):
- Every panel heading is present in SPEC §13's order.
- No `<script`, `<link`, `http://`, `https://`, `@import`, `url(`, `src=`, `href=`
  or `<style>` appears.
- The viewport line appears once, and the title names D.
- Two renders of the same state are byte-identical and equal step 7's stored page
  and the stdout render.
- Thresholds:
  - each `data-threshold` value equals the value the alert code reads for its key;
  - every key of `alerts.THRESHOLD_KEYS` is shown;
  - the page follows a changed threshold, and its history entry is shown.
- The money condition equals the test's `fsum` of `portfolio_clean` `net_2x`, on
  both sides of `min_clean_days` and of 0.
- The `group_edge` and `rank_persistence` verdicts come from the alert state.
- The `journal_mismatch` count and the owner flags are shown, and a non-boolean
  owner flag is refused.
- The table panel's rows equal `table.json`'s.
- O-14's plain sum equals the test's, and static = plain − adjusted.
- Each new day's commit holds its page. A re-run writes no page.
- The command writes nothing in the state, refuses `--out` inside it, and exits 1
  with no journaled day.
- Seen to fail: the three wrong changes of 153 (d).

The gates (U6): G1.1 to G1.4 PASS, `gate M3: PASS`, `gate M2: PASS` and `gate M0:
PASS`, at the pushed tip ef9359f, with nothing uncommitted but the drafts.

The check and frozen files:
- `./scripts/check` was green three times at ef9359f, 0 skipped.
- `git diff --stat 031f5e4 e2bde18 -- src config tests/fixtures/rejected
  tests/fixtures/config tests/fixtures/config_frozen.json tests/gates` shows, under
  `config/`, only the new `config/gates.toml`. Under `tests/gates/` it shows only
  `test_g1_3_lifecycle.py`'s one line. Nothing under `tests/fixtures/rejected/`,
  `tests/fixtures/config/` or `tests/fixtures/config_frozen.json` changed.

## NOT PROVEN

Items of the U7 brief:
- **No finding alert fires on any replay a gate runs today.** The fixture models'
  cutoffs (2024 and 2026) make every approach observation of a replay over 2019
  exposed (DESIGN §11.3; `meta/BACKLOG.md`). So `persistent_approach`,
  `group_edge` and `rank_persistence`'s alert are proven by their unit tests at the
  production thresholds, not by a replay. G4.2 is step S4.3's. Likewise, no
  dashboard gate shows "pass" on a replay a gate runs.
- **The bootstrap's quantile and the t-test** (`stats.t_sf`, the bisection `t_crit`,
  the normal quantile) are proven against the values the tests compute, not
  against an outside statistics package. `t_sf`'s accuracy is shown only at the
  points tested (1e-12 there, 1e-6 at the two critical values). The p the page
  derives is not checked against an outside package either.
- **The dashboard's readability on a phone** is asserted by its viewport line and
  single max-width column only, not on a device.
- **`no_finding` is not called by the day loop** (decision 152 (e)). It is built
  and unit-tested at twelve months only. Its call is step S4.2's.
- **The speed figures are from the builder's machine** (four cores, shared, varying
  load):
  - The seconds per replay day were measured in separate sessions, and the parents'
    figures differ from the preceding commits' figures by up to about 0.4 s
    (`## Speed`).
  - No figure exists at mission 18's tip.
  - The check is 1066 to 1131 s at the tip, above HF-006's 15 minutes (D-013 open).

The units' own items:
- U1: that the check's rise of about +195 s comes only from the table's 51
  `paper.adjusted` calls per approach row per day. Its profile of one build:
  `adjusted_deflated` 1.19 s of 1.44 s.
- U1: decision 147 (d)'s equality beyond the subjects, columns and windows the test
  enumerates.
- U2: the rank rows' `timing` beyond the populations and windows the tests' states
  enumerate. Also, that the check's wall time change comes from U2.
- U4: `few_valid_candidates` and `cost_stale` raised by a day-loop run. Both are
  tested only as functions; the loop's appending of detector events is proven only
  through a health event of D.
- U4: the rules and detectors beyond the inputs the tests write.
- U5: O-14's adjusted sum and average positions are not asserted on the page against
  the test's own computation. Only the plain sum and plain − adjusted are asserted.
- U5: the portfolio band, the rank panel's running mean and the significance-band
  figures are not asserted.
- U5: the health panel shows `journal_mismatch` events in place of a recomputation
  record, which the state does not keep (U5's choice where the design is silent).
- U6: why G1.3 doubled (542 s at mission 17 U5 to 855 s at U1, 962 s at U4 and
  1049 s at the tip) was not measured per test (D-014 times line).
- G4.5, the dashboard's gate test over a replay's state, is step S4.3's.

What remains of FINAL-REPORT-18's NOT PROVEN, item by item:
1. No real provider, model or `claude` binary was called (L3, L4 not run): remains.
2. G3.3's leak checks cover the G3.1 replay's prompts on `test_synth` only, with
   no other track, profile version or coordinator: remains. G3.3 PASS at ef9359f;
   this mission changed no prompt code.
3. The value comparison of 142 (b) is at a relative 1e-9 and part (c) runs on three
   days and one cell per family: remains.
4. The corpus was written by the builder and its yield is arranged: remains.
5. The speed figures are from the builder's machine, with the check above 15
   minutes: remains, now 1066 to 1131 s (above).
6. U2's (mission 18) "a file listed with no `served` day" clause passes trivially:
   remains.
7. Mission 18 U2 maps call rows to files by the cursor: remains. REVIEW-18 note 3
   stands, 154 (a).
8. Mission 18 U1's wrong change 5 turned part (c) red only through the missing
   trial ledger: remains as recorded.
9. Mission 18's gate ran at e9076d5, not at that report's tip: superseded. This
   mission's gates ran at ef9359f, which differs from this report's parent e2bde18
   only under `meta/` (`## Gate`).
10. FINAL-REPORT-17's carried items, as mission 18 left them:
    - 17.1 (no real provider): remains.
    - 17.2 (the twenty replay days with the real pool are the owner's): remains.
    - 17.3 (`config/models.toml`'s base URL, model ids and cutoffs unverified):
      remains. This mission added no number from outside the project;
      `config/gates.toml` holds two `false` flags and no number.
    - 17.4 (every replay observation over 2019 exposed): remains. It is the reason
      no finding alert fires on a gate's replay (above).
    - 17.5 (scripted token counts estimated by rule): remains.
    - 17.6 (corpus arranged): remains.
    - 17.7 (the leak checks for symbols, venues, contract names and dates cover
      only the forms the test lists): remains.
    - 17.8 (`--provider openai` tested for its refusal only): remains.
    - 17.9 (speed from the builder's machine; check above 15 minutes): remains.
    - 17.10 (D-017): closed in mission 18.
    - 17.11 (the registry-sanitize wrong change red only in the direct test):
      remains.
    - 17.12 (`tests/test_gate_script.py`'s two "without gate tests" cases check
      M4, not M3): remains.
    - 17.13 (M2, M1 and M0 last run at 45dc893 with mission 17 U5's files
      uncommitted): **closed**. U6 ran M1 item by item, M2 and M0 at the pushed tip
      ef9359f with nothing uncommitted but the drafts.
    - 17.14 (the `## Corpus` and `## Day` figures measured only, beyond the
      served-file mapping): remains.
    - 17.15 (FINAL-REPORT-16's carried items): remain.
    - 17.16 (REVIEW-16 note 9's additions: the `doctor --live workers` refusal
      untested, to step S5.1; the doctor tests of mission 16 U1 never seen to
      fail; the check timings the builder's own): remain.
11. REVIEW-17 note 3's second half (a call-limit breach on T under the container
    backend raises `DailyError`, untested), note 4 (a failed day's health events
    appended again on its re-run) and note 5 (`replay.scripted_start`'s `KeyError`;
    `WORKERS_TRANSPORT`): remain, step S4.2 (144 (a), (b); `meta/BACKLOG.md`).

## Findings filed and answered

- The architect role's escalation of 2026-10-17 on step S4.1 (no D-number) was
  answered by the owner's O-23 to O-25. This mission built those rulings.
- **HF-013** (sub-agent reports run past the 12-line limit; REVIEW-18 note 10):
  **filed** at U0, e0d19df. Open, for the hands Project.
- **HF-014** (the architect role's guard refuses ordinary read-only commands):
  **filed** at U0, e0d19df. Open, for the hands Project.
- **HF-006** (long runs and the 20-minute cap): status line at U0, e0d19df
  (REVIEW-18 note 7). No run of this mission passed the cap, as the units' bodies
  and U6 report. Open.
- **HF-012** (reviewer concurrency): status line at U0, e0d19df (REVIEW-18 note 8).
  Open.
- **HF-010** (stale worktrees): status line at U0, e0d19df (REVIEW-18 note 9).
  `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered at this report
  (`git worktree list`). Open.
- **D-013** (`./scripts/check` time): times line at U6, d1f4b81 (1066, 1079,
  1131 s at ef9359f). Open (decisions 121 (c), 140).
- **D-014** (G1.3 against O-3's 10 minutes): times line at U6, d1f4b81. G1.3 took
  1049 s against mission 17 U5's 542 s, recorded as a finding. M3, M2 and M0 were
  each under 15 minutes. Open, for the owner.
- D-015, HF-008, HF-009 and HF-011 remain open as FINAL-REPORT-18 left them. This
  report's commit carries `meta:`, a prefix the review protocol skips (HF-011). No
  other finding was filed and none was answered in this mission. No unit stopped
  under decision 146 (b).

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-18 note 1 (G3.3 part 1 allows the cell line's integers anywhere in the brief) | stands, 154 (a) | — |
| REVIEW-18 note 2 (the cost-line allowed set builds up across lines) | stands, 154 (a) | — |
| REVIEW-18 note 3 (mission 18 U2 maps by the cursor, then checks bytes) | stands, 154 (a); carried in NOT PROVEN | — |
| REVIEW-18 note 4 (reviewers' check runs 1105 s and 1108 s) | to D-013, open, 154 (a); U6's D-013 times line and `## Check` | d1f4b81 |
| REVIEW-18 note 5 (FINAL-REPORT-18's corrections and NOT PROVEN) | no action needed, 154 (a) | — |
| REVIEW-18 note 6 (forbidden edits: none) | no action, records no forbidden edit, 154 (a) | — |
| REVIEW-18 note 7 (gate M3 past the 20-minute cap; HF-006) | U0, HF-006 status line, 154 (b) | e0d19df |
| REVIEW-18 note 8 (concurrent reviewers; HF-012) | U0, HF-012 status line, 154 (b) | e0d19df |
| REVIEW-18 note 9 (stale worktrees; HF-010) | U0, HF-010 status line, 154 (b) | e0d19df |
| REVIEW-18 note 10 (sub-agent reports past 12 lines) | U0, new HF-013, 154 (b) | e0d19df |
| REVIEW-11 note 8 (`paper.portfolio` and `paper._series` `producer` where O-18 says display and `stage3_money`) | U5, decision 153 (c): they stay `producer`; the one `stage3_money` entry is `dashboard.stage3_money`; `test_the_one_stage3_money_entry_is_the_dashboards` asserts both | a21beb7 |

## Acceptance

- `./scripts/check` was green three times at the pushed tip ef9359f (1066, 1079,
  1131 s; mission 18's 917 to 931 s), 0 skipped, so the `container` tests ran. Met.
- At the pushed tip ef9359f, nothing uncommitted but the drafts, every check passed:
  - `./scripts/gate M1 G1.1` to `G1.4` each printed PASS;
  - M3, M2 and M0 printed `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`;
  - every output, the sha and every wall time are under `## Gate`.
  
  Met. G1.3 is above 10 minutes, a D-014 finding, not a failure under O-2.
- `table.json` keeps `S`, `E_N` and `excess` as G1.3 asserts them (G1.3 PASS), and
  every approach row carries the three adjusted fields. The only change under
  `tests/gates/` is 148 (d)'s line. Met.
- `stats.rank_persistence` is unchanged. `control_moments` gains only `column`, with
  today's result by default. New rank rows carry `timing` and `gross`. No earlier
  row is rewritten: `append_rank_rows` appends only lines the file does not hold,
  and `test_a_rerun_appends_nothing` passes. Met.
- The register:
  - it has no `pending` entry;
  - `rank_rows` is `timing_gross`;
  - the rule functions and `table.adjusted_deflated` are `adjusted`;
  - there is exactly one `stage3_money` entry;
  - the audit passes.
  
  Met.
- Each finding rule is unit-tested on both sides of each production threshold, and
  each wrong change of decisions 148 to 153 turned a test red (the units' bodies).
  Met.
- The day loop writes the alert state, the payloads and the page in staging on a new
  day only, and a re-run writes nothing (U4's and U5's tests). Met.
- No frozen file, rejected fixture, config record or `config_frozen.json` entry
  changed, and `config/gates.toml` is the one new config file. Met.
- Unit prefixes: U0 `plan:`, U1 `table:`, U2 `stats:`, U3 and U4 `alerts:`, U5
  `dashboard:`, U6 `meta:`. Each body lists its files. Met.
- No test uses the network, a secret or the wall clock. No state or job directory
  is written in the repository, and no test builds the image. Met as the units'
  tests and the check show; U5's first check run was red on `test_offline.py` until
  its test ran git through `state._git`.
- This file has `## Gate` with its four regression gates, `## Owner rulings
  applied`, `## Register`, `## Speed`, NOT PROVEN and the review-items table. Met.

VERDICT: mission 19 finished
