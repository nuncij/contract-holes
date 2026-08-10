from pathlib import Path
import unittest


WORKFLOW = Path("examples/github-actions/contract-holes.yml")
COMPATIBILITY_WORKFLOW = Path("examples/github-actions/compatibility.yml")
REPOSITORY_WORKFLOW = Path(".github/workflows/ci.yml")


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

    def test_compatibility_workflow_covers_published_reference_points(self) -> None:
        content = COMPATIBILITY_WORKFLOW.read_text(encoding="utf-8")

        for python in ("3.10", "3.11", "3.12", "3.13", "3.14"):
            self.assertIn(f'"{python}"', content)
        for entry in (
            "v1.5.0",
            "v1.7.1",
            "0.8.20",
            "0.8.25",
            "0.8.29",
            "0.8.31",
            "0.8.36",
            "paris",
            "shanghai",
            "cancun",
            "prague",
            "osaka",
        ):
            self.assertIn(entry, content)
        self.assertIn("FOUNDRY_SOLC_VERSION", content)
        self.assertIn("FOUNDRY_EVM_VERSION", content)
        self.assertIn("--compile --online --format json", content)

    def test_repository_workflow_runs_full_tests_and_reproducible_build(self) -> None:
        content = REPOSITORY_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("contents: read", content)
        self.assertIn("persist-credentials: false", content)
        self.assertIn("cancel-in-progress: true", content)
        self.assertIn("actions/checkout@v6", content)
        self.assertIn("actions/setup-python@v6", content)
        self.assertIn("foundry-rs/foundry-toolchain@v1", content)
        self.assertIn("version: v1.7.1", content)
        self.assertIn("--compile --online --format json", content)
        self.assertIn("python -m unittest discover -s tests -q", content)
        self.assertIn("python -m pip install -r requirements/release.txt", content)
        self.assertIn("python scripts/release.py", content)
        self.assertIn("sha256sum --check SHA256SUMS", content)


if __name__ == "__main__":
    unittest.main()
