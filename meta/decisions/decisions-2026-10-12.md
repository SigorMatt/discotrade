# Decisions — 2026-10-12 (architect role, consultation 2, after REVIEW-1)

Clarifications where `DESIGN.md` is silent or ambiguous. Each breaks no
invariant, moves no gate, changes no threshold and changes no value of a
frozen configuration file (`meta/ARCHITECT.md` §1, §5). They bind mission 2
and every later mission until a newer decisions file says otherwise.

1. **D-001, DESIGN §4 with §4.2: the `[spec]` table is confirmed.** The
   companions `checked`, `source` and `verified` of an instrument's
   top-level contract values (`multiplier`, `tick_size`, `trusted_from`,
   `main_session`) live in a `[spec]` table, required when the adapter is
   not `synth`, optional for synthetic records. Reason: TOML cannot hold a
   top-level `source` key beside the `[source]` table; `[spec]` is what
   mission 1 built and it keeps every companion.

2. **D-002, DESIGN §5.4: a window's gap fraction runs to the end of `D`.**
   For the window fraction only, the expected bars of an instrument are
   its expected bar times in the window's trading days, from the later of
   the window's start and `trusted_from` to the end of `D`'s trading day,
   and its missing bars are those of them with no stored bar. An
   instrument whose feed stopped, or that has no stored bar at all,
   therefore counts as missing for every bar it lacks, and generation is
   skipped by the existing `data_gaps` rule. The bars appended to
   `gaps.jsonl` keep §5.4's first definition (from the later of
   `trusted_from` and the first stored bar to the last stored bar), bounded
   at `D` by decision 3. No new health kind. Reason: a stopped feed is
   missing data, and SPEC §4 and §11 skip generation on missing data; a
   numerator and denominator limited to the stored span cannot see it
   (REVIEW-1 note on D-002: an empty store gave a fraction of 0).

3. **REVIEW-1 should-fix 4, DESIGN §5.4 with I-12: the gap check for day
   `D` reads only bars up to the end of `D`.** Stored bars whose `ts` is not
   before the end of `D`'s trading day are neither reported nor appended to
   `gaps.jsonl`, so a replay of a past day equals the original run of that
   day. The default `D` of `discotrade bars gaps` is §16.1's: the latest
   trading day whose last expected bar closed at or before the source's
   `available_until` at the `--as-of` instant (for synthetic sources,
   `available_until(now) = now`).

4. **REVIEW-1 should-fix 4: `gaps.jsonl` is appended atomically.** An
   append writes the whole file beside the old one, with every earlier line
   byte-identical, flushes and `fsync`s it, and renames it into place, as
   the bar store does. Reason: a torn last line made the next run crash.

5. **REVIEW-1 should-fix 1, DESIGN §5.2: an interrupted append is
   completed, not refused for ever.** A month file whose content hash
   differs from the index, or that the index does not list, is an
   interrupted append when (a) its first `r` rows, `r` being the row count
   the index records for that file (0 when unlisted), have exactly the
   indexed content hash, and (b) every further row is later than the
   instrument's indexed last `ts`. The writer checks this before every
   append to an instrument and `bars fetch` before every fetch; it then
   completes the index for that file (rows, last `ts`, content hash),
   changes no row, and returns a health notice of kind `store_recovered`
   naming the instrument and the file. Every other mismatch stays a
   revised data point, refused as now. The reader does not repair: it
   refuses both cases, with an error that says which, so that only a
   revised data point will raise `revised_data`. The writer `fsync`s a
   rewritten month file before the rename, and the directory after it.
   Reason: the rows of an interrupted append were written by the harness
   from a closed source bar; recording them changes no recorded row (I-5),
   while refusing them locked the instrument out for good.

6. **REVIEW-1 should-fix 1, DESIGN §5.1: a bar with a value that is not
   finite is not stored.** The writer refuses a bar whose `open`, `high`,
   `low`, `close` or `volume` is NaN or infinite, and writes nothing of
   that call. `bars fetch` drops such bars from a source's result before
   writing and prints how many it dropped per instrument; to the gap check
   they are missing bars, never interpolated.

7. **REVIEW-1 should-fix 3, DESIGN §3 with I-14: the state-directory
   refusal does not depend on how the package is installed.** A `--state`
   path is refused (exit 2, naming I-14) when it, or any directory above
   it, is a discotrade code repository: a directory that holds both
   `pyproject.toml` and `src/discotrade/`. The existing check against the
   package's own repository stays. An empty or all-blank `--state`, and an
   empty `DISCOTRADE_STATE`, are usage errors (exit 2).

