# Decisions — 2026-10-15 (owner, written by the phone architect)

Rulings the owner took on 2026-10-15 at the architect role's escalation of
2026-10-15 02:11 (`shape`: gate G2.1's suite cannot be written by any agent
in this series). This file wins over `DESIGN.md` (§12.5, §18.3 G2.1) and
over any earlier decision it names (role decisions 2026-10-14-m13 items
104, 105 (e) and 106 (b); `tests/gates/test_g1_3_lifecycle.py`'s expected
texts). Items continue the owner numbering from O-18 of
`decisions-2026-10-13-owner.md`. This file replaces two earlier drafts of the
same name that were never committed; O-21 of the first is withdrawn and its
number is not reused. It also changes `scripts/gate` (M2 counts five items)
and adds gate item G2.5 to DESIGN §18.3.

Findings closed: D-011 (O-19), D-012 (O-20); the U4 block of mission 13,
recorded in `meta/plan.md` and `meta/CHECKPOINT.md` (O-22).
Reviewed twice by the owner's reviewer before issue; this is the third form.

Branch state when written: `main` at eff2dff, mission 13 at U5 done, U4
blocked, U6 and U7 not started, no `meta/reviews/REVIEW-13.md`.

## O-19. D-011: gate G1.3's expected retire reasons become the sandbox's text

Decision 105 (c) is right: an approach retired for a contract failure
carries `failure: <the error text>`, where the text is the sandbox's
(decision 101 (a): no returned value, no date, no symbol). Gate item G1.3
asserted the reason the retired in-process loader wrote; that assertion
changes to the new text. This is a change to a met milestone's gate
(`meta/ARCHITECT.md` §1), approved here, of wording only: G1.3 still
asserts retirement on failure as a lifecycle row at the same date for the
same two approaches, as an exact literal.

- In `tests/gates/test_g1_3_lifecycle.py`, the two reasons of 2019-06-13
  become the exact texts U5 measured, as literals written in the test:
  `failure: dry_run [out_of_range]: position returned a number outside
  [-1, 1] at window bar 18 (parameter set 0)` for the first approach and
  the same with `bar 19` for the second. Nothing else in the file changes;
  the commit body quotes this item.
- For the future: a gate test of a met milestone changes only by an owner
  decision naming the test and the assertion, and never in what it
  proves. A role decision that changes a text a gate asserts is not
  complete until the owner has ruled on the gate; the role escalates
  `shape` before building it.

## O-20. D-012: one fork server per process; O-3's target stands

Decision 105 (e)'s "one process per run of the day loop" becomes "one
process per harness process": the subprocess backend's fork server is
started on its first job, lives for the whole `replay`, `run-day`, `journal
recompute` or test process, and is stopped when that process ends (and by
the backend's close, which tests call). Everything else of 105 (e) stands:
the server imports only the runner's modules, never runs a text, forks one
fresh child per job with the limits set in the child, and a child is never
reused. A server that has died is started again on the next job, with a
health notice in a run. Nothing else is done for speed: approaches are
never run in the harness's own process again.

O-3's target (each item of gate M1 under 10 minutes on the builder's
machine) stands and is measured at U6. If G1.3 is still above 10 minutes
with one server per process, that is a finding with the times, and the
gate is run as it is; nothing is weakened. `./scripts/check` keeps HF-006's
rule (one foreground call per run, 20-minute timeout); a run above 15
minutes is a finding, as the brief already says.

## O-22. Gate G2.1 narrows to the rejection suite; the limits get their own item

Decision 104 and DESIGN §12.5 asked for one text per entry of a list, a
rejection pass over all of them (104 (b)) and a containment pass over the
run-time ones (104 (c)). No agent of this series will write the texts the
containment pass needs, and the owner has decided they are not needed:
what the boundary must hold is proven by inspection from inside the
container (G2.3) and by trusted, bounded fixtures on the container backend
(G2.5, new), both ordinary tests of the kind missions 12 and 13 wrote
without trouble. G2.1 proves the static check and the contract outcomes,
and nothing else.

