# CHECKPOINT

Mission: 2 (`meta/BUILDER-2-PROMPT.md`), roadmap step S0.2. Base 1151e55.
Done: U0 87d4a23, U1 f3f8c2d.

Unit in progress: U2 Command-line, config-check and gate-script repairs (REVIEW-1 should-fix 3, 6, 7; decisions 7-9; DESIGN §3, §4.3, §18.1, §18.2; I-10, I-14).
Intent: refuse --state inside a code repo and empty --state/DISCOTRADE_STATE; type-strict frozen-config comparison; single-item gate run prints only the item verdict; gate marker collection errors.
Done means: U2 gate tests pass, ./scripts/check green x3 printing config check: ok and check: green, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN; no value of a frozen file changes (config/, existing
entries of tests/fixtures/config_frozen.json); one commit per unit, files
listed, never `git add -A`, push; ./scripts/check green three times before
each commit; sub-agents in the foreground only; no network, secret or
wall clock in tests.
