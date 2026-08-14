# Changelog

All notable project changes are recorded here. Versions follow semantic
versioning; public JSON/SARIF schemas have their own compatibility rules.

## Unreleased

### Closed

- Published the repository publicly under its existing MIT license after a
  full-history audit (no target source, private digest, candidate identifier,
  finding, or credential in any commit) and a program-rules check (the programs
  restrict disclosure of vulnerabilities, of which there are none). Added
  [the retrospective](docs/RETROSPECTIVE.md): the negative result across four
  bounty targets, the in-model/out-of-model split that explains it, and the
  freeze-and-replay research discipline worth reusing.
- **The project is closed as of 2026-08-14** at the signed `1.1.1` release. Four
  authorized real-world bounty trials scanned 39 reportable files, produced 157
  candidates, and confirmed none; no report, export, disclosure, submission,
  chain action, or target contact ever occurred. The ceiling is structural rather
  than a sample-size or tuning problem: the detectors recognize local primitives,
  while the frozen historical corpus labels the families that current bounty
  programs pay for — share pricing, verification logic, share accounting,
  flash-loan governance, and health-check invariants — as out-of-model. Two
  independent engines evaluated the same evidence and both recommended stopping.
  Added [the closeout record](docs/PROJECT_CLOSEOUT.md) with the decision, the
  measured evidence, the reusable components, and the two reopening conditions;
  marked `README.md`, `TASKS.md`, `docs/DEVELOPMENT_PLAN.md`, and
  `docs/NEXT_SESSION_PROMPT.md` closed. No task is queued and none will be
  added. Corrected the `PILOT-009` precision row to state 0 of 25 under its own
  reviewer labels, with independently established precision still undefined.

### Fixed

- Isolated bounty compiler now derives the direct-library remappings that the
  approved closure actually requires. When a reportable or compiler-only file
  imports an uncovered package path such as `v4-periphery/src/...`, and the
  exact unit is already declared below `lib/<name>/`, the compiler appends
  `<name>/=lib/<name>/` in stable lexical order to the temporary staging
  `remappings.txt`. `libs = []` stays empty, explicit validated `remappings.txt`
  entries remain authoritative, undeclared imports still fail closed, and no
  profile/source-manifest schema or legacy digest changes when no mapping is
  derived. This closes the `COMP-005` gap observed in the frozen PILOT-009
  EulerSwap closure. Added a fail-closed regression proving an active derived
  mapping cannot widen the approved closure to an undeclared sibling file in the
  same library. Suite: 248 tests.

### Documentation

- Completed `COMP-005` and `PILOT-009`. Repair commit `04781a9` was pushed to
  `main` and GitHub CI run `31787480206` passed both Quality and Reproducible
  package. Two new private offline scans of the unchanged frozen EulerSwap v2
  closure (five reportable plus 56 compiler-only files, schema `1.2`, Solidity
  `0.8.27`) reproduced byte-identical profile, source-manifest, scan, and
  candidate-ledger identities; all 25 candidates received a private review
  decision and none was confirmed. The source manifest still matches the frozen
  pre-scan manifest, so the source and dependency sets are unchanged. The
  evaluation, plans, task tracker, and next-session handoff are updated; no
  task is currently queued. The observed-backlog verdict is recorded: all 25
  rejected candidates (23 `SOL008`, 1 `SOL005`, 1 `SOL003`) fall inside the
  manual-review and unsatisfied boundaries `PRECISION-002` already documents
  (factory-owned target provenance, callback safety for creation and fresh
  targets, immutable deployment trust boundaries, governance/config-derived and
  role-controlled call targets, and caller-harm-only or self-directed targets
  without harmless-use analysis), so the untouched target confirmed the
  documented boundaries and no follow-up precision task is opened.
- Added the queued `COMP-005` plan for the generic direct-library remapping
  repair exposed by PILOT-009. Rewrote the next-session handoff as a coordinator
  prompt: OpenCode with `opencode-go/deepseek-v4-flash` implements the task, and
  the primary session independently verifies code, tests, private replay,
  documentation, Git, and CI.
- Completed `PRECISION-002`: commit `2574b6e` was pushed to `main` and GitHub
  CI run `31720097982` passed both Quality and Reproducible package. The final
  fresh private offline replay was an exact match (Solidity `0.8.28`, ten
  reportable files, 59 findings/candidates, SOL003=1 SOL005=13 SOL008=41
  SOL009=3 SOL011=1, 22 removed and none added). The frozen audit result and the
  versioned historical result (candidate precision 0.933333, supported recall
  and evidence 1.0) are recorded.
