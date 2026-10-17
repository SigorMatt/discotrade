# CHECKPOINT

Mission: 18 (`meta/BUILDER-18-PROMPT.md`), roadmap step S3.2b, continued. Closes milestone M3. Base 63c6d57.
Container runtime: docker. Image at mission 17's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 e6c33ae (plan; D-017 answered; HF-010, HF-011, HF-006, HF-012 lines).
U1 da7634b (gate: test_g3_3_prompts.py 3 new tests: (a) 11,367 tokens of 20 first prompts accounted, 7 retries
rebuilt; (b) 10,080 values, no meeting at rel 1e-9; (c) days 2019-07-15, 07-26, 08-09 under prices x7/3, volumes
x5/2; m3_harness.scaled_store; G3.3 PASS 180.36 s (REVIEW-17 158.80 s); five 142 (e) wrong changes red; check 3/3
1022, 1030, 1034 s; image discotrade-sandbox:3b7d75c39621).

Unit in progress: U2 — a gate test in tests/gates/test_g3_2_pool.py (markers gate, gate_m3) over the existing
m3/ and m3_pool/ replays: every manifest file with a `served` day gives exactly one call row with that day,
attempt and outcome (file = the one whose bytes the row's stored text equals); every call row with a response maps
to such a manifest row; a file with no `served` day was not served. tests/test_worker_corpus.py docstring and the
manifest's third line name that test and claim nothing more. Done means: `gate:` commit, pushed; `./scripts/gate
M3 G3.2` PASS with wall time beside 183.28 s; the three 143 (d) wrong changes each seen red; check 3/3 green.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-17-m18 (141-145) bind; decisions 1-140
still bind (139 (c)'s raw-bar/score clause replaced by 142); owner files win. No file under src/, config/ or
tests/fixtures/rejected/, no record under tests/fixtures/config/, no entry of tests/fixtures/config_frozen.json
changes. Under tests/gates/ only test_g3_3_prompts.py, test_g3_2_pool.py and m3_harness.py change (O-19); among
other tests only tests/test_worker_corpus.py (docstring) and tests/fixtures/worker_corpus/manifest.toml (third
line, a row only if measured differently). A real leak or an unexplained meeting of values: stop, finding, the
builder replies VERDICT: question (141 (a), 142 (b)). Gate config under tmp with thresholds_gate.toml copied
unchanged (72); dates and seeds in the test file; m3_harness.py holds no seed, date or assertion. Tests write
state/job dirs only under tmp, read time only via --as-of or the replay's clock, run `discotrade` in-process; a
test computes expected figures itself; ScriptedProvider over tests/fixtures/worker_corpus/; no network, secret,
real model or claude binary; no test builds the image. Wrong changes made one at a time, seen red, reverted,
named in the body; "seen to fail" only of a test seen to fail; a claim names the test that holds it (REVIEW-17
note 14). Each sub-agent runs `discotrade sandbox build` first, then ./scripts/check three times, each its own
foreground call with a 20-minute timeout (HF-006); a run past the cap is waited for and recorded (145). One
commit per unit, files listed, never `git add -A`, push. Sub-agents in the foreground only.
