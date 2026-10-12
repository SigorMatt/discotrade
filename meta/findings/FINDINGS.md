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
