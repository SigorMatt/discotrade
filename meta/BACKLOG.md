# BACKLOG — carried items and the owner's list

Maintained by the architect. The builder does not act on this file. The
mission sequence is in `meta/ROADMAP.md`; this file holds what the roadmap
does not: review items postponed to a named step, and what waits for the
owner.

## Carried review items

Each item names the review it came from and the step that takes it.
REVIEW-1 should-fix 1 to 4, 6 and 7 are taken by mission 2 (step S0.2,
units U1 to U3); item 5 is the owner's (below). REVIEW-2 should-fix 1 and
2, and its note that no conftest blocks sockets (I-11), are taken by
mission 3 (step S0.3, unit U1; decisions-2026-10-12 items 18 to 20).
REVIEW-3 blocker 1 and should-fix 1 to 4 are taken by mission 4 (step
S0.3, units U1 to U4; decisions-2026-10-12 items 30 to 33). REVIEW-4
should-fix 1 and its note on `gaps.py` and `rolls.py` reading the index
before the reader are taken by mission 5 (step S0.4, unit U1;
decisions-2026-10-12 items 34 and 35). REVIEW-3's notes carried to step
S0.4 (reads before `trusted_from`, a roll record with the right `ts` and
the wrong contracts, the unlabelled cost lines of the `backtest` plain
output) are taken by mission 5 (unit U2; items 36 to 38). REVIEW-5
blocker 1, its should-fix 1 (finding D-005), its note on D-004 and its
note on `tests/test_gate_script.py`'s timeout are taken by mission 6
(step S0.4, units U0 to U4; decisions-2026-10-12 items 41 to 43 and 45).
REVIEW-6 should-fix 1 (FINAL-REPORT-6's sentence on the roll probe) is
taken by mission 7 (step S1.1, the final report; item 56), and the
REVIEW-3 note on the socket backstop (I-11) by mission 7 (unit U1; item
47). REVIEW-7 should-fix 1 (the network paths the backstop does not
guard) and 2 (no test separates the whole-span recompute from one chained
through stored positions) are taken by mission 8 (step S1.2, unit U1;
item 58). REVIEW-8 should-fix 1 (no test shows revival counts trading
days) and 2 (the scratch session's unguarded reverse lookup) are taken by
mission 9 (step S1.3, unit U1; items 66 and 67); its notes on the matched
draw's reading and on two transitions for one approach on one day are
answered by item 68 (a test of the second in U1). REVIEW-9 should-fix 1
(the per-day paper update no longer heals an interrupted day) is taken by
mission 10 (step S2.0a, unit U3; decisions-2026-10-14 item 78), and its
should-fix 2 (the untested branch of the not-closed refusal) and 3 (the T
days passed to admission), with finding D-007, by mission 10 (unit U4;
items 77 and 79). REVIEW-10 has no blocker and no should-fix; its note 3
(`paper.adjusted` calls the private `journal._empty()`, and a caller
passing staged records must pass `overlay` too) is taken by mission 11
(step S2.0b, unit U1; decisions-2026-10-14-m11 item 84), its `hands:`
note 7 is recorded as a hands finding by mission 11 U0 (item 90), and the
REVIEW-9 note on decision 68 (b) with the day's admission doing the
displacing by mission 11 (unit U3; item 86). REVIEW-11 has no blocker;
its should-fix 1 (`cli._backtest_result` unregistered) is taken by
mission 12 (step S2.1, unit U1; decisions-2026-10-14-m12 item 92), with
its note 7's list subscript and `replay._adjusted`, and finding D-010
(its note 3) by mission 12 U1 (item 93).

- REVIEW-11 notes, not carried as work unless named: decision 84 said
  the existing tests of `tests/test_exposure.py` stay unchanged while it
  replaced what one of them asserted, and the builder changed that test
  without filing a finding (a kit that changes what a test asserts names
  the test; the briefs since say so); `paper.adjusted` does not refuse a
  day missing from `positions.parquet` while `unit.parquet` holds it
  (decision 78's heal repairs it the next day; the step that next touches
  `paper.py`'s records may refuse it); the U3 "not rewritten" test writes
  the parent's format by hand; decision 79 (b)'s replay test passes on the
  plain measure too; G1.3 tells the two measures apart only through
  dormancy and return, every scenario line's adjusted admission score
  equalling its plain one, and step 3's return by displacing the weakest
  is not driven by G1.3 (step S3.2 or S4.1, whichever next touches the
  scenario, may give one admission line a non-zero `avg_position`); the
  rest of note 7 (the audit's module-wide match of the name `paper`, the
  one-hop call through `_figures` counted where only the plain figure is
  used, an uncalled nested function counted) and note 8 (`paper.portfolio`
  and `paper._series` are `producer` where O-18's table says display and
  `stage3_money` for the one condition) are step S4.1's, which next
  changes the register and builds the stage-3 reader; `table.build`'s
  `positions()` closure duplicates `paper._read_staged`, and the test
  helpers `own_journal`/`own_unit` cache by state path (the step that next
  touches `table.py`); G1.3 went from 450 s to 518 s and the per-day cost
  grows with history unprofiled (step S4.3, whose replays are longest,
  measures it if an M4 item nears 10 minutes).

- REVIEW-10 notes, not carried as work unless named: a month file changed
  on disk during a day run after its first verified read is served from
  the run's cache and refused only by the next day run (decision 80 (b)
  permits it), and no test drives a partial append that fails mid-day
  while the day continues; `state._column_fields` reads the private pandas
  attribute `column._values` (pinned by `tests/test_speed_pins.py`; the
  step that next touches `state.py` may use `column.array`); the paper
  heal compares dates only, and a death between the `journal/` and
  `ledger/` moves of `_move` still loses that day's lifecycle and rank
  rows (step S4.2, which builds staging and retry, takes it); the
  Saturday test of decision 79 (a) does not assert SYNX's bars had
  closed, and the mission 8 equivalence test shares `latest_closed_day`
  with the code under test.

- REVIEW-9 notes, not carried as work unless named: the net-return
  rank-persistence statistic G1.1 reports goes to a pytest warning that
  `scripts/gate` does not print (step S2.0b, which runs gate M1 again, or
  step S4.1, which builds O-5's net version beside the timing statistic,
  may make it readable); G1.3 does not assert the random pool's seeds as
  literals (a deterministic rule, decision 64); no test drives a block row
  due on a weekend day, the candidates file's refusal of a symlink or a
  `..` path, or decision 68 (b) with the day's admission doing the
  displacing (taken by mission 11, unit U3).

- REVIEW-8 notes, not carried as work: a state journaled before the
  controls existed would fail `journal.py`'s carry check (no state of this
  series predates the controls; no step takes it unless one does); the
  `if not dates` branch of the rank-persistence population rule is
  untested; a month whose 1st is a non-trading day on every calendar is
  met by G1.1's one-year replay on `test_synth` (all `synth_week`), not by
  a unit test.

- REVIEW-7 notes, not carried as work; the step that next touches the
  file may take them: `init_state` is not atomic (a failed first commit
  leaves a directory every later run refuses, `state.py`); the git
  protocol test checks only the environment dict, not that `_git` passes
  it; `journal.py`'s `REPO_ROOT = parents[2]` finds `reference/` and
  `tests/fixtures/` only from a source checkout (step S2.2 or S5.1 decides
  where trusted sources live in an installed package); `revised_data` is
  detected by matching the bar store's error text, and `daily.py` calls
  the private `store._indexed_last_ts` (a typed error is sturdier; step
  S4.2, which stages step 1, may take it); `journal recompute` leaves its
  `journal_mismatch` health line uncommitted until the next `run-day`.

- Finding D-006 (decision 44): each instrument's evaluation gets a
  freshly loaded strategy, and the cheating strategy of G0.2 is driven
  through the multi-instrument path. Step S2.1, with the sandbox's runner:
  taken by mission 12 (unit U3; decisions-2026-10-14-m12 item 95).
- REVIEW-5 notes, not carried as work; the step that next touches the
  file may take them: `rolls.py` reads, through `store.last_n`, up to 24
  bars before a roll that may lie before `trusted_from`, and uses only
  the first one's `ts`, clipped to `trusted_from` (decision 36 read
  literally says no such bar is read); `gaps.py` checks no listed file's
  hash when `start >= end`; the independent calculation's `ast` import
  check does not catch `builtins.__import__`, `sys.modules` or `runpy`
  (enough for honest code); G0.3 builds the gap-free series with the
  product's `tradingcal.expected_bars`, so a calendar defect shared by
  the generator and the gap check is not seen; G0.4 proves that contract
  roots are collected only through its planted control.

