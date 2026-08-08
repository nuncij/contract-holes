# Configuration

The main `holes` scan command discovers the nearest `.holes.toml` from the
working directory upward. Use `--config FILE` to select a specific file or
`--no-config` to use CLI values and built-in defaults only. Inspection,
benchmark, and proof-runner subcommands keep their explicit command-line inputs.

## Schema

```toml
schema_version = 1

[scan]
paths = ["src", "contracts"]
exclude = ["mocks/**", "*.generated.sol"]
include_dependencies = false
minimum_severity = "medium"

[rules]
enabled = ["SOL001", "SOL002", "SOL005"]

[rules.severity]
SOL005 = "critical"

[compiler]
enabled = true
offline = true

[limits]
max_files = 5000
max_source_bytes = 104857600
compiler_timeout_seconds = 120
scan_timeout_seconds = 300
max_python_memory_mb = 1024
```

All sections and keys are optional. `schema_version` defaults to `1` when
omitted. Paths are resolved relative to the configuration file. Exclusion globs
match paths relative to each scan root and also match individual filenames.

`rules.enabled` limits the active rules; if omitted, every registered rule is
enabled. `rules.disabled` is then removed from that set. The same rule cannot
appear in both lists. Severity values are `info`, `low`, `medium`, `high`, or
`critical`. Overrides affect filtering, reports, SARIF rule metadata, and CI
thresholds.

`compiler.offline = true` requires `compiler.enabled = true`. Compiler mode uses
the isolated Foundry build and enables compiler-backed rules.

The `[limits]` table controls finite file-count, total-source-size, compilation,
total-time, and Python-memory boundaries. All values are positive;
`compiler_timeout_seconds` cannot exceed `scan_timeout_seconds`. See
[Resource limits](RESOURCE_LIMITS.md) for enforcement details and diagnostics.

## Precedence

For settings that have a command-line equivalent, precedence is:

1. an explicit CLI value;
2. the selected or discovered `.holes.toml` value;
3. the built-in default.

CLI paths replace `scan.paths`. One or more `--exclude` values replace the
configured exclusion list. `--include-dependencies` and
`--exclude-dependencies`, `--compile` and `--no-compile`, and `--offline` and
`--online` are explicit pairs. Disabling compilation also disables inherited
offline mode unless `--offline` was explicitly supplied, which is rejected as a
contradiction.

Unknown tables, keys, rule IDs, invalid severities, duplicate list entries, and
type errors exit with status 2. They are never silently ignored.
