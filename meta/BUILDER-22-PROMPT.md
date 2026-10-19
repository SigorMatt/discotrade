# BUILDER-22-PROMPT — discotrade mission 22: the full daily run, the digest and the issue sinks (step S4.2b)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 22. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-22.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 22 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-19-m22.md` (items 177 to 188, new for
this mission; every unit below cites them),
`meta/decisions/2026-10-18-owner.md` (the owner's; O-26 and O-27, the speed
measurement and the 15-minute stop),
`meta/decisions/decisions-2026-10-19-m21.md` (items 168 to 176; 168, 170,
171 and 176 in particular), `meta/decisions/decisions-2026-10-18-m20.md`
(items 155 to 167; 155, 156, 157 (c), 160, 163, 165 and 166 in
particular), `meta/decisions/2026-10-17-owner.md` (the owner's; O-25, add
never replace), `meta/decisions/decisions-2026-10-17-m19.md` (items 146 to
154; 146 (b), (c), 152 (e) and (f) in particular),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-18 the
register), `meta/decisions/decisions-2026-10-17-m18.md` (item 145, the
check's time), `meta/decisions/decisions-2026-10-16-m17.md` (items 136 and
137), `meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still bind;
47, 50, 51, 52, 54 and 72 in particular), `DESIGN.md` (§9.4 for the weekly
recomputation, §14.1 and §14.3 for the coordinator's input and output,
§15.2 to §15.4 for the health alerts, the alert state, the digest and the
issue, §16.1 to §16.4 for the daily run, its atomic days, its budgets and
the replay, §19.3 L6 for the issue check, §18.2 for the gate configuration;
read §2 twice, in particular I-5, I-6, I-8, I-11, I-12, I-13 and I-14),
`SPEC.md` §11 and §13 (the daily procedure, its retry and catch-up, the
digest), `meta/reviews/REVIEW-21.md` (its `## Notes`),
`meta/FINAL-REPORT-21.md`, `meta/findings/FINDINGS.md`, `meta/BACKLOG.md`,
and `meta/CHECKPOINT.md` (a unit in progress means §R first). This is
roadmap step S4.2b, mission 22.

---

## Mission

Build the rest of the daily run as decisions 177 to 188 say, and nothing
else. Concretely:
- `src/discotrade/digest.py` with the issue sinks (`FileIssueSink`,
  `GhIssueSink`), the `--issues` option and `doctor --live issues`'s
  refusals (decision 178);
- the digest page or the coordinator's run log sentence in step 7, and a
  run log line on every new day (decision 179);
- step 8: the commit, the push when the state repository has `origin`, and
  one issue per fired alert (decision 180);
- step 1 staged with the rest of the day (decision 181);
- the retry from a clean staging directory, `run_retried`, `run_failed`
  (decision 182), and the catch-up of missed days with `day_caught_up`
  (decision 183);
- the weekly journal recomputation as step 6 (decision 184), the
  `no_finding` call (decision 185), and the live defaults of `run-day`
  (decision 186).

Every unit that changes the day loop (U2 to U5) gives `./scripts/gate M1
G1.3`'s time and decision 170's three measurements at its commit (O-27 item
2, decision 177 (c)). An M1 item above 15 minutes stops the mission (O-27
item 3). Then run gate M1 again item by item, and gates M3, M2 and M0, at
the pushed tip (O-25, decision 177 (a)). Each must pass unchanged. No file
under `tests/gates/` changes. A test of a met gate that fails because of
what this mission adds is not edited: the unit stops, files a finding, and
you reply `VERDICT: question` with it (decision 177 (b)). This mission
closes no milestone. The M4 gate tests, the planted-edge market and the
failure injection of G4.3 are step S4.3's. Finish with a report whose first
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
- Your final reply begins with exactly one of: `VERDICT: mission 22
  finished` | `VERDICT: mission 22 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-19-m22.md`
and the items of the earlier decisions files and of the owner's files that
the unit names.

What no unit changes:
- any file under `tests/gates/`;
- any file under `tests/fixtures/rejected/`;
- any record under `tests/fixtures/config/`, except
  `tests/fixtures/config/run.toml` gaining the `[issues]` and `[state]`
  tables when decision 178 (c) or 180 (a) says so, and nothing else in it;
- any entry of `tests/fixtures/config_frozen.json`;
- any value of a frozen configuration file (`config/thresholds.toml`,
  `config/instruments/`, `config/tracks/`, `config/calendars/`,
  `config/spreads/`, `config/models.toml`).

