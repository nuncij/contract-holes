# PRECISION-001 development plan

Status: **COMPLETE**

## Goal

Reduce the false-positive patterns found during the first compiler-enabled
real-world trial. Preserve every existing positive finding and historical
supported case.

This task improves triage quality. It does not prove audit completeness,
unknown-bug recall, bounty eligibility, or commercial viability.

## Evidence boundary

The trial produced 51 reviewer-labelled false positives in five groups:

| Group | Labels | Required generic behavior |
| --- | ---: | --- |
| Call semantics | 27 | Pure calls, internal calls, and user-defined value-type conversions are not external interactions. |
| Branch feasibility | 8 | Mutually exclusive callback and state-write branches do not form one reentrancy path. |
| Target provenance | 12 | Intended callbacks and fixed deployment targets retain enough provenance for accurate review. |
| Authorization context | 3 | Dominating role checks and caller-owned mapping writes are recognized. |
| Reentrancy trust boundary | 1 | A fixed target and unreachable in-flight state remain visible without an unsupported exploitability claim. |

These labels come from one reviewer and one target. They are not independent
ground truth. Recall on that target remains unknown.

Use the private records only to derive minimal generic behavior. Keep candidate
IDs, target paths, source excerpts, and candidate-specific evidence outside the
repository. Use no project names or FHE-specific identifiers in code or tests.

## Test seam

Test scanner behavior through compiler-backed `ProjectIndex` and
`Scanner.scan_source`. A generic Solidity entry point is the input. Its finding
set and documented evidence are the output.

Use inspection JSON only when a public evidence field needs coverage. Do not
test private helper methods or reproduce detector logic in test assertions.

Add one task-specific compiler corpus under `tests/fixtures/precision_001/` and
one integration test module, `tests/test_precision_001.py`. Pin the existing
offline test compiler, Solidity `0.8.25`. Keep the frozen `audit-1`, `m2-1`, and
`m3-1` corpus identities unchanged.

Each safe case must meet one of these conditions before implementation:

1. It produces the misleading finding and gives a red test.
2. Current code already handles it. Add the regression test, make no code
   change for that case, and identify the missing generic distinction.

Pair every new suppression with a nearby positive case that must still produce
the original rule. A fix cannot rely on a filename, contract name, function
name, project name, or target-specific constant.

## Relevant modules

| Area | Primary modules | Existing regression suites |
| --- | --- | --- |
| Call classification and facts | `callgraph.py`, `dataflow.py` | `test_callgraph.py`, `test_dataflow.py` |
| Reentrancy ordering and path compatibility | `execution.py`, `reentrancy.py` | `test_reentrancy.py`, `test_m2_corpus.py` |
| External-target provenance | `dataflow.py`, `target_taint.py` | `test_target_taint.py`, `test_m3_corpus.py` |
| Authorization and mapping ownership | `dataflow.py`, `authorization.py` | `test_authorization.py`, `test_m3_corpus.py` |
| Public finding metadata | `rules.py`, `inspector.py` | rule, inspection, schema, and documentation tests |

Inspect these modules before selecting a seam. Put shared compiler facts in the
shared analysis modules instead of adding a raw-AST traversal inside one rule.

## Development sequence

Work in vertical red-to-green slices. Finish and test one slice before starting
the next.

### 1. Freeze the baseline

1. Verify a clean `main` worktree and the hashes in
   [the next-session prompt](NEXT_SESSION_PROMPT.md).
2. Run the full Python suite and the frozen `audit-1` evaluation offline.
3. Run the historical bounty evaluation offline.
4. Mark `PRECISION-001` **IN PROGRESS** in `TASKS.md`.

Completion criterion: baseline commands pass, and their label and finding
counts are recorded in the development notes or commit message.

### 2. Add the generic regression corpus

Create minimal safe and positive neighbors for all five groups. The manifest
must name generic behavior and expected rule IDs. It must not contain private
candidate identities or target-derived source.

Assert these outcomes through the scanner seam:

- conversions and compiler-resolved pure/internal calls create no external
  interaction;
- sibling `if`/`else` paths do not combine an interaction with a write;
- a write after an interaction on the same feasible path still reports
  `SOL005`;
- fixed target provenance does not become user-controlled target taint;
- a fixed target is not treated as non-reentrant solely because it is
  immutable;
- a dominating role check protects the following privileged write;
- a mapping write keyed exactly by `msg.sender` is caller-owned;
- a privileged mapping write keyed by another account still requires
  authorization.

Completion criterion: every observed group has a generic case. Each new
suppression also has a positive neighbor.

### 3. Correct call semantics

Use compiler call kind, declaration resolution, type information, and function
mutability to distinguish calls. Do not add a list of library or conversion
function names.

Check `CallGraph._call_edge`, `CallGraph._member_call`, and the sink handling in
`DataFlowAnalysis`. A type conversion or compiler-resolved pure/internal call
must not emit an `external-interaction` fact. Real external, low-level,
delegate, and callback-capable calls must remain sinks.

Completion criterion: the call-semantics cases pass, and existing call-graph,
data-flow, `SOL002`, and `SOL005` positives remain unchanged.

### 4. Add minimal branch compatibility

Model only the branch relation needed by the red case. At minimum, events in
opposite arms of one `if`/`else` statement are mutually exclusive. An event in
one arm and a later event after the conditional can still share a path.

