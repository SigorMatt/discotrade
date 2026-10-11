# CHECKPOINT

Mission: 2 (`meta/BUILDER-2-PROMPT.md`), roadmap step S0.2. Base 1151e55.
Done: U0 87d4a23.

Unit in progress: U1 Store and gap-check repairs (REVIEW-1 should-fix 1
and 4; decisions 2-6, 16; DESIGN §5.1, §5.2, §5.4, §15.2; I-5, I-6, I-12).
Intent: interrupted-append recovery with a `store_recovered` notice;
non-finite bars refused by the writer and dropped by `bars fetch`; gap
check for day D ignores bars after D; window fraction counts stopped and
absent feeds to the end of D; atomic append of gaps.jsonl; `bars gaps`
default day from §16.1 for `--as-of`; fsync before each rename.
Done means: the U1 gate tests in the brief pass, ./scripts/check green x3,
one commit pushed listing every file.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12
wins over DESIGN; no value of a frozen file changes (config/, existing
entries of tests/fixtures/config_frozen.json); one commit per unit, files
listed, never `git add -A`, push; ./scripts/check green three times before
each commit; sub-agents in the foreground only; no network, secret or
wall clock in tests.
