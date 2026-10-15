# REVIEW-13 — cold review of mission 13 (roadmap step S2.2, closes M2)

Base: 019435e (`review: mission 12`, the last `review:` commit), reviewed up to
origin/main 8315c2f (`report: mission 13 final report`). Brief:
`meta/BUILDER-13-PROMPT.md`; decisions `meta/decisions/decisions-2026-10-14-m13.md`
(100 to 108) and the owner's `meta/decisions/decisions-2026-10-15-owner.md` (O-19,
O-20, O-22), which wins over decisions 104, 105 (e), 106 (b), DESIGN §12.5 and
§18.3 G2.1, and adds G2.5. Runtime on the review machine: docker, server 29.1.3.
Unit commits reviewed, one sub-agent each, run one at a time (HF-008): 6372322
(U1), c702fc4 (U2), 0823a2d (U3), bb27c90 (U5), ad1b588 (U4), 8b9f9be (U5b),
8b923fd (U5c), 42cea0f (U6a), 68bee5f (U6b). Read for forbidden edits only:
9db93b8, 2a216eb, 6e12834, cb2063e, 40fc911, 10142a7, eff2dff, 8bae433, 47ebf8d,
d248b6b, fe5ac3c, 6e18b74, a44581f, 13b2631, 8315c2f.

## Gate

Gate M2: PASS

Run by the reviewer at the tip 8315c2f (origin/main; product code identical to
68bee5f), one foreground call, after `discotrade sandbox build`:

```
sandbox build: present, nothing built
discotrade-sandbox:1edd0f8558cb
G2.1 PASS 36 passed in 41.94s
G2.2 PASS 3 passed in 24.85s
G2.3 PASS 8 passed in 3.54s
G2.4 PASS 9 passed in 39.60s
G2.5 PASS 5 passed in 19.78s
gate M2: PASS
exit=0 wall=132s
```

No container of the run remained (`docker ps -a` showed only the unrelated
`ntfy` container).

Item by item, against DESIGN §18.3 M2 as O-22 amends it and decision 106 (a)
to (e):

- **G2.1** (`tests/gates/test_g2_1_rejected.py`, O-22 item 2). §12.5's list is
  held as a literal (27 entries, split as 104 (a) splits them) plus REVIEW-12's
  two. The manifest must equal it, one file per entry. Each text goes through
  the whole `validate` on the container backend, on `test_synth`'s W of
  2019-07-15, at the production thresholds. Each must be rejected at its
  manifest stage, and for static texts at its rule. Static texts must start no
  container and run-time texts at least one. Shorter limits are used only for
  the endless loop and the memory bomb, and the file says so. Error texts must
  pass 101 (f)'s check. State bytes, `HEAD`, ledgers/`trials/` and a sentinel
  tree must be unchanged, and no container may remain. `changes_30.py` must
  then pass in the same process. Any raise fails the pass's fixture, which
  covers "no harness failure". Meets the item as narrowed.
- **G2.2** (`test_g2_2_duplicate.py`, 106 (c)). An approach from
  `reference/trend_ma.py` is admitted. Its sign-flipped twin must fail stage
  `correlation`, with the exact text naming the approach id. The correlation is
  computed in the test and must be below `-corr_max`, so only the absolute value
  catches it. `changes_30.py`, whose |r| < `corr_max` (computed in the test),
  must pass every stage, and the approach's job must run. Meets the item.
- **G2.3** (`test_g2_3_probe.py`, 106 (d), O-22 item 3). One probe run on W's
  job. Assertions:
  - network: no route, `lo` only, failed TEST-NET-1 connection;
  - file system: EROFS under `/`, `/usr`, `/home` and `/job`, and `/tmp`
    writable;
  - user: non-root uid/gid/euid/egid and an empty CapEff;
  - limits: `pids.max`, `memory.max` with swap 0, `cpu.max` and `RLIMIT_CPU`
    equal the production `run.toml`'s;
  - mount: per instrument, count = W + context, counted from the store, which
    holds later bars (`after > 0` asserted);
  - `judge` passes all 19 findings, and `sandbox selftest` prints 19 PASS lines
    and exits 0.

  Meets the item. The "no later bar" part rests on counts, not content
  (Should-fix 1).
- **G2.4** (`test_g2_4_sequence.py`, 106 (e)). `grid_lean.py`'s grid must fix
  the combination with the greatest exposure-adjusted Sharpe at 1x. The test
  computes this from the rows and the stored bars without the forbidden `paper`
  functions, and asserts the plain Sharpe would pick another. `changes_30.py`
  must pass determinism, activity and every stage. Each of the five stages must
  fail on its fixture with the exact rule, the run must stop there (the job
  modes are asserted), and the error text must be clean. Meets the item.
