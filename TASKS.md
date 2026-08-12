# Contract Holes Task Tracker

This is the execution view of the [development plan](docs/DEVELOPMENT_PLAN.md).
Keep one task marked **NEXT** while queued work exists and at most one task
marked **IN PROGRESS**.

Current release: `1.1.1`

Current milestone: **M8 — Private Real-World Validation — COMPLETE**

Current position: M0 through M8 are complete. The private GitHub repository has
passing production CI, verified signed `v1.1.0` and `v1.1.1` releases,
dependency alerts, and automated security fixes. The `v1.1.1` patch updates the
release toolchain after both initial dependency advisories were fixed on `main`.
Current-plan limits on private branch protection and secret scanning are
recorded. The authorized OpenZeppelin Confidential Contracts `v0.4.0` trials
now cover both source-only and offline compiler analysis at the bounty-pinned
commit. The compiler trial kept 22 reportable files separate from 58 exact
compiler-only dependencies and materialized 51 private candidates. Human review
rejected 50 false positives and left one candidate under investigation. No
candidate is confirmed, and no proof, report, export, disclosure, submission,
chain action, or target interaction occurred.

The operator authorized local, private, isolated, offline analysis and proof
work for the exact pinned trial on 2026-08-12. This standing authorization
removes repeat approval prompts for `PILOT-006`. It does not authorize RPC,
chain activity, target contact, report export, disclosure, or submission.

Next: **PILOT-006 — Resolve the sole investigating candidate with focused
trust-boundary analysis and an offline local proof.**

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
- [x] **RULE-010** — Signature recovery, nonce, deadline, and domain-separation hazards — P0 — **COMPLETE**.
- [x] **RULE-011** — Proxy initializer and storage-layout hazards — P0 — **COMPLETE**.
- [x] **RULE-012** — ERC-20 return value and balance-delta assumptions — P1 — **COMPLETE**.
- [x] **RULE-013** — Oracle freshness, spot-price, and missing-slippage signals — P1 — **COMPLETE**.
- [x] **CORPUS-001** — Versioned precision/false-positive cases for every M3 rule — P0 — **COMPLETE**.

Each M3 rule must emit a source-to-sink path, state its confidence, include safe
counterexamples, and document conditions that require manual review.

## M4 — Dynamic verification (`0.5.0`)

- [x] **PROOF-002** — Generate a configurable `SOL005` reentrancy probe — P0 — **COMPLETE**.
- [x] **FUZZ-001** — Generate calldata-driven Foundry transaction sequences — P0 — **COMPLETE**.
- [x] **INVARIANT-001** — Define user-supplied protocol invariants and assertion output — P0 — **COMPLETE**.
- [x] **PROOF-003** — Record compiler, chain/fork, constructor, and setup requirements — P1 — **COMPLETE**.
- [x] **RUNNER-001** — Execute proofs in isolated Foundry directories with timeouts — P0 — **COMPLETE**.

## M5 — Team and CI workflow (`0.6.0`)

- [x] **CONFIG-001** — Add `.holes.toml` with rule, path, severity, and compiler settings — P0 — **COMPLETE**.
- [x] **BASELINE-001** — Compare fingerprints and fail CI only on new findings — P0 — **COMPLETE**.
- [x] **CATALOG-001** — Add `holes rules` with examples and remediation references — P1 — **COMPLETE**.
- [x] **CI-001** — Publish a reusable SARIF/CI workflow example — P1 — **COMPLETE**.
- [x] **LIMIT-001** — Add file, compiler, time, and memory limits with explicit diagnostics — P0 — **COMPLETE**.
- [x] **ADDRESS-001** — Ingest verified source by chain/address with provenance — P2 — **COMPLETE**.
- [x] **AI-001** — Correlate and explain deterministic evidence without inventing findings — P2 — **COMPLETE**.

## M6 — Audit-ready release (`1.0.0`)

