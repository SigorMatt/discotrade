# discotrade — DESIGN v1.0

Strategy Discovery Swarm, stage 1 (simulation). Derived from `SPEC.md`
(Design Spec v1, 2026-10-10, findings of 2026-10-11) on 2026-10-11.

## 0. What this document is

`SPEC.md` is the owner's product specification: what the system is for and
what it must never do. This document is the build specification: the shape
of the code, the definitions the spec leaves open, and the tests that prove
each phase. Builders and reviewers work from this document.

**Precedence.** A decisions file under `meta/decisions/` (newest first) wins
over this document; this document wins over `SPEC.md`; `SPEC.md` wins over
anything a builder infers. Where this document and `SPEC.md` disagree and no
decisions file settles it, the builder follows this document and files a
finding in `meta/findings/FINDINGS.md`. Section 20 lists the places where
this document chose a reading of the spec; the owner may overrule any of
them with a decisions file.

**Purpose of the product.** The system runs unattended and answers one
question: do systematic, price-based trading rules proposed by LLM agents
hold up on data the agents never saw, after realistic costs? It is a
research instrument. Every trading decision in this series is simulated.

**Purpose of the build series.** This project is also the first shakedown of
the `hands` architect role (hands DESIGN §31, `architect/README.md`). The
series runs autonomously from its first kit: a builder session executes one
mission, a cold reviewer grades it, and a headless architect reads the
review and `meta/ROADMAP.md` and files the next kit. The human approved the
plan once, at the switch point, and is called only on the escalation
conditions written in `PLAYBOOK.toml`. Three consequences bind every
document in this repository:

1. Everything a later session needs is on the branch. No session has
   memory; a decision that is not in a file does not exist.
2. Every milestone has a gate that a command decides (section 18). Nobody
   judges "done" by reading prose.
3. Findings about hands itself (its guard, its documents, its playbook
   engine) are never fixed here. They are recorded in
   `meta/findings/FINDINGS.md` under the heading "hands findings" and the
   human carries them to the hands Project.

## 1. Scope of the series

In scope: SPEC phases 0 to 4, built and proven offline (milestones M0 to
M4), and the deployment package for phase 5 (milestone M5). "Offline" means
no network, no API key and no real LLM: every gate in section 18 runs on
synthetic markets, recorded fixtures and scripted stand-ins.

Out of scope for the series, and never started by a builder:

- Running the live daily loop on the cloud server (SPEC phase 5), more
  tracks (phase 6), and stages 2 and 3 (broker paper account, real money).
- Anything that needs a secret: the data vendor key, the model provider
  key, the coordinator's API key, the broker account. The code paths that
  use them are built and tested against fakes; proving them against the
  real service is a **live check** the owner runs (section 19.3). A live
  check is never a milestone gate.
- Everything SPEC §1 and §15 put out of scope or defer to v2.

## 2. Invariants

Numbered so that briefs, commits and reviews can cite them. A change that
breaks one is a blocker whatever else it achieves.

- **I-1 Deterministic results.** Only deterministic code touches market
  data and scores. No LLM output is ever used as a number, a score, a
  position or a decision about a result. LLMs supply a strategy function's
  source text, a brief, a description and digest prose.
- **I-2 No lookahead by construction.** A strategy function receives only
  bars that had closed at the moment of the decision. The harness builds
  that slice; nothing a strategy does can widen it.
- **I-3 Three segments.** An approach is devised on W, ranked once on T,
  and believed only on its paper record P. No statistic used for an alert
  or a claim reads W or T.
- **I-4 Costs everywhere.** Every score is net of the cost model, at 1x and
  at 2x. No code path reports a gross number without the net one beside it.
- **I-5 Append-only records.** Bars, the decision journal, the trial
  ledger, the lifecycle log and the call log are append-only. Code never
  rewrites or deletes a recorded row; a correction is a new row.
- **I-6 Idempotent days.** Re-running a day with the same inputs produces
  the same journal and table, byte for byte in content hash, and writes
  nothing new.
- **I-7 Untrusted code stays in the sandbox.** Source text that came from a
  worker is executed only inside the container sandbox of section 12, for
  its whole life, live approaches included. Isolation comes from what the
  sandbox contains, never from what a prompt says.
- **I-8 Roles talk only to the harness.** Workers receive text and return
  text: no tools, no raw bars, no T, no P, no state. The coordinator never
  sees a score and can write nothing that scoring, cost, alert or ledger
  code reads.
- **I-9 Instrument-agnostic code.** Each instrument is a config record. No
  file under `src/` names a market, a contract root or a venue.
- **I-10 One source for every threshold.** Every number in SPEC §2, §5, §8,
  §9 and §13 lives in `config/thresholds.toml` or a track record, is read
  from there by the code that enforces it and by the dashboard that
  displays it, and changes only with a dated history entry. The same holds
  for every other value that moves a result: once a file under
  `config/instruments/`, `config/tracks/`, `config/calendars/`,
  `config/spreads/` or `config/models.toml` exists, a value in it changes
  only by the owner's decision and with a dated history entry (section
  4.3).
- **I-11 Offline tests.** Every test that `./scripts/check` or a gate runs
  works with no network and no secret; installing the locked dependencies
  with `uv sync` is the one thing those scripts may fetch. A test that
  needs either is marked `network` or `live` and is not part of any gate.
- **I-12 No wall clock in results.** The harness reads time only through an
  injected clock, so a replay of a past day equals the run of that day. The
  one measured time, a strategy's call time (section 12.2), is enforced by
  the container backend only, and its verdict is stored with the call.
- **I-13 Secrets stay in the harness process.** Keys come from environment
  variables, never appear in a prompt, a log, a state file or the sandbox,
  and are never committed.
- **I-14 State is not in this repository.** Run state lives in a separate
  state directory that is its own private Git repository (section 9). The
  code repository holds code, config, fixtures and documents only.
- **I-15 Simulation only.** No code in this series can send an order to a
  broker. The executor interface has one implementation, the simulator.

## 3. Stack, layout and command line

**Stack.** Python 3.11 or later, managed with `uv`. Runtime dependencies:
`numpy`, `pandas`, `pyarrow`, `httpx`. Optional extra `vendor`: the data
vendor's official client, imported lazily by its adapter only. Development
extra `dev`: `pytest`, `ruff`, `hypothesis`. Any other dependency needs a
finding that explains why before it is added. Container runtime for the
sandbox: Docker or Podman, found at run time (section 12.4).

**Layout.** Package names and the modules listed here are binding;
function names inside a module are the builder's unless this document names
them.

    pyproject.toml            src layout, package discotrade, console script
    src/discotrade/
      cli.py                  the `discotrade` command
      config.py               track, instrument, model, threshold records (§4)
      clock.py                the injected clock (I-12)
      tradingcal.py           sessions, trading days, expected bars (§5.3)
      bars/store.py           the Parquet bar store (§5.2)
      bars/gaps.py            the gap check (§5.4)
      sources/base.py         the BarSource interface (§5.5)
      sources/synth.py        synthetic markets (§17)
      sources/crypto.py       public exchange bars, test data only
      sources/vendor.py       the futures data vendor adapter
      rolls.py                roll detection, adjusted series (§5.6)
      spreads.py              spread tables and their measurement (§5.7)
      indicators.py           the indicator library (§6.3)
      strategy.py             the strategy contract: PARAMS, GRID, position
      backtest.py             the evaluation loop (§7.1, §7.2)
      costs.py                the cost model (§7.3)
      executor.py             the executor interface and the simulator (§7.4)
      metrics.py              the metrics of §8
      state.py                the state directory, the content hash, the
                              health log (§9.1, §9.2, §15.2)
      journal.py              the decision journal (§9.2, §9.4)
      paper.py                paper records (§9.3)
      controls.py             buy-and-hold and random controls (§10.1)
      ledger.py               trial ledger, call log, lifecycle log (§10.2)
      lifecycle.py            states and transitions (§10.3)
      table.py                the table (§10.4)
      portfolio.py            the combined paper portfolio (§10.5)
      stats.py                rank persistence, deflation, tightening (§11)
      validation/static.py    the static check (§12.1)
      validation/sequence.py  the validation sequence and the grid (§12.2)
      validation/correlation.py   the correlation gate (§12.3)
      sandbox/base.py         the Sandbox interface (§12.4)
      sandbox/container.py    the container backend
      sandbox/process.py      the test backend for repository fixtures
      sandbox/inprocess.py    the unit-test backend for function objects
      sandbox/runner.py       the program that runs inside the sandbox
      workers/profile.py      the W profile (§13.1)
      workers/anonymize.py    labels and scaling (§13.2)
      workers/registry.py     registry lines (§13.3)
      workers/prompt.py       the prompt builder (§13.4)
      workers/parse.py        the response parser (§13.4)
      workers/providers.py    chat providers (§13.5)
      workers/pool.py         model pool, rotation, failure tracking (§13.6)
      coordinator.py          the coordinator interface and its two forms (§14)
      alerts.py               alert rules and alert state (§15.1 to §15.3)
      digest.py               digest assembly (§15.4)
      dashboard.py            the status dashboard (§15.5)
      daily.py                the daily run (§16.1 to §16.3)
      replay.py               the replay harness (§16.4)
      doctor.py               offline and live checks (§19)
    config/
      tracks/<name>.toml      one record per track
      instruments/<symbol>.toml   one record per instrument
      calendars/<name>.toml   one record per trading calendar
      spreads/<symbol>.toml   measured spread tables, when they exist
      models.toml             the worker model pool
      thresholds.toml         every threshold, with its history
      run.toml                run settings: sandbox runtime and limits,
                              coordinator options (keys named `sandbox.*`
                              and `coordinator.*` in this document)
      gates.toml              the owner's two manual stage-gate flags (§15.5)
      protected_paths.toml    paths the coordinator may never write (§14.4)
    reference/                hand-written reference strategies (trusted)
    sandbox/                  the container image definition
    tests/                    unit tests; tests/fixtures/; tests/gates/
    scripts/check             the commit gate (§18.1)
    scripts/gate              the milestone gate runner (§18.2)
    deploy/                   the deployment package (§19, M5)
    docs/OPERATIONS.md        the owner's runbook (§19, M5)

