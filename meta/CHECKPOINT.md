# CHECKPOINT

Mission: 7 (`meta/BUILDER-7-PROMPT.md`), roadmap step S1.1. Closes no milestone. Base c73a695.
Done: U0 057f9d2, U1 de2a5b2, U2 c8342c4.

Unit in progress: U3 Approaches and the decision journal (decisions 24, 25, 39, 48, 49, 51; DESIGN §6.2, §7, §9.1, §9.2; I-5, I-6, I-7).
Intent: state.py approach writer, new src/discotrade/journal.py, backtest.py/executor.py only to share §7, new tests/test_journal.py.
Done means: U3 gate in BUILDER-7-PROMPT met; wrong changes (position reset each day; first-row position = target; re-run rewriting file) seen red; check green x3; gate M0 G0.1 passes if backtest/executor changed; one commit pushed.

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
