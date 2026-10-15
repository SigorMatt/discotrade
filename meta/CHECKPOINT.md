# CHECKPOINT

Mission: 13 (`meta/BUILDER-13-PROMPT.md`), roadmap step S2.2. Closes milestone M2. Base 9db93b8.
Container runtime: docker, server Engine 29.1.3 (API 1.52).
Done: U0 2a216eb, U1 6372322 (error texts via fixed built-in/numpy tuples, private result fd + no_result,
BaseException caught, static order by attr name position, determinism `called` check; check 3/3 ~675 s),
U2 c702fc4 (container.py, sandbox/Dockerfile, tag discotrade-sandbox:20fa1f2225a3 built; check 3/3 712-737 s),
U3 0823a2d (probe, selftest, doctor --live sandbox; tag discotrade-sandbox:edeee6d2120e; check 3/3 697-738 s).
U5 bb27c90 (approaches behind the sandbox; fork server per day; findings D-011, D-012; check 3/3 970-1422 s under load).
Resumed under meta/decisions/decisions-2026-10-15-owner.md (O-19 D-011, O-20 D-012, O-22 U4's block; 47ebf8d).

U4 ad1b588 (rejection suite, 29 entries, no miss; check 3/3 1051-1204 s).

U5b 8b9f9be (fork server per process; 1.885 s per replay day, G1.3 projected ~621-694 s; check 3/3 858-881 s).

U5c 8b923fd (probe limit findings, G2.5 tests, scripts/gate M2 five items; image discotrade-sandbox:1edd0f8558cb; D-013;
check 3/3 877-910 s).

U6 42cea0f (O-19), 68bee5f (M2 gate tests); gate M2 PASS 157 s, M1 G1.1-G1.4 PASS (457/200/576/1 s), M0 PASS 266 s at
68bee5f; outputs in meta/drafts/gate-runs-13.md.

Unit in progress: none. Mission 13 finished; final report meta/FINAL-REPORT-13.md.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-14-m13 (100-108) bind; the owner's
decisions-2026-10-13-owner (O-N wins); decisions-2026-10-15-owner (O-19, O-20, O-22 win over 104, 105 (e), 106 (b)); decisions 1-99 still bind (48 replaced by 105 for the day loop, U5 only);
no value of a frozen file changes (config/instruments, tracks, calendars, thresholds.toml, existing entries of
tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/ except run.toml's new [sandbox]
keys in U2, same in config/run.toml); config/models.toml is not created; no existing file under tests/gates/
changes (U6 adds test_g2_*.py); only U5 changes daily.py's approach execution; no rejected fixture runs through the
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
