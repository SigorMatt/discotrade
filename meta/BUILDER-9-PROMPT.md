# BUILDER-9-PROMPT — discotrade mission 9: the table, the combined portfolio, rank persistence in the day loop, the replay and the M1 gate (step S1.3)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 9. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-9.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 9 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ; items 66 to 75 are new for this mission and every unit below
cites them; items 1 to 65 still bind, and items 9, 19, 23, 25, 30, 39 to
41, 47 to 55 and 58 to 64 are the ones this mission's code meets),
`DESIGN.md` (§10.4, §10.5, §11.1, §16.4 and §18.3's M1 items are this
mission; §9, §10.1 to §10.3, §11.2 to §11.4, §16.1, §16.2 and §18.2 for
the day, the ledgers, the statistics and the gate configuration; §4.1 for
the track's T, blocks and epoch; §17.1; read §2 twice, in particular I-3,
I-5, I-6, I-11 and I-12), `meta/reviews/REVIEW-8.md` (its `## Should-fix`
and `## Notes`), `meta/FINAL-REPORT-8.md`, `meta/BACKLOG.md`,
`meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a unit in progress
means §R first). This is roadmap step S1.3.

---

## Mission

Build roadmap step S1.3 as decisions 66 to 75 cut it: close REVIEW-8's two
should-fix items (decisions 66, 67) and add the test decision 68 (b)
asks; the replay command of §16.4 (decision 72); the two performance items
of `meta/BACKLOG.md` (REVIEW-1's `bars fetch` and synthetic regeneration,
REVIEW-2's `recover`); the combined portfolio of §10.5 in the paper
records and rank persistence in the day loop (decisions 69, 70); the table
of §10.4 (decision 71); scripted candidates fed through the replay
(decision 73); and the gate tests of G1.1 to G1.4 (decision 74). This
mission closes milestone M1. Scoring a candidate on T is step S3.2's;
running approaches in the sandbox is step S2.2's; staging of step 1's
writes, the retry, catch-up and the weekly recomputation are step S4.2's.
Add nothing else. Where a cited decision changes what an existing test
asserts, the unit changes that assertion and says so in its commit body;
every other existing test stays unchanged in what it asserts. Finish with
a report whose first line the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 9
  finished` | `VERDICT: mission 9 blocked <unit>` | `VERDICT: question <one
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
that already exist): a value believed wrong is a finding. No unit creates
`config/models.toml` (step S3.2's, decision 61). No unit changes an
existing record under `tests/fixtures/config/` (the gate configuration is
built under a test's temporary directory with
`tests/fixtures/config/thresholds_gate.toml` copied in unchanged,
decision 72); a unit that needs something new adds a new fixture file (a
strategy under `tests/fixtures/strategies/`, a scenario under
`tests/fixtures/scenarios/`) and says so in its body. Where a unit's code
already exists and is right, so that a new test cannot be seen to fail
first against the parent, the sub-agent instead makes, in its worktree and
without committing it, the wrong change the test is meant to catch, sees
the test fail, reverts it, and names that change in the commit body. Each
unit names below the wrong changes its tests must be seen to fail on;
these are made and reverted the same way and named in the body.

Long commands (finding HF-006): every run of `./scripts/check` or
`./scripts/gate` is its own foreground Bash call with an explicit timeout
of 20 minutes, the tool's maximum; never chain two such runs in one call,
and never let one run in the background. Each sub-agent runs
`./scripts/check` three times before its commit, as three calls, and says
in its report how many runs were green. Tests that `./scripts/check` runs
replay a few days at most; the long replays are the gate tests'.

Every test of this mission writes state only under a pytest temporary
directory, reads time only through a `FixedClock` or `--as-of` (or the
replay's clock, decision 72), and runs the `discotrade` command in-process
through the function the console script calls, except where it tests the
console script itself. A test that runs `git` passes
`GIT_ALLOW_PROTOCOL=file` in its environment and uses local paths only
(decision 47). Every test that runs days runs on a synthetic source from
`tests/fixtures/config/` (`test_mixed` or `test_synth`, the gate tests on
`test_synth` with the gate configuration), with every seed and date
written in the test file. Each rule is unit-tested at its production value
from `config/thresholds.toml`; a test may also use a lower value from a
configuration copied under its temporary directory, and says so.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S1.3, the statement that
this mission closes milestone M1, and as carried items REVIEW-8
should-fix 1 and 2 (decisions 66, 67, both taken by U1) and the two
performance items of `meta/BACKLOG.md` (taken by U3), each with the unit
that takes it), rewrite `meta/CHECKPOINT.md` for this mission, and append
to `meta/journal.md`. Nothing else. Gate: the three files are committed
and pushed in one `plan:` commit.

**U1 REVIEW-8's should-fix items and decision 68 (b) (decisions 63, 66,
67, 68; I-11; DESIGN §10.3, §18.1).** `tests/test_lifecycle.py`,
`tests/test_offline.py`, and `tests/conftest.py` only if the scratch
session's fixture needs it; no file under `src/` unless the lifecycle is
found wrong, which is then a finding first. Gate: a test shows step 3
waiting `revival_min_dormant_days` (production value 5) trading days of
the track across a span holding days that are not trading days, staying
dormant on a day with five or more calendar days but fewer than five
trading days, returning on the fifth trading day (decision 66); the
scratch session's `network`-marked test calls for real only the lookups
decision 67 lists, its comment says why each needs no resolver, and
`gethostbyaddr` is shown left alone there by identity and refused again in
the following unmarked test; a test through the lifecycle functions shows
decision 68 (b): an approach that returns on `D` and is displaced later on
`D` has both rows dated `D`, in order, and a later count of its dormancy
starts from the second. Every other assertion of the three files keeps
what it asserts. Seen to fail: revival counting calendar days (`(D -
since).days`); `gethostbyaddr` replaced in the scratch session by a
function that is not the original (the identity assertion goes red).
`./scripts/check` green.

**U2 The replay command (decisions 19, 51, 55, 72; DESIGN §16.4, §16.1,
§3; I-6, I-12).** `src/discotrade/cli.py`, `src/discotrade/daily.py` (the
day function the replay calls, unchanged in what it does), a new
`src/discotrade/replay.py` if the sub-agent prefers it to a function in
`daily.py`, and a new `tests/test_replay.py`. Gate: tests show, on
`test_mixed` and on `test_synth` with the gate configuration over a few
days each, that `replay --from A --to B` processes exactly the track's
trading days from `A` to `B` in ascending order, each with the injected
clock at the close of the last expected bar of that day, and that its
state equals, file for file and byte for byte outside `.git/`, the state
that the same days run one by one through `run-day` with those `--as-of`
instants give; that it prints one line per day and exits 0; that a day
that fails stops it with exit 1 naming the day, the earlier days
committed; that `A` after `B` exits 2; that replaying a span already
journaled writes nothing (every file's bytes and `HEAD` unchanged); and
that two replays of the same span into fresh state directories give
identical bytes outside `.git/` and the same `HEAD` tree. Seen to fail: a
day list that leaves out the last day `B`; the clock set to the start of
the day instead of the close of its last bar. `./scripts/check` green.

**U3 The two performance items (`meta/BACKLOG.md`: REVIEW-1 should-fix
U6, REVIEW-2 note U1; DESIGN §5.2, §5.5, §16.1 step 1, §18.2; decisions 4,
5, 18, 31, 35).** `src/discotrade/bars/` and `src/discotrade/sources/`
files that `bars fetch` and step 1 use, `src/discotrade/daily.py` and
`src/discotrade/paper.py` where the replay's measured cost lies, and their
tests. `bars fetch` and step 1 build each instrument's source once per
run, and the synthetic source generates for a fetch only what it needs,
with every bar it returns equal to the bar the full generation gives;
recovery (decision 5) reads and hashes only the files that can be an
interrupted append (the instrument's unlisted month files and the file
holding its indexed last bar), runs once per instrument per fetch, and
every reader still refuses as decisions 18, 31 and 35 say. If the paper
rebuild of every day from the whole journal is a measured cost, the day
may update the paper file from the day's journal file instead, provided a
test shows, after every day of a multi-day run, that the file equals a
full rebuild's content hash. No stored byte, journal row, paper row or
ledger line changes. Gate: tests show that the store written by fetching
day by day over at least a month equals, byte for byte (month files and
index), the store written by one fetch over the span; that a synthetic
fetch's bars equal the slice of the full generation for at least three
instruments with different calendars and a roll; that an interrupted
append and a revised data point are still told apart and handled as
decision 5 says, and refused by every reader as decisions 18 and 31 say;
and that the existing tests of the store, the gap check, the rolls and the
day assert what they assert today. The commit body gives the seconds per
replay day of a controls-only replay of `test_synth` on the gate
configuration (at least 20 days, measured the same way before and after
the change, foreground, one call), and the one-year time it implies
against DESIGN §18.2's 15 minutes for the whole M1 gate (about 900 replay
days over G1.1, G1.2 and G1.3, decision 74). Seen to fail: a synthetic
fetch that starts its generation at the fetch's start instead of the
series' (its bars differ from the full generation's); recovery skipping an
unlisted month file. `./scripts/check` green.

**U4 The combined portfolio and rank persistence in the day loop
(decisions 59, 62, 63, 69, 70; DESIGN §9.3, §10.5, §11.1, §16.1 steps 2
and 6).** `src/discotrade/paper.py`, `src/discotrade/stats.py`,
`src/discotrade/daily.py`, `src/discotrade/controls.py` and
`src/discotrade/lifecycle.py` only where they must leave portfolio rows
out, and tests (`tests/test_paper.py`, `tests/test_stats.py`,
`tests/test_daily.py`, or new files). Gate: tests show `portfolio` and
`portfolio_clean` on days with no member, one member, several members
with a clean and an exposed one, a member made dormant on `D` (still a
member on `D`, not on `D + 1`) and one admitted on `D` (a member from `D +
1`), each value equal to the test's own equal-weight mean from the paper
rows; that `portfolio_clean` has no row on a day without a clean member;
that rebuilding the paper file gives the same content hash; that rank
persistence, the control moments, the matched draw and the lifecycle's
Sharpes take no portfolio row; that, through `run-day` or `replay` on
`test_synth` (`block_days` 7), the row of each block is appended on the
first new day on or after the block's last calendar day, with decision
59's fields, for the approaches live or dormant after that day's steps,
none for a block whose previous block starts before the first journaled
day, and that a re-run appends nothing. Seen to fail: portfolio members
taken from the state after `D`'s steps instead of at its start; a block
row written before its last calendar day; a block row appended again on a
re-run. `./scripts/check` green.

**U5 The table (decisions 25, 30, 41, 60, 62, 71; DESIGN §10.4, §8,
§11.2).** A new `src/discotrade/table.py`, `src/discotrade/daily.py`
(written with the day, staged), and a new `tests/test_table.py`. Gate:
tests show, on a state with live approaches in two cells, a dormant one, a
retired one, the controls and the portfolio series (approaches written by
the lifecycle functions and journaled through `run-day`), that
`table.json` holds the rows of decision 71 in its order, the retired
approach absent, each field equal to the test's own computation from the
paper rows, the journal rows, the trial rows and the lifecycle rows
(Sharpe with decision 30's rule and maximum drawdown with decision 41's,
written in the test; `E(N)` and the excess against decision 60 with the
test's own quantile), `null` where decision 71 says; that `table.md`
holds the same rows in the same order with four decimals and `-` for
`null`; that both files are staged with the day and committed with it;
and that a re-run of a finished day writes neither. Seen to fail: dormant
approaches listed before live ones; the deflated figures taken over the
whole track's days instead of the subject's paper days; the table
rewritten on a re-run of an earlier day. `./scripts/check` green.

**U6 Scripted candidates in the replay (decisions 48, 63, 73; DESIGN
§10.2, §10.3, §16.1 step 5).** `src/discotrade/cli.py`,
`src/discotrade/daily.py` (and `replay.py` if U2 made it),
`src/discotrade/lifecycle.py` only where the admission function must be
called inside the day, new fixture files under `tests/fixtures/scenarios/`
and `tests/fixtures/strategies/`, and tests (`tests/test_replay.py` or a
new file). Gate: tests show, over a few days of `test_synth` or
`test_mixed`, that a candidate dated `D` is admitted or refused after
lifecycle steps 1 to 4 of `D`, with one trial row (grid and W metrics
`null`), and when admitted its approach under `approaches/<id>/`, its
lifecycle row dated `D`, and its first journal rows on the next trading
day; that a refused one is written under `trials/<id>/`; that the rows are
staged with the day (a day failing in step 2 leaves every ledger and
`approaches/` untouched); that a file with two candidates for one day, a
line missing a key, or a source outside `reference/` and `tests/fixtures/`
is refused before any day runs; and that a re-run of the day appends
nothing. Seen to fail: admission run before lifecycle steps 1 to 4; the
candidate's trial row appended again on a re-run. `./scripts/check` green.

**U7 The M1 gate tests (decisions 9, 59, 60, 69 to 74; DESIGN §18.2,
§18.3 M1).** New `tests/gates/test_g1_1_*.py` to `tests/gates/test_g1_4_*.py`,
each test marked `gate` and `gate_m1`, a new scenario under
`tests/fixtures/scenarios/` (U6's, or a new one) and any new fixture
strategy it needs. Gate: each item's tests assert what decision 74 says
for that item, no less; every seed and date is written in the test file;
the hand counts of G1.3 and the literals of G1.4 are computed in the test
files without `table.py`, `stats.py` or `paper.py`'s functions under test.
Then, after `./scripts/check` is green three times at the pushed tip (three
calls), run `./scripts/gate M1` there once, in the foreground with a
20-minute timeout, and then `./scripts/gate M0` once the same way; keep
both outputs verbatim for the report, with each run's wall time. If
`./scripts/gate M1` takes longer than DESIGN §18.2's 15 minutes, file a
finding (the next free `D-###`) with each item's time, and weaken
nothing. If it cannot finish within the 20-minute call, do not start it
again in the background: reply `VERDICT: question` naming the times
measured. Seen to fail (made in the worktree, each against the one item it
breaks, run with `./scripts/gate M1 G1.<n>` as its own 20-minute call):
a cost model whose costs are zero (G1.1's positive-cost assertion goes
red); a recompute that skips control subjects (G1.2); the lifecycle's
step 4 counting trading days instead of calendar days (G1.3); `E(N)`
without the floor at 2 (G1.4). `./scripts/check` green.

