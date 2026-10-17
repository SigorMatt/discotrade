# CHECKPOINT

Mission: 19 (`meta/BUILDER-19-PROMPT.md`), roadmap step S4.1. Closes no milestone. Base 031f5e4.
Container runtime: docker. Image at mission 18's tip: discotrade-sandbox:3b7d75c39621.

Done: U0 e0d19df (plan; HF-006, HF-012, HF-010 lines; HF-013, HF-014 new).
U1 27a83b9 (table: adjusted_S/E_N/excess, control_moments column, register PENDING empty, 147 (d) exposure
parameter added; G1.3 one line; three 148 (e) wrong changes red; check 3/3 1121, 1128, 1125 s; G1.3 PASS 855 s
(above 10 min: D-014 times line due at U6), G1.4 PASS 1 s; image discotrade-sandbox:3b7d75c39621).
U2 a7854da (stats: alerts.rank_rows `timing_gross`, rows gain timing and gross, stats.t_sf; daily passes the
exposure records once; four wrong changes red; check 3/3 1153, 1072, 1185 s; G1.1 PASS 424 s; 2.554 -> 2.422 s
per replay day).
U3 efc35de (alerts: persistent_approach, group_edge, bootstrap, slot_series all `adjusted`; paper.clean_members,
portfolio unchanged; five 151 (c) wrong changes red; check 3/3 1019, 1000, 997 s; finished from the tree under §R).
U4 3ee67d3 (alerts: state, firing, payloads, rank_persistence on timing, revival, ten health kinds,
few_valid_candidates, cost_stale, no_finding (not called); step 6 in daily; four 152 (g) wrong changes red; check 3/3
1069, 1058, 1055 s; G1.2 PASS 260 s, G1.3 PASS 962 s (above 10 min: D-014); 2.165 -> 2.519 s per replay day;
no new register entry, no existing test edited).

Unit in progress: U5 the dashboard (O-6, O-14, O-16, O-18; decision 153; DESIGN §15.5, §3; SPEC §13, §14).
Done means: `dashboard:` commit pushed; check 3/3; 153 (d) tests; its three wrong changes seen red; one
`stage3_money` register entry; config/gates.toml new with both owner flags false; page written on a new day only
into staging; seconds per replay day at parent and commit.

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