**Command line.** One console script, `discotrade`, with subcommands added
by the mission that builds what they call: `config check`, `bars fetch`,
`bars gaps`, `backtest` (evaluate a strategy file from `reference/` on
stored bars over a window and print the metrics of section 8),
`init-state`, `journal recompute`, `run-day`, `replay`, `sandbox build`,
`sandbox selftest`, `spreads measure`, `dashboard`, `doctor`. Every
subcommand takes `--state <dir>` (default: the environment variable
`DISCOTRADE_STATE`; there is no built-in default path, and a state directory
inside the code repository is refused, I-14), `--track <name>` (default
`hourly`), `--config <dir>` (default: the repository's `config/`; tests
point it at `tests/fixtures/config/`) and `--as-of <instant>` (sets the
injected clock; default: now). Exit status 0 on success, 1 on failure, 2 on
a usage error.

## 4. Configuration records

All configuration is TOML, loaded by `config.py` into frozen dataclasses.
An unknown key is refused, naming it. Every number that came from outside
the project (a fee, a tick size, a listing date, a training cutoff) is
stored with three companions: `checked` (ISO date), `source` (text) and
`verified` (boolean: true only when read from a primary source, such as an
account statement or the exchange's own file). `discotrade config check`
loads everything, prints one line per record, lists each unverified value,
and fails on an invalid one.

### 4.1 Track

    name = "hourly"
    bar_seconds = 3600
    w_days = 90                  # devise window, calendar days
    t_days = 14                  # rank window, calendar days
    history_cap_bars = 1500      # bars passed to a strategy; W's length in bars
    block_days = 14              # rank-persistence block, calendar days
    epoch = "2019-06-03"         # the date blocks are counted from
    instruments = ["MES", "MNQ", "MYM", "M2K", "MGC", "SIL", "MCL", "M6E"]
    families = ["trend", "mean_reversion", "breakout", "volatility_regime",
                "volume", "time_of_day"]
    cell_slots = 3

    [horizons]
    short = [1, 6]               # holding time in bars, inclusive bounds
    medium = [6, 48]

A cell is a pair (family, horizon); a track has `len(families) *
len(horizons)` cells in the order families-then-horizons, and that order is
the cell index used wherever a deterministic order is needed. A second
track is a second file; no code changes (SPEC §4, phase 6).

**Windows.** For a trading day `D`, T is the trading days whose date lies
in the last `t_days` calendar days ending with `D`, and W is the trading
days whose date lies in the `w_days` calendar days before those. A
window's bars are the bars of its trading days.

### 4.2 Instrument

    symbol = "MES"
    venue = "CME"
    quote_currency = "USD"
    calendar = "cme_globex"
    multiplier = 5.0             # quote currency per point
    tick_size = 0.25
    shorting = true
    test_only = false            # true for crypto test instruments
    trusted_from = "2019-05-06"  # history before this date is never used
    main_session = ["09:30", "16:00"]   # exchange-local, for the spread rule

    [cost]
    fee_per_side = 0.61          # quote currency per contract per side
    spread_ticks_main = 1.0
    spread_ticks_off = 2.0
    slippage_coef = 0.02
    checked = "2026-10-11"
    source = "SPEC.md §17"
    verified = false

    [source]
    adapter = "vendor"           # vendor | crypto | synth
    dataset = "GLBX.MDP3"
    symbol = "MES.v.0"           # volume-based continuous contract
    roll_rule = "volume"

An instrument whose fee is proportional to notional (the crypto test
instruments) sets `fee_bps` instead of `fee_per_side` and `multiplier`;
exactly one of the two forms is present. An instrument with `adapter =
"synth"` gives the generator's parameters in its `[source]` table (seed,
hourly volatility, dropped-bar fraction, and the keys section 17 names).
The eight futures records carry
the figures of SPEC §17 with `verified = false`; a value the spec does not
give (a tick size, a multiplier, a main session, a listing date) is taken
from the exchange's public contract specification, with its source, and is
listed in the mission's report under NOT PROVEN until a live check confirms
it. `test_only` instruments can never appear in a track whose name is not
prefixed `test_`.

### 4.3 Calendar, models, thresholds

A calendar record is described in section 5.3, the model pool in section
13.6. `config/thresholds.toml` holds every threshold in named tables, with
the SPEC defaults:

    [validation]
    max_params = 5
    max_lines = 60
    grid_max_params = 2
    grid_max_values = 3
    call_p95_ms = 50
    call_max_ms = 500
    min_changes_w = 30
    corr_max = 0.7
    description_max_chars = 200

    [admission]
    min_trades_t = 30

    [lifecycle]
    dormant_window_days = 30         # trading days
    retire_dormant_days = 365        # calendar days
    revival_min_dormant_days = 5     # trading days

    [controls]
    random_pool = 50
    match_window_days = 30           # paper days the random pool is matched on
    match_min_live = 3

    [gaps]
    max_fraction = 0.01

    [journal]
    recompute_sample = 20

    [alerts]
    persistent_min_days = 60
    persistent_base_percentile = 0.95
    false_alerts_per_year = 0.5
    group_days = 120
    group_level = 0.05
    group_bootstrap = 1000
    rank_blocks = 12
    rank_level = 0.05
    rank_min_population = 5
    revival_min_days = 60
    cost_stale_days = 90
    min_valid_candidates = 5
    valid_candidates_window_days = 14
    no_finding_months = 12

    [pool]
    fail_window = 20
    fail_rate = 0.5

    [coordinator]
    brief_max_chars = 600
    weak_window_days = 30

    [stage_gate]
    min_clean_days = 126             # six months of trading days (SPEC §14)

    [budgets]
    worker_tokens_per_day = 60000
    coordinator_tokens_per_day = 40000
    worker_max_output_tokens = 8000

    [[history]]
    date = "2026-10-11"
    key = "*"
    reason = "starting values from SPEC.md v1"

Every later change to a value adds a `[[history]]` entry with `date`, `key`
(`table.name`), `old`, `new` and `reason`. `tests/fixtures/thresholds_v1.toml`
is a frozen copy of the starting values; a test fails when a current value
differs from that copy and the last history entry for its key does not
give the current value as `new`. The dashboard prints the history (I-10).

The other result-moving files (instrument, track and calendar records,
spread tables, `config/models.toml`) are frozen the same way. The mission
that creates one adds its values to `tests/fixtures/config_frozen.json` (a
map from file and key to value). `config/HISTORY.toml` holds one
`[[change]]` entry per later change: `date`, `file`, `key`, `old`, `new`,
`reason`, and `decision`, the decisions file that carries the owner's
approval. A test fails when a current value differs from the frozen map
and the last change entry for it does not give the current value as `new`
and name a decisions file that exists; a new file (a measured spread
table, a new instrument) needs an entry too. No builder and no architect
role changes such a value on its own authority: needing to is an
escalation. The dashboard prints these changes with the threshold history.

## 5. Data layer

### 5.1 Bars

A bar has: `ts` (open time, UTC, nanosecond timestamp), `open`, `high`,
`low`, `close`, `volume` (all float64) and `contract` (string: the
underlying contract the bar was taken from; equal to the symbol where an
instrument does not roll). Stored prices are raw, never adjusted. A bar is
closed when `ts + bar_seconds` is not later than the source's
`available_until` (section 5.5). Only closed bars are ever written.

### 5.2 The bar store

`<state>/bars/<track>/<symbol>/<YYYY-MM>.parquet`, one file per instrument
per calendar month of `ts` in UTC, rows sorted by `ts`, no duplicate `ts`.
The writer only appends: it refuses a bar whose `ts` is not later than the
last stored bar of that instrument, and it never changes a stored row. An
append rewrites the month's file atomically (write beside, then rename)
with the old rows unchanged; a test proves the old rows are identical after
an append. `<state>/bars/<track>/index.json` records per instrument the
first and last `ts`, the row count and the content hash of each month
file (section 9.2 defines the content hash). The Parquet files are
not committed to the state repository; the index is. A stored file whose
hash no longer matches the index is a revised data point: the reader
refuses it and the daily run raises a health alert.

The reader returns, for an instrument, the bars in a half-open time range,
or the last `n` bars ending at a given bar.

### 5.3 Trading calendar

A calendar record gives a time zone, the weekly opening and closing times,
the daily break, and dated closures:

    name = "cme_globex"
    tz = "America/New_York"
    week_open = ["Sun", "18:00"]
    week_close = ["Fri", "17:00"]
    daily_break = ["17:00", "18:00"]
    day_rolls_at = "17:00"       # a bar belongs to the trading day that
                                 # ends at the next 17:00 local

    [[closure]]                  # the market is shut for this local interval
    start = "2026-12-24 13:15"
    end = "2026-12-27 18:00"
    note = "Christmas"
    checked = "2026-10-11"
    source = "exchange holiday calendar"
    verified = false

A calendar with `always_open = true` has no other key (crypto test data);
its trading day is the UTC date.

`tradingcal.py` answers four questions, all pure functions of the record:
whether the market is open at an instant; the trading date of a bar; the
expected bar open times in a range (every `bar_seconds`-aligned UTC
instant whose bar interval overlaps an open interval); and whether a bar
lies in the instrument's main session (the instrument's `main_session`
hours on a weekday that is not closed). "Trading day" everywhere in this
document means a trading date of the track's calendar; "calendar day" means
a date.

