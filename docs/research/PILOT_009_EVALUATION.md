# PILOT-009 Evaluation

Trial date: 2026-08-13
Target: EulerSwap v2 Ethereum subset (Euler `Euler-Bounty`)
Pinned commit: `81cf6dc988468fd56f690e6bc0e338a5be02d034`
Status: **UNSATISFIED — the fixed detector's isolated compiler cannot reproduce
the target's Foundry auto-remapping, so the frozen closure cannot be compiled
and no scan or candidate identity exists. EulerSwap is retained as a non-bounty
research corpus; a product repair and a re-trial are required.**

## Outcome

The trial selected a genuinely untouched, independent target (EulerSwap v2, not
OpenZeppelin, Silo, or Olas), verified the exact deployed-source mapping from
Euler's pinned first-party verification record, acquired the exact pinned
source and its recursively pinned submodules, enumerated the exact compiler
closure, and froze it as a clean user-read-only Git-backed checkout with the
exact compiler pin. Both required private workspaces then failed deterministically
at the compile stage with the identical unresolved import, before any scan
record or candidate could be produced.

The blocker is a fixed-detector limitation, not a target or mapping failure:
Contract Holes' isolated bounty compiler stages the approved files into a
temporary project with `libs = []` and copies only the target's `remappings.txt`.
The EulerSwap target resolves one import in the reportable closure only through
Foundry's automatic submodule remapping (its own `foundry.toml` sets
`libs = ["lib"]`), and that prefix is not present in the tracked `remappings.txt`.
A standalone offline trial compile that reproduces the automatic remapping
compiles the identical frozen closure cleanly with Solidity `0.8.27`, so the
closure itself is pinned and complete.

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
| Scanner | Contract Holes at fixed detector commit `2574b6e` |
| Solidity compiler | `0.8.27` exact pin, profile and source-manifest schema `1.2` |
| Reportable Solidity files | 5 (factory, implementation, periphery, protocol-fee config, registry) |
| Compiler-only dependency files | 56 |
| Total closure | 61 files, all pinned |
| Compiler mode | Offline, isolated staged reportable + compiler-only dependencies |
| Freeze | Clean detached checkout, Git metadata retained, user-read-only; public selection and status commit pushed before any source download |

The closure was enumerated by following the recursive Solidity import graph from
the five reportable files with the target's remappings and Foundry's automatic
submodule remappings. A standalone isolated offline trial compile of the exact
staged 61 files with the automatic remapping reproduced all 61 source units,
including all five reportable units.

## Blocker evidence

Both private workspaces (first scan and deterministic replay) failed before any
scan record with the identical fixed-detector compile error: one import in the
closure (`v4-periphery/src/utils/BaseHook.sol` from `src/UniswapHook.sol`,
itself in the closure of the reportable `src/EulerSwap.sol`) cannot be resolved
because the temporary staging project disables Foundry's automatic submodule
remapping (`libs = []`) and the target's tracked `remappings.txt` does not map
that prefix. The same closure compiles offline with Solidity `0.8.27` when the
automatic remapping is present, so no target source, dependency, compiler, or
scope change is needed.

The failure is deterministic: the two workspaces produced byte-identical
schema-`1.2` source manifests and the identical compile diagnostic. No scan
record, candidate, or review decision exists.

## Results

| Measurement | Result |
| --- | ---: |
| Selected deployed assets | 5 addresses at one pinned commit |
| Mapping verdict | PASS |
| Reportable Solidity files | 5 |
| Compiler-only Solidity files | 56 |
| Candidates | None; compile blocker, no scan |
| Rule distribution | None |
| Rejected / investigating / confirmed | 0 / 0 / 0 |
| Candidate precision | Undefined; no predictions |
| Recall | Unknown; no ground truth |

## Comparison

| Trial | Mapping verdict | Reportable files | Candidates | Confirmed |
| --- | --- | ---: | ---: | ---: |
| OpenZeppelin Confidential Contracts | Pass | 22 | 51, all rejected | 0 |
| Silo operational corpus | Fail; research only | 10 | 81, all rejected | 0 |
| Olas governance subset | Pass | 2 | 0 | 0 |
| EulerSwap v2 subset (this trial) | Pass | 5 | none (fixed-detector compile blocker) | 0 |

The EulerSwap trial is the only one blocked before scanning. It therefore
provides no generalization or precision evidence, but it does identify a generic
fixed-detector boundary: Contract Holes' bounty compiler does not reproduce
Foundry's automatic submodule remapping. This is a new, observed, generic gap,
parallel to the compiler-pin gap that `COMP-004` closed after `PILOT-008`.

## Recommended next task

Execute [COMP-005](../COMP_005_PLAN.md): derive only the missing direct-library
remappings required by approved imports, keep `libs = []` and explicit
remappings authoritative, publish the generic repair, and then run two private
scans of this same frozen EulerSwap closure. The closure, profile, and freeze are
already complete. If the narrow repair is rejected, select a different untouched
target whose tracked `remappings.txt` is self-contained.

## Limitations

- The trial could not scan, so it yields no precision, recall, or review-effort
  evidence for this target.
- The fixed detector cannot compile the frozen closure; this is a scanner
  boundary, not evidence about the target's safety.
- Recall remains unknown for every trial target; an all-rejected or blocked
  trial does not show that a target is safe.
- Reviewer labels from prior trials are single-reviewer and not independent
  ground truth.
- No proof, report, export, disclosure, submission, chain action, RPC, fork,
  or target contact occurred; the target build/test/deploy scripts were never
  executed.
