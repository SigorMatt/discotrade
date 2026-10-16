# CHECKPOINT

Mission: 16 (`meta/BUILDER-16-PROMPT.md`), roadmap step S3.2a repaired. Does not close a milestone; runs no gate. Base 72c7836.
Container runtime: docker. Image at mission 15's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 ef3ebc4 (plan; D-013, HF-010, HF-011, HF-012 lines; decision 131 (e)).

Unit in progress: U1 (one place reads the worker key; decision 128). Intent: providers.key_present(); doctor's
live_workers key check calls it and stops importing KEY_ENV; the two docstrings state 128 (b) and no more; every
ProviderError of OpenAICompatProvider has __cause__ and __context__ None. Done means: the source test of 128 (c), the
key_present tests, the doctor unset/blank-key tests with a failing transport, the cause/context test for status
error, malformed body and timeout pass; existing provider and doctor tests unchanged; check 3/3; one commit pushed.

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