- Updated the `PRECISION-002` plan and tracker after resolving all
  independent-review blockers, recording the versioned historical result, the
  completed private offline replay, the unsatisfied governance/config-derived
  and factory-owned families, and the completion of the review, commit, push,
  and CI steps.
- Added the queued `PILOT-009` plan and rewrote the next-session prompt to
  start `PILOT-009`: validate detector commit `2574b6e` on a genuinely
  untouched target that is not OpenZeppelin, Silo, or Olas.
- Marked `PILOT-009` IN PROGRESS and added the public
  [target-selection record](docs/research/PILOT_009_TARGET_SELECTION.md) for
  the EulerSwap v2 Ethereum subset at commit
  `81cf6dc988468fd56f690e6bc0e338a5be02d034`. Every claim was re-checked
  against Euler's pinned first-party verification manifest (`euler-interfaces`
  commit `d938bc264d6e1cee68a559798044d43ade8ac95e`) and the pinned source
  trees; the tag `eulerswap-2.0` resolves to the same commit, `foundry.toml`
  pins Solidity `0.8.27`, and the candidate dependency graph is a bounded,
  fully pinned gitlink set. No target source has been downloaded or scanned.
- Completed the PILOT-009 acquisition and freeze, then recorded the trial as
  UNSATISFIED. The exact pinned EulerSwap v2 source and its recursive
  submodule closure (five reportable and 56 compiler-only Solidity files) were
  acquired, verified against the public record, and frozen clean and
  user-read-only with Git metadata. Both private workspaces then failed
  deterministically at the compile stage before any scan: the fixed detector
  commit `2574b6e` cannot reproduce Foundry's automatic submodule remapping
  (its isolated compiler writes `libs = []` and loads only the target
  `remappings.txt`), so the import `v4-periphery/src/utils/BaseHook.sol` from
  `src/UniswapHook.sol` in the reportable closure cannot resolve even though a
  standalone offline trial compile of the identical 61-file closure succeeds
  with Solidity `0.8.27` when the automatic remapping is present. No scan or
  candidate identity exists, so the completion gate fails; EulerSwap is
  retained as a research corpus and a detector repair plus a re-trial are
  required. See [the evaluation](docs/research/PILOT_009_EVALUATION.md).
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
- Added the completed `PILOT-008` Olas target selection and aggregate evaluation,
  plus the `COMP-004` exact-compiler profile plan.

### Bounty workflow

- Added optional `--compiler-version X.Y.Z` to bounty initialization. The value
  must be an exact release inside the published supported Solidity range and is
  rejected with `--source-only`.
- Pinned profiles emit additive normalized profile and source-manifest schemas
  `1.2`; the fixed temporary Foundry project writes `solc_version = "X.Y.Z"`
  instead of auto-detection, and the isolated compile fails closed unless the
  build reports one compiler release and it matches the pin.
- Preserved every legacy unpinned `1.0`/`1.1` profile, normalized payload, and
  digest byte-for-byte, and kept `scan.json` recording the compiler version
  strings observed in Foundry build information.
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

- Resolved all independent-review blockers on the `PRECISION-002` diff by
  narrowing or retaining findings, not by a no-callback proof. Compiler-resolved
  `view`/`pure` callees and `staticcall` no longer form `SOL005` reentrancy
  paths; state-changing calls, contract creation, and fresh-target initializers
  remain reportable. There is no no-callback proof and no blanket fresh or
  creation suppression.
- Replaced the loose timelock guard with a strict structural authorization
  mechanism: separate unconditional direct guards proving a nonzero pending
  value (`state != zero`) and an elapsed deadline via `block.timestamp >=
  deadline` (or `deadline <= timestamp`) over distinct state declarations.
  The pending value must feed the protected sensitive write without
  user-controlled taint. The mechanism then protects that write from `SOL009`. Exact
  zero-clears of the guarded pending/deadline fields are also accepted. No
  other later write inherits protection. Wrong comparison
  directions, timestamp `==`/`!=`, OR/optional delay, unrelated zero/nonzero
  flags, timestamp-only, mixed pending/caller values, deadline-derived writes,
  local pending reads,
  unrelated later privileged writes, compound expressions, and combined
  boolean guards still report.
- Immutable receiver identity never clears `external-return` taint; receiver
  identity is not provenance for returned targets, so governance/config-derived
  call lists remain `SOL008` manual-review findings.
- Created addresses carry non-user-controlled fresh provenance for `SOL008`;
  this says nothing about callback safety for `SOL005`.
