# CHECKPOINT

Mission: 1 (`meta/BUILDER-1-PROMPT.md`), roadmap step S0.1. Base 9ed3cd4.
Done: U0 766cf32, U1 f04fab2, U2 5ddcba4, U3 f4e0141, U4 8348743, U5 3b5439e, U6 e1c3f76.

Unit in progress: U7 Final report.
Intent: meta/FINAL-REPORT-1.md drafted under meta/drafts/ and moved in: sha per unit, what tests prove, NOT PROVEN, findings filed, empty Review items table.
Done means: the report is committed and pushed; then the verdict line.

Standing constraints: one sub-agent per unit, foreground only; every unit
ends with a commit and a push listing every file; never `git add -A`;
`./scripts/check` green three times before every commit; builder never edits
DESIGN.md, SPEC.md, PLAYBOOK.toml or the other files CLAUDE.md protects;
design problems are findings in `meta/findings/FINDINGS.md`; report drafts
live in `meta/drafts/`.
