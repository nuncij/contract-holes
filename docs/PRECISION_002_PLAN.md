# PRECISION-002 development plan

Status: **IN PROGRESS — all independent-review blockers are resolved, all
repository-local gates pass, and the private offline replay is complete. Only
final review, commit/push, and CI remain (see Result)**

## Goal

Reduce the generic false-positive families observed during the Silo
compiler-enabled operational validation. `PILOT-008` supplied the required
untouched independent baseline with an exact deployed-source mapping. Start
after `COMP-004` bound the compiler version used by private replay profiles.
Preserve every existing positive finding and historical supported case.

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

The following are the original acceptance criteria. They are preserved here
even where the result had to retain a finding instead of claiming an unsafe
suppression.

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
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check
```

Keep diagnostic output on stdout. If a captured copy is needed, write it under
an ignored repository directory and remove it before finishing.

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

## Result

All independent-review blockers on the green implementation were resolved
in this repository-local slice on 2026-08-13. The generic compiler corpus under
`tests/fixtures/precision_002/` (Solidity `0.8.25`, compiler-backed
`ProjectIndex` plus `Scanner.scan_source`) plus `tests/test_precision_002.py`
now provide generic coverage for supported outcomes plus explicit unsatisfied
and manual-review boundaries. No private target code, paths, candidate IDs, or
excerpts entered the repository.
No target network, chain, RPC, proof, report, export, disclosure, submission,
target contact, or bounty-platform write occurred.

Detector changes are in shared analysis modules. No rule-local AST walks, name
lists, configuration toggles, or target suppressions were added:

- `dataflow.py` records callee mutability, fresh-deployment provenance, and
  result-ignored state on shared sink facts. It taints freshly created addresses
  with a non-user-controlled `fresh-created` marker. It evaluates the index
  expression of index-write targets so a read used as a mapping key reaches a
  sink. It emits a strict `timelock:delay-and-pending` authorization fact only
  when separate unconditional direct guards prove a nonzero pending value
  (`state != zero`) and a different state deadline via `block.timestamp >=
  deadline` or `deadline <= block.timestamp`, with the pending value feeding the
  protected sensitive write without user-controlled taint. Exact zero-clears of
  the guarded pending and deadline declarations are also accepted. No other
  write inherits protection.
- `reentrancy.py` no longer classifies compiler-resolved view/pure callees or
  `staticcall` interactions as `SOL005` events. State-changing calls, contract
  creation, and fresh-target initializers remain reportable. There is no
  no-callback proof and no blanket fresh or creation suppression.
- `target_taint.py` deletes the read-result use tracer. A view/pure/staticcall
  `SOL008` sink is suppressed only when its result is ignored at the call site
  or the externally callable enclosing function is view/pure. In a non-view
  entry any used result (mapping key, state-changing call argument, or write
  value) reports `SOL008`, and mapping-index calls are evaluated so that use is
  not missed.
- `dataflow.py` never clears `external-return` taint for calls whose receiver is
  an immutable/constant declaration. Receiver identity is not provenance for
  the returned targets.
- The unconditional-node check moved to the shared `dataflow` module so
  `authorization.py` reuses it instead of duplicating a private helper.

Safe/positive outcomes per family:

| Family | Clean | Positive neighbor retained |
| --- | --- | --- |
| View-interaction ordering | view-then-write, write-then-interact | state-changing interaction before write reports `SOL005` |
| Timelock authorization | separate unconditional nonzero-pending and elapsed-delay guards, pending value feeding the protected write without user-controlled taint, then exact zero cleanup of those guarded fields | wrong directions, timestamp `==`/`!=`, OR/optional delay, unrelated zero/nonzero flags, timestamp-only, mixed pending/caller values, deadline-derived writes, local pending reads, unrelated later privileged writes, compound, and combined boolean guards report `SOL009` |
| Deployment sequence | created address is non-user-controlled fresh provenance for `SOL008` | a freshly deployed clone and a caller-supplied existing target report `SOL005` |
| Governance call lists | none (unsatisfied) | both a fixed-module list and a caller-selected module report `SOL008`. `SOL003` stays a manual-review signal on both |
| Read-only target taint | caller-supplied read-only query with an ignored result or in a view entry | a used read result in a non-view entry reports `SOL008` (mapping key, call argument, write value) |
| Fixed asset provenance | immutable underlying asset (already green before this task) | caller-supplied token target reports `SOL008` |

Unsatisfied families and explicit boundaries (not suppressed, no fake
coverage):

- Governance/config-derived call lists: a list returned by a fixed-module view
  call is not proven non-attacker-controlled. `external-return` taint is never
  cleared by receiver identity, so `executeGovernance` reports `SOL008`.
  A provenance proof that the returned array is governance-owned was not
  implemented. The slice is incomplete by design.
- Factory-owned targets generally: no provenance proof exists for addresses
  derived from a factory's own state. Only the direct immutable-receiver case
  is handled, and it predates this task.
- Callback safety for creation and fresh targets is not proved: contract
  creation and fresh-target initializers report `SOL005` whenever callback
  capability or target control remains unknown. There is no no-callback proof
  and no blanket fresh or creation suppression.
- Timelock recognition is deliberately strict: wrong comparison directions,
  timestamp `==`/`!=`, OR/optional delay, unrelated zero/nonzero flags,
  timestamp-only guards, compound expressions, combined boolean guards, a
  named-constant zero, and a pending comparison against the same state deadline
  are not recognized and still report `SOL009`.
- Multiple independent timelock sections in one callable are collapsed to one
  conservative fact and can leave an otherwise safe write reportable.
- Read-result use is conservative by construction: in a non-view function any
  used read result reports `SOL008`. There is no harmless-use or
  cross-transaction analysis. The previous claim that unsafe missed uses stay
  conservative was removed because the tracer itself was deleted.
- The private offline replay is complete: unchanged exact source and dependency
  identities, exact cached Solidity `0.8.28`, ten reportable files. It produced
  59 findings/candidates versus 81 before tuning: 22 removed, no new findings.
  Current rule distribution: SOL003=1, SOL005=13, SOL008=41, SOL009=3, SOL011=1.
  removed distribution: SOL005=13, SOL008=9. The remaining 59 findings are
  investigation leads, not vulnerabilities and not bounty submissions.

Frozen gates: the `audit-1` evaluation retains 33/33 positive and 31/31 safe
labels with 1.0 precision/recall. The historical `m7-history-1` result changed
deterministically: the view-interaction fix removed one out-of-model `SOL005`
candidate from the Enzyme reduction (a `totalSupply()` view read before a
write), improving candidate precision from 0.875 to 0.933333 with all five
supported cases, 1.0 supported-class recall, 1.0 evidence completeness, and the
`go` decision unchanged. `evaluation/bounty-history-1.0.json` was regenerated
through the public CLI. No fixture, label, threshold, or split changed.

Suite: 238 tests pass with `git diff --check`. The remaining completion-gate
items — final review, the single coherent commit, push to `main`, and green
project CI — are outside this documentation slice, so `PRECISION-002` stays
**IN PROGRESS** until they complete.