- REVIEW-6 notes, not carried as work: `test_g0_1_reference.py` writes
  the trade floor `1e-9` as a literal rather than reading it from the
  product (a test constant, not an I-10 threshold; if the floor ever
  moves, that test moves with it); the UTC-date grouping of the
  always-open calendar in the U2 self-test cases was not read against
  §5.3 by the reviewer.
- REVIEW-1 note: DESIGN §18.1's rule that tests marked `container` skip,
  with the reason printed, when no runtime is found is not built. The
  mission that adds the first `container` test builds it: step S2.2.
- REVIEW-1 note: every seed a gate test uses is written in the test file,
  not only in a fixture TOML (DESIGN §18.2). Step S0.4 (the first gate
  tests, mission 5, item 40) and every closing step.
- REVIEW-1 should-fix (U6, performance only): `bars fetch` builds a source
  per instrument and the synthetic source regenerates its series from
  `trusted_from` on every fetch. Take it when a replay gate's time limit
  (DESIGN §18.2, 15 minutes) is at risk: step S1.3 (the one-year replay
  of G1.1) at the latest (item 65). Taken by mission 9 (step S1.3, unit
  U3).
- REVIEW-2 note (U1, performance only): `recover` reads and hashes every
  month file of an instrument on every append, and `bars fetch` runs it
  twice per instrument. Take it with the item above: step S1.3 at the
  latest. Taken by mission 9 (step S1.3, unit U3).
