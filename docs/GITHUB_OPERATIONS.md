# GitHub Operations

Status checked: 2026-08-10

## Current private-repository state

| Control | State |
| --- | --- |
| Repository | `nuncij/contract-holes` is private; `main` is the default branch |
| Production CI | Enabled; both the compiler-backed 201-test job and reproducible-package job pass on `main` |
| Release | Private GitHub release `v1.1.0` is published from the signed tag with five verified assets |
| Dependency vulnerability alerts | Enabled |
| Automated dependency security fixes | Enabled |
| Open dependency alerts | None; the initial `setuptools` and `wheel` build-tool alerts are fixed on `main` |
| Branch protection and repository rulesets | Unavailable for this private repository on the current GitHub plan |
| Secret scanning and push protection | Unavailable for this private repository on the current GitHub plan |
| Private vulnerability reporting form | Not enabled while the repository is private; use a private maintainer contact or the private Security Advisory area |

The unavailable controls are plan limitations, not completed protections. GitHub
returned an explicit instruction to upgrade the account or make the repository
public for branch protection/rulesets, and rejected secret scanning as
unavailable for this repository.

## Release integrity

The [private `v1.1.0` GitHub release](https://github.com/nuncij/contract-holes/releases/tag/v1.1.0)
contains:

- `contract_holes-1.1.0-py3-none-any.whl`;
- `contract_holes-1.1.0.tar.gz`;
- `release-manifest.json`;
- `SHA256SUMS`;
- `SHA256SUMS.asc`.

After downloading all five files into one directory, verify them with:

```bash
gpg --verify SHA256SUMS.asc SHA256SUMS
sha256sum --check SHA256SUMS
```

The expected signing-key fingerprint is
`6A606D37A243C52A198D1807573A445A282E1FF5`. Verification must report a good
signature and an `OK` result for the wheel, source distribution, and manifest.

## When the repository becomes public or the plan changes

Before treating `main` as protected:

1. Enable a branch ruleset or branch protection for `main`.
2. Require these checks before merge:
   - `Quality / Python 3.13 / Foundry 1.7.1`;
   - `Reproducible package`.
3. Block branch deletion and force pushes.
4. Require pull requests for changes; choose an approval rule that still works
   for the actual maintainer team size.
5. Enable secret scanning and push protection.
6. Enable private vulnerability reporting before advertising the GitHub form as
   the primary external reporting channel.
7. Recheck code-scanning and dependency-review features under the new
   visibility or plan.

Do not make the repository public only to obtain these features. Public release
is a separate product and disclosure decision.
