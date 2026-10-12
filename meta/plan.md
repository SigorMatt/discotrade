# PLAN — mission 7 (roadmap step S1.1)

Base commit: c73a695 (`plan: mission 7 kit (S1.1, state, health log, journal, run-day)`).
Brief: `meta/BUILDER-7-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-12.md` (items 47-57 new; 1-46 still bind).
Roadmap step: S1.1. This mission closes no milestone and adds no test under `tests/gates/`.

Carried items:
- REVIEW-3 note on the socket backstop outside function-scoped tests (decision 47). — taken by U1
- REVIEW-6 should-fix 1: FINAL-REPORT-6 describes the probe test as asserting more than it does (decision 56). — taken by U6
- REVIEW-6 `hands:` note (protocol step 2 vacuous on tests-only commits; check run once). — recorded as HF-007 by U0

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, HF-007 in `meta/findings/FINDINGS.md`. — 057f9d2
- [x] U1 The socket backstop outside function-scoped tests (REVIEW-3 note; decisions 20, 47; I-11; DESIGN §18.1). — de2a5b2
- [x] U2 The state directory, the lock, the state commit and the health log (decisions 7, 50, 52, 55; DESIGN §3, §9.1, §15.2, §16.2). — c8342c4
- [x] U3 Approaches and the decision journal (decisions 24, 25, 39, 48, 49, 51; DESIGN §6.2, §7, §9.1, §9.2). — e44866d
- [x] U4 `run-day` and the paper records (decisions 2, 3, 19, 50-53, 55; DESIGN §9.3, §15.2, §16.1 steps 1-2, §16.2). — 1fbf800
- [ ] U5 `journal recompute` (decision 54; DESIGN §9.4, §15.2).
- [ ] U6 Final report (`meta/FINAL-REPORT-7.md`), with `./scripts/gate M0` at the pushed tip.
