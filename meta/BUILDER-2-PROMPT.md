# BUILDER-2-PROMPT — discotrade mission 2: bar sources, rolls, adjusted series, spreads, review-1 repairs

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 2. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-2.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 2 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ, and every unit below cites its items), `DESIGN.md` (§4.2,
§5.1 to §5.7, §15.2 for the health event shape, §17.1, §18.1, §18.2 and
§19.3 L1 and L2 are this mission; §7.3 for how spreads and rolls are used
later; read §2 twice), `meta/reviews/REVIEW-1.md` (its `## Should-fix` and
`## Notes`), `meta/FINAL-REPORT-1.md`, `meta/findings/FINDINGS.md`, and
`meta/CHECKPOINT.md` (a unit in progress means §R first). This is the
mission of roadmap step S0.2.

---

## Mission

Repair what REVIEW-1 found in mission 1's store, gap check, command line,
config check and gate script, as the decisions file settles each point;
then build the rest of the data layer: the synthetic market with
contracts, rolls and the adjusted series, the vendor adapter against a
fake client, the crypto adapter against a mock transport, spread tables
and their measurement, and the offline behaviour of live checks L1 and L2
(DESIGN §5.5 to §5.7, §17.1, §19.3). It does not build the strategy
contract, the backtester, the cost model, metrics or any gate test; those
are step S0.3. This mission does not close a milestone. Finish with a
report whose first line the playbook can match.

## Execution model (binding)

- You are a thin orchestrator. You plan units, write the checkpoint,
  dispatch ONE sub-agent per unit (Task tool, foreground only), verify the
  unit cheaply, record one line, move on. You run nothing longer than `git
  status`, `git log --oneline -5`, and `./scripts/check` yourself.
- Before each unit: write `meta/CHECKPOINT.md` (unit id, intent, what
  "done" means, standing constraints). After each unit: update it and
  append one line to `meta/journal.md`.
- Every unit ends with a commit AND a push. A unit commit carries only its
  own files and its body lists every one; never `git add -A`. The U0 commit
  uses the `plan:` prefix. Drafts of the final report live under
  `meta/drafts/` (git-ignored) until the last unit.
- Retry a failed unit once with the sub-agent's report attached; after two
  failures mark it `blocked` in `meta/plan.md` and continue with units that
  do not depend on it.
- Never edit product code yourself. Never edit `DESIGN.md` or any other
  file `CLAUDE.md` lists as not a builder's (file a finding instead).
- `./scripts/check` three times before every commit, once it exists (U1
  creates it; U0 has nothing to check).
- Your final reply begins with exactly one of: `VERDICT: mission 2
  finished` | `VERDICT: mission 2 blocked <unit>` | `VERDICT: question <one
  line>`.

## Sub-agent brief (give this to every unit sub-agent, verbatim, plus the unit)

    You are implementing one unit of discotrade. Read, in this order:
    CLAUDE.md, the DESIGN.md sections named by the unit and DESIGN.md §2,
    meta/CHECKPOINT.md, the review or report item named by the unit if any,
    then only the files the unit touches. Rules: the design is the spec;
    where it is silent, choose the simplest thing and say so in the commit
    body; write the failing test before the code and confirm it fails;
    tests use no network, no secret, no real model, no wall clock and a
    fixed seed for every random draw; ./scripts/check green three times in
    a row before you commit; one commit, `<area>: <one line>` plus a body
    naming the unit and the DESIGN sections, listing every file, and
    stating only what the tests prove (never a totality claim unless a test
    enumerates the whole space); never `git add -A`; push; never edit
    meta/plan.md, meta/CHECKPOINT.md, DESIGN.md, SPEC.md, PLAYBOOK.toml or
    any file CLAUDE.md lists as not a builder's; add no dependency beyond
    the ones CLAUDE.md names; if the unit needs a design change, stop and
    write a finding to meta/findings/FINDINGS.md instead of improvising (a
    problem with hands itself goes under its "hands findings" heading);
    every number taken from outside the project goes into config with
    checked, source and verified, and is reported as not proven when it
    did not come from a primary source; dispatch nothing in the background
    and run long commands in the foreground with a timeout; report in at
    most 12 lines: sha, files, tests added, what is NOT proven.

