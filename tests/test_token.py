from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionFilters, ProjectInspector
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/rule012").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for SOL012 tests")
class TokenAnalysisTests(unittest.TestCase):
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
            if finding.rule_id == "SOL012"
        ]

    def test_detects_ignored_returns_and_nominal_amount_credits(self) -> None:
        actual = sorted(
            (
                {
                    "entry_function": finding.metadata["entry_function"],
                    "issue_kind": finding.metadata["issue_kind"],
                    "trace_kinds": [
                        event["kind"] for event in finding.metadata["trace"]
                    ],
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

    def test_checked_nonreturning_and_balance_delta_paths_are_clean(self) -> None:
        entries = {finding.metadata["entry_function"] for finding in self.findings}
        self.assertTrue(entries.isdisjoint(self.expectations["expected_clean_entries"]))
        self.assertEqual(len(self.index.token.issues), 3)

    def test_helper_parameter_origins_reach_the_caller_write(self) -> None:
        helper = next(
            finding
            for finding in self.findings
            if finding.metadata["entry_function"].endswith(".nominalDepositViaHelper")
        )
        token_call = next(
            event for event in helper.metadata["trace"] if event["kind"] == "token-call"
        )
        state_write = helper.metadata["trace"][-1]
        self.assertTrue(set(token_call["origins"]) & set(state_write["origins"]))

    def test_inspection_exposes_filtered_token_trace(self) -> None:
        payload = ProjectInspector(
            self.index,
            root=FIXTURE_ROOT,
            filters=InspectionFilters.create(
                contracts=["TokenVulnerable"],
                functions=["nominalDepositViaHelper"],
            ),
        ).to_dict()
        self.assertEqual(payload["summary"]["token_issues"], 1)
        issue = payload["token"]["issues"][0]
        self.assertEqual(issue["issue_kind"], "nominal-amount-accounting")
        self.assertEqual(
            [event["kind"] for event in issue["trace"]],
            ["entry", "call", "token-call", "state-write"],
        )


if __name__ == "__main__":
    unittest.main()
