# PLAN — mission 12 (roadmap step S2.1)

Base commit: c2612a6 (`plan: mission 12 kit (S2.1, static check, sandbox, validation, grid)`).
Brief: `meta/BUILDER-12-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-14-m12.md` (items 91-99 new); `meta/decisions/decisions-2026-10-14-m11.md` (83-90; 84, 86, 89 met here); `meta/decisions/decisions-2026-10-14.md` (76-82; 81 met here); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 21-25, 30, 36, 37, 39, 40, 44, 47, 48, 62, 63 met here); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-16, O-17, O-18 this mission; O-1 to O-4 and O-11 to O-13 still bind).
Roadmap step: S2.1 (as decisions 91-99 cut it). This mission closes no milestone; it runs gate M1 item by item and gate M0 again as a regression check at its pushed tip, as decision 91 says (U7). No file under `tests/gates/` changes. The container backend, its image, the probe, the hostile suite and approach execution behind the sandbox in the day loop are step S2.2's; the grid and W figures on a trial row and the retry with the error text are step S3.2's (decision 99).

Carried items:
- REVIEW-11 should-fix 1: `cli._backtest_result` registered, the audit widened (decision 92). — taken by U1
- REVIEW-11 note 7: the list subscript and `replay._adjusted` (decision 92). — taken by U1
- Finding D-010: `ledger.append` requires the figures on new rows (decision 93). — taken by U1
- Finding D-006: a fresh load of the text per instrument (decision 44; decision 95). — taken by U3
- Owner decision O-17: the grid on W fixes its combination on the exposure-adjusted net Sharpe at 1x, both measures recorded (decision 97). — taken by U5

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, D-010 and D-006 status lines in `meta/findings/FINDINGS.md`. — d250987
- [x] U1 The widened audit, REVIEW-11 should-fix 1 and finding D-010 (decisions 92, 93; decisions 62, 87, 89; O-13, O-18). — 52d7fec (2 entries added: cli._backtest_result display, replay._adjusted producer; 17 test_lifecycle seeds carry null figures under decision 93)
- [x] U2 The static check (decision 94; DESIGN §12.1; R-24; I-10). — 92703c9 (365 tests; from-import-star refused under the "further trick" clause)
- [x] U3 The sandbox interface, the job, the runner and the in-process backend (decision 95; decisions 22, 23, 24, 36, 37, 44; DESIGN §12.4, §6.2, §5.6; I-2, I-7; D-006). — fa4b53b (check ~506 s, +13 s)
- [ ] U4 The subprocess backend and `config/run.toml` (decision 96; DESIGN §12.4, §3; I-7, I-11, I-13; decision 47).
- [ ] U5 The dry run and the grid on W, on the exposure-adjusted measure (O-17, O-4, O-18; decisions 97, 81, 86 (a), 89, 23, 25, 30; DESIGN §12.2 stage 2, §4.1, §8; R-23).
- [ ] U6 Determinism, activity, the correlation gate and the sequence (decision 98; decisions 25, 63, 95 (e); DESIGN §12.2 stages 1, 3, 4, 5, §12.3; R-1).
- [ ] U7 Gate M1 and gate M0 as a regression check, and the final report (decision 91; O-2, O-3).
