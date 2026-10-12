# CHECKPOINT

Mission: 5 (`meta/BUILDER-5-PROMPT.md`), roadmap step S0.4. Closes M0. Base 3854c96.
Done: U0 9d2d781, U1 8e8215c, U2 8d27fe1, U3 3be4e9b, U5 2c64e8d, U6 tests 80ffc78, U4 calc fix de9fc09, U4 2881ee0, U6 gate run at 62edb14 (gate M0: PASS), U7 dd55021.

Unit in progress: none. Mission 5 finished; meta/FINAL-REPORT-5.md exists. M0 gate PASS at 62edb14.
Intent: next: the cold review of mission 5, then the architect's next kit (carry D-004's answer as
decision 41; D-005, D-006 open).
Done means: n/a

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 34-40 new, 1-33 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ with markers gate and gate_m0, seeds in the file, state under tmp_path,
in-process command, no subprocess, no skip; one commit per unit, files listed, never `git add -A`,
push; ./scripts/check green three times before each commit (foreground, timeout >= 20 min);
sub-agents in the foreground only; no network, secret or wall clock in tests; existing tests
unchanged in what they assert unless a cited decision changes it (then the body says so).
