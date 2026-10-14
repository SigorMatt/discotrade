# CHECKPOINT

Mission: 12 (`meta/BUILDER-12-PROMPT.md`), roadmap step S2.1. Closes no milestone. Base c2612a6.
Done: U0 d250987, U1 52d7fec (audit widened; +cli._backtest_result display, +replay._adjusted producer;
ledger requires figures, D-010; 3 test_return_readers assertions changed under 92, test_lifecycle seeds under 93; check 3/3 ~487 s), U2 92703c9 (static check, 365 tests, check 3/3 ~493 s),
U3 fa4b53b (sandbox job/runner/in-process; runner `python -I -m discotrade.sandbox.runner <dir>`; check 3/3 ~506 s),
U4 d553c35 (ProcessSandbox(scratch).run(job); run.toml wall/cpu 1200 s, 2 GiB, 64 MiB; base.py outside list; check 3/3 ~509 s),
U5 4c09fd1 (validation/sequence.py Context/Submission/dry_run_and_grid -> Outcome, STAGES; register +paper._window_units,
+paper.adjusted_rows producer, +sequence.fix_combination adjusted, +sequence._grid_result producer; check ~608 s, +100 s).

Unit in progress: U6 next — determinism, activity, the correlation gate and the sequence (decision 98; decisions 25,
63, 95 (e); DESIGN §12.2 stages 1, 3, 4, 5, §12.3; R-1).
Intent: stages 1/3/4/5 and the five in order in validation/sequence.py; validation/correlation.py; error texts
free of symbols/venues/contracts/dates; the sequence writes nothing to the state directory.
Done means: U6's gate in meta/BUILDER-12-PROMPT.md met, committed and pushed, check green 3/3.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-14-m12 (91-99) bind; the owner's
decisions-2026-10-13-owner (O-N wins); decisions 1-90 still bind; no value of a frozen file changes
(config/instruments, tracks, calendars, thresholds.toml, existing entries of tests/fixtures/config_frozen.json,
existing records under tests/fixtures/config/; gate config built under tmp with thresholds_gate.toml copied
unchanged, decision 72); only new config files are config/run.toml and tests/fixtures/config/run.toml (U4);
config/models.toml is not created; no file under tests/gates/ changes; daily.py's approach execution unchanged
(decision 48 until S2.2); no earlier ledger line rewritten (I-5); a re-run writes nothing (I-6); tests write
state/job dirs only under tmp, read time only via FixedClock, --as-of or the replay's clock; run `discotrade`
in-process via the console-script function; tests running git pass GIT_ALLOW_PROTOCOL=file, local paths only;
new subprocess-starting files go in SUBPROCESS_FILES; day-running tests on test_mixed/test_synth, seeds and
dates in the file; each rule tested at its production value; adjusted figures in tests computed from rows and
bars without paper.adjusted/adjusted_rows/unit_bars/unit_returns/average_positions; test-first, or the wrong
change made and reverted in the worktree and named in the body; existing tests unchanged in what they assert
unless a cited decision changes it (body says so); one commit per unit, files listed, never `git add -A`, push;
./scripts/check green three times before each commit, each run its own foreground call with a 20-minute
timeout (HF-006); sub-agents in the foreground only.
