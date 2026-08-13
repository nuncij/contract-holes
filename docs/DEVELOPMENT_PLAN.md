# Contract Holes Development Plan

Last updated: 2026-08-13
Current release: `1.1.1`
Current milestone: **Post-M8 — independent validation rework**
Next: **`PRECISION-002` is in progress; all independent-review blockers are
resolved, repository-local gates pass, and the private offline replay is
complete. Only final review, commit/push, and CI remain.**

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
| Repository | Private `nuncij/contract-holes` GitHub repository on `main`, with signed release tags |
| Release | Signed `1.1.1` security patch; M7 functionality remains `1.1.0` compatible |
| Inputs | Solidity files/directories or Etherscan V2 verified source by chain/address |
| Source analysis | Comment/string masking, contract/function regions, state-variable heuristics |
| Compiler analysis | Optional isolated Foundry build with solc ASTs and UTF-8 source mapping |
| Rules | Thirteen registered rules, `SOL001` through `SOL013` |
| Proofs | Runnable `SOL007` proof; `SOL005` probe, sequence fuzzing, invariants, requirement manifests, and isolated runner |
| Output | Terminal text, finding JSON, SARIF 2.1.0, filtered inspection JSON, and evidence-bound AI triage JSON |
| Workflow | `.holes.toml`, baselines, `holes rules`, verified-source provenance, severity/CI policy, suppressions, inspection, benchmarks, and proofs |
| Project model | Shared AST, inheritance, calls, value-flow facts, execution order, reentrancy, target-taint, authorization, signature, proxy-upgrade, token-flow, and market-integrity traces |
| Verification | 238 Python tests; frozen JSON/SARIF and bounty schemas, 64 audit labels, ten historical cases, an authorized end-to-end pilot, CI/catalog/config/baselines/limits/address/AI boundaries, offline benchmarks, inspection, and isolated Forge execution tested |
| Runtime dependencies | None; Foundry is optional and required only for compiler-aware analysis |

### Rule maturity

| Rule | Detection level | Important remaining limitation |
| --- | --- | --- |
| `SOL001` `tx.origin` | Source signal | Does not yet prove the value controls authorization |
| `SOL002` unchecked call | Compiler evidence when available | Does not track an assigned success value to its later use |
| `SOL003` `delegatecall` | Source signal | Does not yet determine whether the target is user-controlled or trusted |
| `SOL004` `selfdestruct` | Direct evidence | Protocol impact still depends on the call path and deployment assumptions |
| `SOL005` reentrancy ordering | Compiler-backed interprocedural evidence plus configurable callback probe | View/pure and staticcall interactions no longer form paths; state-changing calls, contract creation, and fresh-target initializers remain reportable (no no-callback proof, no blanket fresh/creation suppression); opposite `if`/`else` arms remain separate across internal helpers; target deployment, setup, callback reachability, and impact assertions remain project-specific |
| `SOL006` weak randomness | Source heuristic | Does not trace the random value to a value-bearing decision |
| `SOL007` packed hash collision | Compiler evidence plus primitive proof | Does not trace the hash to authorization, signatures, or identifiers |
| `SOL008` controlled call target | Compiler-backed interprocedural taint | Immutable/fixed receivers retain structured provenance through aliases and internal parameters, and created addresses carry non-user-controlled fresh provenance; a read-only view/pure/staticcall sink is suppressed only when its result is ignored or the enclosing external entry is view/pure; `external-return` taint is never cleared by receiver identity, so governance/config-derived and factory-owned target provenance is not proven and stays reportable; the rule does not prove allowlist dominance or persist taint through state across transactions |
| `SOL009` exposed privileged write | Compiler-backed authorization reachability | Dominating role checks, exact `msg.sender` mapping keys, and a strict timelock guard (separate unconditional nonzero-pending and `block.timestamp >= deadline` guards over distinct declarations, with the pending value feeding the protected write without user-controlled taint or an exact zero-clear of a guarded field) are recognized; no unrelated later write inherits protection, and wrong directions, timestamp `==`/`!=`, OR/optional delay, unrelated zero/nonzero flags, timestamp-only, mixed pending/caller values, compound, and combined boolean guards still report; a role self-grant remains reportable, while privileged-state names, branch dominance, and custom protocol authorization may require review |
| `SOL010` signature authorization | Compiler-backed recovery-to-action path | Protection and domain recognition are conservative; external library and cross-function digest provenance may require review |
| `SOL011` proxy and upgrade safety | Compiler-backed initializer, delegatecall-storage, and versioned-layout evidence | Custom proxy standards and unnamed upgrade relationships require project-specific review |
| `SOL012` ERC-20 interaction safety | Compiler-backed typed-call and amount-origin flow | Custom wrappers, accepted-token policy, and indirect recipients may require review |
| `SOL013` oracle and swap safety | Compiler-backed price-origin, freshness, and router-argument evidence | Custom oracle/router APIs, indirect origins, and TWAP quality require review |

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

