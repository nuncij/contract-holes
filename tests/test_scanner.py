import json
from pathlib import Path
import tempfile
import unittest

from contract_holes.models import Severity
from contract_holes.reporters import json_report, sarif_report
from contract_holes.scanner import ScanError, Scanner, discover_sources


class ScannerTests(unittest.TestCase):
    def test_severity_filter(self) -> None:
        findings, count = Scanner().scan_paths(
            [Path("tests/fixtures/VulnerableVault.sol")],
            minimum_severity=Severity.HIGH,
        )
        self.assertEqual(count, 1)
        self.assertTrue(findings)
        self.assertTrue(all(finding.severity >= Severity.HIGH for finding in findings))
        self.assertNotIn("SOL002", {finding.rule_id for finding in findings})

    def test_json_and_sarif_are_valid(self) -> None:
        scanner = Scanner()
        findings, count = scanner.scan_paths([Path("tests/fixtures/VulnerableVault.sol")])

        json_payload = json.loads(json_report(findings, count))
        sarif_payload = json.loads(sarif_report(findings, [rule.info for rule in scanner.rules]))

        self.assertEqual(json_payload["finding_count"], 7)
        self.assertEqual(sarif_payload["version"], "2.1.0")
        self.assertEqual(len(sarif_payload["runs"][0]["results"]), 7)

    def test_dependency_directories_are_excluded_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "lib").mkdir()
            (root / "src" / "Main.sol").write_text("contract Main {}", encoding="utf-8")
            (root / "lib" / "Dependency.sol").write_text("contract Dependency {}", encoding="utf-8")

            default = discover_sources([root])
            included = discover_sources([root], include_dependencies=True)

            self.assertEqual([item.name for item in default], ["Main.sol"])
            self.assertEqual({item.name for item in included}, {"Main.sol", "Dependency.sol"})

    def test_invalid_path_is_an_actionable_error(self) -> None:
        with self.assertRaisesRegex(ScanError, "path does not exist"):
            discover_sources(["definitely-missing.sol"])


if __name__ == "__main__":
    unittest.main()