- [x] **SCHEMA-001** — Freeze and document versioned JSON/SARIF compatibility — P0 — **COMPLETE**.
- [x] **BENCH-002** — Measure per-rule precision and recall on a versioned labelled corpus — P0 — **COMPLETE**.
- [x] **COMPAT-001** — Publish supported Python, Solidity, EVM, and Foundry ranges — P0 — **COMPLETE**.
- [x] **SECURITY-001** — Add threat model, secure-use guidance, and disclosure policy — P0 — **COMPLETE**.
- [x] **DOCS-001** — Complete install, rule, CI, proof, and contributor documentation — P0 — **COMPLETE**.
- [x] **RELEASE-001** — Produce reproducible package artifacts and a signed release checklist — P0 — **COMPLETE**.

## M7 — Bounty Hunter Mode (`1.1.0`)

The complete architecture, phase gates, product boundaries, and validation
strategy are defined in the
[M7 Bounty Hunter Mode plan](docs/BOUNTY_HUNTER_PLAN.md). M7 is a local research
assistant with mandatory human approval. Automatic submission, live-network
exploit execution, automatic confirmation, and payout prediction are out of
scope.

Work in dependency order.

### [x] BOUNTY-001 — Profile schema, command contract, and workspace model — P0 — **COMPLETE**

Define the versioned bounty profile, private local workspace, and public CLI
contract before implementing later workflow stages.

Acceptance criteria:

- a versioned TOML schema records program identity, rules URL, review date,
  source location, immutable revision/content identity, in-scope paths and
  impacts, restrictions, and an explicit authorization acknowledgement;
- incomplete authorization, mutable source identity, unknown keys, or ambiguous
  scope fails validation;
- workspace records are placed outside the target tree, use relative paths and
  atomic writes, and never overwrite existing user files silently;
- the provisional `holes bounty` command family, JSON envelopes, exit statuses,
  and compatibility policy are documented and snapshot tested;
- there is no submission, upload, email, transaction, or remote-RPC command;
- ordinary scanner commands and frozen `1.0` output schemas remain unchanged.

Depends on: `CONFIG-001`, `SCHEMA-001`, `SECURITY-001`.

### [x] BOUNTY-002 — Pinned source provenance and default-deny scope — P0 — **COMPLETE**

Resolve approved source identity and ensure the scanner consumes only declared
in-scope content.

Acceptance criteria:

- local Git targets require an exact commit and clean/reproducible source
  identity; non-Git input requires a deterministic content manifest;
- every scanned file maps to an approved relative path and recorded digest;
- scope checks cover explicit files, directories, imports, remappings,
  dependencies, generated sources, path traversal, and symlink escapes;
- stale revisions, changed bytes, missing assets, and out-of-scope compiler
  source units fail closed with specific diagnostics;
- the source manifest binds scanner version, profile digest, source revision,
  file digests, and compiler provenance;
- acquisition, when separately requested, remains distinct from offline scope
  validation and scanning.

Depends on: `BOUNTY-001`, `ADDRESS-001`.

### [x] BOUNTY-003 — Offline and private-workspace safety controls — P0 — **COMPLETE**

Harden bounty commands for untrusted targets and confidential reports.

Acceptance criteria:

- scan, triage, proof, report, approval, and export paths perform no network
  operation by default and never send transactions;
- inherited RPC, wallet, explorer, cloud, CI, and common credential variables
  are removed from native subprocess environments;
- target build scripts, tests, plugins, hooks, and deployment scripts are not
  executed implicitly;
- private records use restrictive permissions where supported and are covered
  by recommended ignore patterns;
- shareable output redacts secrets, credential-bearing URLs, temporary paths,
  and local absolute paths;
- adversarial tests cover malicious profiles, source trees, Foundry settings,
  symlinks, oversized inputs, timeouts, and attempted environment leakage;
- the threat model and secure-use guide document residual risk and operator
  responsibilities.

Depends on: `BOUNTY-001`, expands with `BOUNTY-002` and `BOUNTY-006`.

### [x] BOUNTY-004 — Stable candidates and human review state — P0 — **COMPLETE**

Store immutable scanner observations separately from explicit reviewer
decisions.

Acceptance criteria:

- candidate IDs bind the target revision, profile, scanner version, rule, and
  finding fingerprint and are stable across identical runs;