**U8 Final report.** `meta/FINAL-REPORT-9.md` (drafted under
`meta/drafts/`, moved in by this commit). The report gives: what changed
(sha per unit); the outputs of `./scripts/gate M1` (under a heading `##
Gate M1`) and of `./scripts/gate M0` (under `## M0 still passes`) from U7,
verbatim, with the tip they ran at, their wall times, and the seconds per
replay day U3 measured; for each of decisions 66 to 74, the test file and
test names that hold it; what the tests prove; NOT PROVEN (mandatory: that
admission is driven only by scripted candidates whose T metrics a file
supplies, scoring on T being step S3.2's; that the `cutoff` behind the
`clean` flag comes from a test or a scenario file until step S3.2 builds
the model pool; that approach sources still run in-process until step
S2.2; that the replay has no provider, coordinator, issue sink or sandbox
option yet; that G1.1's statistical bounds hold on the seeds the test
writes, which is what a gate can show; what the socket backstop still
cannot see; what remains of FINAL-REPORT-8's NOT PROVEN); the findings
filed and answered; and a `## Review items` table with one row each for
REVIEW-8 should-fix 1 and 2 and for the two performance items of
`meta/BACKLOG.md`: the item, its resolution (the unit and decisions item),
and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M1` at the pushed tip prints `G1.1` to `G1.4 PASS` and
  `gate M1: PASS`, and `./scripts/gate M0` prints `G0.1` to `G0.4 PASS`
  and `gate M0: PASS`; both outputs are in the report.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- `discotrade replay` processes each trading day in order with the
  injected clock, and two replays from scratch give identical state
  files.
- The paper records hold the two portfolio series of §10.5, and still
  rebuild to the same content hash.
- `stats/<track>/rank_persistence.jsonl` gains one row per completed
  block, and `table/<track>/table.json` and `table.md` are written with
  each new day.
- A re-run of a finished day writes nothing: no file, no index line, no
  ledger, pool, stats or table change, no health line, no commit (I-6).
- Revival is shown to count trading days; no lookup in the scratch
  session can reach a resolver.
- No value of a frozen file changed in this mission (`git diff` of
  `config/`, of the existing entries of `tests/fixtures/config_frozen.json`
  and of the existing records under `tests/fixtures/config/` against the
  base is empty), and `config/models.toml` does not exist.
- No test uses the network, a secret or the wall clock; no state is
  written inside the repository; no file under `src/` names a market, a
  contract root or a venue.
- `meta/FINAL-REPORT-9.md` exists with `## Gate M1`, `## M0 still passes`,
  NOT PROVEN, and the review-items table.
