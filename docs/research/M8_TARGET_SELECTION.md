# M8 Target Selection

Reviewed: 2026-08-10

## Decision

Use **OpenZeppelin Confidential Contracts v0.4.0** for the first external M8
trial. Pin the trial to commit
[`7ac7cee5fec408dc81b31121f90417dfd87f3d13`](https://github.com/OpenZeppelin/openzeppelin-confidential-contracts/tree/7ac7cee5fec408dc81b31121f90417dfd87f3d13).

This is the cleanest authorization boundary found. The live OpenZeppelin bounty
names that release and commit as the only in-scope Confidential Contracts
version, and excludes mocks and examples. Its resource page limits contract
scope to `contracts/`, excluding `contracts/mocks` and `contracts/vendor`.
([scope](https://immunefi.com/bug-bounty/openzeppelin/scope/),
[resources](https://immunefi.com/bug-bounty/openzeppelin/resources/))

The official release resolves to the same commit. Its notes identify ERC-20
wrappers, routing, access management, and upgradeable OpenZeppelin dependencies.
Those areas overlap most directly with `SOL005`, `SOL008`, `SOL009`, `SOL011`,
and `SOL012`; this is a reason to investigate, not evidence of a vulnerability.
([v0.4.0 release](https://github.com/OpenZeppelin/openzeppelin-confidential-contracts/releases/tag/v0.4.0))

The published maximum reward is USD 25,000. A valid report still needs a PoC,
and payout requires KYC and an invoice; running the scanner creates no claim to
a reward. ([program rules](https://immunefi.com/bug-bounty/openzeppelin/information/))

The repository is an experimental Solidity library for the Zama fhEVM and warns
that confidential functions can have failure semantics unlike ordinary
contracts. That makes compiler compatibility and false-positive triage part of
the trial result instead of something to hide.
([official repository](https://github.com/OpenZeppelin/openzeppelin-confidential-contracts/tree/7ac7cee5fec408dc81b31121f90417dfd87f3d13))

## Candidate comparison

| Program | Authorization and source identity | Fit for the first trial | Why it ranks lower |
| --- | --- | --- | --- |
| **OpenZeppelin Confidential Contracts v0.4.0** | The program is live, provides a private submission link, and pins one in-scope release to one full commit. | Bounded, immutable Solidity library boundary; source analysis needs no chain, RPC, or user funds; useful detector and compatibility overlap. | **Selected.** The main risk is FHE-specific behavior, which requires careful human triage. |
| [SPOT](https://immunefi.com/bug-bounty/spot/information/) | The live scope lists four smart-contract addresses: SPOT, Router, Bond Factory, and Bond Issuer. Testing public chains is prohibited and local forks are directed. ([scope](https://immunefi.com/bug-bounty/spot/scope/)) | Only four deployed assets and good overlap with token, authorization, call, and randomness checks. | The program does not expose an immutable source revision on its resource page, so code-to-address mapping must be established first. The page was last updated in 2024, and its v1.0 audits plus MEV and insolvency issues must be removed from candidates. ([resources](https://immunefi.com/bug-bounty/spot/resources/)) |
| [0x Settler](https://immunefi.com/bug-bounty/0x/information/) | The live program names 0x Settler in scope and links the official [`src` tree](https://github.com/0xProject/0x-settler/tree/master/src), deployed addresses, and private submission channel. ([scope](https://immunefi.com/bug-bounty/0x/scope/), [resources](https://immunefi.com/bug-bounty/0x/resources/)) | Strong overlap with external-call targets, signatures, token movement, proxies, and swap bounds. | The bounty points to mutable `master`, covers many chains and addresses, and the source tree contains specialized settlement, bridge, proxy, and multicall code. Pinning and deployed-version mapping are more work than the first trial needs. |
| [Silo Finance v2/v3](https://immunefi.com/bug-bounty/silofinance-v2/information/) | The live scope names Solidity files such as `Silo.sol`, `SiloFactory.sol`, `SiloRouterV2.sol`, and vault contracts; the official v3 repository links back to the bounty. ([scope](https://immunefi.com/bug-bounty/silofinance-v2/scope/), [repository](https://github.com/silo-finance/silo-contracts-v3)) | Strong overlap with reentrancy, token assumptions, authorization, oracle, hooks, and vault behavior. Official instructions support local-fork testing. | There are 34 assets, the repository default is mutable `develop`, deployed-version mapping is separate, and all published audits and known issues must be reconciled. This is a better later protocol trial. |

## Frozen trial boundary

Record these values in the bounty profile before scanning:

- program: OpenZeppelin on Immunefi;
- rules: [information](https://immunefi.com/bug-bounty/openzeppelin/information/),
  [scope](https://immunefi.com/bug-bounty/openzeppelin/scope/), and
  [resources](https://immunefi.com/bug-bounty/openzeppelin/resources/);
- rules reviewed: 2026-08-10;
- source: `OpenZeppelin/openzeppelin-confidential-contracts`;
- revision: `7ac7cee5fec408dc81b31121f90417dfd87f3d13`;
- include only the 22 Solidity files listed below;
- analysis: released Contract Holes source-only workflow in a private workspace,
  with the network disabled after the pinned source is acquired;
- proof: local-only and only after a human confirms an in-scope impact;
- submission: manual and private through Immunefi only.

Authorization update on 2026-08-12: the operator later authorized a local,
private, isolated, offline diagnostic proof for `PILOT-006` before the final
candidate decision. This extends the proof timing only for the exact pinned
trial. It does not confirm impact or authorize RPC, chain activity, target
contact, report export, disclosure, or submission.

The bounty profile has positive paths, not exclusion patterns. Do not use the
whole `contracts` directory because that would also admit the out-of-scope
`contracts/mocks` subtree. Pin these exact paths:

```text
contracts/finance/BatcherConfidential.sol
contracts/finance/ERC7821WithExecutor.sol
contracts/finance/VestingWalletCliffConfidential.sol
contracts/finance/VestingWalletConfidential.sol
contracts/finance/VestingWalletConfidentialFactory.sol
contracts/governance/utils/VotesConfidential.sol
contracts/interfaces/IERC7984.sol
contracts/interfaces/IERC7984ERC20Wrapper.sol
contracts/interfaces/IERC7984Receiver.sol
contracts/interfaces/IERC7984Rwa.sol
contracts/token/ERC7984/ERC7984.sol
contracts/token/ERC7984/extensions/ERC7984ERC20Wrapper.sol
contracts/token/ERC7984/extensions/ERC7984Freezable.sol
contracts/token/ERC7984/extensions/ERC7984ObserverAccess.sol
contracts/token/ERC7984/extensions/ERC7984Omnibus.sol
contracts/token/ERC7984/extensions/ERC7984Restricted.sol
contracts/token/ERC7984/extensions/ERC7984Rwa.sol
contracts/token/ERC7984/extensions/ERC7984Votes.sol
contracts/token/ERC7984/utils/ERC7984Utils.sol
contracts/utils/FHESafeMath.sol
contracts/utils/HandleAccessManager.sol
contracts/utils/structs/CheckpointsConfidential.sol
```

These paths are present at the pinned commit. Mocks, vendor files, examples,
tests, scripts, and every path outside this list remain out of the trial. Start
source-only: compiler dependencies must not be added to the bounty scope merely
to make a build pass. Record that limitation during the trial if it blocks
compiler-backed rules.

The program covers impacts including theft, access-control bypass, governance
manipulation, freezing, denial of service, griefing, and unbounded gas use. It
rejects best-practice-only reports and previously disclosed unfixed issues.
([scope](https://immunefi.com/bug-bounty/openzeppelin/scope/),
[program rules](https://immunefi.com/bug-bounty/openzeppelin/information/))

## Safety and disclosure rules

- Do not test deployed code on mainnet or public testnet. The program directs
  testing to local forks and also prohibits testing with pricing oracles and
  third-party contracts.
- Do not execute denial of service, generate traffic against services, touch
  user funds, or publish an unpatched vulnerability.
- A PoC is required for every severity. A scanner finding alone is not a PoC or
  a valid report.
- Recheck all three bounty pages immediately before source acquisition and
  again before any submission. Stop if the release, commit, scope, or rules
  changed.
- Keep every candidate private. OpenZeppelin's repository security policy
  directs reports to Immunefi or `security@openzeppelin.com`.

Sources: [OpenZeppelin program rules](https://immunefi.com/bug-bounty/openzeppelin/information/)
and [repository security policy](https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-confidential-contracts/7ac7cee5fec408dc81b31121f90417dfd87f3d13/SECURITY.md).

The reviewed pages provide scoped program authorization, not a general legal
safe-harbor promise. Stay within the exact published scope and restrictions.
This selection performed no clone, scan, contract call, transaction, or target
interaction.
