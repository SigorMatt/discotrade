# BUILDER-11-PROMPT — discotrade mission 11: the lifecycle on the exposure-adjusted measure, the register of return readers and G1.3 (step S2.0b)

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 11. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-11.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 11 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-14-m11.md` (items 83 to 90, new for this
mission; every unit below cites them),
`meta/decisions/decisions-2026-10-13-owner.md` (the owner's; O-11 to O-13,
O-15, O-16 and O-18 are this mission, O-1 to O-4 still bind; the rest is
later steps' and is read so that nothing built here contradicts it),
`meta/decisions/decisions-2026-10-14.md` (items 76 to 82; 78, 80 and 81
are the ones this mission's code meets), `meta/decisions/decisions-2026-10-12.md`
(items 1 to 75 still bind; items 22 to 25, 30, 39, 41, 47, 48, 60, 62 to
64 and 68 to 74 are the ones this mission's code meets), `DESIGN.md`
(§10.3, §10.4, §9.3 and §18.3 (M1) are this mission; §4.1 for T, §7.2 and
§8 for the returns, §11.2 for the deflated figures, §16.1 and §16.2 for
the day; read §2 twice, in particular I-3, I-4, I-5, I-6, I-11 and I-12),
`meta/reviews/REVIEW-10.md` (its `## Notes`), `meta/reviews/REVIEW-9.md`
(its `## Notes`), `meta/FINAL-REPORT-10.md`, `meta/BACKLOG.md`,
`meta/findings/FINDINGS.md`, and `meta/CHECKPOINT.md` (a unit in progress
means §R first). This is roadmap step S2.0b.

---

## Mission

Build roadmap step S2.0b as decisions 83 to 90 cut it. First store the
derived exposure records that make O-4's adjusted series cheap to read
every day (decision 84). Then move the lifecycle onto the exposure-adjusted
measure: dormancy, return and displacement (O-11, O-12; decision 85), and
admission with the scripted candidates file's adjusted figures (O-11 to
O-13; decision 86), each lifecycle row recording the figure that decided
it and the plain one beside it (decision 87). Then add the adjusted
figures to the table (O-13; decision 88). Then write the register of
return readers and the audit test that keeps it complete (O-16, O-18;
decision 89). Then update G1.3 to the adjusted measure and run gate M1
again item by item, and gate M0 (O-15, O-2; decision 90). This mission
closes no milestone. The alert rules, rank persistence on gross timing
return, the deflated figures and the control moments on the adjusted
series, and the dashboard are step S4.1's (O-5 to O-8, O-14); the grid on
W is step S2.1's (O-17); scoring real candidates on T is step S3.2's. Add
nothing else. Where a cited decision changes what an existing test
asserts, the unit changes that assertion and says so in its commit body;
every other existing test stays unchanged in what it asserts, and the one
file under `tests/gates/` that changes is
`tests/gates/test_g1_3_lifecycle.py`, in U6 only (decision 90 (a)). Finish
with a report whose first line the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 11
  finished` | `VERDICT: mission 11 blocked <unit>` | `VERDICT: question <one
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

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-14-m11.md`
and the items of `meta/decisions/decisions-2026-10-14.md`, of
`meta/decisions/decisions-2026-10-12.md` and of
`meta/decisions/decisions-2026-10-13-owner.md` that the unit names. No unit
changes a value in a frozen file (`config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit creates `config/models.toml` (step
S3.2's, decision 61). No unit changes an existing record under
`tests/fixtures/config/` (the gate configuration is built under a test's
temporary directory with `tests/fixtures/config/thresholds_gate.toml`
copied in unchanged, decision 72); a unit that needs something new adds a
new fixture file and says so in its body. No unit but U6 changes a file
under `tests/gates/`, and U6 changes only
`tests/gates/test_g1_3_lifecycle.py` (decisions 83, 90 (a)). Where a
unit's code already exists and is right, so that a new test cannot be seen
to fail first against the parent, the sub-agent instead makes, in its
worktree and without committing it, the wrong change the test is meant to
catch, sees the test fail, reverts it, and names that change in the commit
body. Each unit names below the wrong changes its tests must be seen to
fail on; these are made and reverted the same way and named in the body.

Long commands (finding HF-006): every run of `./scripts/check` or
`./scripts/gate` is its own foreground Bash call with an explicit timeout
of 20 minutes, the tool's maximum; never chain two such runs in one call,
and never let one run in the background. Each sub-agent runs
`./scripts/check` three times before its commit, as three calls, and says
in its report how many runs were green. Tests that `./scripts/check` runs
replay a few days at most; the long replays are the gate tests'. Timing
measurements (decision 80 (d), decision 90 (c)) are foreground calls too,
one measurement per call, never two at once, and none while another heavy
process runs.

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
and says so. A test that compares an adjusted figure computes the expected
value itself, from the journal parquet files and the stored bars, without
calling `paper.adjusted`, `paper.unit_bars`, `paper.unit_returns` or
`paper.average_positions`, as `tests/test_exposure.py` does.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S2.0b, the statement that
this mission closes no milestone and runs gate M1 again as decision 90
says, and as carried items REVIEW-10 note 3 (decision 84, taken by U1),
the REVIEW-9 note on decision 68 (b) with the day's admission displacing
(decision 86 (f), taken by U3), and owner decisions O-11 to O-13 (U2, U3,
U4), O-16 and O-18 (U5) and O-15 (U6), each with the unit that takes it),
rewrite `meta/CHECKPOINT.md` for this mission, append to
`meta/journal.md`, and append to `meta/findings/FINDINGS.md`, under its
"hands findings" heading, the next free `HF-###` that decision 90 (d)
describes (severity low; component the review protocol and the tool's
20-minute cap; found 2026-10-14, REVIEW-10 note 7; status open). Nothing
else. Gate: the four files are committed and pushed in one `plan:` commit.