### 5.4 The gap check

After every fetch, for each instrument: missing bars are the expected bar
open times with no stored bar, from the later of `trusted_from` and the
first stored bar to the last stored bar. Each newly found missing bar is
appended to `<state>/bars/<track>/gaps.jsonl`. Missing bars are never
interpolated; a strategy sees the stored bars in order and nothing else.
For a window (W or T), the gap fraction is missing bars over expected bars,
pooled across the track's instruments. When the fraction of W or of T
exceeds `gaps.max_fraction`, the day's candidate generation is skipped and a
health alert is raised; journaling and scoring proceed (SPEC §4, §11).

### 5.5 Bar sources

    class BarSource(Protocol):
        name: str
        def available_until(self, now: datetime) -> datetime: ...
        def fetch(self, instrument, start, end) -> DataFrame: ...
        def fetch_contract(self, instrument, contract, start, end) -> DataFrame: ...

`fetch` returns bars in the schema of section 5.1 for the instrument's
continuous series; `fetch_contract` returns the bars of one named
underlying contract and is used only to measure roll gaps. Three adapters:

- `synth`: the generators of section 17. `available_until(now) = now`.
- `crypto`: hourly bars from a public exchange endpoint that needs no key,
  for `test_only` instruments. It exists to exercise a real HTTP source
  during development (SPEC §4). No gate depends on it.
- `vendor`: the futures data vendor's historical interface, hourly bars of
  the volume-rolled continuous contract, with the underlying contract of
  each bar resolved through the vendor's symbology so that `contract` is
  filled. `available_until(now) = now - 24 hours`. The key is read from the
  environment variable `DATABENTO_API_KEY` (I-13). Before any fetch it asks
  the vendor's cost-estimate call and refuses a request above
  `max_cost_usd` (a `[source]` key, default 5.0). The client library is
  imported inside the adapter; tests drive the adapter with a fake client
  of the same shape. The real service is live check L1.

`discotrade bars fetch` asks the source for every instrument of the track
from the last stored bar to `available_until`, writes closed bars, runs the
gap check and updates rolls.

### 5.6 Rolls and the adjusted series

A roll happens at bar `u` of an instrument when `contract(u)` differs from
`contract(u-1)`. For each roll the harness records, append-only, in
`<state>/rolls/<track>/<symbol>.jsonl`: the roll bar's `ts`, the old and the
new contract, and the gap

    gap = close_new(v) - close_old(v)

where `v` is the latest bar time before `u`, within 24 bars, at which both
contracts have a bar (`fetch_contract`). When no such bar exists the gap is
`open(u) - close(u-1)` of the continuous series, the record carries
`estimated = true`, and a health notice is logged.

The adjusted series as of bar `t` is the raw series up to `t` with, for
every bar `s`, the sum of the gaps of the rolls after `s` and not after `t`
added to its four prices. The last bar is therefore always raw, and the
adjustment of a window never depends on a roll that had not happened yet.
Volume is never adjusted. Strategies see adjusted prices as of the decision
bar; returns are computed from adjusted price differences over raw prices
(section 7.2), so a roll gap is never profit or loss.

### 5.7 Spreads

The spread of an instrument at a bar, in ticks, is read from
`config/spreads/<symbol>.toml` when that file exists (24 values, one per
exchange-local hour of day, with `checked`, `source`, `verified` and a
description of the quote sample), and otherwise is `spread_ticks_main`
inside the main session and `spread_ticks_off` outside it. `discotrade
spreads measure` computes the table from a sample of vendor quote data
(median quoted spread per exchange-local hour, in ticks) and writes the
file; the computation is tested on synthetic quotes, and running it on real
quotes is live check L2. `config check` warns when a measured spread makes
SPEC decision 14 apply (a marginal instrument above one tick).

## 6. The strategy contract

### 6.1 The function

A strategy is one Python source text that defines:

    PARAMS = {"lookback": 48, "threshold": 1.5}     # at most 5, all numeric
    GRID = {"lookback": [24, 48, 96]}               # optional: at most 2
                                                    # parameters, 3 values each

    def position(bars, params):
        """Return a target position in [-1.0, 1.0] for the next bar."""

`GRID` is how a worker declares the values of SPEC §5's tuning grid; a
parameter named in `GRID` must be in `PARAMS`. Helper functions may be
defined at module level. The whole text is at most `max_lines` physical
lines.

### 6.2 What the function receives

`bars` is a DataFrame of the most recent closed bars of one instrument,
oldest first, at most `history_cap_bars` rows, with a plain integer index
from 0 and the columns `open`, `high`, `low`, `close`, `volume` (float64,
prices adjusted as of the last row, section 5.6) and `hour`, `weekday`
(small integers: the bar's open time in the calendar's time zone, Monday
is 0). There is no date and no symbol anywhere in it. `params` is a dict of
the fixed parameter values. The function is called once per bar, per
instrument, with a fresh copy of the frame.

The result must be a real number that is finite and within [-1, 1]. Where
the instrument does not allow shorting, the harness clips a negative result
to 0. The function must be pure: no state between calls, no file, network
or process access, no randomness, no clock (enforced in section 12).

### 6.3 The indicator library

`discotrade.indicators`, importable inside a strategy as `indicators`:
pure functions over a Series or array and a window, each returning a result
aligned to its input whose value at row `i` depends only on rows up to `i`.
At least: `sma`, `ema`, `rolling_std`, `rolling_max`, `rolling_min`,
`returns`, `zscore`, `rsi`, `atr`, `realized_vol`, `bollinger`, `donchian`,
`volume_zscore`. A property test proves the no-lookahead claim for every
function by truncation: the value at `i` is the same whether the input ends
at `i` or later. The function list given to workers (section 13.4) is
generated from this module's names and first docstring lines.

## 7. Backtester, cost model, executor

### 7.1 The evaluation loop

To evaluate a strategy on a window of one instrument, the harness walks the
stored bars of the window in order. At each bar `t` it builds the slice of
section 6.2 ending at `t`, calls the function, and obtains the target
`p(t)`. The position in force during bar `u` is

    h(u) = p(u-1)

that is, a target computed at the close of bar `u-1` is traded at the open
of bar `u` (SPEC §6). Bars before the window are passed as context so that
indicators are warm at the window's first bar, but only positions taken
inside the window are scored: for a window scored on its own (W, T) whose
first bar is `u0`, `h(u0) = 0` whatever the function returned before the
window, and `h(u) = p(u-1)` for every later bar, so the first trade is at
the open of the window's second bar; the target of the window's last bar is
computed and recorded but never traded. In the continuous paper record
the position carries from one day to the next (section 9.2).

Because the slice is built by the harness from bars up to `t`, the function
cannot read a later bar (I-2). Two tests prove it: truncation invariance
(the positions for bars up to `t` are identical whether the stored data
ends at `t` or a year later) and the cheating strategy of gate M0.

### 7.2 Returns

For bar `u` of the window, with `Oa`, `Ca` the adjusted open and close as
of `u`, `Or` the raw open, and `u-1` the previous stored bar:

    gross(u) = ( h(u-1) * (Oa(u) - Ca(u-1)) + h(u) * (Ca(u) - Oa(u)) ) / Or(u)

The first term is the old position carried from the previous close to this
open; the second is the new position from this open to this close. Returns
are fractions of notional; contracts are never rounded (SPEC §6).

### 7.3 Costs

    trade(u) = | h(u) - h(u-1) |
    c(u)     = fee(u) + half_spread(u) + slip(u)        per unit traded
    fee(u)         = fee_per_side / (multiplier * Or(u))      or fee_bps / 10000
    half_spread(u) = max(spread_ticks(u) / 2, 0.5) * tick_size / Or(u)
    slip(u)        = slippage_coef * sigma(u)
    roll_cost(u)   = 2 * | h(u-1) | * c(u)      when a roll happens at u, else 0
    cost(u)        = trade(u) * c(u) + roll_cost(u)
    net(u, m)      = gross(u) - m * cost(u)             m = 1 and m = 2

`spread_ticks(u)` is section 5.7's value for bar `u`. `sigma(u)` is the
sample standard deviation (ddof 1) of the last 24 returns
`r(s) = (Ca(s) - Ca(s-1)) / Cr(s-1)` with `s` up to `u-1`, where the
difference is taken on closes adjusted as of `s` and `Cr` is the raw
close; with fewer than 2 such returns it is 0. A carried position pays two extra trades at a roll, each
at the full per-trade cost (section 20, reading R-3). Orders are market
orders; limit orders are not modeled.

The cost model has a version string, `c1`, changed whenever a formula
here changes, and a config hash (sha256 of the instrument cost tables and
spread tables in force). Both are recorded with every trial (section 10.2).
Costs are reported by component: fee, spread, slippage, roll.

### 7.4 The executor

    class Executor(Protocol):
        def execute(self, orders: list[Order], bars) -> list[Fill]: ...

An `Order` names the subject, the instrument, the decision bar, the
previous position and the target; a `Fill` adds the fill bar, the raw fill
price and each cost component at 1x. `SimExecutor` implements sections 7.1
to 7.3 and is the only implementation (I-15). The journal is written from
fills, so a later stage replaces the executor and nothing upstream changes
(SPEC §9, §14).

## 8. Metrics

A subject (an approach or a control) runs on a set of instruments: the
whole basket for an approach. Its daily net return on a trading day is the
equal-weight mean over its instruments of the sum of `net(u, m)` over that
day's bars. From the daily series `d`, at 1x unless stated:

- `total_return`: the sum of `d` (no compounding).
- `sharpe`: `mean(d) / std(d, ddof=1) * sqrt(252)`; not a number when there
  are fewer than 2 days or the deviation is 0. A Sharpe that is not a
  number is never "positive" and never "above" anything.
