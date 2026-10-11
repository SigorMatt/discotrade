# Strategy Discovery Swarm: Design Spec v1

Oct 10, 2026 · @Matthew Sigurko

## 1. Purpose and scope

The system runs unattended and answers one question: do systematic, price-based trading rules proposed by LLM agents hold up on data the agents never saw, after realistic costs?

It is a research instrument first. In v1 every trading decision is simulated: the system decides as if it were investing, records the decision, and judges it when new data arrives, with all fees and costs charged. Real orders are a later stage that only the owner can enable, under conditions fixed in advance (section 14).

**In scope for v1**

- Hourly bars on a basket of liquid micro futures traded through Interactive Brokers.
- A daily walk-forward loop that generates, tests, ranks and retires approaches without human input, and keeps a journal of every simulated decision with full costs.
- A findings digest that reaches the owner only when a fixed alert rule fires.

**Out of scope for v1**

- Sending orders to a broker, on paper or live (stages 2 and 3 in section 14).
- Workers that run their own multi-step tool loops.
- Discretionary chart patterns, news, fundamentals or order-book data.
- Weighted allocation across approaches; the combined paper portfolio uses equal weights.

## 2. Terms

For any one approach, time is split into three segments that never overlap. The split is the core safeguard: an approach is devised on one, ranked on the next, and believed only on the third.

| Term | Meaning | v1 default |
| --- | --- | --- |
| W (devise window) | Rolling window the workers' prompts are built from; ends where T begins | 90 days |
| T (rank window) | Rolling window of the most recent data, used once to decide whether a candidate enters the table | 14 days |
| P (paper record) | Every day after an approach is admitted; the only data that counts as evidence | Grows daily |
| Slide | Each day one new day of bars enters and the oldest leaves W | 1 day |
| Approach | One submitted strategy function with fixed parameters |  |
| Trial | Any approach that passed validation and was scored on T, kept or not |  |
| Cell | One niche in the grid: strategy family crossed with holding horizon |  |
| Control | A random or buy-and-hold approach scored exactly like the others |  |
| Decision journal | Append-only record of every simulated position, fill and cost |  |

The windows slide forward one day at a time. A candidate created today is devised on the 90 days that ended 14 days ago and ranked on the last 14 days. From tomorrow on, every day is new to it and is added to its paper record.

## 3. Architecture

Three layers, with one rule: only deterministic code touches market data and scores. LLMs supply ideas and prose, never results.

&#91;embedded content: architecture · 3 layers, 5 parts\]

The coordinator and the workers talk only to the harness, never to each other or to the data.

| Layer | What it is | Does | Never does |
| --- | --- | --- | --- |
| Harness | Plain Python on a scheduler, built and maintained by Claude Code | Fetches data, builds profiles, validates and sandboxes submissions, backtests, scores, keeps the decision journal, table and ledger, evaluates alerts | Call an LLM to decide a result |
| Coordinator | Claude Code, invoked headlessly once per day | Chooses cells to fill, writes briefs, writes the digest, proposes code fixes on a branch | See scores when writing briefs; change scoring, cost or alert code unattended |
| Workers | One chat completion each, on open-weight models or Claude subagents | Turn a brief and a W profile into one strategy function | Use tools, see raw bars, see T or P, keep state |

## 4. Data layer

The pipeline is instrument-agnostic: each instrument is a config record, and nothing else in the code names a market.

**Tracks**

A track is one configuration: bar size, W, T, history cap, instrument list and grid. The harness code is identical across tracks, and each track has its own table, ledger and alert state. v1 runs one track, hourly bars with W of 90 days and T of 14 days. A long-horizon track (daily bars, T of about three months) is added as a config once the hourly loop is proven, on the same futures universe.

**Instruments**

- Live track: six to ten micro futures across equity indices, gold, crude oil and currencies, with hourly bars from a data vendor that works with a plain API key and has long history (Databento is the candidate, with CME hourly bars back to 2010). Interactive Brokers is the venue whose contracts and fees are modeled, but it is not the data source: its API needs a weekly manual login and does not serve expired futures older than two years. Confirmed on 2026-10-11: micro S&P 500, micro Nasdaq-100, micro Dow, micro Russell 2000, micro gold, micro silver, micro crude oil, micro EUR/USD (costs and volumes in section 17).
- Test data only: hourly crypto bars from a public exchange API, used to develop the backtester, cost model and sandbox before the vendor data is connected. Crypto never becomes a live track.

**Instrument record**

- Symbol, venue, quote currency, trading hours and calendar.
- Cost profile: fee per side, spread estimate, slippage coefficient, holding cost, whether shorting is allowed.
- Data source and the date from which history is trusted.

**Bars**

- Fields: open time (UTC), open, high, low, close, volume.
- Stored as Parquet, one file per instrument per month, append-only. A bar is written only after it has closed.
- A gap check runs on every fetch. Missing bars are recorded, never interpolated. When gaps exceed 1% of bars in W or T, that day's candidate generation is skipped and a health alert is raised.

**Anonymization for workers**

