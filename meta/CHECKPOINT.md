# CHECKPOINT

Mission: 13 (`meta/BUILDER-13-PROMPT.md`), roadmap step S2.2. Closes milestone M2. Base 9db93b8.
Container runtime: docker, server Engine 29.1.3 (API 1.52).
Done: U0 (this plan commit).

Unit in progress: U1 (next).
Intent: REVIEW-12 should-fix 1 to 4 and notes 2 and 3 (decision 101): error texts name only built-in
exception types and fixed result types; the runner's result on a private descriptor, `no_result`;
BaseException caught at load and call; static check's first offender by the attribute name's position;
determinism compares the reverse job's called bars with its sample (harness error); shared error-text helper.
Done means: the U1 gate of the brief holds, the four "seen to fail" changes were made and reverted,
./scripts/check green 3/3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-14-m13 (100-108) bind; the owner's
decisions-2026-10-13-owner (O-N wins); decisions 1-99 still bind (48 replaced by 105 for the day loop, U5 only);
no value of a frozen file changes (config/instruments, tracks, calendars, thresholds.toml, existing entries of
tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/ except run.toml's new [sandbox]
keys in U2, same in config/run.toml); config/models.toml is not created; no existing file under tests/gates/
changes (U6 adds test_g2_*.py); only U5 changes daily.py's approach execution; no hostile fixture runs through the
subprocess or in-process backend or the decision-21 loader; the image is built only by `discotrade sandbox build`
as a setup step, never in a test; container tests carry the `container` marker, mount only a job dir under tmp,
leave no container; tests write state/job dirs only under tmp, read time only via FixedClock, --as-of or the
replay's clock; run `discotrade` in-process via the console-script function; tests running git pass
GIT_ALLOW_PROTOCOL=file, local paths only; new subprocess-starting files go in SUBPROCESS_FILES; day-running tests
on test_mixed/test_synth, seeds and dates in the file; each rule tested at its production value; adjusted figures in
tests computed from rows and bars without paper.adjusted/adjusted_rows/unit_bars/unit_returns/average_positions;
test-first, or the wrong change made and reverted in the worktree and named in the body; existing tests unchanged
in what they assert unless a cited decision changes it (body says so); one commit per unit, files listed, never
`git add -A`, push; ./scripts/check green three times before each commit, each run its own foreground call with a
20-minute timeout (HF-006); a unit adding >60 s to a run says so; a run >15 min is a finding; sub-agents in the
foreground only.
