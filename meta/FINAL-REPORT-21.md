VERDICT: mission 21 finished

# FINAL REPORT — mission 21 (roadmap step S4.2a: REVIEW-20's blocker and should-fix items, persistent_approach's p(N) from the alert state)

Brief: `meta/BUILDER-21-PROMPT.md`. Base e477f67 (`plan: mission 21 kit (S4.2a, closes
REVIEW-20 blocker and should-fix)`). Decisions: `meta/decisions/decisions-2026-10-19-m21.md`
(168 to 176), with items 1 to 167 and the owner's files (O-25, O-26, O-27 and earlier)
still binding where not replaced. This mission closes no milestone and moves no gate of
M4 (decision 168).

Under O-25 and decision 168 (a), the met gates were run again at the pushed tip
c36df23be86c0a4c2229913f10546e189a8c357e, with nothing uncommitted but the git-ignored
drafts: gate M1 item by item, then M3, M2 and M0. All passed. No M1 item took above
O-27's 15 minutes at U1 or at the tip; G1.3 took 462 s at both. The median ratio of
decision 170's three measurements was 1.116 at U1's commit and 1.170 at the tip. Container
runtime: docker. Image: `discotrade-sandbox:3b7d75c39621`, present and nothing built, at
every unit and at the tip. No unit stopped, no unit was retried, and no finding was filed
by U1 to U5.

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | e43c77c | `plan:` the plan, checkpoint and journal. FINDINGS.md gains finding D-022 and its status line (answered, item 169), the HF-015, HF-012 and HF-010 status lines (REVIEW-20 notes 8 to 10) and a D-013 times line (REVIEW-20 note 1) (decision 175 (b)) |
| U1 | 558e02a | `alerts:` each `persistent_approach` entry of the alert state holds `N` and `p_N` (`alerts.PERSISTENT_N`, `PERSISTENT_P_N`, `PERSISTENT_KEYS`); `transition` carries them for that kind only; `ENTRY_KEYS` keeps its four keys; the rank entry's `p` written through `RANK_P` everywhere (169 (e)). `dashboard.py` reads `N` and `p(N)` from each entry (`—` when absent); its `stats.tightened_percentile` and `alerts.in_force` calls are removed. 5 new tests in `test_alerts.py` and `test_dashboard.py`. No existing test changed. No register entry |
| U2 | 943a18c | `tests:` `test_an_unknown_coordinator_is_a_usage_error` parametrized over `bogus`, `Claude` and `scripted:` (171 (a)); new `test_coordinator_claude_with_no_claude_on_path_resolves_none` (171 (b)); the autouse fixture `_no_secret_env` in `tests/conftest.py` and the new `tests/test_secret_env.py` (171 (c)). No file under `src/` |
| U3 | 50341fc | `coordinator:` `fix_session_command` passes `--tools Read,Glob,Grep,Edit,Write`; `session_settings` denies `Bash`, `WebFetch` and `WebSearch` whole, then the `Edit(//...)` path rules (172 (a)). `config/protected_paths.toml`'s `code` list gains decision 172 (b)'s ten entries. 2 new tests and 2 exact-equality tests extended in `test_coordinator_claude.py` (172 (a), 146 (c)). No register entry |
| U4 | d679adc | `tests:` `test_gap_months.py::test_a_rewritten_complete_month_gives_its_new_missing_bars`, parametrized same-rows and other-rows (173). No file under `src/` |
| U5 | 2affd42 | `meta:` the regression gates at the pushed tip c36df23, and one D-013 times line in FINDINGS.md |
| U6 | this commit | this report |

Meta commits ("unit done"): 692b0d5 (U1), e0a8cfa (U2), d0e424e (U3), c36df23 (U4),
16881ff (U5). Each unit commit's body lists every file its stat shows.

Files changed in the mission outside `meta/` (`git diff --stat e477f67 HEAD`):
- new: `tests/test_secret_env.py`;
- changed:
  - `config/protected_paths.toml`;
  - `src/discotrade/alerts.py`, `coordinator.py`, `dashboard.py`;
  - `tests/conftest.py`, `test_alerts.py`, `test_cli_provider.py`,
    `test_coordinator_claude.py`, `test_dashboard.py`, `test_gap_months.py`.

Tests the check runs went from 2560 to 2576 (+16), with 204 gate tests deselected as at
mission 20. By unit: U1 2565, U2 2572, U3 2574, U4 2576.

## Corrections

Decision 174 (a). Three lines of `meta/FINAL-REPORT-20.md`'s `## Acceptance` did not hold
as written. That report is not edited; the corrections are recorded here.

