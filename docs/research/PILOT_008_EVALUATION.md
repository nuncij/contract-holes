# PILOT-008 Evaluation

Trial date: 2026-08-13
Target: Olas governance `FxGovernorTunnel` and `OptimismMessenger`
Pinned commit: `8ce095fec0efd935af39a89b8ae9c90e6581d1e4`
Status: **SATISFIED — exact source mapping and reproducible offline scans; no
candidates.**

## Outcome

The trial scanned a new independent target whose current bounty records map the
selected deployed assets to an immutable source commit. Two private workspaces
reproduced byte-identical source manifests, scans, and candidate ledgers with
Solidity `0.8.30`. Both scans processed two reportable files and produced zero
candidates. No candidate review decision was required.

This result proves that the bounded workflow completed on this target. It does
not prove that the contracts are safe, that unknown-bug recall is useful, or
that Contract Holes can earn a bounty.

## Target and source gate

The live Olas Immunefi program listed one selected Polygon deployment and four
selected OP-stack deployments. Its resource page mapped governance contracts to
tag `v1.2.5`. The tag object
`ead748e7f20a1b92bfaabebe7558549be401ceef` peeled to the approved commit above
immediately before acquisition. The checkout is detached, clean, private, and
user-read-only. No submodule was initialized because the four-file compiler
closure uses only internal relative imports.

This is an official program-to-source mapping, not a bytecode-reproduction
claim. The public program records do not prove the historical compiler identity
for every deployed address. The tag name has also moved before, so the immutable
tag object and peeled commit remain the source identity.

See [the selection record](PILOT_008_TARGET_SELECTION.md) for the public mapping,
candidate comparison, paths, addresses, and restrictions.

## Reproducible evidence

| Record | Exact-compiler result |
| --- | --- |
| Scanner | Contract Holes `1.1.1` plus the completed generic repairs |
| Solidity compiler | `0.8.30+commit.73712a01.Linux.g++` |
| Compiler SHA-256 | `f3e987dc6ecebd4bd350c48edcbc320b46cf9e3109bd3fc3d88f1acaf4c428f7` |
| Reportable / compiler-only files | 2 / 2 |
| Profile | `53226e80f049e085272f72e0a918992fe5b748e2a2e976fe229f97f195847299` |
| Source set | `9419726e3bf40d47d7983d6557ead89de937a0db3a8b11ef611d270320b87870` |
| Compiler-dependency set | `045dbbf5686bbe23ec359854a6a12a45b6c6ee407b5f61c224af9760b0e2bc15` |
| Source manifest | `3c1df4684335834bd473d9c40647d839a0b077f044c6980a6983910b05550a16` |
| Scan | `875a0f1badf8852bfb8f7eda5ef471f0bfe48d95489cb97c7702783f6a6efc11` |
| Candidate ledger | `c0701335650ff9967d897b887a750272f9b5fb3a51d3f5138e2d0bcc06715b14` |

The primary and replay workspaces have identical profile files and
byte-identical source-manifest, scan, and candidate-ledger records. Both used
offline isolated compilation and reported Solidity `0.8.30`.

## Preserved workflow failure

The first scan was not overwritten. Foundry selected the highest compatible
compiler already in its own cache, Solidity `0.8.28`, even though the separately
installed PATH compiler was `0.8.30`. That scan also produced zero candidates,
but its scan and candidate-ledger identities differ from the exact-compiler
result.

The verified `0.8.30` binary was copied into Foundry's local compiler cache.
Two new workspaces then produced the exact-compiler result above. No source,
profile, detector, or finding logic changed between these scans.

This exposed a generic workflow defect: a compiler-enabled bounty profile binds
offline mode but does not bind an exact Solidity version. The same profile can
therefore select a different compatible cached compiler on another host. The
next task, `COMP-004`, will add an optional exact compiler pin at the existing
bounty-profile seam. Existing unpinned profiles and their digests must remain
unchanged.

## Results

| Measurement | Result |
| --- | ---: |
| Selected deployed assets | 5 addresses across 2 source contracts |
| Reportable Solidity files | 2 |
| Compiler-only Solidity files | 2 |
| Candidates | 0 |
| Rejected / investigating / confirmed | 0 / 0 / 0 |
| Candidate precision | Undefined; no positive predictions |
| Recall | Unknown; no independent ground truth |

There were no candidate-specific source, audit, known-issue, or impact
decisions to record. The program's audits and known-issue exclusions remain
mandatory if a later scan produces a candidate.

## Comparison

| Trial | Mapping verdict | Reportable files | Compiler candidates | Confirmed |
| --- | --- | ---: | ---: | ---: |
| OpenZeppelin Confidential Contracts | Pass | 22 | 51, all rejected | 0 |
| Silo operational corpus | Fail; research only | 10 | 81, all rejected | 0 |
| Olas governance subset | Pass | 2 | 0 | 0 |

Olas is an untouched independent target and satisfies the gate that Silo did
not. Its tiny source set makes it a weak broad-generalization test. The zero
candidate result is useful evidence that the scanner can be quiet on this
bounded target, but it cannot calibrate real-world recall or bounty value.

## Next work

1. Complete `COMP-004` so new bounty profiles can bind an exact supported
   Solidity release and isolated compilation fails if the observed compiler
   differs.
2. Start `PRECISION-002`, using only generic fixtures derived from the Silo
   research families. Keep private target evidence out of the repository.
3. After precision work, evaluate on another untouched target. Do not measure
   the fixes only against the corpus that inspired them.

## Safety record

Source and compiler acquisition stayed within the single approved boundary.
All subsequent target scans were private and offline. No RPC, fork, chain
interaction, transaction, proof, report, export, disclosure, submission,
platform write, target contact, or detector tuning occurred.
