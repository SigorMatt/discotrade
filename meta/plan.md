# PLAN — mission 8 (roadmap step S1.2)

Base commit: fb1e244 (`plan: mission 8 kit (S1.2, controls, ledgers, lifecycle, stats)`).
Brief: `meta/BUILDER-8-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-12.md` (items 58-65 new; 1-57 still bind).
Roadmap step: S1.2 (as decision 65 cuts it). This mission closes no milestone and adds no test under `tests/gates/`.

Carried items:
- REVIEW-7 should-fix 1: the socket backstop leaves `sendmsg` and the name lookups unguarded (decisions 47, 58). — taken by U1
- REVIEW-7 should-fix 2: no test separates a whole-span recompute from one chaining through stored values (decisions 54, 58). — taken by U1

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`. — b06c4b2
- [x] U1 REVIEW-7's should-fix items (decisions 47, 54, 58; I-11; DESIGN §9.4, §18.1). — 060b5e2
- [x] U2 The statistics of §11 and the `clean` flag (decisions 30, 59, 60, 61; DESIGN §8, §9.3, §11.1-§11.4; I-3). — abba5d3
- [x] U3 The ledgers and the lifecycle (decisions 22, 48, 62, 63; DESIGN §9.1, §10.2, §10.3, §16.2; I-5, I-6). — 327c68a
- [x] U4 The controls (decisions 23, 25, 49, 54, 64; DESIGN §7, §9.2, §9.4, §10.1; I-1, I-5, I-6, I-12). — 451471e
- [ ] U5 Final report (`meta/FINAL-REPORT-8.md`), with `./scripts/gate M0` at the pushed tip.
