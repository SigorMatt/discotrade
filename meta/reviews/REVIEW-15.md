# REVIEW-15 — cold review of mission 15 (roadmap step S3.2a)

Base 7249059 (`review: mission 14`, the last `review:` commit); tip 86d56bd
(`origin/main`). Commits in range: 301a5c7 (kit), ccaf429 (U0 `plan:`), unit
commits e404e00 (U1), aeed087 (U2), d9acfcd (U3), 0260f0c (U4), 5f5c5c5 (U5),
41b2670 (U6), the `meta:` checkpoint commits 624315e, 9623799, 9ddce2a, d0ecf80,
bfe4e89, 6259365, 86d56bd, and d5dfa02 (`report:`, the final report and two
FINDINGS lines). One sub-agent per unit commit, each in its own worktree,
run one after another (HF-012). Container runtime docker; image
discotrade-sandbox:3b7d75c39621 present at every commit.

## Gate

not a closing mission

(The brief, decision 118, closes no milestone. The regression runs of gate M0,
M2 and M1 G1.1 to G1.4 are the builder's, recorded in FINAL-REPORT-15 at
6259365; this review did not run them again.)

## Blockers

1. A claim the disk contradicts (decision 122 (c)). The U3 body
   (d9acfcd, "openai_compat_from_env (the one place NEBIUS_API_KEY is
   read)"), the docstrings `src/discotrade/workers/providers.py:13` and `:196`
   ("here and nowhere else") and FINAL-REPORT-15's table ("`openai_compat_from_env`
   the one reader of `NEBIUS_API_KEY`") all say that one function reads the key.
   But `src/discotrade/doctor.py:235` reads `os.environ.get(KEY_ENV, "")` itself,
   in the same commit. Decision 122 (c) says the key is read "by the code that
   builds the provider, never by the provider's callers", and the doctor is a
   caller. The value is only tested for being empty and goes nowhere, so I-13
   holds. Even so, the claim is false as written, and the doctor sidesteps the
   single reader instead of using it. Fix: give `providers.py` a presence helper,
   as `sources/vendor.py:77` does for the vendor key, or drop the pre-check and
   rely on `openai_compat_from_env`'s refusal, which also makes no request.
   Then correct the claim.

## Should-fix

1. `doctor --live workers` was written in U3, before U4, and U4 did not bring
   it in line. `src/discotrade/doctor.py:62` hardcodes `WORKERS_TIMEOUT_SECONDS =
   300.0`. That duplicates `config/run.toml`'s `[workers] request_timeout_seconds`,
   which `config.py:881` loads and nothing in `doctor.py` reads, and its own
   comment says it waits for U4. `doctor.py:238-243` also parses `models.toml`
   with raw `tomllib` rather than `config.load_models`. So L3 skips the refusals
   decision 123 (c) defines (unknown key, bad fallback, duplicate id, empty
   pool), and could list a pool `config check` would refuse. Read both from the
   loaded configuration.
2. The U2 cache key has two parts no test covers. `src/discotrade/sources/synth.py:213`
   keys on `(src, trusted_from, cal, bar_seconds)`. Decision 121 (a) requires
   each part so that "a changed record generates again". With the calendar
   record and the bar length both dropped from the key, the suite still passed
   (2103 passed, 0 failed, without gate and container tests). Only the seed and
   `trusted_from` are tested (`tests/test_synth_cache.py`). The code is right by
   inspection. FINAL-REPORT-15's acceptance line "a changed record generates
   again. Met (U2)" holds by test only for those two parts; its "What the tests
   prove" states that narrower scope correctly. Add a changed-calendar and a
   changed-bar-length test in a copied configuration.

## Notes

1. U4, `src/discotrade/workers/pool.py:106`: a `model_skipped` notice is raised
   even when the fallback replaces the model (detail `replaced: true`).
   Decision 124 (a) names the notice only for a dropped model; DESIGN §13.6
   says "in favour of its fallback, with a health notice". The body states the
   choice. Consistent with the design; the architect may confirm.