- re-scans preserve resolved/rejected history without mutating observations;
- supported states are `new`, `investigating`, `rejected`, `confirmed`, and
  `approved`, with a tested transition table;
- `rejected` requires a reason, `confirmed` requires reviewer reasoning and an
  impact statement, and `approved` requires scope revalidation plus a complete
  report checklist;
- no scanner, proof, ranking, or AI result can automatically enter `confirmed`
  or `approved`;
- review records retain timestamps and reviewer-supplied identity without
  embedding secrets or source contents unnecessarily;
- text and versioned JSON inspection are deterministic and auditable.

Depends on: `BOUNTY-002`, `AI-001` only as an optional explanatory input.

### [x] BOUNTY-005 — Explainable review-priority ranking — P1 — **COMPLETE**

Order candidates for investigation without claiming exploitability, bounty
severity, or expected payout.

Acceptance criteria:

- ranking uses only versioned, inspectable signals such as detector severity,
  confidence, evidence completeness, reachability, proof availability, and
  supported-class metadata;
- each score exposes component values and stable reason codes;
- deterministic tie-breaking produces identical order for identical inputs;
- program impact categories may be displayed but do not silently replace
  scanner severity or prove impact;
- missing or unknown facts lower confidence or remain explicit rather than being
  treated as safe;
- tests prevent ranking labels from being rendered as confirmed vulnerabilities,
  payout estimates, or submission recommendations.

Depends on: `BOUNTY-004`, existing rule catalog and evidence paths.

### [x] BOUNTY-006 — Isolated local proof workspace — P0 — **COMPLETE**

Generate a candidate-specific Foundry workspace for locally reproducing a
primitive or project impact when the reviewer can provide the required setup.

Acceptance criteria:

- proof manifests bind candidate, target, source, compiler, generated files,
  reviewer-supplied setup, and result hashes;
- generated projects are separate from both target and bounty workspaces and do
  not modify the source checkout;
- offline local execution is the default and inherited RPC/wallet settings are
  removed;
- deployment, actor, balance, oracle, fork, timing, calldata, and invariant
  requirements remain explicit unknowns until supplied;
- a primitive proof is never labelled as protocol impact without a separate
  impact assertion and successful result;
- failure, timeout, tampering, unsupported setup, and inconclusive outcomes are
  structured states that cannot confirm a candidate;
- remote forks, if considered in a future task, require a new threat-model review
  and explicit design approval; they are not part of M7's default workflow.

Depends on: `BOUNTY-003`, `BOUNTY-004`, `PROOF-003`, `RUNNER-001`.

### [x] BOUNTY-007 — Private report, approval, and local export — P0 — **COMPLETE**

Render a complete bounty-report draft and require human approval before creating
shareable local output.

Acceptance criteria:

- Markdown and versioned JSON reports contain target/source identity, in-scope
  impact, summary, technical details, preconditions, evidence, reproduction,
  proof results, remediation, limitations, and unresolved questions;
- unconfirmed observations are visibly labelled as hypotheses;
- report content is bound to profile, candidate, source, proof, and review
  digests and becomes stale when any input changes;
- approval requires a confirmed candidate, current scope validation, complete
  checklist, reviewer identity, and explicit acknowledgement that program rules
  were rechecked;
- export writes to an explicit local destination without overwrite and performs
  no submission, upload, email, disclosure, chain, or remote-platform action;
- private and shareable renderers are tested for secret and absolute-path
  redaction;
- secure-use documentation explains manual submission and coordinated
  disclosure responsibilities.

Depends on: `BOUNTY-004`, `BOUNTY-006` when a proof is required.

### [x] BOUNTY-008 — Historical disclosed-vulnerability corpus — P0 — **COMPLETE**

Measure usefulness on real, already-public cases without turning the checked-in
synthetic regression score into a market claim.

Acceptance criteria:

- the manifest contains at least ten disclosed cases from at least five
  independent projects with immutable source, disclosure, root-cause, date,
  license/provenance, and supported/out-of-model labels;