- Each instrument is given a neutral label (A, B, C) that changes for every worker prompt.
- Prices are multiplied by a random constant per instrument per prompt, and volume by another. Returns are unchanged.
- Calendar dates are replaced by bar index. Hour of day and day of week are kept, because time-of-day effects are a legitimate cell.
- Known limit: rescaling removes round-number and tick-size effects, and a distinctive price path can still be recognized. Section 10 covers the stronger defense.

## 5. Strategy interface and validation

A worker's only contract with the pipeline is one Python function. Everything upstream of that function can be flaky without corrupting a result.

```python
PARAMS = {"lookback": 48, "threshold": 1.5}   # at most 5 numeric parameters

def position(bars, params):
    """bars: DataFrame of the most recent closed bars for one instrument,
    columns open/high/low/close/volume plus hour and weekday.
    Returns a target position in [-1.0, 1.0] for the next bar."""
```

**Rules**

- The harness calls the function once per bar and passes only bars that have closed, capped at the track's history cap, which equals W's length in bars. Lookahead is impossible by construction. When a window is scored, the bars before it are still passed as context so indicators are warmed up at its first bar; only positions taken inside the window are scored.
- The function is pure: no state between calls, no file or network access, no randomness, no clock.
- Allowed imports: numpy, pandas, and the project's own indicator library. Nothing else.
- At most 5 numeric parameters and 60 lines of code. The caps limit overfitting and keep approaches comparable.
- A worker may declare up to 3 values for each of at most 2 parameters. The harness runs that grid on W, identically for every worker, and fixes the best net result. This is the only tuning allowed.
- Where an instrument does not allow shorting, negative outputs are clipped to 0.

**Validation, in order**

1. Static check: parses, defines `PARAMS` and `position`, uses only allowed imports, respects the caps.
2. Dry run on W in the sandbox: returns a finite number in range for every bar, under 50 ms per call.
3. Determinism: two runs on W give identical positions.
4. Activity: at least 30 position changes on W, so T is likely to hold enough trades to score.
5. Correlation gate against existing approaches (section 8).

A failed submission gets one retry with the error text. A second failure is logged as a wasted call, not a trial.

## 6. Cost model and fills

Every fill is modeled pessimistically, and all scores are net of costs. At hourly bars, costs decide most outcomes.

| Component | Rule |
| --- | --- |
| Fill timing | A position computed at the close of bar t is traded at the open of bar t+1 |
| Fees | Broker commission plus exchange and regulatory fees, per contract per side |
| Spread | Half the spread paid on every trade, never less than half a tick; wider outside the main session |
| Slippage | Coefficient times recent realized volatility, added per trade |
| Holding cost | Roll cost each time a position is carried into the next contract: two extra trades plus the spread between contracts |
| Order type | Market orders only in v1; limit orders are not modeled |

**Usage**

- Each approach is scored at 1x and at 2x the modeled costs. An approach that is positive at 1x and negative at 2x is flagged fragile.
- Breakeven cost per trade is reported for every approach: the per-trade cost at which its net return is zero.
- Workers are told the cost model in the prompt, so they do not propose turnover that cannot survive it.
- Fee and spread numbers live in the instrument record with the date they were checked. A health alert fires if any is older than 90 days.

Per-contract costs for each micro future come from Interactive Brokers' current commission schedule and the exchange's fee list, recorded with the date checked. Spreads are measured per contract and hour of day from a sample of quote data, not assumed. Positions are scored as fractions of notional in v1; rounding to whole contracts is a live-trading concern and is noted for later.

## 7. Workers

A worker is one chat completion: one prompt in, one code block out. There is no tool calling and no agent loop, so any model that can write a Python function can serve, and swapping models is a config change.

**Prompt contents**

1. The brief: the cell's strategy family and holding horizon, in two or three sentences.
2. The W profile for that cell (below).
3. The registry: one line per live and dormant approach in the same and neighboring cells.
4. The interface, the caps, the indicator library's function list and the cost model.
5. The output format: a single fenced Python block, then a one-sentence description.

**W profile**

The harness computes it; workers never see raw bars. It is identical for all workers on the same day except for the cell-specific block.

- Common block per instrument: return distribution, volatility by hour and weekday, autocorrelation of returns at lags 1 to 48, volume profile, share of bars in high and low volatility regimes.
- Cell block: statistics that fit the family. Trend cells get the persistence of moves over several horizons; mean-reversion cells get the reversal rate after large moves; breakout cells get range and follow-through statistics; and so on.
- The profile is versioned. A change to it is recorded in the trial ledger, because it changes what workers can find.

**Model pool**

- Open-weight models served by Nebius Token Factory through its OpenAI-compatible API, at least three different model families. The starting pool is gpt-oss-120b, MiniMax-M3 and Nemotron-3-Super, chosen because their makers state a training cutoff (section 17). The harness reads the provider's model list at the start of each run, since models are withdrawn without notice, and stores every response in full.
- Claude Code subagents for cells where open models fail validation more than half the time.
- Each trial records the model, its version string and its stated training cutoff.
- Models are assigned to cells in rotation, so no cell is always served by the same model.

