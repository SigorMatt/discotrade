# PLAN — mission 16 (roadmap step S3.2a, repaired)

Base commit: 72c7836 (`plan: mission 16 kit (S3.2a repaired, REVIEW-15 blocker and should-fix)`).
Brief: `meta/BUILDER-16-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-16-m16.md` (items 127-131 new); `meta/decisions/decisions-2026-10-16-m15.md` (118-126; 121 the synthetic cache, 122 the providers and L3, 123 the models and run configuration); `meta/decisions/decisions-2026-10-15-m14.md` (109-117); owner `meta/decisions/decisions-2026-10-15-owner.md` (O-19, O-20, O-22 bind); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-16 to O-18 bind); `meta/decisions/decisions-2026-10-14-m13.md` (100-108); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind).
Roadmap step: S3.2a, repaired (REVIEW-15's blocker and should-fix items).

This mission does not close a milestone and runs no gate (decision 127 (a)).

Not built here: wiring the generation into `run-day` and `replay`, scoring on T, trial rows, the worker corpus, the M3 gate tests (S3.2b).

Carried items:
- REVIEW-15 blocker 1: one place reads the worker key, and the claim says so (decision 128). — taken by U1
- REVIEW-15 note 3, first half: no `ProviderError` keeps a cause or a context (decision 128 (e)). — taken by U1
- REVIEW-15 should-fix 1: `doctor --live workers` reads the loaded configuration (decision 129). — taken by U2
- REVIEW-15 should-fix 2: the cache key's calendar and bar-length parts held by tests (decision 130). — taken by U3
- REVIEW-15 note 6: the cache key parts named in the report with their tests (decision 130 (d)). — taken by U4
- REVIEW-15 note 8: HF-010 line, stale worktrees still registered (decision 131 (e)). — taken by U0
- REVIEW-15 note 9: HF-011 line, d5dfa02 carries `report:` (decision 131 (e)). — taken by U0
- REVIEW-15 note 10: HF-012 line, sequential reviewers and their slips (decision 131 (e)). — taken by U0
- D-013 times line, REVIEW-15's check times 794-834 s (decision 131 (e), (f)). — taken by U0

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (D-013, HF-010, HF-011, HF-012 lines; decision 131 (e)).
- [x] U1 One place reads the worker key, and the claim says so (decision 128; 122 (c), (e); DESIGN §13.5, §19.3 L3; I-13). — 6e3caa5 (key_present; doctor asks it; 128 (b) docstrings; no cause/context; 22 tests; cli.py help string and doctor docstring changed for 128 (c)'s test, finding D-016; check 3/3 828, 832, 825 s)
- [x] U2 `doctor --live workers` reads the loaded configuration (decision 129; 122 (e), 123 (c), (d); DESIGN §19.3 L3, §4.3, §13.6; I-10). — 512bb3e (load_models and load_run; constant and raw parse gone; 8 tests; the test file's MODELS_TOML given the loader's fields, assertions unchanged; run.toml without [workers] refused, design silent; check 3/3 831, 835, 837 s)
- [x] U3 The cache key's calendar and bar-length parts held by tests (decision 130; 121 (a); DESIGN §5.5, §17.1; I-6). — dcff385 (2 tests in tests/test_synth_cache.py; synth.py unchanged, 130 (c) did not apply; each key part's red test named in the body; check 3/3 834, 837, 890 s)
- [ ] U4 The final report (decisions 127 to 131; DESIGN §18.2).