1. FINAL-REPORT-20: "**`p` and D-018.** The `rank_persistence` entry holds `p`, and the
   page recomputes no rule's figure. D-018 is filed and answered. Met."
   - What the disk showed: at mission 20's tip `dashboard.py` still computed
     `persistent_approach`'s `p(N)` with `stats.tightened_percentile`, from the trial count
     and the thresholds in force when the page renders. No state entry held it (REVIEW-20
     blocker 1). That is finding D-022, filed at U0 (e43c77c) and answered by decision 169.
   - Closed by U1, **558e02a**: the entry holds `N` and `p_N`, the page reads them, and
     `dashboard.py` no longer calls `stats.tightened_percentile` or `alerts.in_force`.
2. FINAL-REPORT-20: "**The coordinator.** ... `config/protected_paths.toml` exists, and
   every path in it is denied by the generated settings. Met."
   - What the disk showed: the generated settings held `Edit(...)` path rules only. The
     fix session ran with `--permission-mode acceptEdits` and no tool restriction, so
     `Bash` was not restricted and the claim held for the editing tools only (REVIEW-20
     should-fix 3).
   - Closed by U3, **50341fc**: `--tools` offers exactly `Read`, `Glob`, `Grep`, `Edit` and
     `Write`, and the settings deny `Bash`, `WebFetch` and `WebSearch` whole. That Claude
     Code enforces this stays NOT PROVEN (decision 172 (c)).
3. FINAL-REPORT-20: "**Test hygiene.** No test uses the network, a secret or the wall
   clock. ... Met as the units' tests and the check show, except for one caveat: U5's
   `test_cli_provider` case depends on `ANTHROPIC_API_KEY` being unset."
   - What the disk showed: the caveat was an I-11 defect, not a caveat. With a key set and
     a `claude` on `PATH`, the test failed (`assert 0 == 2`), and a `ClaudeCodeCoordinator`
     was built around the real `/home/msi/.local/bin/claude` (REVIEW-20 should-fix 2).
   - Closed by U2, **943a18c**: the test names really unknown coordinators, the
     `claude`-off-`PATH` path has its own test, and an autouse fixture removes every
     secret variable the source names from each test's environment.

## Check

`./scripts/check` wall times on the builder's machine (four cores, shared). Each run was its
own foreground call with a 20-minute timeout. No run passed the cap.

| Where | Runs | tests |
|---|---|---|
| mission 20's tip 78b5535 (FINAL-REPORT-20) | 990, 988, 982 s | 2560 |
| U1 558e02a | 976, 981, 995 s | 2565 |
| U2 943a18c | 987, 997, 985 s (body: 16m27s, 16m37s, 16m25s) | 2572 |
| U3 50341fc | 994, 990, 994 s (body: 993.7, 990.4, 993.5 s) | 2574 |
| U4 d679adc | 986, 978, 997 s (from `meta/plan.md` and the checkpoint; U4's body gives no times) | 2576 |
| **tip c36df23 (U5)** | **987, 974, 989 s**, each `check: green` | 2576 |

Every tip run printed `2576 passed, 204 deselected` with nothing skipped, so the
`container` tests ran on discotrade-sandbox:3b7d75c39621. Pytest took 970.94 s, 985.72 s
and 983.86 s; `real` was 16m26.628s, 16m13.720s and 16m28.507s. Each also printed `config
check: ok, 173 unverified values` and `check: green`. The outputs are in
`meta/drafts/m21-u5-check{1,2,3}.txt`; each file's first line is
`c36df23be86c0a4c2229913f10546e189a8c357e`, and its second and last lines are
`/proc/loadavg` at the start and end. The 1-minute load was 0.53 to 1.26.

All three tip runs are above HF-006's 15 minutes (D-013 open, times line at U5 2affd42).
They lie within mission 20's tip range give or take 8 s, with 16 more tests.

## Speed

Decision 170's measurement: three complete `./scripts/speed --work <dir>` replays, each
with its own new directory outside the repository, one after another, with no other
check, gate or speed run going on. The figures are first30, last30, the ratio (last30 over
first30) and fresh (one fresh process running the last replay day), as decision 156 (c)
defines them. The load is the 1-minute load average at the start and end of the run.

**At U1's commit 558e02a** (from its body; `--work /tmp/m21u1-speed-{1,2,3}`, one call
each):

| Run | first30 | last30 | ratio | fresh | process starts | load |
|---|---|---|---|---|---|---|
| 1 | 0.027745 | 0.033340 | 1.202 | 6.465 s | 2019-06-03 | 1.02 -> 1.32 |
| 2 | 0.030615 | 0.034158 | 1.116 | 5.981 s | 2019-06-03 | 1.21 -> 1.36 |
| 3 | 0.029319 | 0.032166 | 1.097 | 6.625 s | 2019-06-03 | 1.36 -> 1.33 |

