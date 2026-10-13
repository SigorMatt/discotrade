# PLAN — mission 9 (roadmap step S1.3)

Base commit: 974b700 (`plan: mission 9 kit (S1.3, table, portfolio, replay, M1 gate)`).
Brief: `meta/BUILDER-9-PROMPT.md`. Decisions: `meta/decisions/decisions-2026-10-12.md` (items 66-75 new; 1-65 still bind).
Roadmap step: S1.3 (as decisions 66-75 cut it). This mission closes milestone M1 and adds the gate tests G1.1-G1.4 under `tests/gates/`.

Carried items:
- REVIEW-8 should-fix 1: revival must count trading days of the track, not calendar days (decision 66). — taken by U1
- REVIEW-8 should-fix 2: the scratch session's `network`-marked test may call for real only the lookups decision 67 lists; `gethostbyaddr` left alone by identity (decision 67). — taken by U1
- BACKLOG (REVIEW-1 should-fix U6): `bars fetch` and synthetic regeneration performance (decisions 4, 5, 18, 31, 35). — taken by U3
- BACKLOG (REVIEW-2 note U1): `recover` reads and hashes only files that can be an interrupted append (decision 5). — taken by U3

- [x] U0 Plan (`plan:` commit): this file, `meta/CHECKPOINT.md`, `meta/journal.md`. — 3c0b023
- [x] U1 REVIEW-8's should-fix items and decision 68 (b) (decisions 63, 66, 67, 68; I-11; DESIGN §10.3, §18.1). — 94e1294
- [x] U2 The replay command (decisions 19, 51, 55, 72; DESIGN §16.4, §16.1, §3; I-6, I-12). — 15754e9 (finding D-007: daily.py refusal changed for decision 72)
- [x] U3 The two performance items (BACKLOG; DESIGN §5.2, §5.5, §16.1 step 1, §18.2; decisions 4, 5, 18, 31, 35). — d65964f
- [x] U4 The combined portfolio and rank persistence in the day loop (decisions 59, 62, 63, 69, 70; DESIGN §9.3, §10.5, §11.1, §16.1 steps 2 and 6). — 04aee87
- [x] U5 The table (decisions 25, 30, 41, 60, 62, 71; DESIGN §10.4, §8, §11.2). — 33cfe7a
- [x] U6 Scripted candidates in the replay (decisions 48, 63, 73; DESIGN §10.2, §10.3, §16.1 step 5). — 984cc0c
- [ ] U7 The M1 gate tests (decisions 9, 59, 60, 69-74; DESIGN §18.2, §18.3 M1), then `./scripts/gate M1` and `./scripts/gate M0` at the pushed tip. — tests ae7158b, findings 6163568; stopped on D-008 and D-009, answered by owner decisions O-1 and O-2 (5acec56); resumed under them
- [ ] U8 Final report (`meta/FINAL-REPORT-9.md`).
