# REVIEW-18 — cold review of mission 18 (step S3.2b continued; closes M3)

Base: 384ee2e (`review: mission 17`, the last `review:` commit). Range
`384ee2e..origin/main` = 63c6d57..74a80af, ten commits. Unit commits: da7634b
(U1, `gate:`) and ac3e67e (U2, `gate:`); the rest are `plan:` (63c6d57, e6c33ae)
and `meta:` (3522d4f, e9076d5, db527f3, d8a129a, 95d7585, 74a80af), read for
forbidden edits only. One sub-agent per unit commit; the two ran in the
foreground side by side (HF-012).

## Gate

Gate M3: PASS

Run by the reviewer at the pushed tip 74a80afde92a4dcae565b983afd0998dab2c8cb7
(= `origin/main`, `git status --short` empty), after `uv run discotrade sandbox
build` (`sandbox build: present, nothing built` / `discotrade-sandbox:3b7d75c39621`),
as one foreground call with a 20-minute timeout. The tip differs from e9076d5,
where the builder ran the gate, only under `meta/`.

```
74a80afde92a4dcae565b983afd0998dab2c8cb7
 13:55:11 up 61 days, 19:44,  1 user,  load average: 1.58, 2.31, 2.20
G3.1 PASS 3 passed in 503.56s (0:08:23)
G3.2 PASS 9 passed in 594.82s (0:09:54)
G3.3 PASS 10 passed in 456.53s (0:07:36)
gate M3: PASS
EXIT 0 WALL 1559.968941612 s
 14:21:11 up 61 days, 20:10,  2 users,  load average: 5.23, 6.28, 6.23
```

The times are about three times the builder's (514 s): the run shared the
four cores with two reviewers' `./scripts/check` runs and, from about 14:13,
an unrelated project's five parallel pytest processes (load 7). Each item stayed
under DESIGN §18.2's 15 minutes. The call passed the tool's 20-minute cap and
was moved to the background by the harness; it was waited for to its end
(see Notes, hands).

Item by item, against DESIGN §18.3 M3:

- **G3.1** (twenty replay days, null market, scripted provider over a corpus of
  three model families, at least ten mutually distinct valid candidates):
  `tests/gates/test_g3_1_candidates.py` is unchanged in this mission and was read
  item by item by REVIEW-17; its three tests (span and configuration, at least
  ten trials from the three makers, every pair at most `corr_max` on W of the
  later day) passed. No loosening.
- **G3.2** (no cell always served by one model; a retry carries the error
  text; every response stored in full; removal after a full window with the
  health alert; the token budget ends generation while journaling completes):
  each clause has a test (`test_no_cell_is_always_served_by_one_model`,
  `test_a_retry_carries_the_error_text`, `test_every_response_is_stored_in_full`,
  `test_a_failing_model_is_removed_after_a_full_window`,
  `test_the_token_budget_ends_generation_and_the_day_is_journaled`), unchanged
  in what they assert. New: `test_the_manifest_gives_each_served_files_day_attempt_and_outcome`
  asserts decision 143 (a)'s three clauses for both `m3/` (G3.1's replay) and
  `m3_pool/` (the pool replay), reading the manifest with `tomllib`; it adds to
  "stored in full" and loosens nothing. Its third clause (a file without
  `served` was not served) is vacuous today, as the report says.
- **G3.3** (no symbol, venue, contract name, calendar date, raw bar or score; the
  labelling differs; the scaling function leaves returns and scales a
  price-unit field; the registry block sanitised): the symbol/venue/contract/date
  test, the labelling test, the scaling test and the two sanitising tests are
  unchanged. "No raw bar" and "no score" now hold as decision 142 reads them:
  (a) `test_every_number_of_every_prompt_has_a_source` fails on any numeric token
  of any stored message that no source of its part accounts for, whatever its
  value; the parts are split at the five headings and the message rebuilt from
  them; cost lines are matched in full with exact `.4g` figures of
  `prompt.unit_costs`; the contract and output parts less the cost lines are one
  text across all first prompts; attempt 2 is rebuilt from attempt 1, the
  served corpus file and the recomputed retry text. (b)
  `test_no_harness_figure_meets_a_bar_or_an_earlier_trial_figure` compares each
  finite real leaf of the anonymized profile and each cost mean with every OHLC
  of the day's W and T of every instrument, stored and times the call's factor,
  and every non-integral figure of earlier trial rows, by `math.isclose` at
  1e-9. (c) `test_the_profile_is_free_of_price_and_volume_units` uses the first,
  a middle and the last day, prices x7/3, volumes x5/2, roll gaps x7/3, nulls in
  place and finite leaves to 1e-9. (d) `looked_for` and the text search are
  unchanged (the diff touches only docstrings there). The da7634b reviewer saw
  wrong changes #1, #4 and #5 of 142 (e) turn the named tests red; #2 and #3 are
  the builder's alone.
