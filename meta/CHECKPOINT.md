# CHECKPOINT

Mission: 21 (`meta/BUILDER-21-PROMPT.md`), roadmap step S4.2a. Closes REVIEW-20's items; closes no milestone. Base e477f67.
Container runtime: docker. Image at mission 20's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 e43c77c (plan; D-022 and its status; HF-015, HF-012, HF-010 lines; D-013 times line).
U1 558e02a (alerts: persistent_approach entry holds N and p_N, page reads them, tightened_percentile and in_force
removed from dashboard.py, RANK_P; 5 tests; no key-set test changed; register none; check 3/3 976, 981, 995 s;
sandbox discotrade-sandbox:3b7d75c39621; G1.3 PASS 462 s (460.18 s); speed ratios 1.202, 1.116, 1.097, median 1.116,
load 1.0-1.4; no finding).

U2 943a18c (tests: unknown-coordinator test over bogus/Claude/scripted:; claude off PATH test (no-key path already
held by test_cli::test_coordinator_claude_is_refused_before_any_day); autouse _no_secret_env removing ANTHROPIC_API_KEY
(coordinator.KEY_ENV), NEBIUS_API_KEY (workers.providers.KEY_ENV), DATABENTO_API_KEY (sources.vendor.KEY_ENV);
tests/test_secret_env.py 4 tests; dummy-key run 201 passed; check 3/3 987, 997, 985 s; no finding. Not proven:
module/session-scoped fixtures still see the env).

U3 50341fc (coordinator: fix session --tools Read,Glob,Grep,Edit,Write; session_settings deny Bash, WebFetch, WebSearch
then Edit(//path) rules; protected_paths code list + config.py, workers/providers.py, CLAUDE.md, DESIGN.md, SPEC.md,
PLAYBOOK.toml, meta/, .claude/, docs/ARCHITECT-HANDBOOK.md, templates/; 2 tests added, 2 exact-equality tests extended
by the three whole-tool rules (172 (a)); claude 2.1.303; check 3/3 994, 990, 994 s; no finding).

U4 d679adc (tests: test_a_rewritten_complete_month_gives_its_new_missing_bars, same-rows and other-rows cases; month
replaced through BarStore.append after the test deletes index.json and the month files (append and recover cannot
replace a complete month; docstring says so); wrong change seen red; check 3/3 986, 978, 997 s; no finding).

U5 2affd42 (gates at tip c36df23: check 3/3 987, 974, 989 s (2576 passed); sandbox discotrade-sandbox:3b7d75c39621;
G1.1 PASS 282 s, G1.2 PASS 169 s, G1.3 PASS 462 s, G1.4 PASS 1 s, M3 PASS 503 s, M2 PASS 132 s, M0 PASS 245 s; speed
1.197, 1.170, 1.096, median 1.170, load 1.2-1.3; outputs meta/drafts/m21-u5-*.txt; D-013 times line; no finding).

U6 dec0f84 (meta/FINAL-REPORT-21.md). Mission 21 finished; nothing in progress.

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
