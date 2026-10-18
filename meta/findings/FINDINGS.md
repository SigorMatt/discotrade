# FINDINGS — the ledger

Append-only; a correction is appended, never edited in. Two series:

- `D-###` — findings about discotrade: its design, its spec, its plan, its
  code. Section "discotrade findings".
- `HF-###` — findings about hands itself: its guard, its hooks, its
  documents, its playbook engine, its notifications. Section "hands
  findings". They are never fixed or worked around in this project's
  product code. The human carries them to the hands Project.

Every entry has: severity, component, symptom with evidence (command and
output, file and line), direction, and `Status: open | fixing | fixed <sha>
| deferred <gate> | rejected <reason> | answered <decisions file>`.

---

## discotrade findings

### D-001 — the instrument record cannot hold top-level companions: `source` is already the `[source]` table

Severity: low · Component: DESIGN §4 (companions) with §4.2 (instrument
record) · Found: 2026-10-12, mission 1 U2.

Symptom. DESIGN §4 stores every number from outside the project with the
companions `checked`, `source` and `verified`. In the §4.2 instrument
record, `multiplier`, `tick_size`, `trusted_from` and `main_session` are
top-level keys taken from the exchange's contract specification, so their
companions would be top-level keys too; but the record's top level already
has the table `[source]`, and TOML refuses a key `source` beside it:

    tomllib.TOMLDecodeError: Cannot overwrite a value (at line 29, column 8)

(from an instrument file with `source = "..."` at the top level and a
`[source]` table). DESIGN is silent on where those four values' companions
go.

What U2 did (the simplest thing, stated in its commit body): a `[spec]`
table holding only `checked`, `source` and `verified`, which covers the four
top-level contract-specification values; `[cost]` keeps its own companions
as §4.2 shows. `[spec]` is required for an instrument whose adapter is not
`synth` and optional for synthetic ones, whose values the project invents.

Direction (for the architect). Confirm `[spec]`, or name another place in
DESIGN §4.2.

Status: open

---

### D-002 — the window gap fraction cannot see an instrument whose feed stopped

Severity: medium · Component: DESIGN §5.4 (gap check, window fraction) ·
Found: 2026-10-12, mission 1 U5.

Symptom. §5.4 defines missing bars only from the later of `trusted_from`
and the first stored bar to the last stored bar, then says the window
fraction is "missing bars over expected bars". U5 counts both numerator and
denominator over that same checked span (`src/discotrade/bars/gaps.py`,
`check_gaps`). Under that reading, an instrument whose source returns
nothing after some date adds neither missing nor expected bars to T: with
three of four instruments complete and the fourth stopped a week ago, T's
pooled fraction is 0 and generation is not skipped. Counting expected bars
of the whole window in the denominator while keeping the span-limited
numerator would only dilute the fraction further.

