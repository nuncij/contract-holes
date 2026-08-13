# COMP-004 development plan

Status: **COMPLETE — 2026-08-13**

## Goal

Let a compiler-enabled bounty profile bind one exact supported Solidity release.
The isolated compiler module must select that release and fail if the observed
build information reports another version.

This fixes the concrete `PILOT-008` failure where one unchanged profile selected
Solidity `0.8.28` before the approved `0.8.30` binary was present in Foundry's
cache. It does not reproduce deployment bytecode or import target build settings.

## Interface and compatibility

Add one optional initialization argument:

```text
holes bounty init ... --compiler-version 0.8.30
```

Keep the compiler profile as the single external seam. Callers declare the
version once; profile validation, manifest binding, isolated Foundry
configuration, and observed-version verification stay behind that interface.

- Accept an exact `MAJOR.MINOR.PATCH` release inside the published supported
  Solidity range.
- Reject the option with `--source-only`.
- Emit additive profile and source-manifest schema `1.2` when pinned.
- Preserve existing unpinned `1.0`/`1.1` profiles, normalized payloads, digests,
  and auto-detection behavior byte-for-byte.
- Write `solc_version = "X.Y.Z"` in the temporary safe `foundry.toml` when a
  pin exists; do not load the target configuration.
- Require one observed compiler release, matching the pin; reject empty, mixed,
  or mismatched observed version sets.
- Continue recording the compiler version strings supplied by Foundry build
  information in `scan.json` without normalization.

Optimizer runs and EVM target are intentionally outside this task. Contract
Holes consumes compiler ASTs in a fixed isolated project; it does not claim
bytecode reproduction.

## Development sequence

1. Add failing interface-level tests for CLI/profile normalization, invalid
   combinations, legacy digest stability, pinned temporary Foundry
   configuration, and observed-version mismatch.
2. Extend `BountyProfile` and its closed TOML/schema validation with the optional
   exact version.
3. Carry the pin through source identity and isolated compilation, keeping the
   selection logic inside the compiler module.
4. Add additive `1.2` schemas and documentation.
5. Run the full suite and frozen synthetic/historical evaluations.
6. Create a new private pinned Olas validation workspace and reproduce the
   frozen zero-candidate `0.8.30` scan offline. Do not modify the canonical
   `PILOT-008` workspaces.
7. Update status docs, simplify the final diff, commit, push, and verify CI.

## Completion gate

- a pinned profile cannot silently use another compatible compiler;
- existing unpinned profiles and digests are unchanged;
- the public and packaged schemas describe the additive fields;
- positive, negative, schema, CLI, and end-to-end tests pass;
- the private pinned replay matches the `PILOT-008` scan semantics;
- no target-specific detector behavior or target source enters the repository.

## Completion record

The public implementation added 13 interface and integration tests; the full
suite now passes 234 tests. Frozen synthetic evaluation remains 33/33 positive
and 31/31 safe labels, and the historical gate remains at 0.875 candidate
precision and 1.0 supported-class recall.

A new private offline Olas replay used the unchanged commit and exact two-file
reportable plus two-file compiler-only closure. Its profile and source manifest
used schema `1.2`, Foundry reported only Solidity `0.8.30`, the frozen source-set
and compiler-dependency-set identities matched `PILOT-008`, and the scan again
produced zero findings and zero candidates. No target source or candidate
evidence entered the repository, and no external target action occurred.
