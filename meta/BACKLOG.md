# BACKLOG — carried items and the owner's list

Maintained by the architect. The builder does not act on this file. The
mission sequence is in `meta/ROADMAP.md`; this file holds what the roadmap
does not: review items postponed to a named step, and what waits for the
owner.

## Carried review items

Each item names the review it came from and the step that takes it.
REVIEW-1 should-fix 1 to 4, 6 and 7 are taken by mission 2 (step S0.2,
units U1 to U3); item 5 is the owner's (below). REVIEW-2 should-fix 1 and
2, and its note that no conftest blocks sockets (I-11), are taken by
mission 3 (step S0.3, unit U1; decisions-2026-10-12 items 18 to 20).
REVIEW-3 blocker 1 and should-fix 1 to 4 are taken by mission 4 (step
S0.3, units U1 to U4; decisions-2026-10-12 items 30 to 33). REVIEW-4
should-fix 1 and its note on `gaps.py` and `rolls.py` reading the index
before the reader are taken by mission 5 (step S0.4, unit U1;
decisions-2026-10-12 items 34 and 35). REVIEW-3's notes carried to step
S0.4 (reads before `trusted_from`, a roll record with the right `ts` and
the wrong contracts, the unlabelled cost lines of the `backtest` plain
output) are taken by mission 5 (unit U2; items 36 to 38). REVIEW-5
blocker 1, its should-fix 1 (finding D-005), its note on D-004 and its
note on `tests/test_gate_script.py`'s timeout are taken by mission 6
(step S0.4, units U0 to U4; decisions-2026-10-12 items 41 to 43 and 45).
REVIEW-6 should-fix 1 (FINAL-REPORT-6's sentence on the roll probe) is
taken by mission 7 (step S1.1, the final report; item 56), and the
REVIEW-3 note on the socket backstop (I-11) by mission 7 (unit U1; item
47). REVIEW-7 should-fix 1 (the network paths the backstop does not
guard) and 2 (no test separates the whole-span recompute from one chained
through stored positions) are taken by mission 8 (step S1.2, unit U1;
item 58). REVIEW-8 should-fix 1 (no test shows revival counts trading
days) and 2 (the scratch session's unguarded reverse lookup) are taken by
mission 9 (step S1.3, unit U1; items 66 and 67); its notes on the matched
draw's reading and on two transitions for one approach on one day are
answered by item 68 (a test of the second in U1). REVIEW-9 should-fix 1
(the per-day paper update no longer heals an interrupted day) is taken by
mission 10 (step S2.0a, unit U3; decisions-2026-10-14 item 78), and its
should-fix 2 (the untested branch of the not-closed refusal) and 3 (the T
days passed to admission), with finding D-007, by mission 10 (unit U4;
items 77 and 79). REVIEW-10 has no blocker and no should-fix; its note 3
(`paper.adjusted` calls the private `journal._empty()`, and a caller
passing staged records must pass `overlay` too) is taken by mission 11
(step S2.0b, unit U1; decisions-2026-10-14-m11 item 84), its `hands:`
note 7 is recorded as a hands finding by mission 11 U0 (item 90), and the
REVIEW-9 note on decision 68 (b) with the day's admission doing the
displacing by mission 11 (unit U3; item 86). REVIEW-11 has no blocker;
its should-fix 1 (`cli._backtest_result` unregistered) is taken by
mission 12 (step S2.1, unit U1; decisions-2026-10-14-m12 item 92), with
its note 7's list subscript and `replay._adjusted`, and finding D-010
(its note 3) by mission 12 U1 (item 93). REVIEW-12 has no blocker; its
should-fix 1 to 4 (error texts naming a type the text chose, the result
channel the text can write, the static check naming the last offender of
a chain, determinism not checking the bars called) and its notes 2 and 3
are taken by mission 13 (step S2.2, unit U1; decisions-2026-10-14-m13
item 101), its notes 5 and 6 by mission 13 U2 (item 102), and its
`hands:` note 10 is appended to HF-008 by mission 13 U0 (item 108).
REVIEW-13 has no blocker and records `Gate M2: PASS`; its should-fix 1 to
4 (the mount judged by count only, the self-test judged against its own
job, the zero-timeout race of the fork server, the restart notice on a
re-run) and its notes 3, 4 and 5 are taken by mission 14 (step S3.1, unit
U1; decisions-2026-10-15-m14 items 110 to 112), its should-fix 5 and 6
and its `hands:` notes 12 and 15 by mission 14 U0 and U6 (findings D-014,
D-015, HF-010, HF-011; item 113), and finding D-013 (the check's run time)
by mission 14 U2 (item 114). REVIEW-14 has no blocker; its should-fix 1
(a fence line after the last block taken as the description) and its
notes 3, 4 and 7 are taken by mission 15 (step S3.2a, unit U1;
decisions-2026-10-16-m15 item 119), its `hands:` notes 11 to 13 by mission
15 U0 (HF-010, HF-011 lines, HF-012; item 120), and finding D-013 again
(the synthetic source rebuilt every day) by mission 15 U2 (item 121).
REVIEW-15 blocker 1 (the claim that one function reads `NEBIUS_API_KEY`,
which `doctor.py` contradicted) and its note 3's first half (the context
an error keeps) are taken by mission 16 (step S3.2a, unit U1;
decisions-2026-10-16-m16 item 128), its should-fix 1 (`doctor --live
workers` reading raw TOML and a fixed timeout) by mission 16 U2 (item
129), its should-fix 2 (the cache key's calendar and bar-length parts
untested) by mission 16 U3 (item 130), and its `hands:` notes 8 to 10 and
the D-013 times by mission 16 U0 (item 131 (e), (f)). REVIEW-16 has no
blocker; its should-fix 1 (6e3caa5's body says more about its test history
than the disk shows) is taken by mission 17 (step S3.2b, the final report's
`## Corrections`; decisions-2026-10-16-m17 item 133), its notes 10 to 12
and finding D-016 by mission 17 U0 (item 134 (e), (f)), and REVIEW-15's
notes 2 and 4, left to step S3.2b, by mission 17 U2 (item 136 (g), (h)).
REVIEW-17 blockers 1 and 2 (finding D-017; the corpus manifest's served
day, attempt and outcome) are taken by mission 18 (step S3.2b, units U1 and
U2; decisions-2026-10-17-m18 items 142 and 143), its note 1 by mission 18
U3 (item 141 (b)) and its notes 10 to 13 by mission 18 U0 (item 144 (f)).
REVIEW-18 has no blocker and no should-fix and records `Gate M3: PASS`; its
notes 7 to 10 are recorded as hands findings by mission 19 U0
(decisions-2026-10-17-m19 item 154 (b)). The owner's rulings O-23 to O-25
(`meta/decisions/2026-10-17-owner.md`) are built by mission 19 (step S4.1;
items 146 to 153). REVIEW-19 has no blocker; its should-fix 1 (finding
D-018, the rank rule's `p` recomputed on the page) and 2 (the health
panel's failure counts untested) are taken by mission 20 (step S4.2a, unit
U4; decisions-2026-10-18-m20 items 160 and 161), its should-fix 3 (no
speed figure at mission 18's tip) by mission 20's report (item 162), its
note 1 by the owner's O-26 and O-27 (`meta/decisions/2026-10-18-owner.md`),
built by mission 20 (units U1 to U3; items 155 to 159), and its notes 11
to 15 are recorded as hands findings by mission 20 U0 (item 167 (b)).
REVIEW-20's blocker 1 (finding D-022, `persistent_approach`'s `p(N)`
recomputed on the page) is taken by mission 21 (step S4.2a, unit U1;
decisions-2026-10-19-m21 item 169). Its should-fix 1 (which speed run
binds) is taken by mission 21 U1 and U5 (item 170). Should-fix 2 (the
unknown-coordinator test depends on the environment) is taken by U2 (item
171), should-fix 3 with note 5 (the fix session's tools, the protected
paths) by U3 (item 172), and should-fix 4 (`_MONTH_MISSING`'s key
untested) by U4 (item 173). Note 6 is taken by items 169 (e) and 170 (d),
the corrections of FINAL-REPORT-20 by mission 21's report (item 174), and
notes 1 and 8 to 10 are recorded by mission 21 U0 (item 175 (b)).
REVIEW-21 has no blocker and no should-fix; S4.2a is ticked (missions 20
and 21). Its notes 1, 10 and 11 are recorded by mission 22 U0
(decisions-2026-10-19-m22 item 187 (b)), and its note 2 is corrected by
mission 22's report (item 188 (a)). Step S4.2b is mission 22: the items
left to it below are taken by its units U1 to U5 (items 178 to 186).

- REVIEW-21 notes, not carried as work unless named (decision 187 (a)):
  notes 3 to 9 stand as the review accepts them (note 4: `_MONTH_MISSING`'s
  `rows` is guarded through the hash; note 6: `persistent_approach`'s
  zero-clean-days branch holds by reading the code; notes 7 and 8: the
  tests' style); note 1's check times go to finding D-013, open.

- REVIEW-20 notes, not carried as work unless named (decision 175 (a)):
  notes 1 to 4 stand as the review accepts them; note 1's check times go
  to finding D-013, open; note 7 is answered by HF-016's status line.

- REVIEW-19 notes, not carried as work unless named (decision 167 (a)):
  note 3 (U2's body does not say which two-sided form it used), note 5
  (`alerts.revival` copies lifecycle step 3's `stats.trading_dates` call
  rather than sharing a helper; the step that next touches `lifecycle.py`
  may share it), note 7 (inactive health entries kept in `state.json`)
  and note 8 (`dashboard.BAND` is a display band, not an I-10 threshold)
  stand as the review accepts them; note 2's check times go to finding
  D-013, open.
- Left by REVIEW-19 to step S4.2b (decision 167 (a)): `alerts.group_edge`
  raises `ValueError` when `portfolio_clean`'s dates and
  `paper.clean_members` disagree, which fails the day rather than skipping
  the rule (note 4); the detectors' events appended to the health log
  before staging is moved, appended again on a failed day's retry (note 6,
  with REVIEW-17 note 4). Taken by mission 22 (step S4.2b, unit U4;
  decisions-2026-10-19-m22 item 182 (d), (e)): the `ValueError` stays a
  failure of the day, now retried and ended in `run_failed`; an event the
  log holds is not appended again.

- REVIEW-18 notes, not carried as work (decision 154 (a)): note 1 (the
  cell line's integers allowed anywhere in the brief part), note 2 (the
  cost-line allowed set built up across lines) and note 3 (U2 maps call
  rows to files by the cursor, then checks the bytes) stand as the review
  accepts them; note 4's check times go to finding D-013, open.
- REVIEW-17 notes, not carried as work unless named (decision 144): notes
  6 and 7 stand as REVIEW-17 accepts them; note 8 (the doubled "Status" in
  the D-016 line) stands, the ledger being append-only.
- Left by REVIEW-17 to step S4.2, now step S4.2b (decision 144 (a), (b);
  decisions-2026-10-18-m20 item 155): a call-limit
  breach on T under the container backend raises `DailyError`, untested
  (note 3's second half); a failed day's health events of steps 3 to 5
  appended again on its re-run (note 4); `replay.scripted_start`'s uncaught
  `KeyError` on a stored response without `model`, and `WORKERS_TRANSPORT`
  as a module-level test hook (note 5). Taken by mission 22 (units U4 and
  U5; decisions-2026-10-19-m22 items 182 (d), (e) and 186 (c));
  `WORKERS_TRANSPORT` stays as built.
- Left by step S4.1 to step S4.2, now step S4.2b (decision 152 (e), (f);
  decisions-2026-10-18-m20 item 155): the day loop's
  call of the `no_finding` detector, which needs the full daily run's
  records to tell months of live running from a replay; the digest and the
  issues for the alerts mission 19 fires. Taken by mission 22 (units U1,
  U2 and U5; decisions-2026-10-19-m22 items 178 to 180 and 185: the run log
  line of every day, with its `mode`, tells live running from a replay).
- Left by step S4.1 to step S4.3: G4.5, the dashboard's gate test, over
  the replay's state (decision 153 (d) builds its unit tests only).
- REVIEW-11 note 8 (`paper.portfolio` and `paper._series` registered
  `producer` where O-18's table says display and `stage3_money`) is settled
  by decision 153 (c): they stay `producer`, and the one `stage3_money`
  entry is the dashboard's reader, built by mission 19 U5.

- REVIEW-16 notes, not carried as work unless named (decision 134): note 3
  (`ClaudeWorkerProvider` filtering the environment) stands, decision 128
  (b) read as "reads it to use it"; note 7 (the understated cache-key row,
  the "27 hours" comment) stands.
- Left by REVIEW-16 to step S5.1 (decision 134 (b)), which builds the
  doctor: a test of `doctor --live workers` with a `run.toml` that has no
  `[workers]` table, and a `models.toml` path that is a directory reported
  as missing (note 6).
- Left by step S3.2b to step S4.2 (decision 137 (a)): the live default of
  `run-day --provider` and `--coordinator`, chosen with the full daily run;
  `--coordinator` gains the Claude Code form there. The Claude Code form is
  taken by mission 20 (step S4.2a, unit U5; decisions-2026-10-18-m20 item
  163); the live defaults go to step S4.2b, taken by mission 22 (unit U5;
  decisions-2026-10-19-m22 item 186).
- For step S4.3: the fixture models of `tests/fixtures/config/models.toml`
  have cutoffs in 2024 and 2026, so every approach observation of a replay
  over 2019 is exposed (DESIGN §11.3), and no finding alert can read a
  clean day. G4.2 needs clean paper days; S4.3 gives its replay models
  whose cutoffs precede it, as new fixture records (no existing record
  changes).

- REVIEW-15 notes, not carried as work unless named (decision 131): note 1
  (`model_skipped` also raised when the fallback replaces the model, with
  `replaced: true`) stands as built; note 5 (the synthetic cache has no
  bound) stands as built.
- Left by REVIEW-15 to step S3.2b (decision 131 (b), (c)): whether a
  lifecycle row to `dormant` dated D, written by D's own lifecycle step,
  makes its cell weak on D or from D+1, with a test of either, and a test
  of the weak flag at an approach's paper day 0 (note 2); the full list of
  retry messages checked in the duplicate test too (note 4).
- Left by REVIEW-15 to step S4.2 (decision 131 (d)): a timeout of the
  `claude` child kills it but not a grandchild it starts (note 3's second
  half); S4.2 runs `claude` again for the coordinator and takes both.
  Taken by mission 20 (step S4.2a, unit U5; decisions-2026-10-18-m20 item
  166).

- REVIEW-14 notes, not carried as work unless named: note 5 (the profile's
  tests do not tell the adjustment anchor apart; roll gaps are additive),
  note 6 (ddof 1 in the mean-reversion block; "``` python" is no block, as
  pinned) and note 8 (`registry.lines()` reads every approach of the state
  directory; one track per state in this series) stand as built
  (decision 119 (e)).
- Left by step S3.2a to step S3.2b (decision 118): the generation called by
  `run-day` and `replay` (with the provider and coordinator options of
  §16.4 and the scripted provider's cursor built from `calls.jsonl`),
  scoring on T with both measures, the trial rows with model, version and
  cutoff, the worker corpus, the M3 gate tests, and the rest of live check
  L3 (twenty replay days with the real pool). REVIEW-11's note on G1.3's
  scenario (one admission line with a non-zero `avg_position`) may be
  taken there if S3.2b touches the scenario. Taken by mission 17
  (decisions-2026-10-16-m17 items 135 to 139; the cursor is built from the
  stored responses, item 137 (c)); `replay --provider openai` is built
  there and tested for its refusal only, so the twenty days with the real
  pool stay the owner's live check L3. G1.3's scenario is not touched
  (O-19); REVIEW-11's note on it stays with step S4.1 or S4.3. Step S4.1
  does not take it either: the scenario belongs to G1.3, which changes only
  by the owner (O-19, O-25); it is listed for the owner below.

- REVIEW-13 notes, not carried as work unless named: note 8
  (`changes_bars_in_place.py` is rejected only for being flat; nothing
  detects an in-place change of `bars` itself) stands as O-22 allows; note
  7 (the unused `fail()` helper of `tests/gates/test_g1_3_lifecycle.py`)
  stays, that file changing only by the owner (O-19); note 6
  (`tests/test_gate_script.py` checks the M2 count, not the printed item
  lines) stands; G2.5's 64 MiB tolerance and 5 s kill grace (REVIEW-13
  68bee5f) are the test's own bounds, disclosed in FINAL-REPORT-13.

- REVIEW-12 notes, not carried as work unless named: note 4 (the
  subprocess backend leaves a forked grandchild after a clean exit; its
  CPU-time and memory-limit branches are not shown firing; `build_job`
  still accepts an explicit `limits=`; `trusted_hashes` re-hashes every
  trusted file on every run) is not carried (decision 107: that backend
  runs only repository sources and is not a boundary; the step that next
  touches `process.py` for speed may cache the hashes); note 9's readings
  (the approaches compared are those live or dormant after `D`; `|r| ==
  corr_max` passes; a function-object submission skips the static stage)
  stand as built.

- REVIEW-11 notes, not carried as work unless named: decision 84 said
  the existing tests of `tests/test_exposure.py` stay unchanged while it
  replaced what one of them asserted, and the builder changed that test
  without filing a finding (a kit that changes what a test asserts names
  the test; the briefs since say so); `paper.adjusted` does not refuse a
  day missing from `positions.parquet` while `unit.parquet` holds it
  (decision 78's heal repairs it the next day; the step that next touches
  `paper.py`'s records may refuse it); the U3 "not rewritten" test writes
  the parent's format by hand; decision 79 (b)'s replay test passes on the
  plain measure too; G1.3 tells the two measures apart only through
  dormancy and return, every scenario line's adjusted admission score
  equalling its plain one, and step 3's return by displacing the weakest
  is not driven by G1.3 (step S3.2 or S4.1, whichever next touches the
  scenario, may give one admission line a non-zero `avg_position`); the
  rest of note 7 (the audit's module-wide match of the name `paper`, the
  one-hop call through `_figures` counted where only the plain figure is
  used, an uncalled nested function counted) and note 8 (`paper.portfolio`
  and `paper._series` are `producer` where O-18's table says display and
  `stage3_money` for the one condition) are step S4.1's, which next
  changes the register and builds the stage-3 reader; `table.build`'s
  `positions()` closure duplicates `paper._read_staged`, and the test
  helpers `own_journal`/`own_unit` cache by state path (the step that next
  touches `table.py`); G1.3 went from 450 s to 518 s and the per-day cost
  grows with history unprofiled (step S4.3, whose replays are longest,
  measures it if an M4 item nears 10 minutes). The per-day growth is taken
  by mission 20 under O-26 (step S4.2a, units U1 to U3;
  decisions-2026-10-18-m20 items 156 to 158).

- REVIEW-10 notes, not carried as work unless named: a month file changed
  on disk during a day run after its first verified read is served from
  the run's cache and refused only by the next day run (decision 80 (b)
  permits it), and no test drives a partial append that fails mid-day
  while the day continues; `state._column_fields` reads the private pandas
  attribute `column._values` (pinned by `tests/test_speed_pins.py`; the
  step that next touches `state.py` may use `column.array`); the paper
  heal compares dates only, and a death between the `journal/` and
  `ledger/` moves of `_move` still loses that day's lifecycle and rank
  rows (left by step S4.2b, whose retry covers a day that raises, not a
  process that dies mid-move, to step S5.1: its offline doctor may name a
  state tree changed since its last commit; decisions-2026-10-19-m22 item
  187 (d)); the
  Saturday test of decision 79 (a) does not assert SYNX's bars had
  closed, and the mission 8 equivalence test shares `latest_closed_day`
  with the code under test.

- REVIEW-9 notes, not carried as work unless named: the net-return
  rank-persistence statistic G1.1 reports goes to a pytest warning that
  `scripts/gate` does not print (step S2.0b, which runs gate M1 again, or
  step S4.1, which builds O-5's net version beside the timing statistic,
  may make it readable); G1.3 does not assert the random pool's seeds as
  literals (a deterministic rule, decision 64); no test drives a block row
  due on a weekend day, the candidates file's refusal of a symlink or a
  `..` path, or decision 68 (b) with the day's admission doing the
  displacing (taken by mission 11, unit U3).

- REVIEW-8 notes, not carried as work: a state journaled before the
  controls existed would fail `journal.py`'s carry check (no state of this
  series predates the controls; no step takes it unless one does); the
  `if not dates` branch of the rank-persistence population rule is
  untested; a month whose 1st is a non-trading day on every calendar is
  met by G1.1's one-year replay on `test_synth` (all `synth_week`), not by
  a unit test.

- REVIEW-7 notes, not carried as work; the step that next touches the
  file may take them: `init_state` is not atomic (a failed first commit
  leaves a directory every later run refuses, `state.py`); the git
  protocol test checks only the environment dict, not that `_git` passes
  it; `journal.py`'s `REPO_ROOT = parents[2]` finds `reference/` and
  `tests/fixtures/` only from a source checkout (step S5.1 decides
  where trusted sources live in an installed package, decisions-2026-10-14-m13
  item 107); `revised_data` is
  detected by matching the bar store's error text, and `daily.py` calls
  the private `store._indexed_last_ts` (a typed error is sturdier; taken
  by mission 22, step S4.2b, unit U3; decisions-2026-10-19-m22 item 181
  (c)); `journal recompute` leaves its
  `journal_mismatch` health line uncommitted until the next `run-day`.

- Finding D-006 (decision 44): each instrument's evaluation gets a
  freshly loaded strategy, and the cheating strategy of G0.2 is driven
  through the multi-instrument path. Step S2.1, with the sandbox's runner:
  taken by mission 12 (unit U3; decisions-2026-10-14-m12 item 95).
- REVIEW-5 notes, not carried as work; the step that next touches the
  file may take them: `rolls.py` reads, through `store.last_n`, up to 24
  bars before a roll that may lie before `trusted_from`, and uses only
  the first one's `ts`, clipped to `trusted_from` (decision 36 read
  literally says no such bar is read); `gaps.py` checks no listed file's
  hash when `start >= end`; the independent calculation's `ast` import
  check does not catch `builtins.__import__`, `sys.modules` or `runpy`
  (enough for honest code); G0.3 builds the gap-free series with the
  product's `tradingcal.expected_bars`, so a calendar defect shared by
  the generator and the gap check is not seen; G0.4 proves that contract
  roots are collected only through its planted control.

- REVIEW-6 notes, not carried as work: `test_g0_1_reference.py` writes
  the trade floor `1e-9` as a literal rather than reading it from the
  product (a test constant, not an I-10 threshold; if the floor ever
  moves, that test moves with it); the UTC-date grouping of the
  always-open calendar in the U2 self-test cases was not read against
  §5.3 by the reviewer.
- REVIEW-1 note: DESIGN §18.1's rule that tests marked `container` skip,
  with the reason printed, when no runtime is found is not built. The
  mission that adds the first `container` test builds it: step S2.2.
  Taken by mission 13 (unit U2; decisions-2026-10-14-m13 item 102 (g)).
- REVIEW-1 note: every seed a gate test uses is written in the test file,
  not only in a fixture TOML (DESIGN §18.2). Step S0.4 (the first gate
  tests, mission 5, item 40) and every closing step.
- REVIEW-1 should-fix (U6, performance only): `bars fetch` builds a source
  per instrument and the synthetic source regenerates its series from
  `trusted_from` on every fetch. Take it when a replay gate's time limit
  (DESIGN §18.2, 15 minutes) is at risk: step S1.3 (the one-year replay
  of G1.1) at the latest (item 65). Taken by mission 9 (step S1.3, unit
  U3).
- REVIEW-2 note (U1, performance only): `recover` reads and hashes every
  month file of an instrument on every append, and `bars fetch` runs it
  twice per instrument. Take it with the item above: step S1.3 at the
  latest. Taken by mission 9 (step S1.3, unit U3).
- REVIEW-1 note: `tradingcal.in_main_session` cannot represent a main
  session that crosses midnight. No instrument has one; the step that adds
  such an instrument takes it.
- REVIEW-1 note: `config.py` bounds `drop_fraction` at 0.5 without a
  DESIGN source. Harmless for fixtures; no step takes it unless a fixture
  needs more.
- Left by step S1.1 to step S4.2, now step S4.2b (decisions-2026-10-12
  items 50, 51, 54): staging of step 1's writes (bars, rolls, `gaps.jsonl`), the retry
  from a clean staging directory, `run_failed`, the push to a remote, the
  catch-up of missed days with `day_caught_up`, and the weekly journal
  recomputation as step 6 of §16.1. Taken by mission 22 (units U2 to U5;
  decisions-2026-10-19-m22 items 180 to 184). Left to step S2.2 (item 48): running
  approaches through the sandbox instead of the in-process loader; taken
  by mission 13 (unit U5; decisions-2026-10-14-m13 item 105).
- REVIEW-2 note (U4): when `update_rolls` fails after `bars fetch` wrote
  the bars, the command exits 1 and the next fetch records the roll,
  measuring its gap from a later source state. The daily run's staging and
  retry (step S4.2b) take it: mission 22 (unit U3; decisions-2026-10-19-m22
  item 181 (d)).
- REVIEW-2 notes (U5, U6), for step S5.1, which builds the doctor and
  runs a day through the vendor adapter (G5.2): `vendor.py` passes the key
  to the client unstripped while its presence check strips it;
  `doctor --live spreads --days` is not range-checked (0 becomes 20);
  `spreads.py` calls `vendor.py`'s private `_guard`; the marginal-spread
  warning counts any hour that touches the main session while the spread
  rule treats the 09:00 bar as off-session; no test hits an even-count
  median in `spreads measure`.
- REVIEW-2 notes (U3): the 120-day roll look-ahead of `synth.py` is untested
  on sparse calendars, and only `roll_day` is tested for "contract key
  without a schedule". No step takes them unless a fixture calendar needs
  it.
- REVIEW-4 notes, not carried as work: the decision 18 test of `backtest`
  puts the unlisted month file after the window, so an unlisted file
  inside the window is not driven through the command; the `indicators`
  docstring's "no leading NaN" for `ema` holds for input finite at row 0,
  and "a Series or array and a window" is loose for `atr` and `donchian`.
  The step that next touches those files may take them.

## For the owner, before the first builder mission that needs it

- Steps S2.2 and S4.3 need Docker or Podman on the builder's machine.
  Without one the builder asks and the series stops there.
- The architect role's directory, set up as hands `architect/README.md`
  says, with this project's parameters (the plan kit's hand-over message
  gives the block).

## For the owner, at any time (after M2)

- `DESIGN.md` still says `tests/fixtures/hostile/` (§12.5's title and
  text) and lists four M2 items in §18.3, where the owner's
  `meta/decisions/decisions-2026-10-15-owner.md` (O-22) retires the name
  and adds G2.5 (REVIEW-13 note 9). The owner's file wins until the text
  is applied; neither the builder nor the architect role may edit
  `DESIGN.md` (`meta/ARCHITECT.md` §4).
- Gate item G2.3 (`tests/gates/test_g2_3_probe.py`) judges the probe's
  mount against the job it built, by count; mission 14 makes `judge`, the
  self-test and L5 compare count and last close with the store
  (decisions-2026-10-15-m14 item 110), proven by a test outside the gate.
  Whether G2.3 itself should call that store expectation is the owner's,
  by a decision naming the test and the assertion (O-19).
- Finding D-014: G1.3 ran 607 s and 618 s in REVIEW-13, above O-3's 10
  minutes, against the builder's 576 s; O-20 keeps the gate as it is.
  Decided by the owner's O-26 and O-27 (`meta/decisions/2026-10-18-owner.md`,
  after G1.3 reached 1087 s in REVIEW-19): a flat cost per replay day
  within one process, and a 15-minute stop for every M1 item. Built by
  mission 20.
- Findings D-019 and D-020 (mission 20 U1 and U2): the table's figures and
  step 6's figures over a whole paper record cannot be updated day by day
  and stay bit-equal to a full recompute (O-26 item 5). So they are still
  recomputed from the records each day, with a residual growth as plain
  arithmetic. The tip's ratio was 1.166, within O-26 item 4. Accepting this,
  or naming a tolerance or a change to their arithmetic, is the owner's.
  Neither blocks the series while the ratio holds (decision 175 (a)).
- Finding D-021 (mission 20 U3): with exposure passed, `table.adjusted_deflated`
  takes every paper row of a slot dated in the approach's days. The code
  before mission 20 U1 kept the last row of a date, so the two give
  different figures for a slot holding two rows of one date. No writer
  produces such a record, and the G1.3 replay is bit-identical. Saying which
  reading holds, or that `paper.write` refuses such records, is the owner's,
  or the role's at the step that next touches `table.py` (decision 175 (a)).
- `config/run.toml`'s `[coordinator]` table (mission 20, decision 163 (b)):
  the model name, the turn limit, the spending limit and the timeout are
  the project's own choices, unverified until live check L4. Confirming or
  replacing the model is the owner's.
- REVIEW-11's note on G1.3's scenario: every scripted admission line has
  an adjusted admission score equal to its plain one, so G1.3 tells the two
  measures apart only through dormancy and return. Giving one admission
  line a non-zero `avg_position` changes a met gate's fixture, which is the
  owner's under O-19 and O-25. G4.7 (e) tests admission on the adjusted
  measure in step S4.3 meanwhile.
- Finding D-015: O-22 item 1's "copied by path" conflicts with decision
  104 (d)'s hash exclusion; the four run-time entries of the rejection
  suite point at their originals under `tests/fixtures/strategies/` until
  the owner confirms or rules otherwise.

- `config/models.toml` (mission 15, decision 123): the base URL, the model
  ids and the cutoffs are SPEC §17's and the provider's public pages,
  `verified = false` until live check L3. The Claude worker of the cell
  fallback (R-21) has no model configured; choosing one, with its cutoff,
  is the owner's when `workers.claude_fallback` is switched on.

## For the owner, at any time (frozen-config changes)

- REVIEW-1 should-fix 5, finding D-003 (filed by mission 2 U0): the
  `[spec]` `checked` and `source` strings of the eight instrument records
  read as if the exchange's pages were read on 2026-10-12; mission 1's
  report says the values are from memory. `[cost] source = "SPEC.md §17"`
  also covers the spread ticks and `slippage_coef`, which come from DESIGN
  §4.2 and R-5. Changing these strings is a frozen-config change: a
  decisions file and `config/HISTORY.toml` entries.

## For the owner, after the series (not milestones)

- Live checks L1 to L8 (DESIGN §19.3): vendor key, cost estimate and delay;
  measured spreads; the real model pool; a real coordinator call; the
  sandbox on the server; issues on the state repository's remote; every
  unverified fee, tick size, multiplier, session and cutoff; the planted
  market with the real worker pool.
- L1 and L2 as soon as M0 is met (their commands are built in step S0.2),
  while the data layer is fresh; they need the vendor key and do not stop
  the series.
- The slippage coefficient (0.02, R-5) calibrated against real fills in
  stage 2.
- The readings of DESIGN §20 (R-1 to R-28), to confirm or replace.
- SPEC §15's decisions: the length of T; the alert thresholds; where the
  dashboard is hosted; the stage-3 gate values; the money limits.
- Token budgets in `config/thresholds.toml` (R-19 placeholders).
- The architect's decisions of 2026-10-12
  (`meta/decisions/decisions-2026-10-12.md`), in particular item 2 (a
  stopped feed counts as missing bars to the end of the day, so generation
  is skipped), item 5 (an interrupted bar append is completed, not
  refused) and item 23 (how a basket's daily return is formed when its
  instruments have different calendars), to confirm or replace.

## Deferred to v2 (SPEC §15)

Workers with their own tool loop; cross-asset and portfolio-level
approaches; limit-order modeling; weighted allocation.
