# BUILDER-16-PROMPT — discotrade mission 16: REVIEW-15's blocker and should-fix items (step S3.2a, repaired)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 16. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-16.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 16 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-16-m16.md` (items 127 to 131, new for
this mission; every unit below cites them),
`meta/decisions/decisions-2026-10-16-m15.md` (items 118 to 126; 121 is the
synthetic source's cache, 122 the providers and live check L3, 123 the
models and run configuration, all three repaired here),
`meta/decisions/decisions-2026-10-15-m14.md` (items 109 to 117),
`meta/decisions/decisions-2026-10-15-owner.md` (the owner's; O-19, O-20 and
O-22 bind, O-19's rule on gate tests of a met milestone in particular),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-16 to O-18
bind), `meta/decisions/decisions-2026-10-14-m13.md` (items 100 to 108),
`meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still bind),
`DESIGN.md` (§13.5 for the providers, §19.3 L3 for `doctor --live
workers`, §4.3 and §13.6 for the configuration it reads, §5.5 and §17.1
for the synthetic source, §18.1 for the commit gate; read §2 twice, in
particular I-6, I-10, I-11 and I-13), `meta/reviews/REVIEW-15.md` (its
`## Blockers`, `## Should-fix` and `## Notes`), `meta/FINAL-REPORT-15.md`,
`meta/BACKLOG.md`, `meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a
unit in progress means §R first). This is roadmap step S3.2a, repaired.

---

## Mission

Close REVIEW-15's blocker and its two should-fix items for step S3.2a, as
decisions 127 to 131 say. First file the findings lines of decision 131
(e). Then make one place read the worker key, and make the claim about it
say exactly what the code does (decision 128, with the first half of
REVIEW-15's note 3). Then make `doctor --live workers` read the loaded
configuration (decision 129). Then hold the synthetic cache key's calendar
and bar-length parts by tests (decision 130). This mission does not close
a milestone and runs no gate (decision 127 (a)). Add nothing else. Wiring
the generation into `run-day` and `replay`, scoring on T, trial rows, the
worker corpus and the M3 gate tests are step S3.2b's. Where a cited
decision changes what an existing test asserts, the unit changes that
assertion and says so in its commit body; every other existing test stays
unchanged in what it asserts, and no file under `tests/gates/` changes.
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
- Your final reply begins with exactly one of: `VERDICT: mission 16
  finished` | `VERDICT: mission 16 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-16-m16.md`
and the items of the earlier decisions files and of the owner's files that
the unit names. No unit changes any file under `config/`, any record under
`tests/fixtures/config/` or any entry of `tests/fixtures/config_frozen.json`;
a test that needs another configuration copies one under its temporary
directory and changes it there, and says so. No unit changes any file under
`tests/gates/` (O-19) or under `tests/fixtures/rejected/`. Where a unit's
code already exists and is right, so that a new test cannot be seen to
fail first against the parent, the sub-agent instead makes, in its
worktree and without committing it, the wrong change the test is meant to
catch, sees the test fail, reverts it, and names that change in the commit
body. Each unit names below the wrong changes its tests must be seen to
fail on; these are made one at a time, reverted the same way, and named in
the body.

Long commands (finding HF-006): every run of `./scripts/check` is its own
foreground Bash call with an explicit timeout of 20 minutes, the tool's
maximum; never chain two such runs in one call, and never let one run in
the background. Each sub-agent runs `./scripts/check` three times before
its commit, as three calls, and says in its report how many runs were
green, with the wall time of one run. `./scripts/check` took 828 to 848 s
at mission 15's tip on the builder's machine, with the `container` tests
run; a unit that adds more than 60 s to one run says so in its body with
the tests that cost it; a run above 15 minutes is a finding with the times
(HF-006, D-013), never a reason to drop a test. Every sub-agent first runs
`discotrade sandbox build`, as its own foreground call with a 20-minute
timeout, so that the `container` tests of the check run and do not skip,
and says in its report that they ran and the tag.

Every test of this mission writes state and job directories only under a
pytest temporary directory, reads time only through a `FixedClock` or
`--as-of`, and runs the `discotrade` command in-process through the
function the console script calls. Every test that reads bars does so on a
synthetic source from `tests/fixtures/config/` (`test_mixed` or
`test_synth`), or a copy of it under its temporary directory, with every
seed, date and bar length written in the test file. A test that checks a
figure computes the expected value itself, without calling the function
under test. No test opens a socket, calls a real provider, a real model or
a real `claude` binary (I-11); the doctor's tests reach the provider only
through `WORKERS_TRANSPORT` set to an `httpx.MockTransport`. No key is
read, logged, stored or put in a prompt by a test or by product code
outside what decision 128 (b) states (I-13); a test that needs the key set
sets a dummy value with `monkeypatch.setenv`. `src/discotrade/workers/providers.py`
stays the only module under `src/discotrade/workers/` that imports `httpx`
or starts a process (decision 122 (f)). Nothing of this mission is called
from `run-day` or `replay`.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S3.2a repaired, the
statement that this mission does not close a milestone and runs no gate
(decision 127 (a)), and as carried items REVIEW-15 blocker 1 and note 3's
first half (decision 128, U1), should-fix 1 (decision 129, U2),
should-fix 2 and note 6 (decision 130, U3 and U4), and notes 8, 9 and 10
with the D-013 times (decision 131 (e), U0), each with the unit that
takes it), rewrite `meta/CHECKPOINT.md` for this mission, append to
`meta/journal.md`, and append to `meta/findings/FINDINGS.md`, after its
last line and in its form, the D-013, HF-010, HF-011 and HF-012 lines of
decision 131 (e). Nothing else. Gate: the four files are committed and
pushed in one `plan:` commit.

**U1 One place reads the worker key, and the claim says so (REVIEW-15
blocker 1 and note 3's first half; decision 128; decision 122 (c), (e);
DESIGN §13.5, §19.3 L3; I-13).** `src/discotrade/workers/providers.py`
(`key_present`, the two docstrings, the errors' context),
`src/discotrade/doctor.py` (the key check of `live_workers` only), and
tests (`tests/test_workers_providers.py`, the doctor's test file). Gate:
the source test of decision 128 (c) passes (the text `NEBIUS_API_KEY`
under `src/discotrade/` only in `providers.py`; no other module imports
`KEY_ENV` from `discotrade.workers.providers`); `key_present()` is false
with the key unset and with a key of spaces, and true with a dummy key,
and its result holds no part of the value; `doctor --live workers` with
the key unset and with a key of spaces prints one line on standard error
and exits 1, with a transport that fails the test if it is called; every
`ProviderError` of `OpenAICompatProvider`'s status error, malformed body
and timeout has `__cause__` and `__context__` both `None`, and no key in
its text; the two docstrings state decision 128 (b) and no more; every
existing provider and doctor test passes unchanged. Seen to fail: the
doctor's own read of the environment restored; the error raised inside
the `except` block with `from None` only. The body states the rule in
decision 128 (b)'s words and no wider. `./scripts/check` green.

**U2 `doctor --live workers` reads the loaded configuration (REVIEW-15
should-fix 1; decision 129; decisions 122 (e), 123 (c), (d); DESIGN §19.3
L3, §4.3, §13.6; I-10).** `src/discotrade/doctor.py` (`live_workers` and
the module constants it used only), and tests (the doctor's test file).
Gate: `WORKERS_TIMEOUT_SECONDS` and the raw `tomllib` parse of
`models.toml` are gone from `doctor.py`; each of decision 123 (c)'s four
refusals, in a configuration copied under the temporary directory, gives
`doctor --live workers: FAIL: <the error's text>; no request was made` on
standard error and exit 1, the error's text being the one `discotrade
config check` gives for the same file, with a transport that fails the
test if it is called; a copied `run.toml` with a `request_timeout_seconds`
written in the test builds the provider with that value, observed by the
test; a missing `models.toml` keeps its one-line refusal; the ok path and
the missing-model path still print the pool in file order with its
`pool` and `fallback` labels. An existing doctor test that set
`WORKERS_TIMEOUT_SECONDS` or wrote a `models.toml` the loader refuses
changes to a copied configuration, and the body names it. Seen to fail:
the raw parse restored; the fixed 300.0 restored. `./scripts/check` green.

**U3 The cache key's calendar and bar-length parts held by tests
(REVIEW-15 should-fix 2; decision 130; decision 121 (a); DESIGN §5.5,
§17.1; I-6).** `tests/test_synth_cache.py`, and
`src/discotrade/sources/synth.py` only if decision 130 (c) applies. Gate:
the two tests of decision 130 (a) pass, each asserting both that the
second series differs from the first and that it equals the series
generated with the cache cleared; the calendar change and the second bar
length are written in the test; every existing test of the file passes
unchanged. Seen to fail, each made alone and reverted: the key without the
calendar record (the calendar test goes red); the key without the bar
length (the bar-length test goes red). The body names, for each of the
key's parts, the test that goes red without it. `./scripts/check` green.

**U4 The final report (decisions 127 to 131; DESIGN §18.2).** After U3 is
pushed and `./scripts/check` is green three times at the tip (three
calls, each wall time kept, after `discotrade sandbox build` with its tag
kept), write `meta/FINAL-REPORT-16.md` (drafted under `meta/drafts/`,
moved in by this commit). The report gives: what changed (sha per unit);
`./scripts/check`'s wall times at the tip beside mission 15's (828 to
848 s); a `## Corrections` section as decision 128 (d) says (each place
the false claim stands, quoted, with decision 128 (b)'s sentence beside
it); a `## Cache key` section naming, for each part of decision 121 (a)'s
key, the test that holds it and the wrong change that turns it red; for
each of decisions 128 to 130, the test files and test names that hold it;
what the tests prove; NOT PROVEN (mandatory: that no real provider, model
or `claude` binary was called, which is live checks L3 and L4; that the
base URL, the model ids and the cutoffs stay unverified; that nothing of
S3.2a is called from `run-day` or `replay`; what remains of
FINAL-REPORT-15's NOT PROVEN); the findings filed and answered; and a `##
Review items` table with one row each for REVIEW-15 blocker 1, should-fix
1 and 2, and notes 1 to 10: the item, its resolution (the unit and
decisions item, or "stands" or the step that takes it, as decision 131
says), and the sha where there is one. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 15's.
- Under `src/discotrade/`, the text `NEBIUS_API_KEY` appears only in
  `providers.py`, and no other module imports its `KEY_ENV`; the doctor
  asks `key_present()`; a test enumerates the files and holds both.
- No `ProviderError` of the OpenAI-compatible provider keeps a cause or a
  context.
- `doctor --live workers` reads `models.toml` through `config.load_models`
  and its timeout from `config/run.toml`'s `[workers]`, refuses each of
  decision 123 (c)'s four refusals with one line and no request, and
  builds the provider with the configured timeout.
- Each of the synthetic cache key's parts (the `[source]` table with its
  seed, `trusted_from`, the calendar record, the bar length) has a test
  that goes red when that part is left out of the key.
- The false claim of REVIEW-15's blocker is corrected in the docstrings
  and in FINAL-REPORT-16's `## Corrections`, in decision 128 (b)'s words.
- No file under `config/`, `tests/gates/` or `tests/fixtures/rejected/`,
  no record under `tests/fixtures/config/` and no entry of
  `tests/fixtures/config_frozen.json` changed in this mission.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no file under `src/` names
  a market, a contract root or a venue; no test builds the image.
- `meta/FINAL-REPORT-16.md` exists with `## Corrections`, `## Cache key`,
  NOT PROVEN, and the review-items table.
