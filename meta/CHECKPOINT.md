# CHECKPOINT

Mission: 22 (`meta/BUILDER-22-PROMPT.md`), roadmap step S4.2b. The rest of the daily run; closes no milestone. Base 72400d7.
Container runtime: docker. Image at mission 21's tip: discotrade-sandbox:3b7d75c39621.

In progress: U2 The digest, the run log and step 8 in the day (decisions 179, 180; DESIGN 15.4, 16.1 steps 7 and 8,
16.2, 14.3; I-6, I-8). Done means: `daily:` commit pushed; step 7 writes digests/<track>/<D>.md (harness tables +
coordinator prose from kinds and subjects only) or the coordinator's run log sentence; every new day appends one run
log line with its `mode` (179 (c)); a re-run writes neither; step 8 commits, pushes when the state repo has `origin`
(push_failed on failure), opens one issue per fired alert via the sink (issue_failed on failure); [state] table in
run.toml; replay --issues default none; tests of 179 (f), 180 (d) pass; wrong changes (payload number in the digest
prompt; run log line skipped on a digest day; push before commit) seen red; G1.3 at the commit and decision 170's three
measurements, median ratio <= 1.25; check 3/3 green with container tests.

Done: U0 (plan; D-013 times, HF-010, HF-012 lines; decision 187 (b)). U1 41accb7 (digest.py, sinks, render, --issues,
doctor --live issues; check 3/3, 1014 s).

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
