# CHECKPOINT

Mission: 6 (`meta/BUILDER-6-PROMPT.md`), roadmap step S0.4 repaired. Closes M0. Base 19196da.
Done: U0 cdc031f, U1 c1a2100, U2 9ca8575, U3 9e16050.

Unit in progress: U4 tests/test_gate_script.py under load (REVIEW-5 note; decision 45; DESIGN §18.2).
Intent: each test of the file asserts what it did at the base, but any ./scripts/gate subprocess runs
an item that takes seconds (e.g. G0.4) and no subprocess timeout is below 1200 s.
Done means: with the script made to print PASS for a failing item (made and reverted) the file goes
red; body lists per test the item before/after and the file's run time before/after; check green x3.

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
