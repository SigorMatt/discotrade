# PLAN — mission 18 (roadmap step S3.2b, continued)

Base commit: 63c6d57 (`plan: mission 18 kit (S3.2b closer, G3.3 bar and score reading, gate M3)`).
Brief: `meta/BUILDER-18-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-17-m18.md` (items 141-145 new); `meta/decisions/decisions-2026-10-16-m17.md` (132-140; 138 the corpus, 139 the M3 gate tests, 139 (c)'s raw-bar/score clause replaced by 142); `meta/decisions/decisions-2026-10-16-m15.md` (118-126; 122 (b)); `meta/decisions/decisions-2026-10-15-m14.md` (109-117; 116, 117, 119 (b)); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19); owner `meta/decisions/decisions-2026-10-13-owner.md`; `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 72).
Roadmap step: S3.2b, continued.

This mission closes milestone M3.

Gate runs (decision 141 (b)): at the pushed tip after U2, `discotrade sandbox build`, then `./scripts/gate M3`, each its own foreground call with a 20-minute timeout, output verbatim with wall time and sha. Gates M2, M1 and M0 are not run again because no file under `src/` changes (decision 141 (a), (b)).

Carried items:
- REVIEW-17 blocker 1 with finding D-017: G3.3's "no raw bar" and "no score" as decision 142 reads them. — taken by U1
- REVIEW-17 blocker 2 with note 3's first half: the manifest's served day, attempt and outcome proven by a gate test; FINAL-REPORT-18 `## Corrections` (decision 143). — taken by U2 and U4
- REVIEW-17 note 1: gate M3 at the pushed tip, nothing uncommitted (decision 141 (b)). — taken by U3
- REVIEW-17 notes 10 to 13: HF-010, HF-011, HF-006 and HF-012 lines; D-017 status line (decision 144 (f)). — taken by U0
- Left to step S4.2: REVIEW-17 note 3's second half and note 4 (decision 144 (a)), note 5 (decision 144 (b)).

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (D-017 status; HF-010, HF-011, HF-006, HF-012 lines; decision 144 (f)). — e6c33ae
- [x] U1 G3.3: no raw bar and no score, as decision 142 reads them (decision 142; 116, 117, 119 (b), 139 (c); D-017; REVIEW-17 blocker 1; DESIGN §13.1-§13.4, §18.2, §18.3 G3.3). `gate:` commit. — da7634b (3 tests, parts (a)-(c); G3.3 PASS 180.36 s; five wrong changes red; check 3/3 1022, 1030, 1034 s)
- [ ] U2 The corpus manifest's served day, attempt and outcome (decision 143 (a), (b), (d); 138 (e); REVIEW-17 blocker 2; DESIGN §18.3 G3.2). `gate:` commit.
- [ ] U3 Gate M3 at the pushed tip (decision 141 (b); DESIGN §18.2, §18.3 M3; REVIEW-17 note 1). `meta:` commit (D-013 times line).
- [ ] U4 The final report (decisions 141 to 145; DESIGN §18.2).
