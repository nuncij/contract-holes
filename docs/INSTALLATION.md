# Installation

## Requirements

Contract Holes supports CPython 3.10 through 3.14. Source-only scanning has no
runtime package dependencies. Compiler-backed scans, inspection, evaluation, and
proof execution additionally require a supported Foundry installation and a
project-compatible solc release; see [toolchain compatibility](COMPATIBILITY.md).

Linux is the published reference platform. Use a disposable environment and the
[secure-use guide](SECURE_USE.md) when the source repository is not fully trusted.

## Install from a checkout

Clone or otherwise obtain a reviewed repository revision, then create a virtual
environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/holes --version
```

An editable install is convenient for development. For a stable local install,
replace `-e .` with `.`. The package has no required third-party runtime
dependencies.

Without installation, run from the repository root:

```bash
PYTHONPATH=src python3 -m contract_holes --version
PYTHONPATH=src python3 -m contract_holes tests/fixtures/SafeVault.sol
```

## Install a reviewed wheel

Release artifacts include a pure-Python wheel and source distribution. Verify
the artifact digest and release attestation/checklist before installation, then:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ./contract_holes-1.1.1-py3-none-any.whl
```

If a package index is used, pin the exact reviewed release rather than an open
range. The canonical repository and release notes are the authority for artifact
names and hashes; do not install a similarly named package from an unverified
publisher.

## Add compiler support

Install a supported Forge release using the official
[Foundry installation instructions](https://getfoundry.sh/introduction/installation/).
Foundry normally selects solc from the target project's pragma/configuration and
may download it. Preinstall the required compiler and use `--offline` for a
reproducible or network-restricted scan.

Verify the complete host:

```bash
holes compatibility
forge --version
holes contracts --compile --offline
```

The `holes compatibility` command reports the policy plus observed Python,
Foundry, and PATH solc versions. The PATH solc is informational because Foundry
can select a project-specific compiler.

## Smoke checks

After installation:

```bash
holes --version
holes compatibility
holes rules SOL001
```

From a source checkout, run the complete suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

If compiler tests are skipped, install Foundry and the corpus compiler before
claiming compiler-mode validation. The versioned evaluation command is documented
in [precision and recall evaluation](EVALUATION.md).

## Upgrade and uninstall

Upgrade by installing another reviewed exact wheel or checkout revision into the
same virtual environment. Read schema, compatibility, and security notes before a
major-version change. Remove the environment to uninstall cleanly, or run:

```bash
.venv/bin/python -m pip uninstall contract-holes
```

Contract Holes does not write global configuration. Scan outputs, baselines,
fetched source, and generated proofs are user-selected project artifacts and are
not removed by package uninstall.