Median ratio **1.116** (at most 1.25).

G1.3 at U1's commit (`./scripts/gate M1 G1.3`, one call): PASS, `10 passed in 460.18s
(0:07:40)`, **462 s** wall (mission 20 U6 at 78b5535: 458 s).

**At the tip c36df23** (U5; `meta/drafts/m21-u5-speed{1,2,3}.txt`, verbatim under `##
Gate`, one call each):

| Run | first30 | last30 | ratio | fresh | process starts | load | wall |
|---|---|---|---|---|---|---|---|
| 1 | 0.027375 (21 days) | 0.032780 (22 days) | 1.197 | 6.460 s | 2019-06-03 | 1.17 -> 1.30 | 459.8 s |
| 2 | 0.027532 (21 days) | 0.032210 (22 days) | 1.170 | 5.585 s | 2019-06-03 | 1.27 -> 1.18 | 465.3 s |
| 3 | 0.030026 (21 days) | 0.032900 (22 days) | 1.096 | 5.831 s | 2019-06-03 | 1.18 -> 1.17 | 470.9 s |

Median ratio **1.170** (at most 1.25). Mission 20's single tip run gave 1.166 (load 1.47 to
1.11). No run was dropped, repeated or killed, at U1 or at the tip.

U1 changes what a day writes (`N` and `p_N` in the entry), so it is not a speed unit and
made no byte-identical comparison with its parent (decision 169 (f)). Item 157 (c)'s
equality test (`tests/test_speed_equality.py`) is unchanged and passed in every unit's
check and at the tip.

## Gate

The regression gates under O-25 (decision 168 (a)) were run at the pushed tip
c36df23be86c0a4c2229913f10546e189a8c357e (U4 done):
- nothing uncommitted but the git-ignored drafts;
- after `./scripts/check` was green three times there;
- each run its own foreground call with a 20-minute timeout;
- in this order: the three checks, `discotrade sandbox build`, G1.1, G1.2, G1.3, G1.4, M3,
  M2, M0, then the three speed runs.

The tip c36df23 differs from U4's commit d679adc only under `meta/`. This report's parent
16881ff differs from the tip only by `meta/findings/FINDINGS.md` (2affd42) and the U5
meta files.

In each output below, the first line is `git rev-parse HEAD`, and the second and last
lines are `/proc/loadavg` at the start and end of the run.

`uv run discotrade sandbox build` (`meta/drafts/m21-u5-sandbox.txt`, verbatim), run after
the three checks:

```
c36df23be86c0a4c2229913f10546e189a8c357e
sandbox build: present, nothing built
discotrade-sandbox:3b7d75c39621

real	0m0.659s
user	0m0.855s
sys	0m0.077s
```

### Gate M1

Item by item (O-2). Each output below is verbatim from `meta/drafts/m21-u5-<item>.txt`.

`./scripts/gate M1 G1.1` at c36df23: wall 282 s (mission 20 U6 at 78b5535: 279 s)

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.16 1.22 1.17 1/790 2695702
G1.1 PASS 6 passed, 1 warning in 280.67s (0:04:40)
gate M1 G1.1: PASS

real	4m41.706s
user	4m9.529s
sys	0m9.971s
1.35 1.25 1.19 2/790 2702856
```

`./scripts/gate M1 G1.2` at c36df23: wall 169 s (mission 20 U6: 170 s)

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.35 1.25 1.19 1/790 2702862
G1.2 PASS 4 passed in 168.27s (0:02:48)
gate M1 G1.2: PASS

real	2m49.108s
user	2m36.756s
sys	0m5.740s
1.03 1.16 1.17 1/788 2705559
```

`./scripts/gate M1 G1.3` at c36df23: wall 462 s (mission 20 U6: 458 s)

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.03 1.16 1.17 2/789 2705566
G1.3 PASS 10 passed in 460.60s (0:07:40)
gate M1 G1.3: PASS

real	7m41.926s
user	7m6.436s
sys	0m17.807s
1.37 1.22 1.19 1/789 2713673
```

`./scripts/gate M1 G1.4` at c36df23: wall 1 s (mission 20 U6: 1 s)

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.37 1.22 1.19 1/790 2713680
G1.4 PASS 15 passed in 0.57s
gate M1 G1.4: PASS

