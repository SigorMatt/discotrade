# CHECKPOINT

Mission: 21 (`meta/BUILDER-21-PROMPT.md`), roadmap step S4.2a. Closes REVIEW-20's items; closes no milestone. Base e477f67.
Container runtime: docker. Image at mission 20's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 (plan; D-022 and its status; HF-015, HF-012, HF-010 lines; D-013 times line).

In progress: U1 — `persistent_approach`'s `N` and `p_N` in the alert state, the dashboard reads them (decision 169;
D-022), `RANK_P` in place of the literal "p" (169 (e)). Done means: an `alerts:` commit pushed, check 3/3 green with
the container tests run, the tests of 169 (d) pass, the wrong change (page calling stats.tightened_percentile) seen
red, the body lists every dashboard.py call into stats/alerts/table/paper (169 (c)), G1.3 time at the commit (beside
458 s), decision 170's three measurements with median ratio <= 1.25.

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