`SOL013` follows direct compiler value origins from Chainlink-style
`latestRoundData` and AMM `getReserves`/`slot0` reads to state writes or external
interactions. It requires a preceding timestamp freshness assertion for oracle
data, treats direct reserve/slot use without TWAP evidence as manipulable, and
reports zero minimum output or `block.timestamp` deadlines on common V2 router
calls. Safe freshness, TWAP, and caller-bounded swap fixtures remain clean.

`SOL013` intentionally has no source-only fallback. Member-name recognition and
V2 router positions are conservative, and value origins are currently direct.
Round completeness, heartbeat policy, observation duration, market liquidity,
V3 structs, custom routers, and upstream bounds still require manual review.

The versioned `m3-1` aggregate corpus pins every rule fixture, evidence label,
compiler version, positive finding, and safe counterexample for `SOL008` through
`SOL013`. Its 25 positive and 24 safe labels close the M3 release gate while
remaining deliberately curated rather than claiming real-world precision or
recall.

For compiler-backed `SOL005` findings, proof generation now emits a dependency-free
Foundry file containing a generic vulnerable model and a configurable callback
probe. The model test demonstrates nested execution. The probe accepts target,
entry and reentry calldata, and separate ETH values at runtime so reviewers can
wire it into project-specific deployment and setup. Generated comments retain
the finding's entry, interaction, state-write function, and state variable, and
explicitly avoid claiming protocol impact.

The same generated artifact includes a generic sequence executor and Foundry
fuzz entrypoint. Reviewers can supply up to 32 calldata/value pairs, continue or
stop after a reverted step, and inspect executed/succeeded counts plus a stable
result digest. Target calls share the executor as their caller; distinct actors,
block/time changes, token funding, and other protocol state transitions belong
in a project-specific adapter.

Generated sequence executors accept user-defined invariant adapters. The adapter
returns a stable ID, pass/fail result, and detail bytes before the first call and
after every executed step. The executor stores and emits the assertion ID, step,
result, and detail hash, provides a Foundry-visible custom violation error, and
treats an adapter revert as a failed check. This makes assertion output stable
without pretending the scanner can infer a protocol's economic invariant.

Every generated Solidity artifact now has a deterministic `.proof.json`
requirements sidecar. The versioned manifest records finding provenance and a
locally runnable generated-test profile with its tested compiler. A separate
project-probe profile leaves compiler/EVM, chain/fork, constructor, deployment,
state, funding, actor, calldata, and invariant inputs explicitly unknown until a
reviewer configures them. Modified sources or manifests are never overwritten.
The format is documented in [PROOF_REQUIREMENTS.md](PROOF_REQUIREMENTS.md).

The `holes proofs` runner validates manifest/source hashes and executes each
runnable bundle in its own temporary Foundry project. It uses the recorded solc
version, defaults to offline compilation, removes inherited Foundry/RPC settings,
enforces a per-artifact timeout, redacts temporary paths, and returns structured
pass/fail/timeout/unsupported JSON. The input proof directory remains unchanged.

Project scans now discover a validated `.holes.toml`. The versioned schema sets
scan roots and exclusions, dependency policy, minimum severity, enabled/disabled
rules, per-rule severity overrides, and compiler/offline behavior. Relative paths
resolve from the configuration file, explicit CLI values win, and unknown or
contradictory settings fail instead of being ignored. The schema and precedence
are documented in [CONFIGURATION.md](CONFIGURATION.md).

Versioned fingerprint baselines support new-finding-only reports and CI failure
thresholds. Fingerprints normalize finding paths relative to the baseline file,
making a repository-root snapshot portable. Comparison reports new, existing,
and resolved counts; baseline creation refuses overwrite, while explicit updates
use an atomic replace. Stored entries omit source excerpts and absolute project
paths. The workflow is documented in [BASELINES.md](BASELINES.md).

`holes rules` renders all registered detectors or one selected rule as text or
versioned JSON. Catalog entries combine the live rule severity, confidence,
description, and recommendation with analysis mode, vulnerable/safer examples,
manual-review boundaries, and authoritative remediation references. Tests
require exact coverage of `SOL001` through `SOL013`. Usage is documented in
[RULE_CATALOG.md](RULE_CATALOG.md).

