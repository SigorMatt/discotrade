# CHECKPOINT

Mission: 4 (`meta/BUILDER-4-PROMPT.md`), roadmap step S0.3 (repair). Base 9f00d99.
Done: U0 593c0ea, U1 836c2ab, U2 6445223, U3 9c4023b, U4 300be21, U5 e740b3b.

Unit in progress: none. Mission 4 finished; meta/FINAL-REPORT-4.md exists.
Intent: next: the cold review of mission 4, then the architect's next kit (mission 5, S0.4,
closes M0 per decision 33).
Done means: n/a

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 30-33 new, 1-29 still bind with item 33's renumbering); no value of a frozen file
changes (config/, existing entries of tests/fixtures/config_frozen.json); nothing under
tests/gates/; one commit per unit, files listed, never `git add -A`, push; ./scripts/check
green three times before each commit; sub-agents in the foreground only; no network, secret
or wall clock in tests; every existing test unchanged in what it asserts unless a cited
decision changes it (then the commit body says so).
