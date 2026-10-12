# BUILDER-6-PROMPT — discotrade mission 6: REVIEW-5's blocker and should-fix item, and the M0 gate again (closes M0)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 6. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-6.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 6 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ; items 41 to 46 are new for this mission and every unit below
cites them; items 1 to 40 still bind, and items 22 to 26, 29, 30, 36, 37
and 39 are what the independent calculation is written from), `DESIGN.md`
(§18.2 and §18.3 M0 are this mission; §5.6, §7 and §8 for the roll cost,
the half spread and the metrics; §3 for `backtest`; §18.1; read §2
twice), `meta/reviews/REVIEW-5.md` (its `## Blockers`, `## Should-fix`
and `## Notes`), `meta/FINAL-REPORT-5.md`, `meta/findings/FINDINGS.md`,
and `meta/CHECKPOINT.md` (a unit in progress means §R first). This is
roadmap step S0.4, repaired.

---

## Mission

Close REVIEW-5's blocker and its should-fix item for step S0.4, and run
the M0 gate again. This mission closes milestone M0. Make the G0.1 test
of the `backtest --json` output compare every field the object carries
(decision 42); make the timing of the roll cost visible to the
independent calculation's self-test, to the product's unit tests and to
G0.1 (decision 43); keep `tests/test_gate_script.py` from turning
`./scripts/check` red under load (decision 45); record findings D-004 to
D-006 as answered (decisions 41, 43, 44); then run `./scripts/gate M0`
at the tip until it prints `gate M0: PASS`. Add nothing else. A gate
test asserts what DESIGN §18.3 and the cited decisions say, no less; no
gate test is made to pass by a special case in product code. Where a
cited decision changes what an existing test asserts, the unit changes
that assertion and says so in its commit body; every other existing test
stays unchanged in what it asserts. Finish with a report whose first
line the playbook can match.

## Execution model (binding)

- You are a thin orchestrator. You plan units, write the checkpoint,
  dispatch ONE sub-agent per unit (Task tool, foreground only), verify the
  unit cheaply, record one line, move on. You run nothing longer than `git
  status`, `git log --oneline -5`, and `./scripts/check` yourself.
- Before each unit: write `meta/CHECKPOINT.md` (unit id, intent, what
  "done" means, standing constraints). After each unit: update it and
  append one line to `meta/journal.md`.
- Every unit ends with a commit AND a push. A unit commit carries only its
  own files and its body lists every one; never `git add -A`. The U0 commit
  uses the `plan:` prefix. Drafts of the final report live under
  `meta/drafts/` (git-ignored) until the last unit.
- Retry a failed unit once with the sub-agent's report attached; after two
  failures mark it `blocked` in `meta/plan.md` and continue with units that
  do not depend on it.
- Never edit product code yourself. Never edit `DESIGN.md` or any other
  file `CLAUDE.md` lists as not a builder's (file a finding instead).
- `./scripts/check` three times before every commit, once it exists (U1
  creates it; U0 has nothing to check).
- Your final reply begins with exactly one of: `VERDICT: mission 6
  finished` | `VERDICT: mission 6 blocked <unit>` | `VERDICT: question <one
  line>`.

## Sub-agent brief (give this to every unit sub-agent, verbatim, plus the unit)

    You are implementing one unit of discotrade. Read, in this order:
    CLAUDE.md, the DESIGN.md sections named by the unit and DESIGN.md §2,
    meta/CHECKPOINT.md, the review or report item named by the unit if any,
    then only the files the unit touches. Rules: the design is the spec;
    where it is silent, choose the simplest thing and say so in the commit
    body; write the failing test before the code and confirm it fails;
    tests use no network, no secret, no real model, no wall clock and a
    fixed seed for every random draw; ./scripts/check green three times in
    a row before you commit; one commit, `<area>: <one line>` plus a body
    naming the unit and the DESIGN sections, listing every file, and
    stating only what the tests prove (never a totality claim unless a test
    enumerates the whole space); never `git add -A`; push; never edit
    meta/plan.md, meta/CHECKPOINT.md, DESIGN.md, SPEC.md, PLAYBOOK.toml or
    any file CLAUDE.md lists as not a builder's; add no dependency beyond
    the ones CLAUDE.md names; if the unit needs a design change, stop and
    write a finding to meta/findings/FINDINGS.md instead of improvising (a
    problem with hands itself goes under its "hands findings" heading);
    every number taken from outside the project goes into config with
    checked, source and verified, and is reported as not proven when it
    did not come from a primary source; dispatch nothing in the background
    and run long commands in the foreground with a timeout; report in at
    most 12 lines: sha, files, tests added, what is NOT proven.

