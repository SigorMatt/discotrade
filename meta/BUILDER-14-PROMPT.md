# BUILDER-14-PROMPT — discotrade mission 14: REVIEW-13's should-fix items, the check's run time, the W profile, anonymization, the registry, the prompt builder and the response parser (step S3.1)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 14. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-14.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 14 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-15-m14.md` (items 109 to 117, new for
this mission; every unit below cites them),
`meta/decisions/decisions-2026-10-15-owner.md` (the owner's; O-19, O-20 and
O-22 bind, O-19's rule on gate tests of a met milestone in particular),
`meta/decisions/decisions-2026-10-14-m13.md` (items 100 to 108; 101 to 105
are the code U1 hardens), `meta/decisions/decisions-2026-10-14-m12.md`
(items 91 to 99; 92 is the audit of return readers, 94 the static check's
tables the prompt lists), `meta/decisions/decisions-2026-10-13-owner.md`
(the owner's; O-16 to O-18 bind every new module; the rest is later
steps' and is read so that nothing built here contradicts it),
`meta/decisions/decisions-2026-10-14-m11.md` (items 83 to 90),
`meta/decisions/decisions-2026-10-14.md` (items 76 to 82; 80 is the method
of the speed figures), `meta/decisions/decisions-2026-10-12.md` (items 1
to 75 still bind), `DESIGN.md` (§13.1 to §13.4 are this mission, with
§4.1 for W, the cells and the horizons, §4.3 for the thresholds the prompt
reads, §5.6 for the adjusted series, §6 for the contract the prompt states,
§7.3 for the cost model, §10.3 for the states the registry reads, §12.1
and §12.2 for the static check and the error text, §12.4 and §19.3 L5 for
the probe U1 changes, §16.2 for the health log, §18.1 for the commit gate;
read §2 twice, in particular I-1, I-3, I-6, I-7, I-8, I-10, I-11, I-12 and
I-13), `meta/reviews/REVIEW-13.md` (its `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-13.md`, `meta/BACKLOG.md`, `meta/findings/FINDINGS.md`,
and `meta/CHECKPOINT.md` (a unit in progress means §R first). This is
roadmap step S3.1.

---

## Mission

Build roadmap step S3.1 as decisions 109 to 117 cut it. First take
REVIEW-13's six should-fix items and its notes 3, 4 and 5: the probe's
mount judged by content against the store, the backends' edges, and the
restart notice under I-6 (decisions 110 to 112), and file the findings of
decision 113. Then bring `./scripts/check` under 12 minutes without
dropping or changing a test (decision 114, finding D-013). Then build the
W profile (decision 115), anonymization and the registry (decision 116),
and the prompt builder and the response parser (decision 117). Then run
gate M2 once and gate M1 item by item at the pushed tip as a regression
check (decision 109 (b)). This mission does not close a milestone.
Providers, the pool, the coordinator, the day's generation, storing
responses, the call log and the M3 gate tests are step S3.2's (decision
109 (a)). Add nothing else. Where a cited decision changes what an
existing test asserts, the unit changes that assertion and says so in its
commit body; every other existing test stays unchanged in what it
asserts, and no file under `tests/gates/` changes. Finish with a report
whose first line the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 14
  finished` | `VERDICT: mission 14 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-15-m14.md`
and the items of the earlier decisions files and of the owner's files that
the unit names. No unit changes a value in a frozen file
(`config/instruments/`, `config/tracks/`, `config/calendars/`,
`config/thresholds.toml`, `tests/fixtures/config_frozen.json` entries that
already exist), and no unit changes a value of `config/run.toml` or
`tests/fixtures/config/run.toml`: a value believed wrong is a finding. No unit creates `config/models.toml`
(step S3.2's, decision 61). No unit changes an existing record under
`tests/fixtures/config/`; a unit that needs something new adds a new
fixture file and says so in its body, or builds a configuration under a
test's temporary directory. No unit changes any file under `tests/gates/`
(O-19: a gate test of a met milestone changes only by the owner's
decision naming it) or under `tests/fixtures/rejected/`. Where a unit's code
already exists and is right, so that a new test cannot be seen to fail first against the
parent, the sub-agent instead makes, in its worktree and without
committing it, the wrong change the test is meant to catch, sees the test
fail, reverts it, and names that change in the commit body. Each unit
names below the wrong changes its tests must be seen to fail on; these are
made and reverted the same way and named in the body.

Long commands (finding HF-006): every run of `./scripts/check` or
`./scripts/gate` is its own foreground Bash call with an explicit timeout
of 20 minutes, the tool's maximum; never chain two such runs in one call,
and never let one run in the background. Each sub-agent runs
`./scripts/check` three times before its commit, as three calls, and says
in its report how many runs were green, with the wall time of one run.
`./scripts/check` took about 870 s at mission 13's tip on the builder's
machine, with the `container` tests run; U2 brings it down (decision 114),
and every later unit adds as little as it can: a unit that adds more than
60 s to one run says so in its body with the tests that cost it; a run
above 15 minutes is a finding with the times (HF-006, HF-008, D-013),
never a reason to drop a test. Every sub-agent that runs a `container`
test first runs `discotrade sandbox build`, as its own foreground call
with a 20-minute timeout, so that the tests run and do not skip, and says
in its report that they ran and the tag.

Every test of this mission writes state and job directories only under a
pytest temporary directory, reads time only through a `FixedClock` or
`--as-of` (or the replay's clock, decision 72), and runs the `discotrade`
command in-process through the function the console script calls, except
where it tests the console script itself. A test that runs `git` passes
`GIT_ALLOW_PROTOCOL=file` in its environment and uses local paths only
(decision 47), and a new file that starts a subprocess is added to
`SUBPROCESS_FILES` in `tests/test_offline.py`. Every test that reads bars
or runs days does so on a synthetic source from `tests/fixtures/config/`
(`test_mixed` or `test_synth`), with every seed and date written in the
test file. Each rule is unit-tested at its production value from
`config/thresholds.toml`; a test may also use another value from a
configuration copied under its temporary directory, and says so. A test
that checks a figure computes the expected value itself, from the stored
bars, without calling the function under test. A test that starts a
container carries the `container` marker (decision 102 (g)), mounts only a
job directory under its temporary directory, and leaves no container
behind (it removes, by name, any its job left). The image is built only by
`discotrade sandbox build`, run as a setup step, never inside a test
(decision 102 (f)). Modules under `src/discotrade/workers/` import nothing
that reaches the network or a secret (I-11, I-13), and no test calls a
provider or a model.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S3.1, the statement that
this mission does not close a milestone and runs gate M2 and gate M1 item
by item again as decision 109 (b) says, and as carried items REVIEW-13
should-fix 1 and 2 (decision 110, U1), should-fix 3 and notes 3, 4 and 5
(decision 111, U1), should-fix 4 (decision 112, U1), should-fix 5 and 6
and notes 12 and 15 (decision 113, U0 and U6), and finding D-013 (decision
114, U2), each with the unit that takes it), rewrite `meta/CHECKPOINT.md`
for this mission, append to `meta/journal.md`, and append to
`meta/findings/FINDINGS.md`, after its last line and in its form, the
entries `D-014`, `D-015`, `HF-010` and `HF-011` of decision 113 and a
status line for D-013 naming decision 114. Nothing else. Gate: the four
files are committed and pushed in one `plan:` commit.

**U1 REVIEW-13's should-fix items 1 to 4 and notes 3 to 5: the mount
judged against the store, the backends' edges, the restart notice
(decisions 110, 111, 112; decisions 101, 103, 105; O-20, O-22 item 3;
DESIGN §5.6, §12.4, §16.2, §19.3 L5; I-6, I-7, I-12).**
`sandbox/probe.py`, `src/discotrade/sandbox/container.py`,
`src/discotrade/sandbox/process.py`, `src/discotrade/sandbox/runner.py`,
`src/discotrade/daily.py` (the notice only), `src/discotrade/cli.py` and
`src/discotrade/doctor.py` only as the self-test's new expectation needs,
new fixtures under `tests/fixtures/strategies/` as needed, and tests
(`tests/test_sandbox_probe.py`, `tests/test_sandbox_container.py`,
`tests/test_sandbox_process.py`, `tests/test_sandbox_runner.py`,
`tests/test_daily_sandbox.py`). The sub-agent runs `discotrade sandbox
build` after changing `probe.py` and `runner.py` and gives the new tag.
Gate: on the container backend, a probe run on `test_synth`'s W of a
fixed day reports each instrument's `last_close`, and every
`mount.<symbol>` finding passes against the expectation read from the
store (decision 110 (b)); a job built with its earliest context bar
dropped and the first bar after W added, same count, fails that
instrument's finding; `sandbox selftest` on a state with no bars fails its
mount findings and exits 1; `tests/gates/test_g2_3_probe.py` is unchanged
and passes (run as `./scripts/gate M2 G2.3`, its own call); a remaining
time of zero at the fork server's read gives `limit [wall_clock]` with
the server kept; a result whose `float` conversion raises is a `dry_run`
error; the runner's exception tuple equals the exception classes of
`builtins`; a removal that raises still ends the runtime client; a re-run
of a journaled day after the server was killed leaves the state's bytes,
the health log included, unchanged, and the notice is still written on a
day that is written. Seen to fail: the mounted last close not compared;
the store expectation replaced by the job's bars; `settimeout(0.0)`
reached again; the `float` conversion moved back outside the catch-all;
the notice written on the re-run. `./scripts/check` green.

**U2 `./scripts/check` under 12 minutes (decision 114; finding D-013;
HF-006, HF-008; DESIGN §18.1).** Test modules and `tests/conftest.py` as
the shared fixtures need, `src/discotrade/journal.py` for the
`trusted_hashes` cache only, and its test. No file under `tests/gates/`.
Gate: `pytest --collect-only -q -m "not gate and not network and not
live"` lists the same node ids at the unit's parent and at its commit
(the two counts and a diff of the lists, empty, in the body); the twenty
slowest tests (`--durations=20`) at the parent and at the commit, and
`./scripts/check`'s wall time at both, in the body; every changed test
file named with what it now shares and why no test's assertion moved; a
test shows the `trusted_hashes` cache hashing a file again after it
changes. Seen to fail: a shared fixture that a writing test mutates
without a copy (the test that reads it after goes red), made and reverted.
A run still above 12 minutes is recorded under D-013 with the durations.
`./scripts/check` green.

**U3 The W profile (decision 115; DESIGN §13.1, §4.1, §5.6, §6.2; I-1,
I-3, I-9, I-12).** `src/discotrade/workers/__init__.py` and
`src/discotrade/workers/profile.py` (new), and tests (a new
`tests/test_workers_profile.py`). Gate: every test decision 115 (e)
lists, on `test_synth` and `test_mixed`: the profile identical with and
without T's and later bars in the store; identical under a price constant
and a volume constant to a relative 1e-9; the same document for two cells
of one family and a difference only in the cell block across families; at
least one figure of each block, common and each of the six families',
equal to the test's own computation from the stored bars; `version` is
`p1`; no key or value of the document holds a date, a timestamp or a
symbol other than the instrument keys anonymization replaces. Seen to
fail: a return taken across W's first bar from a bar before W; one bar of
T read into the profile; the cell block keyed by the horizon.
`./scripts/check` green.

**U4 Anonymization and the registry (decision 116; DESIGN §13.2, §13.3,
§10.3, §4.1, §4.3; I-8, I-10).** `src/discotrade/workers/anonymize.py` and
`src/discotrade/workers/registry.py` (new), and tests (new
`tests/test_workers_anonymize.py` and `tests/test_workers_registry.py`).
Gate: every test decision 116 (c) lists; the labelling for a call id is
the same on two runs and differs between two call ids, with the seed rule
of 116 (a) checked by the test's own computation; the scaling function
leaves returns unchanged and scales a field the test lists; the registry
on a state built in the test (approaches admitted from fixture sources in
several cells, one dormant, one retired) holds exactly the expected lines
in order; the description cap read from the thresholds. Seen to fail:
Python's `hash` used for the seed; a retired approach listed; angle
brackets kept by the sanitizer. `./scripts/check` green.

**U5 The prompt builder and the response parser (decision 117; DESIGN
§13.4, §6, §7.3, §12.1, §12.2, §13.2; I-8, I-10, I-13).**
`src/discotrade/workers/prompt.py` and `src/discotrade/workers/parse.py`
(new), `tests/fixtures/return_readers.toml` only for an entry decision 92's
audit finds, and tests (new `tests/test_workers_prompt.py` and
`tests/test_workers_parse.py`). Gate: every test decision 117 (d) lists,
the leak check on prompts built for every cell of `test_synth` and
`test_mixed` with two call ids each and a registry holding fixture
descriptions; the five parts in order under their headings; the profile
rendered at 4 significant digits with `null` for a non-finite value; each
label's cost line equal to the test's own computation from the stored bars
and the instrument record. Seen to fail: a symbol left in a cost line;
`max_lines` written as a literal in `prompt.py` rather than read; the
parser taking the first block. `./scripts/check` green.

**U6 The gate runs and the final report (decisions 109, 113; DESIGN
§18.2).** After U5 is pushed and `./scripts/check` is green three times at
the tip (three calls, each wall time kept): `discotrade sandbox build`
(its tag kept), `./scripts/gate M2` as one foreground call, then
`./scripts/gate M1 G1.1`, `G1.2`, `G1.3` and `G1.4`, each its own
foreground call, every call with a 20-minute timeout, all at the same tip,
each output verbatim with its wall time; decision 109 (b) says what
follows a FAIL, an item above 10 minutes or an item that cannot finish.
Then write `meta/FINAL-REPORT-14.md` (drafted under `meta/drafts/`, moved
in by this commit). The report gives: what changed (sha per unit);
`./scripts/check` wall time at the base, after U2 and at the tip; the
outputs of the gate runs under `## Regression gates`, verbatim, with the
tip, the tag and their wall times beside mission 13's; a `## Profile`
section (the document's blocks and fields for `p1`, and its size in
bytes rendered for `test_synth`); a `## Prompt` section (one prompt built
for one cell of `test_synth`, verbatim, under a fence, and its length in
characters); for each of decisions 110 to 117, the test files and test
names that hold it; what the tests prove; `## Corrections to
FINAL-REPORT-13` (decision 113); NOT PROVEN (mandatory: that the profile's
statistics were chosen by decision 115 and whether they help a worker is
not tested; that anonymization cannot hide a distinctive path, DESIGN
§13.2's known limit; that the leak check covers the symbols, venues,
contract names and date patterns it lists and the texts the tests build,
and a description is the worker's own text, passed as data; that no prompt
has been sent to a model, which is step S3.2's and live check L3's; that
G2.3's gate file still judges the mount against the job, the content
check against the store being proven outside the gate until the owner
rules (decision 110 (d)); that the speed figures are from the builder's
machine; what remains of FINAL-REPORT-13's NOT PROVEN); the findings
filed and answered; and a `## Review items` table with one row each for
REVIEW-13 should-fix 1 to 6, notes 3, 4, 5, 12 and 15, and finding D-013:
the item, its resolution (the unit and decisions item), and the sha. Then
the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 13's.
- `./scripts/gate M2` and `./scripts/gate M1 G1.1` to `G1.4` at the pushed
  tip print their PASS lines; the outputs and times are in the report
  beside mission 13's, and any M1 item above 10 minutes is recorded under
  D-014.
- The probe's mount is judged by its count and its last close against the
  store, a W of no bars fails, and `sandbox selftest` and `doctor --live
  sandbox` use that judgement; a zero remaining time is a wall-clock limit,
  not a harness error; a re-run of a journaled day writes nothing, the
  health log included (REVIEW-13 should-fix 1 to 4).
- `pytest --collect-only` lists the same tests before and after U2, and
  no test's assertion changed in U2.
- The W profile reads W's bars only, holds no price or volume unit, no
  date and no symbol, and differs between cells only in its cell block;
  its version is `p1`.
- Labels and scaling come from a generator seeded by the call id; the
  registry lists live and dormant approaches of the cell and its
  neighbours with no score, its descriptions sanitized, capped and
  delimited as data.
- The prompt has the five parts of §13.4 in order, its caps read from the
  thresholds, its forbidden names from the static check and its indicator
  list from the library; no prompt the tests build contains a symbol, a
  venue, a contract name or a date; the parser takes the last Python
  block and the next non-empty line, and refuses the rest with a fixed
  text.
- No file under `tests/gates/` or `tests/fixtures/rejected/` changed; no
  value of a frozen file changed in this mission (`git diff` of
  `config/instruments/`, `config/tracks/`, `config/calendars/`,
  `config/thresholds.toml`, `config/run.toml`, of the existing entries of
  `tests/fixtures/config_frozen.json` and of the existing records under
  `tests/fixtures/config/` against the base is empty); and
  `config/models.toml` does not exist.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no file under `src/` names
  a market, a contract root or a venue; no test builds the image.
- `meta/FINAL-REPORT-14.md` exists with `## Regression gates`, `##
  Profile`, `## Prompt`, `## Corrections to FINAL-REPORT-13`, NOT PROVEN,
  and the review-items table.
