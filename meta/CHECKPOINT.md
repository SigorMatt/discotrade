# CHECKPOINT

Mission: 4 (`meta/BUILDER-4-PROMPT.md`), roadmap step S0.3 (repair). Base 9f00d99.
Done: U0.

Unit in progress: U1 Sharpe at zero deviation, and the `trades` test.
Intent: `sharpe` / `sharpe_2x` not a number when the daily series' deviation is 0 by
decision 30 (all values equal to the first, or std(ddof=1) <= 1e-12 * max|d|); a `trades`
test that fails for both wrong implementations named in the brief.
Done means: tests in tests/test_metrics.py seen to fail on the parent (and against the two
wrong `trades` changes, made and reverted); src/discotrade/metrics.py fixed; check green x3;
one commit listing every file, pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 30-33 new, 1-29 still bind with item 33's renumbering); no value of a frozen file
changes (config/, existing entries of tests/fixtures/config_frozen.json); nothing under
tests/gates/; one commit per unit, files listed, never `git add -A`, push; ./scripts/check
green three times before each commit; sub-agents in the foreground only; no network, secret
or wall clock in tests; every existing test unchanged in what it asserts unless a cited
decision changes it (then the commit body says so).