**Failure handling**

- One retry with the validation error appended. Then the call is dropped.
- Validation failure rate per model is tracked. A model above 50% over 20 calls is removed from the pool and a health alert fires.

## 8. Diversity

Workers are steered apart before they generate, and duplicates are caught after. Both are needed: descriptions differ more easily than behavior does.

**The grid**

Six strategy families crossed with two holding horizons give 12 cells.

| Family | What it bets on |
| --- | --- |
| Trend | Moves continue |
| Mean reversion | Large moves partly reverse |
| Breakout | Leaving a range leads to follow-through |
| Volatility regime | Behavior differs between calm and turbulent periods |
| Volume | Unusual volume carries information about the next move |
| Time of day and week | Returns depend on the hour or weekday |

Horizons: short (1 to 6 hours) and medium (6 to 48 hours). Long horizons (2 to 10 days) are not in the hourly track; they run later as their own track with daily bars and longer windows (section 4).

Cross-asset approaches are deferred to v2, because they need a different function interface.

**Before generation**

- Each worker gets exactly one cell.
- The registry in the prompt lists what already exists, with the instruction to propose something absent.
- Workers run one at a time, and each sees the registry as it stands, including approaches admitted on earlier days.
- Models rotate across cells.

**After generation: the correlation gate**

- The harness computes the submission's position series on W and correlates it with every live and dormant approach.
- A correlation above 0.7 in absolute value with any existing approach rejects the submission. Strong negative correlation counts, because it is the same idea with the sign flipped.
- The worker gets one retry, told which approach it duplicated.
- A rejected duplicate is not a trial.

**The table keeps the best per cell**

Ranking is within a cell, and each cell holds at most 3 live approaches. A global top-N list would fill with variants of whatever worked last month.

## 9. Scoring, decision journal and lifecycle

The system trades on paper: it decides as if investing, records the decision, and learns from the next day's data whether the decision was good, with every fee charged. Approaches are code, so doing this for all of them every day costs nothing.

**Decision journal**

- An approach's function is committed to the repository when it is admitted. Every decision it makes afterwards is on data that did not exist when its code was frozen.
- Each day, for every live and dormant approach and every instrument, the harness appends: the target position for each new bar, the simulated fill at the next bar's open, each cost component, and the net return.
- The journal is append-only and committed to Git daily, so no entry can be revised after its outcome is known.
- Weekly, the harness recomputes a sample of past entries from stored bars. A mismatch means a bug or a revised data point, and raises a health alert.
- Decisions pass through an executor interface. In v1 the executor is the simulator; later stages replace it with the broker (section 14) and nothing upstream changes.

**Records per approach**

- Admission score: its net result on T, the 14 days before it was admitted. Used once, to decide entry. A candidate with fewer than 30 trades on T is not admitted.
- Paper record: its daily net returns from the day after admission. This is the only record used for alerts and for any claim that an approach works.
- All statistics are computed from the daily return series, not from window-by-window scores.

**Metrics**

- The function runs on every instrument in the basket. Results are pooled with equal weight per instrument.
- All net of costs: total return, Sharpe ratio, maximum drawdown, number of trades, average holding time, breakeven cost per trade, and the same Sharpe at 2x costs.

**Combined paper portfolio**

One paper account follows all live approaches with equal weight, adjusted when the live set changes. It answers whether following the system as a whole would have made money, net of costs. Equal weighting is deliberate: a smarter allocation would be one more thing that can be overfitted.

**Lifecycle**

| State | Entered when | Effect |
| --- | --- | --- |
| Candidate | Passed validation and the correlation gate | Scored on T; counted as a trial |
| Live | Admission score beats the weakest live approach in its cell over the same 14 days, or the cell has a free slot, and net Sharpe on T is positive at 1x costs | Journaled daily; in the table, the registry and the combined portfolio |
| Dormant | Displaced from its cell, or net Sharpe over its last 30 trading days of paper record is negative | Still journaled daily; listed in the registry; out of the combined portfolio; can return to live |
| Retired | Fails to run on new data, or dormant for 12 months | No longer scored; kept in the ledger |

**The table**

One row per live approach, grouped by cell: description, model, date admitted, admission score, paper record (days, net Sharpe at 1x and 2x, trades, drawdown), breakeven cost, and state history. Controls and the combined portfolio appear in the same table, marked as such.

## 10. Statistical safeguards

With enough trials, good-looking results on T are guaranteed even if nothing works. These five mechanisms are what separate a finding from luck.

**Trial ledger**

- Append-only record of every trial: date, cell, model and cutoff, code hash, profile version, cost-model version, all scores.
- The cumulative trial count feeds the alert thresholds (section 13). Nothing is ever deleted from it.

**Controls**

- Buy-and-hold per instrument.
- A standing pool of 50 random approaches, redrawn monthly: random entry times with trade counts and holding times drawn to match the live approaches. They pass through the same cost model and scoring.
- The control distribution is the baseline every claim is measured against. If live approaches as a group do not beat it on P, the system has found nothing.

