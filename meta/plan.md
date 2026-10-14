# PLAN — mission 13 (roadmap step S2.2)

Base commit: 9db93b8 (`plan: mission 13 kit (S2.2, container sandbox, hostile suite, gate M2)`).
Brief: `meta/BUILDER-13-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-14-m13.md` (items 100-108 new); `meta/decisions/decisions-2026-10-14-m12.md` (91-99; 94-98 hardened and built on here); `meta/decisions/decisions-2026-10-14-m11.md` (83-90); `meta/decisions/decisions-2026-10-14.md` (76-82; 80 is the speed method); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 15, 19, 21-23, 44, 47, 48, 49, 63, 72 met here; 48 replaced by 105 for the day loop); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-1 to O-4, O-11 to O-13, O-16 to O-18 still bind).
Roadmap step: S2.2 (as decisions 100-107 cut it).

This mission closes milestone M2.

It also runs gate M1 item by item (G1.1 to G1.4, each its own call) and gate M0 again as a regression check at its pushed tip, as decision 100 (b) says (U6), each output verbatim with its time beside mission 12's (G1.1 386 s, G1.2 172 s, G1.3 575 s, G1.4 1 s, M0 257 s).

Container runtime found (decision 100 (a)): `docker version` — Server: Engine Version 29.1.3 (API 1.52, minimum 1.44), Go go1.24.4, Git commit 29.1.3-0ubuntu3~24.04.2, linux/amd64; containerd 2.2.1; runc 1.3.4-0ubuntu1~24.04.1.

Not built here (decision 107): calling the validation sequence from the day loop, the retry with the error text, workers, the call log (S3.2); gate G4.6 and the container smoke replay (S4.3); where trusted sources live in an installed package (S5.1).

Carried items:
- REVIEW-12 should-fix 1: no error text names a type a submission chose (decision 101 (a)). — taken by U1
- REVIEW-12 should-fix 2: the runner's result on a private descriptor; `no_result` (decision 101 (b)). — taken by U1
- REVIEW-12 should-fix 3: the static check's first offender in source order (decision 101 (d)). — taken by U1
- REVIEW-12 should-fix 4: determinism checks the bars the reverse job called (decision 101 (e)). — taken by U1
- REVIEW-12 note 2: error-text tests pass alone and in any order; compact dates matched (decision 101 (f)). — taken by U1
- REVIEW-12 note 3: `BaseException` while loading or calling (decision 101 (c)). — taken by U1
- REVIEW-12 note 5: correlation with an approach whose frozen source is not a repository file (decision 102 (g)). — taken by U2
- REVIEW-12 note 6: how `import discotrade.indicators` resolves in the image (decision 102 (e)). — taken by U2
- REVIEW-1 note on the `container` marker (decision 102 (g); `meta/BACKLOG.md`). — taken by U2
- Decision 48's in-process path in the day loop (decision 105). — taken by U5

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, the HF-008 status line in `meta/findings/FINDINGS.md` (decision 108).
- [x] U1 REVIEW-12's should-fix items: the runner's error texts and result channel, the static check's order, determinism's sample (decision 101; decisions 94, 95, 98; DESIGN §12.1, §12.2, §12.4, §13.2; I-1, I-8). — 6372322 (check 3/3 674-699 s; helper tests/error_texts.py; three test_zz_* replaced by per-test helper checks under 101 (f))
- [x] U2 The container backend, its image and `discotrade sandbox build` (decision 102; decisions 47, 95, 96, 97 (a), 98 (c); DESIGN §12.4, §3, §18.1; I-7, I-11, I-13, I-14; REVIEW-12 notes 5 and 6). — c702fc4 (tag discotrade-sandbox:20fa1f2225a3; python:3.14.6-slim by digest; numpy 2.5.4, pandas 3.0.6 = uv.lock; check 3/3 712-737 s, +~55 s from test_sandbox_container.py; SandboxUnavailable harness error in base.py; `run_program` not `execute` for I-15's test)
- [x] U3 The probe, `discotrade sandbox selftest` and `discotrade doctor --live sandbox` (decision 103; decisions 15, 19, 95 (a); DESIGN §12.4, §18.3 G2.3, §19.3 L5; I-11, I-12). — 0823a2d (tag discotrade-sandbox:edeee6d2120e; 15 PASS findings on test_synth W of 2019-07-15; job carries no timestamps, so "no bar after W" judged by count against the store and the harness's own last bar time; read-only root judged by EROFS since the non-root user gets EACCES without --read-only; check 3/3 697-738 s)
- [ ] **blocked** U4 The hostile suite, its rejection pass and its containment pass (decision 104; decisions 94, 98, 101, 102; DESIGN §12.5, §12.1, §12.2, §12.4; I-7, I-14). — blocked after two attempts: each sub-agent was stopped by a safety classifier while planning the attack fixtures, before writing any file; nothing committed. Leads it recorded: process.py trusts all of tests/fixtures/ via trusted_hashes (must leave hostile/ out, 104 (d)); the runner's private result descriptor (os.dup(1)) has a predictable number, possibly a finding under 104 (d). U6 depends on it (G2.1).
- [ ] U5 Approaches in the day loop behind the sandbox (decision 105; decisions 23, 44, 48, 49, 63, 72, 80; DESIGN §12.4, §16.1 step 2, §16.4, §9.4; I-6, I-7, I-12).
- [ ] U6 The gate tests of M2 and the gate runs (decisions 106, 100 (b); decisions 9, 40, 72; O-2, O-3; DESIGN §18.2, §18.3 M2).
- [ ] U7 The final report (decision 100; DESIGN §18.2).
