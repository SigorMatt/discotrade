# CHECKPOINT

Mission: 18 (`meta/BUILDER-18-PROMPT.md`), roadmap step S3.2b, continued. Closes milestone M3. Base 63c6d57.
Container runtime: docker. Image at mission 17's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 (plan; D-017 answered; HF-010, HF-011, HF-006, HF-012 lines).

Unit in progress: U1 — G3.3 asserts "no raw bar" and "no score" as decision 142 reads them: (a) every numeric
token of every stored message accounted for by a source of its part; (b) every harness-computed value (finite
real profile leaves, cost-line figures) meets no OHLC of W/T (as stored and times the factor) and no non-integral
earlier trial figure at rel 1e-9; (c) the profile under prices x7/3, volumes x5/2 equal to the profile, three days.
Done means: `gate:` commit touching only tests/gates/test_g3_3_prompts.py (and m3_harness.py for a helper without
seed, date or assertion), pushed; `./scripts/gate M3 G3.3` PASS with its wall time beside 158.80 s; the five wrong
changes of 142 (e) each seen red and named; check 3/3 green.

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