- REVIEW-1 note: `tradingcal.in_main_session` cannot represent a main
  session that crosses midnight. No instrument has one; the step that adds
  such an instrument takes it.
- REVIEW-1 note: `config.py` bounds `drop_fraction` at 0.5 without a
  DESIGN source. Harmless for fixtures; no step takes it unless a fixture
  needs more.
- Left by step S1.1 to step S4.2 (decisions-2026-10-12 items 50, 51,
  54): staging of step 1's writes (bars, rolls, `gaps.jsonl`), the retry
  from a clean staging directory, `run_failed`, the push to a remote, the
  catch-up of missed days with `day_caught_up`, and the weekly journal
  recomputation as step 6 of §16.1. Left to step S2.2 (item 48): running
  approaches through the sandbox instead of the in-process loader.
- REVIEW-2 note (U4): when `update_rolls` fails after `bars fetch` wrote
  the bars, the command exits 1 and the next fetch records the roll,
  measuring its gap from a later source state. The daily run's staging and
  retry (step S4.2) take it.
- REVIEW-2 notes (U5, U6), for step S5.1, which builds the doctor and
  runs a day through the vendor adapter (G5.2): `vendor.py` passes the key
  to the client unstripped while its presence check strips it;
  `doctor --live spreads --days` is not range-checked (0 becomes 20);
  `spreads.py` calls `vendor.py`'s private `_guard`; the marginal-spread
  warning counts any hour that touches the main session while the spread
  rule treats the 09:00 bar as off-session; no test hits an even-count
  median in `spreads measure`.
- REVIEW-2 notes (U3): the 120-day roll look-ahead of `synth.py` is untested
  on sparse calendars, and only `roll_day` is tested for "contract key
  without a schedule". No step takes them unless a fixture calendar needs
  it.
- REVIEW-4 notes, not carried as work: the decision 18 test of `backtest`
  puts the unlisted month file after the window, so an unlisted file
  inside the window is not driven through the command; the `indicators`
  docstring's "no leading NaN" for `ema` holds for input finite at row 0,
  and "a Series or array and a window" is loose for `atr` and `donchian`.
  The step that next touches those files may take them.

## For the owner, before the first builder mission that needs it

- Steps S2.2 and S4.3 need Docker or Podman on the builder's machine.
  Without one the builder asks and the series stops there.
- The architect role's directory, set up as hands `architect/README.md`
  says, with this project's parameters (the plan kit's hand-over message
  gives the block).

## For the owner, at any time (frozen-config changes)

- REVIEW-1 should-fix 5, finding D-003 (filed by mission 2 U0): the
  `[spec]` `checked` and `source` strings of the eight instrument records
  read as if the exchange's pages were read on 2026-10-12; mission 1's
  report says the values are from memory. `[cost] source = "SPEC.md §17"`
  also covers the spread ticks and `slippage_coef`, which come from DESIGN
  §4.2 and R-5. Changing these strings is a frozen-config change: a
  decisions file and `config/HISTORY.toml` entries.

## For the owner, after the series (not milestones)

- Live checks L1 to L8 (DESIGN §19.3): vendor key, cost estimate and delay;
  measured spreads; the real model pool; a real coordinator call; the
  sandbox on the server; issues on the state repository's remote; every
  unverified fee, tick size, multiplier, session and cutoff; the planted
  market with the real worker pool.
- L1 and L2 as soon as M0 is met (their commands are built in step S0.2),
  while the data layer is fresh; they need the vendor key and do not stop
  the series.
- The slippage coefficient (0.02, R-5) calibrated against real fills in
  stage 2.
- The readings of DESIGN §20 (R-1 to R-28), to confirm or replace.
- SPEC §15's decisions: the length of T; the alert thresholds; where the
  dashboard is hosted; the stage-3 gate values; the money limits.
- Token budgets in `config/thresholds.toml` (R-19 placeholders).
- The architect's decisions of 2026-10-12
  (`meta/decisions/decisions-2026-10-12.md`), in particular item 2 (a
  stopped feed counts as missing bars to the end of the day, so generation
  is skipped), item 5 (an interrupted bar append is completed, not
  refused) and item 23 (how a basket's daily return is formed when its
  instruments have different calendars), to confirm or replace.

## Deferred to v2 (SPEC §15)

Workers with their own tool loop; cross-asset and portfolio-level
approaches; limit-order modeling; weighted allocation.