- `sharpe_2x`: the same at `m = 2`.
- `max_drawdown`: the largest peak-to-trough fall of the running sum of `d`.
- `trades`: the count, summed over instruments, of bars with
  `trade(u) > 1e-9`. Roll trades are not counted.
- `avg_holding_bars`: the mean length in bars of maximal runs of non-zero
  position of one sign, over all instruments.
- `breakeven_cost`: the sum of `gross` over the sum of traded and rolled
  turnover, per unit traded, in basis points; not a number without turnover.
- `fragile`: true when `total_return` is positive at 1x and negative at 2x.

All statistics are computed from daily series, never from window-by-window
scores (SPEC §9).

## 9. State, journal and paper records

### 9.1 The state directory

One directory outside the code repository, itself a Git repository
(`discotrade init-state` creates it with its `.gitignore`):

    bars/<track>/...                 section 5.2 (Parquet ignored, index committed)
    rolls/<track>/<symbol>.jsonl     section 5.6
    approaches/<id>/strategy.py      the frozen source of an admitted approach
    approaches/<id>/meta.json
    trials/<id>/strategy.py          the source of a trial that was not admitted
    trials/<id>/meta.json
    journal/<track>/<YYYY>/<YYYY-MM-DD>.parquet
    journal/<track>/index.jsonl      one line per day: date, rows, content hash
    paper/<track>/daily.parquet      derived from the journal; rebuildable
    controls/<track>/pools.jsonl     section 10.1
    ledger/<track>/trials.jsonl      section 10.2
    ledger/<track>/calls.jsonl
    ledger/<track>/lifecycle.jsonl
    responses/<track>/<date>/<call>.json    every worker response, in full
    stats/<track>/rank_persistence.jsonl
    table/<track>/table.json, table.md
    alerts/<track>/state.json, <date>-<kind>-<subject>.json
    digests/<track>/<date>.md
    dashboard/<track>/index.html
    runlog/<track>.jsonl
    health/<track>.jsonl

An approach id is `a` followed by the first 12 hex digits of the sha256 of
its source text and its fixed parameters. `meta.json` holds: id, cell,
model id, model version string, the model's cutoff date as used (section
11.3), description, fixed parameters, code sha256, profile version, cost
model version and config hash, and the admission date.

### 9.2 The decision journal

One Parquet file per trading day, holding one row per subject, instrument
and bar of that day:

    date, ts, subject, kind, instrument,
    prev_position, position, target_next,
    fill_price, trade, roll,
    fee, spread, slippage, roll_cost,          at 1x
    gross, net_1x, net_2x

`kind` is `approach`, `control_random` or `control_bh`. `position` is
`h(u)`; `target_next` is `p(u)`, the target that the next bar will trade;
`fill_price` is the raw open of `u`. An approach's first row is the first
bar of the first trading day after its admission, with `prev_position` 0
and `position` 0 (section 7.1's rule for the first bar of a window); its
`target_next` is the first target that trades.
Every later day starts from the previous day's last `target_next`.

The content hash of a table is the sha256 of its rows, sorted by the key
columns, written as text with every float in `%.17g`. A day's file is
written once, with its line in `index.jsonl`. Running the same day again
recomputes the rows and compares content hashes: equal means nothing is
written (I-6); unequal means the file is left untouched and a
`journal_mismatch` health alert is raised. The state repository is
committed after every day (section 16.2), so no entry can be revised after
its outcome is known.

### 9.3 Paper records

`paper/<track>/daily.parquet` is derived from the journal: per subject and
trading day, the daily gross, net at 1x and 2x, trades, and the `clean`
flag of section 11.3. An approach's paper record starts the day after its
admission. It is the only record used for an alert or for any claim that an
approach works (I-3). Rebuilding the file from the journal gives the same
content hash.

### 9.4 Recomputation

On the first trading day of each ISO week the daily run recomputes
`journal.recompute_sample` past (day, subject) pairs, drawn by a generator
seeded with the run's date, from the stored bars and the frozen sources,
and compares the rows exactly. A mismatch raises the `journal_mismatch`
health alert naming the pair. `discotrade journal recompute --all` does the
same for every day.

## 10. Controls, ledger, lifecycle, table, portfolio

### 10.1 Controls

Controls pass through the same executor, cost model, journal and metrics as
approaches. They are harness code, not strategy functions.

- **Buy and hold**, one per instrument (`bh:<symbol>`): position 1 on its
  instrument at every bar. Its instrument set is that one instrument.
- **Random**, a pool of `controls.random_pool` slots (`rc:<slot>`), redrawn
  on the first trading day of each calendar month. A draw gives each slot a
  mean holding time `H` in bars and an entry probability per bar `q`,
  sampled from the live approaches' measured pairs (average holding bars
  and trades per bar over their last `match_window_days` paper days) when
  at least `match_min_live` approaches are live, and otherwise `H` log-uniform on the union of the
  track's horizons with `q = 1 / H`. From the draw's first bar the slot
  follows a state machine on every instrument independently: when flat it
  enters with probability `q`, long or short with equal probability (long
  only where shorting is not allowed); when in a position it leaves with
  probability `1 / H`. Every random number is a pure function of (pool
  seed, slot, instrument, bar `ts`, purpose) through a hash, so a control's
  position at a bar is a function of the pool record and the bar times
  since the draw, and is recomputable. Each draw appends its record (month,
  seed, per-slot `H` and `q`, the measured pairs it used) to `pools.jsonl`.
  A slot's return series continues across redraws.

The control distribution is the baseline for every claim (SPEC §10).

### 10.2 The ledgers

All three are JSON lines, append-only (I-5).

- `trials.jsonl`: one row per trial, that is, per submission that passed
  validation and the correlation gate and was scored on T, admitted or not:
  date, id, cell, model id, model version, cutoff date, code sha256,
  profile version, cost model version and config hash, the grid and its
  results on W, the fixed parameters, every metric of section 8 on W and on
  T, `admitted`, the reason, and the id it displaced if any. The cumulative
  trial count `N` is the number of rows; nothing is ever deleted.
- `calls.jsonl`: one row per worker call: call id, date, cell, model,
  attempt, tokens in and out, the outcome (`trial`, `duplicate`,
  `invalid:<stage>`, `provider_error`, `budget`), the response file.
- `lifecycle.jsonl`: one row per state change: date, id, from, to, reason.

### 10.3 Lifecycle

States: `candidate`, `live`, `dormant`, `retired`. At the end of each day's
journaling, in this order, for the track:

1. **Retire failures.** An approach whose function raised, timed out, or
   returned a value that is not finite and in range on any bar today is
   retired; its rows for today are not journaled.
2. **Go dormant.** A live approach with at least `dormant_window_days` of
   paper record whose net Sharpe at 1x over its last `dormant_window_days`
   trading days is negative becomes dormant.
3. **Return.** A dormant approach, dormant for at least
   `revival_min_dormant_days` trading days, whose net Sharpe at 1x over its
   last `dormant_window_days` trading days is positive becomes live when
   its cell has a free slot, or when that Sharpe beats the weakest live
   approach of its cell over the same days, which is then displaced to
   dormant.
4. **Retire the long dormant.** An approach dormant for
   `retire_dormant_days` calendar days is retired.

Then the day's candidate, if there is one (section 16.1 step 5): its
admission score is its net Sharpe at 1x on T. It becomes live when that
score is positive, it has at least `min_trades_t` trades on T, and either
its cell has fewer than `cell_slots` live approaches, or its score beats
the net Sharpe at 1x, over the same T days, of the weakest live approach of
its cell, which is then displaced to dormant. Otherwise it is a trial that
was not admitted. Every change is one lifecycle row and takes effect on the
next trading day. Dormant approaches are journaled daily; retired ones are
not scored again and stay in the ledger.

### 10.4 The table

Derived on every run and written as `table.json` and `table.md`: one row
per live approach, grouped by cell, then dormant approaches, then controls
and the combined portfolio, each marked as such. Columns: description,
model, date admitted, admission score, paper record (days, clean days, net
Sharpe at 1x and 2x, trades, maximum drawdown), breakeven cost, the
deflated figures of section 11.2, and the state history.

### 10.5 The combined paper portfolio

Two daily series in the paper records. `portfolio`: the equal-weight mean
of the day's net returns (1x and 2x) of the approaches that were live at
the start of the day; 0 on a day with none. `portfolio_clean`: the same
over the live approaches whose observation that day is clean; a day with
none is not part of the series. Weights are equal by decision (SPEC §9).

## 11. Statistical safeguards

### 11.1 Rank persistence

Blocks are consecutive spans of `block_days` calendar days counted from the
track's `epoch`. When a block completes, for the population of approaches
(live or dormant) that have a paper row on every trading day of that block
and of the one before it: the block statistic is the Spearman rank
correlation between their summed net returns at 1x in the two blocks. With
fewer than `rank_min_population` members the statistic is recorded as
missing. Each block appends a row to `rank_persistence.jsonl`. Blocks do
not overlap and use paper records only. The same function accepts another
population; gate M1 applies it to the random control slots.

### 11.2 Deflated scores

For an approach with paper-record Sharpe `S` over a set of days, let `mu_c`
and `sd_c` be the mean and standard deviation of the random control slots'
Sharpes over the same days. The Sharpe expected from the best of `N`
random trials is

    E(N) = mu_c + sd_c * ( (1 - g) * z(1 - 1/N) + g * z(1 - 1/(N * e)) )

with `g` the Euler-Mascheroni constant, `z` the standard normal quantile
and `N` the cumulative trial count (at least 2). The table reports `S`,
`E(N)` and the excess `S - E(N)`; only the excess counts (SPEC §10).

### 11.3 Clean and exposed observations

