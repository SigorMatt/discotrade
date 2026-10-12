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

## Added at consultation 6, after REVIEW-3

Items 1 to 29 above are unchanged except where item 33 renumbers a
mission. Items 30 to 33 below bind mission 4 and every later mission
until a newer decisions file says otherwise; the same rules apply to them
(no invariant broken, no gate moved, no threshold or frozen value
changed).

30. **REVIEW-3 blocker 1, DESIGN §8: when the deviation of a daily series
    is 0.** For `sharpe` and `sharpe_2x`, the deviation of the daily
    series `d` is 0, and the Sharpe is not a number, when every value of
    `d` equals its first value, or when `std(d, ddof=1)` is not above
    `1e-12` times the largest absolute value in `d`. The tolerance is a
    constant of the §8 formula, like the `1e-9` trade floor, and lives in
    the module, not in `config/thresholds.toml`. The independent
    calculation of step S0.4 applies the same rule (item 29 reads
    "decisions 23 to 26 and 30"). Reason: a constant series has a
    mathematical deviation of 0, but the floating-point `std` of most
    constants is a rounding residue (about `1e-17` for `[0.1, 0.1, 0.1]`),
    which gave a Sharpe near `1e17`, positive and above every threshold,
    the opposite of §8's rule.

31. **REVIEW-3 should-fix 3, decision 18: `BarStore.last_ts` is a reader
    entry point.** The public `last_ts(symbol)` refuses, as `read_range`
    and `last_n` do, when the instrument's directory holds a month file
    the index does not list or a listed file whose hash differs, with the
    same errors. The writer's and `bars fetch`'s own use of the indexed
    last `ts` (decision 5's test, completing an interrupted append) reads
    the index through a private helper that does not refuse, so recovery
    still works. Reason: decision 18 covers "any other reader entry
    point"; a later caller of `last_ts` must not silently miss bars of an
    interrupted append.

32. **REVIEW-3 should-fix 4, DESIGN §6.3 with §13.4: the indicator
    module's text is true of every public function.** `ema` keeps its
    behaviour (seeded at the first value, a value from row 0); the module
    docstring says that `ema` is seeded at the first value and has no
    leading NaN, and that the other windowed functions are NaN until
    their window is full. A test checks, for every public function of
    the module, that a function the module text says is NaN-led returns
    NaN at row 0 for a window above 1, and that `ema` does not. Reason:
    the workers' function list is built from this module's text (§13.4);
    changing `ema` would change the reference strategies' results for no
    gain.

33. **`meta/ROADMAP.md`: mission 4 repairs step S0.3; step S0.4 is
    mission 5.** REVIEW-3 recorded a blocker, so mission 4 closes it and
    REVIEW-3's four should-fix items and adds nothing new
    (`meta/ARCHITECT.md` §3 case 1); step S0.3 is ticked when mission 4's
    review has no blocker. Step S0.4 (the independent calculation, the
    cheating strategy, the gate tests, closing M0) is mission 5: where
    items 28 and 29 say "mission 4" for that work, read "mission 5". No
    gate item moves.

## Added at consultation 7, after REVIEW-4

Items 1 to 33 above are unchanged. Items 34 to 40 below bind mission 5
and every later mission until a newer decisions file says otherwise; the
same rules apply to them (no invariant broken, no gate moved, no
threshold or frozen value changed). Where item 39 or 40 states how a gate
item of DESIGN §18.3 is tested, it says what the item's words mean; it
never asserts less than they say.

34. **REVIEW-4 should-fix 1, decisions 18 and 31: the `BarStore`
    classification covers every public name.** The test that classifies
    `BarStore` enumerates every name of the class (through its MRO,
    `object` excluded) that does not begin with an underscore, whatever
    its kind (method, property, class or static method, plain attribute),
    and fails when one is in neither its list of refusing readers nor its
    list of names that do not read bars. A reader written as a property
    is a reader. Reason: the test is there so that a reader added later
    must be classified; a property escaped it.

35. **REVIEW-4 note on U3, decision 18: a caller that looks at the index
    before it reads refuses as the reader does.** `bars/gaps.py`,
    `rolls.py` (`update_rolls`, `adjusted_as_of`) and any other code that
    consults the bar index for an instrument before reading its bars, and
    finds no entry for it, refuses with decision 18's error (interrupted
    append or revised data point, whichever applies) when the
    instrument's directory holds a month file; it reports "no stored bar"
    only when the directory holds none. Reason: a first append that
    crashed before its index write would otherwise read as "no bars"
    instead of being refused; `bars fetch` runs recovery first, so no
    behaviour of today changes.

36. **REVIEW-3 note carried to S0.4, DESIGN §4.2 (`trusted_from`), §5.6,
    §7.1, §7.3: no bar before `trusted_from` is read for a result.**
    Measuring a roll gap (both the `fetch_contract` bars and the fallback
    `open(u) - close(u-1)`), the adjusted series (`adjusted_as_of`,
    whatever its start argument), the context of the evaluation loop
    (decision 23) and `sigma(u)` read no stored bar whose `ts` is before
    the instrument's `trusted_from`. A contract change between a bar
    before `trusted_from` and the first bar at or after it is not a roll.
    The synthetic sources generate no bar before `trusted_from`, so no
    fixture result changes. The independent calculation applies the same
    rule.

37. **REVIEW-3 note carried to S0.4, decision 24: a roll record must
    match.** An evaluation that meets a contract change at bar `u` uses
    the roll record whose `ts` is `u`'s and whose old and new contracts
    are `contract(u-1)` and `contract(u)`. A record with the right `ts`
    and other contracts is a missing roll record: the same error, exit 1
    from `backtest`.

38. **REVIEW-3 note carried to S0.4, DESIGN §7.3 with I-4: the
    `backtest` plain output says what each cost line is.** The subject's
    cost totals by component (summed over bars, divided by `N` as the
    daily series is, decision 23) are labelled as the subject's, and each
    per-instrument line is labelled as that instrument's undivided sum.
    The figures and the `--json` output do not change. Tests that assert
    the old labels change with it, and the commit body says so.

