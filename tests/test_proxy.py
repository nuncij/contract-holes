from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionFilters, ProjectInspector
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/rule011").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for SOL011 tests")
class ProxyAnalysisTests(unittest.TestCase):
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
            if finding.rule_id == "SOL011"
        ]

    def test_detects_initializer_proxy_slot_and_layout_hazards(self) -> None:
        actual = sorted(
            (
                {
                    "contract": finding.metadata["contract"],
                    "issue_kind": finding.metadata["issue_kind"],
                    "entry_function": finding.metadata.get("initializer")
                    or (
                        finding.metadata["trace"][1]["owner"]
                        if finding.metadata["issue_kind"] == "proxy-storage-collision"
                        else None
                    ),
                    "trace_kinds": [
                        step["kind"] for step in finding.metadata["trace"]
                    ],
                }
                for finding in self.findings
            ),
            key=lambda item: (
                item["contract"],
                item["issue_kind"],
                item["entry_function"] or "",
            ),
        )
        expected = sorted(
            self.expectations["expected_findings"],
            key=lambda item: (
                item["contract"],
                item["issue_kind"],
                item["entry_function"] or "",
            ),
        )
        self.assertEqual(actual, expected)
        self.assertTrue(
            all(
                finding.metadata["evidence"] == self.expectations["evidence"]
                for finding in self.findings
            )
        )

    def test_one_time_guards_unstructured_slots_and_appended_layout_are_clean(self) -> None:
        finding_labels = {
            str(finding.metadata.get("initializer") or finding.metadata.get("contract"))
            for finding in self.findings
        }
        self.assertTrue(finding_labels.isdisjoint(self.expectations["expected_clean"]))
        self.assertEqual(len(self.index.proxy.issues), 4)

    def test_layout_finding_explains_the_changed_prefix(self) -> None:
        layout = next(
            finding
            for finding in self.findings
            if finding.metadata["issue_kind"] == "incompatible-upgrade-layout"
        )
        self.assertEqual(layout.metadata["mismatch_index"], 0)
        self.assertEqual(layout.metadata["previous_layout"][0]["name"], "owner")
        self.assertEqual(layout.metadata["current_layout"][0]["name"], "totalAssets")

    def test_inspection_exposes_filtered_proxy_trace(self) -> None:
        payload = ProjectInspector(
            self.index,
            root=FIXTURE_ROOT,
            filters=InspectionFilters.create(
                contracts=["UnsafeProxy"],
                functions=["forward"],
            ),
        ).to_dict()
        self.assertEqual(payload["summary"]["proxy_issues"], 1)
        issue = payload["proxy"]["issues"][0]
        self.assertEqual(issue["issue_kind"], "proxy-storage-collision")
        self.assertEqual(
            [step["kind"] for step in issue["trace"]],
            ["structured-storage", "delegatecall"],
        )


if __name__ == "__main__":
    unittest.main()
