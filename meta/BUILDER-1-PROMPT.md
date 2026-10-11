# BUILDER-1-PROMPT — discotrade mission 1: skeleton, config, calendar, bar store, gap check, null market

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 1. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-1.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 1 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`DESIGN.md` (§0 to §5.5, §9.2 for the content hash, §15.2 for the health
event, §17.1, §18.1 and §18.2 are this mission; read §2 twice), `SPEC.md`
§1 to §4 for intent, and
`meta/CHECKPOINT.md` (a unit in progress means §R first). There is no
earlier review: this is the first mission of roadmap step S0.1.

---

## Mission

Build the ground everything else stands on: the project skeleton with its
two gate scripts, the configuration records with the real track and its
eight instruments, the trading calendar, the append-only bar store, the gap
check, and the null synthetic market that later missions test against
(DESIGN §3, §4, §5.1 to §5.4, §17.1, §18.1, §18.2). It does not build bar
sources other than the null market, rolls, the adjusted series, spreads,
the backtester or any state beyond the bar files; those are steps S0.2 and
S0.3. This mission does not close a milestone. Finish with a report whose
first line the playbook can match.

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
- Your final reply begins with exactly one of: `VERDICT: mission 1
  finished` | `VERDICT: mission 1 blocked <unit>` | `VERDICT: question <one
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

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S0.1), rewrite
`meta/CHECKPOINT.md` for this mission, and start `meta/journal.md`. Nothing
else. Gate: the three files are committed and pushed in one `plan:` commit.

**U1 Skeleton and the two gate scripts (DESIGN §3, §18.1, §18.2; I-11,
I-12, I-14).** `pyproject.toml` (uv, src layout, package `discotrade`,
console script `discotrade`, the runtime dependencies and the `dev` extra
that DESIGN §3 names, ruff and pytest configuration with the markers
`gate`, `gate_m0` to `gate_m5`, `container`, `network`, `live`), `uv.lock`,
`.gitignore` (at least `.venv/`, caches, `meta/drafts/`),
`src/discotrade/__init__.py`, `src/discotrade/cli.py` (`--help`,
`--version`, and the `--state`, `--track`, `--config` and `--as-of`
options with the rule that a state directory inside this repository is
refused), `src/discotrade/clock.py` (the injected clock: a real one and a
fixed one), `scripts/check`, `scripts/gate` (the whole gate, or one item),
`tests/conftest.py` (under `DISCOTRADE_GATE=1` a skip is a failure),
`tests/test_cli.py`, `tests/test_gate_script.py`, a short `README.md`.
Gate: `./scripts/check`, run by hand and not from inside a test, prints
`check: green` and exits 0, and it does not collect a test marked `gate`;
a test runs `scripts/gate M0` as a child process and sees a non-zero exit
and `gate M0: FAIL`, because a milestone with no gate tests has not
passed; tests prove the refusal of a state directory inside the
repository, that `--as-of` sets the clock, and exit status 2 on a usage
error.

**U2 Configuration records (DESIGN §4.1, §4.2, §4.3; I-9, I-10).**
`src/discotrade/config.py` (frozen records for track, instrument and
thresholds; unknown keys refused by name; the `checked`, `source`,
`verified` companions; exactly one fee form; the `test_only` rule; cells in
families-then-horizons order), `config/tracks/hourly.toml`, the eight
records under `config/instruments/` with SPEC §17's costs and
`verified = false` and the slippage coefficient DESIGN §4.2 gives,
`config/thresholds.toml` exactly as DESIGN §4.3 gives it,
`tests/fixtures/thresholds_v1.toml`, the frozen-config map
`tests/fixtures/config_frozen.json` with the track and instrument values,
an empty `config/HISTORY.toml` with its test (DESIGN §4.3), and under
`tests/fixtures/config/` the fixture configuration of DESIGN §18.2 and
§18.3: six synthetic instruments (four that can be shorted with a
per-contract fee, one that cannot be shorted, one with `fee_bps`), the
track `test_synth` on the first four with the window lengths §18.2 gives,
the track `test_mixed` on one of the four plus the other two, and
`thresholds_gate.toml` with the test that it differs from the production
file in the keys §18.2 lists and no other; then the `discotrade config
check` subcommand, and `config check` added to the smoke test in
`scripts/check`.
Tick sizes, multipliers, main sessions and listing dates that SPEC does not
give come from the exchange's public contract specifications, each with
its source and `verified = false`. Gate: tests for every refusal above;
the thresholds history test of DESIGN §4.3; the windows of DESIGN §4.1 for
a given day on a fixture calendar stub or plain dates (the calendar itself
is U3; here W and T are tested as date ranges); a test that fails when any
file under `src/` contains, as a whole word, an instrument symbol or venue
found in the repository's `config/` (I-9); `uv run discotrade config
check` exits 0 and lists every unverified value.

**U3 Trading calendar (DESIGN §5.3, §4.3 frozen config).** `src/discotrade/tradingcal.py`,
`config/calendars/cme_globex.toml` (the weekly schedule, the daily break,
and the dated closures the sub-agent can source for 2019 to 2027, each
with `checked`, `source`, `verified = false`), an `always_open` calendar
and a small synthetic calendar with one closure under
`tests/fixtures/config/calendars/`, the calendar's values added to
`tests/fixtures/config_frozen.json`, and `config check` loading calendars.
Gate: tests for whether the market is open, the trading date of a bar,
the expected bar times and the main session, across a week with the
spring clock change and a week with the autumn one, a weekend, the daily
break and a closure; a hypothesis test that every expected bar overlaps an
open interval and no bar inside a closed interval is expected. The real
closure dates are NOT PROVEN and the report says so.

**U4 Bar store (DESIGN §5.1, §5.2, §9.2 content hash; I-5).**
`src/discotrade/bars/__init__.py`, `src/discotrade/bars/store.py`,
`src/discotrade/state.py` holding only the content hash function of DESIGN
§9.2 for now, and tests. Gate: tests that the writer refuses a bar that
has not closed, a bar not later than the last stored one and a duplicate;
that an append leaves every old row identical; that month files split on
the UTC month of `ts`; that the index records first and last `ts`, row
counts and content hashes; that the reader returns a half-open range and
the last `n` bars ending at a bar; and that the reader refuses a month
file whose content no longer matches the index.

**U5 Gap check (DESIGN §5.4, §4.1 windows, §15.2 health event).**
`src/discotrade/bars/gaps.py`, the `discotrade bars gaps` subcommand,
tests. The check returns the health event of DESIGN §15.2 as a value; the
health log itself is a later step's. Gate: on stored bars with known
bars removed, the check reports exactly those bars and appends each once
to `gaps.jsonl`; it reports none across the daily break, the weekend or a
closure; the fraction for a window is pooled over the track's instruments;
above `gaps.max_fraction` in W or in T the result says generation is
skipped and carries a `data_gaps` health event, and at or below it does
not.

**U6 Null synthetic market (DESIGN §5.5 interface, §17.1 without
contracts).** `src/discotrade/sources/__init__.py`,
`src/discotrade/sources/base.py` (the `BarSource` protocol),
`src/discotrade/sources/synth.py` (the null market on a calendar, with the
dropped-bar option and the instrument that cannot be shorted; contracts
and `fetch_contract` are step S0.2 and raise a clear "not built" error),
and `discotrade bars fetch` for a track whose instruments use the `synth`
adapter (parameters from each instrument's `[source]` table, the range
ending at the `--as-of` instant), writing closed bars through the store
and running the gap check.
Gate: the same seed gives identical bars and a different seed different
ones; highs and lows enclose open and close; bars exist only at expected
times; over two synthetic years the hourly returns of each instrument have
a mean within four standard errors of zero and a lag-1 autocorrelation
within four standard errors of zero; `uv run discotrade bars fetch` into
a temporary state directory followed by `discotrade bars gaps` reports
exactly the dropped bars.

**U7 Final report.** `meta/FINAL-REPORT-1.md` (drafted under
`meta/drafts/`, moved in by this commit): what changed (sha per unit),
what the tests prove, NOT PROVEN (mandatory: at least the externally
sourced config values and closure dates), the findings filed, and a
`## Review items` table (empty for this mission, with one line saying no
review precedes it). Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- `uv run discotrade config check` exits 0 on the `hourly` track with its
  eight instruments.
- `./scripts/gate M0` exits non-zero with `gate M0: FAIL` (no gate tests
  exist yet; they are step S0.3's).
- No test uses the network, a secret or the wall clock; no file under
  `src/` names a market.
- `meta/FINAL-REPORT-1.md` exists with NOT PROVEN and the review-items
  table.
