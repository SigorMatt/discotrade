VERDICT: mission 20 finished

# FINAL REPORT — mission 20 (roadmap step S4.2a: the day loop's speed under O-26 and O-27, REVIEW-19's items, and the Claude Code coordinator with its deny rules)

Brief: `meta/BUILDER-20-PROMPT.md`. Base f1b8346 (`plan: mission 20 kit (S4.2a, speed
under O-26 and O-27, coordinator)`). Owner's rulings: `meta/decisions/2026-10-18-owner.md`
(O-26, O-27). Decisions: `meta/decisions/decisions-2026-10-18-m20.md` (155 to 167), with
items 1 to 154 and the owner's earlier files still binding where not replaced. This
mission closes no milestone and moves no gate of M4 (decision 155).

Under O-25 and decision 155 (a), the met gates were run again at the pushed tip
78b553583f6f75bdc7becc12e978370cfe3fd14a, with nothing uncommitted but the git-ignored
drafts: gate M1 item by item, then M3, M2 and M0. All passed. No M1 item took above
O-27's 15 minutes at any unit or at the tip; the closest was U1's G1.3 at 898 s. G1.3 took
458 s at the tip, against mission 19's 1049 s and REVIEW-19's 1087 s. Container runtime:
docker. Image: `discotrade-sandbox:3b7d75c39621`, present and nothing built, at every unit
and at the tip.

The mission stopped once, at U2, on 2026-10-18 (HF-016, 5ca133c), and resumed the same day
(`## Findings filed and answered`).

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | 4ed47b4 | `plan:` the plan, checkpoint and journal. FINDINGS.md gains D-014's status line (O-27 item 4), finding D-018 and its status line (decision 160), the HF-006, HF-012, HF-010 and HF-013 lines, and the new HF-015 (decision 167 (b)) |
| U1 | 431a82e | `table:` `scripts/speed` and `scripts/speed.py` (decision 156). `state.register_cache`, `registered_caches` and `clear_caches` (157 (b)), with the existing caches of `sources/synth.py`, `journal.py`, `bars/store.py` and `dashboard.py` registered. The table's exposure-record cache, keyed by resolved path, length and sha256. `adjusted_deflated` computes each slot's series from the slot's own rows. `paper.less_exposure` and `stats.moments` (factored out; existing results unchanged). New tests: `test_speed_command.py`, `test_speed_equality.py` (157 (c)), `test_caches.py`. D-019 filed. No register entry |
| U2 | becb570 | `alerts:` `alerts._SPLITS`, a content-keyed cache that splits the slots', unit and position records once per content. `slot_series` builds every slot's series from the split rows, with O-4's subtraction done element by element for all slots and days at once. New `slot_moments`. Register: `slot_series` note changed, `slot_moments` added. New `test_alerts_cache.py`. D-020 filed. Resumed under §R from the WIP stashed at the HF-016 stop |
| U3 | e8d31bb | `bars:` (the area that took most; `dashboard.render` did not grow, so `dashboard.py` is unchanged, as U3 allows). `bars/store._CARRIED` reuses month files across day runs by their bytes. `bars/gaps.find_missing` and `rolls.update_rolls` work per month. `stats.trading_dates` gains `_OPEN_DAYS`. `paper.less_exposure_rows`, moved from alerts. The table subtracts all slots at once. Five new test files (26 tests). D-021 filed. No register entry |
| U4 | 9269ad7 | `alerts:` the `rank_persistence` entry holds the rule's `p`. The page reads it, and `dashboard._rank_p` is removed (decision 160, D-018). The health panel's failures are tested over `pool.fail_window` (decision 161). Two existing tests in `tests/test_alerts.py` were changed only to admit `p` (146 (c)). No register entry |
| U5 | 6833101 | `coordinator:` `ClaudeCodeCoordinator`, `claude_flags`, `deny_rules`, `session_settings`, `fix_session_command` (163, 164). The token budget (165). `providers.run_claude` kills the whole process group on a timeout (166). `--coordinator claude`, `doctor --live coordinator`. `config/run.toml` gains `[coordinator]`. New `config/protected_paths.toml`. `tests/fixtures/config/run.toml` gains the same table (163 (b)). New `test_coordinator_claude.py` (38 tests), plus 7 tests in `test_cli.py` and 3 in `test_doctor.py`. No register entry |
| U6 | 2a614bd | `meta:` the regression gates at the pushed tip 78b5535, and one D-013 times line in FINDINGS.md |
| U7 | this commit | this report |

Meta commits:
- unit done: 3c317f4 (U1), d67f708 (U2), 50d935b (U3), 0d55156 (U4), 78b5535 (U5),
  5c272ab (U6);
- 5ca133c: the stop at U2, HF-016;
- 786ffb6: the journal line of the driver's consultation on HF-016.

a39bbde (`plan: playbook 2026-10-18 (owner)`) is the owner's commit. It raises
`PLAYBOOK.toml`'s `max_architect_consults` from 30 to 35, and the builder did not write it.
Each unit commit's body lists every file its stat shows.

Files changed in the mission outside `meta/` (`git diff --name-status f1b8346 HEAD`),
besides the owner's `PLAYBOOK.toml`:
- new:
  - `config/protected_paths.toml`, `scripts/speed`, `scripts/speed.py`;
  - `tests/test_alerts_cache.py`, `test_bar_carry.py`, `test_caches.py`,
    `test_coordinator_claude.py`, `test_gap_months.py`, `test_rolls_months.py`,
    `test_speed_command.py`, `test_speed_equality.py`, `test_table_slots.py`,
    `test_trading_dates_cache.py`;
- changed:
  - `config/run.toml`;
  - `src/discotrade/alerts.py`, `bars/gaps.py`, `bars/store.py`, `cli.py`,
    `config.py`, `coordinator.py`, `daily.py`, `dashboard.py`, `doctor.py`,
    `journal.py`, `paper.py`, `replay.py`, `rolls.py`, `sources/synth.py`, `state.py`,
    `stats.py`, `table.py`, `workers/providers.py`;
  - `tests/fixtures/config/run.toml`, `tests/fixtures/return_readers.toml`,
    `tests/test_alerts.py`, `test_cli.py`, `test_dashboard.py`, `test_doctor.py`.

Tests the check runs went from 2458 to 2560 (+102), with 204 gate tests deselected as at
mission 19. By unit: U1 2470, U2 2478, U3 2504, U4 2513, U5 2560.

## Check

`./scripts/check` wall times on the builder's machine (four cores, shared). Each run was its
own foreground call with a 20-minute timeout.

