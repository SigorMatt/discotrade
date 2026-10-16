# CHECKPOINT

Mission: 16 (`meta/BUILDER-16-PROMPT.md`), roadmap step S3.2a repaired. Does not close a milestone; runs no gate. Base 72c7836.
Container runtime: docker. Image at mission 15's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 ef3ebc4 (plan; D-013, HF-010, HF-011, HF-012 lines; decision 131 (e)).
U1 6e3caa5 (key_present; doctor asks it; docstrings per 128 (b); ProviderError raised outside except; 22 tests;
cli.py help text and doctor docstring name removed, finding D-016; check 3/3 825-832 s).
U2 512bb3e (doctor reads load_models and load_run's [workers] timeout; 8 tests; test MODELS_TOML given loader fields;
run.toml without [workers] refused (design silent); check 3/3 831-837 s).
U3 dcff385 (calendar and bar-length cache key tests; synth.py unchanged; check 3/3 834, 837, 890 s).

Unit in progress: U4 (final report; decisions 127-131; DESIGN §18.2). Intent: sandbox build, ./scripts/check 3x at
the tip, meta/FINAL-REPORT-16.md (drafted under meta/drafts/) with Corrections, Cache key, NOT PROVEN and the
review-items table. Done means: the report committed and pushed; verdict line.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-16-m16 (127-131) bind; decisions 1-126 still
bind; owner files (O-16..O-20, O-22) win. Product files changed only: src/discotrade/doctor.py,
src/discotrade/workers/providers.py, and src/discotrade/sources/synth.py only if 130 (c) applies. No file under
config/, tests/gates/, tests/fixtures/rejected/, no record under tests/fixtures/config/, no entry of
tests/fixtures/config_frozen.json changes; a test needing another configuration copies one under tmp. Nothing of this
mission is called from run-day or replay. Only workers/providers.py under src/discotrade/workers/ imports httpx or
starts a process (122 (f)). Doctor tests reach the provider only through WORKERS_TRANSPORT (httpx.MockTransport); a
key is set only as a dummy via monkeypatch.setenv. Tests write state/job dirs only under tmp, read time only via
FixedClock or --as-of, run `discotrade` in-process; bars on test_mixed/test_synth, seeds/dates/bar lengths in the
file; figures checked by the test's own computation. Test-first, or the wrong change made and reverted and named in
the body; each unit's "seen to fail" changes named. Existing tests unchanged in what they assert unless a cited
decision changes it (body says so). One commit per unit, files listed, never `git add -A`, push. Each sub-agent runs
`discotrade sandbox build` first (20-min timeout), then ./scripts/check three times, each its own foreground call with
a 20-minute timeout (HF-006); a unit adding >60 s says so; a run >15 min is a finding. Sub-agents in the foreground only.
