# CHECKPOINT

Mission: 5 (`meta/BUILDER-5-PROMPT.md`), roadmap step S0.4. Closes M0. Base 3854c96.
Done: U0.

Unit in progress: U1 (next).
Intent: U1 — BarStore classification test enumerates every public name, properties included
(decision 34); gaps.py, update_rolls and adjusted_as_of refuse with decision 18's errors when the
index has no entry but the directory holds an unlisted month file (decision 35).
Done means: one commit pushed with the U1 tests seen to fail first (or by a wrong change made and
reverted), ./scripts/check green three times.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 34-40 new, 1-33 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); gate tests
only under tests/gates/ with markers gate and gate_m0, seeds in the file, state under tmp_path,
in-process command, no subprocess, no skip; one commit per unit, files listed, never `git add -A`,
push; ./scripts/check green three times before each commit (foreground, timeout >= 20 min);
sub-agents in the foreground only; no network, secret or wall clock in tests; existing tests
unchanged in what they assert unless a cited decision changes it (then the body says so).
