# Decisions — 2026-10-13 (owner, written by the phone architect)

Decisions the owner took on 2026-10-13. Unlike the architect role's
decisions, these change `DESIGN.md` where they say so: a statistic, two
alert rules, one invariant's wording and the gate of milestone M4. They
are the owner's to take (`meta/ARCHITECT.md` §1) and the role builds on
them as on `DESIGN.md`. Items are numbered O-1 onward so that they never
collide with the numbered items of the role's decisions file. This file
wins over `DESIGN.md` and over any earlier decision it names.

How this file reached the branch: the mission 9 builder copied it,
unchanged, as its own `plan:` commit, on the owner's instruction. That is
the one exception to the never-edit list of `CLAUDE.md`; the reviewer does
not count that commit as a forbidden edit, and compares nothing but that
the file is the only one it touches.

Branch state when written: `main` at 768cb1c, mission 9 stopped at U7 on
findings D-008 and D-009.

## Part 1. Mission 9: findings D-008 and D-009

**O-1. D-008; DESIGN §18.3 G1.1, role decision 74: the rank-persistence
clause of G1.1 reads gross returns.** Decision 59's statistic, unchanged
in every other respect, taken on each random slot's summed paper `gross`
in place of `net_1x`, with the random slots as the population, has a mean
over its non-missing values within four standard errors of 0, with at
least 40 non-missing values. `stats.py`'s function takes the paper column
as a parameter, default `net_1x`, with a unit test. The day loop,
`rank_persistence.jsonl` and every production caller keep `net_1x` until
step S4.1 builds O-4. The test also computes the net statistic and reports
its mean and standard error, asserting nothing about it. G1.1's other
assertions stand. Reason: each slot's holding time, hence its cost, is
fixed for a month, and costs are about ten times the dispersion of gross
returns, so the ranking of net returns is the ranking of costs and
persists by construction (measured: mean 0.707 on net, -0.020 on gross,
51 blocks). The null market's claim is about gross returns.

