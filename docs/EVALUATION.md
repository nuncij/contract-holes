# Precision and recall evaluation

The versioned `audit-1` corpus measures every registered rule against explicit
positive and safe labels. It contains 33 positive labels and 31 safe labels,
pins solc `0.8.25`, and reuses the checked-in M3 fixtures plus paired legacy-rule
contracts.

Run it without network access after the pinned compiler is installed:

```bash
holes evaluate tests/fixtures/evaluation/manifest.json > evaluation.json
```

Evaluation is offline by default. `--allow-downloads` permits Foundry to install
the pinned compiler. Status 0 means every rule met both thresholds, status 1
means at least one rule missed a metric threshold, and status 2 means the corpus,
compiler, or execution was invalid.

For each rule the result records:

- true positives: actual findings matched one-to-one with positive labels;
- false positives: actual findings that matched no positive label;
- false negatives: positive labels with no matching finding;
- precision: `TP / (TP + FP)`;
- recall: `TP / (TP + FN)`;
- any finding whose deterministic scope overlaps a labelled safe entry.

The output also includes micro and macro precision/recall. The manifest requires
at least 0.80 precision and 0.80 recall per rule. Timing and memory are excluded
from this gate; `holes benchmark` reports those separately without flaky
wall-clock failures.

The current corpus produces 1.0 precision and recall for all 13 rules. This is a
regression result on a small, curated corpus, not an estimate of performance on
unseen production contracts. Labels are code-adjacent and may share assumptions
with detector authors. Expand the corpus with independently labelled real-world
cases before making external accuracy claims, and never interpret the score as
evidence that a clean contract is safe.