## §R Recovery brief

If `meta/CHECKPOINT.md` names a unit in progress and the working tree is
dirty: finish that unit under the sub-agent rules if it can pass
`./scripts/check`; otherwise `git stash push -m "wip <unit> <date>"`,
record in the checkpoint where it stopped and that a stash exists, and
leave the tree clean. Then continue from that unit. Push before taking any
new unit.

## Units, in order

Every unit's sub-agent also reads `meta/decisions/decisions-2026-10-12.md`
and the REVIEW-1 items the unit names. No unit changes a value in a frozen
file (`config/instruments/`, `config/tracks/`, `config/calendars/`,
`config/thresholds.toml`, `tests/fixtures/config_frozen.json` entries that
already exist): a value believed wrong is a finding.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S0.2), rewrite
`meta/CHECKPOINT.md` for this mission, append to `meta/journal.md`, and
append to `meta/findings/FINDINGS.md`: D-001 and D-002 `Status: answered
meta/decisions/decisions-2026-10-12.md` (appended lines, the entries
themselves unchanged), and a new finding D-003 for REVIEW-1 should-fix 5
(the `[spec]` `checked` and `source` strings of the eight instrument
records, and `[cost] source = "SPEC.md §17"` covering DESIGN §4.2 / R-5
values; severity low; direction: the owner rewrites them by a frozen-config
change; `Status: open`, decisions item 17). Nothing else. Gate: the four
files are committed and pushed in one `plan:` commit.

**U1 Store and gap-check repairs (REVIEW-1 should-fix 1 and 4; decisions
2 to 6, 16; DESIGN §5.1, §5.2, §5.4, §15.2; I-5, I-6, I-12).**
`src/discotrade/bars/store.py`, `src/discotrade/bars/gaps.py`,
`src/discotrade/cli.py` (`bars gaps` default day, `bars fetch` recovery
and non-finite drop), `tests/test_bar_store.py`, `tests/test_gaps.py`, and
the CLI tests they need. Gate: tests that a crash simulated after a month
file's rename and before the index write (several months in one append
included) is completed by the next append and by `bars fetch`, with no
row changed and a `store_recovered` notice returned, while a changed old
row, a removed row and an inserted earlier row stay refused as revised;
that the reader's error tells the two cases apart; that the writer refuses
a bar with NaN or infinite values and writes nothing of that call, and
`bars fetch` drops such bars and the gap check then lists them as
missing; that a gap check for a past day `D` ignores stored bars after
`D` (a replay of `D` after later fetches appends nothing new to
`gaps.jsonl` beyond what the original run of `D` appended); that a window
fraction counts an instrument with no stored bar after some date, and an
instrument with no stored bar at all, as missing to the end of `D`, so
generation is skipped; that an append to `gaps.jsonl` leaves every
earlier line byte-identical and a simulated crash before the rename leaves
the old file intact; that `bars gaps` with no day argument checks
§16.1's `D` for the `--as-of` instant (one case where the UTC date and the
trading date differ). A test asserts that `fsync` is called before each
rename (by patching `os.fsync`).

**U2 Command-line, config-check and gate-script repairs (REVIEW-1
should-fix 3, 6 and 7; decisions 7 to 9; DESIGN §3, §4.3, §18.1, §18.2;
I-10, I-14).** `src/discotrade/cli.py`, `src/discotrade/config.py`,
`scripts/gate`, `tests/conftest.py`, `tests/test_cli.py`,
`tests/test_config_history.py`, `tests/test_gate_script.py`. Gate: tests
that `--state` inside a temporary directory laid out as a discotrade code
repository (`pyproject.toml` and `src/discotrade/`) is refused with exit
2 naming I-14 while the package's own location is unchanged, and that
`--state ""`, `--state "  "` and an empty `DISCOTRADE_STATE` exit 2; that
the frozen-config check reports a change from `5.0` to `5`, from `1` to
`true` and from `"1"` to `1` on constructed copies, and passes on the
repository; that `scripts/gate M0 G0.3` run as a child process ends with
`gate M0 G0.3: PASS` or `gate M0 G0.3: FAIL` and never prints `gate M0:
PASS`; that a throwaway test file marked `gate_m0` without `gate` (and
one under a constructed `tests/gates/` without a milestone marker) makes
collection fail naming it. `./scripts/check` still prints `config check:
ok` and `check: green`.