**U1 The derived exposure records (decision 84; decisions 78, 81; O-4;
DESIGN §9.2, §9.3, §16.1, §16.2; REVIEW-10 note 3).**
`src/discotrade/paper.py`, `src/discotrade/daily.py`, and tests
(`tests/test_exposure.py` for new tests only, or a new
`tests/test_exposure_records.py`). Store, staged with the day, the records
decision 84 names, and make `paper.adjusted` read them. Gate: every
existing test of `tests/test_exposure.py` passes unchanged; new tests show,
on `test_mixed` over days holding a roll and a weekend, that the stored
records equal the test's own computation; that `paper.adjusted` on the
stored records equals, at 1e-12, the on-call computation the parent made
(written in the test from the journal and the bars) for an approach, a
random slot and a buy-and-hold control on two windows; that a stored
`R_i(D)` equals the value computed from a state with a later roll of the
instrument; that the records are written into the staging directory on a
new day only and a re-run writes nothing (I-6); that a rebuild from the
journal and the bars gives the same content hash; that decision 78's heal
restores them after a day whose records were removed, and after an extra
date; that a caller passing staged records and `overlay` reads the staged
day's rows; and that `paper.py` no longer calls `journal._empty`. The
commit body gives decision 90 (c)'s two measurements of the G1.3
scenario's first 30 calendar days (parent and commit) and the time of one
`paper.adjusted` call over the whole paper record of an approach at the
end of that replay, on call at the parent and from the records at the
commit. Seen to fail: `hbar_i(W)` as the mean of daily means instead of
summed position over summed rows; the records written on a re-run; the
heal skipped for the records. `./scripts/check` green.

**U2 Dormancy, return and displacement on the adjusted measure (O-11,
O-12; decisions 85, 87; decisions 62, 63, 68; DESIGN §10.3).**
`src/discotrade/lifecycle.py`, `src/discotrade/daily.py` if the call
needs the staging directory, and tests (`tests/test_lifecycle.py` or the
existing lifecycle tests). Gate: tests at the production
`lifecycle.dormant_window_days` (and at a lower value from a copied
configuration where a replay would otherwise be long, said so) show an
approach whose plain Sharpe over its last `N` rows is positive while its
adjusted Sharpe is negative going dormant, and one whose plain Sharpe is
negative while its adjusted is not, staying live; a dormant approach
returning on a positive adjusted Sharpe, and not on a positive plain one
with a non-positive adjusted one; a return that displaces the live
approach with the lowest adjusted Sharpe over the same dates, where the
plain measure names another; each `dormant`, `returned` and `displaced`
row carrying `adjusted` and `plain` as decision 87 says, `null` for a
figure that is not a number; `retired_dormant` and failure rows carrying
neither; an approach holding one constant position (adjusted series of
zeros, Sharpe not a number) neither going dormant nor returning. Existing
lifecycle tests whose assertions the adjusted measure changes are updated
and the commit body names each with decision 85. The commit body gives
decision 90 (c)'s two measurements. Seen to fail: the plain `net_1x` kept
in step 2; the live approaches of step 3 scored with the dormant
approach's average positions instead of their own; `W` taken as the
approach's whole paper record. `./scripts/check` green.

