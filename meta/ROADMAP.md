# ROADMAP — discotrade series `discotrade-v1`

## Purpose

The product (`SPEC.md`, `DESIGN.md`): an unattended research instrument
that answers one question: do systematic, price-based trading rules
proposed by LLM agents hold up on data the agents never saw, after
realistic costs? Every trading decision in this series is simulated.

The series: this project is also the first shakedown of the hands architect
role (hands DESIGN §31, `architect/README.md`). The series runs
autonomously from its first kit. A builder executes one mission, a cold
reviewer grades it, and the architect role reads the review and this file
and files the next kit. The human approved this plan once, at the switch
point, and is called only on the escalation conditions in `PLAYBOOK.toml`.
Whatever is decided at an escalation becomes a decisions file in the next
kit. Findings about hands itself are never fixed in this project: they go
to `meta/findings/FINDINGS.md` under "hands findings" and the human carries
them to the hands Project.

## How to read this file

- A milestone is one list entry below. It is met when its gate command
  passes at the branch tip and the cold review of the mission that closes
  it has no blocker (DESIGN §18.2). Nothing else meets it.
- A milestone is built in steps, one builder mission per step, in order.
  A step is ticked `[x]` with its mission number and date when that
  mission's review has no blocker. A mission that only closes a review's
  blockers belongs to the step it repairs and takes the next mission
  number.
- The architect marks a milestone met by rewriting its first line as
  `- **M0 Harness core** — DONE <date> (missions <first> to <last>).` and
  changes nothing else in the entry. The first entry not so marked is the
  next unmet milestone.
- `meta/ARCHITECT.md` holds the architect role's standing instructions for
  this series: what a kit contains, how a brief is written, when to
  escalate. `meta/BACKLOG.md` holds carried review items and the owner's
  list.
- The series ends when M5 is met: the architect replies `VERDICT: series
  complete`. Running the live loop, more tracks and the stages toward real
  trading are the owner's and are not milestones of this series.

## Milestones

- **M0 Harness core** — DONE 2026-10-12 (missions 1 to 6).
  Gate: `./scripts/gate M0` prints `gate M0: PASS` at the branch tip, items G0.1 to G0.4 of DESIGN §18.3: three reference strategies equal an independent calculation; a lookahead-cheating strategy cannot gain; store, gap check, adjusted series and roll cost hold; config check passes and no market is named in the source.
  - [x] S0.1 Skeleton, config records, trading calendar, bar store, gap check, null synthetic market. DESIGN §3, §4, §5.1 to §5.4, §17.1, §18.1, §18.2. Mission 1, 2026-10-12.
  - [x] S0.2 Bar sources (synthetic with contracts, crypto test data, vendor adapter against a fake client), rolls and the adjusted series, spread tables and their measurement. DESIGN §5.5 to §5.7, §17.1, §19.3 (L1, L2 offline behaviour). Mission 2, 2026-10-12.
  - [x] S0.3 Strategy contract, indicator library, evaluation loop, cost model, executor and simulator, metrics, the `backtest` command, the three reference strategies; REVIEW-2's two should-fix items. DESIGN §6, §7, §8, §3. Mission 3; mission 4 closes REVIEW-3's blocker and should-fix items (decisions-2026-10-12 item 33). (Step S0.3 as first written did not fit seven units; it was split into S0.3 and S0.4, decisions-2026-10-12 item 28.) Missions 3 and 4, 2026-10-12.
  - [x] S0.4 The independent calculation (given to a sub-agent of its own that is told not to open the modules it checks), the cheating strategy, the gate tests. DESIGN §7, §8, §18.2, §18.3 (M0). Mission 5; mission 6 closes REVIEW-5's blocker and should-fix item and runs the gate again (decisions-2026-10-12 item 46). Closes M0. Missions 5 and 6, 2026-10-12.
- **M1 Journal, controls and ledger** — steps S1.1 to S1.3 (SPEC phase 1).
  Gate: `./scripts/gate M1` prints `gate M1: PASS` at the branch tip, items G1.1 to G1.4 of DESIGN §18.3: a one-year replay of the null market with controls only is centred on minus costs with rank persistence near zero; the journal recomputes exactly and a re-run writes nothing; the scripted lifecycle scenario shows every transition; deflation and tightening match hand values.
  - [ ] S1.1 State directory with `init-state`, the health log, decision journal, paper records, content hashes, the day loop for journaling (daily steps 1 and 2 on a synthetic source), `journal recompute`, idempotent days, the injected clock. DESIGN §9, §15.2 (the health event and its log only), §16.1 (steps 1 and 2), §16.2, §2 (I-5, I-6, I-12, I-14). Mission 7, 2026-10-12.
  - [ ] S1.2 Controls, the three ledgers, lifecycle, clean and exposed observations, and the statistics of §11 as functions (rank persistence, deflated scores, tightening); REVIEW-7's two should-fix items. DESIGN §10.1 to §10.3, §11, §9.3 (the `clean` flag). (Step S1.2 as first written did not fit seven units; it was split into S1.2 and S1.3, decisions-2026-10-12 item 65.)
  - [ ] S1.3 Table, combined portfolio, rank persistence in the day loop, the replay harness for controls only (and scripted candidates for G1.3), the two performance items of `meta/BACKLOG.md`, the gate tests. DESIGN §10.4, §10.5, §11.1, §16.4, §18.3 (M1). Closes M1.
