# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Objective

Start PILOT-009 with the develop -> test -> docs -> Git workflow. PRECISION-002
is COMPLETE: detector commit 2574b6e is pushed to main and GitHub CI run
31720097982 passed both Quality and Reproducible package. Validate that commit
on a genuinely untouched real-world target that is not OpenZeppelin, Silo, or
Olas. Follow docs/PILOT_009_PLAN.md as the authoritative scope. Preserve every
existing positive, frozen corpus identity, label, threshold, split, and public
evidence contract. Do not copy private target code or evidence into the
repository.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/PILOT_009_PLAN.md (authoritative scope)
- docs/PRECISION_002_PLAN.md
- docs/COMP_004_PLAN.md
- docs/research/PILOT_008_EVALUATION.md (prior trial)
- docs/EVALUATION.md
- this handoff

Treat current command output as authoritative for mutable state.

Project state

- Release: 1.1.1.
- PRECISION-002 is COMPLETE on commit 2574b6e, pushed to main; GitHub CI run
  31720097982 passed Quality and Reproducible package.
- Suite: 238 tests.
- Frozen synthetic evaluation: 33/33 positive labels and 31/31 safe labels at
  1.0.
- Historical candidate precision: 0.933333; supported-class recall: 1.0;
  evidence completeness: 1.0; decision: go.
- Final fresh private offline replay exact-match with Solidity 0.8.28: ten
  reportable files, 59 findings/candidates (SOL003=1 SOL005=13 SOL008=41
  SOL009=3 SOL011=1), 22 removed and none added. These are investigation leads,
  not vulnerabilities and not bounty submissions.
- PILOT-009 is QUEUED; it validates detector commit 2574b6e on a genuinely
  untouched target that is not OpenZeppelin, Silo, or Olas.

Authorization boundary (standing, do not re-ask)

Public research and one-time exact-source/dependency downloads plus private
offline analysis are authorized under the operator's standing yolo direction.
Do not ask for repeat approvals within this boundary; ask only if the boundary
itself must change. No RPC, chain/fork/transaction, proof, report, export,
disclosure, submission, bounty-platform write, or target contact is authorized.
Do not download source until the selection record establishes an exact mapping.
Do not scan until the pre-scan freeze is complete.

Private evidence boundary

Keep target source and all candidate evidence private. Do not send private
source, paths, candidate IDs, source excerpts, traces, or records to OpenCode,
delegated agents, or another secondary model or service. The primary session
can inspect them only through approved local tools. Cheaper agents can handle
public research and public documentation. Do not put private evidence in
fixtures, tests, commits, documentation, or logs intended for sharing. No
target-specific detector rule, project name, contract name, function name,
constant, or path is allowed.

Required behavior

Select and map a target per the plan: research at least three current programs
from official sources, establish the exact deployed-source mapping from
official records before source download, and record the verdict in
docs/research/PILOT_009_TARGET_SELECTION.md. Reject a target that cannot be
mapped exactly to a pinned immutable revision. Download only that pinned source,
then record the exact compiler closure and one supported Solidity release with
--compiler-version. Freeze the target revision, compiler closure, compiler
version, and scope before the first scan. Run one private offline
compiler-enabled scan, keep the
first result frozen, run a deterministic replay in a second private workspace,
and compare digests, compiler version, file count, and candidate
count/rule distribution. Review candidates without prior tuning labels and
record their states with holes bounty review. Write
docs/research/PILOT_009_EVALUATION.md with aggregate information only.

Workflow

1. Verify a clean main worktree that matches origin/main. Confirm no scanner
   code or test changed after detector commit 2574b6e.
2. Run the full suite, the frozen audit evaluation, and the historical bounty
   evaluation; record the results.
3. Select and map a target; record the deployed-source mapping verdict.
4. Download the pinned source, record the exact compiler closure, and create the
   immutable pre-scan freeze. Commit and push the public selection/status record
   and verify CI before the first scan.
5. Create a new private workspace, add exact scope and compiler-only dependency
   paths, and run holes bounty validate.
6. Run the private offline scan and the deterministic replay.
7. Review candidates without prior tuning labels and record their states.
8. Write the aggregate evaluation.
9. Update README.md, CHANGELOG.md, TASKS.md, docs/DEVELOPMENT_PLAN.md,
   docs/NEXT_SESSION_PROMPT.md, and the docs index. Inspect the staged diff for
   private material. Run the validation gates, a simplification review, commit,
   push main, and verify project CI. Mark PILOT-009 COMPLETE in TASKS.md only
   when every plan completion gate passes.

Validation gates

PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check

Stop only if the deployed-source mapping cannot be evidenced from official
records, a target revision/scope/dependency/compiler/rule changes after the
freeze, a plausible candidate would need a proof, report, disclosure, or
submission, safe progress requires RPC, a fork, chain activity, target contact,
or an unapproved download, private evidence may have entered the repository or
another public channel, or the authorization boundary itself must change.
```
