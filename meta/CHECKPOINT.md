# CHECKPOINT

Mission: 8 (`meta/BUILDER-8-PROMPT.md`), roadmap step S1.2. Closes no milestone. Base fb1e244.
Done: U0 b06c4b2, U1 060b5e2, U2 abba5d3, U3 327c68a.

Unit in progress: U4 The controls (decisions 23, 25, 49, 54, 64; DESIGN §7, §9.2, §9.4, §10.1; I-1, I-5, I-6, I-12).
Intent: new src/discotrade/controls.py; bh:<symbol> and rc:0..rc:49 journaled every day by run-day,
monthly draws (seed YYYYMM) with pools.jsonl lines, matched/fallback draws, decision-64 hash and state
machine; controls in journal recompute and paper (clean true); tests/test_controls.py plus named
changes in test_daily/test_journal_recompute/test_journal/test_paper.
Done means: committed and pushed; wrong changes (per-bar random not keyed by ts, state machine not
restarted flat at redraw, redraw reusing previous month's seed, short entry on no-short instrument)
seen red; ./scripts/check green 3/3.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 58-65 new, 1-57 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/);
config/models.toml is not created; no test under tests/gates/ is added; tests write state only
under tmp, read time only via FixedClock or --as-of, run `discotrade` in-process via the
console-script function (except tests of the script itself); tests running git pass
GIT_ALLOW_PROTOCOL=file and local paths only (decision 47); journal/paper/control/lifecycle tests
on synthetic sources from tests/fixtures/config/ (test_mixed, test_synth), seeds in the file;
each rule tested at its production value from config/thresholds.toml (a lower value only on a
copy under tmp, said so); test-first, or where code is already right the wrong change is made and
reverted in the worktree and named in the body; each unit's named wrong changes seen to fail;
existing tests unchanged in what they assert unless a cited decision changes it (body says so);
one commit per unit, files listed, never `git add -A`, push; ./scripts/check green three times
before each commit (foreground, timeout >= 20 min, HF-006); sub-agents in the foreground only.
