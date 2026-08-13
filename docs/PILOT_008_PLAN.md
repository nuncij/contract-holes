# PILOT-008 development plan

Status: **BLOCKED BY `REPAIR-007`**

## Goal

Select, authorize, and scan a new independent real-world target whose deployed
assets can be mapped exactly to a pinned immutable source revision. Use the
released `1.1.1` scanner plus the completed `PRECISION-001` repairs and the
generic defect fixes added during the `PILOT-007` completion repair.

This task measures generalization and review effort. It does not promise a
vulnerability, a bounty payment, audit completeness, or unknown-bug recall.
Freeze the first scan before any detector tuning based on the selected target.

## Why this task exists

`PILOT-007` was marked unsatisfied because its selected target (Silo Finance
v2/v3 tag `4.26.0`, commit `570a668a98a88a6a2b92697e7b9a3b1c6299dce7`) could
not be mapped exactly to the deployed in-scope assets. The repository's own
`DeployedSiloVersions.md` documented those assets as Silo version `3.5.0`
(commit `b1f428f1c3d5fc989974fd8e7b3b84180e05e31f`), so filename equality was
not sufficient. Silo is retained only as a research corpus. `PILOT-008` selects
a target where the deployed-source correspondence can be proved from official
records before analysis.

Before target selection starts, `REPAIR-007` must reproduce the Silo minimal
closure through the public scanner from a read-only Git-backed checkout,
strengthen the repair regressions, and correct the completion record. This is an
evidence-quality gate; it does not change the unsatisfied Silo verdict.

## Work boundary

Use a target independent of the OpenZeppelin Confidential Contracts trial and
of the Silo research corpus. Prefer a different team, codebase, dependency
graph, and protocol model.

Use public network access only for target selection and the approved one-time
source download. Use official program, repository, release, audit, and
documentation sources. After the download, keep analysis offline.

Keep source checkouts and all candidate evidence outside this repository. Use
private directories with mode `0700` and private files with mode `0600` where
POSIX permissions are available.

This task does not include RPC access, a fork, a chain transaction, a proof,
report creation, export, disclosure, submission, platform write, or target
contact. A later task needs separate authorization for any of these actions.

## Public and private records

Commit only these public records:

- `docs/research/PILOT_008_TARGET_SELECTION.md` with public selection evidence
  and the deployed-source mapping verdict.
- `docs/research/PILOT_008_EVALUATION.md` with aggregate, redacted results.
- normal project status and handoff updates.

Keep these records only in the private workspace:

- target source and compiler dependencies.
- source manifests, scans, candidates, and review ledgers.
- candidate IDs, source paths, excerpts, traces, and review notes.
- possible vulnerability details or target-specific hypotheses.

## Selection criteria

Research at least three current programs from official sources. Record the
review date and direct links. For each candidate, establish the exact
deployed-source mapping from official records (program resource pages,
repository release/version documentation, verified-source metadata) before
acquisition:

- current program status and private reporting channel;
- explicit smart-contract scope and allowed testing methods;
- exact source-to-scope mapping: each in-scope deployed asset corresponds to a
  pinned immutable Git revision or release, evidenced by program or repository
  records, not just matching filenames;
- immutable Git revision or release identity;
- Solidity and supported compiler compatibility;
- exact, manageable dependency closure;
- known issues, prior audits, and program exclusions;
- useful overlap with several Contract Holes rules;
- no need for RPC, a fork, deployed-state access, or target interaction;
- independence from the OpenZeppelin and Silo trials.

Reject a candidate if its rules are unclear, its official source lacks an
immutable revision, its scope does not map to exact deployed assets, or the
deployed-source correspondence cannot be evidenced. Safe compilation must not
require target scripts or unpinned dependencies.

Write the comparison, selection, and the deployed-source mapping verdict to
`docs/research/PILOT_008_TARGET_SELECTION.md`.

## Development sequence

### 1. Freeze the project baseline

1. Read `AGENTS.md`, `TASKS.md`, `docs/DEVELOPMENT_PLAN.md`, this plan, and the
   prior trial research documents.
