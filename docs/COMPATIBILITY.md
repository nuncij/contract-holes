# Toolchain compatibility

Contract Holes separates supported ranges from tested reference points. A range
means releases in that interval are accepted and maintained; the reference
matrix contains the boundary and fork combinations exercised by the compatibility
workflow.

## Supported ranges

| Component | Supported | Required for |
| --- | --- | --- |
| CPython | `>=3.10,<3.15` | Every command |
| Solidity | `>=0.8.20,<0.8.37` | Compiler-backed AST analysis and generated proofs |
| Foundry | `>=1.5.0,<1.8.0` | `--compile`, inspection, evaluation, and proof execution |
| EVM target | Paris, Shanghai, Cancun, Prague, Osaka | Compiler-backed analysis |

Foundry is optional for source-only scans. The source-only parser can inspect
files with other Solidity pragmas, but that is graceful fallback behavior rather
than a compiler-compatibility guarantee. Compiler-backed results outside the
published Solidity range are unsupported even if Forge happens to build them.

The upper bounds are exclusive. Supporting a new Python, Solidity, or Foundry
series requires a compatibility-policy update and CI evidence; it is not implied
by a successful installation. `pyproject.toml` enforces the Python range during
package installation.

## Reference matrix

The checked-in compatibility workflow covers Python 3.10, 3.11, 3.12, 3.13,
and 3.14 independently. It also performs compiler-backed scans at these points:

| Foundry | Solidity | EVM target |
| --- | --- | --- |
| 1.5.0 | 0.8.20 | Paris |
| 1.7.1 | 0.8.25 | Shanghai |
| 1.7.1 | 0.8.29 | Cancun |
| 1.7.1 | 0.8.31 | Prague |
| 1.7.1 | 0.8.36 | Osaka |

The matrix is in
[`examples/github-actions/compatibility.yml`](../examples/github-actions/compatibility.yml).
The normal regression and evaluation corpus remains pinned to Solidity 0.8.25,
so it is reproducible after that compiler is installed.

This policy follows the upstream [Python release series](https://www.python.org/downloads/),
[Foundry releases](https://github.com/foundry-rs/foundry/releases), and Solidity's
[compiler/EVM target documentation](https://docs.soliditylang.org/en/latest/using-the-compiler.html).
Solidity warns that choosing the wrong EVM target can change compilation behavior;
the target must match the chain on which the contract is intended to run.

## Inspect the current host

Run:

```bash
holes compatibility
```

The command emits deterministic policy fields plus observations for the current
Python interpreter, `forge`, and `solc` on `PATH`. Tool observations are labelled
`supported`, `unsupported`, `unavailable`, or `unrecognized`. Missing Foundry or
solc does not fail this informational command because source-only scanning does
not require either tool.

The observed `solc` executable is informational. Foundry can install and select a
different compiler for each project; the compiler versions used by an actual scan
are taken from Foundry build information and appear in compiler-aware benchmark,
inspection, and evaluation output.

## EVM and platform boundaries

EVM support means the scanner can consume compiler ASTs produced for the listed
targets. Contract Holes does not emulate a chain, validate a deployment's actual
fork, or make fork-sensitive findings automatically exploitable. In particular,
`SELFDESTRUCT` semantics differ from Cancun onward, so `SOL004` remains a manual
review signal tied to the deployment environment.

Linux GitHub-hosted runners are the published CI reference environment. Other
operating systems may work when a supported CPython and Foundry build is
available, but are not part of the 1.0 compatibility commitment.

When reporting a compatibility problem, include the output of
`holes compatibility`, the project compiler/EVM settings, and the smallest source
that reproduces the issue. Remove secrets and proprietary source before sharing.
