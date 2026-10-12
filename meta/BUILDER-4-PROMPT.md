# BUILDER-4-PROMPT — discotrade mission 4: review-3 repairs (Sharpe at zero deviation, trades test, backtest exit 1, last_ts, indicator text)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 4. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-4.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 4 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ; items 30 to 33 are new for this mission and every unit below
cites them; items 1 to 29 still bind, with item 33's renumbering),
`DESIGN.md` (§8 and §6.3 are this mission; §5.2 for the store's reader;
§3 and §6.2 for the `backtest` command and the result check; §7.2 and
§7.3 for the per-bar rows; §13.4 for why the indicator text matters;
§18.1; read §2 twice), `meta/reviews/REVIEW-3.md` (its `## Blockers`,
`## Should-fix` and `## Notes`), `meta/FINAL-REPORT-3.md`,
`meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a unit in progress
means §R first). This is a repair mission of roadmap step S0.3.

---

## Mission

Close REVIEW-3's blocker and its four should-fix items, and nothing else
(decisions 30 to 33): `sharpe` and `sharpe_2x` are not a number for a
constant daily series whatever its value; the `trades` test tells a right
implementation from a wrong one; `backtest`'s exit 1 paths of decision 27
are tested; `BarStore.last_ts` refuses as the other readers do; the
indicator module's text is true of `ema`. It does not build the
independent calculation, the cheating strategy or any gate test, and
creates nothing under `tests/gates/`: those are step S0.4, mission 5,
which closes M0 (decision 33). This mission does not close a milestone.
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
- Your final reply begins with exactly one of: `VERDICT: mission 4
  finished` | `VERDICT: mission 4 blocked <unit>` | `VERDICT: question <one
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
(the items the unit names) and the REVIEW-3 items the unit names. No unit
changes a value in a frozen file (`config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit creates a file under `tests/gates/`.
Where a unit's code already exists and is right, so that a new test cannot
be seen to fail first against the parent, the sub-agent instead makes, in
its worktree and without committing it, the wrong change the test is meant
to catch, sees the test fail, reverts it, and names that change in the
commit body.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S0.3 as a repair mission,
and REVIEW-3 blocker 1 and should-fix 1 to 4 as carried items, each with
the unit that takes it), rewrite `meta/CHECKPOINT.md` for this mission,
and append to `meta/journal.md`. Nothing else. Gate: the three files are
committed and pushed in one `plan:` commit.

**U1 Sharpe at zero deviation, and the `trades` test (REVIEW-3 blocker 1
and should-fix 1; decisions 25, 30; DESIGN §8; R-7; I-4).**
`src/discotrade/metrics.py`, `tests/test_metrics.py`. `sharpe` (and
through it `sharpe_2x`) treats the deviation as 0 by decision 30: every
value equal to the first, or `std(d, ddof=1)` not above `1e-12` times the
largest absolute value in `d`. Gate: a test, seen to fail on the parent,
that `sharpe` is not a number for each of these constant daily series:
`[0.1] * 3`, `[0.03] * 10`, `[0.01] * 3`, `[1/3] * 10`, `[0.07] * 10`,
`[-0.05] * 5`, `[0.0] * 4`, `[1e-6] * 20`; that `compute` (or whatever
builds the metrics from per-bar rows) gives `sharpe` and `sharpe_2x` not
a number on a hand case whose daily net series is constant and non-zero
at both 1x and 2x; that such a value is neither positive nor above any
number in every comparison the module offers; that a series with a small
real deviation, `[0.1, 0.1, 0.1 + 1e-9]`, still gives a finite Sharpe
equal to its hand value, so the tolerance does not swallow real data. For
`trades`: a test with a rolled row whose `trade` is above `1e-9` (it is
counted) and a rolled row with `trade = 0` and a non-zero roll cost (it
is not), which fails both for a `trades` that drops every rolled row and
for one that counts a row with a non-zero roll cost; the sub-agent makes
each of those two wrong changes, sees the test fail, and names them in
the commit body. The commit body says "roll trades are not counted; a
bar with a roll and a real trade is", not "roll rows".

**U2 `backtest` exit 1 paths (REVIEW-3 should-fix 2; decisions 18, 21,
22, 24, 27; DESIGN §3, §6.2).** `tests/test_cli_backtest.py`, and
`src/discotrade/cli.py` only if a path below does not already exit 1, or
for a test seam that changes no behaviour. Gate: tests that `discotrade
backtest` exits 1, with an error naming the cause, after `bars fetch` on
`test_mixed` into a temporary state directory, when: SYNA's roll record
for a contract change inside the window or its context is missing
(decision 24); the strategy returns `2.0` at some bar, and when it
raises (decision 22, the error naming the instrument and the bar's `ts`);
the loader refuses the strategy text (six parameters; decision 21 is
silent on the exit code, and 1, the current behaviour, is kept); and the
instrument's directory holds a month file the index does not list
(decision 18). Strategy texts for these tests are not committed under
the repository's `reference/` and no test writes into the repository's
working tree: the test points the command's reference root at a
temporary directory in-process, or uses an equivalent seam; the
sub-agent states which in the commit body. Each new test is shown to
fail when the path it covers exits with another code (a wrong change
made and reverted as above). The existing exit 2 and refused-bar-file
tests stay unchanged.

**U3 `BarStore.last_ts` refuses as a reader (REVIEW-3 should-fix 3;
decisions 5, 18, 31; DESIGN §5.2; I-5, I-6).**
`src/discotrade/bars/store.py`, `tests/test_bar_store.py`, and
`src/discotrade/cli.py` only where a call must move to the private
index helper of decision 31. Gate: tests, seen to fail on the parent,
that `last_ts` refuses with the interrupted-append error for an unlisted
month file that passes decision 5's test with `r = 0`, and with the
revised-data-point error for one that does not and for a listed file
whose hash differs; that after `bars fetch` completes the interrupted
append, `last_ts` returns the completed last `ts`; and a test that lists
every public method of `BarStore` and fails when a method is in neither
its list of refusing readers nor its list of methods that do not read
bars (writers, recovery, paths), so a reader added later must be
classified, with every listed reader shown to refuse. The existing
recovery and writer tests stay unchanged in what they assert.

**U4 Indicator module text (REVIEW-3 should-fix 4; decision 32; DESIGN
§6.3, §13.4; I-2).** `src/discotrade/indicators.py` (its docstrings
only; no function's behaviour changes), `tests/test_indicators.py`.
Gate: a test, enumerating every public function of the module as the
property test does, that each windowed function's result is not a number
at row 0 for a window of at least 2, in every column it returns, except
the functions the module docstring names as seeded, and that each of
those (at least `ema`) is a number at row 0; the module docstring names
`ema`'s seeding at the first value, and any other exception the test
finds, so that the text is true of every function. The existing hand-value
and property tests stay unchanged.

**U5 Final report.** `meta/FINAL-REPORT-4.md` (drafted under
`meta/drafts/`, moved in by this commit): what changed (sha per unit),
what the tests prove, a `## Corrections to FINAL-REPORT-3` section
restating its two claims REVIEW-3 found overreaching (Sharpe not a number
at zero deviation; "roll rows not counted") as the code now does them,
NOT PROVEN (mandatory: at least that no independent calculation has
checked the loop, the costs or the metrics yet, which is mission 5's;
every cost value that is still from SPEC §17, DESIGN §4.2 or R-5 and not
measured; the reference strategies' results meaning nothing about any
market; the REVIEW-3 notes this mission does not take, which
`meta/BACKLOG.md` carries to step S0.4 or S1.1; and what remains of
mission 3's NOT PROVEN), the findings filed, and a `## Review items`
table with one row for REVIEW-3 blocker 1 and one per REVIEW-3
should-fix item (1 to 4): the item, its resolution (the unit and
decisions item), and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- `uv run discotrade config check` exits 0 on the `hourly` track with its
  eight instruments, and no value of a frozen file changed in this mission
  (`git diff` of `config/` and of the existing entries of
  `tests/fixtures/config_frozen.json` against the base is empty).
- Nothing exists under `tests/gates/`; `./scripts/gate M0` exits non-zero
  with `gate M0: FAIL`, and `./scripts/gate M0 G0.3` ends with `gate M0
  G0.3: FAIL` (the gate tests are step S0.4's, mission 5).
- `uv run discotrade backtest` of each of the three reference strategies
  on `test_mixed`, in a temporary state directory after `bars fetch`,
  exits 0 and prints the metrics of §8 with net figures at 1x and 2x.
- No test uses the network, a secret or the wall clock; no file under
  `src/` names a market, a contract root or a venue.
- `meta/FINAL-REPORT-4.md` exists with NOT PROVEN, the corrections to
  FINAL-REPORT-3, and the review-items table covering REVIEW-3 blocker 1
  and should-fix 1 to 4.
