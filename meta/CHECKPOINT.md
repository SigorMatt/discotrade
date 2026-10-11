# CHECKPOINT

Mission: 2 (`meta/BUILDER-2-PROMPT.md`), roadmap step S0.2. Base 1151e55.
Done: U0 87d4a23, U1 f3f8c2d, U2 8e423c1.

Unit in progress: U3 Synthetic market with contracts and configured generator settings (REVIEW-1 should-fix 2; decision 10; DESIGN §4.2, §5.1, §5.5, §17.1).
Intent: quarterly roll schedule, contract column, fetch_contract, per-contract constants from [source]; generator keys read from config and refused by name when missing; fixture fetches unchanged by hash.
Done means: U3 gate tests pass, ./scripts/check green x3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN; no value of a frozen file changes (config/, existing
entries of tests/fixtures/config_frozen.json); one commit per unit, files
listed, never `git add -A`, push; ./scripts/check green three times before
each commit; sub-agents in the foreground only; no network, secret or
wall clock in tests.
