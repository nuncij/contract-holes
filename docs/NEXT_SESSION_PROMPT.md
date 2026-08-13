# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Start by reading AGENTS.md if it exists, TASKS.md, docs/DEVELOPMENT_PLAN.md,
docs/PRECISION_001_PLAN.md, docs/research/M8_TARGET_SELECTION.md,
docs/research/M8_OPENZEPPELIN_TRIAL.md, docs/research/PILOT_007_TARGET_SELECTION.md,
docs/research/PILOT_007_EVALUATION.md, and this handoff. Treat current command
output as authoritative for mutable hashes and state.

Project state

- The current release is 1.1.1.
- M0 through M8 are complete.
- PILOT-006, PRECISION-001, and PILOT-007 are complete. The next task is
  PRECISION-002: convert the generic false-positive families observed on the
  second independent target into regression fixtures and minimal detector fixes.
- The OpenZeppelin Confidential Contracts trial scanned 22 reportable files
  with 58 exact compiler-only dependencies. The compiler trial produced 51
  candidates; human review rejected all 51. No candidate is investigating or
  confirmed.
- The independent Silo trial scanned 10 reportable files with 124 pinned
  compiler-only dependencies and Solidity 0.8.28. It produced 81 candidates;
  the operator confirmed all 81 rejections after source review. No candidate is
  investigating or confirmed.
- The Silo trial surfaced and fixed three generic scanner defects: iterative
  AST traversal, cycle-safe signature domain analysis, and exclusion of custom
  error/event members from the call graph.
- The observed generic false-positive families from the Silo trial are the
  PRECISION-002 backlog: timelock-style authorization modifiers, view-only
  interaction facts in reentrancy ordering, governance-configured call lists
  and freshly deployed clones as non-user-controlled target provenance, and
  read-only view-call arguments in target taint.
- No report, export, disclosure, submission, chain action, or target contact
  occurred.
- Keep the exact candidate IDs, source paths, code, and evidence only in the
  private workspaces. Do not add them to repository files or Git output.

Local evidence

- OpenZeppelin target checkout:
  ../targets/openzeppelin-confidential-contracts-v0.4.0-compiler
- Expected OpenZeppelin target commit:
  7ac7cee5fec408dc81b31121f90417dfd87f3d13
- Private OpenZeppelin compiler workspace:
  ../bounty-workspaces/openzeppelin-confidential-v0.4.0-compiler-redacted
- Frozen source-only workspace:
  ../bounty-workspaces/openzeppelin-confidential-v0.4.0
- Silo target checkout:
  ../targets/silo-contracts-v3-4.26.0
- Expected Silo target commit:
  570a668a98a88a6a2b92697e7b9a3b1c6299dce7
- Private Silo canonical workspace:
  ../bounty-workspaces/silo-contracts-v3-4.26.0
- Private Silo replay workspace:
  ../bounty-workspaces/silo-contracts-v3-4.26.0-replay
- Expected Silo scan digest:
  9784d71e91ae86d4380c738badb2c1dfcfa9d9871425064c814b4237183825e6
- Expected Silo candidate-ledger digest:
  8b1352ed188f4f2f6f93b7e365a9721c6f0a2204116b4e6eaa1a0109347f6b2f
- Expected Silo review-ledger digest:
  3c58c01c81df6fe3c93c70e4d59c1b944360beaa289137c1cf80404519f72540
- Expected solc version:
  0.8.28+commit.7893614a.Linux.g++

Work boundary

Continue local development, tests, documentation, Git commits, pushes, and
project CI without another approval prompt. Keep the prior targets and private
evidence read-only. Use private evidence only to derive generic tests. Do not
contact, disclose to, or submit to any target or platform.

Execution

Follow TASKS.md and docs/DEVELOPMENT_PLAN.md for the current milestone. Work in
red-to-green slices for PRECISION-002. Keep the frozen evaluation gates
unchanged. When the task is complete, update all status documents and this
prompt, commit, push, and verify CI.
```
