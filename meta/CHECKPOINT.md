# CHECKPOINT

Mission: 2 (`meta/BUILDER-2-PROMPT.md`), roadmap step S0.2. Base 1151e55.
Done: U0 87d4a23, U1 f3f8c2d, U2 8e423c1, U3 cb9c21d, U4 61e1c59, U5 5995b92.

Unit in progress: U6 Spread tables and their measurement, and live check L2 offline (DESIGN §5.7, §19.3 L2; decisions 13-15; I-10).
Intent: spread rule (table hour or main/off), config/spreads loading and frozen rule, marginal-spread warning, spreads measure command, doctor --live spreads offline refusal.
Done means: U6 gate tests pass, ./scripts/check green x3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN; no value of a frozen file changes (config/, existing
entries of tests/fixtures/config_frozen.json); one commit per unit, files
listed, never `git add -A`, push; ./scripts/check green three times before
each commit; sub-agents in the foreground only; no network, secret or
wall clock in tests.
