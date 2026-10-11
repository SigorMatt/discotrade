# CHECKPOINT

Mission: 1 (`meta/BUILDER-1-PROMPT.md`), roadmap step S0.1. Base 9ed3cd4.
Done: U0 766cf32, U1 f04fab2, U2 5ddcba4.

Unit in progress: U3 Trading calendar (DESIGN §5.3, §4.3 frozen config).
Intent: tradingcal.py, config/calendars/cme_globex.toml with 2019-2027 closures (verified=false), fixture calendars always_open and synth_week, calendar values in config_frozen.json, config check loads calendars.
Done means: tests for open/closed, trading date, expected bar times, main session across both DST weeks, weekend, daily break, closure; hypothesis test that expected bars overlap open intervals; one commit, pushed.

Standing constraints: one sub-agent per unit, foreground only; every unit
ends with a commit and a push listing every file; never `git add -A`;
`./scripts/check` green three times before every commit; builder never edits
DESIGN.md, SPEC.md, PLAYBOOK.toml or the other files CLAUDE.md protects;
design problems are findings in `meta/findings/FINDINGS.md`; report drafts
live in `meta/drafts/`.
