from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionFilters, ProjectInspector
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/rule010").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for SOL010 tests")
class SignatureAnalysisTests(unittest.TestCase):
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
            if finding.rule_id == "SOL010"
        ]

    def test_isolates_replay_deadline_domain_and_recovery_hazards(self) -> None:
        actual = sorted(
            (
                {
                    "entry_function": finding.metadata["entry_function"],
                    "hazards": finding.metadata["hazards"],
                }
                for finding in self.findings
            ),
            key=lambda item: item["entry_function"],
        )
        self.assertEqual(actual, self.expectations["expected_findings"])
        self.assertTrue(
            all(
                finding.metadata["evidence"] == self.expectations["evidence"]
                for finding in self.findings
            )
        )

    def test_helper_trace_reaches_recovery_and_action(self) -> None:
        helper = next(
            finding
            for finding in self.findings
            if finding.metadata["entry_function"].endswith(".executeThroughHelper")
        )
        self.assertEqual(helper.metadata["recovery_function"], "SignatureVulnerable._recoverWeak")
        self.assertEqual(
            [event["kind"] for event in helper.metadata["trace"]],
            ["entry", "call", "recovery", "signer-validation", "action"],
        )

    def test_complete_protection_and_pure_recovery_are_clean(self) -> None:
        entries = {finding.metadata["entry_function"] for finding in self.findings}
        self.assertTrue(entries.isdisjoint(self.expectations["expected_clean_entries"]))
        self.assertEqual(len(self.index.signature.issues), 7)

    def test_data_flow_and_inspection_expose_signature_evidence(self) -> None:
        recovery_facts = self.index.data_flow.facts_for(kind="signature-recovery")
        self.assertEqual(len(recovery_facts), 11)
        payload = ProjectInspector(
            self.index,
            root=FIXTURE_ROOT,
            filters=InspectionFilters.create(
                contracts=["SignatureVulnerable"],
                functions=["executeThroughHelper"],
            ),
        ).to_dict()
        self.assertEqual(payload["summary"]["signature_issues"], 1)
        issue = payload["signature"]["issues"][0]
        self.assertEqual(issue["entry_function"], "SignatureVulnerable.executeThroughHelper")
        self.assertEqual(
            [event["kind"] for event in issue["trace"]],
            ["entry", "call", "recovery", "signer-validation", "action"],
        )


if __name__ == "__main__":
    unittest.main()
