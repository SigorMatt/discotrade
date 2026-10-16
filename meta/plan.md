# PLAN — mission 14 (roadmap step S3.1)

Base commit: 1267318 (`plan: mission 14 kit (S3.1, W profile, registry, prompt, parser)`).
Brief: `meta/BUILDER-14-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-15-m14.md` (items 109-117 new); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19, O-20, O-22 bind); `meta/decisions/decisions-2026-10-14-m13.md` (100-108; 101-105 hardened by U1); `meta/decisions/decisions-2026-10-14-m12.md` (91-99; 92 the return-reader audit, 94 the static check's tables); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-16 to O-18 bind every new module); `meta/decisions/decisions-2026-10-14-m11.md` (83-90); `meta/decisions/decisions-2026-10-14.md` (76-82; 80 the speed method); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind).
Roadmap step: S3.1 (DESIGN §13.1 to §13.4, as decisions 115 to 117 cut it).

This mission does not close a milestone.

It runs, at its pushed tip, `discotrade sandbox build`, then gate M2 in one foreground call and gate M1 item by item (G1.1 to G1.4, each its own call) as a regression check, as decision 109 (b) says (U6), each output verbatim with its wall time beside mission 13's (M2 157 s; G1.1 457 s, G1.2 200 s, G1.3 576 s, G1.4 1 s). Gate M0 is not run.

Not built here (decision 109 (a)): providers, the pool, the coordinator, the day's generation and its retry, storing responses, the call log, `config/models.toml`, the M3 gate tests (S3.2). Nothing of this mission is called from `run-day` or `replay`.

Carried items:
- REVIEW-13 should-fix 1: the probe's mount judged by content (last close) (decision 110). — taken by U1
- REVIEW-13 should-fix 2: the mount judged against the store, not the job (decision 110). — taken by U1
- REVIEW-13 should-fix 3: a zero remaining time at the fork server's read is `limit [wall_clock]` (decision 111 (a)). — taken by U1
- REVIEW-13 note 3: the runner's `float` conversion inside its catch-all (decision 111 (b)). — taken by U1
- REVIEW-13 note 4: the runner's built-in exception tuple equals `builtins`' exception classes (decision 111 (c)). — taken by U1
- REVIEW-13 note 5: a removal that raises still ends the runtime client (decision 111 (d)). — taken by U1
- REVIEW-13 should-fix 4: the `sandbox_restarted` notice only on a day that is written (I-6) (decision 112). — taken by U1
- REVIEW-13 should-fix 5: finding D-014 (G1.3 above 10 minutes) (decision 113 (a)). — taken by U0 (filed) and U6 (time appended)
- REVIEW-13 should-fix 6: finding D-015 (O-22 item 1 and 104 (d)); corrections to FINAL-REPORT-13 (decision 113 (b)). — taken by U0 (filed) and U6 (`## Corrections to FINAL-REPORT-13`)
- REVIEW-13 note 12: HF-010 stale worktrees (decision 113 (c)). — taken by U0
- REVIEW-13 note 15: HF-011 journal commit prefix (decision 113 (d)). — taken by U0
- Finding D-013: `./scripts/check` near 15 minutes (decision 114). — taken by U0 (status line) and U2

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (D-014, D-015, HF-010, HF-011, D-013 status line; decisions 113, 114). — 53401fd
- [x] U1 REVIEW-13's should-fix items 1 to 4 and notes 3 to 5: the mount judged against the store, the backends' edges, the restart notice (decisions 110, 111, 112; DESIGN §5.6, §12.4, §16.2, §19.3 L5; I-6, I-7, I-12). — ad53fad (image discotrade-sandbox:3b7d75c39621; G2.3 PASS unchanged; expected_from_store; check 3/3 890-912 s, times appended to D-013)
- [x] U2 `./scripts/check` under 12 minutes (decision 114; D-013; HF-006, HF-008; DESIGN §18.1). — a0ba5e8 (session-built shared states copied per module, trusted_hashes cache keyed by stat; parent 916 s, commit 841-891 s, 12-minute target missed, recorded under D-013; collect 2067 -> 2068, only the cache test added)
- [x] U3 The W profile, `p1` (decision 115; DESIGN §13.1, §4.1, §5.6, §6.2; I-1, I-3, I-9, I-12). — 1112052 (profile(state_dir, track, instruments, calendars, day, cell); 42 tests; 14,565 bytes for test_synth trend/short 2019-07-15; check 3/3 849-901 s, 901 s line under D-013)
- [x] U4 Anonymization and the registry (decision 116; DESIGN §13.2, §13.3, §10.3, §4.1, §4.3; I-8, I-10). — 7e4c098 (anonymize.labelling/anonymize/scale, registry.sanitize/registry; 17 tests; check 3/3 845-882 s)
- [ ] U5 The prompt builder and the response parser (decision 117; DESIGN §13.4, §6, §7.3, §12.1, §12.2, §13.2; I-8, I-10, I-13).
- [ ] U6 The gate runs (sandbox build, M2, M1 G1.1-G1.4) and the final report (decisions 109, 113; DESIGN §18.2).
