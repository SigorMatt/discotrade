# REVIEW-11 — cold review of mission 11 (roadmap step S2.0b)

Base: 168d700 (`review: mission 10`, the last `review:` commit). Range
`168d700..origin/main`, tip f85a569. Unit commits reviewed, one sub-agent
each in a worktree at that commit: 93c2f91 (U1), 489e749 (U2), 5962663
(U3), 3ff738a (U4), 95650a4 (U5), 6b61c6e (U6). The sub-agents ran three at a
time, not six, because of HF-008; one `./scripts/check` run took 703 to
796 s. Read for forbidden edits only:
- c3a3f1d, the architect's kit: `KIT.md`, `meta/BACKLOG.md`,
  `meta/ROADMAP.md`, `meta/BUILDER-11-PROMPT.md`,
  `meta/decisions/decisions-2026-10-14-m11.md`;
- 7629de6 (`plan:`): plan, checkpoint, journal, and HF-008 appended to
  `meta/findings/FINDINGS.md`;
- db467d8, e80ccb0, 8da0276, bc96cf2, d9332b1 (`meta:`): plan, checkpoint
  and journal only;
- f85a569 (`report:`): the report, checkpoint, journal and plan.

No unit commit touches `meta/plan.md` or `meta/CHECKPOINT.md`.

`git diff 168d700 origin/main -- config/ tests/fixtures/config/
tests/fixtures/config_frozen.json DESIGN.md SPEC.md PLAYBOOK.toml .claude
templates docs meta/ARCHITECT.md meta/REVIEW-PROTOCOL.md` is empty. Under
`tests/gates/`, only `tests/gates/test_g1_3_lifecycle.py` changed, in U6
(decisions 83 and 90 (a)). `config/models.toml` does not exist.

## Gate

not a closing mission

Decision 83: mission 11 closes no milestone. The builder ran gate M1 item
by item and gate M0 at 6b61c6e; `meta/FINAL-REPORT-11.md` (`## Gate M1`,
`## M0 still passes`) gives the outputs. This review did not run them
again.

## Blockers

None.

## Should-fix

1. U5 (95650a4): the register misses `cli._backtest_result`, a function
   O-18 defines as a reader.
   - At `src/discotrade/cli.py:742-753` it calls `metrics.compute` and sums
     the `net_1x` and `net_2x` columns for each instrument.
   - The audit does not see it, because the column names sit in a tuple
     inside a generator, which is not one of decision 89 (b)'s shapes.
   - O-18 lists "every function under `src/` that reads a return … a
     reference to the columns `gross`, `net_1x` or `net_2x`". O-18's table
     makes `cli`'s backtest output `display`, but the register holds only
     `cli._print_backtest`.
   - Fix: register it as `display` (or `producer`) with a note.
   - FINAL-REPORT-11 says "every function the audit finds" is registered,
     and that is true. Its NOT PROVEN covers this class of miss in general,
     but not this known one.

## Notes

