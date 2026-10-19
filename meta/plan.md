# PLAN — mission 21 (roadmap step S4.2a)

Base commit: e477f67 (`plan: mission 21 kit (S4.2a, closes REVIEW-20 blocker and should-fix)`).
Brief: `meta/BUILDER-21-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-19-m21.md` (items 168-176 new); owner `meta/decisions/2026-10-18-owner.md` (O-26, O-27); `meta/decisions/decisions-2026-10-18-m20.md` (155-167; 155, 156, 157 (c), 160, 163, 164, 166); owner `meta/decisions/2026-10-17-owner.md` (O-25); `meta/decisions/decisions-2026-10-17-m19.md` (146-154; 146 (b), (c), 151 (a), 152 (a), 153); owner `meta/decisions/decisions-2026-10-13-owner.md` (O-18); `meta/decisions/decisions-2026-10-17-m18.md` (145); `meta/decisions/decisions-2026-10-16-m17.md` (137, 140); `meta/decisions/decisions-2026-10-12.md` (1-75 still bind; 72).
Roadmap step: S4.2a. Mission 21 closes REVIEW-20's items (blocker 1, should-fix 1 to 4).

This mission closes no milestone. It moves no gate of M4.

Regression gates (decision 168 (a); O-25), taken by U5: at the pushed tip after U4, with nothing uncommitted but the git-ignored drafts, each its own foreground call with a 20-minute timeout: `discotrade sandbox build`; gate M1 item by item (`./scripts/gate M1 G1.1`, `G1.2`, `G1.3`, `G1.4`); then `./scripts/gate M3`, `./scripts/gate M2`, `./scripts/gate M0`; then decision 170's three measurements (median ratio at most 1.25). Each must pass unchanged. Under O-27 item 3, an M1 item above 15 minutes of wall time stops the mission (finding, then `VERDICT: question`). No file under `tests/gates/` changes in this mission (decision 168 (b)).

Carried items:
- REVIEW-20 blocker 1, finding D-022: `persistent_approach`'s `N` and `p_N` in the alert state, the page reads them (decision 169). — taken by U1
- REVIEW-20 should-fix 1: the binding ratio is the median of three complete measurements (decision 170). — taken by U1 and U5
- REVIEW-20 should-fix 2: the unknown-coordinator test, the secret-free test environment (decision 171). — taken by U2
- REVIEW-20 should-fix 3 and note 5: the fix session's `--tools` and whole-tool deny rules; the protected paths extended (decision 172). — taken by U3
- REVIEW-20 should-fix 4: `gaps._MONTH_MISSING`'s content identity pinned (decision 173). — taken by U4
- REVIEW-20 note 6: the literal `"p"` replaced by `RANK_P` (decision 169 (e)), U1; the speed day's bookkeeping (decision 170 (d)), stands.
- REVIEW-20 notes 1 and 8 to 10: D-013 times, HF-015, HF-012, HF-010 lines (decision 175 (b)). — taken by U0
- The corrections of `meta/FINAL-REPORT-20.md` (decision 174). — taken by U6

Left items:
- findings D-019, D-020 and D-021 — the owner (`meta/BACKLOG.md`; decision 175 (a));
- the digest, the issue sinks, the full daily run, the `no_finding` call, the live defaults of `run-day`, REVIEW-17 notes 3 to 5 and REVIEW-19 notes 4 and 6 — step S4.2b;
- G4.4 and G4.5 as gate tests — step S4.3.

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`, `meta/findings/FINDINGS.md` (D-022 and its status; HF-015, HF-012, HF-010 lines; D-013 times line; decision 175 (b)).
- [x] U1 `persistent_approach`'s `N` and `p(N)` from the alert state (REVIEW-20 blocker 1, D-022; decisions 169, 170; DESIGN §15.1, §15.3, §15.5, §11.4). `alerts:` commit. G1.3 and decision 170's three measurements at the commit. — 558e02a (G1.3 PASS 462 s; median ratio 1.116; check 976, 981, 995 s)
- [x] U2 The unknown-coordinator test and a secret-free test environment (REVIEW-20 should-fix 2; decision 171; DESIGN §14.2, §19.3 L4). `tests:` commit. — 943a18c (check 987, 997, 985 s)
- [x] U3 The fix session's tools and the protected paths (REVIEW-20 should-fix 3, note 5; decision 172; DESIGN §14.4). `coordinator:` commit. — 50341fc (check 994, 990, 994 s)
- [x] U4 `gaps._MONTH_MISSING`'s content identity (REVIEW-20 should-fix 4; decision 173; DESIGN §5.4). `tests:` commit. — d679adc (check 986, 978, 997 s)
- [x] U5 The regression gates at the pushed tip (O-2, O-25, O-27; decisions 168 (a), 170; DESIGN §18.2). `meta:` commit (one D-013 times line). — 2affd42 (all gates PASS at c36df23; G1.3 462 s; median ratio 1.170; check 987, 974, 989 s)
- [ ] U6 The final report (decisions 168-176; O-26, O-27; DESIGN §18.2). `meta/FINAL-REPORT-21.md`.