- third-party source is checked in only when redistribution is permitted;
  otherwise a reproducible fetch/verification manifest is used;
- labels and supported-class decisions are written before scanner results are
  evaluated, with calibration and holdout subsets kept distinct;
- metrics include candidate precision, supported-class recall, investigation
  count, rejected candidates, evidence completeness, and out-of-model cases;
- at least three independent historical vulnerabilities in supported classes
  must produce useful investigation evidence for the M7 product claim to pass;
- raw results and limitations are versioned and reproducible without requiring
  live-network writes or funded credentials;
- failure to meet the product claim is reported as a go/no-go result, not hidden
  by changing labels or fixtures.

Depends on: can begin after `BOUNTY-001`; evaluation completes after
`BOUNTY-005` and may exercise `BOUNTY-006`.

### [x] BOUNTY-009 — Authorized end-to-end pilot — P1 — **COMPLETE**

Exercise the complete local workflow against one explicitly authorized target
without requiring a bounty submission.

Acceptance criteria:

- the operator records the program rules, exact source revision, scope,
  restrictions, review date, and authorization acknowledgement;
- profile validation, scope scan, candidate triage, proof decision, report draft,
  approval decision, and local export are exercised and logged;
- findings are handled privately and no target is contacted or disclosed by the
  tool;
- no live-network transaction, public-testnet execution, or automatic platform
  interaction occurs;
- workflow time, candidate counts, review decisions, friction, and safety
  failures are recorded without publishing confidential details;
- any real report submission remains a separate manual user decision governed by
  the selected program.

Depends on: `BOUNTY-002` through `BOUNTY-008`.

### [x] BOUNTY-010 — Documentation and signed `1.1.0` release — P0 — **COMPLETE**

Stabilize the bounty workflow only after its safety and historical-evaluation
gates pass.

Acceptance criteria:

- installation, CLI, profile schema, workspace lifecycle, proof workflow,
  report/approval flow, threat model, secure use, and evaluation are documented;
- compatibility and migration policy distinguishes frozen `1.0` scanner output
  from new versioned bounty records;
- all unit, integration, adversarial, reproducibility, documentation, and
  historical-corpus tests pass from a clean checkout;
- build artifacts are reproducible and smoke-tested in a fresh environment;
- changelog, task tracker, development plan, release checklist, checksums, and
  signed tag are complete;
- release messaging says research assistant, requires human validation, and
  makes no payout, completeness, audit-equivalence, or automatic-submission
  claim.

Depends on: `BOUNTY-001` through `BOUNTY-009`.

## M8 — Private Real-World Validation

M8 applies the released local workflow to an external target only after its
owner or bounty program explicitly authorizes the review. No target interaction,
submission, disclosure, transaction, or remote exploit execution is automatic.

- [x] **OPS-001** — Create the private `nuncij/contract-holes` GitHub repository,
  push `main`, and push the signed `v1.0.0` and `v1.1.0` tags — P0 — **COMPLETE**.
- [x] **OPS-002** — Add production CI, publish and verify the signed `v1.1.0`
  GitHub release assets, and enable available repository security controls — P0
  — **COMPLETE**.
- [x] **OPS-003** — Update vulnerable release-build pins, verify the dependency
  graph and reproducible build, close superseded automated PRs, and publish the
  signed `v1.1.1` security patch without changing `v1.1.0` — P0 — **COMPLETE**.
- [x] **PILOT-002** — Select OpenZeppelin Confidential Contracts `v0.4.0`, pin
  the program rules, exact commit, 22 source paths, impacts, and restrictions,
  and record the comparison in
  [the M8 target selection](docs/research/M8_TARGET_SELECTION.md) — P0 —
  **COMPLETE**.
- [x] **PILOT-003** — Run the 22-file source-only workflow privately at the
  approved commit, produce an empty candidate ledger, verify deterministic
  replay, and perform no proof, report, export, submission, or target contact —
  P0 — **COMPLETE**.
