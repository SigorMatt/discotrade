# BUILDER-5-PROMPT — discotrade mission 5: the independent calculation, the cheating strategy and the gate tests of M0 (closes M0)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 5. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-5.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 5 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ; items 34 to 40 are new for this mission and every unit below
cites them; items 1 to 33 still bind, and items 23 to 26, 29 and 30 are
what the independent calculation is written from), `DESIGN.md` (§18.2 and
§18.3 M0 are this mission; §5.6, §6.2, §7 and §8 for the calculation;
§5.1 to §5.4 for the store and the gap check; §12.1 for what the cheating
strategy may use; §17.1 for the synthetic market and its contracts; §4.2
for `trusted_from`; §18.1; read §2 twice), `meta/reviews/REVIEW-4.md`
(its `## Should-fix` and `## Notes`), `meta/FINAL-REPORT-4.md`,
`meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a unit in progress
means §R first). This is roadmap step S0.4.

---

## Mission

Build step S0.4 and close milestone M0. This mission closes milestone M0.
First take REVIEW-4's should-fix item and the review notes carried to this
step (decisions 34 to 38). Then write the independent calculation of G0.1
with a sub-agent of its own that never opens the modules it checks
(decisions 29, 39), the cheating strategy of G0.2 (decision 40), and the
gate tests of G0.1 to G0.4 under `tests/gates/`, and run `./scripts/gate
M0` at the tip until it prints `gate M0: PASS`. A gate test asserts what
DESIGN §18.3 says, no less; no gate test is made to pass by a special case
in product code. Where a cited decision changes what an existing test
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
- Your final reply begins with exactly one of: `VERDICT: mission 5
  finished` | `VERDICT: mission 5 blocked <unit>` | `VERDICT: question <one
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
(the items the unit names) and the REVIEW-4 or REVIEW-3 items the unit
names. No unit changes a value in a frozen file (`config/instruments/`,
`config/tracks/`, `config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit changes an existing record under
`tests/fixtures/config/` (the gate fixtures' bars must stay as they are);
a unit that needs another fixture adds a new file and says why. Where a
unit's code already exists and is right, so that a new test cannot be seen
to fail first against the parent, the sub-agent instead makes, in its
worktree and without committing it, the wrong change the test is meant to
catch, sees the test fail, reverts it, and names that change in the commit
body. `./scripts/check` and `./scripts/gate` are run in the foreground with
an explicit timeout of at least 20 minutes (finding HF-006).

Every test under `tests/gates/` follows DESIGN §18.1, §18.2 and decisions 9
and 40: it carries the markers `gate` and `gate_m0`; it lives in a file
named `tests/gates/test_g0_<n>_<what>.py` for the item `G0.<n>` it proves,
which is how `./scripts/gate` finds it; every seed it uses is written in
the test file; it writes state only under a pytest temporary directory;
it runs the `discotrade` command in-process, through the function the
console script calls, and launches no subprocess; it never skips (under
`DISCOTRADE_GATE=1` a skip fails); and each item finishes within 15
minutes on a laptop. Where a gate test of U5 or U6 finds product code
that does not do what its item says, the unit fixes the product code with
a unit test outside `tests/gates/` seen to fail first, in the same commit,
and the body names the defect; U4's own rule is below.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S0.4, `This mission closes
milestone M0.`, and as carried items REVIEW-4 should-fix 1, REVIEW-4's
note on `gaps.py` and `rolls.py` (U3 section), and REVIEW-3's three notes
carried to S0.4 by `meta/BACKLOG.md`, each with the unit that takes it),
rewrite `meta/CHECKPOINT.md` for this mission, and append to
`meta/journal.md`. Nothing else. Gate: the three files are committed and
pushed in one `plan:` commit.

**U1 The store's readers, and callers that look at the index first
(REVIEW-4 should-fix 1 and its note on U3; decisions 5, 18, 31, 34, 35;
DESIGN §5.2, §5.4, §5.6; I-5, I-6).** `tests/test_bar_store.py`,
`src/discotrade/bars/gaps.py`, `src/discotrade/rolls.py`, their tests
(`tests/test_gaps.py`, `tests/test_rolls.py`), and
`src/discotrade/bars/store.py` only if a helper is needed. Gate: the
`BarStore` classification test enumerates every public name of the class
by decision 34, properties included, and is seen to fail when the
sub-agent adds a public property that reads bars (a wrong change made and
reverted) and when it adds a public method, as it already does; tests,
seen to fail on the parent, that the gap check, `update_rolls` and
`adjusted_as_of` each refuse with decision 18's interrupted-append error
when the instrument has no index entry and its directory holds an
unlisted month file that passes decision 5's test with `r = 0`, and with
the revised-data-point error for one that does not, and still report no
stored bar when the directory holds no month file; and that after `bars
fetch` completes such an interrupted first append, the three return what
they return on a clean store. The existing recovery, gap and roll tests
stay unchanged in what they assert.

**U2 Rolls and `backtest`: `trusted_from`, roll records, cost labels
(REVIEW-3 notes carried to S0.4; decisions 23, 24, 27, 36, 37, 38;
DESIGN §4.2, §5.6, §7.1, §7.3; I-4).** `src/discotrade/rolls.py`,
`src/discotrade/backtest.py`, `src/discotrade/costs.py` and
`src/discotrade/cli.py` where a change is needed, and their tests
(`tests/test_rolls.py`, `tests/test_backtest.py`, `tests/test_costs.py`,
`tests/test_cli_backtest.py`). Gate: tests on a store into which the test
writes bars before an instrument's `trusted_from` (through the store's
writer, into a temporary state directory, with a test-local instrument
record whose `trusted_from` is later than its first bar; no fixture record
changes) that no such bar is read by the roll gap measurement (both the
`fetch_contract` path and the estimated fallback), by `adjusted_as_of`
for any start it is given, by the evaluation loop's context, or by
`sigma(u)`, and that a contract change across `trusted_from` is not
recorded as a roll (decision 36), each seen to fail on the parent or by a
wrong change made and reverted; a test that `backtest` exits 1 with the
missing-roll error when the roll record has the right `ts` and the wrong
old or new contract (decision 37), seen to fail by a wrong change that
matches on `ts` alone; and a test that the plain output labels the
subject's cost totals as the subject's (divided by `N`) and each
per-instrument line as that instrument's undivided sum, with the figures
and `--json` unchanged (decision 38; a test that asserted the old labels
changes, and the body says so).

**U3 The independent calculation (DESIGN §18.3 G0.1, §5.6, §6.2, §7, §8,
§5.3; decisions 22 to 26, 29, 30, 36, 37, 39).**
`tests/gates/independent_calc.py`, `tests/gates/test_g0_1_calc_self.py`,
and `tests/gates/__init__.py` or a `tests/gates/conftest.py` only if
needed to import it. This unit's sub-agent is a sub-agent of its own,
dispatched for this unit only. Give it the sub-agent brief and, with it,
these words verbatim: "You write a calculation that checks discotrade's
evaluation loop, cost model, roll handling and metrics, so you must not
know how they are written. Do not open, read, grep, diff or `git log -p`
any file under `src/discotrade/`, nor `tests/test_backtest.py`,
`tests/test_costs.py`, `tests/test_rolls.py`, `tests/test_metrics.py`,
`tests/test_executor.py`, `tests/test_reference.py` or
`tests/test_cli_backtest.py`, nor any commit body or report that describes
their code (`meta/FINAL-REPORT-*.md`, `meta/reviews/`). Write the
calculation from DESIGN.md §5.3, §5.6, §6.2, §7 and §8 and from items 22
to 26, 29, 30, 36, 37 and 39 of meta/decisions/decisions-2026-10-12.md
alone. It imports nothing from discotrade. State in your commit body that
you opened none of those files." The calculation is a plain loop: given a
state directory, a fixture config directory, a track, a window and a
strategy (its `position` callable and `PARAMS`, decision 39), it returns
per-bar rows (`ts`, `contract`, trading date, `p`, `h`, `gross`, `trade`,
`fee`, `spread`, `slippage`, `roll`, `cost`, `net_1x`, `net_2x`) per
instrument, the subject's daily series at 1x and 2x, every metric of §8,
and the cost totals by component. Gate: `tests/gates/test_g0_1_calc_self.py`
checks by reading its source with `ast` that `independent_calc.py`
imports only the modules decision 39 allows and nothing from
`discotrade`; and checks the calculation against values the sub-agent
computes by hand, written in the test with their derivation in comments,
on a constructed store of at most a few dozen bars written with `pyarrow`
in a temporary directory: one roll with a carried position and one with
a flat position, one missing bar, one bar on each side of a daily break,
an instrument that cannot be shorted given a negative target, a
proportional-fee instrument, a spread table hour and a main-session and
off-session spread, `sigma` with fewer than 2 returns and with more than
24, and a constant daily series (decision 30). `./scripts/gate M0 G0.1`
passes.

**U4 Gate G0.1: the reference strategies against the independent
calculation (DESIGN §18.3 G0.1; decisions 23 to 27, 39).**
`tests/gates/test_g0_1_reference.py`, and product code only as the
mismatch rule below allows. The sub-agent may read product code; it does
not edit `tests/gates/independent_calc.py`. Gate: a test that runs `bars
fetch` on the fixture track `test_mixed` into a temporary state directory
at an `--as-of` after the window; chooses a window of at least eight
weeks that contains a SYNA roll and the `synth_week` closure of
2019-07-03 to 2019-07-04 (for example 2019-06-03 to 2019-07-31) and
asserts that the window holds what G0.1 names: SYNA rolls in it, SYNL
cannot be shorted and at least one reference strategy gives it a negative
target there (so the clip is exercised), SYNX has a proportional fee, and
each instrument has dropped bars in it; then, for each of
`reference/trend_ma.py`, `reference/zscore_reversal.py` and
`reference/hour_of_day.py`, evaluates the strategy with discotrade (the
evaluation the `backtest` command uses, and the `backtest` command itself
in-process with `--json`) and with the independent calculation, and
asserts by decision 39 that every per-bar field of every instrument,
both daily series, every metric of §8 and the cost totals by component
are equal to 1e-12, that the counts of rows are equal, and that the
`--json` figures equal the module's. The sub-agent makes at least two
wrong changes in product code (for example a roll cost on `h(u)` instead
of `h(u-1)`, and a half spread without its floor of half a tick), sees
the test fail on each, reverts them, and names them in the commit body.
**Mismatch rule.** A difference is settled by DESIGN and the decisions
alone. If discotrade is wrong, U4 fixes the product code with a unit test
outside `tests/gates/` seen to fail first, in this unit's commit, and the
body names the bar, the field, both values and the DESIGN sentence. If
the independent calculation is wrong, U4 stops and reports it; you
dispatch a fresh sub-agent under U3's rules and words, with the mismatch
(the bar, the field, both values, the DESIGN sentence) and nothing about
the product code, which fixes `independent_calc.py` and its self-test in
a commit of its own before U4 resumes. If DESIGN and the decisions do not
settle it, write a finding and reply `VERDICT: question` naming it. Every
mismatch found and how it was settled goes into the report.

**U5 Gate G0.2: the cheating strategy (DESIGN §18.3 G0.2, §6.2, §7.1,
§12.1; I-2; decision 40).** `tests/fixtures/strategies/cheat_lookahead.py`,
`tests/gates/test_g0_2_cheating.py`. Gate: the strategy text does what
decision 40 lists (module-level references to earlier frames read again,
the index read and used in arithmetic, rows past the end tried through
`iloc`, `loc`, `values`, `to_numpy()` and their `base`, `attrs`) and
passes discotrade's loader; a test reads its source with `ast` and checks
it uses no name or attribute beginning with an underscore and none of the
imports §12.1 rejects. On `test_mixed`, for every instrument: its
positions are truncation-invariant (the targets for bars up to `t` are
identical whether the store ends at `t` or at least one year later) for
at least ten values of `t` per instrument, including the window's first
and last bars and the bars on each side of a SYNA roll; and its per-bar
rows and every metric on a window of at least four weeks are identical
whether the store ends at the window's last bar or at least one year
after it. A control in the same file shows the comparison can see a gain:
the same text, given by the test a frame that does hold later rows,
produces different positions and a higher `total_return` than through the
harness, so that a leak would have been caught. The sub-agent makes one
wrong change in product code that leaks a later row into the slice (for
example a slice ending one bar late, or a view of the full array instead
of a copy), sees the test fail, reverts it, and names it in the commit
body.

**U6 Gates G0.3 and G0.4, and the gate run (DESIGN §18.3 G0.3, G0.4,
§18.2, §5.1 to §5.4, §5.6, §7.3, §17.1; I-5, I-9; decisions 3 to 6, 9,
18, 24, 36, 40).** `tests/gates/test_g0_3_store.py`,
`tests/gates/test_g0_4_config.py`. Gate for G0.3, each a test: the store
refuses a bar that is not closed (`ts + bar_seconds` later than the
source's `available_until` at the clock's instant) and a bar whose `ts`
is not later than the last stored bar, and writes nothing of that call;
after an append, every old row of every month file is identical to
before, byte for byte in content hash; on `synth_week` instruments of
`test_mixed`, the gap check finds exactly the bars the synthetic source
dropped, which the test obtains from the generator and not from the gap
check, and none across the daily break, the weekend or the closure of
2019-07-03 to 2019-07-04, each of which the test's range contains; for
SYNA, over a range holding at least two rolls, the adjusted series as of
every bar equals the generator's gap-free underlying series plus the
constant of the contract current at that bar (DESIGN §17.1), for every
earlier bar of that series, to 1e-9 relative; and a position carried
through a roll pays `roll_cost = 2 * |h(u-1)| * c(u)` at the roll bar
while a flat position pays none. Gate for G0.4: `discotrade config check`
on the `hourly` track exits 0 and reports eight instruments; and a test
that collects, from the files under `config/` (not from a list written in
the test), every instrument symbol, every contract root (the part of each
`[source]` `symbol` before its first `.`) and every venue, and finds none
of them as a whole word in any file under `src/`, and is seen to fail
when the sub-agent adds such a word to a file under `src/` (made and
reverted). Then, after `./scripts/check` is green three times: run
`./scripts/gate M0` at this unit's tip; it prints `gate M0: PASS` with
each item under 15 minutes. Paste its output verbatim into the commit
body and into the report draft. When an item fails, the unit that wrote
its test is retried once with the output (U3 and U4 under their own
rules); a gate test is never loosened to pass.

**U7 Final report.** `meta/FINAL-REPORT-5.md` (drafted under
`meta/drafts/`, moved in by this commit): what changed (sha per unit,
and per fix commit of the independent calculation if any), a `## Gate`
section with the `./scripts/gate M0` output at the pushed tip pasted
verbatim and, for each item G0.1 to G0.4, the test file that proves it
and what it asserts against DESIGN §18.3's words, every mismatch U4
found and how it was settled, what the tests prove, NOT PROVEN
(mandatory: at least the limits of the calculation's independence, since
its author read DESIGN and the decisions, which were written while the
code existed, and shares the synthetic bars, the roll records and the
strategy callable with the code it checks; that G0.1 is shown on one
fixture track and one window; that G0.2 covers what §12.1 lets a
strategy text reach, not escapes through the interpreter, which are
G2.1's; every cost value still from SPEC §17, DESIGN §4.2 or R-5 and not
measured; the reference strategies' results meaning nothing about any
market; the I-11 note that `meta/BACKLOG.md` carries to S1.1; and what
remains of mission 4's NOT PROVEN), the findings filed, and a `## Review
items` table with one row for REVIEW-4 should-fix 1, one for REVIEW-4's
note on `gaps.py` and `rolls.py`, and one for each of REVIEW-3's three
notes carried to S0.4: the item, its resolution (the unit and decisions
item), and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M0` at the pushed tip prints `G0.1` to `G0.4 PASS` and
  `gate M0: PASS`, exits 0, and each item finishes within 15 minutes.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- U3's commit body states that its sub-agent opened none of the files
  its words forbid, and `tests/gates/independent_calc.py` imports nothing
  from `discotrade` (U3's self-test).
- `uv run discotrade config check` exits 0 on the `hourly` track with its
  eight instruments, and no value of a frozen file changed in this mission
  (`git diff` of `config/`, of the existing entries of
  `tests/fixtures/config_frozen.json` and of the existing records under
  `tests/fixtures/config/` against the base is empty).
- No test uses the network, a secret or the wall clock; no gate test
  launches a subprocess; no file under `src/` names a market, a contract
  root or a venue.
- `meta/FINAL-REPORT-5.md` exists with the `## Gate` section, NOT PROVEN,
  and the review-items table covering REVIEW-4 should-fix 1, REVIEW-4's
  note on `gaps.py` and `rolls.py`, and REVIEW-3's three notes carried to
  S0.4.
