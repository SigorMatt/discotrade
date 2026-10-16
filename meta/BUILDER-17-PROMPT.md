# BUILDER-17-PROMPT — discotrade mission 17: workers in the day loop, scoring on T, the worker corpus and gate M3 (step S3.2b)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 17. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-17.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 17 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-16-m17.md` (items 132 to 140, new for
this mission; every unit below cites them),
`meta/decisions/decisions-2026-10-16-m16.md` (items 127 to 131; 128 the
worker key, 131 (b) and (c) the two REVIEW-15 notes left to this step),
`meta/decisions/decisions-2026-10-16-m15.md` (items 118 to 126; 118 the
split of the step, 122 the providers, 124 the pool, 125 the coordinator,
126 the generation, all called by the day here),
`meta/decisions/decisions-2026-10-15-m14.md` (items 109 to 117),
`meta/decisions/decisions-2026-10-15-owner.md` (the owner's; O-19, O-20 and
O-22 bind, O-19's rule on gate tests of a met milestone in particular),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-11, O-13 and
O-16 to O-18 bind: scoring on T reads the exposure-adjusted figures and
records both measures), `meta/decisions/decisions-2026-10-14-m13.md` (items
100 to 108), `meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still
bind), `DESIGN.md` (§16.1 to §16.4 for the day and the replay, §13 for the
workers, §14 for the coordinator, §10.2 and §10.3 for the ledgers and
admission, §7.1 and §8 for scoring a window, §11.3 for the cutoff, §12.2 to
§12.4 for validation and the sandbox, §15.2 for the health events, §17 for
the synthetic market, §18.2 and §18.3 (M3) for the gate, §19.3 L3; read §2
twice, in particular I-3, I-5, I-6, I-7, I-8, I-11, I-12 and I-13),
`meta/reviews/REVIEW-16.md` (its `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-16.md`, `meta/BACKLOG.md`, `meta/findings/FINDINGS.md`,
and `meta/CHECKPOINT.md` (a unit in progress means §R first). This is
roadmap step S3.2b.

---

## Mission

Build step S3.2b as decisions 132 to 140 say. This mission closes
milestone M3. First file the findings lines of decision 134 (e) and (f).
Then score a generated candidate on T with the exposure-adjusted figures
and both measures recorded (decision 135). Then call the generation of
step S3.2a from the day: daily steps 3 to 5 in `run_day` (decision 136).
Then give `run-day` and `replay` their provider and coordinator options,
with the scripted provider's cursor built from the stored responses
(decision 137). Then write the worker corpus attributed to three model
families (decision 138). Then write the gate tests of M3 and run
`./scripts/gate M3`, with gate M2, M1 and M0 run again as a regression
check (decisions 132 (b), 139). Add nothing else: the Claude Code
coordinator, digests, issues, staging of step 1, retry of a failed day and
catch-up are step S4.2's; alert rules and the dashboard are step S4.1's.
Where a cited decision changes what an existing test asserts, the unit
changes that assertion and says so in its commit body; every other
existing test stays unchanged in what it asserts, and no existing file
under `tests/gates/` changes (the new `tests/gates/test_g3_*.py` files and
their helper are added). Finish with a report whose first line the
playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 17
  finished` | `VERDICT: mission 17 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-16-m17.md`
and the items of the earlier decisions files and of the owner's files that
the unit names. No unit changes any file under `config/`, any record under
`tests/fixtures/config/` or any entry of `tests/fixtures/config_frozen.json`;
a test that needs another configuration copies one under its temporary
directory and changes it there, and says so (the gate configuration is
built under a test's temporary directory with
`tests/fixtures/config/thresholds_gate.toml` copied in unchanged, decision
72). No unit changes an existing file under `tests/gates/` (O-19) or any
file under `tests/fixtures/rejected/`; U5 adds the M3 gate files. A unit
may add `producer` and `display` entries to
`tests/fixtures/return_readers.toml`, each named in its commit body
(O-18); no `adjusted` entry is reclassified and no second `stage3_money`
entry is added. Where a unit's code already exists and is right, so that a
new test cannot be seen to fail first against the parent, the sub-agent
instead makes, in its worktree and without committing it, the wrong change
the test is meant to catch, sees the test fail, reverts it, and names that
change in the commit body. Each unit names below the wrong changes its
tests must be seen to fail on; these are made one at a time, reverted the
same way, and named in the body. A commit body says "seen to fail" only of
a test that was seen to fail; a test that passed at the parent is named as
such (REVIEW-16 should-fix 1).

