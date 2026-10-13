VERDICT: mission 9 finished

# FINAL REPORT — mission 9 (roadmap step S1.3)

Builder prompt: `meta/BUILDER-9-PROMPT.md`. Base 974b700. This mission
builds roadmap step S1.3 as decisions 66 to 75 cut it: REVIEW-8's two
should-fix items and decision 68 (b)'s test; the `replay` command of §16.4
(decision 72); the two performance items of `meta/BACKLOG.md`; the
combined portfolio of §10.5 and rank persistence in the day loop
(decisions 69, 70); the table of §10.4 (decision 71); scripted candidates
in the replay (decision 73); and the M1 gate tests (decision 74). It
closes milestone M1. It binds `meta/decisions/decisions-2026-10-12.md`
(cited as "decision N") and, from 5acec56, the owner's
`meta/decisions/decisions-2026-10-13-owner.md` (cited as "O-N"), which
answered findings D-008 and D-009 when U7 stopped on them.

## What changed

| Unit | Sha | What |
|---|---|---|
| U0 | 3c0b023 | `plan:` the plan, checkpoint and journal |
| U1 | 94e1294 | tests: revival in trading days (decision 66); scratch-session lookups limited to decision 67's list, `gethostbyaddr` left alone by identity and refused again after; decision 68 (b). No `src/` change (`lifecycle.py` already counted trading days) |
| U2 | 15754e9 | `src/discotrade/replay.py`, `replay` in `cli.py`; `daily.py`'s not-closed refusal changed so a mixed-calendar track's weekend day runs at decision 72's clock (finding D-007) |
| U3 | d65964f | one source per run; synthetic source generates only what a fetch needs; recovery reads only unlisted month files and the last-bar file; `bars fetch` and step 1 check every stored file once before writing; paper file updated per day from the day's journal file |
| U4 | 04aee87 | `portfolio` and `portfolio_clean` paper rows; rank persistence rows staged with the day |
| U5 | 33cfe7a | `src/discotrade/table.py`: `table.json` and `table.md` written staged with each new day |
| U6 | 984cc0c | `replay --candidates <file>`: checked before any day, admission after lifecycle steps 1 to 4, staged with the day; `run-day` refuses the option |
| U7 | ae7158b | the M1 gate tests `tests/gates/test_g1_1_*.py` to `test_g1_4_*.py`, `tests/gates/m1_harness.py`, scenario `g1_lifecycle.jsonl`, strategy `always_flat.py` |
| U7 | 6163568 | findings D-008 (G1.1's rank-persistence clause cannot hold on net) and D-009 (gate M1 about 38 minutes) |
| — | 5acec56 | `plan:` the owner's decisions file, copied unchanged on the owner's instruction |
| U7 | b62f5f0 | O-1: `stats.rank_persistence` takes the paper column (default `net_1x`, no production caller passes it); G1.1's clause reads `gross` and reports the net statistic as a warning, asserting nothing about it |
| U8 | this commit | this report |

Meta commits between units: 0dc513e, 8ea9e0b, 6383f99, cd346c6, eec3025,
41e66c2, 768cb1c, 33414b8, 77f2ea3.

Seconds per replay day (U3, a controls-only replay of `test_synth` on the
gate configuration, first 20 days, measured the same way before and after,
foreground, one call): 3.702 s before, 2.480 s after; about 10.7 min for
G1.1's year (16.0 before) and about 37 min for M1's ~900 replay days
(55.5 before), against §18.2's 15 minutes. Per-day cost grows with stored
history, so these are lower bounds. A profile after the change put about
40% of the remaining time in content hashes of bar files recomputed on
every read, about 22% in `backtest.score` and about 13% in journal row
hashing. The table adds about 40 ms per day after 10 days (U5).

## Gate M1

Run item by item as O-2 rules (each `./scripts/gate M1 G1.<n>` its own
foreground call with a 20-minute timeout, wrapped in `timeout 1190`), all
at the pushed commit b62f5f0. Verbatim, with each call's wall time:

```
G1.1 PASS 6 passed, 1 warning in 891.52s (0:14:51)
gate M1 G1.1: PASS
wall: 892 s
```
```
G1.2 PASS 4 passed in 323.44s (0:05:23)
gate M1 G1.2: PASS
wall: 324 s
```
```
G1.3 PASS 10 passed in 1083.24s (0:18:03)
gate M1 G1.3: PASS
wall: 1083 s
```
```
G1.4 PASS 15 passed in 0.51s
gate M1 G1.4: PASS
wall: 1 s
```

Gate M1: PASS (O-2: all four items printed their PASS line at one pushed
commit, each within its call). Total about 38 minutes; §18.2's 15 minutes
is waived for M1 only (O-2). G1.3 finished 107 s inside its 1190 s
`timeout`. The one warning of G1.1 is the net-return statistic O-1 asks
to be reported; `scripts/gate` prints only pytest's last line, so its
value is not in this output.

The run before the owner's ruling (`./scripts/gate M1` whole, at ae7158b):
`G1.1 FAIL 1 failed, 5 passed in 888.56s (0:14:48)`, then stopped by its
`timeout 1185` during G1.2, with no milestone verdict (D-008, D-009).

## M0 still passes

At b62f5f0, `./scripts/gate M0`, one foreground call, verbatim:

```
G0.1 PASS 62 passed in 59.55s
G0.2 PASS 7 passed in 113.35s (0:01:53)
G0.3 PASS 13 passed in 166.70s (0:02:46)
G0.4 PASS 4 passed in 0.26s
gate M0: PASS
wall: 342 s
```

## Acceptance checks

- `./scripts/check` green three consecutive runs at 77f2ea3, whose code is
  b62f5f0's (1222 passed, 121 deselected; 626, 647, 627 s). The U7 commit
  b62f5f0 itself was green 3 of 3 before it was made.
- Gate M1 PASS item by item (O-2) and gate M0 PASS, above.
- `git diff 974b700 -- config tests/fixtures/config tests/fixtures/config_frozen.json`
  is empty; `config/models.toml` does not exist.
- Every unit commit's body lists every file it touches; U0 is `plan:`.

## Decisions 66 to 74: the tests that hold them

- 66 (revival counts trading days): `tests/test_lifecycle.py::test_step_3_waits_revival_min_dormant_days_trading_days_not_calendar_days`.
- 67 (scratch-session lookups): `tests/test_offline.py`, the scratch
  session's `test_marked_network_connects` and
  `test_unmarked_after_network_is_blocked_again`, run by
  `test_a_test_marked_network_is_left_alone`; `tests/conftest.py`
  restores the five lookups for `network`/`live` tests and guards them
  again after.
- 68 (b): `tests/test_lifecycle.py::test_returned_and_displaced_on_one_day_both_rows_stand_and_dormancy_counts_from_the_second`.
- 69 (combined portfolio): `tests/test_portfolio.py` (all nine tests);
  `tests/gates/test_g1_3_lifecycle.py::test_portfolio_series_match_a_hand_count`.
- 70 (rank persistence in the day loop): `tests/test_rank_daily.py::test_no_row_before_the_blocks_last_calendar_day_nor_for_block_1`,
  `::test_monday_appends_block_2s_row_over_the_live_and_dormant_approaches`,
  `::test_a_rerun_appends_nothing`;
  `tests/gates/test_g1_1_null_controls.py::test_one_rank_persistence_row_per_completed_block`.
- 71 (the table): `tests/test_table.py` (all eight tests);
  `tests/gates/test_g1_3_lifecycle.py::test_table_matches_a_hand_count`.
- 72 (replay): `tests/test_replay.py` (all twelve tests, parametrized on
  `test_mixed` and on `test_synth` with the gate configuration);
  `tests/gates/test_g1_2_recompute.py::test_a_second_replay_from_scratch_gives_the_same_state`.
- 73 (scripted candidates): `tests/test_replay_candidates.py` (all ten
  tests); `tests/gates/test_g1_3_lifecycle.py`.
- 74 (the gate tests), with O-1: `tests/gates/test_g1_1_null_controls.py`,
  `test_g1_2_recompute.py`, `test_g1_3_lifecycle.py`,
  `test_g1_4_deflation.py`; O-1's parameter:
  `tests/test_stats.py::test_the_column_parameter_chooses_the_paper_column_summed`.

## What the tests prove

- Revival waits five trading days of the track: dormant on a day with five
  or more calendar days but fewer trading days, back on the fifth trading
  day; the calendar-day count was made and seen red.
- Replay runs exactly the track's trading days from A to B in order at
  each day's last-bar close; its state equals the same days through
  `run-day` byte for byte outside `.git/`; one line per day, exit 0; a
  failing day exits 1 naming it with earlier days committed; A after B,
  `--as-of` and unknown options exit 2; a journaled span writes nothing;
  two fresh replays are identical. Leaving out B and the clock at the
  day's start were seen red.
- Day-by-day fetches over 31 days write the store one fetch writes, byte
  for byte; a synthetic fetch equals the slice of the full generation for
  SYNA, SYNL, SYNX and SYNA's contracts across a roll; recovery reads only
  unlisted files and the last-bar file and every reader still refuses a
  revised file; after each of six days the paper file equals a full
  rebuild. Generation started at the fetch's start and recovery skipping
  an unlisted file were seen red.
- The two portfolio series equal the tests' own equal-weight means on the
  cases the brief lists; `portfolio_clean` has no row without a clean
  member; rank persistence, control moments, the matched draw and the
  lifecycle's Sharpes take no portfolio row; block rows land on the first
  new day on or after the block's last calendar day and are never
  appended again on a re-run. The three named wrong changes were seen red.
- The table's rows, order and fields equal the tests' own computation;
  `table.md` matches with four decimals and `-`; both are committed with
  each day and not rewritten on a re-run. The three named wrong changes
  were seen red.
- Scripted candidates are admitted or refused after steps 1 to 4 with one
  trial row each; staged with the day; refused files run no day; a re-run
  appends nothing. The two named wrong changes were seen red.
- M1: G1.1 (a year of controls on the null market: gross centred on 0,
  cost positive, net centred on minus cost, gross rank persistence centred
  on 0 over at least 40 blocks, one row per block), G1.2 (recompute of
  every pair equal, count asserted; re-run and fresh replay identical),
  G1.3 (every §10.3 transition in full and in order, ledgers never
  rewritten, portfolio and table equal to hand counts), G1.4 (literals to
  1e-12). Seen red, each via `./scripts/gate M1 G1.<n>`: zero costs (G1.1),
  recompute skipping controls (G1.2, 87 pairs against 2463), step 4 in
  trading days (G1.3), `E(N)` without the floor at 2 (G1.4). O-1's
  parameter ignored was seen red in its unit test.

## Deviations

- U2 changed what `run-day` refuses (`_unclosed` in `daily.py`), which the
  brief said stays unchanged, because decision 72's clock could not run a
  weekend day of `test_mixed` otherwise; on a one-calendar track it refuses
  the same days. Finding D-007, open for the architect.
- U3 touched `cli.py` (where `bars fetch` lives), outside its listed files.
- U4 changed what `tests/test_controls.py` and `tests/test_paper.py` assert
  (they leave portfolio rows out), as decision 69 requires.
- U7 changed `tests/test_gate_script.py`'s two "no gate tests" cases from
  M1 to M2, because M1 now has gate tests; otherwise they assert the same.
- Several new test files were added to `SUBPROCESS_FILES` in
  `tests/test_offline.py` because they run git (decision 47).
- `tests/test_rank_daily.py` replays eleven days (about 35 s) inside
  `./scripts/check`, more than "a few days", because block 2's row needs
  them at `block_days` 7.
- Gate M1 was run item by item, not as one `./scripts/gate M1` call, as O-2
  rules.

## NOT PROVEN

- Admission is driven only by scripted candidates whose T metrics a file
  supplies; scoring on T is step S3.2's.
- The `cutoff` behind the `clean` flag comes from a test or a scenario file
  until step S3.2 builds the model pool.
- Approach sources still run in-process until step S2.2.
- The replay has no provider, coordinator, issue sink or sandbox option
  yet.
- G1.1's statistical bounds hold on the seeds the test writes, which is
  what a gate can show. The net-return rank-persistence figure G1.1 reports
  was not read from this run's output (only pytest's warning count shows);
  the measured figures are D-008's (mean 0.707 net, -0.020 gross).