A copy-ready GitHub Actions template runs baseline-aware SARIF scanning with a
high-severity new-finding gate. It uses minimal token permissions, does not
persist checkout credentials, captures scanner status, uploads valid SARIF for
statuses 0/1, and restores the status afterward. Tool/install pinning, GitHub
code-scanning availability, and fork behavior are documented in [CI.md](CI.md).

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
  -> oracle freshness, spot-price, and swap bounds       [M3: RULE-013 complete]
  -> deterministic security rules
  -> structured findings with evidence paths
  -> filtered compiler-analysis inspection JSON
  -> executable proofs where generation is reliable
  -> text / JSON / SARIF / CI policy
  -> optional AI correlation and explanation            [later]
  -> pinned bounty scope and candidate workspace         [M7: implemented]
  -> local proof, private report, and human approval     [M7: implemented]
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
| M3 — High-value detectors | `0.4.0` | Complete | Access control, call-target taint, signatures, proxies/upgrades, token assumptions, market integrity |
| M4 — Dynamic verification | `0.5.0` | Complete | Reentrancy probes, transaction-sequence fuzzing, protocol invariants, isolated runner |
| M5 — Team and CI workflow | `0.6.0` | Complete | Configuration, baselines, catalog, CI, limits, address provenance, evidence-bound AI triage |
| M6 — Audit-ready release | `1.0.0` | Complete | Benchmarked accuracy, stable schemas, compatibility policy, security docs, reproducible signed release evidence |
| M7 — Bounty Hunter Mode | `1.1.0` | Complete | Authorized scope profiles, candidate triage, isolated local proofs, private reports, historical validation, authorized pilot, and signed reproducible release evidence |
| M8 — Private Real-World Validation | Unreleased | Complete | Production repository operations, authorized source-only and offline compiler trials, and evidence-driven backlog |

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

The output schemas, labelled accuracy corpus, and compatibility policy are now
complete. Supported ranges and tested reference points are published in
[toolchain compatibility](COMPATIBILITY.md), including a machine-readable host
report and CI matrix.

The [threat model](THREAT_MODEL.md), [secure-use guide](SECURE_USE.md), and
[security policy](../SECURITY.md) define native-tool, network, report, proof, AI,
and disclosure boundaries. Proof compiler versions are validated before being
written to Foundry configuration, and common credentials are removed from native
subprocess environments as defense in depth.

The [documentation index](README.md) now routes installation, complete CLI,
rule, CI, proof, evaluation, security, and contributor guidance. Internal links
and public-command coverage are regression tested.

Initial quality targets for supported vulnerability classes are at least 80%
precision for high-confidence findings, no unlabelled silent analysis failures,
and deterministic output across repeated scans of the same revision.

### M7 — Bounty Hunter Mode (`1.1.0`)

Turn the scanner into a human-controlled bounty research assistant. M7 begins
with an approved, revision-pinned scope; preserves immutable scanner evidence;
separates human review decisions; generates local-only proof workspaces; and
produces private report drafts that require explicit approval before local
export.

Automatic platform submission, live-network exploit execution, payout
prediction, and automatic confirmation are out of scope. Program rules and
human judgment remain authoritative.

Release gate:

- incomplete, stale, tampered, or out-of-scope profiles fail closed;
- normal bounty commands are offline and cannot submit or disclose findings;
- observations, review decisions, proof results, and reports remain separately
  attributable and bound to source hashes;
- proof workspaces default to isolated local execution without inherited RPC or
  wallet configuration;
- at least ten disclosed historical cases from five independent projects are
  evaluated, including supported and explicitly out-of-model root causes;
- at least three independent historical vulnerabilities in supported classes
  produce useful investigation evidence;
- one authorized end-to-end pilot is completed without requiring submission or
  live-network interaction;
- limitations and measured historical results are published without treating
  the synthetic regression corpus as real-world accuracy.

The complete architecture, safety boundaries, delivery phases, evaluation
design, and deferred decisions are in the
[M7 Bounty Hunter Mode plan](BOUNTY_HUNTER_PLAN.md). Dependency-ordered work is
tracked in [TASKS.md](../TASKS.md).

The authorized M7 pilot is complete on a repository-owned, content-pinned
fixture. It exercised profile validation, source-only scope scanning, two human
review decisions, an unsupported automatic proof, complete private reporting,
explicit approval, and checksummed local export. The path-independent result
records a 720-second operator-event timeline, three friction observations, two
successfully blocked unsafe actions, and no network, target, chain, platform, or
submission action. See [authorized bounty pilot](BOUNTY_PILOT.md).

