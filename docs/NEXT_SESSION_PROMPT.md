# OpenCode development handoff

Run this handoff with OpenCode model `opencode-go/deepseek-v4-flash`. This is
the only assigned development model. The primary Codex session writes the plan
and verifies the result; OpenCode performs the development workflow.

```text
Continue Contract Holes development in the current repository. Execute
PILOT-009 end to end. Use docs/PILOT_009_PLAN.md as the authoritative scope and
completion gate.

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
- PILOT-009 is in progress. Public research selected the EulerSwap v2 Ethereum
  subset at commit 81cf6dc988468fd56f690e6bc0e338a5be02d034.
- Euler's first-party verification manifest is pinned at euler-interfaces
  commit d938bc264d6e1cee68a559798044d43ade8ac95e. It maps five deployed
  EulerSwap v2 components to the selected source commit. An independent public
  cross-check passed.
- No target source has been downloaded or scanned. The exact import closure has
  not been reproduced yet.
- The worktree contains the new public target-selection record and initial plan
  status edits. Preserve, review, and complete them.

Boundary

Public research, the one-time exact pinned source/dependency downloads, and
private local offline analysis are authorized. Keep the target checkout,
profiles, manifests, scans, candidates, reviews, paths, excerpts, and hashes
outside this repository. Use private directories (0700) and files (0600).

Stay local and source-only after acquisition. No RPC, fork, public or test
chain, transaction, deployment, target build/test/deploy script, proof,
exploit, report export, disclosure, submission, bounty-platform write, or
target contact. Do not change detector code, tests, rules, thresholds, corpus
labels, or evaluation baselines during this fixed-detector trial. Do not put
candidate-specific facts in public docs, commits, terminal summaries, or CI.

Sequence

1. Verify main against origin/main and inspect the existing uncommitted docs.
   Confirm src, tests, evaluation, and pyproject.toml have not changed after
   detector commit 2574b6e. Run the full unit suite, frozen audit evaluation,
   and historical bounty evaluation.

2. Finish the public pre-acquisition record. Check every claim in
   docs/research/PILOT_009_TARGET_SELECTION.md against pinned primary sources.
   Keep the dependency wording provisional: it is a bounded candidate graph,
   not a reproduced closure. Mark PILOT-009 IN PROGRESS consistently in
   TASKS.md, docs/DEVELOPMENT_PLAN.md, docs/PILOT_009_PLAN.md, README.md,
   docs/README.md, CHANGELOG.md, and this handoff. Run doc/test gates, inspect
   the diff for private material, commit, push main, and wait for green GitHub
   CI. This public freeze must be green before any source download.

3. Acquire only euler-xyz/euler-swap at exact commit
   81cf6dc988468fd56f690e6bc0e338a5be02d034 and only the exact pinned
   submodule revisions needed by the five selected reportable components'
   recursive Solidity import closure. Work outside the Contract Holes repo.
   Inspect source, gitlinks, .gitmodules, remappings, and compiler metadata; do
   not execute target configuration or code. Verify tag eulerswap-2.0 resolves
   to the same commit. Stop if an import needs a mutable or unpinned dependency,
   if any gitlink differs from the public selection record, or if the selected
   deployed-source mapping no longer holds.

4. Enumerate the exact reportable closure and compiler-only closure. Record
   their identities privately. Use COMP-004 profile/source-manifest schema 1.2
   and exact compiler version 0.8.27. Freeze the complete Git-backed checkout,
   including Git metadata, as user-read-only after acquisition. Validate that
   Contract Holes accepts the source identity and compiler pin before scanning.

5. Create a new private workspace and run the first compiler-enabled scan with
   detector commit 2574b6e. Preserve the first result even if it is a workflow
   failure. Run with no network access. Do not alter scope, source, compiler,
   detector, or profile after the freeze.

6. Create a second private workspace from the same frozen inputs and replay the
   scan offline. Compare source-manifest, profile, scan, and candidate digests,
   compiler version, reportable file count, finding count, candidate count, and
   rule distribution. A mismatch leaves PILOT-009 incomplete.

7. Review every candidate privately against the pinned source, live program
   impact rules, known issues, and prior audits. Record hypothesis, evidence
   boundary, impact, reachability assumptions, duplicate status, state, reason,
   uncertainty, and review effort. Do not tune the scanner from these labels.
   Treat candidates as investigation leads, not vulnerabilities.

8. Write docs/research/PILOT_009_EVALUATION.md using aggregate public data only:
   public target identity and selection method, mapping verdict, compiler mode,
   reportable file count, total candidates and per-rule counts, aggregate review
   states, review effort, comparison with prior trials, limitations including
   unknown recall, restrictions observed, and the recommended next task. Omit
   private paths, hashes, candidate IDs, source excerpts, traces, and any
   candidate-specific explanation.

9. Update README.md, CHANGELOG.md, TASKS.md, docs/DEVELOPMENT_PLAN.md,
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
