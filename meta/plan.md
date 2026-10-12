# PLAN — mission 3 (roadmap step S0.3)

Base commit: ef2e9f1 (`plan: mission 3 kit (S0.3, strategy loop, costs, metrics, backtest)`).
Brief: `meta/BUILDER-3-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-12.md` (items 18-29 new; 1-17 still bind).
Roadmap step: S0.3 (milestone M0, not closed by this mission; S0.4 / mission 4 closes it, decision 28).

Carried items (taken by U1):
- REVIEW-2 should-fix 1: the reader does not refuse a month file the index does not list (decision 18).
- REVIEW-2 should-fix 2: `bars fetch` defaults its gap-check day to UTC `--as-of` minus one, not §16.1's `D` (decision 19).
- REVIEW-2 note on U5: no socket backstop in `tests/conftest.py` (decision 20).

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`. — 02b366c
- [x] U1 Reader, `bars fetch` default day and socket backstop (REVIEW-2 should-fix 1, 2, note on U5; decisions 3, 5, 18-20; DESIGN §5.2, §5.4, §16.1). — a966344
- [x] U2 Strategy contract, loader and indicator library (DESIGN §6.1, §6.2 result check, §6.3; decisions 21, 22). — 542c171
- [x] U3 Evaluation loop and returns (DESIGN §6.2, §7.1, §7.2, §5.6; decisions 22-24; R-20). — 833aa25, ec1c8a4
- [x] U4 Cost model and executor (DESIGN §7.3, §7.4, §5.7; decisions 24-26; R-3, R-5). — 3c24e5f
- [x] U5 Metrics (DESIGN §8; decisions 23, 25; R-7). — 8cfd390
- [x] U6 Reference strategies and the `backtest` command (DESIGN §3, §6.1, §18.3 G0.1; decisions 21, 27). — efb2b93
- [ ] U7 Final report (`meta/FINAL-REPORT-3.md`).
