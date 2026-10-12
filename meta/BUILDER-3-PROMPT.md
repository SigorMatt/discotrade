# BUILDER-3-PROMPT — discotrade mission 3: strategy contract, indicators, evaluation loop, costs, executor, metrics, backtest, review-2 repairs

Kickoff line (the only way this mission is started or resumed):

    Read the builder prompt with the highest mission number in the meta directory and execute the mission below its divider.

Builder prompts are the files `meta/BUILDER-<N>-PROMPT.md`; this is the one
with N = 3. If a builder prompt with a higher number exists, this is not
your mission: read that one instead. If `meta/FINAL-REPORT-3.md` already
exists, this mission is finished: change nothing and reply `VERDICT:
question mission 3 is already finished and no newer builder prompt exists`.

You are the builder for the `discotrade` repository. Read `CLAUDE.md`,
`meta/decisions/decisions-2026-10-12.md` (it wins over `DESIGN.md` where
they differ; items 18 to 29 are new for this mission and every unit below
cites them; items 1 to 17 still bind), `DESIGN.md` (§6, §7, §8 are this
mission; §3 for the layout and the `backtest` command; §5.1, §5.2, §5.3,
§5.6 and §5.7 for the bars, calendars, rolls and spreads it reads; §16.1
for `D`; §18.1; §20 readings R-3, R-5, R-7, R-20 and R-23; read §2 twice),
`meta/reviews/REVIEW-2.md` (its `## Should-fix` and `## Notes`),
`meta/FINAL-REPORT-2.md`, `meta/findings/FINDINGS.md`, and
`meta/CHECKPOINT.md` (a unit in progress means §R first). This is the
mission of roadmap step S0.3.

---

## Mission

Repair the two items REVIEW-2 found in mission 2's bar reader and `bars
fetch`, and add the I-11 socket backstop it noted (decisions 18 to 20);
then build the harness core that evaluates a strategy: the strategy
contract and its loader, the indicator library, the evaluation loop and
its returns, the cost model, the executor and simulator, the metrics, the
three reference strategies and the `backtest` command (DESIGN §6, §7, §8,
§3; decisions 21 to 27). It does not build the independent calculation,
the cheating strategy or any gate test, and creates nothing under
`tests/gates/`: those are step S0.4, mission 4, which closes M0 (decision
28). This mission does not close a milestone. Finish with a report whose
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
- Your final reply begins with exactly one of: `VERDICT: mission 3
  finished` | `VERDICT: mission 3 blocked <unit>` | `VERDICT: question <one
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
(the items the unit names) and the REVIEW-2 items the unit names. No unit
changes a value in a frozen file (`config/instruments/`, `config/tracks/`,
`config/calendars/`, `config/thresholds.toml`,
`tests/fixtures/config_frozen.json` entries that already exist): a value
believed wrong is a finding. No unit creates a file under `tests/gates/`.

**U0 Plan (`plan:` commit).** Write `meta/plan.md` (these units with
checkboxes, the base commit, the roadmap step S0.3, and REVIEW-2
should-fix 1 and 2 as carried items taken by U1), rewrite
`meta/CHECKPOINT.md` for this mission, and append to `meta/journal.md`.
Nothing else. Gate: the three files are committed and pushed in one
`plan:` commit.

