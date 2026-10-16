# CHECKPOINT

Mission: 17 (`meta/BUILDER-17-PROMPT.md`), roadmap step S3.2b. Closes milestone M3. Base af85e55.
Container runtime: docker. Image at mission 16's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 1a04ee1 (plan; D-016 answered; HF-010, HF-011, HF-012 lines).

Unit in progress: U1 Scoring a generated candidate on T (decision 135). Intent: a function in daily.py turning a
workers.generate.Candidate into a lifecycle.Candidate with T figures (metrics_t, adjusted_t) scored in the day's
backend; producer entry in return_readers.toml; own test module. Done means: decision 135 (f)'s tests pass, the three
wrong changes seen red, check green 3/3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-16-m17 (132-140) bind; decisions 1-131 still
bind; owner files (O-11, O-13, O-16..O-20, O-22) win. No file under config/ or tests/fixtures/rejected/, no existing
file under tests/gates/ (O-19; U5 adds test_g3_*.py and m3_harness.py), no record under tests/fixtures/config/, no
entry of tests/fixtures/config_frozen.json changes; a test needing another configuration copies one under tmp
(thresholds_gate.toml copied unchanged, decision 72). return_readers.toml may gain producer/display entries named in
the body (O-18); no adjusted entry reclassified, no second stage3_money. Only workers/providers.py under
src/discotrade/workers/ imports httpx or starts a process (122 (f)). Providers in tests: ScriptedProvider over a
fixture/tmp dir, or httpx.MockTransport for the openai refusal; a key only as a dummy via monkeypatch.setenv. Every
source a backend runs is byte-identical to a file under reference/ or tests/fixtures/ (104 (d)); no test builds the
image. Tests write state/job dirs only under tmp, read time only via FixedClock, --as-of or the replay's clock, run
`discotrade` in-process; bars on test_mixed/test_synth, seeds/dates/bar lengths in the file; figures by the test's own
computation (adjusted figures without paper.adjusted*, unit_bars, unit_returns, average_positions). Check tests replay
a few days at most; twenty-day replays are the gate's (140). Test-first, or the wrong change made, seen red, reverted,
named in the body; "seen to fail" only of a test seen to fail (REVIEW-16 should-fix 1). Existing tests unchanged in
what they assert unless a cited decision changes it (body says so). One commit per unit, files listed, never
`git add -A`, push. Each sub-agent runs `discotrade sandbox build` first (20-min timeout), then ./scripts/check three
times, each its own foreground call with a 20-minute timeout (HF-006); a unit adding >60 s says so; a run >15 min is a
finding. Sub-agents in the foreground only.
