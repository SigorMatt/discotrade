# PLAN — mission 20 (roadmap step S4.2a)

Base commit: f1b8346 (`plan: mission 20 kit (S4.2a, speed under O-26 and O-27, coordinator)`).
Brief: `meta/BUILDER-20-PROMPT.md`. Decisions: owner `meta/decisions/2026-10-18-owner.md` (O-26, O-27); `meta/decisions/decisions-2026-10-18-m20.md` (items 155-167 new); owner `meta/decisions/2026-10-17-owner.md` (O-25); `meta/decisions/decisions-2026-10-17-m19.md` (146-154; 146 (b), (c), 152, 153); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-18); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19); `meta/decisions/decisions-2026-10-17-m18.md` (145); `meta/decisions/decisions-2026-10-16-m17.md` (136, 137, 140); `meta/decisions/decisions-2026-10-16-m15.md` (121, 122, 125); `meta/decisions/decisions-2026-10-16-m16.md` (131 (d)); `meta/decisions/decisions-2026-10-14.md` (80); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 72).
Roadmap step: S4.2a.

This mission closes no milestone. It moves no gate of M4.

Order (O-26 item 1): after U0, the speed units U1 to U3 come first, before any other unit. They change only how the day loop arrives at its figures, never what any day computes or writes.

Regression gates (decision 155 (a); O-25), taken by U6: at the pushed tip after U5, with nothing uncommitted but the git-ignored drafts, each its own foreground call with a 20-minute timeout: `discotrade sandbox build`; gate M1 item by item (`./scripts/gate M1 G1.1`, `G1.2`, `G1.3`, `G1.4`); then `./scripts/gate M3`, `./scripts/gate M2`, `./scripts/gate M0`. Each must pass unchanged. Under O-27 item 3, an M1 item above 15 minutes of wall time stops the mission (finding, then `VERDICT: question`). No file under `tests/gates/` changes in this mission.

Carried items:
- O-26: items 4 (`./scripts/speed`) and 5 (the equality test) by U1; the table (U1), step 6 (U2), step 7 and whatever else grows (U3); the ratio at most 1.25 binds U3. — taken by U1, U2, U3
- O-27: G1.3's time and the four figures at every code unit's commit (U1 to U5); the 15-minute stop (U1 to U6); item 4, D-014's status line (U0). — taken by U0 to U6
- REVIEW-19 should-fix 1, finding D-018: the `rank_persistence` entry's `p`, the dashboard recomputes no figure (decision 160). — taken by U4
- REVIEW-19 should-fix 2: the health panel's failure counts over `pool.fail_window` (decision 161). — taken by U4
- REVIEW-19 should-fix 3: no speed figure at mission 18's tip, under NOT PROVEN (decision 162). — taken by U7
- REVIEW-15 note 3's second half: the child's process group killed on timeout (decision 166). — taken by U5
- REVIEW-19 notes 11 to 15: HF-006, HF-012, HF-010, HF-013 lines and the new HF-015 (decision 167 (b)). — taken by U0

Left items:
- the digest, the issue sinks, the full daily run, the `no_finding` call, the live defaults of `run-day`, REVIEW-17 notes 3 to 5 and REVIEW-19 notes 4 and 6 — step S4.2b (decision 155, 167 (a));
- G4.4 and G4.5 as gate tests — step S4.3.

- [x] U0 Plan (`plan:` commit) — 4ed47b4: this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (D-014 status; D-018 and its status; HF-006, HF-012, HF-010, HF-013 lines; HF-015 new; decision 167 (b)).
- [x] U1 The measurement (`./scripts/speed`), the equality test, the clearing function, and the table without growth (O-26 items 2 to 5; decisions 156, 157, 158; DESIGN §10.4, §16.4). `table:` commit. G1.3 and the four figures at parent and commit. — 431a82e (G1.3 PASS 898 s; ratio parent 1.577, commit 1.600; table.build 0.89->1.58 s became 0.20->0.31 s; finding D-019 (table not fully incremental); check 3/3 1168, 1196, 1317 s; 157 (d) 267 trees equal, 157 (e) diff empty)
- [x] U2 Step 6 without growth (O-26 item 2; decisions 157, 158; DESIGN §15.1-§15.3, §16.1 step 6). `alerts:` commit. G1.3 and the four figures. — becb570 (G1.3 PASS 582 s; ratio parent 1.805, commit 1.260; D-020 filed; check 3/3 1045, 1016, 1001 s; 157 (d) 267 trees equal, 157 (e) diff empty)
- [x] U3 Step 7 and the rest without growth; the ratio at most 1.25 (O-26 items 2, 4; decisions 157, 158; DESIGN §15.5, §16.1). `dashboard:` commit (or the area that took most). G1.3 and the four figures. — e8d31bb (`bars:`; G1.3 PASS 625 s; ratio commit 1.234/1.246 at low load, above 1.25 under load >=2.6; D-021 filed; check 3/3 1459, 1356, 1198 s; 157 (d)/(e) equal)
- [ ] U4 REVIEW-19 should-fix 1 and 2 (decisions 160, 161; D-018; DESIGN §15.3, §15.5). `alerts:` commit. G1.3 and the four figures.
- [ ] U5 The Claude Code coordinator, its budget, the process group, `config/protected_paths.toml` and the deny rules (decisions 163-166; DESIGN §14.1-§14.4, §16.3, §19.3 L4; SPEC §17). `coordinator:` commit. G1.3 and the four figures.
- [ ] U6 The regression gates at the pushed tip (O-2, O-25, O-27; decision 155 (a); DESIGN §18.2). `meta:` commit (one D-013 times line).
- [ ] U7 The final report (decisions 155-167; O-26, O-27; DESIGN §18.2). `meta/FINAL-REPORT-20.md`.
