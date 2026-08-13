from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
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
        cls.index = ProjectIndex(compilation)
        cls.source = cls.index.source_for_path(files[0]).source
        cls.findings = Scanner().scan_source(cls.source)

    def test_call_semantics_has_no_finding(self) -> None:
        self.assertEqual(
            {case["name"] for case in self.manifest["cases"]},
            {
                "call-semantics",
                "branch-feasibility",
                "target-provenance",
                "authorization-context",
                "reentrancy-trust-boundary",
            },
        )
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

    def test_authorization_context_and_mapping_ownership(self) -> None:
        actual = sorted(
            finding.metadata["entry_function"]
            for finding in self.findings
            if finding.rule_id == "SOL009"
        )
        self.assertEqual(actual, self.expectations["sol009_positive"])

    def test_target_provenance_preserves_fixed_and_caller_selected_boundaries(self) -> None:
        actual = sorted(
            finding.metadata["entry_function"]
            for finding in self.findings
            if finding.rule_id == "SOL008"
        )
        self.assertEqual(actual, self.expectations["sol008_positive"])


if __name__ == "__main__":
    unittest.main()
