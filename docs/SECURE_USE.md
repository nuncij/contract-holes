# Secure-use guide

## Before scanning

1. Confirm authorization for the source, deployed address, network requests, and
   any generated test activity.
2. Install Contract Holes, Python, Foundry, solc, and CI actions from reviewed
   sources. Pin releases or immutable commits and compare them with the
   [compatibility policy](COMPATIBILITY.md).
3. Treat a repository you did not create as hostile. Start with source-only mode
   in a disposable, least-privilege workspace.
4. Review `.holes.toml`, `foundry.toml`, imports/remappings, suppressions,
   baselines, and CI changes before enabling compiler mode.

Never expose a wallet seed, private key, production signer, cloud credential, or
privileged RPC credential to the scanner process. Contract Holes strips common
credential variables from native child processes as defense in depth, but no
name-based filter can identify every secret.

## Source-only versus compiler mode

Use source-only mode for first contact with untrusted code:

```bash
holes contracts --no-compile --format json > holes.json
```

Compiler-backed rules provide much stronger type, inheritance, call, and data
flow evidence. Run them only after reviewing the project configuration, ideally
inside an ephemeral container or VM with:

- no mounted home directory, SSH agent, wallet, Docker socket, or cloud config;
- read-only source plus a separate temporary filesystem;
- no secrets in environment variables;
- CPU, total RSS, process-count, disk, and wall-time limits enforced by the OS;
- network disabled after supported compiler versions are preinstalled.

```bash
holes contracts --compile --offline --format sarif > holes.sarif
```

The scanner's temporary Forge output/cache prevents repository pollution. It is
not a container: Forge, a configured custom compiler, and downloaded solc binaries
are native processes with the caller's permissions. `--scan-timeout`,
`--compiler-timeout`, and `--max-memory-mb` do not replace OS limits for child
processes.

## Networked commands

Normal source-only scans do not use the network. Network can occur when:

- compiler mode is online and Foundry downloads solc;
- `holes fetch` calls Etherscan with its API key, chain ID, and address;
- online `holes explain` sends finding evidence to OpenAI;
- `holes proofs --allow-downloads` fetches a compiler.

Prefer offline mode and preinstalled checksummed compilers in CI. Use scoped,
short-lived API credentials. Run `holes explain REPORT --prepare` and inspect the
bundle before authorizing an online explanation; report excerpts and paths may be
confidential even though full source files are not uploaded.

Fetched source is provider data, not verified bytecode equivalence. Independently
obtain deployed bytecode and proxy implementation details before treating it as
the audited source set.

## Findings, suppressions, and baselines

- Treat every finding as a review lead. Confirm reachability, attacker control,
  deployment/fork semantics, existing guards, and impact manually.
- Treat a clean scan as “no supported signal found,” never “safe.” Run tests,
  independent tools, and expert review appropriate to the value at risk.
- Require a reason and security-owner review for `holes-ignore` comments,
  disabled rules, reduced severities, exclusions, and baseline updates.
- Review resolved baseline entries; disappearance may mean a fix, moved code,
  changed paths, or lost analysis coverage.
- Keep execution errors distinct from findings. Exit `0` is a completed gate,
  `1` is a completed scan that met `--fail-on`, and `2` is an invalid or failed
  execution that must never be treated as clean.

JSON, SARIF, benchmark, inspection, AI, and proof-runner output can contain local
paths, excerpts, compiler diagnostics, and protocol metadata. Apply the same
access controls and retention policy as the source repository. Sanitize artifacts
before attaching them to public issues.

## Proof execution

Generate into a new directory, review each `.t.sol` and `.proof.json`, and commit
both if they become audit evidence. The runner verifies that each source matches
its manifest and rejects compiler-version injection, but an attacker who changes
both files can create a new matching pair.

Run proofs on a local ephemeral chain with test accounts and valueless assets.
Generated tests prove only a vulnerability primitive; project deployment, roles,
funding, actors, fork/block, calldata, and invariants must be configured and
reviewed. Do not connect automatic proofs to production RPC endpoints or signers.

## CI checklist

- Pin the scanner package/commit, Python, Foundry, solc, and action commits.
- Use read-only checkout credentials and the minimum SARIF permission.
- Keep untrusted pull requests away from repository and environment secrets.
- Make compiler downloads explicit; use an approved mirror/cache where required.
- Enforce an OS/job timeout in addition to scanner limits.
- Upload SARIF only for exit `0` or `1`, then restore the finding gate status.
- Review every baseline, suppression, rule/configuration, and workflow change.
- Retain enough version/provenance output to reproduce the scan.

Use [`holes compatibility`](COMPATIBILITY.md#inspect-the-current-host) to capture
the host toolchain and follow [SECURITY.md](../SECURITY.md) for private reporting.