Long commands (finding HF-006): every run of `./scripts/check` or
`./scripts/gate` is its own foreground Bash call with an explicit timeout
of 20 minutes, the tool's maximum; never chain two such runs in one call,
and never let one run in the background. Each sub-agent runs
`./scripts/check` three times before its commit, as three calls, and says
in its report how many runs were green, with the wall time of one run.
`./scripts/check` took 834 to 841 s at mission 16's tip on the builder's
machine, with the `container` tests run. Tests that `./scripts/check` runs
replay a few days at most and make a few provider calls; the twenty-day
replays are the gate's (decision 140). A unit that adds more than 60 s to
one run says so in its body with the tests that cost it; a run above 15
minutes is a finding with the times (HF-006, D-013), never a reason to
drop a test. Every sub-agent first runs `discotrade sandbox build`, as its
own foreground call with a 20-minute timeout, so that the `container`
tests of the check run and do not skip, and says in its report that they
ran and the tag.

Every test of this mission writes state and job directories only under a
pytest temporary directory, reads time only through a `FixedClock`,
`--as-of` or the replay's clock (decision 72), and runs the `discotrade`
command in-process through the function the console script calls. A test
that runs `git` passes `GIT_ALLOW_PROTOCOL=file` in its environment and
uses local paths only (decision 47). Every test that reads bars or runs
days does so on a synthetic source from `tests/fixtures/config/`
(`test_mixed` or `test_synth`), or a copy of it under its temporary
directory, with every seed, date and bar length written in the test file.
A test that checks a figure computes the expected value itself, without
calling the function under test; a test that checks an adjusted figure
does so from the evaluation's rows and the stored bars without calling
`paper.adjusted`, `paper.adjusted_rows`, `paper.unit_bars`,
`paper.unit_returns` or `paper.average_positions`, as
`tests/test_exposure.py` does. Each rule is unit-tested at its production
value from `config/thresholds.toml`. No test opens a socket, calls a real
provider, a real model or a real `claude` binary (I-11); providers in tests
are the `ScriptedProvider` over a directory under `tests/fixtures/` or
under the test's temporary directory, or an `httpx.MockTransport` for the
`openai` refusal. No key is read, logged, stored or put in a prompt by a
test or by product code outside what decision 128 (b) states (I-13); a
test that needs the key set sets a dummy value with `monkeypatch.setenv`.
`src/discotrade/workers/providers.py` stays the only module under
`src/discotrade/workers/` that imports `httpx` or starts a process
(decision 122 (f)). Worker-written text runs only through the sandbox
backends; in tests every source a backend runs is byte-identical to a file
under `reference/` or `tests/fixtures/` (decision 104 (d)), and no test
builds the image.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S3.2b, the statement `This
mission closes milestone M3.`, that it runs gate M2, gate M1 item by item
and gate M0 again as decision 132 (b) says, and as carried items REVIEW-16
should-fix 1 (decision 133, U6), REVIEW-16 notes 10 to 12 and finding
D-016 (decision 134 (e), (f), U0), REVIEW-16 note 9 (decision 134 (d),
U6), and REVIEW-15 notes 2 and 4 (decision 136 (g), (h), U2), each with
the unit that takes it), rewrite `meta/CHECKPOINT.md` for this mission,
append to `meta/journal.md`, and append to `meta/findings/FINDINGS.md`,
after its last line and in its form, the D-016 status line and the HF-010,
HF-011 and HF-012 lines of decision 134 (e) and (f). Nothing else. Gate:
the four files are committed and pushed in one `plan:` commit.

**U1 Scoring a generated candidate on T (decision 135; O-4, O-11, O-13,
O-17, O-18; DESIGN §7.1, §8, §10.2, §10.3, §11.3, §12.4, §16.1 step 5;
I-3, I-7).** `src/discotrade/daily.py` (the scoring function only, not yet
called by the day), `tests/fixtures/return_readers.toml` (its `producer`
entry), and a test module of its own. Gate: decision 135 (f)'s tests pass:
the T figures (`metrics_t` with every §8 metric, `adjusted_t` with
`ADJUSTED_KEYS`) equal the test's own computation on `test_synth` with the
subprocess backend; the sandbox job of the T run holds no bar after the end
of `D`; the `lifecycle.Candidate` built carries every field of decision 135
(c); `lifecycle.admit` on it writes a trial row holding every key of
§10.2, with the model id, version `scripted` and the cutoff as used, and
an admitted candidate's `meta.json` holds them; a sandbox error while
scoring T is raised, not recorded as a worker outcome; the audit test of
O-18 passes with the new entry. Seen to fail: the T window scored without
`h(u0) = 0`; the average positions taken over W in place of T; the
cutoff left out of the candidate. `./scripts/check` green.

