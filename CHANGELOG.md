# Changelog

All notable project changes are recorded here. Versions follow semantic
versioning; public JSON/SARIF schemas have their own compatibility rules.

## Unreleased

### Documentation

- Added a dedicated `PRECISION-001` development plan with test seams, ordered
  red-to-green slices, false-negative guardrails, validation gates, and stop
  conditions.
- Added a copy-ready next-session prompt with the current private-trial state,
  authorization boundary, ordered work, and completion checks.
- Added the `PILOT-007` plan for independent target selection, one consolidated
  authorization, deterministic private replay, review, and redacted evaluation.
- Recorded standing authorization for local, private, isolated, offline work on
  `PILOT-006`. Target-related network activity, report export, disclosure, and
  submission remain outside that authorization.

### Bounty workflow

- Added repeatable `--compiler-dependency` paths to bounty initialization and
  source identification. These Solidity units are separately hashed, staged only
  for fixed offline compilation, and cannot produce reportable findings.
- Added additive normalized profile and source-manifest schemas `1.1`; existing
  profiles without compiler-only dependencies retain schema `1.0` digest
  material and behavior.
- Reject dependency tampering, traversal, symlinks, overlap with reportable
  source units, unsafe imports, and findings attributed outside reportable scope.
- Keep all top-level and nested bounty evidence paths relative to the approved
  target root before writing a private record.

### Analysis

- Coalesce deterministic alternative evidence with the same fingerprint before
  report rendering, preserving the first representative trace and the frozen
  fingerprint definition.
- Keep compiler-resolved pure calls out of reentrancy interaction facts while
  retaining their external-target evidence.
- Carry `if`/`else` branch context through internal calls, preserve immutable
  target provenance through aliases and helper parameters, and keep
  `msg.sender` role self-grants reportable.

### Validation

- Reopened `PILOT-007` after completion review. The completion repair
  (2026-08-13) reconstructed the untouched baseline, which is a reproducible
  `RecursionError` blocker at selection commit `08050a1`; proved the
  source-to-scope gate fails (the deployed in-scope assets are Silo `3.5.0`,
  commit `b1f428f`, not the pinned `4.26.0`, commit `570a668`); reproduced the
  minimal 124-file compiler closure byte-for-byte from local Git objects;
  completed every private review-brief field for all 81 candidates; and added
  the missing regressions. `PILOT-007` is unsatisfied and Silo is retained only
  as a research corpus. A new independent target trial (`PILOT-008`) is required
  before `PRECISION-002` starts.

- Completed the first authorized external source-only trial against the exact
  bounty-pinned OpenZeppelin Confidential Contracts `v0.4.0` release. The
  private deterministic workflow scanned 22 files, produced zero candidates,
  and made no proof, report, submission, disclosure, or external target action.
- Recorded that the real clean scan has undefined precision and unknown recall,
  plus one observed backlog item for separating compiler-only dependencies from
  reportable bounty scope.
- Completed the separately approved offline compiler follow-up with 22
  reportable files, 58 exact compiler-only dependencies, and Solidity `0.8.27`.
  It materialized 51 private candidates. Human review rejected all 51 as false
  positives; no vulnerability was confirmed and no proof, report, export,
  disclosure, submission, chain action, or target interaction occurred.
- Resolved the final investigating candidate under the standing local offline
  authorization. Focused trust-boundary analysis plus a mechanical
  external-call enumeration of the pinned dependency closure showed no
  untrusted actor can reach a callback in the reported interaction window; the
  generic proof workflow could not test that question without inventing setup
  facts. The compiler trial's reviewer-labelled candidate precision is 0/51.
  The review is not independent ground truth, and recall remains unknown.
- Completed `PRECISION-001` with generic compiler fixtures for all five observed
  precision groups. Call classification now excludes pure/internal calls and
  user-defined value conversions, reentrancy traces retain minimal branch
  context, fixed target provenance remains visible, and authorization facts
  recognize caller-owned mapping writes. The fresh private rescan covered 22
  files and produced 47 remaining candidates: 23 call-semantics, 8
  branch-feasibility, 12 target-provenance, 3 authorization-context, and 1
  reentrancy-trust-boundary. The canonical private workspace and target
  checkout were unchanged.
- Completed the `PRECISION-001` follow-up review. Exact path, line, and evidence
  assertions now cover retained `SOL005`, `SOL008`, and `SOL009` positives. All
  216 tests and both frozen evaluation gates pass. A separate locked-down
  offline rescan reproduced the same 47 candidates and deterministic digests.
- Recorded a post-repair `PILOT-007` operational result against Silo Finance v2/v3 pinned
  to tag `4.26.0`. Two private workspaces reproduced identical digests over ten
  reportable files and 124 pinned compiler-only dependencies with Solidity
  `0.8.28`. The scan produced 81 candidates; the operator confirmed all 81
  rejections after source review, with zero investigating or confirmed.
- Fixed three generic scanner defects surfaced by the post-repair Silo run:
  analysis AST walkers now traverse iteratively instead of overflowing Python's
  recursion limit on large contracts; signature domain analysis is cycle-safe
  across mutually recursive call arguments; and custom error and event members
  are excluded from the call graph so reverted errors and emitted events are not
  treated as external interactions. All 221 tests and both frozen evaluation
  gates pass unchanged.
