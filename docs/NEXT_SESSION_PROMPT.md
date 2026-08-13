# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Start by reading AGENTS.md if it exists, TASKS.md, docs/DEVELOPMENT_PLAN.md,
docs/PILOT_007_PLAN.md, docs/research/M8_TARGET_SELECTION.md,
docs/research/M8_OPENZEPPELIN_TRIAL.md, and this handoff. Treat
docs/PILOT_007_PLAN.md as the authoritative sequence and completion gate.

Project state

- The current release is 1.1.1.
- The detector repair baseline is c882f6b. Start from the later planning commit
  on origin/main and verify the current Git state.
- M0 through M8 are complete.
- PILOT-006 and PRECISION-001 are complete. The next task is PILOT-007:
  select and evaluate an independent second real-world target.
- The private compiler trial scanned 22 reportable files with 58 exact
  compiler-only dependencies.
- The trial produced 51 candidates. Human review rejected all 51. No candidate
  is investigating or confirmed.
- PRECISION-001 added generic compiler fixtures for all five observed groups.
  The fresh private rescan produced 47 candidates: 23 call-semantics, 8
  branch-feasibility, 12 target-provenance, 3 authorization-context, and 1
  reentrancy-trust-boundary.
- A completion review repaired pure public-library call handling,
  interprocedural branch context, role self-grant detection, fixed-target
  provenance, and public evidence assertions. A separate offline rescan
  reproduced the same 47 candidates and deterministic digests.
- The final trust-boundary analysis found no reachable untrusted callback. The
  generic proof workflow was unsupported for that question, so no proof ran.
- No report, export, disclosure, submission, chain action, or target contact
  occurred.
- Keep the exact candidate ID, source path, code, and evidence only in the
  private workspace. Do not add them to repository files or Git output.

Local evidence

- Target checkout:
  ../targets/openzeppelin-confidential-contracts-v0.4.0-compiler
- Expected target commit:
  7ac7cee5fec408dc81b31121f90417dfd87f3d13
- Private compiler workspace:
  ../bounty-workspaces/openzeppelin-confidential-v0.4.0-compiler-redacted
- Frozen source-only workspace:
  ../bounty-workspaces/openzeppelin-confidential-v0.4.0
- Expected scan digest:
  8fa3093b06c7bb23710f2d663d728032bc7eb107fb82513982b8560137483433
- Expected candidate-ledger digest:
  889e58b1f0cf91a9db4e011882a40a2b7455e90aeaa68e0e600bda1a10a5d15e
- Expected review-ledger digest:
  6815bf2ea95356be8f44e4627578412d5e1ffed9e84b8de856c32dde86232ce8
- Expected review file SHA-256:
  ce0cc3514cc04c6cc7b148d28459167eb7fc1ac02bc8dbd033f7afaddea8300b
- Private PILOT-006 evidence:
  ../bounty-workspaces/openzeppelin-confidential-v0.4.0-pilot-006
- Expected external-call enumeration SHA-256:
  039930c0a09d9987f011c6dd7ebec807ce523ce137ed5a0d4110d3df7deaddee
- Private PRECISION-001 rescan workspace:
  ../bounty-workspaces/openzeppelin-confidential-v0.4.0-precision-001
- Expected PRECISION-001 rescan digest:
  8bcf4e1b910588932998161b3f4df5f4cd8dc02a6efacd4dc3c670e1f301c66e
- Expected PRECISION-001 candidate-ledger digest:
  92654835b8aa11f95b83bc070547a823a32a0bd3a8ed113ab5c328501c6a437e
- Private PRECISION-001 repair rescan workspace:
  ../bounty-workspaces/openzeppelin-confidential-v0.4.0-precision-001-repair
- Expected solc version:
  0.8.27+commit.40a35a09.Linux.g++
- Expected solc SHA-256:
  b9977d500c17cba6f0032ca939ef98c4decf6363f19f386d05fb02f708115264

Work boundary

Complete routine local research, development, tests, documentation, Git commits,
pushes, and project CI without extra approval prompts. Keep the prior target and
private evidence read-only.

Use public network access only for current official target-selection sources.
Before source acquisition, present one complete target boundary and request the
single consolidated authorization specified in docs/PILOT_007_PLAN.md.

After that approval, retrieve only the approved source and pinned dependencies.
Keep all analysis private, isolated, and offline. Keep RPC, forks, chains,
proofs, reports, exports, disclosure, submission, platform writes, and target
contact outside this task.

Execution

Start at step 1 of docs/PILOT_007_PLAN.md. Work through the plan until a listed
stop condition needs operator input. The first expected stop is the single
target-authorization request after public selection research. The second is one
batch confirmation of proposed candidate decisions, unless the scan is empty.

Do not tune detector behavior after seeing the target. Freeze the independent
evaluation first and create later product tasks for generic gaps. Update all
status documents and this prompt, commit, push, and verify CI before completion.
```
