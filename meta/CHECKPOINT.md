# CHECKPOINT

Mission: 5 (`meta/BUILDER-5-PROMPT.md`), roadmap step S0.4. Closes M0. Base 3854c96.
Done: U0 9d2d781, U1 8e8215c, U2 8d27fe1, U3 3be4e9b.

Unit in progress: U5 (next). U4 waits on finding D-004 (DESIGN §8 max_drawdown: does the
running sum start at 0?): discotrade 0.22244801873145578 vs independent calc 0.21593456441431036
for zscore_reversal on test_mixed 2019-06-03..2019-07-31; all else equal to 1e-12 (20/22 tests).
Draft test kept in `git stash` as "wip U4 2026-10-12 ..."; D-005 filed (G0.1 data cannot see
roll cost on h(u) nor the half-tick floor). U5 and U6 do not depend on U4.
Intent: U5 — cheat_lookahead.py strategy and tests/gates/test_g0_2_cheating.py (decision 40).
Done means: one commit pushed; one leaking wrong change seen to fail; check green x3.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 34-40 new, 1-33 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ with markers gate and gate_m0, seeds in the file, state under tmp_path,
in-process command, no subprocess, no skip; one commit per unit, files listed, never `git add -A`,
push; ./scripts/check green three times before each commit (foreground, timeout >= 20 min);
sub-agents in the foreground only; no network, secret or wall clock in tests; existing tests
unchanged in what they assert unless a cited decision changes it (then the body says so).