**U1 Reader, `bars fetch` default day and socket backstop (REVIEW-2
should-fix 1 and 2, REVIEW-2 note on U5; decisions 5, 18, 19, 20, 3;
DESIGN §5.2, §5.4, §16.1; I-5, I-6, I-11, I-12).**
`src/discotrade/bars/store.py`, `src/discotrade/cli.py` (`bars fetch`'s
default day only), `tests/conftest.py`, `tests/test_bar_store.py`,
`tests/test_cli.py` (or `tests/test_gaps.py`). Gate: tests that
`read_range` and `last_n` refuse when the instrument's directory holds a
month file the index does not list, for one such file that passes
decision 5's test (the error says interrupted append) and one that does
not (the error says revised data point), including a read whose range
does not cover that month; that after `bars fetch` completes the
interrupted append the same reads succeed and return the completed rows;
that `bars fetch` with no `--day` checks the same `D` as `bars gaps` for
the same `--as-of`, in at least three cases including a source whose
`available_until(now)` is `now - 24 hours` (a wrapped synthetic source is
enough) and a case where the UTC date of `--as-of` minus one day differs
from `D`; that a second `bars fetch` at the same `--as-of`, and one at a
later `--as-of` with `--day` set to the first run's `D`, append nothing
to `gaps.jsonl`; that a test not marked `network` or `live` which tries
to open a socket fails with the backstop's error, while the backstop
leaves a test marked `network` alone (a `pytester` run or an equivalent
check of the fixture's marker logic). `./scripts/check` stays green
with every existing test unchanged in what it asserts.

**U2 Strategy contract, loader and indicator library (DESIGN §6.1, §6.2
(the result check), §6.3; decisions 21, 22; I-1, I-2, I-10).**
`src/discotrade/strategy.py`, `src/discotrade/indicators.py`,
`tests/test_strategy.py`, `tests/test_indicators.py`, small strategy
texts under `tests/fixtures/strategies/`. Gate: tests that the loader
accepts a valid text and runs a `position` that uses `indicators` by the
bound name and by `import indicators`; that it refuses, naming the rule,
six parameters, a non-numeric parameter, a `GRID` key not in `PARAMS`,
three `GRID` keys, four values for one key, a text one line over
`max_lines`, and a text with no callable `position`; that changing
`validation.max_lines` in a copied thresholds file changes the line
outcome (the numbers are read from config, I-10); that the result check
refuses NaN, +inf, -inf, 1.5, -1.0000001, a string and a raising call,
each with an error naming the instrument and the bar's `ts`, and clips a
negative result to 0 only when `shorting = false`. For the indicators:
`sma`, `ema`, `rolling_std`, `rolling_max`, `rolling_min`, `returns`,
`zscore`, `rsi`, `atr`, `realized_vol`, `bollinger`, `donchian`,
`volume_zscore` exist; each equals a hand-computed value on a short fixed
input; a `hypothesis` property test, enumerating every public function
of the module (so a function added later is covered), proves that the
value at row `i` is the same whether the input ends at `i` or later; every
public function has a one-line first docstring line.

**U3 Evaluation loop and returns (DESIGN §6.2, §7.1, §7.2, §5.6;
decisions 22, 23, 24; R-20; I-2, I-12).** `src/discotrade/backtest.py`,
`tests/test_backtest.py`. The slice builder, the walk over a window, the
positions and the gross returns per bar, reading bars from the store and
gaps from the roll file. Gate: tests that the slice has exactly the
columns `open`, `high`, `low`, `close`, `volume`, `hour`, `weekday`, an
integer index from 0, at most `history_cap_bars` rows, no date and no
symbol anywhere, prices equal to the adjusted series as of its last row
(`rolls.py`'s, on SYNA across a roll), and `hour` and `weekday` in the
calendar's time zone across the spring clock change; that each call gets
a fresh copy (a strategy that mutates its frame does not change the next
call's frame); that `h(u) = p(u-1)`, `h(u0) = 0` whatever was returned
before the window, the window's last target is recorded and not traded,
and context bars up to the cap precede the window; that window
membership follows each instrument's own calendar (a date where SYNX's
always-open trading date and SYNA's weekly one differ); that `gross`
equals hand values on a constructed store of a few bars with one roll
and one missing bar; that on SYNA across every roll of a two-year store,
for a strategy that is always long and for one that alternates, the
gross per bar equals the gross computed from the gap-free underlying
series (the roll gap is never profit or loss) to 1e-12; that a contract
change with no roll record stops the evaluation with decision 24's error;
and truncation invariance: for a strategy that reads its whole slice, on
all three `test_mixed` instruments, the positions for every bar up to `t`
are identical whether the store ends at `t` or a year later, at no fewer
than three values of `t`.

**U4 Cost model and executor (DESIGN §7.3, §7.4, §5.7; decisions 24, 25,
26; R-3, R-5; I-4, I-15).** `src/discotrade/costs.py`,
`src/discotrade/executor.py`, `tests/test_costs.py`,
`tests/test_executor.py`, and in `src/discotrade/backtest.py` only the
call that turns positions into orders and fills into per-bar rows. Gate:
tests on hand values for each component: `fee` for a per-contract fee
(SYNA) and for `fee_bps` (SYNX); `half_spread` with the half-tick floor
and the spread rule of §5.7 (the fixture spread table for SYNA by
exchange-local hour, main and off values without a table); `sigma` with
`ddof = 1` over the last 24 returns adjusted as of each `s` and divided by
the raw previous close, including a window whose first bars need context
bars, and 0 with fewer than 2 returns; `roll_cost` paid by a carried
position at a roll (twice `|h(u-1)|` times `c(u)`) and not by a flat one,
nor at a window's first bar; `cost`, `net_1x` and `net_2x`; one `Fill` per
`Order` with the fill bar, the raw fill price and the four components
summing to `cost`; the per-bar rows of decision 25 for a constructed
case; the version `c1`; the config hash stable across runs, changed by a
change of a `[cost]` value, of `tick_size` and of one spread-table value,
unchanged by a change of a companion. `SimExecutor` is the only class
implementing `Executor` in `src/` (a test scans the package).

**U5 Metrics (DESIGN §8; decisions 23, 25; R-7; I-4).**
`src/discotrade/metrics.py`, `tests/test_metrics.py`, and in
`src/discotrade/backtest.py` only the call that builds the daily series.
Gate: tests on hand-made inputs for `total_return`, `sharpe` (not a
number with one day and with zero deviation, and such a value is neither
positive nor above any number in every comparison the module offers),
`sharpe_2x`, `max_drawdown`, `trades` (roll trades not counted),
`avg_holding_bars` (runs broken by a sign change and by zero; not a number
with no run), `breakeven_cost` in basis points with rolled turnover in
the denominator (not a number without turnover) and `fragile`; that the
daily series follows decision 23 on a hand case of two instruments with
different calendars, one with no bar on one of the days, and a third with
no window bar at all (`N = 3`); that every metric is computed from the
daily series and none from window-by-window scores; that a gross figure
is never returned without its net figures beside it.

**U6 Reference strategies and the `backtest` command (DESIGN §3, §6.1,
§18.3 G0.1's strategy list; decisions 21, 27; I-4, I-9).**
`reference/trend_ma.py`, `reference/zscore_reversal.py`,
`reference/hour_of_day.py` (the names may differ; three files), each a
§6.1 text with a docstring saying its rule; `src/discotrade/cli.py`
(`backtest`); `tests/test_reference.py`, `tests/test_cli_backtest.py`. A
moving-average trend rule, a z-score reversal rule and an hour-of-day
rule, using `indicators` where it fits. Gate: tests that each file passes
the loader with the repository's thresholds; that after `bars fetch` on
`test_mixed` into a temporary state directory at a fixed `--as-of`,
`discotrade backtest` of each file over a fixed window of at least sixty
trading days exits 0 and its `--json` output holds every metric of §8,
`sharpe_2x`, the 2x total, the four cost totals, `c1` and the config
hash, with `null` for a value that is not a number; that each strategy
trades on each of the three instruments, SYNL's position is never
negative, and at least one strategy pays a non-zero roll cost on SYNA;
that two runs give byte-identical `--json` output; that a file outside
`reference/` and `--from` after `--to` exit 2, and a refused bar file
exits 1; that the plain output prints no gross figure without the net
ones beside it. The I-9 test still passes.

**U7 Final report.** `meta/FINAL-REPORT-3.md` (drafted under
`meta/drafts/`, moved in by this commit): what changed (sha per unit),
what the tests prove, NOT PROVEN (mandatory: at least that no independent
calculation has checked the loop, the costs or the metrics yet, which is
mission 4's; every cost value that is still from SPEC §17, DESIGN §4.2 or
R-5 and not measured; the reference strategies' results meaning nothing
about any market; and what remains of mission 2's NOT PROVEN), the
findings filed, and a `## Review items` table with one row per REVIEW-2
should-fix item (1 and 2): the item, its resolution (the unit and
decisions item), and the sha. Then the verdict line.

## Acceptance

- `./scripts/check` prints `check: green` on the pushed tip, three
  consecutive runs.
- Every unit commit's body lists every file it touches; U0 is `plan:`.
- `uv run discotrade config check` exits 0 on the `hourly` track with its
  eight instruments, and no value of a frozen file changed in this mission
  (`git diff` of `config/` and of the existing entries of
  `tests/fixtures/config_frozen.json` against the base is empty).
- Nothing exists under `tests/gates/`; `./scripts/gate M0` exits non-zero
  with `gate M0: FAIL`, and `./scripts/gate M0 G0.3` ends with `gate M0
  G0.3: FAIL` (the gate tests are step S0.4's).
- `uv run discotrade backtest` of each of the three reference strategies
  on `test_mixed`, in a temporary state directory after `bars fetch`,
  exits 0 and prints the metrics of §8 with net figures at 1x and 2x.
- No test uses the network, a secret or the wall clock; no file under
  `src/` names a market, a contract root or a venue.
- `meta/FINAL-REPORT-3.md` exists with NOT PROVEN and the review-items
  table covering REVIEW-2 should-fix 1 and 2.
