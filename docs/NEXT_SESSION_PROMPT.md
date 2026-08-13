# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Objective

Repair the PILOT-007 completion-review failures. Do not start PRECISION-002 in
this session. Preserve the existing private evidence, reconstruct the untouched
scanner baseline, resolve the source-to-scope gate, repair tests and review
records, correct the public claims, then commit, push, and verify CI.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/PILOT_007_PLAN.md, especially "Completion-review repair"
- docs/research/PILOT_007_TARGET_SELECTION.md
- docs/research/PILOT_007_EVALUATION.md
- docs/PRECISION_002_PLAN.md for the blocked follow-up boundary
- this handoff

Treat current command output as authoritative for mutable state.

Known state

- Release: 1.1.1.
- Untouched scanner selection commit:
  08050a14437abaf47ff45b90a1392a9fbc460a93
- Current Silo source commit:
  570a668a98a88a6a2b92697e7b9a3b1c6299dce7 (tag 4.26.0)
- Current post-repair scan digest:
  9784d71e91ae86d4380c738badb2c1dfcfa9d9871425064c814b4237183825e6
- Current post-repair candidate-ledger digest:
  8b1352ed188f4f2f6f93b7e365a9721c6f0a2204116b4e6eaa1a0109347f6b2f
- Current review-ledger digest:
  3c58c01c81df6fe3c93c70e4d59c1b944360beaa289137c1cf80404519f72540
- Source-manifest digest:
  9e2a7faed9326d4db51b717222d9227f92f7e3909fb0cdf91d6b62378aeb8f84
- Expected compiler: 0.8.28+commit.7893614a.Linux.g++.
- Current suite: 219 tests before this repair.
- The two existing private scans match and contain 81 candidates, all currently
  operator-confirmed rejected. This is post-repair operational evidence, not an
  untouched independent baseline.
- No proof, report, export, disclosure, submission, RPC, fork, chain action,
  platform write, or target contact is authorized.

Existing evidence — preserve unchanged

- Target checkout: ../targets/silo-contracts-v3-4.26.0
- Canonical workspace: ../bounty-workspaces/silo-contracts-v3-4.26.0
- Replay workspace: ../bounty-workspaces/silo-contracts-v3-4.26.0-replay

Use new paths for every reconstructed checkout or workspace. Keep candidate IDs,
source paths, excerpts, traces, and review notes out of the repository and Git
output.

Review failures to close

1. Both preserved scans were created after commits e45f0fc and ab3d5a7 changed
   scanner behavior in response to the target. The plan required the first
   baseline result or failure to remain frozen.
2. The selected Git tag is not yet proven byte-for-byte equivalent to the
   deployed assets in the Immunefi scope. Matching filenames are insufficient.
3. The checkout initialized 87 submodules although only the submodules
   intersecting the 124-file compiler manifest were approved and required.
4. The private review brief lacks per-candidate impact, assumptions,
   duplicate/known-issue status, and remaining uncertainty.
5. Signature-domain recursion and error/event/struct call classification lack
   regression tests.
6. tests/test_deep_ast.py uses a persistent shared /tmp directory.
7. Public documents overstate the trial, regression coverage, and test count.
8. The existing checkout's source files are read-only, but its Git metadata is
   still writable.

Execution

1. Verify the worktree, origin/main, current CI, existing hashes, and permissions.
   Run the full suite, frozen audit evaluation, and historical bounty evaluation.

2. Repair the public test suite first:
   - add public-seam regressions for mutually recursive signature-domain feature
     propagation;
   - add public-seam regressions proving resolved errors, events, and struct
     constructors are not external interactions while a real external call still
     is;
   - replace /tmp/holes-deep-ast-regression with TemporaryDirectory;
   - keep detector behavior unchanged in this repair.
   Run focused tests, then the full suite.

3. Reconstruct the untouched baseline:
   - create a temporary Git worktree at commit 08050a1;
   - copy the approved profile into two new private workspaces;
   - use the existing pinned source and compiler closure offline;
   - run the same compiler-enabled scan in both workspaces;
   - preserve either identical successful digests or the identical reproducible
     blocker from both attempts;
   - remove only the temporary Git worktree after recording the result; preserve
     both private evidence workspaces.
   Call this a retrospective baseline reconstruction. Do not call it the original
   first scan.

4. Resolve source-to-scope identity using current official Immunefi, Silo GitHub,
   and verified deployed-source records over read-only HTTPS. Compare exact source
   content or compiler metadata for all ten selected reportable files. Do not use
   RPC, a fork, or a transaction. If exact correspondence cannot be proved, mark
   the Silo selection invalid for a bounty-scoped independent trial and retain it
   only as a research corpus. Do not silently select or download a replacement
   target in this session.

5. Build a new minimal checkout from existing local Git objects without network
   access. Initialize only the submodules that intersect the frozen 124-file
   compiler manifest. Reproduce the source manifest and scan offline, then make
   the entire checkout, including Git metadata, user-read-only under a private
   parent. Preserve the original checkout unchanged. Record the historical
   over-retrieval honestly; a later minimal checkout does not erase it.

6. Complete the private review brief for all 81 candidates. Record the scanner
   hypothesis, relevant in-scope impact or lack of one, reachability and trust
   assumptions, known/duplicate status, reason, and remaining uncertainty.
   Preserve the confirmed states when supported. If any candidate becomes
   plausible or needs a state change, stop and present only the private decision
   summary to the operator; do not start a proof or report.

7. Correct README.md, CHANGELOG.md, TASKS.md, docs/DEVELOPMENT_PLAN.md,
   docs/PILOT_007_PLAN.md, docs/research/PILOT_007_TARGET_SELECTION.md,
   docs/research/PILOT_007_EVALUATION.md, docs/README.md, and this handoff.
   Distinguish the retrospective untouched baseline from the post-repair
   81-candidate result. State the source-mapping verdict and current test count.
   Keep all public text aggregate and redacted.

8. Decide status from evidence:
   - mark PILOT-007 repaired only if the exact source-to-scope gate passes and all
     completion requirements are satisfied;
   - otherwise mark it unsatisfied, retain Silo as a research-only validation,
     and queue a new independent-target trial before PRECISION-002;
   - do not label the existing 81-candidate scan an untouched frozen trial.

Validation gates

PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check

Inspect the staged diff for candidate details, private paths, target excerpts,
credentials, or generated artifacts. Run a simplification review on the final
code diff. Commit one coherent repair, push main, verify project CI is green,
and leave the worktree clean with main equal to origin/main.

Work autonomously through local development, tests, documentation, Git, CI, and
read-only official-source research. Stop only for a plausible candidate/state
change or if progress would require RPC, a fork, a chain action, a proof, a
report, disclosure, submission, platform writing, target contact, or a new
target download.

Final report

Report the baseline reconstruction outcome, source-to-scope verdict, dependency
closure, private review completeness, tests/evaluations, documentation changes,
commit, push, and CI. State clearly whether PILOT-007 now passes or remains
unsatisfied and what task is next.
```
