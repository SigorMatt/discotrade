# BUILDER-20-PROMPT — discotrade mission 20: the day loop's speed under O-26 and O-27, REVIEW-19's items, and the Claude Code coordinator with its deny rules (step S4.2a)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 20. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-20.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 20 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/2026-10-18-owner.md` (the owner's; O-26 and O-27, which
this mission builds; its "For the builder" step 4 sends you here),
`meta/decisions/decisions-2026-10-18-m20.md` (items 155 to 167, new for
this mission; every unit below cites them),
`meta/decisions/2026-10-17-owner.md` (the owner's; O-25, add never
replace), `meta/decisions/decisions-2026-10-17-m19.md` (items 146 to 154;
146 (b), (c), 152 and 153 in particular),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-18 the
register), `meta/decisions/decisions-2026-10-15-owner.md` (the owner's;
O-19), `meta/decisions/decisions-2026-10-17-m18.md` (item 145, the check's
time), `meta/decisions/decisions-2026-10-16-m17.md` (items 136, 137 and
140), `meta/decisions/decisions-2026-10-16-m15.md` (items 121, 122 and 125:
the synthetic cache, the providers with the Claude worker, and the
coordinator's interface),
`meta/decisions/decisions-2026-10-16-m16.md` (item 131 (d)),
`meta/decisions/decisions-2026-10-14.md` (item 80, the speed rules),
`meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still bind; 72 the
gate configuration), `DESIGN.md` (§14.1 to §14.4 for the coordinator,
§16.1 to §16.4 for the day loop and the replay, §15.2, §15.3 and §15.5 for
the health events, the alert state and the dashboard, §10.4 and §11.1 for
the table and rank persistence, §9.1 for the state directory, §18.2 for the
gate configuration, §19.3 for L4; read §2 twice, in particular I-5, I-6,
I-8, I-11, I-12 and I-13), `SPEC.md` §17 (the coordinator's headless call),
`meta/reviews/REVIEW-19.md` (its `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-19.md`, `meta/findings/FINDINGS.md`, `meta/BACKLOG.md`,
and `meta/CHECKPOINT.md` (a unit in progress means §R first). This is
roadmap step S4.2a.

---

## Mission

Build step S4.2a as the owner's rulings O-26 and O-27 and decisions 155 to
167 say. First, after U0, the speed units (O-26 item 1): within one
process, a replay day's cost must not grow with the history the state
holds. They change only how the day loop arrives at its figures, never
what any day computes or writes. Concretely:
- `./scripts/speed` measures the G1.3 scenario as O-26 item 4 says
  (decision 156);
- the table (U1), step 6 (U2) and step 7 with whatever else the measurement
  shows growing (U3) reuse what earlier days of the same process computed;
- every incremental figure equals its full recompute, proven by a test in
  the check and over the whole scenario (decision 157);
- after a full replay of the scenario, each speed unit's state directory is
  byte-identical to its parent's outside `.git/`;
- at U3 the ratio of the last 30 days' cost per subject-day to the first
  30 days' is at most 1.25.

Then REVIEW-19's should-fix items (decisions 160 to 162, finding D-018),
and the Claude Code form of the coordinator against a fake binary, with
its token budget, the process-group kill, `config/protected_paths.toml`
and the deny rules generated from it (decisions 163 to 166).

Every code unit gives `./scripts/gate M1 G1.3`'s time and the measurement's
four figures at its commit (O-27 item 2). An M1 item above 15 minutes stops
the mission (O-27 item 3, decision 159 (b)). Then run gate M1 again item
by item, and gates M3, M2 and M0, at the pushed tip (O-25, decision 155
(a)). Each must pass unchanged. No file under `tests/gates/` changes. A
test of a met gate that fails because of what this mission adds is not
edited: the unit stops, files a finding, and you reply `VERDICT: question`
with it (decision 155 (b)). This mission closes no milestone. The digest,
the issue sinks and the full daily run are step S4.2b's, and the M4 gate
tests are step S4.3's. Finish with a report whose first line the playbook
can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 20
  finished` | `VERDICT: mission 20 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/2026-10-18-owner.md`,
`meta/decisions/decisions-2026-10-18-m20.md` and the items of the earlier
decisions files and of the owner's files that the unit names.

What no unit changes:
- any file under `tests/gates/`;
- any file under `tests/fixtures/rejected/`;
- any record under `tests/fixtures/config/`, except the one
  `[coordinator]` table decision 163 (b) allows in
  `tests/fixtures/config/run.toml`;
- any entry of `tests/fixtures/config_frozen.json`;
- any value of a frozen configuration file (`config/thresholds.toml`,
  `config/instruments/`, `config/tracks/`, `config/calendars/`,
  `config/spreads/`, `config/models.toml`).

The new files under `config/` are `config/protected_paths.toml` (U5,
decision 164); `config/run.toml` gains its `[coordinator]` table (U5,
decision 163 (b)). Every existing test stays unchanged in what it asserts,
except where an owner item or a decisions item orders the change. Each such
test is named in the body with that item, and nothing it asserted before
is loosened (decision 146 (c)). The speed units U1 to U3 change no test's
assertion at all (O-26 item 3). If a test of a met gate (M0 to M3) fails
because of what a unit adds, the unit does not edit it. It stops, writes a
finding naming the test, the assertion and the change, and you reply
`VERDICT: question` with it (decision 155 (b)).

Every function this mission adds or changes that holds one of the audit's
reference shapes (`tests/test_return_readers.py`) is registered in
`tests/fixtures/return_readers.toml` in the same commit, with its class and
a one-line note, and the audit passes. The commit body names each new or
changed entry (O-18, decision 158).

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

Long commands (finding HF-006; decision 159 (d)):
- Every run of `./scripts/check`, `./scripts/gate` or `./scripts/speed` is
  its own foreground Bash call with an explicit timeout of 20 minutes, the
  tool's maximum. Never chain two such runs in one call, and never let one
  run in the background.
- Each sub-agent runs `./scripts/check` three times before its commit, as
  three calls, and says in its report how many runs were green, with the
  wall time of one run. `./scripts/check` took 1066 to 1131 s at mission
  19's tip on the builder's machine, with the `container` tests run.
- A run that passes the 20-minute cap and is moved to the background by the
  harness is waited for to its end before the next run: a lone `sleep 240`
  call, then a lone read of its output file, repeated until it has printed
  its last line. Never a Monitor, never a background task to wait, never a
  `sleep` chained with another command, and never a report before the run
  has ended. It is recorded as decision 145 says, never dropped, shortened
  or counted green before it ends.
- Every sub-agent first runs `discotrade sandbox build`, as its own
  foreground call with a 20-minute timeout, so that the `container` tests
  of the check run and do not skip, and says in its report that they ran
  and the tag.
- Every code unit (U1 to U5) gives in its body, at its commit:
  `./scripts/gate M1 G1.3` (one call: wall time and pytest's line) and
  `./scripts/speed --work <dir>` (as many calls as it takes: its four
  figures and its process starts), with the load average (O-27 item 2,
  decision 159 (a)). G1.3 above 15 minutes of wall time stops the mission:
  the unit files a finding (the next free `D-###`) with the times and the
  measurement, weakens nothing, and you reply `VERDICT: question` naming it
  (O-27 item 3). A ratio above 1.25 fails U3, U4 or U5 (O-26 item 4,
  decisions 158, 159 (c)).

How tests are written:
- Every test of this mission writes state and job directories only under a
  pytest temporary directory.
- It reads time only through `--as-of` or the replay's clock (decision 72).
  The one exception is `./scripts/speed`'s own timing (decision 156 (b)),
  which writes nothing in a state directory.
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
  roadmap step S4.2a, the statement that this mission closes no milestone,
  the order O-26 item 1 sets (the speed units U1 to U3 first), and the
  regression gates of decision 155 (a) (M1 item by item, then M3, M2 and
  M0, at the pushed tip, U6) under O-27's 15-minute stop.
- Name in it, as carried items, each with the unit that takes it:
  - O-26 (U1 to U3; items 4 and 5 by U1, the ratio by U3);
  - O-27 (U1 to U6; item 4 by U0);
  - REVIEW-19 should-fix 1, finding D-018 (decision 160, U4);
  - REVIEW-19 should-fix 2 (decision 161, U4);
  - REVIEW-19 should-fix 3 (decision 162, U7);
  - REVIEW-15 note 3's second half (decision 166, U5);
  - REVIEW-19 notes 11 to 15 (decision 167 (b), U0).
- Name in it, as left items, each with the step that takes it: the digest,
  the issue sinks, the full daily run, the `no_finding` call, the live
  defaults of `run-day`, REVIEW-17 notes 3 to 5 and REVIEW-19 notes 4 and 6
  (step S4.2b); G4.4 and G4.5 as gate tests (step S4.3).
- Rewrite `meta/CHECKPOINT.md` for this mission and append to
  `meta/journal.md`.
- Append to `meta/findings/FINDINGS.md`, after its last line and in its
  form, the lines of decision 167 (b): D-014's status line exactly as O-27
  item 4 gives it, finding D-018 and its status line, the HF-006, HF-012,
  HF-010 and HF-013 lines, and the new hands finding, numbered from the
  next free `HF-` number.

Nothing else. Gate: the four files are committed and pushed in one `plan:`
commit.

**U1 The measurement, the equality test, and the table without growth
(O-26 items 2 to 5; decisions 156, 157, 158; DESIGN §10.4, §16.4; I-6,
I-12).**

Files:
- `scripts/speed` (new, executable) and any Python it runs, under
  `scripts/` (decision 156 (a));
- `src/discotrade/table.py` (the table's figures reused across the days of
  one process);
- the module the builder chooses for decision 157 (b)'s cache-clearing
  function, and the modules whose existing caches register with it
  (`src/discotrade/sources/synth.py`, the trusted-hash cache, the per-run
  bar verification), changed only to register;
- `src/discotrade/paper.py` and `src/discotrade/stats.py`, only where the
  table's reuse needs them, each existing function's result unchanged for
  every input (O-25);
- `tests/fixtures/return_readers.toml`, only if a function holding a
  reference shape is added or changed;
- new tests: the command's test (decision 156 (d)), the equality test
  (decision 157 (c)), the cache tests (decision 157 (a), (b)).

Gate:
- `./scripts/check` green.
- The new tests pass. Seen to fail, each made alone and reverted:
  - a table cache keyed by path only (a rewritten record of the same length
    is served stale);
  - the clearing function skipping the table's cache (the equality test's
    cold run then differs, or the cache test fails).
- The body gives everything decision 158 lists:
  - the four figures at the parent (measured as decision 156 (e) says) and
    at the commit;
  - the profiles;
  - decision 157 (d)'s cold comparison and 157 (e)'s byte-identical
    comparison;
  - G1.3's wall time and line beside mission 19's 1049 s and REVIEW-19's
    1087 s.

The unit's commit is `table:`.

**U2 Step 6 without growth (O-26 item 2; decisions 157, 158; DESIGN
§15.1 to §15.3, §16.1 step 6).**

Files:
- `src/discotrade/alerts.py` (`rank_rows`, `detectors`, `step` and the four
  rules, with the slots' series `persistent_approach` reads, reused across
  the days of one process; registered with the clearing function);
- `src/discotrade/paper.py`, only where the reuse needs it, each existing
  function's result unchanged for every input;
- `tests/fixtures/return_readers.toml`, as U1;
- new cache tests.

Gate:
- `./scripts/check` green, the equality test of U1 unchanged and passing.
- Seen to fail, made alone and reverted: an alert cache not cleared by the
  clearing function.
- The body gives everything decision 158 lists, with G1.3 beside U1's.

The unit's commit is `alerts:`.

**U3 Step 7 and the rest without growth; the ratio (O-26 items 2 and 4;
decisions 157, 158; DESIGN §15.5, §16.1).**

Files:
- `src/discotrade/dashboard.py` (`render` reusing what earlier days of the
  process computed);
- each other module whose per-day cost the measurement shows growing with
  history, named in the body with its profile (decision 158), changed only
  in how it arrives at its figures;
- `tests/fixtures/return_readers.toml`, as U1;
- new cache tests.

Gate:
- `./scripts/check` green, the equality test unchanged and passing.
- `./scripts/speed`'s ratio at the commit is at most 1.25 (O-26 item 4).
  Above it, the unit fails and is retried once, then marked blocked, never
  passed.
- Seen to fail, made alone and reverted: a dashboard cache not cleared by
  the clearing function.
- The body gives everything decision 158 lists, with G1.3 beside U2's.

The unit's commit is `dashboard:`, or the area of the module that took the
most if that is not the dashboard.

**U4 REVIEW-19's should-fix items 1 and 2 (decisions 160, 161; finding
D-018; DESIGN §15.3, §15.5).**

