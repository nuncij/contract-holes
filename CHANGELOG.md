# Changelog

All notable project changes are recorded here. Versions follow semantic
versioning; public JSON/SARIF schemas have their own compatibility rules.

## Unreleased

### Bounty workflow

- Added repeatable `--compiler-dependency` paths to bounty initialization and
  source identification. These Solidity units are separately hashed, staged only
  for fixed offline compilation, and cannot produce reportable findings.
- Added additive normalized profile and source-manifest schemas `1.1`; existing
  profiles without compiler-only dependencies retain schema `1.0` digest
  material and behavior.
- Reject dependency tampering, traversal, symlinks, overlap with reportable
  source units, unsafe imports, and findings attributed outside reportable scope.

### Validation

- Completed the first authorized external source-only trial against the exact
  bounty-pinned OpenZeppelin Confidential Contracts `v0.4.0` release. The
  private deterministic workflow scanned 22 files, produced zero candidates,
  and made no proof, report, submission, disclosure, or external target action.
- Recorded that the real clean scan has undefined precision and unknown recall,
  plus one observed backlog item for separating compiler-only dependencies from
  reportable bounty scope.

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
