# M7 Bounty Hunter Mode Development Plan

Last updated: 2026-08-08
Target release: `1.1.0`
Status: **In progress**

## Goal

Bounty Hunter Mode should turn an authorized, revision-pinned bounty target into
a private set of reproducible review candidates. It should remove repetitive
work around scope checking, scanning, evidence collection, local proof setup,
and report drafting without deciding that a vulnerability is real or submitting
anything on the reviewer's behalf.

The intended workflow is:

```text
review program rules and obtain authorization
  -> create and approve a pinned local bounty profile
  -> validate source identity and enforce in-scope paths
  -> run deterministic Contract Holes analysis
  -> rank candidates for human review
  -> reject, investigate, or confirm each candidate
  -> build and run an isolated local proof when appropriate
  -> draft a private report bound to source and evidence hashes
  -> require explicit human approval
  -> export for manual submission through the program's required channel
```

There will be no `submit` command. Export is a local file operation and never
contacts a bounty platform, project, chain, RPC endpoint, or public service.

## Product boundaries

M7 is a research assistant, not an autonomous hacker, exploit service, audit
replacement, or payout predictor.

It must not:

- scan a target until the user records the program, allowed source revision,
  in-scope paths, review date, and authorization acknowledgement;
- send transactions to mainnet, a public testnet, or any remote RPC endpoint;
- execute repository scripts, deployment scripts, or tests merely because they
  are present in a target checkout;
- classify a candidate as confirmed from a static finding alone;
- infer bounty severity or payout from scanner severity;
- submit, email, upload, or publicly disclose a finding;
- place API keys, RPC URLs containing credentials, wallet material, or private
  report contents in generated artifacts;
- describe a clean scan as evidence that the target is safe.

Program rules remain authoritative. The operator is responsible for confirming
that local source analysis, compiler use, forks, and proof techniques are
permitted for the selected target.

## Architecture

```text
bounty profile (human-approved TOML)
  -> profile/schema validation
  -> pinned source + scope resolver
  -> existing scanner/compiler pipeline
  -> immutable candidate observations
  -> separate human review decisions
  -> isolated proof workspace and result manifest
  -> deterministic private report renderer
  -> explicit approval record
  -> local export
```

Scanner observations and reviewer decisions remain separate. Re-running the
same scanner version against the same source revision and profile must reproduce
the observation set. Human status changes record who changed what, when, and
why without rewriting the underlying finding evidence.

### Local workspace

The initial design will use a user-selected workspace outside the target source
tree. It will contain only versioned schemas and generated records such as:

```text
bounty.toml
source-manifest.json
candidates.json
reviews.json
proofs/
reports/
```

Exact names are finalized by `BOUNTY-001`. Generated records use relative paths,
content hashes, atomic writes, deterministic ordering, and restrictive file
permissions for private material where the host supports them. The source tree
is never modified.

## CLI shape

The provisional command surface is:

```text
holes bounty init
holes bounty validate
holes bounty scan
holes bounty candidates
holes bounty review CANDIDATE_ID
holes bounty proof CANDIDATE_ID
holes bounty report CANDIDATE_ID
holes bounty approve CANDIDATE_ID
holes bounty export CANDIDATE_ID
```

These names are design inputs, not compatibility commitments. `BOUNTY-001` must
freeze a versioned profile and command contract before later tasks build on it.
Every command must have machine-readable output and documented exit statuses.

## Delivery phases

### Phase A — Safe scope foundation

Tasks: `BOUNTY-001`, `BOUNTY-002`, `BOUNTY-003`.

Deliver a versioned profile, immutable source provenance, default-deny scope
enforcement, and an offline workspace. A path, symlink, source revision, chain
address, or content hash outside the approved profile must fail closed with a
specific diagnostic.

Phase gate:

- incomplete or unapproved profiles cannot scan;
- every scanned byte is attributable to an approved source revision and path;
- target and workspace path traversal and symlink escape tests pass;
- normal bounty commands perform no network operations;
- private workspace data is excluded from source-control examples by default.

### Phase B — Candidate triage

Tasks: `BOUNTY-004`, `BOUNTY-005`.

Convert findings into stable review candidates and rank them using transparent
signals. Ranking may use detector severity, confidence, evidence completeness,
reachability, and proof support. It must call the result review priority, not
exploitability, bounty severity, or expected payout.

Allowed candidate states are initially `new`, `investigating`, `rejected`,
`confirmed`, and `approved`. A transition to `confirmed` requires a reviewer
reason and an impact statement. A transition to `approved` additionally requires
scope revalidation and a complete report checklist.

Phase gate:

- candidate IDs are stable across identical runs;
- observations cannot be altered by review state changes;
- ranking includes reason codes and deterministic tie-breaking;
- no automatic path reaches `confirmed` or `approved`;
- rejections and unresolved assumptions remain visible and auditable.

### Phase C — Local proof and private reporting

Tasks: `BOUNTY-006`, `BOUNTY-007`.

Generate isolated Foundry workspaces and report drafts from selected candidates.
Proof generation must distinguish a demonstrated code primitive from protocol
impact. Deployment, actor, balance, oracle, fork, and invariant assumptions stay
explicit until a reviewer supplies them.

The report contains target/source identity, in-scope impact, summary, technical
details, preconditions, evidence, reproduction, proof results, remediation,
limitations, and unresolved questions. Static observations are labelled as
hypotheses until human confirmation.

Phase gate:

- generated proofs default to local/offline execution with no inherited RPC or
  wallet configuration;
- proof and report inputs are content-hashed and tamper-evident;
- failed, unsupported, and inconclusive proofs cannot be rendered as confirmed;
- secrets and local absolute paths are redacted from shareable output;
- export produces local files only and requires an approval record.

### Phase D — Real-world validation and release

Tasks: `BOUNTY-008`, `BOUNTY-009`, `BOUNTY-010`.

Build a legally redistributable evaluation manifest from at least ten publicly
disclosed historical smart-contract vulnerabilities. Pin the source revision,
disclosure reference, root-cause label, expected supported/out-of-model status,
and licensing/provenance for every case. Full third-party source is checked in
only when its license permits redistribution.

The corpus is separated into calibration and holdout cases. Results report
candidate precision, supported-class recall, investigation effort, rejected
candidates, and cases outside the scanner's model. The checked-in synthetic
corpus and historical corpus are reported separately.

Phase gate:

- at least ten historical cases from at least five independent projects are
  reproducible from pinned public material;
- all cases have a predeclared root cause and supported/out-of-model label;
- supported-class recall and review precision are measured without converting
  out-of-model cases into silent successes;
- at least three independent historical vulnerabilities in supported classes
  are detected with evidence useful for human investigation;
- one end-to-end pilot uses an authorized profile and local-only workflow;
- no live exploit, public disclosure, or bounty submission is required for the
  `1.1.0` release gate;
- user, contributor, threat-model, and secure-use documentation is complete.

If the historical results do not demonstrate useful supported-class detection,
M7 still publishes the measurements but does not market Bounty Hunter Mode as a
bounty-finding product. The next plan must then prioritize detector improvements
before active-program use.

## Task order

| Order | Task | Outcome |
| --- | --- | --- |
| 1 | `BOUNTY-001` | Profile schema, command contract, and workspace model |
| 2 | `BOUNTY-002` | Pinned source identity and default-deny scope resolver |
| 3 | `BOUNTY-003` | Offline/network and private-workspace safety controls |
| 4 | `BOUNTY-004` | Stable candidates and human review state machine |
| 5 | `BOUNTY-005` | Explainable review-priority ranking |
| 6 | `BOUNTY-006` | Isolated local proof workspace |
| 7 | `BOUNTY-007` | Private report, approval, and local export |
| 8 | `BOUNTY-008` | Historical disclosed-vulnerability corpus |
| 9 | `BOUNTY-009` | End-to-end authorized pilot and measured evaluation |
| 10 | `BOUNTY-010` | Documentation, compatibility, and signed `1.1.0` release |

The executable acceptance criteria and dependencies are maintained in
[TASKS.md](../TASKS.md).

## Testing strategy

Every phase needs positive, negative, adversarial, and reproducibility tests.
The M7 suite must cover:

- malformed, incomplete, stale, and tampered profiles;
- out-of-scope paths, imports, remappings, symlinks, and revision changes;
- malicious source trees and unexpected build configuration;
- network/RPC environment removal and secret redaction;
- stable candidate IDs, deterministic ranking, and legal state transitions;
- proof timeout, failure, unsupported setup, and manifest tampering;
- report completeness, path redaction, and approval enforcement;
- historical-corpus provenance, label integrity, and metric calculation;
- unchanged behavior for ordinary `holes` scans and frozen `1.0` output schemas.

No test may require mainnet/public-testnet writes or possession of a funded key.
Network-required source acquisition is tested separately from the offline core
and must always be explicit.

## Decisions deferred until evidence exists

M7 intentionally does not commit to:

- automated platform integration or submission;
- payout prediction;
- hosted storage of private reports or source code;
- automatic exploit generation for arbitrary findings;
- a commercial license or hosted pricing model;
- support for a specific bounty platform's private API.

Those decisions belong after the historical evaluation and an authorized pilot
show that the workflow produces useful, reviewable candidates.
