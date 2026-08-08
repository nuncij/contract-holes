# Contract Holes Task Tracker

This is the execution view of the [development plan](docs/DEVELOPMENT_PLAN.md).
Keep one task marked **NEXT** and at most one task marked **IN PROGRESS**.

Current release: `0.3.0`

Current milestone: **M3 — High-value detectors (`0.4.0`)**

Current position: M0, M1, and M2 are complete; `RULE-008` and `RULE-009` are complete in M3.

Next: **RULE-010**

Status legend: `[x]` complete, `[ ]` queued. Priorities are P0 (release blocker),
P1 (important), and P2 (useful follow-up).

## Completed

- [x] **REPO-001** — Initialize Git on `main` and preserve the MVP.
- [x] **CORE-001** — Define finding, severity, fingerprints, and rule metadata.
- [x] **CORE-002** — Discover Solidity sources and exclude dependencies/artifacts by default.
- [x] **PARSE-001** — Mask comments and strings while preserving source positions.
- [x] **RULE-001..006** — Implement the first six source-analysis rules.
- [x] **REPORT-001** — Add terminal, JSON, and SARIF 2.1.0 output.
- [x] **CLI-001** — Add severity filters, CI failure thresholds, and suppressions.
- [x] **COMP-001** — Run Foundry compilation in an isolated temporary directory.
- [x] **COMP-002** — Load solc ASTs and map UTF-8 byte offsets to source characters.
- [x] **RULE-007** — Detect dynamic-value packed-hash ambiguity from compiler types.
- [x] **PROOF-001** — Generate and execute a standalone `SOL007` Foundry proof.
- [x] **TEST-001** — Establish the 22-test unit/integration suite and packaging check.
- [x] **PLAN-001** — Document milestone gates, rule maturity, and the ordered backlog.

## M2 — Cross-contract analysis (`0.3.0`)

Work in dependency order.

### [x] AST-001 — Project-wide compiler index — P0 — **COMPLETE**

Build a `ProjectIndex` shared by every scanned source instead of handing each
rule an isolated AST.

Acceptance criteria:

- index source units by canonical path and solc source ID;
- index AST nodes, declarations, contracts, and functions by AST ID;
- resolve `referencedDeclaration` without rescanning JSON trees;
- expose source ranges through one UTF-8-safe API;
- cover two-source imports and remapped dependency paths in tests;
- preserve source-only scanning when no compiler index exists.

Depends on: `COMP-002`.

### [x] AST-002 — Inheritance and symbol resolution — P0 — **COMPLETE**

Use `linearizedBaseContracts` to resolve inherited state variables, functions,
modifiers, overrides, and `super` targets.

Acceptance criteria:

- direct, multi-level, and diamond inheritance fixtures pass;
- inherited state variables are visible to derived functions;
- overridden functions and `super` calls resolve to explicit declarations;
- duplicate base contracts do not produce duplicate facts or findings;
- unresolved references are retained as labelled unknowns.

Depends on: `AST-001`.

### [x] FLOW-001 — Internal call graph — P0 — **COMPLETE**

Create function-to-function edges for direct internal calls, inherited calls,
`super`, library calls, and known `this` calls.

Acceptance criteria:

- each edge records caller, callee, call site, and resolution confidence;
- recursion is represented without infinite traversal;
- external/dynamic calls are explicit unresolved or sink edges;
- a CLI-debuggable JSON representation is covered by snapshot-style tests.

Depends on: `AST-001`, `AST-002`.

### [x] FLOW-002 — Reusable data-flow facts — P0 — **COMPLETE**

Introduce expression facts for reads, writes, user-controlled inputs, external
interactions, transferred value, and authorization conditions.

Acceptance criteria:

- facts retain source node and enclosing function IDs;
- local aliases and simple assignments propagate facts;
- branch merges are conservative and deterministic;
- unsupported expressions become labelled unknowns, not silently safe values;
- rules consume facts through a stable API rather than walking raw AST JSON.

Depends on: `AST-001`, `FLOW-001`.

### [x] RULE-005-V2 — Interprocedural reentrancy analysis — P0 — **COMPLETE**

Replace the current source-order heuristic when compiler facts are available.

Acceptance criteria:

- detect interaction-before-effect when either operation occurs in an internal helper;
- include the ordered function/call-site path in finding metadata;
- recognize inherited state and common reentrancy-guard patterns;
- avoid reporting the existing safe vault fixture;
- retain the current heuristic, labelled as such, in source-only mode.

Depends on: `AST-002`, `FLOW-001`, `FLOW-002`.

