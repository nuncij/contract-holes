# Output compatibility

Contract Holes 1.0 freezes two machine-facing producer contracts:

- JSON report schema `1.0`;
- SARIF `2.1.0` with the Contract Holes producer profile.

The packaged schemas are
[`report-1.0.schema.json`](../src/contract_holes/schemas/report-1.0.schema.json)
and
[`sarif-2.1.0-profile.schema.json`](../src/contract_holes/schemas/sarif-2.1.0-profile.schema.json).
They use JSON Schema draft 2020-12. Contract Holes also validates every JSON and
SARIF report before rendering it.

## JSON report 1.0

The root always contains `schema_version`, `files_scanned`, `finding_count`, and
`findings`. Baseline comparisons additionally contain `baseline` with `path`,
`new`, `existing`, and `resolved`.

Every finding contains:

| Field | Type | Meaning |
|---|---|---|
| `rule_id` | string | Stable `SOLnnn` detector ID |
| `severity` | enum | `info`, `low`, `medium`, `high`, or `critical` |
| `title`, `message` | string | Detector identity and evidence statement |
| `path` | string | Path exactly as represented by the scan input |
| `line`, `column` | positive integer | One-based start location |
| `end_line` | integer or null | Optional inclusive ending line |
| `excerpt` | string | Relevant source excerpt |
| `recommendation` | string | Suggested reviewer action |
| `confidence` | enum | `low`, `medium`, or `high` |
| `metadata` | object | Rule-specific deterministic evidence |
| `fingerprint` | string | Fingerprint-v1 identifier |

`finding_count` equals the length of `findings`; fingerprints are unique within
a report. Metadata keys are rule-specific and additive. Consumers must ignore
unknown metadata and root/finding fields.

Fingerprint v1 is the first 16 lowercase hexadecimal characters of SHA-256 over
the UTF-8 string `rule_id + NUL + path + NUL + decimal line + NUL + stripped
excerpt`. Because `path` is part of the material, raw report fingerprints can
change between relative and absolute scan inputs. Baseline files normalize paths
relative to the baseline directory for portable CI comparison.

## SARIF producer profile

SARIF output declares the standard schema URI and version `2.1.0`, contains one
run, and uses driver name `contract-holes`. Each result has one physical location,
the JSON finding message, categorical severity/confidence properties, and the
same fingerprint under `partialFingerprints.primaryLocationLineHash`.

SARIF levels map as follows:

| Contract Holes severity | SARIF level | `security-severity` score |
|---|---|---:|
| Critical | `error` | 9.0 |
| High | `error` | 8.0 |
| Medium | `warning` | 5.0 |
| Low | `note` | 3.0 |
| Info | `note` | 1.0 |

Rule-specific metadata is copied into result `properties`, but cannot override
the canonical `severity` or `confidence` fields.

## Versioning policy

Schema versions use `major.minor`:

- a minor version may add optional fields or enum-independent metadata;
- a major version is required to remove/rename a field, change a type or required
  field, change fingerprint material, or change existing severity semantics;
- fixes that only tighten producer validation without changing valid output do
  not change the schema version.

Consumers should require a supported major version, tolerate a newer minor
version, ignore unknown fields, and retain unknown rule IDs/metadata for display.
Ordering is deterministic for a fixed scan and path representation, but consumers
must use IDs and fingerprints rather than array position as identity.