- [x] **EVAL-002** — Compare the real trial with historical/synthetic results and
  document false positives, unknown recall, evidence quality, audit context,
  workflow time, and resource use in
  [the M8 trial evaluation](docs/research/M8_OPENZEPPELIN_TRIAL.md) — P0 —
  **COMPLETE**.
- [x] **BACKLOG-001** — Convert only the observed compiler-dependency boundary
  into `COMP-003`; retain FHE semantics and verbose exact paths as explicit
  limitations rather than adding speculative mechanisms — P1 — **COMPLETE**.

## Observed post-M8 backlog

- [x] **COMP-003** — Add a separate, immutable, read-only compiler-dependency
  boundary so exact bounty assets can receive compiler-backed analysis without
  making dependencies reportable or broadening the approved scope — P1 —
  **COMPLETE**.

  Acceptance criteria:

  - reportable source paths and compiler-only dependency paths are explicit,
    separately hashed, and fail closed;
  - findings and candidate IDs can originate only from reportable source paths;
  - dependency resolution remains offline and cannot load or execute target
    configuration, hooks, tests, scripts, plugins, or network settings;
  - the current profile schema and source-only behavior remain compatible;
  - tests cover dependency tampering, traversal, symlinks, ambiguous duplicate
    units, and attempted findings from dependency files.

- [x] **PILOT-004** — Create a new private workspace and run the approved target
  through offline compiler analysis using exact reportable and compiler-only
  dependency paths — P1 — **COMPLETE**.

  Acceptance criteria:

  - the operator explicitly approves compiler-enabled local analysis of the
    pinned target before a new scan starts;
  - the existing source-only workspace and its records remain unchanged;
  - the new profile pins the same clean commit and separates reportable assets
    from compiler-only source units;
  - the scan remains local, private, offline, and performs no target, chain,
    platform, proof, report, export, or submission action;
  - results and limitations are added to the private trial evaluation.

  Depends on: `COMP-003`.

- [x] **PILOT-005** — Review the 51 compiler-backed candidates against the
  pinned source and program impact rules — P1 — **COMPLETE**.

  Acceptance criteria:

  - every candidate remains private and receives an explicit human decision
    with a reason before any precision claim is made;
  - review distinguishes duplicated or conservative analysis signals from
    plausible security defects without automatically changing detector logic;
  - proof, report, approval, export, disclosure, submission, chain action, and
    target contact remain separate, explicitly approved actions;
  - only observed, labelled gaps become product work items.

  Depends on: `PILOT-004`.

- [ ] **PILOT-006** — Resolve the sole investigating candidate with focused
  trust-boundary analysis and an offline local proof — P1 — **NEXT, LOCAL WORK
  AUTHORIZED**.

  Acceptance criteria:

  - the exact candidate ID and evidence remain only in the private workspace;
  - analysis determines whether the reported call can reach an untrusted
    callback in the approved reference integration;
  - the operator's 2026-08-12 standing authorization covers proof generation
    and execution for this exact trial;
  - analysis and proof execution remain local, private, isolated, and offline;
  - a human decision records either rejection or confirmation with a concrete
    in-scope impact;
  - no report, approval, export, disclosure, submission, chain action, or target
    contact occurs.

  Depends on: `PILOT-005`.

- [ ] **PRECISION-001** — Convert the 50 rejected real-trial labels into generic
  safe regression fixtures and the smallest detector precision fixes — P1 —
  **QUEUED**.

  Acceptance criteria:

  - private target code, paths, candidate IDs, and evidence are not copied into
    repository fixtures or documentation;
  - pure/internal calls and user-defined value-type conversions are not treated
    as external interactions;
  - intended callbacks, immutable deployment targets, role checks, and
    caller-owned mapping writes retain enough context for accurate review;
  - existing positive corpus findings remain detected; broad name- or
    project-specific suppressions are not added.

  Depends on: `PILOT-005`.

## Definition of done for every task

- Acceptance criteria above are satisfied.
- Positive, negative, and regression tests pass.
- Findings and public output remain deterministic.
- User-facing behavior and limitations are documented.
- `TASKS.md` and the milestone status are updated in the same commit.
- `git diff --check`, the full Python suite, and any relevant Forge proof pass.
