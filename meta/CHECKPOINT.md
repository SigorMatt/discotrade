# CHECKPOINT

Mission: 22 (`meta/BUILDER-22-PROMPT.md`), roadmap step S4.2b. The rest of the daily run; closes no milestone. Base 72400d7.
Container runtime: docker. Image at mission 21's tip: discotrade-sandbox:3b7d75c39621.

In progress: U3 Step 1 staged (decision 181; DESIGN 16.2, 5.2, 5.4, 5.6; decisions 2026-10-12 4, 5, 50, 54; I-5).
Done means: `daily:` commit pushed; step 1's bar appends, gaps file and rolls written to the staging directory and moved
with the day; typed error of 181 (c); a day that fails leaves bars/, rolls/ and the gaps file as they were; tests of
181 (d) pass; wrong change (bar append in place instead of staged) seen red; body names 181 (a)'s means; existing
interrupted-append, gaps, rolls, revised_data tests unchanged and green; G1.3 and three measurements (median <= 1.25);
check 3/3 green with container tests.

Done: U0 (plan; D-013 times, HF-010, HF-012 lines; decision 187 (b)). U1 41accb7 (digest.py, sinks, render, --issues,
doctor --live issues; check 3/3, 1014 s). U2 b614465 (digest page, run log line with mode, push,
issues; test_replay equality adapted to 179 (c)'s mode field; G1.3 522 s; median 1.223; check 1218/1142/1214 s).

Standing constraints: CLAUDE.md invariants I-1..I-15; owner files O-26, O-27 win, then O-25 and earlier owner items,
then decisions 177-188, then 1-176 where not replaced. No file under tests/gates/, tests/fixtures/rejected/, no record
under tests/fixtures/config/ but run.toml's new [issues] and [state] tables, no entry of tests/fixtures/config_frozen.json,
no value of a frozen config file changes; config/run.toml ([issues], [state]) is the one config file that changes.
A met-gate test failing because of what a unit adds: the unit stops, files a finding, builder replies VERDICT: question
(177 (b)). U2-U5 each give G1.3 and decision 170's three measurements at the commit; median above 1.25 fails the unit
(retry once, then blocked); G1.3 or any M1 item above 15 minutes stops the mission (O-27 item 3). Item 157 (c)'s
equality test stays unchanged and green. Every new/changed return reader registered in tests/fixtures/return_readers.toml
in the same commit (O-18). Tests write state/job dirs, issue files and bare remotes only under tmp, read time only via
--as-of or the replay's clock, run `discotrade` in-process, compute expected figures themselves; git with
GIT_ALLOW_PROTOCOL=file and local paths; fake `claude`/`gh` executables under tmp; no network, secret, real model,
real claude or real gh; injected failures by monkeypatch; no test builds the image. Wrong changes made one at a time,
seen red, reverted, named in the body. Each sub-agent runs `discotrade sandbox build` first, then ./scripts/check three
times, each its own foreground call with a 20-minute timeout; a run moved to the background is waited for with one
foreground poll call (timeout <= 20 min) then one read of the output, repeated (176); never Monitor or background
tasks. One commit per unit, files listed, never `git add -A`, push. Sub-agents in the foreground only.
