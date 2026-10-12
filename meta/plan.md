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
- [x] U4 Gate G0.1: reference strategies against the independent calculation (decisions 23-27, 39). — calc fix de9fc09 (D-004), 2881ee0
- [x] U5 Gate G0.2: the cheating strategy (DESIGN §18.3 G0.2, §6.2, §7.1, §12.1; I-2; decision 40). — 2c64e8d
- [ ] U6 Gates G0.3 and G0.4, and the gate run (`./scripts/gate M0` prints `gate M0: PASS`). — tests 80ffc78; G0.2-G0.4 PASS; final gate run waits on U4 (D-004)
- [ ] U7 Final report (`meta/FINAL-REPORT-5.md`).

## Decision on D-004

Decision on finding D-004 (phone architect, 2026-10-12), to be carried as item 41 of the decisions file in the next kit: in DESIGN §8, max_drawdown is the largest fall of the running sum of d from its running peak, where the running sum starts at 0 before the first day and that starting 0 counts as a peak; it is 0 when there is no fall. Reason: every subject starts flat, so a loss on the first day is a drawdown. src/discotrade/metrics.py already does this and does not change. tests/gates/independent_calc.py changes to match: give that one fix to a fresh sub-agent under U3's rules (forbidden-files words verbatim; it works from this paragraph and DESIGN §8 only and does not open metrics.py), with a hand-value check in the independent calculation's own self-test for a series whose first day is a loss and whose running sum never recovers above 0, as its own commit. Then land U4 from the stash, with G0.1 passing for all three reference strategies including max_drawdown in the module and in backtest --json, then U6's gate run at the tip, then U7. Before the fix, copy this paragraph verbatim into meta/plan.md under a heading "Decision on D-004", and append to meta/findings/FINDINGS.md: "D-004 status (appended 2026-10-12, mission 5 U4): Status: answered by the phone architect, recorded in meta/plan.md, to be carried as decision 41." Change nothing else on this account; D-005 and D-006 stay open for the architect. Then continue the mission from the checkpoint.