**U3 Admission on the adjusted measure and the candidates file (O-11 to
O-13; decisions 86, 87; decisions 48, 63, 68, 73, 79 (b); DESIGN §10.3,
§4.1).** `src/discotrade/lifecycle.py`, `src/discotrade/replay.py`, every
candidates file under `tests/fixtures/scenarios/` (`g1_lifecycle.jsonl`
included: it gains `adjusted_t` here, with values that keep the scenario's
admissions as they are; U6 settles the scenario), and tests
(`tests/test_replay_candidates.py`, `tests/test_lifecycle.py` or new
files). Gate: tests show a candidates line without `adjusted_t`, with an
extra key in it, a missing symbol in `avg_position` or a value of the wrong
kind refused before any day runs; the admission score read from
`adjusted_t["sharpe"]` (a candidate with a positive plain and a
non-positive adjusted score refused `not_positive`, and the reverse
admitted); `null` refused `not_positive`; the weakest of a full cell chosen
on its adjusted Sharpe over T's days with its own average positions,
where the plain measure would choose another; the trial row holding
`adjusted_t` and `adjusted_w` (`null`) beside `metrics_t` and `metrics_w`;
the `admitted` and `displaced` rows carrying decision 87's keys; decision
79 (b)'s test still seen to fail on T as the last `t_days` trading days;
and decision 86 (f)'s test of decision 68 (b) with the day's admission
doing the displacing. Rows written before this unit are not rewritten (a
test reads a ledger line written by the parent's code and finds it
unchanged after a new day). Seen to fail: the score read from
`metrics_t["sharpe"]`; the live approaches scored over the candidate's
average positions; `adjusted_t` optional. `./scripts/check` green.

**U4 The table's adjusted figures (O-13; decision 88; decisions 30, 39, 41,
60, 71; DESIGN §10.4, §8).** `src/discotrade/table.py` and its tests
(`tests/test_table.py`). Gate: tests on a `test_mixed` replay with two
approaches, the controls and both portfolio series show each approach
row's `adjusted_sharpe`, `adjusted_sharpe_2x`, `avg_position` and
`adjusted_admission_score` equal to the test's own computation over all
the approach's paper days, under decision 39's rule; `null` for the
controls and the portfolio series; `null` for `adjusted_admission_score`
where the trial row has no `adjusted_t`; the deflated figures and every
earlier field unchanged in value; `table.md` showing the new columns,
each labelled adjusted or plain; a re-run writing nothing. The commit body
gives decision 90 (c)'s two measurements. Seen to fail: `avg_position`
over the last `dormant_window_days` rows instead of the whole paper
record; `adjusted_sharpe_2x` taken from `net_1x`; the deflated `S` moved
to the adjusted series (decision 88 keeps it plain until S4.1).
`./scripts/check` green.

**U5 The register of return readers and its audit (O-16, O-18; decision
89).** `tests/fixtures/return_readers.toml` (new) and a new test file
under `tests/` (not `tests/gates/`); no file under `src/` unless the audit
shows an unregistered reader that O-16 says must be adjusted and is not,
which is then a finding first (the next free `D-###`), not a change.
Gate: the audit test passes at the commit, with every entry decision 89
names; it is seen to fail on the three wrong changes decision 89 (b)
names, each made in the worktree and reverted; the commit body lists every
entry with its class and its one-line note, and names the three `pending`
entries. `./scripts/check` green.

