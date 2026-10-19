# CHECKPOINT

Mission: 20 (`meta/BUILDER-20-PROMPT.md`), roadmap step S4.2a. Closes no milestone. Base f1b8346.
Container runtime: docker. Image at mission 19's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 4ed47b4 (plan; D-014 status; D-018 and status; HF-006, HF-012, HF-010, HF-013 lines; HF-015 new).
U1 431a82e (table: scripts/speed, state.clear_caches, table file cache; 12 tests; check 3/3 1168, 1196, 1317 s
(third past the cap, waited); G1.3 PASS 898 s; figures parent 0.0587/0.0926/1.577/8.887 s, commit
0.0447/0.0716/1.600/7.817 s, load 1.9-2.5; 157 (d) 267 trees equal; 157 (e) diff empty, HEAD tree 5f9c06b7;
D-019 filed: table still recomputed over the whole paper record; D-013 times line; HF-015 status line).

U2 becb570 (alerts: _SPLITS cache in step 6, registered with clear_caches; 8 tests; check 3/3 1045, 1016, 1001 s;
G1.3 PASS 582 s; figures parent 0.0436/0.0786/1.805/7.41 s (load 2.3-3.0), commit 0.0359/0.0453/1.260/5.67 s (load
1.1-1.6); 157 (d) 267 trees equal; 157 (e) diff empty, HEAD tree 5f9c06b7; D-020 filed (step 6 residual growth);
body overclaims "rest of step 6 does not grow" (alerts.write 0.016->0.052 s), noted for the report). HF-016's cause
was CLAUDE_CODE_DISABLE_BACKGROUND_TASKS, removed by the owner.

U3 e8d31bb (bars: dashboard.render did not grow, unchanged; bars/store month files reused by bytes, gaps/rolls per
month, stats.trading_dates, table slots at once, paper/alerts shared subtraction; 26 tests; check 3/3 1459, 1356,
1198 s (first past cap, waited); G1.3 PASS 625 s at load 2.0-3.1; ratio at commit 1.234 and 1.246 in the two quiet
runs (load <=1.5), above 1.25 in every run ending at load >=2.6 (1.289-2.104), parent 1.189-1.461; figures parent p1
0.032473/0.044932/1.384/6.074 s, commit c7 0.029458/0.036355/1.234/5.675 s; 157 (d) 267 trees equal, 157 (e) diff
empty, HEAD tree 5f9c06b7; D-021 filed (U1's adjusted_E_N with two rows of one date)). Report: the ratio holds only
under low load.

U4 9269ad7 (alerts: rank_persistence entry holds p (null when not evaluated); dashboard reads p, _rank_p removed;
health panel over pool.fail_window; 9 tests; two tests changed only to admit p (146 (c)); check 3/3 1044, 1128,
1101 s; G1.3 PASS 534 s; speed 0.031791/0.037430/1.177/5.583 s, load 1.9-2.4, one run; no finding).

U5 6833101 (coordinator: ClaudeCodeCoordinator vs a fake claude, claude 2.1.303 flags --bare -p --output-format json
--max-budget-usd --permission-mode dontAsk --model --tools "" (no --max-turns in help), deny rules Edit(//path) from
code.claude.com/docs/en/permissions.md, config/protected_paths.toml (164 (a) lists + coordinator.py), run_claude
process-group kill; 48 tests; fixture run.toml [coordinator] table only (163 (b)); check 3/3 1111, 1073, 989 s; G1.3
PASS 462 s; speed 0.027775/0.033040/1.190/5.784 s, load 1.1-1.3; no finding. Report: test_cli_provider's unknown
coordinator test passes only with ANTHROPIC_API_KEY unset; token count omits cache fields).

U6 2a614bd (gates at tip 78b5535: check 3/3 990, 988, 982 s; sandbox discotrade-sandbox:3b7d75c39621; G1.1 PASS 279 s,
G1.2 PASS 170 s, G1.3 PASS 458 s, G1.4 PASS 1 s, M3 PASS 506 s, M2 PASS 130 s, M0 PASS 244 s; speed
0.027561/0.032145/1.166/5.493 s, load 1.1-1.5; outputs meta/drafts/m20-*.txt; D-013 times line; no finding).

In progress: U7 — meta/FINAL-REPORT-20.md (drafted under meta/drafts/, moved in by its commit). Done means: report
with every section the brief's U7 lists, committed and pushed; plan and checkpoint closed.

Standing constraints: CLAUDE.md invariants I-1..I-15; owner files O-26, O-27 win, then O-25 and earlier owner
items, then decisions 155-167, then 1-154 where not replaced. Speed units U1-U3 change no test's assertion, nothing
a day writes, no config value; caches in-process, keyed by path and content identity, one state dir and track at a
time; no dependency, no worker process or thread. No file under tests/gates/, tests/fixtures/rejected/, no record
under tests/fixtures/config/ (except decision 163 (b)'s `[coordinator]` table in run.toml, U5), no entry of
tests/fixtures/config_frozen.json, no value of a frozen config file changes; config/protected_paths.toml (U5) is the
one new config file. A met-gate test failing because of what a unit adds: the unit stops, files a finding, builder
replies VERDICT: question (155 (b)). G1.3 above 15 minutes at any unit or U6: finding, VERDICT: question (O-27
item 3). Ratio above 1.25 fails U3, U4, U5 (retry once, then blocked). Every new/changed return reader registered
in tests/fixtures/return_readers.toml in the same commit (O-18). Tests write state/job dirs only under tmp, read time
only via --as-of or the replay's clock, run `discotrade` in-process, compute expected figures themselves; no
network, secret, real model or real claude binary; no test builds the image. Wrong changes made one at a time, seen
red, reverted, named in the body. Each sub-agent runs `discotrade sandbox build` first, then ./scripts/check three
times, each its own foreground call with a 20-minute timeout; a run moved to the background is waited for with a
lone `sleep 240` then a lone read of its output, repeated (159 (d)); never Monitor or background tasks. One commit
per unit, files listed, never `git add -A`, push. Sub-agents in the foreground only.
