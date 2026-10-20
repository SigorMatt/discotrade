# PLAN — mission 22 (roadmap step S4.2b)

Base commit: 72400d7 (`plan: mission 22 kit (S4.2b, the full daily run, digest and issue sinks)`).
Brief: `meta/BUILDER-22-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-19-m22.md` (items 177-188 new); owner `meta/decisions/2026-10-18-owner.md` (O-26, O-27); `meta/decisions/decisions-2026-10-19-m21.md` (168-176; 168, 170, 171, 176); `meta/decisions/decisions-2026-10-18-m20.md` (155-167; 155, 156, 157 (c), 160, 163, 165, 166); owner `meta/decisions/2026-10-17-owner.md` (O-25); `meta/decisions/decisions-2026-10-17-m19.md` (146-154; 146 (b), (c), 152 (e), (f)); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-18); `meta/decisions/decisions-2026-10-17-m18.md` (145); `meta/decisions/decisions-2026-10-16-m17.md` (136, 137); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 47, 50, 51, 52, 54, 72).
Roadmap step: S4.2b. The rest of the daily run: the digest and the issue sinks, step 1 staged, the retry, `run_failed`, the catch-up, the push, the weekly recomputation, the `no_finding` call, the live defaults of `run-day`.

This mission closes no milestone. It moves no gate of M4; the M4 gate tests are step S4.3's.

Regression gates (decision 177 (a); O-25), taken by U6: at the pushed tip after U5, with nothing uncommitted but the git-ignored drafts, each its own foreground call with a 20-minute timeout: `discotrade sandbox build`; gate M1 item by item (`./scripts/gate M1 G1.1`, `G1.2`, `G1.3`, `G1.4`); then `./scripts/gate M3`, `./scripts/gate M2`, `./scripts/gate M0`; then decision 170's three measurements (median ratio at most 1.25). Each must pass unchanged. Under O-27 item 3, an M1 item above 15 minutes of wall time stops the mission (finding, then `VERDICT: question`). Each of U2 to U5 gives `./scripts/gate M1 G1.3` and decision 170's three measurements at its commit (decision 177 (c)). No file under `tests/gates/` changes in this mission (decision 177 (b)).

Carried items:
- REVIEW-17 note 3's second half and note 4, REVIEW-19 notes 4 and 6 (decision 182 (d), (e)). — taken by U4
- REVIEW-17 note 5 (decision 186 (c)). — taken by U5
- REVIEW-7's note on `revised_data` and `_indexed_last_ts`, REVIEW-2's note on `update_rolls` (decision 181). — taken by U3
- The live defaults of `run-day` (decision 137 (a); decision 186). — taken by U5
- The `no_finding` call (decision 152 (e); decision 185). — taken by U5
- The digest and the issues for the alerts mission 19 fires (decision 152 (f); decisions 178 to 180). — taken by U1 and U2
- REVIEW-21 notes 1, 10 and 11 (decision 187 (b)): D-013 times, HF-010, HF-012 lines. — taken by U0
- REVIEW-21 note 2 (decision 188 (a)): the correction of FINAL-REPORT-21's pytest order. — taken by U7

Left items:
- findings D-019, D-020 and D-021 — the owner (`meta/BACKLOG.md`; decision 187 (b));
- the M4 gate tests, G4.4 and G4.5 among them, the planted-edge market and its corpus, and the failure injection of G4.3 — step S4.3;
- REVIEW-10's note on a death between the moves of a day — step S5.1's doctor (`meta/BACKLOG.md`; decision 187 (b)).

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (D-013 times, HF-010, HF-012 lines; decision 187 (b)).
- [x] U1 (41accb7) The digest module and the issue sinks (decision 178; decision 179 (a), (b) as functions; DESIGN 15.4, 19.3 L6; I-8, I-11, I-13). `digest:` commit.
- [x] U2 (b614465) The digest, the run log and step 8 in the day (decisions 179, 180; DESIGN 15.4, 16.1 steps 7 and 8, 16.2, 14.3). `daily:` commit. G1.3 and decision 170's three measurements at the commit.
- [x] U3 (2ae5c04) Step 1 staged (decision 181; DESIGN 16.2, 5.2, 5.4, 5.6). `daily:` commit. G1.3 and the three measurements.
- [x] U4 (7859488, 91d1497) The retry, `run_failed` and the catch-up (decisions 182, 183; DESIGN 16.1, 16.2, 15.2; SPEC §11). `daily:` commit. G1.3 and the three measurements.
- [ ] U5 The weekly recomputation, the `no_finding` call and the live defaults of `run-day` (decisions 184, 185, 186; DESIGN 9.4, 15.2, 16.1 step 6). `daily:` commit. G1.3 and the three measurements.
- [ ] U6 The regression gates at the pushed tip (O-2, O-25, O-27; decisions 177 (a), 170; DESIGN §18.2). `meta:` commit (one D-013 times line).
- [ ] U7 The final report (decisions 177-188; O-26, O-27; DESIGN §18.2). `meta/FINAL-REPORT-22.md`.
