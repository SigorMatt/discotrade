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
