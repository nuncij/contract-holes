from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/precision_002").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for PRECISION-002 tests")
class Precision002Tests(unittest.TestCase):
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

    def _by_rule(self, rule_id: str) -> list[str]:
        return sorted(
            {
                finding.metadata["entry_function"]
                for finding in self.findings
                if finding.rule_id == rule_id and finding.metadata.get("entry_function")
            }
        )

    def test_manifest_compiler_pin_and_case_labels(self) -> None:
        self.assertEqual(self.manifest["schema_version"], "1.0")
        self.assertEqual(self.manifest["corpus_version"], "precision-002")
        self.assertTrue(
            any(
                version.startswith(self.manifest["compiler"])
                for version in self.compilation.compiler_versions
            )
        )
        self.assertTrue(all(case["behavior"] for case in self.manifest["cases"]))
        self.assertEqual(
            {case["name"] for case in self.manifest["cases"]},
            {
                "view-interaction-ordering",
                "timelock-authorization",
                "deployment-sequence",
                "governance-call-lists",
                "read-only-target-taint",
                "fixed-asset-provenance",
            },
        )

    def test_view_interaction_ordering(self) -> None:
        actual = self._by_rule("SOL005")
        self.assertEqual(actual, self.expectations["sol005_positive"])
        self.assertTrue(set(self.expectations["sol005_clean"]).isdisjoint(actual))
        self._assert_public_evidence(
            "SOL005", "PrecisionCases.stateChangingThenWrite"
        )

    def test_timelock_authorization(self) -> None:
        actual = self._by_rule("SOL009")
        self.assertEqual(actual, self.expectations["sol009_positive"])
        self.assertTrue(set(self.expectations["sol009_clean"]).isdisjoint(actual))
        self._assert_public_evidence(
            "SOL009", "PrecisionCases.unprotectedWrite"
        )
        mechanisms = {
            mechanism
            for fact in self.index.data_flow.facts_for(kind="authorization")
            for mechanism in fact.metadata.get("mechanisms", [])
        }
        self.assertIn("timelock:delay-and-pending", mechanisms)

    def test_deployment_and_governance_provenance(self) -> None:
        actual = self._by_rule("SOL008")
        self.assertEqual(actual, self.expectations["sol008_positive"])
        self.assertTrue(set(self.expectations["sol008_clean"]).isdisjoint(actual))
        self._assert_public_evidence(
            "SOL008", "PrecisionCases.depositCallerAsset"
        )
        sol003_lines = sorted(
            finding.line for finding in self.findings if finding.rule_id == "SOL003"
        )
        self.assertEqual(sol003_lines, self.expectations["sol003_lines"])

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
