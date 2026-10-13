# CHECKPOINT

Mission: 9 (`meta/BUILDER-9-PROMPT.md`), roadmap step S1.3. Closes milestone M1. Base 974b700.
Done: U0 3c0b023, U1 94e1294, U2 15754e9 (D-007 filed), U3 d65964f, U4 04aee87, U5 33cfe7a, U6 984cc0c. U7 tests ae7158b, findings D-008/D-009 6163568.
Carried risk: U3 measured 2.480 s per replay day (3.702 before) over the first 20 days of a
controls-only test_synth replay on the gate configuration, a lower bound: ~37 min for M1's ~900
days against DESIGN §18.2's 15 minutes. Handled at U7 as the brief says (finding with Unit in progress: U7, resumed under owner decisions O-1 and O-2
(meta/decisions/decisions-2026-10-13-owner.md, 5acec56), which answer D-008 and D-009.
Intent: (a) stats.py's rank-persistence function takes the paper column as a parameter, default
net_1x, with a unit test; production callers unchanged; (b) G1.1's rank-persistence clause reads
the random slots' summed `gross`, and the test reports the net statistic's mean and standard error
and asserts nothing about it; every other G1.1 assertion stands; (c) gate M1 run item by item
(O-2): `./scripts/gate M1 G1.1`..`G1.4`, each its own foreground 20-minute call at one pushed
commit, PASS when all four print PASS; then `./scripts/gate M0` once. Nothing of O-3..O-18 is built
in mission 9 (O-10).
Done means: one commit pushed with check green 3/3; the four item outputs and gate M0's kept
verbatim under meta/drafts/ with wall times.
Earlier measurement: G1.1 876-888 s, G1.2 287-329 s, G1.3 1058-1069 s, G1.4 1 s; gate M0 PASS 340 s.

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
