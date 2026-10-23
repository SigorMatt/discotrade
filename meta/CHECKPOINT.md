# CHECKPOINT

Mission: 22 (`meta/BUILDER-22-PROMPT.md`), roadmap step S4.2b. The rest of the daily run; closes no milestone. Base 72400d7.
Container runtime: docker. Image at mission 21's tip: discotrade-sandbox:3b7d75c39621.

In progress: U5's retry under O-32 (D-025 decided). Measurement committed 961dfe0 (scripts/speed.py, CPU time in its own
cgroup, load backstop; check 1143/1136/1139 s). The U5 stash popped cleanly 2026-10-23; the finishing sub-agent found the
U5 tests and the return_readers audit green, but two ./scripts/check runs were killed at the 20-minute cap (exit 143,
91 %, tests/test_validation_sequence.py; meta/drafts/m22-u5f-check{1,2}.txt): the role's environment now has
CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 and BASH_MAX_TIMEOUT_MS=1200000, so decision 176's wait cannot be followed and
U5's check (1273-1382 s earlier) cannot end. Finding HF-020. No G1.3, no parent ratio, no O-32 speed run taken (none
counted). Under §R the work is stashed again: "wip U5 2026-10-23 (mission 22; HF-020 check killed at 20 min)"; tree
clean. Resume on an answer to HF-020: pop that stash, then sandbox build, check 3x, G1.3 (O-32 item 8), the parent's
ratio on 91d1497 with 961dfe0's speed.py, U5's first three valid runs. U5's earlier wall-time runs do not count.
U6 and U7 follow U5 under O-32. The report names O-28 and O-32.
Correction for the report: U3's body (2ae5c04) says three new tests failed on the parent; four did.

Done: U0 (plan; D-013 times, HF-010, HF-012 lines; decision 187 (b)). U1 41accb7 (digest.py, sinks, render, --issues,
doctor --live issues; check 3/3, 1014 s). U2 b614465 (digest page, run log line with mode, push,
issues; test_replay equality adapted to 179 (c)'s mode field; G1.3 522 s; median 1.223; check 1218/1142/1214 s). U3 2ae5c04 (step 1 staged via bars.store.staged;
RevisedDataError; G1.3 557 s; median 1.143; check 1161/1203/1165 s; body miscounts tests failing on parent: 3, was 4). U4 7859488 + 91d1497 (retry, run_retried,
run_failed, catch-up with day_caught_up; D-023 filed; first attempt called begin_day per attempt against 179 (d),
corrected by the retry 91d1497; G1.3 553 then 467 s; median 1.088 then 1.116; check 1529/1513/1435 then 1414/1357/1119 s).

Standing constraints: CLAUDE.md invariants I-1..I-15; owner files O-32, O-28, then O-26, O-27 win, then O-25 and earlier owner items,
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
Owner file meta/decisions/2026-10-19-owner.md (O-29 to O-31) read: no builder steps.