2. U5: the weak flag and the registry count only lifecycle rows dated before
   D. A row to `dormant` written by D's own lifecycle step does not make a cell
   weak until D+1. The design does not say which reading holds; step S3.2b
   wires the coordinator into the day and should settle it. The weak flag at
   paper day 0 (a row dated before the approach's first paper row) is untested.
3. U3: `ProviderError` is raised `from None`, but the httpx exception stays in
   `__context__`, where the key can be reached through `.request.headers`. It
   is suppressed and never printed, so it is not a leak today; clearing the
   context would harden I-13. `subprocess.run(timeout=)` kills the `claude`
   child but not any grandchild it starts.
4. U6: only the invalid-then-valid test checks the full list of retry
   messages; the duplicate test checks only the error text. The import test
   checks direct imports only: `generate` loads `socket` and `subprocess`
   indirectly through `ledger`, `journal` and `sandbox`, as before this mission;
   `httpx` is not loaded. The `token_budget` subject (the track) and the model
   recorded on a replayed row are the builder's choices where 126 is silent,
   both stated in the body.
5. U2: the process cache has no bound (one entry per distinct record). It gave
   no speed gain (1.598 vs 1.623 s per replay day). D-013 stays open:
   `./scripts/check` took 794 to 834 s at the unit commits in this review,
   above decision 114's 12 minutes and under HF-006's 15.
6. FINAL-REPORT-15 NOT PROVEN is consistent with what the sub-agents found
   (no live provider, model or `claude`; unverified models and base URL;
   `claude` reply fields not read from a real binary; scripted token counts;
   nothing wired into `run-day`/`replay`). Add to it: decision 121's calendar
   and bar-length key parts (should-fix 2).
7. The kit commit 301a5c7, in this range, changes `meta/ROADMAP.md`,
   `meta/BACKLOG.md`, `meta/decisions/`, `KIT.md` and `meta/BUILDER-15-PROMPT.md`.
   It is the architect's kit, not a builder commit. No builder commit touches
   a forbidden file. `meta:` and `plan:` commits touch only `meta/plan.md`,
   `meta/CHECKPOINT.md`, `meta/journal.md` and `meta/findings/FINDINGS.md`
   (U0, appends only). `d5dfa02` touches only the report and two appended
   D-013 lines. `git diff 7249059 86d56bd` of `tests/gates/` and
   `tests/fixtures/rejected/` is empty. The frozen config diff is additions
   only: the new `models.toml` files, the `[workers]` tables and a new
   frozen-map entry.
8. hands: the worktrees `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still
   registered (HF-010, unchanged since REVIEW-14). This review's own worktrees
   were removed.
9. hands: `d5dfa02` again carries the prefix `report:`, which the protocol's
   skip list does not name (HF-011). I read it as a meta commit.
10. hands: HF-012 is still open. This review ran its six reviewers one after
    another, about 2.5 hours in all. The U2 reviewer returned before writing
    its report while a test run was still going (a background run despite its
    brief) and had to be resumed. The U5 reviewer ran `uv sync --all-extras` by
    mistake (locked dependencies only), then synced back to `--extra dev`
    before any test. The U1 reviewer ran `./scripts/check` twice. The protocol
    template could say "run `./scripts/check` once, in the foreground, and
    report only when every command has finished".

## Per-commit verdicts

### e404e00 (U1)

```
e404e00 (mission 15, unit U1: decision 119 (a) to (d), DESIGN §13.1, §13.3, §13.4) passes all five points; I found no defects.
1. Commit read: pass. The body names the unit and sections, lists all 7 files it changed, and the diff shows no others.
2. Test-first: pass. With the parent's parse.py and registry.py restored, 3 tests fail: the new parse test, the new registry test, and the changed test_workers_prompt brief-cap test. With the commit's code back, 78 pass. I counted tests/conftest.py as test support, not product code, so it stayed as committed. Each "seen to fail" change goes red: the fence line taken as the description (parent parse.py) and stripping only before the cut (parent sanitize) were covered in that run. Making the roll-record condition in profile.py:167 False fails both profile cases. I also checked a fourth change: skipping fence lines and trying the next line fails the parse test. Every change was reverted.
3. Check: pass. `uv run discotrade sandbox build` said "sandbox build: present, nothing built" (discotrade-sandbox:3b7d75c39621), so the container tests ran. `./scripts/check` ended `=============== 2156 passed, 182 deselected in 794.23s (0:13:14) ===============` then `check: green`, wall time 795 s. That was my second run; the first was also green at 795 s, but I hadn't captured its pytest line.
4. Design conformance: pass. parse.py:104-107 does exactly what 119 (a) says: it takes the first non-empty line after the last block's closing fence and tests lstrip(" \t").startswith("```") on the raw line, before sanitizing; on a match it returns no_description and never tries the next line. registry.py:65 strips after the cut. The only changed existing assertion is test_workers_prompt (40 → 39 characters); 119 (b) allows it and the body says so. 119 (d): mixed_ran_template now sets GIT_ALLOW_PROTOCOL=file; it and synth_committed_template are the only templates that run init-state or run-day. The diff adds no network use, secret, market or venue name, number outside config, wall clock, in-repo state or dependency.
5. Forbidden edits: pass. The commit touches only those 7 files. There is no change under config/, tests/fixtures/config, config_frozen.json, tests/gates or tests/fixtures/rejected, and pyproject.toml and uv.lock are unchanged.
6. Cleanup: done. /tmp/rv15-e404e00 is no longer in git worktree list, and the main checkout is clean. Two older worktrees from earlier reviews are still registered, /tmp/rv13-8b9f9be and /tmp/u5/parent; I left them alone (HF-010).
NOT proven: the commit's claim that check was green 3 of 3 — I ran it twice. Also, a profile.py fault that raised some other error would still turn the new profile test red only because it matches the "no roll record" message text.
```

### aeed087 (U2)

```
aeed087 (U2): acceptable, with one test-coverage defect. No test catches a cache key that leaves out the calendar record or the bar length.
1. PASS. Unit U2 claims DESIGN 5.5, 17.1 and 18.1, I-6, decision 121, D-013 and 80 (d). conftest.py counts as test support, but the parent has no clear_cache, so with the parent's synth.py all 4 tests error at setup. I then added a no-op clear_cache to the parent's synth.py: the day-by-day span test and the equal-record test go red (the series is rebuilt from trusted_from), while the seed and trusted_from tests pass. That is acceptable, because the parent cached per source. The body's "All four failed at the parent" holds only through that AttributeError.
2. Mutations. Leaving the seed out turned 2 tests red (the brief's "seen to fail" is confirmed) and leaving trusted_from out turned 1 red. Leaving out both the calendar record and the bar length together ran a single combined mutation: 2103 passed, 0 failed (-m "not gate and not network and not live and not container", 682 s). Defect: no test catches either part. The key is at src/discotrade/sources/synth.py:213 and the tests are in tests/test_synth_cache.py. The gate and container tests were not run under that mutation.
3. PASS. The sandbox image was already present (discotrade-sandbox:3b7d75c39621), so the container tests ran. ./scripts/check (one run, wall 799 s) ended `config check: ok, 168 unverified values` / `check: green`. I did not keep the pytest pass/skip line; I lost it to my output filter.
4. PASS. The key (src, trusted_from, cal, bar_seconds) covers everything _generate and expected_bars read: the origin comes from trusted_from, and symbol and tick_size are applied outside the cache. A cached series cannot be served for a request it does not match: a shorter request is served from a prefix, a longer one extends it, and expected_bars is half-open and aligned to fixed times, so the extension leaves no gap and repeats no bar. Callers cannot corrupt the cache: returned frames pass through reset_index, .copy() or column replacement, and dropped is only read. The cache is unbounded (note only). I-6, I-9, I-10, I-11, I-12 and I-14 hold, and there is no new dependency. The body gives per-replay-day seconds (1.598 at parent vs 1.623 here) and check times (791 vs 801/798/807), lists every file, and no existing assertion moved.
5. PASS. The only files touched are synth.py, conftest.py, the new test file and FINDINGS.md. The FINDINGS.md change is a single appended D-013 line, with 0 lines removed. No forbidden path or frozen config was touched.
6. The worktree was removed after restoring its tree. The main checkout is clean, and git worktree list shows no rv15-aeed087.
NOT proven: byte identity of stored files beyond the 15-day span in the test (I did not rerun the 30-day replay diff); the body's replay timings; the calendar and bar-length mutations one at a time (only together, and not against the gate or container tests).
```

### d9acfcd (U3)

```
Commit d9acfcd (mission 15 U3) passes all five points and I found no blocking defect.
1. Unit and claims: PASS. The body cites decision 122, DESIGN 13.5, 19.3 L3, I-11 and I-13, and lists all 6 changed files. It records the claude flags (--bare -p --output-format json --max-turns 1 --tools "" --permission-mode dontAsk --model <m>) and where each came from: claude --help 2.1.300 for all but --max-turns, which came from SPEC 17.
2. Test-first: PASS. With the parent's cli.py/doctor.py and no providers.py, test_workers_providers.py fails to collect (ImportError). test_doctor.py + test_offline.py give `3 failed, 35 passed, 6 errors`. The test_offline failure comes from the test-side SUBPROCESS_FILES entry, which I accept as part of the test. The three seen-to-fail items, each made and reverted, matched the body: key in Completion.raw 1 red, cursor not advanced 2 red, --tools "" dropped 5 red. Dropping --permission-mode also gives 5 red.
3. Gate: PASS. `sandbox build: present, nothing built` (image discotrade-sandbox:3b7d75c39621). ./scripts/check run once, 810 s wall: `=============== 2201 passed, 182 deselected in 808.48s (0:13:28) ===============` / `config check: ok, 168 unverified values` / `check: green`.
4. Conformance with 122 (a)-(f): PASS. Every item matches. The key sits only in httpx's client headers, which repr as [secure]. Every error uses `from None` and shows only the exception type, and the test covers DEBUG logs. The env strips NEBIUS_API_KEY and DATABENTO_API_KEY. subprocess.run(timeout=) kills the child on timeout; a grandchild would not be killed. Only providers.py under workers/ imports httpx or subprocess. I-9, I-12, I-14 hold, and there is no new dependency.
5. Forbidden edits: PASS. Nothing touched under meta/, config/, tests/gates/, tests/fixtures/, .claude/, DESIGN.md, SPEC.md or the other protected paths. My worktree is removed. The other two worktrees (/tmp/rv13-8b9f9be, /tmp/u5/parent) were already there and I left them.
Notes, none blocking. I-10: src/discotrade/doctor.py:62 hardcodes WORKERS_TIMEOUT_SECONDS = 300.0; the body discloses this and says it waits for run.toml in U4, and U4 should be checked for replacing it. I-13 hardening: at src/discotrade/workers/providers.py:146-153, the ProviderError still holds the httpx exception in __context__, so the key is reachable through .request.headers; the context is suppressed and never printed. Key read in doctor: doctor.py:235 reads NEBIUS_API_KEY itself to test whether it is set, outside openai_compat_from_env; it never uses the value.
NOT proven: the real claude reply fields (result, usage, modelUsage, is_error) and the --max-turns flag, which the body also leaves to live check L3; that no socket opens under the full suite — I only confirmed the tests use MockTransport and that the send-blocker is present.
```

### 0260f0c (U4)

```
Review of 0260f0c (U4, mission 15): ACCEPT. All five points pass, with one minor reading of decision 124 (a) noted below.
1. Unit and sections: PASS. The body names U4, decisions 123 and 124, DESIGN 13.6, 4.3, 11.3, 15.2, R-14, R-21, I-5 and I-10, and it lists all 12 changed files.
2. Test-first: PASS. With config.py and run.toml set back to the parent, and pool.py and config/models.toml removed, the tests went red: test_workers_pool and test_config failed to collect (load_models missing, models.toml missing), and 8 tests failed in test_config_check and test_config_history. I kept the fixture files, since they are test-side; test_doctor passed at the parent because its change only adapts the test. The three "seen to fail" changes, each made and reverted, each failed test_workers_pool: rotation without the cell index (wrong model), provider_error counted as a failure (extra model_removed alerts), and a removal undone on the next day ({} == {gpt: 2019-06-03}).
3. Check: PASS. The sandbox image was already present (discotrade-sandbox:3b7d75c39621), so no container test skipped. ./scripts/check ran once in 801 s: `=============== 2256 passed, 182 deselected in 800.24s (0:13:20) ===============`, `config check: ok, 173 unverified values`, `check: green`.
4. Design conformance: PASS, with one minor point. models.toml: the four records match 123 (a) and SPEC §17 exactly, and the fixture copy is byte-identical; base_url carries its own checked, source and verified = false, its checked 2026-10-16, which 123 does not fix. The R-14 cutoff dates are tested. All four refusals are tested, and so is claude_fallback = true being refused by config check. [workers] is false / 300.0 and adds lines only. pool.py follows 124 (a) to (d): rotation is (ordinal+c) mod len, with the ordinal counted from the epoch and excluding D; windows are built only from calls.jsonl rows (I-5); provider_error and budget rows are not counted; removal is for good; a cell notice re-arms only after a full window at or below the rate. fail_window and fail_rate are read from thresholds.toml, which the commit did not change; no numbers are hardcoded, there is no clock, no network import, and no new dependency. Minor reading: pool.py:106 also logs model_skipped when the fallback does replace the model; 124 (a) reads as a notice only when the model is dropped; the body says it chose this from DESIGN 13.6; a judgement call, not a defect. Retry: "a retry uses the first call's model" is not in pool.py; it holds only because model_for gives the same answer for the same day and cell; enforcing it belongs to U6. doctor.py timeout: no. doctor.py:62 still has WORKERS_TIMEOUT_SECONDS = 300.0 and does not read request_timeout_seconds from run.toml; the body says so.
5. Forbidden edits: PASS. The diff of config/, the fixture config and config_frozen.json from 7249059 is additions only. The commit touches nothing under tests/gates/, tests/fixtures/rejected/, meta/, .claude/ or the protected documents. config/HISTORY.toml was not touched, which the brief allows.
6. Worktree: /tmp/rv15-0260f0c is removed and the main checkout is clean. The /tmp/rv13-8b9f9be and /tmp/u5/parent worktrees already existed and are not mine.
NOT proven: base_url and every model cutoff stay unverified until live check L3. I did not run ./scripts/check three times, only once as asked.
```

### 5f5c5c5 (U5)

```
5f5c5c5 (U5, "coordinator: the interface, cell statuses and the scripted form"). Verdict: pass, no defects found.
1. PASS. The unit is U5 of mission 15. It implements decision 125 and DESIGN §14.1, §14.2 (scripted form only), §14.3 and §16.1 step 3, under I-8 and I-10. The body lists both files the commit touches: src/discotrade/coordinator.py and tests/test_coordinator.py.
2. PASS. Without coordinator.py, tests/test_coordinator.py fails at import; with it, 18 pass. Each change below was made, run and reverted: score field added to CellStatus: 3 fail, the property test among them; tie going to the highest cell index: 1 fails; out-of-list choice accepted: 2 fail; weak flag also true when the cell's summed paper net_1x is negative: 3 fail, the property test among them (a variant that requires both a negative return and early dormancy also fails 3); weak window off by one, as `< window` or by counting paper days `< when`: 2 fail each.
3. PASS. sandbox build: "present, nothing built", tag discotrade-sandbox:3b7d75c39621. ./scripts/check, run once: `=============== 2274 passed, 182 deselected in 799.69s (0:13:19) ===============`, `check: green`, wall time 801 s.
4. PASS. Interface and records: the protocol matches §14.1; CellStatus has exactly cell, live, free, weak; Brief, AlertPayload and RunSummary are minimal. Offered cells: those with a free slot or weak, in cell order. Weak flag: the population is the approaches live on D per lifecycle.states; paper days are rows of the paper record, which holds one row per subject and date (paper.build groups by subject and date); the rule is a row to dormant dated before D with at most weak_window_days paper days on or before it (coordinator.py:131-140); only the subject and date columns are read (:124), so no return, score, figure or trial row is read (I-8). Scripted form and fallback: the choice is fewest live, then lowest track cell index; the brief template contains no digits; a cell not offered falls back with one coordinator_fallback notice; the brief is cut by registry.sanitize at brief_max_chars. Both thresholds come from config/thresholds.toml (I-10). No offered cell gives (None, []) with no coordinator call. No clock, network, venue name or new dependency (I-9, I-11, I-12, I-14). Property test: it builds 8 approaches from always_flat.py across 4 cells, one of them dormant on D; the two states differ only in paper returns (seeds 1 and 2), lifecycle figures and trial metrics, as 125 (e) requires.
5. PASS. The commit touches only the two files above; nothing forbidden.
6. The worktree is removed; git worktree list no longer shows /tmp/rv15-5f5c5c5, and the main checkout is unchanged.
NOT proven or open: today's dormancy is ignored on day D — states and dormancy rows count only when dated before D, the same reading the registry uses (116 (b)), so a row to dormant written by D's own lifecycle step, if dated D, does not count toward weak until D+1; the design does not say. Weak at day 0 is untested: the window is counted from paper rows only, so it is unchecked when a row is dated before the approach's first paper row. uv sync side effect: an accidental `uv sync --all-extras` briefly installed extra packages into the worktree venv; it was re-synced to --extra dev before any test ran.
```

### 41b2670 (U6)

```
Review of 41b2670 (mission 15, unit U6, "workers: the day's generation, one call, storage, parse, validation, retry, budget"). Verdict: pass, no defects found.
1. Pass. The body names U6, decision 126 (with 62, 104 (d), 122 to 125), DESIGN 13.4, 13.7, 10.2, 12.2, 12.3, 16.2, R-25, and I-5, I-6, I-13. It lists all 11 changed files, matching git show --stat.
2. Pass. At the commit, 17 of 17 generate tests pass. With generate.py removed, collection fails with an ImportError (red). All four "seen to fail" changes turned the tests red, each reverted: response stored after the parse: the parse test fails; ATTEMPTS = (1, 2, 3): the duplicate and parse tests fail; stored response ignored: the stored-response test fails; budget compared with used = 0: both budget tests fail. The extra changes also failed: a different retry model (2 variants, 4 tests red), budget row with nonzero tokens (2 red), no token_budget event (2 red), duplicate mapped to invalid:correlation (1 red). Changing > to >= in the budget test also goes red, so the code compares with strictly "above".
3. Pass. discotrade sandbox build printed "sandbox build: present, nothing built" with discotrade-sandbox:3b7d75c39621. ./scripts/check, run once, gave `=============== 2291 passed, 182 deselected in 832.22s (0:13:52) ===============`, `config check: ok, 173 unverified values` and `check: green`. Wall time was 833.6 s; the commit body reported 831.8 to 834.3 s. There were 0 skipped, so the container test ran.
4. Pass on 126 (a) to (g). Call id: 'c' + sha256(...).hexdigest()[:12], 13 characters (generate.py:143); the test computes it on its own and agrees, so "cbe1f010c3ef5" is well formed. Budget: it counts the day's rows including staged ones and is checked before each call, with used + max_out > limit at generate.py:219; it writes a budget row with 0/0 tokens, raises the alert-level token_budget event, and ends the generation. Stored response: it is replayed with no call; otherwise the response is written atomically, keys sorted, before the parse and outside staging, with exactly 126 (c)'s keys; a provider error writes one row and no retry. Outcomes are invalid:parse / invalid:<stage> / duplicate / trial; the retry holds the first prompt, the first reply as the assistant's message, then the fixed text and the error, plus corr_max for a duplicate; attempt 2 uses the same model. Rows have exactly ledger.KEYS["calls"], and the candidate carries every field 126 (f) lists. No trial row is written, and no caller exists in run-day/replay. There is no clock, environment or secret read, no httpx or providers import, and no hardcoded threshold. The text sent back is §12.2's W-only text; the duplicate names a hash approach id, with no T score and no market name. Every test 126 (g) lists exists. The fixture Python blocks are asserted byte-identical to existing strategy files. The container test is marked container, runs under tmp_path, and removes its containers by name. There is no new dependency, and tests/fixtures/strategies/ and return_readers.toml are unchanged.
5. Pass. No forbidden path was touched: nothing under tests/gates, tests/fixtures/rejected, config/, meta/, DESIGN.md, SPEC.md, .claude/ or templates/.
6. Cleanup done. /tmp/rv15-41b2670 is removed and the main checkout is clean. docker ps -a shows only ntfy, which has been up 44 hours and is not from this run. The other worktrees still listed (/tmp/rv13-8b9f9be, /tmp/u5/parent) were already there.
NOT PROVEN: network imports, indirect only — importing generate pulls in socket, subprocess and discotrade.sources through ledger, journal and sandbox, which were already there before this commit; httpx is not loaded; the test checks only direct imports. Retry messages: the full retry message list is checked only in the invalid-then-valid test; the duplicate test checks only the error text. Silent spots in decision 126: the token_budget event's subject being the track and a replayed row taking the pool's model are the builder's own choices where 126 says nothing; both are stated in the body.
```