real	0m1.161s
user	0m1.349s
sys	0m0.099s
1.37 1.22 1.19 1/793 2713693
```

| Item | mission 20 U6 at 78b5535 | U1 558e02a | tip c36df23 |
|---|---|---|---|
| G1.1 | 279 s | — | 282 s |
| G1.2 | 170 s | — | 169 s |
| G1.3 | 458 s | 462 s | 462 s |
| G1.4 | 1 s | — | 1 s |

Every M1 item is under O-27's 15 minutes at U1 and at the tip. No finding was filed under
O-27 item 3.

### Gate M3

`./scripts/gate M3` at c36df23: wall 503 s (mission 20 U6 at 78b5535: 506 s). Verbatim from
`meta/drafts/m21-u5-M3.txt`:

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.26 1.20 1.18 1/793 2713706
G3.1 PASS 3 passed in 190.65s (0:03:10)
G3.2 PASS 9 passed in 153.30s (0:02:33)
G3.3 PASS 10 passed in 157.04s (0:02:37)
gate M3: PASS

real	8m23.041s
user	8m9.215s
sys	0m9.320s
1.15 1.13 1.13 1/789 2716451
```

### Gate M2

`./scripts/gate M2` at c36df23: wall 132 s (mission 20 U6: 130 s). Verbatim from
`meta/drafts/m21-u5-M2.txt`:

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.06 1.11 1.13 1/790 2716462
G2.1 PASS 36 passed in 40.81s
G2.2 PASS 3 passed in 23.59s
G2.3 PASS 8 passed in 4.48s
G2.4 PASS 9 passed in 39.21s
G2.5 PASS 5 passed in 20.99s
gate M2: PASS

real	2m11.859s
user	0m40.513s
sys	0m3.668s
1.15 1.18 1.15 1/791 2722470
```

### Gate M0

`./scripts/gate M0` at c36df23: wall 245 s (mission 20 U6: 244 s). Verbatim from
`meta/drafts/m21-u5-M0.txt`:

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.15 1.18 1.15 1/789 2722479
G0.1 PASS 62 passed in 56.81s
G0.2 PASS 7 passed in 91.96s (0:01:31)
G0.3 PASS 13 passed in 93.17s (0:01:33)
G0.4 PASS 4 passed in 0.70s
gate M0: PASS

real	4m5.009s
user	4m7.139s
sys	0m4.289s
1.27 1.18 1.15 1/788 2723344
```

No M3, M2 or M0 item took above 15 minutes. `git diff --stat e477f67 HEAD -- tests/gates`
is empty: no file under `tests/gates/` changed in this mission.

The three measurements at the tip (`meta/drafts/m21-u5-speed{1,2,3}.txt`, verbatim):

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.17 1.16 1.15 2/792 2723359
speed first30: 0.027375 s per subject-day (21 days counted)
speed last30: 0.032780 s per subject-day (22 days counted)
speed ratio: 1.197
speed fresh last day: 6.460 s
speed process starts: 2019-06-03
speed: done

real	7m39.787s
user	7m1.029s
sys	0m19.113s
1.30 1.12 1.10 1/791 2731510
```

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.27 1.11 1.10 1/793 2731525
speed first30: 0.027532 s per subject-day (21 days counted)
speed last30: 0.032210 s per subject-day (22 days counted)
speed ratio: 1.170
speed fresh last day: 5.585 s
speed process starts: 2019-06-03
speed: done

real	7m45.319s
user	7m4.132s
sys	0m19.449s
1.18 1.23 1.17 1/785 2739689
```

```
c36df23be86c0a4c2229913f10546e189a8c357e
1.18 1.23 1.17 1/789 2739704
speed first30: 0.030026 s per subject-day (21 days counted)
speed last30: 0.032900 s per subject-day (22 days counted)
speed ratio: 1.096
speed fresh last day: 5.831 s
speed process starts: 2019-06-03
speed: done

real	7m50.943s
user	7m9.143s
sys	0m20.050s
1.17 1.17 1.17 2/797 2748423
```

## Coordinator

Changed by U3 (50341fc).

**Version and help line.** Read from the installed binary, as U3's body quotes them:
- `claude --version`: `2.1.303 (Claude Code)`.
- `claude --help`, the `--tools` line:

```
--tools <tools...>  Specify the list of available tools from the built-in
set. Use "" to disable all tools, "default" to use all tools, or specify
tool names (e.g. "Bash,Edit,Read").
```

**The fix session's command** (`coordinator.fix_session_command`), with `--tools` in the
help's comma-separated form, as one argument:

```
<binary> --bare -p --output-format json --max-budget-usd <usd> --permission-mode acceptEdits --model <model> --tools Read,Glob,Grep,Edit,Write --settings <work_dir>/settings.json
```

Nothing calls it while `propose_fixes` is false (v1). The ordinary coordinator call is
unchanged: `--tools ""`, no settings.