- **G2.5** (`test_g2_5_limits.py`, O-22 item 4). The fixtures are trusted and
  bounded by constants in their own text, which the test checks. The wall test
  must end in `limit [wall_clock]` within 3 s + a 5 s grace (the grace is the
  test's own; the design names none), with no container left. The output test
  must end in `limit [output]` with the bytes read ≤ the cap. The memory test
  must end in `limit` or `dry_run`, never a raise, with the harness's peak RSS
  growing by < 64 MiB (O-22 says "unchanged"; the tolerance is disclosed in
  NOT PROVEN). Each fixture must also pass under the production limits.
  Process count and CPU are left to G2.3, and a test records that choice.
  Meets the item.
- No product special case for a gate test was found (68bee5f's sub-agent and
  my reading). Every gate file is marked `gate`, `gate_m2` and `container`.
  Seeds and dates are written in each test file. `m2_harness.py` holds no seed,
  date or item assertion. `scripts/gate` counts five M2 items, as O-22
  approves.
- The sub-agent of 68bee5f made the five seen-to-fail mutations of the commit
  body, and each item went FAIL:
  - `G2.1 FAIL 1 failed, 35 passed`
  - `G2.2 FAIL 1 failed, 2 passed`
  - `G2.3 FAIL 3 failed, 5 passed`
  - `G2.4 FAIL 1 failed, 8 passed`
  - `G2.5 FAIL 1 failed, 4 passed`

## Blockers

None.

## Should-fix

1. **G2.3 proves "no later bar" by count, not by content.** The mount carries no
   `ts` array, so the probe's `latest_open` is always `null`, and the test
   asserts it is (`tests/gates/test_g2_3_probe.py:202`). From inside, the item
   rests on each instrument's bar count equalling the count of W plus context
   taken from the store. A mount that dropped its earliest context bar and
   carried one T bar would have the same count and pass the probe's own
   assertion. Only `judge`'s harness-side check of the job's own last `ts`
   would catch it, and that is not something the probe saw. Decision 106 (d)
   asks the test to compare "the mount's bars with the store itself". Compare
   content, for example each instrument's last mounted close (or a digest of
   the mounted arrays) with the store's last W bar (or W plus context), so that
   a later bar is detected from inside whatever the count.
2. **`sandbox selftest` / L5 judges the mount against the job it built, not
   against the store.** `src/discotrade/sandbox/container.py` `expected_mount`
   takes the expected count from `len(ji.bars)` of the very job under test.
   So in the self-test (the owner's L5), a `write_job` that mounts different
   rows of the same length passes. FINAL-REPORT-13's NOT PROVEN already
   records that a state with no bars passes its `mount.<symbol>` findings with
   0 bars. Derive the expected W + context counts independently from the store
   (as G2.3 does), and fail a mount finding whose W count is 0.
3. **A wall-clock limit can become a harness error that fails the day.** At
   `src/discotrade/sandbox/process.py:469`,
   `server.wait(max(0.0, deadline - time.monotonic()))` reaches
   `self.sock.settimeout(0.0)` (`:254`) when the remaining time has run out.
   A 0.0 timeout makes the socket non-blocking, so `recv` raises
   `BlockingIOError`, not `TimeoutError`. The `except TimeoutError` at `:470`
   misses it, and the `except OSError` at `:475` drops the server and raises
   `SandboxUnavailable`. The job's `limit [wall_clock]` result is lost (decision
   105 (c) says a limit retires the approach), the whole day fails, and the
   next job logs a `sandbox_restarted` notice. The window is narrow, but it is
   real. It came in with bb27c90 and is still at the tip. Treat a remaining
   time ≤ 0 as the breach, or catch `BlockingIOError` with the timeout, and add
   a test that drives the deadline to zero.
