# PILOT-007 development plan

Status: **IN PROGRESS**

## Goal

Evaluate Contract Holes on one independent, previously unseen Solidity target.
Use the released `1.1.1` scanner plus the completed `PRECISION-001` repairs.

This task measures generalization and review effort. It does not promise a
vulnerability, a bounty payment, audit completeness, or unknown-bug recall.
Freeze the first scan before any detector tuning based on the selected target.

## Completion questions

The evaluation must answer these questions:

1. Can the scanner process a second real project through the private workflow?
2. How many candidates require review, and which generic rules produce them?
3. How many candidates does the operator reject, investigate, or confirm?
4. Does each investigating or confirmed candidate contain useful evidence?
5. Which generic limitations should become later product tasks?

## Work boundary

Use a target that is independent of the OpenZeppelin Confidential Contracts
trial. Prefer a different team, codebase, dependency graph, and protocol model.

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

- `docs/research/PILOT_007_TARGET_SELECTION.md` with public selection evidence.
- `docs/research/PILOT_007_EVALUATION.md` with aggregate, redacted results.
- normal project status and handoff updates.

Keep these records only in the private workspace:

- target source and compiler dependencies.
- source manifests, scans, candidates, and review ledgers.
- candidate IDs, source paths, excerpts, traces, and review notes.
- possible vulnerability details or target-specific hypotheses.

## Development sequence

### 1. Freeze the project baseline

1. Read `AGENTS.md`, `TASKS.md`, `docs/DEVELOPMENT_PLAN.md`, this plan, and the
   prior M8 research documents.
2. Verify a clean `main` worktree at the handoff commit.
3. Confirm that `main` matches `origin/main` and that project CI is green.
4. Run the full test suite, the frozen audit evaluation, and historical bounty
   evaluation.
5. Verify the recorded hashes and permissions for the prior private workspaces.
6. Mark `PILOT-007` **IN PROGRESS** in `TASKS.md`.

Completion criterion: all public gates pass, and the prior target and private
workspaces remain unchanged.

### 2. Select an independent target

Research at least three current programs from official sources. Record the
review date and direct links. Do not clone or scan a candidate during this step.

Compare each candidate on these points:

- current program status and private reporting channel.
- explicit smart-contract scope and allowed testing methods.
- exact source-to-scope mapping.
- immutable Git revision or release identity.
- Solidity and supported compiler compatibility.
- exact, manageable dependency closure.
- known issues, prior audits, and program exclusions.
- useful overlap with several Contract Holes rules.
- no need for RPC, a fork, deployed-state access, or target interaction.
- independence from the first OpenZeppelin trial.

Reject a candidate if its rules are unclear or its official source lacks an
immutable revision. Also reject it if its scope does not map to exact files.
Safe compilation must not require target scripts or unpinned dependencies.

Write the comparison and selection to
`docs/research/PILOT_007_TARGET_SELECTION.md`. Include no vulnerability claims.

Completion criterion: one target has current rules, an exact revision, exact
scope, pinned dependencies, and a documented reason for selection. No source
acquisition or scan has occurred.

### 3. Request one consolidated authorization

Ask the operator to approve the complete target boundary once. Include the
program, rules review date, exact revision, reportable paths, dependency
identities, permitted download, analysis mode, and excluded actions.

Use this form with the selected values:

```text
I approve one-time network retrieval of [official repository] at [exact commit]
and its exact lockfile- or commit-pinned compiler dependencies. I approve local,
private, isolated, offline compiler analysis under the [program] rules reviewed
on [date], restricted to [exact scope] and [approved impacts]. I acknowledge
[program restrictions]. I do not approve RPC, forks, chain actions, proofs,
reports, exports, disclosure, submission, platform writes, or target contact.
```

Completion criterion: the operator approves the exact text. If any pinned value
changes, request a new consolidated authorization before acquisition.

### 4. Get and freeze the source

1. Create a new checkout under `../targets/` from the approved official origin.
2. Check out the exact approved commit in detached state.
3. Retrieve only the approved dependency commits or integrity-pinned packages.
4. Disable package scripts and do not execute target build, test, or deployment
   commands.
5. Verify the checkout is clean and record the source identity.
6. Set the target checkout read-only after all approved files are present.
7. Create a new private workspace under `../bounty-workspaces/`.
8. Add exact positive scope paths and compiler-only dependency paths to its
   bounty profile.
