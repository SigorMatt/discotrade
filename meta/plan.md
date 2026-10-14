# PLAN — mission 11 (roadmap step S2.0b)

Base commit: c3a3f1d (`plan: mission 11 kit (S2.0b, adjusted lifecycle, reader register, G1.3)`).
Brief: `meta/BUILDER-11-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-14-m11.md` (items 83-90 new); `meta/decisions/decisions-2026-10-14.md` (76-82; 78, 80, 81 met here); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-11 to O-13, O-15, O-16, O-18 this mission; O-1 to O-4 still bind).
Roadmap step: S2.0b (as decisions 83-90 cut it). This mission closes no milestone; it runs gate M1 again item by item and gate M0 at its pushed tip, as decision 90 says (U6). The only file under `tests/gates/` that may change is `tests/gates/test_g1_3_lifecycle.py`, in U6 only (decisions 83, 90 (a)).

Carried items:
- REVIEW-10 note 3: the derived exposure records stored, `journal._empty` replaced by a public name, staged callers pass `overlay` (decision 84). — taken by U1
- REVIEW-9 note on decision 68 (b): a test with the day's admission doing the displacing (decision 86 (f)). — taken by U3
- Owner decision O-11: dormancy, return, displacement and admission on the exposure-adjusted Sharpe (decisions 85, 86). — taken by U2 and U3
- Owner decision O-12: each subject scored with its own average positions over the window compared (decisions 85, 86 (c)). — taken by U2 and U3
- Owner decision O-13: both measures recorded; trial, lifecycle and table fields (decisions 86 (d), 87, 88). — taken by U2, U3 and U4
- Owner decisions O-16 and O-18: the register of return readers and its audit test (decision 89). — taken by U5
- Owner decision O-15: G1.3 on the adjusted measure (decision 90 (a)). — taken by U6
- REVIEW-10 note 7: concurrent reviewers near the 20-minute cap, recorded as HF-008 (decision 90 (d)). — taken by U0

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, HF-008 in `meta/findings/FINDINGS.md`. — 7629de6
- [x] U1 The derived exposure records (decision 84; decisions 78, 81; O-4; DESIGN §9.2, §9.3, §16.1, §16.2; REVIEW-10 note 3). — 93c2f91 (G1.3 first 30 days 1.341 -> 1.469 s/day; adjusted call 0.347 -> 0.012 s)
- [ ] U2 Dormancy, return and displacement on the adjusted measure (O-11, O-12; decisions 85, 87; decisions 62, 63, 68; DESIGN §10.3).
- [ ] U3 Admission on the adjusted measure and the candidates file (O-11 to O-13; decisions 86, 87; decisions 48, 63, 68, 73, 79 (b); DESIGN §10.3, §4.1).
- [ ] U4 The table's adjusted figures (O-13; decision 88; decisions 30, 39, 41, 60, 71; DESIGN §10.4, §8).
- [ ] U5 The register of return readers and its audit (O-16, O-18; decision 89).
- [ ] U6 G1.3 on the adjusted measure, gate M1 item by item, and gate M0 (O-15, O-2, O-3; decisions 74, 90; DESIGN §18.2, §18.3 (M1)).
- [ ] U7 Final report (`meta/FINAL-REPORT-11.md`).
