# PILOT-007 Evaluation

Trial date: 2026-08-13
Target: Silo Finance v2/v3 (`silo-finance/silo-contracts-v3` tag `4.26.0`)
Pinned commit: `570a668a98a88a6a2b92697e7b9a3b1c6299dce7`
Operator authorization: single consolidated approval on 2026-08-13
Status: **UNSATISFIED — Silo retained as a non-bounty research corpus.
`REPAIR-007` completed the completion-record evidence gap; the required
follow-up `PILOT-008` later completed before `PRECISION-002`.**

## Outcome

The post-repair operational run processed a previously unseen lending
and vaults protocol through the private offline compiler workflow. The scan
materialized 81 candidates; human review rejected all 81 after source
verification. No candidate is investigating or confirmed. This is an
operational result, not evidence that the target is free of vulnerabilities,
and it is not a bounty submission.

The completion repair proved that this operational result is **not an
untouched independent baseline** and that the trial did not meet its
target-selection gate. Silo is therefore kept only as a research corpus.

## Target-selection method

Selection research compared five current Immunefi programs using official
program, repository, release, and audit sources. Silo was selected because it
is a different team, codebase, dependency graph, and protocol model from the
first OpenZeppelin Confidential Contracts trial, has an immutable repository
tag, and names exact in-scope contract files. Details and the public comparison
are in [PILOT_007_TARGET_SELECTION.md](PILOT_007_TARGET_SELECTION.md).

## Post-repair operational evidence

| Record | Value |
| --- | --- |
| Scanner | Contract Holes `1.1.1` plus completed `PRECISION-001` repairs |
| Solidity compiler | `0.8.28+commit.7893614a.Linux.g++` (solc-bin verified) |
| Reportable files | 10 exact contract files at the pinned commit |
| Compiler-only dependencies | 124 exact, commit-pinned git-submodule Solidity files |
| Source manifest | `9e2a7faed9326d4db51b717222d9227f92f7e3909fb0cdf91d6b62378aeb8f84` |
| Scan | `9784d71e91ae86d4380c738badb2c1dfcfa9d9871425064c814b4237183825e6` |
| Candidate ledger | `8b1352ed188f4f2f6f93b7e365a9721c6f0a2204116b4e6eaa1a0109347f6b2f` |
| Review ledger | `3c58c01c81df6fe3c93c70e4d59c1b944360beaa289137c1cf80404519f72540` |

Two private workspaces used the identical profile and reproduced the identical
scan, candidate-ledger, and source-manifest digests. The target checkout and
frozen source-only evidence from the first trial were unchanged.

## Workflow friction and fixes

The target exposed three generic scanner defects. The implementation changed
before the preserved operational result was accepted:

1. Recursive AST walkers overflowed Python's recursion limit on large,
   deeply nested real-world contracts. All analysis walkers now traverse
   iteratively.
2. The signature domain analysis recursed without cycle detection across
   mutually recursive call arguments. `seen` state is now threaded through
   call-feature computation.
3. Custom error constructors (`revert Library.Error(...)`) and event
   emissions were classified as external-dynamic interactions, inflating
   reentrancy findings. Resolved member targets that are error or event
   definitions are now excluded from the call graph.

All 221 tests pass and the frozen synthetic and historical evaluation gates are
unchanged (`1.0` precision/recall on the synthetic corpus; `0.875` candidate
precision and `1.0` supported-class recall on the historical corpus). The
call-graph change altered detector behavior after target feedback. Two genuine
regressions cover the signature and call-graph repairs; `REPAIR-007`
strengthened their stable public evidence assertions and closed the completion
record.

## Completion repair results

A completion review and repair on 2026-08-13 closed the baseline,
source-mapping, private-review, acquisition-reproduction, regression, and
status-text findings.

1. **Untouched baseline reconstructed (reproducible blocker).** The
   released-plus-`PRECISION-001` scanner at selection commit
   `08050a14437abaf47ff45b90a1392a9fbc460a93` was run against the same approved
   Silo profile in two new private workspaces. Both fail with the identical
   `RecursionError` in the signature-domain analysis over the full closure. The
   untouched baseline is therefore a reproducible blocker, not a scan digest.
2. **Source-to-scope gate fails.** The deployed in-scope assets are Silo
   version `3.5.0` (commit `b1f428f1c3d5fc989974fd8e7b3b84180e05e31f`,
   2025-05-15), not the pinned tag `4.26.0` (commit
   `570a668a98a88a6a2b92697e7b9a3b1c6299dce7`, 2026-07-27). This is documented
   in the repository's own `DeployedSiloVersions.md` and the Immunefi scope
   addresses. The trial does not meet its target-selection gate.
3. **Minimal dependency closure reproduced through the scanner.** An earlier
   manual, hash-only checkout was not scanner-compatible because it lacked Git
   metadata. `REPAIR-007` built a new private checkout from existing local Git
   objects with only the three submodules intersecting the frozen 124-file
   compiler closure, retaining usable superproject Git metadata, then froze the
   full checkout (including that metadata) as user-read-only. The public
   `holes bounty validate` and `holes bounty scan` accept it and reproduce the
   source manifest, scan, and candidate ledger offline. The scan produces the
   same 81 findings with the same rule distribution and byte-identical finding
   objects; the only digest differences are profile-bound (program name,
   authorization note, and source root path), which change the candidate IDs but
   not the scan semantics. The historical over-retrieval of 87 submodule
   instances is recorded as an acquisition error.