- G1.3's dormancy and return rows are what the fixed seeds produce, not
  designed in; the scenario asserts them as produced.
- G1.3 ran in 1083 s of its 1190 s budget; more per-day cost will fail it
  under O-2 (O-3 schedules the speed work for the next mission).
- U3's 2.48 s per replay day is a lower bound from 20 days.
- What the socket backstop still cannot see: `socket.SocketType` used
  directly; a binding taken before the session starts; child processes; a
  module- or session-scoped fixture first set up by a `network`-marked
  test. That glibc answers `gethostbyname_ex` of a dotted address with no
  NSS lookup on every host rests on glibc's behaviour, not a test; the
  unchanged `create_connection` in `tests/test_cli.py`'s scratch `network`
  test is not shown to need no resolver.
- Decision 68 (b) with the day's admission, rather than another approach's
  return, doing the displacing is not tested.
- The table is not tested under 900 days; its cost grows with history.
- No number from outside the project was added in this mission.
- Carried from FINAL-REPORT-8: dormancy through `run-day` only at lowered
  windows (production values on lifecycle functions); the matched draw
  through `run-day` at lowered values; step 1's writes not staged; retry,
  `run_failed`, the push to a remote and catch-up are step S4.2's; the
  weekly recomputation not wired into the day; mission 7's items on
  interrupted `init-state`, the lock, the carry guard, roll-gap notices,
  `revised_data` by error text; the half-tick spread floor, the G0.1 roll
  probe, G0.1's single fixture, D-006 (deferred to S2.1), G0.2's and
  G0.3's limits, G0.4's matching, 168 unverified cost values and D-003:
  unchanged. Taken by this mission and no longer open: rank persistence,
  the table and the portfolio not built; recompute not tested beyond a few
  days nor on `test_synth` (G1.2 covers 60+ days); `run-day` never run on
  `test_synth`.

