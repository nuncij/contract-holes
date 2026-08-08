from pathlib import Path
import unittest


WORKFLOW = Path("examples/github-actions/contract-holes.yml")


class CiExampleTests(unittest.TestCase):
    def test_workflow_has_minimal_permissions_and_pinned_tool_majors(self) -> None:
        content = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("contents: read", content)
        self.assertIn("security-events: write", content)
        self.assertIn("persist-credentials: false", content)
        self.assertIn("timeout-minutes: 15", content)
        self.assertIn("actions/checkout@v6", content)
        self.assertIn("actions/setup-python@v6", content)
        self.assertIn("foundry-rs/foundry-toolchain@v1", content)
        self.assertIn("version: v1.7.1", content)
        self.assertIn("github/codeql-action/upload-sarif@v4", content)

    def test_workflow_uploads_valid_sarif_before_restoring_gate_status(self) -> None:
        content = WORKFLOW.read_text(encoding="utf-8")

        scan = content.index("id: holes")
        upload = content.index("name: Upload SARIF")
        gate = content.index("name: Enforce new-finding gate")
        self.assertLess(scan, upload)
        self.assertLess(upload, gate)
        self.assertIn("--baseline .holes-baseline.json", content)
        self.assertIn("--format sarif", content)
        self.assertIn("--fail-on high", content)
        self.assertIn('echo "exit_code=$scan_status"', content)
        self.assertIn("steps.holes.outputs.exit_code == '1'", content)
        self.assertIn('exit "$scan_status"', content)


if __name__ == "__main__":
    unittest.main()
