# CLI reference

The installed entry point is `holes`; `python -m contract_holes` is equivalent.
Run `holes --help` or `holes COMMAND --help` for the exact options shipped by the
installed version.

## Exit status and output streams

| Status | Meaning |
| ---: | --- |
| `0` | Command completed and no configured finding/metric gate fired |
| `1` | Command completed, but a finding, evaluation, or proof gate failed |
| `2` | Usage, configuration, input, compiler, network, or execution error |

Machine-readable command results go to standard output. Diagnostics, baseline
counts, and artifact-write notices go to standard error. Do not merge the streams
when consuming JSON or SARIF. A status `2` is never a clean scan.

## Scan

```text
holes [PATH ...] [OPTIONS]
```

Paths default to `scan.paths` in the selected `.holes.toml`. The main option
groups are:

| Purpose | Options |
| --- | --- |
| Configuration | `--config FILE`, `--no-config` |
| Reporting | `--format text|json|sarif`, `--minimum-severity LEVEL`, `--no-color` |
| Gate | `--fail-on LEVEL` |
| Baseline | `--baseline FILE`, `--write-baseline FILE`, `--update-baseline FILE` |
| Discovery | `--include-dependencies`, `--exclude-dependencies`, `--exclude GLOB` |
| Compiler | `--compile`, `--no-compile`, `--offline`, `--online` |
| Proof generation | `--generate-proofs DIRECTORY` (requires compiler mode) |
| Limits | `--max-files`, `--max-source-bytes`, `--compiler-timeout`, `--scan-timeout`, `--max-memory-mb` |

Severity values are `info`, `low`, `medium`, `high`, and `critical`. See
[configuration](CONFIGURATION.md), [baselines](BASELINES.md), [resource
limits](RESOURCE_LIMITS.md), and [output compatibility](OUTPUT_COMPATIBILITY.md)
for stable semantics.

## Commands

### `holes rules [RULE_ID]`

Print every detector or one detector. `--format text|json` selects reviewer or
machine output. Catalog entries include default severity/confidence, analysis
mode, examples, remediation, manual-review limits, and references. See the
[rule catalog](RULE_CATALOG.md).

### `holes inspect PATH [PATH ...]`

Compile and emit the deterministic project index, inheritance, calls, and
data-flow state as JSON. `--file`, `--contract`, and `--function` are repeatable
filters. `--include-dependencies` expands discovery and `--offline` blocks compiler
downloads. Inspection always requires Foundry.

### `holes benchmark PATH [PATH ...]`

Measure source-only and compiler-aware correctness, duration, and Python peak
allocation. `--expectations FILE` selects finding-count expectations;
`--baseline FILE` adds an informational timing comparison.
`--include-dependencies` and `--offline` control discovery/compiler behavior.
Timing changes do not fail the command; correctness mismatches do.

### `holes evaluate MANIFEST`

Run a labelled corpus and report per-rule/aggregate precision and recall as JSON.
It is offline by default; `--allow-downloads` permits the pinned compiler to be
installed. See [evaluation](EVALUATION.md).

### `holes proofs DIRECTORY`

Validate and execute generated `.proof.json`/`.t.sol` pairs in isolated temporary
Foundry projects. `--timeout SECONDS` is per artifact; `--allow-downloads` opts out
of the offline default. See [proof requirements](PROOF_REQUIREMENTS.md) and the
[secure-use guide](SECURE_USE.md#proof-execution).

### `holes fetch CHAIN_ID ADDRESS --output DIRECTORY`

Fetch public verified Solidity through Etherscan V2 into a new directory.
`--api-key-env NAME` selects the API-key variable and `--timeout SECONDS` bounds
the request. It never overwrites an existing directory. See
[verified-source ingestion](VERIFIED_SOURCE.md).

### `holes explain REPORT`

Correlate deterministic JSON findings and optionally request evidence-bound AI
annotations. `--prepare` performs no network request. Online mode accepts
`--model`, `--api-key-env`, and `--timeout`; model text remains untrusted and
cannot change findings or gates. See [AI triage](AI_TRIAGE.md).

### `holes compatibility`

Emit the versioned compatibility policy and locally observed Python, Forge, and
solc status as JSON. Missing optional compiler tools do not fail this informational
command. See [toolchain compatibility](COMPATIBILITY.md).

### `holes bounty init|validate|identify|scan`

Create or validate a private, human-approved bounty research workspace. `init`
requires program identity, an HTTPS rules URL and review date, explicit
authorization acknowledgement, a local source, an immutable Git revision or
directory-manifest digest, in-scope paths, and in-scope impacts. Compiler mode is
offline by default; `--source-only` disables it. `validate` emits the normalized
profile and its SHA-256 identity.

The workspace must be new and outside the target tree. These commands do not
submit, upload, send transactions, or contact a remote RPC endpoint.
`identify SOURCE --scope PATH` computes a local deterministic source-set digest.
`scan WORKSPACE` validates an exact clean Git commit or directory digest,
enforces approved paths and symlink/remapping boundaries, stages only approved
source, compiles offline under fixed configuration when enabled, and writes
private source/scan records. See the [bounty profile contract](BOUNTY_PROFILE.md).

## Configuration precedence

An explicit CLI setting wins over the selected/discovered `.holes.toml`, which
wins over built-in defaults. Only the main scan command discovers project
configuration; subcommands keep explicit inputs. Unknown flags or contradictory
options are errors rather than silently ignored values.
