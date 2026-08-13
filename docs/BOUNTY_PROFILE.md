# Bounty workspace and profile

`holes bounty` manages a private, local research workspace for an explicitly
authorized target. The workspace is separate from the target checkout and is
ignored by Git by default. The tool does not submit reports, contact projects,
send transactions, or provide a remote-RPC command.

The profile contract is new in the `1.1` development line. It does not change
the frozen scanner JSON/SARIF `1.0` formats.

## Create a workspace

Review the program's current rules first. Record an exact target revision and
only the paths and impacts the program places in scope:

```bash
holes bounty init ../private-example-review \
  --program "Example Protocol" \
  --platform "Example Bounty" \
  --rules-url https://example.org/security/rules \
  --reviewed-on 2026-08-09 \
  --authorized \
  --authorization-note "Public program permits local source analysis" \
  --source ./example-protocol \
  --revision 0123456789abcdef0123456789abcdef01234567 \
  --scope contracts \
  --compiler-dependency lib/openzeppelin-contracts/contracts/access/Ownable.sol \
  --impact "Unauthorized withdrawal of user funds" \
  --restriction "No live-network testing"
```

The output directory must not exist and must be outside the target source tree.
The initializer creates `bounty.toml` with restrictive permissions where the
host supports them and a `.gitignore` that treats every workspace artifact as
private. It never overwrites an existing workspace.

For a non-Git source snapshot, replace `--revision` with the SHA-256 identity of
its deterministic source manifest:

```text
--content-sha256 HEX_DIGEST
```

Generate the non-Git identity with the local-only command:

```bash
holes bounty identify ./source-snapshot \
  --scope contracts \
  --compiler-dependency lib/openzeppelin-contracts/contracts/access/Ownable.sol
```

It hashes normalized relative Solidity paths, file bytes, and a safe
`remappings.txt` when present. Copy `source.source_set_sha256` into
`--content-sha256`; do not invent a digest from an archive with unstable
metadata.

Use repeatable `--compiler-dependency PATH` arguments only for Solidity source
units needed to compile the reportable files. These paths are immutable compiler
inputs, not reportable bounty assets. They cannot produce findings or candidates.
Do not use the option to enlarge scope; only the program's reviewed scope belongs
under `--scope`.

Compiler analysis is enabled and offline by default. `--source-only` records an
explicit source-only profile. Bounty profiles cannot enable online compiler
downloads.

Optional `--compiler-version X.Y.Z` binds one exact supported Solidity release
into a compiler-enabled profile:

```bash
holes bounty init ../private-example-review \
  ... --compiler-version 0.8.30
```

The value must be an exact `MAJOR.MINOR.PATCH` release inside the published
supported Solidity range (see [compatibility](COMPATIBILITY.md)); suffixes such
as `0.8.30+commit.a2be1a0c` and non-canonical spellings are rejected, and the
option is rejected with `--source-only`. The profile binds the compiler once;
validation, manifest binding, isolated Foundry configuration, and
observed-version verification all stay behind that single declaration. Optimizer
runs and EVM target are not part of the pin; Contract Holes consumes compiler
ASTs in a fixed isolated project and does not claim bytecode reproduction.

## Validate a profile

```bash
holes bounty validate ../private-example-review
```

Both `init` and `validate` emit a JSON envelope with schema version `1.0`, the
command, status, workspace, normalized profile, and `profile_sha256`. The digest
binds the normalized program, source identity, scope, authorization, and compiler
settings. It is an integrity identifier, not proof that the program currently
authorizes testing.

Status `0` means the profile is structurally valid. Status `2` means input,
schema, path, identity, or authorization validation failed. There is no
finding-gate status for these two commands.

## `bounty.toml` schema version 1

```toml
schema_version = 1

[program]
name = "Example Protocol"
platform = "Example Bounty"
rules_url = "https://example.org/security/rules"
reviewed_on = "2026-08-09"
authorization_acknowledged = true
authorization_note = "Public program permits local source analysis"

[source]
kind = "git"
root = "../example-protocol"
revision = "0123456789abcdef0123456789abcdef01234567"

[scope]
paths = ["contracts"]
impacts = ["Unauthorized withdrawal of user funds"]
restrictions = ["No live-network testing"]

[compiler]
enabled = true
dependency_paths = ["lib/openzeppelin-contracts/contracts/access/Ownable.sol"]
offline = true
version = "0.8.30"
```