1. U1 (93c2f91): decision 84 contradicts itself, and no finding was filed.
   - Decision 84 says the existing tests of `tests/test_exposure.py` "stay
     unchanged in what they assert", and the U1 brief says that file takes
     new tests only.
   - The same decision replaces decision 81 (d)'s "nothing stored", which
     `test_nothing_is_stored_for_it` asserted.
   - The builder renamed and changed that one test under the brief's
     general rule ("Where a cited decision changes what an existing test
     asserts, the unit changes that assertion and says so"). It said so in
     the commit body and in the report.
   - The result is right. The conflict should have been a finding.
2. U1: `paper.adjusted` refuses a paper day the unit records do not hold.
   It does not refuse a day missing from `positions.parquet` while
   `unit.parquet` holds it; `hbar` is then computed silently over fewer
   rows. Decision 78's heal repairs it on the next day, and a test covers
   that.
3. U2/U3 (489e749, 5962663), D-010: `ledger.py` makes `adjusted`/`plain`
   (and `adjusted_t`/`adjusted_w`) optional as a pair, not required.
   - On the four reasons, a row of decision 87 that lacks them would still
     be appended. The producing code always writes them.
   - The I-5 argument in the body is weak: the check runs on append only,
     so requiring the keys on new rows would not touch old lines.
   - D-010 leaves this to the architect, which is the right route.
     `cli.py` (U3) is outside the unit's file list, is disclosed under
     D-010, and is safe: the track is loaded read-only before
     `--candidates` is read.
4. U3: `test_rows_written_before_are_not_rewritten_after_a_new_day` does not
   run the parent's code.
   - It writes hand-held literals (`OLD_TRIAL`, `OLD_ROW`) whose comment
     says they are what e80ccb0's code wrote.
   - The commit body says "in the parent's format", which is accurate.
     FINAL-REPORT-11's "a ledger line written by the parent's code" reads
     a little stronger than the test shows.
   - The trial-key set matches the unchanged `KEYS`.
5. U3: decision 79 (b)'s replay test passes on the plain measure too. It
   pins T's days. That admission reads the adjusted measure is shown by the
   lifecycle unit tests only. This review reproduced its seen-to-fail on T
   taken as the last `t_days` trading days: red.
6. U6 (6b61c6e): G1.3 tells the two measures apart only through dormancy
   and return (2019-08-13: adjusted -0.619, plain +0.163).
   - Every scenario line has `adjusted_t.sharpe == metrics_t.sharpe` and
     `avg_position` 0.
   - The one displacement (06-11) displaces `always_flat`, whose Sharpe is
     not a number on either measure.
   - So `not_positive`, `too_few_trades`, `free_slot` and admission
     displacement read the same under either measure.
   - Step 3's return by displacing the weakest (O-12) is not driven by
     G1.3; G1.3's item does not list it.
   - FINAL-REPORT-11's NOT PROVEN states the admission half. The U6 commit
     body does not.
   - S4.1 or S3.2, whichever next touches the scenario, could give one
     admission line a non-zero `avg_position`.
7. U5: the audit's call check is looser than its words.
   - It matches a name bound to `discotrade.paper` module-wide, not by
     scope, so a parameter named `paper` would count.
   - A one-hop call to `_figures` counts even where only its plain `[1]`
     is used.
   - A nested function that is never called still counts.
   - A list subscript `df[["net_1x", "net_2x"]]` is not a scanned shape.
     Today it occurs only in registered functions.
   - `replay._adjusted` reads the scripted `adjusted_t` figures for
     validation only and is not registered; it would be `producer`.
8. U5: the classes were read against O-16, O-18 and decision 89 (d).
   - `paper.portfolio`/`_series` are `producer` by decision 89 (d), where
     O-18's table says "display, and stage3_money for the one condition".
     These do not conflict while no stage-3 reader exists, but S4.1 should
     reclassify them.
   - `lifecycle._sharpe_on` as `display` is right: only `figures[1]`
     (`plain`) reaches the rows, and every selection reads `figures[0]`.
   - The three `pending = "S4.1"` entries are the ones decision 89 (c)
     names, and the test holds them as a literal.
9. U4 (3ff738a): `table.build`'s `positions()` closure duplicates
   `paper._read_staged`. The test helpers `own_journal`/`own_unit` cache by
   state path, which is safe today but would go stale if a test rebuilt a
   state in place. `test_mixed_fixture_values` and the mixed re-run test
   pass at the parent as well, as expected for them.
10. Speed: G1.3 went from 450 s to 518 s at 6b61c6e, still under O-3's
    10 minutes. Each U1/U2/U4 measurement adds 0.01 to 0.13 s per replay
    day on the first 30 days. FINAL-REPORT-11 notes that the cost grows
    with history and was not profiled. Nothing here was re-measured.
11. hands: HF-008 held in this review. Three concurrent per-commit
    sub-agents on four cores gave 703 to 796 s per `./scripts/check` run,
    against about 490 s alone (FINAL-REPORT-11). Six at once would likely
    have crossed the 20-minute cap. The protocol still does not say how
    many may run at once.
12. hands: HF-007 again. U5 and U6 change tests only, so protocol step 2
    (revert the non-test files) proves nothing. The sub-agents reproduced
    the bodies' named wrong changes instead: U5 all three of decision
    89 (b). U6's G1.3 seen-to-fail was not re-run (about 9 minutes); it
    rests on the commit body.

## Per-commit verdicts

Each sub-agent's report, with its content unchanged. Its markdown
formatting is reflowed into one plain block per commit.

### 93c2f91 (U1)

```
93c2f91 (u1) — Unit U1, derived exposure records (decision 84; 78, 81; O-4; DESIGN 9.2, 9.3, 16.1, 16.2; REVIEW-10 note 3).
1. Unit — OK. Touches only paper.py, daily.py, tests/test_exposure.py (all in the unit's file list).
2. Test-first — OK. Parent's paper.py+daily.py: tests/test_exposure.py 12 failed, 3 errors, 12 passed (AttributeError UNIT_FILE etc., journal._empty text test fails). Also reproduced wrong changes: heal only on absent files → 3/4 heal cases red; records written on re-run → staged-on-a-new-day-only test red. Reverted; tree clean.
3. ./scripts/check — OK: `config check: ok, 168 unverified values` / `check: green` (732 s wall).
4. Design — OK. hbar = summed position / summed rows, 0 with none; records staged only in daily.py's new-day branch, re-run writes neither; heal per decision 78 (absent file, unit dates ≠ index dates before D, position dates ≠ dates with rows>0); adjusted raises ValueError on absent records / missing paper day (names overlay); paper.py no longer calls journal._empty (removed, not renamed); rebuild test uses state.content_hash (DESIGN 9.2 key-sorted hash). No market names, wall clock, out-of-config numbers, repo state, network, or new deps. NOTE: adjusted only checks unit coverage of paper days — positions rows missing for a day held in unit would silently feed hbar (heal repairs it next day).
5. Forbidden — OK: nothing in config/, tests/fixtures/config*, tests/gates/, meta/plan.md, CHECKPOINT.md or protected docs. NOTE: one existing assertion changed (test_nothing_is_stored_for_it → ..._but_the_records) though the brief says test_exposure.py "new tests only"; decision 84 makes the old assertion impossible and the body discloses it, but no finding was filed for the conflict.
NOT proven: decision 90(c) timings (29.51→32.33 s; 0.3474→0.0118 s) not re-measured; "three greens in a row" checked by one run only.
```

### 489e749 (U2)

```
489e749 (u2) — U2: dormancy/return/displacement on the adjusted measure (O-11, O-12; decisions 85, 87, 62, 63, 68; DESIGN §10.3).
1 Unit: OK — named and sections cited as above.
2 Test-first: OK — parent lifecycle.py+ledger.py → 19 of the changed tests fail (13 test_lifecycle, 4 test_ledger, 1 test_exposure, 1 test_portfolio on the new state_dir kwarg); restored clean. Wrong changes reproduced: plain net_1x in step 2 → 5 red (matches body); W = whole paper record in step 2 → 3 red in test_lifecycle (body's "10" counts steps 2+3).
3 ./scripts/check: OK — "config check: ok, 168 unverified values" / "check: green" (703 s wall).
4 Conformance: OK. Step 2 W = dates of last N paper rows (≤ day), dormant on adjusted<0; step 3 W = dormant's last N rows, each live scored via paper.adjusted(other, W) whose hbar uses that approach's own positions over W (O-12); NaN never triggers dormancy/return, weakest/beats unchanged; _figure writes null. dormant/returned/displaced rows carry both figures (displaced: over the returning approach's W); retired/failure rows carry neither. Existing test changes only add figures with zero exposure; no decision changed. test_portfolio keeps its `== []` assertion. I-9/I-10/I-11/I-12/I-14 clean in diff; no new dependency.
  NOTE: ledger.py keeps one-figure-alone refused and doesn't touch I-5 (append-only unchanged), but makes the figures optional rather than required, so a dormant row without them would still be written; the I-5 rationale is weak (_check runs on append only), the real reason is admission rows pending U3. D-010 leaves this to the architect.
5 Forbidden edits: OK — none of the never-edited files, plan.md, CHECKPOINT.md, config/, fixtures, or tests/gates/ touched. ledger.py is outside the file list but covered by D-010 (next free D number).
NOT proven: the "live scored with dormant's positions" wrong change was not reproduced; decision 90(c) timings (32.43→32.68 s) and "green three times" not re-measured (check run once).
```

### 5962663 (U3)

```
sha 5962663 (U3): no BLOCKER and no SHOULD-FIX; two NOTEs; one thing not proven.
1. Unit — OK. U3, admission on the adjusted measure and the candidates file. Claims O-11..O-13, decisions 86, 87, 48, 63, 68, 73, 79(b), DESIGN §10.3, §4.1.
2. Test-first — OK. Parent's cli/ledger/lifecycle/replay.py: changed tests red (32 failed, 26 errors); restored clean. Wrong changes tried and reverted: score from metrics_t["sharpe"] → 9 red as the body says; live approaches on the plain measure → full-cell weakest test red; T as last t_days trading days in replay.t_days → 79(b) test red on the T-days pin, and with the pin removed red on the verdict (admitted (displaced) instead of not_better_than_weakest). 79(b) still seen to fail.
3. ./scripts/check — OK: `config check: ok, 168 unverified values` / `check: green` (780 s wall).
4. Conformance — OK. Candidates line exactly decision 73's keys + adjusted_t of exact shape (sharpe, sharpe_2x, total_return, total_return_2x, avg_position naming exactly the track's symbols), refused exit 2 before any day runs, nothing on disk changed. Score = adjusted_t["sharpe"], null/NaN → not_positive; too_few_trades reads metrics_t["trades"]. Full cell via _figures: each live approach's own paper.adjusted over T's days with own positions; weakest/beats unchanged. Trial row adjusted_t/adjusted_w (null when absent); admitted/displaced rows adjusted/plain per decision 87. 68(b) via 86(f): rows returned, admitted, displaced; dormancy counts from D. cli.py (D-010) safe: read-only config load before candidates; only change, a bad config exits 1 before the file is read. ledger.py (D-010) adds an optional trial-key pair; KEYS unchanged, old rows valid. Scenario fixtures: other keys identical, only adjusted_t added; sharpe = plain except u4 (0.2, verdict unchanged). I-9/I-10/I-11/I-12 hold; no new dependency.
   NOTE: the "earlier lines not rewritten" test uses hand-written strings in the parent's format, not lines produced by running the parent's code; its trial-key set matches the unchanged KEYS.
   NOTE: the 79(b) replay test passes on the plain measure too; it proves the window only; the adjusted-measure choice is proven by the lifecycle unit test only.
5. Forbidden — OK: no CLAUDE.md-protected file, plan, CHECKPOINT, config, frozen fixture or tests/gates/. Files outside U3's list: cli.py and ledger.py, both recorded under D-010.
NOT proven: that G1.3's admissions with g1_lifecycle.jsonl are unchanged on the adjusted measure (gate not run; expected rows lack the new keys until U6); the always_flat-is-not-a-number argument comes from the commit body only.
```

### 3ff738a (U4)

```
sha 3ff738a (U4): no blockers; points 1 to 5 OK.
1. Unit — OK. U4, the table's adjusted figures (O-13; decision 88; decisions 30, 39, 41, 60, 71; DESIGN 10.4, 8). Changes only src/discotrade/table.py and tests/test_table.py.
2. Test-first — OK. Parent's table.py: 6 of 14 tests fail (the 2 changed existing table tests + 4 new: adjusted figures, dormant window, null adjusted_t, md labels). test_mixed_fixture_values and the mixed re-run test pass on the parent too (expected). Restored clean.
3. ./scripts/check — OK: `config check: ok, 168 unverified values` / `check: green` (772 s wall).
4. Conformance — OK. adjusted_sharpe/_2x = metrics.sharpe of paper.adjusted on net_1x/net_2x over every paper day (mine["date"]), records and overlay=into passed; avg_position = paper.hbar over the same days for every track symbol, 0.0 each with no paper day; adjusted_admission_score = adjusted_t["sharpe"] of the admitted trial row admission_score reads, null when absent; all four null for controls and both portfolio series via _APPROACH_FIELDS; S/E_N/excess and control_moments stay plain net_1x; table.md labels via LABELS; re-run writes nothing on test_mixed. Existing-test changes justified by the four new keys; same_row refactor keeps the old per-field assertions; one other edit (SEEDS → setup.instruments for bh rows) gives the same rows, not mentioned in the body. "Every earlier field unchanged in value" supported indirectly: earlier fields still checked against the test's own (unchanged) computation; no test compares with the parent's output. I-9, I-10, I-11, I-12, I-14 hold; no new dependency.
5. Forbidden — OK. Nothing under config/, frozen fixtures, tests/gates/; plan.md/CHECKPOINT.md differ from 168d700 only through earlier meta commits.
NOTES: table.build's positions() closure duplicates paper._read_staged (simplification only); own_journal/own_unit use functools.cache keyed by state path — safe today, stale if a test rebuilt a state in place.
NOT proven by reviewer: the three "seen to fail" changes (not reproduced), the two decision 90(c) timings, "check green three times".
```

### 95650a4 (U5)

```
sha 95650a4 (u5) — U5, register of return readers and ast audit (O-16, O-18, decision 89; DESIGN §10.3, §10.4, §11). No blocker, two NOTEs.
1. Unit — OK. Body lists all 24 entries with class and note; names the three pending.
2. Test-first — OK (HF-007: tests only). Reproduced decision 89(b)'s three wrong changes, each red, reverted: `_planted` holding "net_1x" in stats.py → fails "unregistered"; _figures' paper_module.adjusted call swapped for _sharpe_on → "does not call paper.adjusted" for _figures, step_rows, admit; pending="S4.1" on admit → test_the_pending_entries_are_the_three_of_decision_89 fails (pending set a literal (module, function, class, "S4.1")).
3. ./scripts/check — OK: "config check: ok, 168 unverified values" / "check: green" (784 s). Test file alone 20 passed.
4. Conformance — OK. Classes match decision 89(d): lifecycle._sharpe_on display (only figures[1] reaches rows; selection reads figures[0]); table._record display per 89(d) (its sharpe becomes S in the pending approach_row); paper portfolio producer per 89(d) vs O-18 table "display/stage3_money" — the newer decision wins; table.build.approach_row pending adjusted, right (computes S/E_N/excess at line 247). Scanner covers every 89(b) shape; independent grep of src/discotrade agrees: exactly the 15 functions holding a shape, all registered.
   NOTE (gaps): list subscript df[["net_1x","net_2x"]] not seen (only in registered functions); cli._backtest_result (net_1x/net_2x via tuple) and replay._adjusted (adjusted_t figures) are unregistered readers, both producer.
   NOTE (loose call check): module-wide name match, not scoped (a parameter named paper would count); one-hop _figures accepted even if only plain [1] used; uncalled nested function counts; `import discotrade.metrics` unaliased unseen as a shape (none in src today).
   I-11, I-9, I-10, I-12, I-14: tests only, no network/secret/clock; no new dependency.
5. Forbidden — OK. Only the two named test files; nothing in config/, tests/fixtures/config/, config_frozen.json, tests/gates/ or meta/.
Not proven: a figure passed under another name, variable or new column (O-18 lists this as known and not proven).
```

### 6b61c6e (U6)

```
6b61c6e (U6): one finding (HF-007), two NOTEs, no blocker.
1. Unit — OK. Mission 11 U6 (part a), G1.3 on the adjusted measure; claims O-15, O-4, O-11..O-13, decisions 74, 81, 85–88, 90(a), DESIGN 10.3, 10.4, 18.3 G1.3. Only tests/gates/test_g1_3_lifecycle.py changed.
2. Test-first — HF-007, not reproduced (tests only; gate item not run as instructed; body records red `3 failed, 7 passed` with step 2 plain, green 516 s). Diff vs 90(a): (a) OK — only expected lifecycle/trial rows, ledger count 9→10, segment-1 table section, decision-88 fields and own adjusted computation changed. (b) OK — imports only costs, journal, cli, config, state; m1_harness only cli; nothing from paper/table/stats/lifecycle. (c) OK — every transition still asserted, same days. (d) OK — SEGMENTS and gate configuration unchanged; a t_days == 7 assert added. (e) OK — nothing weakened; 5-key check stricter (others exactly 5 keys, figured reasons +adjusted/plain compared with own figures). (f) OK — formula = DESIGN 7.2 with h=1, SYNA roll gap per §5.6; R_i(D) summed over bars journaled on D, hbar_i(W) over the subject's rows dated in W (0 with none), mean over the 4 instruments, as paper.adjusted does for approaches.
3. ./scripts/check — OK: `config check: ok, 168 unverified values` / `check: green` (796 s wall).
4. Design — OK, two NOTEs. NOTE (main): every scenario line has adjusted_t.sharpe == metrics_t.sharpe and avg_position all 0, so adjusted == plain at admission; the only displacement (06-11) scores always_flat (positions 0, Sharpe NaN both ways). So not_positive, free_slot, displacement and too_few_trades cannot tell the measures apart; only dormant/returned show the adjusted lifecycle; step 3's "beats the weakest live" (O-12) not exercised. The commit body's NOT PROVEN covers only "scripted figures are not real T figures". NOTE: gate configuration and thresholds untouched; no new numbers reach a gate; T_DAYS/WINDOW are test constants asserted equal to config. I-9, I-11, I-12, I-14 hold; no new dependency.
5. Forbidden — OK: no frozen config, no meta/plan.md or CHECKPOINT.md, no other tests/gates/ file.
NOT proven: that the gap lookup matches the stored bar timestamps (not run; builder's green run suggests it does); the gate item result itself (not re-run).
```
