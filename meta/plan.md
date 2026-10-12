# PLAN — mission 6 (roadmap step S0.4, repaired)

Base commit: 19196da (`plan: mission 6 kit (S0.4, REVIEW-5 blocker, roll timing, M0 gate again)`).
Brief: `meta/BUILDER-6-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-12.md` (items 41-46 new; 1-40 still bind).
Roadmap step: S0.4. This mission closes milestone M0.

Carried items:
- REVIEW-5 blocker 1: G0.1's `backtest --json` test does not compare every field the object carries (decision 42). — taken by U1
- REVIEW-5 should-fix 1 with finding D-005: the timing of the roll cost (`h(u-1)`) is not visible to the independent calculation's self-test, the product's unit tests or G0.1 (decision 43). — taken by U2 (self-test) and U3 (unit tests, probe in G0.1)
- REVIEW-5 note on D-004: `max_drawdown` counts the starting 0 as a peak (decision 41). — recorded answered by U0
- REVIEW-5 note on the timeout of `tests/test_gate_script.py` under load (decision 45). — taken by U4

- [ ] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, D-004..D-006 status lines in `meta/findings/FINDINGS.md`.
- [ ] U1 G0.1: every field of `backtest --json` (REVIEW-5 blocker 1; decisions 27, 39, 42; DESIGN §3, §8, §18.2, §18.3 G0.1).
- [ ] U2 The independent calculation's self-test: a position that changes at the roll (REVIEW-5 should-fix 1; D-005; decisions 24, 25, 39, 43 (a); DESIGN §5.6, §7.3). Own sub-agent, forbidden-files words verbatim.
- [ ] U3 The roll timing in product unit tests and in G0.1 (D-005; decisions 21, 24, 25, 39, 43 (b), (c); DESIGN §5.6, §7.3, §8, §18.3 G0.1).
- [ ] U4 `tests/test_gate_script.py` under load (REVIEW-5 note; decision 45; DESIGN §18.2).
- [ ] U5 The gate run (`./scripts/gate M0` prints `gate M0: PASS` at the pushed tip).
- [ ] U6 Final report (`meta/FINAL-REPORT-6.md`).