**The deny rules now generated** (`coordinator.session_settings`, written to
`<work_dir>/settings.json` as `{"permissions": {"deny": [...]}}`), in this order:
- the whole-tool rules (`coordinator.DENIED_TOOLS`): `Bash`, `WebFetch`, `WebSearch`;
- then the path rules (`coordinator.deny_rules`, unchanged by U3): one `Edit(//<absolute
  path>)` rule per protected path, with `/**` after a directory. `code` paths are
  resolved under the code repository and `state` paths under the state directory.
  `EDIT_TOOLS` stays `("Edit",)`, since the permissions page says `Edit` rules apply to
  all built-in tools that edit files.

U3 chose to keep the whole-tool rules in `session_settings`, not `deny_rules`, so
`deny_rules` stays the path rules alone (its body names this as the simplest choice where
the design is silent).

**The protected paths** (`config/protected_paths.toml`, not frozen):
- `code`:
  - held at mission 20's tip: `src/discotrade/backtest.py`, `costs.py`, `executor.py`,
    `metrics.py`, `paper.py`, `controls.py`, `ledger.py`, `lifecycle.py`, `journal.py`,
    `stats.py`, `table.py`, `alerts.py`, `coordinator.py`; `src/discotrade/validation/`,
    `src/discotrade/sandbox/`, `config/`, `reference/`, `tests/gates/`;
  - **added by U3** (decision 172 (b)): `src/discotrade/config.py`,
    `src/discotrade/workers/providers.py`, `CLAUDE.md`, `DESIGN.md`, `SPEC.md`,
    `PLAYBOOK.toml`, `meta/`, `.claude/`, `docs/ARCHITECT-HANDBOOK.md`, `templates/`.
- `state` (unchanged): `bars/`, `rolls/`, `approaches/`, `trials/`, `journal/`, `paper/`,
  `controls/`, `ledger/`, `responses/`, `stats/`, `table/`, `alerts/`, `dashboard/`,
  `health/`.

No entry was removed. The file's parser accepted `.claude/` unchanged, so no finding was
needed under 172 (b).

## Register

`git diff e477f67 HEAD -- tests/fixtures/return_readers.toml` is empty: no entry of
`tests/fixtures/return_readers.toml` was added or changed in this mission. **None.**

U1 changed `alerts.persistent_approach`, which stays registered with its entry unchanged;
`transition`, `_alerts_panel` and the new `_held_shown` hold no reference shape. U3 added
no function with a reference shape. U2 and U4 change no file under `src/`. Each body says
the audit (`tests/test_return_readers.py`) passes, and it ran in every check.

## What the tests prove

Only what the tests assert, on their inputs. The units' bodies give each test and each
wrong change.

U1 (558e02a):
- On the persistent fixture state, the alert step writes into every `persistent_approach`
  entry the rule's `N` and the `p(N)` the test computes itself from DESIGN §11.4's formula
  (not through `stats.tightened_percentile`). The entry's key set is exactly `ENTRY_KEYS`
  plus `N` and `p_N`; other kinds' entries hold exactly `ENTRY_KEYS`.
- `transition` carries `N` and `p_N` for `persistent_approach` only.
- The page shows an entry's `N` and `p(N)` as held, for an entry whose values the trials
  ledger and the thresholds in force would not give; an entry without them shows the dash
  for both; stored entries hold them and the page shows them.
- Seen to fail at the parent (5 failed). Wrong change, made alone and reverted: the page
  calling `stats.tightened_percentile` on the trials ledger's count; two dashboard tests
  went red.

U2 (943a18c):
- `test_an_unknown_coordinator_is_a_usage_error[bogus|Claude|scripted:]`: exit 2,
  `--coordinator` in the error, no file changed.
- With a dummy key and `PATH` an empty temporary directory, `run-day` and `replay` with
  `--coordinator claude` print one line, exit 1, change no file, every `shutil.which` call
  returns `None`, and no `ClaudeCodeCoordinator` is built. The no-key path is held by the
  existing `test_cli.py::test_coordinator_claude_is_refused_before_any_day[no key-*]`.
- Inside a test, `ANTHROPIC_API_KEY`, `NEBIUS_API_KEY` and `DATABENTO_API_KEY` are absent;
  the fixture's list is exactly these three; every string literal under `src/discotrade/`
  shaped `*_API_KEY`, `*_TOKEN` or `*_SECRET` is one of them.
- Under `ANTHROPIC_API_KEY=sk-dummy-not-a-key` in the environment, `test_secret_env.py`,
  `test_cli_provider.py`, `test_cli.py`, `test_coordinator_claude.py`,
  `test_workers_providers.py` and `test_doctor.py`: 201 passed.
- Seen to fail, each made alone and reverted: the fixture's body dropped under a dummy
  key; `make_coordinator`'s `shutil.which` check disabled; `--coordinator` mapping
  `bogus`/`Claude` to scripted; a `PUSHOVER_TOKEN` constant added under `src/`.

