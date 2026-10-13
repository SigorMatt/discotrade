# Decisions — 2026-10-14 (architect role, consultation 12, after REVIEW-9)

Clarifications where `DESIGN.md`, the role's earlier decisions and the
owner's decisions leave something open. Items are numbered after the last
item of `meta/decisions/decisions-2026-10-12.md` (75) so that a citation
"decision N" stays unique. Each breaks no invariant, moves no gate, changes
no threshold and changes no value of a frozen configuration file
(`meta/ARCHITECT.md` §1, §5). The owner's
`meta/decisions/decisions-2026-10-13-owner.md` (cited "O-N") wins over this
file where they differ. Items 1 to 75 still bind. These items bind mission
10 (step S2.0a) and every later mission until a newer decisions file says
otherwise.

Branch state when written: `main` at 7214fd8 (`review: mission 9`).

76. **`meta/ROADMAP.md`: step S1.3 ticked, milestone M1 met, step S2.0 of
    O-10 split into S2.0a and S2.0b.** REVIEW-9 has no blocker and its
    `## Gate` section records `Gate M1: PASS`, run item by item as O-2
    rules, at 342107b, whose code is b62f5f0's (`meta/ARCHITECT.md` §3
    case 3). So step S1.3 is ticked and M1 is marked met. O-10 puts, before
    step S2.1, O-3's speed work and then a step that builds O-4, the
    lifecycle of O-11 to O-13, the register and audit of O-18 and O-15's
    update of G1.3 with gate M1 run again. That does not fit seven units.
    Mission 10 builds step S2.0a: O-3's speed work first, as O-3 asks,
    then REVIEW-9's three should-fix items, finding D-007, and O-4's
    definitions as one producer function and its derived records, read by
    no rule yet. Mission 11 builds step S2.0b: O-11 to O-13, O-16 and O-18,
    and O-15 with gate M1. The other roadmap changes O-10 approves are made
    in the same kit: M4's gate lists items G4.1 to G4.7, and the step lines
    of S2.1, S3.2, S4.1 and S4.3 name the owner's file. No gate item of
    M2, M3 or M5 moves.

77. **Finding D-007, DESIGN §16.1 and §16.4 with decisions 51 and 72: the
    rule mission 9 U2 built is confirmed.** Decision 72 requires the replay
    to run every trading day of the track at the close of that day's last
    expected bar, which overrides the mission 9 brief's "unchanged in what
    it does". The day function refuses a day `D` when any instrument of the
    track has an expected bar, of a trading day of its own calendar on or
    before `D`, whose close (`ts + bar_seconds`) is later than its source's
    `available_until` at the run's instant; otherwise the day may run (and
    decision 51's other refusals still apply). Missing bars that should
    have closed by then are gaps, not a refusal. The rule is held by the
    tests of decision 79 (REVIEW-9 should-fix 2).

78. **REVIEW-9 should-fix 1, DESIGN §9.3 and §16.2: the per-day paper
    update heals an interrupted day.** Before the day `D` updates
    `paper/<track>/daily.parquet` from `D`'s journal file, it compares the
    set of trading dates the paper file holds with the set of dates of
    `journal/<track>/index.jsonl` before `D`. When they differ in any way
    (a date missing, a date extra, the file absent), the day rebuilds the
    file from the whole journal, as mission 8 did on every day; otherwise
    it updates. Either way the result equals a full rebuild's content hash.
    The same rule applies to every other derived file the day updates
    incrementally (decision 81's records included). The docstring of
    `daily.py` and of `paper.py` say "equal to a rebuild" only with that
    rule in place. Reason: `_move` moves staged files one at a time in path
    order, so a process that dies between `journal/` and `paper/` leaves a
    journaled day whose paper rows are missing; the re-run of that day is
    "already journaled", and only the next day can repair it.

79. **REVIEW-9 should-fix 2 and 3: two tests.** (a) A test on `test_mixed`
    (SYNX trades every day, SYNA on weekdays) refuses a Saturday `D` whose
    SYNX bars have all closed while SYNA's Friday still has an expected bar
    not closed under the source's `available_until` (a fake or delayed
    synthetic source in the test, said so), and runs it once that bar has
    closed. Narrowing the refusal to `D`'s own bars (the reviewer's change,
    `day_end(cal, day - timedelta(days=1))` in `_unclosed`) is the wrong
    change made, seen to fail, reverted and named in the commit body. A
    second test writes the rule mission 8 used (refuse any `D` later than
    the earliest, over the track's instruments, of each one's latest closed
    trading day) in the test file and shows, on `test_synth` (one
    calendar), at every hour of at least fourteen calendar days, that the
    two rules refuse and accept the same days. (b) A test on `test_synth`
    pins the T days that `replay` passes to decision 63's admission
    function for a candidate dated `D` whose seven calendar days hold a
    weekend: exactly the trading dates §4.1 gives (five weekdays). It also
    drives one admission whose verdict depends on those days: a live
    approach of the full cell whose net Sharpe at 1x over the right T days
    is below the candidate's score (`displaced`), and over a wrong window
    is above it (`not_better_than_weakest`), or the reverse. T taken as
    the last `t_days` trading days rather than the trading days in the
    last `t_days` calendar days is the wrong change seen to fail.