| Where | Runs |
|---|---|
| mission 19's tip ef9359f (FINAL-REPORT-19) | 1066, 1079, 1131 s |
| U1 431a82e (U1's files uncommitted on 4ed47b4) | 1168, 1196, 1317 s (the third passed the cap and was waited for to its end) |
| U2 becb570 | 1045, 1016, 1001 s |
| U3 e8d31bb | 1459, 1356, 1198 s (the first passed the cap and was waited for to its end; load about 1.3 to 3.3) |
| U4 9269ad7 | 1044, 1128, 1101 s |
| U5 6833101 | 1111, 1073, 989 s |
| **tip 78b5535 (U6)** | **990, 988, 982 s**, each `check: green` |

Every tip run printed `2560 passed, 204 deselected` with nothing skipped, so the
`container` tests ran on discotrade-sandbox:3b7d75c39621. Each also printed
`config check: ok, 173 unverified values` and `check: green`. Pytest took 987.22 s,
985.47 s and 979.09 s. The outputs are in `meta/drafts/m20-check-<n>.txt`. Each file's
first line is `HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a`, and it ends with `exit 0`
and the wall time. Load average was about 0.3 to 1.4.

No tip run passed the 20-minute cap. All three are still above HF-006's 15 minutes
(D-013 open). They are 76 to 149 s below mission 19's tip runs, with 102 more tests. The
check's time was not measured per test, so this mission does not prove that the speed
units caused the drop (NOT PROVEN).

The order differed from U6 step 2. `discotrade sandbox build` was run at 08:47:46, before
the first check (08:47:49), not after the three checks. So the `container` tests ran in
all three. It was not run again after them.

## Speed

O-26 item 4's measurement, `./scripts/speed --work <dir>` (decision 156): the G1.3
scenario replayed on the gate configuration. Its four figures are:
- first30: seconds per subject-day over 2019-06-03 to 2019-07-02;
- last30: the same over 2020-05-12 to 2020-06-10;
- the ratio, last30 over first30;
- fresh: the wall time of one fresh process running the last replay day.

The process starts follow each row. The load is the 1-minute load average at the start
and end of the run, as each body gives it. Every figure below is copied from the unit's
body or U6's output, not smoothed.

| Unit | Run | first30 | last30 | ratio | fresh | process starts | load |
|---|---|---|---|---|---|---|---|
| U1 parent 4ed47b4 (with U1's speed files) | pw3, 2 calls | 0.058697 | 0.092554 | 1.577 | 8.887 s | 2019-06-03 2020-05-07 | 1.9-2.3 |
| U1 commit 431a82e | cw2, 1 call | 0.044732 | 0.071581 | 1.600 | 7.817 s | 2019-06-03 | 2.2-2.5 |
| U2 parent 786ffb6 | p1, 3 calls | 0.103024 | 0.163093 | 1.583 | 12.696 s | 2019-06-03 2019-12-09 2020-06-03 | 5.2-6.0 |
| U2 parent 786ffb6 | p2, 1 call | 0.043550 | 0.078604 | 1.805 | 7.414 s | 2019-06-03 | 2.3-3.0 |
| U2 commit becb570 | c1, 1 call | 0.051246 | 0.054259 | 1.059 | 8.253 s | 2019-06-03 | 4.5 falling to 2.3 |
| U2 commit becb570 | c2, 1 call | 0.035920 | 0.045266 | 1.260 | 5.666 s | 2019-06-03 | 1.6-1.1 |
| U3 parent d67f708 | p1 | 0.032473 | 0.044932 | 1.384 | 6.074 s | 2019-06-03 | 0.40-1.20 |
| U3 parent d67f708 | pprof | 0.031133 | 0.045479 | 1.461 | 6.213 s | 2019-06-03 | 0.81-1.07 |
| U3 parent d67f708 | p2 | 0.032177 | 0.045818 | 1.424 | 5.811 s | 2019-06-03 | 0.67-1.13 |
| U3 parent d67f708 | p3 | 0.038611 | 0.045901 | 1.189 | 6.055 s | 2019-06-03 | 0.83-1.97 |
| U3 commit e8d31bb | c2 | 0.028157 | 0.053439 | 1.898 | 9.279 s | 2019-06-03 | 0.92-3.58 |
| U3 commit e8d31bb | c3 | 0.029575 | 0.042053 | 1.422 | 10.155 s | 2019-06-03 | 1.15-2.92 |
| U3 commit e8d31bb | c4 | 0.032034 | 0.039628 | 1.237 | 6.967 s | 2019-06-03 | 1.14-2.51 |
| U3 commit e8d31bb | c5 | 0.028802 | 0.060609 | 2.104 | 12.141 s | 2019-06-03 | 1.04-5.76 |
| U3 commit e8d31bb | c6 | 0.031495 | 0.040594 | 1.289 | 6.755 s | 2019-06-03 | 0.90-2.64 |
| U3 commit e8d31bb | c7 | 0.029458 | 0.036355 | **1.234** | 5.675 s | 2019-06-03 | 0.56-1.29 |
| U3 commit e8d31bb | c8 | 0.029563 | 0.038499 | 1.302 | 13.068 s | 2019-06-03 | 1.66-2.63 |
| U3 commit e8d31bb | c9 | 0.027837 | 0.034687 | **1.246** | 6.568 s | 2019-06-03 | 0.49-1.50 |
| U3 commit e8d31bb | cprof3 (profiled) | 0.029902 | 0.035024 | 1.171 | 6.891 s | 2019-06-03 | 0.80-1.94 |
| U4 parent 50d935b | not measured; its code is U3's commit e8d31bb (50d935b differs only under `meta/`) | | | | | | |
| U4 commit 9269ad7 | 1 call | 0.031791 | 0.037430 | 1.177 | 5.583 s | 2019-06-03 | 1.9-2.4 |
| U5 parent 0d55156 | not measured; its code is U4's commit 9269ad7 (0d55156 differs only under `meta/`) | | | | | | |
| U5 commit 6833101 | 1 call (working tree with the commit's content) | 0.027775 | 0.033040 | 1.190 | 5.784 s | 2019-06-03 | 1.1-1.3 |
| **tip 78b5535** (U6) | 1 call, 458 s | 0.027561 | 0.032145 | **1.166** | 5.493 s | 2019-06-03 | 1.47-1.11 |

The first30 window counted 21 days in every run. The last30 window counted 22, except U2's
p1, which counted 21. U1's body also gives two earlier parent runs: ratio 1.375 (load 1.6
to 0.9), and 2.213 (load 2.5 to 3.4; that run's `speed.py` read one more timestamp after a
process's last day).

**The ratio and load.** The ratio binds U3 (O-26 item 4, decision 158).
- Below 1.25 at U3's commit: c7 (1.234) and c9 (1.246), the two runs whose load stayed at
  or below 1.5 throughout. Also c4 (1.237, load ending at 2.51) and the profiled cprof3
  (1.171).
- Above 1.25 at U3's commit: every run that ended at a load of 2.6 or more. These are c2
  1.898, c3 1.422, c5 2.104, c6 1.289 and c8 1.302.
- U3's parent gave 1.384, 1.461, 1.424 and 1.189.

U3 was accepted on its quiet runs. Its margin there is 0.016 and 0.004. At U4, U5 and the
tip, each from one run at load 1.1 to 2.4, the ratio was 1.177, 1.190 and 1.166. The
ratio's sensitivity to load is listed under NOT PROVEN.

**Profiles' summary.** All profiles are cProfile cumulative, warm, inside the replay, on
2019-07-03 and 2020-05-11, parent then commit:
- U1, the table:
  - `table.build` 1.739/2.298 s -> 0.355/0.593 s;
  - `adjusted_deflated` 1.450/1.937 -> 0.155/0.299;
  - day 5.478/8.997 -> 3.490/7.209.
  - Without the profiler, `table.build` on the state through 2020-06-09 took 0.885 s and
    1.581 s at the parent, and 0.203 s and 0.309 s at the commit, with the same sha256 of
    `table.json`.
  - The rest still grows by about 0.1 s over the year. Its figures are recomputed over
    each subject's whole paper record (D-019).
- U2, step 6:
  - `alerts.step` 0.606/1.628 -> 0.081/0.233;
  - `persistent_approach` 0.556/1.607 -> 0.061/0.175;
  - `slot_series` per call 0.446/0.675 -> 0.030/0.049;
  - `rank_rows` (2020-05-11 only) 0.102 -> 0.090;
  - `run_day` 4.060/5.556 -> 3.170/4.006.
  - Per approach, step 6 takes 0.081 and 0.117 s at the commit. The remaining growth is
    with the approach's clean days W (D-020).
  - The body says the rest of step 6 costs no more late than early. That overclaims:
    `alerts.write` rose from 0.016 s to 0.052 s between the two days (the builder's
    verification of U2, recorded in `meta/CHECKPOINT.md`). The commit was not amended or
    force-pushed. This report states the correction.
- U3, step 1 and the rest:
  - `run_day` 3.070/4.079 -> 2.940/3.109;
  - `daily._step_1` 0.657/1.161 -> 0.262/0.297;
  - `store._verify_stored` 0.183/0.505 -> 0.006/0.014;
  - `state.content_hash` 0.207/0.430 -> 0.099/0.100;
  - `gaps.check_gaps` 0.198/0.376 -> 0.084/0.094;
  - `rolls.update_rolls` 0.036/0.079 -> 0.007/0.012;
  - `stats.trading_dates` 0.006/0.151 -> 0.001/0.002;
  - `table.build` 0.353/0.513 -> 0.418/0.445.
  - `dashboard.render` was flat at the parent (0.093/0.041), so it was not changed.
  - A CPU-time profile names what still costs more late than early:
    - `table.build` +0.24 s (D-019);
    - `alerts.step` +0.23 (two approaches against one; D-020);
    - `paper.update_exposure` +0.18;
    - `journal_day` +0.17.

**157 (d), cold against warm.** Each speed unit ran `scripts/speed --cold` at its commit:
- U1: `/tmp/m20u1/cc`, 2 calls;
- U2: `/tmp/m20u2/cc`, 1 call;
- U3: `/tmp/m20u3/cc`, 2 calls, process starts 2019-06-03 and 2020-05-29.

Each was diffed against its unit's warm run with `diff <(git -C cc/state log
--format='%s %T') <(git -C <warm>/state log --format='%s %T')`, and every diff printed
nothing. All 267 `run test_synth <D>` trees, 2019-06-03 to 2020-06-10, are equal. They
cover these lifecycle changes:
- admitted 2019-06-03;
- displaced 06-11;
- retired on failure 06-13;
- dormant 07-02;
- returned 08-12 (a revival payload fired; again 11-18);
- retired_dormant 2020-06-10.

`diff -r` of the two states outside `.git` was also empty in each unit.

**157 (e), byte-identical to the parent.** `diff -r --exclude=.git <parent>/state
<commit>/state` printed nothing (exit 0):
- U1: pw3 against cw2;
- U2: p2 against c1, and p1 against c1;
- U3: p1 against c2, and pprof against c2.

`git rev-parse HEAD^{tree}` gave 5f9c06b769ba4e5a77d61b9106177d3583cfa7ce in every
state compared, at U1, U2 and U3. Each state holds 369 files outside `.git`.

U4 changes what a day writes (the entry's `p`). It is not a speed unit, so its body makes
no byte-identical comparison with its parent (decision 160). U5 made none either.

**G1.3 at each unit** (`./scripts/gate M1 G1.3`, one foreground call each):

| Where | wall | pytest's line | load |
|---|---|---|---|
| mission 19 builder ef9359f | 1049 s | `10 passed in 1048.60s` | |
| REVIEW-19 ad3576c | 1087 s | `10 passed in 1085.65s` | 0.5-1.7 at start |
| U1 431a82e | 898 s | `G1.3 PASS 10 passed in 897.32s (0:14:57)` | 1.0-2.4 |
| U2 becb570 | 582 s | `G1.3 PASS 10 passed in 581.08s (0:09:41)` | 1.1-1.2 |
| U3 e8d31bb | 625 s | `G1.3 PASS 10 passed in 623.20s (0:10:23)` | 2.05-3.09 |
| U4 9269ad7 | 534 s | `G1.3 PASS 10 passed in 532.18s (0:08:52)` | |
| U5 6833101 | 462 s | `G1.3 PASS 10 passed in 460.75s` | |
| tip 78b5535 | 458 s | `G1.3 PASS 10 passed in 457.04s (0:07:37)` | 0.96-1.27 |

U1's 898 s was 2 s under O-27's 15-minute stop.

Mission 18's tip: no figure of either kind exists at d8a129a or 031f5e4 (decision 162).
U1's parent figures (4ed47b4) are the first of O-26's measurement.

## Gate

The regression gates under O-25 (decision 155 (a)) were run at the pushed tip
78b553583f6f75bdc7becc12e978370cfe3fd14a (U5 done):
- nothing uncommitted but the git-ignored drafts;
- after `./scripts/check` was green three times there;
- each run its own foreground call with a 20-minute timeout.

The tip differs from 6833101 (U5's commit) only by `meta/CHECKPOINT.md`, `meta/journal.md`
and `meta/plan.md`. This report's parent 5c272ab differs from the tip only by those three
files and `meta/findings/FINDINGS.md`.

`uv run discotrade sandbox build` (`meta/drafts/m20-sandbox-build.txt`, verbatim). It was
run before the three checks (`## Check`):

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792388866  08:47:46 up 63 days, 14:36,  1 user,  load average: 0.29, 0.79, 1.05
sandbox build: present, nothing built
discotrade-sandbox:3b7d75c39621
real 0.66
user 0.86
sys 0.07
exit 0
end 1792388866  08:47:46 up 63 days, 14:36,  1 user,  load average: 0.29, 0.79, 1.05
```

### Gate M1

Item by item (O-2). Each output below is verbatim from `meta/drafts/m20-<item>.txt`.

`./scripts/gate M1 G1.1` at 78b5535: wall 279 s (mission 19 builder at ef9359f: 411 s;
REVIEW-19 at ad3576c: 383 s)

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792391840  09:37:20 up 63 days, 15:26,  1 user,  load average: 1.10, 1.23, 1.18
G1.1 PASS 6 passed, 1 warning in 278.26s (0:04:38)
gate M1 G1.1: PASS
real 279.27
user 249.01
sys 9.30
exit 0
end 1792392119  09:41:59 up 63 days, 15:30,  1 user,  load average: 1.27, 1.22, 1.19
```

`./scripts/gate M1 G1.2` at 78b5535: wall 170 s (mission 19 builder: 280 s; REVIEW-19:
290 s)

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792392121  09:42:01 up 63 days, 15:30,  1 user,  load average: 1.27, 1.22, 1.19
G1.2 PASS 4 passed in 169.64s (0:02:49)
gate M1 G1.2: PASS
real 170.47
user 157.21
sys 5.52
exit 0
end 1792392292  09:44:52 up 63 days, 15:33,  1 user,  load average: 1.05, 1.14, 1.16
```

`./scripts/gate M1 G1.3` at 78b5535: wall 458 s (mission 19 builder: 1049 s; REVIEW-19:
1087 s)

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792392294  09:44:54 up 63 days, 15:33,  1 user,  load average: 0.96, 1.13, 1.16
G1.3 PASS 10 passed in 457.04s (0:07:37)
gate M1 G1.3: PASS
real 458.35
user 422.96
sys 17.12
exit 0
end 1792392753  09:52:33 up 63 days, 15:41,  1 user,  load average: 1.27, 1.18, 1.17
```

`./scripts/gate M1 G1.4` at 78b5535: wall 1 s (mission 19 builder: 1 s; REVIEW-19: 1 s)

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792392755  09:52:35 up 63 days, 15:41,  1 user,  load average: 1.25, 1.18, 1.16
G1.4 PASS 15 passed in 0.52s
gate M1 G1.4: PASS
real 1.08
user 1.26
sys 0.10
exit 0
end 1792392757  09:52:37 up 63 days, 15:41,  1 user,  load average: 1.25, 1.18, 1.16
```

| Item | mission 19 builder ef9359f | REVIEW-19 ad3576c | the units' own runs | tip 78b5535 |
|---|---|---|---|---|
| G1.1 | 411 s | 383 s | — | 279 s |
| G1.2 | 280 s | 290 s | — | 170 s |
| G1.3 | 1049 s | 1087 s | U1 898, U2 582, U3 625, U4 534, U5 462 s | 458 s |
| G1.4 | 1 s | 1 s | — | 1 s |

Every M1 item is under O-27's 15 minutes at the tip and in each unit's run. No finding was
filed under O-27 item 3.

### Gate M3

`./scripts/gate M3` at 78b5535: wall 506 s (mission 19 builder at ef9359f: 547 s;
REVIEW-19 at ad3576c: 552 s). Verbatim from `meta/drafts/m20-M3.txt`:

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792392759  09:52:39 up 63 days, 15:41,  1 user,  load average: 1.15, 1.16, 1.16
G3.1 PASS 3 passed in 191.29s (0:03:11)
G3.2 PASS 9 passed in 155.04s (0:02:35)
G3.3 PASS 10 passed in 157.95s (0:02:37)
gate M3: PASS
real 506.32
user 490.59
sys 9.55
exit 0
end 1792393265  10:01:05 up 63 days, 15:49,  1 user,  load average: 1.04, 1.11, 1.13
```

### Gate M2

`./scripts/gate M2` at 78b5535: wall 130 s (mission 19 builder: 130 s; REVIEW-19: 144 s).
Verbatim from `meta/drafts/m20-M2.txt`:

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792393268  10:01:08 up 63 days, 15:49,  1 user,  load average: 1.04, 1.11, 1.13
G2.1 PASS 36 passed in 40.73s
G2.2 PASS 3 passed in 24.15s
G2.3 PASS 8 passed in 3.61s
G2.4 PASS 9 passed in 38.88s
G2.5 PASS 5 passed in 19.75s
gate M2: PASS
real 129.88
user 40.01
sys 3.69
exit 0
end 1792393398  10:03:18 up 63 days, 15:52,  1 user,  load average: 0.92, 1.06, 1.11
```

### Gate M0

`./scripts/gate M0` at 78b5535: wall 244 s (mission 19 builder: 245 s; REVIEW-19: 282 s).
Verbatim from `meta/drafts/m20-M0.txt`:

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
start 1792393400  10:03:20 up 63 days, 15:52,  1 user,  load average: 0.85, 1.04, 1.10
G0.1 PASS 62 passed in 58.51s
G0.2 PASS 7 passed in 89.71s (0:01:29)
G0.3 PASS 13 passed in 92.43s (0:01:32)
G0.4 PASS 4 passed in 0.69s
gate M0: PASS
real 243.66
user 246.01
sys 4.32
exit 0
end 1792393644  10:07:24 up 63 days, 15:56,  1 user,  load average: 1.51, 1.20, 1.14
```

No M3, M2 or M0 item took above 15 minutes. `git diff f1b8346 HEAD -- tests/gates` is
empty: no file under `tests/gates/` changed in this mission.

The measurement at the tip (`meta/drafts/m20-speed.txt`, verbatim):

```
HEAD 78b553583f6f75bdc7becc12e978370cfe3fd14a
call 1 start 1792393649  10:07:29 up 63 days, 15:56,  1 user,  load average: 1.47, 1.19, 1.13
speed first30: 0.027561 s per subject-day (21 days counted)
speed last30: 0.032145 s per subject-day (22 days counted)
speed ratio: 1.166
speed fresh last day: 5.493 s
speed process starts: 2019-06-03
speed: done
real 458.04
user 423.11
sys 18.39
exit 0
call 1 end 1792394107  10:15:07 up 63 days, 16:03,  1 user,  load average: 1.11, 1.17, 1.14
```

## Owner rulings applied

### O-26 D-014: a replay day's cost stays flat

1. **When.** Done: after U0 (4ed47b4), the speed units U1 431a82e, U2 becb570 and U3 e8d31bb
   came first, before U4 and U5 (`meta/plan.md`; `git log --oneline f1b8346..HEAD`). Held by
   the commit order.
2. **What they change.**
   - Done:
     - the table (U1, 431a82e);
     - step 6 (U2, becb570);
     - step 1's bar verification, the gap and roll scans, `stats.trading_dates` and the
       table's slot subtraction, which U3's measurement showed growing (U3, e8d31bb).
   - Step 7 (`dashboard.render`) was measured flat (0.093/0.041 s at U3's parent), so it
     was not changed.
   - Held by the profiles in `## Speed`.
3. **What they do not change.** Done in U1 to U3.
   - Byte-identical states: 157 (e) gives empty `diff -r` and HEAD tree 5f9c06b7 at U1,
     U2 and U3.
   - In-process caches keyed by content. Each is shown recomputing a same-length rewrite,
     and each registers with `state.clear_caches`. Held by:
     - `tests/test_caches.py`;
     - `tests/test_alerts_cache.py`;
     - `tests/test_bar_carry.py`;
     - `tests/test_gap_months.py`;
     - `tests/test_rolls_months.py`;
     - `tests/test_trading_dates_cache.py`.
   - No gate test changed (`git diff f1b8346 HEAD -- tests/gates` empty).
   - No frozen value changed, and no dependency was added (`pyproject.toml` and `uv.lock`
     unchanged).
   - One test change to note: U2 and U3 each added names to
     `tests/test_caches.py::CACHES`. That file is U1's own new test, and the additions
     extend what the test asserts.
   - O-18: two register entries, U2 (`## Register`). O-25: every existing function's
     result unchanged for the inputs the gates give it. The gates PASS unedited at the
     tip.
4. **Flat, measured.**
   - Done in U1: `scripts/speed` and `scripts/speed.py`. Held by
     `tests/test_speed_command.py`, which checks the lines, counted days, window
     arithmetic, process starts and the refusal of a work dir inside the repo.
   - The ratio binds U3. It was 1.234 and 1.246 in U3's quiet runs, and above 1.25 under
     load (`## Speed`). At the tip it was 1.166.
5. **Equal to a full recompute.**
   - Done in U1: `tests/test_speed_equality.py`, in `./scripts/check`, unchanged and
     passing at U2 to U5 as their bodies say. It covers the first and last days and
     06-06, a lifecycle change, byte for byte.
   - 157 (d) found all 267 day trees equal at U1, U2 and U3.
   - The figures that could not be made incremental with the same bits were left
     recomputed and filed: D-019 (the table, U1) and D-020 (step 6, U2).
6. **The live loop is not covered.**
   - Reported by the fourth figure, with no threshold: 8.887 s at U1's parent, 5.493 s
     at the tip, each from one fresh process at the scenario's last day.
   - The live loop's growth itself is not measured (NOT PROVEN).

### O-27 The 15-minute stop, and the times every later day-loop unit gives

1. **Targets.** Each M1 item ran as its own foreground call with a 20-minute timeout at
   the tip (U6, 2a614bd). All PASS (`### Gate M1`).
2. **What each day-loop unit gives.** U1 to U5 each give G1.3's wall time and pytest's
   line, and the four figures with process starts, in their bodies (`## Speed`). None
   went to a D-014 times line.
3. **The stop.** No M1 item took above 15 minutes at any unit or at the tip. The highest
   was U1's G1.3 at 898 s. No finding under it, no test weakened.
4. **D-014.** U0 (4ed47b4) appended `D-014 status: decided
   meta/decisions/2026-10-18-owner.md (O-26, O-27)` after the last line of
   FINDINGS.md.

## Coordinator

Built by U5 (6833101).

**Version and flags.** Read from the installed binary.
- `claude --version`: `2.1.303 (Claude Code)`.
- The coordinator's call (`coordinator.claude_flags`), with the prompt on standard input:

```
claude --bare -p --output-format json --max-budget-usd <usd> --permission-mode dontAsk --model <model> --tools ""
```

The `claude --help` lines U5 quotes:
- `--bare  Minimal mode: skip hooks ... Anthropic auth is strictly ANTHROPIC_API_KEY or
  apiKeyHelper via --settings`
- `-p, --print  Print response and exit (useful for pipes).`
- `--output-format <format>  Output format (only works with --print): "text" (default),
  "json" (single result), or "stream-json"`
- `--max-budget-usd <amount>  Maximum dollar amount to spend on API calls (only works
  with --print)`
- `--permission-mode <mode>  Permission mode to use for the session (choices:
  "acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan")`
- `--model <model>  Model for the current session. Provide an alias for the latest model
  (e.g. 'fable', 'opus', or 'sonnet') or a model's full name.`
- `--tools <tools...>  ... Use "" to disable all tools`
- `--settings <file-or-json>  Path to a settings JSON file or a JSON string to load
  additional settings from`

`--max-turns` is in SPEC §17's list, but the installed help does not list it. It is not
passed. `coordinator.max_turns` is read and not used (decision 163 (a)).

HF-016's text (5ca133c) names Claude Code 2.1.302 for the builder's session on 2026-10-18.
U5 read 2.1.303 on 2026-10-19.

**The `[coordinator]` table of `config/run.toml`.** Every value is the project's own
choice (163 (b)), and `tests/fixtures/config/run.toml` holds the same table:
- `binary = "claude"`;
- `model = "sonnet"`, an alias the help names;
- `max_turns = 1`, read and not passed;
- `max_budget_usd = 0.10`;
- `timeout_seconds = 300.0`;
- `propose_fixes = false`.

**Key, fallback and budget.**
- The key reaches the child through its environment only. The child's environment is the
  harness's minus `NEBIUS_API_KEY` and `DATABENTO_API_KEY`.
- `--coordinator scripted` stays the default.
- Tokens (165) are `usage.input_tokens` plus `usage.output_tokens` of claude's JSON
  output. The `cache_*` usage fields are not counted.
- The day's sum is reset by `begin_day(D)`.

**Deny-rule syntax.** Taken from https://code.claude.com/docs/en/permissions.md, read
2026-10-19 (U5's body quotes it):
- "`//path` | Absolute path from filesystem root | `Read(//Users/alice/secrets/**)`";
- "`Edit` rules apply to all built-in tools that edit files";
- a `Write` or `NotebookEdit` path rule is accepted but "never consult[ed]".

So `coordinator.EDIT_TOOLS = ("Edit",)`, and each rule is `Edit(//<absolute path>)`, with
`/**` after a directory.

**The settings generated.** `session_settings` gives `{"permissions": {"deny":
[<deny_rules>]}}`:
- one `Edit(...)` rule per path;
- `code` paths are resolved under the code repository, `state` paths under the state
  directory.

`fix_session_command` writes them to `<work_dir>/settings.json` and builds:

```
<binary> --bare -p --output-format json --max-budget-usd <usd> --permission-mode acceptEdits --model <model> --settings <work_dir>/settings.json
```

Nothing calls it while `propose_fixes` is false. Ordinary calls take no `--settings`, since
they have no tool at all.

**The protected paths** (`config/protected_paths.toml`, new, not frozen):
- `code`:
  - in `src/discotrade/`: `backtest.py`, `costs.py`, `executor.py`, `metrics.py`,
    `paper.py`, `controls.py`, `ledger.py`, `lifecycle.py`, `journal.py`, `stats.py`,
    `table.py`, `alerts.py`, **`coordinator.py`**;
  - directories: `src/discotrade/validation/`, `src/discotrade/sandbox/`, `config/`,
    `reference/`, `tests/gates/`.
- `state`: `bars/`, `rolls/`, `approaches/`, `trials/`, `journal/`, `paper/`,
  `controls/`, `ledger/`, `responses/`, `stats/`, `table/`, `alerts/`, `dashboard/`,
  `health/`.

These are decision 164 (a)'s two lists, plus `src/discotrade/coordinator.py`, which the
builder added: the rules are generated there, so a fix session that could edit it could
drop a rule. `digests/` and `runlog/` are not in the file.

**A fragile test.** `tests/test_cli_provider.py::test_an_unknown_coordinator_is_a_usage_error`
is unchanged and passes. Since U5 it gets exit 2 through the key refusal, whose line names
`--coordinator`. So it passes only while `ANTHROPIC_API_KEY` is unset in the test's
environment. With the key set and no `claude` on PATH, the refusal would be exit 1 (binary
not found), and the test's `got == 2` would fail. The check runs without the key (I-11),
so it holds there.

## Register

Every entry of `tests/fixtures/return_readers.toml` added or changed in this mission
(`git log -p 4ed47b4^..HEAD -- tests/fixtures/return_readers.toml`, one commit):

| Entry | Class | Unit | Change |
|---|---|---|---|
| `discotrade.alerts.slot_series` | `adjusted` | U2 becb570 | changed: note only, now "computed as paper.adjusted does from records split once per content (O-7, O-24, decisions 151, 158)"; class unchanged |
| `discotrade.alerts.slot_moments` | `producer` | U2 becb570 | new: "computes stats.control_moments' moments of the slots' Sharpes over W, from slot_series' values directly; decides nothing (O-24, decision 158)" |

U1, U3, U4 and U5 added and changed no entry. Their bodies say so, and that the audit
(`tests/test_return_readers.py::test_the_audit_passes`) passes:
- U1 changed `table.adjusted_deflated` (`adjusted`) and `table.build.approach_row`
  (`display`) in body only;
- U3 changed `table.adjusted_deflated` and `alerts.slot_series` in body only.

## What the tests prove

Only what the tests assert, on their inputs. The units' bodies give each test and each
wrong change.

U1 (431a82e):
- `test_speed_command`, on a three-day span with a fake timer: the `days.jsonl` lines,
  the counted days, the window arithmetic, the process starts, the before-last copy and
  the printed lines. A work dir inside the repo is refused.
- `test_speed_equality`: a warm replay and a replay that clears every cache before each
  day (2019-06-03..06-07 of `g1_lifecycle.jsonl`, gate config) give equal `run test_synth
  <D>` trees on all five days. On the first day, the last and 06-06 (a lifecycle change),
  these are byte-equal: `table.json`, `table.md`, the alert state, the day's payloads and
  `index.html`.
- `test_caches`:
  - `clear_caches` names and empties every registered cache;
  - a same-length rewrite of a position file is read again;
  - equal bytes are served from the cache;
  - one state dir at a time;
  - staged files are read first.
- Seen to fail, each made alone and reverted:
  - a table cache keyed by path only;
  - the clearing function skipping the table's cache.

U2 (becb570):
- `test_alerts_cache` (seed 20261018):
  - `slot_series` gives `paper.adjusted`'s series for each slot: same slots, order, index,
    name, dtype and float64 bytes. This holds with exposure passed or read, and with a
    slot holding two rows of a date;
  - a changed value of the same length is split again;
  - equal content is served;
  - one state dir and track at a time;
  - `clear_caches` empties the cache;
  - `slot_moments` equals `control_moments` bit for bit;
  - a missing unit day is refused with `paper.adjusted`'s message.
- Seen to fail: the alert cache's registration removed.

U3 (e8d31bb):
- `test_bar_carry`:
  - the same bytes are served in the next day run with no content hash;
  - a same-length rewrite is refused by the next day run;
  - nothing is kept or served outside a day run;
  - one store at a time; `clear_caches` empties it.
- `test_gap_months`:
  - `find_missing` equals the test's own missing bars on seeded stores at three bounds;
  - complete months are reused;
  - another calendar record recomputes;
  - a revised complete month is refused.
- `test_rolls_months`:
  - one contract gives no roll and no file;
  - a change appended later, including into a kept month, is found at the test's ts;
  - a revised whole month is refused.
- `test_trading_dates_cache`:
  - dates equal the test's own;
  - a repeat calls `expected_bars` for new dates only;
  - a changed record or bar size is decided again;
  - the bound of 16 calendars holds.
- `test_table_slots`: `adjusted_deflated` with exposure equals the test's per-slot
  `paper.adjusted` figures bit for bit at N 2, 7 and 40.
- Seen to fail, each made alone and reverted:
  - the dashboard cache's registration removed;
  - `_CARRIED` served without comparing bytes;
  - `_OPEN_DAYS` keyed by name;
  - `find_missing` reading only the last month;
  - `_MONTH_MISSING` keyed without the calendar;
  - `_MONTH_CONTRACTS` keyed by path only;
  - the table's batch divided by 1.

U4 (9269ad7):
- The alert step writes the rule's `p`, computed by the test with its own Simpson's-rule
  `t_sf`, into the `rank_persistence` entry at shifts 0.05, -0.05 and 0.8. The entry holds
  `p` null where the rule is not evaluated. Other kinds' entries hold exactly
  `ENTRY_KEYS`.
- The page shows a `p` from the state that the thresholds in force would not give. An
  entry without `p` shows "—" and "not yet".
- Two models' failures over `pool.fail_window = 5` in a copied `thresholds.toml` equal
  the test's counts.
- Seen to fail, each made alone and reverted:
  - the page computing `p` from `value` and `threshold`;
  - `window = 20` in place of `pool.fail_window`.

U5 (6833101), against a fake `claude` only:
- The argument list equals the flags with the configured values.
- `ANTHROPIC_API_KEY` is in the child's environment, and in no argument and not in the
  prompt. `NEBIUS_API_KEY` is not passed.
- A valid reply gives its cell and brief.
- Each of these gives the scripted choice and one `coordinator_fallback` naming the
  reason:
  - exit 3;
  - a timeout;
  - output that is not JSON;
  - `is_error`;
  - a reply that is not the object;
  - a cell not offered;
  - a binary that cannot start.
- Two states differing only in scores give byte-identical prompts.
- The brief is sanitised and cut to 600 characters.
- The budget: 700+300 tokens against 1000. The later tasks are scripted, and one
  `token_budget` alert is raised.
- A sleeping grandchild is gone after the timeout, for the coordinator and for
  `ClaudeWorkerProvider`.
- Every protected path appears as an `Edit` deny rule, exactly those. A fake started
  through `fix_session_command` receives exactly those rules. The file refuses absolute,
  `~`, `..`, empty-list, missing and unknown keys.
- A two-day replay with `--coordinator claude` starts the fake once per day, and the key
  is nowhere in state.
- The CLI refusals: exit 2 with no table or no key, and exit 1 with no binary. L4 without
  the key exits 1 and never starts the fake.
- Seen to fail, each made alone and reverted:
  - the offered-cell check skipped;
  - the key passed as an argument;
  - a score added to the prompt;
  - one path dropped from the rules;
  - the kill sent to the child only.

The gates (U6): G1.1 to G1.4 PASS, `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`
at the pushed tip 78b5535, with nothing uncommitted but the drafts.

The check and frozen files:
- `./scripts/check` was green three times at 78b5535, 0 skipped.
- `git diff --stat f1b8346 HEAD -- config tests/fixtures/rejected tests/fixtures/config
  tests/fixtures/config_frozen.json tests/gates` shows only:
  - the new `config/protected_paths.toml`;
  - the `[coordinator]` table added to `config/run.toml` and
    `tests/fixtures/config/run.toml`.

## NOT PROVEN

Items of the U7 brief:
- **No figure of either measure exists at mission 18's tip** (d8a129a or 031f5e4), neither
  decision 80 (d)'s seconds per replay day nor O-26's four figures (decision 162). U1's
  parent figures at 4ed47b4 are the first of O-26's (0.058697 / 0.092554 / 1.577 /
  8.887 s). This carries REVIEW-19 should-fix 3 as owed, not done.
- **The live loop's cost still grows with history.** Each live day is a cold process
  (O-26 item 6). The fourth figure reports one such process at the scenario's last day
  (5.493 s at the tip), with no threshold. Its growth over history is not measured.
- **The speed figures are from the builder's machine** (four cores, shared), under the
  load each body gives. The ratio is sensitive to load:
  - At U3's commit it was at or below 1.25 only in the quiet runs: c7 1.234 and c9 1.246
    (load at or below 1.5), c4 1.237 (load ending at 2.5), and the profiled cprof3 1.171.
  - Every commit run ending at a load of 2.6 or more gave above 1.25: 1.898, 1.422,
    2.104, 1.289 and 1.302.
  - The parent's runs gave 1.384, 1.461, 1.424 and 1.189.
  - U4 (1.177), U5 (1.190) and the tip (1.166) are one run each.
  - The U3 margin, 0.016 and 0.004, is within the run-to-run spread. So that the ratio
    stays at or below 1.25 on a re-measure is not proven.
  - That the check's drop (1066-1131 s to 982-990 s) comes from the speed units is not
    measured.
- **No real `claude` was called** (live check L4 not run). The flags are proven against
  the installed help (2.1.303) and a fake binary. The deny rules are proven against the
  settings a fake receives, not against Claude Code enforcing them. Also not checked
  against a real reply or the binary:
  - the JSON fields read (`result`, `is_error`, `usage.input_tokens`,
    `usage.output_tokens`);
  - that leaving out the `cache_*` usage fields counts the tokens that matter;
  - the deny-rule syntax, which comes from the docs page.
- **The coordinator's `model`** (`"sonnet"`) is the project's choice, unverified. So are
  `max_budget_usd = 0.10` and `timeout_seconds = 300.0`.
- **`tests/test_cli_provider.py::test_an_unknown_coordinator_is_a_usage_error`** passes
  only with `ANTHROPIC_API_KEY` unset (`## Coordinator`).

The units' own items:
- U1:
  - that the table's residual growth (about 0.1 s over the year, D-019) is the only growth
    U1 took;
  - that the speed test's fresh child process opens no connection (the socket backstop
    does not reach it).
- U2:
  - that step 6's residual growth is only what D-020 names. The body's claim that the
    rest of step 6 costs no more late than early is contradicted by `alerts.write`,
    0.016 -> 0.052 s (`## Speed`);
  - that a frame of another column type takes the fallback in the day loop.
- U3:
  - that the parts named are the only growth left. The CPU-time profile names the table,
    alerts, `paper.update_exposure` and `journal_day`;
  - that the day loop ever takes `test_table_slots`' two-rows fallback (D-021).
- U4: no byte-identical comparison with the parent, because U4 changes what a day writes
  (`p` in the entry).
- HF-016's cause was an environment setting, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` set in
  the builder role, as the owner reported (`meta/CHECKPOINT.md`). This mission did not
  prove it.
- U6: `discotrade sandbox build` was run before the three checks, not after as step 2
  lists, and not again after them.

What remains of FINAL-REPORT-19's NOT PROVEN, item by item:
1. **No finding alert fires on any replay a gate runs** (every 2019 observation is
   exposed): remains. G4.2 and G4.5 are step S4.3's.
2. **The bootstrap's quantile and the t-test** are checked against the tests' own
   computation, not an outside package: remains. U4's `own_t_sf` (Simpson's rule) is also
   the test's own. The p the page derived is gone: since U4 the page shows the state's
   `p` (D-018).
3. **The dashboard's readability on a phone:** remains.
4. **`no_finding` is not called by the day loop:** remains, step S4.2b.
5. **The speed figures are from the builder's machine:** remains (above).
   - No figure at mission 18's tip: remains (above).
   - The check above HF-006's 15 minutes: remains, now 982 to 990 s at the tip (D-013
     open).
