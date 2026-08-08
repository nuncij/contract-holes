from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionFilters, ProjectInspector
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/rule009").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for SOL009 tests")
class AuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expectations = json.loads(
            (FIXTURE_ROOT / "expectations.json").read_text(encoding="utf-8")
        )
        cls.files = discover_sources([FIXTURE_ROOT / "src"])
        compilation = ForgeCompiler().compile(
            cls.files,
            project_root=FIXTURE_ROOT,
            offline=True,
        )
        cls.index = ProjectIndex(compilation)
        cls.source = cls.index.source_for_path(cls.files[0]).source
        cls.findings = [
            finding
            for finding in Scanner().scan_source(cls.source)
            if finding.rule_id == "SOL009"
        ]

    def test_detects_direct_helper_conditional_and_late_authorization(self) -> None:
        actual = sorted(
            (
                {
                    "entry_function": finding.metadata["entry_function"],
                    "state_variable": finding.metadata["state_variable"],
                    "trace_kinds": [
                        event["kind"] for event in finding.metadata["trace"]
                    ],
                }
                for finding in self.findings
            ),
            key=lambda item: item["entry_function"],
        )
        self.assertEqual(actual, self.expectations["expected_findings"])
        conditional = next(
            finding
            for finding in self.findings
            if finding.metadata["entry_function"].endswith(".conditionalOwner")
        )
        authorization = conditional.metadata["trace"][1]
        self.assertFalse(authorization["guaranteed"])
        self.assertFalse(authorization["protective"])
        self.assertEqual(conditional.metadata["evidence"], self.expectations["evidence"])

    def test_dominating_checks_modifiers_helpers_and_ordinary_state_are_clean(self) -> None:
        entries = {finding.metadata["entry_function"] for finding in self.findings}
        self.assertTrue(entries.isdisjoint(self.expectations["expected_clean_entries"]))
        self.assertEqual(len(self.findings), len(self.expectations["expected_findings"]))

    def test_analysis_classifies_only_privileged_state_writes(self) -> None:
        sensitive_names = {
            str(fact.metadata.get("name"))
            for fact in self.index.authorization.sensitive_writes
        }
        self.assertEqual(
            sensitive_names,
            {"admins", "implementation", "owner", "treasury"},
        )
        self.assertEqual(len(self.index.authorization.issues), 4)

    def test_inspection_exposes_filtered_authorization_trace(self) -> None:
        payload = ProjectInspector(
            self.index,
            root=FIXTURE_ROOT,
            filters=InspectionFilters.create(
                contracts=["AuthorizationVulnerable"],
                functions=["upgrade"],
            ),
        ).to_dict()

        self.assertEqual(payload["summary"]["authorization_issues"], 1)
        issue = payload["authorization"]["issues"][0]
        self.assertEqual(issue["entry_function"], "AuthorizationVulnerable.upgrade")
        self.assertEqual(
            [event["kind"] for event in issue["trace"]],
            ["entry", "call", "write"],
        )


if __name__ == "__main__":
    unittest.main()
