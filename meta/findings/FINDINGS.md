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

D-004 status (appended 2026-10-12, mission 6 U0): Status: answered meta/decisions/decisions-2026-10-12.md (item 41)

D-005 status (appended 2026-10-12, mission 6 U0): Status: answered meta/decisions/decisions-2026-10-12.md (item 43)

D-006 status (appended 2026-10-12, mission 6 U0): Status: deferred S2.1 (meta/decisions/decisions-2026-10-12.md item 44)

D-007 status (appended 2026-10-14, mission 10 U0): Status: answered meta/decisions/decisions-2026-10-14.md (item 77)