The files under `config/` that change are `config/run.toml` (its new
`[issues]` and `[state]` tables, decisions 178 (c) and 180 (a)), which is
not frozen. Every existing test stays unchanged in what it asserts, except
where a decisions item orders the change (decision 177 (d)). Each such test
is named in the body with that item, and nothing it asserted before is
loosened (decision 146 (c)). If a test of a met gate (M0 to M3) fails
because of what a unit adds, the unit does not edit it. It stops, writes a
finding naming the test, the assertion and the change, and you reply
`VERDICT: question` with it (decision 177 (b)).

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
  wall time of one run. `./scripts/check` took 974 to 989 s at mission
  21's tip on the builder's machine, with the `container` tests run.
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
  naming it (O-27 item 3). If a unit changes what `./scripts/speed` must
  pass to the day function (a new argument), the script gains it with the
  replay's default and nothing else, named in the body.

How tests are written:
- Every test of this mission writes state and job directories, issue files
  and bare remotes only under a pytest temporary directory.
- It reads time only through `--as-of` or the replay's clock (decision 72).
- It runs the `discotrade` command in-process, through the function the
  console script calls.
- A test that runs `git` passes `GIT_ALLOW_PROTOCOL=file` in its
  environment and uses local paths only (decision 47).
- A test that checks a figure computes the expected value itself, without
  calling the function under test.
- A test that needs `claude` or `gh` uses a fake executable the test writes
  under its temporary directory, named by `[coordinator] binary` or
  `[issues] binary`. No test opens a socket, or calls a real provider, a
  real model, a real `claude` or a real `gh` (I-11).
