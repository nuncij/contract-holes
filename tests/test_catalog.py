import contextlib
import io
import json
import unittest

from contract_holes.catalog import catalog_payload, text_catalog
from contract_holes.cli import main


class CatalogTests(unittest.TestCase):
    def test_catalog_covers_every_rule_with_examples_and_references(self) -> None:
        payload = catalog_payload()
        entries = payload["rules"]

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["catalog_version"], "1.0")
        self.assertEqual(payload["rule_count"], 13)
        self.assertEqual(
            [entry["rule_id"] for entry in entries],
            [f"SOL{number:03d}" for number in range(1, 14)],
        )
        for entry in entries:
            with self.subTest(rule_id=entry["rule_id"]):
                self.assertTrue(entry["vulnerable_example"])
                self.assertTrue(entry["safer_example"])
                self.assertTrue(entry["recommendation"])
                self.assertTrue(entry["manual_review"])
                self.assertTrue(entry["references"])
                self.assertTrue(
                    all(
                        reference["url"].startswith("https://")
                        for reference in entry["references"]
                    )
                )

    def test_text_detail_is_deterministic_and_complete(self) -> None:
        payload = catalog_payload("sol005")
        first = text_catalog(payload)
        second = text_catalog(payload)

        self.assertEqual(first, second)
        self.assertIn("SOL005 [HIGH]", first)
        self.assertIn("Vulnerable:", first)
        self.assertIn("Safer:", first)
        self.assertIn("Remediation:", first)
        self.assertIn("References:", first)
        self.assertNotIn("SOL004", first)

    def test_rules_cli_supports_json_detail_and_unknown_errors(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["rules", "SOL013", "--format", "json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["rule_count"], 1)
        self.assertEqual(payload["rules"][0]["rule_id"], "SOL013")

        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            status = main(["rules", "SOL999"])
        self.assertEqual(status, 2)
        self.assertIn("unknown rule ID", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
