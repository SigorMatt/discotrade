# PLAN — mission 17 (roadmap step S3.2b)

Base commit: af85e55 (`plan: mission 17 kit (S3.2b, workers in the day, scoring on T, gate M3)`).
Brief: `meta/BUILDER-17-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-16-m17.md` (items 132-140 new); `meta/decisions/decisions-2026-10-16-m16.md` (127-131; 128 the worker key, 131 (b), (c)); `meta/decisions/decisions-2026-10-16-m15.md` (118-126); `meta/decisions/decisions-2026-10-15-m14.md` (109-117); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19, O-20, O-22 bind); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-11, O-13, O-16 to O-18 bind); `meta/decisions/decisions-2026-10-14-m13.md` (100-108); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind).
Roadmap step: S3.2b.

This mission closes milestone M3.

Gate runs (decision 132 (b)), at the pushed tip, each its own foreground call with a 20-minute timeout, output verbatim with wall time: `discotrade sandbox build`; `./scripts/gate M3`; then, as a regression check, `./scripts/gate M2`; `./scripts/gate M1 G1.1`, `G1.2`, `G1.3`, `G1.4`, item by item, each its own call (O-2); `./scripts/gate M0`.

Not built here: the `ClaudeCodeCoordinator`, its token budget, digest and issue sinks, staging of step 1, retry of a failed day, catch-up and the state push (S4.2); alert rules and the dashboard (S4.1); a Claude worker model (the owner's, decision 123 (d)).

Carried items:
- REVIEW-16 should-fix 1: the test history of 6e3caa5's body, in FINAL-REPORT-17's `## Corrections` (decision 133). — taken by U6
- REVIEW-16 note 9: its three additions carried in NOT PROVEN (decision 134 (d)). — taken by U6
- REVIEW-16 note 10: HF-010 line (decision 134 (f)). — taken by U0
- REVIEW-16 note 11: HF-011 line (decision 134 (f)). — taken by U0
- REVIEW-16 note 12: HF-012 line (decision 134 (f)). — taken by U0
- Finding D-016: status line, answered (decision 134 (e)). — taken by U0
- REVIEW-15 note 2: the weak flag reads the states in force on `D` (decision 136 (g), 131 (b)). — taken by U2
- REVIEW-15 note 4: a duplicate on attempt 1 through the day, attempt 2's whole message list (decision 136 (h), 131 (c)). — taken by U2

- [ ] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (D-016 status; HF-010, HF-011, HF-012 lines; decision 134 (e), (f)).
- [ ] U1 Scoring a generated candidate on T (decision 135; O-4, O-11, O-13, O-17, O-18; DESIGN §7.1, §8, §10.2, §10.3, §11.3, §12.4, §16.1 step 5).
- [ ] U2 Daily steps 3 to 5 in `run_day` (decision 136; 124, 125, 126, 131 (b), (c); DESIGN §13.6, §13.7, §14.1, §14.3, §15.2, §16.1, §16.2).
- [ ] U3 The options of `run-day` and `replay`, and the scripted cursor (decision 137; 122 (b), (c); DESIGN §13.5, §14.2, §16.4).
- [ ] U4 The worker corpus (decision 138; 122 (b); DESIGN §13.4, §17.1, §18.3 G3.1; HF-009).
- [ ] U5 The gate tests of M3 and the gate runs (decisions 132 (b), 139; 9, 40, 72; O-2, O-19; DESIGN §18.2, §18.3 M3). `gate:` commit.
- [ ] U6 The final report (decisions 132 to 140; DESIGN §18.2).
