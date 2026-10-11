# CHECKPOINT

Mission: 1 (`meta/BUILDER-1-PROMPT.md`), roadmap step S0.1. Base 9ed3cd4.
Done: U0 766cf32, U1 f04fab2, U2 5ddcba4, U3 f4e0141, U4 8348743.

Unit in progress: U5 Gap check (DESIGN §5.4, §4.1 windows, §15.2 health event).
Intent: bars/gaps.py, `discotrade bars gaps` subcommand, tests; check returns the §15.2 health event as a value.
Done means: tests: known removed bars reported exactly and appended once to gaps.jsonl; none across daily break, weekend, closure; fraction pooled over the track's instruments; above gaps.max_fraction in W or T generation is skipped with a data_gaps health event, at or below not; one commit, pushed.

Standing constraints: one sub-agent per unit, foreground only; every unit
ends with a commit and a push listing every file; never `git add -A`;
`./scripts/check` green three times before every commit; builder never edits
DESIGN.md, SPEC.md, PLAYBOOK.toml or the other files CLAUDE.md protects;
design problems are findings in `meta/findings/FINDINGS.md`; report drafts
live in `meta/drafts/`.
