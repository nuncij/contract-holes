import contextlib
import io
from importlib.resources import files
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from contract_holes.bounty_history import (
    BountyHistoryError,
    evaluate_bounty_history,
    load_bounty_history_manifest,
)
from contract_holes.cli import main


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/fixtures/bounty_history/manifest.json"
EXPECTED = ROOT / "evaluation/bounty-history-1.0.json"


class BountyHistoryTests(unittest.TestCase):
    def test_manifest_freezes_ten_independent_cases_and_two_splits(self) -> None:
        manifest = load_bounty_history_manifest(MANIFEST)
        cases = manifest["cases"]
        self.assertEqual(len(cases), 10)
        self.assertEqual(len({case["project"] for case in cases}), 10)
        self.assertEqual({case["split"] for case in cases}, {"calibration", "holdout"})
        self.assertGreaterEqual(
            len(
                {
                    case["project"]
                    for case in cases
                    if case["model_status"] == "supported"
                }
            ),
            3,
        )
        self.assertTrue(
            all(case["provenance"]["upstream_code_copied"] is False for case in cases)
        )

    def test_offline_evaluation_matches_versioned_raw_result(self) -> None:
        result = evaluate_bounty_history(MANIFEST)
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(result, expected)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["product_claim"]["decision"], "go")
        self.assertEqual(result["metrics"]["supported_cases_with_evidence"], 5)
        self.assertEqual(result["metrics"]["rejected_candidates"], 1)
        self.assertNotIn(str(ROOT), json.dumps(result))

    def test_fixture_tampering_and_label_rewriting_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "corpus"
            shutil.copytree(MANIFEST.parent, corpus)
            fixture = corpus / "src/CreamAmp2021.sol"
            fixture.write_text(
                fixture.read_text(encoding="utf-8") + "\n// changed\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BountyHistoryError, "SHA-256 changed"):
                load_bounty_history_manifest(corpus / "manifest.json")

        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "corpus"
            shutil.copytree(MANIFEST.parent, corpus)
            manifest_path = corpus / "manifest.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            out_of_model = next(
                case for case in payload["cases"] if case["model_status"] == "out-of-model"
            )
            out_of_model["expected_findings"] = [{"rule_id": "SOL001"}]
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(BountyHistoryError, "cannot expect findings"):
                load_bounty_history_manifest(manifest_path)

    def test_failed_product_gate_is_visible_as_no_go(self) -> None:
        class EmptyScanner:
            def scan_paths(self, paths, **kwargs):
                return [], len(paths)

        result = evaluate_bounty_history(MANIFEST, scanner=EmptyScanner())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["product_claim"]["decision"], "no-go")
        self.assertFalse(result["gate_checks"]["supported_class_recall"])
        self.assertEqual(result["metrics"]["supported_cases_with_evidence"], 0)

    def test_history_schemas_are_packaged(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        manifest = json.loads(
            schema_directory.joinpath(
                "bounty-history-manifest-1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        result = json.loads(
            schema_directory.joinpath(
                "bounty-history-result-1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(result["properties"]["schema_version"]["const"], "1.0")


class BountyHistoryCliTests(unittest.TestCase):
    def test_cli_runs_offline_history_gate(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["bounty", "history", str(MANIFEST)])
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertTrue(payload["execution_policy"]["offline"])
        self.assertFalse(payload["execution_policy"]["network_writes"])


if __name__ == "__main__":
    unittest.main()
