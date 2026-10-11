# CHECKPOINT

Mission: 1 (`meta/BUILDER-1-PROMPT.md`), roadmap step S0.1. Base 9ed3cd4.
Done: U0 766cf32, U1 f04fab2, U2 5ddcba4, U3 f4e0141.

Unit in progress: U4 Bar store (DESIGN §5.1, §5.2, §9.2 content hash; I-5).
Intent: bars/__init__.py, bars/store.py (append-only month files with index), state.py holding only the §9.2 content hash, tests.
Done means: tests: writer refuses unclosed, non-increasing and duplicate bars; append keeps old rows identical; month files split on UTC month; index has first/last ts, counts, hashes; reader half-open range and last n bars; reader refuses a month file not matching the index; one commit, pushed.

Standing constraints: one sub-agent per unit, foreground only; every unit
ends with a commit and a push listing every file; never `git add -A`;
`./scripts/check` green three times before every commit; builder never edits
DESIGN.md, SPEC.md, PLAYBOOK.toml or the other files CLAUDE.md protects;
design problems are findings in `meta/findings/FINDINGS.md`; report drafts
live in `meta/drafts/`.
