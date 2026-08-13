# Next-session prompt

Copy the prompt below into a new development session. Run it from the Contract
Holes repository root.

```text
Continue development of Contract Holes in this repository.

Objective

Finish PRECISION-002 with the develop -> test -> docs -> Git workflow. All
independent-review blockers on the first green diff are resolved and the private
offline replay is complete; the work is left as a reviewable uncommitted diff.
Review that diff, run every validation gate, and finish the remaining
completion-gate steps: commit one coherent change, push main, and verify project
CI. Preserve every existing positive, frozen corpus identity, label, threshold,
split, and public evidence contract. Do not copy private target code or evidence
into the repository.

Read first

- AGENTS.md, if present
- CONTRIBUTING.md
- TASKS.md
- docs/DEVELOPMENT_PLAN.md
- docs/PRECISION_002_PLAN.md (authoritative scope)
- docs/COMP_004_PLAN.md
- docs/research/PILOT_008_EVALUATION.md
- docs/EVALUATION.md
- this handoff

Treat current command output as authoritative for mutable state.

Project state

- Release: 1.1.1.
- M0 through M8, PRECISION-001, REPAIR-007, PILOT-008, and COMP-004 are
  complete.
- PRECISION-002 is IN PROGRESS. All independent-review blockers are
  resolved in the uncommitted diff by narrowing or retaining findings: `SOL005`
  no longer forms paths for compiler-resolved view/pure and staticcall
  interactions, while state-changing calls, contract creation, and fresh-target
  initializers remain reportable (there is no no-callback proof and no blanket
  fresh or creation suppression); `external-return` taint is never cleared by an
  immutable receiver; timelock recognition is strict (separate unconditional
  nonzero-pending and `block.timestamp >= deadline` guards over distinct
  declarations, with the pending value feeding the protected write without
  user-controlled taint or an exact
  zero-clear of a guarded field; no unrelated later write inherits it); and the
  read-result use tracer was deleted in favor of a narrow ignore-or-view-entry
  suppression. Unsatisfied manual-review boundaries by design: governance/
  config-derived call lists (`executeGovernance` reports `SOL008`), factory-owned
  target provenance, callback safety for creation and fresh targets, broader
  timelock shapes, and harmless used-read analysis. The private offline replay
  is complete: unchanged source and dependency identities, cached Solidity
  0.8.28, ten reportable files, 59 findings/candidates versus 81 before tuning
  (22 removed, no new findings), which are investigation leads, not
  vulnerabilities and not bounty submissions.
- Suite: 238 tests after PRECISION-002 local slices.
- Frozen synthetic evaluation: 33/33 positive labels and 31/31 safe labels.
- Historical candidate precision: 0.933333; supported-class recall: 1.0;
  evidence completeness: 1.0; decision: go. The `m7-history-1` raw result was
  versioned in `evaluation/bounty-history-1.0.json` because the
  view-interaction fix removed one out-of-model Enzyme `SOL005` candidate; no
  label, fixture, threshold, or split changed.
- COMP-004 added optional `--compiler-version X.Y.Z`, additive normalized
  profile/source-manifest schema 1.2, exact isolated Foundry selection, and
  fail-closed observed-version checking. Frozen unpinned 1.0/1.1 profile
  digests are unchanged.
- A new private offline Olas replay selected only Solidity 0.8.30, matched the
  frozen source and compiler-dependency sets, scanned two reportable files, and
  again produced zero findings and zero candidates.

Private evidence boundary

Private Silo records may be inspected locally only to understand the already
documented generic families. Do not send private source, paths, candidate IDs,
source excerpts, traces, or records to an external model or service. Do not put
them in fixtures, tests, commits, documentation, or logs intended for sharing.

No RPC, fork, chain action, transaction, proof, report, export, disclosure,
submission, platform write, or target contact is authorized. No target-specific
detector rule, project name, contract name, function name, constant, or path is
allowed.

Required behavior

Keep the compiler corpus under tests/fixtures/precision_002 and test through
ProjectIndex plus Scanner.scan_source as specified by the plan. Each safe case
must have a nearby positive neighbor that keeps the original rule reportable.

Cover these generic distinctions:

1. Read-only view/static interactions do not create a SOL005 reentrancy path; a
   real state-changing external interaction before a write still does.
2. Only separate unconditional direct guards — a nonzero pending-state
   comparison plus a different state deadline with block.timestamp >= deadline
   (or deadline <= timestamp) — where the pending value feeds the protected
   sensitive write without user-controlled taint, protect the following
   privileged write from SOL009. Wrong directions, timestamp `==`/`!=`,
   OR/optional delay, unrelated zero/nonzero flags, timestamp-only, mixed
   pending/caller values, deadline-derived writes, local pending reads,
   unrelated later privileged writes, compound expressions, and combined
   boolean guards still report.
3. Contract creation and fresh-target initializers remain `SOL005`-reportable;
   only compiler-resolved view/pure and staticcall interactions are suppressed.
   A created address is non-user-controlled fresh provenance for `SOL008`, but
   that says nothing about callback safety for `SOL005`.
4. Governance-configured call lists are not proven non-attacker-controlled:
   immutable receiver identity never clears `external-return` taint, so both a
   fixed-module list and a caller-selected module report SOL008, with SOL003 a
   manual-review signal on both.
5. Caller-supplied targets used only by read-only queries are caller-harm-only
   only when the read result is ignored or the enclosing external entry is
   view/pure; a used read result in a non-view function (mapping key,
   state-changing call argument, or write value) reports SOL008.
6. Immutable/fixed asset provenance is not user-controlled; mutable
   caller-controlled asset provenance remains reportable.

Workflow

1. Verify the working tree contains the PRECISION-002 uncommitted diff and that
   `git status` shows only intended files.
2. Run a simplification review of the diff: confirm the generic distinctions are
   covered by the `precision-002` corpus, that no rule-local raw-AST walk, name
   list, configuration toggle, or target suppression was added, and that every
   safe case has a positive neighbor.
3. Inspect the full diff for private material (target names, paths, candidate
   IDs, excerpts, constants, FHE identifiers). None is expected.
4. Run the full suite and frozen synthetic/historical evaluations. The
   historical `m7-history-1` raw result was intentionally versioned; verify the
   gate still passes without weakened thresholds and that no supported case or
   positive finding regressed.
5. Update the status docs only if a truthful outcome changed since the last
   commit of this prompt.
6. Commit one coherent change, push main, verify CI, leave main clean and equal
   to origin/main, and mark PRECISION-002 COMPLETE in TASKS.md only when every
   plan completion gate passes (the private-replay validation is already
   complete).

Validation gates

PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check

Stop only if an existing positive or frozen identity changes unexpectedly, a
generic distinction cannot be established without target-specific knowledge,
or work would cross the prohibited external-action boundary.
```
