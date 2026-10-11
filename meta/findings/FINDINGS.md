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

(none yet)

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