**U2 Daily steps 3 to 5 in `run_day` (decision 136; decisions 124, 125,
126, 131 (b), (c); DESIGN §13.6, §13.7, §14.1, §14.3, §15.2, §16.1 steps
3 to 5, §16.2; I-5, I-6, I-8, I-13).** `src/discotrade/daily.py` (the
steps, with a provider passed in by the caller; `run_day` without one
behaves as at the parent), and tests (a test module of its own, and
`tests/test_daily.py` only where a cited decision changes what one of its
tests asserts, said in the body). Gate: decision 136 (g), (h) and (i)'s
tests pass, each a few days at most on `test_synth` with the scripted
provider over fixture responses under the test's temporary directory or
`tests/fixtures/responses/`, and the subprocess backend: a day with a
valid response writes one `trial` call row, one trial row and its
lifecycle row; the weak flag is as decision 136 (g) says, both cases; a
duplicate on attempt 1 gives attempt 2's whole list of messages as
decision 136 (h) says; a day with `data_gaps`, a day with no offered cell
and a day whose model list fails each make no call (the last with
`model_list_failed`); every health event of steps 3 to 5 is in the health
log on a day that fails after them; a re-run writes nothing and makes no
provider call; a day failed after its response was stored runs again with
no provider call and the same rows; `run_day` without a provider gives the
same state as at the parent (the existing tests of `tests/test_daily.py`,
`tests/test_replay.py` and `tests/test_replay_candidates.py` pass
unchanged). Seen to fail: the steps run on a re-run of a journaled day;
the cell statuses read with the rows dated `D`; the call rows written
outside the staging directory. `./scripts/check` green.

