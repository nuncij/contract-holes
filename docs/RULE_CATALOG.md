# Rule Catalog

Use the catalog command before enabling a detector in CI, reviewing a finding,
or documenting a suppression:

```bash
holes rules
holes rules SOL005
holes rules SOL013 --format json
```

Text output is intended for reviewers. JSON output has `schema_version = 1.0`,
`catalog_version = 1.0`, a rule count, and an ordered `rules` array suitable for
internal tooling.

Every catalog entry includes:

- rule ID, default severity, confidence, title, and signal description;
- source, compiler, flow, or proof analysis mode;
- a minimal vulnerable snippet and a safer alternative;
- the scanner's remediation recommendation;
- the conditions that still require manual review;
- one or more primary or authoritative reference links.

Severity overrides in `.holes.toml` apply to scan findings and reports. The
catalog intentionally shows default rule severity so teams can distinguish the
scanner's shipped policy from a project override.

Examples demonstrate the detected primitive, not a complete exploitable
protocol. Read the manual-review line and the finding evidence path before
triage. A clean result for one rule does not establish that the broader
vulnerability class is absent.
