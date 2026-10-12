# PLAN — mission 4 (roadmap step S0.3, repair mission)

Base commit: 9f00d99 (`plan: mission 4 kit (S0.3 repair, review-3 blocker and should-fix)`).
Brief: `meta/BUILDER-4-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-12.md` (items 30-33 new; 1-29 still bind, with item 33's renumbering).
Roadmap step: S0.3, repair mission. Closes no milestone; M0 is closed by step S0.4, mission 5 (decision 33).

Carried items (REVIEW-3):
- Blocker 1: `sharpe` / `sharpe_2x` finite for a constant daily series (decision 30). — taken by U1
- Should-fix 1: the `trades` test does not tell a right implementation from a wrong one. — taken by U1
- Should-fix 2: `backtest` exit 1 paths of decision 27 untested. — taken by U2
- Should-fix 3: `BarStore.last_ts` does not refuse as the other readers do (decision 31). — taken by U3
- Should-fix 4: indicator module text untrue of `ema` (decision 32). — taken by U4

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`. — 593c0ea
- [x] U1 Sharpe at zero deviation, and the `trades` test (REVIEW-3 blocker 1, should-fix 1; decisions 25, 30; DESIGN §8; R-7; I-4). — 836c2ab
- [x] U2 `backtest` exit 1 paths (REVIEW-3 should-fix 2; decisions 18, 21, 22, 24, 27; DESIGN §3, §6.2). — 6445223
- [x] U3 `BarStore.last_ts` refuses as a reader (REVIEW-3 should-fix 3; decisions 5, 18, 31; DESIGN §5.2; I-5, I-6). — 9c4023b
- [x] U4 Indicator module text (REVIEW-3 should-fix 4; decision 32; DESIGN §6.3, §13.4; I-2). — 300be21
- [x] U5 Final report (`meta/FINAL-REPORT-4.md`). — e740b3b