9. Run `holes bounty validate` and `holes bounty identify`.

Use Contract Holes isolated compilation. Do not load the target Foundry
configuration or environment credentials.

Completion criterion: the target, dependencies, scope, profile, source
manifest, permissions, and compiler version are exact and reproducible.

### 5. Run and replay the offline scan

Run one compiler-enabled scan in the new private workspace. Then create a
second new private workspace from the same profile and replay the scan offline.

Compare these values:

- source-manifest digest.
- normalized profile digest.
- scan digest.
- candidate-ledger digest.
- compiler version.
- reportable file count.
- candidate count and rule distribution.

Keep the first result unchanged. Do not tune detectors, source, scope, or
dependencies after seeing candidates. Record an initial workflow failure as a
result instead of hiding it.

Completion criterion: both scans complete with identical deterministic values,
or the evaluation records the exact reproducible blocker.

### 6. Review candidates privately

Review every candidate against the pinned source, current program impacts,
known issues, and published audits. Keep candidate-specific notes in a private
review brief outside this repository.

For each candidate, record:

- the scanner hypothesis and evidence boundary.
- the relevant in-scope impact, if one exists.
- reachability, authorization, trust, and state assumptions.
- duplicate or known-issue status.
- a recommended `rejected`, `investigating`, or `confirmed` state.
- the reason and remaining uncertainty.

Do not impersonate an operator decision. Present all proposed decisions in one
batch and ask the operator to confirm or change them. After confirmation, write
the decisions with `holes bounty review` and verify the review-ledger digest.

If there are no candidates, skip the decision checkpoint. Record undefined
precision and unknown recall.

Completion criterion: every candidate has an operator-confirmed private state,
or no candidates exist. No proof or report has started.

### 7. Evaluate generalization

Write `docs/research/PILOT_007_EVALUATION.md` with aggregate information only.
Record:

- target-selection method and public identity.
- reportable file count and compiler mode.
- total candidates and generic rule distribution.
- rejected, investigating, and confirmed counts.
- candidate precision only when the labels define it.
- review effort and workflow friction.
- comparison with the first trial at an aggregate level.
- limitations, including unknown recall.
- the recommended next product task.

A clean scan does not show that the target is safe. An all-rejected scan shows
review burden on this target, not universal scanner precision. A confirmed
candidate remains private and does not authorize a proof or report.

Convert a repeated generic gap into a later task only after the primary
evaluation is frozen. Do not change detector behavior inside `PILOT-007`.

Completion criterion: the evaluation answers every completion question without
private evidence, target source, or unsupported product claims.

### 8. Complete documentation and Git

Update these files to match the result:

- `README.md`.
- `CHANGELOG.md`.
- `TASKS.md`.
- `docs/DEVELOPMENT_PLAN.md`.
- `docs/NEXT_SESSION_PROMPT.md`.
- relevant rule limitations if the evaluation changes a documented boundary.

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check
```

Inspect the staged file list and diff for private paths, candidate details,
target source, credentials, and generated private artifacts. Commit one coherent
change, push `main`, and verify project CI.

Completion criterion: public tests and evaluations pass, documentation matches
the result, Git is clean, `main` matches `origin/main`, and CI is green.

## Task completion gate

`PILOT-007` is complete only when:

- the target is independent and its authorization boundary is exact.
- source and dependency acquisition matches the single approval.
- two private offline scans reproduce the same result.
- the first result remains frozen before detector tuning.
- every candidate has an operator-confirmed state, or no candidates exist.
- public documentation contains only aggregate and public information.
- no proof, report, export, disclosure, submission, chain action, platform
  write, or target contact occurred.
- all public validation gates and project CI pass.

## Stop conditions

Stop and request operator input when:

- one complete target authorization awaits approval.
- proposed candidate decisions await one batch confirmation.
- a target revision, scope, dependency, or rule changes after approval.
- a plausible candidate would need a proof, report, disclosure, or submission.
- safe progress requires RPC, a fork, chain activity, target contact, or an
  unapproved download.
- private evidence may have entered the repository or another public channel.

Do not stop for routine local development, testing, documentation, Git, or CI
work within the approved boundary.
