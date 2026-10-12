# CHECKPOINT

Mission: 3 (`meta/BUILDER-3-PROMPT.md`), roadmap step S0.3. Base ef2e9f1.
Done: U0 02b366c, U1 a966344.

Unit in progress: U2 Strategy contract, loader and indicator library.
Intent: DESIGN §6.1, §6.2 (the result check), §6.3; decisions 21, 22; I-1, I-2, I-10.
Files: src/discotrade/strategy.py, src/discotrade/indicators.py, tests/test_strategy.py,
tests/test_indicators.py, tests/fixtures/strategies/.
Done means: U2's gate in meta/BUILDER-3-PROMPT.md has tests, check green x3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN (items 18-29 new, 1-17 still bind); no value of a frozen
file changes (config/, existing entries of tests/fixtures/config_frozen.json);
nothing under tests/gates/; one commit per unit, files listed, never
`git add -A`, push; ./scripts/check green three times before each commit;
sub-agents in the foreground only; no network, secret or wall clock in tests.
