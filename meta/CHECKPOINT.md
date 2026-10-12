# CHECKPOINT

Mission: 9 (`meta/BUILDER-9-PROMPT.md`), roadmap step S1.3. Closes milestone M1. Base 974b700.
Done: U0 (this commit).

Unit in progress: U1 (next) — REVIEW-8's should-fix items and decision 68 (b).
Intent: revival counts trading days (decision 66); scratch-session lookups limited per decision 67,
gethostbyaddr left alone by identity and refused again after; decision 68 (b) test through the
lifecycle functions.
Done means: tests in tests/test_lifecycle.py / tests/test_offline.py (conftest.py only if needed)
assert the U1 gate, both named wrong changes seen red, check green 3/3, one commit pushed.

Standing constraints: CLAUDE.md invariants I-1..I-15; decisions-2026-10-12 wins over DESIGN
(items 66-75 new, 1-65 still bind); no value of a frozen file changes (config/, existing entries
of tests/fixtures/config_frozen.json, existing records under tests/fixtures/config/; the gate
configuration is built under tmp with thresholds_gate.toml copied unchanged, decision 72);
config/models.toml is not created; tests write state only under tmp, read time only via
FixedClock, --as-of or the replay's clock; run `discotrade` in-process via the console-script
function (except tests of the script itself); tests running git pass GIT_ALLOW_PROTOCOL=file and
local paths only (decision 47); day-running tests on test_mixed/test_synth (gate tests on
test_synth with the gate configuration), seeds and dates in the file; each rule tested at its
production value (a lower value only on a copy under tmp, said so); test-first, or the wrong
change made and reverted in the worktree and named in the body; each unit's named wrong changes
seen to fail; existing tests unchanged in what they assert unless a cited decision changes it
(body says so); one commit per unit, files listed, never `git add -A`, push; ./scripts/check
green three times before each commit, each run its own foreground call with a 20-minute timeout
(HF-006); sub-agents in the foreground only.
