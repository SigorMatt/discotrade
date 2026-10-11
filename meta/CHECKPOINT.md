# CHECKPOINT

Mission: 1 (`meta/BUILDER-1-PROMPT.md`), roadmap step S0.1. Base 9ed3cd4.
Done: U0 766cf32, U1 f04fab2, U2 5ddcba4, U3 f4e0141, U4 8348743, U5 3b5439e.

Unit in progress: U6 Null synthetic market (DESIGN §5.5 interface, §17.1 without contracts).
Intent: sources/__init__.py, sources/base.py (BarSource protocol), sources/synth.py (null market, dropped-bar option, non-shortable instrument; contracts raise not built), `discotrade bars fetch` writing through the store and running the gap check.
Done means: tests: seed determinism; high/low enclose open/close; bars only at expected times; two-year mean and lag-1 autocorrelation within four standard errors of zero; bars fetch then bars gaps reports exactly the dropped bars; one commit, pushed.

Standing constraints: one sub-agent per unit, foreground only; every unit
ends with a commit and a push listing every file; never `git add -A`;
`./scripts/check` green three times before every commit; builder never edits
DESIGN.md, SPEC.md, PLAYBOOK.toml or the other files CLAUDE.md protects;
design problems are findings in `meta/findings/FINDINGS.md`; report drafts
live in `meta/drafts/`.
