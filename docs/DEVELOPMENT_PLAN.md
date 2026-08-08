# Contract Holes Development Plan

Last updated: 2026-08-08  
Current release: `0.2.0`  
Current milestone: **M2 — Cross-contract analysis (`0.3.0`)**  
Next task: **RULE-005-V2 — Interprocedural reentrancy analysis**

## Product goal

Contract Holes should turn Solidity source into evidence that a security reviewer
can reproduce. Deterministic analysis discovers and validates the evidence. AI
may later correlate and explain it, but it must never be the only reason for a
security finding.

The scanner is successful when it:

- identifies a supported vulnerability with a useful execution or data-flow path;
- distinguishes a confirmed proof from a probable signal;
- produces stable output for local use and CI;
- makes false positives easy to understand, suppress, and measure;
- does not imply that a clean scan is equivalent to an audit.

## Where the project is now

| Area | Current state |
| --- | --- |
| Repository | Local Git repository, clean `main`, two implementation commits |
| Release | `0.2.0` |
| Inputs | One or more Solidity files or directories |
| Source analysis | Comment/string masking, contract/function regions, state-variable heuristics |
| Compiler analysis | Optional isolated Foundry build with solc ASTs and UTF-8 source mapping |
| Rules | Seven registered rules, `SOL001` through `SOL007` |
| Proofs | Runnable Foundry proof for `SOL007` |
| Output | Terminal text, JSON, and SARIF 2.1.0 |
| Workflow | Severity filtering, CI exit thresholds, suppressions, dependency exclusions |
| Project model | Shared AST, inheritance, call, and conservative intra-procedural value-flow facts |
| Verification | 37 Python tests; real compiler data-flow findings, inheritance, and Forge proof tested |
| Runtime dependencies | None; Foundry is optional and required only for compiler-aware analysis |

### Rule maturity

| Rule | Detection level | Important remaining limitation |
| --- | --- | --- |
| `SOL001` `tx.origin` | Source signal | Does not yet prove the value controls authorization |
| `SOL002` unchecked call | Compiler evidence when available | Does not track an assigned success value to its later use |
| `SOL003` `delegatecall` | Source signal | Does not yet determine whether the target is user-controlled or trusted |
| `SOL004` `selfdestruct` | Direct evidence | Protocol impact still depends on the call path and deployment assumptions |
| `SOL005` reentrancy ordering | Intra-contract heuristic | No inherited state, interprocedural path, or executable proof yet |
| `SOL006` weak randomness | Source heuristic | Does not trace the random value to a value-bearing decision |
| `SOL007` packed hash collision | Compiler evidence plus primitive proof | Does not trace the hash to authorization, signatures, or identifiers |

The project-wide index, inheritance layer, call graph, and data-flow engine now
connect source units, inherited symbols, calls, reads, writes, aliases,
authorization conditions, user-controlled values, external returns, and value
transfers. The largest remaining M2 gap is composing those facts across internal
calls into an ordered vulnerability path.

## Analysis architecture

The intended pipeline is:

```text
Solidity project
  -> source discovery and masking
  -> optional Foundry/solc compilation
  -> project index (source units, AST IDs, references)   [M2: complete]
  -> inheritance and symbol resolution                   [M2: complete]
  -> internal call graph                                 [M2: complete]
  -> data-flow facts                                     [M2: complete]
  -> interprocedural reentrancy evidence                 [M2: next]
  -> deterministic security rules
  -> structured findings with evidence paths
  -> executable proofs where generation is reliable
  -> text / JSON / SARIF / CI policy
  -> optional AI correlation and explanation            [later]
```

Source-only mode remains important for fast scans and partially broken projects.
Compiler-aware mode is the higher-confidence path and should never silently fall
back after the user explicitly requests compilation.

## Milestones

| Milestone | Target | Status | Outcome |
| --- | --- | --- | --- |
| M0 — Scanner foundation | `0.1.0` | Complete | CLI, parser, findings, six source rules, reports, suppressions, tests |
| M1 — Compiler evidence | `0.2.0` | Complete | Isolated solc AST loading, AST-backed calls, `SOL007`, first Foundry proof |
| M2 — Cross-contract analysis | `0.3.0` | **Current** | Project index, inheritance resolution, call graph, reusable data-flow facts |
| M3 — High-value detectors | `0.4.0` | Planned | Access control, call-target taint, signatures, proxies/upgrades, token assumptions |
| M4 — Dynamic verification | `0.5.0` | Planned | Reentrancy probes, transaction-sequence fuzzing, protocol invariants |
| M5 — Team and CI workflow | `0.6.0` | Planned | Configuration, baselines, rule catalog, CI integration, performance controls |
| M6 — Audit-ready release | `1.0.0` | Planned | Benchmarked accuracy, stable schemas, compatibility policy, security docs |

### M2 — Cross-contract analysis (`0.3.0`)

Deliverables:

- one shared project index across all compiler source units;
- canonical AST node, contract, function, and declaration lookup;
- Solidity inheritance and inherited state/modifier resolution;
- internal call graph with explicit unresolved edges;
- reusable source-to-sink data-flow facts;
- `SOL005` upgraded to emit an interprocedural evidence path;
- positive and negative multi-file fixtures.

Release gate:

- inherited state mutations are recognized in reentrancy analysis;
- internal helper calls appear in the evidence path;
- diamond inheritance does not duplicate contracts, variables, or findings;
- source-only behavior remains available and all existing tests pass;
- every new analysis primitive has focused unit tests and at least one negative case.

### M3 — High-value detectors (`0.4.0`)

Build rules on the shared M2 facts rather than adding isolated regular
expressions. Priorities are user-controlled external/delegatecall targets,
authorization reachability, replayable signatures, proxy initialization and
storage-layout hazards, unsafe token interaction assumptions, and oracle/slippage
signals.

Release gate: every rule provides a source-to-sink explanation, documents its
known blind spots, and is evaluated against a versioned positive/negative corpus.

### M4 — Dynamic verification (`0.5.0`)

Add Foundry harness generation only where a useful assertion can be produced.
The main targets are a reentrancy probe, calldata-driven transaction sequences,
and user-defined protocol invariants. A generated test must distinguish proving
a vulnerability primitive from proving protocol impact.

Release gate: proof artifacts are deterministic, compile without modifying the
target repository, and report unsupported deployment/setup requirements instead
of inventing them.

### M5 — Team and CI workflow (`0.6.0`)

Add `.holes.toml`, rule selection and severity overrides, fingerprint baselines,
new-finding-only CI gates, a human-readable rule catalog, timing/memory limits,
and a reusable CI example. Consider verified-address ingestion and AI triage only
after these deterministic workflows are stable.

### M6 — Audit-ready release (`1.0.0`)

Freeze a documented finding schema and configuration format, publish supported
Solidity/Foundry ranges, benchmark each rule against a versioned corpus, define a
security disclosure process, and document the scanner's threat model.

Initial quality targets for supported vulnerability classes are at least 80%
precision for high-confidence findings, no unlabelled silent analysis failures,
and deterministic output across repeated scans of the same revision.

## Engineering rules

- Every detector needs a vulnerable fixture and a nearby safe fixture.
- Findings must say whether evidence came from source heuristics, compiler AST,
  data flow, or an executable proof.
- New compiler analysis belongs in shared indexes/facts, not inside one-off rules.
- JSON and SARIF changes require schema-compatible tests.
- Generated files must be deterministic and must not overwrite user edits.
- A task is complete only when its acceptance criteria, tests, and documentation
  are complete in the same commit.
- Update [TASKS.md](../TASKS.md) whenever work starts, finishes, or changes scope.
