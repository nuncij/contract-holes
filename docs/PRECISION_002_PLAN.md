# PRECISION-002 development plan

Status: **BLOCKED — waits for a new independent target trial (`PILOT-008`)**

## Goal

Reduce the generic false-positive families observed during the Silo
compiler-enabled operational validation. Start only after a new independent
target trial (`PILOT-008`) produces an untouched baseline with an exact
deployed-source mapping. Preserve every existing positive finding and
historical supported case.

This task improves triage quality. It does not prove audit completeness,
unknown-bug recall, bounty eligibility, or commercial viability.

## Evidence boundary

The second trial produced 81 reviewer-labelled false positives across generic
families. The primary observed families are:

| Family | Required generic behavior |
| --- | --- |
| Reentrancy ordering on view calls | Read-only view/staticcall interactions before a state write are not state-changing reentrancy paths; the single state-changing external call after the writes, when guarded, is not a reentrancy path. |
| Timelock-style authorization | Modifiers that require a pending value and an elapsed delay protect the following privileged write like a dominating role check. |
| Deployment sequence | External calls on freshly deployed clones or to a factory's own config-derived targets before registration are not untrusted-actor reentrancy. |
| Governance-configured call lists | A delegatecall list returned by a governance-configured module is not attacker-controlled target taint. |
| Read-only target taint | View-call arguments and caller-supplied read-only query targets (caller-harm-only) are not controlled-call-target findings with in-scope impact. |
| Fixed asset provenance | The vault's immutable underlying asset must not be labelled a user-controlled call target. |

These labels come from one reviewer and one target. They are not independent
ground truth. Recall on that target remains unknown.

Use the private records only to derive minimal generic behavior. Keep candidate
IDs, target paths, source excerpts, and candidate-specific evidence outside the
repository. Use no project names, function names, or protocol-specific
identifiers in code or tests.

## Test seam

Test scanner behavior through compiler-backed `ProjectIndex` and
`Scanner.scan_source`. A generic Solidity entry point is the input. Its finding
set and documented evidence are the output.

Use inspection JSON only when a public evidence field needs coverage. Do not
test private helper methods or reproduce detector logic in test assertions.

Add one task-specific compiler corpus under `tests/fixtures/precision_002/` and
one integration test module, `tests/test_precision_002.py`. Pin the existing
offline test compiler, Solidity `0.8.25`. Keep the frozen `audit-1`, `m2-1`,
`m3-1`, and `precision-001` corpus identities unchanged.

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
| Reentrancy ordering and interaction facts | `reentrancy.py`, `dataflow.py` | `test_reentrancy.py`, `test_m2_corpus.py`, `test_precision_001.py` |
| Authorization context | `dataflow.py`, `authorization.py` | `test_authorization.py`, `test_m3_corpus.py`, `test_precision_001.py` |
| External-target provenance | `dataflow.py`, `target_taint.py` | `test_target_taint.py`, `test_m3_corpus.py`, `test_precision_001.py` |
| Call classification and facts | `callgraph.py`, `dataflow.py` | `test_callgraph.py`, `test_dataflow.py`, `test_precision_001.py` |
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
4. Mark `PRECISION-002` **IN PROGRESS** in `TASKS.md`.

Completion criterion: baseline commands pass, and their label and finding
counts are recorded in the development notes or commit message.

### 2. Add the generic regression corpus

Create minimal safe and positive neighbors for each observed family. The
manifest must name generic behavior and expected rule IDs. It must not contain
private candidate identities or target-derived source.

Assert these outcomes through the scanner seam:

- a read-only view interaction followed by a guarded state write does not
  report `SOL005`;
- a state-changing external call followed by a write on the same feasible path
  still reports `SOL005`;
- a timelock-style modifier protects the following privileged write (`SOL009`);
- a governance-configured call list is not user-controlled target taint
  (`SOL008`, `SOL003`);
- a freshly deployed clone used during registration is not an untrusted
  reentrancy path (`SOL005`);
- a view-call argument that can only feed a read-only query is not a
  controlled-call-target finding (`SOL008`);
- the vault's immutable underlying asset remains a fixed target, not
  user-controlled (`SOL008`);
- each safe case has a nearby positive neighbor that still reports.

Completion criterion: every observed family has a generic case. Each new
suppression also has a positive neighbor.

### 3. Distinguish view interactions in reentrancy ordering

Model function mutability and staticcall context in reentrancy event
classification. A `view`/`pure` external call cannot change caller state and
should not form a reentrancy interaction-before-effect path by itself.
Preserve real state-changing interactions as sinks.

Completion criterion: view-only traces are clean, while a genuine
state-changing interaction before a write still reports `SOL005`.

### 4. Recognize timelock-style authorization

Recognize a dominating delay/pending-value guard as protective through the
existing authorization-fact mechanism, using structure and resolved
declarations rather than expanding a project-specific name list. Do not treat
`block.timestamp` alone as authorization.

Completion criterion: timelock-protected writes are clean; unprotected writes
still report `SOL009`.

### 5. Preserve deployment and governance target provenance

Follow freshly deployed clone targets, config-derived addresses, and
governance-configured call lists back to their provenance. Use those facts to
prevent false user-controlled target taint and false reentrancy paths.

Immutability alone does not prove that an external call cannot callback. Keep a
`SOL005` or `SOL008` signal when callback capability or target control remains
unknown. Suppress only when compiler facts prove the call cannot create the
reported reentrant state change or the target is not user-controlled.

Completion criterion: fixed, freshly deployed, and governance-configured
targets are not labelled caller-controlled; caller-selected targets still
report.

### 6. Keep read-only query arguments out of target taint

Do not emit a controlled-call-target finding when the sink is a view/staticcall
whose only influence is a caller-supplied argument to a read-only query, unless
the result feeds a state-changing or value-bearing decision.

Completion criterion: caller-harm-only read-only queries are clean; read
results that feed a protected write or external interaction still report.

## Validation gates

Run focused tests after each slice. Before completion, run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_precision_002 -q
PYTHONPATH=src python3 -m unittest \
  tests.test_callgraph tests.test_dataflow tests.test_reentrancy \
  tests.test_target_taint tests.test_authorization \
  tests.test_precision_001 -q
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

`PRECISION-002` is complete only when:

- every observed family has generic regression coverage;
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

## Stop conditions

Stop the slice and record the limitation if a proposed fix requires:

- a target or protocol name;
- an FHE-specific identifier;
- treating every immutable external target as trusted;
- full EVM or cross-contract symbolic execution;
- a breaking `1.0` JSON, SARIF, fingerprint, or proof-schema change;
- loss of an existing positive or historical supported case.

After this task, evaluate the improved scanner only on a target not used to tune
these fixes. Do not infer bounty viability from the same labels used to tune
`PRECISION-002`.