**Rank persistence**

- Every 14 days, compute the rank correlation between approaches' net returns over the previous 14-day block and over the latest one, using paper records only. The blocks do not overlap, so the test stays valid even though windows slide daily.
- This is the single most important health number. Near zero means the table is reshuffling noise, and approaches falling out carry no information.

**Deflated scores**

- An approach's P Sharpe is reported alongside the Sharpe expected from the best of N random trials, where N is the cumulative trial count. Only the excess counts.

**Leakage from model training data**

- A model may have seen the market history it is asked about. Anonymization (section 4) reduces this but cannot remove it.
- Each P observation is tagged "clean" if its scoring window lies after the stated training cutoff of the model that wrote the approach, and "exposed" otherwise. An approach devised on pre-cutoff data can still earn clean evidence later. A model whose maker states no cutoff is treated as trained up to its release date.
- Alerts fire on clean evidence only. Exposed results are kept for pipeline testing and for comparison.
- A historical replay over past years is useful for shaking out the pipeline, and is not evidence. Replay over the months after a model's training cutoff is clean and does count, so the system starts with some evidence already.

## 11. Daily procedure

The system runs once a day. Three activities share that run but move on different clocks, because unseen market data is the scarce resource and each activity uses it differently.

| Clock | What happens | Cost |
| --- | --- | --- |
| Every bar | Each approach turns the latest bars into a position. In v1 the day's bars are processed in order inside the daily run | None; deterministic code |
| Every day | A day of bars enters, the windows slide, every approach's journal and paper record grow by a day, and the table, states and alerts update | None; deterministic code |
| Every day, as a trickle | One new candidate is generated, validated, ranked on T and admitted or rejected | One worker call and a short coordinator call |
| Every 14 days | The rank-persistence test on non-overlapping blocks | None |

**The daily run**

1. **Harness:** fetch the newest day of bars the vendor serves, run gap checks against the trading calendar, slide W and T by one day.
2. **Harness:** for every live and dormant approach and every control, compute the positions for each new bar, simulate fills and costs, and append to the decision journal. Update paper records, the combined portfolio, states and the table.
3. **Harness:** list the cells that are empty or have a free slot, and compute the W profile.
4. **Coordinator:** choose one cell and write its brief. It sees which cells are empty or weak and the registry descriptions. It does not see scores.
5. **Harness:** run one worker, validate, apply the correlation gate, score the candidate on T, admit or reject.
6. **Harness:** evaluate the alert rules, plus the periodic checks that fall due (rank persistence, journal recomputation, control redraw).
7. **Coordinator:** if any alert fired, write the digest (section 13). If none fired, write a one-line entry to the run log.
8. **Harness:** commit all state to the private repository and open an issue for each alert.
9. **Coordinator:** if a health alert names a code fault, open a fix on a branch with tests and report it in the digest. It never changes scoring, cost or alert code without the owner's approval.

**Budgets and stops**

- At most one new trial per day, about 250 a year. This budget is fixed: generating more candidates would not create evidence faster, and would raise the bar every finding must clear.
- A hard daily token budget for the worker and another for the coordinator. Reaching either ends generation for the day; journaling and scoring still complete.
- A run that fails is retried once. A second failure raises a health alert and leaves all state untouched. A missed day is caught up on the next run, in order.
- Every run is idempotent: re-running a day with the same inputs produces the same journal and table.

**Where it runs**

- Development and the historical replay run locally, where Claude Code is already used.
- The live daily loop runs on a small always-on cloud server, which also keeps untrusted generated code off personal machines. Plain cron starts the run. The vendor's historical data is withheld for 24 hours, so the paper record runs about one day behind the market.
- All state lives in a private Git repository: bars index, approach code, decision journal, trial ledger, table, run log and digests. A fresh Claude Code session needs nothing from a previous one.

## 12. Isolation

Worker-generated code is untrusted input and is treated like any other untrusted code. Isolation is enforced by what the sandbox contains, not by what prompts say.

**Sandbox for generated code**

- A container with no network, a read-only root filesystem, a non-root user, and CPU, memory and wall-clock limits.
- Only the bars for the window being scored are mounted, read-only. During validation on W, the T and P data do not exist inside the container.
- The container is destroyed after each run.
- The static check in section 5 runs before the container starts and rejects disallowed imports, attribute tricks, `eval`, `exec` and file or process access.

**Separation of roles**

- Workers receive text and return text. They have no tools and no access to the project directory.
- The coordinator can read the registry and cell status. Scores, the ledger and the scoring code are outside the paths it may write in an unattended run. This is enforced by running it as a separate Unix user without write access to those paths, backed by Claude Code deny rules and removal of unneeded tools (section 17). It authenticates with an API key, not a personal subscription.
- Scoring, cost and alert code change only through a reviewed commit by the owner.

**Prompt injection**

- Registry descriptions are worker-written text that later workers and the coordinator read. They are length-capped, stripped to plain text, and passed as quoted data.

**Secrets**

