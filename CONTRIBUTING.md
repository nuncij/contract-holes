# Contributing

Contract Holes is evidence-first: a detector must show reproducible source,
compiler, flow, or proof evidence and state where manual review still begins.

## Development setup

Use a supported CPython and, for compiler-aware work, a supported Foundry/solc
toolchain. From a reviewed checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

There are no required third-party runtime or test dependencies. The full suite
runs with `unittest`; compiler/evaluation/proof cases skip when Forge is absent,
so note skipped coverage in a review. See [installation](docs/INSTALLATION.md) and
[compatibility](docs/COMPATIBILITY.md).

Do not put credentials in fixtures, commands, issues, or commits. Use the private
process in [SECURITY.md](SECURITY.md) for suspected vulnerabilities.

## Repository map

| Path | Responsibility |
| --- | --- |
| `src/contract_holes/rules.py` | Detector registration and source/AST rule logic |
| `src/contract_holes/project.py` | Project-wide AST and source identity index |
| `src/contract_holes/*flow*.py` and analysis modules | Shared call/data-flow evidence |
| `src/contract_holes/reporters.py`, `schema.py`, `schemas/` | Stable JSON/SARIF contract |
| `src/contract_holes/cli.py` | Command parsing, exit semantics, and orchestration |
| `src/contract_holes/proofs.py`, `proof_runner.py` | Generated evidence and execution |
| `tests/fixtures/` | Positive, safe, multi-file, proof, and evaluation corpora |
| `docs/`, `TASKS.md` | User contracts, milestone state, and design boundaries |

Keep reusable compiler facts in project/inheritance/call/data-flow modules rather
than embedding another raw-AST traversal in one rule.

## Change workflow

1. Select or add a task in `TASKS.md`; keep one `NEXT` task and at most one task
   in progress.
2. Write the smallest positive and nearby safe fixture that defines expected
   behavior.
3. Implement deterministic evidence with labelled unknowns when resolution is
   incomplete.
4. Add unit/integration assertions, including path/line/evidence metadata and a
   regression for every bug fixed.
5. Update user docs, limitations, task status, and development plan in the same
   change.
6. Run the relevant narrow tests, then the full suite and `git diff --check`.
7. Commit one coherent task with tests and documentation.

Preserve unrelated working-tree changes. Generated output must be deterministic,
must not overwrite user edits, and must not write into scanned repositories unless
the user selected an output path.

## Adding or changing a rule

- Choose the next stable `SOLnnn` identifier; never recycle an ID.
- Define title, default severity, confidence, recommendation, evidence mode,
  vulnerable/safer examples, manual-review boundary, and authoritative references.
- Use compiler-backed types/references when a source regex would overclaim. Keep
  source-only fallback explicitly labelled when retained.
- Add vulnerable and safe fixtures. For compiler rules, include inheritance,
  alias/helper, and unresolved cases that exercise shared analysis.
- Add labels to the versioned evaluation manifest and document corpus limits.
- Verify text, JSON, SARIF, baselines, suppressions, and proof generation if the
  public finding shape or supported proof set changes.

A perfect checked-in fixture score is a regression result, not a real-world
accuracy claim. Do not tune a detector solely to fixture filenames or line
numbers.

## Public compatibility

JSON report schema `1.0`, the SARIF producer profile, fingerprints, baseline
identity, proof manifests, configuration, catalog, and CLI exit codes are public
interfaces. Follow [output compatibility](docs/OUTPUT_COMPATIBILITY.md) before
changing them. Additive fields still require schema/test/doc updates; breaking
changes require a new major schema and migration guidance.

Toolchain-range changes require reference-matrix evidence and updates to
`pyproject.toml`, `compatibility.py`, its workflow, tests, and
[compatibility documentation](docs/COMPATIBILITY.md).

## Required checks

For every change:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
git diff --check
```

For detector/corpus changes:

```bash
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
```

Run affected generated proofs and packaging/reproducibility checks when those
areas change. Record exact versions for failures that depend on Python, Foundry,
solc, or EVM target.

## Review expectations

A review should be able to answer: what evidence changed, which false-positive
and false-negative cases are covered, what remains unknown, which public output
changed, and which commands reproduced the result. Keep commits focused and use
plain, imperative commit subjects.

Only contribute source and fixtures you are authorized to publish under the
repository's [MIT license](LICENSE).
