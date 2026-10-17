# BUILDER-18-PROMPT — discotrade mission 18: G3.3's raw-bar and score checks, the corpus manifest proven, and gate M3 again (step S3.2b, closer)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 18. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-18.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 18 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-17-m18.md` (items 141 to 145, new for
this mission; every unit below cites them),
`meta/decisions/decisions-2026-10-16-m17.md` (items 132 to 140; 138 the
worker corpus, 139 the gate tests of M3, whose clause (c) on raw bars and
scores item 142 replaces),
`meta/decisions/decisions-2026-10-16-m15.md` (items 118 to 126; 122 (b)
the corpus directories),
`meta/decisions/decisions-2026-10-15-m14.md` (items 109 to 117; 116 the
labelling, 117 the prompt's number rendering, 119 (b) the sanitizing),
`meta/decisions/decisions-2026-10-15-owner.md` (the owner's; O-19's rule on
gate tests of a met milestone; M3 is not met, so its gate files change
here), `meta/decisions/decisions-2026-10-13-owner.md` (the owner's),
`meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still bind; 72 the
gate configuration), `DESIGN.md` (§13.1 to §13.4 for the profile, the
anonymization, the registry and the prompt, §18.2 and §18.3 (M3) for the
gate; read §2 twice, in particular I-8, I-9, I-11 and I-12),
`meta/reviews/REVIEW-17.md` (its `## Gate`, `## Blockers` and `## Notes`),
`meta/FINAL-REPORT-17.md`, `meta/findings/FINDINGS.md` (finding D-017),
`meta/BACKLOG.md`, and `meta/CHECKPOINT.md` (a unit in progress means §R
first). This is roadmap step S3.2b, continued.

---

## Mission

Close REVIEW-17's two blockers on step S3.2b, as decisions 141 to 145 say.
This mission closes milestone M3. First file the findings lines of decision
144 (f). Then make gate item G3.3 assert "no raw bar" and "no score" as
decision 142 reads them: every number of every prompt accounted for by its
source, the harness-computed values compared with the bars and the earlier
trial figures at full precision, and the profile shown free of price and
volume units (blocker 1, finding D-017). Then prove the corpus manifest's
per-file day, attempt and outcome with a gate test, and narrow the two
sentences that claimed it to that test (blocker 2, decision 143). Then run
`./scripts/gate M3` at the pushed tip. Add nothing else: no file under
`src/` changes (decision 141 (a)); REVIEW-17's notes go where decision 144
says. Only `tests/gates/test_g3_3_prompts.py`, `tests/gates/test_g3_2_pool.py`,
`tests/gates/m3_harness.py`, `tests/test_worker_corpus.py` and
`tests/fixtures/worker_corpus/manifest.toml` change among the tests and
fixtures, each as its unit says; every other existing test stays unchanged
in what it asserts, and no other file under `tests/gates/` changes (O-19).
Finish with a report whose first line the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 18
  finished` | `VERDICT: mission 18 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-17-m18.md`
and the items of the earlier decisions files and of the owner's files that
the unit names. No unit changes any file under `src/`, `config/` or
`tests/fixtures/rejected/`, any record under `tests/fixtures/config/` or any
entry of `tests/fixtures/config_frozen.json`. If a new test finds a real
leak in product code, or a meeting of values it cannot explain by its
source, the sub-agent stops, writes a finding naming the call, the message,
the token or the two values, and the source, and the builder replies
`VERDICT: question` with it (decision 141 (a), 142 (b)). The gate
configuration is built under a test's temporary directory with
`tests/fixtures/config/thresholds_gate.toml` copied in unchanged (decision
72); every date and seed a gate test uses is written in the test file, and
`tests/gates/m3_harness.py` holds no seed, date or assertion of an item.
Where a new test passes against the parent because the code it checks is
right, the sub-agent instead makes, in its worktree and without committing
it, the wrong change the test is meant to catch, sees the test fail,
reverts it, and names that change in the commit body. Each unit names below
the wrong changes its tests must be seen to fail on; these are made one at
a time, reverted the same way, and named in the body with the test that
went red. A commit body says "seen to fail" only of a test that was seen to
fail, and says a test proves something only when that test asserts it; a
claim that a later unit or the gate will prove something names the test
that does, or is not made (REVIEW-17 blocker 2, note 14).

Long commands (finding HF-006): every run of `./scripts/check` or
`./scripts/gate` is its own foreground Bash call with an explicit timeout
of 20 minutes, the tool's maximum; never chain two such runs in one call,
and never let one run in the background. Each sub-agent runs
`./scripts/check` three times before its commit, as three calls, and says
in its report how many runs were green, with the wall time of one run.
`./scripts/check` took 1021 to 1043 s at mission 17's tip on the builder's
machine, with the `container` tests run. A run that passes the 20-minute
cap and is moved to the background by the harness is waited for to its
end before the next run, and recorded as decision 145 says; it is never
dropped, shortened or counted green before it ends. Every sub-agent first
runs `discotrade sandbox build`, as its own foreground call with a
20-minute timeout, so that the `container` tests of the check run and do
not skip, and says in its report that they ran and the tag. A gate item
run by a sub-agent to see a wrong change go red is run as
`./scripts/gate M3 G3.<n>`, its own foreground call with a 20-minute
timeout.

Every test of this mission writes state and job directories only under a
pytest temporary directory, reads time only through `--as-of` or the
replay's clock (decision 72), and runs the `discotrade` command in-process
through the function the console script calls. A test that runs `git`
passes `GIT_ALLOW_PROTOCOL=file` in its environment and uses local paths
only (decision 47). A test that checks a figure computes the expected value
itself, without calling the function under test. No test opens a socket,
calls a real provider, a real model or a real `claude` binary (I-11); the
provider is the `ScriptedProvider` over `tests/fixtures/worker_corpus/`.
Worker-written text runs only through the sandbox backends; every source a
backend runs is byte-identical to a file under `reference/` or
`tests/fixtures/` (decision 104 (d)), and no test builds the image.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S3.2b continued, the
statement `This mission closes milestone M3.`, that gates M2, M1 and M0
are not run again because no file under `src/` changes (decision 141 (b)),
and as carried items REVIEW-17 blocker 1 with finding D-017 (decision 142,
U1), REVIEW-17 blocker 2 with note 3's first half (decision 143, U2 and
U4), REVIEW-17 note 1 (decision 141 (b), U3), and REVIEW-17 notes 10 to 13
(decision 144 (f), U0), each with the unit that takes it, and notes 3's
second half, 4 and 5 left to step S4.2 (decision 144 (a), (b))), rewrite
`meta/CHECKPOINT.md` for this mission, append to `meta/journal.md`, and
append to `meta/findings/FINDINGS.md`, after its last line and in its
form, the D-017 status line and the HF-010, HF-011, HF-006 and HF-012 lines
of decision 144 (f). Nothing else. Gate: the four files are committed and
pushed in one `plan:` commit.

**U1 G3.3: no raw bar and no score, as decision 142 reads them (decision
142; decisions 116, 117, 119 (b), 139 (c); finding D-017; REVIEW-17
blocker 1; DESIGN §13.1 to §13.4, §18.2, §18.3 G3.3; I-8, I-12).**
`tests/gates/test_g3_3_prompts.py` (new tests for decision 142 (a), (b)
and (c); its module docstring's reading replaced by item 142's, citing
it; `looked_for` and the text search unchanged, decision 142 (d)), and
`tests/gates/m3_harness.py` only for a helper with no seed, date or
assertion (for example writing the scaled copy of the bar store). Gate:
`./scripts/gate M3 G3.3` passes at the unit's commit, one foreground call
with a 20-minute timeout, its output and wall time in the body beside
REVIEW-17's 158.80 s; the tests assert, on every message of every stored
response of the G3.1 replay: every numeric token accounted for by a source
of its part, as decision 142 (a) lists them, with the contract and output
parts less their cost lines identical in every first prompt; every finite
real leaf of the anonymized profile document and every cost-line figure
meeting no open, high, low or close of the day's W and T of any instrument
(as stored and times the call's factor) and no non-integral figure of an
earlier trial row, at a relative 1e-9 (decision 142 (b)); and, for the
three days the test writes, the profile from a copy of the store with
prices times 7/3 and volumes times 5/2 equal to the profile from the store,
every finite leaf to a relative 1e-9 and every null in the same place
(decision 142 (c)). The body names, per source of decision 142 (a), the
function or text the test reads it from. Seen to fail, each made alone in
`src/` in the worktree and reverted, with the part and the test that went
red: the five wrong changes of decision 142 (e). The unit's commit is
`gate:`. `./scripts/check` green.

**U2 The corpus manifest's served day, attempt and outcome (decision 143
(a), (b), (d); decision 138 (e); REVIEW-17 blocker 2; DESIGN §18.3
G3.2).** `tests/gates/test_g3_2_pool.py` (one new test, markers `gate` and
`gate_m3`, over the module's existing replays of `m3/` and `m3_pool/`),
`tests/test_worker_corpus.py` (its module docstring only) and
`tests/fixtures/worker_corpus/manifest.toml` (its third line, and a row
only where the measured call row differs, named in the body). Gate:
`./scripts/gate M3 G3.2` passes at the unit's commit, one foreground call
with a 20-minute timeout, its output and wall time in the body beside
REVIEW-17's 183.28 s; the new test asserts, for both replays, that every
file the manifest lists with a `served` day gives exactly one call row with
that day, attempt and outcome (the file being the one whose bytes the
row's stored `text` equals), that every call row with a response maps to
such a manifest row, and that a file listed with no `served` day was not
served; the docstring and the manifest's third line name that test by its
file and function and claim nothing more. Seen to fail, each made alone in
a copy of the manifest in the worktree and reverted: the three wrong
changes of decision 143 (d). The unit's commit is `gate:`.
`./scripts/check` green.

**U3 Gate M3 at the pushed tip (decision 141 (b); DESIGN §18.2, §18.3
M3; REVIEW-17 note 1).** After U2 is pushed and `./scripts/check` is green
three times at that tip (three calls, each wall time kept), run
`discotrade sandbox build` (its tag kept), then `./scripts/gate M3` as one
foreground call with a 20-minute timeout at that same pushed tip, with no
uncommitted file but the git-ignored drafts, and keep its output verbatim
with its wall time and `git rev-parse HEAD`; it prints `G3.1` to `G3.3
PASS` and `gate M3: PASS`. An item that prints FAIL is a defect: when it is
in U1's or U2's files, that unit is taken again; otherwise `VERDICT:
mission 18 blocked U3` naming it. An item above 15 minutes is a finding
with the times, never a reason to weaken it. The unit's commit is `meta:`
and carries only one line appended to `meta/findings/FINDINGS.md`: a
D-013 times line with the three check runs and the gate's item times at
that tip. The outputs go to the report.

**U4 The final report (decisions 141 to 145; DESIGN §18.2).** Write
`meta/FINAL-REPORT-18.md` (drafted under `meta/drafts/`, moved in by this
commit). The report gives: what changed (sha per unit); `./scripts/check`'s
wall times at the tip beside mission 17's (1021 to 1043 s); the output of
`./scripts/gate M3` under a heading `## Gate M3`, verbatim, with the tip it
ran at and its wall time, and each item's wall time beside REVIEW-17's;
a `## G3.3 reading` section (decision 142's three parts, each with its test
names, the sources of part (a) with what the test reads each from, the
three days of part (c), and the five wrong changes of 142 (e) with the part
and test each turned red); a `## Corrections` section as decision 143 (c)
says; what the tests prove; NOT PROVEN (mandatory: that no real provider,
model or `claude` binary was called, which is live checks L3 and L4, so
G3.1 proves the pipeline, not the models; that the leak checks of G3.3
prove the sources of the G3.1 replay's prompts on `test_synth`, the
accounting reading each source as the test computes it, and no prompt of
another track, profile version or coordinator; that the value comparison
is at a relative 1e-9 and a bar transformed otherwise than by the units of
decision 142 (c) is not shown absent; that the corpus was written by the
builder and its yield is arranged, not discovered; that the speed figures
are from the builder's machine; what remains of FINAL-REPORT-17's NOT
PROVEN, item by item); the findings filed and answered; and a `## Review
items` table with one row each for REVIEW-17 blockers 1 and 2 and notes 1
to 14: the item, its resolution (the unit and decisions item, or "stands"
or the step that takes it, as decisions 141 to 144 say), and the sha where
there is one. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 17's.
- `./scripts/gate M3` at the pushed tip, with nothing uncommitted, prints
  `G3.1` to `G3.3 PASS` and `gate M3: PASS`; its output, the tip's sha and
  its wall time are in the report.
- G3.3 asserts no raw bar and no score as decision 142 reads them: every
  numeric token of every stored message accounted for by its source, the
  harness-computed values meeting no bar and no earlier trial figure at
  full precision, and the profile unchanged under a change of price and
  volume units; each of the five wrong changes of decision 142 (e) turned
  it red.
- A gate test compares each served corpus file's day, attempt and outcome
  with the replay's call rows, for `m3/` and `m3_pool/`; the docstring of
  `tests/test_worker_corpus.py` and the manifest's third line name it and
  claim nothing more; each of the three wrong changes of decision 143 (d)
  turned it red.
- FINAL-REPORT-18's `## Corrections` quotes 446b0a8's and 014f06a's
  sentences as decision 143 (c) says.
- No file under `src/`, `config/` or `tests/fixtures/rejected/`, no record
  under `tests/fixtures/config/`, no entry of
  `tests/fixtures/config_frozen.json` and no file under `tests/gates/`
  other than `test_g3_3_prompts.py`, `test_g3_2_pool.py` and
  `m3_harness.py` changed in this mission.
- Every unit commit's body lists every file it touches; U0 is `plan:`; U1
  and U2 are `gate:`; U3 is `meta:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no test builds the image.
- `meta/FINAL-REPORT-18.md` exists with `## Gate M3`, `## G3.3 reading`,
  `## Corrections`, NOT PROVEN, and the review-items table.
