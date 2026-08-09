# Authorized end-to-end bounty pilot

The M7 pilot exercises the complete private workflow against a repository-owned
Solidity fixture. It is an integration and safety evaluation, not a live bounty
scan. The checked manifest is the operator-reviewed record: it pins the local
rules document, source content identity, allowed path, impact, restrictions,
review decisions, proof decision, report content, approval, and event timeline.

## Reproduce the pilot

Choose a new output directory outside the repository target and run:

```bash
holes bounty pilot tests/fixtures/bounty_pilot/manifest.json \
  --output ../private-bounty-pilot-run
```

The output directory must not already exist. Exit `0` means every pilot gate
passed, exit `1` is a completed failed gate, and exit `2` is a manifest or
workflow error. The checked, path-independent result is
[`evaluation/bounty-pilot-1.0.json`](../evaluation/bounty-pilot-1.0.json).

The command creates a mode-`0700` root on POSIX hosts containing:

```text
workspace/          private profile, scan, candidates, reviews, proof, report, approval
local-export/       report.md, report.json, approval.json, SHA256SUMS
report-input.json   frozen human-authored report material
pilot-result.json  non-confidential metrics and gate result
```

Files are mode `0600` where the host supports POSIX permissions. Existing
output is never overwritten. A failed run may leave a partial private directory
for diagnosis; inspect it locally and choose a different new path for a retry.

## What it exercises

The target intentionally produces two source-only candidates:

| Rule | Human decision | Reason |
| --- | --- | --- |
| `SOL001` | confirmed, then approved | `tx.origin` protects a counter update and permits an owner-originated intermediary call |
| `SOL002` | rejected | the ignored best-effort diagnostic call has no success-dependent or persistent state transition in the fixture |

The confirmed candidate receives an isolated proof bundle. Because Contract
Holes has no automatic `SOL001` generator, the result is explicitly
`unsupported`; the manifest retains the actors, local deployment requirement,
impact assertion, and human-authored reproduction instead of inventing proof.

The pilot then creates a complete private report. Before approval it deliberately
checks that local export is blocked. It also checks that approval without the
manual-submission acknowledgement is blocked. The pre-reviewed manifest contains
the separate human decision, reviewer, reason, and explicit acknowledgement;
only then does the evaluation record approval and create a local export.

This replay harness does not infer either review decision from scanner severity.
For real work, use the individual `candidates`, `review`, `proof`, `report`,
`approve`, and `export` commands so a person inspects each target-specific step.

## Frozen result

The `contract-holes-repository-pilot-1.0` result records:

| Measurement | Result |
| --- | ---: |
| Files scanned | 1 |
| Candidates investigated | 2 |
| Human confirmed / rejected | 1 / 1 |
| Locally approved reports | 1 |
| Automatic proofs generated / unsupported | 0 / 1 |
| Safety checks exercised / failures | 2 / 0 |
| Recorded operator timeline | 720 seconds |

The timeline is the frozen interval between operator events, not wall-clock
process performance. Friction is recorded explicitly: this rule needs manual
reproduction, report context needs human authorship, and export needs separate
approval. Result JSON contains hashes, counts, rule decisions, gate statuses,
and relative artifact names; it omits candidate IDs, report contents, and local
absolute paths so runs in different private directories are reproducible.

## Network and disclosure boundary

The pilot uses source-only scanning and an unsupported proof decision, so it
does not invoke Foundry or a local chain. It performs no socket connection,
remote RPC, mainnet/public-testnet transaction, target contact, platform API,
email, upload, disclosure, or submission. Tests replace Python socket creation
with a failure and still complete the entire workflow.

The reserved `example.test` rules URL is an identifier for this synthetic
evaluation; the checked `RULES.md` and its SHA-256 are the authoritative pilot
rules. The target has no deployment and no bounty eligibility. Any real report
must be reviewed under its actual program rules and submitted manually through
that program's private channel. Never replace this fixture with a third-party
target unless you have independently recorded authorization and accepted the
resulting confidentiality obligations.

The versioned input and output contracts are packaged as
`bounty-pilot-manifest-1.0.schema.json` and
`bounty-pilot-result-1.0.schema.json`.