- **M2 Sandbox and validation** — steps S2.1 and S2.2 (SPEC phase 2).
  Gate: `./scripts/gate M2` prints `gate M2: PASS` at the branch tip with the container backend really running, items G2.1 to G2.4 of DESIGN §18.3: the hostile suite is rejected stage by stage; a sign-flipped duplicate is caught; the probe sees no network, a read-only root, a non-root user and only W bars; the validation sequence passes and fails as built.
  - [ ] S2.1 Static check, the sandbox interface with the runner and the subprocess and in-process backends, the validation sequence and the grid, the correlation gate. DESIGN §12.1 to §12.4.
  - [ ] S2.2 The container backend and its image, the hostile suite, the probe, moving approach execution in the day loop behind the sandbox, the gate tests. DESIGN §12.4, §12.5, §18.3 (M2), §19.3 (L5 offline behaviour). Closes M2. Needs Docker or Podman on the builder's machine; without one the builder asks, it does not skip.
- **M3 Workers** — steps S3.1 and S3.2 (SPEC phase 3).
  Gate: `./scripts/gate M3` prints `gate M3: PASS` at the branch tip, items G3.1 to G3.3 of DESIGN §18.3: twenty replay days with the scripted provider over three model families yield at least ten valid, mutually distinct candidates; rotation, retry, storage, removal and the token budget behave; no prompt leaks a symbol, a date, a bar or a score.
  - [ ] S3.1 The W profile, anonymization, the registry, the prompt builder, the response parser. DESIGN §13.1 to §13.4.
  - [ ] S3.2 Providers (OpenAI-compatible, scripted, Claude worker against a fake binary), the model pool with rotation, failure tracking and the cell fallback, the coordinator interface with its scripted form only, the day's generation with retry and budget, daily steps 3 to 5 in the replay, the worker corpus, the gate tests. DESIGN §13.5 to §13.7, §14.1, §14.2 (scripted form), §14.3, §16.1 (steps 3 to 5), §18.3 (M3), §19.3 (L3 offline behaviour). Closes M3.
- **M4 Coordinator and alerts** — steps S4.1 to S4.3 (SPEC phase 4).
  Gate: `./scripts/gate M4` prints `gate M4: PASS` at the branch tip, items G4.1 to G4.6 of DESIGN §18.3: sixty unattended replay days complete; the planted edge fires the persistent-approach alert for the planted approach and for nothing else, and its null twin fires no finding alert; failures leave state untouched; the coordinator's input has no score; the dashboard shows every panel and the thresholds the alert code reads; three replay days run in the container.
  - [ ] S4.1 Alert rules for findings and health, alert state and payloads, the dashboard, the thresholds history test. DESIGN §15.1 to §15.3, §15.5, §11.4, §4.3.
  - [ ] S4.2 The Claude Code form of the coordinator (fake binary), digest and issue sinks, deny rules from the protected paths, the full daily run with staging, lock, retry, catch-up, budgets and the state commit. DESIGN §14.2, §14.4, §15.4, §16.1 to §16.3, §19.3 (L4, L6 offline behaviour).
  - [ ] S4.3 The full-loop replay, the planted-edge market and its corpus, failure injection, the container smoke replay, the gate tests. DESIGN §16.4, §17.2, §18.2, §18.3 (M4). Closes M4. Needs the container runtime again (G4.6).
- **M5 Deployment package** — step S5.1 (SPEC phase 5, as far as a builder can take it).
  Gate: `./scripts/gate M5` prints `gate M5: PASS` at the branch tip, items G5.1 to G5.4 of DESIGN §18.3: the offline doctor passes on a fresh state repository and names each planted fault; one day runs end to end through the vendor adapter on the fake client; the deploy files parse and protect the protected paths; the operations document covers every live check.
  - [ ] S5.1 The offline doctor, the live checks L1 to L8 gathered under `doctor --live` (L7 and L8 built here), the deploy directory, the operations document, the gate tests. DESIGN §19, §18.3 (M5). Closes M5 and the series.

## After the series (the owner's, not milestones)

1. Run the live checks L1 to L8 (DESIGN §19.3, `docs/OPERATIONS.md`). L1 and L2 can be run as soon as M0 is met, and are best run then.
2. Confirm or replace the readings of DESIGN §20 and the open items of §21.
3. Deploy to the server and start the live daily loop (SPEC phase 5).