## §R Recovery brief

If `meta/CHECKPOINT.md` names a unit in progress and the working tree is
dirty: finish that unit under the sub-agent rules if it can pass
`./scripts/check`; otherwise `git stash push -m "wip <unit> <date>"`,
record in the checkpoint where it stopped and that a stash exists, and
leave the tree clean. Then continue from that unit. Push before taking any
new unit.

## Units, in order

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-12.md`
(the items the unit names) and the REVIEW-5 items the unit names. No unit
changes a value in a frozen file (`config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit changes an existing record under
`tests/fixtures/config/` (the gate fixtures' bars must stay as they are).
Where a unit's code already exists and is right, so that a new test
cannot be seen to fail first against the parent, the sub-agent instead
makes, in its worktree and without committing it, the wrong change the
test is meant to catch, sees the test fail, reverts it, and names that
change in the commit body. `./scripts/check` and `./scripts/gate` are run
in the foreground with an explicit timeout of at least 20 minutes
(finding HF-006), and each sub-agent runs `./scripts/check` three times
before its commit and says in its report how many runs were green.

Every test under `tests/gates/` follows DESIGN §18.1, §18.2 and decisions
9 and 40: it carries the markers `gate` and `gate_m0`; it lives in a file
named `tests/gates/test_g0_<n>_<what>.py` for the item `G0.<n>` it
proves; every seed it uses is written in the test file; it writes state
only under a pytest temporary directory; it runs the `discotrade` command
in-process, through the function the console script calls, and launches
no subprocess; it never skips; and each item finishes within 15 minutes
on a laptop. Where a test of this mission finds product code that does
not do what DESIGN and the decisions say, the unit fixes the product
code with a unit test outside `tests/gates/` seen to fail first, in the
same commit, and the body names the defect, the bar or input, both
values and the DESIGN sentence.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S0.4, `This mission closes
milestone M0.`, and as carried items REVIEW-5 blocker 1, REVIEW-5
should-fix 1 with finding D-005, REVIEW-5's note on D-004 (decision 41)
and REVIEW-5's note on the timeout of `tests/test_gate_script.py`, each
with the unit that takes it), rewrite `meta/CHECKPOINT.md` for this
mission, append to `meta/journal.md`, and append to
`meta/findings/FINDINGS.md` these three status lines, verbatim:
"D-004 status (appended 2026-10-12, mission 6 U0): Status: answered
meta/decisions/decisions-2026-10-12.md (item 41)", "D-005 status
(appended 2026-10-12, mission 6 U0): Status: answered
meta/decisions/decisions-2026-10-12.md (item 43)" and "D-006 status
(appended 2026-10-12, mission 6 U0): Status: deferred S2.1
(meta/decisions/decisions-2026-10-12.md item 44)". Nothing else. Gate:
the four files are committed and pushed in one `plan:` commit.

**U1 G0.1: every field of `backtest --json` (REVIEW-5 blocker 1;
decisions 27, 39, 42; DESIGN §3, §8, §18.2, §18.3 G0.1).**
`tests/gates/test_g0_1_reference.py`, and `src/discotrade/cli.py` only
under the product-defect rule above. The sub-agent may read product
code; it does not edit `tests/gates/independent_calc.py`. Gate: for each
of the three reference strategies, `test_backtest_json_equals_the_module`
(or the tests that replace it, in the same file) compares every key of
the `--json` object as decision 42 lists: the metrics with `days`, the
subject's cost totals, the descriptive keys, and every key of each
instrument's map (`bars`, `trades`, `position_min`, `position_max`,
`fee`, `spread`, `slippage`, `roll`, `cost`, `net_1x`, `net_2x`), each
computed in the test from the module's per-bar rows and, where decision
42 says, from the independent calculation's rows too; and it asserts
that the keys of the object and of each per-instrument map are exactly
the keys it compares. Seen to fail, each made and reverted in the
worktree and named in the commit body: `position_max` taking the min,
`net_1x` set to 999.0, `trades` set to -1 (REVIEW-5's three changes in
`cli.py`), `position_min` from `h` only, and a new key added to each
per-instrument map. `./scripts/gate M0 G0.1` passes. The existing
assertions of the file stay; this unit only adds to them.

