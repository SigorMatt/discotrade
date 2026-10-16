VERDICT: mission 16 finished

# FINAL REPORT — mission 16 (roadmap step S3.2a, repaired)

Brief: `meta/BUILDER-16-PROMPT.md`. Base 72c7836 (`plan: mission 16 kit (S3.2a
repaired, REVIEW-15 blocker and should-fix)`). Decisions:
`meta/decisions/decisions-2026-10-16-m16.md` (127 to 131), with
`meta/decisions/decisions-2026-10-16-m15.md` (118 to 126; 121 (a) and 122 (c)
the items repaired), the owner's `meta/decisions/decisions-2026-10-15-owner.md`
(O-19, O-20, O-22 bind) and `meta/decisions/decisions-2026-10-13-owner.md`
(O-16 to O-18 bind); items 1 to 126 still bind. This mission closes no
milestone and runs no gate (decision 127 (a)). It closes REVIEW-15's blocker and
both should-fix items and the first half of note 3. Container runtime: docker;
`uv run discotrade sandbox build` at the tip printed `sandbox build: present,
nothing built` and `discotrade-sandbox:3b7d75c39621`.

## What changed

| Unit | sha | What |
|---|---|---|
| U0 | ef3ebc4 | `plan:` the plan, checkpoint, journal; D-013, HF-010, HF-011, HF-012 lines appended to FINDINGS.md (decision 131 (e)) |
| U1 | 6e3caa5 | `src/discotrade/workers/providers.py`: `key_present()`; the module and `openai_compat_from_env` docstrings state decision 128 (b) and no more; every `ProviderError` of `OpenAICompatProvider` raised after its `except` block ends, so `__cause__` and `__context__` are `None` (128 (e)). `src/discotrade/doctor.py`: the key check calls `key_present()` and no longer imports `KEY_ENV`. `src/discotrade/cli.py` help text and `doctor.py`'s module docstring say "the worker key" in place of the name (finding D-016). 22 tests (decision 128) |
| U2 | 512bb3e | `src/discotrade/doctor.py`: `doctor --live workers` reads the pool with `config.load_models` and the timeout from `config.load_run(...).workers.request_timeout_seconds`; `WORKERS_TIMEOUT_SECONDS`, the raw `tomllib` parse and its import removed; a `ConfigError` is one line and exit 1, no request. 8 tests; the test file's `MODELS_TOML` given the loader's fields, assertions unchanged (decision 129) |
| U3 | dcff385 | `tests/test_synth_cache.py`: two tests for the cache key's calendar and bar-length parts; `synth.py` unchanged, 130 (c) did not apply (decision 130) |
| U4 | this commit | this report |

Meta commits: 38c98cc (U0 done), bdeb96f (U1), 7f100b4 (U2), ef4548f (U3).
Each unit commit's body lists its files. The only product files changed are
`src/discotrade/doctor.py`, `src/discotrade/workers/providers.py` and (two text
lines, D-016) `src/discotrade/cli.py`; nothing of this mission is called from
`run-day` or `replay`.

## Speed

`./scripts/check` wall time on the builder's machine (four cores), each run its
own foreground call with a 20-minute timeout:

| Where | Runs |
|---|---|
| mission 15's tip 6259365 (FINAL-REPORT-15) | 848, 828, 838 s |
| U1 6e3caa5 | 828, 832, 825 s |
| U2 512bb3e | 831, 835, 837 s |
| U3 dcff385 | 834, 837, 890 s |
| tip ef4548f (U4, before this commit) | 841, 834, 837 s, each `check: green` |

