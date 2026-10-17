# CHECKPOINT

Mission: 17 (`meta/BUILDER-17-PROMPT.md`), roadmap step S3.2b. Closes milestone M3. Base af85e55.
Container runtime: docker. Image at mission 16's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 1a04ee1 (plan; D-016 answered; HF-010, HF-011, HF-012 lines).
U1 014f06a (daily.score_on_t via sequence.dry_run_and_grid on T; producer entry; tests/test_daily_score_t.py 7 tests;
three wrong changes seen red; check 3/3 844, 838, 834 s; image discotrade-sandbox:3b7d75c39621).
U2 db29997 (run_day steps 3-5 with a provider passed in; tests/test_daily_generation.py 11 tests; three wrong changes
seen red; check 3/3 867, 918, 923 s, two above 15 min, D-013 times line appended; module ~36 s).
U3 545e7ec (--provider/--coordinator on run-day and replay; provider once per command; scripted start from stored
responses; tests/test_cli_provider.py 17 tests; two wrong changes seen red; providers.py docstring sentence; check 3/3
925, 928, 963 s, D-013 times line).
U4 446b0a8 (tests/fixtures/worker_corpus/: 16 strategies, m3/ 27 responses, m3_pool/ 21, manifest.toml;
tests/test_worker_corpus.py 6 tests <1 s; G3.1 span 2019-07-15..2019-08-09 (ordinals 29-48) after init-state
2019-06-03, measured 15 trials (MiniMax 5, nemotron 6, openai 4), max |corr| 0.609; m3_pool 2019-07-15..07-31: budget
07-15, model_removed 07-29; check 3/3 1281, 1024, 1079 s on a shared machine, D-013 times and HF-006 status lines).

Unit in progress: U5 The gate tests of M3 and the gate runs (decisions 132 (b), 139). Intent: tests/gates/test_g3_1,
test_g3_2, test_g3_3 and m3_harness.py; the seven wrong changes of 139 (d) seen red; check 3/3 at the tip; sandbox
build; gate M3, M2, M1 G1.1-G1.4, M0, each its own call, outputs kept in meta/drafts/m17-*.txt. Done means: one
`gate:` commit (gate files + D-014 times line) pushed, all gates PASS at the tip.

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