Files:
- `src/discotrade/alerts.py` (the `rank_persistence` entry's `p`);
- `src/discotrade/dashboard.py` (`p` read from the state; `_rank_p` and any
  other recomputation of a rule's figure removed);
- `tests/test_alerts.py`, `tests/test_dashboard.py`;
- any existing test that asserts the `rank_persistence` entry's exact key
  set, changed only to admit `p` (decision 146 (c)).

Gate:
- `./scripts/check` green, the equality test unchanged and passing.
- The tests of decisions 160 and 161 pass. Seen to fail, each made alone
  and reverted:
  - the page computing `p` from `value` and `threshold`;
  - `window = 20` in place of `pool.fail_window` in `dashboard.py`.
- G1.3 and `./scripts/speed` at the commit, as every code unit.

The unit's commit is `alerts:`.

**U5 The Claude Code form of the coordinator, its budget, the process
group, and the deny rules (decisions 163 to 166; DESIGN §14.1 to §14.4,
§16.3, §19.3 L4; SPEC §17; I-8, I-11, I-13).**

Files:
- `src/discotrade/coordinator.py` (`ClaudeCodeCoordinator`, the settings
  generator, the fix-session command builder);
- `src/discotrade/workers/providers.py` (the process-group kill);
- `src/discotrade/daily.py`, `src/discotrade/replay.py` and
  `src/discotrade/cli.py` (`--coordinator claude`, the budget), only as
  far as they need;
- `src/discotrade/config.py`, only to read the `[coordinator]` table and
  `config/protected_paths.toml`;
- `src/discotrade/doctor.py` (`doctor --live coordinator`);
- `config/run.toml` (the `[coordinator]` table);
- `config/protected_paths.toml` (new);
- `tests/fixtures/config/run.toml`, only as decision 163 (b) allows;
- new tests (`tests/test_coordinator_claude.py` or as the builder names
  them), and `tests/test_cli.py`, `tests/test_doctor.py`.

Gate:
- `./scripts/check` green, the equality test unchanged and passing.
- The tests of decisions 163 (g), 164 (c), 165 and 166 pass. Seen to
  fail, each made alone and reverted:
  - the offered-cell check skipped;
  - the key passed as an argument;
  - a score added to the prompt;
  - one path dropped from the generated rules;
  - the kill sent to the child only.
- The body quotes the `claude --help` lines and the `claude --version`
  string the flags were taken from, and the source of the deny-rule
  syntax.
- G1.3 and `./scripts/speed` at the commit, as every code unit.

The unit's commit is `coordinator:`.

**U6 The regression gates at the pushed tip (O-2, O-25, O-27; decision
155 (a); DESIGN §18.2).**
1. After U5 is pushed, run `./scripts/check` three times at that tip
   (three calls, each wall time kept), all green.
2. Run `discotrade sandbox build` (its tag kept).
3. Run, each as one foreground call with a 20-minute timeout at that same
   pushed tip, with no uncommitted file but the git-ignored drafts:
   - `./scripts/gate M1 G1.1`, `G1.2`, `G1.3` and `G1.4`;
   - `./scripts/gate M3`;
   - `./scripts/gate M2`;
   - `./scripts/gate M0`.
4. Run `./scripts/speed --work <dir>` at that tip (as many calls as it
   takes) and keep its lines.
5. Keep each output verbatim with its wall time and `git rev-parse HEAD`.

Each prints its item PASS lines, and the whole-milestone runs print `gate
M3: PASS`, `gate M2: PASS` and `gate M0: PASS`. An item that prints FAIL,
or that does not finish within its call (O-2), is a defect:
- when it lies in a file a unit of this mission changed, that unit is taken
  again;
- when it would need a test of a met gate edited, decision 155 (b)
  applies;
- otherwise reply `VERDICT: mission 20 blocked U6` naming it.

An M1 item above 15 minutes stops the mission as O-27 item 3 says. Any
other item above 15 minutes is a finding with the times (DESIGN §18.2),
never a reason to weaken it. The unit's commit is `meta:`. It carries only
one line appended to `meta/findings/FINDINGS.md`: a D-013 times line with
the three check runs. The gate outputs and the measurement go to the
report, not to a D-014 times line (O-27 item 2).

**U7 The final report (decisions 155 to 167; O-26, O-27; DESIGN §18.2).**
Write `meta/FINAL-REPORT-20.md`, drafted under `meta/drafts/` and moved in
by this commit. The report gives:
- What changed, with the sha of each unit.
- `./scripts/check`'s wall times at the tip, beside mission 19's (1066 to
  1131 s).
- `## Speed`: for U1 to U5 and the tip, O-26's four figures and the process
  starts, at each unit's parent and commit; the profiles' summary; each
  speed unit's cold comparison and byte-identical comparison; G1.3's wall
  time at each unit.
- Under `## Gate`, the outputs of U6, verbatim, as regression gates
  (O-25): `### Gate M1` (the four items, each with its wall time beside
  mission 19's builder's at ef9359f and REVIEW-19's at ad3576c), `### Gate
  M3`, `### Gate M2` and `### Gate M0`, each with the tip it ran at and its
  wall time.
- `## Owner rulings applied`: for each of O-26 items 1 to 6 and O-27 items
  1 to 4, what was done, the unit and sha, and the test or measurement
  that holds it.
- `## Coordinator`: the flags and the version read from the installed
  `claude`, the settings generated, and the protected paths.
- `## Register`: every entry of `tests/fixtures/return_readers.toml` added
  or changed by this mission, with its class and the unit, or "none".
- What the tests prove.
- NOT PROVEN, which is mandatory. It covers:
  - that no figure of either measure exists at mission 18's tip (d8a129a or
    031f5e4), and that U1's parent figures are the first of O-26's
    (decision 162);
  - that the live loop's cost still grows with history, each day a cold
    process (O-26 item 6), reported by the fourth figure with no
    threshold;
  - that the speed figures are from the builder's machine, under the load
    each body gives;
  - that no real `claude` was called (live check L4 not run): the flags
    are proven against the installed help and a fake binary, and the deny
    rules against the settings a fake receives, not against Claude Code
    enforcing them;
  - that the coordinator's `model` is the project's choice, unverified;
  - what remains of FINAL-REPORT-19's NOT PROVEN, item by item.
- The findings filed and answered.
- A `## Review items` table, with one row each for REVIEW-19 should-fix 1
  to 3 and notes 1 to 15: the item, its resolution (the unit and decisions
  item, or "stands", or the step that takes it, as decisions 160 to 162
  and 167 say), and the sha where there is one.

Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 19's.
- At the pushed tip, with nothing uncommitted:
  - `./scripts/gate M1 G1.1` to `G1.4` each print their item PASS line,
    each within 15 minutes of wall time (O-27);
  - `./scripts/gate M3`, `./scripts/gate M2` and `./scripts/gate M0` print
    `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`;
  - every output, the tip's sha and every wall time are in the report.
- `./scripts/speed` exists and prints the lines of decision 156 (c). At
  U3's commit and at the tip its ratio is at most 1.25.
- After a full replay of the G1.3 scenario, the state directory at each of
  U1, U2 and U3 is identical to its parent's outside `.git/`, with the same
  `HEAD` tree, and the cold replay's commit trees equal the warm replay's
  on every day.
- The equality test of decision 157 (c) is in `./scripts/check` and passes
  at every unit's commit from U1 on.
- The `rank_persistence` entry of the alert state holds the rule's `p`, and
  the dashboard recomputes no rule's figure. Finding D-018 is filed and
  answered.
- `ClaudeCodeCoordinator` exists, is tested against a fake `claude` only,
  and passes no key in an argument; `--coordinator scripted` stays the
  default. `config/protected_paths.toml` exists and every path in it is
  denied by the generated settings.
- No file under `tests/gates/`, `tests/fixtures/rejected/`, no record under
  `tests/fixtures/config/` (but decision 163 (b)'s one table), no entry of
  `tests/fixtures/config_frozen.json` and no value of a frozen
  configuration file changed in this mission. `config/protected_paths.toml`
  is the one new file under `config/`.
- Every unit commit's body lists every file it touches. U0 is `plan:`, U1
  is `table:`, U2 is `alerts:`, U3 is `dashboard:` (or as U3 says), U4 is
  `alerts:`, U5 is `coordinator:`, and U6 is `meta:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no test builds the image.
- `meta/FINAL-REPORT-20.md` exists with `## Speed`, `## Gate` (the four
  regression gates), `## Owner rulings applied`, `## Coordinator`, `##
  Register`, NOT PROVEN, and the review-items table.
