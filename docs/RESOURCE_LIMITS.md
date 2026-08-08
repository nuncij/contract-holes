# Resource limits

Every normal scan has finite resource limits. The defaults are intentionally
large enough for ordinary repositories while preventing an accidental scan of
an unbounded source tree or a compiler process that never returns.

| Resource | Default | Configuration key | CLI override |
|---|---:|---|---|
| Solidity files | 5,000 | `limits.max_files` | `--max-files` |
| Total source size | 100 MiB | `limits.max_source_bytes` | `--max-source-bytes` |
| Foundry compilation | 120 seconds | `limits.compiler_timeout_seconds` | `--compiler-timeout` |
| Total scan | 300 seconds | `limits.scan_timeout_seconds` | `--scan-timeout` |
| Python allocated memory | 1,024 MiB | `limits.max_python_memory_mb` | `--max-memory-mb` |

Example:

```toml
[limits]
max_files = 2000
max_source_bytes = 52428800
compiler_timeout_seconds = 90
scan_timeout_seconds = 180
max_python_memory_mb = 512
```

All values must be positive. The compiler timeout cannot exceed the total scan
timeout. Explicit command-line values override configuration values.

File count is enforced during discovery and source bytes are checked before
source contents are loaded. Foundry compilation has a hard subprocess timeout.
The total scan timeout is cooperative: it is checked after discovery, sizing,
compilation, project indexing, and each source file, so a single detector call
cannot be interrupted halfway through. The memory limit is the peak Python
allocation attributable to the scan as reported by `tracemalloc`; it does not
measure Foundry's child-process RSS or native allocations.

Limit failures exit with status 2 and include a stable diagnostic category:
`[files]`, `[source-bytes]`, `[compiler-time]`, `[scan-time]`, or
`[python-memory]`. These are execution errors, not security findings, and must
not be treated as a clean scan.