U3 (50341fc), against a fake `claude` only:
- The fake started through `fix_session_command` receives `--tools` once, with exactly
  `Read`, `Glob`, `Grep`, `Edit` and `Write`, and no `--allowedTools`.
- The settings it receives deny exactly the three whole-tool rules plus every path rule
  read from `config/protected_paths.toml` (exact equality), and `session_settings` gives
  the same.
- The protected paths file holds decision 172 (b)'s entries.
- Seen to fail, each made alone and reverted: `--tools` dropped (1 red); `Bash` dropped
  from `DENIED_TOOLS` (3 red). The new tests were seen to fail before the code (4 red).

U4 (d679adc):
- Under one store root, after June 2019 is complete and its missing bars read through
  `gaps.find_missing`, June rewritten with other bars missing (same row count and another
  hash, or another row count) gives, with no cache cleared, the missing bars the test
  computes from the times it wrote.
- Wrong change, made alone and reverted: `rows` and `hash` dropped from `_MONTH_MISSING`'s
  key in `src/discotrade/bars/gaps.py`; both cases red at the second read.

The gates (U5): G1.1 to G1.4 PASS, `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS` at
the pushed tip c36df23, with nothing uncommitted but the drafts. `./scripts/check` green
three times there, 0 skipped.

## NOT PROVEN

Items of the U6 brief:
- **Mission 20 U3's ratio at `e8d31bb`** stays as REVIEW-20 recorded it: at or below 1.25
  only in the quiet-load runs (1.234, 1.237, 1.246), up to 2.104 under load. Decision 170
  (c) does not reopen mission 20's units, and no median of three was measured at
  `e8d31bb`.
- **The speed figures are from the builder's machine** (four cores, shared), under the
  loads given in `## Speed` (1-minute load 1.02 to 1.36 at U1, 1.17 to 1.30 at the tip).
  That the median stays at or below 1.25 under heavier load, or on another machine, is
  not proven. The six runs of this mission span 1.096 to 1.202.
- **No real `claude` was called** (live check L4 not run). `--tools` and the deny rules
  are proven against the argument list and the settings a fake receives, not against
  Claude Code enforcing them (decision 172 (c)). The `--tools` syntax is taken from the
  installed help (2.1.303), and the deny-rule syntax from the permissions page.
- **A state written before U1** shows `—` for `N` and `p(N)` on the page. No state is
  rewritten to add them, so a page rendered from an older state does not show the figures
  the rule used then.
- **U1:** that a page renders the same figures for states other than those tested.
- **U2:**
  - the autouse fixture is function-scoped (`monkeypatch`), so module- and session-scoped
    fixtures still see the environment's secrets;
  - the source scan catches only string literals shaped `*_API_KEY`, `*_TOKEN` or
    `*_SECRET`; a secret variable named otherwise would not be found.
- **U4:** the replacement is not purely through the writers. `BarStore.append` refuses a
  bar not later than the last stored one (I-5), and recovery only completes an
  interrupted append, so the store cannot replace a complete month in place. The test
  deletes the track's index and month files, then writes the new content through
  `BarStore.append` under the same root (its docstring says so). That no other writer
  path could change a complete month without changing its index `rows` or `hash` is not
  proven (none exists today).
- U4's body gives no check times; the three times (986, 978, 997 s) come from the
  builder's record in `meta/plan.md` and the checkpoint.

