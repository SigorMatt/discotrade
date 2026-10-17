# BUILDER-19-PROMPT — discotrade mission 19: alert rules, alert state and the dashboard on the adjusted and timing measures, under O-23 to O-25 (step S4.1)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 19. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-19.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 19 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/2026-10-17-owner.md` (the owner's; O-23 to O-25, which this
mission builds; its "For the builder" step 3 sends you here),
`meta/decisions/decisions-2026-10-17-m19.md` (items 146 to 154, new for
this mission; every unit below cites them),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-4 to O-8,
O-13, O-14, O-16 and O-18 in particular),
`meta/decisions/decisions-2026-10-15-owner.md` (the owner's; O-19's rule on
gate tests of a met milestone, which O-25 extends),
`meta/decisions/decisions-2026-10-17-m18.md` (items 141 to 145; 145 the
check's time), `meta/decisions/decisions-2026-10-14-m11.md` (items 83 to
90; 89 the register and its audit), `meta/decisions/decisions-2026-10-12.md`
(items 1 to 75 still bind; 59, 60, 62, 69, 70 and 71 the statistics, the
rank rows and the table, 72 the gate configuration), `DESIGN.md` (§15.1 to
§15.3 and §15.5 for the rules, the state and the dashboard, §11.1 to §11.4
for the statistics, §10.4 and §10.5 for the table and the portfolio, §4.3
for the thresholds and their history, §16.1 step 6 and 7 and §16.2 for the
day loop, §18.2 for the gate configuration; read §2 twice, in particular
I-4, I-5, I-6, I-10 and I-12), `SPEC.md` §13 and §14 (the dashboard's
panels and the stage-3 conditions), `meta/reviews/REVIEW-18.md` (its
`## Gate` and `## Notes`), `meta/FINAL-REPORT-18.md`,
`meta/findings/FINDINGS.md`, `meta/BACKLOG.md`, and `meta/CHECKPOINT.md` (a
unit in progress means §R first). This is roadmap step S4.1.

---

## Mission

Build step S4.1 as the owner's rulings O-23 to O-25 and decisions 146 to
154 say. Add, never replace: every function a met gate reads keeps its
result for the inputs it has today (O-25). Concretely:
- `stats.control_moments` gains `column`, and the register's three pending
  entries are settled (decision 147);
- the table keeps `S`, `E_N` and `excess` and gains `adjusted_S`,
  `adjusted_E_N` and `adjusted_excess` (decision 148, O-23);
- the rank-persistence rows gain `timing` and `gross` (decision 149, O-24),
  with the one-sided t-test (decision 150);
- the finding rules `persistent_approach` and `group_edge` read the
  exposure-adjusted series (decision 151, O-7);
- the alert state, the payloads, the `rank_persistence` and `revival` rules
  and the health alerts run in the day loop (decision 152);
- the dashboard is built with its stage-3 panel (decision 153).

