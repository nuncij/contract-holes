# M8 OpenZeppelin trial

Trial date: 2026-08-10

## Outcome

The first authorized external trial completed successfully and produced no
Contract Holes candidates. This is an operational result, not evidence that the
target is free of vulnerabilities.

The operator approved private, local, source-only analysis of OpenZeppelin
Confidential Contracts `v0.4.0`. Immediately before acquisition, the live
[program rules](https://immunefi.com/bug-bounty/openzeppelin/information/),
[scope](https://immunefi.com/bug-bounty/openzeppelin/scope/), and
[resource boundary](https://immunefi.com/bug-bounty/openzeppelin/resources/)
still named commit `7ac7cee5fec408dc81b31121f90417dfd87f3d13`, excluded mocks and examples,
and prohibited deployed-network testing.

No contract call, RPC, fork, transaction, proof, report, export, disclosure,
project contact, or platform submission occurred.

## Frozen evidence

The target was checked out at the exact bounty-pinned commit in detached-HEAD
state. The worktree was clean. The private workspace was outside both the
target and Contract Holes repositories, with a mode-`0700` directory and
mode-`0600` records.

| Record | Value |
| --- | --- |
| Scanner | Contract Holes `1.1.1` |
| Profile | `0ac2b8475b99c1e7b76e7e535be2f28d8afa081c041e58f6cf2bde45477f295b` |
| Source manifest | `e19eed85d8c5473beab0c8de7740a2f06c2d32adf9347127ba88d671023f8243` |
| Source set | `af7dd43c3440b85a6ea158e1a8a4986f5d8164430811f721d5ad020dae5a7681` |
| Scan | `90a883e42a140cfe528f11f13cbfeba4924306aacca8f13c41ab0d19bef52824` |
| Candidate ledger | `d707cd068e4253a960c2196a20ab35113a07f6e916115e4423cd519b4a815fc8` |

The scan consumed the 22 exact non-mock Solidity paths recorded in
[the target selection](M8_TARGET_SELECTION.md). Compiler analysis was disabled
as approved. Repeating the scan produced the same logical identities and was
accepted without replacing the immutable records.

## Measurements

| Measurement | Result |
| --- | ---: |
| Approved Solidity files | 22 |
| Scanner findings | 0 |
| Candidate observations | 0 |
| Human confirm/reject decisions | 0 / 0 |
| Proofs, reports, approvals, or exports | 0 |
| Scan wall time | 0.82 seconds |
| Scan maximum resident memory | 25,720 KiB |
| Checkout-to-candidate-ledger interval | 148 seconds |

The 148-second interval comes from local record timestamps and includes source
verification, profile creation, audit extraction, scanning, replay, and
candidate materialization. It excludes earlier program research, operator
approval time, and this written evaluation.

Four repository audit reports, totaling 57 pages, were extracted locally for
prior-disclosure checks. Because the candidate ledger was empty, no
candidate-specific audit match was required. The reports show that earlier
releases had FHE overflow and handle-allowance findings. Those reports are
important evidence of domain-specific risk, but they do not establish a defect
in the pinned `v0.4.0` release.

## Comparison with existing evaluations

| Evaluation | Ground truth | Result that can be claimed |
| --- | --- | --- |
| Synthetic `audit-1` | 33 positive and 31 safe labels | `1.0` precision and recall on the curated regression corpus |
| Historical `m7-history-1` | 10 disclosed cases from 10 projects | `0.875` candidate precision and `1.0` supported-class recall |
| OpenZeppelin real trial | No independent labels for the pinned release | 22 files scanned, zero candidates; precision undefined and recall unknown |

There were zero observed false-positive candidates in this trial. That is not a
precision score because the denominator is zero. A clean scan also provides no
way to count false negatives. The result therefore does not strengthen the
project's accuracy claims beyond proving that the authorization, source
identity, scope, privacy, deterministic replay, and empty-triage paths worked on
a real repository.

## Observed gaps and decisions

1. Source-only mode provided no compiler AST, inheritance, call-graph,
   data-flow, or executable-proof evidence. The target imports dependencies that
   are not reportable bounty assets, while the current profile treats every
   admitted compiler source unit as part of the approved scan scope.
2. Contract Holes does not model fhEVM encrypted handles, ACL allowances, or
   non-reverting confidential-operation failures. No FHE-specific rule is added
   from this trial because there is no confirmed current vulnerability to
   specify or test.
3. Pinning 22 individual files was verbose but safe. Positive-only scope remains
   preferable to adding exclusion globs after one trial.

Only the first gap becomes a product task: design a separate, immutable,
read-only compiler-dependency boundary that cannot produce reportable findings
or silently expand bounty scope. The other limitations remain explicit accepted
risks until another authorized trial supplies stronger evidence.

## Decision

M8 passes its release gate. The authorized target and rules were pinned before
analysis, private deterministic evidence was produced, every candidate was
accounted for, no unsafe or external action occurred, and the sole accepted
workflow gap is recorded as a testable backlog item.