- API keys for the model providers and the data vendor are available to the harness process only, never inside the sandbox and never in a prompt.

## 13. Alerts and the digest

The owner hears from the system only when one of these rules fires. The rules are code in the harness, fixed before the first run, and evaluated on clean P evidence only.

**Finding alerts**

| Alert | Fires when |
| --- | --- |
| Persistent approach | An approach has at least 60 trading days of clean paper record, positive net Sharpe at 2x costs over them, and a Sharpe above the 95th percentile of the random controls over the same days |
| Group edge | The combined paper portfolio beats the control distribution over the last 120 trading days, at the 5% level |
| Rank persistence | The rank correlation between consecutive 14-day blocks, averaged over the last 12 blocks, is above zero at the 5% level |
| Revival | A dormant approach returns to live after at least 60 dormant trading days |

Thresholds tighten as the cumulative trial count grows: the control percentile for "Persistent approach" rises with the number of approaches tested, so the expected number of false alerts per year stays below one.

**Health alerts**

- Data gaps above the limit, or a day's generation skipped.
- A run failed twice, or a day was missed and caught up.
- A journal recomputation does not match the recorded entry.
- A model removed from the pool, or fewer than 5 valid candidates in 14 days.
- A token budget reached.
- A fee or spread number older than 90 days.
- No finding alert after 12 months of live running. This is itself a result and prompts a review of whether to continue.

**Digest**

One page, written by the coordinator, committed to the private repository and opened as an issue there, which sends the notification:

- Which alert fired and the numbers behind it.
- The approach's description, code, cell, model and clean or exposed status.
- Its paper record over time, next to the control distribution.
- What would falsify it over the coming weeks.

**Status dashboard**

Alerts say when something crossed a line. The dashboard shows, at any time, how far every number is from its line. The harness regenerates it on every daily run as one static page, from the same state files the alert rules read, so the two can never disagree.

| Panel | Shows |
| --- | --- |
| Gates | Every gate condition for the next stage: current value, threshold, pass or not yet, and for time-based conditions the days of clean record so far against the days required |
| Alert rules | Each finding alert's current value against its threshold, including how the threshold has tightened with the trial count |
| Combined paper portfolio | Net result at 1x and 2x costs over time, drawn against the band of the random controls |
| Rank persistence | The correlation for each 14-day block and its running average, with the zero line and the significance band |
| Table | Live and dormant approaches by cell, with their paper records |
| Experiment ledger | Trials to date, admission rate, clean and exposed counts, results by model and by cell |
| Health | Last run, data gaps, journal recomputation, worker failure rates, token spend against budget |

- The page is read-only. It displays thresholds; it cannot change them.
- Any change to a threshold or gate is a logged decision with a date, made in the repository, and the dashboard shows the history of such changes.
- It must be readable on a phone.

## 14. Build phases and the path to trading

Each phase ends with something that runs and a test that proves it. The harness comes first, because every later result depends on it being right.

| Phase | Delivers | Done when |
| --- | --- | --- |
| 0. Harness core | Data fetch and storage, trading calendar and sessions, roll detection and back-adjusted series built in the harness, measured spreads, strategy interface, backtester, cost model, executor interface with the simulator behind it | Three hand-written reference strategies give results that match an independent calculation; a deliberately lookahead-cheating strategy cannot gain from it |
| 1. Journal, controls and ledger | Decision journal, paper records, combined portfolio, random and buy-and-hold controls, trial ledger, table, lifecycle states | A historical replay of one year with controls only shows control Sharpe centered near the negative of costs, rank persistence near zero, and a journal that recomputes exactly |
| 2. Sandbox and validation | Container, static check, validation sequence, correlation gate | A suite of hostile and malformed submissions is rejected; a duplicate with flipped sign is caught |
| 3. Workers | W profile, prompt builder, model pool on Nebius, retry and failure tracking | Twenty replay days yield at least 10 valid, mutually distinct candidates across 3 model families |
| 4. Coordinator and alerts | Headless Claude Code run, brief writing, alert rules, digest, status dashboard, Git commits and issues, scheduler, budgets | Sixty unattended replay days complete with no intervention; a planted synthetic edge triggers the right alert and nothing else does |
| 5. Live daily loop | The loop on current data on the cloud server, one run a day | Runs unattended; clean paper record accumulates, starting from the replay over each model's post-cutoff months |
| 6. More tracks | Long-horizon track on daily bars; ETFs as a further universe | Same loop runs on the new track with no code change outside config |

Phase 4's planted-edge test matters most: a synthetic price series with a known, small, exploitable pattern is fed through the whole loop. If the system cannot find and flag an edge that is known to exist, its silence on real data means nothing.

**Stages toward real trading**

Phases 0 to 6 all run in stage 1. Moving to a later stage is a decision only the owner makes, against conditions written down before any results exist.

| Stage | Executor | What it proves |
| --- | --- | --- |
| 1. Simulation | The simulator with the cost model | Whether approaches hold up on unseen data, net of modeled costs |
| 2. Broker paper account | Interactive Brokers' paper account, real order routing with fake money | That the execution plumbing works, and how actual fills compare with the cost model |
| 3. Real money, capped | The live account, enabled by the owner | Whether the result survives real execution |

