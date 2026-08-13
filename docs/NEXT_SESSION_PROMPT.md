# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Objective

Complete PRECISION-002 with the develop -> test -> docs -> Git workflow. Turn
the generic false-positive families recorded in docs/PRECISION_002_PLAN.md into
small public compiler-backed fixtures and the minimum generic detector fixes.
Preserve every existing positive, frozen corpus identity, and public evidence
contract. Do not copy private target code or evidence into the repository.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/PRECISION_002_PLAN.md (authoritative scope)
- docs/COMP_004_PLAN.md
- docs/research/PILOT_008_EVALUATION.md
- docs/EVALUATION.md
- this handoff

Treat current command output as authoritative for mutable state.

Project state

- Release: 1.1.1.
- M0 through M8, PRECISION-001, REPAIR-007, PILOT-008, and COMP-004 are
  complete.
- Suite: 234 tests after COMP-004.
- Frozen synthetic evaluation: 33/33 positive labels and 31/31 safe labels.
- Historical candidate precision: 0.875; supported-class recall: 1.0.
- COMP-004 added optional `--compiler-version X.Y.Z`, additive normalized
  profile/source-manifest schema 1.2, exact isolated Foundry selection, and
  fail-closed observed-version checking. Frozen unpinned 1.0/1.1 profile
  digests are unchanged.
- A new private offline Olas replay selected only Solidity 0.8.30, matched the
  frozen source and compiler-dependency sets, scanned two reportable files, and
  again produced zero findings and zero candidates.

Private evidence boundary

Private Silo records may be inspected locally only to understand the already
documented generic families. Do not send private source, paths, candidate IDs,
source excerpts, traces, or records to an external model or service. Do not put
them in fixtures, tests, commits, documentation, or logs intended for sharing.

No RPC, fork, chain action, transaction, proof, report, export, disclosure,
submission, platform write, or target contact is authorized. No target-specific
detector rule, project name, contract name, function name, constant, or path is
allowed.

Required behavior

Build one compiler corpus under tests/fixtures/precision_002 and test through
ProjectIndex plus Scanner.scan_source as specified by the plan. Each safe case
must have a nearby positive neighbor that keeps the original rule reportable.

Cover these generic distinctions:

1. Read-only view/static interactions do not create a SOL005 reentrancy path;
   a real state-changing external interaction before a write still does.
2. A structural timelock-style pending-value plus elapsed-delay guard protects
   the following privileged write from SOL009; an unprotected write still
   reports.
3. Freshly deployed clones used during registration are not untrusted callback
   targets; caller-supplied existing targets remain reportable.
4. Governance-configured call lists are not attacker-controlled delegatecall
   targets; caller-selected targets remain reportable under SOL008/SOL003 as
   applicable.
5. Caller-supplied targets used only by read-only queries are caller-harm-only
   and not controlled-call-target findings; a state-changing call remains
   reportable.
6. Immutable/fixed asset provenance is not user-controlled; mutable
   caller-controlled asset provenance remains reportable.

Workflow

1. Verify clean main, origin/main, current CI, and baseline gates.
2. Mark PRECISION-002 IN PROGRESS.
3. Inspect the existing shared compiler facts before choosing a seam.
4. Work in vertical TDD slices. For each family, add the safe and positive
   public fixture first. Confirm the misleading safe finding is red, or record
   that current code already handles it. Then implement the smallest generic
   change and run focused tests.
5. Put reusable semantics in existing shared analysis modules. Do not add raw
   AST walks inside individual rules, target-specific suppressions, or broad
   name heuristics.
6. Run the full suite and frozen synthetic/historical evaluations after each
   logical slice. Stop and repair immediately if any existing positive drops.
7. Update README.md, CHANGELOG.md, TASKS.md, docs/DEVELOPMENT_PLAN.md,
   docs/PRECISION_002_PLAN.md, docs/README.md, and this handoff with truthful
   counts and remaining limitations.
8. Run a simplification review and inspect the full diff for private material.
9. Commit one coherent change, push main, verify CI, and leave main clean and
   equal to origin/main.

Validation gates

PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check

Stop only if an existing positive or frozen identity changes unexpectedly, a
generic distinction cannot be established without target-specific knowledge,
or work would cross the prohibited external-action boundary.
```
