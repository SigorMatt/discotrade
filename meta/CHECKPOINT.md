# CHECKPOINT

Mission: 4 (`meta/BUILDER-4-PROMPT.md`), roadmap step S0.3 (repair). Base 9f00d99.
Done: U0 593c0ea, U1 836c2ab, U2 6445223.

Unit in progress: U3 `BarStore.last_ts` refuses as a reader.
Intent: `last_ts` refuses with the interrupted-append error for an unlisted month file that
passes decision 5's test with r = 0, with the revised-data-point error otherwise and for a
listed file whose hash differs; after `bars fetch` completes the append it returns the
completed last ts; a test classifies every public BarStore method as refusing reader or
non-reader (decision 31: cli.py calls move to a private index helper where needed).
Done means: tests seen to fail on the parent; recovery and writer tests unchanged in what
they assert; check green x3; one commit, pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 30-33 new, 1-29 still bind with item 33's renumbering); no value of a frozen file
changes (config/, existing entries of tests/fixtures/config_frozen.json); nothing under
tests/gates/; one commit per unit, files listed, never `git add -A`, push; ./scripts/check
green three times before each commit; sub-agents in the foreground only; no network, secret
or wall clock in tests; every existing test unchanged in what it asserts unless a cited
decision changes it (then the commit body says so).
