# PILOT-007 Target Selection

Reviewed: 2026-08-13
Status: **UNSATISFIED — source-to-scope gate failed; Silo retained as a
research-only corpus.**

## Source-to-scope verdict

The 2026-08-13 completion repair determined that the selected Git tag does not
exactly correspond to the deployed in-scope assets. The Immunefi scope maps the
in-scope contracts to deployed addresses on Sonic (Silo Factory
`0x4e9dE3a64c911A37f7EB2fCb06D1e68c3cBe9203`, Silo Implementation
`0x435Ab368F5fCCcc71554f4A8ac5F5b922bC4Dc06`, and others). The repository's own
`DeployedSiloVersions.md` at the pinned commit documents that these addresses
correspond to Silo version `3.5.0` (id `101`-`current` on Sonic), which
resolves to commit `b1f428f1c3d5fc989974fd8e7b3b84180e05e31f` (release dated
2025-05-15). The trial pinned tag `4.26.0` at commit
`570a668a98a88a6a2b92697e7b9a3b1c6299dce7` (release dated 2026-07-27). Filename
equality between the scope list and the repo is insufficient; the exact
content correspondence to the deployed bytecode is not established and the two
commits differ. Silo is therefore not usable as a bounty-scoped independent
trial and is retained only as a research corpus. A new independent target trial
(`PILOT-008`) is required.

## Decision