**Gate for stage 3 (starting values, to be set by the owner)**

- The combined paper portfolio is positive, net of 2x costs, over at least six months of clean record. Six months is a minimum; a year is more convincing, since six months can sit inside one market regime.
- It beats the random controls, and rank persistence is statistically above zero.
- Journal recomputation has shown no mismatches.
- Stage 2 fills match the cost model within a set tolerance.
- Tax treatment is confirmed with an accountant.

**Limits once live**

- A fixed capital cap and a maximum position per instrument.
- A drawdown limit that flattens all positions and returns the system to stage 1 automatically.
- Stage 1 keeps running alongside, so real results can always be compared with the simulation.
- The system never enables stage 2 or 3, raises a cap, or re-enables itself after a stop.

## 15. Open items

Only what is still undecided or unchecked. Settled questions are in section 16.

**Decisions for the owner**

- [ ] The length of T, reviewed once the phase 1 replay shows actual trade counts per window.
- [ ] The alert thresholds in section 13 (60 and 120 trading days, the 95th percentile). They are starting values, to confirm or adjust before phase 5.
- [ ] Where the status dashboard is hosted so it can be opened from a phone without exposing the repository. Needed by phase 4.
- [ ] Final review of the stage 3 gate values. Needed before stage 2 begins.
- [ ] The capital cap, maximum position per instrument and drawdown limit. Needed when stage 2 is close; only the owner sets them.

**Still to verify**

The five original checks were researched on 2026-10-11 and the findings are in section 17. These are what the research could not settle from a reliable source.

- [ ] Bid-ask spread per contract by hour of day. No source gave it. Measure it from a sample of vendor quote data before trusting any cost number; this matters most for crude oil, silver, Russell 2000 and EUR/USD overnight.
- [ ] Exchange fees for micro gold, micro crude oil and micro silver. Sources disagree by up to 40 cents a side. Take them from an actual Interactive Brokers statement or the exchange's fee file.
- [ ] The data vendor's real price and delay, checked on an account with its cost-estimate call: the per-bar price is inferred from one third-party example, and the catalog mentions delays other than 24 hours.
- [ ] Whether the worker API accepts a seed, and the exact model IDs, read from the provider's model list on a real key. Also when the existing credits expire.
- [ ] Which Interactive Brokers entity would hold an Israeli resident's account, and that it grants CME futures permission. Both are shown during the application.
- [ ] Tax treatment, with an Israeli accountant, before any live trading. The questions to ask are listed in section 17.

**Deferred to v2**

- Exploring workers with their own tool loop, run through an existing agent runtime.
- Cross-asset and portfolio-level approaches.
- Limit-order modeling.
- Weighted allocation across approaches, beyond the equal-weight paper portfolio.

## 16. Closed decisions

Each row is settled and already reflected in the sections above. Reopening one means adding a new dated row, not editing an old one.

| # | Question | Decision | Date |
| --- | --- | --- | --- |
| 1 | How workers operate | Single-shot: one prompt in, one function out, no tool loop. Open-weight models on Nebius Token Factory, with Claude Code subagents as fallback | 2026-10-10 |
| 2 | Who coordinates | Claude Code, run headlessly; the deterministic harness does everything that touches data or scores | 2026-10-10 |
| 3 | Long-horizon cells (holds of 2 to 10 days) | Not in the hourly track. The harness supports tracks from the start; a long-horizon track on daily bars is added and tested once the hourly loop is proven | 2026-10-10 |
| 4 | History passed to the strategy function | Capped at W's length in bars, about 1,500 for futures hours. The cap is a track setting | 2026-10-10 |
| 5 | Instruments and venue | The first live track is micro futures as traded through Interactive Brokers. Crypto bars are test data only. Nothing is built that will be thrown away | 2026-10-10 |
| 6 | Step length | No step. Windows slide daily, the paper record grows daily, and one candidate is generated per day. T stays a 14-day rolling window. This replaces the 14-day step chosen on 2026-10-10 | 2026-10-11 |
| 7 | What "live trading" means | Simulated decisions, journaled with all fees and costs and judged when new data arrives. Real orders come only through the staged path in section 14, enabled by the owner | 2026-10-11 |
| 8 | Data source | A data vendor with a plain API key, not the broker. The broker account is not needed until stage 2 | 2026-10-11 |
| 9 | Where it runs | Development and replay locally; the live daily loop on a small always-on cloud server | 2026-10-11 |
| 10 | State and delivery | All state in a private Git repository; each alert opens an issue there | 2026-10-11 |
| 11 | May the coordinator see scores when writing briefs | No in v1. Revisit once rank persistence is established | 2026-10-11 |
| 12 | Gate for real money | The gate conditions in section 14 are accepted as provisional and reviewed before stage 2. The money limits stay open (section 15) | 2026-10-11 |
| 13 | Status dashboard | Regenerated on every daily run, read-only, readable on a phone, showing every number against its threshold or gate | 2026-10-11 |
| 14 | Contract list | Eight micro futures: MNQ, MES, MYM, M2K, MGC, SIL, MCL and M6E. M6E is dropped if its measured spread exceeds one tick | 2026-10-11 |

