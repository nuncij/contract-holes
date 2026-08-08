# Contract Holes

`holes` is a fast, evidence-first Solidity security scanner. It is intentionally
small enough to understand and extend: the first release has no runtime
dependencies and does not send contract source code to an external service.

It currently detects:

| Rule | Severity | Signal |
| --- | --- | --- |
| `SOL001` | High | `tx.origin` authorization risk |
| `SOL002` | Medium | Ignored return value from `.call` or `.send` |
| `SOL003` | High | `delegatecall` trust boundary |
| `SOL004` | High | `selfdestruct` usage |
| `SOL005` | High | Persistent state mutation after an external interaction |
| `SOL006` | Medium | Block properties hashed as a source of randomness |

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

The complete suite uses Python's standard library:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The parser masks comments and string contents while preserving byte offsets,
then identifies contract and function regions. Rules return structured findings;
reporters render the same findings as terminal text, JSON, or SARIF 2.1.0.

## Roadmap

The next useful layers are compiler AST/source maps, inheritance-aware data flow,
Foundry-generated exploit tests, transaction-sequence fuzzing, and protocol
invariants. AI belongs after those deterministic stages: it can correlate paths,
rank findings, explain impact, and draft proofs without being the sole source of
a security claim.

Only scan contracts you own or are authorized to assess.

