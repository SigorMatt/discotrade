# CHECKPOINT

Mission: 4 (`meta/BUILDER-4-PROMPT.md`), roadmap step S0.3 (repair). Base 9f00d99.
Done: U0 593c0ea, U1 836c2ab, U2 6445223, U3 9c4023b.

Unit in progress: U4 Indicator module text.
Intent: docstrings only in src/discotrade/indicators.py (no behaviour change); a test over
every public function: windowed functions NaN at row 0 for window >= 2 in every returned
column, except those the module docstring names as seeded (at least `ema`), which are a
number at row 0; the docstring names `ema`'s seeding and any other exception found.
Done means: test seen to fail on the parent; hand-value and property tests unchanged;
check green x3; one commit, pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 30-33 new, 1-29 still bind with item 33's renumbering); no value of a frozen file
changes (config/, existing entries of tests/fixtures/config_frozen.json); nothing under
tests/gates/; one commit per unit, files listed, never `git add -A`, push; ./scripts/check
green three times before each commit; sub-agents in the foreground only; no network, secret
or wall clock in tests; every existing test unchanged in what it asserts unless a cited
decision changes it (then the commit body says so).
