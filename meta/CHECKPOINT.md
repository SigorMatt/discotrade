# CHECKPOINT

Mission: 20 (`meta/BUILDER-20-PROMPT.md`), roadmap step S4.2a. Closes no milestone. Base f1b8346.
Container runtime: docker. Image at mission 19's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 (plan; D-014 status; D-018 and status; HF-006, HF-012, HF-010, HF-013 lines; HF-015 new).

Next: U1 — `./scripts/speed` (decision 156), the cache-clearing function and cache tests (157 (a), (b)), the
equality test in the check (157 (c)), the table's figures reused across the days of one process (158). Done means:
`table:` commit pushed; check 3/3 green with container tests run; new tests pass; the two wrong changes (table
cache keyed by path only; clearing function skipping the table cache) seen red and reverted; body gives the four
figures at parent (speed files copied into a worktree at the parent, 156 (e)) and commit, the profiles (first and
last 30 days, parent and commit), 157 (d) cold comparison and 157 (e) byte-identical comparison, G1.3 wall time and
line beside 1049 s and 1087 s, load average.

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