Each model in the pool has a cutoff date: the last day of its stated
training-cutoff month, or its release date when its maker states none. An
approach's observation on a trading day is `clean` when the day is after
the cutoff date of the model that wrote it, and `exposed` otherwise.
Control observations are always clean. Alerts and gates read clean
observations only; exposed ones are kept and shown for comparison.

### 11.4 Tightening

The control percentile required by the persistent-approach alert rises
with the trial count so that the expected number of false alerts per year
stays below one:

    p(N) = 1 - min(1 - persistent_base_percentile, false_alerts_per_year / max(N, 1))

and the alert compares against the control distribution through its normal
approximation: the threshold is `mu_c + z(p(N)) * sd_c`.

## 12. Validation and the sandbox

### 12.1 The static check

Runs on the source text before anything executes it, with Python's `ast`
module, and rejects, naming the first reason:

- text that does not parse, or is longer than `max_lines`;
- no module-level `PARAMS` dict literal, more than `max_params` entries, a
  key that is not a string, a value that is not an int or float literal;
- a `GRID` that is not a dict literal of lists of numeric literals, names a
  key outside `PARAMS`, or exceeds `grid_max_params` or `grid_max_values`;
- no module-level `def position(bars, params)`;
- any import other than `numpy`, `pandas` and `indicators` (plain or
  aliased), and any `from` import outside those three;
- a class, a decorator, `global`, `nonlocal`, `async`, `await`, `yield` or
  `with`;
- any name or attribute beginning with an underscore;
- the names `eval`, `exec`, `compile`, `open`, `input`, `breakpoint`,
  `globals`, `locals`, `vars`, `dir`, `getattr`, `setattr`, `delattr`,
  `type`, `object`, `super`, `memoryview`, `exit`, `quit`, `help`, `print`;
- the attributes `eval`, `query`, `pipe`, `system`, `popen`, `load`,
  `loads`, `save`, `savez`, `loadtxt`, `savetxt`, `genfromtxt`, `fromfile`,
  `tofile`, `memmap`, `ctypeslib`, `random`, `default_rng`, `RandomState`,
  `now`, `today`, `time`, `datetime`, `testing`, `f2py`, `distutils`, and
  any attribute beginning `read_` or `to_` except `to_numpy`.

The list is a floor: the hostile suite of gate M2 pins it, and a builder who
finds a further trick adds the rule and the test. The static check is the
first line; the container is the boundary (I-7).

### 12.2 The validation sequence

In order, each on W only, in the sandbox; the first failure ends it with an
error text fit to send back to the worker:

1. **Static check** (section 12.1).
2. **Dry run and grid.** For each parameter combination of `GRID` (the
   single `PARAMS` set when there is no grid): every call returns a finite
   number in range; the 95th percentile of call times is at most
   `call_p95_ms` and no call exceeds `call_max_ms` (the two time limits are
   enforced by the container backend; the other backends record call times
   and enforce only the job's wall-clock limit, so a deterministic replay
   never depends on machine load). The harness scores each
   combination on W and fixes the one with the best net Sharpe at 1x (the
   first in declaration order on a tie). This is the only tuning allowed,
   and it is the same for every worker.
3. **Determinism.** A second run on W in a fresh sandbox gives identical
   positions, and a run that calls a sample of bars in reverse order inside
   one process gives the same positions for them (no state between calls).
4. **Activity.** At least `min_changes_w` position changes on W, summed
   over the basket.
5. **Correlation gate** (section 12.3).

A submission that fails gets one retry, with the error text appended to the
prompt. A second failure is logged as a wasted call and is not a trial. A
submission that passes all five is a candidate and is scored on T.

### 12.3 The correlation gate

The submission's position series on W, concatenated over the basket in the
track's instrument order, is correlated (Pearson) with the same series of
every live and dormant approach. An absolute correlation above `corr_max`
with any of them rejects the submission as a duplicate and names the
approach it duplicated; strong negative correlation counts, because it is
the same idea with the sign flipped. A rejected duplicate is not a trial.
Position series of existing approaches on W may be cached; the cache is
derived and never state.

### 12.4 The sandbox

    class Sandbox(Protocol):
        def run(self, job: SandboxJob) -> SandboxResult: ...

A job is a source text, parameter sets, a mode (`positions`, `reverse
sample`), the bars of the window with their context, per instrument, and
the limits. A result is positions per parameter set, instrument and bar,
call times, or an error with its stage. The sandbox never computes a score;
the harness does, outside.

Three backends:

- **Container** (`sandbox/container.py`): the only backend allowed for
  source text that came from a worker, and the one the daily run uses. It
  starts one container per job with Docker or Podman, whichever
  `sandbox.runtime` names or is found first: no network, a read-only root
  file system, a small `tmpfs` at `/tmp`, a non-root user, all capabilities
  dropped, no new privileges, a process limit, a memory limit, a CPU limit
  and a wall-clock limit enforced by the harness, which kills and removes
  the container. The job's input directory is the only mount, read-only: it
  holds the source, the parameters and the bars of the window being scored
  with their warm-up context and nothing else. During validation on W, the
  T and P bars do not exist inside the container (SPEC §12). The result
  comes back on standard output, capped in size. The container is removed
  after every run. The image is built by `discotrade sandbox build` from
  `sandbox/`: a pinned Python base, pinned `numpy` and `pandas`, the
  runner and the indicator library, and nothing else; its tag carries the
  hash of those inputs, so a changed runner or library forces a rebuild.
  `discotrade sandbox selftest` runs the probe of gate M2.
- **Subprocess** (`sandbox/process.py`): the same runner in a plain
  child process with resource limits. It is not a security boundary. It
  exists so that long replays in tests are fast, accepts only a source
  text whose sha256 is that of a file under this repository's `reference/`
  or `tests/fixtures/` (so an approach admitted from a fixture corpus still
  runs after its source is frozen in a state directory), and is refused by
  `run-day` unless the run is a replay on a synthetic source.
- **In-process** (`sandbox/inprocess.py`): calls a Python function object
  directly, for unit tests of the backtester. It accepts no source text.

API keys are never passed to any backend (I-13).

### 12.5 The hostile suite

`tests/fixtures/hostile/` holds one submission per attack, each with the
stage that must reject it: network access, writing a file, reading a file
outside the mount, reading the mounted bars directly, a fork bomb, an
endless loop, a memory bomb, forbidden imports, `__import__` and attribute
walks from a literal to `object`, `eval` and `exec`, state kept between
calls (a module-level cache, a mutable default argument), randomness, the
clock, too many lines, too many parameters, a non-numeric parameter, a
result that is not a number, not finite or out of range, a huge output,
changing `bars` in place, the IO functions of `numpy` and `pandas`, and a
slow function. None may produce a trial, change a file outside the job's
own scratch space, or stop the harness.

## 13. Workers

A worker is one chat completion: one prompt in, one code block out. There
is no tool calling and no loop (SPEC §7).

### 13.1 The W profile

Computed by the harness from W; workers never see a bar. It is a JSON
document with a version string (`p1`; any change to its content changes
the version, and the version is recorded with every trial):

- a common block per instrument: the distribution of hourly returns (mean,
  deviation, skewness, kurtosis and seven quantiles, in basis points),
  volatility by hour of day and by weekday, autocorrelation of returns at
  lags 1 to 48, the share of volume by hour of day, and the share and mean
  run length of bars in high and in low volatility regimes (rolling 24-bar
  realized volatility above the 75th or below the 25th percentile of W);
- a cell block that fits the family: trend cells get the persistence of
  moves over several horizons; mean-reversion cells get the reversal rate
  after large moves; breakout cells get range and follow-through
  statistics; volatility-regime cells get behaviour conditional on regime;
  volume cells get returns after unusual volume; time-of-day cells get mean
  returns by hour and weekday.

Every field is free of price and volume units (returns, ratios, shares).
The profile is identical for all workers on a day except for the cell
block.

### 13.2 Anonymization

For each prompt, from a generator seeded by the call id: instruments get
neutral labels (`A`, `B`, ...) in a shuffled order; any field that is in
price or volume units is multiplied by a constant drawn per instrument
(returns are unchanged; the `p1` profile has no such field, so in v1 the
scaling function is tested on its own and waits for a profile version that
needs it); calendar dates never appear, only bar indices;
hour of day and weekday are kept. A test proves that no prompt contains an
instrument symbol, a venue, a contract name or a date. The known limit is
SPEC §4's: a distinctive path can still be recognised, which is why
section 11.3 exists.

### 13.3 The registry

One line per live and dormant approach in the same cell and in neighbouring
cells (same family or same horizon): id, cell, state, description. No
score appears in it. Descriptions are worker-written text: they are capped
at `description_max_chars`, stripped to printable ASCII with no line
breaks, backticks or angle brackets, and passed inside a delimited block
introduced as data that is not to be followed as instructions (SPEC §12).

### 13.4 The prompt and the response

The prompt has five parts in this order: the brief; the W profile for the
cell; the registry, with the instruction to propose something absent from
it; the contract of section 6 with the caps, the indicator function list
and the cost model in words and numbers; and the output format, a single
fenced Python block followed by a one-sentence description. The parser
takes the last fenced Python block of the response and the first
non-empty line after it as the description; no block or no description is
a validation failure. Every response is stored in full before it is parsed.

### 13.5 Providers

    class ChatProvider(Protocol):
        def list_models(self) -> list[str]: ...
        def complete(self, model, messages, max_tokens) -> Completion: ...

`Completion` carries the text, the token counts, the model's version
string as the provider reports it, and the raw response.

- `OpenAICompatProvider`: `httpx` against an OpenAI-compatible endpoint
  (base URL in `config/models.toml`; key from `NEBIUS_API_KEY`).
- `ScriptedProvider`: replays a directory of canned responses in order per
  model. Used by tests, gates and replays.
