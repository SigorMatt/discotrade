# BUILDER-7-PROMPT — discotrade mission 7: the state directory, the health log, the decision journal and the day loop for journaling (step S1.1)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 7. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-7.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 7 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ; items 47 to 57 are new for this mission and every unit below
cites them; items 1 to 46 still bind, and items 2 to 5, 7, 16, 19 to 26,
36, 37 and 39 are the ones this mission's code meets), `DESIGN.md` (§9,
§15.2, §16.1 steps 1 and 2, §16.2 are this mission; §3 for the command
line; §5.2, §5.4, §5.6 for what step 1 runs; §6.2, §7 and §8 for what a
journal row holds; §12.4 for which sources may run outside the sandbox;
§18.1; read §2 twice, in particular I-5, I-6, I-11, I-12 and I-14),
`meta/reviews/REVIEW-6.md` (its `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-6.md`, `meta/BACKLOG.md` (the REVIEW-3 note on the
socket backstop, now item 47), `meta/findings/FINDINGS.md`, and
`meta/CHECKPOINT.md` (a unit in progress means §R first). This is roadmap
step S1.1.

---

## Mission

Build roadmap step S1.1: the state directory with `discotrade
init-state`, the health log, the approaches' frozen records, the decision
journal with its content hashes and idempotent days, the paper records,
the day loop for journaling (`discotrade run-day`, daily steps 1 and 2 on
a synthetic source) with its lock, staging and state commit, and
`discotrade journal recompute`, all reading time through the injected
clock; and make the socket backstop hold outside function-scoped tests
(the REVIEW-3 note carried to this step). Cut the step as decisions 47 to
55 say: the subjects are approaches only (controls are step S1.2's),
approach sources run in-process only when they are repository files
(decision 48; the sandbox is step S2.2's), and the parts of §16.1 and
§16.2 that decision 50 names are step S4.2's. This mission does not close
a milestone and adds no test under `tests/gates/`. Close REVIEW-6's
should-fix item in the final report (decision 56). Add nothing else.
Where a cited decision changes what an existing test asserts, the unit
changes that assertion and says so in its commit body; every other
existing test stays unchanged in what it asserts. Finish with a report
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
- Your final reply begins with exactly one of: `VERDICT: mission 7
  finished` | `VERDICT: mission 7 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-12.md`
(the items the unit names). No unit changes a value in a frozen file
(`config/instruments/`, `config/tracks/`, `config/calendars/`,
`config/thresholds.toml`, `tests/fixtures/config_frozen.json` entries
that already exist): a value believed wrong is a finding. No unit changes
an existing record under `tests/fixtures/config/`; a unit that needs a
different configuration (for example a lower gap limit to raise
`data_gaps`) builds it under the test's temporary directory, or adds a
new fixture file and says so in its body. Where a unit's code already
exists and is right, so that a new test cannot be seen to fail first
against the parent, the sub-agent instead makes, in its worktree and
without committing it, the wrong change the test is meant to catch, sees
the test fail, reverts it, and names that change in the commit body. Each
unit names below the wrong changes its tests must be seen to fail on;
these are made and reverted the same way and named in the body.
`./scripts/check` and `./scripts/gate` are run in the foreground with an
explicit timeout of at least 20 minutes (finding HF-006), and each
sub-agent runs `./scripts/check` three times before its commit and says
in its report how many runs were green.

Every test of this mission writes state only under a pytest temporary
directory, reads time only through a `FixedClock` or `--as-of`, and runs
the `discotrade` command in-process through the function the console
script calls, except where it tests the console script itself. A test
that runs `git` passes `GIT_ALLOW_PROTOCOL=file` in its environment and
uses local paths only (decision 47). Every journal and paper test runs on
a synthetic source from `tests/fixtures/config/` (`test_mixed` for the
roll, the no-short instrument, the proportional fee and dropped bars;
`test_synth` where a four-instrument basket is wanted), with every seed
written in the test file.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S1.1, and as carried items
the REVIEW-3 note on the socket backstop (decision 47, taken by U1) and
REVIEW-6 should-fix 1 (decision 56, taken by U6), each with the unit that
takes it), rewrite `meta/CHECKPOINT.md` for this mission, append to
`meta/journal.md`, and append to `meta/findings/FINDINGS.md`, under its
"hands findings" heading, a finding with the next free `HF-###` number
recording REVIEW-6's `hands:` note: the review protocol's step 2 (revert
the non-test files of a unit commit and expect red) proves nothing when a
unit commit changes only tests, as all four of mission 6's did; the
reviewer's sub-agents made the wrong changes the commit bodies name
instead, which the protocol does not name as a path; and each sub-agent
ran `./scripts/check` once, not three times (severity low, component the
review protocol of hands' templates and this project's
`meta/REVIEW-PROTOCOL.md`, status open). Nothing else. Gate: the four
files are committed and pushed in one `plan:` commit.

**U1 The socket backstop outside function-scoped tests (REVIEW-3 note;
decisions 20, 47; I-11; DESIGN §18.1).** `tests/conftest.py` and a new
test file (for example `tests/test_offline.py`); no file under `src/`.
Gate: tests show that an attempt to open a network connection fails with
`SocketBlocked` inside a module-scoped fixture and inside a
session-scoped fixture, and through `_socket` used directly; that a test
marked `network` (run in a scratch pytest session, as
`tests/test_gate_script.py` runs its scratch suites, so that no real
connection is attempted) is left alone; and that the test listing the
files under `tests/` and `src/` whose text contains `subprocess` or
`os.system` passes on today's tree and fails, naming the file, when a
file with a subprocess call is added to a scratch copy of its list's
input. Every existing test of `tests/conftest.py`'s behaviour (decision
20, the gate markers, the skip-is-failure rule) asserts what it asserts
at the base. Seen to fail: the backstop back at function scope (the
module-scoped fixture test goes red); `_socket` left unguarded (its test
goes red). `./scripts/check` green.

**U2 The state directory, the lock, the state commit and the health log
(decisions 7, 50, 52, 55; DESIGN §3, §9.1, §15.2, §16.2; I-5, I-12,
I-14).** `src/discotrade/state.py`, `src/discotrade/cli.py` (the
`init-state` subcommand), a new `tests/test_state.py`, and
`tests/test_cli.py` only to add to it. Gate: tests show that `discotrade
init-state --state <dir>` creates the directory as a Git repository with
a `.gitignore` that ignores `bars/**/*.parquet`, the staging directory
and the lock, and commits it; that a second run changes nothing and exits
0; that a non-empty directory that is not a state directory exits 1 and
one inside a code repository exits 2 (decision 7); that a second lock
taken while one is held fails naming it, and that the lock is released
after a failure inside it; that a state commit carries the message `run
<track> <date>`, the author `discotrade <discotrade@invalid>` and author
and committer dates equal to the injected clock's instant, and that a
commit with nothing changed is not made; that the health log appends
`HealthEvent.to_json()` lines atomically with every earlier line
byte-identical, and does not append a line already present. Seen to
fail: the lock created without exclusivity; the health log's duplicate
check removed; the commit dates taken from the wall clock. `./scripts/check`
green; `discotrade init-state --help` exits 0.

**U3 Approaches and the decision journal (decisions 24, 25, 39, 48, 49,
51; DESIGN §6.2, §7, §9.1, §9.2; I-5, I-6, I-7).** `src/discotrade/state.py`
(the approach writer), a new `src/discotrade/journal.py`,
`src/discotrade/backtest.py` and `src/discotrade/executor.py` only where
the journal must share their one implementation of §7 (every existing
test of them unchanged), and new `tests/test_journal.py`. Gate: tests
show the approach id of decision 48 against a value computed in the test
from its definition; `meta.json` with every field §9.1 lists; a source
whose sha256 is not that of a file under `reference/` or
`tests/fixtures/` refused, naming the approach; a day's rows with the
columns, first-row rule and carry of decision 49 (the first row of each
instrument flat, every later row's `position` equal to the previous
row's `target_next` across a day boundary); a day file written once with
its `index.jsonl` line (date, rows, content hash, keys `subject`,
`instrument`, `ts`); a re-run of a day with equal rows writing nothing
(file bytes and index unchanged); a re-run with unequal rows (made by
the test, for example by changing the stored previous day's last
`target_next` it starts from) leaving the file untouched and returning a
`journal_mismatch` event naming the day and subject; a day with no
subject writing an empty file and its index line; and an approach of each
of the three reference strategies, journaled day by day on `test_mixed`
over a span holding the SYNA roll, equal under decision 39's rule to the
module's evaluation of the same strategy over the window from its first
journaled day to its last, field for field (`h`, `p`, `gross`, `trade`,
the four components, `cost` as their sum, `net_1x`, `net_2x`). Seen to
fail: the position reset to 0 at the start of each day; the first row's
`position` taken as the target instead of 0; the re-run writing the file
again. `./scripts/check` green; `./scripts/gate M0 G0.1` still passes
when `backtest.py` or `executor.py` changed.

**U4 `run-day` and the paper records (decisions 2, 3, 19, 50 to 53, 55;
DESIGN §9.3, §15.2, §16.1 steps 1 and 2, §16.2; I-6, I-12).** New
`src/discotrade/daily.py` and `src/discotrade/paper.py`,
`src/discotrade/cli.py` (the `run-day` subcommand with `--day`), and new
`tests/test_daily.py` and `tests/test_paper.py`. Gate: tests show, on a
state directory made by `init-state` with approaches written as decision
48 says, that `run-day` over consecutive trading days fetches the bars,
runs the gap check and updates rolls (step 1), writes the journal file,
its index line and `paper/<track>/daily.parquet` for each day, and makes
one commit `run <track> <date>` per day; that running a finished day
again writes nothing and makes no commit (`git status` clean, commit
count unchanged, health log unchanged); that a skipped trading day
between the last journaled day and `D` makes `run-day` exit 1 naming it
and write nothing; that a day failing in step 2 (an approach whose
source is not a repository file) leaves the journal, its index and the
paper records untouched, makes no commit, releases the lock and exits 1;
that a `data_gaps` alert is appended to the health log when the gap
fraction of W or T for `D` exceeds `gaps.max_fraction` (on a
configuration under the test's temporary directory), and the notices of
step 1 are appended once; that a state directory without `init-state` is
refused; that two fresh state directories run for the same days and
`--as-of` give equal journal and paper content hashes and equal health
logs (decision 55); and that rebuilding the paper records from the
journal gives the same content hash, with `gross`, `net_1x`, `net_2x` as
decision 23's daily mean and `trades` counting rows with `trade > 1e-9`.
Seen to fail: the re-run appending a second index line; the lock left
held after a failed day; the paper `trades` counting rows with `trade >
0`. `./scripts/check` green; `discotrade run-day --help` exits 0.

**U5 `journal recompute` (decision 54; DESIGN §9.4, §15.2; I-6).**
`src/discotrade/journal.py`, `src/discotrade/cli.py` (the `journal
recompute` subcommand with `--all`), new `tests/test_journal_recompute.py`.
Gate: tests show that after `run-day` over consecutive days `discotrade
journal recompute --all` matches every (day, subject) pair, exits 0 and
writes nothing; that with one stored journal file changed by the test in
one field of one row, it exits 1, prints that pair, appends one
`journal_mismatch` event naming it to the health log, and changes no
journal file; that without `--all` it recomputes
`journal.recompute_sample` pairs (or every pair when fewer exist) drawn
by the generator seeded with `D` as `YYYYMMDD`, the same pairs on every
run for the same `D` and pairs from days before `D` only. Seen to fail:
a recompute that reads the stored rows instead of recomputing them; the
sample seeded with anything but `D`. `./scripts/check` green; `discotrade
journal recompute --help` exits 0.

**U6 Final report.** `meta/FINAL-REPORT-7.md` (drafted under
`meta/drafts/`, moved in by this commit). First, after `./scripts/check`
is green three times at the pushed tip, run `./scripts/gate M0` there
once, in the foreground with a timeout of at least 30 minutes, and paste
its output verbatim under a heading `## M0 still passes` (M0 is met; this
shows the mission did not break it). The report gives: what changed (sha
per unit); for each of decisions 47 to 55, the test file and test names
that hold it; what the tests prove; a `## Correction of FINAL-REPORT-6`
section in decision 56's words; NOT PROVEN (mandatory: that the subjects
are approaches only until step S1.2 adds the controls and the lifecycle;
that approach sources run in-process and only when they are repository
files until step S2.2; that step 1's writes are not staged and the
retry, `run_failed`, the push and the catch-up are step S4.2's; that the
weekly recomputation is not yet wired into the day; that `run-day` is
proven on synthetic sources only; that the `clean` flag of the paper
records is step S1.2's; what remains of FINAL-REPORT-6's NOT PROVEN);
the findings filed and answered; and a `## Review items` table with one
row each for REVIEW-6 should-fix 1 and the REVIEW-3 note on the socket
backstop: the item, its resolution (the unit and decisions item), and
the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M0` at the pushed tip prints `G0.1` to `G0.4 PASS` and
  `gate M0: PASS`, and its output is in the report.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- `discotrade init-state`, `discotrade run-day` and `discotrade journal
  recompute` exist, each with `--help`, and each takes `--state`,
  `--track`, `--config` and `--as-of` as DESIGN §3 says.
- A re-run of a finished day writes nothing: no file, no index line, no
  health line, no commit (I-6).
- An approach journaled day by day equals the module's window evaluation
  of the same strategy, field for field under decision 39's rule.
- `journal recompute --all` matches every pair on an unaltered journal and
  names the pair on an altered one.
- A network connection fails inside module- and session-scoped fixtures
  and through `_socket`; every file that launches a subprocess is in the
  listing test's list.
- No value of a frozen file changed in this mission (`git diff` of
  `config/`, of the existing entries of `tests/fixtures/config_frozen.json`
  and of the existing records under `tests/fixtures/config/` against the
  base is empty).
- No test uses the network, a secret or the wall clock; no state is
  written inside the repository; no file under `src/` names a market, a
  contract root or a venue.
- `meta/FINAL-REPORT-7.md` exists with `## M0 still passes`, the
  correction of FINAL-REPORT-6, NOT PROVEN, and the review-items table
  covering REVIEW-6 should-fix 1 and the REVIEW-3 socket-backstop note.