Attach reusable branch context to shared facts or execution events. Let
`ReentrancyAnalysis` reject incompatible interaction/write pairs. Do not build a
general symbolic executor or solver for this task.

Completion criterion: the infeasible callback/write pair is clean, while the
same-branch and post-conditional positive neighbors still report `SOL005`.

### 5. Preserve target provenance

Follow aliases and internal parameters back to their declaration. Record when
a receiver comes from immutable state or another fixed declaration. Use that
fact to prevent false user-controlled target taint.

Immutability alone does not prove that an external call cannot callback. Keep a
`SOL005` signal when callback capability remains unknown. Improve its evidence
or confidence boundary so a reviewer can distinguish fixed deployment trust
from caller control. Suppress only when compiler facts prove that the call
cannot create the reported reentrant state change.

Completion criterion: fixed receivers are not labelled caller-controlled,
caller-selected receivers still report, and no rule treats every immutable
external call as safe.

### 6. Recognize authorization context

Recognize a dominating role or permission check through the existing
authorization-fact mechanism. Use structure and resolved declarations instead
of expanding a project-specific name list.

Retain the index expression for mapping writes. Treat a write as caller-owned
only when the relevant key is proven to be `msg.sender`. Do not suppress writes
to an arbitrary account, role membership, global configuration, or another
user's record.

Completion criterion: role-protected and caller-owned safe cases are clean.
Their unprotected and arbitrary-key positive neighbors still report `SOL009`.

### 7. Reconcile the final reentrancy label

Use the generic results from target provenance and branch compatibility first.
Do not add target names or a deployment allowlist. Do not implement full
cross-contract symbolic execution for one label.

If source facts prove the path safe, add the smallest generic suppression. If
safety still depends on deployment configuration, retain the finding with the
fixed-target and reachability evidence needed for manual rejection. Record that
boundary as an explicit limitation.

Completion criterion: the generic fixture captures the supported conclusion
without claiming that deployment trust is compiler-proven.

## Validation gates

Run focused tests after each slice. Before completion, run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_precision_001 -q
PYTHONPATH=src python3 -m unittest \
  tests.test_callgraph tests.test_dataflow tests.test_reentrancy \
  tests.test_target_taint tests.test_authorization -q
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json > /tmp/contract-holes-evaluation.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json \
  > /tmp/contract-holes-history.json
git diff --check
```

The frozen evaluation must retain every positive and safe label. The historical
evaluation must retain its supported cases, evidence completeness, and go
decision. If a deterministic result changes, explain and version the change.

After the public suite passes, create a new private validation workspace and
rescan the pinned target offline. Keep the canonical trial workspace unchanged.
Record only aggregate candidate counts and generic false-positive groups in
repository docs.

## Completion gate

`PRECISION-001` is complete only when:

- all five observed groups have generic regression coverage;
- every supported safe case is clean or has an explicit manual-review boundary;
- every positive neighbor and frozen positive label remains detected;
- audit and historical evaluation gates pass without weakened thresholds;
- the private rescan reports the remaining workload by generic group;
- public output stays deterministic and schema-compatible;
- rule limitations, evaluation docs, `README.md`, `CHANGELOG.md`,
  `TASKS.md`, and `docs/DEVELOPMENT_PLAN.md` match the result;
- the final diff passes simplification review, the full suite, and
  `git diff --check`;
- the commit is pushed and project CI is green.

Do not define success as zero findings. A remaining evidence-backed unknown is
safer than suppressing a possible vulnerability.

## Result

Completed on 2026-08-13. The generic compiler corpus covers all five observed
false-positive groups without target names, paths, identifiers, or excerpts.
The fix removed four conversion-driven `SOL005` candidates from a fresh
private rescan of the pinned trial. The rescan covered 22 reportable files and
produced 47 candidates remaining across the generic groups: 23
call-semantics, 8 branch-feasibility, 12 target-provenance, 3
authorization-context, and 1 reentrancy-trust-boundary. The canonical private
workspace and target checkout were unchanged. The synthetic evaluation remains
33 positive and 31 safe labels with 1.0 precision and recall; the historical
evaluation remains at 0.875 candidate precision and 1.0 supported-class recall.
The labels are reviewer-derived from one target and are not independent ground
truth. The next task was an independently authorized second real-world target,
completed as `PILOT-007` on 2026-08-13.

A completion review on 2026-08-13 found gaps in the first fixture. It did not
cover a pure public-library call or an interaction reached through an internal
helper branch. It also lacked a post-conditional positive and a role self-grant.
Fixed-target provenance did not cover aliases and internal parameters. The
repair adds these cases and exact path, line, and evidence assertions. All 216
tests and both frozen evaluations pass. A separate private offline rescan
reproduced the same 47 candidates and both deterministic digests. The repair
makes no further precision claim for the pinned target.

## Stop conditions

Stop the slice and record the limitation if a proposed fix requires:

- a target or protocol name;
- an FHE-specific identifier;
- treating every immutable external target as trusted;
- full EVM or cross-contract symbolic execution;
- a breaking `1.0` JSON, SARIF, fingerprint, or proof-schema change;
- loss of an existing positive or historical supported case.

After this task, an independent second real-world target was used to evaluate
the improved scanner. Do not infer bounty viability from the same labels used to
tune `PRECISION-001`.
