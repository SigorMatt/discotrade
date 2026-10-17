VERDICT: mission 18 finished

# FINAL REPORT — mission 18 (roadmap step S3.2b, continued; closes milestone M3)

Brief: `meta/BUILDER-18-PROMPT.md`. Base 63c6d57 (`plan: mission 18 kit (S3.2b
closer, G3.3 bar and score reading, gate M3)`). Decisions:
`meta/decisions/decisions-2026-10-17-m18.md` (141 to 145), with items 1 to 140
(139 (c)'s raw-bar and score clause replaced by 142) and the owner's files still
binding. This mission closes REVIEW-17's two blockers and runs gate M3 again at
the pushed tip: `./scripts/gate M3` printed `gate M3: PASS` at e9076d5. No file
under `src/` changed (decision 141 (a)), so gates M2, M1 and M0 were not run
again (decision 141 (b)). Container runtime: docker; `uv run discotrade sandbox
build` at the tip d8a129a printed `sandbox build: present, nothing built` and
`discotrade-sandbox:3b7d75c39621` (0.65 s).

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | e6c33ae | `plan:` the plan, checkpoint, journal; FINDINGS.md: D-017 status (answered, item 142); HF-010, HF-011, HF-006, HF-012 status lines (144 (f)) |
| U1 | da7634b | `gate:` `tests/gates/test_g3_3_prompts.py`: three new tests, decision 142 (a), (b), (c); module docstring states 142's reading; `looked_for` and the text search unchanged (142 (d)). `tests/gates/m3_harness.py`: `scaled_store`, a helper with no seed, date or assertion |
| U2 | ac3e67e | `gate:` `tests/gates/test_g3_2_pool.py`: `test_the_manifest_gives_each_served_files_day_attempt_and_outcome` (decision 143 (a)); `tests/test_worker_corpus.py` module docstring and `tests/fixtures/worker_corpus/manifest.toml` third line name that test (143 (b)); no manifest row corrected |
| U3 | db527f3 | `meta:` gate M3 at the pushed tip e9076d5; one D-013 times line (141 (b), 145) |
| U4 | this commit | this report |

Meta commits: 3522d4f (U1 done), e9076d5 (U2 done), d8a129a (U3 done). Each unit
commit's body lists its files. Files changed in the mission outside `meta/`
(`git diff --name-status 63c6d57 d8a129a`): `tests/fixtures/worker_corpus/manifest.toml`,
`tests/gates/m3_harness.py`, `tests/gates/test_g3_2_pool.py`,
`tests/gates/test_g3_3_prompts.py`, `tests/test_worker_corpus.py`, each `M`.
Gate tests added: 4 (G3.3 from 7 to 10, G3.2 from 8 to 9). Tests the check runs:
unchanged, 2364 (the gate tests are deselected; 204 deselected, 200 at mission
17's tip).

## Speed

`./scripts/check` wall time on the builder's machine (four cores, shared), each
run its own foreground call with a 20-minute timeout:

| Where | Runs |
|---|---|
| mission 17's tip 7f18206 (FINAL-REPORT-17) | 1021, 1043, 1024 s |
| U1 da7634b | 1022, 1030, 1034 s |
| U2 ac3e67e | 1001, 923, 931 s |
| U3, at the pushed tip e9076d5 | 917, 921, 926 s |
| tip d8a129a (U4, before this commit) | **919, 922, 931 s**, each `check: green` |

At the tip each run printed `2364 passed, 204 deselected` (0 skipped, so the
`container` tests ran on discotrade-sandbox:3b7d75c39621), `config check: ok, 173
unverified values` and `check: green`; pytest 916.08 s, 919.25 s, 928.55 s; wall
918.79 s, 921.95 s, 931.26 s. Outputs kept in `meta/drafts/m18-tip-check-<n>.txt`
(runs 2 and 3: first line `git rev-parse HEAD`; run 1's call printed
d8a129a2ef2582a59d881619aa8a3b1fb7b53b99 before the run, not into the file; last
line of each the exit status and wall time). No run passed the 20-minute cap and
none was moved to the background. All three are above HF-006's 15 minutes
(D-013 open); they are 90 to 124 s below mission 17's tip. Load average about 0.9
to 1.1 at the end. The fall is not measured per test; mission 18 added no test
the check runs (decision 145).

## Gate M3

At the pushed tip e9076d55c5ebf951aa139bfa637811033d7192db (U3), with no
uncommitted file but the git-ignored drafts, after `./scripts/check` was green
three times there (917, 921, 926 s). The tip d8a129a differs from e9076d5 only by
`meta/CHECKPOINT.md`, `meta/findings/FINDINGS.md`, `meta/journal.md` and
`meta/plan.md` (`git diff --stat e9076d5 d8a129a`). Each call its own foreground
call with a 20-minute timeout.

`uv run discotrade sandbox build` — exit 0, wall 0.64 s

```
sandbox build: present, nothing built
discotrade-sandbox:3b7d75c39621
WALL 0.64 s
EXIT 0
```

`./scripts/gate M3` — exit 0, wall 513.94 s (REVIEW-17 at ca91ecf: 561.66 s)

```
HEAD e9076d55c5ebf951aa139bfa637811033d7192db
 12:27:23 up 61 days, 18:16,  1 user,  load average: 0.87, 1.16, 1.18
G3.1 PASS 3 passed in 194.96s (0:03:14)
G3.2 PASS 9 passed in 158.01s (0:02:38)
G3.3 PASS 10 passed in 159.12s (0:02:39)
gate M3: PASS
WALL 513.94 s
EXIT 0
 12:35:57 up 61 days, 18:24,  1 user,  load average: 1.07, 1.09, 1.13
```

| Item | REVIEW-17 (ca91ecf) | This mission (e9076d5) |
|---|---|---|
| G3.1 | 3 passed, 216.53 s | 3 passed, 194.96 s |
| G3.2 | 8 passed, 183.28 s | 9 passed, 158.01 s |
| G3.3 | 7 passed, 158.80 s | 10 passed, 159.12 s |
| gate M3 wall | 561.66 s | 513.94 s |

Each item is under DESIGN §18.2's 15 minutes (decision 142 (f)). The units' own
item runs: G3.3 179.68 s at U1's tree (da7634b), G3.2 176.83 s at U2's tree
(ac3e67e).

## G3.3 reading

Decision 142 replaces 139 (c)'s clause on raw bars and scores. Each part is a
test of `tests/gates/test_g3_3_prompts.py` over every message of every stored
response of the G3.1 replay (20 trading days 2019-07-15 to 2019-08-09 on
`test_synth`, `m3/`, 27 stored responses: 20 first attempts, 7 retries). The text
search of 139 (c) stays as `test_no_prompt_holds_a_raw_bar_or_a_score`, with
`looked_for` unchanged (142 (d)).

**(a) Accounting** — `test_every_number_of_every_prompt_has_a_source`. Every
numeric token (`m3_harness.numbers`) of every message is accounted for by a source
of its part; the first prompt is split at the five headings (`HEADINGS`, written
in the test) and rebuilt from the sources. At U1, 11,367 tokens of the 20 first
prompts were accounted for, and the 7 retries rebuilt. The sources, and what the
test reads each from:
- part 1, the brief: the cell line's integers (the horizons' bounds,
  `bar_seconds`) from `setup.track`; the brief from the test's own `BRIEF` text,
  the scripted coordinator's template filled with the call's family and horizon;
- part 2, the W profile: the test's own `PROFILE_INTRO` text, asserted equal; the
  keys, the integral leaves, and `format(leaf, ".4g")` of each finite real leaf of
  `anonymize.anonymize(profile.profile(...), call id)`, the `.4g` form written by
  the test;
- part 3, the registry: the test's `INTRO`, `OPEN`, `CLOSE`, `ABSENT` and
  `(none)` texts; per entry, the id, cell and state checked against
  `state/approaches/<id>/meta.json` (state live or dormant), the description
  equal to the stored description sanitized by the test's own `sanitized`, and
  its tokens found in the stored reply of the approach's admitting trial call row;
- parts 4 and 5, the contract and the output format: the text left without the
  cost lines, asserted identical in every first prompt; each cost line matched in
  full against the test's `COST_LINE` pattern, in label order, its four figures
  equal to `format(x, ".4g")` of `prompt.unit_costs` for that label's instrument;
- attempt 2: attempt 1's stored messages; the corpus file the cursor served (the
  k-th response of a model is its k-th file, as G3.2 maps them), byte for byte;
  the test's `RETRY_TEXT` plus the error text of `workers.parse` or
  `validation.sequence.validate` run by the test on attempt 1's stored text
  through the child-process backend (with `(corr_max = <value>)` for a
  duplicate), as G3.2 does.

