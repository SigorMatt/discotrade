# CHECKPOINT

Mission: 10 (`meta/BUILDER-10-PROMPT.md`), roadmap step S2.0a. Closes no milestone. Base 54cac11.
Done: (none yet)

Unit in progress: U0 Plan.
Intent: write meta/plan.md, this checkpoint, the journal line and the D-007 status line; one `plan:` commit, pushed.
Done means: the four files committed and pushed in one `plan:` commit.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-14 (76-82) and the owner's
decisions-2026-10-13-owner (O-N wins over 76-82) bind; decisions-2026-10-12 items 1-75 still bind;
no value of a frozen file changes (config/, existing entries of tests/fixtures/config_frozen.json,
existing records under tests/fixtures/config/; the gate configuration is built under tmp with
thresholds_gate.toml copied unchanged, decision 72); config/models.toml is not created; no file
under tests/gates/ changes (decision 82); speed units change nothing a day computes or stores
(decision 80 (a)-(c)): identical state byte for byte at parent and commit, one process, no threads;
tests write state only under tmp, read time only via FixedClock, --as-of or the replay's clock;
run `discotrade` in-process via the console-script function (except tests of the script itself);
tests running git pass GIT_ALLOW_PROTOCOL=file and local paths only (decision 47), new git-running
test files go in SUBPROCESS_FILES; day-running tests on test_mixed/test_synth, seeds and dates in
the file; each rule tested at its production value; test-first, or the wrong change made and
reverted in the worktree and named in the body; each unit's named wrong changes seen to fail;
existing tests unchanged in what they assert unless a cited decision changes it (body says so);
one commit per unit, files listed, never `git add -A`, push; ./scripts/check green three times
before each commit, each run its own foreground call with a 20-minute timeout (HF-006); timing
measurements one per foreground call; sub-agents in the foreground only.
