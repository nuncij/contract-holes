# Threat model

## Purpose and security claims

Contract Holes turns Solidity source and optional compiler evidence into review
signals. Its security goals are to preserve input provenance, keep deterministic
findings and gates stable, limit accidental writes and resource use, and make
external-data boundaries visible.

It does **not** prove that a contract is safe, prove exploitability, emulate a
deployed chain, verify fetched source against runtime bytecode, or sandbox native
toolchain processes. Findings are evidence for a human review; absence of a
finding is not evidence of absence.

## Assets

The model protects:

- contract source, local paths, findings, traces, baselines, and proof inputs;
- developer and CI workspaces, credentials, signing material, and network access;
- the integrity of scanner exit codes, fingerprints, JSON/SARIF, and generated
  proof requirements;
- provenance for fetched source and evidence references in AI annotations;
- downstream reviewers from claims stronger than the collected evidence.

Private keys and production funds are never valid scanner inputs. They remain
out of scope because no scan or generated proof should require them.

## Actors and assumptions

An attacker may control Solidity files, imports, directory names, comments,
suppressions, `.holes.toml`, `foundry.toml`, proof manifests, baseline files,
explorer responses, or AI model output. They may try to exhaust CPU/memory/disk,
escape output paths, hide findings, inject tool configuration, disclose secrets,
or make CI treat an execution error as a clean scan.

The operating system, Python interpreter, installed Contract Holes package, and
pinned native toolchain are trusted. A compromised Python, Forge, solc, action,
package index, or runner is outside the process-level protections in this
repository. HTTPS and the configured external services are trusted for transport;
their returned data is still treated as untrusted.

## Trust boundaries

### Source-only scanning

Source files and configuration are untrusted data read by Python. Comment/string
masking, strict configuration keys, path exclusions, source-size/file-count,
scan-time, and Python-allocation limits reduce accidental interpretation and
denial of service. The scanner does not execute Solidity in source-only mode.

Residual risks: Python/native-library defects, filesystem races, very costly
inputs below configured limits, and missed or misleading findings. Memory limits
cover traced Python allocations, not total process RSS.

### Foundry and compiler mode

`--compile`, `holes inspect`, `holes evaluate`, and compiler-aware benchmarks
start Forge. Build output and cache paths are temporary, and a timeout is
enforced, so the target repository is not used for generated artifacts.
Common credential environment variables are removed before Forge starts.

This is artifact isolation, not a security sandbox. Forge reads project
configuration and can select/download a native compiler; a hostile repository
or compromised compiler may execute code with the scanner user's OS permissions,
read accessible files, consume child-process memory, or use allowed network
access. Offline mode prevents compiler downloads but does not make an installed
compiler trustworthy.

### Generated proofs

Generation refuses to overwrite changed artifacts and writes a requirements
manifest. The runner verifies the proof-source SHA-256, accepts only an exact
supported solc release, creates a fresh local Foundry project, removes Foundry,
RPC, and common credential environment variables, disables implicit project
configuration, and applies a timeout. Downloads are off unless explicitly
enabled.

The digest proves only that source matches its adjacent manifest; an attacker
who can alter both can replace the bundle. Only generated or reviewed bundles
are trusted inputs. Forge and solc remain native trusted processes, and generated
primitive tests do not establish protocol impact.

### Verified-source ingestion

`holes fetch` sends an API key, chain ID, and address to Etherscan. Response size,
JSON shape, compiler type, filenames, traversal, duplicates, and overwrite
behavior are validated. Files and hashes record exactly what the provider
returned.

Etherscan is not an independent truth source. Contract Holes does not compare the
source with deployed runtime bytecode, resolve a proxy automatically, or confirm
the chain/address independently. A provider compromise can return plausible but
incorrect source within the accepted format.

### AI explanation

Online `holes explain` sends report excerpts, locations, messages, and metadata
to OpenAI. Strict output shape plus local group/evidence validation prevents the
model from adding findings or evidence links. Model text remains explicitly
untrusted and cannot affect exit status, baselines, SARIF, or proof generation.

Residual risks are disclosure of sensitive report content and persuasive but
wrong prose within an allowed annotation. `--prepare` is the offline boundary.

### Bounty workspaces and scoped compilation