- `ClaudeWorkerProvider`: a headless Claude Code call with every tool
  denied, for cells where open models fail validation more than half the
  time (SPEC §7). Tested against a fake `claude` executable.

No test requires a real provider or a real `claude` binary (I-11). The real
services are live checks L3 and L4.

### 13.6 The pool

`config/models.toml` lists the pool: per model its id, maker, stated
training cutoff or release date (with `checked`, `source`, `verified`),
and optionally the id of a fallback from the same maker. The starting pool
is the three models of SPEC §17. At the start of each run the harness reads
the provider's model list; a configured model that is missing is skipped
for the day in favour of its fallback, with a health notice. The model for
a call is `pool[(trading-day ordinal + cell index) mod pool size]`, so no
cell is always served by the same model. Per model, the outcomes of its
last `fail_window` calls are kept; a model whose validation failure rate
over a full window exceeds `fail_rate` is removed from the pool and a
`model_removed` health alert is raised. Each trial records the model, its
version string and its cutoff date.

Per cell, the outcomes of the last `fail_window` calls served by open
models are kept as well. When a cell's validation failure rate over a full
window exceeds `fail_rate`, the cell is served by `ClaudeWorkerProvider`
from then on if `workers.claude_fallback` is true in `config/run.toml`
(SPEC §7); while it is false, the v1 default, a `cell_needs_fallback`
health notice is logged instead.

### 13.7 Generation for the day

At most one trial per day (SPEC §11). One call; on a validation failure or
a duplicate, one retry; then the day's generation ends. Before each call
the harness adds the day's tokens from `calls.jsonl` to the call's maximum;
if that exceeds `worker_tokens_per_day` no call is made, the outcome is
`budget`, and a `token_budget` health alert is raised. A day whose stored
response already exists replays it and makes no call (I-6).

## 14. The coordinator

### 14.1 The interface

    class Coordinator(Protocol):
        def choose_cell(self, cells: list[CellStatus], registry: list[str]) -> Brief: ...
        def write_digest(self, alerts: list[AlertPayload]) -> str: ...
        def write_runlog_line(self, summary: RunSummary) -> str: ...

`CellStatus` has a cell, its count of live approaches, its free slots and
one flag, `weak` (no live approach, or every live approach of the cell
dormant within its first `weak_window_days` paper days at least once). It has no score, no
return and no rank, and neither has the registry (I-8). A property test
builds the coordinator's input from two states that differ only in scores
and asserts the inputs are identical.

### 14.2 The two forms

- `ScriptedCoordinator`: chooses the offered cell with the fewest live
  approaches (lowest cell index on a tie), writes a template brief and a
  template digest. Deterministic; used by tests, gates and replays.
- `ClaudeCodeCoordinator`: one headless Claude Code call per task, started
  as SPEC §17 describes (bare mode, JSON output, a turn limit, a spending
  limit, a non-interactive permission mode, an explicit model), with every
  tool denied: its inputs are in the prompt and its output is the reply.
  The exact flags are read from the installed `claude --help` by the
  mission that builds it and recorded in its report. Tested against a fake
  `claude` executable. The real call is live check L4.

### 14.3 What the harness does with its output

The chosen cell must be one of the offered cells, otherwise the scripted
choice is used and a health notice is logged. The brief is capped at
`brief_max_chars` and sanitised like a registry description. Digest text is
stored as written; every number in a digest's tables comes from the alert
payload, which the harness renders itself (section 15.4). The coordinator's
tokens are counted against `coordinator_tokens_per_day`; when the budget is
reached the scripted form finishes the day and a `token_budget` health
alert is raised.

### 14.4 Proposing fixes

SPEC §11 step 9 lets the coordinator open a code fix on a branch when a
health alert names a code fault. In v1 this is off by default
(`coordinator.propose_fixes = false`). M4 delivers the command builder, the
deny rules generated from `config/protected_paths.toml` (the scoring, cost,
alert and ledger code, and the state ledgers), and a test with the fake
`claude` proving the generated settings deny those paths. The coordinator
never changes scoring, cost or alert code; the Unix-user separation that
enforces it on the server is part of the deployment package (section 19).

## 15. Alerts, digest and dashboard

### 15.1 Finding alerts

Evaluated after every day's journaling, on clean observations only.

- `persistent_approach`: an approach has at least `persistent_min_days`
  clean paper days; its net Sharpe at 2x over them is positive; and its net
  Sharpe at 1x over them is above the threshold of section 11.4 computed
  from the random control slots over the same days.
- `group_edge`: over the last `group_days` days of `portfolio_clean`, its
  summed net return at 1x is above the `1 - group_level` quantile of
  `group_bootstrap` control portfolios, each the equal-weight mean of `k`
  random control slots drawn with a generator seeded by the date, with `k`
  the mean number of approaches in `portfolio_clean` over those days,
  rounded, at least 1. It is not evaluated before `portfolio_clean` has
  `group_days` days.
- `rank_persistence`: the mean of the last `rank_blocks` non-missing block
  statistics is above zero at the `rank_level` level by a one-sided
  one-sample t-test; it is not evaluated with fewer than `rank_blocks`.
- `revival`: a dormant approach returns to live after at least
  `revival_min_days` dormant trading days.

### 15.2 Health alerts

`data_gaps` (a window above the gap limit; generation skipped),
`run_failed` (a run failed twice), `day_caught_up` (a missed day was
processed late), `journal_mismatch`, `model_removed`,
`few_valid_candidates` (fewer than `min_valid_candidates` trials in the
last `valid_candidates_window_days` calendar days, once the loop has run
that long), `token_budget`, `cost_stale` (a fee, spread or cutoff `checked`
date older than `cost_stale_days`), `revised_data` (a bar file that no
longer matches its index), and `no_finding` (no finding alert in
`no_finding_months` months of live running). Lesser events (an estimated
roll gap, a skipped model, a coordinator fallback) are health notices:
logged to `health/<track>.jsonl`, shown on the dashboard, no issue.

A health event is one JSON line: date, level (`alert` or `notice`), kind,
subject and a detail object. The code that detects a condition returns the
event; the daily run appends it to the health log, which `state.py` writes
from the first mission that has a state directory. Section 15.3's state,
built with the alert rules, decides whether an alert-level event fires and
opens an issue.

### 15.3 Alert state

An alert is identified by its kind and subject. It fires when its condition
turns from false to true and is recorded in `alerts/<track>/state.json`; it
does not fire again while the condition stays true. Each firing writes a
payload file with every number behind it, the thresholds in force and, for
an approach, its description, source, cell, model, and clean and exposed
counts. Alert rules are code, read their numbers from
`config/thresholds.toml`, and are fixed before the first run (I-10).

### 15.4 The digest and the issue

When at least one alert fired, the harness renders the tables of the
payloads, the coordinator writes the prose around them (which alert, the
numbers, the approach, its record beside the control distribution, what
would falsify it), and the page is written to `digests/<track>/<date>.md`.
Each alert opens one issue through

    class IssueSink(Protocol):
        def open(self, title: str, body: str, labels: list[str]) -> str: ...

with two forms: `GhIssueSink` (the `gh` command against the state
repository's remote) and `FileIssueSink` (writes the issue as a file; used
by tests, gates and replays). On a day with no alert the coordinator writes
one line to the run log.

### 15.5 The dashboard

`dashboard.py` renders one self-contained HTML page from the state files,
on every run: no script, no external request, inline styles and inline SVG
charts, a viewport declaration, and a layout that reads on a phone-width
screen. Panels, in SPEC §13's order: gates for the next stage (each
condition of SPEC §14's stage-3 gate with its current value, its threshold,
pass or not yet, and days of clean record against
`stage_gate.min_clean_days`; the two conditions only the owner can meet
are read from `config/gates.toml`);
alert rules (current value against threshold, and how the threshold has
tightened with the trial count); the combined paper portfolio at 1x and 2x
against the band of the random controls; rank persistence per block with
its running mean, the zero line and the significance band; the table; the
experiment ledger (trials, admission rate, clean and exposed counts,
results by model and by cell); health (last run, gaps, recomputation,
worker failure rates, tokens against budget); and the history of threshold
changes. The page displays thresholds and cannot change them. A test
asserts that every threshold shown equals the value the alert code reads.
Where it is hosted is the owner's decision (section 21).

## 16. The daily run and the replay

### 16.1 The steps

`discotrade run-day` processes one trading day `D`, by default the latest
day whose last bar closed before the source's `available_until`; missed
days are processed first, oldest first, one at a time, each raising
`day_caught_up`.

1. Fetch bars up to `D`, run the gap check, update rolls. W and T for `D`
   are section 4.1's.
2. For every live and dormant approach and every control: positions for
   each new bar (approaches in the sandbox), fills and costs through the
   executor, the journal file for `D`, paper records, the combined
   portfolio, lifecycle steps 1 to 4, redraw of the random pool when due.
3. List the cells with a free slot or flagged weak; compute the W profile.
4. The coordinator chooses one cell and writes its brief (section 14).
5. One worker call, validation, the correlation gate, scoring on T,
   admission or rejection, the ledger rows (sections 12, 13, 10.3). Skipped
   when the gap check says so.
6. Alert rules, and the periodic checks that fall due: rank persistence at
   a block's end, journal recomputation on the first trading day of the
   week.
7. The table and the dashboard; the digest if an alert fired, else the run
   log line.
8. Commit the state repository; open an issue for each alert.
9. Fix proposals, when enabled (section 14.4).

### 16.2 Atomic days

A run takes a lock in the state directory. Everything a day writes goes to
a staging directory and is moved into place only when steps 1 to 7 have
all succeeded, with two exceptions that are written at once and survive a
failed day: a worker response, stored before it is parsed so that a paid
call is never repeated (the retry of the day replays it), and the health
log. Then the state repository is committed with the message
`run <track> <date>` and pushed when it has a remote (a failed push is a
health notice). A day that fails is retried once from a clean staging
directory. A second failure discards the staging directory, leaves every
state file unchanged except those two, records `run_failed` in the health
log and through the issue sink, and exits non-zero (SPEC §11).

