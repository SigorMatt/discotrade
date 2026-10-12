# CHECKPOINT

Mission: 7 (`meta/BUILDER-7-PROMPT.md`), roadmap step S1.1. Closes no milestone. Base c73a695.
Done: (none yet)

Unit in progress: U0 Plan.
Intent: write meta/plan.md, this checkpoint, a journal line, HF-007 (REVIEW-6 hands note) in FINDINGS.md; one `plan:` commit, pushed.
Done means: the four files committed and pushed in one `plan:` commit.

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
