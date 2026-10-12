# CHECKPOINT

Mission: 7 (`meta/BUILDER-7-PROMPT.md`), roadmap step S1.1. Closes no milestone. Base c73a695.
Done: U0 057f9d2, U1 de2a5b2, U2 c8342c4, U3 e44866d, U4 1fbf800, U5 073a5bd.

Unit in progress: U6 Final report (meta/FINAL-REPORT-7.md), with ./scripts/gate M0 at the pushed tip.
Intent: check green x3 at the tip, gate M0 once (timeout >= 30 min), report drafted under meta/drafts/ and moved in by the report commit.
Done means: FINAL-REPORT-7.md committed and pushed with ## M0 still passes, decisions 47-55 map, Correction of FINAL-REPORT-6, NOT PROVEN, findings, Review items table; verdict line.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 47-57 new, 1-46 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/); no test
under tests/gates/ is added; tests write state only under tmp, read time only via FixedClock or
--as-of, run `discotrade` in-process via the console-script function (except tests of the
script itself); tests running git pass GIT_ALLOW_PROTOCOL=file and local paths only (decision 47);
journal/paper tests on synthetic sources from tests/fixtures/config/ (test_mixed, test_synth),
seeds in the file; test-first, or where code is already right the wrong change is made and
reverted in the worktree and named in the body; each unit's named wrong changes seen to fail;
existing tests unchanged in what they assert unless a cited decision changes it (body says so);
one commit per unit, files listed, never `git add -A`, push; ./scripts/check green three times
before each commit (foreground, timeout >= 20 min, HF-006); sub-agents in the foreground only.
