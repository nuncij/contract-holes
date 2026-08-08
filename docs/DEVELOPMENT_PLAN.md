# Contract Holes Development Plan

Last updated: 2026-08-08  
Current release: `0.3.0`
Current milestone: **M3 — High-value detectors (`0.4.0`)**
Next: **RULE-013 — Oracle freshness, spot-price, and missing-slippage signals**

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
| Repository | Local Git repository on `main`, with task-scoped implementation commits |
| Release | `0.3.0` |
| Inputs | One or more Solidity files or directories |
| Source analysis | Comment/string masking, contract/function regions, state-variable heuristics |
| Compiler analysis | Optional isolated Foundry build with solc ASTs and UTF-8 source mapping |
| Rules | Twelve registered rules, `SOL001` through `SOL012` |
| Proofs | Runnable Foundry proof for `SOL007` |
| Output | Terminal text, finding JSON, SARIF 2.1.0, and filtered analysis-inspection JSON |
| Workflow | Severity/CI policy, suppressions, inspection, and correctness/performance benchmarks |
| Project model | Shared AST, inheritance, calls, value-flow facts, execution order, reentrancy, target-taint, authorization, signature, proxy-upgrade, and token-flow traces |
| Verification | 72 Python tests; offline M2 and `SOL008`–`SOL012` corpora, benchmark, inspection, and Forge proof tested |
| Runtime dependencies | None; Foundry is optional and required only for compiler-aware analysis |

### Rule maturity

| Rule | Detection level | Important remaining limitation |
| --- | --- | --- |
| `SOL001` `tx.origin` | Source signal | Does not yet prove the value controls authorization |
| `SOL002` unchecked call | Compiler evidence when available | Does not track an assigned success value to its later use |
| `SOL003` `delegatecall` | Source signal | Does not yet determine whether the target is user-controlled or trusted |
| `SOL004` `selfdestruct` | Direct evidence | Protocol impact still depends on the call path and deployment assumptions |
| `SOL005` reentrancy ordering | Compiler-backed interprocedural evidence | Branch paths remain conservative; no executable proof yet |
| `SOL006` weak randomness | Source heuristic | Does not trace the random value to a value-bearing decision |
| `SOL007` packed hash collision | Compiler evidence plus primitive proof | Does not trace the hash to authorization, signatures, or identifiers |
| `SOL008` controlled call target | Compiler-backed interprocedural taint | Does not yet prove allowlist dominance or persist taint through state across transactions |
| `SOL009` exposed privileged write | Compiler-backed authorization reachability | Privileged-state names and branch dominance are conservative; custom protocol authorization may require review |
| `SOL010` signature authorization | Compiler-backed recovery-to-action path | Protection and domain recognition are conservative; external library and cross-function digest provenance may require review |
| `SOL011` proxy and upgrade safety | Compiler-backed initializer, delegatecall-storage, and versioned-layout evidence | Custom proxy standards and unnamed upgrade relationships require project-specific review |
| `SOL012` ERC-20 interaction safety | Compiler-backed typed-call and amount-origin flow | Custom wrappers, accepted-token policy, and indirect recipients may require review |

The project-wide index, inheritance layer, call graph, and data-flow engine now
connect source units, inherited symbols, calls, reads, writes, aliases,
authorization conditions, user-controlled values, external returns, and value
transfers. `SOL005` composes those facts across internal calls into an ordered
path and recognizes named and state-lock reentrancy guards. A versioned Foundry
corpus now locks down positive and negative behavior for imports, libraries,
overrides, diamond inheritance, recursion, and modifiers. Deterministic
inspection and repeatable correctness/performance benchmarking complete the M2
release gate. M3 began with user-controlled external-call target taint.
`SOL008` now follows external inputs through local aliases and resolved helper
parameters to low-level, typed external, function-pointer, and delegatecall
destinations. It excludes empty-data value payments and fixed state destinations;
target validation and mutable-state provenance still require manual review.
`SOL009` classifies common ownership, administration, upgrade, role, pause,
operator, treasury, and fee-control state, then unfolds resolved modifiers and
internal helpers in execution order. A `require`/`assert`, recognized named
modifier, or unconditional authorization helper must precede the write. Checks
inside optional branches and checks after the write remain in the evidence trace
but do not suppress a finding.

`SOL009` intentionally has no source-only fallback. Its privileged-state name
classification can miss project-specific security state or classify similarly
named ordinary state, and it does not yet build a full control-flow graph. Calls
through dynamic dispatch, authorization established in earlier transactions,
modifiers with unusual placeholder control flow, and protocol invariants require
manual review.

`SOL010` follows compiler-identified `ecrecover` sites through resolved internal
helpers to a subsequent state write or external interaction. It reports which of
four protections are absent before the action: nonce/digest consumption, a
timestamp deadline, chain-and-contract domain separation, and rejection of
zero-address recovery. Pure recovery utilities are excluded, and a paired
EIP-712-style fixture demonstrates the clean path.

`SOL010` intentionally has no source-only fallback. Replay protection is
recognized from writes to common nonce, used-digest, and replay-state names;
expiry currently requires a dominating `require`/`assert` timestamp comparison.
Domain provenance follows local aliases, direct `block.chainid` and
`address(this)` inputs, named domain separators, and resolved helper returns, but
not arbitrary digest parameters across every call boundary. Signature libraries,
custom invalidation schemes, unusual control flow, and cryptographic malleability
policies require manual review.

`SOL011` reports externally callable initializer paths that reach state without a
recognized one-time guard, proxy-like contracts that combine ordinary mutable
storage with `delegatecall`, and incompatible storage prefixes between explicit
version pairs such as `VaultV1` and `VaultV2`. It follows initializer helpers,
recognizes named and state-backed initialization guards, accepts unstructured
proxy slots, and treats append-only inherited layouts as compatible.

`SOL011` requires compiler mode. Initializer and proxy classification relies on
common names, fallback behavior, and compiler-resolved state. Layout comparison
is limited to explicitly versioned contract families and declaration/type
prefixes; it does not replace byte-accurate storage-layout validation for packed
fields, structs, custom assembly slots, diamonds, or externally deployed
implementations. Those cases require manual review.

`SOL012` resolves typed ERC-20 declarations, reports ignored boolean results, and
traces requested `transferFrom` amounts through internal helper parameters to
state credits. Checked return values, interfaces that deliberately return no
value, and credits derived from observed before/after balances remain clean.

`SOL012` requires compiler mode and currently recognizes token interfaces by
ERC-20/token naming plus resolved function declarations. Nominal-amount analysis
is limited to inbound transfers whose recipient is visibly `address(this)` and
does not yet prove later use of a captured boolean. Safe-transfer libraries,
indirect vault recipients, rebasing tokens, and protocol-enforced token allowlists
require manual review.

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
  -> interprocedural reentrancy evidence                 [M2: complete]
  -> interprocedural external-target taint               [M3: RULE-008 complete]
  -> authorization reachability and privileged writes   [M3: RULE-009 complete]
  -> signature recovery-to-action hazards               [M3: RULE-010 complete]
  -> proxy initialization and layout hazards            [M3: RULE-011 complete]
  -> typed token return and amount-flow hazards          [M3: RULE-012 complete]
  -> deterministic security rules
  -> structured findings with evidence paths
  -> filtered compiler-analysis inspection JSON
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
| M2 — Cross-contract analysis | `0.3.0` | Complete | Cross-contract facts, reentrancy traces, corpus, inspection, and benchmark |
| M3 — High-value detectors | `0.4.0` | **Current** | Access control, call-target taint, signatures, proxies/upgrades, token assumptions |
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
