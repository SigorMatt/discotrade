# CHECKPOINT

Mission: 17 (`meta/BUILDER-17-PROMPT.md`), roadmap step S3.2b. Closes milestone M3. Base af85e55.
Container runtime: docker. Image at mission 16's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 1a04ee1 (plan; D-016 answered; HF-010, HF-011, HF-012 lines).
U1 014f06a (daily.score_on_t via sequence.dry_run_and_grid on T; producer entry; tests/test_daily_score_t.py 7 tests;
three wrong changes seen red; check 3/3 844, 838, 834 s; image discotrade-sandbox:3b7d75c39621).
U2 db29997 (run_day steps 3-5 with a provider passed in; tests/test_daily_generation.py 11 tests; three wrong changes
seen red; check 3/3 867, 918, 923 s, two above 15 min, D-013 times line appended; module ~36 s).

Unit in progress: U3 The options of run-day and replay, and the scripted cursor (decision 137). Intent: --provider
(none|scripted:<dir>|openai) and --coordinator scripted on both commands; replay builds the provider once per command
with the scripted cursor's start counted from stored responses. Done means: 137 (d) tests pass, two wrong changes seen
red, check green 3/3, one commit pushed.

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
