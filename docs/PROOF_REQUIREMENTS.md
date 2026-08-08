# Proof Requirements Manifests

Every artifact written by `--generate-proofs` has two files with the same stem:

- `<stem>.t.sol` contains the standalone Foundry test and reusable harnesses;
- `<stem>.proof.json` records provenance and execution requirements.

The manifest schema is versioned independently from the package. Both files are
deterministic, and generation refuses to overwrite either file after it has been
changed.

## Profiles

`profiles.generated_tests` describes the checked-in artifact as generated. It
records the tested solc version and pragma, local or fork chain mode, constructor
requirements, setup steps, and generated test names. A `runnable` status means
the standalone model can run without project deployment; it does not mean the
scanner reproduced impact against the scanned contract.

`profiles.project_probe` describes what remains before using the reusable probe
against the real target. For `SOL005`, its initial status is
`configuration-required`. Unknown values are JSON `null`, not defaults:

- target solc and EVM settings;
- local chain or an authorized fork, chain ID, RPC source, and pinned block;
- target constructor arguments;
- deployment and initialization;
- target/probe funding;
- actors and authorization state;
- entry and reentry calldata;
- a protocol-specific invariant.

`SOL007` is a standalone primitive proof, so its project-probe profile is
`not-applicable`.

## Minimal shape

```json
{
  "schema_version": "1.0",
  "artifact_version": "1.0",
  "artifact_kind": "reentrancy-probe-sequence-invariant",
  "proof_source": "Vault_SOL005_18_<fingerprint>.t.sol",
  "proof_sha256": "<sha256>",
  "finding": {
    "rule_id": "SOL005",
    "fingerprint": "<fingerprint>",
    "evidence": "compiler-interprocedural-data-flow"
  },
  "profiles": {
    "generated_tests": {
      "status": "runnable",
      "compiler": {"solc_version": "0.8.25", "offline": true},
      "chain": {"mode": "local", "fork_url": null}
    },
    "project_probe": {
      "status": "configuration-required",
      "constructor": {"contract": "Vault", "arguments": null},
      "setup": []
    }
  }
}
```

## Isolated execution

Run every bundle in a directory with:

```bash
holes proofs test/holes --timeout 60
```

The runner rejects a changed source hash, unsupported schema, missing source, or
unsafe source path. Each artifact is copied into a separate temporary Foundry
project and compiled with the manifest's solc version. Offline mode is the
default; `--allow-downloads` is explicit. The JSON result distinguishes proof
failure, timeout, unsupported requirements, and runner configuration errors.
Foundry and RPC environment overrides are removed, and the input directory is
not used for cache or build output.

Do not commit RPC credentials in a manifest. Store a non-secret environment
variable name or local runner configuration when fork execution is added. Pin a
fork block so a proof remains reproducible, and run probes only against systems
you are authorized to assess.
