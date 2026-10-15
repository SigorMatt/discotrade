# CHECKPOINT

Mission: 14 (`meta/BUILDER-14-PROMPT.md`), roadmap step S3.1. Does not close a milestone. Base 1267318.
Container runtime: docker (mission 13: server Engine 29.1.3, API 1.52). Image at base: discotrade-sandbox:1edd0f8558cb.

Done: U0 53401fd (plan, findings D-014, D-015, HF-010, HF-011, D-013 status).
U1 ad53fad (mount vs store, last_close, zero remaining time, float in catch-all, builtins tuple, removal ends client,
notice only on a written day; image discotrade-sandbox:3b7d75c39621; check 3/3 890-912 s).

U2 a0ba5e8 (shared states, trusted_hashes cache; check 841-891 s, target 12 min missed, under D-013).

Unit in progress: U3 the W profile p1 (decision 115). Intent: src/discotrade/workers/{__init__,profile}.py and
tests/test_workers_profile.py per 115 (a)-(e). Done means: the unit's gate met, seen-to-fail changes named, check
3/3 green, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-15-m14 (109-117) bind; the owner's
decisions-2026-10-15-owner (O-19, O-20, O-22) and decisions-2026-10-13-owner (O-16..O-18 bind every new module) win;
decisions 1-108 still bind. No value of a frozen file changes (config/instruments, tracks, calendars, thresholds.toml,
config/run.toml, tests/fixtures/config/run.toml, existing entries of tests/fixtures/config_frozen.json, existing
records under tests/fixtures/config/); config/models.toml is not created; no file under tests/gates/ or
tests/fixtures/rejected/ changes (O-19); nothing of this mission is called from run-day or replay (109 (a)); modules
under src/discotrade/workers/ import nothing reaching the network or a secret; no test calls a provider or model.
The image is built only by `discotrade sandbox build` as a setup step; container tests carry the `container`
marker, mount only a job dir under tmp, leave no container. Tests write state/job dirs only under tmp, read time
only via FixedClock, --as-of or the replay's clock; run `discotrade` in-process; git tests pass
GIT_ALLOW_PROTOCOL=file, local paths; new subprocess files go in SUBPROCESS_FILES; bars on test_mixed/test_synth,
seeds and dates in the file; each rule at its production value; a figure checked by the test's own computation
from stored bars. Test-first, or the wrong change made and reverted in the worktree and named in the body; the
"seen to fail" changes of each unit made and reverted and named. Existing tests unchanged in what they assert
unless a cited decision changes it (body says so); U2 changes no assertion. One commit per unit, files listed,
never `git add -A`, push. ./scripts/check green three times before each commit, each its own foreground call
with a 20-minute timeout (HF-006); a unit adding >60 s says so; a run >15 min is a finding. Sub-agents in the
foreground only.
