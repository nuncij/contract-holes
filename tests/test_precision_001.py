from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionFilters, ProjectInspector
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/precision_001").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for PRECISION-001 tests")
class Precision001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expectations = json.loads(
            (FIXTURE_ROOT / "expectations.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads(
            (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        files = discover_sources([FIXTURE_ROOT / "src"])
        compilation = ForgeCompiler().compile(
            files, project_root=FIXTURE_ROOT, offline=True
        )
        cls.compilation = compilation
        cls.index = ProjectIndex(compilation)
        cls.source = cls.index.source_for_path(files[0]).source
        cls.findings = Scanner().scan_source(cls.source)

    def test_call_semantics_has_no_finding(self) -> None:
        self.assertEqual(self.manifest["schema_version"], "1.0")
        self.assertTrue(
            any(
                version.startswith(self.manifest["compiler"])
                for version in self.compilation.compiler_versions
            )
        )
        self.assertEqual(
            {case["name"]: case["rule_ids"] for case in self.manifest["cases"]},
            {
                "call-semantics": [],
                "branch-feasibility": ["SOL005"],
                "target-provenance": ["SOL008", "SOL005"],
                "authorization-context": ["SOL009"],
                "reentrancy-trust-boundary": ["SOL005"],
            },
        )
        self.assertTrue(all(case["behavior"] for case in self.manifest["cases"]))
        functions = {
            finding.metadata.get("entry_function")
            for finding in self.findings
            if finding.rule_id in {"SOL005", "SOL009"}
        }
        self.assertNotIn("PrecisionCases.callSemantics", functions)
        call_function = next(
            key
            for key, node in self.index.functions_by_id.items()
            if node.get("name") == "callSemantics"
        )
        self.assertFalse(
            self.index.data_flow.facts_for(
                function=call_function, kind="external-interaction"
            )
        )

    def test_reentrancy_branch_compatibility_and_fixed_target_boundary(self) -> None:
        actual = sorted(
            finding.metadata["entry_function"]
            for finding in self.findings
            if finding.rule_id == "SOL005"
        )
        expected = sorted(self.expectations["sol005_positive"])
        self.assertEqual(actual, expected)
        self.assertTrue(
            set(self.expectations["sol005_clean"]).isdisjoint(actual)
        )
        self._assert_public_evidence("SOL005", "PrecisionCases.feasibleBranch")

        by_entry = {
            finding.metadata["entry_function"]: finding
            for finding in self.findings
            if finding.rule_id == "SOL005"
        }
        for entry in (
            "PrecisionCases.fixedTargetStillNeedsReview",
            "PrecisionCases.fixedTargetAliasStillNeedsReview",
            "PrecisionCases.fixedTargetHelperStillNeedsReview",
        ):
            self.assertEqual(
                by_entry[entry].metadata["target_provenance"],
                {
                    "kind": "immutable-state",
                    "declarations": ["fixedTarget"],
                    "user_controlled": False,
                },
            )

    def test_authorization_context_and_mapping_ownership(self) -> None:
        actual = sorted(
            finding.metadata["entry_function"]
            for finding in self.findings
            if finding.rule_id == "SOL009"
        )
        self.assertEqual(actual, self.expectations["sol009_positive"])
        self.assertTrue(
            set(self.expectations["sol009_clean"]).isdisjoint(actual)
        )
        self._assert_public_evidence("SOL009", "PrecisionCases.selfGrantRole")

        caller_owned = next(
            fact
            for fact in self.index.data_flow.facts_for(kind="write")
            if fact.metadata.get("name") == "preferences"
        )
        self.assertEqual(caller_owned.metadata["index_ownership"], "msg.sender")

    def test_target_provenance_preserves_fixed_and_caller_selected_boundaries(self) -> None:
        actual = sorted(
            finding.metadata["entry_function"]
            for finding in self.findings
            if finding.rule_id == "SOL008"
        )
        self.assertEqual(actual, self.expectations["sol008_positive"])
        self._assert_public_evidence(
            "SOL008", "PrecisionCases.callerSelectedTarget"
        )

        inspection = ProjectInspector(
            self.index,
            root=FIXTURE_ROOT,
            filters=InspectionFilters.create(
                contracts=["PrecisionCases"],
                functions=["fixedTargetHelperStillNeedsReview"],
            ),
        ).to_dict()
        self.assertEqual(inspection["summary"]["reentrancy_issues"], 1)
        self.assertEqual(
            inspection["reentrancy"]["issues"][0]["target_provenance"],
            {
                "kind": "immutable-state",
                "declarations": ["fixedTarget"],
                "user_controlled": False,
            },
        )

    def _assert_public_evidence(self, rule_id: str, entry: str) -> None:
        finding = next(
            finding
            for finding in self.findings
            if finding.rule_id == rule_id
            and finding.metadata.get("entry_function") == entry
        )
        self.assertEqual(finding.path.resolve(), self.source.path.resolve())
        self.assertEqual(finding.line, self.expectations["evidence_lines"][rule_id])
        self.assertEqual(
            finding.metadata["evidence"], self.expectations["evidence"][rule_id]
        )


if __name__ == "__main__":
    unittest.main()
