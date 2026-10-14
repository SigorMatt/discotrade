# BUILDER-13-PROMPT — discotrade mission 13: the container backend and its image, the probe, the hostile suite, approaches behind the sandbox in the day loop, and gate M2 (step S2.2)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 13. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-13.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 13 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-14-m13.md` (items 100 to 108, new for
this mission; every unit below cites them),
`meta/decisions/decisions-2026-10-14-m12.md` (items 91 to 99; 94 to 98 are
the code this mission hardens and builds on),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-1 to O-4,
O-11 to O-13 and O-16 to O-18 still bind; the rest is later steps' and is
read so that nothing built here contradicts it),
`meta/decisions/decisions-2026-10-14-m11.md` (items 83 to 90),
`meta/decisions/decisions-2026-10-14.md` (items 76 to 82; 80 is the method
this mission's speed figures use), `meta/decisions/decisions-2026-10-12.md`
(items 1 to 75 still bind; items 15, 19, 21 to 23, 44, 47, 48, 49, 63 and
72 are the ones this mission's code meets; item 48 is replaced by item 105
for the day loop), `DESIGN.md` (§12.4 and §12.5 are this mission, with
§18.1 to §18.3 for the `container` marker and gate M2, §19.3 for L5, §16.1
step 2 and §16.4 for the day loop and the replay; §12.1 to §12.3 for the
validation it runs, §6 for the strategy contract, §3 for the module layout
and `config/run.toml`, §13.2 for what an error text sent to a worker may
not hold; read §2 twice, in particular I-2, I-3, I-7, I-8, I-11, I-12,
I-13 and I-14), `meta/reviews/REVIEW-12.md` (its `## Should-fix` and
`## Notes`), `meta/FINAL-REPORT-12.md`, `meta/BACKLOG.md`,
`meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a unit in progress
means §R first). This is roadmap step S2.2.

---

## Mission

Build roadmap step S2.2 as decisions 100 to 108 cut it. This mission
closes milestone M2. First take REVIEW-12's four should-fix items and its
notes 2 and 3 (decision 101). Then build the container backend, its image
and `discotrade sandbox build`, with the `container` marker of §18.1
(decision 102); the probe, `discotrade sandbox selftest` and `discotrade
doctor --live sandbox` (decision 103); the hostile suite of §12.5 with its
rejection and containment passes (decision 104); and approach execution in
the day loop behind the sandbox, replacing decision 48's in-process path
(decision 105). Then write the gate tests of G2.1 to G2.4, run
`./scripts/gate M2`, and run gate M1 item by item and gate M0 again as a
regression check (decisions 100 (b), 106). Calling the validation
sequence from the day loop, the retry with the error text, workers, the
call log, gate G4.6 and where trusted sources live in an installed
package are later steps' (decision 107). Add nothing else. Where a cited
decision changes what an existing test asserts, the unit changes that
assertion and says so in its commit body; every other existing test stays
unchanged in what it asserts, and no existing file under `tests/gates/`
changes (the new `tests/gates/test_g2_*.py` files are added). Finish with
a report whose first line the playbook can match.

Before anything else, and only when `meta/CHECKPOINT.md` names no unit of
this mission done or in progress: run `docker version` and, if it fails,
`podman version`, each its own foreground Bash call with a timeout of two
minutes. When neither prints a server or engine version, change nothing
and reply `VERDICT: question no container runtime: <the commands and what
they printed>` (decision 100 (a)). This mission needs a working container
runtime; it never skips one.

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
- Your final reply begins with exactly one of: `VERDICT: mission 13
  finished` | `VERDICT: mission 13 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-14-m13.md`
and the items of the earlier decisions files and of
`meta/decisions/decisions-2026-10-13-owner.md` that the unit names. No unit
changes a value in a frozen file (`config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit creates `config/models.toml` (step
S3.2's, decision 61). No unit changes an existing record under
`tests/fixtures/config/` (the gate configuration is built under a test's
temporary directory with `tests/fixtures/config/thresholds_gate.toml`
copied in unchanged, decision 72), with one exception: U2 adds the new
`[sandbox]` keys of decision 102 (d) to `tests/fixtures/config/run.toml`
and `config/run.toml`, changing no existing value; a unit that needs
something else new adds a new fixture file and says so in its body. No
unit changes an existing file under `tests/gates/`; U6 adds the M2 gate
files. Only U5 changes `daily.py`'s execution of approaches (decision 105
replaces decision 48 there). No test runs a file under
`tests/fixtures/hostile/` through the subprocess or in-process backend, or
loads one with the decision-21 loader (decision 104 (d)). Where a unit's
code already exists and is right, so that a new test cannot be seen to fail first against the
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
Tests that `./scripts/check` runs replay a few days at most; the long
replays are the gate tests'. A validation or container test that
`./scripts/check` runs keeps its sandbox runs short: it may use a
configuration copied under its temporary directory with a shorter W, fewer
instruments or shorter limits, and says so, while at least one test of
each rule runs at the production thresholds on `test_synth`'s own W.
`./scripts/check` took about 590 s at mission 12's tip on the builder's
machine; with a runtime and the image present, the `container` tests run
in it too. A unit that adds more than 60 s to one run says so in its body
with the tests that cost it; a run above 15 minutes is a finding with the
times (HF-006, HF-008), never a reason to drop a test. Every sub-agent that
runs a `container` test first runs `discotrade sandbox build` (once U2 has
built it), as its own foreground call with a 20-minute timeout, so that
the tests run and do not skip, and says in its report that they ran.

Every test of this mission writes state and job directories only under a
pytest temporary directory, reads time only through a `FixedClock` or
`--as-of` (or the replay's clock, decision 72), and runs the `discotrade`
command in-process through the function the console script calls, except
where it tests the console script itself. A test that runs `git` passes
`GIT_ALLOW_PROTOCOL=file` in its environment and uses local paths only
(decision 47), and a new file that starts a subprocess is added to
`SUBPROCESS_FILES` in `tests/test_offline.py`. Every test that runs days
or builds a window runs on a synthetic source from `tests/fixtures/config/`
(`test_mixed` or `test_synth`), with every seed and date written in the
test file. Each rule is unit-tested at its production value from
`config/thresholds.toml`; a test may also use a lower value from a
configuration copied under its temporary directory, and says so. A test
that compares an adjusted figure computes the expected value itself, from
the evaluation's rows and the stored bars, without calling
`paper.adjusted`, `paper.adjusted_rows`, `paper.unit_bars`,
`paper.unit_returns` or `paper.average_positions`, as
`tests/test_exposure.py` does. A test that starts a container carries the
`container` marker (decision 102 (g)), mounts only a job directory under
its temporary directory, and leaves no container behind (it removes, by
name, any its job left). The image is built only by `discotrade sandbox
build`, run as a setup step, never inside a test (decision 102 (f)).

**U0 Plan (`plan:` commit).** After the runtime check above has passed,
write `meta/plan.md` (these units with checkboxes, the base commit, the
roadmap step S2.2, the statement `This mission closes milestone M2.`, that
it runs gate M1 item by item and gate M0 again as decision 100 (b) says,
the container runtime found with its version line, and as carried items
REVIEW-12 should-fix 1 to 4 and notes 2 and 3 (decision 101, U1),
REVIEW-12 notes 5 and 6 (decision 102, U2), the REVIEW-1 note on the
`container` marker (decision 102 (g), U2) and decision 48's in-process
path (decision 105, U5), each with the unit that takes it), rewrite
`meta/CHECKPOINT.md` for this mission, append to `meta/journal.md`, and
append to `meta/findings/FINDINGS.md` the HF-008 status line of decision
108. Nothing else. Gate: the four files are committed and pushed in one
`plan:` commit.

**U1 REVIEW-12's should-fix items: the runner's error texts and result
channel, the static check's order, determinism's sample (decision 101;
decisions 94, 95, 98; DESIGN §12.1, §12.2, §12.4, §13.2; I-1, I-8).**
`src/discotrade/sandbox/runner.py`, `src/discotrade/sandbox/process.py`
(only as the `no_result` error needs), `src/discotrade/validation/static.py`,
`src/discotrade/validation/sequence.py`, new fixtures under
`tests/fixtures/strategies/` as needed (none of them under
`tests/fixtures/hostile/`, which is U4's), and tests
(`tests/test_sandbox_runner.py`, `tests/test_sandbox_process.py`,
`tests/test_static_check.py`, `tests/test_validation_sequence.py`,
`tests/test_validation_grid.py`, and the shared error-text helper of
decision 101 (f) in a test module of its own). Gate: the reviewer's text
raising a class named from the data, and one returning an object of a
class named like a price, run through the runner past the static check,
give error texts holding neither name; a non-built-in class named
`ValueError` is named `an exception`; a text writing a forged result to
descriptor 1 and calling `os._exit(0)`, through the subprocess backend,
gives stage `dry_run`, rule `no_result`, not the forged targets, and what
a text prints still never reaches the result; `SystemExit` and
`KeyboardInterrupt` raised while loading and by a call give stages `load`
and `dry_run`; the three texts of REVIEW-12 should-fix 3 name `load`,
`_a` and `load`; a fake backend whose reverse job drops one sampled bar
makes `determinism` raise the harness error; every error-text test passes
run alone (`-k`) and in reverse order, and the helper finds `20190715`.
Seen to fail: `type(exc).__name__` put back in the error text; the result
written to descriptor 1 again; attributes ordered by the chain's start
again; the `called` check removed. `./scripts/check` green.

**U2 The container backend, its image and `discotrade sandbox build`
(decision 102; decisions 47, 95, 96, 97 (a), 98 (c); DESIGN §12.4, §3,
§18.1; I-7, I-11, I-13, I-14; REVIEW-12 notes 5 and 6).**
`src/discotrade/sandbox/container.py` (new), `src/discotrade/sandbox/base.py`
(only as the backend needs), `src/discotrade/config.py`,
`src/discotrade/cli.py` (the `sandbox build` subcommand), the image
definition and any file it copies under `sandbox/` (new), `config/run.toml`
and `tests/fixtures/config/run.toml` (the new keys only),
`tests/conftest.py` (the `container` marker and its skip rule),
`pyproject.toml` (the marker's registration only, if that is where markers
are registered), `tests/test_offline.py` (`SUBPROCESS_FILES` only), and
tests (a new `tests/test_sandbox_container.py`, and
`tests/test_sandbox_process.py` for the `run.toml` keys). The sub-agent
builds the image with `discotrade sandbox build` before running the
`container` tests; if the build cannot fetch its pinned inputs, it stops
and reports, and the orchestrator replies decision 100 (a)'s question.
Gate: every test decision 102 (g) lists, run on the container backend and
seen to run (pytest's summary shows no `container` test skipped); with
the runtime made unfindable (an empty `PATH` in a test) the backend raises
the harness error naming no runtime and a `container` test outside a gate
skips with its reason printed; with `DISCOTRADE_GATE=1` that skip fails;
`config.py` loads the new keys and refuses an unknown one naming it;
`config check` still passes on `config/` and on `tests/fixtures/config/`;
the image holds no `pyarrow` and no `httpx` (a `container` test asks the
image's Python); the body gives the base image's digest, the pinned
`numpy` and `pandas` versions beside `uv.lock`'s, the tag and the
runtime's version line. Seen to fail: `--network none` removed from the
options; the parent's environment passed to the container; the container
not removed after a wall-clock kill. `./scripts/check` green.

**U3 The probe, `discotrade sandbox selftest` and `discotrade doctor
--live sandbox` (decision 103; decisions 15, 19, 95 (a); DESIGN §12.4,
§18.3 G2.3, §19.3 L5; I-11, I-12).** `sandbox/probe.py` (new; an input of
the image's tag, so the sub-agent rebuilds the image),
`src/discotrade/sandbox/container.py` (running the probe with a job's
options), `src/discotrade/cli.py` (`sandbox selftest`),
`src/discotrade/doctor.py` (`--live sandbox`), and tests (a new
`tests/test_sandbox_probe.py`; `tests/test_doctor.py` or the file that
holds the doctor's offline tests). Gate: an `ast` test finds that the probe
imports only the standard library; on the container backend, a probe run
on the job of `test_synth`'s W of a fixed day reports no route, loopback
only and a failed connection, every create outside `/tmp` failed and the
one under `/tmp` succeeded, a non-zero user id and an empty effective
capability set, and per instrument the window's bars and context with no
bar after W's last day, the test counting the bars from the store itself;
`sandbox selftest` on that state prints one PASS line per finding and
exits 0; the judgement of decision 103 (b) fails each finding on a report
the test writes by hand with that finding wrong (a route, a writable root,
user id 0, a capability, a bar after W); with an empty `PATH`, `sandbox
selftest` and `doctor --live sandbox` exit 1 naming that no container
runtime was found and start nothing. Seen to fail: the probe started
without `--read-only` (a create under `/` succeeds); the job built for
W with one T bar added to the mount. `./scripts/check` green.

**U4 The hostile suite, its rejection pass and its containment pass
(decision 104; decisions 94, 98, 101, 102; DESIGN §12.5, §12.1, §12.2,
§12.4; I-7, I-14).** `tests/fixtures/hostile/` (new: one text per attack
and `manifest.toml`), `src/discotrade/sandbox/process.py` (leaving the
hostile files out of the sources it accepts),
`src/discotrade/validation/static.py` only if an attack needs a further
rule (each named in the body with its test), and tests (a new
`tests/test_hostile_suite.py`, marked `container` where it starts one).
Gate: the manifest covers §12.5's list held as a literal in the test, with
REVIEW-12's two attacks; the rejection pass of decision 104 (b) rejects
every file at its manifest stage, with the state directory's bytes and
`HEAD` unchanged, no ledger or `trials/` file created, the sentinel tree
unchanged, no container of the suite left, and a valid fixture still
passing afterwards in the same process; the containment pass of decision
104 (c) shows each run-time attack, past the static check, contained (an
error of stage `load`, `dry_run` or `limit`, or targets saying it failed;
no bar after W found in the mount); the subprocess backend refuses a
hostile file. A table in the body gives, per file, the attack, its stage
and rule, and the containment outcome. Seen to fail: the static rule for
`__import__`, or another the suite relies on, removed (the rejection pass
goes red); the container started without its process limit (the fork
bomb's containment goes red, the test bounded so that it cannot exhaust
the machine: the fork bomb's own count is capped in its text, above the
`pids` limit and far below the machine's). `./scripts/check` green.

**U5 Approaches in the day loop behind the sandbox (decision 105;
decisions 23, 44, 48, 49, 63, 72, 80; DESIGN §12.4, §16.1 step 2, §16.4,
§9.4; I-6, I-7, I-12).** `src/discotrade/daily.py`,
`src/discotrade/replay.py`, `src/discotrade/journal.py` (the recompute's
evaluation), `src/discotrade/cli.py` (the `--sandbox` option),
`src/discotrade/sandbox/base.py` and `src/discotrade/sandbox/process.py`
only as the day's jobs need (the fork server of decision 105 (e) only if
the measured speed calls for it), `tests/fixtures/return_readers.toml` only
for an entry decision 105 (f) adds, and tests (a new
`tests/test_daily_sandbox.py`; the existing tests of the day, the replay
and the recompute unchanged). Gate: decision 105 (a)'s byte-for-byte
comparison of the G1.3 scenario's first 30 calendar days at the parent
and at the commit, the command and its output in the body; every test
decision 105 (d) lists, the container one seen to run; the defaults of
decision 105 (b) on `test_synth` (`process`) and on a configuration
copied under the temporary directory holding a non-synthetic instrument
(`container`, and `process` refused, exit 2); no call of the decision-21
loader is left on the day loop's path (a test patches it to raise and a
replay of approaches still passes); the audit of decision 92 passes; the
body gives the seconds per replay day at the parent and at the commit,
the projected G1.3 time and, if it used the fork server, why. Seen to
fail: the approach's targets taken from the in-process loader again; a
`limit` error failing the whole day instead of retiring the approach;
`process` accepted on the non-synthetic configuration. `./scripts/check`
green.

**U6 The gate tests of M2 and the gate runs (decisions 106, 100 (b);
decisions 9, 40, 72; O-2, O-3; DESIGN §18.2, §18.3 M2).** New files
`tests/gates/test_g2_1_hostile.py`, `tests/gates/test_g2_2_duplicate.py`,
`tests/gates/test_g2_3_probe.py` and `tests/gates/test_g2_4_sequence.py`
(and a helper module under `tests/gates/` if they share one, holding no
seed, date or assertion of an item, as `tests/gates/m1_harness.py` does);
no existing file under `tests/gates/` changes. Each test asserts what its
item of §18.3 says, as decision 106 (b) to (e) reads it, and no less.
Gate: after U5 is pushed and `./scripts/check` is green three times at
the tip (three calls, each wall time kept), run `discotrade sandbox build`
(its tag kept), then `./scripts/gate M2` as one foreground call with a
20-minute timeout, and keep its output verbatim with its wall time; it
prints `G2.1` to `G2.4 PASS` and `gate M2: PASS`. Then run `./scripts/gate
M1 G1.1`, `G1.2`, `G1.3` and `G1.4`, each its own foreground call with a
20-minute timeout, and `./scripts/gate M0` once the same way, all at the
same tip, each output verbatim with its wall time. Decision 100 (b) says
what follows a FAIL, an item above 10 minutes, or an item that cannot
finish in its call; decision 106 (f) says what follows an M2 item above
10 minutes or an M2 run above 15. Seen to fail, each made in the worktree
and reverted, with the item that went red: G2.1 with one manifest stage
changed to another; G2.2 with the correlation compared without the
absolute value; G2.3 with the probe's mount given one bar after W; G2.4
with the grid choosing on the plain Sharpe. The image of the tip's tag is
left built. The unit's commit is `gate:` and carries only the new gate
files; the outputs go to the report.

**U7 The final report (decision 100; DESIGN §18.2).** Write
`meta/FINAL-REPORT-13.md` (drafted under `meta/drafts/`, moved in by this
commit). The report gives: what changed (sha per unit);
`./scripts/check` wall time at the base and at the tip; the output of
`./scripts/gate M2` under a heading `## Gate M2`, verbatim, with the tip it
ran at and its wall time; the outputs of the four `./scripts/gate M1
G1.<n>` calls (under `## Gate M1`) and of `./scripts/gate M0` (under `## M0
still passes`), verbatim, with their wall times beside mission 12's; an
`## Image` section (the runtime and its version line, the base image's
digest, the `numpy` and `pandas` versions beside `uv.lock`'s, the tag the
gate ran with); a `## Hostile suite` table (per file: the attack, the
stage and rule that rejected it, its containment outcome, and the test);
a `## Probe` section (each finding of the gate's probe run); a `## Day
loop` section (the backend defaults, the seconds per replay day before and
after, and whether the fork server was built); for each of decisions 101
to 106, the test files and test names that hold it; what the tests prove;
NOT PROVEN (mandatory: that the container is a boundary only as the
runtime, its configuration and the kernel of the builder's machine make
it, shown on that machine only, and on the server only by the owner's
live check L5; that the hostile suite is a floor and the static list with
it; that the call-time limits are measured inside the container and
depend on machine load, so a validation verdict on them can differ
between runs; that the base image and the two packages were fetched by
their pins and not otherwise verified; that a whole-number price in an
error text is not detected by pattern; that the subprocess backend is not
a boundary and runs only repository sources; that the grid's adjusted
figure on W discards a steady-position edge, as O-4's "Known and not
proven" says; that nothing calls the validation sequence from the day loop
until step S3.2; that the speed figures are from the builder's machine;
what remains of FINAL-REPORT-12's NOT PROVEN); the findings filed and
answered; and a `## Review items` table with one row each for REVIEW-12
should-fix 1, 2, 3 and 4, REVIEW-12 notes 2, 3, 5 and 6, the REVIEW-1 note
on the `container` marker, and decision 48's in-process path: the item,
its resolution (the unit and decisions item), and the sha. Then the
verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped.
- `./scripts/gate M2` at the pushed tip, with the container backend really
  running, prints `G2.1` to `G2.4 PASS` and `gate M2: PASS`; its output and
  time are in the report.
- `./scripts/gate M1 G1.1` to `G1.4`, each run on its own at the pushed
  tip, print their item PASS line, and `./scripts/gate M0` prints `G0.1`
  to `G0.4 PASS` and `gate M0: PASS`; the outputs and times are in the
  report beside mission 12's, and any item above 10 minutes has its
  finding.
- No error text names a type a submission chose; the runner's result
  cannot be written by the text; the static check names the first
  offending attribute in source order; determinism checks the bars the
  reverse job called; the error-text tests pass alone and in any order
  (REVIEW-12 should-fix 1 to 4, notes 2 and 3).
- The container backend runs each job in its own container with no
  network, a read-only root, a `/tmp` tmpfs, a non-root user, no
  capabilities, no new privileges and the process, memory, CPU and
  wall-clock limits, mounts only the job's input directory read-only,
  passes no key, removes the container after every run, and enforces the
  call-time limits; its targets equal the in-process runner's on the
  reference strategies; the image holds the runner, the indicator library
  and the probe with pinned `numpy` and `pandas` and nothing else, and its
  tag changes with its inputs.
- The probe, through the container backend, reports no route, a read-only
  root, a non-root user without capabilities, and a mount holding W's bars
  and no later bar; `sandbox selftest` and `doctor --live sandbox` refuse
  clearly without a runtime.
- Every attack of §12.5, with REVIEW-12's two, is rejected at its manifest
  stage on the container backend, and each run-time attack is contained
  past the static check; none produces a trial, changes a file outside its
  scratch space or stops the harness; no hostile file runs outside a
  container.
- The day loop, the replay and `journal recompute` run approaches only
  through a sandbox backend, `process` by default on synthetic tracks and
  refused elsewhere, `container` otherwise; the journal is unchanged byte
  for byte on the G1.3 scenario's first 30 days; a job error retires the
  approach and a harness error fails the day.
- No existing file under `tests/gates/` changed; no value of a frozen file
  changed in this mission (`git diff` of `config/instruments/`,
  `config/tracks/`, `config/calendars/`, `config/thresholds.toml`, of the
  existing entries of `tests/fixtures/config_frozen.json` and of the
  existing records under `tests/fixtures/config/` other than `run.toml`
  against the base is empty); the two `run.toml` changed only by the new
  keys of decision 102 (d); and `config/models.toml` does not exist.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no file under `src/` names
  a market, a contract root or a venue; no test builds the image.
- `meta/FINAL-REPORT-13.md` exists with `## Gate M2`, `## Gate M1`, `## M0
  still passes`, `## Image`, `## Hostile suite`, `## Probe`, `## Day
  loop`, NOT PROVEN, and the review-items table.