### [x] TEST-002 — Multi-file analysis corpus — P0 — **COMPLETE**

Create versioned positive and negative fixtures for every M2 primitive.

Acceptance criteria:

- imports, libraries, overrides, diamond inheritance, recursion, and modifiers are covered;
- every positive fixture has a nearby safe variant;
- expected rule IDs and evidence paths are asserted;
- the suite runs offline after the required solc version is available.

Depends on: can begin with `AST-001`; completes with `RULE-005-V2`.

### [x] DEBUG-001 — Analysis inspection command — P1 — **COMPLETE**

Expose project-index, inheritance, call-edge, and fact summaries for developers
without mixing them into security findings.

Acceptance criteria:

- machine-readable JSON output;
- filters by file, contract, and function;
- deterministic ordering;
- no source contents are written outside explicitly requested output.

Depends on: `AST-001`, expands with later FLOW tasks.

### [x] BENCH-001 — Performance and correctness baseline — P1 — **COMPLETE**

Record scan duration, peak memory, compiler duration, and finding counts for a
small checked-in corpus.

Acceptance criteria:

- one repeatable command produces JSON metrics;
- source-only and compiler-aware timings are separate;
- expected findings are versioned alongside the corpus;
- regressions are reported without introducing flaky wall-clock test failures.

Depends on: `TEST-002`.

## M3 — High-value detectors (`0.4.0`)

- [x] **RULE-008** — User-controlled external and `delegatecall` target taint — P0 — **COMPLETE**.
- [x] **RULE-009** — Authorization reachability and exposed privileged state changes — P0 — **COMPLETE**.
- [ ] **RULE-010** — Signature recovery, nonce, deadline, and domain-separation hazards — P0 — **NEXT**.
- [ ] **RULE-011** — Proxy initializer and storage-layout hazards — P0.
- [ ] **RULE-012** — ERC-20 return value and balance-delta assumptions — P1.
- [ ] **RULE-013** — Oracle freshness, spot-price, and missing-slippage signals — P1.
- [ ] **CORPUS-001** — Versioned precision/false-positive cases for every M3 rule — P0.

Each M3 rule must emit a source-to-sink path, state its confidence, include safe
counterexamples, and document conditions that require manual review.

## M4 — Dynamic verification (`0.5.0`)

- [ ] **PROOF-002** — Generate a configurable `SOL005` reentrancy probe — P0.
- [ ] **FUZZ-001** — Generate calldata-driven Foundry transaction sequences — P0.
- [ ] **INVARIANT-001** — Define user-supplied protocol invariants and assertion output — P0.
- [ ] **PROOF-003** — Record compiler, chain/fork, constructor, and setup requirements — P1.
- [ ] **RUNNER-001** — Execute proofs in isolated Foundry directories with timeouts — P0.

## M5 — Team and CI workflow (`0.6.0`)

- [ ] **CONFIG-001** — Add `.holes.toml` with rule, path, severity, and compiler settings — P0.
- [ ] **BASELINE-001** — Compare fingerprints and fail CI only on new findings — P0.
- [ ] **CATALOG-001** — Add `holes rules` with examples and remediation references — P1.
- [ ] **CI-001** — Publish a reusable SARIF/CI workflow example — P1.
- [ ] **LIMIT-001** — Add file, compiler, time, and memory limits with explicit diagnostics — P0.
- [ ] **ADDRESS-001** — Ingest verified source by chain/address with provenance — P2.
- [ ] **AI-001** — Correlate and explain deterministic evidence without inventing findings — P2.

## M6 — Audit-ready release (`1.0.0`)

- [ ] **SCHEMA-001** — Freeze and document versioned JSON/SARIF compatibility — P0.
- [ ] **BENCH-002** — Measure per-rule precision and recall on a versioned labelled corpus — P0.
- [ ] **COMPAT-001** — Publish supported Python, Solidity, EVM, and Foundry ranges — P0.
- [ ] **SECURITY-001** — Add threat model, secure-use guidance, and disclosure policy — P0.
- [ ] **DOCS-001** — Complete install, rule, CI, proof, and contributor documentation — P0.
- [ ] **RELEASE-001** — Produce reproducible package artifacts and a signed release checklist — P0.

## Definition of done for every task

- Acceptance criteria above are satisfied.
- Positive, negative, and regression tests pass.
- Findings and public output remain deterministic.
- User-facing behavior and limitations are documented.
- `TASKS.md` and the milestone status are updated in the same commit.
- `git diff --check`, the full Python suite, and any relevant Forge proof pass.