### 16.3 Budgets

The two token budgets end generation or coordinator calls for the day;
journaling and scoring always complete (SPEC §11).

### 16.4 Replay

`discotrade replay --from A --to B` runs the daily steps for each trading
day in order against one state directory, with the clock set to each day
(I-12) and with the source, the provider, the coordinator, the issue sink
and the sandbox backend chosen by options. A replay over a synthetic source
with scripted roles is fully deterministic: two replays give state
directories with identical content hashes. A historical replay on vendor
data is how the pipeline is shaken out and how each approach's post-cutoff
months become clean evidence (SPEC §10); it is run by the owner, not by a
gate.

## 17. Synthetic markets

`sources/synth.py` generates bars deterministically from a seed, for a set
of synthetic instrument records (`tests/fixtures/config/`), on their
calendars.

### 17.1 The null market

Hourly log returns are independent normal draws with a per-instrument
volatility and an hour-of-day volatility pattern; opens differ from the
previous close by a small independent gap; highs and lows enclose open and
close; volume is log-normal with an hour-of-day pattern. Nothing in it is
predictable. Options: a fraction of bars dropped at random (to exercise the
gap check), an instrument that does not allow shorting, and contracts: a
quarterly roll schedule, the `contract` column, and per-contract bars for
`fetch_contract`, where each contract's price is one gap-free underlying
series plus a constant known per contract. The adjusted series as of any
bar must therefore equal the underlying plus the constant of the contract
current at that bar.

### 17.2 The planted edge

The null market plus one known, small, exploitable pattern: on the named
instruments, the bar whose exchange-local hour equals `planted.hour` gets
an added drift `planted.drift` (default 10 basis points), a time-of-day
effect well above the round-trip cost of the synthetic instruments. The
drift and the instruments' volatility are sized so that, over the clean
days gate M4 requires, the planted approach's expected Sharpe clears the
alert threshold by more than four standard errors; the mission that builds
the gate computes that margin and reports it.
`tests/fixtures/worker_corpus/planted/` contains the strategy that exploits
it (long during that hour, flat otherwise) among others that do not. If the
system cannot find and flag an edge known to exist, its silence on real
data means nothing (SPEC §14).

## 18. Tests and gates

### 18.1 The commit gate

Every test under `tests/gates/` carries the marker `gate` and the marker
of its milestone (`gate_m0` to `gate_m5`). `./scripts/check` runs, from a
clean checkout: `uv sync --extra dev`, `ruff check .`, `pytest -m "not gate
and not network and not live"`, and a command-line smoke test (`discotrade
--help`, `discotrade config check`).
It prints `check: green` and exits 0 only when all pass. Tests marked
`container` skip, with the reason printed, when no container runtime is
found. It is run three times in a row before every commit: a test that
passes twice and fails once is a failing test.

### 18.2 The milestone gate

`./scripts/gate <milestone>` (for example `./scripts/gate M0`) runs `pytest
-m gate_<milestone>` over `tests/gates/` with the environment variable
`DISCOTRADE_GATE=1`, under which a test that would skip fails instead: a
gate never passes by skipping. It prints one line per gate item of section
18.3 (`G0.1 PASS ...`), then `gate M0: PASS` or `gate M0: FAIL`, and exits
0 only on PASS. A milestone with no gate tests fails. `./scripts/gate
<milestone> <item>` runs one item. Each gate must finish within 15 minutes
on a laptop; a gate that cannot is a finding for the architect, never a
reason to weaken an item.

**The gate configuration.** Gates that replay days run on the fixture
track `test_synth` (four synthetic instruments that can all be shorted,
`w_days = 28`, `t_days = 7`, `history_cap_bars = 480`, `block_days = 7`)
and on `tests/fixtures/config/thresholds_gate.toml`, a copy of the
production thresholds with exactly these values changed so that a replay
fits the time limit: `min_changes_w = 10`, `min_trades_t = 10`,
`dormant_window_days = 15`, `persistent_min_days = 30`, `group_days = 40`,
`rank_blocks = 6`, `revival_min_days = 10`. A test asserts the two files
differ in those keys only. The mechanisms a gate proves are the production
ones; each rule is also unit-tested at its production value. Every seed a
gate uses is written in the test; a statistical item uses a bound of four
standard errors, so that a correct implementation does not fail by chance.

A milestone is met when its gate command passes at the tip of the branch
and the cold review of the mission that closes it has no blocker. The gate
tests are part of the specification: a gate test that asserts less than
its item below says is a blocker, even when it passes.

### 18.3 The gates

**M0 Harness core** (SPEC phase 0).

- G0.1 Three hand-written reference strategies under `reference/` (a
  moving-average trend rule, a z-score reversal rule, an hour-of-day rule)
  are run on the fixture track `test_mixed`: three synthetic instruments,
  one that rolls, one that cannot be shorted and one with a proportional
  fee, with dropped bars. Per-bar
  gross and net returns at 1x and 2x, every cost component and every
  metric of section 8 equal, to 1e-12, an independent calculation,
  `tests/gates/independent_calc.py`: a plain loop written from sections 5.6,
  7 and 8 alone, which reads the fixture bars and TOML directly and imports
  nothing from `discotrade` (a test checks its imports). The mission that
  builds it gives it to a sub-agent of its own, told not to open
  `backtest.py`, `costs.py`, `rolls.py` or `metrics.py`.
- G0.2 A deliberately cheating strategy (it keeps references to earlier
  frames, inspects the index, and tries to reach later rows) cannot gain:
  its positions pass truncation invariance, and its score on a window is
  the same whether or not later bars exist in the store.
- G0.3 The store refuses a bar that is not closed and a bar that is not
  later than the last; old rows are unchanged by an append; the gap check
  finds exactly the dropped bars and none across the daily break, the
  weekend or a closure; the adjusted synthetic series as of each bar equals
  the gap-free underlying series plus the current contract's constant
  (section 17.1); a carried position pays the roll cost and a flat one does
  not.
- G0.4 `discotrade config check` passes on the `hourly` track with its
  eight instruments, and no file under `src/` contains, as a whole word, an
  instrument symbol, contract root or venue named in `config/` (I-9).

**M1 Journal, controls and ledger** (SPEC phase 1).

- G1.1 A replay of one year of the null market with controls only, on the
  gate configuration: across the random control slots, the mean summed
  gross return is within four standard errors of zero, and the mean summed
  net return at 1x is within four standard errors of minus the mean summed
  cost, which is positive, so the controls are centred on minus their
  costs; the mean rank-persistence statistic over the year's blocks,
  computed on the control slots, is within four standard errors of zero.
- G1.2 The journal recomputes exactly: `journal recompute --all` matches
  every day; running the last day again writes nothing; a second replay
  from scratch gives the same content hashes.
- G1.3 A scripted lifecycle scenario (candidates with known scores fed in
  place of workers) shows each transition of section 10.3: admission into
  a free slot, displacement of the weakest, refusal for too few trades and
  for a non-positive score, dormancy, return, retirement on failure and
  after the dormant limit; the ledgers hold one row per event and are never
  rewritten; the table and the two portfolio series match a hand count.
- G1.4 The deflated figures and the tightening function match hand-computed
  values for fixed inputs.

**M2 Sandbox and validation** (SPEC phase 2).

- G2.1 Every submission of the hostile suite is rejected at its documented
  stage, with the container backend really running, and none produces a
  trial, a file outside its scratch space, or a harness failure.
- G2.2 A duplicate with the sign flipped is caught by the correlation gate
  and named; a submission correlated below the limit passes.
- G2.3 A trusted probe run through the container backend reports from
  inside: no route to the network, a read-only root, a non-root user, and
  a mount that holds the W bars and no later bar.
- G2.4 The validation sequence on valid fixtures: the grid fixes the best
  combination on W, determinism and activity pass, and each of the five
  stages fails on the fixture built to fail it, with an error text.

**M3 Workers** (SPEC phase 3).

- G3.1 Twenty replay days on the null market with the scripted provider
  replaying a corpus attributed to three model families yield at least ten
  valid candidates that are mutually distinct (pairwise absolute
  correlation on W at most `corr_max`).
- G3.2 Over those days no cell is always served by the same model; a retry
  carries the error text; every response is stored in full; a model whose
  failure rate crosses the limit over a full window is removed and the
  health alert is raised; the token budget ends generation while journaling
  completes.
- G3.3 No prompt contains an instrument symbol, a venue, a contract name, a
  calendar date, a raw bar or a score; the labelling differs between
  prompts; the scaling function leaves returns unchanged and scales a
  price-unit field; the registry block is sanitised (an injected
  instruction in a description arrives as inert quoted text).

G3.1 proves the pipeline, not the models. Whether real models reach the
same yield is live check L3.

**M4 Coordinator and alerts** (SPEC phase 4).

- G4.1 Sixty replay days on the null market, unattended, with the scripted
  coordinator and provider, the file issue sink and the subprocess backend:
  exit 0, sixty commits in the state repository, no `run_failed`, a run log
  line or a digest for every day.
- G4.2 The planted edge, on the gate configuration: a replay on the
  planted market, long enough for `persistent_min_days` clean paper days
  after the planted approach is admitted, fires `persistent_approach` for
  the planted approach and for no other subject (`group_edge` may fire,
  since the portfolio holds the planted approach); the twin replay with
  the drift set to zero and every seed unchanged fires no
  `persistent_approach` at all. Both hold for each of three seeds written
  in the test, not for one chosen seed.
