# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Objective

Select, authorize, and scan a new independent real-world target whose deployed
assets map exactly to a pinned immutable source revision (PILOT-008). Do not
start PRECISION-002. Preserve the existing private evidence and the Silo
research corpus unchanged. Keep candidate details and target source out of the
repository.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/PILOT_007_PLAN.md (completion-repair outcome)
- docs/research/PILOT_007_TARGET_SELECTION.md
- docs/research/PILOT_007_EVALUATION.md
- docs/PRECISION_002_PLAN.md (blocked follow-up boundary)
- this handoff

Treat current command output as authoritative for mutable state.

Project state

- Release: 1.1.1.
- M0 through M8 complete. PRECISION-001 complete.
- PILOT-007 is UNSATISFIED. The untouched scanner at selection commit
  08050a14437abaf47ff45b90a1392a9fbc460a93 hits a reproducible RecursionError
  blocker on the Silo closure, so there is no frozen baseline scan digest. The
  pinned Silo tag 4.26.0 (commit 570a668a98a88a6a2b92697e7b9a3b1c6299dce7)
  does not map to the deployed in-scope assets, which are Silo version 3.5.0
  (commit b1f428f1c3d5fc989974fd8e7b3b84180e05e31f). Silo is retained only as a
  research corpus.
- The post-repair Silo operational result (scan digest
  9784d71e91ae86d4380c738badb2c1cfa9d9871425064c814b4237183825e6, candidate
  ledger 8b1352ed188f4f2f6f93b7e365a9721c6f0a2204116b4e6eaa1a0109347f6b2f,
  review ledger 3c58c01c81df6fe3c93c70e4d59c1b944360beaa289137c1cf80404519f72540)
  is post-repair operational evidence, not an untouched frozen trial.
- Suite: 221 tests. Frozen evaluation gates pass (1.0/1.0 synthetic; 0.875/1.0
  historical).
- Next: PILOT-008, a new independent target with an exact deployed-source
  mapping, before PRECISION-002 starts.

Existing evidence — preserve unchanged

- Silo target checkout: ../targets/silo-contracts-v3-4.26.0
- Silo canonical workspace: ../bounty-workspaces/silo-contracts-v3-4.26.0
- Silo replay workspace: ../bounty-workspaces/silo-contracts-v3-4.26.0-replay
- Silo baseline workspaces: ../bounty-workspaces/silo-contracts-v3-4.26.0-baseline-a,
  ../bounty-workspaces/silo-contracts-v3-4.26.0-baseline-b
- Silo minimal checkout: ../bounty-workspaces/silo-minimal-checkout
- OpenZeppelin trial evidence (unchanged).

Keep candidate IDs, source paths, excerpts, traces, and review notes out of the
repository and Git output.

Execution

1. Verify the worktree, origin/main, current CI, and the recorded hashes and
   permissions. Run the full suite, frozen audit evaluation, and historical
   bounty evaluation.
2. Research at least three current programs from official sources. Prefer a
   target whose scope maps exact deployed assets to a pinned immutable Git
   revision or release, with a manageable dependency closure and no RPC or fork
   need. Avoid repeating the PILOT-007 failure: filename equality is not proof
   of deployed-source equivalence; use the program's own deployment/version
   records and verified-source metadata.
3. Record the selection and comparison in
   docs/research/PILOT_008_TARGET_SELECTION.md. Present one complete target
   boundary and request the single consolidated operator authorization.
4. After approval, acquire the exact approved source and pinned dependencies,
   build a minimal dependency-closure checkout, and run two private offline
   scans. Preserve the first baseline result frozen before any detector
   change. Do not tune detector behavior against the target.
5. Review candidates privately and present proposed decisions in one batch for
   operator confirmation. Complete the private review brief for every
   candidate.
6. Write docs/research/PILOT_008_EVALUATION.md with aggregate, redacted
   results. Update README.md, CHANGELOG.md, TASKS.md,
   docs/DEVELOPMENT_PLAN.md, docs/README.md, and this handoff. State the
   current test count and the exact source-to-scope verdict.
7. Run all validation gates, inspect the staged diff for private data, run a
   simplification review, commit one coherent change, push main, verify CI, and
   leave the worktree clean with main equal to origin/main.

Validation gates

PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check

Stop only for operator approval, a plausible candidate/state change, or if
progress would require RPC, a fork, a chain action, a proof, a report,
disclosure, submission, platform writing, target contact, or an unapproved
target download.
```
