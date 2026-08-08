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

Python 3.10 or newer is required.

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

Add `--compile` to validate the project with Foundry and enable rules that need
solc types and AST structure:

```bash
holes contracts/ --compile
holes contracts/ --compile --offline
```

Compilation happens in an isolated temporary directory, so the scanner does not
modify the project's Foundry cache or artifacts. Foundry may download a matching
solc version unless `--offline` is used.

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

- [Development plan](docs/DEVELOPMENT_PLAN.md) — architecture, current capability,
  rule maturity, milestones, and release gates.
- [Task tracker](TASKS.md) — task IDs, priorities, dependencies, acceptance criteria,
  completed work, and the single next task.

The project is currently at `0.5.0`. M0 through M4 are complete. The compiler
index, inheritance resolver, call graph, reusable data-flow facts,
interprocedural `SOL005` analysis, versioned multi-file corpus, deterministic
inspection JSON, and repeatable benchmark are complete. `SOL008` traces
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
complete, including user-supplied per-step invariants. The next task is
`CI-001`, a reusable SARIF and baseline CI workflow.

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

The fallback parser masks comments and string contents while preserving offsets,
then identifies contract and function regions. With `--compile`, solc source maps,
exact state declarations, function boundaries, and expression types take
precedence. Rules return structured findings; reporters render the same findings
as terminal text, JSON, or SARIF 2.1.0.

## Roadmap

The concise roadmap is M2 cross-contract analysis, M3 high-value detectors, M4
dynamic verification, M5 team/CI workflow, and M6 audit-ready `1.0.0`. See the
[development plan](docs/DEVELOPMENT_PLAN.md) for release gates and
[TASKS.md](TASKS.md) for the ordered backlog.

Only scan contracts you own or are authorized to assess.
