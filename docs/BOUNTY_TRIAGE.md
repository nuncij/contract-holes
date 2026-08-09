# Bounty candidate triage

`holes bounty scan WORKSPACE` creates immutable candidate observations after a
successful pinned-scope scan. Candidate evidence and human decisions are stored
separately:

- `candidates.json` contains stable scanner observations and scan appearances;
- `reviews.json` contains explicit reviewer state transitions and reasoning.

Both are private, hash-bound, versioned `1.0` records. A changed or invalid
integrity digest stops the workflow. Scanner, profile, source-manifest, rule, and
finding identities are included in every `BNT-` candidate ID.

## List and prioritize

```bash
holes bounty candidates PRIVATE_WORKSPACE
holes bounty candidates PRIVATE_WORKSPACE --state investigating
```

The output combines observations with current review state and orders them by a
deterministic review-priority score. Every score includes its component points
and reason codes:

- detector severity: 0–50 points;
- detector confidence: 0–20 points;
- labelled/compiler/trace evidence: up to 20 points;
- explicit entry/trace reachability: up to 10 points;
- an existing Contract Holes proof generator: 5 points;
- total: capped at 100, with the candidate ID as deterministic tie-breaker.

The profile's in-scope impacts are displayed for reviewer context but never
change the score. The score means review ordering only. It does not establish
exploitability, bounty severity, uniqueness, expected payout, confirmation, or
submission readiness. Missing evidence remains visible and cannot be converted
into a safe result.

## Review states

New candidates begin in the derived `new` state without a human review record.
Record a decision explicitly:

```bash
holes bounty review PRIVATE_WORKSPACE BNT-... \
  --state investigating \
  --reason "Trace authorization and deployed reachability" \
  --reviewer "Nunc"

holes bounty review PRIVATE_WORKSPACE BNT-... \
  --state confirmed \
  --reason "Local reproduction demonstrates the unauthorized action" \
  --impact "Unauthorized withdrawal of user funds" \
  --reviewer "Nunc"
```

`--at RFC3339` may record an externally documented event time; otherwise the
command uses current UTC. Events must be strictly later than prior events.

Allowed transitions are:

```text
new -> investigating | rejected
investigating -> rejected | confirmed
rejected -> investigating
confirmed -> investigating | rejected | approved
approved -> terminal
```

`rejected` requires a reason. `confirmed` requires both reasoning and a concrete
in-scope impact statement. The generic review command cannot enter `approved`;
that state belongs to the later report/checklist workflow, which must revalidate
scope and bind a complete report.

Re-scanning identical inputs reproduces observations and preserves review
history. Synchronization can add new candidates or mark absent candidates
inactive without deleting their observations or reviews. It refuses to mutate
the observation attached to an existing stable ID.

Neither ranking, proof output, AI prose, scanner severity, nor a successful
command can transition a candidate automatically. Human reviewers remain
responsible for scope, reachability, impact, duplication checks, proof quality,
program rules, confidentiality, and any later manual submission.
