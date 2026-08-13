# PILOT-008 Target Selection

Reviewed: 2026-08-13

Status: **SELECTED — Olas governance subset clears the pre-acquisition gates;
authorization has not been granted.**

## Decision

Select the `FxGovernorTunnel` and `OptimismMessenger` assets from the live Olas
(Autonolas) Immunefi program. Pin the official governance source to tag
`v1.2.5`, tag object `ead748e7f20a1b92bfaabebe7558549be401ceef`, peeled
commit
[`8ce095fec0efd935af39a89b8ae9c90e6581d1e4`](https://github.com/valory-xyz/autonolas-governance/commit/8ce095fec0efd935af39a89b8ae9c90e6581d1e4).

The program lists both deployed assets and maps its governance contracts to
`v1.2.5`. The tag is not a GitHub Release and its message says that the tag was
moved to `main` HEAD on 2026-07-07. The immutable tag object and peeled commit,
not the tag name alone, are therefore the approved source identity.
([program resources](https://immunefi.com/bug-bounty/autonolas/resources/),
[tag object](https://api.github.com/repos/valory-xyz/autonolas-governance/git/tags/ead748e7f20a1b92bfaabebe7558549be401ceef))

This is a deliberately narrow trial: two reportable contracts plus two
compiler-only dependencies. It is still independent from OpenZeppelin
Confidential Contracts and Silo Finance, and it exercises cross-chain message,
external-call, and privileged-action analysis without changing detectors or
compiler policy first. Its size limits what the result can say about broad
generalization; the evaluation must record that limitation.

## Candidate comparison

Every shortlisted program was current on 2026-08-13 and provided a private
reporting channel. A candidate fails if official records do not map the selected
deployed assets to an immutable source revision, if its compiler is unsupported,
or if safe isolated compilation needs an unresolved dependency graph.

| Program | Deployed-source evidence | Compiler and closure | Verdict |
| --- | --- | --- | --- |
| **Olas (Autonolas)** | The live Immunefi scope lists deployed `FxGovernorTunnel` and `OptimismMessenger` assets. The resource page maps governance `contracts/` to `v1.2.5`; the tag object peels to immutable commit `8ce095f…`. ([scope](https://immunefi.com/bug-bounty/autonolas/scope/), [resources](https://immunefi.com/bug-bounty/autonolas/resources/), [tag object](https://api.github.com/repos/valory-xyz/autonolas-governance/git/tags/ead748e7f20a1b92bfaabebe7558549be401ceef)) | The pinned configuration uses Solidity `0.8.30`, optimizer 200, and Prague. The selected closure has four internal files and no external Solidity imports. Solidity 0.8.30 and Prague are supported. ([configuration](https://github.com/valory-xyz/autonolas-governance/blob/8ce095fec0efd935af39a89b8ae9c90e6581d1e4/hardhat.config.js), [local compatibility policy](../COMPATIBILITY.md)) | **Selected.** Exact but small independent trial. Pin and recheck the commit because the tag name has moved before. |
| **Uniswap V3 core** | Strong official mapping: the current Cantina program covers V3 core, and Uniswap's deployment record maps the final addresses to `@uniswap/v3-core@1.0.0`, peeled commit `e3589b…`. ([program](https://cantina.xyz/bounties/f9df94db-c7b1-434b-bb06-d1360abdd1be), [deployment record](https://developers.uniswap.org/docs/protocols/v3/deployments/v3-ethereum-deployments)) | The exact production closure uses Solidity `0.7.6`. Contract Holes supports compiler-backed analysis only for `>=0.8.20,<0.8.37`. Source-only fallback would not satisfy this compiler-enabled trial. | **Rejected.** Mapping passes, compiler compatibility fails. Expanding compatibility first would contaminate the evaluation. |
| **0x Settler** | Official program resources point to mutable `master`; no official record maps the selected deployed assets to one immutable revision. ([resources](https://immunefi.com/bug-bounty/0x/resources/)) | Current source has external Solidity dependencies that cannot be frozen against a deployed revision before the mapping gate passes. | **Rejected.** Mutable source identity. |
| **Strata** | Official deployment documentation lists addresses and a repository, but the repository has no release mapping. The program also records a repository fix that was not deployed. ([deployments](https://docs.strata.markets/technical-documentation/contracts-details), [program information](https://immunefi.com/bug-bounty/strata/information/)) | npm and Git-submodule closure cannot be frozen until an exact deployed revision exists. | **Rejected.** Repository head is not a deployment identity. |
| **Balancer** | The program lists deployed V2/V3 assets and source repositories but does not map the selected deployments to one immutable release or commit. ([scope](https://immunefi.com/bug-bounty/balancer/scope/), [resources](https://immunefi.com/bug-bounty/balancer/resources/)) | Multi-package V2/V3 dependency graph is too broad to resolve before the mapping gate passes. | **Rejected for this trial.** Mapping and closure remain unresolved. |

Gearbox, Spark, and Wormhole NTT were screened and rejected before the final
shortlist. Their official records did not provide both a bounded supported
closure and an exact selected-deployment-to-revision mapping. Spark explicitly
warns that repository source can differ from deployed code; Wormhole's NTT
releases do not identify one release for integrator deployments.
([Gearbox resources](https://immunefi.com/bug-bounty/gearbox/resources/),
[Spark resources](https://immunefi.com/bug-bounty/sparklend/resources/),
[Wormhole resources](https://immunefi.com/bug-bounty/wormhole/resources/))

## Exact deployed-source mapping

The selected mapping is based on the current official program records:

1. The Olas scope lists `FxGovernorTunnel` at Polygon
   `0x9338b5153AE39BB89f50468E608eD9d764B755fD` and `OptimismMessenger` at
   Optimism `0x87c511c8aE3fAF0063b3F3CF9C6ab96c4AA5C60c`, Base
   `0xE49CB081e8d96920C38aA7AB90cb0294ab4Bc8EA`, Celo
   `0xC14E191A64a7FB0e5790a8a0B9a58683dFFce04d`, and Mode
   `0x9338b5153AE39BB89f50468E608eD9d764B755fD`.
2. The program resource page maps the governance contracts to the official
   `valory-xyz/autonolas-governance` `v1.2.5` source.
3. The `v1.2.5` tag object
   `ead748e7f20a1b92bfaabebe7558549be401ceef` peels to immutable commit
   `8ce095fec0efd935af39a89b8ae9c90e6581d1e4`.
4. Acquisition must address the peeled commit directly and recheck all three
   identities because the tag message records a prior tag move.

| Selected asset | Reportable source path | Immutable source evidence |
| --- | --- | --- |
| `FxGovernorTunnel`: Polygon `0x9338…55fD` | [`contracts/bridges/FxGovernorTunnel.sol`](https://github.com/valory-xyz/autonolas-governance/blob/8ce095fec0efd935af39a89b8ae9c90e6581d1e4/contracts/bridges/FxGovernorTunnel.sol) | Current scope lists the deployed asset; current resources map governance contracts to `v1.2.5`; the recorded tag object peels to `8ce095f…`. |
| `OptimismMessenger`: Optimism `0x87c5…C60c`, Base `0xE49C…c8EA`, Celo `0xC14E…e04d`, Mode `0x9338…55fD` | [`contracts/bridges/OptimismMessenger.sol`](https://github.com/valory-xyz/autonolas-governance/blob/8ce095fec0efd935af39a89b8ae9c90e6581d1e4/contracts/bridges/OptimismMessenger.sol) | Same program-to-tag-to-commit chain. |

**Mapping verdict: PASS for this exact two-contract subset.** This is an
official program source mapping, not a bytecode-reproduction claim. The public
records do not prove the historical compiler identity for each deployed
address. That limitation does not change which source the program places in
scope, but it must remain explicit in the evaluation.

No other Olas contract, address, repository, release, tag, or bounty asset is
selected.

## Exact proposed compiler manifest

Official source and revision:

- repository: `https://github.com/valory-xyz/autonolas-governance.git`;
- tag: `v1.2.5`;
- tag object: `ead748e7f20a1b92bfaabebe7558549be401ceef`;
- peeled source commit: `8ce095fec0efd935af39a89b8ae9c90e6581d1e4`;
- isolated compiler: Solidity `0.8.30`;
- optimizer: enabled, 200 runs;
- EVM target: Prague.

Exact positive reportable paths:

```text
contracts/bridges/FxGovernorTunnel.sol
contracts/bridges/OptimismMessenger.sol
```

Exact compiler-only paths:

```text
contracts/bridges/BridgeMessenger.sol
contracts/interfaces/IBridgeErrors.sol
```

The four-file graph uses only relative internal imports. Do not install package
dependencies or run target build, test, deployment, package, or audit commands.
Before acquisition, recheck the pinned configuration and the full four-file
import closure. Stop if another Solidity file or package is required.

## Impacts, known issues, and restrictions

The selected contracts process cross-chain governance messages and privileged
calls. They give the scanner useful overlap with external-interaction,
user-controlled call-target, and authorization rules (`SOL005`, `SOL008`, and
`SOL009`). Rule overlap is an evaluation reason, not evidence of a bug.

The program says its updated scope was reviewed in the Code4rena 2026-01 audit
and that every issue already recorded in governance audits, documentation,
tests, contract comments, or the living governance vulnerability list is known
and ineligible. Review every candidate against those exact records and the
program's current impact and general exclusions before classification.
([program audits and known issues](https://immunefi.com/bug-bounty/autonolas/information/),
[governance audits](https://github.com/valory-xyz/autonolas-governance/tree/8ce095fec0efd935af39a89b8ae9c90e6581d1e4/audits),
[governance documentation](https://github.com/valory-xyz/autonolas-governance/tree/8ce095fec0efd935af39a89b8ae9c90e6581d1e4/docs),
[scope and exclusions](https://immunefi.com/bug-bounty/autonolas/scope/))

The program requires a code PoC for a reward and prohibits unauthorized
live-network testing. This trial permits private offline source analysis only;
it does not authorize a PoC.

Do not test a deployment, exploit a suspected issue, access data, contact the
target, or disclose anything. A proof or report requires a later decision and
separate authorization.

## Proposed one-time authorization

This text is a proposal. It records no approval until the operator supplies it
explicitly:

> I approve one-time network acquisition of only the official
> `valory-xyz/autonolas-governance` repository at tag object
> `ead748e7f20a1b92bfaabebe7558549be401ceef`, peeled commit
> `8ce095fec0efd935af39a89b8ae9c90e6581d1e4`, and, only if not already
> installed, the official Solidity `0.8.30` compiler with its published
> checksum recorded. I approve local, private, isolated, offline
> compiler-enabled analysis of only the two positive reportable paths and two
> compiler-only paths recorded in
> `docs/research/PILOT_008_TARGET_SELECTION.md`. Keep the source under a new
> private `../targets/` directory and scan evidence under new private
> `../bounty-workspaces/` directories. After the one-time acquisition, both
> scans must remain offline. No other target source, dependency, repository,
> revision, address, contract, or bounty asset is approved. Do not run target
> build, test, deployment, package, or audit commands. No RPC, fork, chain
> interaction, transaction, proof, report, export, disclosure, submission,
> platform write, target contact, or detector tuning before the first scan is
> frozen is approved.

Immediately before acquisition, recheck the Immunefi program, source resource,
tag object, peeled commit, compiler configuration, and complete four-file import
closure. Stop if any identity, scope, rule, path, or dependency differs.

This research used public official records only. It did not create a target
checkout, run a target scan, use RPC, contact a target, write to a platform, or
make a vulnerability claim.
