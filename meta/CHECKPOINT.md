# CHECKPOINT

Mission: 1 (`meta/BUILDER-1-PROMPT.md`), roadmap step S0.1. Base 9ed3cd4.
Done: U0 766cf32, U1 f04fab2.

Unit in progress: U2 Configuration records (DESIGN §4.1, §4.2, §4.3; I-9, I-10).
Intent: config.py frozen records, hourly track and eight instruments, thresholds.toml, fixtures (frozen map, test config), HISTORY.toml, `discotrade config check` in the smoke test.
Done means: tests for every refusal, thresholds history test, W/T windows as date ranges, I-9 symbol scan test, `uv run discotrade config check` exits 0 listing unverified values; one commit, pushed.

Standing constraints: one sub-agent per unit, foreground only; every unit
ends with a commit and a push listing every file; never `git add -A`;
`./scripts/check` green three times before every commit; builder never edits
DESIGN.md, SPEC.md, PLAYBOOK.toml or the other files CLAUDE.md protects;
design problems are findings in `meta/findings/FINDINGS.md`; report drafts
live in `meta/drafts/`.
