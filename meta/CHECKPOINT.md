# CHECKPOINT

Mission: 6 (`meta/BUILDER-6-PROMPT.md`), roadmap step S0.4 repaired. Closes M0. Base 19196da.
Done: U0 cdc031f, U1 c1a2100.

Unit in progress: U2 The independent calculation's self-test: a position that changes at the roll
(REVIEW-5 should-fix 1; D-005; decisions 24, 25, 39, 43 (a)). Own sub-agent, forbidden-files words.
Intent: tests/gates/test_g0_1_calc_self.py gains hand cases (carried position changing size/sign at a
roll; flat position opening at a roll) checking roll cost, row cost, net_1x, net_2x, breakeven_cost.
Done means: calc roll cost on h(u) and rolled turnover on h(u) each seen to fail; existing cases
unchanged; ./scripts/gate M0 G0.1 passes; check green x3; body states no forbidden file was opened.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 41-46 new, 1-40 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ named test_g0_<n>_<what>.py, markers gate and gate_m0, seeds in the file,
state under tmp_path, in-process command, no subprocess, no skip, each item < 15 min; product
defects fixed only with a unit test outside tests/gates/ seen to fail first; where code is already
right, the wrong change is made and reverted in the worktree and named in the body; one commit per
unit, files listed, never `git add -A`, push; ./scripts/check green three times before each commit
(foreground, timeout >= 20 min, HF-006); sub-agents in the foreground only; no network, secret or
wall clock in tests; existing tests unchanged in what they assert unless a cited decision changes
it (then the body says so); U2 (and any calc fix) by its own sub-agent under the forbidden-files words.