- Deleted the read-result use tracer. A view/pure/staticcall `SOL008` sink is
  suppressed only when its result is ignored at the call site or the externally
  callable enclosing function is view/pure; in a non-view entry any used result
  (mapping key, state-changing call argument, or write value) reports `SOL008`,
  and mapping-index calls are evaluated so that use is not missed.
- Moved the unconditional-node check into the shared `dataflow` module so
  `authorization.py` reuses it instead of duplicating a private helper.
- Coalesce deterministic alternative evidence with the same fingerprint before
  report rendering, preserving the first representative trace and the frozen
  fingerprint definition.
- Keep compiler-resolved pure calls out of reentrancy interaction facts while
  retaining their external-target evidence.
- Carry `if`/`else` branch context through internal calls, preserve immutable
  target provenance through aliases and helper parameters, and keep
  `msg.sender` role self-grants reportable.

### Validation

- Resolved the `PRECISION-002` independent-review blockers by narrowing or
  retaining findings. Added adversarial-positive fixtures to the
  `precision-002` compiler corpus and `test_precision_002` (Solidity `0.8.25`):
  creation and fresh-target initializers, not-yet-elapsed/timestamp-equality/
  inequality/unrelated-flag/timestamp-only/OR-optional-delay, pending-not-
  feeding-the-write, mixed-pending/caller, deadline-derived-write,
  local-pending-read, and unrelated-later-write guards. Added read results used
  as a mapping key or state-changing call argument. Versioned the
  `m7-history-1` raw result after
  the view-interaction fix removed one out-of-model Enzyme `SOL005` candidate:
  candidate precision moved from 0.875 to 0.933333 with all five supported
  cases, 1.0 supported-class recall, 1.0 evidence completeness, and the `go`
  decision unchanged. Frozen `audit-1` evaluation is unchanged (33/33 positive,
  31/31 safe at 1.0). Suite: 238 tests. The final fresh private offline replay
  was an exact match: unchanged source and dependency identities, Solidity
  `0.8.28`, ten reportable files, 59 findings/candidates versus 81 before tuning
  (SOL003=1, SOL005=13, SOL008=41, SOL009=3, SOL011=1), 22 removed and none
  added — investigation leads, not vulnerabilities and not bounty submissions.
  Commit `2574b6e` reached `main`. GitHub CI run `31720097982` passed
  both Quality and Reproducible package. `PRECISION-002` is **COMPLETE**.

- Implemented `COMP-004` exact-compiler binding in the bounty profile and
  isolated compiler. The public `holes bounty init --compiler-version`,
  `validate`, and `scan`/`ScopedForgeCompiler` behaviors pass with new
  interface, schema, legacy-stability, and fail-closed tests. A new private
  pinned Olas replay selected only Solidity `0.8.30`, preserved the frozen
  source and dependency sets, scanned two reportable files, and again produced
  zero findings and candidates.

- Completed `PILOT-008` against the exactly mapped Olas governance `v1.2.5`
  subset. Two private offline Solidity `0.8.30` workspaces reproduced identical
  two-file scan and zero-candidate results. A preserved initial scan selected
  cached Solidity `0.8.28`, exposing that the profile did not bind an exact
  compiler. No detector, proof, report, export, disclosure, submission, RPC,
  chain action, platform write, or target contact occurred. `PRECISION-002` is
  the next precision milestone after `COMP-004`.

- Reopened `PILOT-007` after completion review. The initial repair
  (2026-08-13) reconstructed the untouched baseline, which is a reproducible
  `RecursionError` blocker at selection commit `08050a1`; proved the
  source-to-scope gate fails (the deployed in-scope assets are Silo `3.5.0`,
  commit `b1f428f`, not the pinned `4.26.0`, commit `570a668`); completed every
  private review-brief field for all 81 candidates; and added two genuine
  regressions. `PILOT-007` is unsatisfied and Silo is retained only as a
  research corpus.
- Completed `REPAIR-007` (2026-08-13). A new private Git-backed minimal
  checkout (only the three submodules intersecting the frozen 124-file compiler
  closure, with superproject Git metadata, user-read-only) is accepted by the
  public scanner; `holes bounty scan` reproduces the canonical 81-finding result
  offline, with only profile-bound digest differences (name, note, source root).
  The two compiler-backed regressions now assert expected semantic results and
  exact stable public evidence, and the deep-AST test uses `TemporaryDirectory`.
  The final Silo source-to-scope verdict stays **UNSATISFIED**. At that
  checkpoint, `PILOT-008` was the required next trial before `PRECISION-002`.

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
