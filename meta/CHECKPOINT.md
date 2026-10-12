# CHECKPOINT

Mission: 3 (`meta/BUILDER-3-PROMPT.md`), roadmap step S0.3. Base ef2e9f1.
Done: U0 02b366c, U1 a966344, U2 542c171, U3 833aa25+ec1c8a4, U4 3c24e5f, U5 8cfd390.

Unit in progress: U6 Reference strategies and the `backtest` command.
Intent: DESIGN §3, §6.1, §18.3 G0.1's strategy list; decisions 21, 27; I-4, I-9.
Files: reference/*.py (three), src/discotrade/cli.py (`backtest`), tests/test_reference.py,
tests/test_cli_backtest.py.
Done means: U6's gate in meta/BUILDER-3-PROMPT.md has tests, check green x3, one commit pushed.
Carried from U4: the backtest command must pass each instrument's spread table to evaluate.
Carried to U6: evaluate's spread_table is optional (None = main/off rule); the backtest
command must load each instrument's spread table, with a test.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN (items 18-29 new, 1-17 still bind); no value of a frozen
file changes (config/, existing entries of tests/fixtures/config_frozen.json);
nothing under tests/gates/; one commit per unit, files listed, never
`git add -A`, push; ./scripts/check green three times before each commit;
sub-agents in the foreground only; no network, secret or wall clock in tests.
