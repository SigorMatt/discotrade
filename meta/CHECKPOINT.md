# CHECKPOINT

Mission: 19 (`meta/BUILDER-19-PROMPT.md`), roadmap step S4.1. Closes no milestone. Base 031f5e4.
Container runtime: docker. Image at mission 18's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 e0d19df (plan; HF-006, HF-012, HF-010 lines; HF-013, HF-014 new).

Unit in progress: U1 `control_moments`'s column, the register, the table's adjusted deflated figures (O-23,
O-24; decisions 147, 148). Done means: `table:` commit pushed; check 3/3 green; decision 147 (a) default/named
column test, 148 (e) figure tests; 148 (e)'s three wrong changes seen red; register PENDING empty; G1.3 one line;
`./scripts/gate M1 G1.3` and `G1.4` PASS at the commit, outputs and times in the body.

Standing constraints: CLAUDE.md invariants I-1..I-15; owner files O-23 to O-25 win, then decisions 146-154, then
1-145 where not replaced. Add, never replace (O-25): every function a met gate reads keeps its result for today's
inputs. No file under tests/fixtures/rejected/, no record under tests/fixtures/config/, no entry of
tests/fixtures/config_frozen.json, no value of a frozen config file changes; config/gates.toml (U5) is the one new
config file. Under tests/gates/ only decision 148 (d)'s one line in test_g1_3_lifecycle.py (U1). A met-gate test
failing because of what a unit adds: the unit stops, files a finding, builder replies VERDICT: question (146 (b)).
Every new/changed return reader registered in tests/fixtures/return_readers.toml in the same commit (O-18). Tests
write state/job dirs only under tmp, read time only via --as-of or the replay's clock, run `discotrade` in-process,
compute expected figures themselves, read config/thresholds.toml through the loader (production values); no
network, secret, real model or claude binary; no test builds the image. Wrong changes made one at a time, seen red,
reverted, named in the body. Each sub-agent runs `discotrade sandbox build` first, then ./scripts/check three
times, each its own foreground call with a 20-minute timeout (HF-006); a run past the cap is waited for and
recorded (145). Day-loop units (U2, U4, U5) give seconds per replay day of the G1.3 scenario's first 30 calendar
days at parent and commit (154 (c)). One commit per unit, files listed, never `git add -A`, push. Sub-agents in the
foreground only.
