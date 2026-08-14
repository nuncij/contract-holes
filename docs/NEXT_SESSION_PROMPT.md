# Next-session starter prompt

Copy the text below into a new Codex session opened at the Contract Holes
repository root.

```text
Continue Contract Holes from the current repository state.

Workflow rule

Act as the coordinator and verifier. Do not implement production code yourself.
Use OpenCode for implementation with exactly this model:
opencode-go/deepseek-v4-flash

No task is currently queued in TASKS.md. Confirm the current state before
starting any new work:

/home/nux/.opencode/bin/opencode run --auto \
  -m opencode-go/deepseek-v4-flash \
  "Read TASKS.md and docs/DEVELOPMENT_PLAN.md. If a task is marked NEXT or IN PROGRESS, execute it completely with the develop -> test -> docs -> Git workflow. Otherwise verify the repository state and report PASS or UNSATISFIED. Do not delegate to another model."

After the agent finishes, independently review its diff, tests, documentation,
Git state, private-evidence boundary, and CI. If a repair is needed, write a
precise follow-up contract and send it to OpenCode with the same model; then
verify again. Do not silently implement the repair yourself.

Read first

- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/COMP_005_PLAN.md
- docs/PILOT_009_PLAN.md
- docs/research/PILOT_009_TARGET_SELECTION.md
- docs/research/PILOT_009_EVALUATION.md
- docs/COMP_004_PLAN.md
- docs/EVALUATION.md

Current public state

- Release: 1.1.1.
- COMP-005 completed on 2026-08-14: repair commit 04781a9, CI run
  31787480206 passed both Quality and Reproducible package. No task is
  currently queued.
- PILOT-009 completed on 2026-08-14: the generic direct-library remapping
  repair closed the fixed-detector compile blocker, and two new private offline
  replays of the unchanged frozen EulerSwap closure (five reportable plus 56
  compiler-only files, schema 1.2, Solidity 0.8.27) reproduced byte-identical
  profile, source-manifest, scan, and candidate-ledger identities. All 25
  candidates received a private review decision.
- Suite: 248 tests.
- Frozen audit: 33 positive and 31 safe labels at 1.0.
- Historical result: 0.933333 candidate precision, 1.0 supported recall, 1.0
  evidence completeness, result hash
  9bf60837d252bac17ba579c91a04a8d33fc5f0c9fcb5c8df59402be0397bdf90,
  decision go.

Authority and privacy

The standing yolo direction covers public research, the already completed exact
downloads, and private local offline analysis. Do not ask for routine approvals.
No new target download, RPC, fork, chain action, transaction, deployment, proof,
report, export, disclosure, submission, bounty-platform write, or target contact
is authorized.

OpenCode may operate the existing local private workspaces. Keep target source,
manifests, scans, candidates, reviews, paths, excerpts, and hashes outside the
repository and out of public summaries. Do not use another model or subagent for
private target work.

Verification duties

1. Confirm the worktree is clean and main == origin/main before starting.
2. Rerun the 248+ test suite, frozen audit evaluation, historical evaluation,
   and git diff check. Inspect all changed code and tests.
3. If new work starts, confirm it does not load target configuration, execute
   forge remappings, enable library discovery, expand an approved source
   closure, change frozen identities, or expose private evidence.
4. Verify any commit was pushed and CI passed before claiming completion.
5. Review only aggregate public results; keep candidate evidence private.
6. Verify the final docs, clean worktree, main == origin/main, and green CI.

Use unsigned commits if GPG requires interaction. Stop at a documented stop
condition in the relevant plan or when the authorization boundary must change.
```
