# BUILDER-21-PROMPT — discotrade mission 21: REVIEW-20's blocker and should-fix items, persistent_approach's p(N) from the alert state (step S4.2a)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 21. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-21.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 21 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-19-m21.md` (items 168 to 176, new for
this mission; every unit below cites them),
`meta/decisions/2026-10-18-owner.md` (the owner's; O-26 and O-27, the speed
measurement and the 15-minute stop),
`meta/decisions/decisions-2026-10-18-m20.md` (items 155 to 167; 155, 156,
157 (c), 160, 163, 164 and 166 in particular),
`meta/decisions/2026-10-17-owner.md` (the owner's; O-25, add never
replace), `meta/decisions/decisions-2026-10-17-m19.md` (items 146 to 154;
146 (b), (c), 151 (a), 152 (a) and 153 in particular),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-18 the
register), `meta/decisions/decisions-2026-10-17-m18.md` (item 145, the
check's time), `meta/decisions/decisions-2026-10-16-m17.md` (items 137 and
140), `meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still bind;
72 the gate configuration), `DESIGN.md` (§15.1, §15.3 and §15.5 for the
rule, the alert state and the dashboard, §11.4 for the tightened
percentile, §14.2 and §14.4 for the coordinator and the fix sessions, §5.4
for the gap check, §18.2 for the gate configuration; read §2 twice, in
particular I-6, I-8, I-11, I-12 and I-13), `SPEC.md` §13 (the dashboard
reads the state files the alert rules read), `meta/reviews/REVIEW-20.md`
(its `## Blockers`, `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-20.md`, `meta/findings/FINDINGS.md`, `meta/BACKLOG.md`,
and `meta/CHECKPOINT.md` (a unit in progress means §R first). This is
roadmap step S4.2a, mission 21, which closes REVIEW-20's items.

---

## Mission

Close REVIEW-20's blocker and its four should-fix items as decisions 168 to
176 say, and nothing else. Concretely:
- the alert state's `persistent_approach` entries hold the `N` and the
  `p(N)` the rule used on `D`, and the dashboard shows them from the
  state; the page recomputes no rule's figure (finding D-022, decision
  169);
- the ratio of `./scripts/speed` that binds a unit is the median of three
  complete measurements (decision 170);
- the unknown-coordinator test names unknown coordinators, and no test
  depends on a secret in the environment (decision 171);
- a fix session is offered file tools only and its settings deny `Bash`,
  `WebFetch` and `WebSearch`; the protected paths gain REVIEW-20 note 5's
  entries (decision 172);
- a test pins `gaps._MONTH_MISSING`'s content identity (decision 173).

