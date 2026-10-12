# CHECKPOINT

Mission: 5 (`meta/BUILDER-5-PROMPT.md`), roadmap step S0.4. Closes M0. Base 3854c96.
Done: U0 9d2d781, U1 8e8215c, U2 8d27fe1, U3 3be4e9b.

Unit in progress: U4 (next).
Intent: U4 — tests/gates/test_g0_1_reference.py: three reference strategies on test_mixed, window
with SYNA roll and synth_week closure, discotrade vs independent_calc to 1e-12; mismatch rule.
Done means: one commit pushed; >= 2 wrong changes in product code seen to fail; check green x3.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 34-40 new, 1-33 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ with markers gate and gate_m0, seeds in the file, state under tmp_path,
in-process command, no subprocess, no skip; one commit per unit, files listed, never `git add -A`,
push; ./scripts/check green three times before each commit (foreground, timeout >= 20 min);
sub-agents in the foreground only; no network, secret or wall clock in tests; existing tests
unchanged in what they assert unless a cited decision changes it (then the body says so).