6. U1 (mission 19): that the check's rise of about +195 s comes only from the table's
   `paper.adjusted` calls: remains unmeasured. U1 of this mission cut `table.build` by
   about 80% (`## Speed`), but the check's time was not measured per test.
7. U1 (mission 19): decision 147 (d)'s equality beyond the enumerated subjects, columns
   and windows: remains.
8. U2 (mission 19): the rank rows' `timing` beyond the tests' populations, and the
   check's time change: remain.
9. U4 (mission 19): `few_valid_candidates` and `cost_stale` raised by a day-loop run;
   the rules and detectors beyond the tests' inputs: remain.
10. U5 (mission 19):
    - O-14's adjusted sum and average positions not asserted on the page: remains;
    - the portfolio band, the running mean and the significance band not asserted:
      remains;
    - the health panel showing `journal_mismatch` events: remains.
11. U6 (mission 19): why G1.3 doubled was not measured per test. It is answered in part:
    O-26's profiles in U1 to U3 name the table, step 6 and step 1's bar reads as growing
    with history, and G1.3 fell to 458 s. Still not measured per test.
12. G4.5, the dashboard's gate test: remains, step S4.3.
13. FINAL-REPORT-18's carried items:
    - (1) No real provider, model or `claude` called: remains, and now also covers the
      Claude coordinator.
    - (2) G3.3's leak checks cover the G3.1 replay's prompts on `test_synth` only:
      remains. G3.3 PASS at 78b5535. The Claude coordinator's prompt is checked only by
      U5's scores-only test, not by G3.3.
    - (3) 142 (b) at 1e-9 relative, and part (c) on three days: remains.
    - (4) The corpus is the builder's and its yield is arranged: remains.
    - (5) Speed from the builder's machine: remains.
    - (6) The "a file listed with no `served` day" clause passes trivially: remains.
    - (7) Mapping by the cursor: remains (REVIEW-18 note 3 stands).
    - (8) Wrong change 5 red only through the missing trial ledger: remains as recorded.
    - (9) Mission 18's gate not at its report's tip: superseded. This mission's gates ran
      at 78b5535, which differs from this report's parent 5c272ab only under `meta/`.
    - (10) FINAL-REPORT-17's items:
      - 17.1, 17.2: remain;
      - 17.3 (`config/models.toml` unverified): remains. This mission added no number
        from outside the project. The `[coordinator]` values are the project's own
        choices, so none needed `checked`, `source` or `verified`;
      - 17.4 to 17.9: remain. On 17.5, the scripted form still counts no tokens; the
        Claude form reads `usage`, unverified (above);
      - 17.10: closed in mission 18;
      - 17.11 and 17.12: remain;
      - 17.13: stays closed;
      - 17.14, 17.15: remain;
      - 17.16: remains for the `doctor --live workers` refusal (S5.1). The `doctor --live
        coordinator` refusal is now tested (U5).
    - (11) REVIEW-17 notes 3 (second half), 4 and 5: remain, step S4.2b.