## 17. Verification findings

Researched on 2026-10-11 from provider documentation and public pages. Nothing found blocks the design, and three findings changed it: the data vendor withholds the last 24 hours, most worker models state no training cutoff, and the coordinator should run on an API key. Prices and catalogs change, so each figure should be re-read before it is relied on.

**Worker models on Nebius Token Factory**

The catalog lists 24 chat models from at least six makers, with no minimum spend and a default limit around 60 requests a minute, far above this system's one call a day. Only four makers state a training cutoff.

| Model ID | Maker | USD per 1M tokens, in / out | Stated training cutoff |
| --- | --- | --- | --- |
| `openai/gpt-oss-120b` | OpenAI | 0.15 / 0.60 | June 2024 |
| `MiniMaxAI/MiniMax-M3` | MiniMax | 0.30 / 1.20 | January 2026 |
| `nvidia/nemotron-3-super-120b-a12b` | NVIDIA | 0.30 / 0.90 | February 2026 (post-training) |
| `nvidia/Nemotron-3_5-Lightning` | NVIDIA | 0.06 / 0.24 | May 2026 (post-training) |
| `deepseek-ai/DeepSeek-V4-Flash-0731` | DeepSeek | 0.14 / 0.28 | Not stated; listed July 2026 |
| `Qwen/Qwen3-235B-A22B-Instruct-2507` | Alibaba | 0.20 / 0.60 | Not stated; released July 2025 |
| `moonshotai/Kimi-K2.7-Code` | Moonshot | 0.95 / 4.00 | Not stated; listed June 2026 |
| `zai-org/GLM-5.1` | Z.ai | 1.40 / 4.40 | Not stated; listed April 2026 |

- The starting pool is the first three rows: three makers, all with stated cutoffs. The June 2024 cutoff gives more than two years of clean replay for that model's approaches; the other two give about eight months.
- A model with no stated cutoff is treated as trained up to its release date.
- The provider removed 21 models in two rounds during 2026 with no rerouting. The harness checks the model list at the start of each run and keeps a fallback per maker.
- A seed parameter is not documented, so every worker response is stored in full instead of relying on replay.
- Most of these are reasoning models and reasoning counts toward the output limit, so the limit is set generously.
- Prompts are retained by default. Zero Data Retention is an account-wide switch, and the provider's documents conflict on whether prompts train small models, so the switch is turned on.
- A batch interface exists at half price. It is not needed at this volume.

**Coordinator: Claude Code unattended**

- It runs from plain cron on the server as `claude --bare -p`, with `--output-format json`, `--max-turns`, `--max-budget-usd`, `--permission-mode dontAsk` and an explicit `--model`. Bare mode is the documented choice for scripted calls and skips project hooks, skills and connectors.
- It authenticates with an API key from the Console, billed per token. The documentation points services and automation to API keys, and its policy text describes subscription logins as for ordinary individual use. Cost is negligible: a call on the smallest current model is well under one cent.
- Anthropic's cloud-hosted scheduled tasks do not fit, because they run on a fresh clone and cannot reach the server's state.
- Hard limits, in order of strength: a separate Unix user with read-only ownership of scoring, cost, alert and ledger paths; removal of tools it does not need, including web access; `permissions.deny` rules with `Edit(//absolute/path/**)`; and the operating-system sandbox for shell commands.
- Not boundaries: rules that match shell command text, hooks, and system-prompt instructions. Network egress is limited by the host firewall, since the built-in sandbox covers shell commands only.

**Contracts and trading costs at Interactive Brokers**

All-in cost per side is commission plus exchange and regulatory fees. The round trip adds one tick of spread, which is an assumption and not a measurement.

| Contract | All-in per side, USD | Round trip, basis points | Contracts per day, Sep 2026 | In the basket |
| --- | --- | --- | --- | --- |
| Micro Nasdaq-100 (MNQ) | 0.61 | 0.28 | 2,360,000 | Yes |
| Micro S&P 500 (MES) | 0.61 | 0.63 | 1,070,000 | Yes |
| Micro Dow (MYM) | 0.61 | 0.66 | 124,000 | Yes |
| Micro gold (MGC) | 0.96 | 0.69 | 378,000 | Yes |
| Micro Russell 2000 (M2K) | 0.61 | 1.22 | 82,000 | Yes |
| Micro silver (SIL) | 1.26 | 1.23 | 58,000 | Yes |
| Micro EUR/USD (M6E) | 0.40 | 1.46 | 17,000 | Yes, marginal |
| Micro crude oil (MCL) | 0.86 | 2.96 | 240,000 | Yes |
| Micro Bitcoin (MBT) | 2.01 | 5.45 | 64,000 | No: cost and weekend hours |
| Micro 10-Year Yield and micro Treasuries | 0.56 | n/a | Under 1,500 | No: too thin |

