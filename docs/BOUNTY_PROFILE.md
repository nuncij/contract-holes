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

Manifest construction and byte-level scope validation are implemented by
`BOUNTY-002`; do not invent this digest by hashing an archive with unstable
metadata.

Compiler analysis is enabled and offline by default. `--source-only` records an
explicit source-only profile. Bounty profiles cannot enable online compiler
downloads.

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
offline = true
```

All tables and keys are closed: unknown settings fail instead of being ignored.
Git revisions must be exact lowercase 40- or 64-hex object names. Directory
identities must be lowercase SHA-256 digests. Scope paths are normalized POSIX
paths relative to the target root; absolute paths, `..`, backslashes, empty
scope, and duplicates are rejected. At least one in-scope impact and a non-empty
authorization note are required.

The source root is stored relative to the workspace for portability. The
resolved target must exist when loading a profile, and the workspace cannot be
inside that target.

The normalized representation is described by the packaged
`bounty-profile-1.0.schema.json`. TOML remains the editable source of truth.

## Trust boundary

The acknowledgement records an operator decision; Contract Holes cannot verify
legal authorization or determine whether the linked rules changed after the
recorded review date. Recheck the program rules before every scan, proof, report
approval, and manual submission. Keep the workspace private and follow the
[secure-use guide](SECURE_USE.md) and [M7 development plan](BOUNTY_HUNTER_PLAN.md).
