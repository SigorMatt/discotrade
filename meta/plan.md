# PLAN — mission 5 (roadmap step S0.4)

Base commit: 3854c96 (`plan: mission 5 kit (S0.4, independent calc, cheat, M0 gate tests)`).
Brief: `meta/BUILDER-5-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-12.md` (items 34-40 new; 1-33 still bind).
Roadmap step: S0.4. This mission closes milestone M0.

Carried items:
- REVIEW-4 should-fix 1: the `BarStore` classification test misses a public reader written as a property (decision 34). — taken by U1
- REVIEW-4 note on U3: `bars/gaps.py`, `rolls.py` (`update_rolls`, `adjusted_as_of`) look at the index before the reader, so an interrupted first append reads as "no bars" (decision 35). — taken by U1
- REVIEW-3 note carried to S0.4: reads before `trusted_from` (roll gap, `adjusted_as_of`, evaluation context, `sigma`) and a contract change across `trusted_from` (decision 36). — taken by U2
- REVIEW-3 note carried to S0.4: a roll record with the right `ts` and the wrong contracts (decision 37). — taken by U2
- REVIEW-3 note carried to S0.4: the unlabelled cost lines of the `backtest` plain output (decision 38). — taken by U2

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`. — 9d2d781
- [x] U1 The store's readers, and callers that look at the index first (REVIEW-4 should-fix 1 and note on U3; decisions 5, 18, 31, 34, 35; DESIGN §5.2, §5.4, §5.6; I-5, I-6). — 8e8215c
- [x] U2 Rolls and `backtest`: `trusted_from`, roll records, cost labels (REVIEW-3 notes; decisions 23, 24, 27, 36, 37, 38; DESIGN §4.2, §5.6, §7.1, §7.3; I-4). — 8d27fe1
- [x] U3 The independent calculation (DESIGN §18.3 G0.1, §5.6, §6.2, §7, §8, §5.3; decisions 22-26, 29, 30, 36, 37, 39). Own sub-agent, forbidden-files words verbatim. — 3be4e9b
- [ ] U4 Gate G0.1: reference strategies against the independent calculation (decisions 23-27, 39).
- [ ] U5 Gate G0.2: the cheating strategy (DESIGN §18.3 G0.2, §6.2, §7.1, §12.1; I-2; decision 40).
- [ ] U6 Gates G0.3 and G0.4, and the gate run (`./scripts/gate M0` prints `gate M0: PASS`).
- [ ] U7 Final report (`meta/FINAL-REPORT-5.md`).