Then run gate M1 again item by item, and gates M3, M2 and M0, at the pushed
tip (decision 146 (a), 154 (d)). Each must pass unchanged. The only change
to any file under `tests/gates/` is decision 148 (d)'s one line in
`tests/gates/test_g1_3_lifecycle.py`. A test of a met gate that fails
because of what this mission adds is not edited: the unit stops, files a
finding, and you reply `VERDICT: question` with it (decision 146 (b)). This
mission closes no milestone. The digest, the issues and the full daily run
are step S4.2's, and the M4 gate tests are step S4.3's. Finish with a
report whose first line the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 19
  finished` | `VERDICT: mission 19 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/2026-10-17-owner.md`,
`meta/decisions/decisions-2026-10-17-m19.md` and the items of the earlier
decisions files and of the owner's files that the unit names.

What no unit changes:
- any file under `tests/fixtures/rejected/`;
- any record under `tests/fixtures/config/`;
- any entry of `tests/fixtures/config_frozen.json`;
- any value of a frozen configuration file (`config/thresholds.toml`,
  `config/instruments/`, `config/tracks/`, `config/calendars/`,
  `config/spreads/`, `config/models.toml`);
- any file under `tests/gates/` but the one line of decision 148 (d).

The one new file under `config/` is `config/gates.toml` (U5, decision 153
(b)). Every existing test stays unchanged in what it asserts, except where
an owner item or a decisions item orders the change. Each such test is
named in the body with that item, and nothing it asserted before is
loosened (decision 146 (c)). If a test of a met gate (M0 to M3) fails
because of what a unit adds, the unit does not edit it. It stops, writes a
finding naming the test, the assertion and the change, and you reply
`VERDICT: question` with it (decision 146 (b)).

Every function this mission adds or changes that holds one of the audit's
reference shapes (`tests/test_return_readers.py`) is registered in
`tests/fixtures/return_readers.toml` in the same commit, with the class the
owner's files and decisions 147 to 153 give it and a one-line note. The
commit body names each new or changed entry, and the review reads each one
against O-16 (O-18).

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

Long commands (finding HF-006):
- Every run of `./scripts/check` or `./scripts/gate` is its own foreground
  Bash call with an explicit timeout of 20 minutes, the tool's maximum.
  Never chain two such runs in one call, and never let one run in the
  background.
- Each sub-agent runs `./scripts/check` three times before its commit, as
  three calls, and says in its report how many runs were green, with the
  wall time of one run. `./scripts/check` took 917 to 931 s at mission 18's
  tip on the builder's machine, with the `container` tests run.
- A run that passes the 20-minute cap and is moved to the background by the
  harness is waited for to its end before the next run, and recorded as
  decision 145 says. It is never dropped, shortened or counted green before
  it ends.
- Every sub-agent first runs `discotrade sandbox build`, as its own
  foreground call with a 20-minute timeout, so that the `container` tests
  of the check run and do not skip, and says in its report that they ran
  and the tag.
- A unit that changes the day loop (U2, U4, U5) gives in its body the
  seconds per replay day of the G1.3 scenario's first 30 calendar days, at
  its parent and at its commit, by decision 80 (d)'s method (decision 154
  (c)).

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
- A rule's unit tests read `config/thresholds.toml` through the config
  loader, so they run at the production values (DESIGN §18.2; decisions
  151 (c), 152 (g)). Their inputs are written under the temporary directory
  by the writers the product uses, with every value and seed written in the
  test.
- No test opens a socket, or calls a real provider, a real model or a real
  `claude` binary (I-11).
- No test builds the image.

**U0 Plan (`plan:` commit).** In one `plan:` commit:
- Write `meta/plan.md`: these units with checkboxes, the base commit, the
  roadmap step S4.1, the statement that this mission closes no milestone,
  and the regression gates of decision 146 (a) (M1 item by item, then M3,
  M2 and M0, at the pushed tip, U6).
- Name in it, as carried items, each with the unit that takes it:
  - O-23 (U1);
  - O-24 (U1 for `control_moments` and the register, U2 for the rank rows,
    U3 and U4 for the alert functions);
  - O-25 (every unit, and U6);
  - REVIEW-11 note 8 (decision 153 (c), U5);
  - REVIEW-18 notes 7 to 10 (decision 154 (b), U0).
- Name in it, as left items, each with the step that takes it: the
  `no_finding` call, the digest and the issues (step S4.2), and G4.5
  (step S4.3).
- Rewrite `meta/CHECKPOINT.md` for this mission and append to
  `meta/journal.md`.
- Append to `meta/findings/FINDINGS.md`, after its last line and in its
  form, the five lines of decision 154 (b): the HF-006, HF-012 and HF-010
  lines and the two new hands findings, numbered from the next free `HF-`
  number.

Nothing else. Gate: the four files are committed and pushed in one `plan:`
commit.

**U1 `control_moments`'s column, the register, and the table's adjusted
deflated figures (O-23, O-24; decisions 147, 148; DESIGN §10.4, §11.2).**

Files:
- `src/discotrade/stats.py` (`control_moments` gains `column`, default
  `net_1x`, and its docstring says so);
- `src/discotrade/table.py` (the three fields, their function, `FIELDS`,
  `_REALS`, `LABELS`, the docstring);
- `src/discotrade/paper.py`, only if decision 147 (d)'s optional parameter
  is added;
- `tests/fixtures/return_readers.toml` (decision 147 (c), and the new
  table function, `adjusted`);
- `tests/test_return_readers.py` (`PENDING` empty, its test renamed, the
  docstring sentence; decision 147 (c));
- `tests/test_stats.py`, `tests/test_table.py`, and `tests/test_paper.py`
  if `paper.adjusted` changes (new tests);
- `tests/gates/test_g1_3_lifecycle.py` (exactly decision 148 (d)'s line;
  the body quotes O-23's sentence that permits it).

Gate: `./scripts/check` green; the new tests assert decision 147 (a)'s
default and named column, decision 147 (d)'s equality if it is added, and
decision 148 (e)'s figures. Seen to fail, each made alone and reverted:
decision 148 (e)'s three wrong changes. Run `./scripts/gate M1 G1.3` and
`./scripts/gate M1 G1.4` once each at the unit's commit, each its own
foreground call with a 20-minute timeout. Both print PASS, and their
outputs and wall times go in the body: G1.3 beside mission 17 U5's 542 s,
G1.4 beside its 1 s. The unit's commit is `table:`.

**U2 The timing statistic in the rank rows and the one-sided t-test (O-5,
O-6, O-24; decisions 149, 150; DESIGN §11.1, §15.1, §16.1 step 6).**

Files:
- `src/discotrade/alerts.py` (new; the rank-row function of decision 149
  (a), registered `timing_gross`);
- `src/discotrade/daily.py` (`_rank_persistence` calls it, decision 149
  (b));
- `src/discotrade/stats.py` (the t upper-tail function of decision 150);
- `tests/fixtures/return_readers.toml`;
- `tests/test_stats.py` and `tests/test_rank_daily.py`, plus a new
  `tests/test_alerts.py` if the builder prefers it for the rank-row tests;
- any existing test that asserts a rank row's exact key set, changed only
  to admit `timing` and `gross` (O-24, decision 146 (c)).

Gate: `./scripts/check` green; the tests of decisions 149 (d) and 150
pass. Seen to fail, each made alone and reverted: the three wrong changes
of decision 149 (d), and decision 150's two-sided probability. Run
`./scripts/gate M1 G1.1` once at the unit's commit, one foreground call
with a 20-minute timeout. It prints PASS, and its output and wall time go
in the body beside mission 17 U5's 450 s. The unit's commit is `stats:`.

**U3 `persistent_approach` and `group_edge` on the exposure-adjusted
series (O-7, O-16, O-24; decision 151; DESIGN §15.1, §11.2 to §11.4).**

Files:
- `src/discotrade/alerts.py` (the two rules' figures and conditions, the
  bootstrap);
- `src/discotrade/paper.py`, only for decision 151 (b)'s members function,
  with `paper.portfolio`'s result unchanged;
- `tests/fixtures/return_readers.toml` (each new reader `adjusted`);
- `tests/test_alerts.py`, and `tests/test_portfolio.py` if the members
  function is added.

The two rules are functions of `D` and the state. They are not yet called
by the day loop; U4 wires them.

Gate: `./scripts/check` green; the tests of decision 151 (c) pass at the
production thresholds, each expected figure computed by the test. Seen to
fail, each made alone and reverted: the five wrong changes of decision 151
(c). The unit's commit is `alerts:`.

**U4 Alert state, payloads, the `rank_persistence` and `revival` rules,
health alerts, and the day loop's step 6 (decisions 152, 149 (c); DESIGN
§15.1 to §15.3, §16.1 step 6, §16.2; I-5, I-6, I-10, I-12).**

Files:
- `src/discotrade/alerts.py` (the state, the firing, the payloads, the two
  rules, the health alerts, the `few_valid_candidates` and `cost_stale`
  detectors, and the `no_finding` function, which the day loop does not
  call, decision 152 (e));
- `src/discotrade/daily.py` (step 6 in the order of decision 152 (f), on a
  new day only, into the staging directory);
- `src/discotrade/replay.py` and `src/discotrade/cli.py`, only as far as
  the day loop's new step needs;
- `tests/fixtures/return_readers.toml`;
- `tests/test_alerts.py`, `tests/test_daily.py`, and any existing test that
  lists a day's written files exactly, changed only to admit the alert
  state and payload paths (decision 146 (c)).

Gate: `./scripts/check` green; the tests of decision 152 (g) pass. Seen to
fail, each made alone and reverted: the four wrong changes of decision 152
(g). Run `./scripts/gate M1 G1.2` and `./scripts/gate M1 G1.3` once each at
the unit's commit, each its own foreground call with a 20-minute timeout.
Both print PASS, and their outputs and wall times go in the body (G1.2
beside mission 17 U5's 204 s). The unit's commit is `alerts:`.

**U5 The dashboard (O-6, O-14, O-16, O-18; decision 153; DESIGN §15.5,
§3; SPEC §13, §14).**

Files:
- `src/discotrade/dashboard.py` (new);
- `src/discotrade/daily.py` (step 7 writes the page into the staging
  directory, on a new day only);
- `src/discotrade/cli.py` (`discotrade dashboard` with `--out`);
- `src/discotrade/config.py`, only to read `config/gates.toml`;
- `config/gates.toml` (new: the two owner flags, both `false`, decision
  153 (b));
- `tests/fixtures/return_readers.toml` (the one `stage3_money` entry,
  `display` entries);
- `tests/test_return_readers.py` (`test_no_entry_is_stage3_money_yet`
  becomes the one-entry test, decision 153 (c));
- `tests/test_dashboard.py` (new);
- `tests/test_cli.py`;
- any existing test that lists a day's written files exactly, changed only
  to admit the page (decision 146 (c)).

Gate: `./scripts/check` green; the tests of decision 153 (d) pass. Seen to
fail, each made alone and reverted: the three wrong changes of decision 153
(d). The unit's commit is `dashboard:`.

**U6 The regression gates at the pushed tip (O-2, O-25; decisions 146 (a),
154 (c), (d); DESIGN §18.2).**
1. After U5 is pushed, run `./scripts/check` three times at that tip
   (three calls, each wall time kept), all green.
2. Run `discotrade sandbox build` (its tag kept).
3. Run, each as one foreground call with a 20-minute timeout at that same
   pushed tip, with no uncommitted file but the git-ignored drafts:
   - `./scripts/gate M1 G1.1`, `G1.2`, `G1.3` and `G1.4`;
   - `./scripts/gate M3`;
   - `./scripts/gate M2`;
   - `./scripts/gate M0`.
4. Keep each output verbatim with its wall time and `git rev-parse HEAD`.

Each prints its item PASS lines, and the whole-milestone runs print `gate
M3: PASS`, `gate M2: PASS` and `gate M0: PASS`. An item that prints FAIL,
or that does not finish within its call (O-2), is a defect:
- when it lies in a file a unit of this mission changed, that unit is taken
  again;
- when it would need a test of a met gate edited, decision 146 (b)
  applies;
- otherwise reply `VERDICT: mission 19 blocked U6` naming it.

An M1 item above 10 minutes, or any other item above 15, is a finding with
the times, never a reason to weaken it. The unit's commit is `meta:`. It
carries only two lines appended to `meta/findings/FINDINGS.md`: a D-013
times line with the three check runs, and a D-014 times line with the M1
item times beside mission 17 U5's (G1.1 450 s, G1.2 204 s, G1.3 542 s, G1.4
1 s) and the M3, M2 and M0 times. The outputs go to the report.

**U7 The final report (decisions 146 to 154; O-23 to O-25; DESIGN
§18.2).** Write `meta/FINAL-REPORT-19.md`, drafted under `meta/drafts/` and
moved in by this commit. The report gives:
- What changed, with the sha of each unit.
- `./scripts/check`'s wall times at the tip, beside mission 18's (917 to
  931 s).
- Under `## Gate`, the outputs of U6, verbatim, as regression gates
  (O-25): `### Gate M1` (the four items, each with its wall time beside
  mission 17 U5's), `### Gate M3`, `### Gate M2` and `### Gate M0`, each
  with the tip it ran at and its wall time.
- `## Owner rulings applied`: for each of O-23, O-24 and O-25, what was
  built, the unit and sha, and the test that holds it.
  - For O-23, quote the G1.3 line before and after.
  - For O-24, give the register entries before and after, and the rank
    row's keys before and after.
- `## Register`: every entry of `tests/fixtures/return_readers.toml` added
  or changed by this mission, with its class and the unit.
- `## Speed`: the seconds per replay day of the G1.3 scenario at mission
  18's tip and after each of U2, U4 and U5.
- What the tests prove.
- NOT PROVEN, which is mandatory. It covers:
  - that no finding alert fires on any replay a gate runs today, because
    the fixture models' cutoffs make every approach observation exposed
    (`meta/BACKLOG.md`; G4.2 is step S4.3's), so the rules are proven by
    their unit tests at the production thresholds and not by a replay;
  - that the bootstrap's quantile and the t-test are proven against the
    values the tests compute, not against an outside statistics package;
  - that the dashboard's readability on a phone is asserted by its
    viewport and single column, not by a device;
  - that `no_finding` is not called by the day loop (decision 152 (e));
  - that the speed figures are from the builder's machine;
  - what remains of FINAL-REPORT-18's NOT PROVEN, item by item.
- The findings filed and answered.
- A `## Review items` table, with one row each for REVIEW-18 notes 1 to
  10 and REVIEW-11 note 8: the item, its resolution (the unit and
  decisions item, or "stands", or the step that takes it, as decisions 153
  (c) and 154 say), and the sha where there is one.

Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 18's.
- At the pushed tip, with nothing uncommitted:
  - `./scripts/gate M1 G1.1` to `G1.4` each print their item PASS line;
  - `./scripts/gate M3`, `./scripts/gate M2` and `./scripts/gate M0` print
    `gate M3: PASS`, `gate M2: PASS` and `gate M0: PASS`;
  - every output, the tip's sha and every wall time are in the report.
- `table.json` keeps `S`, `E_N` and `excess` as G1.3 asserts them, and
  every row carries `adjusted_S`, `adjusted_E_N` and `adjusted_excess` as
  decision 148 says. The only change under `tests/gates/` is decision 148
  (d)'s line.
- `stats.rank_persistence` is unchanged. `stats.control_moments` gains only
  `column`, and gives today's result by default. New rank rows carry
  `timing` and `gross` beside `statistic`. No earlier row is rewritten.
- The register has no `pending` entry. The rank-row function is
  `timing_gross`, the rule functions and the table's new function are
  `adjusted`, there is exactly one `stage3_money` entry (the dashboard's),
  and `tests/test_return_readers.py`'s audit passes.
- Each finding rule is unit-tested on both sides of each production
  threshold, and each wrong change of decisions 148 to 153 turned a test
  red.
- The day loop writes `alerts/<track>/state.json`, the payloads and
  `dashboard/<track>/index.html` in the staging directory on a new day
  only, and a re-run of a finished day writes nothing.
- No file under `tests/fixtures/rejected/`, no record under
  `tests/fixtures/config/`, no entry of `tests/fixtures/config_frozen.json`
  and no value of a frozen configuration file changed in this mission.
  `config/gates.toml` is the one new file under `config/`.
- Every unit commit's body lists every file it touches. U0 is `plan:`, U1
  is `table:`, U2 is `stats:`, U3 and U4 are `alerts:`, U5 is
  `dashboard:`, and U6 is `meta:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no test builds the image.
- `meta/FINAL-REPORT-19.md` exists with `## Gate` (the four regression
  gates), `## Owner rulings applied`, `## Register`, `## Speed`, NOT
  PROVEN, and the review-items table.
