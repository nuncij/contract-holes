# Security policy

## Supported versions

Until 1.0.0 is released, security fixes are made on `main`; pre-1.0 snapshots do
not receive separate maintenance releases. After 1.0.0, the latest 1.x release
and `main` receive security fixes. Unsupported versions should be upgraded before
a report is investigated.

| Version | Security fixes |
| --- | --- |
| `main` | Yes |
| Latest `1.x` after release | Yes |
| `0.x` snapshots | No separate backports |

## Report a vulnerability privately

Use the canonical repository's **Security → Advisories → Report a
vulnerability** form. This is the preferred channel because it keeps the report,
discussion, and any patch private until coordinated disclosure.

If private vulnerability reporting is unavailable, ask the repository owner for
a private maintainer contact without including vulnerability details. Do not put
an undisclosed vulnerability, exploit, confidential contract source, credentials,
or deployment secrets in a public issue.

Include:

- affected Contract Holes version or commit;
- impact and the trust boundary crossed;
- minimal reproduction steps or a sanitized fixture;
- whether the issue is already public or actively exploited;
- any suggested mitigation, if known.

Encrypt attachments using the key offered by the private reporting channel when
one is available. Never send live private keys, seed phrases, API keys, or
proprietary contracts that you are not authorized to share.

## Response and disclosure targets

Maintainers aim to acknowledge a complete report within three business days,
provide an initial severity/impact assessment within seven business days, and
send progress updates at least every 14 days while remediation is active. These
are response targets, not guaranteed fix deadlines.

The reporter and maintainers should agree on a disclosure date after a fix or
mitigation is available. A security advisory should credit the reporter if they
want credit, describe affected versions and impact without exposing unnecessary
user data, and publish upgrade or containment steps. Immediate disclosure may be
necessary when exploitation is already public; otherwise, please allow time for
users to update.

## Scope

In scope are vulnerabilities in the scanner, CLI, report generation, verified
source ingestion, AI evidence binding, proof generation/runner, packaging, and
official CI examples. Examples include command execution that crosses a documented
boundary, path traversal or overwrite, secret disclosure, schema/gate bypass,
unsafe proof execution, and materially incorrect security results caused by an
implementation defect.

Detector false positives and false negatives are important correctness bugs but
are not automatically security vulnerabilities in the scanner. A clean scan is
never a safety guarantee. Reports about third-party contracts, Foundry, Solidity,
Etherscan, OpenAI, GitHub Actions, or another dependency should go to that
project unless Contract Holes introduces or amplifies the issue.

See the [threat model](docs/THREAT_MODEL.md) and
[secure-use guide](docs/SECURE_USE.md) for the boundaries this policy relies on.
