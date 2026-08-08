# CI and SARIF

The template at
[`examples/github-actions/contract-holes.yml`](../examples/github-actions/contract-holes.yml)
runs a baseline-aware scan, uploads SARIF, and then restores the scanner's exit
status so a high-severity new finding fails the job.

## Adopt the workflow

1. Copy the template to `.github/workflows/contract-holes.yml` in the Solidity
   repository.
2. Add a reviewed `.holes.toml` with `scan.paths` and compiler settings.
3. Pin `CONTRACT_HOLES_INSTALL` to the package version or immutable Git commit
   your team reviewed. The example package spec is a placeholder until that
   release is available from your package source.
4. If existing findings are accepted, create and commit
   `.holes-baseline.json` as described in [BASELINES.md](BASELINES.md).
5. Adjust `--fail-on high` only as an explicit team policy decision.

The example pins Python and Foundry versions and uses current major versions of
the official checkout, Python setup, and CodeQL SARIF actions. For stricter
supply-chain policy, replace action major tags with reviewed full commit SHAs and
use dependency automation to propose updates.

The separate
[`compatibility.yml`](../examples/github-actions/compatibility.yml) example tests
all supported Python minors and the published Foundry/Solidity/EVM reference
points. It is a maintainer matrix, not required in every consuming repository.
See [toolchain compatibility](COMPATIBILITY.md) before changing those pins.

## Why the scan step captures status

`holes --fail-on high` exits 1 after writing a valid report when the gate finds a
matching issue. A configuration, compiler, or execution error exits 2. The
workflow captures that code instead of marking the scan step failed immediately:

- status 0 or 1 allows the valid SARIF file to upload;
- status greater than 1 fails the scan step and skips SARIF upload;
- the final step exits with the captured status, so findings still fail CI after
  upload.

When `.holes-baseline.json` exists, SARIF contains only new findings. Without a
baseline, every reported finding is new for gate purposes.

## Permissions and platform behavior

The job grants read-only repository access plus `security-events: write` for
SARIF upload. Keep the workflow-level token read-only and do not persist checkout
credentials. GitHub code scanning availability and SARIF upload behavior depend
on repository visibility, GitHub Advanced Security entitlement, event type, and
fork permissions. The scanner gate itself does not depend on SARIF upload and
still enforces the captured exit status.

The template installs Foundry because compiler-backed rules are the preferred
path. Set `compiler.offline = true` only when the required solc version is already
available on the runner; otherwise allow the initial compiler download and pin
the resulting tool versions in your reproducible CI image.