**(b) Values** — `test_no_harness_figure_meets_a_bar_or_an_earlier_trial_figure`.
Every finite real leaf of the anonymized profile document and every cost mean
behind a cost line (10,080 values at U1) meets, by `math.isclose` at a relative
`RTOL` of 1e-9, no open, high, low or close of any bar of the day's W and T of
any instrument, as stored and times that instrument's factor for the call
(`anonymize.labelling`), and no non-integral figure of a trial row dated before
the day (`metrics_w`, `metrics_t`, `adjusted_w`, `adjusted_t` and the grid's
results). No value met one, so no unit stopped under 141 (a).

**(c) Units** — `test_the_profile_is_free_of_price_and_volume_units`. On the
three days `UNIT_DAYS` 2019-07-15 (the first), 2019-07-26 (between) and
2019-08-09 (the last), for one cell of each of the six families, the profile from
a copy of the state's bar store written by `m3_harness.scaled_store` under the
test's temporary directory (prices times 7/3, volumes times 5/2, roll gaps times
7/3, gap records copied) equals the profile from the store: every finite leaf to
a relative 1e-9 and every null in the same place.

**The five wrong changes of 142 (e)**, each made alone in `src/` at U1's tree, run
as `./scripts/gate M3 G3.3`, and reverted (da7634b's body):

| # | Wrong change | Part red | Test red (and also red) |
|---|---|---|---|
| 1 | W's last close (stored) of each instrument added as a field `last_close` of the profile's common block (`workers/profile.py`) | (b) | `test_no_harness_figure_meets_a_bar_or_an_earlier_trial_figure` (met "SYNB close stored"); also `test_the_profile_is_free_of_price_and_volume_units` |
| 2 | the same close times the call's factor instead (the field listed in `anonymize.SCALED_FIELDS["p1"]`) | (b) | the same test (met "SYNB close times its factor"); also (c)'s test and `test_scaling_leaves_returns_and_scales_a_price_unit_field` |
| 3 | the latest earlier trial row's `metrics_w` Sharpe appended to each registry line (`workers/registry.py`) | (a) | `test_every_number_of_every_prompt_has_a_source`; also `test_the_injected_description_arrives_sanitized` |
| 4 | one open of W (the first instrument's first W open, `.4g`) written into the first cost line's text (`workers/prompt.py`) | (a) | `test_every_number_of_every_prompt_has_a_source` (the text search passed it) |
| 5 | the latest earlier trial row's `metrics_t` `total_return` added as a field `prior` of the profile document (`workers/profile.py`) | (b) | `test_no_harness_figure_meets_a_bar_or_an_earlier_trial_figure`; (c)'s test also red, only because the scaled copy holds no trial ledger (the key sets differ), not as a units failure |

Each of the five turned G3.3 red. Where 142 is silent, U1 chose (its body): (c)
for one cell of every family, since the cell block depends on the family only;
(b) compares the cost means at full precision, their `.4g` text tied to them by
(a); a registry entry is accounted for by its fields, which must equal the stored
approach's.

## Corrections

Decision 143 (c). Commit bodies are not rewritten (decision 128 (d)'s rule).

(a) 446b0a8's body (mission 17 U4) says: "It does not prove the outcomes or days
below; the M3 gate (U5) does." No gate test proved them, at 446b0a8 or at
8d54f9f (mission 17 U5): no gate test of either commit read the manifest's
`served`, `attempt` or `outcome` fields (REVIEW-17 blocker 2). From mission 18,
the test that does is
`tests/gates/test_g3_2_pool.py::test_the_manifest_gives_each_served_files_day_attempt_and_outcome`
(ac3e67e): for `m3/` over the G3.1 replay and `m3_pool/` over the pool replay,
every file the manifest lists with a `served` day gives exactly one call row with
that day, attempt and outcome; every call row with a response maps to a file so
listed; a file listed with no `served` day gives no call row.

(b) 014f06a's body (mission 17 U1) says that a sandbox error on T "writes nothing
to the state directory". Its test,
`tests/test_daily_score_t.py::test_a_sandbox_error_on_t_is_raised_and_recorded_as_no_worker_outcome`,
proves less: the state directory's file list is unchanged and the calls ledger's
bytes are unchanged. It does not compare the contents of the other files
(REVIEW-17 note 3, first half).

## What the tests prove

- G3.3 (U1): on the G3.1 replay's 27 stored responses, every numeric token of
  every message is accounted for by a source of its part as `## G3.3 reading`
  lists them; no harness-computed value of the profile or the cost lines meets a
  bar of the day's W or T (as stored or scaled) or an earlier trial figure at a
  relative 1e-9; on three days the profile is unchanged, to 1e-9, under prices
  times 7/3 and volumes times 5/2. Seen to fail: the five wrong changes of
  142 (e), each with the part and test above.
- G3.2 (U2): for `m3/` and `m3_pool/`, each served file's day, attempt and
  outcome as the manifest records them equal the replay's call rows, the row's
  stored `text` equal to the file's bytes. Seen to fail, each made alone in the
  manifest and reverted, by the new test alone: `m3/nvidia__nemotron-3-super-120b-a12b/0002.md`
  served 2019-07-17 moved to 2019-07-18; `m3_pool/openai__gpt-oss-120b/0005.md`
  outcome `invalid:activity` changed to `invalid:static`;
  `m3/MiniMaxAI__MiniMax-M3/0002.md` attempt 2 changed to 1.
- Gate M3 (U3): `G3.1` to `G3.3 PASS` and `gate M3: PASS` at the pushed tip
  e9076d5, nothing uncommitted but the drafts; the other G3.1 to G3.3 tests, as
  FINAL-REPORT-17 lists them, unchanged in what they assert.
- `./scripts/check` green three times at the tip d8a129a, 0 skipped.
- Frozen files: `git diff --stat 63c6d57 d8a129a -- src config
  tests/fixtures/rejected tests/fixtures/config tests/fixtures/config_frozen.json`
  is empty; under `tests/` only the five files of `## What changed` differ, and
  under `tests/gates/` only `m3_harness.py`, `test_g3_2_pool.py` and
  `test_g3_3_prompts.py`.
- `git status --short` was empty after the three tip runs: no state or job
  directory was written inside the repository.

## NOT PROVEN

- No real provider, model or `claude` binary was called: live checks L3 and L4
  are not run. G3.1 proves the pipeline, not the models.
- The leak checks of G3.3 prove the sources of the G3.1 replay's prompts on
  `test_synth`, the accounting reading each source as the test computes it. No
  prompt of another track, another profile version or another coordinator (a
  real one in place of the scripted) is checked.
- The value comparison of 142 (b) is at a relative 1e-9; a bar transformed
  otherwise than by the units of 142 (c) (prices times 7/3, volumes times 5/2) is
  not shown absent. Part (c) runs on three days and one cell per family.
- The corpus was written by the builder and its yield is arranged, not
  discovered: the 15 trials, the one admission, the duplicate, the retries and the
  injected description are where mission 17 U4 put them.
- The speed figures are from the builder's machine (four cores, shared, varying
  load). `./scripts/check` is 919 to 931 s at the tip, above HF-006's 15 minutes
  (D-013 open).
- U2's clause "a file listed with no `served` day was not served" passes
  trivially today: all 48 manifest entries have a `served` day.
- U2 maps call rows to files by the cursor (the k-th response of a model is its
  k-th file) and checks the bytes; bytes alone cannot name the file, since
  `m3_pool/` holds byte-identical files (two groups of ten).
- U1's wrong change 5 also turned part (c)'s test red only because the scaled
  copy holds no trial ledger, not as a units failure; part (b) is the part that
  caught it.
- The gate ran at e9076d5, not at this report's tip; the tip differs only under
  `meta/` (`## Gate M3`).
- What remains of FINAL-REPORT-17's NOT PROVEN, item by item:
  1. No real provider, model or `claude` (L3, L4): remains (above).
  2. The twenty replay days with the real pool (the rest of L3) are the
     owner's: remains.
  3. Base URL, model ids and cutoffs of `config/models.toml` unverified
     (`verified = false`): remains; this mission added no number from outside the
     project.
  4. Every observation of a replay over 2019 exposed under the fixture cutoffs
     (DESIGN §11.3): remains.
  5. The scripted token counts an estimate by rule (`ceil(characters / 4)`):
     remains.
  6. The corpus written by the builder, its yield arranged: remains (above).
  7. "The leak checks of G3.3 cover the forms the test lists and no other
     spelling": narrowed. For raw bars and scores, parts (a) to (c) of 142 now hold
     as above, within the limits stated above. For symbols, venues, contract names
     and dates it remains: the forms the test lists and no other spelling.
  8. `--provider openai` tested for its refusal only: remains.
  9. Speed figures from the builder's machine, check above 15 minutes: remains
     (above; 919 to 931 s here against 1021 to 1043 s).
  10. D-017's reading of the two- and four-decimal forms awaits the architect:
      closed. Answered by decision 142 (g); U0's status line (e6c33ae); asserted
      by U1 (da7634b).
  11. The wrong change "registry description passed unsanitized" went red only in
      `test_a_raw_stored_description_is_sanitized_in_the_registry`: remains (those
      tests are unchanged; REVIEW-17 note 7 stands, 144 (c)).
  12. `tests/test_gate_script.py`'s two "without gate tests" cases check M4, not
      M3: remains.
  13. The gates ran on HEAD 45dc893 with U5's files uncommitted: closed for M3 by
      U3's run at the pushed tip e9076d5 (and REVIEW-17's at ca91ecf). M2, M1 and
      M0 were not run again (141 (b)); their last runs remain those at 45dc893
      with mission 17 U5's test files uncommitted.
  14. The `## Corpus` and `## Day` figures from one throwaway replay each: each
      served file's day, attempt and outcome for `m3/` and `m3_pool/` is now
      asserted by U2's test. The tokens in and out, the trial and approach ids,
      the admission and dormancy rows, the correlation matrix and its 0.609
      maximum, and the seconds per replay day remain measured only (G3.1 asserts
      every pair at most `corr_max`, not the figures).
  15. FINAL-REPORT-16's carried items (the source test's spelling limits, the
      cache-key removals over two modules only, `__cause__` and `__context__`
      shown `None` for the raised kinds only, FINAL-REPORT-15's carried items,
      the numbers from outside the project in `config/models.toml`): remain.
  16. REVIEW-16 note 9's additions: the refusal of a `run.toml` without
      `[workers]` in `doctor --live workers` untested (to step S5.1): remains; the
      doctor tests of mission 16 U1 never seen to fail: remains; the builder's
      check timings: REVIEW-17 measured one run per unit (865 to 1048 s); this
      mission's times are again the builder's own.