**U6 G1.3 on the adjusted measure, gate M1 item by item, and gate M0
(O-15, O-2, O-3; decisions 74, 90; DESIGN §18.2, §18.3 (M1)).**
`tests/fixtures/scenarios/g1_lifecycle.jsonl` and
`tests/gates/test_g1_3_lifecycle.py`, as decision 90 (a) says and no
more; the commit body names each changed line of the scenario and why,
each changed expected row, and states that every transition G1.3 lists
still occurs (with the day it occurs). After the commit is pushed and
`./scripts/check` is green three times at the tip (three calls), run
`./scripts/gate M1 G1.1`, `G1.2`, `G1.3` and `G1.4`, each its own
foreground call with a 20-minute timeout, all at that tip, then
`./scripts/gate M0` once the same way; keep each output verbatim with its
wall time for the report. If an item prints FAIL, decision 90 (b) says
what follows. If an item passes above 10 minutes, file decision 90 (c)'s
finding (the next free `D-###`) with each item's time and a profile, in a
`findings:` commit of `meta/findings/FINDINGS.md` only, and weaken
nothing. If an item cannot finish within its 20-minute call, do not start
it again in the background: reply `VERDICT: question` naming the times
measured. Seen to fail before the commit: the G1.3 test with its expected
rows and the scenario changed but the lifecycle reading plain `net_1x` in
step 2 (made in the worktree on `lifecycle.py`, the G1.3 item run once,
red, reverted, named in the body with its output's last line).

**U7 Final report.** `meta/FINAL-REPORT-11.md` (drafted under
`meta/drafts/`, moved in by this commit). The report gives: what changed
(sha per unit); a `## Speed` section with decision 90 (c)'s measurements
from U1, U2 and U4 and a table of each gate M1 item's time in mission 10
and in this mission; the outputs of the four `./scripts/gate M1 G1.<n>`
calls (under a heading `## Gate M1`) and of `./scripts/gate M0` (under `##
M0 still passes`) from U6, verbatim, with the tip they ran at and their
wall times; a `## Register` section listing every entry of
`tests/fixtures/return_readers.toml` with its class, the three `pending`
entries and the step that removes them; for each of decisions 84 to 90,
the test file and test names that hold it; what the tests prove; NOT
PROVEN (mandatory: that rank persistence, the control moments and the
deflated figures still read plain returns until step S4.1; that the
audit sees only the reference shapes it scans; that the scripted
candidates' adjusted T figures come from a file, not from scoring, until
step S3.2; that the speed figures are from the builder's machine; what
remains of FINAL-REPORT-10's NOT PROVEN); the findings filed and answered;
and a `## Review items` table with one row each for REVIEW-10 note 3, the
REVIEW-9 note on decision 68 (b), REVIEW-10 note 7 (the hands finding),
and owner decisions O-11, O-12, O-13, O-15, O-16 and O-18: the item, its
resolution (the unit and decisions item), and the sha. Then the verdict
line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- `./scripts/gate M1 G1.1` to `G1.4`, each run on its own at the pushed
  tip, print their item PASS line, and `./scripts/gate M0` prints `G0.1`
  to `G0.4 PASS` and `gate M0: PASS`; the outputs and times are in the
  report beside mission 10's, and any item above 10 minutes has its
  finding.
- G1.3 shows every transition it listed before, on the adjusted measure,
  and its expected rows carry the keys of decisions 86 and 87.
- Dormancy, return, displacement and admission read the adjusted Sharpe at
  1x over the windows decisions 85 and 86 name, each subject with its own
  average positions; the plain figure is recorded beside it and decides
  nothing.
- The trial rows, lifecycle rows and table rows written from this mission
  on carry the fields of decisions 86 to 88; no earlier ledger line is
  rewritten (I-5).
- `tests/fixtures/return_readers.toml` registers every function the audit
  finds; the audit test passes; exactly three entries carry `pending`.
- The derived exposure records are staged with the day, rebuilt to the
  same content hash, healed by decision 78's rule, and `paper.adjusted`
  returns from them what it returned on call.
- A re-run of a finished day writes nothing: no file, no index line, no
  ledger, pool, stats, table or derived record change, no health line, no
  commit (I-6).
- The only file under `tests/gates/` that changed is
  `tests/gates/test_g1_3_lifecycle.py`; no value of a frozen file changed
  in this mission (`git diff` of `config/`, of the existing entries of
  `tests/fixtures/config_frozen.json` and of the existing records under
  `tests/fixtures/config/` against the base is empty), and
  `config/models.toml` does not exist.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- No test uses the network, a secret or the wall clock; no state is
  written inside the repository; no file under `src/` names a market, a
  contract root or a venue.
- `meta/FINAL-REPORT-11.md` exists with `## Speed`, `## Gate M1`, `## M0
  still passes`, `## Register`, NOT PROVEN, and the review-items table.