### M8 — Private Real-World Validation

First, establish production CI, attach signed and checksummed release artifacts
to private GitHub releases, and enable the security controls that
the private-repository plan supports. Branch protection and unavailable
security features must be recorded as limitations instead of being claimed as
enabled.

Then select one external target whose published program rules explicitly permit
this type of review. Pin the rules, source revision, paths, impacts, and
restrictions before scanning. Run the released workflow privately, make every
candidate confirmation and submission decision manually, and record useful
evidence, false positives, out-of-model behavior, and operator time. Only those
observations may create the next detector/workflow backlog.

Release gate:

- production CI passes from GitHub on `main`;
- the latest private GitHub release contains artifacts, checksums, and the
  maintainer's detached checksum signature;
- available dependency security controls are enabled and unavailable private
  repository controls are documented;
- one external trial has explicit authorization and immutable source/scope
  identity before analysis begins;
- the trial produces a private evaluation record without automatic submission,
  public disclosure, live-network exploitation, or payout claims;
- observed gaps are converted into prioritized, testable work items.

Completed on 2026-08-10. The authorized OpenZeppelin Confidential Contracts
`v0.4.0` source-only trial scanned 22 exact files, produced zero candidates,
and performed no proof, report, disclosure, submission, or deployed-network
action. The clean result has undefined precision and unknown recall. See the
[M8 trial evaluation](research/M8_OPENZEPPELIN_TRIAL.md). `COMP-003` then
separated reportable assets from immutable compiler-only dependencies.

The separately approved `PILOT-004` follow-up compiled the same 22 reportable
files offline with 58 exact compiler-only dependencies and Solidity `0.8.27`.
It produced 51 deduplicated private candidates, all left in human-review state
`new`. Replaying the scan reproduced its immutable digest. `PILOT-005` then
reviewed all 51: 50 were rejected with source-backed reasons and one remained
under investigation. No candidate is confirmed. No proof, report, approval,
export, disclosure, submission, chain action, or target interaction occurred,
and the frozen source-only evidence was unchanged.

The operator granted standing authorization on 2026-08-12 for local, private,
isolated, offline analysis and proof work on the exact pinned trial.
`PILOT-006` completed the same day under that authorization: focused
trust-boundary analysis showed the reported interaction cannot reach an
untrusted callback, and an offline mechanical enumeration of the pinned
dependency closure found zero actor-controlled external call targets in the
reported window. The existing proof workflow could not test that decisive
question without inventing setup facts, so proof execution is recorded as
unsupported. The final human decision rejected the last investigating
candidate. All 51 candidates are now rejected false positives, and none is
confirmed. The reviewer-labelled candidate precision is 0/51. The review is
not independent ground truth, and recall remains unknown. RPC, chain activity,
target contact, report export,
disclosure, and submission remained outside the authorization and did not
occur. `PRECISION-001` completed on 2026-08-13. Its generic compiler corpus
covers all five observed detector gaps. A fresh private rescan of the same
pinned trial scanned 22 reportable files and produced 47 candidates: 23
call-semantics, 8 branch-feasibility, 12 target-provenance, 3
authorization-context, and 1 reentrancy-trust-boundary. The canonical private
workspace and target checkout were unchanged. The synthetic and historical
evaluation gates remain unchanged and passing. These reviewer labels are not
independent ground truth; the next step is an independently authorized second
real-world target. Private target evidence will not become a repository
fixture.

A completion review on 2026-08-13 found four gaps in the first implementation.
The repair adds a pure public-library call and carries branch context through
internal helpers. It adds post-conditional positives and role self-grant
coverage. Structured immutable-target provenance now follows aliases and
internal parameters. Tests assert the exact public path, line, and evidence
metadata. All 216 tests and both frozen evaluations pass. A new private offline
workspace reproduced the same 47-candidate scan and both prior digests. The
repair does not claim a lower workload for this target.

The next validation step was `PILOT-007`, which intended to test an independent
second real-world target. The run remained local, private, isolated, and
offline. No target contact, proof, report, export, disclosure, submission,
chain action, or platform interaction occurred.

`PILOT-007` recorded an operational result on 2026-08-13 against Silo Finance
v2/v3 at tag `4.26.0`. Two private workspaces reproduced identical digests over
ten
reportable files and 124 pinned compiler-only dependencies with Solidity
`0.8.28`. The scan produced 81 candidates; the operator confirmed all 81
rejections after source review, with zero investigating or confirmed. The trial
surfaced and fixed three generic scanner defects: recursive AST walkers now
traverse iteratively, signature domain analysis is cycle-safe across mutually
recursive call arguments, and custom error/event members are excluded from the
call graph.