The unit that changes the day loop (U1) gives `./scripts/gate M1 G1.3`'s
time and the measurement at its commit (O-27 item 2, decision 170). An M1
item above 15 minutes stops the mission (O-27 item 3). Then run gate M1
again item by item, and gates M3, M2 and M0, at the pushed tip (O-25,
decision 168 (a)). Each must pass unchanged. No file under `tests/gates/`
changes. A test of a met gate that fails because of what this mission adds
is not edited: the unit stops, files a finding, and you reply `VERDICT:
question` with it (decision 168 (b)). This mission closes no milestone.
The digest, the issue sinks and the full daily run are step S4.2b's, and
the M4 gate tests are step S4.3's. Finish with a report whose first line
the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 21
  finished` | `VERDICT: mission 21 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-19-m21.md`
and the items of the earlier decisions files and of the owner's files that
the unit names.

What no unit changes:
- any file under `tests/gates/`;
- any file under `tests/fixtures/rejected/`;
- any record under `tests/fixtures/config/`;
- any entry of `tests/fixtures/config_frozen.json`;
- any value of a frozen configuration file (`config/thresholds.toml`,
  `config/instruments/`, `config/tracks/`, `config/calendars/`,
  `config/spreads/`, `config/models.toml`).

The one file under `config/` that changes is `config/protected_paths.toml`
(U3, decision 172 (b)), which is not frozen. Every existing test stays
unchanged in what it asserts, except where a decisions item orders the
change. Each such test is named in the body with that item, and nothing it
asserted before is loosened (decision 146 (c)). If a test of a met gate (M0
to M3) fails because of what a unit adds, the unit does not edit it. It
stops, writes a finding naming the test, the assertion and the change, and
you reply `VERDICT: question` with it (decision 168 (b)).

Every function this mission adds or changes that holds one of the audit's
reference shapes (`tests/test_return_readers.py`) is registered in
`tests/fixtures/return_readers.toml` in the same commit, with its class and
a one-line note, and the audit passes. The commit body names each new or
changed entry (O-18).

Wrong changes. Where a new test passes against the parent because the code
it checks is right, the sub-agent instead makes, in its worktree and
without committing it, the wrong change the test is meant to catch, sees
the test fail, reverts it, and names that change in the commit body. Each
unit names below the wrong changes its tests must be seen to fail on. These
are made one at a time, reverted the same way, and named in the body with
the test that went red. A commit body says "seen to fail" only of a test
that was seen to fail, and says a test proves something only when that test
asserts it. A claim that a later unit or a gate will prove something names
the test that does, or is not made (decision 144 (e)).

Long commands (finding HF-006; decision 176):
- Every run of `./scripts/check`, `./scripts/gate` or `./scripts/speed` is
  its own foreground Bash call with an explicit timeout of 20 minutes, the
  tool's maximum. Never chain two such runs in one call, and never let one
  run in the background.
- Each sub-agent runs `./scripts/check` three times before its commit, as
  three calls, and says in its report how many runs were green, with the
  wall time of one run. `./scripts/check` took 982 to 990 s at mission
  20's tip on the builder's machine, with the `container` tests run.
- A run that passes the 20-minute cap and is moved to the background by the
  harness is waited for to its end before the next run, as decision 176
  says: one foreground call, with a timeout of at most 20 minutes, that
  polls the run's output file until its last line is there, then one read
  of the whole file, repeated until the run has ended. Never a Monitor,
  never a background task to wait, and never a report before the run has
  ended. It is recorded as decision 145 says, never dropped, shortened or
  counted green before it ends.
- Every sub-agent first runs `discotrade sandbox build`, as its own
  foreground call with a 20-minute timeout, so that the `container` tests
  of the check run and do not skip, and says in its report that they ran
  and the tag.
- The measurement (decision 170): three complete `./scripts/speed --work
  <dir>` replays, each with its own new directory outside the repository,
  one after another, with nothing else of the three commands above running
  meanwhile. For each: its four figures, its process starts, and the load
  average at its start and its end; then the median ratio. A median above
  1.25 fails the unit (O-26 item 4): it is retried once, then marked
  blocked, never passed. G1.3 above 15 minutes of wall time stops the
  mission: the unit files a finding (the next free `D-###`) with the times
  and the measurement, weakens nothing, and you reply `VERDICT: question`
  naming it (O-27 item 3).

How tests are written:
- Every test of this mission writes state and job directories only under a
  pytest temporary directory.
- It reads time only through `--as-of` or the replay's clock (decision 72).
- It runs the `discotrade` command in-process, through the function the
  console script calls.
- A test that runs `git` passes `GIT_ALLOW_PROTOCOL=file` in its
  environment and uses local paths only (decision 47).
- A test that checks a figure computes the expected value itself, without
  calling the function under test.
- A test that needs `claude` uses a fake executable the test writes under
  its temporary directory, named by `[coordinator] binary` or the worker's
  setting. No test opens a socket, or calls a real provider, a real model
  or a real `claude` binary (I-11).
- No test builds the image.

