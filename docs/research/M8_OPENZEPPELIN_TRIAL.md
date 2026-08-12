# M8 OpenZeppelin trial

Trial date: 2026-08-10
Review date: 2026-08-11
Handoff update: 2026-08-12
Candidate resolution: 2026-08-12

## Outcome

The first authorized external, source-only trial completed successfully and
produced no Contract Holes candidates. This is an operational result, not
evidence that the target is free of vulnerabilities. A separately approved
offline compiler follow-up is recorded below.

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

## Compiler-enabled follow-up

The operator separately approved local, private, offline compiler analysis of
the same pinned commit. The profile retained the 22 reportable paths and added
exactly 58 compiler-only Solidity dependencies. The dependencies were acquired
once at pinned Git or package-lock identities, verified locally, and were never
eligible to produce a reportable finding. The subsequent scans were offline.

| Record or tool | Value |
| --- | --- |
| Scanner | Contract Holes `1.1.1` plus the unreleased `COMP-003` boundary |
| Solidity compiler | `0.8.27+commit.40a35a09.Linux.g++` |
| Compiler SHA-256 | `b9977d500c17cba6f0032ca939ef98c4decf6363f19f386d05fb02f708115264` |
| Profile | `ef8439b4b14dacc5d9c8ce1450924c19194b2d3b4e8f308cf3ff4410b3384a9d` |
| Source manifest | `f40f1cee224101bf440fe07514ec34f92d2f02a283b1b373d6eec9b3dac74604` |
| Source set | `550251d65a1d6d29856a2b1a66e847f481633a61913d14e674e4a3f08a16e1da` |
| Compiler-dependency set | `0837f1adb6cae49fdc2aabd3e7af5debfed1f299bc92fb2e36e8e1094bb2597a` |
| Scan | `8fa3093b06c7bb23710f2d663d728032bc7eb107fb82513982b8560137483433` |
| Candidate ledger | `889e58b1f0cf91a9db4e011882a40a2b7455e90aeaa68e0e600bda1a10a5d15e` |
| Review ledger | `0a321f9e919175b8879019d1b80996a434bd35b9866d2c214d2750ccd162f238` |

The canonical scan compiled 22 reportable files, materialized 51 candidates,
and initially left all 51 in review state `new`. The operator later approved
source-backed decisions that rejected 50 and retained one in state
`investigating`. On 2026-08-12 the final candidate was also rejected after the
focused `PILOT-006` analysis described below. All 51 candidates are now
rejected; none is confirmed. Candidate details and reasons remain only in the
mode-`0600` private workspace.

The first canonical pass took 103.95 seconds and used at most 1,176,856 KiB of
resident memory. An immutable replay reproduced the scan digest in 79.81
seconds and used at most 1,177,080 KiB. Both measured runs sent and received
zero socket messages.

The real compiler workload exposed two producer defects before the result was
accepted:

1. Several rules emitted alternative traces with the same stable finding
   fingerprint. The JSON reporter correctly rejected the duplicate identity.
   The scanner now keeps the first representative in deterministic order.
2. Compiler traces contained absolute local paths in nested metadata. The
   bounty boundary now converts nested `path` evidence to target-relative paths
   and fails closed for paths outside the target. The diagnostic record remains
   private; the canonical result was produced in a fresh immutable workspace
   and contains no target-root literal.

Neither fix changes the fingerprint definition or treats a candidate as a
confirmed vulnerability. The completed review grouped the 51 rejected
candidates into five observed precision failures:

- 27 traces treated pure/internal calls or user-defined value-type conversions
  as external interactions;
- eight callback traces paired an intentional, previously audited callback with
  an infeasible state-write branch;
- 12 call-target traces treated intended generic interfaces, callbacks, or
  immutable deployment configuration as uncontrolled privileged targets;
- three authorization traces missed a role check or a caller-owned mapping key;
- one reentrancy-ordering trace treated an immutable, interface-checked
  deployment target as callback-capable and did not recognize that the
  in-flight state is unreachable to reentrant entry points during the window.

The final candidate's exact identity and evidence remain private. These labels
justify generic safe fixtures and precision work, not target-specific or
FHE-name suppressions.

On 2026-08-12, the operator granted standing authorization for local, private,
isolated, offline analysis and proof work on this exact pinned trial.
`PILOT-006` used that authorization the same day. Focused trust-boundary
analysis of the pinned reference integration showed that no untrusted actor can
reach a callback during the reported interaction window. An offline mechanical
enumeration of the exact pinned dependency closure, compiled read-only with
the pinned compiler, confirmed that every external call in the window targets
deployment-fixed fhEVM predeploys, the immutable deployment-configured target,
or read-only view/staticcall reads, with zero actor-controlled targets. The
existing bounty-proof workflow could not test this decisive question without
inventing setup facts, so proof execution is recorded as unsupported rather
than run. The human decision rejected the candidate. RPC, chain activity,
target contact, report export, disclosure, and submission remained outside the
authorization and did not occur.

## Comparison with existing evaluations

| Evaluation | Ground truth | Result that can be claimed |
| --- | --- | --- |
| Synthetic `audit-1` | 33 positive and 31 safe labels | `1.0` precision and recall on the curated regression corpus |
| Historical `m7-history-1` | 10 disclosed cases from 10 projects | `0.875` candidate precision and `1.0` supported-class recall |
| OpenZeppelin source-only trial | No independent labels for the pinned release | 22 files scanned, zero candidates; precision undefined and recall unknown |
| OpenZeppelin compiler trial | 51 rejected, none confirmed | False-positive modes measured; candidate precision 0/51 on this target and recall unknown |

The source-only phase had no candidates, so its precision is undefined and its
recall is unknown. The compiler phase now has 51 reviewed false positives and
no unresolved candidates, giving a measured candidate precision of 0/51 on
this target. Neither phase provides ground truth for counting false negatives,
so recall remains unknown.

## Observed gaps and decisions

1. Source-only mode provided no compiler AST, inheritance, call-graph,
   data-flow, or executable-proof evidence. The target imports dependencies that
   are not reportable bounty assets, while the profile implementation at trial
   time treated every admitted compiler source unit as part of approved scan
   scope.
2. Contract Holes does not model fhEVM encrypted handles, ACL allowances, or
   non-reverting confidential-operation failures. No FHE-specific rule is added
   from this trial because there is no confirmed current vulnerability to
   specify or test.
3. Pinning 22 individual files was verbose but safe. Positive-only scope remains
   preferable to adding exclusion globs after one trial.

The first gap became product task `COMP-003`, which enabled the compiler
follow-up without changing the frozen source-only evidence. The follow-up then
produced two regression-backed implementation fixes: stable-identity
coalescing and nested evidence-path normalization. FHE semantics and verbose
positive-only scope remain explicit limitations. `PILOT-005` recorded decisions
for every candidate. `PILOT-006` used the recorded local-work authorization to
resolve the one investigating candidate, which is now rejected. `PRECISION-001`
converts the 51 rejected labels into generic safe fixtures and minimal
detector fixes.

## Decision

M8 passes its release gate. The authorized target and rules were pinned before
analysis, private deterministic evidence was produced, every candidate was
accounted for, and no target, chain, proof, report, export, disclosure, or
submission action occurred. The sole initial workflow gap was recorded as a
testable backlog item. `COMP-003` later closed that gap, and the separately
approved compiler trial reproduced its private scan and candidate records
without changing the source-only evidence. Human review rejected all 51
candidates; none is a confirmed vulnerability.