**U2 The independent calculation's self-test: a position that changes at
the roll (REVIEW-5 should-fix 1; finding D-005; decisions 24, 25, 39, 43
(a); DESIGN §5.6, §7.3).** `tests/gates/test_g0_1_calc_self.py`, and
`tests/gates/independent_calc.py` only if a new hand case shows it
wrong. This unit's sub-agent is a sub-agent of its own, dispatched for
this unit only. Give it the sub-agent brief and, with it, these words
verbatim: "You extend the self-test of a calculation that checks
discotrade's evaluation loop, cost model, roll handling and metrics, so
you must not know how they are written. Do not open, read, grep, diff or
`git log -p` any file under `src/discotrade/`, nor
`tests/test_backtest.py`, `tests/test_costs.py`, `tests/test_rolls.py`,
`tests/test_metrics.py`, `tests/test_executor.py`,
`tests/test_reference.py`, `tests/test_cli_backtest.py` or
`tests/gates/test_g0_1_reference.py`, nor any commit body or report that
describes their code (`meta/FINAL-REPORT-*.md`, `meta/reviews/`). Work
from DESIGN.md §5.6, §7 and §8 and from items 22 to 26, 29, 30, 36, 37,
39, 41 and 43 of meta/decisions/decisions-2026-10-12.md alone, and from
`tests/gates/independent_calc.py` and its self-test. Import nothing from
discotrade. State in your commit body that you opened none of those
files." Gate: the self-test gains hand cases, with their derivation in
comments, on a constructed store as the existing cases build theirs: a
roll at which a carried position changes size or sign (for example
`h(u-1) = 1` and `h(u) = -0.5`), and a roll at which a flat position
opens (`h(u-1) = 0`, `h(u) != 0`), each checking the roll cost, the
row's `cost`, `net_1x` and `net_2x`, and `breakeven_cost` with its
rolled turnover. Seen to fail, each made and reverted and named in the
commit body: the calculation's roll cost on `h(u)` instead of `h(u-1)`
(REVIEW-5 names `independent_calc.py:341`), and its rolled turnover on
`h(u)` (`:351`). If a new hand case shows the calculation wrong, the fix
is in this commit and the body names the case, the field, both values
and the DESIGN sentence. Every existing self-test case stays unchanged
in what it asserts. `./scripts/gate M0 G0.1` passes.

**U3 The roll timing in product unit tests and in G0.1 (finding D-005;
decisions 21, 24, 25, 39, 43 (b), (c); DESIGN §5.6, §7.3, §8, §18.3
G0.1).** `tests/test_executor.py` and, for `breakeven_cost`,
`tests/test_metrics.py` or `tests/test_backtest.py`;
`tests/fixtures/strategies/roll_probe.py`;
`tests/gates/test_g0_1_reference.py`. The sub-agent may read product
code; it does not edit `tests/gates/independent_calc.py` or its
self-test. Gate: a unit test in which the position changes at a roll bar
(carried and changing, and flat then opening) asserts the roll cost `2 *
|h(u-1)| * c(u)` and the rolled turnover `2 * |h(u-1)|` in
`breakeven_cost`; `roll_probe.py` is a strategy text that passes
discotrade's loader and whose position changes at the SYNA roll bar of
the G0.1 window (how is the sub-agent's choice, from the bars the slice
holds; it names no market); and G0.1 compares it with the independent
calculation, through the module API, on the same window and fields as
the reference strategies (every per-bar field, both daily series, every
metric of §8, the cost totals by component, under decision 39), and
asserts that `h(u-1) != h(u)` at the SYNA roll bar in the window. Seen
to fail, each made and reverted and named in the commit body: discotrade's
roll cost on `h(u)` instead of `h(u-1)` fails both the unit test and the
probe's G0.1 comparison, and its rolled turnover on `h(u)` fails both
too. **Mismatch rule.** A difference between discotrade and the
calculation on the probe is settled by DESIGN and the decisions alone. If
discotrade is wrong, U3 fixes the product code under the product-defect
rule above. If the calculation is wrong, U3 stops and reports it; you
dispatch a fresh sub-agent under U2's rules and words, with the mismatch
(the bar, the field, both values, the DESIGN sentence) and nothing about
the product code, which fixes `independent_calc.py` and its self-test in
a commit of its own before U3 resumes. If DESIGN and the decisions do not
settle it, write a finding and reply `VERDICT: question` naming it.
`./scripts/gate M0 G0.1` passes.

