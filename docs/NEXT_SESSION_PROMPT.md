# Next-session starter prompt

Copy the text below into a new Codex session opened at the Contract Holes
repository root.

```text
Continue Contract Holes from the current repository state.

Workflow rule

Act as the coordinator and verifier. Do not implement production code yourself.
Use OpenCode for implementation with exactly this model:
opencode-go/deepseek-v4-flash

Start the development agent with:

/home/nux/.opencode/bin/opencode run --auto \
  -m opencode-go/deepseek-v4-flash \
  "Read docs/COMP_005_PLAN.md and execute it completely with the develop -> test -> docs -> Git workflow. Work autonomously until PASS, UNSATISFIED, or a documented stop condition. Do not delegate to another model."

After the agent finishes, independently review its diff, tests, documentation,
Git state, private-evidence boundary, and CI. If a repair is needed, write a
precise follow-up contract and send it to OpenCode with the same model; then
verify again. Do not silently implement the repair yourself.

Read first

- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/COMP_005_PLAN.md (authoritative next task)
- docs/PILOT_009_PLAN.md (original trial gate)
- docs/research/PILOT_009_TARGET_SELECTION.md
- docs/research/PILOT_009_EVALUATION.md
- docs/COMP_004_PLAN.md
- docs/EVALUATION.md

Current public state

- Release: 1.1.1.
- The last implementation/outcome commit before the doc-only COMP-005 handoff
  is afc702fa7980b5c90f658fce08a29ce7402cf079. Treat current Git output as
  authoritative and require clean main == origin/main before development.
- Public selection freeze: commit 649b923; CI 31723534741 passed.
- PILOT-009 unsatisfied record: commit afc702f; CI 31725057831 passed.
- Suite: 238 tests.
- Frozen audit: 33 positive and 31 safe labels at 1.0.
- Historical result: 0.933333 candidate precision, 1.0 supported recall, 1.0
  evidence completeness, result hash
  9bf60837d252bac17ba579c91a04a8d33fc5f0c9fcb5c8df59402be0397bdf90,
  decision go.
- PILOT-009 selected EulerSwap v2 at immutable commit
  81cf6dc988468fd56f690e6bc0e338a5be02d034. The exact frozen closure is five
  reportable plus 56 compiler-only Solidity files at exact compiler 0.8.27.
- Two preserved private workspaces reproduced the same schema-1.2 manifest and
  the same pre-scan compile blocker. No scan or candidate identity exists.
- The blocker is generic: isolated bounty staging uses libs = [] and only the
  tracked remappings.txt, so it cannot resolve a direct Foundry lib package
  prefix that the complete declared closure already contains.
- COMP-005 is the single NEXT task. It adds a narrow deterministic direct-lib
  remapping repair, publishes it with green CI, and replays the unchanged frozen
  EulerSwap closure twice before any completion claim.

Authority and privacy

The standing yolo direction covers public research, the already completed exact
downloads, and private local offline analysis. Do not ask for routine approvals.
No new target download, RPC, fork, chain action, transaction, deployment, proof,
report, export, disclosure, submission, bounty-platform write, or target contact
is authorized.

OpenCode may operate the existing local private workspace. Keep target source,
manifests, scans, candidates, reviews, paths, excerpts, and hashes outside the
repository and out of public summaries. Do not use another model or subagent for
private target work.

Verification duties

1. Confirm the agent used a generic test-first repair and did not load target
   configuration, execute forge remappings, enable library discovery, or expand
   the approved source closure.
2. Confirm explicit validated remappings retain precedence, synthesized mappings
   are deterministic, and undeclared imports still fail closed.
3. Confirm no profile/source-manifest schema or legacy identity changed when no
   derived mapping is needed.
4. Rerun the 238+ test suite, frozen audit evaluation, historical evaluation,
   and git diff check. Inspect all changed code and tests.
5. Verify the generic repair commit was pushed and CI passed before private
   replay.
6. Verify two new private offline replays used the unchanged 5+56 closure and
   produced matching identities. Review only aggregate public results; keep
   candidate evidence private.
7. Verify the final docs, clean worktree, main == origin/main, and green final CI.

Use unsigned commits if GPG requires interaction. Stop only at a condition in
docs/COMP_005_PLAN.md or when the authorization boundary must change.
```
