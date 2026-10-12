# CHECKPOINT

Mission: 8 (`meta/BUILDER-8-PROMPT.md`), roadmap step S1.2. Closes no milestone. Base fb1e244.
Done: U0 b06c4b2, U1 060b5e2, U2 abba5d3.

Unit in progress: U3 The ledgers and the lifecycle (decisions 22, 48, 62, 63; DESIGN §9.1, §10.2, §10.3, §16.2; I-5, I-6).
Intent: new src/discotrade/ledger.py and lifecycle.py; trial writer in state.py; lifecycle steps 1-4
in daily.py after journaling, staged with the day; journal.py drops a contract-failing approach's
rows; tests/test_ledger.py, tests/test_lifecycle.py, tests/test_daily.py additions.
Done means: committed and pushed; wrong changes (NaN Sharpe as negative in step 2, change effective
on D, lifecycle row re-appended on re-run, contract failure failing the day) seen red;
./scripts/check green 3/3.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 58-65 new, 1-57 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/);
config/models.toml is not created; no test under tests/gates/ is added; tests write state only
under tmp, read time only via FixedClock or --as-of, run `discotrade` in-process via the
console-script function (except tests of the script itself); tests running git pass
GIT_ALLOW_PROTOCOL=file and local paths only (decision 47); journal/paper/control/lifecycle tests
on synthetic sources from tests/fixtures/config/ (test_mixed, test_synth), seeds in the file;
each rule tested at its production value from config/thresholds.toml (a lower value only on a
copy under tmp, said so); test-first, or where code is already right the wrong change is made and
reverted in the worktree and named in the body; each unit's named wrong changes seen to fail;
existing tests unchanged in what they assert unless a cited decision changes it (body says so);
one commit per unit, files listed, never `git add -A`, push; ./scripts/check green three times
before each commit (foreground, timeout >= 20 min, HF-006); sub-agents in the foreground only.
