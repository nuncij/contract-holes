# Evidence-bound AI triage

AI triage is an optional explanation layer over a completed Contract Holes JSON
report. It cannot create scanner findings, change severity or confidence, or
turn a signal into a proof.

First inspect the deterministic bundle without making a network request:

```bash
holes contracts --format json > holes.json
holes explain holes.json --prepare > evidence-bundle.json
```

The preparer verifies the report schema, finding count, unique fingerprints, and
the fingerprint material itself. It groups findings by source path and detected
entry/function scope, then assigns stable group and evidence IDs. The same report
bytes produce the same bundle.

To request explanations:

```bash
export OPENAI_API_KEY="your key"
holes explain holes.json > triage.json
```

The default model is `gpt-5.6-luna`. Use `--model MODEL`, `--api-key-env NAME`,
or `--timeout SECONDS` to override the defaults. Contract Holes calls the OpenAI
Responses API with `store: false` and a strict Structured Outputs schema. The
API key is never included in the result.

Reports are capped at 2 MiB and 200 findings. Online requests are capped at 50
correlation groups; filter the scanner report by severity or baseline before
online explanation if it exceeds that boundary. Offline `--prepare` remains
available for the full accepted report.

## Grounding guarantees

Deterministic code, not the model, defines every correlation group, finding
identity, and evidence item. The model can return only:

- one annotation for each pre-existing group ID;
- a summary;
- references to evidence IDs belonging to that group;
- up to five manual-review questions.

The result is rejected if a group is unknown, missing, or duplicated; if an
evidence reference is unknown, cross-group, or duplicated; or if the API refuses,
returns incomplete output, or violates local size/content boundaries. Valid
annotations remain labelled `untrusted-model-explanation`. Review their claims
against the embedded deterministic evidence. They are not findings and are not
used by scanner exit status, baselines, SARIF, or proof generation.

## Data boundary

Online mode sends the JSON report's finding titles, messages, excerpts,
recommendations, locations, and metadata to OpenAI. It does not read additional
source files, but excerpts and trace metadata can still contain sensitive code
or local paths. Use `--prepare` only for confidential reports unless sending this
data is authorized under your organization's policy.

The API format follows the official OpenAI documentation for
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
