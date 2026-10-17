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
U5 8d54f9f (gate: tests/gates/m3_harness.py, test_g3_1/2/3, 18 tests; tests/test_gate_script.py M3->M4 for the
no-gate-tests cases; D-017 filed (two-decimal forms), D-013 and D-014 times lines; seven wrong changes red (the
unsanitized description only via G3.3's direct test); check 3/3 1116, 1054, 1180 s; gates at 45dc893 + the uncommitted
gate files: M3 PASS 555 s (218/175/161), M2 PASS 142 s, G1.1 450, G1.2 204, G1.3 542, G1.4 1 s PASS, M0 PASS 247 s;
outputs meta/drafts/m17-*.txt; image discotrade-sandbox:3b7d75c39621).

Unit in progress: U6 The final report (decisions 132 to 140). Intent: decision 133 (b)'s two wrong changes run on the
two doctor cases; meta/FINAL-REPORT-17.md drafted under meta/drafts/ and moved in. Done means: the report with every
section the brief names, committed and pushed.

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
