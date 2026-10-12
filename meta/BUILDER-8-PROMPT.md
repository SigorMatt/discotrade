# BUILDER-8-PROMPT — discotrade mission 8: the controls, the ledgers, the lifecycle, the clean flag and the statistics of §11 (step S1.2)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 8. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-8.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 8 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ; items 58 to 65 are new for this mission and every unit below
cites them; items 1 to 57 still bind, and items 4, 22 to 25, 30, 39 and
47 to 55 are the ones this mission's code meets), `DESIGN.md` (§10.1 to
§10.3, §11 and §9.3's `clean` flag are this mission; §7, §8, §9.2, §9.4,
§16.1 step 2 and §16.2 for how a subject is journaled, scored and
staged; §4.1 for the track's horizons, cells and blocks; §18.1; read §2
twice, in particular I-3, I-5, I-6, I-11 and I-12),
`meta/reviews/REVIEW-7.md` (its `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-7.md`, `meta/BACKLOG.md`, `meta/findings/FINDINGS.md`,
and `meta/CHECKPOINT.md` (a unit in progress means §R first). This is
roadmap step S1.2.

---

## Mission

Build roadmap step S1.2 as decision 65 cuts it: the buy-and-hold and
random controls of §10.1, journaled every day beside the approaches, with
their pool records; the three ledgers of §10.2; the lifecycle of §10.3
(steps 1 to 4 in the day loop, and admission as a function); the `clean`
flag of the paper records (§9.3, §11.3); and the statistics of §11 as
functions (rank persistence, deflated scores, tightening); and close
REVIEW-7's two should-fix items (decision 58). The table, the combined
portfolio, rank persistence in the day loop, the replay harness and the
gate tests are step S1.3's; scoring a candidate on T is step S3.2's;
running approaches in the sandbox is step S2.2's. This mission does not
close a milestone and adds no test under `tests/gates/`. Add nothing
else. Where a cited decision changes what an existing test asserts, the
unit changes that assertion and says so in its commit body; every other
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
- Your final reply begins with exactly one of: `VERDICT: mission 8
  finished` | `VERDICT: mission 8 blocked <unit>` | `VERDICT: question <one
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
existing record under `tests/fixtures/config/`; a unit that needs a
different configuration (for example a lower `match_window_days` or
`dormant_window_days`) builds it under the test's temporary directory, or
adds a new fixture file (for example a strategy under
`tests/fixtures/strategies/` that breaks the contract on a known bar) and
says so in its body. Where a unit's code already exists and is right, so
that a new test cannot be seen to fail first against the parent, the
sub-agent instead makes, in its worktree and without committing it, the
wrong change the test is meant to catch, sees the test fail, reverts it,
and names that change in the commit body. Each unit names below the
wrong changes its tests must be seen to fail on; these are made and
reverted the same way and named in the body. `./scripts/check` and
`./scripts/gate` are run in the foreground with an explicit timeout of
at least 20 minutes (finding HF-006), and each sub-agent runs
`./scripts/check` three times before its commit and says in its report
how many runs were green.

Every test of this mission writes state only under a pytest temporary
directory, reads time only through a `FixedClock` or `--as-of`, and runs
the `discotrade` command in-process through the function the console
script calls, except where it tests the console script itself. A test
that runs `git` passes `GIT_ALLOW_PROTOCOL=file` in its environment and
uses local paths only (decision 47). Every journal, paper, control and
lifecycle test that runs days runs on a synthetic source from
`tests/fixtures/config/` (`test_mixed` for the roll, the no-short
instrument, the proportional fee, the mixed calendars and dropped bars;
`test_synth` where a four-instrument basket is wanted), with every seed
written in the test file. Each rule is unit-tested at its production
value from `config/thresholds.toml`; a test may also use a lower value
from a configuration copied under its temporary directory, and says so.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S1.2, and as carried items
REVIEW-7 should-fix 1 and 2 (decision 58, both taken by U1), each with
the unit that takes it), rewrite `meta/CHECKPOINT.md` for this mission,
and append to `meta/journal.md`. Nothing else. Gate: the three files are
committed and pushed in one `plan:` commit.

**U1 REVIEW-7's should-fix items (decisions 47, 54, 58; I-11; DESIGN
§9.4, §18.1).** `tests/conftest.py`, `tests/test_offline.py` and
`tests/test_journal_recompute.py`; no file under `src/` unless the
recompute itself is found wrong, which is then a finding first. Gate:
tests show that, in a test, in a module-scoped and in a session-scoped
fixture, through `socket` and through `_socket`, `sendmsg` with an
address on an `AF_INET` socket and each of `gethostbyname`,
`gethostbyname_ex`, `gethostbyaddr` and `getnameinfo` fail with
`SocketBlocked` before any packet or lookup leaves the process; that an
`AF_UNIX` socket still works; that a test marked `network` is still left
alone (in a scratch pytest session, as U1 of mission 7 did); and the
recompute test of decision 58 (b), on a journal of at least three days,
reporting both `(D1, subject)` and `(D2, subject)` and exiting 1. Every
existing test of `tests/conftest.py`'s behaviour and of `journal
recompute` asserts what it asserts at the base. Seen to fail: `sendmsg`
left unguarded; `gethostbyname` left unguarded; a recompute that starts
each day from the stored previous `target_next` (its `D2` assertion goes
red). `./scripts/check` green.

**U2 The statistics of §11 and the `clean` flag (decisions 30, 59, 60,
61; DESIGN §8, §9.3, §11.1 to §11.4; I-3).** A new
`src/discotrade/stats.py`, `src/discotrade/paper.py`, a new
`tests/test_stats.py`, and `tests/test_paper.py`. Gate: tests show the
block dates of decision 59 from the track's `epoch` and `block_days`;
the population rule (a subject missing one trading day of either block
is left out; a buy-and-hold subject on a weekly calendar is judged on
its own instrument's days); the Spearman statistic against values
computed in the test, ties taking the average rank; a missing statistic
below `alerts.rank_min_population` (production value 5) and when a rank
series has zero deviation; `E(N)`, the excess and the threshold of
§11.4 against values computed in the test with its own bisection
quantile, for at least three `N` (including `N = 0`, `1` and a large
`N`) and with the published quantiles of decision 60 asserted; slots
whose Sharpe is not a number left out of `mu_c` and `sd_c`, and fewer
than two slots giving values that are not numbers; `p(N)` at `N = 0`,
`1`, `10` and `1000` against hand values at the production thresholds
(`persistent_base_percentile` 0.95, `false_alerts_per_year` 0.5); the
paper records' `clean` column (an approach clean only on days after its
`cutoff`, exposed on and before it; controls always clean once U4 writes
them, shown here with a control-kind row the test builds) and the clean
and exposed counts; and that rebuilding the paper records from the
journal still gives the same content hash. Seen to fail: ties ranked by
position instead of averaged; `sd_c` with ddof 0; `N` not floored at 2
in `E(N)`; `clean` when the day is on or after the cutoff instead of
after it. `./scripts/check` green.

**U3 The ledgers and the lifecycle (decisions 22, 48, 62, 63; DESIGN
§9.1, §10.2, §10.3, §16.2; I-5, I-6).** New `src/discotrade/ledger.py`
and `src/discotrade/lifecycle.py`, `src/discotrade/state.py` (the trial
writer beside the approach writer), `src/discotrade/daily.py` (steps 1
to 4 after the day's journaling, staged with the day) and
`src/discotrade/journal.py` only where a contract failure must drop one
approach's rows instead of failing the day, new `tests/test_ledger.py`
and `tests/test_lifecycle.py`, additions to `tests/test_daily.py`, and a
new fixture strategy under `tests/fixtures/strategies/` if a failing
approach is needed. Gate: tests show the ledgers' append rules of
decision 62 (one sorted-key JSON object per line, atomic, earlier lines
byte-identical, a line already present not appended, a torn last line
refused) and the trial row's keys, `null` where a scripted candidate
carries nothing; admission into a free slot, admission displacing the
weakest (that one going dormant with reason `displaced`), refusal for a
score that is not positive (a score that is not a number included),
refusal for too few trades at `admission.min_trades_t` (production value
30), refusal when not better than the weakest, each writing exactly one
trial row and, when admitted, the approach and one lifecycle row with
the reasons of decision 63; a trial not admitted written under
`trials/<id>/`; dormancy at `dormant_window_days` (production value 30)
and not before it, and not for a Sharpe that is not a number; return to
live into a free slot and by displacing the weakest, not before
`revival_min_dormant_days` (production value 5) trading days; retirement
after `retire_dormant_days` (production value 365) calendar days;
through `run-day`, an approach that breaks decision 22's contract on `D`
retired with reason `failure: ...`, its rows of `D` absent from the
journal, the other subjects journaled and the day committed, and the
retired approach not journaled on the next day; a change taking effect
from the next trading day (an approach made dormant on `D` is journaled
on `D + 1`, an approach admitted on `D` first journaled on the next
trading day); the weakest chosen by lowest Sharpe, a Sharpe that is not
a number lowest, ties to the lowest id; a re-run of a finished day
appending no ledger line; a day that fails in step 2 (a non-repository
source, decision 48) leaving every ledger untouched. Seen to fail: a
Sharpe that is not a number treated as negative in step 2; a change
taking effect on `D` itself; the lifecycle row appended again on a
re-run; a contract failure failing the whole day. `./scripts/check`
green.

**U4 The controls (decisions 23, 25, 49, 54, 64; DESIGN §7, §9.2, §9.4,
§10.1; I-1, I-5, I-6, I-12).** A new `src/discotrade/controls.py`,
`src/discotrade/daily.py`, `src/discotrade/journal.py` (control subjects
in the day and in `journal recompute`), `src/discotrade/backtest.py` and
`src/discotrade/executor.py` only where controls must share their one
implementation of §7 (every existing test of them unchanged),
`src/discotrade/paper.py` if control rows need it, a new
`tests/test_controls.py`, and `tests/test_daily.py`,
`tests/test_journal_recompute.py`, `tests/test_journal.py` and
`tests/test_paper.py` only where decision 64 changes what a test asserts
(each named in the body). Gate: tests show, through `run-day` on a state
made by `init-state`, that every day journals `bh:<symbol>` for each
instrument of the track (target 1 at every bar, first row flat, the roll
cost paid when the carried position rolls) and `rc:0` to `rc:49` on
every instrument (`controls.random_pool`, production value 50), with
`kind` `control_bh` and `control_random`; that a draw is made on the
first journaled day and on the first trading day of each later calendar
month, and not on other days, with seed `YYYYMM`, one `pools.jsonl` line
per draw holding decision 64's fields, and a re-run appending nothing;
that the fallback draw's `H` lies in the track's horizon bounds and
equals, slot by slot, values the test computes from
`numpy.random.default_rng(seed)`; that a matched draw, with at least
`match_min_live` live approaches with enough paper rows (a lower
`match_window_days` on a configuration copy is allowed), takes its pairs
from those approaches' measured holding bars and trades per bar, values
the test computes from their journal rows; that a slot's targets on one
instrument over a few days equal those the test computes from decision
64's hash and state machine on its own, long only on the instrument that
cannot be shorted; that the position carries across a redraw; that the
controls' journal rows equal, field for field under decision 39's rule,
the module's evaluation of the same targets over the span from their
first journaled day; that the paper records hold the controls with
`clean` true; that `journal recompute --all` matches every control pair
and reports a control row changed by the test; and that two fresh state
directories run for the same days and `--as-of` give equal journal,
paper and pool content. Seen to fail: the per-bar random number not
keyed by the bar's `ts`; the state machine not restarted flat at a
redraw's first bar; a redraw reusing the previous month's seed; a short
entry on the instrument that cannot be shorted. `./scripts/check` green.

**U5 Final report.** `meta/FINAL-REPORT-8.md` (drafted under
`meta/drafts/`, moved in by this commit). First, after `./scripts/check`
is green three times at the pushed tip, run `./scripts/gate M0` there
once, in the foreground with a timeout of at least 30 minutes, and paste
its output verbatim under a heading `## M0 still passes` (M0 is met; this
shows the mission did not break it). The report gives: what changed (sha
per unit); for each of decisions 58 to 64, the test file and test names
that hold it; what the tests prove; NOT PROVEN (mandatory: that the
controls and the lifecycle have not run over a long replay, which is
step S1.3's; that rank persistence is not yet written in the day loop,
and the table and the combined portfolio do not exist, until step S1.3;
that admission is driven only by candidates whose T metrics a test
supplies, scoring on T being step S3.2's; that the `cutoff` behind the
`clean` flag is written by a test until step S3.2 builds the model pool;
that approach sources still run in-process until step S2.2; what the
socket backstop still cannot see; what remains of FINAL-REPORT-7's NOT
PROVEN); the findings filed and answered; and a `## Review items` table
with one row each for REVIEW-7 should-fix 1 and 2: the item, its
resolution (the unit and decisions item), and the sha. Then the verdict
line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M0` at the pushed tip prints `G0.1` to `G0.4 PASS` and
  `gate M0: PASS`, and its output is in the report.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- Every day `run-day` journals the buy-and-hold controls and the random
  pool beside the live and dormant approaches, and `journal recompute
  --all` matches every pair, controls included.
- Each transition of §10.3 is shown by a test, with one ledger row per
  event and no line ever rewritten.
- `E(N)`, its excess, `p(N)` and the threshold of §11.4 match values the
  tests compute on their own; the Spearman statistic and its missing
  cases match decision 59.
- The paper records carry `clean`, and still rebuild from the journal to
  the same content hash.
- A re-run of a finished day writes nothing: no file, no index line, no
  ledger or pool line, no health line, no commit (I-6).
- `sendmsg` with an address and the four name lookups fail under the
  socket backstop in every scope; `journal recompute` is shown not to
  chain through stored values.
- No value of a frozen file changed in this mission (`git diff` of
  `config/`, of the existing entries of `tests/fixtures/config_frozen.json`
  and of the existing records under `tests/fixtures/config/` against the
  base is empty), and `config/models.toml` does not exist.
- No test uses the network, a secret or the wall clock; no state is
  written inside the repository; no file under `src/` names a market, a
  contract root or a venue.
- `meta/FINAL-REPORT-8.md` exists with `## M0 still passes`, NOT PROVEN,
  and the review-items table covering REVIEW-7 should-fix 1 and 2.
