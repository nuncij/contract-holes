# Contract Holes

`holes` is a fast, evidence-first Solidity security scanner. It is intentionally
small enough to understand and extend: the first release has no runtime
dependencies and does not send contract source code to an external service.

It currently detects:

| Rule | Severity | Signal |
| --- | --- | --- |
| `SOL001` | High | `tx.origin` authorization risk |
| `SOL002` | Medium | Ignored low-level call return value |
| `SOL003` | High | `delegatecall` trust boundary |
| `SOL004` | High | `selfdestruct` usage |
| `SOL005` | High | Persistent state mutation after an external interaction |
| `SOL006` | Medium | Block properties hashed as a source of randomness |
| `SOL007` | Medium | Multiple dynamic values in a packed hash encoding (compiler AST) |
| `SOL008` | High | User-controlled value reaches an external or `delegatecall` target |
| `SOL009` | High | Externally reachable privileged state write lacks dominating authorization |
| `SOL010` | High | Signature-authorized action lacks replay or validation protection |
| `SOL011` | High | Proxy initialization or versioned storage layout is unsafe |
| `SOL012` | Medium | ERC-20 return value or nominal transfer amount is assumed |
| `SOL013` | High | Oracle freshness, spot-price manipulation, or swap bounds are missing |

These are review signals, not proofs. Findings include confidence and evidence;
the scanner deliberately does not claim that a clean report means a contract is
safe.

Inspect the complete detector guidance or one rule directly:

```bash
holes rules
holes rules SOL005
holes rules SOL013 --format json
```

The catalog includes live severity/confidence metadata, vulnerable and safer
snippets, remediation, manual-review boundaries, and authoritative references.
See [rule catalog usage](docs/RULE_CATALOG.md).

## Quick start

CPython 3.10 through 3.14 is supported.
For wheel/source installs, Foundry setup, offline compiler use, upgrades, and
smoke checks, see [installation](docs/INSTALLATION.md).

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
holes contracts/
```

Without installing the package:

```bash
PYTHONPATH=src python3 -m contract_holes tests/fixtures/VulnerableVault.sol
```

Machine-readable reports and CI gating are built in:

```bash
holes contracts/ --format json
holes contracts/ --format sarif > holes.sarif
holes contracts/ --minimum-severity medium --fail-on high
```

The `1.1` development line adds a private, human-approved bounty research
workspace. Start by recording reviewed program rules, an immutable source
revision, explicit scope, and authorization; initialization does not scan or
contact any external service:

```bash
holes bounty init --help
holes bounty validate PRIVATE_WORKSPACE
holes bounty identify TARGET --scope contracts
holes bounty scan PRIVATE_WORKSPACE
holes bounty candidates PRIVATE_WORKSPACE
holes bounty review --help
holes bounty proof --help
holes bounty report --help
holes bounty approve --help
holes bounty export --help
holes bounty history tests/fixtures/bounty_history/manifest.json
holes bounty pilot tests/fixtures/bounty_pilot/manifest.json --output ../private-pilot
```

See the [bounty profile contract](docs/BOUNTY_PROFILE.md). There is deliberately
no automatic submission or live-network transaction command.

The [CLI reference](docs/CLI_REFERENCE.md) documents every command, exit status,
output stream, and option group.

JSON reports use the frozen Contract Holes `1.0` schema. SARIF follows version
2.1.0 plus a documented producer profile, with stable severity mapping and the
same finding fingerprint as JSON. Packaged schemas, fingerprint-v1 material, and
consumer versioning rules are in [output compatibility](docs/OUTPUT_COMPATIBILITY.md).

Add `--compile` to validate the project with Foundry and enable rules that need
solc types and AST structure:

```bash
holes contracts/ --compile
holes contracts/ --compile --offline
```

Compilation happens in an isolated temporary directory, so the scanner does not
modify the project's Foundry cache or artifacts. Foundry may download a matching
solc version unless `--offline` is used.

The compiler-backed compatibility commitment is Solidity 0.8.20 through 0.8.36,
Foundry 1.5.x through 1.7.x, and EVM targets Paris through Osaka. Inspect the
machine-readable policy and current host without scanning source:

```bash
holes compatibility
```

Supported versus tested versions, EVM caveats, and the reference CI matrix are
documented in [toolchain compatibility](docs/COMPATIBILITY.md).

## Project configuration

Place `.holes.toml` at the project root to share scan paths, exclusion globs,
rule selection, severity overrides, and compiler behavior:

```toml
schema_version = 1