2. Verify a clean `main` worktree and that `main` matches `origin/main`.
3. Run the full test suite, the frozen audit evaluation, and historical bounty
   evaluation.
4. Verify the recorded hashes and permissions for the prior private workspaces.
5. Mark `PILOT-008` **IN PROGRESS** in `TASKS.md`.

Completion criterion: all public gates pass, and the prior targets and private
workspaces remain unchanged.

### 2. Select and map a target

Follow the selection criteria above. Before requesting authorization, record
the deployed-source mapping evidence for the selected target so the
source-to-scope gate is resolved up front.

### 3. Request one consolidated authorization

Ask the operator to approve the complete target boundary once, using the same
form and boundary as `PILOT-007`.

### 4. Get and freeze the source

1. Create a new checkout under `../targets/` from the approved official origin.
2. Check out the exact approved commit in detached state.
3. Retrieve only the approved dependency commits or integrity-pinned packages.
4. Do not execute target build, test, or deployment commands.
5. Build a minimal dependency-closure checkout so only the submodules that
   intersect the approved compiler manifest are initialized. Record the full
   initial retrieval state honestly.
6. Verify the checkout is clean and record the source identity.
7. Make the entire checkout, including Git metadata, user-read-only under a
   private parent.
8. Create a new private workspace under `../bounty-workspaces/`.
9. Add exact positive scope paths and compiler-only dependency paths.
10. Run `holes bounty validate` and `holes bounty identify`.

Use Contract Holes isolated compilation. Do not load the target Foundry
configuration or environment credentials.

### 5. Run and replay the offline scan

Run one compiler-enabled scan, then a second private workspace replay with the
same profile. Compare source-manifest, profile, scan, and candidate digests,
compiler version, reportable file count, and candidate count/rule distribution.
Keep the first result frozen before any detector change. Record an initial
workflow failure as a result instead of hiding it.

### 6. Review candidates privately

Review every candidate against the pinned source, program impacts, known
issues, and audits. For each candidate record the scanner hypothesis and
evidence boundary, relevant in-scope impact or lack of one, reachability and
trust assumptions, duplicate/known-issue status, a recommended state, the
reason, and remaining uncertainty. Present proposed decisions in one batch for
operator confirmation, then record them with `holes bounty review`.

### 7. Evaluate generalization

Write `docs/research/PILOT_008_EVALUATION.md` with aggregate information only:
target-selection method and public identity, deployed-source mapping verdict,
reportable file count and compiler mode, total candidates and rule
distribution, rejected/investigating/confirmed counts, review effort, aggregate
comparison with prior trials, limitations including unknown recall, and the
recommended next product task.

### 8. Complete documentation and Git

Update `README.md`, `CHANGELOG.md`, `TASKS.md`, `docs/DEVELOPMENT_PLAN.md`,
`docs/NEXT_SESSION_PROMPT.md`, and the docs index to match the result. Run the
validation gates, inspect the staged diff for private data, run a
simplification review, commit, push `main`, and verify project CI.

## Task completion gate

`PILOT-008` is complete only when:

- the target is independent and its authorization boundary is exact;
- the deployed-source mapping is evidenced and recorded before scanning;
- source and dependency acquisition matches the single approval;
- two private offline scans reproduce the same result;
- the first result remains frozen before detector tuning;
- every candidate has an operator-confirmed state, or no candidates exist;
- public documentation contains only aggregate and public information;
- no proof, report, export, disclosure, submission, chain action, platform
  write, or target contact occurred;
- all public validation gates and project CI pass.

## Stop conditions

Stop and request operator input when:

- one complete target authorization awaits approval;
- proposed candidate decisions await one batch confirmation;
- a target revision, scope, dependency, or rule changes after approval;
- a plausible candidate would need a proof, report, disclosure, or submission;
- safe progress requires RPC, a fork, chain activity, target contact, or an
  unapproved download;
- private evidence may have entered the repository or another public channel.
