# REVIEW-PROTOCOL — cold review of a discotrade mission

You are the aux session. You start with no context of the mission you are
reviewing; that is the point. The prompt names the mission number N;
everything else you learn from disk. The base of the review is the last
`review:` commit on the branch (`git log --oneline --grep='^review: ' -1`),
or the mission's kit commit if no review exists yet (the latest commit that
added `meta/BUILDER-N-PROMPT.md`). Never take the base from a job: a job
that resumed a mission starts mid-mission.

Read, in this order: `CLAUDE.md`; `meta/BUILDER-N-PROMPT.md`; the
`DESIGN.md` sections that brief names, and always §2 (the invariants) and
§18; every file under `meta/decisions/` the brief names;
`meta/FINAL-REPORT-N.md`; `meta/findings/FINDINGS.md`; then
`git log --oneline <base>..origin/main`.

You never use a secret, a real model or a background task, you never run
anything marked `network` or `live`, and the only thing you let touch the
network is `uv sync` installing the locked dependencies.

## Per unit commit

Dispatch ONE sub-agent per unit commit, in the foreground. A unit commit
is one that changes product code, tests, config or scripts; skip `plan:`,
`meta:` and `review:` commits, which you read yourself for forbidden
edits only. Each sub-agent, in a `git worktree` at that commit:

1. Names the unit and the DESIGN sections it claims to implement.
2. Confirms test-first: the commit adds or changes tests that exercise the
   claimed behaviour, and those tests fail when the product change is
   reverted in the worktree: put the non-test files the commit changed
   back to their parent version (`git checkout <sha>~1 -- <files>`; remove
   the ones the commit added), run the tests the commit added or changed,
   expect red, then restore the commit's tree (`git checkout <sha> -- .`).
3. Runs `./scripts/check` at that commit; records green or red verbatim.
4. Checks design conformance against the named sections, and the
   invariants of DESIGN §2 that the unit touches. In particular: no test
   reaches the network or reads a secret (I-11); no file under `src/`
   names a market (I-9); no number that an alert, a score or a gate uses is
   written outside `config/` (I-10); nothing reads the wall clock where a
   result depends on it (I-12); no state is written inside the repository
   (I-14); no new dependency without a finding.
5. Checks that nothing forbidden was touched: the files `CLAUDE.md` lists
   as never edited by builders; `meta/plan.md` or `meta/CHECKPOINT.md` by a
   sub-agent commit; and any value in the frozen config of DESIGN §4.3
   that existed before this mission (`git diff <base> -- config/`), unless
   the brief names the decisions file that approves it and the history
   entry is there. A changed frozen value without both is a blocker.
6. Reports in at most 12 lines: sha, verdict per point, anything NOT
   proven.

## The gate

When the brief says `This mission closes milestone <M>`, you run the gate
yourself at the branch tip, in the foreground with a timeout:

    ./scripts/gate <M>

and record its output verbatim. Then you read the gate tests under
`tests/gates/` against the items of DESIGN §18.3 for that milestone, one by
one. The gate fails when the command does not print `gate <M>: PASS`, when
an item of §18.3 has no test, when a test asserts less than its item says
(a looser tolerance, a smaller sample, a skipped case, a stand-in where the
item says the real thing), or when a gate test was made to pass by a
special case in product code. A failed gate is blocker number 1, and its
text begins exactly `GATE <M> FAILED:` followed by the items that failed
and why.

When the brief does not close a milestone, the `## Gate` section says
`not a closing mission`.

## The review file

Read `meta/FINAL-REPORT-N.md` §NOT PROVEN against what the sub-agents
found, then write `meta/reviews/REVIEW-N.md` with exactly these sections,
in this order:

- `## Gate` — `Gate <M>: PASS` or `Gate <M>: FAIL` with the command's
  output and your item-by-item reading, or `not a closing mission`.
- `## Blockers` — numbered. A blocker is a failed gate, a failed
  `./scripts/check`, a missing test, a broken invariant, a design
  violation, or a claim the disk contradicts. A claim that overreaches is a
  blocker even when the code is right. When a blocker is a question the
  design does not answer, say so in its first words: `DESIGN QUESTION:`.
- `## Should-fix` — numbered.
- `## Notes` — including anything you noticed about hands itself (its
  hooks, its prompts, its protocol), marked `hands:`; you do not fix it.
- `## Per-commit verdicts` — the sub-agents' reports, verbatim.

You may commit that one file only, as `review: mission N`, and push. Touch
nothing else.

Your reply's first line is exactly:

    VERDICT: review mission N blockers=<k> should-fix=<m>

followed by the Blockers and Should-fix sections verbatim.