**O-2. D-009; DESIGN §18.2, role decision 74: for M1 the gate is run item
by item.** `./scripts/gate M1 G1.1` to `G1.4`, each as its own foreground
call with a 20-minute timeout, all at the same pushed commit. M1's gate is
PASS when all four print their item PASS line there, and FAIL when any
prints FAIL or does not finish in its call. The builder and the reviewer
both run it this way, and the review's `## Gate` section records `Gate M1:
PASS` or `Gate M1: FAIL` on that basis, with the four outputs. `scripts/gate`
does not change, no span of decision 74 is shortened, and the 15-minute
limit of §18.2 is waived for M1 only. Reason: the spans are fixed by what
the items prove (a year; the 365-day dormant limit) and the measured total
is about 38 minutes.

**O-3. Plan line: the day loop's speed comes first in the next mission.**
A replay day costs 2.4 to 4 seconds with at most two approaches and no
sandbox; the gates of M3 and M4 replay with many approaches, each in a
sandbox. The first units of the mission after mission 9 measure where a
replay day's time goes and bring it down, before that mission's own step.
Target: each item of gate M1 under 10 minutes on the builder's machine,
with the before and after times in the report. If the target cannot be
met without changing what a day computes, that is a finding for the
owner, not a reason to change it.

## Part 2. Static exposure and the three finding alerts

The flaw O-1 found in the gate is also in the live statistic (DESIGN
§11.1, §15.1), and it has a second form. Cost is one stable offset between
approaches that is not skill; a directional lean is another. Four of the
eight contracts are equity indices: in a rising market an approach that is
long more often than short outranks a short-leaning one block after block,
and beats random controls that go long and short with equal probability,
with no predictive ability at all.

**O-4. Definitions: unit return, average position, static exposure,
timing return.** For a subject `s`, one of its instruments `i`, and a set
`W` of trading days (the window of the rule that asks):

- The unit return `r_i(u)` of bar `u` is the gross return DESIGN §7.2
  gives a position of 1 held into and through `u` (both terms of the
  formula with `h = 1`), computed by the same code as the journal's
  `gross`. `R_i(D)` is its sum over the bars of trading day `D`.
- The average position `hbar_i(W)` is the mean of the journal `position`
  `h(u)` of `s` on `i` over its rows in `W`.
- The static exposure of `s` on day `D` in `W` is the equal-weight mean,
  over the instruments of `s`, of `hbar_i(W) * R_i(D)`.
- The gross timing return of `s` on `D` is its paper `gross` on `D` minus
  its static exposure on `D`. The exposure-adjusted net return, at 1x and
  at 2x, is its paper `net_1x` or `net_2x` on `D` minus the same static
  exposure. Costs are not adjusted.

What this keeps is what the subject earned by varying its position; what
it drops is what it earned by being long or short on average. A
buy-and-hold control's gross timing return is exactly 0. Everything here
is derived from the journal and the stored bars, is rebuildable, and
follows the content-hash rule of DESIGN §9.3; what is stored to make it
cheap (per subject, instrument and day: rows, summed position, unit
return) is the builder's to shape.

**O-5. Rank persistence reads gross timing return (DESIGN §11.1, §15.1;
replaces the column of role decision 59 for the rules).** The block
statistic is the Spearman correlation, over the same population as
before, of the subjects' summed gross timing return in block `k - 1` and
in block `k`, where each block is its own window `W` (each block has its
own average positions). This is the statistic the `rank_persistence`
alert tests and the one the stage-3 condition "rank persistence
statistically above zero" (SPEC §14) reads. Each row of
`rank_persistence.jsonl` also carries the net-return version of decision
59, for information.

**O-6. The dashboard shows the net version beside it, used by no rule.**
The rank-persistence panel draws the timing statistic with its running
mean and significance band, and the net statistic beside it, labelled in
words as not used by any rule or gate.

**O-7. `persistent_approach` and `group_edge` read exposure-adjusted net
returns (DESIGN §15.1, §11.2, §11.4; role decision 60).**

- `persistent_approach`: `W` is the approach's clean paper days. Its
  Sharpe at 2x and at 1x are those of its exposure-adjusted net series
  over `W`. `mu_c` and `sd_c` are the mean and deviation of the random
  slots' Sharpes of their own exposure-adjusted net series at 1x over the
  same days, each slot with its own average positions. The conditions and
  the tightening of §11.4 are otherwise unchanged.
- `group_edge`: `W` is the last `group_days` days of `portfolio_clean`.
  The portfolio's figure is the sum over `W` of the equal-weight mean of
  its members' exposure-adjusted net returns at 1x, each member's average
  positions taken over the days of `W` on which it is a member. The
  bootstrap's control portfolios are built the same way from the slots'
  exposure-adjusted series.
- The deflated figures of §11.2 in the table (`S`, `E(N)`, the excess)
  are computed on the same exposure-adjusted series as the alert, and the
  table shows them beside the plain net Sharpe, each labelled.

What does not change: the journal, the paper record's `gross`, `net_1x`
and `net_2x`, the two portfolio series, the metrics of DESIGN §8,
retirement, and the stage-3 condition "the combined paper portfolio is
positive net of 2x costs", which is about money actually made. The
stage-3 condition "beats the random controls" is `group_edge`'s reading.
Admission, dormancy and return change in Part 3.

**O-8. Invariant I-4 gets a stated exception.** I-4 stands ("every score
is net of the cost model, at 1x and 2x") with one exception: the
rank-persistence statistic that rules read is computed on gross timing
return, by design, because its one job is to detect whether relative
performance carries information; whether an edge survives costs is tested
by the other two alerts, on net returns at 2x. Its net version is always
reported beside it.

**O-9. Gate M4 gains item G4.7, the null market with drift (DESIGN §18.3;
`scripts/gate` counts seven items for M4).** No item of M1 moves. On the
gate configuration, with every seed in the test:

- The market: the null market of DESIGN §17.1 with a positive mean hourly
  return, sized like a strongly rising index year, on new fixture
  instruments and a new fixture track (new records; no frozen fixture
  changes).
- (a) Leaning controls: a population of random slots with one shared
  holding time and long probabilities spread evenly from 0.1 to 0.9, each
  fixed for the whole replay. The long probability is a parameter of the
  control machine whose production value stays 0.5 (role decision 64);
  only the test passes another. Over at least 40 completed blocks, the
  rank-persistence statistic on gross timing return has a mean within
  four standard errors of 0, and the same statistic on plain `gross` has
  a mean more than four standard errors above 0, so the test is seen to
  detect the bias it removes.
- (b) Costs: with slots of differing holding times, as in G1.1, the
  statistic on gross timing return is within four standard errors of 0.
- (c) The alerts: fixture strategies that are long most of the time, trade
  often enough to be admitted, and whose timing carries no information,
  replayed long enough for `persistent_min_days` clean days and for
  `group_days`: neither `persistent_approach` nor `group_edge` fires. The
  test also computes, in the test, the plain net Sharpe of one such
  approach and the plain threshold, and asserts the plain reading would
  have crossed it.
- (d) Every buy-and-hold control's summed gross timing return is 0 to
  1e-12 in every block.
- (e) The lifecycle (O-11, O-12): a set of fixture strategies whose timing
  carries no information, half long-leaning and half their short-leaning
  mirrors, at least 100 of each over the T windows of the replay, scored
  by the admission function without being admitted (so that slots do not
  confound the count). The mean admission score of the long-leaning group
  and of the short-leaning group differ by less than four standard errors
  of the difference, and so do the shares with a positive score; the same
  two comparisons on the plain net Sharpe differ by more than four
  standard errors, so the test is seen to detect the bias. One small
  replay then shows a long-leaning approach with no timing skill neither
  admitted into a free slot nor displacing a live approach.
- (f) The grid (O-17): a fixture strategy whose timing is pseudo-random
  from a seed parameter and carries no information, with a `GRID` of two
  values of one parameter, a long lean and the mirrored short lean, run
  through the validation grid on at least 100 different seeds and W
  windows, the declaration order of the two values alternating so that
  the tie rule favours neither. The share of runs in which the grid fixes
  the long-leaning value is within four standard errors of one half; on
  the plain net Sharpe the same share is more than four standard errors
  from one half.
- G4.2 is unchanged and must still fire `persistent_approach` for the
  planted approach, now on the exposure-adjusted series.

**O-10. Where it is built.** Mission 9 builds none of this: M1 closes on
the lifecycle as built. Then, in this order:

1. O-3's speed work.
2. A step the role adds to M2 ahead of S2.1 (it moves no gate of M2): the
   definitions of O-4, the lifecycle of Part 3, the register and audit of
   O-18 with every reader that exists by then, and O-15's update of G1.3
   with gate M1 run again.
3. Step S2.1 builds the grid on the adjusted figure (O-17) from the start;
   step S3.2 scores real candidates on T with it from the start.
4. Step S4.1 builds O-5 to O-8 and O-14 with the alert rules and the
   dashboard, each rule unit-tested at its production thresholds.
5. Step S4.3 builds G4.7 with the other M4 gate tests.

The role updates `meta/ROADMAP.md` (the new step line in M2; the M4
gate's items become G4.1 to G4.7; the step lines concerned name this
file) in the kit that first touches them; those changes are approved
here.

## Part 3. The lifecycle reads the same measure

Slots are scarce (three per cell), and the registry tells workers to avoid
what already exists. On plain net Sharpe, long-leaning approaches would
take slots in a rising market on direction alone, be admitted together in
a rally and go dormant together at a reversal, and a short-leaning
approach with real timing skill would be refused for the wrong reason.
"Did better" now means one thing for admission, dormancy, return, the
alerts and rank persistence.

**O-11. Admission, dormancy and return read net Sharpe at 1x with static
exposure removed (DESIGN §10.3; role decisions 63 and 73).** Wherever
§10.3 and decision 63 say "net Sharpe at 1x", the figure is the Sharpe
of the subject's exposure-adjusted net series at 1x (O-4), with the
window `W` the days that rule already reads:

- the admission score: T, the candidate's average positions taken over
  its evaluation on T;
- dormancy (step 2) and return (step 3): the approach's last
  `dormant_window_days` paper rows.

Every other condition is unchanged (the trade count on T, the day
counts, the slot rules, a Sharpe that is not a number being neither
positive nor negative). A subject that holds one constant position has an
adjusted series of zeros, hence no Sharpe, and is not admitted.

**O-12. Comparisons with the weakest live approach use the same measure
over the same days.** For admission, each live approach of the cell is
scored on the same T days, with its own average positions over those
days; for return, over the same `dormant_window_days` rows. "Weakest"
is the lowest of those figures.

**O-13. Both figures are recorded, so the choice can be re-examined
without a replay.** A trial row keeps `metrics_t` (and `metrics_w`) as
they are and gains the exposure-adjusted figures for the same window:
Sharpe at 1x and 2x, total return at 1x and 2x, and the average position
per instrument. A lifecycle row for admission, displacement, dormancy or
return gains the adjusted figure that decided it and the plain one beside
it. The table shows, for each approach, the plain and the adjusted paper
Sharpe at 1x and 2x and its average position per instrument over its
paper record. New keys appear on new rows only; no earlier ledger line is
rewritten (I-5). A scripted candidates file (decision 73) supplies the
adjusted figures for T beside `metrics_t`; the scenario files of the
tests are updated by the mission that builds this.

**O-14. The dashboard shows the combined portfolio's exposure.** Beside
the combined portfolio's plain net result at 1x and 2x: its average net
position per instrument (the equal-weight mean of its members' average
positions over the last `group_days` days), and the part of its plain
net result that is static exposure (plain minus adjusted) over the same
days. A live approach can lose real money on its lean while its timing
return is positive; selection is not where that is handled, so it is
shown.

**O-15. Gate M1's item G1.3 follows the lifecycle.** G1.3's scenario
asserts lifecycle rows that the plain measure decided. The mission that
builds O-11 to O-13 updates that scenario's candidates file and the
test's own counts to the adjusted measure, keeps every transition G1.3
lists, and runs gate M1 again, item by item as O-2 says. No other item of
M1 or M0 changes. Gate M4's G4.7 gains part (e), in O-9.

## Part 4. One rule for every reader, and an audit

Three plain-net readers were found one at a time (the gate, the alerts,
the lifecycle), and a fourth by asking. This part settles the class.

**O-16. The rule.** Every place that selects, ranks or compares
approaches, or compares an approach or the portfolio with the controls,
reads the exposure-removed figure: exposure-adjusted net return for
everything except rank persistence, which reads gross timing return
(O-5, O-8). The window of the average position is the window the reader
already reads. Plain net return is used for two things only: display, and
the stage-3 condition "the combined paper portfolio is positive net of 2x
costs". A reader that fits neither and is not adjusted is a defect.

**O-17. The grid on W (DESIGN §12.2; reading R-23).** The grid fixes the
parameter combination with the best exposure-adjusted net Sharpe at 1x on
W, the average positions taken over W for each combination; the tie rule
is unchanged. The activity check, the dry run, determinism and the
correlation gate read positions, not returns, and do not change. The
trial row's `grid` records each combination's result under both measures
(plain and adjusted Sharpe at 1x and 2x), as O-13 does for T.

**O-18. The register of readers, and the test that keeps it complete.**
`tests/fixtures/return_readers.toml` lists every function under `src/`
that reads a return or a figure made from one: a reference to the columns
`gross`, `net_1x` or `net_2x`, to `metrics.sharpe`, `total_return` or
`max_drawdown`, or to a `sharpe` or `total_return` key of a metrics
mapping. Each entry names the module and function and one class:

- `producer`: computes or stores the figure and decides nothing with it;
- `display`: shows or records it, and nothing selects on what it shows;
- `stage3_money`: the one stage-3 money condition;
- `adjusted`: selects, ranks or compares on exposure-adjusted net return;
- `timing_gross`: rank persistence for the rules.

A test walks `src/` with `ast`, finds every such function, and fails when
one is not in the register, when a registered one no longer exists, or
when an `adjusted` or `timing_gross` entry does not call the one function
of O-4 that builds its series. So a new reader cannot appear unclassified.
A builder may add `producer` and `display` entries, each named in the
commit body, and the review of that mission reads each new entry against
O-16. An `adjusted` entry is never reclassified, and a second
`stage3_money` entry is never added, without the owner.

The register at the branch tip 768cb1c, read from the code, and what each
entry becomes:

| Reader | Today | Class |
|---|---|---|
| `lifecycle.step_rows`, dormancy (step 2) | Sharpe of paper `net_1x`, last window | adjusted (O-11) |
| `lifecycle.step_rows`, return and displacement (step 3), with `_sharpe_on` | Sharpe of paper `net_1x` | adjusted (O-11, O-12) |
| `lifecycle.admit`, the admission score | `metrics_t["sharpe"]` | adjusted (O-11) |
| `lifecycle.admit`, the weakest of the cell on T, with `_sharpe_on` | Sharpe of paper `net_1x` | adjusted (O-12) |
| `stats.rank_persistence` | summed paper `net_1x` | timing_gross for the rules; its net version display (O-5, O-6) |
| `stats.control_moments` | Sharpes of the slots' paper `net_1x` | adjusted (O-7) |
| `table`, the deflated figures `S`, `E_N`, `excess` | paper Sharpe at 1x | adjusted (O-7) |
| `table`, the paper record (Sharpe at 1x and 2x, drawdown, breakeven) and the admission score column | plain | display, with the adjusted figures added beside (O-13) |
| `paper`, the two portfolio series | means of members' plain returns | display, and stage3_money for the one condition |
| `replay`, the scripted candidate's `metrics_t` | carries `sharpe` | producer; it also carries the adjusted figures (O-13) |
| `cli`, the `backtest` output | plain §8 metrics | display |
| `metrics`, `backtest`, `journal`, `paper` (the subjects' rows) | compute and store | producer |

Readers the design names that are not built yet, classified now so that
the mission that builds each one registers it this way:

| Reader | Class |
|---|---|
| The grid on W (§12.2) | adjusted (O-17) |
| `persistent_approach`, both conditions (§15.1) | adjusted (O-7) |
| `group_edge` and its bootstrap (§15.1) | adjusted (O-7) |
| The `rank_persistence` alert and the stage-3 rank condition | timing_gross (O-5) |
| The stage-3 gates panel: "positive net of 2x costs" | stage3_money |
| The stage-3 gates panel: "beats the random controls" | adjusted (O-7) |
| Dashboard charts, the digest's tables, alert payload numbers | display, each alert payload carrying the figure that decided it and the plain one |
| Live checks L3 and L8, their counts of submissions "positive net of 2x costs on T" | adjusted, with the plain count reported beside it |

Confirmed as not readers of a return, so unchanged:

- The `weak` flag of a cell for the coordinator (DESIGN §14.1,
  `weak_window_days`). It is defined from lifecycle events (no live
  approach, or every live approach having gone dormant within its first
  `weak_window_days` paper days). It reads no return itself and follows
  the adjusted measure through the dormancy rule. Only its config key
  exists in the code today.
- The matching of the random control pool to live approaches (§10.1): it
  reads holding time and trade rate.
- The `revival` alert, portfolio membership, the trial count `N`, the
  trade-count conditions and the health alerts: events and counts.
- The `fragile` flag and `breakeven_cost`: display; nothing selects on
  them.

## Known and not proven

- Timing return discards a real edge that consists of holding one steady
  position for a whole window. With holds of 1 to 48 hours inside a
  14-day block this should be small; that is reasoning, not a
  measurement. The first historical replay on real data should report
  the three statistics both ways.
- On T (14 days) the discarded steady-position part is larger than on
  the alerts' 60 days, because a medium-horizon approach changes position
  fewer times in the window. Still reasoning, not measurement.
- The register's lower table classifies readers from `DESIGN.md`, not
  from code; a reader the design does not name can still be written. The
  audit test of O-18 is what catches it, and only for the reference
  shapes it scans; a figure passed on under another name, through a
  variable or a new column, is the review's to catch.
- G4.7's replay length depends on O-3's speed work.
