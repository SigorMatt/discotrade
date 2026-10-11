# CHECKPOINT

Mission: 2 (`meta/BUILDER-2-PROMPT.md`), roadmap step S0.2. Base 1151e55.
Done: U0 87d4a23, U1 f3f8c2d, U2 8e423c1, U3 cb9c21d.

Unit in progress: U4 Rolls and the adjusted series (DESIGN §5.6, §5.5 bars fetch; decision 16; I-5, I-6, I-12).
Intent: roll detection on stored bars; append-only <state>/rolls/<track>/<symbol>.jsonl with measured or estimated gap and notice; adjusted series as of t; bars fetch updates rolls.
Done means: U4 gate tests pass, ./scripts/check green x3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN; no value of a frozen file changes (config/, existing
entries of tests/fixtures/config_frozen.json); one commit per unit, files
listed, never `git add -A`, push; ./scripts/check green three times before
each commit; sub-agents in the foreground only; no network, secret or
wall clock in tests.