**U3 Synthetic market with contracts and configured generator settings
(REVIEW-1 should-fix 2 and the U6 coverage notes; decision 10; DESIGN
§4.2, §5.1, §5.5, §17.1).** `src/discotrade/sources/synth.py`,
`src/discotrade/config.py` (the `[source]` keys of a synthetic record),
the six records under `tests/fixtures/config/instruments/`,
`tests/test_synth.py`, `tests/test_config.py`. The quarterly roll
schedule, the `contract` column, and `fetch_contract` returning one
contract's bars, each contract's prices being one gap-free underlying
series plus a constant known per contract (the constants and the
schedule from `[source]`); contracts overlap around each roll by at least
24 bars so that §5.6's gap can be measured. Gate: a fixed fetch of each
fixture instrument made before this unit (its content hash written in the
test) is identical after it, so moving the constants changed no bar; a
missing generator key is refused by name; on SYNA, the `contract` column
changes exactly at the scheduled rolls, `fetch_contract` for two adjacent
contracts gives prices that differ by exactly the difference of their
constants at every common bar, and the continuous series equals the
underlying plus the current contract's constant; the hour-of-day
volatility pattern and volume pattern are visible (over two synthetic
years, the ratio of hourly return deviations at the peak hour and the
trough hour is within four standard errors of the configured shape's
ratio); the open gap is uncorrelated with the same bar's return within
four standard errors; and `bars fetch` on `test_mixed` writes SYNA bars
with their contracts.

**U4 Rolls and the adjusted series (DESIGN §5.6, §5.5 `bars fetch`;
decision 16; I-5, I-6, I-12).** `src/discotrade/rolls.py`,
`src/discotrade/cli.py` (`bars fetch` updates rolls after writing bars),
`tests/test_rolls.py`. Roll detection on stored bars, including a roll
whose bar is the first bar of a fetch (compared with the last stored bar);
the append-only `<state>/rolls/<track>/<symbol>.jsonl` with the roll bar's
`ts`, old and new contract, the gap measured from `fetch_contract` at the
latest common bar within 24 bars, and `estimated = true` with
`open(u) - close(u-1)` and a health notice when there is none; the
adjusted series as of a bar `t`. Gate: on SYNA, every recorded gap equals
the difference of the two contracts' constants (to 1e-9) and none is
estimated; the adjusted series as of each of at least 200 bars spread over
two years, rolls included, equals the gap-free underlying plus the
constant of the contract current at that bar (to 1e-9), its last bar is
raw, and volume is never adjusted; the adjusted series as of `t` is the
same whether the store ends at `t` or a year later; a source whose
`fetch_contract` has no common bar gives an estimated gap and a notice; a
second `bars fetch` with no new bar appends no roll, and two incremental
fetches give the same roll file as one.

