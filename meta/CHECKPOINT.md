# CHECKPOINT

Mission: 6 (`meta/BUILDER-6-PROMPT.md`), roadmap step S0.4 repaired. Closes M0. Base 19196da.
Done: U0 cdc031f, U1 c1a2100, U2 9ca8575, U3 9e16050, U4 b268252, U5 gate run at 65718c5 (gate M0: PASS), U6 final report.

Unit in progress: none. Mission 6 finished; meta/FINAL-REPORT-6.md exists. M0 gate PASS at 65718c5.
Intent: next: the cold review of mission 6, then the architect's next kit.
Done means: n/a

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 41-46 new, 1-40 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ named test_g0_<n>_<what>.py, markers gate and gate_m0, seeds in the file,
state under tmp_path, in-process command, no subprocess, no skip, each item < 15 min; product
defects fixed only with a unit test outside tests/gates/ seen to fail first; where code is already
right, the wrong change is made and reverted in the worktree and named in the body; one commit per
unit, files listed, never `git add -A`, push; ./scripts/check green three times before each commit
(foreground, timeout >= 20 min, HF-006); sub-agents in the foreground only; no network, secret or
wall clock in tests; existing tests unchanged in what they assert unless a cited decision changes
it (then the body says so); U2 (and any calc fix) by its own sub-agent under the forbidden-files words.
