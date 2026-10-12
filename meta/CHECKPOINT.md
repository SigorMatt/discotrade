# CHECKPOINT

Mission: 5 (`meta/BUILDER-5-PROMPT.md`), roadmap step S0.4. Closes M0. Base 3854c96.
Done: U0 9d2d781, U1 8e8215c, U2 8d27fe1, U3 3be4e9b, U5 2c64e8d, U6 tests 80ffc78.

Unit in progress: U4 fix (D-004 answered, see meta/plan.md "Decision on D-004"): a fresh
sub-agent under U3's rules makes independent_calc.py count the starting 0 as a peak, with a
hand-value self-test, own commit. Then U4 from the stash ("wip U4 2026-10-12"), U6 gate run, U7.
Done means: calc fix committed; U4 committed with G0.1 reference passing; `gate M0: PASS` at tip.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 34-40 new, 1-33 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ with markers gate and gate_m0, seeds in the file, state under tmp_path,
in-process command, no subprocess, no skip; one commit per unit, files listed, never `git add -A`,
push; ./scripts/check green three times before each commit (foreground, timeout >= 20 min);
sub-agents in the foreground only; no network, secret or wall clock in tests; existing tests
unchanged in what they assert unless a cited decision changes it (then the body says so).
