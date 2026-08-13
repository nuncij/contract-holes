# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Objective

Complete COMP-004 using the develop -> test -> docs -> Git workflow. Add one
optional exact Solidity compiler version to new compiler-enabled bounty
profiles. Bind it into isolated compilation and fail if the observed compiler
differs. Preserve all existing unpinned profiles and digests exactly. After
COMP-004 is complete, PRECISION-002 is the next task.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/COMP_004_PLAN.md (authoritative scope)
- docs/PILOT_008_PLAN.md
- docs/research/PILOT_008_TARGET_SELECTION.md
- docs/research/PILOT_008_EVALUATION.md
- docs/PRECISION_002_PLAN.md
- docs/BOUNTY_PROFILE.md
- this handoff

Treat current command output as authoritative for mutable state.

Project state

- Release: 1.1.1.
- M0 through M8, PRECISION-001, REPAIR-007, and PILOT-008 are complete.
- Suite: 221 tests before COMP-004; frozen synthetic evaluation is 33/33
  positives and 31/31 safe labels; historical candidate precision is 0.875 and
  supported-class recall is 1.0.
- PILOT-008 scanned the program-mapped Olas governance v1.2.5 subset at commit
  8ce095fec0efd935af39a89b8ae9c90e6581d1e4. The exact profile is
  53226e80f049e085272f72e0a918992fe5b748e2a2e976fe229f97f195847299,
  source manifest 3c1df4684335834bd473d9c40647d839a0b077f044c6980a6983910b05550a16,
  Solidity 0.8.30 scan 875a0f1badf8852bfb8f7eda5ef471f0bfe48d95489cb97c7702783f6a6efc11,
  and zero-candidate ledger
  c0701335650ff9967d897b887a750272f9b5fb3a51d3f5138e2d0bcc06715b14.
- An initial unchanged-profile scan selected cached Solidity 0.8.28. It was
  preserved. This proves the concrete COMP-004 failure: the profile binds
  offline mode but not an exact compiler version.
- Solidity 0.8.30 is already installed and SHA-256 verified in Foundry's local
  cache. No network download is needed. The user's global solc-select version
  was restored to 0.8.36.

Private evidence — preserve unchanged

- Target: ../targets/olas-governance-v1.2.5 (detached, clean, user-read-only)
- Preserved initial mismatch: ../bounty-workspaces/olas-governance-v1.2.5-a
- Exact primary: ../bounty-workspaces/olas-governance-v1.2.5-b
- Exact replay: ../bounty-workspaces/olas-governance-v1.2.5-c
- All prior OpenZeppelin and Silo targets/workspaces.

Do not send private source, scan records, candidate details, paths, excerpts, or
traces to an external model or service. Keep all target validation offline. No
RPC, fork, chain action, proof, report, export, disclosure, submission, platform
write, or target contact is authorized.

Required interface

1. Add `holes bounty init --compiler-version X.Y.Z` for compiler-enabled
   profiles.
2. Accept only an exact release in the published supported Solidity range.
3. Reject it with `--source-only`.
4. Emit additive normalized profile and source-manifest schema 1.2 when pinned.
5. Keep every existing unpinned 1.0/1.1 payload, digest, and behavior unchanged.
6. In the fixed temporary Foundry project, use `solc_version = "X.Y.Z"` for a
   pinned profile instead of auto-detection.
7. Fail closed unless exactly one observed compiler release matches the pin.
8. Do not load target Foundry configuration and do not add optimizer/EVM options;
   this scanner consumes isolated ASTs and does not claim bytecode reproduction.

Workflow

1. Verify clean main, origin/main, current CI, and baseline gates.
2. Mark COMP-004 IN PROGRESS.
3. Add failing interface-level tests first: CLI/profile normalization, invalid
   combinations, legacy digest stability, pinned temporary configuration, and
   observed-version mismatch.
4. Implement the smallest change at the existing bounty profile/compiler seam.
5. Add packaged 1.2 schemas and update docs/schema tests.
6. Run focused tests, full suite, frozen synthetic evaluation, historical
   evaluation, and git diff --check.
7. Create a new private validation workspace (do not modify a/b/c), set
   compiler-version 0.8.30, and reproduce the existing zero-candidate Olas scan
   semantics offline.
8. Update README.md, CHANGELOG.md, TASKS.md, docs/DEVELOPMENT_PLAN.md,
   docs/BOUNTY_PROFILE.md, docs/README.md, and this handoff. Mark PRECISION-002
   NEXT only after all COMP-004 gates pass.
9. Run a simplification review, inspect the staged diff for private data, commit
   one coherent change, push main, verify CI, and leave main clean and equal to
   origin/main.

Validation gates

PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check

Stop only if a legacy digest changes, a positive/historical gate regresses, the
private replay cannot remain offline, or work would cross the prohibited
external-action boundary.
```
