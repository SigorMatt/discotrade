# BACKLOG — carried items and the owner's list

Maintained by the architect. The builder does not act on this file. The
mission sequence is in `meta/ROADMAP.md`; this file holds what the roadmap
does not: review items postponed to a named step, and what waits for the
owner.

## Carried review items

(none yet; each item names the review it came from and the step that takes
it)

## For the owner, before the first builder mission that needs it

- Steps S2.2 and S4.3 need Docker or Podman on the builder's machine.
  Without one the builder asks and the series stops there.
- The architect role's directory, set up as hands `architect/README.md`
  says, with this project's parameters (the plan kit's hand-over message
  gives the block).

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

## Deferred to v2 (SPEC §15)

Workers with their own tool loop; cross-asset and portfolio-level
approaches; limit-order modeling; weighted allocation.
