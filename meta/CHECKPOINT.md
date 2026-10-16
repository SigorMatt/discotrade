# CHECKPOINT

Mission: 15 (`meta/BUILDER-15-PROMPT.md`), roadmap step S3.2a. Does not close a milestone. Base 301a5c7.
Container runtime: docker. Image at mission 14's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 (plan; HF-010, HF-011 lines, HF-012; decision 120).

Unit in progress: U1 — REVIEW-14 should-fix 1 and notes 3, 4, 7 (decision 119). Done means: a fence line after
the last block parses to `no_description`; `sanitize('ab cd', 3) == 'ab'`; the profile's roll-record refusal tested
on a store built in the test; conftest templates running init-state/run-day pass GIT_ALLOW_PROTOCOL=file; seen-to-fail
changes named; check 3/3; one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-16-m15 (118-126) bind; owner files
(O-11, O-13, O-16..O-20, O-22) win; decisions 1-117 still bind (117 (c) amended by 119 (a)). No value of a frozen
file changes (config/instruments, tracks, calendars, thresholds.toml, existing values of config/run.toml and
tests/fixtures/config/run.toml, existing entries of tests/fixtures/config_frozen.json, existing records under
tests/fixtures/config/); only U4 creates config/models.toml, tests/fixtures/config/models.toml, the [workers]
tables and new frozen-map entries. No file under tests/gates/ or tests/fixtures/rejected/ changes (O-19). Nothing of
this mission is called from run-day or replay (118 (a)). Only workers/providers.py under src/discotrade/workers/
imports httpx or starts a process (122 (f)); no test opens a socket or calls a provider, model or claude binary; no
key read, logged, stored or prompted. The image is built only by `discotrade sandbox build` as a setup step;
container tests carry the marker, mount only a job dir under tmp, leave no container. Tests write state/job dirs
only under tmp, read time only via FixedClock, --as-of or the replay's clock; run `discotrade` in-process; git tests
pass GIT_ALLOW_PROTOCOL=file, local paths; new subprocess files go in SUBPROCESS_FILES; bars on test_mixed/test_synth,
seeds and dates in the file; each rule at its production value; a figure checked by the test's own computation.
Test-first, or the wrong change made and reverted and named in the body; each unit's "seen to fail" changes named.
Existing tests unchanged in what they assert unless a cited decision changes it (body says so). One commit per unit,
files listed, never `git add -A`, push. ./scripts/check green three times before each commit, each its own
foreground call with a 20-minute timeout (HF-006); a unit adding >60 s says so; a run >15 min is a finding.
Sub-agents in the foreground only.
