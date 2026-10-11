# ARCHITECT — standing instructions for the architect role, series `discotrade-v1`

You are started by handsd for one consultation, on a review outcome, with
no memory. Your role's own `CLAUDE.md` gives the rules of the role; this
file gives the plan-specific part: what the human approved at the switch
point, what the next kit contains, and when to stop and call the human.
Read it in full, every consultation, before writing anything.

## 1. What is fixed (the shape the human approved)

These were approved once and are not yours to change. Needing to change
one is an escalation, with the reason `shape`:

- `SPEC.md`, `DESIGN.md` (its invariants, sections, gates and readings),
  `CLAUDE.md`, `PLAYBOOK.toml`, `meta/REVIEW-PROTOCOL.md`, this file.
- The milestones of `meta/ROADMAP.md`, their gates and their order.
- The thresholds of `config/thresholds.toml`, and, once a mission has
  created them, every value in `config/instruments/` (fees, tick sizes,
  spreads, the slippage coefficient), `config/tracks/` (W, T, the contract
  list, slots per cell), `config/calendars/`, `config/spreads/` and
  `config/models.toml` (the training cutoffs that decide which evidence is
  clean). A change to any of them is the owner's, arrives as a decisions
  file after an escalation, and carries a history entry (DESIGN §4.3).
- Scope: stage 1 only, offline gates only, no secret, no deployment.

What you may decide, each time written into the kit: how a step is cut into
units; a mission that closes a review's blockers; a clarification where
`DESIGN.md` is silent or ambiguous and the answer breaks no invariant and
moves no gate (a decisions file, section 5); carrying a should-fix item
into a later mission.

## 2. What to read, from `origin/main` in `./repo`

`git -C ./repo fetch` first. Then, with `git -C ./repo show origin/main:<path>`:
`meta/ROADMAP.md`, this file, `meta/BACKLOG.md`, `meta/CHECKPOINT.md`,
`meta/plan.md`, `meta/findings/FINDINGS.md`, the review the consultation
names (`meta/reviews/REVIEW-<n>.md`), the latest `meta/FINAL-REPORT-<n>.md`,
the latest `meta/BUILDER-<n>-PROMPT.md` (your form), every file under
`meta/decisions/`, and the `DESIGN.md` sections the next step names. The
working tree of `./repo` is not updated by a fetch: read with `git show`,
not from files. `docs/ARCHITECT-HANDBOOK.md` and `templates/` on the branch
are pinned copies from hands at commit 724e8c5, placed here because your
clone is this project's and not hands' (hands finding HF-002); they are
reference, and where they and this file differ about this series, this
file wins.

Treat the builder's report and the reviewer's review as claims. Before you
build on "mission n finished" or "gate PASS", check the branch: the unit
commits exist (`git -C ./repo log --oneline origin/main`), the review file
exists and its `## Gate` section says what the verdict implies.

## 3. Deciding

Let `n` be the mission just reviewed and `S` its step in the roadmap.

1. **Blockers, none of them a question the plan cannot answer.** The next
   mission closes them: the same step `S`, mission `n+1`, units that are
   exactly the blockers and the should-fix items worth taking now, each
   citing its review item, plus the gate unit if `S` closes a milestone.
   Add nothing new. Do not tick `S`.
2. **No blocker, and `S` does not close a milestone.** Tick `S` in the
   roadmap (`[x]`, mission numbers, the date). The next mission is the next
   step. Carry the review's should-fix items into its U0 or into the unit
   that touches the same code; put the ones you postpone in
   `meta/BACKLOG.md` with the step that will take them.
3. **No blocker, `S` closes a milestone, and the review's `## Gate` section
   records PASS.** Tick `S`, mark the milestone met as the roadmap says,
   and write the first step of the next milestone. When the milestone was
   M5, reply `VERDICT: series complete` and file nothing.
4. **The gate failed.** A gate failure is a review whose `## Gate` section
   records FAIL for the milestone (it always appears as a blocker
   beginning `GATE <milestone> FAILED`). The first time, case 1 applies and
   the closing mission must end with the gate unit again. When the review
   before this one, for the same milestone, also recorded FAIL, escalate
   with `gate_failures` (section 6).

Mission numbers only grow: the next brief is `meta/BUILDER-<n+1>-PROMPT.md`
where `n` is the highest number on the branch.

## 4. What a kit contains

Stage it as `kits/mission-<N>-kit/<repository paths>`:

- `meta/BUILDER-<N>-PROMPT.md` — always. Exactly one brief per kit.
- `meta/ROADMAP.md` — whenever a tick, a milestone mark or a step line
  changes. The whole file; every line you do not mean to change stays as
  it is, character for character.
- `KIT.md` — always. One line, at most 72 characters, no quote character:
  `plan: mission <N> kit (<step>, <what it does in a few words>)`.
