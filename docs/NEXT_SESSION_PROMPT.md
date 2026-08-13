# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Objective

Finish REPAIR-007, the remaining PILOT-007 completion-record repair. Do not
start PILOT-008 or PRECISION-002 in this session. Use the normal workflow:
develop, test, update docs, inspect the diff, commit, push, and verify CI.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md, especially the regression-test evidence requirements
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/PILOT_007_PLAN.md, especially "REPAIR-007 follow-up"
- docs/research/PILOT_007_EVALUATION.md
- docs/PILOT_008_PLAN.md (blocked follow-up boundary)
- docs/PRECISION_002_PLAN.md (blocked follow-up boundary)
- this handoff

Treat current command output as authoritative for mutable Git and CI state.

Known project state

- Release: 1.1.1. M0 through M8 and PRECISION-001 are complete.
- PILOT-007 is UNSATISFIED because the pinned Silo 4.26.0 source does not map
  to the deployed in-scope Silo 3.5.0 assets. Silo remains a private,
  non-bounty research corpus.
- The untouched scanner at selection commit
  08050a14437abaf47ff45b90a1392a9fbc460a93 has a reproducible RecursionError
  on the full Silo closure. The 81-candidate scan is a separate post-repair
  operational result, not an untouched baseline.
- All 81 private review records are complete and operator-confirmed rejected.
- The two new regression tests are genuine: substituting either pre-fix
  implementation makes its matching test fail. Their assertions still need to
  satisfy CONTRIBUTING.md by checking stable public path, line, kind, and
  evidence where a finding is retained.
- Suite at handoff: 221 tests. Frozen evaluation gates: 1.0 precision and
  recall on the synthetic audit corpus; 0.875 candidate precision and 1.0
  supported-class recall on the historical corpus.
- Correct post-repair scan digest:
  9784d71e91ae86d4380c738badb2c1dfcfa9d9871425064c814b4237183825e6.

Preserve these private artifacts unchanged

- ../targets/silo-contracts-v3-4.26.0
- ../bounty-workspaces/silo-contracts-v3-4.26.0
- ../bounty-workspaces/silo-contracts-v3-4.26.0-replay
- ../bounty-workspaces/silo-contracts-v3-4.26.0-baseline-a
- ../bounty-workspaces/silo-contracts-v3-4.26.0-baseline-b
- ../bounty-workspaces/silo-minimal-checkout
- ../bounty-workspaces/silo-minimal-verify
- all OpenZeppelin trial evidence

Keep target source, candidate IDs, source paths, excerpts, traces, review notes,
credentials, and generated private artifacts out of the repository and Git
output.

Required work

1. Verify the worktree, main versus origin/main, current project CI, the full
   test suite, both frozen evaluations, and the recorded private-artifact
   permissions and hashes. Do not rewrite existing evidence.

2. Fix the minimal-checkout reproduction in new private paths. Build a new
   scanner-compatible Git checkout from the existing local Git objects, with
   only the three submodules that intersect the frozen 124-file compiler
   closure. Do not use the network. Retain usable Git metadata, then make the
   entire checkout, including Git metadata, user-read-only under a private
   parent. Create a new private verification workspace that points at it.

3. Through the public bounty CLI, validate the new profile and reproduce the
   source manifest and compiler-enabled scan offline. Materialize the candidate
   ledger too if that is a separate CLI step. Compare the reportable and
   compiler-only file sets, per-file hashes, remappings, compiler identity,
   scan result, and candidate result with the canonical post-repair workspace.
   Explain any profile-bound digest difference; do not call a manual hash-only
   comparison a scanner reproduction. The canonical reference digests are:

   - source manifest:
     9e2a7faed9326d4db51b717222d9227f92f7e3909fb0cdf91d6b62378aeb8f84
   - scan:
     9784d71e91ae86d4380c738badb2c1dfcfa9d9871425064c814b4237183825e6
   - candidate ledger:
     8b1352ed188f4f2f6f93b7e365a9721c6f0a2204116b4e6eaa1a0109347f6b2f

   A changed candidate set, unexpected source difference, or plausible
   security state change is a stop condition. Do not copy private records into
   the repository.

4. Improve tests/test_repair_007.py with the smallest useful assertions. Compile
   the signature fixture once and assert its expected semantic result, not
   merely non-None output or equality with a second run. For the call-kind
   fixture, assert that error/event/struct members create no external
   interaction and that the real retained interaction/finding has the exact
   stable public fixture path, line, kind, entry function, and evidence fields
   required by CONTRIBUTING.md. Keep the tests at the public compiler-backed
   seam and avoid new abstractions.

5. Replace mkdtemp plus manual cleanup in tests/test_deep_ast.py with a
   context-managed tempfile.TemporaryDirectory. Keep the change local to the
   test.

6. Correct all public status text. In particular:

   - describe the first minimal checkout as a manual, hash-only reproduction
     that was not scanner-compatible because it lacked Git metadata;
   - remove the contradictory claims that regression work was open and that
     every review finding was already closed;
   - use the correct 64-character scan digest above;
   - state that REPAIR-007 blocks PILOT-008 until this work passes;
   - keep PRECISION-002 blocked by PILOT-008;
   - keep the final source-to-scope verdict UNSATISFIED even if this repair
     succeeds.

   Update README.md, CHANGELOG.md, TASKS.md, docs/DEVELOPMENT_PLAN.md,
   docs/PILOT_007_PLAN.md, docs/PILOT_008_PLAN.md,
   docs/research/PILOT_007_EVALUATION.md, and this handoff as needed. Keep all
   target reporting aggregate and redacted.

7. Run the focused regressions, then all gates:

   PYTHONPATH=src python3 -m unittest tests.test_repair_007 tests.test_deep_ast -v
   PYTHONPATH=src python3 -m unittest discover -s tests -q
   PYTHONPATH=src python3 -m contract_holes evaluate \
     tests/fixtures/evaluation/manifest.json
   PYTHONPATH=src python3 -m contract_holes bounty history \
     tests/fixtures/bounty_history/manifest.json
   git diff --check

8. Inspect the staged file list and staged diff for private data and accidental
   complexity. If every completion criterion passes, mark REPAIR-007 complete,
   make PILOT-008 NEXT, update this handoff for PILOT-008, commit one coherent
   change, push main, verify CI, and leave the worktree clean with main equal to
   origin/main. If a criterion does not pass, leave REPAIR-007 open and report
   the exact blocker. Do not start PILOT-008 in the same session.

Completion criteria

- A new read-only, Git-backed minimal checkout is accepted by the public scanner.
- A new private workspace contains an offline scanner-produced source manifest
  and scan; its semantic inputs and result match the canonical operational run.
- The repaired regressions assert stable public evidence and fail for their
  corresponding pre-fix behavior.
- TemporaryDirectory owns the deep-AST test lifecycle.
- Public documents make no contradictory or overstated completion claim.
- All public tests and frozen evaluations pass.
- No private target or candidate content enters Git.
- One coherent commit is pushed, project CI is green, and the worktree is clean.

No new operator approval is needed for this local, private, offline repair.
Stop only for a changed candidate/security state, missing local source needed
to continue, or any action requiring network target acquisition, RPC, a fork,
a chain action, proof, report, export, disclosure, submission, external bounty
or target-platform writing, or target contact. The normal project-repository
push and CI check in step 8 remain part of this task.
```