**U0 Plan (`plan:` commit).** In one `plan:` commit:
- Write `meta/plan.md`: these units with checkboxes, the base commit, the
  roadmap step S4.2a (mission 21 closes REVIEW-20's items), the statement
  that this mission closes no milestone, and the regression gates of
  decision 168 (a) (M1 item by item, then M3, M2 and M0, at the pushed tip,
  U5) under O-27's 15-minute stop.
- Name in it, as carried items, each with the unit that takes it:
  - REVIEW-20 blocker 1, finding D-022 (decision 169, U1);
  - REVIEW-20 should-fix 1 (decision 170, U1 and U5);
  - REVIEW-20 should-fix 2 (decision 171, U2);
  - REVIEW-20 should-fix 3 and note 5 (decision 172, U3);
  - REVIEW-20 should-fix 4 (decision 173, U4);
  - REVIEW-20 note 6 (decisions 169 (e), U1, and 170 (d), stands);
  - REVIEW-20 notes 1 and 8 to 10 (decision 175 (b), U0);
  - the corrections of `meta/FINAL-REPORT-20.md` (decision 174, U6).
- Name in it, as left items, each with the step or the owner that takes
  it: findings D-019, D-020 and D-021 (the owner, `meta/BACKLOG.md`); the
  digest, the issue sinks, the full daily run, the `no_finding` call, the
  live defaults of `run-day`, REVIEW-17 notes 3 to 5 and REVIEW-19 notes 4
  and 6 (step S4.2b); G4.4 and G4.5 as gate tests (step S4.3).
- Rewrite `meta/CHECKPOINT.md` for this mission and append to
  `meta/journal.md`.
- Append to `meta/findings/FINDINGS.md`, after its last line and in its
  form, the lines of decision 175 (b): finding D-022 and its status line,
  the HF-015, HF-012 and HF-010 lines, and the D-013 times line.

Nothing else. Gate: the four files are committed and pushed in one `plan:`
commit.

**U1 `persistent_approach`'s `N` and `p(N)` from the alert state (REVIEW-20
blocker 1, finding D-022; decisions 169, 170; DESIGN §15.1, §15.3, §15.5,
§11.4; I-6, I-12).**

Files:
- `src/discotrade/alerts.py` (the `persistent_approach` entry's `N` and
  `p_N`, their module constant, `transition` carrying them; `RANK_P` in
  place of the literal `"p"`);
- `src/discotrade/dashboard.py` (`N` and `p(N)` read from each entry; the
  computing line and the `stats.tightened_percentile` call removed; any
  other recomputation of a rule's figure that decision 169 (c)'s audit
  finds, removed the same way);
- `tests/test_alerts.py`, `tests/test_dashboard.py`;
- any existing test that asserts a `persistent_approach` entry's exact key
  set, changed only to admit the two keys (decision 146 (c));
- `tests/fixtures/return_readers.toml`, only if a function holding a
  reference shape is added or changed.

Gate:
- `./scripts/check` green, with item 157 (c)'s equality test unchanged and
  passing.
- The tests of decision 169 (d) pass. Seen to fail, made alone and
  reverted: the page calling `stats.tightened_percentile` in place of
  reading the entry.
- The body gives decision 169 (c)'s list of every call `dashboard.py` makes
  into `stats`, `alerts`, `table` or `paper`, each with what it computes.
- The body gives `./scripts/gate M1 G1.3` at the commit (one call: wall
  time and pytest's line, beside mission 20 U6's 458 s) and decision 170's
  three measurements with their median ratio, at most 1.25.

The unit's commit is `alerts:`.

**U2 The unknown-coordinator test and a secret-free test environment
(REVIEW-20 should-fix 2; decision 171; DESIGN §14.2, §19.3 L4; I-11,
I-13).**

Files:
- `tests/test_cli_provider.py` (the test of decision 171 (a), changed as
  that item orders);
- `tests/conftest.py` (the autouse fixture of decision 171 (c));
- the test files that take decision 171 (b)'s two paths and (c)'s
  fixture test, named in the body;
- no file under `src/`.

Gate:
- `./scripts/check` green, with the equality test unchanged and passing.
- The tests of decision 171 pass. Seen to fail, made alone and reverted:
  the autouse fixture dropped, with its test run under a dummy
  `ANTHROPIC_API_KEY` in the environment.
