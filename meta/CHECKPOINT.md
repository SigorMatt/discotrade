# CHECKPOINT

Mission: 3 (`meta/BUILDER-3-PROMPT.md`), roadmap step S0.3. Base ef2e9f1.
Done: U0 02b366c, U1 a966344, U2 542c171, U3 833aa25+ec1c8a4.

Unit in progress: U4 Cost model and executor.
Intent: DESIGN §7.3, §7.4, §5.7; decisions 24, 25, 26; R-3, R-5; I-4, I-15.
Files: src/discotrade/costs.py, src/discotrade/executor.py, tests/test_costs.py,
tests/test_executor.py, and in src/discotrade/backtest.py only the call that turns
positions into orders and fills into per-bar rows.
Done means: U4's gate in meta/BUILDER-3-PROMPT.md has tests, check green x3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN (items 18-29 new, 1-17 still bind); no value of a frozen
file changes (config/, existing entries of tests/fixtures/config_frozen.json);
nothing under tests/gates/; one commit per unit, files listed, never
`git add -A`, push; ./scripts/check green three times before each commit;
sub-agents in the foreground only; no network, secret or wall clock in tests.
