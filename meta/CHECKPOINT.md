# CHECKPOINT

Mission: 4 (`meta/BUILDER-4-PROMPT.md`), roadmap step S0.3 (repair). Base 9f00d99.
Done: U0 593c0ea, U1 836c2ab.

Unit in progress: U2 `backtest` exit 1 paths.
Intent: tests that `discotrade backtest` exits 1 with an error naming the cause, after
`bars fetch` on test_mixed into a temp state dir, for: missing roll record/context
(decision 24), strategy returns 2.0 and strategy raises (decision 22), loader refuses the
text (decision 21), unlisted month file (decision 18). Strategy texts in a temp reference
root (in-process seam), nothing written into the working tree.
Done means: each new test seen to fail against a wrong change (made and reverted); existing
exit 2 and refused-bar-file tests unchanged; check green x3; one commit, pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 30-33 new, 1-29 still bind with item 33's renumbering); no value of a frozen file
changes (config/, existing entries of tests/fixtures/config_frozen.json); nothing under
tests/gates/; one commit per unit, files listed, never `git add -A`, push; ./scripts/check
green three times before each commit; sub-agents in the foreground only; no network, secret
or wall clock in tests; every existing test unchanged in what it asserts unless a cited
decision changes it (then the commit body says so).
