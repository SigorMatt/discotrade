# PLAN — mission 15 (roadmap step S3.2a)

Base commit: 301a5c7 (`plan: mission 15 kit (S3.2a, providers, pool, coordinator, generation)`).
Brief: `meta/BUILDER-15-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-16-m15.md` (items 118-126 new); `meta/decisions/decisions-2026-10-15-m14.md` (109-117; 115-117 the modules called, 117 (c) amended by 119 (a)); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19, O-20, O-22 bind); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-16 to O-18 bind every new module; O-11, O-13 read for S3.2b); `meta/decisions/decisions-2026-10-14-m13.md` (100-108; 104 (d)); `meta/decisions/decisions-2026-10-14-m12.md` (91-99; 92 the return-reader audit); `meta/decisions/decisions-2026-10-14-m11.md` (83-90); `meta/decisions/decisions-2026-10-14.md` (76-82; 80 the speed method); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 61-63 what this step writes).
Roadmap step: S3.2a (DESIGN §13.5 to §13.7, §14.1 to §14.3, as decisions 118 to 126 cut it).

This mission does not close a milestone.

It runs, at its pushed tip, `discotrade sandbox build`, then gate M0 in one foreground call, gate M2 in one foreground call and gate M1 item by item (G1.1 to G1.4, each its own call) as a regression check, as decision 118 (b) says (U7), each output verbatim with its wall time beside mission 14's (M2 135 s; G1.1 385 s, G1.2 174 s, G1.3 546 s, G1.4 1 s).

Not built here (decision 118 (a)): wiring the generation into `run-day` and `replay`, scoring on T, trial rows, the worker corpus, the M3 gate tests (S3.2b). Nothing of this mission is called from `run-day` or `replay`.

Carried items:
- REVIEW-14 should-fix 1: a fence line after the last block is no description (decision 119). — taken by U1
- REVIEW-14 note 3: a sanitized text ends in no whitespace (decision 119). — taken by U1
- REVIEW-14 note 4: the profile's roll-record refusal tested (decision 119). — taken by U1
- REVIEW-14 note 7: the conftest templates pass `GIT_ALLOW_PROTOCOL=file` (decision 119). — taken by U1
- REVIEW-14 note 11: HF-010 line, stale worktrees still registered (decision 120 (a)). — taken by U0
- REVIEW-14 note 12: HF-011 line, the `report:` prefix (decision 120 (b)). — taken by U0
- REVIEW-14 note 13: HF-012, concurrency of per-commit reviewers (decision 120 (c)). — taken by U0
- Finding D-013: the synthetic source's per-day cost (decision 121). — taken by U2

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (HF-010 and HF-011 lines, HF-012; decision 120).
- [ ] U1 REVIEW-14's should-fix 1 and notes 3, 4, 7 (decision 119; decisions 115, 116 (b), 117 (c); DESIGN §13.1, §13.3, §13.4).
- [ ] U2 The synthetic source's per-day cost (decision 121; D-013; DESIGN §5.5, §17.1, §18.1; I-6).
- [ ] U3 The providers and live check L3's offline behaviour (decision 122; DESIGN §13.5, §19.3 L3; I-11, I-13).
- [ ] U4 `config/models.toml` and the pool (decisions 123, 124; DESIGN §13.6, §4.3, §11.3, §15.2; R-14, R-21; I-5, I-10).
- [ ] U5 The coordinator interface and its scripted form (decision 125; DESIGN §14.1-§14.3, §16.1 step 3; I-8).
- [ ] U6 The day's generation (decision 126; DESIGN §13.4, §13.7, §10.2, §12.2, §12.3, §16.2; R-25; I-5, I-6, I-13).
- [ ] U7 The gate runs (sandbox build, M0, M2, M1 G1.1-G1.4) and the final report (decisions 118, 120, 121; DESIGN §18.2).