[scan]
paths = ["src"]
exclude = ["mocks/**", "*.generated.sol"]
minimum_severity = "medium"

[rules]
disabled = ["SOL004"]

[rules.severity]
SOL005 = "critical"

[compiler]
enabled = true
offline = true
```

Then `holes` can run without a path. The nearest `.holes.toml` is discovered
from the working directory; use `--config FILE` or `--no-config` explicitly.
CLI paths and corresponding flags override configured values. Unknown keys,
rule IDs, severities, and contradictory compiler settings fail clearly. See
[configuration](docs/CONFIGURATION.md) for the complete schema and precedence.

Normal scans also enforce finite file-count, total-source-size, compilation,
total-time, and Python-memory boundaries. Configure them under `[limits]` or use
the matching CLI overrides; failures are execution errors rather than clean
scans. See [resource limits](docs/RESOURCE_LIMITS.md) for defaults and diagnostic
categories.

## Fetching verified source

Public verified Solidity can be ingested by chain and address before scanning:

```bash
export ETHERSCAN_API_KEY="your key"
holes fetch 1 0x1234567890abcdef1234567890abcdef12345678 \
  --output verified/example
holes verified/example --compile
```

The new output directory contains normalized source files, preserved standard
compiler input when available, and `provenance.json` with provider/compiler/proxy
metadata and SHA-256 hashes. It refuses overwrites, rejects unsafe source paths,
and never stores the API key. This records the explorer response; it does not
independently prove deployed-bytecode equivalence or follow proxy implementations.
See [verified-source ingestion](docs/VERIFIED_SOURCE.md).

## Baselines and new-finding CI

Create a reviewed fingerprint baseline, then gate only findings introduced after
that snapshot:

```bash
holes --write-baseline .holes-baseline.json
holes --baseline .holes-baseline.json --fail-on high --format sarif
```

Baseline mode reports only new findings and fails only when a new finding meets
`--fail-on`. JSON also includes new, existing, and resolved counts. Fingerprints
use paths relative to the baseline file, so a baseline stored at the repository
root is portable across checkouts. Creating refuses to overwrite; after review,
refresh explicitly with `--update-baseline`. Baselines contain locations and
fingerprints, not source excerpts. See [baseline workflow](docs/BASELINES.md).

A copy-ready GitHub Actions template is available at
[`examples/github-actions/contract-holes.yml`](examples/github-actions/contract-holes.yml).
It runs baseline-aware SARIF, uploads valid results for scanner statuses 0/1,
then restores the finding gate status. Review the install pin, permissions, and
platform notes in [CI and SARIF](docs/CI.md) before adoption.

## Evidence-bound AI explanations

AI can optionally annotate a completed JSON report after deterministic findings
exist:

```bash
holes contracts --format json > holes.json
holes explain holes.json --prepare
OPENAI_API_KEY="your key" holes explain holes.json > triage.json
```

The offline preparation step fixes correlation groups and evidence IDs. Online
mode uses strict Structured Outputs, then rejects missing/added groups and
unknown/cross-group evidence references. Model text stays labelled untrusted and
cannot affect findings, gates, SARIF, or proofs. Online mode sends report excerpts
and metadata to OpenAI; see [AI triage](docs/AI_TRIAGE.md) before using it with
confidential code.

## Inspecting compiler analysis

Developers can inspect the compiler-backed model separately from security
findings:

```bash
holes inspect contracts/ --offline
holes inspect contracts/ --file Vault.sol --contract Vault --function withdraw
```

The command emits deterministic JSON containing project-index summaries,
inheritance, callable nodes, call edges, data-flow facts, guard recognition,
reentrancy traces, target taint, authorization reachability, and signature
recovery-to-action hazards, proxy-upgrade evidence, and token amount flows.
Market-integrity traces include oracle freshness, AMM spot-price use, and router
swap protections.
`--file`, `--contract`, and `--function` are repeatable;
different filter types combine, while repeated values of one type are alternatives.
File filters match source-path suffixes, contract names are exact, and functions
accept either `withdraw` or `Vault.withdraw`.

Inspection always compiles with Foundry and writes JSON only to standard output.
The compiler build remains isolated in a temporary directory, and the payload
does not contain Solidity source contents.

## Benchmarking

Run source-only and compiler-backed correctness and performance measurements in
one command:

```bash
holes benchmark tests/fixtures/m2_corpus/src --offline > benchmark.json
holes benchmark tests/fixtures/m2_corpus/src --offline \
  --baseline benchmark.json > comparison.json
