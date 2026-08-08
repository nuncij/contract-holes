from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionFilters, ProjectInspector
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/rule008").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for SOL008 tests")
class TargetTaintTests(unittest.TestCase):
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
            if finding.rule_id == "SOL008"
        ]

    def test_detects_direct_helper_delegatecall_and_typed_targets(self) -> None:
        actual = sorted(
            (
                {
                    "entry_function": finding.metadata["entry_function"],
                    "call_kind": finding.metadata["call_kind"],
                    "trace_kinds": [
                        step["kind"] for step in finding.metadata["trace"]
                    ],
                }
                for finding in self.findings
            ),
            key=lambda item: item["entry_function"],
        )
        self.assertEqual(actual, self.expectations["expected_findings"])
        by_entry = {finding.metadata["entry_function"]: finding for finding in self.findings}
        helper = by_entry["TargetVulnerable.throughHelper"]
        self.assertEqual(helper.metadata["sink_function"], "TargetVulnerable._dispatch")
        self.assertEqual(helper.metadata["evidence"], self.expectations["evidence"])

    def test_fixed_targets_and_empty_data_payments_are_clean(self) -> None:
        entries = {finding.metadata["entry_function"] for finding in self.findings}
        self.assertTrue(entries.isdisjoint(self.expectations["expected_clean_entries"]))

    def test_shared_facts_retain_target_and_argument_values(self) -> None:
        target_facts = self.index.data_flow.facts_for(kind="external-target")
        argument_facts = self.index.data_flow.facts_for(kind="call-argument")
        self.assertGreaterEqual(len(target_facts), 7)
        self.assertTrue(any(fact.value.user_controlled for fact in target_facts))
        self.assertTrue(
            any(fact.metadata.get("empty_calldata") is True for fact in target_facts)
        )
        self.assertTrue(argument_facts)
        self.assertEqual(len(self.index.target_taint.issues), 4)

    def test_inspection_exposes_filtered_target_taint_trace(self) -> None:
        payload = ProjectInspector(
            self.index,
            root=FIXTURE_ROOT,
            filters=InspectionFilters.create(
                contracts=["TargetVulnerable"],
                functions=["throughHelper"],
            ),
        ).to_dict()

        self.assertEqual(payload["summary"]["target_taint_issues"], 1)
        issue = payload["target_taint"]["issues"][0]
        self.assertEqual(issue["entry_function"], "TargetVulnerable.throughHelper")
        self.assertEqual(
            [step["kind"] for step in issue["trace"]],
            ["input", "call", "parameter", "sink"],
        )


if __name__ == "__main__":
    unittest.main()