39. **DESIGN §18.3 G0.1 with decisions 29 and 30: what the independent
    calculation receives, and what "equal, to 1e-12" means.**
    `tests/gates/independent_calc.py` imports nothing from `discotrade`
    (the standard library, `numpy`, `pandas`, `pyarrow` and `tomllib`
    only). It reads the stored bars (the month Parquet files that `bars
    fetch` wrote from the synthetic source into a temporary state
    directory), the roll records, and the track, instrument, calendar and
    spread TOML files under `tests/fixtures/config/` itself. The strategy
    reaches it only as a callable `position(bars, params)` and its
    `PARAMS`, which the gate test obtains with discotrade's loader and
    passes in; the calculation builds every slice of DESIGN §6.2 itself
    (history cap, prices adjusted as of the slice's last bar, `hour` and
    `weekday` in the calendar's time zone, a plain integer index) and
    applies the clipping of decision 22. "Equal, to 1e-12" means
    `|a - b| <= 1e-12 * max(1, |a|, |b|)` for real numbers, both or
    neither not a number, and exact equality for counts, booleans,
    contracts, timestamps and trading dates. The comparison covers, per
    instrument and window bar, `p`, `h`, `gross`, `trade`, `fee`,
    `spread`, `slippage`, `roll`, `cost`, `net_1x` and `net_2x`; per
    subject, the daily series at 1x and 2x and every metric of §8
    (`total_return` at 1x and 2x, `sharpe`, `sharpe_2x`, `max_drawdown`,
    `trades`, `avg_holding_bars`, `breakeven_cost`, `fragile`); and the
    cost totals by component. Reason: item 29 named "the fixture bars",
    and the fixture bars exist only once the synthetic source has written
    them; a calculation that called discotrade to build slices or load the
    strategy's indicators would not be independent of what it checks.

40. **DESIGN §18.3 G0.2 and G0.3, §18.2, I-11: the cheating strategy and
    the gate tests' shape.** The cheating strategy is a strategy text
    under `tests/fixtures/strategies/` that a worker could submit: it
    uses no name or attribute beginning with an underscore and none of
    the names, attributes or imports §12.1 rejects. It keeps module-level
    references to every frame it has received and reads them again later;
    reads the frame's index (its length, its last label) and arithmetic
    on it; tries to read rows past the last one through `iloc`, `loc`,
    `values`, `to_numpy()` and the `base` of those arrays, and the frame's
    `attrs`; and takes a long position whenever any of these shows a
    price later than the slice's last close that is higher. Reaching the
    harness through the interpreter (caller frames, the garbage
    collector, `sys`) is what §12.1 and the container refuse; it is the
    hostile suite's (G2.1), not G0.2's. The G0.2 test runs it through the
    module API (the `backtest` command takes files under `reference/`
    only, decision 21). The G0.3 gap check uses the `synth_week` fixture
    calendar, whose daily break, weekend and closure of 2019-07-03 to
    2019-07-04 are the ones the item names; the dropped bars are those
    the synthetic source dropped, which the test obtains from the
    generator, not from the gap check. Gate tests run the `discotrade`
    command in-process, through the function the console script calls,
    and launch no subprocess; every seed a gate test uses is written in
    the test file. The I-11 note on subprocesses launched by tests
    therefore stays with step S1.1.

## Added at consultation 8, after REVIEW-5

Items 1 to 40 above are unchanged. Items 41 to 46 below bind mission 6
and every later mission until a newer decisions file says otherwise; the
same rules apply to them (no invariant broken, no gate moved, no
threshold or frozen value changed). Item 41 records an answer already
given and applied during mission 5; it changes nothing that mission
built.

41. **D-004, DESIGN §8: `max_drawdown` counts the starting 0 as a peak.**
    `max_drawdown` is the largest fall of the running sum of `d` from its
    running peak, where the running sum starts at 0 before the first day
    and that starting 0 counts as a peak; it is 0 when there is no fall.
    `src/discotrade/metrics.py` already does this; the independent
    calculation was changed to match in de9fc09, with a hand-value case
    for a series whose first day is a loss and whose running sum never
    recovers above 0. Reason: every subject starts flat, so a loss on the
    first day is a drawdown. (Answered by the phone architect on
    2026-10-12 during mission 5 and recorded in `meta/plan.md` under
    "Decision on D-004"; this item is that answer's place in the
    decisions file, REVIEW-5 note on de9fc09.)

42. **REVIEW-5 blocker 1, DESIGN §18.2 with decisions 27 and 39: "the
    `--json` figures equal the module's" means every field.** The G0.1
    test of the `backtest` command's `--json` output compares every key
    the object carries with the module's evaluation of the same strategy,
    window and store: each metric of §8 with `days`, `sharpe_2x` and
    `total_return_2x`; the subject's cost totals; and, per instrument,
    every key of its map (today `bars`, `trades`, `position_min`,
    `position_max`, `fee`, `spread`, `slippage`, `roll`, `cost`, `net_1x`
    and `net_2x`), each computed in the test from the module's per-bar rows
    (not through the command's own helper), and, where the independent
    calculation has the figure (every one of those but `trades`,
    `position_min` and `position_max` per instrument, which the test
    computes from the calculation's rows the same way), with the
    calculation too. The descriptive keys (`strategy`, `params`, `track`,
    `from`, `to`, `cost_model`, `config_hash`) equal the file, its
    `PARAMS`, the track, the window, the string `c1` and the module's
    config hash. The test asserts that the set of keys of the object and
    of each per-instrument map is exactly the set it compares, so that a
    key added later fails the test until it is compared. Under decision
    39 a count is compared exactly and a real number to 1e-12. Reason:
    DESIGN §18.2 makes a gate test that asserts less than it claims a
    blocker; FINAL-REPORT-5 claimed this clause and the test did not hold
    it.

43. **D-005, REVIEW-5 should-fix 1, DESIGN §5.6, §7.3 and §18.3 G0.1: the
    timing of the roll cost and the half-tick floor are each proven on
    their own side, and the timing also through G0.1.** No frozen fixture
    changes. (a) The independent calculation's self-test gains hand cases
    in which the position changes on the roll bar (at least one carried
    position that changes size or sign at the roll, and one flat position
    that opens at the roll), so that a roll cost or a rolled turnover on
    `h(u)` instead of `h(u-1)` fails it; its half-tick floor is already
    seen to fail it (REVIEW-5, U3). (b) The product's unit tests hold a
    roll at which the position changes, with the roll cost on `h(u-1)`
    and the rolled turnover of `breakeven_cost` (decision 25) on `h(u-1)`;
    the floor is already held by `tests/test_costs.py`. (c) G0.1 adds, as
    a fourth comparison beside the three reference strategies, a
    test-only strategy text `tests/fixtures/strategies/roll_probe.py`
    whose position changes at the SYNA roll bar of the G0.1 window; it is
    compared with the independent calculation under decision 39 through
    the module API (the `backtest` command takes files under `reference/`
    only, decision 21), and the test asserts that `h(u-1) != h(u)` at that
    roll bar. The half-tick floor stays unseen by G0.1 on `test_mixed`,
    whose spreads are all at least one tick; a new fixture track for it
    would add a frozen-style fixture for one constant, and (a) and the
    existing unit test already pin it on each side independently. Reason:
    G0.1's words ("every cost component equal") hold on the fixture data
    either way, but a comparison that cannot see a named mistake proves
    less than it seems to; the probe makes the roll timing visible
    without changing any existing fixture.

44. **D-006, DESIGN §6.2, §12.1, §12.4 with I-2: each instrument's
    evaluation gets a freshly loaded strategy; built in step S2.1.**
    When a strategy text is evaluated on several instruments, each
    instrument's evaluation runs on a strategy loaded afresh from the
    text, in a namespace of its own, so that nothing a text keeps from
    one instrument's frames is visible while it evaluates another. Step
    S2.1 builds it with the sandbox's runner, through which every
    worker's text will be evaluated, and drives the cheating strategy of
    G0.2 through the multi-instrument path in its tests. Until then the
    `backtest` command runs only trusted files under `reference/`
    (decision 21), which keep no frames, so no result of today changes
    and mission 6 does not touch it. Reason: a text that keeps frames
    could otherwise read an earlier instrument's later bars; no
    untrusted text can reach `backtest` before M2.

45. **REVIEW-5 note (hands), DESIGN §18.2: `tests/test_gate_script.py`
    does not turn `./scripts/check` red under load.** Its tests that run
    `./scripts/gate` as a subprocess assert what they assert today, on
    the cheapest item that shows it (an item whose tests take seconds,
    such as G0.4, or a milestone with no gate test), never on an item
    that replays or fetches for minutes, and any subprocess timeout they
    keep is at least 1200 seconds. Reason: a 600-second timeout on a
    three-minute item failed one reviewer's check when five checks shared
    four CPUs; what the test proves (the script's lines, its exit status,
    one-item runs) does not depend on which item runs.

46. **`meta/ROADMAP.md`: mission 6 repairs step S0.4.** REVIEW-5 recorded
    a blocker, so mission 6 closes it and REVIEW-5's should-fix item,
    records findings D-004 to D-006 as answered here, and adds nothing
    new (`meta/ARCHITECT.md` §3 case 1). Step S0.4 still closes M0, so
    mission 6 ends with the gate run; step S0.4 is ticked, and M0 marked
    met, when mission 6's review has no blocker and records the gate
    PASS. No gate item moves.

## Added at consultation 9, after REVIEW-6

Items 1 to 46 above are unchanged. REVIEW-6 recorded no blocker and the
gate M0 PASS at e239dee, so step S0.4 is ticked and milestone M0 is
marked met (item 46). Items 47 to 57 below bind mission 7 (step S1.1)
and every later mission until a newer decisions file says otherwise; the
same rules apply to them (no invariant broken, no gate moved, no
threshold or frozen value changed). Where an item leaves a part of a
DESIGN section to a later step, that step is named, and the part stays
the roadmap's for that step.

47. **REVIEW-3 note (I-11), decision 20, `meta/BACKLOG.md` (step S1.1):
    the socket backstop holds outside function-scoped tests too.** From
    the start of the pytest session, every attempt to open a network
    connection fails as decision 20 says, in module- and session-scoped
    fixtures as well as in tests, and through `_socket` used directly as
    well as through `socket`; a test marked `network` or `live` is left
    alone while it runs. A subprocess launched by a test, or by product
    code under test, is one of: `git` on local paths only, with
    `GIT_ALLOW_PROTOCOL=file` in its environment so that git refuses
    every other transport; or a Python program of this repository (the
    `discotrade` command, `./scripts/gate`, a scratch pytest run, or a
    `python -c` snippet the test writes) that opens no connection, as the
    tests of today's subprocess calls already show (`test_cli.py`,
    `test_config_check.py`, `test_costs.py`, `test_vendor.py`,
    `test_gate_script.py`). A test that finds the files under `tests/`
    and `src/` whose text contains `subprocess` or `os.system` fails on a
    file that is not in its list, so that a new subprocess call is
    classified when it is added. Reason: mission 7 adds `git`
    subprocesses (the state repository, item 50), and the note was
    carried to this step.

48. **DESIGN §9.1, §9.2, §10.3 with I-7 and decision 21: which subjects
    step S1.1 journals, and how their source runs before the sandbox.**
    The journal is written for the subjects the state holds. In step S1.1
    those are the approaches under `approaches/<id>/`, written by a
    harness function of `state.py` (source, fixed parameters, cell, model
    id, model version, cutoff date, description, profile version, and the
    admission date) that tests call in place of admission, and that step
    S1.2's lifecycle calls when it admits a candidate; until S1.2 builds
    the lifecycle, every approach in the state is journaled from its first
    day on. The controls of §10.1 are step S1.2's and go through the same
    journaling function with their `kind`. Until step S2.2 moves approach
    execution behind the sandbox, the day loop runs an approach's frozen
    source in-process through the decision-21 loader, and only when its
    sha256 equals that of a file under the repository's `reference/` or
    `tests/fixtures/` (the rule §12.4 gives the subprocess backend); any
    other source fails the day, naming the approach, and nothing of the
    day is moved into place. The approach id is `a` followed by the first
    12 hex digits of the sha256 of the UTF-8 source text, a newline, and
    the canonical JSON (keys sorted, no whitespace) of the fixed
    parameters. `meta.json` holds the fields §9.1 lists; the cost model
    version and config hash are decision 26's.

49. **DESIGN §7, §9.2 with decisions 23 to 25: a journal row, and the
    continuous record.** A day's rows for an approach are, per
    instrument, its bars whose trading date by its own calendar is `D`
    and whose `ts` is not before `trusted_from` (decision 23). They are
    computed by the same evaluation loop, executor and cost model as
    `backtest` (one implementation of §7, decisions 24, 25, 36, 37), with
    the slice of §6.2 ending at each bar. Per instrument, the approach's
    first row is the first bar of the first trading day of that
    instrument's calendar after the admission date, with `prev_position`
    0 and `position` 0; every later row's `position` is the previous
    row's `target_next` on that instrument, whichever day that row
    belongs to, and `u-1` is the previous stored bar (decision 24). The
    columns are §9.2's: `date` (the trading date `D`), `ts`, `subject`
    (the approach id), `kind` (`approach`), `instrument`,
    `prev_position` (`h(u-1)`), `position` (`h(u)`), `target_next`
    (`p(u)`), `fill_price` (`Or(u)`), `trade`, `roll` (true when a roll
    happens at `u`), `fee`, `spread`, `slippage`, `roll_cost` (decision
    25's components at 1x), `gross`, `net_1x`, `net_2x`. The key columns
    of the content hash are `subject`, `instrument` and `ts`. A test
    shows that an approach's journal rows over consecutive days equal,
    field for field under decision 39's rule, the module's evaluation of
    the same strategy over the window from its first journaled day to the
    last, whose first bar is flat by §7.1. A day with no subject writes a
    journal file with no row and its index line, so every processed day
    has both.

50. **DESIGN §9.1, §16.2 with I-5, I-6, I-12, I-14: the state directory
    and the atomic day in step S1.1.** `discotrade init-state` creates the
    state directory (refused inside a code repository, decision 7) as a
    Git repository with a `.gitignore` that ignores the bar Parquet files,
    the staging directory and the lock; run on an existing state
    directory it changes nothing and exits 0; on a non-empty directory
    that is not one it exits 1. `run-day` refuses a directory that
    `init-state` did not create. A run takes a lock in the state
    directory (created exclusively; a held lock exits 1 naming it) and
    releases it at the end, success or failure. The journal file, its
    index line and the paper records of the day are written to a staging
    directory and moved into place only when steps 1 and 2 have
    succeeded; then the state repository is committed with the message
    `run <track> <date>`, the author `discotrade <discotrade@invalid>` and
    the author and committer dates of the injected clock, with
    `GIT_ALLOW_PROTOCOL=file` in git's environment. A run that moves
    nothing makes no commit. In step S1.1 the bars, rolls and
    `gaps.jsonl` of step 1 are written as `bars fetch` writes them (each
    append atomic, decisions 4 and 5), not staged. Step S4.2 builds the
    rest of §16.2 and §16.1: staging of step 1's writes, the retry from a
    clean staging directory, `run_failed`, the push to a remote, and the
    catch-up of missed days with `day_caught_up`.

51. **DESIGN §16.1 with decisions 3 and 19: which day `run-day` processes
    in step S1.1.** `run-day` processes one trading day `D`: by default
    decision 19's `D` at the `--as-of` instant, or the date `--day`
    names. The track's trading days are the union of its instruments'
    trading dates (decision 23). When the journal holds a day and a
    trading day of the track between that day and `D` has no journal
    file, `run-day` exits 1 naming the first such day and writes nothing
    (the catch-up is step S4.2's). A `D` on or before the last journaled
    day is a re-run: it recomputes the rows of `D` from the state as it
    stood before `D` (the previous day's last `target_next` per approach
    and instrument) and compares content hashes as §9.2 says; equal
    writes nothing (I-6), unequal leaves the file untouched and raises
    `journal_mismatch`.

52. **DESIGN §15.2, decision 16: the health log.** `state.py` appends
    health events to `health/<track>.jsonl`, one `HealthEvent.to_json()`
    per line, atomically as decision 4 appends `gaps.jsonl`, at once and
    never through the staging directory (§16.2). The day appends every
    event its steps return: `store_recovered` and estimated-roll-gap
    notices (decision 16), `data_gaps` when the gap fraction of W or of T
    for `D` (decision 2) exceeds `gaps.max_fraction`, `revised_data` when
    a reader refuses a revised data point (the day then fails),
    `journal_mismatch`. An event whose JSON line is already in the log is
    not appended again, so a re-run of a day writes nothing new (I-6);
    `bars fetch` and `bars gaps` keep printing their notices as today.

53. **DESIGN §9.3 with §11.3: paper records in step S1.1.**
    `paper/<track>/daily.parquet` is rebuilt from the journal after each
    day: one row per subject and trading day from its first journaled day,
    with `gross`, `net_1x`, `net_2x` (decision 23's daily mean over the
    subject's instruments) and `trades` (rows with `trade > 1e-9`, the §8
    floor). The `clean` flag needs the model cutoffs of §11.3 and is added
    by step S1.2; the file is derived, so adding the column changes no
    record. Rebuilding it from the journal gives the same content hash
    (key columns `subject`, `date`).

54. **DESIGN §9.4: `journal recompute` in step S1.1.** `discotrade journal
    recompute --all` recomputes every journaled (day, subject) pair from
    the stored bars and the frozen source, each subject evaluated once
    from its first journaled day to the last, and compares each day's rows
    exactly (equal content hashes of the pair's rows, decision 49's keys).
    Without `--all` it recomputes `journal.recompute_sample` pairs of the
    days before `D`, drawn by `numpy.random.default_rng` seeded with `D`
    written as the integer `YYYYMMDD` (fewer when fewer exist), in the
    same way. Each mismatch prints the pair and returns a
    `journal_mismatch` event naming it, which the command appends to the
    health log; the command exits 1 on any mismatch and writes nothing
    else. Running it on the first trading day of each ISO week, as step 6
    of §16.1, is step S4.2's.

55. **DESIGN §3, I-12: time in step S1.1.** `run-day`, `init-state` and
    `journal recompute` read time only through the injected clock
    (`--as-of`); no state file, commit date or event carries the wall
    clock. A test runs `run-day` twice for the same `--as-of` in two fresh
    state directories and finds equal journal and paper content hashes and
    equal health logs.

56. **REVIEW-6 should-fix 1: FINAL-REPORT-6's sentence on the roll
    probe.** No test changes. FINAL-REPORT-7 states, in a correction of
    FINAL-REPORT-6, that `test_probe_changes_position_at_the_syna_roll`
    asserts, at every SYNA roll bar of the window, that a roll exists and
    that `h(u-1) != h(u)`, `h(u-1) != 0`, `|h(u-1)| != |h(u)|` and roll and
    trade are positive in both sets of rows; and that the bar
    2019-06-14T00:00Z and the values `h(u-1) = 1.0`, `h(u) = -0.5` were
    observed by the reviewer, not asserted. Reason: decision 43 (c)
    requires only `h(u-1) != h(u)`, which the test asserts; only the
    report overstated it.

57. **`meta/ROADMAP.md`: step S0.4 ticked, M0 met, mission 7 is step
    S1.1.** REVIEW-6 has no blocker and records `gate M0: PASS` at
    e239dee, which this consultation found on `origin/main`
    (`meta/ARCHITECT.md` §3 case 3). Mission 7 builds step S1.1 as the
    roadmap writes it, cut as items 47 to 55 say; it does not close a
    milestone and has no gate unit. No gate item moves.

## Added at consultation 10, after REVIEW-7

Items 1 to 57 above are unchanged. REVIEW-7 recorded no blocker and the
mission closed no milestone, so step S1.1 is ticked (item 65). Items 58
to 65 below bind mission 8 (step S1.2) and every later mission until a
newer decisions file says otherwise; the same rules apply to them (no
invariant broken, no gate moved, no threshold or frozen value changed).
Where an item leaves a part of a DESIGN section to a later step, that
step is named, and the part stays the roadmap's for that step.

58. **REVIEW-7 should-fix 1 and 2, decisions 47 and 54: the remaining
    network paths, and a recompute that reads no stored position.**
    (a) The socket backstop of decision 47 also refuses, with the same
    error and in the same scopes (session start, every fixture scope,
    through `socket` and through `_socket`): `sendmsg` with an address
    on a socket that is not `AF_UNIX`, and the name lookups
    `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr` and
    `getnameinfo` (beside `getaddrinfo`, already refused). An `AF_UNIX`
    socket stays usable, and a test marked `network` or `live` is left
    alone, as today. What the backstop still cannot see (`SocketType`
    used directly, a binding taken before the session starts, child
    processes) stays in the report's NOT PROVEN. (b) A test of `journal
    recompute --all`, on a journal of at least three days, changes for
    one approach and one instrument the stored `target_next` of its last
    row of day `D1` to a value that moves the next position, then
    replaces that approach's rows of the next journaled day `D2` (and
    `D2`'s index line) with the rows the journaling function computes
    for `D2` when it starts from the changed stored `D1`, so that the
    stored journal is what a journal chained through the changed value
    would hold. It shows that the command reports both `(D1, subject)`
    and `(D2, subject)` as mismatches and exits 1. A recompute that
    started `D2` from the stored `target_next` of `D1` would find `D2`
    equal, so the test separates decision 54's whole-span recompute from
    one chained through stored values; that wrong change is made, seen to
    fail the test, reverted and named in the commit body. Reason:
    decision 47 says every
    attempt to open a network connection fails, and decision 54 says each
    subject is evaluated once from its first journaled day; REVIEW-7
    found the first not held for these paths and the second not proven.

59. **DESIGN §11.1: the rank-persistence statistic, as a function, in
    step S1.2.** `stats.py` computes, for a block index `k >= 1` and a
    population of subjects, one row: `block` (`k`), the calendar dates of
    block `k` and of block `k - 1`, the sorted subject ids of the
    population, its size, and the statistic. Block `k` is the
    `block_days` calendar days from `epoch + k * block_days`. A subject
    belongs to the population when it has a paper row on every trading
    day of both blocks, the trading days being the union of the trading
    dates, by their own calendars, of the subject's own instruments (the
    track's basket for an approach or a random slot, its one instrument
    for a buy-and-hold control), and that union holds at least one day in
    each block. The statistic is the Spearman correlation of the
    subjects' summed paper `net_1x` in block `k - 1` and in block `k`:
    the Pearson correlation of their ranks, ties taking the average rank.
    It is missing (`null`) when the population has fewer than
    `alerts.rank_min_population` members or either rank series has zero
    deviation. Writing the row to `stats/<track>/rank_persistence.jsonl`
    when a block completes, in the day loop, is step S1.3's. Reason:
    §11.1 leaves the tie rule, the zero-deviation case and whose trading
    days count unsaid; a buy-and-hold control on a weekly calendar has
    no row on an always-open instrument's weekend.

60. **DESIGN §11.2 and §11.4: deflated scores and tightening.** The
    normal quantile `z` is `statistics.NormalDist().inv_cdf` from the
    standard library (no dependency). `g` is the Euler-Mascheroni
    constant `0.5772156649015329` and `e` is `math.e`, constants of the
    formula that live in the module, not in `config/thresholds.toml`.
    For a set of days, `mu_c` and `sd_c` are the mean and the sample
    standard deviation (ddof 1) of the paper net Sharpes at 1x (DESIGN §8,
    decision 30) over those days of the random control slots that have
    a paper row on each of them, a slot whose Sharpe is not a number left
    out. With fewer than two such slots, `mu_c`, `sd_c`, `E(N)`, the
    excess and the threshold of §11.4 are not numbers. `N` is the row
    count of `ledger/<track>/trials.jsonl`, and `E(N)` uses `max(N, 2)`;
    `p(N)` uses `max(N, 1)` as §11.4 writes. The excess is `S - E(N)`; a
    Sharpe `S` that is not a number gives an excess that is not a
    number. Tests compare with values computed in the test itself, the
    quantile found there by bisection on `math.erf` to `1e-15`, not
    through `stats.py`, and assert the published quantiles `z(0.95) =
    1.6448536269514722`, `z(0.975) = 1.959963984540054` and `z(0.99) =
    2.3263478740408408` to `1e-12`. Reason: §11.2 and §11.4 name `z`
    without a source, and the project adds no dependency for it.

61. **DESIGN §9.3 and §11.3 with decision 53: the `clean` flag in step
    S1.2.** `paper/<track>/daily.parquet` gains the boolean column
    `clean`: for an approach, true when the paper row's trading date is
    after the `cutoff` date recorded in its `meta.json` (the model's
    cutoff date as used, frozen at admission, §9.1); for a control,
    always true. `stats.py` gives a subject's clean and exposed day
    counts from the paper records. `config/models.toml` and the rule that
    turns a stated cutoff month into a date (R-14) are step S3.2's, which
    builds the pool and writes `cutoff` at admission; until then a test
    writes `cutoff` with the approach. The paper file is derived, so the
    added column changes no record; tests of `paper.py` that assert its
    exact columns change with it, and the commit body says so.

62. **DESIGN §10.2 with I-5, I-6 and decision 52: the three ledgers.**
    `ledger.py` appends JSON lines (keys sorted, one object per line) to
    `ledger/<track>/trials.jsonl`, `calls.jsonl` and `lifecycle.jsonl`,
    each append atomic as decision 4 appends `gaps.jsonl`, every earlier
    line byte-identical, a line already present not appended again, a
    torn last line refused. Inside `run-day` they are written to the
    staging directory with the day's journal and moved with it (§16.2).
    A trial row holds every field §10.2 lists, under the keys `date`,
    `id`, `cell`, `model_id`, `model_version`, `cutoff`, `code_sha256`,
    `profile_version`, `cost_model`, `config_hash`, `grid` (the grid and
    its results on W), `params`, `metrics_w`, `metrics_t`, `admitted`,
    `reason` and `displaced`; a value the candidate does not carry (the
    grid and the W metrics of a scripted candidate) is `null`, never
    invented. A lifecycle row holds `date`, `id`, `from`, `to` and
    `reason`. A call row holds the fields §10.2 lists; `ledger.py`
    provides its writer, and its first caller is step S3.2. A trial not
    admitted is written under `trials/<id>/` (`strategy.py`, `meta.json`,
    §9.1) by the writer of decision 48; an admitted one under
    `approaches/<id>/`.

63. **DESIGN §10.3 with decisions 22 and 48: the lifecycle in step
    S1.2.** The state of an approach is the `to` of its last row in
    `lifecycle.jsonl`; an approach under `approaches/` with no row is
    `live` from its admission date (so step S1.1's writer and its tests
    keep their meaning). `run-day` runs steps 1 to 4 of §10.3 after the
    day's journaling, in that order; within a step, approaches are taken
    in ascending id order, and each step and each approach sees the
    states the earlier ones left; every change is one lifecycle row dated
    `D` and takes effect for journaling from the next trading day.
    (1) An approach whose evaluation on `D` breaks the contract of
    decision 22 (raises, or returns a value that is not finite and in
    range) is retired with reason `failure: <the error text>`, and its
    rows of `D` are not journaled; the day goes on. A source that is not
    a repository file (decision 48) still fails the whole day: that is a
    harness refusal, not a strategy failure. (2) A live approach with at
    least `dormant_window_days` paper rows whose net Sharpe at 1x over
    its last `dormant_window_days` paper rows is negative goes dormant
    (reason `dormant`); a Sharpe that is not a number is not negative.
    (3) A dormant approach whose dormancy has lasted at least
    `revival_min_dormant_days` trading days of the track (counted after
    the date of its row to `dormant`, up to and including `D`) and whose
    net Sharpe at 1x over its last `dormant_window_days` paper rows is
    positive returns to live (reason `returned`) when its cell has fewer
    than `cell_slots` live approaches, or when that Sharpe is above the
    weakest live approach's over the same days, which goes dormant
    (reason `displaced`). (4) An approach dormant for at least
    `retire_dormant_days` calendar days (`D` minus the date of its row to
    `dormant`) is retired (reason `retired_dormant`). The weakest live
    approach of a cell is the one with the lowest net Sharpe at 1x over
    the days compared; a Sharpe that is not a number counts as the
    lowest, and ties go to the lowest id. Admission is a function of
    `lifecycle.py` that takes a candidate (source, parameters, cell,
    model id, model version, cutoff, description, profile version, the
    grid and W metrics when it has them, and its §8 metrics on T with T's
    trading days) and the day `D`, and applies §10.3's rule after steps 1
    to 4: refused with reason `not_positive` when the score (net Sharpe
    at 1x on T) is not positive, else `too_few_trades` below
    `admission.min_trades_t`, else admitted with `free_slot` when the
    cell has fewer than `cell_slots` live approaches, else admitted with
    `displaced` when the score is above the weakest live approach's net
    Sharpe at 1x over T's days in its paper records (that approach goes
    dormant), else refused with `not_better_than_weakest`. It writes the
    trial row and, when admitted, the approach (admission date `D`) and
    its `candidate` to `live` row (reason `admitted`). Scoring a
    candidate on T is step S3.2's (§16.1 step 5); feeding scripted
    candidates into the day loop for G1.3 is step S1.3's. Dormant
    approaches are journaled; retired ones are not journaled again and
    stay in the ledgers.

64. **DESIGN §10.1 with decisions 23, 25, 49 and 54: the controls.**
    The controls are journaled from the first day `run-day` journals on
    a state, every day, through the same evaluation loop, executor and
    cost model as approaches (one implementation of §7: a control
    supplies its targets `p(t)` per bar in place of a strategy call), with
    decision 49's columns and continuity, `kind` `control_bh` or
    `control_random`, and each instrument's first row flat. `bh:<symbol>`
    has the target 1 at every bar of its one instrument. The random pool
    is `controls.random_pool` slots `rc:0` to `rc:<pool - 1>`, each on
    every instrument of the track. A draw is made on the first day the
    controls are journaled and on the first trading day of the track in
    each later calendar month; its seed is the integer `YYYYMM` of that
    day's month. Its `H` and `q` per slot, in slot order, come from
    `numpy.random.default_rng(seed)`: when at least
    `controls.match_min_live` approaches are live at the start of the
    draw's day and each has at least `controls.match_window_days` paper
    rows before that day, each slot takes one of their measured pairs
    chosen uniformly (`integers`), a pair being the approach's
    `avg_holding_bars` (decision 25, from its journal `position` over
    those days' rows) and its trades per bar (rows with `trade > 1e-9`
    over rows) over its last `match_window_days` paper days, a pair whose
    `H` is not a number left out; otherwise `H = exp(uniform(ln lo, ln
    hi))` with `lo` the smallest and `hi` the largest bound of the
    track's horizons, and `q = 1 / H`. Each per-bar random number is the
    first 8 bytes of the sha256 of `<seed>|<slot>|<instrument>|<bar ts in
    ns>|<purpose>`, read big-endian, over `2**64`, the purposes being
    `enter`, `side` and `exit`. On each instrument, from its first bar
    whose trading date is on or after the draw's day, the machine starts
    flat; at each bar, flat, it enters when `enter < q`, long when `side
    < 0.5` or when the instrument does not allow shorting, short
    otherwise; in a position it leaves when `exit < 1 / H`; the target
    `p(t)` is the state after the bar. The return series and the
    position carry across a redraw (the first target of a new draw may
    trade against the old position). Each draw appends one line to
    `controls/<track>/pools.jsonl` (`month`, `day`, `seed`, per slot `H`
    and `q`, and the measured pairs used with their approach ids), staged
    with the day; a draw already recorded is read back, never appended
    again. `journal recompute` recomputes control subjects from
    `pools.jsonl` and the stored bars. Tests of step S1.1 that assert a
    journal or paper file holds approaches only (its subjects, its row
    count, an empty day file) change with this item, and the commit body
    names each one.

65. **`meta/ROADMAP.md`: step S1.1 ticked; step S1.2 split into S1.2
    and S1.3.** REVIEW-7 has no blocker and the mission closed no
    milestone (`meta/ARCHITECT.md` §3 case 2), so step S1.1 is ticked.
    Step S1.2 as written (controls, three ledgers, lifecycle, table,
    portfolio, rank persistence, deflation, clean and exposed, tightening,
    replay harness, gate tests) does not fit seven units. Mission 8
    builds step S1.2: the controls, the ledgers, the lifecycle, the
    `clean` flag and the statistics of §11 as functions, with REVIEW-7's
    two should-fix items. Mission 9 builds step S1.3: the table, the
    combined portfolio, rank persistence in the day loop, the replay
    harness (controls only, and the scripted candidates G1.3 feeds), the
    two performance items `meta/BACKLOG.md` sets for "the latest" step
    before a one-year replay, and the gate tests of G1.1 to G1.4; it
    closes M1. No gate item moves.

## Added at consultation 11, after REVIEW-8

Items 1 to 65 above are unchanged. REVIEW-8 recorded no blocker and the
mission closed no milestone, so step S1.2 is ticked (item 75). Items 66 to
75 below bind mission 9 (step S1.3) and every later mission until a newer
decisions file says otherwise; the same rules apply to them (no invariant
broken, no gate moved, no threshold or frozen value changed). Where an
item states how a gate item of DESIGN §18.3 is tested, it says what the
item's words mean; it never asserts less than they say.

66. **REVIEW-8 should-fix 1, decision 63 (3): revival counts trading days,
    shown by a test.** A test of step 3 of §10.3 uses a track whose
    calendars have a day that is not a trading day inside the waiting span
    (the fixture track `test_synth`, whose instruments are all on
    `synth_week`, has weekends; or a configuration copied under the test's
    temporary directory, said so), at the production value
    `revival_min_dormant_days = 5`: the approach stays dormant on the day
    on which five or more calendar days, but fewer than five trading days
    of the track, have passed since its row to `dormant`, and returns on
    the fifth trading day. Counting calendar days (`(D - since).days`) is
    the wrong change made, seen to fail the test, reverted and named in
    the commit body. Reason: `test_mixed` holds an always-open instrument,
    so every calendar day was a trading day of its track and the two
    counts could not be told apart.

67. **REVIEW-8 should-fix 2, decisions 47 and 58 with I-11: no lookup in
    the scratch session can reach a resolver.** In the scratch pytest
    session of `tests/test_offline.py`, the `network`-marked test calls
    for real only lookups that Python or the C library answer without a
    resolver (a numeric address with `AI_NUMERICHOST`, `getnameinfo`
    with `NI_NUMERICHOST | NI_NUMERICSERV`, `gethostbyname` and
    `gethostbyname_ex` of a dotted numeric address), and its comment says
    exactly that, with the reason for each. `gethostbyaddr`, a reverse
    lookup that reads the hosts file or asks DNS, is not called there: the
    test shows it is left alone in a `network`-marked test by identity
    (the attribute of `socket` and `_socket` is the original function
    while the test runs), and refused again in the following unmarked
    test as today. Every other assertion of the file keeps what it
    asserts. Reason: `gethostbyaddr("127.0.0.1")` is answered without a
    query only on a host whose hosts file lists that address with
    `files` first; on another host the scratch session could send a PTR
    query or change its outcome.

68. **REVIEW-8 notes on U3 and U4: two readings confirmed.** (a) Decision
    64's matched draw takes place when at least `controls.match_min_live`
    of the approaches live at the start of the draw's day each have at
    least `controls.match_window_days` paper rows before that day, and
    takes its pairs from those approaches only; a live approach with
    fewer rows neither blocks the draw nor contributes a pair. This is
    the reading `controls.measured_pairs` implements. (b) Under decision
    63, an approach that returns earlier on `D` (step 3) may be displaced
    later on the same `D` by another approach's return or by the day's
    admission; both lifecycle rows dated `D` stand, in the order they
    were taken, and the date of its last row to `dormant` is the one any
    later count uses. Mission 9 adds a test of (b) through the lifecycle
    functions, and changes no code for either. Reason: REVIEW-8 found the
    code consistent with both readings and the design silent; recording
    them makes the reviewer's question an answer.

69. **DESIGN §10.5 with §9.3, decisions 53, 61 and 63: the combined
    portfolio in the paper records.** `paper/<track>/daily.parquet` gains
    rows for two subjects, `portfolio` and `portfolio_clean`. The members
    of `D` are the approaches whose state at the start of `D` (from the
    lifecycle rows dated before `D`, decision 63) is `live` and that have
    a paper row on `D`; `portfolio_clean`'s members are those of them
    whose row on `D` is `clean`. Each series' `gross`, `net_1x` and
    `net_2x` on `D` are the equal-weight means of its members' values,
    and `trades` the sum of its members' trades. `portfolio` has a row on
    every trading day of the track (decision 51) from the first journaled
    day, with 0 for `gross`, `net_1x`, `net_2x` and `trades` on a day with
    no member; `portfolio_clean` has a row only on a day with at least one
    member. `clean` is true on every `portfolio_clean` row, and on a
    `portfolio` row true exactly when every member's row is clean (true
    with no member). The rows are derived like every paper row: rebuilding
    the file from the journal, the lifecycle ledger and the approaches'
    `meta.json` gives the same content hash. The rank-persistence
    population, the control moments of decision 60, the matched draw of
    decision 64 and the paper-record Sharpes of decision 63 never take a
    portfolio row. Tests that assert the paper file's subjects equal the
    journal's change with this item, and the commit body names each one.

70. **DESIGN §11.1 and §16.1 step 6 with decisions 59 and 62: rank
    persistence in the day loop.** On the run of a new day `D`, after the
    lifecycle steps and the day's admission, for every block `k >= 1`
    whose last calendar day is on or before `D`, whose block `k - 1`
    starts on or after the state's first journaled day, and which has no
    row yet, in ascending `k`, decision 59's row is appended to
    `stats/<track>/rank_persistence.jsonl` under decision 62's append
    rules (sorted keys, atomic, staged with the day, a row already present
    not appended). The population is the approaches whose state after
    `D`'s steps is `live` or `dormant`, under decision 59's rule. A
    re-run of a finished day appends nothing.

71. **DESIGN §10.4 with §8, §11.2, decisions 25, 30, 41, 60 and 62: the
    table.** On the run of a new day `D`, after rank persistence, the
    day writes `table/<track>/table.json` and `table.md` to the staging
    directory with the day; a re-run of a finished day writes nothing.
    `table.json` is one JSON object (keys sorted, a float that is not
    finite written as `null`) holding the track, `D`, the trial count `N`,
    and a list of rows in this order: the live approaches (state after
    `D`'s steps) grouped by cell, cells in ascending string order and ids
    ascending within a cell; then the dormant approaches by ascending id;
    then the controls, `bh:<symbol>` in the track's instrument order and
    then `rc:0` to the last slot in slot order; then `portfolio` and
    `portfolio_clean`. Retired approaches are not listed. Each row holds
    `section` (`live`, `dormant`, `control` or `portfolio`), `subject`,
    `cell`, `description`, `model_id`, `model_version`, `admitted` (the
    admission date), `admission_score` (the `sharpe` of its trial row's
    `metrics_t`), the paper record over all its paper days (`days`,
    `clean_days`, `sharpe`, `sharpe_2x`, `trades`, `max_drawdown`, by the
    §8 formulas of `metrics.py` with decisions 30 and 41), `breakeven_cost`
    (decision 25, from its journal rows of its paper days), the deflated
    figures over its paper days (`S`, `E_N`, `excess`, decision 60), and
    `state_history` (its lifecycle rows, `date`, `from`, `to`, `reason`,
    in ledger order). A field that does not apply to a row is `null`: the
    approach fields and the deflated figures for controls and the
    portfolio series, and `breakeven_cost` for the portfolio series.
    `table.md` renders the same rows, in the same order, as Markdown
    tables, one per section, with every real number printed to four
    decimals and `null` printed as `-`; it carries no wall-clock time.

72. **DESIGN §16.4 with decisions 19, 51 and 55: the replay command in
    step S1.3.** `discotrade replay --from A --to B` (with the common
    options `--state`, `--track` and `--config`) runs, for each trading
    day `D` of the track from `A` to `B` in ascending order, the same day
    function as `run-day` for `D`, with the injected clock set to the
    instant at which the last expected bar of `D` among the track's
    instruments closes. It prints one line per day, stops at the first
    day that fails, exits 1 naming it (the days before it stay
    committed), and exits 0 when every day succeeds; `A` after `B` is a
    usage error (exit 2). A day already journaled is a re-run and writes
    nothing (I-6); a day after a gap is refused as `run-day` refuses it
    (decision 51). The provider, coordinator, issue sink and sandbox
    options of §16.4 are added by the steps that build those roles (S2.2,
    S3.2, S4.2); until then the command takes the source from the track's
    records and refuses an unknown option. The gate configuration of
    DESIGN §18.2 is a configuration directory built under the test's
    temporary directory from `tests/fixtures/config/`, with
    `tests/fixtures/config/thresholds_gate.toml` copied in, unchanged, as
    its thresholds file. Two replays of the same span on the same
    configuration and options, each into a fresh state directory, give
    identical bytes for every file outside `.git/` and the same tree at
    `HEAD`.

73. **DESIGN §10.3, §16.1 step 5 and §18.3 G1.3 with decisions 48 and 63:
    scripted candidates.** `replay` takes `--candidates <file>`, a JSON
    lines file whose lines each hold `day`, `source` (a file under the
    repository's `reference/` or `tests/fixtures/`, decision 48),
    `params`, `cell`, `model_id`, `model_version`, `cutoff`,
    `description`, `profile_version` and `metrics_t` (the §8 metrics on T,
    `sharpe` and `trades` included). On day `D`, after lifecycle steps 1
    to 4, the day calls decision 63's admission function with the
    candidate dated `D`, if any, with T's trading days those §4.1 gives
    for `D`; its trial row, its approach and its lifecycle row are staged
    with the day. A file with two candidates for one day, or a line
    missing a key, is refused before any day runs (exit 2). The candidate
    carries no grid and no W metrics, so those trial fields are `null`.
    `run-day` takes no candidate. Scoring a real candidate on T stays step
    S3.2's.

74. **DESIGN §18.2 and §18.3 (M1): the gate tests.** Each item's tests are
    `tests/gates/test_g1_<n>_*.py` (the files `./scripts/gate` runs), and
    each item builds its own replays, since `./scripts/gate` runs each
    item in its own pytest process. Every replay runs on the gate
    configuration (item 72) and the fixture track `test_synth`, in-process
    through the function the console script calls, with every seed and
    date written in the test file. (G1.1) A controls-only replay from
    `2019-06-03` (the track's `epoch`) to `2020-06-01`, one year: over the
    `controls.random_pool` slots, with each slot's sums taken over its
    paper rows of the year, the mean summed `gross` is within four
    standard errors (the sample standard deviation over the slots divided
    by the square root of their number) of 0; the mean summed cost
    (`gross - net_1x`) is positive; the mean summed `net_1x` is within
    four standard errors (of the slots' summed `net_1x`, the same way) of
    minus the mean summed cost; decision 59's statistic, computed for each block completed in
    the year with the random slots as the population, has a mean over its
    non-missing values within four standard errors of 0, with at least 40
    non-missing values; and `stats/test_synth/rank_persistence.jsonl`
    holds one row per completed block. (G1.2) The scenario of G1.3,
    replayed from `2019-06-03` over at least 60 calendar days (so the
    state holds approaches, controls, a monthly redraw, completed blocks
    and lifecycle rows): `journal recompute --all` exits 0 and reports
    every (day, subject) pair of the journal equal, their count asserted;
    running the last day again (through `run-day` or `replay`) leaves
    every file's bytes and `HEAD` unchanged; and a second replay into a
    fresh state directory gives what item 72's last sentence says. (G1.3)
    A replay of a scripted candidates file under
    `tests/fixtures/scenarios/` long enough for the dormant limit
    (`retire_dormant_days`, 365 calendar days, unchanged in the gate
    configuration) shows, as lifecycle and trial rows the test lists in
    full and in order: admission into a free slot, admission displacing
    the weakest (which goes dormant, `displaced`), refusal for too few
    trades, refusal for a score that is not positive, dormancy (step 2),
    return (step 3), retirement on failure and retirement after the
    dormant limit; one trial row per candidate and one lifecycle row per
    event; the ledgers never rewritten (the test replays in segments and
    finds each ledger's earlier bytes a prefix of its later bytes); the
    two portfolio series on every day equal to the test's own count from
    the paper rows and the lifecycle rows; and `table.json` on at least
    two days (one mid-scenario, the last) equal, row for row and field
    for field under decision 39's rule, to the test's own count, the §8
    figures computed in the test with decisions 30 and 41 written there.
    A scenario on fixed seeds is deterministic; the test asserts the
    transitions the scenario is built to produce, and the fixture
    strategies under `tests/fixtures/strategies/` that it needs are new
    files (for example an always-flat strategy, whose paper Sharpe is not
    a number, so that once displaced it never returns and is retired at
    the dormant limit; the existing `breaks_thursday_noon.py` for the
    failure). (G1.4) For fixed inputs written in the test (a list of
    control-slot Sharpes, `S`, and `N` in 0, 1, 2, 10 and 1000), `E(N)`,
    the excess, `p(N)` at the production thresholds and the threshold of
    §11.4 equal literal values to `1e-12`, each literal worked out in the
    test file's comments from the formulas of §11.2 and §11.4 and
    decision 60, not produced by `stats.py`. The whole `./scripts/gate M1`
    run should finish within DESIGN §18.2's 15 minutes; when it cannot,
    the builder files a finding with the measured time of each item and
    weakens nothing.

75. **`meta/ROADMAP.md`: steps S1.1 and S1.2 ticked; mission 9 is step
    S1.3.** Item 65 ticked step S1.1, but the roadmap's box was left
    unticked on the branch; this consultation ticks it. REVIEW-8 has no
    blocker and mission 8 closed no milestone (`meta/ARCHITECT.md` §3
    case 2), so step S1.2 is ticked. Mission 9 builds step S1.3 as items
    66 to 74 cut it, with REVIEW-8's two should-fix items and the two
    performance items of `meta/BACKLOG.md`, and closes M1: it ends with
    the gate run, and M1 is marked met when its review has no blocker and
    records `gate M1: PASS`. No gate item moves.