```

The JSON report separates source scanning, Foundry compilation, project-index
construction, and compiler-backed rule scanning. It records finding counts,
durations, compiler versions, diagnostics, and Python peak allocated memory.
The memory value covers this Python process and loaded compiler output; it does
not claim to include Forge's child-process peak RSS.

If the project root contains `expectations.json`, benchmark finding counts are
checked automatically. Correctness mismatches exit with status 1. Comparison to
a previous report labels performance changes over 20% but remains informational,
so variable wall-clock timings never make CI flaky.

For supported findings, the scanner can also write a standalone Foundry test
that reproduces the underlying vulnerability primitive:

```bash
holes contracts/ --compile --generate-proofs test/holes
holes proofs test/holes --timeout 60
```

Automatic artifacts cover `SOL007` and compiler-backed `SOL005` findings.
`SOL007` demonstrates the packed-encoding collision. `SOL005` writes a standalone
primitive test plus a configurable callback probe whose `run` function accepts
the deployed target, entry calldata, reentry calldata, and call values. The
generated model proves that nested execution is possible, not that the scanned
protocol is exploitable; its deployment, setup, authorization, funding, and
impact assertions still need project-specific configuration. Generated files
are deterministic, and the scanner refuses to overwrite a manually changed
artifact.

Each `.t.sol` file is paired with a versioned `.proof.json` requirements
manifest. It records finding provenance and the tested compiler/local-chain
settings separately from project-probe requirements. Unknown target compiler,
fork, constructor, funding, actor, calldata, and invariant setup stays `null`
and `configuration-required`; the generator does not guess it. See the
[proof requirements guide](docs/PROOF_REQUIREMENTS.md) for the schema and
handoff workflow.

`holes proofs` validates each source hash, creates one temporary Foundry project
per artifact, uses the manifest's compiler in offline mode by default, enforces
the per-artifact timeout, and emits JSON with pass, fail, timeout, or unsupported
status. It does not create Foundry cache or output files in the proof directory.
Use `--allow-downloads` only when the pinned compiler is missing and network use
is acceptable.

The `SOL005` artifact also contains a bounded transaction-sequence executor and
a dependency-free Foundry `testFuzz` entrypoint. A project test can provide up to
32 calldata/value steps, choose whether execution stops on a revert, and assert
against the recorded executed/succeeded counts and result digest. Calls originate
from the executor; multiple actors, time changes, token funding, and protocol
setup require a project adapter.

Project-specific invariants plug into the generated interface with a stable
assertion ID, boolean result, and arbitrary detail bytes. The sequence executor
checks the adapter before execution and after each step, emits the assertion ID,
step, result, and detail hash, and exposes a custom `HolesInvariantViolation`
error through `assertLastInvariant()`. Adapter reverts are reported as failed
invariants instead of being treated as safe.

Directories named `lib`, `vendor`, `node_modules`, `out`, `cache`, and
`artifacts` are skipped unless `--include-dependencies` is supplied.

## Suppressions

Accepted risks can be documented next to the affected line:

```solidity
// holes-ignore-next-line SOL003 -- audited proxy implementation
(bool success, ) = implementation.delegatecall(payload);
```

Use a comma-separated rule list when necessary. `all` suppresses every rule on
the associated line. Suppressions should include a reason and be reviewed like
code.

## Development

Project status and future work are tracked explicitly:

- [Documentation index](docs/README.md) — installation, CLI, team workflow,
  evidence, compatibility, and governance guides.
- [Development plan](docs/DEVELOPMENT_PLAN.md) — architecture, current capability,
  rule maturity, milestones, and release gates.
- [Task tracker](TASKS.md) — task IDs, priorities, dependencies, acceptance criteria,
  completed work, and the single next task.
- [Bounty workspace](docs/BOUNTY_PROFILE.md) — authorization, immutable target
  identity, scope, and private-workspace schema.
- [Bounty triage](docs/BOUNTY_TRIAGE.md) — stable candidates, explainable review
  priority, and auditable human state transitions.
- [Bounty proof and report workflow](docs/BOUNTY_PROOFS_REPORTS.md) — isolated
  local evidence, private reports, human approval, and checksummed local export.
- [Authorized bounty pilot](docs/BOUNTY_PILOT.md) — reproducible full-workflow
  evaluation, measured friction, and local-only safety checks.
- [Contributing guide](CONTRIBUTING.md) — development setup, rule workflow,
  compatibility constraints, tests, and review expectations.
- [Threat model](docs/THREAT_MODEL.md) and
  [secure-use guide](docs/SECURE_USE.md) — trust boundaries, residual risks, and
  safe local/CI operation.
- [Security policy](SECURITY.md) — supported versions, private reporting, and
  coordinated disclosure targets.

The latest release is `1.1.1`; M7 Bounty Hunter Mode is complete. M8 private
real-world validation is in progress: repository CI, private release assets, and
available dependency security controls are complete, while selection of the
first externally authorized target is next. The compiler index, inheritance
resolver, call graph, reusable
data-flow facts, interprocedural `SOL005` analysis, versioned multi-file corpus,
deterministic inspection JSON, and repeatable benchmark are complete. `SOL008` traces
externally controlled call destinations across aliases and internal helpers.
`SOL009` traces externally reachable ownership, administration, upgrade, role,
pause, operator, treasury, and fee-control writes and requires preceding
authorization. `SOL010` follows signature recovery through helpers to a
state-changing action and checks replay consumption, expiry, domain separation,
and zero-address recovery. `SOL011` checks initializer guards, proxy storage
feeding `delegatecall`, and explicit versioned storage prefixes. `SOL012` checks
typed ERC-20 returns and requested-amount credits after inbound transfers.
`SOL013` checks stale oracle use, direct AMM spot-price use, and ineffective
minimum-output/deadline arguments. The versioned `m3-1` corpus validates 25
positive labels and 24 safe labels across `SOL008` through `SOL013`. Configurable
`SOL005` reentrancy probes and calldata-driven transaction sequences are also
complete, including user-supplied per-step invariants. Scan resource limits are
now explicit and configurable. Verified-source ingestion records chain/address
provenance, and optional AI annotations are constrained to deterministic evidence.
The frozen output schemas, per-rule evaluation corpus, supported toolchain policy,
security boundaries, complete user/contributor documentation, reproducible
artifacts, and signed release evidence are ready. See the
[release process](docs/RELEASING.md), [signed checklist](release/1.1.1-checklist.md),
and [changelog](CHANGELOG.md).

`SOL009` requires compiler mode. Its privileged-state classification and branch
ordering are conservative, so findings can require review for custom authorization
frameworks and project-specific state semantics. A clean scan is not evidence
that every privileged operation was classified.

`SOL010` also requires compiler mode. It recognizes common nonce/digest state,
timestamp checks, and EIP-712-style chain/contract domains. Custom signature
libraries, invalidation schemes, cross-call digest provenance, and malleability
policies can require manual review; pure recovery utilities without a subsequent
action are intentionally not findings.

`SOL011` also requires compiler mode. It recognizes common initializer and proxy
patterns plus contract families named like `VaultV1`/`VaultV2`. Custom assembly
slots, packed or structured storage, diamonds, and upgrade relationships that
are not explicit in source naming need byte-accurate project-specific review.

`SOL012` requires compiler mode and resolved token declarations. It recognizes
common ERC-20/token interfaces and direct inbound recipients. Safe-transfer
wrappers, indirect vault recipients, accepted-token policy, and rebasing behavior
can require project-specific review.

`SOL013` requires compiler mode. It recognizes common Chainlink-style round
reads, AMM reserve/slot reads, TWAP method names, and V2-style router argument
positions. Custom oracle APIs, indirect price propagation, round-completeness
policies, TWAP window/liquidity quality, V3 swap structs, and custom router
semantics require manual review.

The complete suite uses Python's standard library:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Per-rule correctness is measured separately on the versioned `audit-1` corpus:

```bash
holes evaluate tests/fixtures/evaluation/manifest.json
```

It currently covers 33 positive and 31 safe labels across `SOL001`–`SOL013` and
reports TP/FP/FN plus macro/micro precision and recall. Its perfect checked-in
regression score is not a real-world accuracy claim; see
[precision and recall evaluation](docs/EVALUATION.md).

M7 also freezes ten already-public cases from ten independent projects, with
calibration/holdout splits and explicit supported/out-of-model labels:

```bash
holes bounty history tests/fixtures/bounty_history/manifest.json
```

The checked result records 16 investigation candidates, two reviewer rejections,
87.5% candidate precision, 100% supported-label recall, and useful evidence for
five independent supported cases. This is a bounded research-assistant claim,
not exploit confirmation or expected bounty performance; see the
[historical bounty evaluation](docs/BOUNTY_HISTORY.md).

The authorized end-to-end gate uses a repository-owned target and a frozen
human-reviewed manifest:

```bash
holes bounty pilot tests/fixtures/bounty_pilot/manifest.json \
  --output ../private-bounty-pilot-run