What remains of FINAL-REPORT-20's NOT PROVEN, item by item:
1. **No figure at mission 18's tip** (REVIEW-19 should-fix 3, owed): remains.
2. **The live loop's cost still grows with history:** remains. The fourth figure at the
   tip was 6.460, 5.585 and 5.831 s (mission 20's tip: 5.493 s), with no threshold.
3. **Speed figures from the builder's machine; the ratio's sensitivity to load; U3's
   margin:** remains (above). The binding figure is now the median of three (decision 170),
   at U1 and at the tip. That the check's drop in mission 20 came from the speed units:
   remains unmeasured.
4. **No real `claude` called:** remains (above); now also covers `--tools` and the
   whole-tool deny rules.
5. **The coordinator's `model`, `max_budget_usd` and `timeout_seconds`** are the project's
   choices, unverified: remains.
6. **`test_an_unknown_coordinator_is_a_usage_error` passes only with the key unset:**
   closed by U2, 943a18c (`## Corrections` 3).
7. Mission 20 U1: the table's residual growth (D-019) the only growth; the speed test's
   fresh child opening no connection: remain.
8. Mission 20 U2: step 6's residual growth only what D-020 names; another column type
   taking the fallback: remain.
9. Mission 20 U3: the parts named the only growth left; the day loop taking the two-rows
   fallback (D-021): remain.
10. Mission 20 U4: no byte-identical comparison with the parent: remains. Mission 21 U1
    also changes what a day writes and made none (decision 169 (f)); the equality test
    passes.
11. HF-016's cause (an environment setting, as the owner reported): remains not proven by
    the builder.
12. Mission 20 U6's sandbox build before the checks: superseded for this mission. At
    c36df23 it ran after the three checks, as U5 step 2 lists; the image was present
    throughout, so the checks' `container` tests ran (0 skipped).
13. FINAL-REPORT-19's items, as FINAL-REPORT-20 carried them:
    - (1) no finding alert fires on any replay a gate runs: remains (S4.3);
    - (2) the bootstrap's quantile and the t-test checked against the tests' own
      computation: remains. U1's `p(N)` is also checked against the test's own §11.4
      formula. The page now derives neither `p` nor `p(N)`;
    - (3) the dashboard on a phone: remains;
    - (4) `no_finding` not called by the day loop: remains, S4.2b;
    - (5) speed from the builder's machine, and the check above HF-006's 15 minutes:
      remain; the check is now 974 to 989 s at the tip (D-013 open);
    - (6) to (10) mission 19's U1, U2, U4 and U5 items (the check's rise, 147 (d)'s
      equality beyond the enumerated cases, the rank rows' `timing`,
      `few_valid_candidates` and `cost_stale` in a day-loop run, O-14's figures and the
      bands not asserted on the page, `journal_mismatch` on the health panel): remain;
    - (11) why G1.3 doubled, not measured per test: remains;
    - (12) G4.5, the dashboard's gate test: remains, S4.3;
    - (13) FINAL-REPORT-18's carried items: (1) remains and covers the Claude coordinator;
      (2) G3.3's leak checks on `test_synth` only: remains (G3.3 PASS at c36df23); (3) to
      (8): remain; (9) superseded, this mission's gates ran at c36df23, which differs from
      this report's parent only under `meta/`; (10) FINAL-REPORT-17's items remain as
      FINAL-REPORT-20 left them (17.10 and 17.13 closed); (11) REVIEW-17 notes 3 to 5:
      remain, S4.2b.

This mission added no number from outside the project.

## Findings filed and answered

- **D-022** (decision 153 (b) 2's `p(N)` recomputed by the page against 152 (a); REVIEW-20
  blocker 1): **filed** at U0, e43c77c, with its status line **answered** by decision 169.
  Built by U1, 558e02a.
- **HF-015** (no sanctioned way to wait): status line at U0, e43c77c (REVIEW-20 note 8;
  decision 176 now makes the foreground poll call the wait). Open.
- **HF-012** (five sub-agents at once on four cores): status line at U0, e43c77c
  (REVIEW-20 note 9). Open.