- No gate test was made to pass by a special case in product code: no file under
  `src/` changed in the range.

## Blockers

None.

## Should-fix

None.

## Notes

1. Decision 142 (a) part 1 allows the cell line's integers (horizon bounds,
   `bar_seconds`) anywhere in the brief part, not only in the cell line
   (`tests/gates/test_g3_3_prompts.py`, the part-1 check of
   `test_every_number_of_every_prompt_has_a_source`). A token equal to one of
   those three integers elsewhere in the brief would pass. That is no less than
   the decision says, so it is not a should-fix.
2. In the cost-line check the allowed set builds up across lines
   (`allowed |= cost_line_sources(...)`). It is harmless, because each line must
   match `COST_LINE` in full with its own four figures (da7634b reviewer).
3. U2 maps call rows to files by the cursor (the k-th response of a model is
   its k-th file) and then asserts the bytes are equal. It does not identify the
   file by bytes alone, as 143 (a) words it, because `m3_pool/` holds
   byte-identical files. The commit body and the report say so. It is accepted
   as the simplest choice where the design is silent.
4. The reviewers' one `./scripts/check` run each took 1105.0 s (da7634b) and
   1108.2 s (ac3e67e). Each ran beside the other reviewer and the gate, about
   95 s under the 20-minute cap. The builder's tip runs took 919 to 931 s.
   D-013 stays open.
5. The `## Corrections` section of FINAL-REPORT-18 quotes 446b0a8's and
   014f06a's sentences as decision 143 (c) asks. It names the U2 test and says
   what 014f06a's test proves. Its NOT PROVEN covers the five mandatory items
   and carries FINAL-REPORT-17's items one by one. The sub-agents found nothing
   that contradicts it. U1's wrong changes #2 and #3, and the builder's three
   check runs per unit, were not reproduced here.
