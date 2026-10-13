# CHECKPOINT

Mission: 9 (`meta/BUILDER-9-PROMPT.md`), roadmap step S1.3. Closes milestone M1. Base 974b700.
Done: U0 3c0b023, U1 94e1294, U2 15754e9 (D-007 filed), U3 d65964f, U4 04aee87, U5 33cfe7a,
U6 984cc0c, U7 ae7158b + 6163568 (D-008, D-009) + b62f5f0 (under owner O-1, O-2).
Gate M1 at b62f5f0, item by item (O-2): G1.1 PASS 892 s, G1.2 PASS 324 s, G1.3 PASS 1083 s,
G1.4 PASS 1 s. Gate M0 PASS 342 s.

Unit in progress: U8 (next) — final report meta/FINAL-REPORT-9.md (drafted under meta/drafts/).
Done means: check green 3/3 at the tip, the report committed and pushed with the verdict line.

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