`holes bounty` requires a private mode-`0700` workspace, mode-`0600` profile,
explicit authorization acknowledgement, immutable source identity, and
default-deny relative scope. Git profiles require the exact clean worktree
commit. Directory profiles bind normalized Solidity bytes and safe remappings.
Source manifests and scan records use deterministic hashes, atomic creation, and
refuse changed or symlinked files.

Compiler-enabled bounty scans do not load the target `foundry.toml`. Approved
source is copied into a temporary project with fixed local configuration,
offline compilation, no tests/scripts, `ffi = false`, a scrubbed Git/Foundry/RPC/
wallet/cloud/CI environment, and contained remappings. Absolute, traversing,
URL, or backslash imports are rejected before Forge runs. Compiler build-info
must contain the exact approved literal bytes and no extra source unit.

This remains native compilation, not a process sandbox. A compromised Forge or
installed solc can access the host, and source-only filesystem reads retain
TOCTOU risk against an attacker who can modify approved files concurrently.
Use a disposable OS/container boundary with no secrets or network. Profile
acknowledgement records a human decision; it does not prove legal authorization
or that linked program rules remain current.

Candidate proof manifests bind generated bytes, supplied setup, and an impact
assertion separately. Execution uses the existing isolated local proof runner;
unsupported or failed execution remains non-confirming. Reports bind profile,
source, candidate, review, and proof digests. Approval requires a complete
human-confirmed report and current scope; export writes a new local directory
with redaction and checksums. There is no submission transport.

Residual risks include a reviewer entering false impact/reproduction claims,
credentials not matched by name-based redaction, malicious text in Markdown,
duplicate or out-of-scope reports, native toolchain compromise, and disclosure
after the local export leaves the workspace. Hashes show which local inputs were
used; they do not attest truth, exploitability, ownership, or program acceptance.

The historical gate hashes local reductions and records immutable upstream
identities without downloading them at evaluation time. This removes live-source
drift and third-party code redistribution from the test path, but reductions can
omit material protocol behavior. Calibration and holdout separation, frozen
supported/out-of-model labels, raw rejected candidates, and an explicit no-go
state limit score tuning. The result remains evidence about these ten reductions,
not a population-wide accuracy or bounty-income claim.

### Reports, baselines, suppressions, and CI

Reports may contain source excerpts and local paths. A baseline can hide an
unchanged fingerprint from a new-finding gate, and source comments can suppress
rules. Both are policy inputs that require code review. Fingerprints are stable
identifiers, not cryptographic attestations of safety.

Finding exits (`1`) and execution/configuration errors (`2`) are distinct. CI
must preserve that distinction and upload SARIF only when a valid report exists.
The example does this, but action tags, package sources, runners, and artifact
retention remain supply-chain/operations responsibilities.

## Abuse cases and controls

| Abuse case | Current control | Residual action |
| --- | --- | --- |
| Source path escapes fetch output | normalized relative paths, staging, refuse overwrite | review provenance before use |
| Huge source/API/compiler run | byte/file/response/time/Python-memory limits | add OS/container CPU, RSS, disk, and network limits |
| Secret reaches optional subprocess | common credential variables removed | use a secret-free least-privilege runner |
| Manifest injects Foundry config | exact supported solc release validation | review/hash the complete bundle |
| AI invents evidence | fixed groups and local evidence-ID validation | treat all model prose as untrusted |
| Baseline/suppression hides issue | explicit checked-in policy inputs | require security-owner review |
| Explorer returns wrong source | provider provenance and content hashes | compare bytecode independently |
| Bounty scope/import escapes target | normalized paths, no symlinks/traversal, staged approved sources | run in a disposable read-only target mount |
| Private bounty record is replaced | private permissions, hashes, atomic create/refuse overwrite | restrict workspace access and review digests |
| Toolchain/package compromise | documented pins and compatibility matrix | use immutable hashes, trusted registry, and provenance |

## Out of scope

- vulnerabilities in a scanned contract or third-party service by themselves;
- chain consensus, RPC correctness, bridge/oracle operation, or key custody;
- social engineering and malicious use by an already authorized OS user;
- complete availability against untrusted native compilers without an external
  sandbox;
- accuracy for Solidity, Foundry, Python, or EVM versions outside the published
  [compatibility policy](COMPATIBILITY.md).

Revisit this model whenever a command adds network access, native execution,
automatic deployment, new output writes, credential handling, or a schema/gate
that downstream automation trusts.