6. Forbidden edits: none. 63c6d57 (the architect's kit) adds
   `meta/BUILDER-18-PROMPT.md` and the decisions file and changes `KIT.md`.
   `git diff --stat 384ee2e origin/main -- src config tests/fixtures/rejected
   tests/fixtures/config tests/fixtures/config_frozen.json DESIGN.md SPEC.md
   PLAYBOOK.toml .claude templates docs` is empty. Only `plan:` and `meta:`
   commits touch `meta/plan.md` and `meta/CHECKPOINT.md`. db527f3 carries only
   the one FINDINGS line, as U3 says.
7. hands: the gate call passed the tool's 20-minute cap under outside load and
   the harness moved it to the background. The reviewer had to poll its output
   file to wait for it. The protocol's "in the foreground with a timeout" cannot
   be kept for gate M3 on a loaded machine (HF-006).
8. hands: the protocol says one sub-agent per unit "in the foreground" but does
   not say whether they may run at the same time. Here they did, which roughly
   halved the wall time (about 28 min for both) but slowed every check run
   (HF-012).
9. hands: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` are still registered as
   worktrees (HF-010). This review's two worktrees were removed.
10. hands: the sub-agents' reports ran past the protocol's 12-line limit; they
    are recorded below as the agents returned them.

## Per-commit verdicts

### da7634b (U1)

**Review of da7634b (mission 18 U1): pass, no blocker, no should-fix.**

1. **Unit:** U1 of mission 18 makes G3.3's "no raw bar" and "no score" mean what decision 142 says. It claims DESIGN 13.1 to 13.4, 18.2 and 18.3 G3.3, plus I-8 and I-12. Only `tests/gates/test_g3_3_prompts.py` and `tests/gates/m3_harness.py` change.
2. **Test-first: confirmed for the three wrong changes of 142(e) I made.** Each was made alone in `src/`, with the targeted G3.3 tests run.
   - #4 (one W open written into the first cost line): (a) red at `test_g3_3_prompts.py:568`, while the text search stayed green.
   - #5 (an earlier trial's `metrics_t.total_return` as a profile field `prior`): (b) red at `:755`; (a) and the text search stayed green.
   - #1 (W's last close as `last_close` in the common block): (b) red ("SYNB close stored") and (c) red at `:779`.
   - The worktree was clean after each revert.
3. **`./scripts/check` at da7634b: green.** Pytest summary: `2364 passed, 203 deselected in 1101.64s (0:18:21)`, then `check: green`. Wall time 1105.0 s, about 95 s under the 20-minute cap. The sandbox image was already present (3b7d75c39621).
4. **Design conformance: OK.**
   - (a) fails on any token no source accounts for, whatever its value. Parts are split at the five headings and the message is rebuilt from them. Cost lines must match the pattern in full with exact `.4g` figures. The non-cost text of parts 4 and 5 is asserted identical in all first prompts, and attempt 2 is checked as the decision says.
   - (b) compares profile leaves and cost means with the W and T bars of every instrument, stored and times the call's factor, and with non-integral earlier trial figures, at rel 1e-9.
   - (c) uses three days (first, 2019-07-26, last), prices x7/3, volumes x5/2 and roll gaps x7/3, and compares nulls. It covers one cell per family; that is justified because `profile.document` uses only `cell[0]`.
   - `m3_harness.scaled_store` has no seed, date or assertion. `looked_for` is unchanged (the diff touches only docstring lines).
   - I-8, I-9, I-10, I-11, I-12 and I-14 hold: all state goes under `tmp_path`, nothing in `src/` changes, and there is no new dependency.
5. **Forbidden touches: none by this commit.** The 384ee2e..da7634b diff over the protected paths shows only `meta/decisions/decisions-2026-10-17-m18.md`, which the architect's kit commit 63c6d57 (a `plan:` commit) added. The commit does not touch `meta/plan.md` or `meta/CHECKPOINT.md`.
6. **Commit body: no overclaim found.** The failures it describes for #1, #4 and #5 match what I saw, and its check figures (2364 passed, 203 deselected) match my run.

**Not proven by me:** wrong changes #2 and #3, the full `./scripts/gate M3 G3.3` run and its 180 s time (I ran only the targeted tests, about 135 to 146 s each), and the body's "check green three times".

**Notes:** In the cost-line check (`test_g3_3_prompts.py:662-665`), the allowed tokens build up across lines, but the exact full-line match makes this harmless. The check's 1105 s, close to the cap, belongs to D-013. The worktree is removed; other worktrees remain registered: `/tmp/rv13-8b9f9be` and `/tmp/u5/parent` (HF-010), plus `/tmp/rv18-ac3e67e`, which is probably the concurrent reviewer's.

### ac3e67e (U2)

ac3e67e (mission 18 U2): no blockers and no should-fix defects. All six points pass.

1. **Unit:** U2 covers the manifest's served day, attempt and outcome. It claims decision 143 (a), (b), (d), decision 138 (e), REVIEW-17 blocker 2, and DESIGN §18.3 G3.2. `sandbox build` reported "present, nothing built, discotrade-sandbox:3b7d75c39621".
2. **Test-first: PASS.** Each wrong change was made alone in the worktree's manifest and turned the new test red (about 163 s each), then `git checkout ac3e67e -- .` left the tree clean. I chose different rows from the builder's, and these cover both replays:
   - m3_pool `openai__gpt-oss-120b/0001.md` served 2019-07-15 -> 2019-07-16: red at test_g3_2_pool.py:281.
   - m3 `MiniMaxAI__MiniMax-M3/0001.md` outcome duplicate -> trial: red.
   - m3_pool `0001.md` attempt 1 -> 2: red.
3. **`./scripts/check`: green, one run.** "check: green", "2364 passed, 204 deselected in 1105.28s (0:18:25)", wall 1108.2 s. This matches the body's count.
4. **Design: PASS.**
   - All three clauses of 143(a) are asserted for both m3/ and m3_pool/.
   - The manifest is read with `tomllib`.
   - The docstring and the manifest's third line name the test by file and function and claim nothing more.
   - No existing test changed what it asserts; only an import and a constant were added.
   - I-9, I-10, I-11, I-12 and I-14 hold: no src/ or config change, state stays in tmp, no network or clock. No new dependency.
5. **Forbidden touches: PASS.** The only hit in the 384ee2e..ac3e67e range is meta/decisions, and that comes from the architect's kit commit 63c6d57, not this one. No manifest row changed, only the comment line. meta/plan.md and meta/CHECKPOINT.md are untouched.
6. **Body claims: accurate.** No overclaim found. The body is open that the no-`served` clause holds vacuously, since every entry has a `served` day.

Note: 143(a) says to identify the file by bytes, but the test maps it by the cursor (the k-th response is the k-th file) and then asserts the bytes are equal. The commit body says why: m3_pool/ holds files with equal bytes. I accept it as a choice where DESIGN is silent; the result is equivalent.

**NOT proven:** I did not re-run the body's `./scripts/gate M3 G3.2` (9 passed, 177.65 s) or its 3-of-3 check timings.

The worktree /tmp/rv18-ac3e67e is removed. /tmp/rv13-8b9f9be and /tmp/u5/parent are still registered and are not mine.
