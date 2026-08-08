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

The project is currently at `0.2.0`. M0 and M1 are complete; M2 is underway.
The compiler index, inheritance resolver, call graph, reusable data-flow facts,
and interprocedural `SOL005` analysis (`AST-001` through `RULE-005-V2`) are
complete. The next task is `TEST-002`: turn the focused compiler tests into a
versioned multi-file positive and negative analysis corpus.

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
