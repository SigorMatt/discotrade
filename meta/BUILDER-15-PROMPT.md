# BUILDER-15-PROMPT — discotrade mission 15: REVIEW-14's should-fix item, the synthetic source's speed, the providers, the model pool, the scripted coordinator and the day's generation (step S3.2a)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 15. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-15.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 15 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-16-m15.md` (items 118 to 126, new for
this mission; every unit below cites them),
`meta/decisions/decisions-2026-10-15-m14.md` (items 109 to 117; 115 to 117
are the modules this mission calls, 117 (c) amended by 119 (a)),
`meta/decisions/decisions-2026-10-15-owner.md` (the owner's; O-19, O-20 and
O-22 bind, O-19's rule on gate tests of a met milestone in particular),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-16 to O-18
bind every new module, O-11 and O-13 are step S3.2b's scoring and are read
so that nothing built here contradicts them),
`meta/decisions/decisions-2026-10-14-m13.md` (items 100 to 108; 104 (d) is
the subprocess backend's trusted-text rule the generation tests rely on),
`meta/decisions/decisions-2026-10-14-m12.md` (items 91 to 99; 92 is the
audit of return readers), `meta/decisions/decisions-2026-10-14-m11.md`
(items 83 to 90), `meta/decisions/decisions-2026-10-14.md` (items 76 to
82; 80 is the method of the speed figures),
`meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still bind; 61,
62 and 63 name what this step writes), `DESIGN.md` (§13.5 to §13.7 and
§14.1 to §14.3 are this mission, with §13.4 for storing responses, §4.3 for
the thresholds and frozen files, §9.1 for the state directory and an
approach's `meta.json`, §10.2 for the call log, §11.3 for the cutoff,
§12.2 and §12.3 for the validation sequence and the correlation gate,
§15.2 for health events, §16.1 steps 3 to 5 and §16.2 for what the day
will call, §17.1 and §5.5 for the synthetic source, §18.1 for the commit
gate, §19.3 L3, §20 R-14, R-19, R-21 and R-25; read §2 twice, in
particular I-5, I-6, I-8, I-10, I-11, I-12 and I-13), `SPEC.md` §7 and
§17 (the model pool and its records), `meta/reviews/REVIEW-14.md` (its
`## Should-fix` and `## Notes`), `meta/FINAL-REPORT-14.md`,
`meta/BACKLOG.md`, `meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a
unit in progress means §R first). This is roadmap step S3.2a.

---

## Mission

Build roadmap step S3.2a as decisions 118 to 126 cut it. First take
REVIEW-14's should-fix item and its notes 3, 4 and 7 (decision 119) and
file the findings of decision 120. Then cut the synthetic source's
per-day cost without changing a byte it stores (decision 121, finding
D-013). Then build the providers (decision 122), `config/models.toml` and
the pool (decisions 123 and 124), the coordinator interface with its
scripted form (decision 125), and the day's generation as a function
(decision 126). Then run gate M0 once, gate M2 once and gate M1 item by
item at the pushed tip as a regression check (decision 118 (b)). This
mission does not close a milestone. Wiring the generation into `run-day`
and `replay`, scoring on T, trial rows, the worker corpus and the M3 gate
tests are step S3.2b's (decision 118 (a)). Add nothing else. Where a cited
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
- Your final reply begins with exactly one of: `VERDICT: mission 15
  finished` | `VERDICT: mission 15 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-16-m15.md`
and the items of the earlier decisions files and of the owner's files that
the unit names. No unit changes a value in a frozen file
(`config/instruments/`, `config/tracks/`, `config/calendars/`,
`config/thresholds.toml`, `tests/fixtures/config_frozen.json` entries that
already exist), and no unit changes an existing value of `config/run.toml`
or `tests/fixtures/config/run.toml`: a value believed wrong is a finding.
U4 creates `config/models.toml` and `tests/fixtures/config/models.toml`
with the records decision 123 (a) lists, adds their values to
`tests/fixtures/config_frozen.json` as new entries, and adds the
`[workers]` table of decision 123 (d) to both `run.toml` files; no other
unit touches those files. No unit changes an existing record under
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
`./scripts/check` took 784 to 830 s at mission 14's tip on the builder's
machine, with the `container` tests run; U2 cuts the synthetic source's
cost (decision 121), and every later unit adds as little as it can: a unit
that adds more than 60 s to one run says so in its body with the tests
that cost it; a run above 15 minutes is a finding with the times (HF-006,
HF-008, D-013), never a reason to drop a test. Every sub-agent that runs a
`container` test first runs `discotrade sandbox build`, as its own
foreground call with a 20-minute timeout, so that the tests run and do not
skip, and says in its report that they ran and the tag.

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
that checks a figure computes the expected value itself, without calling
the function under test. A test that starts a container carries the
`container` marker (decision 102 (g)), mounts only a job directory under
its temporary directory, and leaves no container behind (it removes, by
name, any its job left). The image is built only by `discotrade sandbox
build`, run as a setup step, never inside a test (decision 102 (f)).
`src/discotrade/workers/providers.py` is the only module under
`src/discotrade/workers/` that may import `httpx` or start a process
(decision 122 (f)); no test opens a socket, calls a real provider, a real
model or a real `claude` binary (I-11), and no key is read, logged, stored
or put in a prompt (I-13). Nothing of this mission is called from `run-day`
or `replay` (decision 118 (a)).

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S3.2a, the statement that
this mission does not close a milestone and runs gate M0, gate M2 and gate
M1 item by item again as decision 118 (b) says, and as carried items
REVIEW-14 should-fix 1 and notes 3, 4 and 7 (decision 119, U1), notes 11,
12 and 13 (decision 120, U0) and finding D-013 (decision 121, U2), each
with the unit that takes it), rewrite `meta/CHECKPOINT.md` for this
mission, append to `meta/journal.md`, and append to
`meta/findings/FINDINGS.md`, after its last line and in its form, the
HF-010 and HF-011 lines and the entry `HF-012` of decision 120. Nothing
else. Gate: the four files are committed and pushed in one `plan:` commit.

**U1 REVIEW-14's should-fix 1 and notes 3, 4 and 7 (decision 119;
decisions 115, 116 (b), 117 (c); DESIGN §13.1, §13.3, §13.4).**
`src/discotrade/workers/parse.py`, `src/discotrade/workers/registry.py`,
`tests/conftest.py` (the environment of the templates only), and tests
(`tests/test_workers_parse.py`, `tests/test_workers_registry.py`,
`tests/test_workers_profile.py`). Gate: REVIEW-14's example parses to
`no_description`, and so does a block followed by a fence line of another
language; every existing parser test passes unchanged; `sanitize('ab cd',
3) == 'ab'`; the profile's refusal of a contract change with no roll record
raises `ProfileError` on a store built in the test; every template of
`tests/conftest.py` that runs `init-state` or `run-day` passes
`GIT_ALLOW_PROTOCOL=file`. Seen to fail: the fence line taken as the
description; the strip done before the cut only; the roll-record refusal
removed. `./scripts/check` green.

**U2 The synthetic source's per-day cost (decision 121; finding D-013;
DESIGN §5.5, §17.1, §18.1; I-6).** `src/discotrade/sources/synth.py`, the
caller that builds the source only as the cache needs, and tests (a new
`tests/test_synth_cache.py`). Gate: a span fetched day by day with the
cache and in one fetch with the cache cleared stores byte-identical bar
files, index and roll records; a seed changed in a configuration copied
under the temporary directory gives a different series in the same
process; the seconds per replay day of the G1.3 scenario's first 30
calendar days at the parent and at the commit (decision 80 (d)'s method),
and `./scripts/check`'s wall time at both, in the body; no test's
assertion moved. Seen to fail: the cache keyed without the seed (the
changed-seed test goes red). A run at or above 12 minutes is appended to
D-013 with the times. `./scripts/check` green.

**U3 The providers and live check L3's offline behaviour (decision 122;
DESIGN §13.5, §19.3 L3; I-11, I-13).**
`src/discotrade/workers/providers.py` (new), `src/discotrade/cli.py` and
`src/discotrade/doctor.py` for `doctor --live workers` only,
`tests/test_offline.py` (`SUBPROCESS_FILES` only), and tests (new
`tests/test_workers_providers.py`, and the doctor's test file). Gate:
`ScriptedProvider` returns each model's files in order from its cursor,
continues from a given start, counts tokens by decision 122 (b)'s rule and
raises `ProviderError` when a model's files are used up;
`OpenAICompatProvider` through `httpx.MockTransport` sends the model, the
messages and `max_tokens`, reads the text, the tokens and the version
string, lists the models, and raises `ProviderError` on a status error, a
malformed body and a timeout, with no key in any error text, stored field
or log line; construction without a key or with an empty base URL is
refused with a text naming what is missing; `ClaudeWorkerProvider` against
a fake `claude` written by the test receives the flags recorded in the
body, the prompt on standard input and no `NEBIUS_API_KEY` in its
environment, and a non-zero exit, a non-JSON reply and a timeout are
`ProviderError`; `doctor --live workers` without the key prints one line
and exits 1 with no request made. Seen to fail: the key put into
`Completion.raw`; the corpus cursor not advanced; the tool denial dropped
from the fake's expected arguments. `./scripts/check` green.

**U4 `config/models.toml` and the pool (decisions 123, 124; DESIGN §13.6,
§4.3, §11.3, §15.2; R-14, R-21; I-5, I-10).** `config/models.toml` and
`tests/fixtures/config/models.toml` (new), `config/run.toml` and
`tests/fixtures/config/run.toml` (the `[workers]` table only),
`tests/fixtures/config_frozen.json` (new entries only), `config/HISTORY.toml`
only if the frozen-config test asks a new file for an entry,
`src/discotrade/config.py`, `src/discotrade/workers/pool.py` (new), and
tests (new `tests/test_workers_pool.py`, and the config tests). Gate:
`discotrade config check` passes and lists the models' unverified values;
the cutoff dates are 2024-06-30, 2026-01-31, 2026-02-28 and 2026-05-31 by
the test's own reading of R-14; an unknown key, a bad fallback, a duplicate
id and an empty pool are refused; every test decision 124 (f) lists, each
threshold read from `config/thresholds.toml`; the failure windows rebuilt
from a `calls.jsonl` written by the test. Seen to fail: rotation without
the cell index; `provider_error` rows counted as failures; a removal
undone on the next day. `./scripts/check` green.

**U5 The coordinator interface and its scripted form (decision 125;
DESIGN §14.1, §14.2, §14.3, §16.1 step 3; I-8).**
`src/discotrade/coordinator.py` (new) and tests (new
`tests/test_coordinator.py`). Gate: every test decision 125 (e) lists, the
states of the property test built in the test (approaches admitted from
fixture sources in several cells, one dormant), with their paper records
and metrics changed and nothing else. Seen to fail: a score added to
`CellStatus`; the tie going to the highest index; the out-of-list choice
accepted. `./scripts/check` green.

**U6 The day's generation (decision 126; DESIGN §13.4, §13.7, §10.2,
§12.2, §12.3, §16.2; R-25; I-5, I-6, I-13).**
`src/discotrade/workers/generate.py` (new), `src/discotrade/ledger.py` only
if a call row needs it, new fixture responses under
`tests/fixtures/responses/` and new strategy files under
`tests/fixtures/strategies/` as decision 126 (g) says,
`tests/fixtures/return_readers.toml` only for an entry decision 92's audit
finds, and tests (new `tests/test_workers_generate.py`). Gate: every test
decision 126 (g) lists, the `container` one run, not skipped; each call
row checked against the keys of decision 62; the response file read back
equal to what the provider returned. Seen to fail: the response written
after the parse; a second retry made; the stored response ignored and the
provider called again; the budget compared without the day's earlier
tokens. `./scripts/check` green.

**U7 The gate runs and the final report (decisions 118, 120, 121; DESIGN
§18.2).** After U6 is pushed and `./scripts/check` is green three times at
the tip (three calls, each wall time kept): `discotrade sandbox build`
(its tag kept), `./scripts/gate M0` as one foreground call,
`./scripts/gate M2` as one foreground call, then `./scripts/gate M1 G1.1`,
`G1.2`, `G1.3` and `G1.4`, each its own foreground call, every call with a
20-minute timeout, all at the same tip, each output verbatim with its wall
time; decision 118 (b) says what follows a FAIL, an item above 10 minutes
or an item that cannot finish. Then write `meta/FINAL-REPORT-15.md`
(drafted under `meta/drafts/`, moved in by this commit). The report gives:
what changed (sha per unit); `./scripts/check` wall time at the base,
after U2 and at the tip, and the seconds per replay day before and after
U2; the outputs of the gate runs under `## Regression gates`, verbatim,
with the tip, the tag and their wall times beside mission 14's; a `##
Models` section (the records of `config/models.toml` as written, the
cutoff date each gives, and where `base_url` came from); a `## Claude
worker flags` section (the flags `ClaudeWorkerProvider` passes and where
they were read); a `## Generation` section (for one fixture day on
`test_synth`: the call rows, verbatim, and the stored response file's
keys); for each of decisions 119 and 121 to 126, the test files and test
names that hold it; what the tests prove; NOT PROVEN (mandatory: that no
real provider, model or `claude` binary was called, which is live checks
L3 and L4; that the base URL, the model ids and the cutoffs are from
SPEC §17 and public pages, not verified; that the Claude worker's flags
are those of the builder's installed `claude` or, where none was found,
SPEC §17's, and match a real binary only as far as that; that the token
counts of the scripted provider are an estimate by rule, not a tokenizer;
that nothing of this mission is called from `run-day` or `replay`, so
retry, storage and budget inside a day are step S3.2b's to prove; that
the speed figures are from the builder's machine; what remains of
FINAL-REPORT-14's NOT PROVEN); the findings filed and answered; and a `##
Review items` table with one row each for REVIEW-14 should-fix 1, notes 3,
4, 7, 11, 12 and 13, and finding D-013: the item, its resolution (the unit
and decisions item), and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs, with the `container` tests run, not skipped, and its
  wall time is in the report beside mission 14's.
- `./scripts/gate M0`, `./scripts/gate M2` and `./scripts/gate M1 G1.1` to
  `G1.4` at the pushed tip print their PASS lines; the outputs and times
  are in the report beside mission 14's, and any M1 item above 10 minutes
  is recorded under D-014.
- A fence line after the last block is no description; a sanitized text
  ends in no whitespace (REVIEW-14 should-fix 1, note 3).
- The synthetic source stores byte-identical files with its cache, and a
  changed record generates again (decision 121).
- Three providers behind one protocol, tested with a scripted corpus, a
  mock transport and a fake `claude`; no key leaves the code that reads it.
- `config/models.toml` holds SPEC §17's three pool models and the NVIDIA
  fallback with `verified = false`, its values in the frozen map; the pool
  rotates by trading-day ordinal plus cell index, falls back per maker,
  removes a failing model for good with a `model_removed` event, and
  derives its windows from `calls.jsonl` alone.
- The coordinator's input has no score (the property test), the scripted
  choice and the fallback for an out-of-list cell behave, and the brief is
  sanitized and capped.
- The day's generation makes at most two calls, stores every response in
  full before parsing it, replays a stored response without a call, stops
  at the token budget with a `budget` row and a `token_budget` event, and
  writes one call row per attempt with the keys of decision 62.
- No file under `tests/gates/` or `tests/fixtures/rejected/` changed; no
  existing value of a frozen file changed in this mission (`git diff` of
  `config/instruments/`, `config/tracks/`, `config/calendars/`,
  `config/thresholds.toml`, of the existing values of `config/run.toml`,
  of the existing entries of `tests/fixtures/config_frozen.json` and of
  the existing records under `tests/fixtures/config/` against the base is
  empty, save the added `[workers]` tables and new entries).
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- No test uses the network, a secret or the wall clock; no state or job
  directory is written inside the repository; no file under `src/` names
  a market, a contract root or a venue; no test builds the image.
- `meta/FINAL-REPORT-15.md` exists with `## Regression gates`, `##
  Models`, `## Claude worker flags`, `## Generation`, NOT PROVEN, and the
  review-items table.