**U4 `tests/test_gate_script.py` under load (REVIEW-5 note; decision 45;
DESIGN §18.2).** `tests/test_gate_script.py` only. Gate: every test of
the file asserts what it asserts at the base; each that runs
`./scripts/gate` as a subprocess runs an item or milestone whose run
takes seconds (for example G0.4, or a milestone with no gate test),
never one that fetches or replays for minutes, and keeps no subprocess
timeout below 1200 seconds; the commit body lists, per test, the item it
ran before and after, and the file's run time before and after on the
same machine. Seen to fail: with the script made to print `PASS` for a
failing item (made and reverted), the file still goes red.

**U5 The gate run (DESIGN §18.2, §18.3 M0).** No product or test file.
After `./scripts/check` is green three times at the tip: run
`./scripts/gate M0` at the pushed tip; it prints `G0.1` to `G0.4 PASS`
and `gate M0: PASS` with each item under 15 minutes. Paste its output
verbatim into the report draft and record it in `meta/journal.md` and
`meta/CHECKPOINT.md` in a `meta:` commit naming the tip sha. When an
item fails, the unit that wrote its test is retried once with the output
(U2 under its own rules); a gate test is never loosened to pass.

**U6 Final report.** `meta/FINAL-REPORT-6.md` (drafted under
`meta/drafts/`, moved in by this commit): what changed (sha per unit,
and per fix commit if any), a `## Gate` section with the `./scripts/gate
M0` output at the pushed tip pasted verbatim and, for each item G0.1 to
G0.4, the test file that proves it and what it asserts against DESIGN
§18.3's words; a correction of FINAL-REPORT-5, stating that its claim
that "the `--json` figures equal the module's" was not held by its test
at bf943a4 and is held from U1's sha on; every mismatch found and how it
was settled; what the tests prove; NOT PROVEN (mandatory: what remains
of FINAL-REPORT-5's NOT PROVEN, updated; that the half-tick floor is
proven by unit tests on each side and not through G0.1, whose fixture
spreads are all at least one tick (decision 43); that the roll timing is
shown through G0.1 by a test-only probe on one roll bar of one window;
that the calculation's independence for U2 rests on its sub-agent's
statement; D-006 deferred to S2.1 (decision 44)); the findings filed and
answered; and a `## Review items` table with one row each for REVIEW-5
blocker 1, REVIEW-5 should-fix 1, REVIEW-5's note on D-004 and its note
on `tests/test_gate_script.py`: the item, its resolution (the unit and
decisions item), and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M0` at the pushed tip prints `G0.1` to `G0.4 PASS` and
  `gate M0: PASS`, exits 0, and each item finishes within 15 minutes.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- U1's test compares every key of the `--json` object and of each
  per-instrument map, and fails on each of REVIEW-5's three wrong changes
  and on an added key.
- U2's commit body states that its sub-agent opened none of the files its
  words forbid; the self-test fails with the calculation's roll cost or
  rolled turnover on `h(u)`; `tests/gates/independent_calc.py` imports
  nothing from `discotrade`.
- U3's unit test and the probe's G0.1 comparison each fail with
  discotrade's roll cost or rolled turnover on `h(u)`, and the probe's
  position changes at the SYNA roll bar of the window.
- No value of a frozen file changed in this mission (`git diff` of
  `config/`, of the existing entries of `tests/fixtures/config_frozen.json`
  and of the existing records under `tests/fixtures/config/` against the
  base is empty).
- No test uses the network, a secret or the wall clock; no gate test
  launches a subprocess; no file under `src/` names a market, a contract
  root or a venue.
- `meta/FINAL-REPORT-6.md` exists with the `## Gate` section, the
  correction of FINAL-REPORT-5, NOT PROVEN, and the review-items table
  covering REVIEW-5 blocker 1, should-fix 1, the D-004 note and the
  `tests/test_gate_script.py` note.