All tables and keys are closed: unknown settings fail instead of being ignored.
Git revisions must be exact lowercase 40- or 64-hex object names. Directory
identities must be lowercase SHA-256 digests. Scope paths are normalized POSIX
paths relative to the target root; absolute paths, `..`, backslashes, empty
scope, and duplicates are rejected. At least one in-scope impact and a non-empty
authorization note are required.

`compiler.version` is optional and requires compiler mode. When present it is
stored as a canonical exact release; when absent the profile keeps legacy
auto-detection behavior byte-for-byte. A `compiler.version` without
`compiler.enabled = true` is rejected.

Compiler dependency paths use the same path rules. They must not overlap a
reportable source unit, require compiler mode, and are separately listed and
hashed. `--source-only` and compiler dependencies cannot be combined.

The source root is stored relative to the workspace for portability. The
resolved target must exist when loading a profile, and the workspace cannot be
inside that target.

The normalized representation is described by the packaged
`bounty-profile-1.0.schema.json`. Profiles with compiler-only dependencies use
the additive `bounty-profile-1.1.schema.json`. Pinned profiles use the additive
`bounty-profile-1.2.schema.json`, which describes `compiler.version`. Existing
profiles without a pin remain schema `1.0` (no dependencies) or `1.1`
(compiler-only dependencies) with unchanged digest material. TOML remains the
editable source of truth.

## Validate scope and scan

```bash
holes bounty scan ../private-example-review
```

For Git sources, `source.root` must be the worktree root, `HEAD` must equal the
exact approved commit, the object must be a commit, and tracked plus untracked
worktree state must be clean. Directory snapshots must reproduce the recorded
source-set digest. Missing files, changed bytes, non-Solidity scoped files,
absolute/traversing paths, symlinks, escaping remappings, and empty scopes fail
closed.

The command writes two private, deterministic records:

- `source-manifest.json` binds the profile, scanner, source identity, reportable
  and compiler-only relative paths, their separate byte counts and hashes,
  remappings, and compiler-isolation policy;
- `scan.json` binds that manifest to the relative-path scanner report and exact
  compiler policy/version observations.

Top-level finding paths and nested evidence fields named `path` are stored
relative to the approved target root. An absolute nested path outside that root
fails closed instead of being written.

Records use mode `0600` where supported, are created atomically, and are
accepted on a repeat run only when their complete bytes are identical. Changed
or symlinked records are never overwritten.

Source-only mode reads only reportable Solidity files. Compiler mode rechecks and
copies reportable plus explicitly declared compiler-only files into a temporary
project, writes a fixed safe
`foundry.toml`, carries forward only contained `remappings.txt` entries, runs
Foundry offline, and rejects build information containing any source unit or
literal bytes outside the declared sets. A pinned profile writes
`solc_version = "X.Y.Z"` instead of enabling auto-detection, and the run fails
closed unless the build reports one compiler release and it matches the pin. Only
reportable files are scanned; a
finding attributed to a compiler-only file fails the scan. The target's
`foundry.toml`, tests,
scripts, hooks, plugins, output, and cache are not loaded or executed.

Absolute paths, backslashes, URLs, and parent imports that escape the source root
or resolve to an undeclared file are rejected before Foundry starts. A contained
parent import is accepted only when its resolved source unit is explicitly
declared. A target needing unsafe or unsupported build behavior is reported as
an execution error; the bounty workflow does not weaken isolation to make it
compile.

Packaged schemas `bounty-source-manifest-1.0.schema.json`,
`bounty-source-manifest-1.1.schema.json`,
`bounty-source-manifest-1.2.schema.json`, and
`bounty-scan-1.0.schema.json` describe these records. Pinned profiles emit
source-manifest schema `1.2` with `compiler.version`; `scan.json` remains schema
`1.0` and records the compiler version strings observed in Foundry build
information. Status `0` means a complete
scan, including one with findings. Status `2` means profile, provenance, scope,
compiler, record-integrity, or execution failure; it is never a clean result.

## Trust boundary

The acknowledgement records an operator decision; Contract Holes cannot verify
legal authorization or determine whether the linked rules changed after the
recorded review date. Recheck the program rules before every scan, proof, report
approval, and manual submission. Keep the workspace private and follow the
[secure-use guide](SECURE_USE.md) and [M7 development plan](BOUNTY_HUNTER_PLAN.md).
