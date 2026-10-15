# PLAN — mission 13 (roadmap step S2.2)

Base commit: 9db93b8 (`plan: mission 13 kit (S2.2, container sandbox, hostile suite, gate M2)`).
Brief: `meta/BUILDER-13-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-14-m13.md` (items 100-108 new); `meta/decisions/decisions-2026-10-14-m12.md` (91-99; 94-98 hardened and built on here); `meta/decisions/decisions-2026-10-14-m11.md` (83-90); `meta/decisions/decisions-2026-10-14.md` (76-82; 80 is the speed method); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 15, 19, 21-23, 44, 47, 48, 49, 63, 72 met here; 48 replaced by 105 for the day loop); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-1 to O-4, O-11 to O-13, O-16 to O-18 still bind); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19, O-20, O-22; wins over 104, 105 (e), 106 (b) and DESIGN §12.5, §18.3 G2.1).
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
- [x] U4 The rejection suite and its rejection pass (decision 104 as O-22 narrows it; decisions 94, 98, 101, 102; DESIGN §12.5, §12.1, §12.2, §12.4; I-7, I-14). — unblocked under O-22 (decisions-2026-10-15-owner.md): the rejection suite under tests/fixtures/rejected/, no containment pass; G2.3 extended and G2.5 added. (Earlier: two attempts at the hostile suite stopped by a safety classifier before writing any file; HF-009.) — ad1b588 (29 fixtures, 24 texts + 4 by path to strategies/, all rejected at manifest stage on container; no miss, no static rule added; process.py excludes rejected/; check 3/3 1051-1204 s, above 15 min per D-012)
- [x] U5 Approaches in the day loop behind the sandbox (decision 105; decisions 23, 44, 48, 49, 63, 72, 80; DESIGN §12.4, §16.1 step 2, §16.4, §9.4; I-6, I-7, I-12). — bb27c90 (finished under §R from a stopped session's WIP; fork server built, one per day; 1.561 → 2.204 s per replay day, G1.3 projected ~812 s; journal byte-identical on G1.3's first 30 days except two retire reasons in lifecycle.jsonl, which 105 (c) changes; findings D-011 (G1.3 hardcodes the old reason) and D-012 (G1.3 above 10 min; check 970-1422 s under load); check 3/3)
- [x] U5b The fork server per harness process (O-20; decision 105 (e), 80 (d)): started on the first job, lives for the whole replay, run-day, journal recompute or test process, restarted after it dies; tests for a second replay day starting no new server and a fresh server after a dead one; seconds per replay day at parent and commit. — 8b9f9be (one server per process, atexit + close, restart with sandbox_restarted notice; 30-day journal byte-identical; 2.466 → 1.885 s per replay day, G1.3 projected ~621-694 s; check 3/3 858-881 s)
- [x] U5c The probe's limit findings and gate item G2.5 (O-22 items 3 and 4): container.py's probe source and judge, sandbox selftest, doctor --live sandbox; the G2.5 trusted bounded fixtures and their container tests; scripts/gate counting five items for M2. — 8b923fd (probe limits pids 64, memory 2 GiB swap 0, cpu 100000/100000, RLIMIT_CPU; selftest 19 PASS; image discotrade-sandbox:1edd0f8558cb; G2.5 tests in tests/test_sandbox_limits.py; output-cap overrun fixed; scripts/gate M2 five items; D-013 filed (check 910 s); check 3/3 877-910 s)
- [x] U6 The gate tests of M2 and the gate runs (decisions 106, 100 (b); decisions 9, 40, 72; O-2, O-3, O-19, O-22; DESIGN §18.2, §18.3 M2). First its own commit changing G1.3's two expected reasons (O-19); then G2.1 to G2.5 and the gate runs of 106 (f). — 42cea0f (O-19 G1.3 reasons), 68bee5f (G2.1-G2.5 gate files + test_gate_script.py M2→M3); gates at 68bee5f: M2 PASS 157 s; M1 G1.1 457 s, G1.2 200 s, G1.3 576 s, G1.4 1 s PASS; M0 PASS 266 s; image discotrade-sandbox:1edd0f8558cb
- [ ] U7 The final report (decision 100; DESIGN §18.2).
