# PILOT-009 development plan

Status: **UNSATISFIED. The public selection gate passed for the EulerSwap v2
Ethereum subset at commit `81cf6dc988468fd56f690e6bc0e338a5be02d034`.
Euler's pinned first-party verification record maps five deployed components to
that commit, and the exact pinned source with its recursive submodule closure
was acquired, enumerated (five reportable and 56 compiler-only files), and
frozen user-read-only. Both private workspaces then failed deterministically at
the compile stage: the fixed detector commit `2574b6e` cannot reproduce
Foundry's automatic submodule remapping, so the frozen closure cannot be
compiled and no scan or candidate identity exists. EulerSwap is retained as a
research corpus; [COMP-005](COMP_005_PLAN.md) is the queued generic repair and
private re-scan task.**

## Goal

Validate the `PRECISION-002` detector commit `2574b6e` on a genuinely untouched
real-world target that is not OpenZeppelin, Silo, or Olas. Run the scanner at
detector commit `2574b6e` from a frozen target
baseline, review candidates privately, replay deterministically, and publish
only an aggregate evaluation.

This task measures generalization and review effort. It does not promise a
vulnerability, a bounty payment, audit completeness, or unknown-bug recall.
Freeze the first scan before any detector tuning based on the selected target.

## Why this task exists

`PRECISION-002` completed the generic false-positive reduction but validated
its fixes against a target whose labels it had already observed. `PILOT-009`
is the required validation on a genuinely untouched target. It is also the
standing rule: do not measure the fixes only against the corpus that inspired
them.

## Work boundary

The standing yolo direction authorizes public research, one-time exact-source
and dependency downloads, and private offline analysis.
No RPC, chain/fork/transaction, proof, report, export, disclosure, submission,
bounty-platform write, or target contact is authorized. Do not scan or download
until the target selection record establishes an exact deployed-source mapping.

Keep source checkouts and all candidate evidence outside this repository. Use
private directories with mode `0700` and private files with mode `0600` where
POSIX permissions are available.

OpenCode with `opencode-go/deepseek-v4-flash` is the assigned development agent.
It can operate the local private workspace for this task. Keep target source and
candidate evidence outside this repository and out of public documentation,
commits, remote messages, and reports. Do not delegate this private work to any
additional model or service.

## Selection criteria

Research at least three current programs from official sources. Record the
review date and direct links. Before source acquisition, establish the exact
deployed-source mapping from official program records, repository releases, or
verified-source metadata:

- current program status and private reporting channel.
- explicit smart-contract scope and allowed testing methods.
- exact source-to-scope mapping: each selected deployed asset corresponds to a
  pinned immutable Git revision or release. Program or repository records must
  support the mapping. Matching filenames are not sufficient.
- immutable Git revision or release identity.
- Solidity version and supported compiler compatibility.
- exact, manageable dependency closure.
- known issues, prior audits, and program exclusions.
- useful overlap with several Contract Holes rules.
- no need for RPC, a fork, deployed-state access, or target interaction.
- independence from the OpenZeppelin, Silo, and Olas trials.

Reject a candidate if its rules are unclear, its official source lacks an
immutable revision, its scope does not map to exact deployed assets, or the
deployed-source correspondence cannot be evidenced. Safe compilation must not
require target scripts or unpinned dependencies.

## Development sequence

### 1. Freeze the project baseline

1. Read `AGENTS.md`, `TASKS.md`, `docs/DEVELOPMENT_PLAN.md`, this plan, and the
   prior trial research documents.
2. Verify a clean `main` worktree that matches `origin/main`. Confirm no scanner
   code or test changed after detector commit `2574b6e`.
3. Run the full test suite, the frozen audit evaluation, and historical bounty
   evaluation.
4. Verify the recorded hashes and permissions for the prior private workspaces.
5. Mark `PILOT-009` **IN PROGRESS** in `TASKS.md`.

Completion criterion: all public gates pass, and the prior targets and private
workspaces remain unchanged.

### 2. Select and map a target

Follow the selection criteria above. Before any download, record the
deployed-source mapping evidence for the selected target so the source-to-scope
gate is resolved up front. Write the comparison, selection, and mapping verdict
to `docs/research/PILOT_009_TARGET_SELECTION.md`.

### 3. Download source and freeze the compiler closure

Download the selected pinned source once. Inspect its compiler metadata offline.
Determine the reportable paths and compiler-only dependency paths. Hash each
set separately. Use the `COMP-004` schema `1.2` compiler pin. Do not execute
target build, test, or deployment commands.

### 4. Immutable pre-scan freeze

Record the target revision, compiler closure, compiler pin, profile scope, and
program rules before the first scan. The freeze is immutable: no detector
change, scope change, or revision change after it. Download only missing
integrity-pinned dependencies after the closure is known.

Commit the public selection record and `IN PROGRESS` status before the first
scan. Keep private hashes and target evidence outside the repository. Push the
public freeze commit and verify CI.

### 5. Private offline scan

Run one compiler-enabled scan in a new private workspace. Keep the first result
frozen before any detector change. Record an initial workflow failure as a
result instead of hiding it.

### 6. Deterministic replay

Replay the scan in a second private workspace with the same profile. Compare
source-manifest, profile, scan, and candidate digests, compiler version,
reportable file count, and candidate count/rule distribution.

### 7. Fixed-detector review

Review every candidate against the pinned source, program impacts, known
issues, and audits before any aggregate result is written. Do not show the
reviewer prior target-derived labels or tuning outcomes before the decision.
The reviewer can use the current finding and rule evidence. Do not tune the
detector against these labels. Record the hypothesis, evidence boundary,
possible impact, reachability assumptions, duplicate status, recommended state,
reason, and uncertainty. Record decisions privately. Keep candidate IDs, paths,
excerpts, and target-specific evidence out of the repository.

### 8. Public aggregate evaluation

Write `docs/research/PILOT_009_EVALUATION.md` with aggregate information only:
target-selection method and public identity, deployed-source mapping verdict,
reportable file count and compiler mode, total candidates and rule
distribution, rejected/investigating/confirmed counts, review effort, aggregate
comparison with prior trials, limitations including unknown recall, and the
recommended next product task.

### 9. Complete documentation and Git

Update `README.md`, `CHANGELOG.md`, `TASKS.md`, `docs/DEVELOPMENT_PLAN.md`,
`docs/NEXT_SESSION_PROMPT.md`, and the docs index to match the result. Run the
validation gates, inspect the staged diff for private data, run a
simplification review, commit, push `main`, and verify project CI.

## Task completion gate

`PILOT-009` is complete only when:

- the target is genuinely untouched and independent of the OpenZeppelin, Silo,
  and Olas trials.
- official records establish the exact deployed-source mapping before source
  download, and the exact compiler closure is frozen before scanning.
- an immutable pre-scan freeze precedes the first scan.
- the public selection and status commit precedes the first scan.
- two private offline scans reproduce the same source, scan, and candidate
  identities.
- every candidate has a recorded state, or no candidates exist.
- review is independent of tuning labels and the public evaluation is aggregate
  only.
- no proof, report, export, disclosure, submission, chain action, platform
  write, or target contact occurred.
- all public validation gates and project CI pass.

## Stop conditions

Stop when:
- a target revision, scope, dependency, compiler, or rule changes after the
  pre-scan freeze.
- a plausible candidate would need a proof, report, disclosure, or submission.
- safe progress requires RPC, a fork, chain activity, target contact, or an
  unapproved download.
- private evidence may have entered the repository or another public channel.
- the deployed-source mapping cannot be evidenced from official records.
