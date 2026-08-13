# PILOT-009 Target Selection

Reviewed: 2026-08-13

Status: **SELECTED — EulerSwap v2 Ethereum subset.** This record is public
research only. No target source archive, RPC endpoint, fork, deployment, or
target interaction was used.

Independent cross-check: **PASS.** The reviewer first questioned whether the
live program required a mutable branch. A second check found no such rule. The
program excludes development-branch issues, while Euler's first-party
verification manifest maps the selected deployed bytecode to an immutable
release commit.

## Decision

Select the five Ethereum EulerSwap v2 component contracts listed in Euler's
official verification report:

- `eulerSwapV2Factory` — `0xD05213331221fAB8a3C387F2affBb605Bb04DF5F`;
- `eulerSwapV2Implementation` — `0x8B0E044E364F2cE913799d53b300e15A6974DC97`;
- `eulerSwapV2Periphery` — `0xD3a349EE0A21eA0A7E9513ac236ae614b5FD513E`;
- `eulerSwapV2ProtocolFeeConfig` — `0x5171Aed04Fa9551DB484F07c853F252Bc6F53b63`;
- `eulerSwapV2Registry` — `0x5FcCB84363F020c0cADE052C9c654aABF932814A`.

The immutable source identity is the full EulerSwap commit
[`81cf6dc988468fd56f690e6bc0e338a5be02d034`](https://github.com/euler-xyz/euler-swap/tree/81cf6dc988468fd56f690e6bc0e338a5be02d034),
identified by Euler's official bytecode verification manifest and Ethereum
report. The report states that the deployed v2 release is tag `eulerswap-2.0`
and that all five selected contracts are bytecode-proven against this commit:
[`verify/1.md`](https://github.com/euler-xyz/euler-interfaces/blob/d938bc264d6e1cee68a559798044d43ade8ac95e/verify/1.md#component-euler-swap-v2).
The evidence record is itself pinned at `euler-interfaces` commit
`d938bc264d6e1cee68a559798044d43ade8ac95e`; it is not a mutable-branch
assumption.

The selected source paths are:

```text
src/EulerSwapFactory.sol
src/EulerSwap.sol
src/EulerSwapPeriphery.sol
src/EulerSwapProtocolFeeConfig.sol
src/EulerSwapRegistry.sol
```

This is a source-to-scope mapping, not a claim that this research has
reproduced deployed bytecode. The official verification record is the mapping
evidence required before acquisition.

## Candidate comparison

The review used current official bounty/program records and first-party source
metadata only. A candidate fails if its current rules do not map selected
deployed assets to one immutable source revision, if the compiler is outside
the supported policy, or if the exact dependency closure cannot be pinned.

| Program | Public evidence | Compiler / closure | Verdict |
| --- | --- | --- | --- |
| **Euler Euler-Bounty — EulerSwap v2** | The live Cantina program requires private reporting, identifies EulerSwap v2 as in scope, and points to the EulerSwap repository. Euler's first-party verification report maps the five selected Ethereum addresses to the same immutable commit `81cf6dc9…`. ([program](https://cantina.xyz/bounties/4d285eee-602e-440a-845e-25e155cec26a), [pinned verification report](https://github.com/euler-xyz/euler-interfaces/blob/d938bc264d6e1cee68a559798044d43ade8ac95e/verify/1.md#component-euler-swap-v2), [addresses](https://docs.euler.finance/developers/contract-addresses/)) | The pinned [`foundry.toml`](https://github.com/euler-xyz/euler-swap/blob/81cf6dc988468fd56f690e6bc0e338a5be02d034/foundry.toml) specifies Solidity `0.8.27`, optimizer enabled with 2,500 runs. The commit has five directly pinned submodules ([tree](https://github.com/euler-xyz/euler-swap/tree/81cf6dc988468fd56f690e6bc0e338a5be02d034/lib)); nested submodules are also pinned: EVK `83481a4e…` ([tree](https://github.com/euler-xyz/euler-vault-kit/tree/83481a4/lib)), Uniswap v4 periphery `9628c36b…` ([tree](https://github.com/uniswap/v4-periphery/tree/9628c36/lib)), and v4 core `b619b671…` ([tree](https://github.com/uniswap/v4-core/tree/b619b67/lib)). This is a finite candidate graph to enumerate and hash offline; no package resolution or mutable branch appears necessary. | **Selected.** Exact deployed-source mapping, supported compiler, and a bounded pinned dependency graph to reproduce after acquisition. |
| **PancakeSwap Infinity** | The current Cantina bounty lists deployed addresses and three mutable GitHub repositories, but does not provide a commit or release identity for those deployed assets. ([program scope](https://cantina.xyz/bounties/ea552420-8bd6-4119-815d-3d5203d0377a), [core repository](https://github.com/pancakeswap/infinity-core), [core releases](https://github.com/pancakeswap/infinity-core/releases)) | The repository's public deployment instructions point to script configuration and do not establish a deployment-to-immutable-revision mapping. The exact closure therefore cannot be frozen before source acquisition. | **Rejected.** Scope has addresses, but no official immutable deployed-source revision. |
| **Wormhole Native Token Transfers** | The current Wormhole Immunefi program is live and says only the listed repository and tagged `v1.x.x`/`v2.x.x` releases are in scope. ([program scope](https://immunefi.com/bug-bounty/wormhole/scope/), [NTT releases](https://github.com/wormhole-foundation/native-token-transfers/releases)) | The release list contains several versions, but the program record does not identify which single release corresponds to the selected deployed assets. The broader Wormhole scope also covers multiple chains and non-Solidity components. | **Rejected.** Tagged releases are allowed, but no exact deployed-asset-to-release mapping is evidenced. |

## Exact deployed-source mapping

The official Euler verification report gives a direct address-to-source mapping
for each selected asset. It states that verification proves deployed runtime
bytecode equivalent to a build of the exact recorded source commit, and lists:

| Selected deployed asset | Reportable source path | Immutable identity evidence |
| --- | --- | --- |
| `eulerSwapV2Factory` at `0xD052…DF5F` | `src/EulerSwapFactory.sol` | [`verify/1.md` row](https://github.com/euler-xyz/euler-interfaces/blob/d938bc264d6e1cee68a559798044d43ade8ac95e/verify/1.md#component-euler-swap-v2), [`81cf6dc9…` tree](https://github.com/euler-xyz/euler-swap/tree/81cf6dc988468fd56f690e6bc0e338a5be02d034/src) |
| `eulerSwapV2Implementation` at `0x8B0E…4DC97` | `src/EulerSwap.sol` | Same official row and commit pin |
| `eulerSwapV2Periphery` at `0xD3a3…D513E` | `src/EulerSwapPeriphery.sol` | Same official row and commit pin |
| `eulerSwapV2ProtocolFeeConfig` at `0x5171…3b63` | `src/EulerSwapProtocolFeeConfig.sol` | Same official row and commit pin |
| `eulerSwapV2Registry` at `0x5FcC…2814` | `src/EulerSwapRegistry.sol` | Same official row and commit pin |

**Mapping verdict: PASS.** The five selected deployed assets are all mapped by
the target's first-party verification metadata to the same immutable Git
revision before any source acquisition. No filename matching or repository
head assumption is being used.

## Compiler and dependency gate

The pinned source declares `pragma solidity ^0.8.27` in the selected core
contract ([`EulerSwap.sol`](https://github.com/euler-xyz/euler-swap/blob/81cf6dc988468fd56f690e6bc0e338a5be02d034/src/EulerSwap.sol)) and pins
Solidity `0.8.27`, optimizer enabled, 2,500 runs in
[`foundry.toml`](https://github.com/euler-xyz/euler-swap/blob/81cf6dc988468fd56f690e6bc0e338a5be02d034/foundry.toml).
This satisfies the project's supported compiler range
([COMPATIBILITY.md](../COMPATIBILITY.md)).

The public Git tree records this candidate dependency graph as immutable
gitlinks. The graph was re-checked against the pinned primary sources on
2026-08-13 (GitHub trees and `.gitmodules` at each pinned revision); every
listed gitlink below resolved to the recorded commit. The graph is a bounded
candidate set to enumerate and hash from the actual checkout after acquisition,
not a reproduced import closure.

```text
euler-swap@81cf6dc988468fd56f690e6bc0e338a5be02d034
  lib/ethereum-vault-connector@4538f07342d116c6ade2af6d2aeac5398bfb578d
  lib/euler-vault-kit@83481a4e95d4d2ee50c95843841be952bbf3f48d
    lib/ethereum-vault-connector@084b32284ba643921f8d21bff3ddaf0c4e08d754
    lib/forge-std@b6a506db2262cad5ff982a87789ee6d1558ec861
    lib/openzeppelin-contracts@e682c7e5b5b347662868b9c8378a694626406c01
    lib/permit2@cc56ad0f3439c502c246fc5cfcc3db92bb8b7219
  lib/forge-std@1eea5bae12ae557d589f9f0f0edae2faa47cb262
  lib/openzeppelin-contracts@acd4ff74de833399287ed6b31b4debf6b2b35527
  lib/v4-periphery@9628c36b4f5083d19606e63224e4041fe748edae
    lib/permit2@cc56ad0f3439c502c246fc5cfcc3db92bb8b7219
    lib/v4-core@b619b6718e31aa5b4fa0286520c455ceb950276d
      lib/forge-std@1de6eecf821de7fe2c908cc48d3ab3dced20717f
      lib/openzeppelin-contracts@dbb6104ce834628e473d2173bbc9d47f81a9eec3
      lib/solmate@4b47a19038b798b4a33d9749d25e570443520647
```

These are expected to be compiler-only dependencies unless an imported path is
part of the selected deployed component. The exact reportable and compiler-only
import closures have not been reproduced yet. They must be enumerated from the
pinned checkout after acquisition and must match these public gitlink
identities. Stop if the checkout requires a mutable package, an unpinned source,
or an additional dependency outside this recorded finite graph. OpenZeppelin
is only present as a pinned compiler dependency here; it is not the selected
target or the OpenZeppelin trial.

## Rule overlap, known issues, and restrictions

The selected subset is useful for several existing Contract Holes rules without
requiring live state:

- `EulerSwap.swap` performs optimistic token withdrawals, invokes the caller's
  `eulerSwapCall` callback, and then deposits observed balances before checking
  the invariant. This gives source-level interaction/effect and token balance
  flow overlap for `SOL005` and `SOL012` ([source](https://github.com/euler-xyz/euler-swap/blob/81cf6dc988468fd56f690e6bc0e338a5be02d034/src/EulerSwap.sol)).
- The implementation delegates management calls to an immutable
  `managementImpl`, giving `SOL008`/`SOL009` external-target and privileged
  state-change overlap ([source](https://github.com/euler-xyz/euler-swap/blob/81cf6dc988468fd56f690e6bc0e338a5be02d034/src/EulerSwap.sol)).
- The factory, registry, fee configuration, and periphery add cross-contract
  authorization, callback, and fee/amount paths for compiler-backed analysis;
  this is evaluation overlap, not evidence of a vulnerability.

Euler's program requires private reporting and excludes issues already covered
by documentation, known issues, or prior security reviews. The official report
also records that the deployed v2 release has a substantive post-audit delta
and no follow-up external review of that delta. These facts constrain later
private review; they do not authorize a proof, report, disclosure, or contact.
([program rules](https://cantina.xyz/bounties/4d285eee-602e-440a-845e-25e155cec26a),
[official verification/audit notes](https://github.com/euler-xyz/euler-interfaces/blob/d938bc264d6e1cee68a559798044d43ade8ac95e/verify/1.md#component-euler-swap-v2))

No RPC, fork, chain interaction, target contact, bounty-platform write, proof,
report, export, or disclosure is authorized by this selection record.

## Selection gate

**PASS for pre-acquisition selection.** Before any source download, the public
records establish the current program, private channel, explicit smart-contract
scope, exact deployed addresses, one immutable source commit, supported
compiler, and an apparently finite recursively pinned dependency graph.
Acquisition and exact closure hashing remain separate later gates. If any
identity or closure differs from this record, stop and mark PILOT-009
unsatisfied rather than weakening the mapping gate.
