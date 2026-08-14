# COMP-005 development plan

Status: **COMPLETE — 2026-08-14.** The generic deterministic direct-library
remapping repair is implemented, published, and validated by a green CI run.
Two new private offline scans of the unchanged frozen PILOT-009 EulerSwap
closure (five reportable plus 56 compiler-only files, Solidity `0.8.27`, schema
`1.2`) reproduced byte-identical profile, source-manifest, scan, and
candidate-ledger identities, and every candidate received a private review
decision. `PILOT-009` is complete. See
[the evaluation](research/PILOT_009_EVALUATION.md).

## Goal

Compile approved Solidity closures that use Foundry's direct `lib/<name>/`
package convention without loading target configuration or weakening source
isolation. Derive only the missing remappings required by imports in the
content-bound closure. Keep `libs = []`, keep explicit safe `remappings.txt`
entries authoritative, and preserve legacy profile and source-manifest
identities when no derived remapping is needed.

The observed case is generic: an approved file imports
`v4-periphery/src/utils/BaseHook.sol`, while the declared compiler dependency is
`lib/v4-periphery/src/utils/BaseHook.sol`. The isolated staging project copies
the dependency but cannot resolve the package prefix because it disables
Foundry library discovery.

## Work boundary

OpenCode model `opencode-go/deepseek-v4-flash` implements this task. The primary
session writes the task contract and verifies the result. Keep the repair
generic; target names, paths, and candidate facts do not belong in production
code or public test fixtures.

The existing standing authorization covers the frozen local EulerSwap checkout
and private offline replay. Keep target source and evidence outside this
repository. No new download, RPC, fork, chain action, proof, report, export,
disclosure, submission, bounty-platform write, or target contact is authorized.

## Required design

Repair the existing isolated compiler seam in `bounty_scope.py` with the
smallest deterministic mechanism that closes the observed gap:

1. Inspect imports only in the already approved reportable and compiler-only
   files. Reuse the existing Solidity import parser and comment masking.
2. Keep relative imports and imports covered by the target's validated
   `remappings.txt` unchanged.
3. For an uncovered package import, derive `<name>/=lib/<name>/` only when the
   imported file resolves to an already declared staged path below that exact
   direct library directory.
4. Append derived mappings in stable lexical order to the temporary staging
   project's remappings. Keep `libs = []`; do not load `foundry.toml`, execute
   `forge remappings`, search undeclared files, or expand the approved closure.
5. Treat the derived mapping as deterministic scanner behavior computed from
   content-bound manifest inputs. Do not change profile or source-manifest
   schemas or legacy digests merely to cache it.

Explicit validated remappings take precedence. A missing or undeclared target
must still fail closed. Do not attempt full Foundry remapping parity beyond the
direct-library case observed here.

## Test-first sequence

### 1. Freeze the baseline

Verify clean `main` matching `origin/main`. Commit `afc702f` is the last
implementation/outcome commit before this doc-only plan. Run the full suite,
frozen audit evaluation, and historical bounty evaluation. Confirm no scanner
code changed after detector commit `2574b6e`.

Completion criterion: 238 tests pass; audit remains 33 positive and 31 safe at
1.0; history remains 0.933333 candidate precision, 1.0 supported recall, 1.0
evidence completeness, result hash
`9bf60837d252bac17ba579c91a04a8d33fc5f0c9fcb5c8df59402be0397bdf90`.

### 2. Add red generic tests

Add the smallest generic fixture and tests that prove:

- an uncovered import such as `example-lib/src/Dependency.sol` compiles when
  the exact declared dependency is staged at
  `lib/example-lib/src/Dependency.sol`;
- explicit validated remappings remain authoritative and are not duplicated;
- an import cannot pull an undeclared file into the compiler;
- mapping order and scan output are deterministic;
- an existing self-contained bounty fixture retains its exact profile and
  source-manifest identities.

Completion criterion: the new positive integration test fails for the observed
reason before production code changes, while all existing tests remain green.

### 3. Implement the narrow repair

Add one focused helper at the bounty compiler boundary and use it when writing
the temporary `remappings.txt`. Avoid a new public configuration surface unless
the direct deterministic derivation proves impossible.

Completion criterion: the new tests pass, undeclared imports still fail closed,
and no target-specific string appears in production code or fixtures.

### 4. Validate and publish the repair

Run all public gates and inspect the diff for scope growth, schema changes,
target data, and accidental complexity. Commit the generic repair, push `main`,
and require green Quality and Reproducible package CI before private replay.

### 5. Replay PILOT-009 privately

Use the existing frozen checkout and closure. Create two new private workspaces;
do not overwrite the preserved failed workspaces. Use schema `1.2`, Solidity
`0.8.27`, the same five reportable files, and the same 56 compiler-only files.
Run both scans offline and compare profile, source-manifest, scan, and candidate
digests plus compiler version and aggregate counts.

Completion criterion: both scans complete and all compared identities match.
If compilation still fails or identities differ, keep PILOT-009 unsatisfied.

### 6. Review and close out

Review every candidate privately without tuning the detector from its labels.
Update the aggregate PILOT-009 evaluation and project status without private
paths, hashes, IDs, excerpts, or candidate-specific explanations. Run the public
gates, commit, push, and verify final CI.

Completion criterion: every candidate has a private state, public docs are
aggregate-only, the repository is clean, and `main` matches `origin/main`.

## Validation gates

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check
```

## Completion gate

`COMP-005` is complete only when the generic regression is green, legacy
identities are unchanged, both frozen EulerSwap replays match, all candidates
are reviewed privately, aggregate docs are truthful, both repair and closeout
commits are pushed, and both CI runs pass. PILOT-009 becomes complete only when
its original completion gate also passes.

## Stop conditions

Stop and leave the task incomplete if the repair requires target configuration
execution, undeclared source discovery, a schema-breaking change, target-tuned
detector behavior, a changed frozen closure, non-deterministic replay, private
evidence in the repository, or any action outside the standing authorization.

## Completion record

The generic repair added one focused helper at the isolated bounty compiler
boundary. The staging compiler now derives `<name>/=lib/<name>/` for an
uncovered package import only when the imported unit resolves to an already
declared staged path below that exact direct library directory, and appends the
derived mappings in stable lexical order to the temporary `remappings.txt`.
`libs = []` stays empty, explicit validated remappings retain precedence and are
not duplicated, relative imports are untouched, undeclared imports still fail
closed, and no profile or source-manifest schema or legacy digest changes when
no mapping is derived. No target-specific string appears in production code or
public fixtures.

Nine new tests cover the uncovered direct-library compile, explicit
precedence and non-duplication, fail-closed undeclared imports, deterministic
mapping order, and unchanged legacy identities; the suite is now 247 tests with
the frozen audit and historical gates unchanged. Repair commit `04781a9` was
pushed to `main`; GitHub CI run `31787480206` passed both Quality and
Reproducible package before private replay.

Two new private offline workspaces then replayed the unchanged frozen EulerSwap
closure (five reportable plus 56 compiler-only files, schema `1.2`, Solidity
`0.8.27`). Both scans completed and produced byte-identical profile,
source-manifest, scan, and candidate-ledger identities; the source manifest
matches the frozen pre-scan manifest. The scan produced 25 candidates across
three rules; every candidate received a private operator-confirmed rejection
after source review. No proof, report, export, disclosure, submission, chain
action, or target contact occurred. `PILOT-009` is now complete.
