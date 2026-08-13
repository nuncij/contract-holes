# Historical bounty evaluation

M7's historical gate asks a narrow question: does Contract Holes produce useful
investigation evidence on already-public vulnerabilities that overlap its
documented rule classes? It does not measure exploit automation, completeness,
bounty eligibility, or expected payout.

## Reproduce the frozen result

Foundry and solc `0.8.25` must already be installed because the command is
offline by default:

```bash
holes bounty history tests/fixtures/bounty_history/manifest.json \
  > bounty-history.json
```

Exit `0` means every frozen product-claim threshold passed, exit `1` is an
explicit no-go result, and exit `2` means the manifest, compiler, or evaluation
failed. `--allow-downloads` only permits Foundry to obtain the pinned compiler;
it does not fetch historical sources or contact any project.

The checked raw result is
[`evaluation/bounty-history-1.0.json`](../evaluation/bounty-history-1.0.json).
The evaluator verifies every fixture and compiler-config SHA-256 before scanning
and emits a stable `labels_sha256` and `result_sha256`.

## Frozen corpus

The corpus has ten cases from ten independent projects. Labels are split into
five calibration and five holdout cases. The source and disclosure references
below are provenance metadata only; evaluation uses small MIT-licensed
reductions written for this repository, with no upstream source copied.

| Split | Project/case | Frozen status | Useful evidence boundary | Public reference |
| --- | --- | --- | --- | --- |
| Calibration | Parity library, 2017 | Supported | unguarded owner initialization and `selfdestruct`; deployment impact remains manual | [Parity postmortem](https://medium.com/paritytech/a-postmortem-on-the-parity-multi-sig-library-self-destruct-63daca3a4cf7) |
| Calibration | C.R.E.A.M. AMP, 2021 | Supported | transfer-hook interaction before debt accounting; cross-market impact remains manual | [C.R.E.A.M. postmortem](https://medium.com/cream-finance/c-r-e-a-m-finance-post-mortem-amp-exploit-6ceb20a630c5) |
| Calibration | Enzyme Idle pricing, 2021 | Out of model | protocol-specific mutable share-supply economics | [Immunefi bugfix review](https://immunefi.com/blog/bug-fix-reviews/enzyme-finance-price-oracle-manipulation-bugfix-review/) |
| Calibration | Nomad Replica, 2022 | Out of model | Merkle-root authentication and deployment arguments | [Nomad root-cause analysis](https://medium.com/nomad-xyz-blog/nomad-bridge-hack-root-cause-analysis-875ad2e5aacd) |
| Calibration | Belt shares, 2021 | Out of model | cross-strategy asset/share accounting | [Immunefi bugfix review](https://immunefi.com/blog/bug-fix-reviews/belt-finance-logic-error-bugfix-review-largest-ever-bounty-payout/) |
| Holdout | Wormhole implementation, 2022 | Supported | unguarded initialization, privileged write, controlled delegatecall and proxy-storage evidence; deployed state remains manual | [Immunefi bugfix review](https://immunefi.com/blog/bug-fix-reviews/wormhole-uninitialized-proxy-bugfix-review/) |
| Holdout | Harvest implementations, 2021 | Supported | unguarded initialization and hard-worker delegatecall/storage evidence; chain history remains manual | [Immunefi bugfix review](https://immunefi.com/blog/bug-fix-reviews/harvest-finance-uninitialized-proxies-bugfix-review-200k-bounty/) |
| Holdout | Aurora inflation, 2022 | Supported signal only | caller-controlled `delegatecall` boundary; no model of Aurora Engine balance/precompile semantics | [Aurora disclosure](https://aurora.dev/blog/aurora-mitigates-its-inflation-vulnerability) |
| Holdout | Beanstalk governance, 2022 | Out of model | flash-loan voting economics, proposal intent, and temporal snapshots | [Beanstalk disclosure](https://bean.money/blog/beanstalk-governance-exploit) |
| Holdout | Euler donation, 2023 | Out of model | protocol-specific health, reserve, exchange-rate, and liquidation invariants | [Euler historical account](https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery) |

The manifest also pins a commit, transaction, deployed address, or fixed
repository reference for each original source relationship. Third-party code is
not redistributed when permission is unclear or the original source was not
verified; the provenance record says `metadata-only` explicitly.

## Versioned result

The `m7-history-1` result is:

| Metric | Result | Gate |
| --- | ---: | ---: |
| Cases / projects | 10 / 10 | at least 10 / 5 |
| Supported cases with useful evidence | 5 | at least 3 |
| Candidate precision | 0.933333 | at least 0.8 |
| Supported-class recall | 1.0 | at least 0.8 |
| Evidence completeness | 1.0 | at least 0.9 |
| Investigation candidates | 15 | reported, not optimized away |
| Rejected candidates | 1 | reported, not hidden |
| Holdout precision / recall | 1.0 / 1.0 | reported separately |

The single rejected candidate is a generic reentrancy observation on the Enzyme
reduction. It is deliberately retained in raw output rather than relabelled as
the disclosed price-integration root cause. A second out-of-model `SOL005`
candidate was removed on 2026-08-13 when `PRECISION-002` stopped treating view
interactions as reentrancy paths (`totalSupply()` is a read-only `view` call);
the versioned raw result was regenerated through the public CLI and no fixture,
label, threshold, or split changed.

The gate decision is `go` only for this wording: Contract Holes produced useful
investigation evidence for at least three independent historical cases in
supported classes. It does not say the tool rediscovered complete exploits, can
confirm a vulnerability without a reviewer, replaces an audit, or predicts a
bounty payout. Changing a fixture, label, threshold, split, or source identity
creates a new corpus version and requires a newly reviewed raw result.

