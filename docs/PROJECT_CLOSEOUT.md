# Project closeout

Decision date: 2026-08-14
Final release: `1.1.1`
Status: **CLOSED. Development stopped by owner decision. No task is queued and
none will be.**

Contract Holes is wound down as a bug-bounty-finding tool. The code works, the
gates pass, and the last release is signed and reproducible. It is stopped
because it did not find anything, and because the reason it did not find
anything is structural rather than incidental.

This record exists so the decision is legible later, including to whoever
reopens the repository.

## What the tool achieved

- 13 detectors (`SOL001`–`SOL013`), 248 tests, no runtime dependencies.
- Frozen JSON `1.0` and SARIF 2.1.0 output contracts, a versioned bounty profile
  and candidate schema, baselines, suppressions, a rule catalog, and CI examples.
- Three signed tag objects (`v1.0.0`, `v1.1.0`, `v1.1.1`); the latter two are
  verified private GitHub releases with reproducible build artifacts.
- A local bounty research workflow with immutable pinned scope, offline isolated
  compilation, deterministic replay, human-only review states, and a strict
  private/public evidence boundary.
- Four real-world trials against authorized live bug-bounty targets, all private
  and offline, with no report, export, disclosure, submission, chain action, or
  target contact at any point.

## What it did not achieve

| Trial | Reportable files | Candidates | Confirmed |
| --- | ---: | ---: | ---: |
| OpenZeppelin Confidential Contracts `v0.4.0` | 22 | 51, all rejected | 0 |
| Silo Finance v2/v3 (source-to-scope gate failed) | 10 | 81, all rejected | 0 |
| Olas governance `v1.2.5` | 2 | 0 | 0 |
| EulerSwap v2 | 5 | 25, all rejected | 0 |
| **Total** | **39** | **157, all rejected** | **0** |

No candidate was ever confirmed. No report was written and no submission was
made. Exactly one candidate reached `investigating`, in the first trial, and
deeper trust-boundary analysis rejected that one too.

Read the totals carefully. The 157 candidates are **not** 157 independent
observations: they span more than one detector revision, and the 81 Silo
candidates came from a source revision the project itself later invalidated. The
number therefore does not measure recall, and it does not show that these
targets were free of vulnerabilities. What it does measure is operator utility —
roughly one working day per target, 157 human review decisions, one temporary
lead, and zero reports.

## Why the project is stopped

**The limit is structural, not a matter of sample size or tuning.** The
detectors recognize local primitives. Confirming a bounty-relevant defect
requires trust boundaries, deployment state, protocol semantics, and economic
invariants, all of which the rule implementations deliberately leave to manual
review. Two precision tasks reduced candidate *volume* without changing *yield*:
the Silo re-scan fell from 81 candidates to 59, and the untouched EulerSwap
target still produced 25 rejections that all landed inside boundaries
`PRECISION-002` had already documented as intentional.

**The frozen historical corpus predicted this, and says so in its own labels.**
Of ten disclosed real vulnerabilities, five are marked out-of-model: share
pricing (Enzyme), verification bypass (Nomad), share accounting (Belt),
flash-loan governance (Beanstalk), and a donation path that breaks a health
check (Euler). The five in-model cases collapse to roughly three families —
three are uninitialized-implementation/proxy-init, one is reentrancy, and the
Aurora case is a supported *signal* only, since the scanner never discovers the
inflation mechanism. The excluded half is where current bounty programs
concentrate their value.

**The reported precision figures do not transfer.** The `audit-1` gate scores
1.0/1.0 on 33 positive and 31 safe labels that the detector author wrote. The
`m7-history-1` gate scores 0.933333 precision on cases its own limitations field
describes as "locally authored reductions, not the complete historical
deployments". Neither measures unseen production code.

**There is no discovery moat.** Slither ships 101 detectors with a mature IR,
CFG/SSA and taint APIs; Aderyn covers the same headline classes with far greater
breadth, speed, and adoption. Contract Holes is ahead of lighter tooling and
ahead of LLM-assisted review on reproducibility, privacy, and deterministic
evidence — but LLM-assisted review attacks precisely the out-of-model territory
this tool cannot reach. Beating the lighter tools is not a moat while Slither
and Aderyn exist.

**Trial #5 had no expected value left, including informational value.**
EulerSwap reproduced already-known limitations and revealed no new
false-positive family, so an unchanged fifth run would have tested no
hypothesis.

## Verdict provenance

Two independent engines evaluated the project against the same evidence and
reached the same conclusion. The second was given the measurements without the
first engine's conclusion, so it was not anchored. Both recommended winding
down as a bug-bounty tool, freezing `1.1.1`, and skipping trial #5.

## What is worth keeping

The durable asset is the **process harness**, not the analyzer:

- immutable scope and provenance pinning, exact compiler pinning, isolated
  offline compilation, credential stripping, and byte-identical deterministic
  replay;
- the candidate and evidence schemas, and the private/public boundary that kept
  four real targets' source, paths, hashes, and candidate identities out of this
  repository;
- the real-target rejection taxonomy and the nearby safe fixtures it produced;
- the detector *ideas* behind `SOL008`–`SOL013`, which would be better ported
  onto Slither or Aderyn than maintained on a private IR.

Treat as sunk for the bounty objective: the custom AST, call-graph, and
data-flow stack that duplicates mature frameworks; the generic detectors already
available elsewhere; the proof, report, approval, and export machinery, which
processed no reports and could not answer the one candidate that reached
investigation; and the curated reductions as evidence of real-world efficacy.

## If this is ever reopened

Do not add more generic detectors, and do not run another trial on the current
design. Two options, in order:

1. **Settle the question properly.** Run a blinded benchmark: complete, exact
   historical vulnerable repositories plus matched clean revisions, root causes
   labelled independently and withheld, scored against Slither, Aderyn, and an
   LLM-assisted reviewer on actionable root-cause discovery and review time.
   Recovering the actual root causes would mean the four-target sample was
   unlucky. Better out-of-sample precision without root causes would mean a
   tuning problem. Generic signals without root causes would confirm the ceiling
   and end the question.
2. **Change target class, not detector count.** Pick one protocol vertical, such
   as lending or vault accounting, derive economic invariants manually or with a
   model, and verify them with Foundry stateful and differential tests. Reuse
   the scope and evidence harness above. This is a different project that
   imports this one; it is not a continuation of the rule set.

## Standing boundaries

These remain in force for the archived repository:

- Only scan contracts you own or are explicitly authorized to assess.
- No target source, manifest, scan, candidate, review, path, excerpt, or hash
  belonging to any private trial may enter this repository.
- The four trial targets were never contacted, and no finding was ever
  disclosed. Nothing here authorizes reopening that.
- `PILOT-007` (Silo) stays **UNSATISFIED** and will not be resumed. Silo is
  retained only as a non-bounty research corpus.
