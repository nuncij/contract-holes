# OpenCode development handoff

Run this handoff with OpenCode model `opencode-go/deepseek-v4-flash`. This is
the only assigned development model. The primary Codex session writes the plan
and verifies the result; OpenCode performs the development workflow.

```text
Continue Contract Holes development in the current repository. PILOT-009 is
UNSATISFIED. Add the generic compiler-boundary repair (reproduce Foundry
automatic submodule remapping in the isolated bounty compiler) and re-run the
frozen EulerSwap v2 closure privately. Use docs/PILOT_009_PLAN.md as the
authoritative scope, its completion gate, and its stop conditions.

Role

You are the implementation agent. Work autonomously through develop -> test ->
docs -> Git. Do not ask for routine approvals. The primary session will review
your finished work and evidence. Do not delegate to another model or agent.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/PILOT_009_PLAN.md
- docs/research/PILOT_009_TARGET_SELECTION.md
- docs/research/PILOT_009_EVALUATION.md
- docs/PRECISION_002_PLAN.md
- docs/COMP_004_PLAN.md
- docs/EVALUATION.md
- this handoff

Current state

- Release 1.1.1 is complete.
- PRECISION-002 is complete at detector commit 2574b6e. GitHub CI run
  31720097982 passed both jobs.
- The suite has 238 tests. The frozen audit result is 33 positive and 31 safe
  labels at 1.0. The historical result has 0.933333 candidate precision, 1.0
  supported-class recall, and 1.0 evidence completeness.
- PILOT-009 is UNSATISFIED. The public selection gate passed for the EulerSwap
  v2 Ethereum subset at commit 81cf6dc988468fd56f690e6bc0e338a5be02d034.
  Euler's pinned first-party verification manifest (euler-interfaces commit
  d938bc264d6e1cee68a559798044d43ade8ac95e) maps five deployed components to
  that commit. The exact pinned source and recursive submodule closure were
  acquired, enumerated (5 reportable and 56 compiler-only Solidity files), and
  frozen clean and user-read-only with Git metadata.
- Both private workspaces reproduced byte-identical schema-1.2 source manifests
  and failed deterministically at the compile stage before any scan: the fixed
  detector commit 2574b6e cannot reproduce Foundry's automatic submodule
  remapping (its isolated compiler writes libs = [] and loads only the target
  remappings.txt). The unresolved import is v4-periphery/src/utils/BaseHook.sol
  from src/UniswapHook.sol, in the closure of reportable src/EulerSwap.sol; the
  target itself resolves it through libs = ["lib"] in foundry.toml. A
  standalone offline trial compile of the identical 61-file closure with the
  automatic remapping succeeds with Solidity 0.8.27.
- No scan record or candidate identity exists. EulerSwap is retained as a
  research corpus. The frozen target checkout is at
  targets/euler-swap-v2-81cf6dc9 and the freeze record is at
  bounty-workspaces/euler-swap-v2-0.8.27-freeze (outside this repository).

Boundary

Public research, the one-time exact pinned source/dependency downloads, and
private local offline analysis are authorized. Keep the target checkout,
profiles, manifests, scans, candidates, reviews, paths, excerpts, and hashes
outside this repository. Use private directories (0700) and files (0600).

Stay local and source-only after acquisition. No RPC, fork, public or test
chain, transaction, deployment, target build/test/deploy script, proof,
exploit, report export, disclosure, submission, bounty-platform write, or
target contact. Do not change detector rules, thresholds, corpus labels, or
evaluation baselines for target-specific reasons; a generic compiler-boundary
repair must keep every frozen corpus identity and public evidence contract
unchanged. Do not put candidate-specific facts in public docs, commits,
terminal summaries, or CI.

Sequence

1. Verify main against origin/main. Confirm src, tests, evaluation, and
   pyproject.toml have not changed after detector commit 2574b6e. Run the full
   unit suite, frozen audit evaluation, and historical bounty evaluation.

2. Design the generic compiler-boundary repair at the existing isolated
   compiler seam: reproduce Foundry's automatic submodule remappings (the
   prefixes the target's libs/ directories imply) in the temporary staging
   project, or accept a profile-declared additive remapping extension, so a
   closure that relies on automatic remapping compiles offline. Keep legacy
   digests and behavior unchanged for targets whose remappings.txt is
   self-contained. Add generic fixtures and tests for a target that relies on
   automatic remapping (a root import that resolves only via a libs/ prefix).

3. Run the full suite and both frozen evaluations. Verify the frozen audit,
   historical, and prior corpus identities are unchanged and that legacy
   unpinned profiles/digests are byte-identical.

4. Re-run the frozen EulerSwap closure privately with the repaired detector in
   two new workspaces (schema 1.2, Solidity 0.8.27, the same 5 reportable and
   56 compiler-only files). Compare source-manifest, profile, scan, and
   candidate digests, compiler version, reportable file count, finding count,
   candidate count, and rule distribution. A mismatch leaves the repair
   incomplete.

5. Review every candidate privately against the pinned source, live program
   impact rules, known issues, and prior audits. Record hypothesis, evidence
   boundary, impact, reachability assumptions, duplicate status, state, reason,
   uncertainty, and review effort. Do not tune the scanner from these labels.
   Treat candidates as investigation leads, not vulnerabilities.

6. Write docs/research/PILOT_009_EVALUATION.md using aggregate public data only:
   public target identity and selection method, mapping verdict, compiler mode,
   reportable file count, total candidates and per-rule counts, aggregate review
   states, review effort, comparison with prior trials, limitations including
   unknown recall, restrictions observed, and the recommended next task. Omit
   private paths, hashes, candidate IDs, source excerpts, traces, and any
   candidate-specific explanation.

7. Update README.md, CHANGELOG.md, TASKS.md, docs/DEVELOPMENT_PLAN.md,
   docs/PILOT_009_PLAN.md, docs/README.md, and this handoff to the final truthful
   state. Mark PILOT-009 COMPLETE only if every completion gate in its plan
   passes. Run all validation gates, inspect the staged diff for private data,
   commit, push main, and wait for green GitHub CI. If GPG commit signing needs
   interaction, use an unsigned commit; release tag signing is separate.

Validation gates

PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check

Finished output

Return a concise aggregate summary: PASS/UNSATISFIED, public commit IDs, CI run
IDs and results, test/evaluation totals, private workspace locations and
permissions without candidate-specific details, replay-match verdict, aggregate
candidate/review counts, docs changed, and any remaining blocker. Leave the
repository clean with main matching origin/main.
```
