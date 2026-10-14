# CHECKPOINT

Mission: 11 (`meta/BUILDER-11-PROMPT.md`), roadmap step S2.0b. Closes no milestone. Base c3a3f1d.
Done: U0 7629de6, U1 93c2f91 (records unit.parquet, positions.parquet; G1.3 30 days 1.341->1.469 s/day;
one changed existing test: test_nothing_is_stored_for_it -> ..._but_the_records, decision 84 replaces 81 (d)).

Unit in progress: U2 Dormancy, return and displacement on the adjusted measure (O-11, O-12; decisions 85, 87).
Intent: lifecycle steps 2 and 3 read metrics.sharpe of paper.adjusted net_1x over decision 85's W, each subject
with its own average positions; dormant/returned/displaced rows carry adjusted and plain (decision 87).
Done means: one pushed commit; tests as the brief's U2 gate; named wrong changes seen to fail; timings in body;
./scripts/check green three times.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-14-m11 (83-90) and the owner's
decisions-2026-10-13-owner (O-N wins) bind; decisions 1-82 still bind; no value of a frozen file changes
(config/, existing entries of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/;
the gate configuration is built under tmp with thresholds_gate.toml copied unchanged, decision 72);
config/models.toml is not created; no file under tests/gates/ changes except tests/gates/test_g1_3_lifecycle.py
in U6 only; no earlier ledger line rewritten (I-5); a re-run writes nothing (I-6); tests write state only
under tmp, read time only via FixedClock, --as-of or the replay's clock; run `discotrade` in-process via the
console-script function; tests running git pass GIT_ALLOW_PROTOCOL=file, local paths only, new git-running
test files go in SUBPROCESS_FILES; day-running tests on test_mixed/test_synth, seeds and dates in the file;
each rule tested at its production value; adjusted figures in tests computed from journal parquet and bars
without paper.adjusted/unit_bars/unit_returns/average_positions; test-first, or the wrong change made and
reverted in the worktree and named in the body; existing tests unchanged in what they assert unless a cited
decision changes it (body says so); one commit per unit, files listed, never `git add -A`, push;
./scripts/check green three times before each commit, each run its own foreground call with a 20-minute
timeout (HF-006); timing measurements one per foreground call; sub-agents in the foreground only.