- Added public-seam regressions for signature-domain recursion termination and
  for error, event, and struct member call classification, and replaced the
  fixed `/tmp` deep-AST test directory with a per-test temporary directory.
- Recorded the observed generic false-positive families from the Silo research
  corpus as `PRECISION-002` work, gated on a new independent target trial
  (`PILOT-008`).

## 1.1.1 — 2026-08-10

### Security

- Updated the pinned release build toolchain to `setuptools 83.0.0` and
  `wheel 0.46.2`, addressing `GHSA-h35f-9h28-mq5c` and
  `GHSA-8rrh-rw8j-w5fx`. Contract Holes continues to have no runtime Python
  dependencies.

## 1.1.0 — 2026-08-09

M7 adds a local bounty research assistant with mandatory human decisions. It
does not claim audit completeness, automatic confirmation or submission,
exploitability, program eligibility, payout likelihood, or expected income.

### Bounty research workflow

- Added the versioned, default-private `bounty.toml` workspace contract and
  normalized JSON schema.
- Added `holes bounty init` and `holes bounty validate` with explicit
  authorization, immutable source identity, normalized scope, offline compiler
  policy, unknown-key rejection, and no-overwrite behavior.
- Kept submission, uploads, remote RPC, transactions, and automatic
  confirmation outside the command surface.
- Added `holes bounty identify` and `holes bounty scan` with exact clean Git or
  deterministic directory identity, default-deny scope, symlink/remapping
  rejection, private tamper-evident records, and relative finding paths.
- Added staged offline compiler analysis that ignores target Foundry
  configuration, scrubs native-tool/cloud/CI environment settings, rejects
  unsafe imports, and accepts only approved literal compiler source units.
- Added stable `BNT-` candidate observations, separately hash-bound human review
  history, enforced state transitions, and reason/impact requirements.
- Added transparent review-priority scoring with component points and reason
  codes that explicitly cannot claim exploitability, bounty severity, or payout.
- Added content-addressed candidate proof bundles with explicit setup unknowns,
  separate impact assertions, offline isolated execution, and tamper checks.
- Added immutable private report drafts, completeness/staleness gates, explicit
  human approval, and checksummed redacted local export with no submission path.
- Added a frozen ten-project historical corpus, calibration/holdout labels,
  tamper-evident offline evaluation, raw rejected-candidate metrics, and an
  explicit go/no-go product-claim gate via `holes bounty history`.
- Added a reproducible repository-owned end-to-end pilot with pinned local
  rules/scope, human confirm/reject inputs, an unsupported proof decision,
  complete private report and approval, checksummed local export, workflow and
  friction metrics, socket-denial coverage, and exercised safety guards via
  `holes bounty pilot`.

## 1.0.0 — 2026-08-08

First audit-ready release.

### Analysis

- Thirteen documented Solidity rules covering authorization, calls and
  reentrancy, signatures, proxy/storage initialization, ERC-20 assumptions,
  and oracle/swap hazards.
- Optional isolated Foundry compilation with project-wide AST, inheritance,
  call-graph, data-flow, taint, authorization, signature, proxy, token, and
  market-integrity evidence.
- Source-only fallback with explicit confidence/evidence boundaries.

### Verification and evaluation

- Deterministic Foundry proof generation for supported `SOL005` and `SOL007`
  findings, requirements manifests, fuzz sequences, invariant adapters, and an
  isolated proof runner.
- Versioned per-rule evaluation corpus with 33 positive and 31 safe labels across
  `SOL001`–`SOL013`, plus repeatable correctness/performance benchmarks.
- Published CPython, Solidity, Foundry, and EVM compatibility policy and matrix.

### Team workflow

- Versioned text, JSON, and SARIF output; stable fingerprints; suppressions;
  `.holes.toml`; reviewed baselines; severity gates; resource limits; and
  baseline-aware GitHub Actions examples.
- Verified Etherscan V2 source ingestion with path validation, hashes, and
  provenance; optional evidence-bound AI explanations that cannot alter findings.
- Threat model, secure-use/disclosure policies, complete user/contributor docs,
  and deterministic release artifact validation.

### Security hardening

- Refuse unsafe fetched paths and output overwrites, cap network/report inputs,
  isolate build/proof artifacts, enforce time/resource limits, and scrub common
  credentials from native subprocess environments.
- Reject proof-manifest compiler strings that are not exact supported releases,
  preventing Foundry-configuration injection through `solc_version`.

## 0.6.0 — 2026-08-08

Team configuration, new-finding baselines, rule catalog, SARIF CI, resource
limits, verified-source ingestion, and evidence-bound AI triage.

## 0.5.0 — 2026-08-08

Generated proofs, bounded transaction sequences, invariants, requirements
manifests, and isolated execution.

## 0.4.0 — 2026-08-08

High-value compiler-backed detectors `SOL008`–`SOL013` and their versioned
positive/safe corpus.

## 0.3.0 — 2026-08-08

Project-wide AST/inheritance/call/data-flow analysis, interprocedural reentrancy,
inspection JSON, and benchmark corpus.

## 0.2.0 — 2026-08-08

Foundry/solc AST loading, compiler-aware packed-hash detection, and first proof.

## 0.1.0 — 2026-08-08

Source scanner MVP, six initial detectors, suppressions, and text/JSON/SARIF
reporting.
