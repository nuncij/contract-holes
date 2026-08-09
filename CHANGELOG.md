# Changelog

All notable project changes are recorded here. Versions follow semantic
versioning; public JSON/SARIF schemas have their own compatibility rules.

## Unreleased — `1.1.0`

### Bounty research workflow

- Added the versioned, default-private `bounty.toml` workspace contract and
  normalized JSON schema.
- Added `holes bounty init` and `holes bounty validate` with explicit
  authorization, immutable source identity, normalized scope, offline compiler
  policy, unknown-key rejection, and no-overwrite behavior.
- Kept submission, uploads, remote RPC, transactions, and automatic
  confirmation outside the command surface.

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
