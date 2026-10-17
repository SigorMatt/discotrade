# PLAN — mission 19 (roadmap step S4.1)

Base commit: 031f5e4 (`plan: mission 19 kit (S4.1, alerts and dashboard under O-23 to O-25)`).
Brief: `meta/BUILDER-19-PROMPT.md`. Decisions: owner `meta/decisions/2026-10-17-owner.md` (O-23 to O-25); `meta/decisions/decisions-2026-10-17-m19.md` (items 146-154 new); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-4 to O-8, O-13, O-14, O-16, O-18); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19); `meta/decisions/decisions-2026-10-17-m18.md` (141-145; 145); `meta/decisions/decisions-2026-10-14-m11.md` (83-90; 89); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 59, 60, 62, 69-72).
Roadmap step: S4.1.

This mission closes no milestone. It moves no gate of M4.

Regression gates (decision 146 (a), 154 (d); O-25), at the pushed tip after U5, with nothing uncommitted but the git-ignored drafts, each its own foreground call with a 20-minute timeout, taken by U6: `discotrade sandbox build`; gate M1 item by item (`./scripts/gate M1 G1.1`, `G1.2`, `G1.3`, `G1.4`); then `./scripts/gate M3`, `./scripts/gate M2`, `./scripts/gate M0`. Each must pass unchanged. The only change under `tests/gates/` is decision 148 (d)'s one line in `tests/gates/test_g1_3_lifecycle.py` (U1).

Carried items:
- O-23: the table keeps `S`, `E_N`, `excess` and gains `adjusted_S`, `adjusted_E_N`, `adjusted_excess`; G1.3's one line. — taken by U1
- O-24: `control_moments` gains `column` and the register's pending entries settled (U1); the rank rows gain `timing` and `gross` (U2); the alert functions as registered call sites (U3, U4). — taken by U1, U2, U3, U4
- O-25: add, never replace; every met gate run again at the end. — taken by every unit, and U6
- REVIEW-11 note 8: `paper.portfolio` and `paper._series` stay `producer`; the one `stage3_money` entry is the dashboard's (decision 153 (c)). — taken by U5
- REVIEW-18 notes 7 to 10: HF-006, HF-012, HF-010 lines, HF-013 and HF-014 (decision 154 (b)). — taken by U0

Left items:
- the `no_finding` call by the day loop, the digest and the issues — step S4.2 (decision 152 (e), (f));
- G4.5 — step S4.3 (decision 153 (d)).

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (HF-006, HF-012, HF-010 lines; HF-013, HF-014; decision 154 (b)). — e0d19df
- [x] U1 `control_moments`'s column, the register, and the table's adjusted deflated figures (O-23, O-24; decisions 147, 148; DESIGN §10.4, §11.2). `table:` commit. G1.3 and G1.4 run at the commit. — 27a83b9 (147 (d) parameter added; three wrong changes red; check 3/3 1121, 1128, 1125 s; G1.3 PASS 855 s, G1.4 PASS 1 s)
- [x] U2 The timing statistic in the rank rows and the one-sided t-test (O-5, O-6, O-24; decisions 149, 150; DESIGN §11.1, §15.1, §16.1 step 6). `stats:` commit. G1.1 run at the commit. — a7854da (four wrong changes red; check 3/3 1153, 1072, 1185 s; G1.1 PASS 424 s; 2.554 -> 2.422 s per replay day)
- [x] U3 `persistent_approach` and `group_edge` on the exposure-adjusted series (O-7, O-16, O-24; decision 151; DESIGN §15.1, §11.2-§11.4). `alerts:` commit. — efc35de (five wrong changes red; check 3/3 1019, 1000, 997 s; resumed under §R)
- [ ] U4 Alert state, payloads, `rank_persistence` and `revival` rules, health alerts, the day loop's step 6 (decisions 152, 149 (c); DESIGN §15.1-§15.3, §16.1 step 6, §16.2). `alerts:` commit. G1.2 and G1.3 run at the commit.
- [ ] U5 The dashboard (O-6, O-14, O-16, O-18; decision 153; DESIGN §15.5, §3; SPEC §13, §14). `dashboard:` commit.
- [ ] U6 The regression gates at the pushed tip (O-2, O-25; decisions 146 (a), 154 (c), (d); DESIGN §18.2). `meta:` commit (D-013 and D-014 times lines).
- [ ] U7 The final report (decisions 146-154; O-23 to O-25; DESIGN §18.2). `meta/FINAL-REPORT-19.md`.