- The body gives the item's tests run once more under a dummy
  `ANTHROPIC_API_KEY` in the environment (green), the list of secret
  variables the fixture removes with the constants that name them, and
  decision 171 (d)'s list.

The unit's commit is `tests:`.

**U3 The fix session's tools and the protected paths (REVIEW-20 should-fix
3 and note 5; decision 172; DESIGN §14.4; I-8).**

Files:
- `src/discotrade/coordinator.py` (`fix_session_command`'s `--tools`, and
  the whole-tool deny rules in the generated settings);
- `config/protected_paths.toml` (decision 172 (b)'s entries added; none
  removed);
- `tests/test_coordinator_claude.py`, or the test file the builder names.

Gate:
- `./scripts/check` green, with the equality test unchanged and passing.
- The tests of decision 172 (a) pass, and decision 164 (c)'s test passes
  over the extended file. Seen to fail, each made alone and reverted:
  - `--tools` dropped from the fix session's argument list;
  - `Bash` dropped from the deny rules.
- The body quotes the installed `claude --help` line for `--tools` and the
  `claude --version` string.

The unit's commit is `coordinator:`.

**U4 `gaps._MONTH_MISSING`'s content identity (REVIEW-20 should-fix 4;
decision 173; DESIGN §5.4; decision 157 (a)).**

Files:
- `tests/test_gap_months.py`, or the test file the builder names;
- no file under `src/`.

Gate:
- `./scripts/check` green, with the equality test unchanged and passing.
- The test of decision 173 passes. Seen to fail, made alone and reverted:
  the index entry's `rows` and `hash` dropped from `_MONTH_MISSING`'s key
  in `src/discotrade/bars/gaps.py`.

The unit's commit is `tests:`.

**U5 The regression gates at the pushed tip (O-2, O-25, O-27; decisions 168
(a), 170; DESIGN §18.2).**
1. After U4 is pushed, run `./scripts/check` three times at that tip
   (three calls, each wall time kept), all green.
2. Run `discotrade sandbox build` (its tag kept).
3. Run, each as one foreground call with a 20-minute timeout at that same
   pushed tip, with no uncommitted file but the git-ignored drafts:
   - `./scripts/gate M1 G1.1`, `G1.2`, `G1.3` and `G1.4`;
   - `./scripts/gate M3`;
   - `./scripts/gate M2`;
   - `./scripts/gate M0`.
4. Run decision 170's three measurements at that tip and keep their lines,
   their loads and the median ratio.
5. Keep each output verbatim with its wall time and `git rev-parse HEAD`.

Each prints its item PASS lines, and the whole-milestone runs print `gate
M3: PASS`, `gate M2: PASS` and `gate M0: PASS`. An item that prints FAIL,
or that does not finish within its call (O-2), is a defect:
- when it lies in a file a unit of this mission changed, that unit is taken
  again;
- when it would need a test of a met gate edited, decision 168 (b)
  applies;
- otherwise reply `VERDICT: mission 21 blocked U5` naming it.

An M1 item above 15 minutes stops the mission as O-27 item 3 says. Any
other item above 15 minutes is a finding with the times (DESIGN §18.2),
never a reason to weaken it. A median ratio above 1.25 at the tip is a
defect of U1, which is taken again. The unit's commit is `meta:`. It
carries only one line appended to `meta/findings/FINDINGS.md`: a D-013
times line with the three check runs. The gate outputs and the
measurements go to the report.

**U6 The final report (decisions 168 to 176; O-26, O-27; DESIGN §18.2).**
Write `meta/FINAL-REPORT-21.md`, drafted under `meta/drafts/` and moved in
by this commit. The report gives:
- What changed, with the sha of each unit.
- `## Corrections`: the three lines of `meta/FINAL-REPORT-20.md`'s `##
  Acceptance` that decision 174 (a) names, each with what the disk showed
  and the sha that closes it. `meta/FINAL-REPORT-20.md` itself is not
  edited.
- `./scripts/check`'s wall times at the tip, beside mission 20's (982 to
  990 s).
- `## Speed`: decision 170's three measurements and their median ratio at
  U1's commit and at the tip, each run with its load; G1.3's wall time at
  U1.