80. **O-3, DESIGN §18.2 with I-5, I-6 and decisions 18, 31 and 35: what the
    speed work may and may not change.** (a) Nothing a day computes or
    stores changes: for a fixed replay (the G1.3 scenario
    `tests/fixtures/scenarios/g1_lifecycle.jsonl` on `test_synth` with the
    gate configuration, from `2019-06-03` over at least 30 calendar days),
    the state directory written at the unit's parent and at the unit's
    commit is identical byte for byte outside `.git/`, with the same tree at
    `HEAD`; the commit body gives the command and its output. (b) Every
    reader still refuses a stored bar file whose content hash does not
    match the index. A listed month file may be hashed once per day run and
    the result used by every read of that run; a file changed after it was
    verified is refused by the first read of the next day run, which a test
    shows inside one `replay`. An in-memory cache that outlives one day run
    holds only values computed from inputs the day run reading it verifies
    again. Nothing new is written to the state directory for speed. (c) The
    day stays one process: no worker processes or threads are added. (d)
    Each speed unit measures, the same way before and after, foreground,
    one call each: the seconds per replay day of a controls-only replay of
    `test_synth` on the gate configuration (the first 20 days, as mission 9
    U3 measured) and of the G1.3 scenario's first 30 calendar days, and
    puts a profile of where the after-time goes in its commit body. (e) The
    target is O-3's: each item of gate M1 under 10 minutes (pytest's time
    as `./scripts/gate M1 G1.<n>` prints it) on the builder's machine. If it
    cannot be met without changing what a day computes, the builder files a
    finding (the next free `D-###`) with the measured times and the
    profile, and changes nothing that (a) forbids.

81. **O-4 in step S2.0a: one producer function and its derived records.**
    (a) The function lives in `src/discotrade/paper.py` (DESIGN §3 fixes
    the module list; O-4's series is derived from the journal like the
    paper records). Given a subject, a set `W` of trading dates and a
    column (`gross`, `net_1x` or `net_2x`), it returns, for each date of
    the subject's paper days in `W`, that column of the paper record minus
    the static exposure on that day: with `gross` the gross timing return,
    with `net_1x` or `net_2x` the exposure-adjusted net return. It is the
    one function O-18 names; mission 11's readers call it. (b) The unit
    return `r_i(u)` is the journal's `gross(u)` computed by the same code
    with the previous and the current position 1 (decisions 24 and 25;
    `u-1` the previous stored bar, prices adjusted as of `u`, so a roll gap
    is not a return); at an instrument's first stored bar, which has no
    previous bar, only the second term counts. `R_i(D)` is the sum over the
    bars of `i` whose trading date is `D`. (c) The subject's instruments
    and the daily mean are those of its paper `gross` (decision 23): the
    mean over all `N` of its instruments, an instrument with no bar on `D`
    contributing 0. `hbar_i(W)` is the mean of the journal `position` of
    the subject on `i` over its rows whose date is in `W`; with no such
    row it is 0. (d) What is stored to make this cheap is the builder's
    to shape (for example per instrument and day `R_i(D)`, and per subject,
    instrument and day the row count and the summed position, under
    `paper/<track>/`); anything stored is derived, staged with the day,
    written by a new day only, not rewritten by a re-run (I-6), rebuilt
    from the journal and the stored bars to the same content hash, and
    healed by decision 78's rule. (e) No lifecycle rule, statistic, table
    field, alert or gate reads it in this step; the register of O-18 that
    classifies it `producer` and its readers are step S2.0b's.

82. **Gate M1 in mission 10, O-2 and O-3.** Mission 10 closes no milestone,
    and its review's `## Gate` section says `not a closing mission`.
    Because O-3 measures its target on gate M1, the mission runs gate M1
    again at its pushed tip after the speed and O-4 units, item by item as
    O-2 rules (`./scripts/gate M1 G1.1` to `G1.4`, each its own foreground
    call with a 20-minute timeout), and `./scripts/gate M0` once, and
    reports each item's output verbatim with its time beside mission 9's
    (G1.1 892 s, G1.2 324 s, G1.3 1083 s, G1.4 1 s). An item that prints
    FAIL is a defect the mission fixes before its report, or, when the
    defect is outside the mission's units, a `VERDICT: mission 10 blocked`
    naming it. An item over 10 minutes that passes is decision 80 (e)'s
    finding, not a failure. No gate test changes in this mission.
