# PILOT-009 Evaluation

Trial date: 2026-08-13 (selection, acquisition, freeze, and blocked first scan)
Replay date: 2026-08-14 (after the `COMP-005` generic repair)
Target: EulerSwap v2 Ethereum subset (Euler `Euler-Bounty`)
Pinned commit: `81cf6dc988468fd56f690e6bc0e338a5be02d034`
Status: **SATISFIED — the fixed detector's repaired isolated compiler replays
the frozen closure twice, all compared identities match, and every candidate has
a private review state.**

## Outcome

The trial selected a genuinely untouched, independent target (EulerSwap v2, not
OpenZeppelin, Silo, or Olas), verified the exact deployed-source mapping from
Euler's pinned first-party verification record, acquired the exact pinned
source and its recursively pinned submodules, and froze the exact compiler
closure before any scan. The original fixed detector (`2574b6e`) could not
compile the closure because its isolated compiler wrote `libs = []` and loaded
only the target's tracked `remappings.txt`, so the import
`v4-periphery/src/utils/BaseHook.sol` could not resolve. Both original private
workspaces failed deterministically at that compile stage and no scan or
candidate identity existed.

The `COMP-005` repair closes that generic gap: the isolated compiler now derives
only the direct-library remappings that the approved closure's own imports
require, while keeping `libs = []` and explicit validated remappings
authoritative. After the repair, two new private workspaces replayed the
unchanged frozen closure offline. Both scans completed with the same exact
compiler release, and their profile, source-manifest, scan, and candidate-ledger
identities are byte-identical. The source manifest still matches the frozen
pre-scan manifest exactly, so the source and dependency sets are unchanged.

The scan produced candidates in several rules; every candidate was reviewed
privately against the pinned source and program impact rules and received an
explicit human decision. No proof, report, export, disclosure, submission,
chain action, or target contact occurred, and no detector behavior was tuned
from these labels.

## Target and source gate

Public selection research compared three current programs and selected the
EulerSwap v2 Ethereum subset. Euler's first-party verification manifest
(`euler-interfaces` commit `d938bc264d6e1cee68a559798044d43ade8ac95e`) maps the
five selected deployed addresses to the pinned commit. The immutable tag
`eulerswap-2.0` resolves to the same commit. The target's `foundry.toml` pins
Solidity `0.8.27` with optimizer 2,500 runs, inside the supported range.

**Mapping verdict: PASS.** Every recorded gitlink (top-level and nested) in the
acquired checkout matches the public selection record exactly; all dependencies
are pinned immutable revisions, so the candidate dependency graph needed no
mutable or unpinned source.

See [the selection record](PILOT_009_TARGET_SELECTION.md) for the public
candidate comparison, addresses, paths, and restrictions.

## Frozen pre-scan closure

| Item | Value |
| --- | --- |
| Scanner | Contract Holes at the `COMP-005`-repaired detector (schema `1.2`) |
| Solidity compiler | `0.8.27` exact pin, profile and source-manifest schema `1.2` |
| Reportable Solidity files | 5 (factory, implementation, periphery, protocol-fee config, registry) |
| Compiler-only dependency files | 56 |
| Total closure | 61 files, all pinned |
| Compiler mode | Offline, isolated staged reportable + compiler-only dependencies |
| Freeze | Clean detached checkout, Git metadata retained, user-read-only; public selection and status commit pushed before any source download |

The closure was enumerated by following the recursive Solidity import graph from
the five reportable files with the target's remappings and Foundry's automatic
submodule remappings, and verified by an isolated offline trial compile with the
automatic remapping. It was not changed by the repair.

## COMP-005 repair

The generic repair derives `<name>/=lib/<name>/` for an uncovered package import
only when the imported unit is already declared below that exact direct library
directory in the approved closure. Explicit validated `remappings.txt` entries
remain authoritative; relative imports are untouched; `libs = []` stays empty;
no target configuration is loaded and no undeclared file can enter the
compiler. The source manifest and profile identities do not change when no
derived mapping is needed. For this closure the repair adds exactly the single
`v4-periphery/` prefix mapping that the approved imports require.

## Results

| Measurement | Result |
| --- | ---: |
| Selected deployed assets | 5 addresses at one pinned commit |
| Mapping verdict | PASS |
| Reportable Solidity files | 5 |
| Compiler-only Solidity files | 56 |
| Candidates | 25 |
| Rule distribution | `SOL003`: 1, `SOL005`: 1, `SOL008`: 23 |
| Rejected / investigating / confirmed | 25 / 0 / 0 |
| Replay identities | byte-identical profile, manifest, scan, and candidates |
| Candidate precision | 0 of 25 under this trial's own reviewer labels; independently established precision remains undefined |
| Recall | Unknown; no independent ground truth |

Every candidate received one private operator-confirmed decision after review
against the pinned source and the program's impact rules. The rejected families
are consistent with the scanner's documented conservative boundaries: immutable
deployment settings and freshly created clones are not attacker-selected
targets; registry-bonded or factory-deployed pools are bounded targets; the
swap callback to the caller-selected recipient is the documented flash-swap
design; and the management `delegatecall` is an immutable deployment trust
boundary. None was confirmed as an in-scope impact.

## Comparison

| Trial | Mapping verdict | Reportable files | Candidates | Confirmed |
| --- | --- | ---: | ---: | ---: |
| OpenZeppelin Confidential Contracts | Pass | 22 | 51, all rejected | 0 |
| Silo operational corpus | Fail; research only | 10 | 81, all rejected | 0 |
| Olas governance subset | Pass | 2 | 0 | 0 |
| EulerSwap v2 subset (this trial) | Pass | 5 | 25, all rejected | 0 |

The EulerSwap trial is the first to exercise the repaired isolated compiler
against a genuinely untouched target that needs a derived direct-library
remapping. It therefore validates both the repair and the deterministic replay
gate. As with every prior trial, an all-rejected or quiet result does not show
that the target is safe or that unknown-bug recall is useful.

## Limitations

- The trial produces no precision or recall evidence: recall is unknown, and
  every prediction was rejected after source review, so candidate precision is
  undefined for this target.
- Reviewer labels are single-reviewer and not independent ground truth.
- The scanner does not model every program rule; an all-rejected trial does not
  establish that the target is safe.
- The `COMP-005` repair reproduces only the direct-library remapping case
  observed here; it does not implement full Foundry remapping parity.
- No proof, report, export, disclosure, submission, chain action, RPC, fork,
  or target contact occurred; the target build/test/deploy scripts were never
  executed.