4. **A re-run of a journaled day can write a new health line (I-6).**
   `src/discotrade/daily.py:342-350` appends a `sandbox_restarted` notice
   whenever the fork server restarted during `journal_day`, including on a
   re-run of a day already journaled (status unchanged). I-6 says a re-run
   "writes nothing new". §16.2 exempts the health log only for a failed day.
   FINAL-REPORT-13 reads I-6 more narrowly ("I-6 holds for the day's records,
   not for that notice"), and no finding records that reading. Either write no
   notice when the day's journal is unchanged, or file the `D-###` finding
   that asks the architect whether operational notices fall under I-6.
5. **G1.3 ran above O-3's 10 minutes in this review.** The U6a sub-agent ran
   `./scripts/gate M1 G1.3` at 42cea0f twice, one call at a time with nothing
   else running: 618 s (the parent assertion, FAIL as expected) and 607 s (the
   commit, `G1.3 PASS 10 passed in 606.57s (0:10:06)`). The builder measured
   576 s at 68bee5f, "24 s under". O-20 makes G1.3 above 10 minutes a finding
   with the times. File it, with the builder's and these times, since the
   margin depends on the machine's load.
6. **U4 departed from O-22 item 1 without a finding, and its body is
   inexact.** O-22 item 1 asks that a run-time entry's existing text be "copied
   by path with its manifest entry pointing at the copy". The manifest instead
   points at the four originals under `tests/fixtures/strategies/`. The reason
   is sound: a byte-identical copy under `rejected/` shares its hash with a
   trusted original, so 104 (d)'s exclusion would either accept the copy or
   refuse the original. That makes this a conflict inside the owner's file,
   and it belongs in `FINDINGS.md`, not in the commit body as "design silent".
   The same body says "24 validation fixtures" where the directory holds 25
   (FINAL-REPORT-13 notes this). It also lists the change to
   `src/discotrade/journal.py` (`trusted_hashes(exclude=...)`), a file outside
   U4's permitted files, without saying it falls outside them or why. File the
   finding and record the corrections in the next report.

## Notes

1. FINAL-REPORT-13 §NOT PROVEN was read against the sub-agents' findings. It
   covers the container boundary (one machine, L5), the floor of the suite, the
   dropped containment pass, the load-dependent call-time limits, the
   fetched-not-verified pins, whole-number prices, the subprocess backend not
   being a boundary, the grid's adjusted figure, the cgroup-v2-only probe,
   G2.5's 64 MiB tolerance and 5 s grace, the 0-bar self-test, `atexit`
   coverage and the restart notice. The sub-agents found nothing it claims as
   proven that the disk contradicts. Should-fix 3 (the timeout race) is not in
   it.
2. `./scripts/check` in this review, one run per commit:
   - U1: 589 s
   - U2: 644 s
   - U3: 733 s
   - U5: 955 s (15:53)
   - U4: 939 s (15:37)
   - U5b: 881 s
   - U5c: 872 s
   - U6a: 909 s
   - U6b: 872 s (14m31.6s)

   All were green with the `container` tests run, not skipped. The U4 and U5
   runs were above HF-006's 15 minutes, which is already in D-012 and D-013.
   The tip is about 870 s, against 590 s at the base.
3. `src/discotrade/sandbox/runner.py:190` and `:264-267`: `check()` calls
   `float(value)` outside the catch-all. Past the static check, a `float`
   subclass whose `__float__` raises escapes `execute`. The static check
   refuses `def __float__` (underscore rule). In a child process this ends as
   an abnormal exit, a job error, so nothing leaks and nothing fails the
   harness. It predates the mission. A later unit may want it caught as
   `dry_run`.
4. `runner.py:92` `BUILTIN_EXCEPTIONS` omits the `Warning` family,
   `ExceptionGroup` and `BaseExceptionGroup`. They are named `an exception`,
   which is safe, but the tuple is narrower than 101 (a)'s "the exception
   classes of Python's builtins".
5. `src/discotrade/sandbox/container.py:349`: if `remove()` raises (for example
   its 120 s timeout against a stuck daemon), the `finally` skips `_end(proc)`,
   so the runtime client and the container may be left. This is unlikely and
   untested.
6. 68bee5f also changes `tests/test_gate_script.py`, although the brief says
   the U6 commit "carries only the new gate files". The change was
   unavoidable: the old test expected `gate M2` to fail for want of tests, so
   `./scripts/check` would go red. The body says so, and the assertions move
   to M3 unchanged.
7. `tests/gates/test_g1_3_lifecycle.py:117`: the helper `fail()` is now unused,
   left in place so that no other line moved, as the 42cea0f body says.
8. `changes_bars_in_place.py` is rejected only for being flat (`activity`), as
   O-22 allows. Nothing detects the in-place change itself.
9. The owner's file says it "adds gate item G2.5 to DESIGN §18.3" and retires
   the name `hostile`, "DESIGN §12.5's title included". `DESIGN.md` is
   unchanged and still says `tests/fixtures/hostile/` and lists four M2 items.
   Builders may not edit it, so the architect or owner should apply the text
   so that the design matches the gate. Until then the owner's file wins.
10. Frozen config: `git diff 019435e origin/main` of `config/` and
    `tests/fixtures/config/` shows only the new `[sandbox]` keys of 102 (d) in
    the two `run.toml` files. `tests/fixtures/config_frozen.json` is
    unchanged, and `config/models.toml` does not exist. Under `tests/gates/`,
    the only existing file changed is `test_g1_3_lifecycle.py`, under O-19.
    `scripts/gate` changed only the M2 count, under O-22.
11. Meta commits: the kit 9db93b8 (architect) and 47ebf8d (the owner's file)
    touch protected paths by their roles' right. 47ebf8d's file is
    byte-identical to `~/Downloads/decisions-2026-10-15-owner.md`. No builder
    or sub-agent commit touches `DESIGN.md`, `SPEC.md`, `PLAYBOOK.toml`, the
    protected `meta/` files, `.claude/`, `docs/ARCHITECT-HANDBOOK.md` or
    `templates/`. No unit commit touches `meta/plan.md` or
    `meta/CHECKPOINT.md`.
12. hands: two stale git worktrees from earlier sessions were present and
    left untouched: `/tmp/rv13-8b9f9be` (8b9f9be, with
    `/tmp/rv13-8b9f9be-check.log`, apparently an earlier, unfinished review
    attempt of this mission) and `/tmp/u5/parent` (10142a7). Nothing in hands
    cleans up after an aborted aux session.
13. hands: HF-008 held. With `./scripts/check` near 15 minutes, the nine
    per-commit sub-agents had to run one at a time, about 3 h 15 min in all.
14. hands: HF-007 held. For the tests-only commits 42cea0f and 68bee5f,
    protocol step 2 is vacuous. Their sub-agents instead ran G1.3 at the
    parent assertion (FAIL) and the commit body's five gate mutations (each
    FAIL).
15. hands: 8bae433 has the prefix `journal:`. The protocol's skip list names
    only `plan:`, `meta:` and `review:`. It changes only `meta/journal.md` and
    was read for forbidden edits only.

## Per-commit verdicts

### 6372322 (U1)

```
sha 6372322 (U1, REVIEW-12 should-fix 1-4, decision 101 (a)-(f)):
1 unit/sections: U1 of mission 13. It claims DESIGN §12.1, 12.2, 12.4 and 13.2, decision 101 of m13 (plus 94, 95, 98 of m12), and I-1, I-8. It needs no container: `discotrade.sandbox.container` does not exist at this commit, so I skipped the image check and no image was built.
2 test-first: PASS. With the 4 src files put back to the parent: 13 failed (the 12 error-text cases, the name-tuple test and both fd-1 process tests). The static source-order test and both reverse-sample harness-error cases ([drop], [ascending]) also failed. The KeyboardInterrupt case escaped the runner and aborted the pytest session, so that is red too. Four mutations all went red: `type(exc).__name__` back (4 failed), result on fd 1 without the dup2 (3 failed), attributes ordered by chain start (1 failed), `called` check removed (2 failed). After restoring, `git status` was clean.
3 ./scripts/check: "1892 passed, 121 deselected in 588.01s", "config check: ok, 168 unverified values", "check: green", exit 0, 589 s wall.
4 design/invariants: PASS. (a) names come only from fixed identity tuples, never a message or repr. (b) fd 1 is copied to a private descriptor and pointed at fd 2 before the text loads; empty output gives dry_run/no_result. (c) BaseException is caught at load and at a call. (d) attributes are ordered by end position minus the name's UTF-8 length. (e) the called bars must equal the sample, per instrument, descending, else ValidationError. (f) the helper also matches 8 digits; 159 tests passed in reverse order, and three -k subsets passed alone. No network, secret or wall clock in the added code; no market name in src/; no new dependency; no state written in the repo.
5 forbidden edits: PASS. None of the 12 files is under DESIGN, SPEC, PLAYBOOK, meta/, .claude, docs/, templates, config/, tests/gates or tests/fixtures/config. The body lists all 12 files and does not claim more than the tests prove.
6 NOT proven: the container path (no container code at this commit); a text reaching the private descriptor by its number; a whole-number price in an error text; the check covers only the texts the tests produce. I re-ran only 3 of the 21 -k runs.
should-fix-candidate, src/discotrade/sandbox/runner.py:190 and :264-267: `check()` calls `float(value)` outside any catch-all. Past the static check, a float subclass whose `__float__` raises escapes `execute`; I confirmed this in-process (a RuntimeError escaped). Through the subprocess backend this should end as limit/abnormal_exit rather than dry_run/raised, but I did not run it. No text leaks into the error. The static check refuses `def __float__` (underscore rule), so it only matters past the static check. It is outside the letter of 101 (c), which covers raises "while loading or by a call", and the gap predates this commit.
nit, runner.py:92: `BUILTIN_EXCEPTIONS` leaves out the Warning family, ExceptionGroup, BaseExceptionGroup and EncodingWarning. These are named "an exception", which is safe but does not match 101 (a)'s "the exception classes of Python's builtins".
Cleanup: worktree removed, no discotrade container left. Two other worktrees (/tmp/rv13-8b9f9be, /tmp/u5/parent) were not mine and I left them alone.
```

### c702fc4 (U2)

```
sha c702fc4 (U2: container backend, its image and `discotrade sandbox build`):
1. Unit/sections: mission 13 U2. Implements decision 102 (a)-(g), also 47, 95, 96, 97 (a), 98 (c); DESIGN §12.4, §3, §18.1; I-7, I-11, I-13, I-14; REVIEW-12 notes 5 and 6.
2. Test-first: PASS. With the parent's non-test files put back and the new files deleted, `test_sandbox_container.py` fails at collection (ImportError, counted as red) and `test_sandbox_process.py` + `test_offline.py` give 10 failed, 39 passed. Restored, `git status` clean. All three mutations went red: removing `--network none` failed 2 tests (options and network probe); passing the parent env to the container (`--env` per name plus `os.environ` to Popen) failed the fake-key test; skipping removal after a wall-clock kill made the endless-loop test find the container left. The fixture teardown then removed it, so none remained.
3. `./scripts/check`: `1930 passed, 121 deselected in 642.69s (0:10:42)` … `config check: ok, 168 unverified values` / `check: green`, 644 s wall. Image `discotrade-sandbox:20fa1f2225a3` was already present locally, and the container tests ran with none skipped (`-m container`: 14 passed, 17 deselected). `discotrade sandbox build` printed "present, nothing built" and the tag.
4. Design/invariants: PASS.
   - (a) runtime is `[sandbox] runtime` or the first of docker/podman on PATH; none found raises SandboxUnavailable.
   - (b) every option is built in one function, `run_command`: network none, read-only root, tmpfs, user, cap-drop, no-new-privileges, pids, memory = memory-swap, cpus, one read-only mount, a chosen name. Env is `CONTAINER_ENV` only. Output is capped. `rm --force` runs in a `finally`.
   - (c) function objects are refused and `enforces_call_limits=True`.
   - (d) the run.toml keys are only added; config.py still refuses unknown keys.
   - (e) base image pinned by digest at 3.14. numpy 2.5.4 and pandas 3.0.6 hashes match uv.lock's cp314 wheels. No pyarrow/httpx. Tag = 12 hex of sha256 over the inputs.
   - (f)/(g) container.py is in SUBPROCESS_FILES, the `container` marker is registered, and the skip names `sandbox build`.
   - Invariants: no test builds or pulls (`--pull never`; the build test is container-marked, so it skips when the image is absent). No market names in src (I-9). No new dependency; pyproject.toml and uv.lock are untouched. The monotonic deadline only decides kills (I-12). Job dirs go to a temp scratch dir (I-14).
5. Forbidden edits: PASS. No protected or frozen file is touched. The body lists all 13 files and gives the base digest, numpy/pandas beside uv.lock, the tag and the runtime version line.
6. NOT proven: Podman (only Docker 29.1.3 was used). The arm64 wheels in the image. The image build itself (it fetches from the network, so it was not run). DISCOTRADE_GATE=1 with no runtime, beyond the scratch test.
- should-fix-candidate: `src/discotrade/sandbox/container.py:349` — if `remove()` raises (e.g. `TimeoutExpired` after 120 s while the daemon is stuck), the `finally` block skips `_end(proc)`. The docker client process is then left unreaped, and so is the container.
- note for U3: `container.py:383` `_readable` chmods every file under whatever `input_dir` it is given; harmless for U2's temp job dirs, but it must never be pointed at the state directory.
```

### 0823a2d (U3)

```
sha 0823a2d (U3, the probe, `sandbox selftest` and `doctor --live sandbox`):
1. Unit and sections: mission 13 U3. It cites decision 103 (2026-10-14-m13), decisions 15 and 19 (2026-10-12), 95 (a) (m12), DESIGN §12.4, §18.3 G2.3 and §19.3 L5, and I-11, I-12.
2. Test-first: PASS.
   - Parent code restored and probe.py deleted: test_sandbox_probe.py fails at collection (ImportError: `Expected`), which counts as red. The doctor L5 test and the two image-input/tag tests fail (3 failed, 41 passed). The reverted tag 20fa1f2225a3 exists locally, so the other container tests ran rather than skipped. Restored, and `git status` was clean.
   - Mutation 1, run_command without `--read-only`: container.py is not an image input (the tag stayed edeee6d2120e). Both container tests went red: 'EACCES' != 'EROFS', and the self-test reported 3 of 15 failed. The brief's "a create under / succeeds" does not hold, because the user is non-root. The body says so and judges by errno instead, which is sound.
   - Mutation 2, build_job with the first real T bar added: red. The probe test failed `913 == 433 + 479` and selftest exited 1. Both mutations were reverted.
3. ./scripts/check: "1960 passed, 121 deselected in 731.96s (0:12:11)", "config check: ok, 168 unverified values", "check: green". Wall time 733 s. The image edeee6d2120e was present, so I did not build. Container tests ran: 0 skipped.
4. Design and invariants: PASS.
   - 103 (a): the probe is stdlib only (ast test) and an image input. It starts through run_program, so with run_command's options.
   - 103 (a) report contents: it reports routes, interfaces, the TEST-NET-1 192.0.2.1:9 connect with a 1 s timeout, creates under / /usr /home /job /tmp, uid/gid and CapEff, and per-instrument counts.
   - 103 (b): `judge` runs in the harness, and 15 hand-written wrong reports each fail exactly their own finding.
   - 103 (c) and (d): selftest builds the W job of decision 19's D, prints PASS/FAIL lines, and exits 1 naming no runtime or no image, checked before anything starts. `doctor --live sandbox` is wired, with an empty-PATH test.
   - "No bar after W": `latest_open` is always None on a real mount, which carries no ts. So in the container test the claim rests on counts only, but those counts are compared with a count taken independently from BarStore (W plus context, with `after > 0` asserted). selftest/L5 has no such independent count (see the should-fix below).
   - Invariants: I-12 holds (the clock is `ctx.clock.now()`; only `time.monotonic` is used, for the deadline). I-9 holds (no market names under src/). I-14 holds (scratch goes under tempfile and is removed). No new dependency. No container left (only ntfy).
5. Forbidden edits: PASS. Only the 8 listed files changed. The body names the three changed test assertions and gives decision 103 as the reason.
6. NOT proven: the body's 3-of-3 green runs (I ran check once). L5 on the real server.

- should-fix-candidate, src/discotrade/sandbox/container.py `judge`/`expected_mount` (~l.531, ~l.616): in selftest/L5 the mount count is compared with `len(ji.bars)` from the very job under test. A write_job that mounts different rows with the same count would pass. The "after W" check is really the harness's own job `ts` against `w_end`, not something the probe saw. An independent W-plus-context count from the store, as the test does, would close this.
- Nothing blocker-grade found. The worktree is removed; the stale worktrees /tmp/rv13-8b9f9be and /tmp/u5/parent were not touched.
```

### bb27c90 (U5)

```
sha bb27c90 (U5, approaches in the day loop behind the sandbox):
1 unit/sections: mission 13 unit U5, decision 105 (with 23, 44, 48, 49, 63, 72, 80). It claims DESIGN §12.4, §16.1 step 2, §16.4, §9.4 and I-6, I-7, I-12. It touches six src files, tests/test_daily_sandbox.py (new), tests/test_daily.py and FINDINGS.md (D-011, D-012). The body lists every file.
2 test-first: PASS. With the parent's src, test_daily_sandbox.py fails at import (SandboxChoiceError is missing) and the changed test_daily contract-failure test fails (1 failed). After the restore, `git status` was clean. Mutation 1 (loader called again in subject_rows): red, "the decision-21 loader was called on the day loop's path". Mutation 2 (limit raises JournalError): red, "run-day: FAIL: limit [wall_clock]...". Mutation 3 (refusal disabled): 4 of the 5 "-k refuse" tests went red; the 5th is the source-refusal test, which does not cover this mutation. The body says "the 5 refusal tests go red"; I saw 4, which is not a defect.
3 ./scripts/check: last lines "config check: ok, 168 unverified values" and "check: green", with "1978 passed, 121 deselected in 953.11s (0:15:53)". Wall time 955 s at load about 1.6, above HF-006's 15 minutes (already in D-012). The image edeee6d2120e was present and no test was skipped, so the container tests ran, U5's included. No container or process was left behind.
4 design/invariants: PASS. (a) one positions job per approach and day, with frozen source, fixed params, window plus cap-1 context, and score() with decision 49's carry; the 30-day diff is in the body. (b) choose_backend and --sandbox on all three commands; the refusal exits 2 naming DESIGN 12.4 before the state is read. (c) a job error becomes ApproachFailure and the approach retires with "failure: <text>"; a harness error becomes JournalError before any write; call_ms is ignored (I-12). (e) the fork server imports only runner (numpy, pandas, indicators) and never runs a text; it forks a fresh child per job, which sets setsid and the CPU/AS/CORE limits in itself. (f) the audit passes as the body states; return_readers.toml is unchanged. I-6: job scratch sits in a TemporaryDirectory and the server writes nothing to the state. I-7: the process backend's repository-source check stays on the day path, and a foreign source fails the day (tested). The test_daily assertion change cites 105 (c) in the body.
5 forbidden edits: PASS. tests/gates/, frozen config and the meta files under control are untouched; FINDINGS.md only gains D-011 and D-012, which O-19 and O-20 later closed.
6 NOT proven: fork-safety of the server's children (pyarrow's jemalloc thread); the projected G1.3 time of about 812 s; a container day loop on a non-synthetic track. The 30-day byte-for-byte comparison and the speed figures are the builder's own; I did not re-run them.
should-fix-candidate: src/discotrade/sandbox/process.py:375 with :233. If the child's output closes at the deadline, `server.wait(max(0.0, ...))` calls `settimeout(0.0)`, which makes the socket non-blocking. `recv` then raises BlockingIOError (checked: it is an OSError but not a TimeoutError). So it skips the TimeoutError branch, is caught at :381 and becomes SandboxUnavailable, which fails the whole day. A job that should finish or retire on a wall-clock limit instead fails the day (a narrow race). Fix: clamp the timeout to a small positive value, or treat BlockingIOError as TimeoutError.
```

### ad1b588 (U4)

```
sha ad1b588 (U4, the rejection suite under tests/fixtures/rejected/):
1. Unit and sections: U4 of mission 13, decision 104 (a), (b), (d) as narrowed by O-22 items 1-2 (104 (c) dropped), plus decisions 94, 98, 101 (f), 102; DESIGN §12.5, §12.1, §12.2, §12.4; I-7, I-14.
2. Test-first: PASS. With journal.py and process.py put back to the parent, 2 tests failed and 65 passed: `test_a_text_of_the_rejection_suite_is_refused...` failed for both fork_server=False and True ("DID NOT RAISE SandboxRefused"). Restored, tree clean. Mutation: I turned off the underscore rule in static.py:114 and the suite went red (3 failed, 37 passed). The failures were the static-check test, then `__import__` and the attribute walk, which both reached `activity [min_changes_w]`. This matches the body. Reverted, tree clean.
3. ./scripts/check: `=============== 2020 passed, 121 deselected in 937.31s (0:15:37) ===============` … `config check: ok, 168 unverified values` / `check: green`. Wall time 939 s, above the 15-minute line (already recorded as D-012). 0 skipped: the image edeee6d2120e was present, so the container tests ran.
4. Design and invariants: PASS. Checked and true: 27 §12.5 entries plus REVIEW-12's 2 held as literals; manifest has only file/entry/stage/rule and a test forbids `containment`; static texts are just the construct and return 0; the 4 run-time texts that exist in strategies/ are reused (slow_call.py imports `time`, so a new slow text is justified; its loop takes about 2 s on the host, 4 times the 500 ms limit); every 104 (b) check and the 101 (f) check are tested and passed. No stage looks wrong. Note that changes_bars_in_place.py is rejected only because it is flat, which O-22 allows, so nothing detects the in-place change itself. I-7: the in-process backend refuses source texts, the decision-21 loader only takes reference/, and the subprocess backend now refuses rejected/. I-9 and I-14 hold. journal.py: the change adds an optional `exclude` to `trusted_hashes`. Its default is unchanged, its only caller is process.py, and it is harmless. It is not strictly needed (the filter could live in process.py), and the body lists it without saying it falls outside U4's allowed files.
5. Forbidden edits / file list: PASS for forbidden paths (none touched). The file list is complete, but the body says "24 validation fixtures" when there are 25 .py files (26 entries with manifest.toml; the table's 29 rows minus 4 strategies/ rows is 25). 25 is right.
6. NOT proven: the body's count of "18 containers"; its three earlier check times; the slow-function timing margin on other machines.
- should-fix-candidate (commit body): "24 validation fixtures" should be 25.
- should-fix-candidate (commit body): O-22 item 1 says run-time texts are "copied by path with its manifest entry pointing at the copy", but the manifest points at the strategies/ originals. The reason given is sound: a copy would have the same hash as its trusted original, so the subprocess backend would still accept it, against 104 (d). But the body files this under "design silent" when it actually departs from O-22; it should be a finding.
- should-fix-candidate (src/discotrade/journal.py:257): outside U4's allowed files, and the body does not say so or why.

The worktree /tmp/rvw13-ad1b588 is removed. No container or process of mine is left, and the main checkout is untouched.
```

### 8b9f9be (U5b)

```
sha 8b9f9be (U5b: one fork server per harness process, O-20):
1. Unit and sections: U5b under O-20, which replaces 105 (e)'s "one process per run". It cites DESIGN §12.4, §16.1 step 2 and §16.4, and invariants I-6, I-7, I-12. The 5 files in the body match the stat.
2. Test-first: PASS. With the parent's source the test file fails on import (`SANDBOX_RESTARTED` is missing). I added name-only shims to get past that, and both new tests went red: the replay started 3 servers where 1 was expected, and the restart test got ProcessLookupError. Restoring the commit left the tree clean. My mutation (`if restarted:` changed to `if False and restarted:` in daily.py) turned the restart test red with FileNotFoundError on health/test_synth.jsonl. I reverted it.
3. ./scripts/check: `=============== 2022 passed, 121 deselected in 879.00s (0:14:38) ===============` … `config check: ok, 168 unverified values` / `check: green`. Wall time 881 s, which is close to the 15-minute finding line. Container tests ran and none were skipped (image edeee6d2120e was present, nothing built).
4. Design and invariants: PASS, with two should-fix items. Conforms to O-20:
   - one server per process, started on the first job;
   - stopped by atexit and by close();
   - SERVER_CODE unchanged, one fresh child per job, limits set in the child;
   - a dead server is restarted on the next job, with a notice in day runs only.
   I-12 holds: the notice carries the day `d` and a detail with no wall-clock time. I-6 is a should-fix-candidate, see the first defect below. The settimeout race exists and is a should-fix-candidate, see the second defect.
5. Forbidden edits and file list: PASS. Only src/discotrade/{daily,journal}.py, src/discotrade/sandbox/{base,process}.py and tests/test_daily_sandbox.py changed. The body gives seconds per replay day at the parent (2.466 s) and at the commit (1.885 s).
6. NOT proven by me:
   - the speed numbers and the byte-identical gate replay (I did not re-run them);
   - that atexit stops the server on every way the process ends;
   - restart after a server dies in the middle of a job;
   - the race below (found by reading the code, not triggered).

Concrete defects:
- should-fix-candidate, src/discotrade/daily.py:342-350 (I-6). The `sandbox_restarted` notice is appended even when an already-journaled day is re-run. A fresh process starts with `_LOST` False, so this only happens if the server dies within the same process. Even so, it conflicts with the literal text of I-6 ("writes nothing new") and with G4.3's "re-running a finished day writes nothing". §16.2 only exempts the health log on failed days. The body treats this as a choice where the design is silent, but I-6 is not silent. Either skip the notice for an already-journaled day or file a D-### finding.
- should-fix-candidate, src/discotrade/sandbox/process.py:469 (with :254, :475). `server.wait(max(0.0, deadline - time.monotonic()))` can pass `settimeout(0.0)`. This happens when `_read` saw EOF just before the deadline. A 0.0 timeout makes the socket non-blocking, so `recv` raises BlockingIOError rather than TimeoutError. The inner `except TimeoutError` (:470) misses it, and the outer `except OSError` (:475) discards the server and raises SandboxUnavailable, which fails the day. What should have been a wall-clock limit result becomes a harness error, and the next job also logs a restart notice. The window is narrow. The bug predates this commit: it came in with bb27c90 (parent line 387), and the same pattern on the subprocess path at :443 is safe because Popen.wait raises TimeoutExpired. A fix is to treat a remaining time of 0 or less as a breach, or to clamp it to a small positive value.

Cleanup: I removed /tmp/rvw13-8b9f9be and left no fork server or docker container running. I did not touch /tmp/rv13-8b9f9be or /tmp/u5/parent, and the main checkout is clean.
```

### 8b923fd (U5c)

```
sha 8b923fd (U5c: the probe's limit findings and the G2.5 limit fixtures, O-22):
1. Unit and sections: U5c, under O-22 items 3 and 4 and "For the builder" step 6; decisions 102 (b), 103 and 106 of 2026-10-14-m13; DESIGN §12.4, §18.1, §18.3 (G2.3, G2.5), §19.3 (L5); I-7, I-11, I-12, I-14.
2. Test-first: PASS.
   - With probe.py, container.py and scripts/gate put back to the parent, the tag became edeee6d2120e. That image is present, so the container tests ran.
   - Red on the parent: test_sandbox_probe.py fails at collection (`Required` not importable), the output test fails (16720 > 4096), and the gate-script test fails (only four items). The wall and memory tests pass on the parent, as expected.
   - Removing `--pids-limit` turns 2 probe tests red ("FAIL limits.pids: pids.max '7856', required at most 64", "selftest: FAIL, 1 of 19").
   - Setting the deadline to `max(wall_seconds, 1200)` turns the wall test red (the job returned ok).
   - The output-cap fix is at container.py:377 (bounded `os.read`) and the `del out[cap:]` line. Reverting only that turns the output test red (16706 > 4096).
   - Each restore left the tree clean.
3. ./scripts/check: last lines `config check: ok, 168 unverified values` and `check: green`. Wall time 872 s. Container tests ran (tag 1edd0f8558cb present, "present, nothing built"). I did not capture the pytest pass/skip count line.
4. Design and invariants: PASS.
   - Item 3: the probe only reads pids.max, memory.max, memory.swap.max, cpu.max and RLIMIT_CPU. `judge` compares them with `required_limits(run.toml)`; a value that is missing, `max` or wider fails, and swap must be 0. selftest and `doctor --live sandbox` both call `container.selftest`.
   - Item 4: the three fixtures are bounded by constants in their own text, and a test checks those constants. The short limits come from a run.toml copied under tmp. All four O-22 assertions are present, each fixture also runs under production limits, and scripts/gate counts five M2 items.
   - Subprocess backend: it accepts the new fixtures by hash, like any file under tests/fixtures/. This is harmless. The `process` backend only runs synthetic sources whose text equals a repository file, and nothing on a gate or day path references these files (grep finds them only in test_sandbox_limits.py). wall_wait.py's `import time` is refused by the static check anyway.
   - I-12: `time.monotonic` is used only in the backend's deadline and in a test assertion. I-9: no market names added under src. I-14: everything runs under pytest tmp. I-11: no network or secret used.
5. Forbidden edits and file list: PASS. The 10 files in `--stat` match the body's list. Nothing under tests/gates, DESIGN, meta/decisions, plan or CHECKPOINT changed, and no config value changed. The scripts/gate change is only the 4 to 5 count. D-013 is filed for the 910 s run.
6. NOT proven:
   - I ran `./scripts/check` once, not three times. The body's 877/910/881 s and "2044 passed" are its own numbers.
   - The CLI selftest needs a state directory, so I saw selftest's limit findings only through its tests. `doctor --live sandbox` I checked by code only, not by running it.
   - KILL_GRACE (5 s) is the test's own bound; the design names no grace.

No blocker-candidate or should-fix-candidate defects. The worktree is removed, no container of mine remains (only ntfy), and the stale worktrees were not touched.
```

### 42cea0f (U6a)

```
sha 42cea0f (U6a, "gate: G1.3's retire reasons become the sandbox's text (O-19)"):
1. Unit/sections: mission 13 unit U6, first commit, under O-19 (decisions-2026-10-15-owner), decision 105 (c) and 101 (a) (decisions-2026-10-14-m13), and DESIGN §18.3 G1.3. The body names all of them and lists the one file.
2. Test-first: reverting product code is vacuous because the commit changes no non-test file. With the test at its parent version: `1 failed, 9 passed in 618.15s (0:10:18)` / `G1.3 FAIL 1 failed, 9 passed in 618.15s (0:10:18)` / `gate M1 G1.3: FAIL` (619 s). It failed at index 5, because the ledger now holds the sandbox's `dry_run [out_of_range] ... window bar 18 (parameter set 0)` where the old test expected `position on SYNA at bar ts 2019-06-13 16:00:00+00:00 returned 2.0`. At the commit: `G1.3 PASS 10 passed in 606.57s (0:10:06)` / `gate M1 G1.3: PASS` (607 s).
3. ./scripts/check: `config check: ok, 168 unverified values` / `check: green`, exit 0, wall time 909 s.
4. Design/invariants: PASS.
   - Exactly the two 2019-06-13 reasons changed, to O-19's literal texts (bar 18 for BREAK12, bar 19 for BREAK13).
   - The date, the two approaches, from/to (live to retired) and the exact-literal list comparison are unchanged.
   - The new texts hold no date, symbol, price or returned value; "[-1, 1]" is the contract bound and the bar number is a window index (101 (a), §13.2).
   - The body quotes O-19 in full.
   - Note only: the helper `fail()` at line 117 is now unused and stays in place, as the body says.
5. Forbidden edits: PASS. Only `tests/gates/test_g1_3_lifecycle.py` changed. Editing an existing gate file is allowed here by O-19 alone.
6. NOT proven: no other gate item was run, and `./scripts/check` ran once, not three times. The worktree is removed, the main checkout is unchanged, and the only running container is `ntfy`.

Observation, not a defect of this commit: G1.3 took 606–618 s at both versions, just over O-3's 10-minute-per-item target. O-20 says that is measured at U6 and filed as a finding with the times if it holds.

No blocker-candidate or should-fix-candidate.
```

### 68bee5f (U6b)

```
sha 68bee5f (U6b, gate: the M2 gate tests G2.1 to G2.5):
1 Unit U6, second commit. It cites decision 106 (a)-(e), 104 (b), 103 (b), 101 (f), O-22 items 2-4, and DESIGN 18.2 and 18.3 M2.
2 Test-first: this commit changes no non-test file, so the revert step is vacuous. Image 1edd0f8558cb was present ("present, nothing built"). I reproduced all five mutations, each reverted afterwards with `git status` clean: (a) manifest "an endless loop" dry_run->activity: `G2.1 FAIL 1 failed, 35 passed in 49.63s`. (b) correlation.py:86 `r` in place of `abs(r)`: `G2.2 FAIL 1 failed, 2 passed in 31.73s`. (c) `_window_bars` kept the first bar after W: `G2.3 FAIL 3 failed, 5 passed in 5.88s`. (d) grid fixed `first_greatest` of the plain Sharpe: `G2.4 FAIL 1 failed, 8 passed in 41.45s`. (e) container.py:362 deadline 3600.0 in place of wall_seconds: `G2.5 FAIL 1 failed, 4 passed in 18.47s`. Unmutated `./scripts/gate M2`: G2.1-G2.5 PASS, `gate M2: PASS`, 2m36s.
3 `./scripts/check`: last lines `config check: ok, 168 unverified values` / `check: green`, wall time 14m31.6s.
4 G2.1 PASS: all 29 entries (the 27 of §12.5 as a literal plus REVIEW-12's two) are rejected at their manifest stage and rule. Static texts start no container and run-time texts start at least one. Error texts pass 101 (f), state bytes, HEAD and the sentinel tree are unchanged, no ledger or trials file appears, no container is left, and changes_30 then passes. Shorter limits apply only to the endless loop and memory bomb, and the file says so. G2.2 PASS: both correlations are computed in the test, the flipped one is below -corr_max, and the error names the approach id. G2.3 PASS: network, EROFS, non-root user with no capabilities, mount counts against the store (which does hold later bars), and pids, memory with swap 0, cpu and RLIMIT_CPU equal to production run.toml. judge and selftest pass. G2.4 PASS: the adjusted Sharpe is computed by hand, the plain one would pick another combination, and each of the five stages fails, stops there and gives a clean text. G2.5 PASS: wall within limit plus grace, output cap with the read no longer than the cap, memory limit or dry_run, each also run under production limits, and pids/CPU left to G2.3 as recorded. Thresholds are production, every seed and date is in the test file, and every file is marked gate, gate_m2 and container. m2_harness.py holds no seed, date or item assertion. The commit adds no special case to src/.
5 Forbidden edits PASS: six files added under tests/gates/, no existing gates file changed, no frozen config or protected file touched. Deviation: tests/test_gate_script.py is modified although the brief says the commit carries only the new gate files. It was unavoidable: the old test asserts that no `test_g2_*.py` exists and runs `gate M2` expecting FAIL, so `./scripts/check` goes red without the change. The new version keeps the same assertions on M3/G3.2 and moves the five-item count to `ITEMS["M2"] == 5`. That is slightly weaker than checking the printed G2.1..G2.5 lines, but acceptable.
6 Not proven: results hold only on this machine's docker and image 1edd0f8558cb. G2.3 checks the mount from inside by bar counts only, so a slice shifted by one bar with its length unchanged would pass that test's own count assertion; only judge()'s harness-side check of the last bar's open time would catch it. The rejection suite is a floor, not every attack.
should-fix-candidate: tests/gates/test_g2_3_probe.py:202 compares counts only, not values or ends. Comparing, for example, the mount's last close with the store's last W bar would actually prove "no later bar" from inside, as 106 (d)'s "compare with the store" asks.
should-fix-candidate (minor): tests/gates/test_g2_5_limits.py:77 allows the harness's memory to grow by up to 64 MiB, where O-22 says "unchanged". The tolerance is justified in the file, but it is still a tolerance.
Cleanup: worktree removed, no discotrade container left, main checkout untouched and clean.
```
