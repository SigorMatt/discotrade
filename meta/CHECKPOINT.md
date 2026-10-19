# CHECKPOINT

Mission: 21 (`meta/BUILDER-21-PROMPT.md`), roadmap step S4.2a. Closes REVIEW-20's items; closes no milestone. Base e477f67.
Container runtime: docker. Image at mission 20's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 e43c77c (plan; D-022 and its status; HF-015, HF-012, HF-010 lines; D-013 times line).
U1 558e02a (alerts: persistent_approach entry holds N and p_N, page reads them, tightened_percentile and in_force
removed from dashboard.py, RANK_P; 5 tests; no key-set test changed; register none; check 3/3 976, 981, 995 s;
sandbox discotrade-sandbox:3b7d75c39621; G1.3 PASS 462 s (460.18 s); speed ratios 1.202, 1.116, 1.097, median 1.116,
load 1.0-1.4; no finding).

In progress: U2 — the unknown-coordinator test parametrized over bogus, Claude, scripted: (171 (a)); the two claude
paths before any day held by env-independent tests (171 (b)); autouse fixture in tests/conftest.py removing every
secret env var named by a src/discotrade constant, with its test (171 (c)); 171 (d)'s list. Done means: a `tests:`
commit pushed, no src/ change, check 3/3 green, the fixture-dropped wrong change seen red under a dummy
ANTHROPIC_API_KEY, the item's tests green under a dummy key.

Standing constraints: CLAUDE.md invariants I-1..I-15; owner files O-26, O-27 win, then O-25 and earlier owner items,
then decisions 168-176, then 1-167 where not replaced. No file under tests/gates/, tests/fixtures/rejected/, no record
under tests/fixtures/config/, no entry of tests/fixtures/config_frozen.json, no value of a frozen config file changes;
config/protected_paths.toml (U3) is the one config file that changes. A met-gate test failing because of what a unit
adds: the unit stops, files a finding, builder replies VERDICT: question (168 (b)). An M1 item above 15 minutes at U1
or U5: finding, VERDICT: question (O-27 item 3). Median ratio of three runs above 1.25 fails U1 (retry once, then
blocked) and at the tip is U1's defect (170). Every new/changed return reader registered in
tests/fixtures/return_readers.toml in the same commit (O-18). Tests write state/job dirs only under tmp, read time only
via --as-of or the replay's clock, run `discotrade` in-process, compute expected figures themselves; no network,
secret, real model or real claude binary; no test builds the image. Wrong changes made one at a time, seen red,
reverted, named in the body. Each sub-agent runs `discotrade sandbox build` first, then ./scripts/check three times,
each its own foreground call with a 20-minute timeout; a run moved to the background is waited for with one
foreground poll call (timeout <= 20 min) then one read of the output, repeated (176); never Monitor or background
tasks. One commit per unit, files listed, never `git add -A`, push. Sub-agents in the foreground only.
