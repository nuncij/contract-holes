# Finding Baselines

Baselines let a team adopt Contract Holes without making every accepted existing
finding block CI. The scanner still analyzes the configured project, but reports
and `--fail-on` evaluate only fingerprints absent from the reviewed snapshot.

## Create and compare

From the repository root:

```bash
holes --write-baseline .holes-baseline.json
git add .holes-baseline.json

holes --baseline .holes-baseline.json --fail-on high --format sarif
```

Creation refuses to replace an existing file. After reviewing current findings,
update deliberately:

```bash
holes --update-baseline .holes-baseline.json
```

The write is atomic. Commit baseline changes with the code or review decision
that explains newly accepted or resolved findings.

## Comparison semantics

Each baseline fingerprint uses the rule ID, normalized path, line, and finding
excerpt identity. Paths are relative to the directory containing the baseline;
putting the file at the repository root makes it stable across checkout paths.
Severity is not part of identity, so a severity policy change does not create a
different vulnerability identity.

With `--baseline`:

- new findings appear in text, JSON, or SARIF output;
- existing findings are omitted from the report and cannot trigger `--fail-on`;
- resolved fingerprints are counted but not emitted as findings;
- JSON adds a `baseline` object with path and new/existing/resolved counts;
- stderr prints the same comparison counts for text and SARIF workflows.

The baseline schema stores fingerprint, rule ID, relative location, line, and
column. It does not store source excerpts or absolute project paths. Changing a
finding's relevant line or expression intentionally creates a new fingerprint
and requires review.

Invalid schemas, duplicate fingerprints, missing files, and accidental overwrite
attempts exit with status 2. Use the same scan configuration in local and CI
runs; enabling/disabling rules or changing minimum severity changes the set being
compared.