8. **REVIEW-1 should-fix 6, DESIGN §4.3: the frozen-config comparison is
   type-strict.** A current value equals its frozen value only when both
   have the same TOML type (boolean, integer, float, string, date or
   time, array, table) and the same value: `5` against a frozen `5.0`, and
   `true` against a frozen `1`, are changes. A removed frozen file keeps
   failing the test: removing one is the owner's, and that change updates
   the frozen map and `config/HISTORY.toml` itself. No removal form is
   added to `HISTORY.toml`.

9. **REVIEW-1 should-fix 7, DESIGN §18.2: a single-item gate run never
   prints the milestone's verdict.** `./scripts/gate <M> <item>` prints the
   item's line and ends with `gate <M> <item>: PASS` or `gate <M> <item>:
   FAIL`; only the whole-milestone run prints `gate <M>: PASS`. A test that
   lives under `tests/gates/` or carries a `gate_m0` to `gate_m5` marker
   must carry `gate` and exactly one milestone marker; collection fails
   otherwise, naming the test.

10. **REVIEW-1 should-fix 2, DESIGN §4.2 with §17.1: every generator
    setting is a `[source]` key.** A synthetic record's `[source]` table
    carries, required for `adapter = "synth"`: `gap_scale`, `range_scale`,
    `volume_median`, `volume_sigma`, `hour_vol_amplitude`,
    `hour_volume_amplitude` and `hour_peak_utc`, read by `synth.py` in
    place of its constants, with the shapes the module documents (the
    volatility shape `1 + hour_vol_amplitude * cos(2 pi (h - hour_peak_utc)
    / 24)` scaled to root mean square one; the log-volume offset
    `hour_volume_amplitude * cos(2 pi (h - hour_peak_utc) / 24)`). Every
    fixture record gets the values mission 1 hard-coded (0.1, 0.5, 1000.0,
    0.5, 0.5, 0.5, 15), so no bar changes. The contract keys of §17.1 (the
    roll schedule and the per-contract constants) are `[source]` keys too.
    Synthetic records live under `tests/fixtures/config/`, are invented by
    the project and are not in the frozen map, so this is not a
    frozen-config change. Reason: §4.2 puts "the keys section 17 names" in
    `[source]`, and gates replay on these bars.

11. **DESIGN §5.5, I-9: what the vendor adapter may name.** I-9 forbids
    naming a market, a contract root or a venue. `sources/vendor.py` may
    name the vendor's client package and the key variable
    `DATABENTO_API_KEY`, which DESIGN §5.5 gives; a vendor is not a venue.
    Datasets, symbols, venues and roll rules come from the instrument's
    `[source]` table only. The `vendor` extra in `pyproject.toml` names the
    vendor's official client; `./scripts/check` does not install it.

12. **DESIGN §5.5: the crypto adapter's endpoint is configuration.** The
    endpoint's base URL and the market's name are `[source]` keys
    (`base_url`, `market`) of a `test_only` record under
    `tests/fixtures/config/instruments/`. No record is added under
    `config/instruments/` (a new frozen file is the owner's).
    `available_until(now) = now`. Tests drive it with
    `httpx.MockTransport`; a test that reaches the real endpoint is marked
    `network` and is in no gate.

13. **DESIGN §5.7: measuring spreads writes a new file and nothing else.**
    `discotrade spreads measure --symbol <s>` reads a quote sample (bid,
    ask, `ts`) from the vendor adapter, or from `--quotes <file>` (Parquet)
    for tests, computes the median quoted spread per exchange-local hour in
    ticks, and writes `<config>/spreads/<symbol>.toml` with `checked`,
    `source`, `verified = false` and a description of the sample. It
    refuses to overwrite an existing file, and prints that the new file
    needs a `config/HISTORY.toml` entry and a decisions file before it is
    committed (§4.3). An hour in which the calendar is never open in the
    sample's days (a daily break) takes the largest median of the measured
    hours, and the file's description lists those hours; an hour in which
    the calendar is open but the sample has no quote is an error naming
    the hour, and nothing is written.

14. **DESIGN §5.7 with SPEC decision 14: the marginal-spread warning.**
    `discotrade config check` prints a warning, and still exits 0, for
    every instrument whose measured spread table has a main-session hour
    above 1.0 tick. The code names no instrument.

15. **DESIGN §19.3: what `doctor` is in step S0.2.** `discotrade doctor
    --live vendor` (L1) and `discotrade doctor --live spreads` (L2) are
    built with their live behaviour, and are tested offline: without the
    key each refuses clearly, exits 1 and makes no request. Plain `doctor`
    and every other check name are usage errors that name step S5.1, which
    builds them.

16. **DESIGN §15.2: notices before the health log exists.** An estimated
    roll gap (§5.6) and a completed interrupted append (decision 5) are
    health notices returned as values in the §15.2 event shape; `bars
    fetch` prints them. The health log writer is step S1.1's.

17. **REVIEW-1 should-fix 5: the provenance strings are the owner's.** The
    `[spec]` `checked` and `source` strings of the eight instrument records
    suggest a reading of the exchange's pages that did not happen, and
    `[cost] source = "SPEC.md §17"` also covers spread and slippage values
    that come from DESIGN §4.2 and R-5. These are values of frozen files.
    No builder changes them; mission 2 files the finding, and the owner
    decides (`meta/BACKLOG.md`).

## Added at consultation 5, after REVIEW-2

Items 1 to 17 above are unchanged. Items 18 to 29 below bind mission 3
and every later mission until a newer decisions file says otherwise; the
same rules apply to them (no invariant broken, no gate moved, no
threshold or frozen value changed).

18. **REVIEW-2 should-fix 1, DESIGN §5.2 with decision 5: the reader
    refuses a month file the index does not list.** Every read of an
    instrument (`read_range`, `last_n`, and any other reader entry point)
    refuses when that instrument's directory holds a month file the index
    does not list, whatever range the read asks for, as it already
    refuses a listed file whose hash differs. The error says which case
    it is: an interrupted append (the file passes decision 5's test with
    `r = 0`) or a revised data point. The reader still repairs nothing;
    the writer and `bars fetch` complete an interrupted append as
    decision 5 says. Reason: an unlisted file may be an interrupted
    append into a new month, which `last_n` would otherwise silently
    leave out, or a revised past month.

19. **REVIEW-2 should-fix 2, DESIGN §16.1 with decision 3 and I-12: `bars
    fetch` defaults its gap-check day to §16.1's `D`.** With no `--day`,
    `bars fetch` checks the same `D` that `bars gaps` checks for the same
    `--as-of` (decision 3), computed by the same function: the latest
    trading day whose last expected bar closed at or before the source's
    `available_until` at the `--as-of` instant. Reason: a day that is
    still open for a delayed source (the vendor's 24 hours) must not be
    checked, or a later replay of it would append to `gaps.jsonl` what
    the original run did not.

20. **REVIEW-2 note on U5, I-11: tests cannot open a socket.** An autouse
    fixture in `tests/conftest.py` makes every attempt to open a network
    connection fail with a clear error in every test not marked `network`
    or `live`. Reason: offline tests stayed offline only because each one
    injected a fake; a forgotten injection must fail, not reach the
    network.

21. **DESIGN §6.1, §6.3 with I-7: how a strategy is loaded before the
    sandbox exists.** In step S0.3 only trusted strategies are run: the
    files under the repository's `reference/` and test fixtures. The
    loader (`strategy.py`) executes the source text in-process in a fresh
    namespace in which `indicators` names `discotrade.indicators`, so a
    strategy may use the bound name or write `import indicators`. It
    checks the §6.1 shape with numbers read from `config/thresholds.toml`
    (`validation.max_params`, `max_lines`, `grid_max_params`,
    `grid_max_values`): `PARAMS` a dict of at most `max_params` numeric
    values, `GRID` optional, naming only `PARAMS` keys, at most
    `grid_max_params` keys with at most `grid_max_values` values each, a
    callable `position`, at most `max_lines` physical lines. Anything
    else is refused naming the rule. `discotrade backtest` refuses (exit
    2) a strategy file that does not lie under the repository's
    `reference/` directory. The static check of §12.1 and the sandbox
    are M2's; nothing in S0.3 runs a worker's text.

22. **DESIGN §6.2: a result outside the contract ends the evaluation.**
    A `position` result that is not a real finite number within [-1, 1],
    or a call that raises, is an error naming the instrument and the
    bar's `ts`; the evaluation stops and nothing is clipped or
    substituted. After that check, a negative result on an instrument
    with `shorting = false` is clipped to 0. Whether such an error
    rejects a candidate is the validation sequence's (§12.2, M2).

23. **DESIGN §7.1 and §8 with §5.3: windows and trading days when a
    subject's instruments have different calendars.** A window is given
    as an inclusive range of trading dates. A bar belongs to the window
    when its trading date, by its own instrument's calendar, is in the
    range, and its `ts` is not before the instrument's `trusted_from`.
    Each instrument is evaluated on its own: the bars before its first
    window bar, up to the history cap, are context, and `h(u0) = 0` at
    its first window bar `u0` (R-20). The subject's days are the sorted
    union of the trading dates of its instruments' window bars; its
    daily net return on a day is the sum, over its `N` instruments, of
    that instrument's summed `net(u, m)` over its bars of that day,
    divided by `N`, an instrument with no bar that day contributing 0.
    `N` counts every instrument of the subject, including one with no
    window bar. Reason: `test_mixed` mixes a weekly calendar with an
    always-open one, and a track has no calendar of its own.

24. **DESIGN §5.6, §7.2 and §7.3: the edges of the formulas.** At an
    instrument's first window bar the previous position is 0, so its
    gross, trade and roll cost are 0. `u-1` is always the previous
    stored bar, whether or not bars are missing between them. A roll
    happens at bar `u` when its `contract` differs from the previous
    stored bar's; its gap is the one recorded in
    `<state>/rolls/<track>/<symbol>.jsonl`, and an evaluation that meets
    a contract change with no roll record stops with an error telling
    the user to run `bars fetch`. `sigma(u)` uses stored bars before the
    window too. Every adjusted price in a formula is adjusted as of the
    bar the formula names (`u` for `gross(u)`, `s` for `r(s)`).

25. **DESIGN §7.3, §7.4: the per-bar result and the executor's orders.**
    For each instrument and each window bar `u`, the evaluation yields
    one row: `ts`, `contract`, the trading date, `p` (the target computed
    at `u`), `h` (the position in force during `u`), `gross`, `trade`,
    the four cost components at 1x in return units (`fee = trade(u) *
    fee(u)`, `spread = trade(u) * half_spread(u)`, `slippage = trade(u) *
    slip(u)`, `roll = roll_cost(u)`), `cost` (their sum), `net_1x` and
    `net_2x`. `SimExecutor` receives one `Order` per instrument per
    window bar (decision bar `u-1`, previous position `h(u-1)`, target
    `h(u)`) and returns one `Fill` per order with the fill bar `u`, the
    raw fill price `Or(u)` and the four components; an order with no
    trade has zero fee, spread and slippage and may still carry a roll
    cost. The per-bar rows are built from the fills. Metrics use them:
    `trades` counts rows with `trade > 1e-9`; `breakeven_cost` is the sum
    of `gross` over the sum of `trade` plus the rolled turnover `2 *
    |h(u-1)|` at each roll, times 10000; `avg_holding_bars` is not a
    number when there is no run.

26. **DESIGN §7.3: the cost configuration hash.** The cost model's
    version is the string `c1`. Its config hash is the sha256, in hex, of
    the canonical JSON (keys sorted, no whitespace) of a map from each
    instrument symbol in force to its `[cost]` values without the
    companions `checked`, `source` and `verified`, its `tick_size`, its
    `multiplier` when present, and its spread table's 24 values or null.
    A change to any of those values changes the hash; a change to a
    companion does not.

27. **DESIGN §3: the `backtest` command.** `discotrade backtest <file>
    --from <date> --to <date>` evaluates the strategy file (decision 21)
    with its `PARAMS` on every instrument of `--track`, from the bars and
    rolls stored in `--state`, over that window, and prints the metrics
    of §8 at 1x with `sharpe_2x` and the total return at 2x, the cost
    totals by component, the cost model's version and its config hash.
    `--json` prints the same as one JSON object, a number that is not a
    number as `null`. Exit 1 when a bar file is refused (decisions 5 and
    18), a roll record is missing (decision 24) or the strategy breaks
    its contract (decision 22); exit 2 for a usage error, including a
    file outside `reference/` and `--from` after `--to`.

28. **`meta/ROADMAP.md`: step S0.3 is split in two.** The step as written
    (contract, indicators, loop, costs, executor, metrics, command,
    reference strategies, independent calculation, gate tests) does not
    fit seven units. Mission 3 builds step S0.3 (everything but the
    independent calculation and the gate tests, plus REVIEW-2's two
    should-fix items); mission 4 builds step S0.4 (the independent
    calculation, the cheating strategy, the gate tests of G0.1 to G0.4)
    and closes M0. No gate item moves (`meta/ARCHITECT.md` §5).

29. **DESIGN §18.3 G0.1: what the independent calculation may read.**
    `tests/gates/independent_calc.py` is written from DESIGN §5.6, §7
    and §8 and from decisions 23 to 26 above, which clarify those
    sections and contain no code; it reads the fixture bars, the roll
    file and the TOML directly and imports nothing from `discotrade`.
    Mission 4 states this in the brief of its sub-agent.
