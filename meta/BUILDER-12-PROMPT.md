# BUILDER-12-PROMPT — discotrade mission 12: the static check, the sandbox with its runner and two backends, the validation sequence with the grid on W, and the correlation gate (step S2.1)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 12. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-12.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 12 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-14-m12.md` (items 91 to 99, new for this
mission; every unit below cites them),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-17, O-16
and O-18 are this mission, O-1 to O-4 and O-11 to O-13 still bind; the
rest is later steps' and is read so that nothing built here contradicts
it), `meta/decisions/decisions-2026-10-14-m11.md` (items 83 to 90; 84, 86
and 89 are the ones this mission's code meets),
`meta/decisions/decisions-2026-10-14.md` (items 76 to 82; 81 is the one
this mission's code meets), `meta/decisions/decisions-2026-10-12.md`
(items 1 to 75 still bind; items 21 to 25, 30, 36, 37, 39, 40, 44, 47, 48,
62 and 63 are the ones this mission's code meets), `DESIGN.md` (§12.1 to
§12.4 are this mission; §6 for the strategy contract, §7 and §8 for the
evaluation, the returns and the metrics, §4.1 for W, §3 for the module
layout and `config/run.toml`, §13.2 for what an error text sent to a
worker may not hold; read §2 twice, in particular I-2, I-3, I-7, I-8,
I-10, I-11, I-12 and I-13), `meta/reviews/REVIEW-11.md` (its `##
Should-fix` and `## Notes`), `meta/FINAL-REPORT-11.md`, `meta/BACKLOG.md`,
`meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a unit in progress
means §R first). This is roadmap step S2.1.

---

## Mission

Build roadmap step S2.1 as decisions 91 to 99 cut it. First take
REVIEW-11's should-fix item with the audit widened (decision 92) and
answer finding D-010 (decision 93). Then build the static check of §12.1
(decision 94); the sandbox interface, the job and the runner, with the
in-process backend and decision 44's fresh load per instrument (decision
95); and the subprocess backend with `config/run.toml` (decision 96). Then
the validation sequence: the dry run and the grid on W, fixing its
combination on the exposure-adjusted net Sharpe at 1x and recording both
measures (O-17; decision 97), with its reader registered as O-18 says;
then determinism, activity and the correlation gate of §12.3, and the five
stages run in order (decision 98). Then run gate M1 item by item and gate
M0 again as a regression check (decision 91). This mission closes no
milestone. The container backend, its image, the probe, the hostile suite
and moving approach execution in the day loop behind the sandbox are step
S2.2's; writing the grid and the W figures to a trial row and the retry
with the error text are step S3.2's (decision 99). Add nothing else. Where
a cited decision changes what an existing test asserts, the unit changes
that assertion and says so in its commit body; every other existing test
stays unchanged in what it asserts, and no file under `tests/gates/`
changes. Finish with a report whose first line the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 12
  finished` | `VERDICT: mission 12 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-14-m12.md`
and the items of the earlier decisions files and of
`meta/decisions/decisions-2026-10-13-owner.md` that the unit names. No unit
changes a value in a frozen file (`config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit creates `config/models.toml` (step
S3.2's, decision 61). No unit changes an existing record under
`tests/fixtures/config/` (the gate configuration is built under a test's
temporary directory with `tests/fixtures/config/thresholds_gate.toml`
copied in unchanged, decision 72); a unit that needs something new adds a
new fixture file and says so in its body (U4 adds
`tests/fixtures/config/run.toml`, decision 96). No unit changes a file
under `tests/gates/`. No unit changes `daily.py`'s execution of approaches
(decision 48 holds until step S2.2). Where a unit's code already exists
and is right, so that a new test cannot be seen to fail first against the
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
replays are the gate tests'. A validation test that `./scripts/check` runs
keeps its sandbox runs short: it may use a configuration copied under its
temporary directory with a shorter W or fewer instruments, and says so,
while at least one test of each stage runs at the production thresholds
on `test_synth`'s own W. `./scripts/check` took about 490 s at mission 11's
tip on the builder's machine; a unit that adds more than 60 s to one run
says so in its body with the tests that cost it.

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
`tests/test_exposure.py` does.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S2.1, the statement that
this mission closes no milestone and runs gate M1 and gate M0 again as
decision 91 says, and as carried items REVIEW-11 should-fix 1 (decision
92, taken by U1), REVIEW-11 note 7's list subscript and `replay._adjusted`
(decision 92, U1), finding D-010 (decision 93, U1), finding D-006
(decision 44, U3) and owner decision O-17 (U5), each with the unit that
takes it), rewrite `meta/CHECKPOINT.md` for this mission, append to
`meta/journal.md`, and append to `meta/findings/FINDINGS.md` two status
lines in the form the file already uses: D-010 `answered
meta/decisions/decisions-2026-10-14-m12.md (item 93)` and D-006 `taken by
mission 12 U3 (decision 44; meta/decisions/decisions-2026-10-14-m12.md
item 95)`. Nothing else. Gate: the four files are committed and pushed in
one `plan:` commit.

**U1 The widened audit, REVIEW-11 should-fix 1 and finding D-010
(decisions 92, 93; decisions 62, 87, 89; O-13, O-18).**
`tests/test_return_readers.py`, `tests/fixtures/return_readers.toml`,
`src/discotrade/ledger.py` and `tests/test_ledger.py` (and any other test
file whose rows decision 93 changes, each named in the body). Gate: the
audit reads the six string constants anywhere in a function body;
`cli._backtest_result` is registered `display` and `replay._adjusted`
`producer`; every function the widened audit finds is registered, the
body listing each new entry with its class and note; the audit passes;
`ledger.append` refuses a lifecycle row of reason `admitted`, `displaced`,
`dormant` or `returned` without both figures, and a trial row without
both `adjusted_t` and `adjusted_w`, and still refuses one figure alone and
a figure on a row of another reason; a ledger file holding a line written
before (without the figures) is still appended to, its earlier bytes a
prefix of the new file. Seen to fail: the `cli._backtest_result` entry
removed; a function holding `"net_1x"` only in a tuple of a generator
added in the worktree; `ledger.append` accepting a `dormant` row without
`plain`. `./scripts/check` green.

**U2 The static check (decision 94; DESIGN §12.1; R-24; I-10).**
`src/discotrade/validation/__init__.py`,
`src/discotrade/validation/static.py` and tests (a new
`tests/test_static_check.py`). Gate: one test per rule of §12.1, each with
a text that breaks only that rule and is refused naming it, at the
production thresholds: a text that does not parse; `max_lines` + 1
physical lines (and `max_lines` passing); no `PARAMS`, `PARAMS` assigned
twice, `max_params` + 1 entries, a non-string key, a non-numeric value, a
`bool` value, `-1.5` accepted; a `GRID` that is not a dict of lists, a
`GRID` key outside `PARAMS`, too many keys, too many values, a non-numeric
value; no `def position(bars, params)`, a default, a third parameter,
`*args`; each refused import form and each accepted one of decision 94
(e); a class, a decorator, `global`, `nonlocal`, `async def`, `await`,
`yield`, `yield from`, `with`; an underscore name, an underscore attribute
(`__class__`) and an underscore parameter; each forbidden name of §12.1
used as a name, a parameter and a keyword argument; each forbidden
attribute; an attribute beginning `read_` and one beginning `to_`, with
`to_numpy` accepted. A text breaking two rules is refused naming the
earlier rule in §12.1's order. Every file under `reference/`, and
`tests/fixtures/strategies/cheat_lookahead.py`,
`tests/fixtures/strategies/roll_probe.py`,
`tests/fixtures/strategies/valid_bound.py` and
`tests/fixtures/strategies/valid_import.py`, pass. The thresholds are read
from the configuration (a test with a copied configuration whose
`max_lines` is lower refuses a text the production value accepts, said
so). Seen to fail: the underscore rule applied to names only and not to
attributes; `from numpy.random import default_rng` accepted;
`max_lines` counted with `len(source.split("\n"))` on a text ending with
a newline, if the test can tell the two apart, else named as not
applicable in the body. `./scripts/check` green.

**U3 The sandbox interface, the job, the runner and the in-process
backend (decision 95; decisions 22, 23, 24, 36, 37, 44; DESIGN §12.4,
§6.2, §5.6; I-2, I-7; finding D-006).** `src/discotrade/sandbox/__init__.py`,
`src/discotrade/sandbox/base.py`, `src/discotrade/sandbox/runner.py`,
`src/discotrade/sandbox/inprocess.py` and tests (new
`tests/test_sandbox_runner.py`, `tests/test_sandbox_job.py`). The runner
is exercised in-process in this unit (its `main` called on a job
directory the test writes); the subprocess backend is U4's. Gate: the
runner's imports are the standard library, `numpy`, `pandas` and
`discotrade.indicators` only (an `ast` test); its targets equal, exactly,
those of `backtest.evaluate` for `reference/trend_ma.py`,
`reference/zscore_reversal.py` and `reference/hour_of_day.py` on every
instrument of `test_mixed` over a window holding a SYNA roll, for two
parameter sets in one job; its result check agrees with
`strategy.check_result` on a table of values (an int, a float, `-0.0`,
`1.0`, `1.0000001`, `nan`, `inf`, a `bool`, a string, `None`, a numpy
float, a negative value on an instrument without shorting); a text that
raises while loading, one with no callable `position`, one whose call
raises and one returning `2.0` each give their stage with an error text
under decision 95 (e); `cheat_lookahead.py` through the runner on every
instrument of `test_mixed` gives, for each instrument, the targets of that
instrument evaluated alone (D-006), and the same test with the text loaded
once for all instruments (the wrong change) differs, made in the worktree
and reverted; a job built for W of a day `D` on `test_synth` holds no bar
whose trading date is after W's last day and holds the context decision
23 gives; mode `reverse_sample` gives, for the bars it is given, the
targets of mode `positions`; the in-process backend runs a function
object and refuses a job carrying source text. Seen to fail: prices in the
slice adjusted as of the window's last bar instead of the slice's last
bar; the text loaded once per job instead of per parameter set and
instrument; a bar of T placed in a W job. `./scripts/check` green.

**U4 The subprocess backend and `config/run.toml` (decision 96; DESIGN
§12.4, §3; I-7, I-11, I-13; decision 47).**
`src/discotrade/sandbox/process.py`, `src/discotrade/config.py`,
`config/run.toml` (new), `tests/fixtures/config/run.toml` (new),
`tests/test_offline.py` (`SUBPROCESS_FILES` only) and tests (a new
`tests/test_sandbox_process.py`). Gate: the backend runs the runner in a
child process and returns, for `reference/trend_ma.py` on `test_mixed`,
the targets the in-process runner gives; it refuses a source text whose
sha256 matches no file under `reference/` or `tests/fixtures/`, naming
the rule; an endless loop is killed at the wall-clock limit and returns
stage `limit`, the harness going on (a fixture with a short limit from a
copied `run.toml`, said so; this and the slow fixture of U5 are the only
tests that meet elapsed time, and they assert the stage, never a measured
time, I-12); an output over the cap returns `limit`; a
memory bomb returns `limit` or a `dry_run` error, never a harness failure;
the child's environment holds no variable outside the allow-list (a test
sets a fake key variable in the parent and finds it absent in the
child); `config.py` loads `run.toml`, refuses an unknown key naming it,
and job building refuses a configuration without `run.toml`, naming it;
`config check` still passes on `config/` and on `tests/fixtures/config/`.
Every fixture the unit adds that a test runs through this backend lives
under `tests/fixtures/` (for example `tests/fixtures/strategies/`). Seen
to fail: the sha256 check removed; the parent's environment passed to the
child unchanged; the wall-clock kill skipped (the test's own timeout
showing the hang, the test bounded so that it cannot hang
`./scripts/check`). `./scripts/check` green.

**U5 The dry run and the grid on W, on the exposure-adjusted measure
(O-17, O-4, O-18; decisions 97, 81, 86 (a), 89, 23, 25, 30; DESIGN §12.2
stage 2, §4.1, §8; R-23).** `src/discotrade/paper.py` (`adjusted_rows`
and the shared private function), `src/discotrade/validation/sequence.py`
(new), `tests/fixtures/return_readers.toml`,
`tests/test_return_readers.py` (the call check of decision 97 (c) and its
case), new strategy fixtures under `tests/fixtures/strategies/` as needed,
and tests (a new `tests/test_validation_grid.py`). Gate: every existing
test of `tests/test_exposure.py` passes unchanged; the combinations come
in decision 97 (a)'s order for a `GRID` of two keys; a combination whose
call returns a value out of range fails stage `dry_run` with an error
text under decision 95 (e); on `test_synth`'s W of a fixed day, with a
fixture whose `GRID` holds a long-leaning and a short-leaning value, the
grid fixes the combination with the greatest adjusted Sharpe at 1x where
the plain Sharpe at 1x would fix another, both figures computed in the
test from the evaluation rows and the stored bars; a tie fixes the first
in order, and a grid of figures that are all not a number fixes the first;
the result's `grid`, `metrics_w` and `adjusted_w` have decision 97 (e)'s
shapes and values equal to the test's own computation (under decision
39's rule); the call-time limits are not enforced by the in-process and
subprocess backends (a slow fixture passes stage 2 on the subprocess
backend within its wall-clock limit) and are enforced by a fake backend
that says it enforces them (a recorded p95 above `call_p95_ms` and a call
above `call_max_ms` each fail, at the production values); the function
that fixes the combination is registered `adjusted`, `paper.adjusted_rows`
`producer`, every other new entry named in the body; the audit passes, and
an `adjusted` entry that calls neither `paper.adjusted` nor
`paper.adjusted_rows` fails it. Seen to fail: the grid choosing on the
plain Sharpe; `hbar_i(W)` taken over the context bars as well as the
window bars; the tie going to the last combination; `paper.adjusted`
computing the subtraction outside the shared private function, if the
test can see it, else named as not applicable. `./scripts/check` green.

**U6 Determinism, activity, the correlation gate and the sequence
(decision 98; decisions 25, 63, 95 (e); DESIGN §12.2 stages 1, 3, 4 and
5, §12.3; R-1).** `src/discotrade/validation/sequence.py`,
`src/discotrade/validation/correlation.py` (new), new strategy fixtures
under `tests/fixtures/strategies/` as needed, and tests (new
`tests/test_validation_sequence.py`, `tests/test_correlation.py`). Gate,
on the subprocess backend unless a test says otherwise: a fixture that
keeps state between calls (a module-level list it appends to) passes the
static check and fails stage `determinism` through the reverse sample;
the sample is drawn as decision 98 (a) says (a test pins, for one text,
the bars sampled); a fixture with fewer than `min_changes_w` position
changes on W fails stage `activity`, and one with exactly
`min_changes_w` passes, at the production value; with an approach
admitted from `reference/trend_ma.py` in the state, its sign-flipped
duplicate (a new fixture) fails stage `correlation` naming that
approach's id, and a fixture whose absolute correlation with it is below
`corr_max` passes, both correlations computed in the test from the two
series; a dormant approach is compared and a retired one is not; a pair
with zero deviation is not a duplicate; with two approaches over the
limit, the one with the larger absolute correlation is named; the full
sequence on a valid fixture passes every stage and returns decision 97
(e)'s result; each of the five stages fails on a fixture built to fail it
and stops there, returning that stage and an error text; every error text
these fixtures produce holds no instrument symbol, venue or contract of
`config/` or `tests/fixtures/config/` and no date or timestamp (decision
95 (e)); the sequence writes nothing to the state directory (its bytes and
`HEAD` unchanged). Seen to fail: the correlation compared without the
absolute value; a retired approach compared; the second determinism run
reusing the first job's result instead of a new job; the activity count
taken per instrument instead of summed. `./scripts/check` green.

**U7 Gate M1 and gate M0 as a regression check, and the final report
(decision 91; O-2, O-3).** After U6 is pushed and `./scripts/check` is
green three times at the tip (three calls, each wall time kept), run
`./scripts/gate M1 G1.1`, `G1.2`, `G1.3` and `G1.4`, each its own
foreground call with a 20-minute timeout, all at that tip, then
`./scripts/gate M0` once the same way; keep each output verbatim with its
wall time. If an item prints FAIL, decision 91 says what follows. If an
item passes above 10 minutes, file decision 91's finding (the next free
`D-###`) in a `findings:` commit of `meta/findings/FINDINGS.md` only, and
weaken nothing. If an item cannot finish within its 20-minute call, do not
start it again in the background: reply `VERDICT: question` naming the
times measured. Then write `meta/FINAL-REPORT-12.md` (drafted under
`meta/drafts/`, moved in by this commit). The report gives: what changed
(sha per unit); `./scripts/check` wall time at the base and at the tip;
the outputs of the four `./scripts/gate M1 G1.<n>` calls (under a heading
`## Gate M1`) and of `./scripts/gate M0` (under `## M0 still passes`),
verbatim, with the tip they ran at and their wall times beside mission
11's; a `## Register` section listing every entry added or changed in
`tests/fixtures/return_readers.toml` in this mission with its class and
note, and the count by class; a `## Validation` section naming, for each
of the five stages, the fixture that fails it and the test that shows it,
and the fixture that passes them all; for each of decisions 92 to 98, the
test file and test names that hold it; what the tests prove; NOT PROVEN
(mandatory: that the subprocess backend is not a security boundary and
the container backend, the probe and the hostile suite are step S2.2's;
that the static check's list is a floor, pinned against attacks only by
step S2.2's hostile suite; that call-time limits are enforced only by the
container backend, so no call time was enforced in this mission; that the
grid's adjusted figure on W discards a steady-position edge, as O-4's
"Known and not proven" says; that the audit sees only the shapes it scans;
that approaches still run in-process in the day loop until step S2.2;
that the speed figures are from the builder's machine; what remains of
FINAL-REPORT-11's NOT PROVEN); the findings filed and answered; and a
`## Review items` table with one row each for REVIEW-11 should-fix 1,
REVIEW-11 note 7 (the list subscript and `replay._adjusted`), finding
D-010, finding D-006 and owner decision O-17: the item, its resolution
(the unit and decisions item), and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M1 G1.1` to `G1.4`, each run on its own at the pushed
  tip, print their item PASS line, and `./scripts/gate M0` prints `G0.1`
  to `G0.4 PASS` and `gate M0: PASS`; the outputs and times are in the
  report beside mission 11's, and any item above 10 minutes has its
  finding.
- The static check refuses each rule of §12.1 naming it, in §12.1's
  order, at the production thresholds, and passes every reference
  strategy.
- The runner's targets equal `backtest.evaluate`'s on the reference
  strategies; each instrument and parameter set gets a freshly loaded
  text (D-006); a W job holds no later bar; no error text sent toward a
  worker holds a symbol, venue, contract, date or timestamp.
- The subprocess backend accepts only repository sources, enforces the
  wall-clock limit and the output cap, and passes no key to the child.
- The grid fixes its combination on the exposure-adjusted net Sharpe at
  1x on W, records both measures for every combination, and its function
  is registered `adjusted` and calls `paper.adjusted_rows`;
  `paper.adjusted` returns what it returned before.
- Each of the five stages fails on its fixture with its stage and an
  error text, and a valid fixture passes all five; the sequence writes
  nothing to the state directory.
- `tests/fixtures/return_readers.toml` registers every function the
  widened audit finds, `cli._backtest_result` included; the audit passes;
  exactly three entries carry `pending`.
- `ledger.append` requires decision 87's and 86 (d)'s figures on new rows
  (D-010); no earlier ledger line is rewritten (I-5).
- No file under `tests/gates/` changed; no value of a frozen file changed
  in this mission (`git diff` of `config/instruments/`, `config/tracks/`,
  `config/calendars/`, `config/thresholds.toml`, of the existing entries
  of `tests/fixtures/config_frozen.json` and of the existing records under
  `tests/fixtures/config/` against the base is empty); the only new files
  under `config/` and `tests/fixtures/config/` are the two `run.toml`; and
  `config/models.toml` does not exist.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no file under `src/` names
  a market, a contract root or a venue.
- `meta/FINAL-REPORT-12.md` exists with `## Gate M1`, `## M0 still
  passes`, `## Register`, `## Validation`, NOT PROVEN, and the
  review-items table.