**U5 Vendor and crypto adapters, and live check L1 offline (DESIGN §5.5,
§19.3 L1; decisions 11, 12, 15; I-9, I-11, I-13).**
`src/discotrade/sources/vendor.py`, `src/discotrade/sources/crypto.py`,
`src/discotrade/sources/__init__.py` (adapter selection),
`src/discotrade/doctor.py` (`--live vendor`, the dispatcher, the usage
errors of decision 15), `src/discotrade/cli.py` (`doctor`),
`pyproject.toml` and `uv.lock` (the `vendor` extra only), a crypto
fixture record under `tests/fixtures/config/instruments/` with a fixture
track for it, `tests/fakes/` (the fake vendor client), `tests/test_vendor.py`,
`tests/test_crypto.py`, `tests/test_doctor.py`. The vendor adapter imports
its client inside the adapter, asks the cost estimate before any fetch and
refuses above `max_cost_usd` (default 5.0), sets `available_until(now) =
now - 24 hours`, fills `contract` through the vendor's symbology, and
implements `fetch_contract`. The fake client has the method shapes the
adapter calls on the real client; which shapes those are, and that they
match the real client, is written in the commit body and is NOT PROVEN
until L1. Gate: with the fake client, a fetch returns bars in the §5.1
schema with `contract` resolved, a cost estimate above the limit refuses
and fetches nothing, the embargo holds, and `bars fetch` on a fixture
track using the vendor adapter writes closed bars and rolls; importing
`discotrade.sources.vendor` does not import the client package; without
`DATABENTO_API_KEY` the adapter and `discotrade doctor --live vendor`
refuse clearly, exit 1 and make no call; a test with a known fake key
proves the key appears in no output, exception text or written file; the
crypto adapter, driven by `httpx.MockTransport`, returns closed hourly
bars in the §5.1 schema with `contract` equal to the symbol and refuses a
malformed response; the I-9 test still passes.

**U6 Spread tables and their measurement, and live check L2 offline
(DESIGN §5.7, §19.3 L2; decisions 13 to 15; I-10).**
`src/discotrade/spreads.py`, `src/discotrade/config.py` (loading
`config/spreads/` and the frozen rule for it; the marginal-spread
warning), `src/discotrade/doctor.py` (`--live spreads`),
`src/discotrade/cli.py` (`spreads measure`), a fixture spread table under
`tests/fixtures/config/spreads/`, `tests/test_spreads.py`. The spread of
an instrument at a bar, in ticks: the measured table's value for the
bar's exchange-local hour when the file exists, else `spread_ticks_main`
in the main session and `spread_ticks_off` outside it. Gate: the rule
gives the table's value per hour, and the main/off values without a
table, across the spring clock change; `spreads measure` on a synthetic
quote sample with known spreads per hour writes a file whose 24 values are
those medians in ticks, with the companions and the sample description;
it refuses to overwrite, errors on an open hour with no quote and writes
nothing, and fills a never-open hour as decision 13 says; `config check`
warns, and exits 0, for a fixture table with a main-session hour above
one tick; without the key `discotrade doctor --live spreads` refuses
clearly, exits 1 and makes no call.

**U7 Final report.** `meta/FINAL-REPORT-2.md` (drafted under
`meta/drafts/`, moved in by this commit): what changed (sha per unit),
what the tests prove, NOT PROVEN (mandatory: at least the vendor client's
method shapes, the crypto endpoint's response shape, every measured value
that is not measured yet, the fixture-only crypto record, and what remains
of mission 1's NOT PROVEN), the findings filed, and a `## Review items`
table with one row per REVIEW-1 should-fix item (1 to 7): the item, its
resolution (the unit and decisions item, or "finding D-003, owner's" for
item 5), and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- `uv run discotrade config check` exits 0 on the `hourly` track with its
  eight instruments, and no value of a frozen file changed in this mission
  (`git diff` of `config/` and of the existing entries of
  `tests/fixtures/config_frozen.json` against the base is empty).
- `./scripts/gate M0` exits non-zero with `gate M0: FAIL` (no gate tests
  exist yet; they are step S0.3's), and `./scripts/gate M0 G0.3` ends
  with `gate M0 G0.3: FAIL`.
- `uv run discotrade bars fetch` on `test_mixed` into a temporary state
  directory writes SYNA's bars with contracts and its roll file.
- No test uses the network, a secret or the wall clock; no file under
  `src/` names a market, a contract root or a venue.
- `meta/FINAL-REPORT-2.md` exists with NOT PROVEN and the review-items
  table covering REVIEW-1 should-fix 1 to 7.
