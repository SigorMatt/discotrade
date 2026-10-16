# REVIEW-16 — cold review of mission 16 (roadmap step S3.2a, repaired)

Base d3fee0d (`review: mission 15`, the last `review:` commit); range
`d3fee0d..origin/main`, tip ee750d3. Unit commits reviewed, one sub-agent each,
in sequence, each in its own worktree: 6e3caa5 (U1), 512bb3e (U2), dcff385 (U3).
Read for forbidden edits only: 72c7836 (the architect's kit: `KIT.md`,
`meta/BACKLOG.md`, `meta/BUILDER-16-PROMPT.md`, `meta/ROADMAP.md`,
`meta/decisions/decisions-2026-10-16-m16.md`), ef3ebc4 (`plan:`), 38c98cc,
bdeb96f, 7f100b4, ef4548f, ee750d3 (`meta:`, the builder's `meta/plan.md`,
`meta/CHECKPOINT.md`, `meta/journal.md` only), 6c10a3b (`report:`,
`meta/FINAL-REPORT-16.md` only). No builder commit touches a file `CLAUDE.md`
reserves. `git diff --stat d3fee0d origin/main -- config tests/gates tests/fixtures`
is empty.

## Gate

not a closing mission

(The brief, decision 127 (a): "This mission closes no milestone and runs no
gate.")

## Blockers

None.

## Should-fix

1. 6e3caa5's body says more about its test history than the disk shows. It
   says: "The status and wrong-type cases already passed before the change;
   the others were seen to fail first." With `providers.py`, `doctor.py` and
   `cli.py` set back to 6e3caa5~1, 16 of the 22 new tests fail and 6 pass. The
   U1 reviewer saw this and I re-ran it myself. The 6 that pass are the three
   cases the body names, plus three others:
   - `tests/test_doctor.py::test_live_workers_without_a_usable_key_never_calls_the_transport[unset]`
   - `tests/test_doctor.py::test_live_workers_without_a_usable_key_never_calls_the_transport[spaces]`
   - `tests/test_workers_providers.py::test_the_source_test_resolves_a_relative_import_of_key_env`

   None of the three was seen to fail. The two doctor cases hold behaviour the
   parent already had, since the parent's doctor read the key itself and
   refused. None of the brief's named wrong changes turns them red either: the
   doctor's own read restored turns only the source test red. The resolver
   case tests the test's own reader.

   I file this as should-fix, not a blocker. The sentence is about test
   history, not about what the code does or what the tests prove. Every test
   holds the behaviour it names at the tip. FINAL-REPORT-16's "What the tests
   prove" does not repeat the sentence.

   Commit bodies are not rewritten (decision 128 (d)'s rule). So the fix is a
   correction line in the next report: name the three tests as passing at the
   parent. For the two doctor cases, either name a wrong change that turns
   them red (for example a `key_present` that ignores blanks, which would
   turn `[spaces]` red), or state that none was seen.

## Notes

1. U1, `key_present` and the docstrings. `key_present()` returns a `bool`
   only: false for an unset, `""`, `"   "` or `"\t \n"` key, true for a dummy
   key. Both docstrings say decision 128 (b)'s sentences and no more; the only
   wording change is "Here"/"this module" in place of "There"/the path.
2. U1, the raise sites. Every raise site of `ProviderError` in
   `OpenAICompatProvider` now stands outside an `except` block: `__init__`
   twice, `_call`'s timeout, transport, not-JSON and status, the malformed
   bodies of `list_models` and `complete`, and `complete`'s wrong type. So
   decision 128 (e) holds by inspection for every raise site, wider than the
   failure kinds the tests raise. FINAL-REPORT-16's NOT PROVEN line on this
   is accurate and cautious.
3. Decision 128 (b)'s own wording. The decision calls `openai_compat_from_env`
   "the one function that reads the key's value". But `ClaudeWorkerProvider`
   (`src/discotrade/workers/providers.py`, around line 269) iterates
   `os.environ.items()` to leave the key out of its child's environment, so
   it touches the value while filtering it. This is the decision's wording,
   which the builder was bound to state, not builder overreach. It is for the
   architect to read the rule as "reads in order to use". I-13 holds: the
   value goes nowhere.
4. U1, finding D-016. The `cli.py` help string and `doctor.py`'s module
   docstring changed outside decision 127 (a)'s file list. Both are text only,
   decision 128 (c)'s test cannot pass without the change, and it is filed
   openly as D-016 (status open, for the architect). I accept it as done.
5. U2. The `config check` comparison is real: each refusal test runs
   `discotrade config check` on the same copied configuration and compares
   against its stderr, not against a written copy. The timeout test reads
   `request.extensions["timeout"]` at the `MockTransport`. The doctor and
   `config check` read the same `ctx.config`. The only change to an existing
   test is `MODELS_TOML`, given the loader's fields with the same ids, pools,
   fallback and `base_url`; no existing assertion changed.
6. U2, not tested. No test covers the refusal of a `run.toml` without a
   `[workers]` table (`src/discotrade/doctor.py:241-243`), the case the body
   calls the simplest thing where the design is silent. Also, a `models.toml`
   path that is a directory gets the "does not exist" line. Both are minor.
7. U3. In both new tests the first fetch fills the cache over the same span,
   so a key missing the part would serve the stale series. Mutations (a) and
   (b) show this, so the "differs" check is not trivially met.

   FINAL-REPORT-16's `## Cache key` row for "the whole `[source]` table
   replaced by its adapter name (the seed test red)" understates: 14 other
   `tests/test_synth.py` tests go red too. That understates rather than
   overclaims.

   The comment at `tests/test_synth_cache.py:182` says "27 hours of open
   market". The span is 27 clock hours but 26 open hours, since the
   17:00-18:00 break is outside it. The assertion is `> 20`, so the result is
   unaffected.
8. Speed. One `./scripts/check` per unit commit in this review: 832 s at
   6e3caa5, 840 s at 512bb3e, 839 s at dcff385, each green with the
   `container` tests run on discotrade-sandbox:3b7d75c39621. All three are
   above decision 114's 12 minutes and under HF-006's 15 (D-013, open). They
   match FINAL-REPORT-16's 825 to 890 s.
9. FINAL-REPORT-16's NOT PROVEN checked against what the sub-agents found:
   - Its items stand: no real provider, model or `claude` called (L3, L4);
     the base URL, model ids and cutoffs unverified; nothing of S3.2a called
     from `run-day` or `replay`; the source test's spelling limits; the U3
     mutations run only over the two synth test files.
   - The reviewers add three items: the `[workers]`-missing refusal is
     untested (note 6); the doctor tests of U1 were never seen to fail
     (should-fix 1); the builder's own check timings were not re-measured
     beyond one run per unit.
10. hands: the worktrees `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still
    registered (HF-010, unchanged since REVIEW-14). This review's own
    worktrees were removed.
11. hands: 6c10a3b carries the `report:` prefix again (HF-011). The report
    says it kept the prefix on purpose. The protocol's skip list still does
    not name it.
12. hands: this review ran its three reviewers in sequence, about 51 minutes
    of sub-agent time, each running `./scripts/check` once in the foreground.
    No reviewer ran a background task or synced extras beyond `--extra dev`
    (HF-012's direction followed by hand, as the protocol does not yet say
    it).

## Per-commit verdicts

### 6e3caa5 (U1)

Commit 6e3caa5 (mission 16, unit U1) passes on all six points. I found no blocker and one minor should-fix in the commit body.

1. **Unit and sections:** U1, REVIEW-15 blocker 1 and the first half of note 3. It claims decision 128 (a), (b), (c), (e), decision 122 (c), (e), DESIGN 13.5, 19.3 L3 and I-13. Sandbox image was already present (`discotrade-sandbox:3b7d75c39621`).
2. **Test-first: pass.** With providers.py, doctor.py and cli.py reverted to the parent, 16 of the 22 new tests fail (source test, key_present ×5, error-context ×10). The 6 that pass are the two status cases, the wrong-type case, the resolver test and both doctor tests, which is expected because the parent doctor already stripped the key.
   - Mutation (a), the doctor's own `os.environ.get(KEY_ENV, "")` restored: only the source test fails, with `['doctor.py']`.
   - Mutation (b), the parent's in-except `from None` raises: exactly 10 context tests fail.
3. **`./scripts/check`: green**, run once, 832 s wall, rc=0. It ends `2313 passed, 182 deselected in 829.93s` / `config check: ok, 173 unverified values` / `check: green`.
4. **Design conformance: pass.**
   - `key_present` returns a bool only, false for unset, "", "   " and "\t \n".
   - Both docstrings state 128 (b) and nothing wider: "Here"/"this module" in place of "There"/the path is the only rewording.
   - The source test enumerates every `.py` under `src/discotrade` itself and checks both the text and the `ast` import.
   - In `OpenAICompatProvider`, every ProviderError raise site now sits outside an except block: `__init__` ×2, `_call` timeout/transport/not-JSON/status, `list_models` and `complete` malformed body, `complete` wrong-type. `_field`'s KeyError text is never empty, so no silent fall-through.
   - I-9, I-10, I-11, I-12, I-13 and I-14 hold. No new dependency, and providers.py is still the only workers module that imports httpx.
5. **Forbidden touches: pass.** Nothing changed under `config/` since d3fee0d, nor in `tests/gates`, `tests/fixtures`, meta/plan.md, meta/CHECKPOINT.md or the files CLAUDE.md reserves. The cli.py help string and the doctor.py docstring change sit outside 127 (a)'s list. That is acceptable: they are text only, 128 (c)'s test cannot pass without them, and the change is filed openly as D-016.
6. **Should-fix (minor, commit body):** "the others were seen to fail first" overstates. The two doctor tests (`tests/test_doctor.py:257`) and the resolver test passed at the parent. Since commit bodies are not rewritten, this would be corrected in FINAL-REPORT-16.

**Not proven:**
- `ClaudeWorkerProvider` (`src/discotrade/workers/providers.py:269`) iterates `os.environ.items()`, so it technically touches the key's value while filtering it out. The "one function that reads the value" sentence is the decision's own wording, so this is a note for the architect, not builder overreach.
- The source test does not catch attribute access such as `providers.KEY_ENV`. That is outside what 128 (c) asks.

I removed the review worktree; nothing was edited or committed in the main checkout.

### 512bb3e (U2)

Review of 512bb3e (mission 16 U2): **PASS, no blocker and no should-fix.**

1. **Unit and setup:** U2 is "doctor --live workers reads the loaded models.toml and run.toml". It claims decision 129, decisions 122 (e) and 123 (c), (d), DESIGN §19.3 L3, §4.3, §13.6 and I-10, and those match the brief. The worktree synced, and the sandbox image `discotrade-sandbox:3b7d75c39621` was already present.
2. **Test-first: PASS.** With the parent's `doctor.py`, 7 failed and 23 passed. The 7 red were the four 123 (c) refusals, the run.toml refusal, the timeout test and the ast test. The file-order listing test and all existing tests passed there, as expected since that behaviour is not new. Each mutation was made alone and reverted:
   - (a) Raw tomllib parse restored: 5 red, the four refusals and the ast test.
   - (b) Fixed 300.0 restored: 1 red, the timeout test.
   Both match the commit body.
3. **`./scripts/check`, run once: GREEN.** `2321 passed, 182 deselected in 839.03s (0:13:59)`, wall 840 s. Last lines `config check: ok, 173 unverified values` and `check: green`. The body's 2321 passed matches.
4. **Design conformance with 129 (a)-(c): PASS.**
   - Order is key check, then config, then provider. `WORKERS_TIMEOUT_SECONDS` and the tomllib import are gone, and `WORKERS_TRANSPORT` stays.
   - A `ConfigError` gives one stderr line, exit 1, empty stdout. Each test runs real `config check` first and compares against its own stderr text, not a hardcoded copy.
   - Each of the four loader messages names the intended rule. The "fallback of another maker" case gives "...not a pool = false model of the same maker ('A')".
   - The timeout test reads `request.extensions["timeout"]` at the MockTransport, so it sees the value the provider used. The failing transport calls `pytest.fail`.
   - The only existing-test change is `MODELS_TOML`, now in the loader's shape with the same ids, pools, fallback and base_url. No existing assertion changed.
   - Doctor and `config check` both read the same `ctx.config` from the CLI's `--config`.
   - Invariants: I-9, I-10 (17.5 lives only in a test), I-11, I-12, I-13 and I-14 hold, and there is no new dependency. Every claim in the commit body checked out on disk.
5. **Forbidden touches: none.** The commit changes only `src/discotrade/doctor.py` and `tests/test_doctor.py`. `git diff d3fee0d` shows nothing under `config/`, `tests/gates/` or `tests/fixtures/`; the `meta/plan.md` and `meta/CHECKPOINT.md` changes there come from the builder's own `meta:` commits.
6. **Cleanup:** the worktree is removed and the main checkout is unchanged.

**Not proven:**
- No test covers a run.toml without a `[workers]` table (`src/discotrade/doctor.py:241-243`), the path the body labels "simplest thing". It is a minor gap, not a should-fix.
- A `models.toml` path that exists as a directory now gets the "does not exist" line. That is harmless.
- The real provider's behaviour, as the body already says.

### dcff385 (U3)

Commit dcff385 (mission 16, unit U3, tests only). **Verdict: pass. No blocker, no should-fix.**

1. **Setup, OK.** I made the worktree at dcff385 and ran `uv sync --extra dev`. `sandbox build` reported image `discotrade-sandbox:3b7d75c39621` already present, so nothing was built.
2. **Unit and sections, OK.** The body names U3 (REVIEW-15 should-fix 2), decision 130 of m16, decision 121 (a) of m15, DESIGN §5.5 and §17.1, and I-6. That matches the brief.
3. **Mutations, all confirmed.** Both new tests pass unmutated (53 passed over `tests/test_synth_cache.py` and `tests/test_synth.py`). I edited the key at `src/discotrade/sources/synth.py:213` one change at a time and reverted with `git checkout dcff385 -- .`:
   - (a) calendar record removed: only the calendar test red.
   - (b) bar length removed: only the bar-length test red.
   - (c) seed dropped from the `[source]` params: red in the seed cache test and `test_synth.py::test_same_seed_same_bars_and_different_seed_different_bars`.
   - (d) `trusted_from` removed: only the `trusted_from` test red.
   - (e) whole `[source]` table replaced by its adapter name: the seed test goes red as the body says, but 14 other `test_synth.py` tests fail too. The body understates this; it does not overclaim.
4. **`./scripts/check`, green.** One run, 839 s wall, `2323 passed, 182 deselected in 838.02s`, container tests ran (`test_sandbox_container.py` all passed). Last lines verbatim: `config check: ok, 173 unverified values` / `check: green`.
5. **Decision 130 (a), conforms.**
   - Each test asserts both that the second series differs and that it equals the series fetched after `clear_cache`.
   - The stale-cache check is real, not trivial: in both tests the first fetch fills the cache with the same stop date, so a key missing that part would serve the stale series. Mutations (a) and (b) show this.
   - The closure (2019-02-12 09:00 to 2019-02-13 12:00 New York, 14:00 to 17:00 UTC under EST) is written in the test, falls inside the fetched span, and is appended to a copy under `tmp_path`. `tests/fixtures/config` is untouched.
   - The 1800 s bar length suits `synth_week`, whose boundaries all fall on the hour (18:00, 17:00 and the 2019-07-03 closure's 13:00).
   - Every date, seed and bar length is written in the file, and nothing reads the wall clock.
   - Existing tests are unchanged: the diff adds 63 lines and deletes none.
   - I-6, I-9, I-10, I-11, I-12 and I-14 hold. Every claim in the body matches the disk. I did not re-measure the "3/3, 834/837/890 s" timings.
6. **Forbidden touches, none.** The commit changes only `tests/test_synth_cache.py`.
7. **Cleanup, done.** The worktree is removed and the main checkout is clean. Two older worktrees are still registered and were left alone: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent`.

**NOT PROVEN:** the mutations were not run against the gate or container tests (the body says so too), and the body's own three check timings were not reproduced.

**Note only:** the comment at `tests/test_synth_cache.py:182` calls the closed span "27 hours of open market". That is 27 hours of clock time but only 26 open hours once the 17:00-18:00 break is taken out. The assertion is `> 20`, so the result is unaffected.