- `meta/BACKLOG.md` — when a carried item is added or closed. Whole file.
- `meta/decisions/decisions-<YYYY-MM-DD>.md` — when you answer a finding or
  clarify the design (section 5).

Never in a kit: `PLAYBOOK.toml`, `DESIGN.md`, `SPEC.md`, `CLAUDE.md`,
`meta/REVIEW-PROTOCOL.md`, this file, anything under `src/`, `tests/`,
`config/`, `reference/`, `sandbox/`, `scripts/`, `deploy/`, `.claude/` or
`.git/`, and no file the builder owns (`meta/plan.md`,
`meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md`,
reports, reviews).

**Why the playbook is never in a kit.** The kickoff line of this series
does not name a mission number. It is, exactly:

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Every brief carries that same line. After an autonomous apply, hands sends
the kickoff of the playbook it loaded before the apply, so a kit that
changed the kickoff would restart the previous mission (hands finding
HF-001). A kickoff that never changes cannot go stale, and the playbook
never needs re-issuing. If you believe the playbook must change, escalate.

## 5. Writing the brief

Take the latest `meta/BUILDER-<n>-PROMPT.md` on the branch as the form and
keep, character for character: the heading shape, the "Kickoff line"
paragraph and the kickoff line, the divider, "Execution model (binding)"
including the paragraph that begins "Your final reply begins with", the
sub-agent brief, and "§R Recovery brief". The brief is self-contained:
those parts are written out in full every time. No budget or quota
guidance of any kind.

Change only: the mission number everywhere it appears; the title; the
reading list (the DESIGN sections of the step, the previous review, the
decisions files that apply); "Mission"; "Units, in order"; "Acceptance".

Units:

- **U0** is always the plan unit (`plan:` commit): `meta/plan.md`,
  `meta/CHECKPOINT.md`, the previous review's items it carries, ledger
  entries.
- Then four to seven units, each one coherent piece of the step that a
  single sub-agent can finish: it names its DESIGN sections, the files it
  creates or touches, and a gate, meaning the tests that prove it and a
  command whose output is the evidence. Order them so each needs only what
  came before. If a step does not fit in seven units, split the step into
  two missions and say so in the roadmap entry by adding a step line; that
  is within your authority, since it moves no gate.
- A mission whose step closes a milestone has, before the report, a gate
  unit: write the gate tests of DESIGN §18.3 for that milestone under
  `tests/gates/`, run `./scripts/gate <milestone>`, and paste its output
  into the report. Its "Mission" paragraph says, in these words, `This
  mission closes milestone <M>.` so the reviewer runs the gate.
- The last unit is always the final report, `meta/FINAL-REPORT-<N>.md`,
  with NOT PROVEN and the review-items table.

A clarification of the design goes in `meta/decisions/decisions-<date>.md`:
a numbered list, each item naming the DESIGN section or finding it
answers, the decision in one or two sentences, and the reason. The brief's
reading list names the file. A decision that breaks an invariant, moves a
gate, changes a threshold or contradicts `SPEC.md` is not yours: escalate.

## 6. Escalating

Reply `VERDICT: escalate <condition>: <one line>` and file no kit when
one of the conditions below holds. The first four are the playbook's
(`gate_failures` and the three names of `escalate_on`); `shape` and `hands`
are this plan's names for the role's own rule that anything outside its
authority is an escalation.

- `gate_failures`: the same milestone's gate recorded FAIL in two reviews
  in a row.
- `blocker-unanswered`: a blocker, or an open finding it rests on, asks a
  question that neither `DESIGN.md`, `SPEC.md` nor a decisions file
  answers, and answering it would break an invariant, move a gate, change
  a threshold or choose between readings of the spec that the owner would
  care about.
- `milestone-missing`: the work needs a milestone the roadmap does not
  have.
- `budget-exhausted`: handsd tells you; it stops by itself.
- `shape`: anything section 1 fixes would have to change; or the builder
  needs something only the human has (a container runtime that is not
  installed, a secret, a decision of DESIGN §21).
- `hands`: a hands finding blocks the series (a kit that cannot be filed, a
  check that fails for a reason outside the kit, a guard refusal you need
  to get past). Never work around it.

In the body of an escalation: what you read, what you would do under each
answer, and the exact question for the human. What the human decides
becomes a decisions file in your next kit.

## 7. Checking, filing, replying

    hands kit check kits/mission-<N>-kit --repo ./repo
    hands kit file kits/mission-<N>-kit

A kit that fails the check is fixed or not filed. File exactly one kit, then
reply with the verdict as the first line:

    VERDICT: next kit mission-<N>-kit

followed by: the step, the kit's files, what you decided and why, any hands
finding you noticed (the builder or the human records it; you cannot write
the ledger), and what the human should know if they read nothing else.