A completion review and repair on 2026-08-13 found the operational result is
not an untouched independent baseline. The untouched scanner at selection
commit `08050a1` hits a reproducible `RecursionError` blocker on the full Silo
closure, so there is no frozen baseline scan digest. The pinned Silo tag
`4.26.0` (commit `570a668`, 2026-07-27) does not map to the deployed in-scope
assets, which the repository's `DeployedSiloVersions.md` documents as version
`3.5.0` (commit `b1f428f`, 2025-05-15). `PILOT-007` therefore does not satisfy
its independent-bounty-trial gate. Silo is retained only as a non-bounty
research corpus. The first repair completed all 81 private review-brief records
and added two genuine regressions (221 tests, frozen gates unchanged); its
minimal checkout matched the 124-file closure by manual hashes but lacked Git
metadata. `REPAIR-007` (2026-08-13) then built a new private Git-backed minimal
checkout (only the three submodules intersecting the frozen 124-file closure,
with superproject Git metadata, user-read-only) that the public scanner
accepts, and reproduced the source manifest, compiler-enabled scan, and
candidate ledger offline with the same semantics as the canonical post-repair
result. It also strengthened the two compiler-backed regressions and switched
the deep-AST test to `TemporaryDirectory`. The final Silo source-to-scope
verdict stays **UNSATISFIED**.

`PILOT-008` completed on 2026-08-13 against two Olas governance contracts at
the program-mapped `v1.2.5` commit `8ce095f`. Two private offline Solidity
`0.8.30` scans reproduced identical source-manifest, scan, and zero-candidate
ledger identities. The trial therefore satisfies the independent target gate,
but its two-file scope is too small to establish broad real-world recall or
bounty viability. The preserved initial run selected cached Solidity `0.8.28`,
showing that compiler-enabled profiles do not bind an exact compiler release.
`COMP-004` now fixes that profile/compiler interface. A new private pinned replay
selected only Solidity `0.8.30`, preserved the frozen source and dependency
sets, and again produced zero candidates.

`PRECISION-002` is in progress; only final review, commit/push, and CI remain.
All independent-review blockers on the first green diff are resolved by
narrowing or retaining findings. The generic `precision-002` compiler corpus and
`test_precision_002` cover supported outcomes with adversarial-positive
neighbors and record explicit unsatisfied/manual-review boundaries:
view/staticcall interactions no longer form
`SOL005` paths, while state-changing calls, contract creation, and fresh-target
initializers remain reportable (no no-callback proof); a strict
nonzero-pending-value plus elapsed-delay guard protects a following privileged
write from `SOL009`; created addresses carry non-user-controlled fresh
provenance for `SOL008` (nothing about `SOL005` callback safety); `external-return`
taint is never cleared by an immutable receiver (so a governance-configured call
list still reports `SOL008`); a used read result in a non-view function reports
`SOL008`; and the immutable underlying asset was already a fixed target.
Governance/config-derived and factory-owned address provenance, callback safety
for creation and fresh targets, broader timelock shapes, and harmless used-read
analysis are unsatisfied manual-review boundaries. Shared `dataflow` facts carry
callee mutability, fresh-deployment provenance, result-ignored state, and the
strict timelock authorization fact; `reentrancy` and `target_taint` consume them
without rule-local AST walks. The frozen `audit-1` evaluation is unchanged. The
historical `m7-history-1` result was versioned after the view-interaction fix
removed one out-of-model Enzyme `SOL005` candidate: candidate precision moved
from 0.875 to 0.933333, all five supported cases retain 1.0 supported-class
recall and evidence completeness, and the `go` decision is unchanged. Suite:
238 tests. The private offline replay (unchanged source and dependency
identities, cached Solidity `0.8.28`, ten reportable files) produced 59
findings/candidates versus 81 before tuning — 22 removed, no new findings —
which are investigation leads, not vulnerabilities and not bounty submissions.
Only final review, commit, push, and project CI remain.

### Post-M8 — Compiler-only dependency boundary

`COMP-003` is complete. Bounty profiles can now declare repeatable compiler-only
Solidity paths separately from reportable `scope.paths`. Both sets are explicit,
content-bound, staged into the fixed offline compiler project, and rechecked for
tampering. Only reportable files are requested for scanning, and findings outside
that set fail closed. Profiles and source manifests using this feature emit their
additive `1.1` normalized record schemas; existing workspaces retain `1.0` digest
material and behavior.

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