Direction (for the architect). Decide whether a window's missing bars run
to the end of the window (the end of `D`'s trading day) rather than to the
last stored bar, so that a stopped or absent feed counts as gaps in T, or
whether a stale feed is a separate health condition.

Status: open

---

D-001 status (appended 2026-10-12, mission 2 U0): Status: answered meta/decisions/decisions-2026-10-12.md

D-002 status (appended 2026-10-12, mission 2 U0): Status: answered meta/decisions/decisions-2026-10-12.md

---

### D-003 — the provenance strings of the instrument records read stronger than what was done

Severity: low · Component: `config/instruments/*.toml` (`[spec]` and
`[cost]` companions) with DESIGN §4 and §4.2 · Found: REVIEW-1 should-fix
5, filed 2026-10-12, mission 2 U0.

Symptom. Each of the eight instrument records has a `[spec]` table with
`checked = "2026-10-12"` and a `source` naming the exchange's
contract-specification page "(multiplier, tick size)", which implies the
page was read that day; FINAL-REPORT-1 NOT PROVEN says the values are from
memory of those pages (`verified = false` is set honestly). Likewise
`[cost] source = "SPEC.md §17"` also covers the spread ticks and
`slippage_coef = 0.02`, which come from DESIGN §4.2 / R-5, not SPEC §17.

Direction. These are values of frozen files (DESIGN §4.3); no builder
changes them. The owner rewrites the `checked` and `source` strings by a
frozen-config change (decisions-2026-10-12 item 17; `meta/BACKLOG.md`).

Status: open

---

### D-004 — `max_drawdown`: does the start of the running sum (0) count as a peak?

Severity: medium (blocks G0.1) · Component: DESIGN §8 (`max_drawdown`) with
`src/discotrade/metrics.py` and `tests/gates/independent_calc.py` · Found:
2026-10-12, mission 5 U4.

Symptom. DESIGN §8 says only "`max_drawdown`: the largest peak-to-trough
fall of the running sum of `d`"; no decision adds to it. The two
implementations read it differently:

- `src/discotrade/metrics.py` `max_drawdown` prepends 0 to the running sum
  (`np.concatenate([[0.0], np.cumsum(x)])`): the start counts as a peak, so
  a fall from 0 to the first days counts.
- `tests/gates/independent_calc.py` `max_drawdown` (its docstring: "no
  leading zero", a choice stated as made where DESIGN is silent) takes
  peaks only among `cum[0..n-1]`.

Evidence. The draft gate `tests/gates/test_g0_1_reference.py` (uncommitted)
on `test_mixed`, window 2019-06-03 to 2019-07-31, `bars fetch` at
2019-08-05T00:00Z, `reference/zscore_reversal.py`: the daily series starts
at -0.006513454317145457 on 2019-06-03 and the running sum never returns
above it; its trough is -0.2224480187314558 on 2019-07-31. discotrade gives
`max_drawdown` 0.22244801873145578 (module and `backtest --json`); the
independent calculation gives 0.21593456441431036. Every other per-bar
field, daily value, metric and cost total of the three reference
strategies is equal to 1e-12 (20 of 22 tests pass; the two failures are
this metric, module and `--json`).

Direction (for the architect). Decide whether the running sum starts at 0
(an equity curve that begins flat, so a loss on the first day is a
drawdown) or at the first day's value; then one of the two implementations
changes to match, with a unit test.

Status: open

D-004 status (appended 2026-10-12, mission 5 U4): Status: answered by the phone architect, recorded in meta/plan.md, to be carried as decision 41.

---

### D-005 — G0.1's data cannot see a roll cost on `h(u)` nor the half-tick spread floor

Severity: low · Component: DESIGN §18.3 G0.1 with the frozen fixtures
`tests/fixtures/config/` (SYNA, SYNL, SYNX, `spreads/SYNA.toml`) and
`reference/` · Found: 2026-10-12, mission 5 U4.

Symptom. U4's brief names two wrong changes the G0.1 test should be seen to
fail on. Neither can fail it on the fixture data, whatever the window:

- Roll cost on `h(u)` instead of `h(u-1)` (`executor.py`,
  `costs.roll_cost(order.target, ...)`): at both SYNA rolls up to
  2019-08-05 (2019-03-14T00:00Z, 2019-06-14T00:00Z), every reference
  strategy has `h(u-1) == h(u)` (trend_ma -1/-1 and 1/1, zscore_reversal
  0/0 and -1/-1, hour_of_day 0/0), so the two readings give the same cost.
  The draft test passed with the change in place.
- Half spread without its floor (`max(ticks/2, 0.5)` to `ticks/2`): every
  spread value of SYNA's table and of SYNL's and SYNX's main/off settings
  is at least 1 tick, so the floor never binds. The draft test passed with
  the change in place.

Wrong changes the draft test did fail on: `sigma` with `ddof=0`; `gross`
without the roll gap in `Ca(u-1)`; the spread floor raised to a full tick.

Direction (for the architect). Either accept that G0.1 does not prove
these two (G0.3 covers "a carried position pays the roll cost and a flat
one does not"; a unit test can cover the floor), or add fixture data where
a position changes at a roll bar and a spread below one tick applies (a new
fixture record or table, frozen files being unchangeable).

Status: open

---

### D-006 — `backtest` shares one loaded strategy across a subject's instruments

Severity: low to medium (not reproduced) · Component: DESIGN §6.2, §12.1,
§12.4 with I-2 and decision 40; `backtest` in `src/discotrade/cli.py` ·
Found: 2026-10-12, mission 5 U5 (reported by its sub-agent, not reproduced
by the orchestrator).

Symptom. U5's G0.2 test loads the cheating strategy afresh for each
evaluation. The sub-agent reports that the `backtest` command loads the
strategy once and evaluates every instrument of the subject with it. A
strategy that keeps module-level references to the frames it was given
(decision 40's first item) could then, while evaluating a later
instrument, read bars of an earlier instrument that are later than the
current bar's close. G0.2 as built does not exercise this.

Direction (for the architect). Decide whether each instrument's evaluation
gets a freshly loaded strategy (or the sandbox of §12.4 is the only
answer), and whether G0.2 should drive the cheating text through the
multi-instrument path.

Status: open

---

### D-007 — `run-day` refused a weekend trading day of a mixed-calendar track at decision 72's clock

Severity: low (resolved in code, needs confirmation) · Component: DESIGN
§16.1 step 1, §16.4 with decisions 51 and 72; `_locked` / `_unclosed` in
`src/discotrade/daily.py` · Found: 2026-10-13, mission 9 U2 (reported by
its sub-agent; the orchestrator read the diff).

Symptom. `run-day` refused any `D` later than the earliest, across the
track's instruments, of each instrument's latest closed trading day. On
`test_mixed` (SYNX trades every day, SYNA on weekdays) the Saturday run at
its close (2019-06-09 00:00 UTC) was refused because SYNA's latest closed
day was Friday. Decision 72 requires the replay to run every trading day
of the track with the clock at the close of that day's last expected bar,
so the old refusal made decision 72 impossible on a track whose calendars
differ. The mission 9 brief said U2 leaves the day function "unchanged in
what it does".

Resolution taken (U2, 15754e9). The refusal now asks that no instrument
has an expected bar of a trading day on or before `D` that has not closed
by its source's `available_until`. On a track whose instruments share one
calendar it refuses exactly the days the old check refused (the existing
tests of the day are unchanged and green); `tests/test_replay.py` shows
`run-day` taking test_mixed's Saturday at its close and refusing a day
whose SYNX bar has not closed.

Direction (for the architect). Confirm that decision 72 overrides the
brief's "unchanged" here, or name the refusal rule the day should use.

Status: open

---

### D-008 — G1.1's rank-persistence assertion cannot hold: the random slots' costs persist from block to block

Severity: high (gate M1 cannot pass as specified) · Component: DESIGN
§18.3 G1.1 with §10.1 and §11.1; decisions 59, 64 and 74 (G1.1);
`tests/gates/test_g1_1_null_controls.py::test_rank_persistence_of_the_random_slots_is_centred_on_zero`
· Found: 2026-10-13, mission 9 U7 (ae7158b).

Symptom. The one-year controls-only replay of test_synth on the gate
configuration (2019-06-03 to 2020-06-01, 50 random slots) gives, for
decision 59's statistic over blocks 1 to 51 with the random slots as the
population, 51 values that are not missing with mean 0.7066 and SE 0.0427.
Four SE is 0.171, so the assertion fails (`./scripts/gate M1 G1.1`: "1
failed, 5 passed"; output kept in meta/drafts/gate-M1-mission9.txt). The
other five G1.1 tests pass: mean summed gross -0.0092 (sd over slots 0.067),
mean summed cost 2.547 (sd 0.766), mean summed net_1x -2.556 (sd 0.769).

Cause. Measured on the same state: the same statistic on `gross` in place
of `net_1x` has mean -0.0195 and SE 0.0199, within four SE of 0. Each draw
gives each slot its own `H` (log-uniform on 1 to 48 bars) with `q = 1/H`
(DESIGN 10.1, decision 64), so a slot's turnover, hence its cost, is set
for a whole month; costs are about ten times the gross dispersion, so the
ranking of summed `net_1x` is the ranking of costs, and it persists from
one 7-day block to the next. Rank persistence of net returns across
heterogeneous random controls is not centred on zero, whatever the
implementation. With the costs made zero (the seen-to-fail change of
G1.1) the same rank-persistence test passes and only the positive-cost
test goes red, which confirms it.

Direction (for the architect). G1.1's rank-persistence clause, as decision
74 states it, cannot be met. Options: compute the statistic on the slots'
gross returns; or on net returns of slots that share one `(H, q)`; or keep
net returns and assert something else (for example that the statistic is
positive and explained by cost). The test keeps decision 74's assertion
until a decision changes it; nothing was weakened.

Status: answered — owner decision O-1 of `meta/decisions/decisions-2026-10-13-owner.md` (5acec56): G1.1's rank-persistence clause reads each random slot's summed paper `gross`; `stats.py`'s function takes the paper column as a parameter, default `net_1x`; the day loop and every production caller keep `net_1x` until step S4.1; the test reports the net statistic's mean and standard error and asserts nothing about it. Taken by mission 9 U7.

---

### D-009 — gate M1 takes about 38 minutes, beyond DESIGN 18.2's 15

Severity: medium · Component: DESIGN §18.2 with §18.3 M1 and decision 74;
the day loop's speed (`src/discotrade/daily.py` and what it calls) ·
Found: 2026-10-13, mission 9 U7 (ae7158b).

Symptom. Measured on the builder's laptop, each item's pytest process:

- G1.1 (one year, controls only, about 260 replay days): 876 s run
  directly, 869 s and 888 s through `./scripts/gate`;
- G1.2 (two replays of 2019-06-03 to 2019-08-02, recompute, a re-run):
  329 s run directly, 287 s through `./scripts/gate M1 G1.2`;
- G1.3 (2019-06-03 to 2020-06-10, about 265 days with approaches): 1069 s
  run directly, 1058 s through `./scripts/gate M1 G1.3`;
- G1.4: 1 s.

The sum is about 2275 s (38 min). `./scripts/gate M1` at ae7158b, in one
foreground call wrapped in `timeout 1185`, printed `G1.1 FAIL` after 889 s
and was terminated at 1185 s while G1.2 ran; it printed no milestone
verdict. A replay day costs about 2.4 to 3.3 s with controls only (rising
with the history) and about 4 s with two approaches journaled.

Direction (for the architect). The spans are fixed by decision 74 (G1.1's
year, G1.3's 365-calendar-day dormant limit) and were not shortened. The
gate needs either a faster day loop (the performance items) or a time limit
for M1 that the spans allow; until then `./scripts/gate M1` does not finish
within one 20-minute call, and each item has to be run on its own.

Status: answered — owner decision O-2 of `meta/decisions/decisions-2026-10-13-owner.md` (5acec56): for M1 the gate is run item by item (`./scripts/gate M1 G1.1` to `G1.4`, each its own foreground 20-minute call at one pushed commit), PASS when all four print their item PASS line; `scripts/gate` and the spans of decision 74 unchanged; §18.2's 15-minute limit waived for M1 only. Speed work is planned for the next mission (O-3). Taken by mission 9 U7.

---

### D-010 — decision 87's lifecycle keys need `ledger.py`, which no unit of mission 11 names

Severity: low · Component: `meta/BUILDER-11-PROMPT.md` U2 and U3 file lists
with decision 87 and decision 62's `ledger.KEYS` · Found: 2026-10-14,
mission 11 U2.

Symptom. `ledger.append` refuses a row whose keys are not exactly its
ledger's `KEYS` (decision 62), so a `dormant`, `returned`, `displaced` or
`admitted` row carrying decision 87's `adjusted` and `plain` cannot be
written without a change to `src/discotrade/ledger.py`. U2's files are
`lifecycle.py`, `daily.py` and tests; U3's do not name `ledger.py` either.
U3's trial keys `adjusted_t` and `adjusted_w` (decision 86 (d)) meet the
same check.

What U2 did (the simplest reading of decision 87, said in its commit body).
`ledger.py` gains `FIGURES` (`adjusted`, `plain`) and `FIGURE_REASONS`
(`admitted`, `displaced`, `dormant`, `returned`): a lifecycle row of those
reasons may hold both figures, never one alone; a row of another reason
holds neither. `KEYS` is unchanged, so rows written before (and the
admission rows U3 has not yet changed) still pass, and no earlier line is
rewritten (I-5). Whether the figures become required on those rows once U3
is in is the architect's call.

Status: open (for the architect: confirm, or name the file for U3).

2026-10-14, mission 11 U3: U3 touched `ledger.py` for the trial keys, in U2's spirit: `TRIAL_FIGURES` (`adjusted_t`, `adjusted_w`), a trial row may hold both, never one alone, `KEYS` unchanged; it also touched `cli.py` (not in U3's files either): `replay` loads the track before reading `--candidates`, so that `avg_position` is checked against the track's symbols (decision 86 (a)), and its help names `adjusted_t`.

### D-011 — gate G1.3 expects the retire reason of decision 48's in-process loader, which decision 105 (c) replaces

Severity: high (gate M1 item G1.3 goes red at mission 13's tip) · Component:
`tests/gates/test_g1_3_lifecycle.py` (its `LIFECYCLE` reasons, built at line
118) with decision 2026-10-14-m13 105 (c) and 101 (a) · Found: 2026-10-15,
mission 13 U5.

Symptom. G1.3 asserts the two `failure` retirements of 2019-06-13 with the
text the decision-21 loader wrote, `failure: position on SYNA at bar ts
2019-06-13 16:00:00+00:00 returned 2.0, outside [-1, 1]`. Decision 105 (c)
retires the approach with `failure: <the error text>`, item 101 (a)'s text,
which by 101 (a) and (f) holds no returned value and no date. At U5's commit
the G1.3 scenario's first 30 calendar days write the reasons `failure:
dry_run [out_of_range]: position returned a number outside [-1, 1] at window
bar 18 (parameter set 0)` (and bar 19 for the second approach). Every other
file of the state, the journal included, is byte-identical to the parent's
(`diff -r -x .git -x lifecycle.jsonl`), and only those two lines of
`ledger/test_synth/lifecycle.jsonl` differ. The mission's brief forbids a
change to an existing file under `tests/gates/`, so U5 left G1.3 as it is,
and gate M1 G1.3 is expected to fail at U6 on the `reason` comparison
(inferred from line 118 and the diff; G1.3 was not run by U5).

What U5 did. It follows decision 105 (c): the reason is the sandbox's text.
`tests/test_daily.py`'s contract-failure test changed its two reason
assertions accordingly (named in U5's commit body).

Direction (for the architect). Either a decision lets G1.3's expected
reasons become the sandbox's text, or one says another reason form.

Status: open
Status: decided meta/decisions/decisions-2026-10-15-owner.md (O-19)

### D-012 — G1.3 projected at about 812 s with approaches behind the sandbox, above O-3's 10 minutes

Severity: medium · Component: `src/discotrade/journal.py` and
`src/discotrade/sandbox/process.py` (decision 2026-10-14-m13 105 (a), (e))
with O-3 and decision 80 (e) · Found: 2026-10-15, mission 13 U5.

Symptom. Decision 80 (d)'s method on the G1.3 scenario's first 30 calendar
days (22 replay days, `test_synth`, gate configuration) measured: parent
10142a7 34.34 s (1.561 s a day); U5 without a fork server 55.85 s (2.539 s a
day); U5 with the fork server of 105 (e) 48.48 s (2.204 s a day). Scaled from
mission 12's G1.3 (575 s) by the ratio, G1.3 projects to about 812 s. The
rest of the cost is the fork server's start once a day (about 0.4 s:
an interpreter that imports `numpy` and `pandas`) and the jobs themselves
(about 0.1 s each, against the in-process evaluation they replace). Decision
105 (e) allows nothing else for speed.

The same cost reaches `./scripts/check`: its three runs at U5's tree took
1134 s, 1422 s and 970 s (all green; each above HF-006's 15 minutes, the
second above the 20-minute foreground cap, so the harness moved it to the
background; mission 13 U3's runs took 697 to 738 s) on the builder's four-core
machine while other projects' pytest runs held its load average near 2.5 to
3. The fourteen test files that run days took 476 s at the parent and 843 s
at U5's tree, back to back, the load rising from 2.2 to 3.9 during the
second run. A profile of the 30-day replay puts about 0.64 s a day under
that load in the fork server's start and about 0.12 s in each job.

Direction (for the architect). Whether the fork server may live for a
whole `replay` or test process (one process per replay, not per day), or the
10-minute target of G1.3 and the check time move.

Status: open
Status: decided meta/decisions/decisions-2026-10-15-owner.md (O-20)

### D-013 — a `./scripts/check` run took 910 s at mission 13 U5c, above HF-006's 15 minutes

Severity: low · Component: the test suite's run time (`./scripts/check`,
HF-006, HF-008) · Found: 2026-10-15, mission 13 U5c.

Symptom. U5c's three `./scripts/check` runs, each its own foreground call
with a 20-minute timeout, took 877 s, 910 s and 881 s, all green (2044
passed). The second is above the 15 minutes the brief and HF-006 set for a
run. U5b's runs took 858 to 881 s; U5c adds about 25 s a run (its new
`container` tests, `tests/test_sandbox_limits.py` about 23 s, of which about
11 s is `wall_wait.py`'s run under the production limits and about 4 s its
run under the short one; the probe's limit findings under a second). The
machine has four cores; its load average was near 2.0 during the runs.

Direction (for the architect). The suite sits at the 15-minute line with
nothing more added; whether the line moves, or which tests the check keeps,
before U6's gate files and later missions add to it.

Status: open

---

## hands findings

### HF-001 — after an autonomous apply, the engine sends the kickoff of the playbook it loaded before the apply

Severity: high for any role-mode series whose kits change `[series]
kickoff` · Component: playbook engine (hands `src/hands/playbook.py`,
`_engine_rules`, `on_job_start`, `_ensure_loaded`; hands DESIGN §31) ·
Found: 2026-10-11 by the phone architect, hands at commit 724e8c5.

Symptom. The engine reads `PLAYBOOK.toml` when a job starts
(`on_job_start` calls `_load`). The apply job of an architect-filed kit
starts with the old playbook; the apply commits the kit's new playbook;
the apply's `builder.done` is then decided with the playbook already in
memory (`_ensure_loaded` does not reload), and the engine's own rule sends
`book.kickoff` from it. So a kit that carries the next mission's kickoff
line, which is what the handbook's mission form does every time
(`Read meta/BUILDER-N-PROMPT.md ...`), starts the previous mission again.

Evidence. A probe test in the hands repository, modelled on
`test_end_to_end_next_kit_waits_for_the_apply_the_architect_filed`, in
which the scripted apply rewrites and commits the playbook with kickoff
`Read meta/BUILDER-18-PROMPT.md ...` before replying `VERDICT: kit applied`:

    JOB aux cli | FAKE:result VERDICT: review mission 16 blockers=1 should-fix=1
    JOB architect playbook | hands consult: aux.done on job ... (role aux)
    JOB builder architect | Apply ~/.hands/demo/kits/.../mission-17-kit.zip to this repository: unzip -o
    JOB builder playbook | Read meta/BUILDER-17-PROMPT.md and execute the mission below its divider.
    COMMITTED KICKOFF: ['kickoff = "Read meta/BUILDER-18-PROMPT.md and execute the mission below its divider. ..."']

The kickoff job's prompt is the old line while the committed playbook holds
the new one. The existing end-to-end test does not see it because its
apply changes nothing.

Direction (for the hands Project). Reload the playbook before deciding the
`builder.done` of a kit apply, or read `[series] kickoff` from the
committed file when the engine's rule fires.

What this project does meanwhile (plan, not product code): the series'
kickoff line names no mission number and never changes, and no later kit
carries `PLAYBOOK.toml` (`meta/ARCHITECT.md` §4). This sidesteps the
finding; it does not fix it.

Status: open

### HF-002 — the architect role is told to read the handbook "from the clone", and its clone is the project's

Severity: medium · Component: `architect/CLAUDE.md` rule 2 ("Read
`docs/ARCHITECT-HANDBOOK.md` from the clone before writing anything;
`templates/` are your forms") with `architect/README.md` (the clone is
`git clone <repo url> repo`, the driven project) · Found: 2026-10-11, hands
at 724e8c5.

Symptom. For any project other than hands, `./repo` has no
`docs/ARCHITECT-HANDBOOK.md` and no `templates/`, so rule 2 cannot be
followed as written, and rule 10 makes "needing more" an escalation. The
role's first consultation can end in an escalation before it writes
anything.

Evidence. `architect/README.md` and `architect/CLAUDE.md` at 724e8c5, read
side by side; this repository at 484ab80 holds only `SPEC.md` and
`.claude/`.

Direction (for the hands Project). Give the role the handbook and the
templates from the installed hands (a path in its environment, or
`hands guide`-style output), not from the project's clone.

What this project does meanwhile: the plan kit places pinned copies of
`docs/ARCHITECT-HANDBOOK.md` and `templates/` from hands 724e8c5 on the
branch, and `meta/ARCHITECT.md` carries the series' own instructions. The
copies go stale when hands changes and can be deleted once the role reads
its documents from hands.

Status: open

### HF-003 — the architect role cannot copy a file from its clone into a kit

Severity: low to medium · Component: the guard's architect mode
(`mkdir`, `cp`, `mv` only with every path under `HANDS_KITS`; hands
`docs/INTEGRATION.md`, "The architect role") with the handbook's rule
"whole files, never patches" · Found: 2026-10-11, by reading; not run.

Symptom. To change one line of a long file (a roadmap tick, the kickoff
line of a playbook) the role must reproduce the whole file through the
Write tool, from what `git show` printed. Every such re-issue is a chance
for an unnoticed change elsewhere in the file, and nothing in `hands kit
check` compares a re-issued file with its predecessor.

Direction (for the hands Project). Allow `cp` with a source inside the
clone and a target under `HANDS_KITS`, or give `hands kit` a way to stage
a repository file for editing.

What this project does meanwhile: the files the role re-issues are kept
short (`meta/ROADMAP.md`), and the long ones are never in its kits
(`meta/ARCHITECT.md` §4). The cold review does not diff re-issued plan
files; the human may want to.

Status: open

### HF-004 — the handbook says `[series]` holds two keys; the playbook reference lists seven

Severity: low · Component: `docs/ARCHITECT-HANDBOOK.md` §6 ("`[series]`
holds two keys: `name` ... and `kickoff`") against `docs/PLAYBOOK.md`
("The table's keys are `name`, `kickoff`, `architect`, `autonomous`,
`gate_failures`, `escalate_on` and `kit_wait_s`") · Found: 2026-10-11,
hands at 724e8c5.

Symptom. The handbook's §6 predates the architect role; an architect who
reads only the handbook does not learn the five role-mode keys there (they
appear in §12 by example only).

Status: open

### HF-005 — a role-mode plan kit cannot be checked where it is written

Severity: low (known and documented: hands DESIGN §33, instruction rule
13) · Component: `hands kit check`, the `playbook` check · Found:
2026-10-11.

Symptom. In the phone architect's sandbox there is no project config, so
the `playbook` check of this plan kit fails there by design, and the check
prints no apply prompt (five checks pass, `playbook` fails with "no
project config"). A phone-mode copy cannot stand in for it either: the
playbook's architect `consult` rule does not load with `architect =
"phone"`. What was run instead: the kit as shipped, with `--project`
naming a stand-in config that has `[roles.builder]`, `[roles.aux]` and a
`[roles.architect]` table, passes six of six; and a follow-on kit of the
shape `meta/ARCHITECT.md` §4 describes (a brief, the roadmap, `KIT.md`, no
playbook) passes six of six against a copy of the repository with this kit
applied. Neither is the laptop's own check against the real config, which
the human runs before sending the kit.

Status: open

### HF-006 — long foreground `./scripts/check` runs were moved to the background by the harness

Severity: low · Component: the agent harness's command runner and
`.claude/hooks/no_background.py` (CLAUDE.md "Never run a background
task") · Found: 2026-10-12, mission 3 U6.

Symptom. With mission 3's tests, `./scripts/check` takes about 2 min 50 s
(measured by the orchestrator at efb2b93). The U6 sub-agent ran it three
times in the foreground; it reports that the harness moved the runs to the
background because they ran long, and that it waited for all three to end
before committing. The hook refuses a background request the agent makes;
it does not see one the harness makes on its own when a foreground command
passes its default time limit.

Direction (for the hands Project). Either give builder sessions a default
foreground limit above the gate's run time, or have the brief tell every
sub-agent to pass an explicit timeout to `./scripts/check` (the
orchestrator's runs with a 10-minute timeout stayed in the foreground).

What this project does meanwhile: nothing in product code. The mission 4
brief may name the timeout.

Status: open

### HF-007 — the review protocol's step 2 proves nothing on a tests-only unit commit

Severity: low · Component: the review protocol of hands' templates and
this project's `meta/REVIEW-PROTOCOL.md` · Found: 2026-10-12, REVIEW-6
(`hands:` note), recorded by mission 7 U0.

Symptom. The protocol's step 2 (revert the non-test files of a unit
commit and expect red) is vacuous when a unit commit changes only tests,
as all four of mission 6's unit commits did. The reviewer's sub-agents
made the wrong changes the commit bodies name instead, a path the
protocol does not name. Separately, each review sub-agent ran
`./scripts/check` once, not three times.

Direction (for the hands Project). Name in the protocol the path for a
tests-only commit: make, in a worktree and without committing, each wrong
change the commit body names, and expect red; and say how many
`./scripts/check` runs a reviewer owes.

What this project does meanwhile: nothing in product code.

Status: open

### HF-008 — concurrent per-commit reviewers push `./scripts/check` near the tool's 20-minute cap

Severity: low · Component: the review protocol (`meta/REVIEW-PROTOCOL.md`
and hands' templates) and the agent tool's 20-minute foreground cap
(HF-006) · Found: 2026-10-14, REVIEW-10 (`hands:` note 7), recorded by
mission 11 U0 (decision 90 (d)).

Symptom. With five per-commit review sub-agents running at once on a
four-core machine, `./scripts/check` took 906 to 944 s a run, near the
20-minute cap a foreground call has, and one run had to be split.

Direction (for the hands Project). The review protocol should say
whether per-commit reviewers may run concurrently, and if so how many on
how many cores, so that a `./scripts/check` run stays well inside the
cap.

What this project does meanwhile: nothing in product code.

Status: open

### HF-009 — a sub-agent cannot be assumed to write whatever a unit asks

Severity: medium · Component: the plan and escalation model of hands
(the builder's unit dispatch, the architect role's escalation conditions)
· Found: 2026-10-14, mission 13 U4, recorded by mission 13 under
meta/decisions/decisions-2026-10-15-owner.md (O-22).

Symptom. The plan assumed a sub-agent writes whatever a unit asks. For the
texts of decision 104 a safety classifier stopped two sub-agents and the
phone architect, and no escalation condition anticipated it.

Resolved for this project by O-22 (the suite narrowed to rejection texts,
the limits proven by inspection and trusted bounded fixtures).

Status: open (for the hands Project)

D-004 status (appended 2026-10-12, mission 6 U0): Status: answered meta/decisions/decisions-2026-10-12.md (item 41)

D-005 status (appended 2026-10-12, mission 6 U0): Status: answered meta/decisions/decisions-2026-10-12.md (item 43)

D-006 status (appended 2026-10-12, mission 6 U0): Status: deferred S2.1 (meta/decisions/decisions-2026-10-12.md item 44)

D-007 status (appended 2026-10-14, mission 10 U0): Status: answered meta/decisions/decisions-2026-10-14.md (item 77)

D-010 status (appended 2026-10-14, mission 12 U0): Status: answered meta/decisions/decisions-2026-10-14-m12.md (item 93)

D-006 status (appended 2026-10-14, mission 12 U0): Status: taken by mission 12 U3 (decision 44; meta/decisions/decisions-2026-10-14-m12.md item 95)

HF-008 status (appended 2026-10-14, mission 13 U0): REVIEW-12 note 10: with `./scripts/check` near 660 s, per-commit reviewers had to run one at a time, and a reviewer's endless-loop mutant left an orphaned runner child it killed by hand. Status: open (meta/decisions/decisions-2026-10-14-m13.md item 108)

### D-014 — gate G1.3 ran above O-3's 10 minutes in REVIEW-13

Severity: low · Component: gate M1 item G1.3 (`tests/gates/test_g1_3_lifecycle.py`)
with O-3's 10-minute target, O-20 and decision 2026-10-15-m14 113 (a) · Found:
2026-10-15, REVIEW-13 (should-fix 5), recorded by mission 14 U0.

Symptom. REVIEW-13 ran `./scripts/gate M1 G1.3` at 618 s at 42cea0f's parent
and 607 s at 42cea0f, each one call with nothing else running, where mission
13's builder measured 576 s at 68bee5f. The item passes; its margin under
O-3's 10 minutes depends on the machine's load.

Direction (for the owner). O-3's target for G1.3. O-20 says the gate is run as
it is and nothing is weakened; each later mission's G1.3 time is appended here.

Status: open

### D-015 — O-22 item 1's copies under `tests/fixtures/rejected/` against decision 104 (d)'s exclusion

Severity: low · Component: `tests/fixtures/rejected/` and its manifest, with
O-22 item 1 and decision 2026-10-14-m13 104 (d) · Found: 2026-10-15, REVIEW-13
(should-fix 6), recorded by mission 14 U0 (decision 113 (b)).

Symptom. O-22 item 1 asks that a run-time entry's existing text be copied under
`tests/fixtures/rejected/` with its manifest entry pointing at the copy. A
byte-identical copy has the hash of its trusted original, so decision 104
(d)'s exclusion by hash would either accept the copy or refuse the original.
Mission 13 U4 (ad1b588) pointed the four entries at the originals under
`tests/fixtures/strategies/`, which keeps both 104 (d) and the item's purpose
(no new text where one exists).

Direction (for the owner). Confirm the manifest as built, or say another form.
Until the owner rules, the manifest stays as built.

Status: open

### D-016 — decision 128 (c)'s source test needs two lines outside the files decision 127 (a) names

Severity: low · Component: `src/discotrade/cli.py` and `src/discotrade/doctor.py`'s
module docstring, with decisions 2026-10-16-m16 127 (a) and 128 (b), (c) · Found:
2026-10-16, mission 16 U1.

Symptom. Decision 128 (c)'s test asserts that the text `NEBIUS_API_KEY` appears,
under `src/discotrade/`, only in `workers/providers.py`. At 38c98cc it also stood in
two texts that read nothing: the `--live` help string of `src/discotrade/cli.py`
(line 475, "workers (L3) needs NEBIUS_API_KEY and ...") and `doctor.py`'s module
docstring (line 31). Decision 127 (a) names `doctor.py` and `providers.py` as the
only product files the mission changes, and the U1 brief names `doctor.py`'s key
check only.

What U1 did. The simplest change that lets 128 (c)'s test pass: both texts now say
"the worker key" in place of the name. No behaviour changes; no test asserted
either text.

Direction (for the architect). Confirm the two text changes, or say another form.

Status: open

### D-017 — decision 139 (c)'s short number forms collide with the prompt's own `.4g` statistics

Severity: low · Component: `tests/gates/test_g3_3_prompts.py`, with decision
2026-10-16-m17 139 (c) and decision 117 (the prompt renders every float with
`.4g`) · Found: 2026-10-17, mission 17 U5.

Symptom. Decision 139 (c) asks G3.3 to look for every open, high, low and close of
the day's W and T bars, and every figure of an earlier trial row, "written as
`repr` and rounded to two and to four decimals, as a whole token". The fixture
instrument SYNA trades near 50 (start price 70), so its bars rounded to two decimals
cover nearly every four-digit number between about 45 and 55, and the W profile's
statistics in basis points, rendered `.4g`, fall in that range. On the replay's first
prompt (2019-07-15, call cbe1f010c3ef5) the tokens `48.25` (an hourly deviation in
bp) and `53.54` (a mean cost per unit traded in bp) are each also a SYNA price of
that W rounded to two decimals. Read literally, the test fails on a correct
implementation, by coincidence.

What U5 did. The simplest reading that keeps every form that can only be a bar's or
a score's: a form is not looked for when it is a whole number (`0.0`, `-1.0`: the
contract's text holds `[-1.0, 1.0]`) or when it is exactly what `.4g` writes for its
value (`format(float(f), '.4g') == f`). Every `repr` and every form with more digits
than `.4g` writes is still looked for, so the prices of SYNB, SYNC and SYND (near
2000 to 15000) are checked at two and four decimals, and SYNA's at four decimals and
as `repr`. The test's docstring states the reading.

Direction (for the architect). Confirm the reading, or say another (for example, a
fixture instrument whose prices cannot meet a bp statistic).

Status: open

## hands findings (continued)

### HF-010 — stale git worktrees of earlier aux sessions are left on the machine

Severity: low · Component: hands' session lifecycle (aux sessions, aborted
sessions) · Found: 2026-10-15, REVIEW-13 (`hands:` note 12), recorded by
mission 14 U0 (decision 113 (c)).

Symptom. Git worktrees of earlier aux sessions (`/tmp/rv13-8b9f9be`,
`/tmp/u5/parent`) were left on the machine; nothing in hands cleans up after
an aborted session.

Direction (for the hands Project). A cleanup of a session's worktrees when it
ends or is aborted, or a sweep at the next session's start.

What this project does meanwhile: nothing in product code.

Status: open

### HF-011 — a `journal:` commit prefix the review protocol's skip list does not name

Severity: low · Component: the review protocol's skip list (`meta/REVIEW-PROTOCOL.md`
and hands' templates) · Found: 2026-10-15, REVIEW-13 (`hands:` note 15),
recorded by mission 14 U0 (decision 113 (d)).

Symptom. The commit 8bae433, `journal: architect consult ...`, carries a
prefix the review protocol's list of commits a reviewer skips does not name.

Direction (for the hands Project). Name the `journal:` prefix in the skip list,
or have hands write its journal lines under a prefix the list names.

What this project does meanwhile: nothing in product code.

Status: open

D-013 status (appended 2026-10-15, mission 14 U0): Status: taken by mission 14 U2 (meta/decisions/decisions-2026-10-15-m14.md item 114)

D-013 times (appended 2026-10-16, mission 14 U1): U1's three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (2067 passed, `container` tests run, image discotrade-sandbox:3b7d75c39621), took 911 s, 890 s and 912 s; the first and third are above HF-006's 15 minutes. U1's new tests take about 12 s together (three probe or self-test container runs, one re-run day, the process, runner and judgement tests); no test was dropped. Status: taken by mission 14 U2 (meta/decisions/decisions-2026-10-15-m14.md item 114)

D-013 times (appended 2026-10-16, mission 14 U2): U2 shared identical setup across modules (five session state templates in `tests/conftest.py`, each module given its own copy) and within three modules, and cached `trusted_hashes` per file (decision 114). `./scripts/check` took 916 s at the parent 819f96c (one run, 2067 passed) and 841 s, 872 s and 891 s at U2 (three runs, all green, 2068 passed, `container` tests run on discotrade-sandbox:3b7d75c39621), with another project's pytest running on the four-core machine throughout (load average near 2.0). The target of 12 minutes is missed by about 120 to 170 s; no test was dropped or shortened. The twenty slowest at U2 (`--durations=20`): rejected suite setup 45.9 s; replay_candidates weekend window 28.7 s; rank_daily setup 18.5 s; container replay equals process 16.8 s; synth day-by-day fetch 15.6 s; short wall limit wait 14.6 s; cli_backtest setup 14.3 s; slow fixture call_p95 12.7 s; replay setup 11.7 s; table setup 11.0 s; sign-flipped duplicate 10.6 s; paper setup 10.4 s; correlation stage on a non-repository source 10.3 s; contract failure retires 8.7 s; validation_grid setup 8.4 s; limit error retires 8.0 s; journal equals module zscore 8.0 s; dormant compared 7.3 s; replay equals run-day test_synth 7.3 s; replay_candidates setup 7.2 s. What remains is product work each test asserts on: of a profiled 11-day replay (28.8 s), journal_day took 14.2 s (the approaches' sandbox jobs 5.0 s, backtest.score 5.3 s), step 1 8.3 s (the bar fetch 5.3 s, which rebuilds the synthetic source every day), content hashes 2.2 s; the container tests' waits on their limits are fixed by the limits they test. Direction (for the architect): the line moves, the check drops `container` tests to a gate, or product time per day is cut in a unit allowed to change it. Status: open (mission 14 U2 at its commit)

D-013 times (appended 2026-10-16, mission 14 U3): U3's three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (2110 passed, `container` tests run on discotrade-sandbox:3b7d75c39621), took 849 s, 901 s and 850 s; the second is above HF-006's 15 minutes by under 2 s (pytest 899.9 s). U3's new module `tests/test_workers_profile.py` (42 tests) takes about 12 s alone: its stores (two fetches, one template copy, two scaled stores) about 5 s, its 72 profile documents about 6 s. No test was dropped or shortened. Status: open (mission 14 U3 at its commit)

D-014 times (appended 2026-10-16, mission 14 U6): at tip a3734d9, after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present) and `./scripts/check` green three times (830 s, 785 s, 784 s), each item its own foreground call with a 20-minute timeout and nothing else of this project running: `./scripts/gate M1 G1.3` took 546 s wall (`G1.3 PASS 10 passed in 524.97s (0:08:44)`), against 576 s at mission 13 U6 and 607 s and 618 s in REVIEW-13; G1.1 385 s, G1.2 174 s, G1.4 1 s. No M1 item took above 10 minutes in this run. Status: open (for the owner, O-3's target)

HF-010 status (appended 2026-10-16, mission 15 U0): REVIEW-14 (`hands:` note 11) found `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` still registered as worktrees. Status: open (meta/decisions/decisions-2026-10-16-m15.md item 120 (a))

HF-011 status (appended 2026-10-16, mission 15 U0): REVIEW-14 (`hands:` note 12): the commit f5f43ee carries the prefix `report:`, which the review protocol's skip list does not name either. Status: open (meta/decisions/decisions-2026-10-16-m15.md item 120 (b))

### HF-012 — the review protocol does not say whether per-commit reviewers may run at once

Severity: low · Component: the review protocol (`meta/REVIEW-PROTOCOL.md` and hands'
templates) · Found: 2026-10-16, REVIEW-14 (`hands:` note 13), recorded by mission 15
U0 (decision 120 (c)).

Symptom. The review protocol dispatches one sub-agent per unit commit and does not
say whether they may run at once. With `./scripts/check` near 13 minutes on four
cores and the `container` tests' time limits, REVIEW-14 ran its five reviewers in
sequence (about 83 minutes).

Direction (for the hands Project). Say it in the protocol template.

What this project does meanwhile: nothing in product code.

Status: open

D-013 times (appended 2026-10-16, mission 15 U2): U2 keeps the synthetic source's generated series for the life of the process (decision 121; `src/discotrade/sources/synth.py`, keyed by the `[source]` table with its seed, `trusted_from`, the calendar record and the bar length; an extension lists only the expected bar times after those kept). `./scripts/check` took 791 s at the parent 624315e (one run, green) and 801 s, 798 s and 807 s at U2 (three runs, all green, 2160 passed, `container` tests run on discotrade-sandbox:3b7d75c39621), load average near 1.0; U2's new module `tests/test_synth_cache.py` takes about 7 s. The G1.3 scenario's first 30 calendar days (22 replay days, decision 80 (d)'s method) took 35.16 s (1.598 s per replay day) at the parent and 35.70 s (1.623 s) at U2, the state directories identical outside `.git/`; under cProfile the synthetic fetch fell from 1.49 s to 0.58 s of about 61 s, while `daily._fetch` (the store's verify and append) stays near 7.4 s, `journal_day` near 30 s and content hashes near 4.9 s. The synthetic source was not where the per-day time goes: a replay already built its source once. The target of 12 minutes is missed by about 80 s; no test was dropped or shortened. Status: open (mission 15 U2 at its commit)

D-013 times (appended 2026-10-16, mission 15 U7): at tip 6259365, after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built), `./scripts/check` ran three times, each its own foreground call with a 20-minute timeout, all green (`2291 passed, 182 deselected`, 0 skipped, so the `container` tests ran): 848 s, 828 s and 838 s wall (pytest 846.70 s, 826.49 s, 836.61 s). All three are above decision 114's 12 minutes and under HF-006's 15; mission 14's tip took 784 to 830 s, U2's parent 791 s, U2 801 to 807 s, U6 832 to 834 s. The mission added 139 tests to the check (2152 at mission 14's tip, 2291 here); U6's 17 generation tests are the largest addition (about 30 s, its body). No test was dropped or shortened. Status: open (mission 15 U7)

D-013 times (appended 2026-10-16, mission 16 U0): REVIEW-15 found `./scripts/check` at 794 s to 834 s at mission 15's unit commits, each run green with the `container` tests run on discotrade-sandbox:3b7d75c39621: above decision 114's 12 minutes and under HF-006's 15. No test was dropped or shortened. Status: open (meta/decisions/decisions-2026-10-16-m16.md item 131 (e), (f); decision 121 (c)'s rule)

HF-010 status (appended 2026-10-16, mission 16 U0): REVIEW-15 (`hands:` note 8) still found `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` registered as worktrees, unchanged since REVIEW-14. Status: open (meta/decisions/decisions-2026-10-16-m16.md item 131 (e))

HF-011 status (appended 2026-10-16, mission 16 U0): REVIEW-15 (`hands:` note 9): the commit d5dfa02 again carries the prefix `report:`, which the review protocol's skip list does not name. Status: open (meta/decisions/decisions-2026-10-16-m16.md item 131 (e))

HF-012 status (appended 2026-10-16, mission 16 U0): REVIEW-15 (`hands:` note 10) ran its six reviewers in sequence, about 2.5 hours in all. One reviewer ran a background test run and returned before it finished, and had to be resumed; one ran `uv sync --all-extras` (then synced back to `--extra dev` before any test); one ran `./scripts/check` twice. Direction (for the hands Project): the protocol template should say "run `./scripts/check` once, in the foreground, and report only when every command has finished". Status: open (meta/decisions/decisions-2026-10-16-m16.md item 131 (e))

D-016 status (appended 2026-10-16, mission 17 U0): Status: answered meta/decisions/decisions-2026-10-16-m17.md (item 134 (e))

HF-010 status (appended 2026-10-16, mission 17 U0): REVIEW-16 (note 10) still found `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` registered as worktrees. Status: open (meta/decisions/decisions-2026-10-16-m17.md item 134 (f))

HF-011 status (appended 2026-10-16, mission 17 U0): REVIEW-16 (note 11): the commit 6c10a3b again carries the prefix `report:`, which the review protocol's skip list does not name. Status: open (meta/decisions/decisions-2026-10-16-m17.md item 134 (f))

HF-012 status (appended 2026-10-16, mission 17 U0): REVIEW-16 (note 12) ran its three reviewers in sequence, about 51 minutes in all, each running `./scripts/check` once in the foreground, following HF-012's direction by hand. Status: open (meta/decisions/decisions-2026-10-16-m17.md item 134 (f))

D-013 times (appended 2026-10-17, mission 17 U2): after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built), U2's three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (`2341 passed, 182 deselected`, 0 skipped, so the `container` tests ran), took 867 s, 918 s and 923 s wall (pytest 866.28 s, 917.18 s, 921.75 s); the second and third are above HF-006's 15 minutes. U1's were 844 s, 838 s and 834 s. U2's new module `tests/test_daily_generation.py` (11 tests: run_day days on test_synth with the scripted provider and the child-process backend, a few days at most, decision 140) took 35 s to 36 s alone; the rest of the rise between runs was not measured per test. No test was dropped or shortened. Status: open (decision 121 (c); decision 140)
D-013 times (appended 2026-10-17, mission 17 U3): after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built), U3's three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (`2358 passed, 182 deselected`, 0 skipped, so the `container` tests ran), took 925 s, 928 s and 963 s wall (pytest 922.14 s, 924.52 s, 959.99 s); all three are above HF-006's 15 minutes. U2's were 867 s, 918 s and 923 s. U3's new module `tests/test_cli_provider.py` (17 tests: four-day replays on test_synth from init-state with the scripted provider and the child-process backend, four four-day replays (seven `replay` calls) and two `run-day` days in all, decision 140) took 49 s to 51 s alone; the rest of the rise between runs was not measured per test. No test was dropped or shortened. Status: open (decision 121 (c); decision 140)
D-013 times (appended 2026-10-17, mission 17 U4): after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built), U4's three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (`2364 passed, 182 deselected`, 0 skipped, so the `container` tests ran), took 1281 s, 1024 s and 1079 s wall (pytest 1277.04 s, 1020.29 s, 1074.97 s); all three are above HF-006's 15 minutes, and the first passed the 20-minute timeout (see the HF-006 status line). U3's were 925 s, 928 s and 963 s. U4's new module `tests/test_worker_corpus.py` (6 tests, reading files only) took under 1 s alone; during the runs the machine was shared (another project's pytest and several agent sessions; load average about 2.2 on 4 cores), and the rise was not measured per test. No test was dropped or shortened. Status: open (decision 121 (c); decision 140)
HF-006 status (appended 2026-10-17, mission 17 U4): the first of U4's three `./scripts/check` runs, a foreground call with the 1200000 ms timeout (the most the runner allows), took 1281 s; the harness moved it to the background at 1200 s, and the sub-agent waited for it to end (green) before the next run. The 20-minute timeout HF-006's direction gives no longer covers a check run on a shared machine. Status: open
D-013 times (appended 2026-10-17, mission 17 U5): after the U5 test files were written (uncommitted, on HEAD 45dc893), `./scripts/check` ran four times, each its own foreground call with a 20-minute timeout: the first went red (5 failed: `tests/test_gate_script.py`'s two "without gate tests" cases still named M3, and `tests/test_offline.py`'s listing found the word "subprocess" in the four new gate files) in 1092 s; after the fix, three runs all green (`2364 passed, 200 deselected`, 0 skipped, so the `container` tests ran on discotrade-sandbox:3b7d75c39621) took 1116 s, 1054 s and 1180 s wall (pytest 1112.62 s, 1051.03 s, 1176.70 s); all are above HF-006's 15 minutes and the last is 20 s under the 20-minute cap. U4's were 1281 s, 1024 s and 1079 s. U5 adds no test the check runs (the M3 gate tests are deselected); the machine was shared (load average 2.7 to 3.2 on 4 cores at the start). No test was dropped or shortened. Status: open (decision 121 (c); decision 140)
D-014 times (appended 2026-10-17, mission 17 U5): on HEAD 45dc893 with the U5 gate files uncommitted, after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built) and `./scripts/check` green three times, each item its own foreground call with a 20-minute timeout: `./scripts/gate M1 G1.3` took 542 s wall (`G1.3 PASS 10 passed in 541.09s (0:09:01)`), against 546 s at mission 14 U6; G1.1 450 s, G1.2 204 s, G1.4 1 s. No M1 item took above 10 minutes in this run. Gate M3 took 555 s (G3.1 218 s, G3.2 175 s, G3.3 161 s by pytest), M2 142 s, M0 247 s, all PASS. Status: open (for the owner, O-3's target)
D-013 times (appended 2026-10-17, mission 17 U6): at the tip 7f18206, after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built), three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (`2364 passed, 200 deselected`, 0 skipped, so the `container` tests ran) took 1021 s, 1043 s and 1024 s wall (pytest 1017.75 s, 1040.63 s, 1021.06 s); all three are above HF-006's 15 minutes and none passed the 20-minute timeout (no run moved to the background). U5's were 1116 s, 1054 s and 1180 s; mission 16's tip 834 to 841 s. U6 adds no test; load average about 1.5 to 1.9 on 4 cores. No test was dropped or shortened. Status: open (decision 121 (c); decision 140)
D-017 status (appended 2026-10-17, mission 18 U0): Status: answered meta/decisions/decisions-2026-10-17-m18.md (item 142)
HF-010 status (appended 2026-10-17, mission 18 U0): REVIEW-17 (note 10) still found `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` registered as worktrees. Status: open (meta/decisions/decisions-2026-10-17-m18.md item 144 (f))
HF-011 status (appended 2026-10-17, mission 18 U0): REVIEW-17 (note 11): the commit d1abd9e again carries the prefix `report:`, which the review protocol's skip list does not name. Status: open (meta/decisions/decisions-2026-10-17-m18.md item 144 (f))
HF-006 status (appended 2026-10-17, mission 18 U0): REVIEW-17 (note 12) saw one of mission 17 U4's `./scripts/check` runs pass the 20-minute tool cap, and its reviewers' own check runs take 865 s to 1048 s. Status: open (meta/decisions/decisions-2026-10-17-m18.md item 144 (f))
HF-012 status (appended 2026-10-17, mission 18 U0): REVIEW-17 (note 13) ran its five reviewers in sequence, about 1 h 50 min in all. Status: open (meta/decisions/decisions-2026-10-17-m18.md item 144 (f))
D-013 times (appended 2026-10-17, mission 18 U3): at the pushed tip e9076d5, with no uncommitted file but the git-ignored drafts, three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (`2364 passed, 204 deselected`, 0 skipped, so the `container` tests ran) took 917 s, 921 s and 926 s wall (pytest 913.81 s, 918.32 s, 923.20 s); all three are above HF-006's 15 minutes and none passed the 20-minute timeout (no run moved to the background). Mission 17 U6's were 1021 s, 1043 s and 1024 s. Then `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built) and `./scripts/gate M3` as one foreground call with a 20-minute timeout at e9076d5: 514 s wall, G3.1 PASS (3 passed in 194.96 s), G3.2 PASS (9 passed in 158.01 s), G3.3 PASS (10 passed in 159.12 s), `gate M3: PASS`; no M3 item took above 15 minutes. Load average about 0.5 to 1.2 on 4 cores. No test was dropped or shortened. Status: open (decision 121 (c); decision 140)
HF-006 status (appended 2026-10-17, mission 19 U0): REVIEW-18 (note 7) ran gate M3 in 1560 s under outside load, past the 20-minute tool cap; the harness moved the call to the background and the reviewer had to poll its output file for its end. Status: open (meta/decisions/decisions-2026-10-17-m19.md item 154 (b))
HF-012 status (appended 2026-10-17, mission 19 U0): REVIEW-18 (note 8) ran its two reviewers at the same time, which roughly halved the wall time (about 28 min for both) and slowed every check run. Status: open (meta/decisions/decisions-2026-10-17-m19.md item 154 (b))
HF-010 status (appended 2026-10-17, mission 19 U0): REVIEW-18 (note 9) still found `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` registered as worktrees. Status: open (meta/decisions/decisions-2026-10-17-m19.md item 154 (b))

### HF-013 — sub-agent reports run past the protocol's 12-line limit

Severity: low · Component: the review protocol and the builder's sub-agent brief (hands'
templates) · Found: 2026-10-17, REVIEW-18 (`hands:` note 10), recorded by mission 19 U0
(decision 154 (b)).

Symptom. The protocol asks each sub-agent to report in at most 12 lines. REVIEW-18's
sub-agents returned longer reports, which the review records as returned.

Direction (for the hands Project). Either enforce the limit where reports are collected or
state what a report must hold and drop the line count.

What this project does meanwhile: nothing in product code.

Status: open

### HF-014 — the architect role's guard refuses ordinary read-only commands

Severity: medium · Component: the architect role's command guard (hands) · Found:
2026-10-17, architect consultations 22 and 23, recorded by mission 19 U0 (decision 154 (b)).

Symptom. At consultations 22 and 23 the guard refused every command holding `#`, `{` or a
backslash anywhere, so a Markdown heading or a regex count could not be searched for. It
also refused the options `ls -R`, `git ls-tree --name-only`, `git status --short` and
`git log --date`. Reading the branch took workarounds.

Direction (for the hands Project). Let the guard admit read-only commands by what they do,
not by the characters they hold.

What this project does meanwhile: nothing in product code.

Status: open
D-013 times (appended 2026-10-18, mission 19 U6): at the pushed tip ef9359f, with no uncommitted file but the git-ignored drafts, after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built), three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (`2458 passed, 204 deselected`, 0 skipped, so the `container` tests ran) took 1066 s, 1079 s and 1131 s wall (pytest 1063.69 s, 1075.34 s, 1127.53 s); all three are above HF-006's 15 minutes and none passed the 20-minute timeout (no run moved to the background). Mission 18's were 917 s to 931 s; mission 19 added 94 tests to the check (2364 to 2458). Load average about 1.2 to 2.2 on 4 cores. No test was dropped or shortened. Status: open (decision 121 (c); decision 140)
D-014 times (appended 2026-10-18, mission 19 U6): at the pushed tip ef9359f, with no uncommitted file but the git-ignored drafts, after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built) and `./scripts/check` green three times, each item its own foreground call with a 20-minute timeout (decision 154 (d)): G1.1 411 s (`G1.1 PASS 6 passed, 1 warning in 410.20s`), G1.2 280 s (`G1.2 PASS 4 passed in 278.60s`), G1.3 1049 s (`G1.3 PASS 10 passed in 1048.60s (0:17:28)`), G1.4 1 s (`G1.4 PASS 15 passed in 0.52s`), against mission 17 U5's 450 s, 204 s, 542 s and 1 s. Finding: G1.3 took above 10 minutes (1049 s, 507 s more than mission 17 U5's 542 s), under the 20-minute call, so it is PASS under O-2 and no test was weakened (decision 154 (c)); the rise was not measured per test. Gate M3 took 547 s (G3.1 PASS 3 passed in 212.89 s, G3.2 PASS 9 passed in 165.95 s, G3.3 PASS 10 passed in 166.07 s), M2 130 s, M0 245 s, all PASS; no M3, M2 or M0 item took above 15 minutes. Status: open (for the owner, O-3's target)
D-014 status: decided meta/decisions/2026-10-18-owner.md (O-26, O-27)

### D-018 — decision 152 (a)'s alert-state entry has no `p` that decision 153 (b) 1 asks the page to read from it

Severity: low · Component: `src/discotrade/dashboard.py` (`_rank_p`) and `src/discotrade/alerts.py`
(`ENTRY_KEYS`), with decisions 2026-10-17-m19 152 (a) and 153 (b) 1 · Found: 2026-10-18,
REVIEW-19 (should-fix 1), recorded by mission 20 U0 (decision 167 (b)).

Symptom. Decision 152 (a) says the dashboard reads the rules' figures from the alert state and never
recomputes them. Decision 153 (b) 1 asks for the `rank_persistence` rule's `p` "from the alert state",
but 152 (a)'s entry has no `p` (`alerts.ENTRY_KEYS`). Mission 19 U5 resolved it in code: `_rank_p`
derives `p` on the page from the state's `value` and `threshold` and the current `alerts.rank_blocks`
and `alerts.rank_level`. That is exact while the thresholds are unchanged, and can differ from the
rule's own `p` (which is in the payload) if they change after the state was written. Two decisions
disagree, so this is a finding, not a choice made in the code.

Direction (for the architect). Say which item gives way.

Status: open
D-018 status (appended 2026-10-18, mission 20 U0): Status: answered meta/decisions/decisions-2026-10-18-m20.md (item 160)
HF-006 status (appended 2026-10-18, mission 20 U0): REVIEW-19 (note 11) saw mission 19 U1's sub-agent move a check run past the cap into a background task with a Monitor and stop waiting for a notice that never came; it was resumed twice. This project's answer is decision 2026-10-18-m20 159 (d) (a lone `sleep 240`, then a lone read of the output file, repeated). Status: open (meta/decisions/decisions-2026-10-18-m20.md item 167 (b))
HF-012 status (appended 2026-10-18, mission 20 U0): REVIEW-19 (note 12) saw outside load of about 7.6 on four cores during U1's review decide whether a check run fits the cap. Status: open (meta/decisions/decisions-2026-10-18-m20.md item 167 (b))
HF-010 status (appended 2026-10-18, mission 20 U0): REVIEW-19 (note 13) still found `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` registered as worktrees. Status: open (meta/decisions/decisions-2026-10-18-m20.md item 167 (b))
HF-013 status (appended 2026-10-18, mission 20 U0): REVIEW-19 (note 14) again recorded every sub-agent report past the 12-line limit. Status: open (meta/decisions/decisions-2026-10-18-m20.md item 167 (b))

### HF-015 — a reviewer waiting on a sub-agent has no sanctioned way to wait

Severity: medium · Component: the reviewer's harness and the project's `no_background` rule (hands) ·
Found: 2026-10-18, REVIEW-19 (`hands:` note 15), recorded by mission 20 U0 (decision 167 (b)).

Symptom. The reviewer's harness refused a `sleep` followed by other commands and pointed to Monitor
or background tasks instead. Those are the tools the project's `no_background` rule
(`.claude/hooks/no_background.py`) forbids, so a reviewer waiting on a sub-agent has no sanctioned way
to wait.

Direction (for the hands Project). Give the reviewer one sanctioned way to wait in the foreground
that the harness and the `no_background` rule both admit.

What this project does meanwhile: nothing in product code; decision 2026-10-18-m20 159 (d) gives the
builder's sub-agents a lone `sleep 240` call followed by a lone read.

Status: open
HF-015 status (appended 2026-10-18, mission 20 U1): the builder's sub-agent met the same refusal. Its harness refused a lone `sleep 240` call, decision 2026-10-18-m20 159 (d)'s wait, with "Blocked: standalone sleep 240. To wait for a condition, use Monitor with an until-loop ... To wait for a command you started, use run_in_background: true", so 159 (d) cannot be followed as written. For a `./scripts/check` run the harness moved to the background at the 20-minute cap, the sub-agent waited instead with one foreground call, `timeout 1100 bash -c 'while ! grep -q ^real <output file>; do sleep 15; done'`, then read the whole output file. Status: open

### D-019 — the table's figures over a whole paper record cannot be updated day by day and stay equal to a full recompute

Severity: low · Component: `src/discotrade/table.py` (`build`, `adjusted_deflated`) with O-26 items 2
and 5 · Found: 2026-10-18, mission 20 U1.

Symptom. Every figure of a table row is taken over all of the subject's paper days: the paper record
(Sharpe at 1x and 2x, drawdown), `adjusted_sharpe`, `avg_position`, `S`, `E_N`, `adjusted_S`,
`adjusted_E_N`, and behind the last two every random slot's adjusted series and Sharpe over the
approach's days. The paper days grow by one each day, and a new day changes `hbar_i`, so it changes
every adjusted value of the window, not only the new one. O-26 item 5 asks for the same value, not one
within a tolerance. numpy's pairwise sum, `np.mean`, `np.std` and O-4's subtraction in Python's order
cannot be carried from yesterday's partial results and give the same bits. So U1 does not make these
figures incremental. It recomputes them each day from the records, as before, but each subject's paper
and position rows are split once per build (the exposure files once per content) instead of each
random slot filtering every subject's history again. What is left grows with history as plain
arithmetic: one subtraction per slot and day, and each slot's Sharpe over the approach's days.

Measured on the G1.3 state of the full replay (`/tmp/m20u1/cw/before-last`, through 2020-06-09), warm,
one process each, one after the other: `table.build` took 0.20 s for 2019-07-03 and 0.31 s for
2020-06-09 at U1's commit, against 0.89 s and 1.58 s at the parent 4ed47b4. Under cProfile within
`./scripts/speed`'s replay: 0.355 s on 2019-07-03 and 0.593 s on 2020-05-11 at U1's commit, against
1.739 s and 2.298 s at the parent.

Direction (for the owner). Accept these figures recomputed from the records each day with the residual
growth above, or say what tolerance or change to their arithmetic would allow a day-by-day update.

Status: open
D-013 times (appended 2026-10-18, mission 20 U1): on 4ed47b4 with U1's files uncommitted, after `discotrade sandbox build` (discotrade-sandbox:3b7d75c39621, present, nothing built), three `./scripts/check` runs, each its own foreground call with a 20-minute timeout, all green (`2470 passed, 204 deselected`, 0 skipped, so the `container` tests ran) took 1168 s, 1196 s and 1317 s wall (pytest 1165.06 s, 1192.89 s, 1312.94 s). The third passed the 20-minute timeout, was moved to the background by the harness and was waited for to its end in the foreground (HF-015's status line of U1) before anything else ran; it is counted green only after it printed `check: green`. All three are above HF-006's 15 minutes. Mission 19's tip took 1066 s to 1131 s; U1 adds 12 tests (2458 to 2470), about 40 s of one run (the warm-against-cold replay and the command's three-day replay). Load average about 1.6 to 3.1 on 4 cores, from other work on the machine. An earlier run in U1, before `tests/test_speed_*.py` stopped naming subprocess, failed `tests/test_offline.py` (3 tests) after 1410 s; it was not counted. No test was dropped or shortened. Status: open (decision 121 (c); decision 140; HF-006)