The initial selection used **Silo Finance v2/v3** for the second M8+ trial and pinned it to
the Silo V3 monorepository tag `4.26.0`, which resolves to commit
[`570a668a98a88a6a2b92697e7b9a3b1c6299dce7`](https://github.com/silo-finance/silo-contracts-v3/tree/570a668a98a88a6a2b92697e7b9a3b1c6299dce7).

Silo is the program the first-trial review already earmarked for a later
protocol test. It is a different team, codebase, dependency graph, and protocol
model from the OpenZeppelin Confidential Contracts `v0.4.0` fhEVM library used
in M8, which satisfies the independence requirement. It is a lending and vaults
protocol with hooks, routers, oracles, ERC-4626 wrappers, and token flows, so it
directly exercises `SOL005` (reentrancy), `SOL008` (call targets), `SOL009`
(authorization), `SOL011` (proxy/upgrade), `SOL012` (token interaction), and
`SOL013` (oracle/swap) evidence.

## Candidate comparison

| Program | Authorization and source identity | Fit for the second trial | Why it ranks lower |
| --- | --- | --- | --- |
| **Silo Finance v2/v3** | The live program on Immunefi names Silo Lending and Silo Vaults, links the official [`silo-contracts-v3`](https://github.com/silo-finance/silo-contracts-v3) codebase, and lists the in-scope contract files below. The repository publishes immutable tags; the current tag `4.26.0` resolves to commit `570a668a98a88a6a2b92697e7b9a3b1c6299dce7`. | Strong rule overlap across a real lending/vaults stack: hooks and routers (`SOL005`, `SOL008`), roles and allocation control (`SOL009`), proxies (`SOL011`), ERC-4626 and share tokens (`SOL012`), oracles and swap routers (`SOL013`). All in-scope files verified present at the pinned tag. | **Selected.** The program's asset table lists deployed addresses on Sonic in addition to contract file names, so the exact deployed-version correspondence is a review-time limitation rather than a source-identity blocker. The dependency closure uses commit-pinned git submodules. |
| [0x Settler](https://immunefi.com/bug-bounty/0x/information/) | Live program with Immunefi triage and a private submission channel; the smart-contract scope is the [`0x-settler/src`](https://github.com/0xProject/0x-settler/tree/master/src) source tree plus deployed addresses. | Strong overlap with call targets, signatures, token movement, swap bounds, and proxies; Solidity `^0.8.25` is compiler-compatible. | The program scope points to the mutable `master` branch, so its official source lacks an immutable revision in scope. The first-trial review rejected it for the same reason. |
| [Instadapp](https://immunefi.com/bug-bounty/instadapp/information/) | Live program whose scope includes [`fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) (Liquidity, Lending, Vault) excluding the periphery folder. | Fluid is a strong lending/vaults overlap. | The Fluid repository publishes no release tags, so its official source identity is mutable; the scope is defined by an exclusion rather than a positive file list. |
| [Balancer](https://immunefi.com/bug-bounty/balancer/information/) | Live program with a vault/hooks model and strong `SOL005`/`SOL008`/`SOL013` overlap. | Excellent rule overlap for a vault/hooks AMM. | The scope table maps assets to deployed addresses (Instascope) rather than exact repository files at an immutable revision, so code-to-address identity must be established before scanning. |
| [Ethena](https://immunefi.com/bug-bounty/ethena/information/) | Live stablecoin program. | Some overlap with token, authorization, and proxy rules. | The scope is a large set of deployed-address assets verified via Etherscan (Instascope), not an immutable repository revision with exact file scope. |
| [LayerZero](https://immunefi.com/bug-bounty/layerzero/information/) | Live cross-chain program. | Weak fit for a bounded source-only trial. | The scope spans dozens of chains and many deployed assets; the source-to-scope mapping and dependency closure are far larger than this trial needs. |

## Frozen trial boundary

Record these values in the bounty profile before scanning:

- program: Silo Finance v2/v3 on Immunefi;
- rules: [information](https://immunefi.com/bug-bounty/silofinance-v2/information/),
  [scope](https://immunefi.com/bug-bounty/silofinance-v2/scope/), and
  [resources](https://immunefi.com/bug-bounty/silofinance-v2/resources/);
- rules reviewed: 2026-08-13;
- source: `silo-finance/silo-contracts-v3`;
- revision: tag `4.26.0` resolving to `570a668a98a88a6a2b92697e7b9a3b1c6299dce7`;
- analysis: released Contract Holes `1.1.1` plus completed `PRECISION-001`
  repairs, using local, private, isolated, offline compiler analysis;
- proof, report, approval, export, disclosure, and submission: not part of
  `PILOT-007`; each requires separate explicit authorization.

The program lists the following in-scope contract files. Pin exactly these
positive paths (mocks, tests, scripts, deployments, and other assets remain out
of the trial):

```text
silo-core/contracts/Silo.sol
silo-core/contracts/SiloFactory.sol
silo-core/contracts/hooks/SiloHookV1.sol
silo-core/contracts/silo-router/SiloRouterV2.sol
silo-core/contracts/interestRateModel/InterestRateModelV2.sol
silo-core/contracts/utils/ShareDebtToken.sol
silo-core/contracts/utils/ShareProtectedCollateralToken.sol
silo-vaults/contracts/PublicAllocator.sol
silo-vaults/contracts/SiloVault.sol
silo-vaults/contracts/SiloVaultsFactory.sol
```

All ten files were confirmed present at the pinned commit during selection.
The in-scope source uses Solidity `0.8.28`, which is inside the published
supported range `>=0.8.20,<0.8.37`. The Solidity compiler must therefore be
provisioned at version `0.8.28` for the offline analysis.

Dependencies are pinned git submodules recorded in the superproject tree. The
relevant remappings are `openzeppelin5/`, `openzeppelin5-upgradeable/`,
`chainlink/`, `morpho-blue/`, `pyth-sdk-solidity/`,
`@openzeppelin/`, and others under `gitmodules/`. They are treated as
compiler-only dependencies in the bounty profile and can never produce a
reportable finding. The target Foundry configuration, scripts, cargo tooling,
tests, and deployment code are not executed.

## Compiler provisioning

The pinned Silo tag requires Solidity `0.8.28`. The environment already has
`solc` `0.8.25` and `0.8.27`. `0.8.28` is inside the published supported range
and is provisioned locally before the offline scan so that the analysis does
not require a network download during the scan.

## Known issues and audits

The program directs reviewers to read all audit reports before submitting and
treats issues disclosed in the repository `audits` folder as known issues.
(`[audits](https://docs.silo.finance/docs/audits/)`,
`[repository audits](https://github.com/silo-finance/silo-contracts-v3/tree/570a668a98a88a6a2b92697e7b9a3b1c6299dce7/audits)`)
The repository also carries a `KnownIssues.md` at the pinned commit. These are
review-time inputs for candidate triage and are not part of the scan.

## Safety and disclosure rules

- Do not test deployed code on mainnet or public testnet; the program directs
  testing to local forks and prohibits testing with pricing oracles or
  third-party contracts.
- Do not execute denial of service, generate traffic against services, touch
  user funds, or publish an unpatched vulnerability.
- A PoC is required for every severity. A scanner finding alone is not a PoC or
  a valid report.
- Recheck the program pages immediately before source acquisition and stop if
  the release, commit, scope, or rules changed.
- Keep every candidate private. Reporting to the program is a separate manual
  user decision and is not part of this task.

## Independence

Silo is a lending and vaults protocol owned by Silo Finance. It shares no
team, repository, dependency graph, or protocol model with the OpenZeppelin
Confidential Contracts fhEVM library. The source-only identity is pinned to an
immutable repository tag rather than to deployed-address verified source, which
is the cleanest boundary found for a second real-world evaluation.

This selection performed no clone, scan, contract call, transaction, or target
interaction.
