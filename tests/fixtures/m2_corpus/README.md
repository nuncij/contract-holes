# M2 Analysis Corpus

This Foundry project is the versioned positive and negative corpus for the M2
cross-contract analysis milestone. It targets solc `0.8.25` and is designed to
compile offline once that compiler version is installed.

Each directory keeps a vulnerable contract next to a safe contract with the same
structure:

- `imports`: imported inherited state plus an internal library interaction;
- `overrides`: an overridden external entry and an explicit `super` state update;
- `diamond`: shared state inherited through two branches without duplication;
- `recursion`: a recursive internal helper represented without infinite unfolding;
- `modifiers`: an inherited semantic lock modifier whose name is intentionally not
  a built-in `nonReentrant` pattern.

[`expectations.json`](expectations.json) records the exact expected rule IDs,
entry functions, state variables, and normalized evidence paths. Run the corpus
integration tests with:

```bash
PYTHONPATH=src python3 -m unittest tests.test_m2_corpus -v
```

The vulnerable contracts are deliberately minimal review fixtures, not deployable
protocol implementations.

The same manifest contains source-only and compiler-backed finding-count
expectations for the repeatable M2 benchmark:

```bash
holes benchmark tests/fixtures/m2_corpus/src --offline
```

Performance values are emitted for the current environment rather than checked
into the corpus. A prior JSON report can be supplied with `--baseline`; timing
regressions are reported but do not fail the command.