4. **Private review records completed.** All 81 candidates now have a complete
   review-brief entry with hypothesis, impact, assumptions, reachability,
   duplicate/known-issue status, reason, and remaining uncertainty. All 81
   remain operator-confirmed `rejected`.
5. **Regressions strengthened and test cleanup complete.** Public-seam tests now
   cover signature-domain recursion termination and error/event/struct member
   call classification. The signature test compiles once and asserts the
   expected semantic result; the retained-positive test asserts exact stable
   path, line, kind, entry function, evidence, and target-provenance fields. The
   tests fail under their corresponding pre-fix implementations. The deep-AST
   compiler test uses `TemporaryDirectory` for its full lifecycle. The suite is
   221 tests; frozen gates unchanged.

Because the source-to-scope gate fails, `PILOT-007` is **UNSATISFIED**. Silo
remains a research-only validation corpus. `REPAIR-007` completion does not
change that verdict; it only unblocked the next independent target trial
(`PILOT-008`), which later completed before `PRECISION-002`.

## Results

| Measurement | Result |
| --- | ---: |
| Approved Solidity files | 10 |
| Compiler mode | Offline, staged reportable + compiler-only dependencies |
| Total candidates | 81 |
| Rule distribution | `SOL008` 50, `SOL005` 26, `SOL009` 3, `SOL011` 1, `SOL003` 1 |
| Rejected / investigating / confirmed | 81 / 0 / 0 |
| Review decisions | 81 human rejections (Nunc), operator-confirmed |
| Candidate precision on this target | 0/81 (all rejected) |
| Recall | Unknown (no independent ground truth) |

## Review families

All 81 candidates were rejected after verifying each finding against the
pinned source. The rejections group into generic families:

- deployment-sequence findings on freshly created clones and factories before
  registration;
- reentrancy traces whose flagged interactions are read-only view/staticcall
  reads, with the only state-changing external call occurring after the writes
  and protected by downstream guards;
- role-gated functions (owner, curator, allocator, timelock, hook receiver)
  whose writes are protected and whose call targets are trusted or
  governance-configured;
- call-target traces where the target resolves to a deployment-fixed
  immutable asset or a freshly created clone rather than a user-controlled
  address;
- read-only view functions with caller-supplied parameters that are
  caller-harm-only;
- an initializer already protected by a one-time guard;
- a governance-configured delegatecall list rather than attacker-controlled
  state.

These families are generic and match the first trial's observed precision
modes. They are candidates for later product tasks, not justifications for
target-specific suppressions.

## Comparison with the first trial

| | First trial (OpenZeppelin Confidential) | Second trial (Silo) |
| --- | --- | --- |
| Target model | fhEVM encrypted library | Lending / vaults protocol |
| Reportable files | 22 | 10 |
| Compiler | `0.8.27` | `0.8.28` |
| Candidates | 47 post-repair | 81 |
| Confirmed | 0 | 0 |
| Review outcome | 47 rejected, none confirmed | 81 rejected, none confirmed |

Both trials were all-rejected after review. The second trial confirms the
scanner can process a different protocol family and that the improved
detectors still produce a substantial review burden from generic false-positive
families.

## Recommended next product task

The completion-record repair (`REPAIR-007`) is complete: the Git-backed minimal
checkout reproduces the scan through the public scanner, and the regressions
assert stable public evidence. The required independent follow-up,
`PILOT-008`, later produced an untouched baseline whose deployed assets map
exactly to a pinned immutable source revision. The generic families observed
here are therefore available for `PRECISION-002` precision work. The
highest-value items are:

- distinguish custom error/event members from external interactions (already
  fixed in this trial, with regression coverage);
- recognize timelock-style authorization modifiers and view-only interaction
  facts when evaluating reentrancy ordering;
- treat governance-configured call lists and freshly deployed clones as
  non-user-controlled target provenance;
- keep read-only view-call arguments out of caller-controlled target taint
  when the call is a view/staticcall.

## Limitations

- The Silo result is a post-repair operational replay, not an untouched frozen
  trial; the untouched baseline is a reproducible scanner blocker.
- The source-to-scope gate failed: the pinned Silo tag does not correspond to
  the deployed in-scope assets. Silo is a research corpus, not a bounty trial.
- Recall is unknown: the trial provides no independent ground-truth labels.
- An all-rejected scan does not show that the target is safe.
- A confirmed candidate would remain private and would not authorize a proof
  or report.
- Reviewer labels are from one reviewer and one target and are not independent
  ground truth.
- The historical acquisition over-retrieved 87 submodule instances; the later
  minimal checkout matches only the approved 124-file closure. A newer
  Git-backed minimal checkout (with superproject Git metadata, user-read-only)
  reproduces the scan through the public scanner.
- No proof, report, export, disclosure, submission, chain action, RPC, fork,
  or target contact occurred.
