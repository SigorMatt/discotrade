# CHECKPOINT

Mission: 2 (`meta/BUILDER-2-PROMPT.md`), roadmap step S0.2. Base 1151e55.
Done: U0 87d4a23, U1 f3f8c2d, U2 8e423c1, U3 cb9c21d, U4 61e1c59.

Unit in progress: U5 Vendor and crypto adapters, and live check L1 offline (DESIGN §5.5, §19.3 L1; decisions 11, 12, 15; I-9, I-11, I-13).
Intent: vendor adapter with lazy client import, cost-estimate refusal, 24h embargo, symbology contract, fetch_contract; fake client; crypto adapter over httpx with MockTransport tests; doctor --live vendor offline refusal; vendor extra only.
Done means: U5 gate tests pass, ./scripts/check green x3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN; no value of a frozen file changes (config/, existing
entries of tests/fixtures/config_frozen.json); one commit per unit, files
listed, never `git add -A`, push; ./scripts/check green three times before
each commit; sub-agents in the foreground only; no network, secret or
wall clock in tests.
