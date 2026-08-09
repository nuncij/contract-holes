# Bounty proofs, reports, approval, and export

The final local workflow turns one review candidate into hash-bound evidence and
a private report. Every action remains local. Contract Holes has no submission,
email, project-contact, wallet, transaction, or remote-RPC operation.

## Create a proof bundle

```bash
holes bounty proof PRIVATE_WORKSPACE BNT-... \
  --requirement "actors=unprivileged caller and victim" \
  --requirement "deployment=local deployment at known initial state" \
  --impact-assertion "Unauthorized state transition" \
  --run
```

Allowed requirement names are `actors`, `balances`, `calldata`, `constructor`,
`deployment`, `invariant`, `oracle`, and `timing`. Unspecified requirements stay
explicitly `unknown`. Credential-like values are rejected.

The immutable proof directory is addressed by `proof_sha256`. Its manifest binds
the profile, source manifest, candidate observation, finding, generated files,
setup requirements, impact assertion, compiler requirement manifests, and local
offline execution policy. Generated files use restrictive permissions and their
hashes are rechecked before later use.

Only rules with an existing Contract Holes generator receive automatic Foundry
tests. Other candidates produce an `unsupported` bundle that records the missing
automation instead of inventing a PoC. `--run` executes supported generated
tests through the isolated proof runner with downloads disabled. Failure,
timeout, unsupported setup, and inconclusive/manual work cannot confirm a
candidate automatically.

A passed primitive test is not proof of protocol impact. Deployment, actor,
funding, oracle, timing, calldata, and invariant assumptions must be supplied and
reviewed separately.

## Author the report input

A complete report uses a reviewer-authored JSON file matching packaged schema
`bounty-report-input-1.0.schema.json`:

```json
{
  "summary": "An unprivileged caller can reach the protected action.",
  "technical_details": "Explain the exact source and execution path.",
  "preconditions": ["List every required state and actor assumption."],
  "reproduction_steps": ["Deploy locally.", "Execute the reviewed call sequence."],
  "remediation": "Describe a concrete code or invariant correction.",
  "limitations": ["State what the reproduction does not establish."],
  "unresolved_questions": ["List remaining deployment or duplicate questions."],
  "duplicate_check": "Record which public issues, audits, and program notes were checked.",
  "proof_status_explanation": "Explain the passed, failed, manual, or unsupported PoC status.",
  "program_rules_rechecked_on": "2026-08-09"
}
```

Secrets, credential-bearing URLs, private workspace paths, unknown fields,
missing sections, oversized content, and future rule-review dates are rejected.

## Create a private report

```bash
holes bounty report PRIVATE_WORKSPACE BNT-... \
  --input report-input.json \
  --proof-sha PROOF_SHA256
```

Without `--input`, the command still creates an immutable report, but labels it
`draft-incomplete` and `review-hypothesis`. A report is `complete` only when:

- the candidate is explicitly human-confirmed with an in-scope impact;
- summary, technical details, preconditions, reproduction, remediation, and
  limitations are complete;
- duplicate and current-program-rule checks are recorded;
- proof status is explicitly addressed, whether automatic, manual, failed, or
  unsupported;
- current source scope and every candidate/review/proof digest still match.

Private JSON and Markdown live under a content-addressed report directory.
Changing source, candidate observations, review state, or a bound proof makes
the prior report stale rather than silently updating it.

## Approve

```bash
holes bounty approve PRIVATE_WORKSPACE BNT-... \
  --report-sha REPORT_SHA256 \
  --reviewer "Nunc" \
  --reason "Scope, impact, reproduction, and report reviewed" \
  --rules-rechecked-on 2026-08-09 \
  --acknowledge-manual-submission
```

Approval revalidates immutable source scope, requires the candidate to remain
confirmed, requires the complete report to match current review state, checks
the program-rule date, and records a separate hash-bound approval. The candidate
then enters terminal `approved` state. Approval is local evidence only. It does
not contact a project or authorize Contract Holes to submit anything.

## Export locally

```bash
holes bounty export PRIVATE_WORKSPACE BNT-... \
  --report-sha REPORT_SHA256 \
  --output ../private-export
```

The output must be a new directory outside both target and workspace. Export
requires the current approved review and matching approval record, rechecks
source identity, redacts credentials/private paths as defense in depth, and
writes `report.md`, `report.json`, `approval.json`, and `SHA256SUMS` atomically.

The result says `submitted: false` and `network_action: false`. The operator must
read the selected program rules again and manually use its required private
channel. Do not publish exported material unless coordinated-disclosure rules
explicitly allow it.
