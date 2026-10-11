# discotrade — project instructions (read by every session and sub-agent)

discotrade is a research instrument: an unattended daily loop that asks
LLM workers for price-based trading rules, tests them on data the workers
never saw, charges realistic costs, and tells its owner only when a fixed
alert rule fires. Every trading decision is simulated. Nothing in this
repository may send an order to a broker.

## Which document wins

1. A decisions file under `meta/decisions/`, newest first.
2. `DESIGN.md`, the build specification. Its sections are what briefs,
   commits and reviews cite.
3. `SPEC.md`, the owner's product specification. Read it for intent.

Where the code and `DESIGN.md` disagree, the design wins unless a finding
in `meta/findings/FINDINGS.md` says otherwise. Where `DESIGN.md` is silent,
choose the simplest thing and say so in the commit body. Where `DESIGN.md`
and `SPEC.md` disagree, follow `DESIGN.md` and file a finding. Builders
never edit `DESIGN.md`, `SPEC.md`, `PLAYBOOK.toml`, `meta/ROADMAP.md`,
`meta/BACKLOG.md`, `meta/ARCHITECT.md`, `meta/REVIEW-PROTOCOL.md`, any
`meta/BUILDER-*-PROMPT.md`, `meta/decisions/`, or anything under
`.claude/`, `docs/ARCHITECT-HANDBOOK.md` and `templates/`.

## Missions

A mission is one builder prompt, `meta/BUILDER-<N>-PROMPT.md`. The kickoff
line of the series never names a number: the mission to execute is the
prompt with the highest N on the branch. If that mission's
`meta/FINAL-REPORT-<N>.md` already exists, it is finished: change nothing
and reply with the `VERDICT: question` line its prompt gives for that case.

## The invariants (DESIGN §2), in one line each

- I-1 Only deterministic code touches market data and scores; an LLM never
  decides a result.
- I-2 A strategy sees only bars that had closed; the harness builds the
  slice.
- I-3 Devised on W, ranked once on T, believed only on the paper record.
- I-4 Every score is net of costs, at 1x and 2x.
- I-5 Bars, journal, ledgers are append-only.
- I-6 Re-running a day writes nothing new.
- I-7 Worker-written source runs only inside the container sandbox.
- I-8 Workers and the coordinator talk only to the harness; the coordinator
  never sees a score.
- I-9 No file under `src/` names a market, a contract or a venue.
- I-10 Every threshold lives in `config/thresholds.toml`, with history;
  instrument, track, calendar, spread and model config is frozen once
  created and changes only by the owner's decision, with history.
- I-11 Every test that `./scripts/check` or a gate runs works with no
  network and no secret.
- I-12 No wall clock in results; time comes from the injected clock.
- I-13 Secrets come from the environment, stay in the harness process, and
  are never written, logged, prompted or committed.
- I-14 Run state lives in a separate state directory, never in this
  repository.
- I-15 The simulator is the only executor.

A change that breaks an invariant is wrong whatever else it achieves.

## Stack

Python 3.11 or later, `uv`, src layout, package `discotrade`. Runtime
dependencies: `numpy`, `pandas`, `pyarrow`, `httpx`. Development: `pytest`,
`ruff`, `hypothesis`. No other dependency without a finding that explains
why. Module names and the directory layout are fixed by DESIGN §3.

## Gates

- `./scripts/check` (ruff, pytest without gate tests, command-line smoke):
  green three times in a row before every commit.
- `./scripts/gate <milestone>`: the milestone's gate tests under
  `tests/gates/`, run by the mission that closes the milestone and by its
  reviewer. A gate test asserts what DESIGN §18.3 says, no less.

## Conventions

- One commit per unit: `<area>: <one line>`, with a body that names the
  unit and the DESIGN sections it implements, lists every file, and states
  only what the tests prove. Push immediately. Never `git add -A`.
- Write the failing test before the code and see it fail.
- Tests never use the network, a real key, a real model, or a real `claude`
  binary. Fakes and fixtures live in `tests/`. A test that needs the
  network is marked `network`, one that needs a secret is marked `live`,
  and neither runs in `./scripts/check` or in a gate.
- Tests are deterministic: every random draw has a fixed seed, and nothing
  reads the wall clock.
- Every number that came from outside the project (a fee, a tick size, a
  date) is stored in config with `checked`, `source` and `verified`, and a
  value that could not be confirmed from a primary source is listed in the
  mission's report under NOT PROVEN.
- Config that moves a result is frozen once created (DESIGN §4.3):
  `config/thresholds.toml`, `config/instruments/`, `config/tracks/`,
  `config/calendars/`, `config/spreads/`, `config/models.toml`. The mission
  that creates a file fills it in; after that, no builder changes a value
  in it, even a wrong one, unless the brief names the decisions file that
  approves the change. A value you believe is wrong is a finding.
- Never run a background task (`run_in_background`, `nohup`, `setsid`,
  `disown`, a trailing `&`): the harness reaps them. Run long commands in
  the foreground with a timeout; `.claude/hooks/no_background.py` refuses
  the rest. Sub-agents run in the foreground, never in the background.
- `meta/` is the builder's state (checkpoint, plan, journal, findings,
  reports). Sub-agents do not edit `meta/plan.md` or `meta/CHECKPOINT.md`.
- A problem with the design, the spec or the plan is a finding in
  `meta/findings/FINDINGS.md` (the next free `D-###`), not an improvised
  change. A problem with hands itself (its guard, hooks, documents,
  playbook engine, notifications) goes under that file's "hands findings"
  heading (the next free `HF-###`) and is never worked around in product
  code.
