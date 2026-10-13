# BUILDER-10-PROMPT — discotrade mission 10: the day loop's speed, REVIEW-9's should-fix items and static exposure (step S2.0a)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 10. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-10.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 10 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-14.md` (items 76 to 82, new for this
mission; every unit below cites them),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-3, O-4 and
O-10 are this mission, O-1 and O-2 still bind; the rest is later steps'
and is read so that nothing built here contradicts it),
`meta/decisions/decisions-2026-10-12.md` (items 1 to 75 still bind; items
5, 18, 23 to 25, 31, 35, 39, 47 to 55, 62 to 64 and 69 to 74 are the ones
this mission's code meets), `DESIGN.md` (§5.2, §9.2, §9.3, §16.1, §16.2,
§16.4 and §18.2 are this mission; §4.1 for T, §7.2 and §8 for the returns,
§10.3 for admission; read §2 twice, in particular I-2, I-5, I-6, I-11 and
I-12), `meta/reviews/REVIEW-9.md` (its `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-9.md`, `meta/BACKLOG.md`, `meta/findings/FINDINGS.md`
(D-007, D-009), and `meta/CHECKPOINT.md` (a unit in progress means §R
first). This is roadmap step S2.0a.

---

## Mission

Build roadmap step S2.0a as decisions 76 to 82 cut it. First the day
loop's speed (O-3, decision 80): measure where a replay day's time goes and
bring it down, without changing anything a day computes or stores, toward
each item of gate M1 under 10 minutes. Then close REVIEW-9's three
should-fix items (decisions 78 and 79) and confirm finding D-007 by test
(decision 77). Then build O-4's definitions as one producer function and
its derived records (decision 81), read by no rule yet. Then run gate M1
again item by item and gate M0 (decision 82), and report the times before
and after. This mission closes no milestone. The lifecycle on the adjusted
measure, the register of readers and the update of G1.3 are step S2.0b's
(mission 11); the grid, the sandbox, workers and alerts are later steps'.
Add nothing else. Where a cited decision changes what an existing test
asserts, the unit changes that assertion and says so in its commit body;
every other existing test stays unchanged in what it asserts, and no test
under `tests/gates/` changes. Finish with a report whose first line the
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
- Your final reply begins with exactly one of: `VERDICT: mission 10
  finished` | `VERDICT: mission 10 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-14.md`
and the items of `meta/decisions/decisions-2026-10-12.md` and of
`meta/decisions/decisions-2026-10-13-owner.md` that the unit names. No unit
changes a value in a frozen file (`config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit creates `config/models.toml` (step
S3.2's, decision 61). No unit changes an existing record under
`tests/fixtures/config/` (the gate configuration is built under a test's
temporary directory with `tests/fixtures/config/thresholds_gate.toml`
copied in unchanged, decision 72); a unit that needs something new adds a
new fixture file and says so in its body. No unit changes a file under
`tests/gates/` (decision 82). Where a unit's code already exists and is
right, so that a new test cannot be seen to fail first against the parent,
the sub-agent instead makes, in its worktree and without committing it,
the wrong change the test is meant to catch, sees the test fail, reverts
it, and names that change in the commit body. Each unit names below the
wrong changes its tests must be seen to fail on; these are made and
reverted the same way and named in the body.

Long commands (finding HF-006): every run of `./scripts/check` or
`./scripts/gate` is its own foreground Bash call with an explicit timeout
of 20 minutes, the tool's maximum; never chain two such runs in one call,
and never let one run in the background. Each sub-agent runs
`./scripts/check` three times before its commit, as three calls, and says
in its report how many runs were green. Tests that `./scripts/check` runs
replay a few days at most; the long replays are the gate tests'. Timing
measurements (decision 80 (d)) are foreground calls too, one measurement
per call, never two at once, and none while another heavy process runs.

Every test of this mission writes state only under a pytest temporary
directory, reads time only through a `FixedClock` or `--as-of` (or the
replay's clock, decision 72), and runs the `discotrade` command in-process
through the function the console script calls, except where it tests the
console script itself. A test that runs `git` passes
`GIT_ALLOW_PROTOCOL=file` in its environment and uses local paths only
(decision 47), and a new test file that runs git is added to
`SUBPROCESS_FILES` in `tests/test_offline.py`. Every test that runs days
runs on a synthetic source from `tests/fixtures/config/` (`test_mixed` or
`test_synth`, with the gate configuration where it says so), with every
seed and date written in the test file. Each rule is unit-tested at its
production value from `config/thresholds.toml`; a test may also use a
lower value from a configuration copied under its temporary directory,
and says so.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S2.0a, the statement that
this mission closes no milestone and runs gate M1 again as decision 82
says, and as carried items REVIEW-9 should-fix 1 (decision 78, taken by
U3), should-fix 2 and 3 (decision 79, taken by U4), finding D-007
(decision 77, taken by U4) and owner decision O-3 (decision 80, taken by
U1 and U2), each with the unit that takes it), rewrite
`meta/CHECKPOINT.md` for this mission, append to `meta/journal.md`, and
append to `meta/findings/FINDINGS.md` the status line `D-007 status
(appended <date>, mission 10 U0): Status: answered
meta/decisions/decisions-2026-10-14.md (item 77)`. Nothing else. Gate: the
four files are committed and pushed in one `plan:` commit.

**U1 Where a replay day's time goes, and the bar files' hashes (O-3;
decision 80; DESIGN §5.2, §9.2, §16.1, §18.2; decisions 18, 31, 35).**
`src/discotrade/bars/store.py`, `src/discotrade/daily.py`,
`src/discotrade/replay.py` and the other `src/` files a measured cost lies
in, and their tests (`tests/test_bar_store.py`, `tests/test_daily.py`,
`tests/test_replay.py`, or a new file). First measure at the base, as
decision 80 (d) says, and profile one replay day of each of the two
measured replays. Then remove the largest cost the profile shows; mission
9 measured about 40% of a day in content hashes of bar files recomputed on
every read, and decision 80 (b) says how often a file may be hashed. Gate:
tests show that within one day run each listed month file is hashed at
most once whatever the number of subjects that read it; that a month file
whose bytes are changed between two days of one `replay` is refused by the
next day's first read of it, the day failing as a revised data point does
today; that every existing test of the store, the gap check, the rolls,
the day and the replay asserts what it asserts today. The commit body
gives decision 80 (a)'s identical-state comparison, (d)'s two
measurements before and after, the profile after, and the one-year time
the after-figure implies for each gate M1 item. Seen to fail: the
per-day-run hash result kept for the whole process (the revised-file test
goes red); the verified result keyed by path only and used for a file
appended to during the day, if the day appends (or, if it does not, a
second wrong change the sub-agent names that lets a revised file be read).
`./scripts/check` green.

**U2 The rest of the measured cost (O-3; decision 80; DESIGN §7, §9.2,
§9.3, §10.4, §16.1).** The `src/` files U1's profile after names as the
largest remaining costs (mission 9 measured about 22% in
`backtest.score` and 13% in journal row hashing, and the table's cost
grows with the history), and their tests. Bring them down without
changing anything a day computes or stores (decision 80 (a), (b), (c)).
Gate: decision 80 (a)'s identical-state comparison at this unit's parent
and commit; tests that pin, for each piece of code changed, its result
against the parent's way of computing it on at least one case written in
the test (for example a journal content hash, a control's positions over a
redraw, a table row), at 1e-12 or byte for byte where the stored form is
bytes; every existing test asserts what it asserts today. The commit body
gives (d)'s two measurements before and after, the profile after, and the
one-year time the after-figure implies for each gate M1 item; when that
time is above 10 minutes for an item, it says by how much and what the
profile says remains. Seen to fail: for each piece of code changed, a
wrong change the sub-agent names that the pinning test catches (for
example a hash over rows in another order). `./scripts/check` green.

**U3 REVIEW-9 should-fix 1: the paper update heals an interrupted day
(decision 78; DESIGN §9.3, §16.2).** `src/discotrade/paper.py`,
`src/discotrade/daily.py`, and `tests/test_daily.py` or
`tests/test_paper.py`. Gate: a test runs days through `run-day` or
`replay`, removes one journaled day's rows from the paper file (as an
interrupted move would leave it), runs the next day, and shows the paper
file equal to a full rebuild's content hash, with the removed day's
records and portfolio rows back; a second test leaves an extra date in the
paper file and shows the same; the existing six-day test (the file equals a
rebuild after every day) still passes; the docstrings say "equal to a
rebuild" only with the rule. Seen to fail: the old fallback (rebuild only
when the stored maximum date is on or after `D`). `./scripts/check` green.

**U4 REVIEW-9 should-fix 2 and 3, and finding D-007 (decisions 77, 79;
DESIGN §4.1, §10.3, §16.1, §16.4; decisions 51, 63, 72, 73).**
`tests/test_replay.py` and `tests/test_replay_candidates.py` (or new test
files), and new fixture files under `tests/fixtures/scenarios/` or
`tests/fixtures/strategies/` if the admission case needs them; no file
under `src/` unless a test shows the code wrong, which is then a finding
first. Gate: the three tests of decision 79, each as that item says.
Seen to fail: the refusal narrowed to `D`'s own bars (79 (a)); T as the
last `t_days` trading days (79 (b)); both made in the worktree and
reverted. `./scripts/check` green.

**U5 Static exposure, unit return and the adjusted series (O-4; decision
81; DESIGN §7.2, §8, §9.2, §9.3; decisions 23, 24, 25, 39, 78).**
`src/discotrade/paper.py`, `src/discotrade/daily.py` (the derived records
staged with the day, if any are stored), and tests (`tests/test_paper.py`
or a new `tests/test_exposure.py`). Gate: tests show, on `test_mixed`
(SYNA rolls and has no weekend bars, SYNX trades every day) over a window
holding a roll and a weekend, for an approach and for a random slot, that
the unit returns equal the journal `gross` of a buy-and-hold row on the
same bars, that `hbar_i(W)`, the static exposure, the gross timing return
and the exposure-adjusted `net_1x` and `net_2x` equal the test's own
computation from the journal parquet files and the stored bars under
decision 39's rule, written in the test without the function under test;
that the window's average positions change when `W` changes and the
function uses the `W` it is given; that a buy-and-hold control's gross
timing return is 0 to 1e-12 on every day of any window that does not hold
its instrument's first journaled row; that a subject holding one constant
position has an adjusted series of zeros, whose Sharpe (`metrics.py`) is
not a number; that `net_1x` minus its adjusted value equals `gross` minus
the gross timing return on every day (costs not adjusted); and, if
records are stored, that they are staged with the day, that a re-run
writes nothing, that a rebuild gives the same content hash and that
decision 78's heal holds for them. The commit body states the window,
subjects and instruments the tests use and does not claim more. Seen to
fail: `hbar_i` taken over the subject's whole paper record instead of
`W`; the unit return on raw prices across a roll; the daily mean taken
over the instruments with a bar on `D` instead of all `N` (decision 23).
`./scripts/check` green.

**U6 Gate M1 again, and gate M0 (decision 82; O-2, O-3; DESIGN §18.2).**
No file changes unless an item fails. After `./scripts/check` is green
three times at the pushed tip (three calls), run `./scripts/gate M1
G1.1`, `G1.2`, `G1.3` and `G1.4`, each its own foreground call with a
20-minute timeout, all at that tip, then `./scripts/gate M0` once the same
way; keep each output verbatim with its wall time for the report. If an
item prints FAIL, decision 82 says what follows. If an item passes above
10 minutes, file decision 80 (e)'s finding (the next free `D-###`) with
each item's time and U2's profile, in a `findings:` commit of
`meta/findings/FINDINGS.md` only, and weaken nothing. If an item cannot
finish within its 20-minute call, do not start it again in the background:
reply `VERDICT: question` naming the times measured.

**U7 Final report.** `meta/FINAL-REPORT-10.md` (drafted under
`meta/drafts/`, moved in by this commit). The report gives: what changed
(sha per unit); a `## Speed` section with, for U1 and U2, decision 80
(d)'s measurements before and after and the profiles, and a table of each
gate M1 item's time in mission 9 and in this mission; the outputs of the
four `./scripts/gate M1 G1.<n>` calls (under a heading `## Gate M1`) and of
`./scripts/gate M0` (under `## M0 still passes`) from U6, verbatim, with
the tip they ran at and their wall times; for each of decisions 77 to 81,
the test file and test names that hold it; what the tests prove; NOT
PROVEN (mandatory: that the adjusted series is read by no rule yet, step
S2.0b's; that O-5 to O-9 and O-14 are not built; that the speed figures are
from the builder's machine and the per-day cost still grows with the
history; that a stored bar file is now hashed once per day run, not on
every read; what remains of FINAL-REPORT-9's NOT PROVEN); the findings
filed and answered; and a `## Review items` table with one row each for
REVIEW-9 should-fix 1, 2 and 3, finding D-007 and owner decision O-3: the
item, its resolution (the unit and decisions item), and the sha. Then the
verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M1 G1.1` to `G1.4`, each run on its own at the pushed
  tip, print their item PASS line, and `./scripts/gate M0` prints `G0.1`
  to `G0.4 PASS` and `gate M0: PASS`; the outputs and times are in the
  report beside mission 9's, and any item above 10 minutes has its
  finding.
- For each speed unit, the fixed replay's state at its parent and at its
  commit is identical byte for byte outside `.git/` (decision 80 (a)).
- Every reader still refuses a bar file whose hash does not match the
  index, at the latest on the next day run's first read of it.
- The paper file equals a full rebuild after a day whose paper rows were
  lost, on the next day (decision 78).
- The refusal of decision 77 and the T days of decision 73 are pinned by
  tests (decision 79).
- O-4's function exists in `paper.py`, matches the tests' own computation,
  and is read by no rule, statistic, table field or gate.
- A re-run of a finished day writes nothing: no file, no index line, no
  ledger, pool, stats, table or derived record change, no health line, no
  commit (I-6).
- No file under `tests/gates/` changed; no value of a frozen file changed
  in this mission (`git diff` of `config/`, of the existing entries of
  `tests/fixtures/config_frozen.json` and of the existing records under
  `tests/fixtures/config/` against the base is empty), and
  `config/models.toml` does not exist.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- No test uses the network, a secret or the wall clock; no state is
  written inside the repository; no file under `src/` names a market, a
  contract root or a venue.
- `meta/FINAL-REPORT-10.md` exists with `## Speed`, `## Gate M1`, `## M0
  still passes`, NOT PROVEN, and the review-items table.
