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
a report. If a detector produces alternative evidence with the same fingerprint,
the producer keeps the first representative in deterministic finding order.
Metadata keys are rule-specific and additive. Consumers must ignore unknown
metadata and root/finding fields.

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

## 1.1 bounty records and 1.0 migration

Contract Holes 1.1 does not change the ordinary scanner JSON `1.0` or SARIF
producer contract. Existing 1.0 scan consumers, baselines, fingerprints, and CI
gates continue to use the same fields and semantics. Upgrading the package does
not rewrite an existing report or baseline.

Bounty workspaces introduce separate, explicitly versioned private record
families. Their packaged schemas cover profiles, source manifests, scans,
candidates, reviews, proofs/results, reports/inputs, approvals, historical
evaluation, and the authorized pilot. These records are not additions to the
ordinary report schema and must not be sent to a generic 1.0 report consumer.

The initial bounty record versions are `1.0`, independently of package version
`1.1.0`. Profiles and source manifests that declare compiler-only dependencies
use additive schema `1.1`; profiles and source manifests that pin an exact
compiler release use additive schema `1.2`. Records without those features
remain `1.0` with unchanged digest material. The scan record remains `1.0`.
Their compatibility policy is:

- an additive optional field requires a record-schema minor version;
- removing, renaming, or changing a required field or digest definition requires
  a record-schema major version;
- immutable records keep their original schema version and digest material;
- a managed workspace record is never silently migrated or rewritten;
- a newer scanner may create different candidate IDs because the scanner version
  is deliberately part of candidate identity, while the old observation remains
  attributable to its original source and scanner hashes.

There was no released bounty workspace in package 1.0, so no automatic data
migration is needed. Users of an M7 development checkout should keep the original
private workspace as evidence and create a new workspace when source, profile,
scanner version, or a record-schema major changes. Never hand-edit hashes to make
an old workspace appear current.