- **HF-010** (stale worktrees): status line at U0, e43c77c (REVIEW-20 note 10). Open;
  `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered at this report (`git
  worktree list`).
- **D-013** (`./scripts/check` time): times lines at U0 (e43c77c, REVIEW-20 note 1's
  figures) and U5 (2affd42: 987, 974 and 989 s at c36df23). Open (decisions 121 (c), 140).
- No new finding was filed by U1 to U5. No unit stopped under decision 168 (b) or O-27
  item 3, and no median exceeded 1.25.
- D-019, D-020 and D-021 stay open for the owner (`meta/BACKLOG.md`; decision 175 (a)).
  HF-016 stays open as filed. D-015, HF-006, HF-008, HF-009, HF-011, HF-013 and HF-014
  remain as FINAL-REPORT-20 left them. This report's commit carries `meta:`, a prefix the
  review protocol skips (HF-011).

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-20 blocker 1 (the page recomputes `persistent_approach`'s `p(N)`; no finding filed) | U1, decision 169: `N` and `p_N` in each entry, the page reads them, `tightened_percentile` gone from `dashboard.py`; D-022 filed at U0, answered by 169 | e43c77c, 558e02a |
| REVIEW-20 should-fix 1 (which `./scripts/speed` ratio binds) | U1 and U5, decision 170: the median of three complete measurements; 1.116 at U1, 1.170 at the tip | 558e02a, 2affd42 |
| REVIEW-20 should-fix 2 (the unknown-coordinator test passes for the wrong reason; I-11) | U2, decision 171: unknown coordinators parametrized, `claude` off `PATH` tested, autouse secret-free fixture | 943a18c |
| REVIEW-20 should-fix 3 (fix-session deny rules cover `Edit` only) | U3, decision 172 (a): `--tools` file tools only; `Bash`, `WebFetch`, `WebSearch` denied | 50341fc |
| REVIEW-20 should-fix 4 (`_MONTH_MISSING`'s content identity untested) | U4, decision 173: the rewritten-month test, seen red without `rows` and `hash` | d679adc |
| REVIEW-20 note 1 (reviewers' check runs past the cap) | D-013 times line at U0, decision 175 (a), (b); D-013 open | e43c77c |
| REVIEW-20 note 2 (D-021) | stays open for the owner with D-019 and D-020, in `meta/BACKLOG.md`, decision 175 (a) | — |
| REVIEW-20 note 3 (O-4's subtraction outside `paper.py` at becb570) | stands, decision 175 (a) (the tip conforms since mission 20 U3) | — |
| REVIEW-20 note 4 (U3 left `dashboard.py` unchanged) | stands, decision 175 (a) | — |
| REVIEW-20 note 5 (protected paths missing `config.py`, `providers.py`, CLAUDE.md's documents) | U3, decision 172 (b): ten entries added | 50341fc |
| REVIEW-20 note 6 (literal `"p"`; speed's bookkeeping; `max_turns`) | literal `"p"`: U1, decision 169 (e), written through `RANK_P`; the bookkeeping: stands, decision 170 (d); `max_turns`: no action | 558e02a |
| REVIEW-20 note 7 (the stop at U2, HF-016) | HF-016's status line already on the branch, decision 175 (a) | — |
| REVIEW-20 note 8 (the lone `sleep 240` refused; HF-015) | U0, HF-015 status line, decision 175 (b); decision 176 the wait | e43c77c |
| REVIEW-20 note 9 (five sub-agents at once; HF-012) | U0, HF-012 status line, decision 175 (b) | e43c77c |
| REVIEW-20 note 10 (stale worktrees; HF-010) | U0, HF-010 status line, decision 175 (b); still registered | e43c77c |

## Acceptance

- **The check.** `check: green` three consecutive times at the pushed tip c36df23 (987,
  974 and 989 s; mission 20's 982 to 990 s), 0 skipped, so the `container` tests ran. Met.
- **The gates.** At the pushed tip c36df23, with nothing uncommitted but the drafts:
  - G1.1 to G1.4 each printed their PASS line, each within 15 minutes (282, 169, 462 and
    1 s);
  - M3, M2 and M0 printed `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`;
  - every output, the sha and every wall time are under `## Gate`.

  Met.
- **The ratio.** Median of decision 170's three measurements: 1.116 at U1's commit
  558e02a and 1.170 at the tip, each at most 1.25, with each run's figures and loads under
  `## Speed`. Met.
- **`N`, `p_N` and D-022.** Each `persistent_approach` entry holds the rule's `N` and
  `p_N` (U1's tests). `dashboard.py` calls no function that computes a rule's figure, as
  U1's 169 (c) list shows; `grep` finds no `tightened_percentile` or `in_force` in it. D-022
  is filed and answered (e43c77c, item 169). Met.
- **The unknown-coordinator test and the environment.**
  `test_an_unknown_coordinator_is_a_usage_error` names `bogus`, `Claude` and `scripted:`
  only. Decision 171's tests pass in the check (no key) and under a dummy
  `ANTHROPIC_API_KEY` (201 passed, U2's body). Met.
- **The fix session.** Its argument list offers exactly `Read`, `Glob`, `Grep`, `Edit` and
  `Write`; its settings deny `Bash`, `WebFetch` and `WebSearch` and `Edit` on every path of
  `config/protected_paths.toml`, which holds decision 172 (b)'s entries. The tests hold
  this against a fake `claude`. Met (enforcement by Claude Code: NOT PROVEN).
- **`_MONTH_MISSING`.** A test pins its content identity, seen to fail without `rows` and
  `hash` in its key (d679adc). Met.
- **Protected files.** `git diff --stat e477f67 HEAD -- tests/gates tests/fixtures/rejected
  tests/fixtures/config tests/fixtures/config_frozen.json config/` shows only
  `config/protected_paths.toml | 14 ++++++++++++++`. No file under `tests/gates/` or
  `tests/fixtures/rejected/`, no record under `tests/fixtures/config/`, no entry of
  `config_frozen.json` and no frozen value changed. `config/protected_paths.toml` is the
  one file under `config/` that changed. Met.
- **The commits.** Each unit commit's body lists every file its stat shows. The prefixes:
  U0 `plan:`, U1 `alerts:`, U2 `tests:`, U3 `coordinator:`, U4 `tests:`, U5 `meta:`. Met.
- **Test hygiene.** No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no test builds the image. Met as the units'
  tests and the check show. The secret part is now held by U2's autouse fixture and
  `test_secret_env.py`, within the limits under NOT PROVEN (function scope; the name
  pattern of the source scan).
- **This report.** It has `## Corrections`, `## Speed`, `## Gate` (the four regression
  gates), `## Coordinator`, `## Register`, NOT PROVEN and the review-items table. Met.

VERDICT: mission 21 finished
