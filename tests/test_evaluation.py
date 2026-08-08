import contextlib
import io
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from contract_holes.cli import main
from contract_holes.evaluation import (
    evaluate_labelled_corpus,
    evaluation_exit_status,
    load_evaluation_manifest,
    score_labelled_findings,
)
from contract_holes.models import Finding, Severity


MANIFEST = Path("tests/fixtures/evaluation/manifest.json")


def finding(line: int, scope: str) -> Finding:
    return Finding(
        rule_id="SOL005",
        severity=Severity.HIGH,
        title="Reentrancy",
        message="interaction before write",
        path=Path("Vault.sol"),
        line=line,
        column=1,
        excerpt=f"call{line}()",
        recommendation="update first",
        metadata={"entry_function": scope},
    )


class EvaluationTests(unittest.TestCase):
    def test_manifest_versions_all_rules_and_label_totals(self) -> None:
        manifest = load_evaluation_manifest(MANIFEST)

        self.assertEqual(manifest["corpus_version"], "audit-1")
        self.assertEqual(manifest["solc_version"], "0.8.25")
        self.assertEqual(manifest["expected_positive_labels"], 33)
        self.assertEqual(manifest["expected_safe_labels"], 31)
        self.assertEqual(len(manifest["rule_ids"]), 13)
        self.assertEqual(len(manifest["cases"]), 13)

    def test_scoring_reports_true_false_positive_and_false_negative_counts(self) -> None:
        actual = [finding(10, "Vault.one"), finding(30, "Vault.safe")]
        result = score_labelled_findings(
            "SOL005",
            [{"line": 10}, {"line": 20}],
            ["Vault.safe"],
            actual,
            minimum_precision=0.8,
            minimum_recall=0.8,
        )

        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["false_positives"], 1)
        self.assertEqual(result["false_negatives"], 1)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["safe_label_violations"], ["Vault.safe"])
        self.assertEqual(result["status"], "failed")

    @unittest.skipUnless(shutil.which("forge"), "Foundry is required for evaluation")
    def test_audit_corpus_meets_every_per_rule_threshold_offline(self) -> None:
        payload = evaluate_labelled_corpus(MANIFEST, offline=True)

        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["failed_rules"], [])
        self.assertEqual(payload["aggregate"]["true_positives"], 33)
        self.assertEqual(payload["aggregate"]["false_positives"], 0)
        self.assertEqual(payload["aggregate"]["false_negatives"], 0)
        self.assertEqual(payload["aggregate"]["macro_precision"], 1.0)
        self.assertEqual(payload["aggregate"]["macro_recall"], 1.0)
        self.assertTrue(
            all(result["status"] == "passed" for result in payload["rules"])
        )
        self.assertEqual(evaluation_exit_status(payload), 0)

    def test_evaluate_cli_is_offline_by_default_and_returns_metric_gate(self) -> None:
        payload = {"schema_version": "1.0", "status": "failed"}
        output = io.StringIO()
        with (
            patch(
                "contract_holes.cli.evaluate_labelled_corpus",
                return_value=payload,
            ) as evaluate,
            contextlib.redirect_stdout(output),
        ):
            status = main(["evaluate", "manifest.json"])

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue()), payload)
        evaluate.assert_called_once_with("manifest.json", offline=True)


if __name__ == "__main__":
    unittest.main()
