# REVIEW-17 — cold review of mission 17 (roadmap step S3.2b; closes M3)

Base: 5c0adab (`review: mission 16`, the last `review:` commit). Range
`5c0adab..origin/main`, tip ca91ecf. Unit commits reviewed, one sub-agent each,
in sequence: 014f06a (U1), db29997 (U2), 545e7ec (U3), 446b0a8 (U4), 8d54f9f
(U5). The commits af85e55 (the architect's kit), 1a04ee1 (`plan:`), the
`meta:` commits 7e82bf0, 8edae6e, 0de1a6a, d67eedb, 45dc893, 7f18206, ca91ecf
and d1abd9e (`report:`) I read myself, for forbidden edits only. None of them
touches a file a builder may not edit. The architect's kit commit touches only
architect files. No unit commit touches `meta/plan.md` or `meta/CHECKPOINT.md`.

## Gate

Gate M3: FAIL. The command passes, but G3.3 asserts less than its item says
(blocker 1).

I ran it at the pushed tip ca91ecf (equal to `origin/main`) myself, after
`uv run discotrade sandbox build` (`sandbox build: present, nothing built`,
`discotrade-sandbox:3b7d75c39621`, 0.9 s). One foreground call with a
20-minute timeout:

```
ca91ecf29237f84a114fa5d31e5f23478badfa87
G3.1 PASS 3 passed in 216.53s (0:03:36)
G3.2 PASS 8 passed in 183.28s (0:03:03)
G3.3 PASS 7 passed in 158.80s (0:02:38)
gate M3: PASS
exit 0
wall 561.659410261 s
```

Each item is under DESIGN §18.2's 15 minutes. Below, each item of §18.3 M3 as
decision 139 reads it, against the tests.

**G3.1.** `tests/gates/test_g3_1_candidates.py` covers the item in full:
- twenty trading days on `test_synth` with `m3/`, the gate configuration, the
  child-process backend and the scripted coordinator;
- at least ten `trials.jsonl` rows;
- the rows' makers equal the pool's three;
- every trial's source equals a repository strategy file and its
  `code_sha256`;
- every pair has |Pearson| ≤ `corr_max`, computed by the test with numpy. The
  series are held positions `h` on W of the later day, concatenated over the
  basket in track order. The positions come from positions jobs on the
  child-process backend, and the test asserts no series is constant.

Cutting the jobs as one span job plus one own-W job per trial, with the two
asserted equal on own W, is a reading where the decision is silent. It asserts
no less. Covered.

**G3.2.** `tests/gates/test_g3_2_pool.py` covers the item:
- every call row's model is `pool[(ordinal(D) + c) mod len(pool)]`. The test
  computes the ordinal itself and asserts it, and asserts no pool event;
- every cell index meets at least two models over the twenty ordinals, and an
  observed cell has two models;
- every attempt-2 message list is attempt 1's prompt, its reply, and a retry
  message. That message begins with the literal retry text and holds the error
  text of the test's own `parse`/`validate` run on attempt 1's stored text. A
  duplicate names an approach that exists and `corr_max`. Both a duplicate and
  a non-parse stage are required;
- every stored response has the full key set, and its `text` equals the corpus
  file the cursor served;
- with `m3_pool/`, `fail_window` and `fail_rate` are at production values. The
  test walks the counted rows itself, then asserts exactly one `model_removed`
  alert on the removal day, calls on that day and the day before, and none
  after;
- the budget day has one `budget` row (attempt 2, no response, zero tokens),
  one `token_budget` alert, one stored response, the arithmetic, and the
  journal file tracked and committed.

Covered.

**G3.3.** `tests/gates/test_g3_3_prompts.py`. What is covered:
- names, contract names and dates: covered;
- labelling: the stored first prompts equal `prompt.build` rebuilt for the
  call id, and at least two maps differ. Covered;
- scaling: return fields unchanged, an added price-unit field multiplied by a
  factor ≠ 1, and `p1`'s own fields unchanged. Covered;
- sanitising: covered end to end, and in a direct test that went red on the
  unsanitised registry.

**Raw bars and scores: not covered as the item says.** See blocker 1.

No product code under `src/` holds a special case for the gate: the mission's
`src/` diff names no corpus file, model id, 2019 date or call id (U5 reviewer).
`m3_harness.py` holds no seed, date or assertion. No existing file under
`tests/gates/` changed (`git diff --name-status 5c0adab origin/main --
tests/gates/` shows only `A`).

## Blockers

1. GATE M3 FAILED: DESIGN QUESTION: G3.3's "no raw bar" and "no score" checks
   skip the forms the prompt itself writes. So they assert less than §18.3 G3.3
   and decision 139 (c) say.

   Decision 139 (c) asks for no open, high, low or close of any bar of the
   day's W or T, and no figure of an earlier trial row, "written as `repr` and
   rounded to two and to four decimals, as a whole token". `looked_for`
   (`tests/gates/test_g3_3_prompts.py`, the function after `forms`) drops any
   form that is a whole number, or that equals `format(value, ".4g")`. The
   prompt renders every float with `.4g` (decision 117). So exactly the
   renderer's output is never looked for:
   - SYNA's prices (near 50): the two-decimal form of every one is a
     four-significant-digit string, so it is dropped. A SYNA close leaked
     through the profile would appear as `48.25` and not be caught.
   - Scores: for every figure with |x| < 1, both rounded forms equal their
     `.4g` text and are dropped. Only the full-precision `repr` is still looked
     for, and a `.4g` renderer never writes it. For figures from 1 to 100 the
     two-decimal form is dropped as well. So a score leaked through the prompt's
     own number rendering would pass the score check for almost every figure.

   The literal reading cannot be asserted on this fixture either. In a scratch
   worktree at ca91ecf (removed afterwards), I let `looked_for` drop only whole
   numbers and printed the hits in place of asserting. 23 of the replay's
   stored prompts held a token equal to:
   - a SYNA bar rounded, for example `48.25`, `53.54`, `47.97`, `49.92`;
   - a score form, for example `0.03`, `-0.0348`, `0.3113`, `18.24`, `33.88`,
     `6.861`.

   These are the profile's own `.4g` statistics colliding by chance, not leaks
   I could show. So a correct implementation fails the literal test, and the
   test as written skips the leak channel that matters most.

   The builder filed this openly as finding D-017 (status open) and carried it
   in NOT PROVEN. But the milestone cannot be met while its gate test asserts
   less than its item (DESIGN §18.2). The question is the architect's. Options:
   - a fixture instrument whose prices cannot meet a basis-point statistic;
   - checking prices and scores in the `.4g` form against what each prompt line
     is known to render;
   - a reading of "raw bar" and "score" that the architect states and the test
     enforces.

   G3.3's other checks and G3.1 and G3.2 stand as covered (see `## Gate`).

2. A claim the disk contradicts: three places say the M3 gate proves the
   corpus's per-file outcomes, days and attempts. It does not. The three places:
   - `tests/test_worker_corpus.py` (module docstring: "What a replay makes of
     the corpus (the outcomes, days and attempts the manifest records) is proven
     by the M3 gate, not here");
   - `tests/fixtures/worker_corpus/manifest.toml` line 3 ("what a replay makes
     of it is proven by the M3 gate");
   - 446b0a8's body ("It does not prove the outcomes or days below; the M3 gate
     (U5) does").

   No gate test reads the manifest's `served`, `attempt` or `outcome` fields.
   G3.1 and G3.2 assert aggregates:
   - at least ten trials and the three makers;
   - the rotation;
   - that a duplicate retry and a non-parse retry exist;
   - that the k-th response of a model is its k-th file.

   A manifest row with a wrong day, attempt or outcome passes every gate item.
   The U4 reviewer found this, and I confirmed it by reading the three gate
   files and `m3_harness.py`. The per-file table in FINAL-REPORT-17 `## Corpus`
   is labelled measured, which is accurate.

   The overclaim came from the brief's own U4 text ("as the builder measured
   it ... (the gate proves it)"). Two fixes are possible:
   - a test, in the gate or outside it, that compares the replay's call rows to
     the manifest;
   - the two file comments narrowed to what the gate proves.

   Commit bodies are not rewritten, so the body's sentence goes in a
   correction.

## Should-fix

None.

## Notes

1. Gate at the tip. FINAL-REPORT-17 states in NOT PROVEN that its gates ran on
   45dc893 with U5's files uncommitted. My run of `./scripts/gate M3` above is
   at the pushed tip ca91ecf and closes that item for M3. The tip's tree
   outside `meta/` equals what the builder ran, so I did not run gates M2, M1
   and M0 again.
2. Check times, one reviewer run per unit, each green:
   - 014f06a: 865 s;
   - db29997: 1001 s;
   - 545e7ec: 1048 s;
   - 446b0a8: 1037 s (`2364 passed, 182 deselected`, 0 skipped);
   - 8d54f9f: 1006 s (`2364 passed, 200 deselected`, 0 skipped).

   Every run from U2 on is above 15 minutes, which agrees with the builder's
   D-013 lines. The U1 to U3 reviewers did not capture the pytest summary line,
   so their skip counts are not confirmed by a reviewer. The U4 and U5 counts
   show the `container` tests ran.
3. U1 (014f06a). The body says a failed T run "writes nothing to the state
   directory". The test proves that the file list and the calls ledger's bytes
   are unchanged, not that every file's contents are. With append-only ledgers
   this is close, but narrower than the sentence. A call-limit breach on T under
   the container backend would also raise `DailyError`; this is untested, and
   DESIGN is silent on it.
4. U2 (db29997). The health events of steps 3 to 5 are appended at once, so a
   day that failed and is run again appends them a second time. DESIGN §16.2's
   exception allows the health log to survive a failed day. Whether a duplicate
   notice on the retry is intended is for step S4.2, which builds the retry.
5. U3 (545e7ec). `replay.scripted_start` raises an uncaught `KeyError`, which
   prints a traceback, on a stored response without a `model` key. `_roles`
   catches only `ConfigError`, `OSError` and `ValueError`. The harness always
   writes the key. `WORKERS_TRANSPORT` is a module-level test hook in product
   code.
6. U5 (8d54f9f). The commit changes the existing `tests/test_gate_script.py`.
   Its two "without gate tests" cases move from M3 to M4, which the brief's U5
   file list does not name. The body names it, what the cases assert is
   otherwise unchanged, and 68bee5f (M2) and ae7158b (M1) did the same. I
   accept it.

   `tests/test_offline.py` lists files holding the bytes `subprocess`. The new
   gate files held the word only in docstrings and were reworded to
   "child-process backend". They launch nothing themselves and go through
   `ProcessSandbox`, so this is a text fix, not a way around the test.
7. The wrong change "registry description passed unsanitized" went red only in
   G3.3's direct test, because `workers.parse` sanitizes before storing.
   FINAL-REPORT-17 says so in NOT PROVEN. Decision 139 (d) is met, since an
   item of G3.3 went red.
8. The U0 line in `meta/findings/FINDINGS.md` reads "D-016 status (...):
   Status: answered ...". The word "Status" appears twice. Cosmetic.
9. FINAL-REPORT-17's `## Corrections` meets decision 133 (a) to (c). The six
   tests are named, the two doctor cases are reported green under both wrong
   changes, and the reason is given: `OpenAICompatProvider.__init__` refuses
   with the same line and exit status. NOT PROVEN carries FINAL-REPORT-16's
   items and REVIEW-16 note 9's three additions. The sub-agents found nothing
   that NOT PROVEN omits, other than blocker 2's claim and note 3.
10. hands: HF-010. `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered
    as worktrees. This review's own worktrees were removed.
11. hands: HF-011. d1abd9e carries `report:` again. The brief names that
    prefix, and the protocol's skip list does not.
12. hands: HF-006. A U4 check run passed the 20-minute tool cap and was moved
    to the background by the harness. Reviewer runs now take 865 to 1048 s,
    which leaves 150 to 335 s of margin under the cap.
13. hands: HF-012. I ran the five reviewers in sequence, about 1 h 50 min in
    all, each running `./scripts/check` once in the foreground. Run in
    parallel, the check would likely pass the 20-minute cap on this 4-core
    machine.
14. hands: the brief's U4 text asked the builder to state served-on-which-day
    "(the gate proves it)", which no gate item was specified to prove. That is
    where blocker 2 came from.

## Per-commit verdicts

**014f06a (U1)**

> I found no defects in 014f06a (mission 17 unit U1); it passes all five points. Worktree /tmp/rv17-014f06a is removed and the main checkout is clean. Two other worktrees, /tmp/rv13-8b9f9be and /tmp/u5/parent, predate this review and I left them alone.
>
> 1. **Unit:** U1, scoring a generated candidate on T into a `lifecycle.Candidate` (decision 135). It claims DESIGN §7.1, §8, §10.2, §10.3, §11.3, §12.4 and §16.1 step 5, plus O-4/11/13/17/18 and I-3/I-7. The change is `score_on_t` and `_OnT` in src/discotrade/daily.py:410-441, one register entry, and the new tests/test_daily_score_t.py.
> 2. **Test-first: PASS.** With the parent's daily.py and return_readers.toml put back, 6 of the 7 new tests went red (2 failed, 4 errors) and the seeds/window test passed, as the body says. Two of the body's wrong changes, each made alone and reverted:
>    - avg_position taken from W's figures: red at test_daily_score_t.py:337.
>    - h(u0) = targets[0] in backtest.py:287: red through the test's own h check at test_daily_score_t.py:247 (2 errors).
> 3. **`./scripts/check`: PASS.** Final lines "config check: ok, 173 unverified values" then "check: green", wall 865 s. The tail I captured did not include pytest's pass/skip line. A separate collect-only run shows the check selects 2330 tests, which matches the body's 2330, but I did not see the passed or skipped counts myself. After `sandbox build`: "present, nothing built", discotrade-sandbox:3b7d75c39621.
> 4. **Design conformance: PASS.**
>    - **(a)** `_OnT` swaps only the window, so both the job and the stored bars use T in positions mode. The test checks the job's last bar ends at D's end while the store holds later bars, and checks h(u0)=0.
>    - **(b)** adjusted_t's average positions are over T.
>    - **(c)** Every field is carried; cell is "family/horizon", the same format as generate.py:178.
>    - **(d)** The new entry is `producer`; `lifecycle.admit` stays `adjusted` and no entry is reclassified.
>    - **(e)** A sandbox error raises DailyError.
>    - **(f)** The expected figures come from backtest.evaluate rows plus Parquet bars and roll files read directly. The test calls none of the forbidden paper.* functions and not the function under test.
>    - **Invariants:** no network, secret, wall clock, market name, new constant, new dependency or in-repo state.
> 5. **Forbidden touches: PASS.** The diff 5c0adab..014f06a over config/, tests/fixtures/config/, config_frozen.json, tests/gates/ and tests/fixtures/rejected/ is empty. Only the three listed files changed.
>
> **Not proven / minor:**
> - The body says a failed T run "writes nothing to the state directory". The test proves less: the file list is unchanged and the calls ledger's bytes are unchanged, but other files' contents are not compared.
> - With a backend that enforces call limits, a call_p95/call_max breach on T also raises DailyError with "failed in the sandbox" text. This is untested and DESIGN is silent on it.
> - The "stored response keeps the paid call" part of 135(e) belongs to U2 and is not tested here.

**db29997 (U2)**

> db29997: I found no defects; the commit is accepted. All work was in a worktree at /tmp/rv17-db29997, now removed. Nothing was edited in the repo. The other worktrees still listed (/tmp/rv13-8b9f9be, /tmp/u5/parent) were there before me and I left them alone.
>
> 1. **Unit:** mission 17 U2, decision 136 (with 124, 125, 126, 131 (b), (c), 137 (b)). It claims DESIGN 16.1 steps 3 to 5, 13.6, 13.7, 14.1, 14.3, 15.2, 16.2 and I-5, I-6, I-8, I-13. Files: `src/discotrade/daily.py`, the new `tests/test_daily_generation.py` (11 tests), and one line appended to `meta/findings/FINDINGS.md`. OK.
> 2. **Test-first:** with the parent's `daily.py`, 10 of the 11 tests went red (7 failed, 3 errors, `run_day() got an unexpected keyword argument 'provider'`); the facts test passed, as the body says. Three wrong changes, one at a time:
>    - Steps 3 to 5 run on a re-run (WRITTEN condition dropped, `daily.py` ~l.521): the re-run test went red.
>    - Cell statuses reading rows dated D: red only when `coordinator.py:148` also read the staged ledger, together with `d+1`; then the dormant-on-D test went red. `d+1` alone stayed green, because `cell_statuses` only reads committed rows. That matches the body's own description of this change.
>    - Call rows written outside staging (`into=None`): the failed-day and health-event tests went red.
> 3. **Check:** `./scripts/check` passed once (`sandbox build`: present, nothing built, discotrade-sandbox:3b7d75c39621). Last line verbatim: `check: green`. Wall time 1001 s, which is over 15 minutes, in line with the D-013 line the commit adds. The tail did not include the pytest summary line. A separate `--collect-only` gives `2341/2523 tests collected (182 deselected)`, matching the body's 2341/182.
> 4. **Design conformance:** OK on every item.
>    - (a)–(e) Steps run after `lifecycle.run_steps`, before `_rank_persistence` and the table, only when the day is WRITTEN, a provider is given and the gap check does not skip. No offered cell, an empty pool or no brief means no call. `list_models` is read once, and a `ProviderError` gives `model_list_failed`.
>    - `removed_models` reads the committed `calls.jsonl` and filters to `day-1` itself (`pool.py:183`). The call rows and the admission go to staging. `day_events` runs over the staged rows. Each event is appended to the real health log as it is returned.
>    - (f) and (g) are covered by the tests. A provider together with a candidate raises `ValueError`.
>    - Invariants and the rest: `run_day` without a provider follows the parent's path, and `tests/test_daily.py`, `test_replay.py` and `test_replay_candidates.py` are unchanged. I saw no breach of I-5, I-6, I-8, I-9, I-11, I-12, I-13 or I-14, no new dependency, and no number a gate, score or alert uses written outside `config/`. The body's "seen to fail" claims match what I saw, and I found no overclaim.
> 5. **Forbidden touches:** none. `git diff 5c0adab db29997` over the frozen config paths is empty. `FINDINGS.md` is append-only (one blank line plus the D-013 line). `meta/plan.md`, `CHECKPOINT.md` and the protected documents are untouched. OK.
>
> **Not proven:**
> - The skipped count (0) of my run, because the tail did not show the summary line.
> - Events from steps 3 to 5 are logged again when a failed day is re-run. I did not check whether DESIGN 16.2 allows that.
> - I did not review whether `registry_lines` itself carries no score (I-8). That code is older than this commit, and decision 136 (c) names it.

**545e7ec (U3)**

> **Review of 545e7ec (mission 17 U3). Verdict: PASS. No defects found; the pytest count is unconfirmed (my one check run didn't capture it).**
>
> 1. **Unit:** mission 17 U3, the `--provider` and `--coordinator` options of run-day and replay, and the scripted cursor. It cites decision 137, decision 122 (b),(c) as 137 (c) amends it, DESIGN 13.5, 14.2, 16.4, and I-6, I-12, I-13. The commit touches 5 files: `cli.py`, `replay.py`, `providers.py` (docstring only), the new `tests/test_cli_provider.py` (17 tests), and `FINDINGS.md`. PASS.
> 2. **Test-first:** with the parent's source files, 12 of 17 tests failed and 5 passed, exactly the 5 the body names. Wrong change 1 (cursor start counted from the `calls.jsonl` rows) failed only `test_a_split_replay_after_a_day_failed_with_its_response_stored`. Wrong change 2 (a new ScriptedProvider for each day in `replay()`) failed only `test_the_provider_is_built_once_per_command` ("assert 5 == 1"). The "seen to fail" claims hold. PASS.
> 3. **Check:** the sandbox build said "present, nothing built", tag discotrade-sandbox:3b7d75c39621. One `./scripts/check` run, final line `check: green`, wall time 1048 s (above 15 minutes, in line with the open D-013 times). Not captured: the pytest summary line. `config check` prints over 40 lines after pytest, so `tail -40` cut it off, and I did not run the check a second time. The body's "2358 passed, 182 deselected, 0 skipped" is not independently confirmed.
> 4. **Design conformance:** PASS.
>    - **(a)** The options accept none (default), scripted:<dir> and openai; `--coordinator` takes only scripted. openai is built through `openai_compat_from_env` with `base_url` from `models.toml` and the timeout from `run.toml`'s `[workers]`.
>    - **(b)** `--candidates` with a provider other than none exits 2. A missing scripted directory, or a missing or refused `models.toml`, exits 2 with one line before any day runs. openai without a usable key exits 1 with one line on stderr; the test's MockTransport fails if called, and no test sets a key.
>    - **(c)** The cursor start counts the stored response files under `responses/<track>/*/*.json` per model, read once when the provider is built.
>    - **(d)** With none, the provider is None and nothing changes for days. `tests/test_cli.py`, `test_replay.py` and `test_replay_candidates.py` are untouched by the commit, and they ran green inside the check.
>    - **Invariants:** `providers.py` is still the only module under `workers/` importing httpx or starting a process. The key is read only in `openai_compat_from_env`, and its name appears only in `providers.py`; the docstring change only replaces the sentence that is no longer true. I-6, I-9, I-11, I-12, I-13 and I-14 hold: no wall clock, no market names, no new dependency, no new number that moves a result.
> 5. **Forbidden touches:** none. The commit touches no file builders must never edit, and neither `meta/plan.md` nor `meta/CHECKPOINT.md`. The frozen config diff (5c0adab..545e7ec over config/, the config fixtures, config_frozen.json, tests/gates/, tests/fixtures/rejected/) is empty. `FINDINGS.md` only gains one appended line (no lines removed). PASS.
>
> **Minor notes, not defects:**
> - `replay.py` `scripted_start` stops with an uncaught `KeyError` (exit with a traceback) if a stored response has no `model` key. `_roles` catches only `ConfigError`, `OSError` and `ValueError`. The harness always writes that key.
> - `WORKERS_TRANSPORT` is a module-level test hook in product code.
> - Two choices the design leaves open are both declared in the body: a `run.toml` without `[workers]` under openai exits 2, and an empty `base_url` exits 1.
>
> **Not proven:** the pytest pass, skip and deselect counts, and that the `container` tests ran rather than skipped (the image was present, but no summary line was seen). The worktree is removed and the main repo was not modified.

**446b0a8 (U4)**

> 446b0a8 is mostly sound, but one claim is false: the commit says the M3 gate (U5) proves the per-day outcomes, and it does not.
>
> 1. **Unit and claims:** this is mission 17 U4, the worker corpus. It cites decision 138 (m17), decision 122 (b) (m15), DESIGN 13.4, 13.5, 17.1, 18.3 G3.1 and G3.2, and HF-009. It adds 48 responses, 16 strategies, `manifest.toml` and `tests/test_worker_corpus.py`, and touches no file under `src/`.
> 2. **Test-first: PASS.** The test passes (6 passed, 3.17 s in pytest, 4.5 s wall). I changed one character in the block of `m3/MiniMaxAI__MiniMax-M3/0002.md` ("fast": 12 to 22): the byte-identity test and the parse test went red. Deleting `m3/nvidia.../0005.md` turned four tests red. Both reverted.
> 3. **Check: PASS.** The sandbox image was present (`discotrade-sandbox:3b7d75c39621`). Summary line: `2364 passed, 182 deselected in 1033.09s (0:17:13)`, 0 skipped. Final line: `check: green`. Wall time 1037 s, which is above the 15-minute limit in HF-006, matching the commit's D-013 line.
> 4. **Decision 138 (a) to (f): PASS, with one overclaim.**
>    - Directories are named per 122 (b) after the three pool models.
>    - Responses are reasoning, one block, then one sentence. The injected description in `nemotron/0001.md` (two sentences counting its `<note>`) has a backtick and angle brackets.
>    - Byte identity is test-proven.
>    - I read all 16 strategy files: each is an ordinary price, volume or calendar rule importing only `indicators`. None touches files or the network, and none uses introspection (HF-009 holds). The family and horizon in the body match each file's docstring and cover all six families.
>    - `m3_pool/` holds 21 invalid responses (11 `six_params`, 10 `always_flat`).
>    - The budget file has 212587 characters (my count); ceil(212587/4) = 53147. 53147 + 3463 + 8000 = 64610 > 60000 at production values, and it still holds without tokens_in.
>    - The manifest lists every file with model, strategy, parse result, outcome and description.
>    - **Defect:** the commit body ("It does not prove the outcomes or days below; the M3 gate (U5) does"), `tests/test_worker_corpus.py:19-20` and `manifest.toml:3` all say the gate proves the manifest's per-file `served`, `attempt` and `outcome`. At tip ca91ecf, `tests/gates/test_g3_*.py` and `m3_harness.py` assert only aggregates (at least ten trials, three makers, corr_max, rotation, retries). Nothing reads those manifest fields.
>    - I-7, I-9, I-11 and I-14 hold.
> 5. **Forbidden touches: PASS.** The commit touches no protected file and no plan or checkpoint. `git diff 5c0adab 446b0a8` on the frozen paths shows only `src/` changes from the earlier commits 014f06a, db29997 and 545e7ec, none from 446b0a8. `FINDINGS.md` is only appended to (a D-013 line and an HF-006 line).
>
> **Not proven:**
> - The per-day served/outcome table, the "15 trials (MiniMax 5, nemotron 6, openai 4)" split and the "0.609" correlation figure are the builder's own measurement. No test checks them, and I did not replay.
> - I did not reproduce the builder's 3/3 green runs; I ran the check once.
>
> The worktree is removed. The other worktrees still listed (`/tmp/rv13-8b9f9be`, `/tmp/u5/parent`) are not mine.

**8d54f9f (U5)**

> **8d54f9f** (mission 17 U5): verdict PASS, no blocking defects. The worktree /tmp/rv17-8d54f9f is removed. Two older worktrees (/tmp/rv13-8b9f9be, /tmp/u5/parent) are still there; I did not create them and did not touch them.
>
> 1. **Unit and sections: PASS.** U5, the M3 gate tests G3.1 to G3.3. It cites DESIGN §18.2 and §18.3 M3, decisions 139 and 132 (b), decisions 9, 40 and 72, and O-2 and O-19.
> 2. **Seen to fail: PASS for three of the seven changes.** Each was made alone in src/, the item run, then reverted with an empty `git diff --stat`.
>    - Model chosen without the cell index (pool.py:118): G3.2 red, 1 failed of 8, in `test_every_call_row_model_is_the_rotation` (test_g3_2_pool.py:172, 2019-07-16 trend/medium), as the body says.
>    - Retry sent without the error text (generate.py:174 returns RETRY_TEXT): G3.2 red, 1 failed, `test_a_retry_carries_the_error_text`.
>    - Profile block keyed by symbol (anonymize.py:131): G3.3 red, 2 failed, the symbol/venue/date test and the scaling test, matching the body's "SYND ... and the scaling test".
> 3. **Check: PASS.** `./scripts/check` exit 0 at the commit after the sandbox build reported "present, nothing built", discotrade-sandbox:3b7d75c39621. Summary line: `2364 passed, 200 deselected in 1003.33s (0:16:43)`, 0 skipped. Final line: `check: green`. Wall time 1006 s, over 15 minutes, which the commit already records as a D-013 times line.
> 4. **Conformance: PASS.**
>    - The three test files carry `pytestmark = [gate, gate_m3]` (g3_1:52, g3_2:86, g3_3:84). m3_harness.py has no marker, which matches m1_harness and m2_harness.
>    - m3_harness.py holds no assert, date or seed.
>    - Every date and seed is written in the test files.
>    - Gate config is reused from m1_harness: test_synth from the fixture config tree copied under tmp (models.toml with it), thresholds_gate.toml copied over unchanged, `--sandbox process`, `--provider scripted:<corpus>`, `--coordinator scripted`, in-process through `cli.main`.
>    - The mission's src/ diff (cli.py, daily.py, replay.py, providers.py) contains no corpus name, model id, 2019 date, call id or `worker_corpus`.
>    - tests/test_gate_script.py: only M3/G3.x becomes M4/G4.x (six G4 items), plus the comments; the assertions keep their shape. This is the same pattern as 68bee5f (M2) and ae7158b (M1).
>    - That file is outside "carries only the new gate files and the FINDINGS line". It is a minor deviation, allowed by the brief's "Where a cited decision changes what an existing test asserts..." clause, and it is named in the body.
>    - test_offline: it lists every file under tests/ or src/ containing the bytes `subprocess` or `os.system` (test_offline.py:409-430). The new gate files only had the word in docstrings. They import nothing that launches a process and go through `ProcessSandbox`, whose module src/discotrade/sandbox/process.py is already listed. So rewording to "child-process backend" is a text fix that keeps the listing honest, not gaming.
>    - Invariants: state and jobs only under tmp_path or tmp_path_factory; git through `m1_harness.git`, which sets GIT_ALLOW_PROTOCOL=file (I-14, I-11). No wall clock, no network (I-12, I-11). No market name in src/ (I-9).
> 5. **Forbidden touches: PASS.**
>    - The commit touches only FINDINGS.md, four new tests/gates/ files and test_gate_script.py. None is a builder-forbidden file, meta/plan.md or meta/CHECKPOINT.md.
>    - `git diff --name-status 5c0adab 8d54f9f -- tests/gates/` shows only A.
>    - The frozen config, config_frozen.json and rejected/ diff is empty.
>    - FINDINGS.md has no removed line: D-017 is added before the "hands findings (continued)" heading, and the D-013 and D-014 lines are added at the end.
>
> **Not proven:** the other four of 139 (d)'s changes (correlation gate, removal, budget, registry sanitize) were not re-run. I did not run `./scripts/gate M3`, M2, M1 or M0 myself. Whether the D-017 reading of 139 (c) is right is the architect's call.