## Findings filed and answered

- **D-014** (G1.3 against O-3's 10 minutes): **decided** by O-26 and O-27. Status line at
  U0, 4ed47b4.
- **D-018** (decision 152 (a)'s entry has no `p` that 153 (b) 1 asks for; REVIEW-19
  should-fix 1):
  - **filed** at U0, 4ed47b4;
  - **answered** by decision 160 (status line at U0);
  - built by U4, 9269ad7.
- **D-019** (the table's whole-record figures cannot be updated day by day with the same
  bits): **filed** at U1, 431a82e. Open, for the owner.
- **D-020** (step 6's figures over W, the same question): **filed** at U2, becb570. Open,
  for the owner.
- **D-021** (`adjusted_E_N` with exposure differs from the plain recompute for a slot
  holding two rows of one date, at d67f708 already): **filed** at U3, e8d31bb. Open, for
  the owner or the role.
- **HF-015** (a reviewer waiting on a sub-agent has no sanctioned way to wait; REVIEW-19
  note 15): **filed** at U0, 4ed47b4. Open, for the hands Project.
  - U1 (431a82e) added a status line: the harness also refused the lone `sleep 240` of
    decision 159 (d).
  - U1 waited instead with one foreground `timeout 1100 bash -c 'while ! grep -q ^real
    <file>; do sleep 15; done'`. U3 waited the same way for its first check run.
- **HF-016** (the builder cannot dispatch a sub-agent): **filed** at 5ca133c on 2026-10-18.
  - Every Agent call was refused by `.claude/hooks/no_background.py`, and the mission
    stopped at U2 with `VERDICT: question`. U2's WIP was stashed as `wip U2 2026-10-18`.
  - The owner traced the refusal to `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`, set in the
    builder role's environment, and removed it (`meta/CHECKPOINT.md`). U2 then resumed
    from the stashed WIP under §R (becb570).
  - The finding's text attributes the refusal to the hook's reading of the Agent tool.
    The cause was an environment setting, as the owner reported; this mission did not
    prove it.
  - FINDINGS.md has no status line for HF-016. It stays open as filed, for the hands
    Project.
- **HF-006, HF-012, HF-010, HF-013:** status lines at U0, 4ed47b4 (REVIEW-19 notes 11 to
  14). All open.
  - HF-006: the first check run of U3, and the third of U1, passed the 20-minute cap and
    were waited for to their end.
  - HF-010: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered at this report
    (`git worktree list`).
- **D-013** (`./scripts/check` time): times lines at U1 (431a82e: 1168, 1196 and 1317 s)
  and U6 (2a614bd: 990, 988 and 982 s at 78b5535). Open (decisions 121 (c), 140).
- D-015, HF-008, HF-009, HF-011 and HF-014 remain open as FINAL-REPORT-19 left them. No
  unit stopped under decision 155 (b) or O-27 item 3. This report's commit carries
  `meta:`, a prefix the review protocol skips (HF-011).

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-19 should-fix 1 (`_rank_p` recomputes the rank rule's `p` on the page; D-018) | U4, decision 160: the entry holds `p`, the page reads it, `_rank_p` removed; D-018 filed at U0, answered by 160 | 4ed47b4, 9269ad7 |
| REVIEW-19 should-fix 2 (the health panel's failure counts untested) | U4, decision 161: `test_the_health_panel_counts_each_models_failures_over_pool_fail_window`, seen red with `window = 20` | 9269ad7 |
| REVIEW-19 should-fix 3 (no speed figure at mission 18's tip) | U7, decision 162: listed under NOT PROVEN as owed; U1's parent figures are the first of O-26's | this commit |
| REVIEW-19 note 1 (G1.3's margin under the cap; D-014 needs a ruling) | answered by O-26 and O-27, 167 (a); D-014 status line at U0; G1.3 458 s at the tip | 4ed47b4 |
| REVIEW-19 note 2 (reviewers' check times; U1's check never seen as one line) | to D-013, open, 167 (a); times lines at U1 and U6 | 431a82e, 2a614bd |
| REVIEW-19 note 3 (the two-sided `t_sf` wrong change's form unstated) | stands, 167 (a) | — |
| REVIEW-19 note 4 (`group_edge`'s `ValueError` fails the day) | to step S4.2b's run-failure handling, 167 (a) | — |
| REVIEW-19 note 5 (`revival` copies lifecycle's `trading_dates` call) | stands, 167 (a) | — |
| REVIEW-19 note 6 (detector events appended again on a retry) | to step S4.2b, 167 (a) | — |
| REVIEW-19 note 7 (`state.json` keeps every inactive health entry) | stands, 167 (a) | — |
| REVIEW-19 note 8 (`dashboard.BAND` is display only) | stands, 167 (a) | — |
| REVIEW-19 note 9 (forbidden edits: none) | no action, 167 (a) | — |
| REVIEW-19 note 10 (FINAL-REPORT-19's NOT PROVEN matches) | no action, 167 (a) | — |
| REVIEW-19 note 11 (a sub-agent moved a run to the background; HF-006) | U0, HF-006 status line, 167 (b); decision 159 (d)'s wait | 4ed47b4 |
| REVIEW-19 note 12 (outside load; HF-006, HF-012) | U0, HF-012 status line, 167 (b) | 4ed47b4 |
| REVIEW-19 note 13 (stale worktrees; HF-010) | U0, HF-010 status line, 167 (b); still registered | 4ed47b4 |
| REVIEW-19 note 14 (sub-agent reports past 12 lines; HF-013) | U0, HF-013 status line, 167 (b) | 4ed47b4 |
| REVIEW-19 note 15 (no sanctioned way to wait) | U0, new HF-015, 167 (b); U1's status line | 4ed47b4, 431a82e |

## Acceptance

- **The check.** Green three times at the pushed tip 78b5535 (990, 988 and 982 s; mission
  19's 1066 to 1131 s), 0 skipped, so the `container` tests ran. Met.
- **The gates.** At the pushed tip 78b5535, with nothing uncommitted but the drafts:
  - G1.1 to G1.4 each printed their PASS line, each under 15 minutes;
  - M3, M2 and M0 printed `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`;
  - every output, the sha and every wall time are under `## Gate`.

  Met.
- **The ratio.** `./scripts/speed` exists and prints decision 156 (c)'s lines. At the tip
  its ratio is 1.166. At U3's commit, 1.234 and 1.246 in the two quiet runs, but above
  1.25 in every run that ended at a load of 2.6 or more. Met at the tip; at U3, met only
  under low load (NOT PROVEN).
- **Byte-identical states.** After a full replay, the state at each of U1, U2 and U3 is
  identical to its parent's outside `.git/`, with the same HEAD tree 5f9c06b7. The cold
  replay's 267 day trees equal the warm replay's. Met.
- **The equality test.** It is in `./scripts/check` and passes at U1 to U5 (their bodies)
  and at the tip. Met.
- **`p` and D-018.** The `rank_persistence` entry holds `p`, and the page recomputes no
  rule's figure. D-018 is filed and answered. Met.
- **The coordinator.** `ClaudeCodeCoordinator` is tested against a fake `claude` only, and
  passes no key in an argument. `--coordinator scripted` stays the default.
  `config/protected_paths.toml` exists, and every path in it is denied by the generated
  settings. Met.
- **Protected files.** Nothing under `tests/gates/` or `tests/fixtures/rejected/` changed.
  No record under `tests/fixtures/config/` changed but the `[coordinator]` table in
  `run.toml`, no entry of `config_frozen.json`, and no frozen value.
  `config/protected_paths.toml` is the one new file under `config/`. Met.
- **The commits.** Each unit commit's body lists its files. The prefixes:
  - U0 `plan:`;
  - U1 `table:`;
  - U2 `alerts:`;
  - U3 `bars:`, the area that took most, as U3 allows;
  - U4 `alerts:`;
  - U5 `coordinator:`;
  - U6 `meta:`.

  Met.
- **Test hygiene.** No test uses the network, a secret or the wall clock. No state or job
  directory is written in the repository, and no test builds the image. Met as the units'
  tests and the check show, except for one caveat: U5's `test_cli_provider` case depends
  on `ANTHROPIC_API_KEY` being unset.
- **This report.** It has `## Speed`, `## Gate` (the four regression gates), `## Owner
  rulings applied`, `## Coordinator`, `## Register`, NOT PROVEN and the review-items
  table. Met.

VERDICT: mission 20 finished
