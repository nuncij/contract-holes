from pathlib import Path
import json
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionFilters, ProjectInspector
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


FIXTURE_ROOT = Path("tests/fixtures/rule013").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for SOL013 tests")
class MarketAnalysisTests(unittest.TestCase):
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
            if finding.rule_id == "SOL013"
        ]

    def test_detects_stale_spot_and_unbounded_swap_paths(self) -> None:
        actual = sorted(
            (
                {
                    "entry_function": finding.metadata["entry_function"],
                    "issue_kind": finding.metadata["issue_kind"],
                    "hazards": finding.metadata["hazards"],
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

    def test_fresh_twap_and_bounded_swap_paths_are_clean(self) -> None:
        entries = {finding.metadata["entry_function"] for finding in self.findings}
        self.assertTrue(entries.isdisjoint(self.expectations["expected_clean_entries"]))
        self.assertEqual(len(self.index.market.issues), 3)

    def test_oracle_trace_retains_price_origin_and_action(self) -> None:
        stale = next(
            finding
            for finding in self.findings
            if finding.metadata["issue_kind"] == "stale-oracle"
        )
        source = stale.metadata["trace"][1]
        action = stale.metadata["trace"][2]
        self.assertTrue(set(source["origins"]) & set(action["origins"]))
        self.assertEqual(action["state_variable"], "lastPrice")

    def test_inspection_exposes_filtered_market_trace(self) -> None:
        payload = ProjectInspector(
            self.index,
            root=FIXTURE_ROOT,
            filters=InspectionFilters.create(
                contracts=["MarketVulnerable"],
                functions=["unsafeSwap"],
            ),
        ).to_dict()
        self.assertEqual(payload["summary"]["market_issues"], 1)
        issue = payload["market"]["issues"][0]
        self.assertEqual(issue["issue_kind"], "swap-protection")
        self.assertEqual(
            issue["hazards"],
            ["missing-minimum-output", "ineffective-deadline"],
        )


if __name__ == "__main__":
    unittest.main()
