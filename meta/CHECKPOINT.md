# CHECKPOINT

Mission: 22 (`meta/BUILDER-22-PROMPT.md`), roadmap step S4.2b. The rest of the daily run; closes no milestone. Base 72400d7.
Container runtime: docker. Image at mission 21's tip: discotrade-sandbox:3b7d75c39621.

In progress: U5 STOPPED (O-27 item 3). The uncommitted U5 tree (base e4dd5c3) gave G1.3 PASS in 934 s wall (over 15
minutes) and a median ratio of 2.473 (limit 1.25): decision 184's weekly recomputation recomputes each sampled subject
from its first journaled day (decision 54), so a Monday's cost grows with history. Finding D-024 filed, committed,
awaiting the architect. The U5 work is in `git stash` as "wip U5 2026-10-20 (mission 22; D-024: G1.3 934 s, median
2.473)"; its patch, new test file and every run output are copied under meta/drafts/m22-u5-*. Tree clean. Resume
U5 only on an answer to D-024 (decisions file); U6 and U7 not started. Correction for the report: U3's body (2ae5c04)
says three new tests failed on the parent; four did.

Done: U0 (plan; D-013 times, HF-010, HF-012 lines; decision 187 (b)). U1 41accb7 (digest.py, sinks, render, --issues,
doctor --live issues; check 3/3, 1014 s). U2 b614465 (digest page, run log line with mode, push,
issues; test_replay equality adapted to 179 (c)'s mode field; G1.3 522 s; median 1.223; check 1218/1142/1214 s). U3 2ae5c04 (step 1 staged via bars.store.staged;
RevisedDataError; G1.3 557 s; median 1.143; check 1161/1203/1165 s; body miscounts tests failing on parent: 3, was 4). U4 7859488 + 91d1497 (retry, run_retried,
run_failed, catch-up with day_caught_up; D-023 filed; first attempt called begin_day per attempt against 179 (d),
corrected by the retry 91d1497; G1.3 553 then 467 s; median 1.088 then 1.116; check 1529/1513/1435 then 1414/1357/1119 s).

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
