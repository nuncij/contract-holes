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

These are review signals, not proofs. Findings include confidence and evidence;
the scanner deliberately does not claim that a clean report means a contract is
safe.

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

## Inspecting compiler analysis

Developers can inspect the compiler-backed model separately from security
findings:

```bash
holes inspect contracts/ --offline
holes inspect contracts/ --file Vault.sol --contract Vault --function withdraw
```

The command emits deterministic JSON containing project-index summaries,
inheritance, callable nodes, call edges, data-flow facts, guard recognition, and
reentrancy traces. `--file`, `--contract`, and `--function` are repeatable;
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
forge test --match-path 'test/holes/*.t.sol'
```

Automatic proofs currently cover `SOL007`. They demonstrate the collision but
do not claim protocol impact; that still requires checking how the contract uses
the hash. Generated files are deterministic, and the scanner refuses to
overwrite a proof that was manually changed.

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

The project is currently at `0.3.0`. M0, M1, and M2 are complete. The compiler
index, inheritance resolver, call graph, reusable data-flow facts,
interprocedural `SOL005` analysis, versioned multi-file corpus, deterministic
inspection JSON, and repeatable benchmark are complete. `SOL008` now traces
externally controlled call destinations across aliases and internal helpers. The
next task is `RULE-009`: authorization reachability and exposed privileged state
changes.

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