**U3 The options of `run-day` and `replay`, and the scripted cursor
(decision 137; decision 122 (b), (c); DESIGN §13.5, §14.2, §16.4; I-6,
I-12, I-13).** `src/discotrade/cli.py` (the two commands' options),
`src/discotrade/replay.py` (passing the provider and coordinator to each
day, and building the scripted provider's `start` from the stored
responses), `src/discotrade/daily.py` only as the options need, and tests
(`tests/test_cli.py` or a test module of its own, and
`tests/test_replay.py` where it gains tests). Gate: decision 137 (d)'s
tests pass: two replays from scratch with the scripted roles over the same
four trading days give state directories with identical content hashes; a
replay run as two `replay` calls over consecutive spans gives the same
state as one call over both, and serves no corpus file twice; `--candidates`
with a provider other than `none` exits 2; a missing `scripted:` directory
and a missing or refused `models.toml` are refused before any day runs
with one line and exit 2; `--provider openai` without a usable key prints
one line on standard error and exits 1, with a transport that fails the
test if called; `--provider none` leaves every existing test of the two
commands passing unchanged. Seen to fail: the cursor's `start` built from
the call rows instead of the stored responses (the split-replay test goes
red when a day failed after storing its response, which the test
injects); the provider built once per day instead of once per command.
`./scripts/check` green.

**U4 The worker corpus (decision 138; decision 122 (b); DESIGN §13.4,
§17.1, §18.3 G3.1; HF-009).** New files under
`tests/fixtures/worker_corpus/` (`m3/`, `m3_pool/`, `strategies/`,
`manifest.toml`) and `tests/test_worker_corpus.py`. The sub-agent's unit
text describes every strategy file as an ordinary price-based trading rule
written as a validation fixture for the family its manifest entry names,
which is what each is. Gate: `tests/test_worker_corpus.py` passes: every
response file the manifest lists exists, every Python block is
byte-identical to the strategy file the manifest names, every response
parses or fails to parse as the manifest says, and the corpus directories
are named by decision 122 (b)'s rule after the three pool models of
`tests/fixtures/config/models.toml`; the test takes under 5 s. The body
lists, per strategy file, its family and horizon, and states which
response is expected to be served on which replay day, as the builder
measured it with a throwaway replay outside the repository (the gate
proves it). Seen to fail: one block changed by one character (the
byte-identity check red). `./scripts/check` green.

**U5 The gate tests of M3 and the gate runs (decisions 132 (b), 139;
decisions 9, 40, 72; O-2, O-19; DESIGN §18.2, §18.3 M3).** New files
`tests/gates/test_g3_1_candidates.py`, `tests/gates/test_g3_2_pool.py`,
`tests/gates/test_g3_3_prompts.py` and `tests/gates/m3_harness.py`; no
existing file under `tests/gates/` changes. Each test asserts what its
item of §18.3 says, as decision 139 (a) to (c) reads it, and no less.
Gate: after U4 is pushed and `./scripts/check` is green three times at the
tip (three calls, each wall time kept), run `discotrade sandbox build`
(its tag kept), then `./scripts/gate M3` as one foreground call with a
20-minute timeout, and keep its output verbatim with its wall time; it
prints `G3.1` to `G3.3 PASS` and `gate M3: PASS`. Then run `./scripts/gate
M2` the same way, then `./scripts/gate M1 G1.1`, `G1.2`, `G1.3` and
`G1.4`, each its own foreground call with a 20-minute timeout, and
`./scripts/gate M0` once the same way, all at the same tip, each output
verbatim with its wall time. Decision 132 (b) says what follows a FAIL, an
item above its time, or an item that cannot finish in its call. Append to
`meta/findings/FINDINGS.md` one D-014 times line with G1.3's wall time.
Seen to fail, each made in the worktree and reverted, with the item that
went red: the seven wrong changes of decision 139 (d). The image of the
tip's tag is left built. The unit's commit is `gate:` and carries only the
new gate files and the FINDINGS line; the outputs go to the report.

**U6 The final report (decisions 132 to 140; DESIGN §18.2).** Write
`meta/FINAL-REPORT-17.md` (drafted under `meta/drafts/`, moved in by this
commit). Before writing, the sub-agent makes decision 133 (b)'s two wrong
changes in a worktree, one at a time, runs the two doctor cases after
each, reverts each, and keeps what went red. The report gives: what
changed (sha per unit); `./scripts/check`'s wall times at the tip beside
mission 16's (834 to 841 s); the output of `./scripts/gate M3` under a
heading `## Gate M3`, verbatim, with the tip it ran at and its wall time,
and each item's wall time; the outputs of `./scripts/gate M2` (under
`## Gate M2`), of the four `./scripts/gate M1 G1.<n>` calls (under `## Gate
M1`) and of `./scripts/gate M0` (under `## M0 still passes`), verbatim, with
their wall times beside FINAL-REPORT-15's; a `## Corrections` section as
decision 133 says; a `## Corpus` section (per response file served in the
G3.1 replay: the day, the cell, the model, the attempt, the outcome, and
for a trial whether it was admitted; the pairwise correlation matrix of
the trials on W, or its maximum with the pair; the tokens in and out of
each call; the arithmetic of the budget response of decision 138 (d)); a
`## Day` section (the order of steps 3 to 5 in `run_day`, the health
events they can raise, and the seconds per replay day with and without a
provider on the G3.1 days); for each of decisions 135 to 139, the test
files and test names that hold it; what the tests prove; NOT PROVEN
(mandatory: that no real provider, model or `claude` binary was called,
which is live checks L3 and L4, so G3.1 proves the pipeline, not the
models; that the twenty replay days with the real pool (the rest of L3)
are the owner's; that the base URL, the model ids and the cutoffs stay
unverified; that every observation of a replay over 2019 is exposed under
the fixture cutoffs (DESIGN §11.3), so nothing here reads a clean day; that
the scripted token counts are an estimate by rule; that the corpus was
written by the builder and its yield is arranged, not discovered; that the
leak checks of G3.3 cover the forms the test lists and no other spelling;
that `--provider openai` is tested for its refusal only; that the speed
figures are from the builder's machine; what remains of FINAL-REPORT-16's
NOT PROVEN, with REVIEW-16's three additions of note 9); the findings
filed and answered; and a `## Review items` table with one row each for
REVIEW-16 should-fix 1 and notes 1 to 12, and for REVIEW-15 notes 2 and 4:
the item, its resolution (the unit and decisions item, or "stands" or the
step that takes it, as decisions 133, 134 and 136 say), and the sha where
there is one. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 16's.
- `./scripts/gate M3` at the pushed tip prints `G3.1` to `G3.3 PASS` and
  `gate M3: PASS`; its output and wall time are in the report.
- `./scripts/gate M2` prints `gate M2: PASS`; `./scripts/gate M1 G1.1` to
  `G1.4`, each run on its own at the pushed tip, print their item PASS
  line; `./scripts/gate M0` prints `gate M0: PASS`; the outputs and times
  are in the report.
- A new day of `run-day` or `replay` with a provider runs steps 3 to 5 as
  decision 136 says; without one it gives the state the parent gives; a
  re-run of a journaled day writes nothing and makes no provider call.
- A generated candidate is scored on T in the day's sandbox backend with
  both measures recorded, and its trial row holds every key of §10.2 with
  the model, its version and its cutoff.
- The scripted provider's cursor is built from the stored responses, and a
  replay split in two calls equals one.
- The worker corpus is attributed to the three pool models, every block is
  byte-identical to a trusted strategy file, and the manifest lists every
  file.
- REVIEW-16 should-fix 1 is corrected in FINAL-REPORT-17's `## Corrections`
  as decision 133 says.
- No file under `config/` or `tests/fixtures/rejected/`, no existing file
  under `tests/gates/`, no record under `tests/fixtures/config/` and no
  entry of `tests/fixtures/config_frozen.json` changed in this mission.
- Every unit commit's body lists every file it touches; U0 is `plan:`; U5
  is `gate:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no file under `src/` names
  a market, a contract root or a venue; no test builds the image.
- `meta/FINAL-REPORT-17.md` exists with `## Gate M3`, `## Gate M2`, `## Gate
  M1`, `## M0 still passes`, `## Corrections`, `## Corpus`, `## Day`, NOT
  PROVEN, and the review-items table.
