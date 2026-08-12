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
- The next task is PILOT-006. PRECISION-001 follows it.
- The private compiler trial scanned 22 reportable files with 58 exact
  compiler-only dependencies.
- The trial produced 51 candidates. Human review rejected 50 and left one in
  state investigating. No candidate is confirmed.
- No proof, report, export, disclosure, submission, chain action, or target
  interaction has occurred for the investigating candidate.
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
  0a321f9e919175b8879019d1b80996a434bd35b9866d2c214d2750ccd162f238
- Expected review file SHA-256:
  19d59d25ce0a520609e0715caf8d4ee1cc304b19e2042d786d96373d100fcbf4
- Expected solc version:
  0.8.27+commit.40a35a09.Linux.g++
- Expected solc SHA-256:
  b9977d500c17cba6f0032ca939ef98c4decf6363f19f386d05fb02f708115264

Authorization boundary

The operator authorized local, private, isolated, offline analysis and proof
work for this exact pinned trial. Continue that work without another approval
prompt. You may inspect and update the private workspace, generate the smallest
useful local proof, and run the pinned compiler or local proof runner offline.

Keep target-related network access disabled. Do not use RPC, a fork, a public or
private chain, target contact, report export, disclosure, submission, or a
platform API. A normal Contract Holes Git push and its project CI are part of
the development workflow. Never commit private candidate details or target
source.

PILOT-006 workflow

1. Verify the Contract Holes worktree and target checkout before analysis.
2. Verify the private ledger permissions, hashes, and 50 rejected plus one
   investigating state count.
3. Load the sole investigating candidate from the private workspace.
4. Trace the reported interaction through the approved reference integration.
5. Decide whether an untrusted actor can reach a callback under the pinned
   deployment trust boundary.
6. Use the existing bounty-proof workflow if it can test this question without
   inventing setup facts.
7. If that workflow cannot test the question, build the smallest isolated
   offline harness that can. Keep it outside the target checkout.
8. Record pass, fail, unsupported, or inconclusive evidence accurately. A
   generic reentrancy primitive does not prove target impact.
9. Record the final review as Nunc only when the evidence supports rejection or
   a concrete in-scope impact supports confirmation.
10. If the candidate is rejected, update aggregate counts only and continue to
    PRECISION-001.
11. If the candidate is confirmed, stop before report creation or any external
    action. Give the operator a private summary without candidate details in
    repository docs.
12. Update TASKS.md, docs/DEVELOPMENT_PLAN.md,
    docs/research/M8_OPENZEPPELIN_TRIAL.md, README.md, and CHANGELOG.md.
13. Run documentation checks, relevant focused tests, the full Python suite,
    and git diff --check.
14. Review the final diff for unnecessary complexity. Commit, push main, and
    verify project CI.

Completion criteria

- The target checkout and frozen source-only workspace stay unchanged.
- The proof stays local, isolated, private, and offline.
- The private ledger contains one evidence-backed final decision.
- Repository docs contain aggregate results only.
- Tests pass and Git is clean after the pushed commit.
- The next task in TASKS.md matches the actual remaining work.
```
