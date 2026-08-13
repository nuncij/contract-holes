# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Start by reading AGENTS.md if it exists, TASKS.md, docs/DEVELOPMENT_PLAN.md,
docs/research/M8_TARGET_SELECTION.md,
docs/research/M8_OPENZEPPELIN_TRIAL.md, and this handoff. Inspect Git and the
private records before changing anything. Treat the files and current command
output as authoritative when they differ from this prompt.

Project state

- The current release is 1.1.1.
- M0 through M8 are complete.
- PILOT-006 is complete. The next task is PRECISION-001.
- The private compiler trial scanned 22 reportable files with 58 exact
  compiler-only dependencies.
- The trial produced 51 candidates. Human review rejected all 51. No candidate
  is investigating or confirmed.
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
- Expected solc version:
  0.8.27+commit.40a35a09.Linux.g++
- Expected solc SHA-256:
  b9977d500c17cba6f0032ca939ef98c4decf6363f19f386d05fb02f708115264

Work boundary

Continue local development, tests, documentation, Git commits, pushes, and
project CI without another approval prompt. Keep the target checkout and
private evidence read-only. Use private evidence only to derive generic tests.

Keep target-related network access disabled. RPC, forks, chains, target contact,
report export, disclosure, submission, and platform APIs remain outside this
work. Never commit private candidate details or target source.

PRECISION-001 workflow

1. Verify Git, the private ledger hashes, and the 51 rejected state count.
2. Read the PRECISION-001 acceptance criteria in TASKS.md.
3. Inspect the shared call, data-flow, authorization, taint, and reentrancy
   models before changing a detector.
4. Add generic safe fixtures for each observed false-positive class.
5. Cover pure or internal calls and user-defined value-type conversions.
6. Cover infeasible post-callback branches and proven immutable call targets.
7. Cover role checks, caller-owned mapping writes, and unreachable in-flight
   reentrant state.
8. Make the smallest shared analysis fixes that pass the new safe fixtures.
9. Keep every existing positive fixture detected. Add no project-specific names
   or FHE-specific suppressions.
10. Update TASKS.md, docs/DEVELOPMENT_PLAN.md, README.md, and CHANGELOG.md.
11. Run focused tests, documentation checks, the full suite, and
    git diff --check.
12. Review the final diff for unnecessary complexity. Commit, push main, and
    verify project CI.

Completion criteria

- The target checkout and frozen source-only workspace stay unchanged.
- Every observed false-positive class has a generic safe regression fixture.
- Existing positive fixtures still pass.
- Repository code and docs contain no candidate IDs, target source excerpts, or
  candidate-specific evidence.
- Tests pass and Git is clean after the pushed commit.
- The next task in TASKS.md matches the actual remaining work.
```