1. **The suite.** `tests/fixtures/rejected/` (the name `hostile` is
   retired everywhere, DESIGN §12.5's title included) holds one text per
   entry of §12.5's list plus REVIEW-12's two, and `manifest.toml` with
   the fields of 104 (a): file, the entry covered, the stage that rejects
   it, and for the static stage the rule. No `containment` field.
   - For an entry the static check rejects, the text is the smallest text
     that trips the rule: the construct, and otherwise a function that
     returns 0. It performs no operation; it is refused before it runs.
   - For an entry that a run-time stage rejects (`dry_run`, `determinism`,
     `activity`), the text is one that already exists under
     `tests/fixtures/strategies/` where one does, copied by path with its
     manifest entry pointing at the copy, or else the smallest text whose
     result the stage refuses (a value that is not a number, not finite or
     out of range; a text that is flat).
   - Decision 104 (c), the containment pass, is dropped. Decision 104 (d)
     stands: the subprocess backend leaves `tests/fixtures/rejected/` out
     of the sources it accepts, and a test shows it refusing one.

2. **G2.1.** The rejection pass of 104 (b) over the whole manifest against
   §12.5's literal list, on the container backend, with the state
   directory, `HEAD`, the ledgers, the sentinel tree and the container
   count checked as 104 (b) says, and a valid fixture still passing
   afterwards. An entry whose text is not rejected at its manifest stage
   is attributed before anything is changed:
   - a static-stage entry that reaches a later stage is a missing static
     rule, added with its test (§12.1, 104 (d));
   - a run-time-stage entry that reaches a later stage is a defect in that
     stage or in the backend's limits, fixed there with a test that goes
     red on the fix's revert, before the gate is run again. A static rule
     may be added as well; it does not close the item.
   G2.2 to G2.4 and decision 106 are unchanged except that 106 (b) now
   reads this item and 106 (a) covers G2.5.

3. **G2.3 extended: the limits by inspection.** The probe already reports
   network, root file system, user and mount from inside the container.
   It also reports the limits the runtime set, read from inside (the
   container's cgroup values for process count, memory and CPU, and the
   CPU-time resource limit of the probe's own process) and the gate
   compares each with the value `run.toml` and decision 102 (b) require;
   a limit missing or wider than required fails the item. The probe
   attempts nothing against a limit. `discotrade sandbox selftest` and
   `doctor --live sandbox` (L5) report the same findings.

4. **G2.5, new: the limits by trusted fixtures on the container backend.**
   Trusted fixtures under `tests/fixtures/strategies/` (mission 12's where
   they fit, else new ones written by the builder, each bounded by a value
   in its text), run through the container backend with a `run.toml`
   copied under the temporary directory holding short limits, said so:
   - wall clock: a text that waits longer than the short wall limit ends
     with the backend's `limit` error naming `wall_clock`, within the limit
     plus the kill grace, and no container remains;
   - output cap: a text whose output exceeds the short cap ends with the
     `limit` error for output, and the result read is no longer than the
     cap;
   - memory: a text that allocates a fixed amount above the short memory
     limit ends with a `limit` or `dry_run` error, never a harness failure,
     and the harness process's own memory is unchanged.
   Process count and CPU are proven by G2.3's inspection, not by attempt;
   the item records that choice. Each test also runs its fixture under the
   production limits and shows it passing or failing as its comment says,
   so the short limits are what the test exercises. `scripts/gate` counts
   five items for M2.

5. **What stands as the boundary's proof.** G2.3 as extended, G2.5, and
   live check L5 on the server. The reviewer judges M2 on G2.1 to G2.5.

6. **Who writes it.** The builder, by a sub-agent, as any unit. The unit
   text describes each suite file as a validation fixture for the stage and
   rule its manifest entry names, and each G2.5 fixture as a test of one
   configured limit, which is what they are.

## For the builder

You start fresh. Read this section only, then act in this order.

1. Confirm the working tree is clean and at `origin/main` (`git status`,
   `git fetch`, `git log --oneline -1 origin/main`). If `meta/CHECKPOINT.md`
   names a unit in progress with a dirty tree, apply the brief's §R first.
2. Copy `~/Downloads/decisions-2026-10-15-owner.md` unchanged to
   `meta/decisions/decisions-2026-10-15-owner.md`. Commit it alone as
   `plan: decisions 2026-10-15 (owner)` and push. The reviewer does not
   count this commit as a forbidden edit.
3. In `meta/findings/FINDINGS.md`, append one line to D-011: `Status:
   decided meta/decisions/decisions-2026-10-15-owner.md (O-19)`; one to
   D-012: `Status: decided meta/decisions/decisions-2026-10-15-owner.md
   (O-20)`. Under "hands findings", add `HF-009`: the plan assumed a
   sub-agent writes whatever a unit asks; for the texts of decision 104 a
   safety classifier stopped two sub-agents and the phone architect, and
   no escalation condition anticipated it; resolved by O-22; status open
   for the hands Project. In `meta/plan.md`, change U4's line from blocked
   to open with `unblocked under O-22 (decisions-2026-10-15-owner.md): the
   rejection suite under tests/fixtures/rejected/, no containment pass;
   G2.3 extended and G2.5 added`, remove the blocked mark from U6, add unit
   U5b of step 5 between U5 and U6, and add this file to the plan's
   decisions line. Rewrite `meta/CHECKPOINT.md` for U4 in progress. Append
   one line to `meta/journal.md`. Commit as `meta: mission 13 resumed under
   decisions-2026-10-15-owner, U4 open` and push.
4. **U4**, as O-22 items 1 and 2 say: `tests/fixtures/rejected/` with its
   texts and `manifest.toml`; the exclusion in
   `src/discotrade/sandbox/process.py`; `tests/test_rejected_suite.py`
   with the rejection pass of 104 (b) over the manifest and the literal
   list of §12.5 plus REVIEW-12's two, attributing any miss as item 2
   says; any static rule a static-stage miss shows missing, with its test;
   the brief's seen-to-fail change that still applies (a static rule the
   suite relies on removed; the container-without-process-limit change
   moves to U5c). The sub-agent's unit text describes each file as a
   validation fixture for its stage and rule.
5. **U5b**, under O-20: the fork server lives for the whole harness
   process; tests that a second day of a replay starts no new server and
   that a job after a dead server gets a fresh one; the seconds per replay
   day of the G1.3 scenario's first 30 calendar days at the unit's parent
   and commit (decision 80 (d)'s method) in the body.
6. **U5c**, under O-22 items 3 and 4: the probe's limit findings
   (container.py's probe source and `judge`, `sandbox selftest`, `doctor
   --live sandbox`), the G2.5 fixtures and their tests marked `container`,
   and `scripts/gate` counting five items for M2. Seen to fail: the
   container started without its process limit (G2.3's inspection goes
   red); the short wall limit not enforced by the harness (G2.5 goes red).
7. **U6**, as the brief says, with two changes: first its own commit
   changing the two expected reasons of `tests/gates/test_g1_3_lifecycle.py`
   as O-19 says, the body quoting O-19; then the gate tests of M2 with
   G2.1, G2.3 and G2.5 as O-22 states them, and the gate runs of decision
   106 (f): `discotrade sandbox build` (tag printed), `./scripts/gate M2`
   in one foreground call with a 20-minute timeout, then gate M1 item by
   item (`./scripts/gate M1 G1.1` to `G1.4`, each its own 20-minute call)
   and `./scripts/gate M0` once, every output verbatim with its wall time.
8. **U7**, the final report `meta/FINAL-REPORT-13.md`, as the brief says,
   naming O-19, O-20 and O-22 under the decisions applied and stating that
   decision 104 (c) was dropped by O-22 and what proves the boundary
   instead (O-22 item 5), with G2.3's limit findings and G2.5's results
   quoted.
9. End your reply with one of the brief's lines: `VERDICT: mission 13
   finished`, or `VERDICT: mission 13 blocked <unit>`, or `VERDICT:
   question <one line>`.