- A failure a test injects into a day is made by the test (for example by
  `monkeypatch` of one step's function), never by a hostile strategy
  written for the purpose (decision 182 (e)).
- No test builds the image.

**U0 Plan (`plan:` commit).** In one `plan:` commit:
- Write `meta/plan.md`: these units with checkboxes, the base commit, the
  roadmap step S4.2b, the statement that this mission closes no milestone,
  and the regression gates of decision 177 (a) (M1 item by item, then M3,
  M2 and M0, at the pushed tip, U6) under O-27's 15-minute stop.
- Name in it, as carried items, each with the unit that takes it:
  - REVIEW-17 note 3's second half and note 4, REVIEW-19 notes 4 and 6
    (decision 182 (d), (e), U4);
  - REVIEW-17 note 5 (decision 186 (c), U5);
  - REVIEW-7's note on `revised_data` and `_indexed_last_ts`, REVIEW-2's
    note on `update_rolls` (decision 181, U3);
  - the live defaults of `run-day` (decision 137 (a); decision 186, U5);
  - the `no_finding` call (decision 152 (e); decision 185, U5);
  - the digest and the issues for the alerts mission 19 fires (decision
    152 (f); decisions 178 to 180, U1 and U2);
  - REVIEW-21 notes 1, 10 and 11 (decision 187 (b), U0);
  - REVIEW-21 note 2 (decision 188 (a), U7).
- Name in it, as left items, each with the step or the owner that takes
  it: findings D-019, D-020 and D-021 (the owner, `meta/BACKLOG.md`); the
  M4 gate tests, G4.4 and G4.5 among them, the planted-edge market and its
  corpus, and the failure injection of G4.3 (step S4.3); REVIEW-10's note
  on a death between the moves of a day (step S5.1's doctor,
  `meta/BACKLOG.md`).
- Rewrite `meta/CHECKPOINT.md` for this mission and append to
  `meta/journal.md`.
- Append to `meta/findings/FINDINGS.md`, after its last line and in its
  form, the lines of decision 187 (b): the D-013 times line, the HF-010
  line and the HF-012 line.

Nothing else. Gate: the four files are committed and pushed in one `plan:`
commit.

**U1 The digest module and the issue sinks (decision 178; decision 179 (a)
and (b) as functions; DESIGN 15.4, 19.3 L6; I-8, I-11, I-13).** Not a
day-loop unit: nothing the day calls changes.

Files:
- `src/discotrade/digest.py` (new: `IssueSink`, `FileIssueSink`,
  `GhIssueSink`, `IssueError`, and `render` of decision 179 (a), not yet
  called by the day);
- `src/discotrade/config.py` (the `[issues]` table of `run.toml`);
- `config/run.toml` (its `[issues]` table), and
  `tests/fixtures/config/run.toml` only as decision 178 (c) says;
- `src/discotrade/doctor.py` and `src/discotrade/cli.py` (`doctor --live
  issues`; the `--issues` option's parsing and refusals of decision 178
  (d), passed to nothing yet);
- `tests/test_digest.py` (new), and the doctor and CLI test files the body
  names.

Gate:
- `./scripts/check` green, with item 157 (c)'s equality test unchanged and
  passing.
- The tests of decision 178 (f) pass, and a test of `render` over payloads
  written by the test, whose tables hold each value the test computes from
  them, and whose prose comes from a scripted coordinator given kind and
  subject only. Seen to fail, each made alone and reverted: the labels'
  class dropped; the kill sent to the child only.
- The body quotes the `gh issue create --help` lines it took the flags from
  and `gh --version`, or says that `gh` is not installed and names the
  manual.

The unit's commit is `digest:`.

**U2 The digest, the run log and step 8 in the day (decisions 179, 180;
DESIGN 15.4, 16.1 steps 7 and 8, 16.2, 14.3; I-6, I-8).**

Files:
- `src/discotrade/daily.py` (step 7's digest page or run log line, the run
  log line of every new day with its `mode`, the push and the issues after
  the commit);
- `src/discotrade/coordinator.py` (the harness function of decision 179
  (d) for `write_digest` and `write_runlog_line`);
- `src/discotrade/replay.py` and `src/discotrade/cli.py` (the sink and the
  `mode` passed to the day; `replay`'s `--issues`, default `none`);
- `src/discotrade/config.py` and `config/run.toml` (the `[state]` table of
  decision 180 (a)), and `tests/fixtures/config/run.toml` only as decision
  178 (c) says;
- `scripts/speed.py`, only as "Long commands" above says;
- `tests/test_daily_digest.py` (new), and the test files the body names;
- `tests/fixtures/return_readers.toml`, only if a function holding a
  reference shape is added or changed.

Gate:
- `./scripts/check` green, with item 157 (c)'s equality test unchanged and
  passing.
- The tests of decisions 179 (f) and 180 (d) pass. Seen to fail, each made
  alone and reverted: a payload number added to the digest prompt; the run
  log line skipped on a digest day; the push run before the commit.
- The body gives `./scripts/gate M1 G1.3` at the commit (one call: wall
  time and pytest's line, beside mission 21 U5's 462 s) and decision 170's
  three measurements with their median ratio, at most 1.25.

The unit's commit is `daily:`.

**U3 Step 1 staged (decision 181; DESIGN 16.2, 5.2, 5.4, 5.6; decisions
2026-10-12 4, 5, 50, 54; I-5).**

Files:
- `src/discotrade/daily.py`, and the step 1 writers the body names
  (`src/discotrade/bars/store.py`, `src/discotrade/bars/gaps.py`,
  `src/discotrade/rolls.py`) for the staging directory and the typed error
  of decision 181 (c);
- the test files the body names;
- `tests/fixtures/return_readers.toml`, only as above.

Gate:
- `./scripts/check` green, with the equality test unchanged and passing,
  and the existing tests of interrupted appends, gaps, rolls and
  `revised_data` unchanged and passing.
- The tests of decision 181 (d) pass. Seen to fail, made alone and
  reverted: the bar append written in place instead of to the staging
  directory.
- The body names the means of decision 181 (a), and gives G1.3 and the
  three measurements at the commit, as U2 does.

The unit's commit is `daily:`.

**U4 The retry, `run_failed` and the catch-up (decisions 182, 183; DESIGN
16.1, 16.2, 15.2; SPEC §11; REVIEW-17 notes 3 and 4, REVIEW-19 notes 4 and
6).**

Files:
- `src/discotrade/daily.py` (the retry inside the lock, `run_retried`,
  `run_failed` with its issue, the catch-up with `day_caught_up`, the
  command's lines for caught-up days);
- `src/discotrade/cli.py` and `src/discotrade/replay.py`, only as the
  retry and the catch-up need;
- `tests/test_daily_retry.py` and `tests/test_daily_catch_up.py` (new),
  and the existing tests decisions 182 (f) and 183 (a) change, each named;
- `tests/fixtures/return_readers.toml`, only as above.

Gate:
- `./scripts/check` green, with the equality test unchanged and passing.
- The tests of decisions 182 (g) and 183 (d) pass, and decision 182 (e)'s
  call-limit test, or the body says which fixture strategy it looked for
  and why the note stays open. Seen to fail, each made alone and reverted:
  the retry removed; the staging directory not cleared before the retry;
  the missed days run newest first.
- The body gives G1.3 and the three measurements at the commit, as U2
  does.

The unit's commit is `daily:`.

**U5 The weekly recomputation, the `no_finding` call and the live defaults
of `run-day` (decisions 184, 185, 186; DESIGN 9.4, 15.2, 16.1 step 6;
decisions 54, 137 (a), 152 (e); REVIEW-17 note 5).**

Files:
- `src/discotrade/daily.py` (the weekly recomputation and the `no_finding`
  call in step 6);
- `src/discotrade/journal.py` and `src/discotrade/cli.py` (one function
  that draws and recomputes the sample, used by the day and by `journal
  recompute`; `run-day`'s defaults);
- `src/discotrade/replay.py` (`scripted_start`'s refusal);
- `scripts/check`, only if its smoke runs `run-day` (decision 186 (b));
- `tests/test_daily_weekly.py` (new), the `no_finding` and CLI test files
  the body names, and the existing tests decision 186 (b) changes, each
  named;
- `tests/fixtures/return_readers.toml`, only as above.

Gate:
- `./scripts/check` green, with the equality test unchanged and passing,
  and `journal recompute`'s existing tests unchanged and passing.
- The tests of decisions 184 (c), 185 and 186 (d) pass. Seen to fail, each
  made alone and reverted: the generator seeded with the day before;
  `replay` lines counted as live; the default of `--provider` left `none`.
- The body gives G1.3 and the three measurements at the commit, as U2
  does.

The unit's commit is `daily:`.

**U6 The regression gates at the pushed tip (O-2, O-25, O-27; decisions 177
(a), 170; DESIGN §18.2).**
1. After U5 is pushed, run `./scripts/check` three times at that tip
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
- when it would need a test of a met gate edited, decision 177 (b)
  applies;
- otherwise reply `VERDICT: mission 22 blocked U6` naming it.

An M1 item above 15 minutes stops the mission as O-27 item 3 says. Any
other item above 15 minutes is a finding with the times (DESIGN §18.2),
never a reason to weaken it. A median ratio above 1.25 at the tip is a
defect of U5, which is taken again.
The unit's commit is `meta:`. It carries only one line appended to
`meta/findings/FINDINGS.md`: a D-013 times line with the three check runs.
The gate outputs and the measurements go to the report.

**U7 The final report (decisions 177 to 188; O-26, O-27; DESIGN §18.2).**
Write `meta/FINAL-REPORT-22.md`, drafted under `meta/drafts/` and moved in
by this commit. The report gives:
- What changed, with the sha of each unit.
- `## Corrections`: decision 188 (a)'s line. `meta/FINAL-REPORT-21.md`
  itself is not edited.
- `./scripts/check`'s wall times at the tip, beside mission 21's (974 to
  989 s).
- `## Speed`, `## Gate`, `## Daily run`, `## Issues` and `## Register`, as
  decision 188 (b) to (f) says.
- What the tests prove.
- NOT PROVEN, which is mandatory, covering at least decision 188 (g)'s
  items.
- The findings filed and answered.
- A `## Review items` table, as decision 188 (h) says.

Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 21's.
- At the pushed tip, with nothing uncommitted:
  - `./scripts/gate M1 G1.1` to `G1.4` each print their item PASS line,
    each within 15 minutes of wall time (O-27);
  - `./scripts/gate M3`, `./scripts/gate M2` and `./scripts/gate M0` print
    `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`;
  - every output, the tip's sha and every wall time are in the report.
- At each of U2 to U5 and at the tip, the median ratio of decision 170's
  three measurements is at most 1.25, with each run's figures and loads in
  the report, and G1.3's wall time at each of U2 to U5 is in the report.
- A day on which an alert fired writes `digests/<track>/<D>.md` with the
  harness's tables of every fired payload and the coordinator's prose,
  whose prompt holds kinds and subjects only; every new day appends one
  run log line with the fields of decision 179 (c); a re-run writes
  neither.
- After the commit, a state repository with `origin` is pushed (a failure
  is `push_failed`), and one issue is opened per fired alert through the
  command's sink (a failure is `issue_failed`). `FileIssueSink` and
  `GhIssueSink` hold decision 178's behaviour against files and a fake
  `gh`; `doctor --live issues` refuses as decision 178 (e) says.
- Step 1's writes are staged: a day that fails leaves `bars/`, `rolls/`
  and the gaps file as they were. A day that fails once is retried from a
  clean staging directory and committed once with `run_retried`; a day
  that fails twice leaves every state file but the health log and the
  stored responses unchanged, records `run_failed`, opens its issue and
  exits 1; its retry makes no second provider call.
- Missed trading days are run first, oldest first, each with its own
  commit and a `day_caught_up` alert.
- The first trading day of each ISO week recomputes the sample of decision
  184, by the function `journal recompute` uses; `no_finding` is called as
  decision 185 says and never raised by a replay.
- `run-day` defaults to `--provider openai --coordinator claude --issues
  gh`, each refused before any day without its key, binary or remote;
  `replay`'s defaults are unchanged.
- No file under `tests/gates/`, `tests/fixtures/rejected/`, no record under
  `tests/fixtures/config/` but `run.toml`'s new tables, no entry of
  `tests/fixtures/config_frozen.json` and no value of a frozen
  configuration file changed in this mission.
- Every unit commit's body lists every file it touches. U0 is `plan:`, U1
  is `digest:`, U2 to U5 are `daily:`, and U6 is `meta:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory, issue file or remote is written inside the repository; no test
  builds the image.
- `meta/FINAL-REPORT-22.md` exists with `## Corrections`, `## Speed`, `##
  Gate` (the four regression gates), `## Daily run`, `## Issues`, `##
  Register`, NOT PROVEN, and the review-items table.
