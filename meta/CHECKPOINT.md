# CHECKPOINT

Mission: 5 (`meta/BUILDER-5-PROMPT.md`), roadmap step S0.4. Closes M0. Base 3854c96.
Done: U0 9d2d781, U1 8e8215c, U2 8d27fe1, U3 3be4e9b, U5 2c64e8d, U6 tests 80ffc78.

Unit in progress: U4, waiting on the architect's decision of finding D-004 (DESIGN §8
max_drawdown: does the running sum start at 0?). discotrade 0.22244801873145578 vs independent
calc 0.21593456441431036 for zscore_reversal on test_mixed 2019-06-03..2019-07-31; every other
field equal to 1e-12. Draft test in `git stash` "wip U4 2026-10-12 ...". Tree clean.
On resume: apply the decision (fix metrics.py with a unit test, or a fresh U3-rules sub-agent fixes
independent_calc.py), land U4 from the stash, then U6's gate run at the tip, then U7.
NOTE: `./scripts/gate M0` at 80ffc78 prints PASS, but G0.1 there holds only the self-test; that
PASS does not close M0.
Done means: U4 committed with G0.1 reference test passing; `gate M0: PASS` at the tip with it.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 34-40 new, 1-33 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ with markers gate and gate_m0, seeds in the file, state under tmp_path,
in-process command, no subprocess, no skip; one commit per unit, files listed, never `git add -A`,
push; ./scripts/check green three times before each commit (foreground, timeout >= 20 min);
sub-agents in the foreground only; no network, secret or wall clock in tests; existing tests
unchanged in what they assert unless a cited decision changes it (then the body says so).
