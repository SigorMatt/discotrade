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
output) are taken by mission 5 (unit U2; items 36 to 38).

- REVIEW-3 note (I-11): the socket backstop is a function-scoped autouse
  fixture, so module-scoped fixtures (`test_gaps.py`, `test_rolls.py`)
  and subprocesses launched by tests run outside it, and `_socket` used
  directly passes. Step S1.1: mission 5's gate tests launch no
  subprocess (decisions-2026-10-12 item 40).
- REVIEW-1 note: DESIGN §18.1's rule that tests marked `container` skip,
  with the reason printed, when no runtime is found is not built. The
  mission that adds the first `container` test builds it: step S2.2.
- REVIEW-1 note: every seed a gate test uses is written in the test file,
  not only in a fixture TOML (DESIGN §18.2). Step S0.4 (the first gate
  tests, mission 5, item 40) and every closing step.
- REVIEW-1 should-fix (U6, performance only): `bars fetch` builds a source
  per instrument and the synthetic source regenerates its series from
  `trusted_from` on every fetch. Take it when a replay gate's time limit
  (DESIGN §18.2, 15 minutes) is at risk: step S1.2 at the latest.
- REVIEW-2 note (U1, performance only): `recover` reads and hashes every
  month file of an instrument on every append, and `bars fetch` runs it
  twice per instrument. Take it with the item above: step S1.2 at the
  latest.
- REVIEW-1 note: `tradingcal.in_main_session` cannot represent a main
  session that crosses midnight. No instrument has one; the step that adds
  such an instrument takes it.
- REVIEW-1 note: `config.py` bounds `drop_fraction` at 0.5 without a
  DESIGN source. Harmless for fixtures; no step takes it unless a fixture
  needs more.
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