- These costs are a small fraction of the 10 to 20 basis points estimated earlier for crypto, so far more hourly approaches can survive them.
- Four of the eight are US equity indices that move together. The basket is closer to five independent markets than eight, and statistics should not count it as eight.
- Trading runs Sunday 18:00 to Friday 17:00 New York time with a one-hour halt each day. Index contracts roll quarterly and crude oil monthly; gold and silver volume rolls about ten business days before delivery.

**Data vendor: Databento**

- Historical hourly bars are billed by usage with no subscription. Ten years for ten contracts is estimated at about 6 USD and the daily update at under 1 USD a year, against a 125 USD credit for new accounts. No exchange licence fee applies to data older than 24 hours.
- The historical interface serves only data older than 24 hours. The paper record therefore runs about one day behind the market, which does not affect stage 1. Stages 2 and 3 need a live feed: the vendor's 199 USD a month plan, or the broker's own data at 1.55 USD a month per exchange.
- Continuous contracts are stitched but not back-adjusted. The harness builds its own adjusted series by detecting each roll and applying the price gap backwards, and uses the volume-based roll rule so that metals do not hold to expiry.
- Micro contracts begin at their listing dates, May 2019 for the index micros, which bounds the historical replay.
- Hours with no trades produce no bar, so the gap check works from the trading calendar and not from a fixed bar count.

**Interactive Brokers for an Israeli resident**

- Israel is on the list of countries from which accounts can be opened. There is no Israeli entity. A site called Interactive Israel is a separate Cyprus-regulated firm, not Interactive Brokers.
- No minimum deposit or inactivity fee. Opening a futures position needs 2,000 USD in the account, and overnight margin is roughly 3,700 USD for MES, 7,000 for MNQ and 4,200 for MGC per contract.
- The paper account and the API both require an approved, funded live account. Paper fills are simulated from the top of the book and are not guaranteed to match the live market.
- Automation needs a manual login once a week and a daily restart. This affects stage 2 onward only.
- Known Israel-specific limits are on leveraged currency trading and fractional shares, not on exchange-listed futures.

**Tax background for the accountant**

This is background gathered from Israeli accounting-firm publications, not advice. No government page could be opened to confirm the figures.

- Capital gains for an individual are taxed at 25% of the real gain. Since 2025 a surtax adds up to 5% on capital income above about 721,560 ILS of annual taxable income.
- The main risk is classification. Frequent, systematic, short-holding trading can be treated as business income, taxed at marginal rates of up to about 50% plus national insurance. The Supreme Court's tests include frequency, holding period, expertise and the existence of a permanent mechanism, and an automated system meets several of them.
- A foreign broker withholds no Israeli tax, so an annual return is required, with a report and advance payment due each 31 January and 31 July.
- On the US side, a non-US person's futures gains are generally not taxed in the US.

Questions to put to the accountant:

1. Would automated intraday futures trading with own capital, alongside a salary, be capital gains or business income, and is a pre-ruling worth seeking?
2. If business income: national insurance, a self-employed file, VAT status, and whether data, server and software costs are deductible.
3. Are CME futures within the semi-annual reporting rule, and if not, what is the route?
4. How is the real gain computed for daily-settled dollar futures, and at which exchange-rate dates?
5. How losses offset other gains and carry forward.
6. Which records to keep from the broker, and the expected annual cost of filing.

**Main sources**

- [Nebius Token Factory model catalog](https://tokenfactory.nebius.com/api/public/models_info), [rate limits](https://docs.tokenfactory.nebius.com/ai-models-inference/rate-limits.md) and [terms of service](https://docs.tokenfactory.nebius.com/legal/terms-of-service)
- [Claude Code headless mode](https://code.claude.com/docs/en/headless.md), [permissions](https://code.claude.com/docs/en/permissions.md), [sandboxing](https://code.claude.com/docs/en/sandboxing.md), [authentication](https://code.claude.com/docs/en/authentication.md) and [legal and compliance](https://code.claude.com/docs/en/legal-and-compliance.md)
- [Interactive Brokers futures commissions](https://www.interactivebrokers.com/en/pricing/commissions-futures.php), [futures margin](https://www.interactivebrokers.com/en/trading/margin-futures-fops.php), [market data pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php) and [country list](https://www.interactivebrokers.com/en/accounts/open-account-country-list.php)
- [CME Group September 2026 volume](https://www.cmegroup.com/media-room/press-releases/2026/10/02/cme_group_reportsrecordaveragedailyvolumeforseptemberandq3driven.html)
- [Databento pricing](https://databento.com/pricing), [continuous contract symbology](https://databento.com/docs/standards-and-conventions/symbology) and [licensing FAQ](https://databento.com/docs/faqs/usage-pricing-and-licensing)
- [Deloitte Israel on the semi-annual report](https://www.deloitte.com/content/dam/assets-zone2/il/he/docs/services/tax/2025/152024.pdf) and [Capitax on capital versus business income](https://www.capitax.co.il/content/1/print/2059)