- REVIEW-17 note 3's second half (a call-limit breach on T under the container
  backend raises `DailyError`, untested), note 4 (a failed day's health events
  of steps 3 to 5 appended again on its re-run) and note 5
  (`replay.scripted_start`'s uncaught `KeyError`; `WORKERS_TRANSPORT`) are not
  addressed here: step S4.2 (144 (a), (b)).

## Findings filed and answered

- **D-017** (G3.3's two- and four-decimal forms): **answered**, decision 142 (g);
  status line at U0, e6c33ae.
- **D-013** (`./scripts/check` time): times line at U3, db527f3 (917, 921, 926 s
  at e9076d5; gate M3 514 s). At this tip 919, 922, 931 s, no run past the cap,
  so no line is appended (decision 145). **Open** (144 (g); 121 (c), 140).
- **D-014** (G1.3 against O-3's 10 minutes): open, for the owner; M1 not run in
  this mission (144 (g)).
- **HF-006** (long runs and the 20-minute cap): status line at U0, e6c33ae
  (REVIEW-17 note 12). No run of this mission's units, as their bodies report,
  and no tip run passed the cap. Open.
- **HF-010** (stale worktrees): status line at U0, e6c33ae. `/tmp/rv13-8b9f9be`
  and `/tmp/u5/parent` are still registered at this report (`git worktree
  list`). Open, for the hands Project.
- **HF-011** (`report:` not in the review protocol's skip list): status line at
  U0, e6c33ae. This report's commit carries `meta:`, a prefix
  `meta/REVIEW-PROTOCOL.md` names among those it skips (`plan:`, `meta:`,
  `review:`), in place of mission 17's `report:`. Open.
- **HF-012** (reviewer concurrency): status line at U0, e6c33ae. Open.
- D-015, HF-008 and HF-009 remain open as FINAL-REPORT-17 left them. No other
  finding was filed in this mission.

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-17 blocker 1 (G3.3's raw-bar and score checks skip the `.4g` forms; D-017) | U1, decision 142 (a) to (g): `## G3.3 reading` | da7634b |
| REVIEW-17 blocker 2 (three places claim the gate proves the manifest's day, attempt and outcome) | U2, decision 143 (a), (b), (d): the gate test, the docstring and the manifest's third line; U4, 143 (c): `## Corrections` (a) | ac3e67e, this commit |
| REVIEW-17 note 1 (gate at the tip) | U3, decision 141 (b): gate M3 at the pushed tip e9076d5 | db527f3 |
| REVIEW-17 note 2 (reviewer check times 865 to 1048 s) | stands; D-013 stays open, 144 (g); U3's times line and `## Speed` | db527f3 |
| REVIEW-17 note 3 (014f06a's "writes nothing"; call-limit breach on T untested) | first half: U4, 143 (c), `## Corrections` (b); second half: to step S4.2, 144 (a) | this commit |
| REVIEW-17 note 4 (health events appended again on a failed day's re-run) | to step S4.2, 144 (a) | — |
| REVIEW-17 note 5 (`scripted_start`'s `KeyError`; `WORKERS_TRANSPORT`) | to step S4.2, 144 (b) | — |
| REVIEW-17 note 6 (`tests/test_gate_script.py` change; "child-process backend" rewording) | stands, 144 (c) | — |
| REVIEW-17 note 7 (registry-sanitize wrong change red only in the direct test) | stands, 144 (c); carried in NOT PROVEN | — |
| REVIEW-17 note 8 (doubled "Status" in the D-016 line) | stands, 144 (d): the ledger is append-only | — |
| REVIEW-17 note 9 (FINAL-REPORT-17's corrections and NOT PROVEN) | no action (observation); NOT PROVEN carried item by item above | — |
| REVIEW-17 note 10 (HF-010) | U0 findings line, 144 (f) | e6c33ae |
| REVIEW-17 note 11 (HF-011) | U0 findings line, 144 (f); this commit uses `meta:` | e6c33ae |
| REVIEW-17 note 12 (HF-006) | U0 findings line, 144 (f) | e6c33ae |
| REVIEW-17 note 13 (HF-012) | U0 findings line, 144 (f) | e6c33ae |
| REVIEW-17 note 14 (the brief's "(the gate proves it)") | stands as answered by 144 (e): this mission's brief names the test for each claim; U1's and U2's bodies name theirs | — |

## Acceptance

- `./scripts/check` green three times at the pushed tip d8a129a (919, 922,
  931 s; mission 17's tip 1021 to 1043 s), 0 skipped, so the `container` tests
  ran. Met.
- `./scripts/gate M3` at the pushed tip e9076d5, nothing uncommitted but the
  drafts, printed `G3.1` to `G3.3 PASS` and `gate M3: PASS` (513.94 s). Met.
- G3.3 asserts no raw bar and no score as decision 142 reads them, and each of
  142 (e)'s five wrong changes turned it red. Met (U1).
- A gate test compares each served corpus file's day, attempt and outcome with
  the replay's call rows for `m3/` and `m3_pool/`; the docstring and the
  manifest's third line name it and claim nothing more; each of 143 (d)'s three
  wrong changes turned it red. Met (U2).
- `## Corrections` quotes 446b0a8's and 014f06a's sentences as 143 (c) says. Met.
- No file under `src/`, `config/` or `tests/fixtures/rejected/`, no record under
  `tests/fixtures/config/`, no entry of `tests/fixtures/config_frozen.json`, and no
  file under `tests/gates/` other than the three named changed. Met (the diffs
  above).
- Every unit commit's body lists every file; U0 is `plan:`, U1 and U2 `gate:`, U3
  `meta:`. Met.
- No test uses the network, a secret or the wall clock; no state or job directory
  inside the repository; no test builds the image. Met as the units' tests and the
  check show.
- This file has `## Gate M3`, `## G3.3 reading`, `## Corrections`, NOT PROVEN and
  the review-items table. Met.

VERDICT: mission 18 finished