- G4.3 Failure handling: a day made to fail twice leaves every state file
  but the health log and the stored responses unchanged, records
  `run_failed`, and its retry replays the stored response without a second
  provider call; a missed day
  is caught up in order with `day_caught_up`; re-running a finished day
  writes nothing.
- G4.4 The coordinator's input contains no score (the property test of
  section 14.1); an out-of-list cell choice falls back to the scripted
  choice; the generated deny rules cover every protected path.
- G4.5 The dashboard renders from the replay's state, shows every panel of
  section 15.5, makes no external request, and shows thresholds equal to
  the ones the alert code reads; a threshold changed without a history
  entry fails the test of section 4.3.
- G4.6 Three replay days with the container backend complete (the same
  loop, the real boundary).

**M5 Deployment package** (SPEC phase 5, as far as a builder can take it).

- G5.1 `discotrade init-state` creates a state repository; `discotrade
  doctor` (offline) passes on it and fails, naming the fault, on each of: a
  state directory inside the code repository, a missing container runtime,
  a threshold without history, a `test_only` instrument in a live track.
- G5.2 `run-day` with the vendor adapter driven by the fake client
  completes one day end to end, including the 24-hour embargo and the cost
  refusal.
- G5.3 `deploy/` holds the cron entry, the two Unix users and the
  ownership script generated from `config/protected_paths.toml`, the
  coordinator's settings with its deny rules, and the firewall note; a test
  parses each and checks the protected paths are read-only for the
  coordinator's user in the generated script.
- G5.4 `docs/OPERATIONS.md` documents every live check of section 19.3
  with its exact command; a test lists the checks `doctor --live` knows and
  fails when one is undocumented or a documented one is unknown.

## 19. Deployment and live checks

### 19.1 Where it runs

Development and replays run locally. The live daily loop runs on a small
always-on server, started by plain cron, with untrusted generated code kept
off personal machines (SPEC §11). The harness and the coordinator run as
two Unix users; the coordinator's user cannot write the scoring, cost,
alert and ledger paths (SPEC §12, §17). The coordinator authenticates with
an API key, never a personal subscription.

### 19.2 The package

Milestone M5 delivers `deploy/` and `docs/OPERATIONS.md`: installation,
the two users, the state repository and its private remote, the secrets as
environment variables of the harness user only, the model provider's
zero-data-retention switch turned on (SPEC §17), the sandbox image, the
cron line, the first historical replay, and the live checks. Nothing in the
series deploys anything.

### 19.3 Live checks (the owner's, never a gate)

`discotrade doctor --live <name>` runs one check against the real service
and prints what it found. Each is built by the mission that builds the code
it exercises, and is tested only for its offline behaviour (a clear refusal
without the key).

- L1 `vendor`: the key works; the cost estimate for the full history; the
  real delay; one day fetched; `contract` resolved; gap fraction per
  instrument on real data.
- L2 `spreads`: measure spreads from a quote sample and write the tables;
  report any marginal instrument above one tick (SPEC decision 14).
- L3 `workers`: the provider's model list against the pool; whether a seed
  is accepted; twenty replay days with the real pool (SPEC phase 3's own
  wording).
- L4 `coordinator`: one real headless coordinator call for a brief and one
  for a digest, with the installed flags.
- L5 `sandbox`: the container self-test on the server.
- L6 `issues`: one test issue opened in the state repository's remote and
  closed.
- L7 `costs`: print every unverified fee, tick size, multiplier, session
  and cutoff, for checking against a statement or the exchange's file.
- L8 `planted`: the planted market of section 17.2 with the real worker
  pool. For each model, a few dozen calls on the planted market's W
  profile for the cell the edge lives in and for its neighbours, each
  submission validated as usual; the check reports, per model, how many
  submissions were valid, how many are correlated above `corr_max` on W
  with the fixture strategy that exploits the edge, and how many were
  positive net of 2x costs on T. Gate G4.2 proves the harness flags a
  planted edge that is handed to it; only this check asks whether a real
  model, given only the profile, proposes it. If none does, the profile is
  too thin to act on, and a silent year of the live system would mean
  nothing (SPEC §14).

L1 and L2 can be run as soon as M0 is met, and are best run then: gaps,
roll behaviour and real spreads surface while the data layer is fresh.

## 20. Readings of the spec

Where `SPEC.md` leaves a definition open, this document chose one. Each is
a starting value in the sense of SPEC §15: the owner may replace it with a
decisions file, and none changes an invariant.

- R-1 Trade counts (`min_changes_w`, `min_trades_t`) are summed over the
  basket, not per instrument (sections 8, 10.3, 12.2).
- R-2 W and T are measured in calendar days; the history cap is a fixed
  number of bars (section 4.1, SPEC decision 4).
- R-3 "Holding cost" at a roll is two extra trades at the full per-trade
  cost; the price gap between contracts is removed by adjustment and is not
  a cost (section 7.3).
- R-4 The off-session spread is twice the main-session assumption until
  spreads are measured (sections 4.2, 5.7).
- R-5 Slippage volatility is the deviation of the last 24 hourly returns;
  the coefficient starts at 0.02 (section 7.3). The owner set it on
  2026-10-11: about one extra tick per side on the S&P micro at 20 basis
  points of hourly volatility, a judgment from tick sizes and not a
  measurement, to be calibrated against real fills in stage 2. At 0.1,
  slippage would be nearly nine tenths of the cost and would decide the
  experiment by itself. The 2x stress run stays.
- R-6 The gap limit applies to the basket pooled, not per instrument
  (section 5.4).
- R-7 Returns are summed, not compounded; Sharpe is annualised with 252
  trading days (section 8).
- R-8 "Under 50 ms per call" is the 95th percentile, with a hard limit of
  500 ms on any call (section 12.2).
- R-9 A dormant approach returns to live under rule 3 of section 10.3,
  after at least five dormant trading days.
- R-10 Random controls follow the state machine of section 10.1 and match
  live approaches through holding time and trade rate.
- R-11 The tightening rule is section 11.4's, with an expected half false
  alert per year; the comparison uses the normal approximation of the
  control distribution.
- R-12 "Beats the control distribution at the 5% level" for the combined
  portfolio is the bootstrap of control portfolios in section 15.1.
- R-13 "Above zero at the 5% level" for rank persistence is a one-sided
  t-test over the last twelve block statistics (section 15.1).
- R-14 A model's cutoff date is the last day of its stated cutoff month
  (section 11.3).
- R-15 Registry neighbours are the cells of the same family or the same
  horizon (section 13.3).
- R-16 The parser takes the last fenced block of a response, because most
  pool models print their reasoning first (section 13.4).
- R-17 Fix proposals by the coordinator are built but off by default
  (section 14.4).
- R-18 Bar files are kept out of the state repository's history; their
  index and hashes are in it (section 5.2).
- R-19 The token budgets and the maximum output tokens in
  `config/thresholds.toml` are placeholders until the owner sets them.
- R-20 A window scored on its own starts flat and does not trade its last
  target (section 7.1).
- R-21 The Claude worker fallback for a failing cell is built but off by
  default, so that no paid call is made that the owner has not switched on
  (section 13.6).
- R-22 The W profile has no field in price or volume units, so per-prompt
  scaling has nothing to scale in v1; labels are still shuffled per prompt
  (sections 13.1, 13.2).
- R-23 The admission score, and the grid's "best net result", are the net
  Sharpe at 1x (sections 10.3, 12.2).
- R-24 The 60-line cap counts physical lines of the submitted text
  (section 12.1).
- R-25 A day's candidate gets one retry in all, whether the first failure
  was validation or duplication (sections 12.2, 13.7).
- R-26 The dormancy rule applies once an approach has 30 trading days of
  paper record (section 10.3).
- R-27 "Centred near the negative of costs" and "near zero" in SPEC phase 1
  are the four-standard-error tests of gate item G1.1.
- R-28 Milestone gates run on a scaled-down fixture track and threshold
  copy so that they finish in minutes (section 18.2); the production
  numbers are unit-tested, and proven at scale only by the owner's first
  historical replay.

## 21. Open items

Carried from SPEC §15; none blocks the series, and none is a builder's to
close.

Owner decisions: the length of T (after G1.1 and the first real replay show
trade counts per window); the alert thresholds before phase 5; where the
dashboard is hosted; the stage-3 gate values; the capital cap, position
limits and drawdown limit; any reading of section 20.

Still to verify, each by a live check: spreads by hour (L2); exchange fees
for the metals and crude contracts (L7); whether real workers can find a
planted edge (L8); the vendor's real price and delay
(L1); the worker API's seed and model ids (L3); the broker entity and
permissions, and tax treatment (outside this system).

## 22. Traceability

| SPEC | This document | Milestone |
|---|---|---|
| §2 terms, windows | 4.1, 16.1 | M0, M1 |
| §3 architecture | 2 (I-1, I-8), 3 | all |
| §4 data layer | 4, 5, 13.2 | M0, M3 |
| §5 interface, validation | 6, 12.1 to 12.3 | M0, M2 |
| §6 cost model and fills | 7, 8 | M0 |
| §7 workers | 13 | M3 |
| §8 diversity | 4.1, 12.3, 13.3, 13.6 | M2, M3 |
| §9 journal, lifecycle | 9, 10 | M1 |
| §10 safeguards | 10.1, 10.2, 11 | M1, M4 |
| §11 daily procedure | 16 | M1, M4 |
| §12 isolation | 2 (I-7, I-8, I-13), 12.4, 12.5, 14.4 | M2, M4, M5 |
| §13 alerts, digest, dashboard | 15 | M4 |
| §14 phases, stages | 1, 18, 19 | M0 to M5 |
| §15 open items | 20, 21 | owner |
| §17 findings | 4.2, 13.5, 13.6, 14.2, 19 | M0, M3, M4, M5 |