- Under `## Gate`, the outputs of U5, verbatim, as regression gates
  (O-25): `### Gate M1` (the four items, each with its wall time beside
  mission 20 U6's at 78b5535), `### Gate M3`, `### Gate M2` and `### Gate
  M0`, each with the tip it ran at and its wall time.
- `## Coordinator`: the `--tools` help line and the version read, the deny
  rules now generated (path rules and whole-tool rules), and the protected
  paths, with the entries U3 added.
- `## Register`: every entry of `tests/fixtures/return_readers.toml` added
  or changed by this mission, with its class and the unit, or "none".
- What the tests prove.
- NOT PROVEN, which is mandatory. It covers:
  - U3 of mission 20's ratio at `e8d31bb`, which stays as REVIEW-20
    recorded it (decision 170 (c));
  - that the speed figures are from the builder's machine, under the loads
    the runs give;
  - that no real `claude` was called (live check L4 not run): the tools
    and the deny rules are proven against the settings and the arguments a
    fake receives, not against Claude Code enforcing them (decision 172
    (c));
  - that a state written before U1 shows `—` for `N` and `p(N)`, and no
    state is rewritten to add them;
  - what remains of FINAL-REPORT-20's NOT PROVEN, item by item.
- The findings filed and answered.
- A `## Review items` table, with one row each for REVIEW-20 blocker 1,
  should-fix 1 to 4 and notes 1 to 10: the item, its resolution (the unit
  and decisions item, or "stands", or the step or owner that takes it, as
  decisions 169 to 175 say), and the sha where there is one.

Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 20's.
- At the pushed tip, with nothing uncommitted:
  - `./scripts/gate M1 G1.1` to `G1.4` each print their item PASS line,
    each within 15 minutes of wall time (O-27);
  - `./scripts/gate M3`, `./scripts/gate M2` and `./scripts/gate M0` print
    `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`;
  - every output, the tip's sha and every wall time are in the report.
- At U1's commit and at the tip, the median ratio of decision 170's three
  measurements is at most 1.25, with each run's figures and loads in the
  report.
- Each `persistent_approach` entry of the alert state holds the rule's `N`
  and `p_N`. `dashboard.py` calls no function that computes a rule's
  figure, as U1's list shows. Finding D-022 is filed and answered.
- `test_an_unknown_coordinator_is_a_usage_error` names unknown coordinators
  only, and decision 171's tests pass with and without a dummy
  `ANTHROPIC_API_KEY` in the environment.
- A fix session's argument list offers exactly `Read`, `Glob`, `Grep`,
  `Edit` and `Write`. Its settings deny `Bash`, `WebFetch` and `WebSearch`
  and the editing tools on every path of `config/protected_paths.toml`,
  which holds decision 172 (b)'s entries. The tests hold this against a
  fake `claude`.
- A test pins `_MONTH_MISSING`'s content identity, seen to fail without
  `rows` and `hash` in its key.
- No file under `tests/gates/`, `tests/fixtures/rejected/`, no record under
  `tests/fixtures/config/`, no entry of `tests/fixtures/config_frozen.json`
  and no value of a frozen configuration file changed in this mission.
  `config/protected_paths.toml` is the one file under `config/` that
  changed.
- Every unit commit's body lists every file it touches. U0 is `plan:`, U1
  is `alerts:`, U2 is `tests:`, U3 is `coordinator:`, U4 is `tests:`, and
  U5 is `meta:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no test builds the image.
- `meta/FINAL-REPORT-21.md` exists with `## Corrections`, `## Speed`, `##
  Gate` (the four regression gates), `## Coordinator`, `## Register`, NOT
  PROVEN, and the review-items table.