At the tip each run printed `2323 passed, 182 deselected` (0 skipped, so the
`container` tests ran on discotrade-sandbox:3b7d75c39621), `config check: ok,
173 unverified values` and `check: green`; pytest 840.10 s, 832.36 s, 835.92 s.
The mission added 32 tests to the check (2291 at mission 15's tip). Decision
114's 12 minutes (720 s) is missed by 114 to 121 s at the tip; no run at the tip
is above HF-006's 15 minutes, so no D-013 line is appended by this unit.

## Corrections

REVIEW-15 blocker 1: the claim that one function reads `NEBIUS_API_KEY` was false
when written, because `src/discotrade/doctor.py` read `os.environ.get(KEY_ENV,
"")` itself (d9acfcd). Commit bodies are not rewritten and FINAL-REPORT-15 is not
edited (decision 128 (d)); the docstrings were corrected by U1 (6e3caa5). Each
place the claim stands, quoted, with decision 128 (b)'s sentence beside it:

| Where the claim stands | As it stands | The rule as the code holds it (decision 128 (b)) |
|---|---|---|
| d9acfcd's body (mission 15 U3), its Files list | "OpenAICompatProvider with openai_compat_from_env (the one place NEBIUS_API_KEY is read)," | Under `src/`, the name `NEBIUS_API_KEY` appears only in `src/discotrade/workers/providers.py`. There, `openai_compat_from_env` is the one function that reads the key's value, and it reads it to build the provider. `key_present` only tests whether the key is set. `ClaudeWorkerProvider` leaves the key out of its child's environment. |
| `src/discotrade/workers/providers.py` module docstring before 6e3caa5 (line 13) | "The worker key is read from ``NEBIUS_API_KEY`` only by :func:`openai_compat_from_env`, the code that builds the provider; it is never logged, stored in a field or put in a prompt (I-13)." | Under `src/`, the name `NEBIUS_API_KEY` appears only in `src/discotrade/workers/providers.py`. There, `openai_compat_from_env` is the one function that reads the key's value, and it reads it to build the provider. `key_present` only tests whether the key is set. `ClaudeWorkerProvider` leaves the key out of its child's environment. |
| `openai_compat_from_env`'s docstring before 6e3caa5 (line 196) | "The provider with its key read from ``NEBIUS_API_KEY`` here and nowhere else." | Under `src/`, the name `NEBIUS_API_KEY` appears only in `src/discotrade/workers/providers.py`. There, `openai_compat_from_env` is the one function that reads the key's value, and it reads it to build the provider. `key_present` only tests whether the key is set. `ClaudeWorkerProvider` leaves the key out of its child's environment. |
| FINAL-REPORT-15, `## What changed`, row U3 | "`src/discotrade/workers/providers.py`: `ScriptedProvider`, `OpenAICompatProvider` (`openai_compat_from_env` the one reader of `NEBIUS_API_KEY`), `ClaudeWorkerProvider`; `doctor --live workers` (L3) (decision 122)" | Under `src/`, the name `NEBIUS_API_KEY` appears only in `src/discotrade/workers/providers.py`. There, `openai_compat_from_env` is the one function that reads the key's value, and it reads it to build the provider. `key_present` only tests whether the key is set. `ClaudeWorkerProvider` leaves the key out of its child's environment. |

At this tip, `grep -rn NEBIUS_API_KEY src/` hits only
`src/discotrade/workers/providers.py` (lines 13, 35, 221, 223: the module
docstring, `KEY_ENV`, and `openai_compat_from_env`'s docstring); the docstrings
there now say decision 128 (b)'s sentences.

## Cache key

Decision 121 (a)'s key for the synthetic source's process cache
(`src/discotrade/sources/synth.py`, line 213), each part with the test that holds
it and the wrong change that turns it red (dcff385's body: each change made
alone in the key and reverted, run over `tests/test_synth_cache.py` and
`tests/test_synth.py` only):

| Key part | Test that holds it | Wrong change that turns it red |
|---|---|---|
| the `[source]` table with its seed | `tests/test_synth_cache.py::test_a_changed_seed_in_a_copied_configuration_gives_another_series_in_the_same_process` (also red: `tests/test_synth.py::test_same_seed_same_bars_and_different_seed_different_bars`) | the seed removed from the `[source]` table in the key (both tests red); the whole `[source]` table replaced by its adapter name (the seed test red) |
| `trusted_from` | `tests/test_synth_cache.py::test_a_changed_trusted_from_in_a_copied_configuration_gives_another_series` | `trusted_from` removed from the key (only this test red) |
| the calendar record | `tests/test_synth_cache.py::test_a_changed_calendar_record_in_a_copied_configuration_gives_another_series` (U3) | the calendar record removed from the key (only this test red) |
| the bar length | `tests/test_synth_cache.py::test_the_same_instrument_at_another_bar_length_gives_another_series` (U3) | the bar length removed from the key (only this test red) |

The calendar test copies `tests/fixtures/config/` under the test's temporary
directory, fetches SYNL (calendar `synth_week`, seed 105) hourly over
[2019-01-07, 2019-04-01), appends a closure 2019-02-12 09:00 to 2019-02-13
12:00 New York to the copied calendar, and finds in the same process a series
with no bar in that span, fewer bars, and equal to the series fetched after
`clear_cache()`. The bar-length test fetches the same record at 1800 s (every
`synth_week` boundary is on a half hour; U3's choice, the design setting no
other constraint) and finds bars at :00 and :30, more bars than the hourly
series, and equal to the 1800 s series fetched after `clear_cache()`.

## Decisions 128 to 130: the tests that hold them

- **128** (one place reads the worker key; no cause or context) —
  `tests/test_workers_providers.py`:
  `test_the_worker_key_is_named_only_in_providers_and_key_env_is_imported_nowhere`
  (128 (c): enumerates every `.py` under `src/discotrade/` itself; the text
  `NEBIUS_API_KEY` only in `providers.py`; no `KEY_ENV` import from
  `discotrade.workers.providers` elsewhere, read by `ast`),
  `test_the_source_test_resolves_a_relative_import_of_key_env`,
  `test_key_present_tells_whether_the_key_is_set_and_not_blank` (unset, `""`,
  `"   "`, `"\t \n"`, a dummy key),
  `test_openai_compat_complete_errors_have_no_cause_and_no_context`,
  `test_openai_compat_list_models_errors_have_no_cause_and_no_context` (128 (e));
  `tests/test_doctor.py`:
  `test_live_workers_without_a_usable_key_never_calls_the_transport` (ids
  `unset`, `spaces`) and the existing
  `test_live_workers_without_the_key_prints_one_line_exits_1_no_request`.
- **129** (`doctor --live workers` reads the loaded configuration) —
  `tests/test_doctor.py`:
  `test_live_workers_refuses_a_models_toml_the_loader_refuses_as_config_check_does`
  (one case per decision 123 (c) refusal: unknown key, a fallback of another
  maker, a duplicate id, an empty pool),
  `test_live_workers_refuses_a_run_toml_the_loader_refuses_with_one_line`,
  `test_live_workers_builds_the_provider_with_run_tomls_request_timeout`,
  `test_live_workers_lists_the_pool_in_file_order_with_its_labels`,
  `test_doctor_module_holds_no_timeout_constant_and_no_raw_toml_parse`; and the
  existing L3 tests moved to a valid copied configuration
  (`test_live_workers_without_models_toml_prints_one_line_exits_1_no_request`,
  `test_live_workers_with_an_empty_base_url_prints_one_line_exits_1_no_request`,
  `test_live_workers_prints_the_pool_against_the_providers_list`,
  `test_live_workers_reports_a_model_the_provider_does_not_list`).
- **130** (the cache key's calendar and bar-length parts) —
  `tests/test_synth_cache.py`:
  `test_a_changed_calendar_record_in_a_copied_configuration_gives_another_series`,
  `test_the_same_instrument_at_another_bar_length_gives_another_series`; the
  table above for every key part.

## What the tests prove

- Worker key (U1): of the `.py` files under `src/discotrade/` the test
  enumerates, only `workers/providers.py` contains the text `NEBIUS_API_KEY`, and
  none imports `KEY_ENV` from `discotrade.workers.providers` in the forms the
  test's `ast` reader resolves (absolute and relative `from ... import`).
  `key_present()` is `False` for an unset, empty or whitespace-only key and
  `True` for a dummy key, and returns a `bool`. `doctor --live workers` with the
  key unset or of spaces prints one line on standard error and exits 1, with a
  transport that fails the test if called. Seen to fail (U1's body): the
  doctor's own `os.environ.get(KEY_ENV, "")` restored turns the source test red.
- No cause or context (U1): each `ProviderError` of `OpenAICompatProvider` the
  tests raise (complete's status, not-JSON, three malformed bodies, timeout and
  transport cases; list_models' status, not-JSON, timeout, transport and two
  malformed bodies) has `__cause__` and `__context__` both `None` and no key in
  its text. Seen to fail: the error raised inside its `except` block with `from
  None` only turns 10 context tests red.
- Doctor configuration (U2): in a configuration copied under the test's
  temporary directory, each of decision 123 (c)'s four refusals gives one
  standard-error line, equal to the doctor's head plus `discotrade config
  check`'s own FAIL text for the same file plus `; no request was made`, exit 1,
  standard output empty, no transport call; a `run.toml` `[workers]` with an
  unknown key the same; `request_timeout_seconds = 17.5` in a copied `run.toml`
  reaches the provider's request (`request.extensions` in the `MockTransport`);
  the listing is the pool in file order with its labels; `doctor.py` holds no
  `WORKERS_TIMEOUT_SECONDS` and imports no `tomllib` (`ast`). Seen to fail: the
  raw parse restored (the four refusal tests and the `ast` test red); the fixed
  300.0 restored (the timeout test red).
- Cache key (U3): as the `## Cache key` table says, each part's removal from the
  key turns its own test red, run over `tests/test_synth_cache.py` and
  `tests/test_synth.py`.
- `./scripts/check` green three times at ef4548f (above), with the `container`
  tests run.
- Frozen files: `git diff --stat 72c7836 HEAD -- config tests/gates
  tests/fixtures/rejected tests/fixtures/config tests/fixtures/config_frozen.json`
  is empty at ef4548f: no file under `config/`, `tests/gates/` or
  `tests/fixtures/rejected/`, no record under `tests/fixtures/config/` and no
  entry of `tests/fixtures/config_frozen.json` changed in this mission.

## Where the design is silent

- U1: decision 128 (c)'s source test cannot pass with the name in
  `src/discotrade/cli.py`'s `--live` help string and `doctor.py`'s module
  docstring, both outside decision 127 (a)'s list and the U1 brief's "key check
  only". The simplest change was made (both say "the worker key"; no behaviour
  changes, no test asserted either text) and filed as finding **D-016**.
- U2: a `run.toml` without a `[workers]` table is refused by the same one line,
  as a `ConfigError` naming `run.toml` (the design is silent; the simplest
  thing).

## NOT PROVEN

- No real provider, model or `claude` binary was called: live checks L3 (the
  pool listed by the provider) and L4 are not run. Every test uses the scripted
  corpus, `httpx.MockTransport` or a fake `claude`; a key is set only as a dummy.
- The base URL, the model ids and the cutoffs of `config/models.toml` stay
  unverified (`verified = false`); this mission read none of them from a
  primary source and changed none.
- Nothing of step S3.2a (mission 15 and this mission) is called from `run-day`
  or `replay`; the generation, the pool and the coordinator in the day are step
  S3.2b's to prove.
- The source test's limits: it reads the text `NEBIUS_API_KEY` and `from
  discotrade.workers.providers import KEY_ENV` (absolute or relative); another
  spelling of the name (built from parts, encoded), `import
  discotrade.workers.providers` followed by attribute access to `KEY_ENV`, or a
  read through another module's alias is not caught.
- The cache-key removals in U3 were run against `tests/test_synth_cache.py` and
  `tests/test_synth.py` only, not against the gate, container or full check
  tests.
- `__cause__` and `__context__` are shown `None` for the failure kinds the tests
  raise; a failure kind not raised by a test is not shown.
- The speed figures are from the builder's machine (four cores, varying load);
  `./scripts/check` is above decision 114's 12 minutes at every unit and the tip
  (825 to 890 s; D-013 open).
- What remains of FINAL-REPORT-15's NOT PROVEN, item by item:
  1. No real provider, model or `claude` called (L3, L4): remains (above).
  2. Base URL, model ids, cutoffs unverified: remains (above).
  3. The Claude worker's flags only as the builder's `claude --help` (Claude
     Code 2.1.300) and SPEC §17 give them, the JSON reply fields not read from
     that binary: remains.
  4. The scripted provider's token counts an estimate by rule
     (`ceil(characters / 4)`): remains.
  5. Nothing called from `run-day` or `replay`: remains (above).
  6. The speed figures from the builder's machine; check above 12 minutes:
     remains (above); U2 of mission 15's cache gave no speed gain.
  7. The generation section of FINAL-REPORT-15 from one throwaway run per
     scenario: remains; not repeated here.
  8. What FINAL-REPORT-15 carried from FINAL-REPORT-14 and earlier (the
     profile's statistics, anonymization, the leak check's scope, G2.3's gate
     file, the prompt sample's registry state, `trusted_hashes`' same-stat
     rewrite, `BUILTIN_EXCEPTIONS` on Python 3.14.6 only, the container a
     boundary only as docker 29.1.3 and this kernel make it, and the rest as
     FINAL-REPORT-15 lists them): remains, unchanged by this mission.
  9. The numbers from outside the project in `config/models.toml` (four model
     records and `base_url`): remain not proven from a primary source. This
     mission added no number from outside the project.
  Closed by this mission: REVIEW-15 note 6's addition (decision 121's calendar
  and bar-length key parts) is now held by tests, within the limit above.

## Findings filed and answered

- **D-013** (`./scripts/check` time): times line appended at U0, ef3ebc4
  (REVIEW-15's 794 to 834 s; decision 131 (e)). No line from this unit: no run
  above 15 minutes. **Open** (decision 121 (c)'s rule; 131 (f)).
- **HF-010** (stale worktrees): status line at U0, ef3ebc4 (REVIEW-15 note 8).
  Open, for the hands Project.
- **HF-011** (prefixes missing from the review protocol's skip list): status
  line at U0, ef3ebc4 (REVIEW-15 note 9, d5dfa02's `report:`). Open, for the
  hands Project. This report's commit carries the same `report:` prefix, kept
  for consistency with d5dfa02.
- **HF-012** (reviewer concurrency and slips): status line at U0, ef3ebc4
  (REVIEW-15 note 10, with its direction for the protocol template). Open, for
  the hands Project.
- **D-016** (filed by U1, 6e3caa5): decision 128 (c)'s source test needed two
  text lines outside decision 127 (a)'s list, `cli.py`'s help text and
  `doctor.py`'s module docstring. Open, for the architect.
- D-014, D-015, HF-008 and HF-009 remain open as FINAL-REPORT-15 left them. No
  other finding was filed in this mission.

## Review items

| Item | Resolution | sha |
|---|---|---|
| REVIEW-15 blocker 1 (the false claim that one function reads the key; the doctor read it itself) | U1, decision 128 (a) to (c): `key_present()`, the doctor asks it, the source test; the docstrings corrected (128 (b)); `## Corrections` above (128 (d)) | 6e3caa5, this commit |
| REVIEW-15 should-fix 1 (`doctor --live workers` hardcodes the timeout and parses `models.toml` raw) | U2, decision 129: `config.load_models` and `config.load_run`'s `[workers]` timeout; the four refusals tested | 512bb3e |
| REVIEW-15 should-fix 2 (cache key's calendar and bar-length parts untested) | U3, decision 130: two tests in `tests/test_synth_cache.py`; `synth.py` unchanged | dcff385 |
| REVIEW-15 note 1 (`model_skipped` also when the fallback replaces) | stands as built, decision 131 (a) | — |
| REVIEW-15 note 2 (weak flag dated D; weak at paper day 0 untested) | to step S3.2b, decision 131 (b) | — |
| REVIEW-15 note 3 (`ProviderError` keeps the httpx `__context__`; `claude` grandchild not killed) | first half U1, decision 128 (e); second half to step S4.2, decision 131 (d) | 6e3caa5 |
| REVIEW-15 note 4 (duplicate retry messages; indirect imports) | duplicate retry test to step S3.2b; the indirect imports of `socket` and `subprocess` stand, decision 131 (c) | — |
| REVIEW-15 note 5 (the cache has no bound) | stands, one entry per distinct record, decision 131 (d) | — |
| REVIEW-15 note 6 (add the calendar and bar-length key parts to NOT PROVEN) | U3 tests and this report's `## Cache key`, decision 130 (d) | dcff385, this commit |
| REVIEW-15 note 7 (kit commit 301a5c7 in range; no forbidden builder edit) | no action (observation) | — |
| REVIEW-15 note 8 (stale worktrees, HF-010) | U0 findings line, decision 131 (e) | ef3ebc4 |
| REVIEW-15 note 9 (`report:` prefix, HF-011) | U0 findings line, decision 131 (e) | ef3ebc4 |
| REVIEW-15 note 10 (sequential reviewers and their slips, HF-012) | U0 findings line, decision 131 (e) | ef3ebc4 |

## Acceptance

- `./scripts/check` green three times at ef4548f (841, 834, 837 s; mission 15's
  tip 828 to 848 s), 0 skipped, so the `container` tests ran. Met.
- Under `src/discotrade/`, `NEBIUS_API_KEY` appears only in `providers.py` and
  no other module imports its `KEY_ENV`; the doctor asks `key_present()`; a test
  enumerates the files and holds both. Met (U1).
- No `ProviderError` of the OpenAI-compatible provider the tests raise keeps a
  cause or a context. Met (U1).
- `doctor --live workers` reads `models.toml` through `config.load_models` and
  its timeout from `config/run.toml`'s `[workers]`, refuses each of decision
  123 (c)'s four refusals with one line and no request, and builds the provider
  with the configured timeout. Met (U2).
- Each of the cache key's parts has a test that goes red when that part is left
  out of the key. Met (U3; `## Cache key`).
- The false claim corrected in the docstrings (U1) and in `## Corrections`
  above, in decision 128 (b)'s words. Met.
- No file under `config/`, `tests/gates/`, `tests/fixtures/rejected/`, no record
  under `tests/fixtures/config/` and no entry of
  `tests/fixtures/config_frozen.json` changed (the diff above is empty). Met.
- Every unit commit's body lists its files; U0 is `plan:`. Met.
- No test uses the network, a secret or the wall clock; no state or job
  directory inside the repository (`git status` clean after the three runs);
  no test builds the image. Met as the units' tests and the check show.
- This file has `## Corrections`, `## Cache key`, NOT PROVEN and the
  review-items table.

VERDICT: mission 16 finished