```

It exercises profile validation, pinned scope, two candidate decisions, an
unsupported proof decision, a complete private report, explicit approval, and
checksummed local export. It records 12 minutes of operator-event timeline,
three workflow-friction observations, and two successfully blocked unsafe
actions with zero safety failures. No target, network, chain, platform, or
submission action occurs; see the [authorized bounty pilot](docs/BOUNTY_PILOT.md).

The fallback parser masks comments and string contents while preserving offsets,
then identifies contract and function regions. With `--compile`, solc source maps,
exact state declarations, function boundaries, and expression types take
precedence. Rules return structured findings; reporters render the same findings
as terminal text, JSON, or SARIF 2.1.0.

## Roadmap

M0 through M6 produced the signed audit-ready `1.0.0` release. M7 completed a
human-controlled `1.1.0` bounty research workflow with pinned authorized scope,
candidate triage, isolated local proofs, private report drafts, historical
validation, an authorized repository pilot, and an explicit approval gate. It
will not submit reports or touch live networks. See the
[M7 Bounty Hunter Mode plan](docs/BOUNTY_HUNTER_PLAN.md),
[development plan](docs/DEVELOPMENT_PLAN.md), and [TASKS.md](TASKS.md).

Only scan contracts you own or are authorized to assess. Start untrusted code in
source-only mode and read the [secure-use guide](docs/SECURE_USE.md) before
enabling native compiler or proof execution.