## Findings filed and answered

- D-007 (filed, U2): `run-day`'s refusal and decision 72's clock on a
  mixed-calendar track. Open, for the architect to confirm.
- D-008 (filed, U7; answered by O-1): G1.1's rank-persistence clause reads
  gross returns.
- D-009 (filed, U7; answered by O-2): M1's gate is run item by item; §18.2's
  15 minutes waived for M1 only; speed work next mission (O-3).
- HF-006 and HF-007 stay open; D-003 stays; D-006 stays deferred to S2.1.

## Review items

| Item | Review | Resolution | Sha |
|---|---|---|---|
| REVIEW-8 should-fix 1 | Revival must count trading days of the track, not calendar days | U1, decision 66: `test_step_3_waits_revival_min_dormant_days_trading_days_not_calendar_days`; the calendar-day count made, seen red, reverted; `lifecycle.py` already right | 94e1294 |
| REVIEW-8 should-fix 2 | The scratch session's `network` test called lookups that may reach a resolver | U1, decision 67: only the listed numeric lookups called, each commented; `gethostbyaddr` held by identity and refused again after; a non-original replacement seen red | 94e1294 |
| BACKLOG: REVIEW-1 should-fix U6 | `bars fetch` and synthetic regeneration cost | U3: one source per run, generation only of what a fetch needs, equal to the full generation; 3.702 to 2.480 s per replay day | d65964f |
| BACKLOG: REVIEW-2 note U1 | `recover` read and hashed every file | U3, decision 5: recovery reads only unlisted month files and the last-bar file, once per instrument per fetch; readers still refuse per decisions 18, 31, 35 | d65964f |

VERDICT: mission 9 finished
