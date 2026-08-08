import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.baseline import (
    BaselineError,
    compare_baseline,
    load_baseline,
    normalized_fingerprint,
    write_baseline,
)
from contract_holes.cli import main
from contract_holes.models import Finding, Severity


def finding(
    path: Path,
    *,
    rule_id: str = "SOL005",
    line: int = 10,
    severity: Severity = Severity.HIGH,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        title="Example",
        message="example finding",
        path=path,
        line=line,
        column=5,
        excerpt="target.call(payload)",
        recommendation="fix it",
    )


class BaselineTests(unittest.TestCase):
    def test_round_trip_uses_project_relative_normalized_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / ".holes-baseline.json"
            contract_path = root / "contracts" / "Vault.sol"
            original = finding(contract_path)

            payload = write_baseline([original], baseline_path)
            loaded = load_baseline(baseline_path)

            self.assertEqual(loaded, payload)
            self.assertEqual(payload["findings"][0]["path"], "contracts/Vault.sol")
            self.assertEqual(
                payload["findings"][0]["fingerprint"],
                normalized_fingerprint(original, root),
            )
            rendered = baseline_path.read_text(encoding="utf-8")
            self.assertNotIn("target.call", rendered)
            self.assertNotIn(str(root), rendered)

    def test_comparison_classifies_new_existing_and_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / ".holes-baseline.json"
            existing = finding(root / "Existing.sol", line=10)
            resolved = finding(root / "Resolved.sol", line=20)
            write_baseline([existing, resolved], baseline_path)
            new = finding(root / "New.sol", line=30)

            comparison = compare_baseline(
                [existing, new],
                load_baseline(baseline_path),
                baseline_path,
            )

            self.assertEqual(comparison.new_findings, (new,))
            self.assertEqual(comparison.existing_findings, (existing,))
            self.assertEqual(len(comparison.resolved_fingerprints), 1)
            self.assertEqual(
                comparison.summary(),
                {"new": 1, "existing": 1, "resolved": 1},
            )

    def test_create_refuses_overwrite_but_update_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            first = finding(Path(directory) / "First.sol")
            second = finding(Path(directory) / "Second.sol")
            write_baseline([first], baseline_path)

            with self.assertRaisesRegex(BaselineError, "refusing to overwrite"):
                write_baseline([second], baseline_path)
            write_baseline([second], baseline_path, overwrite=True)

            loaded = load_baseline(baseline_path)
            self.assertEqual(loaded["findings"][0]["path"], "Second.sol")
            self.assertEqual(list(baseline_path.parent.glob("*.tmp")), [])

    def test_invalid_or_duplicate_baseline_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "baseline_version": "1.0",
                        "path_base": "baseline-directory",
                        "findings": [
                            {"fingerprint": "same"},
                            {"fingerprint": "same"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(BaselineError, "duplicate"):
                load_baseline(path)

    def test_cli_baseline_reports_and_gates_only_new_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / ".holes-baseline.json"
            existing = finding(root / "Existing.sol")
            new = finding(root / "New.sol")
            write_baseline([existing], baseline_path)

            output = io.StringIO()
            errors = io.StringIO()
            with (
                patch(
                    "contract_holes.cli.Scanner.scan_paths",
                    return_value=([existing], 1),
                ),
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(errors),
            ):
                status = main(
                    [
                        "contracts",
                        "--no-config",
                        "--baseline",
                        str(baseline_path),
                        "--format",
                        "json",
                        "--fail-on",
                        "high",
                    ]
                )

            self.assertEqual(status, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["finding_count"], 0)
            self.assertEqual(
                payload["baseline"],
                {
                    "path": str(baseline_path),
                    "new": 0,
                    "existing": 1,
                    "resolved": 0,
                },
            )
            self.assertIn("0 new, 1 existing", errors.getvalue())

            output = io.StringIO()
            with (
                patch(
                    "contract_holes.cli.Scanner.scan_paths",
                    return_value=([existing, new], 2),
                ),
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                status = main(
                    [
                        "contracts",
                        "--no-config",
                        "--baseline",
                        str(baseline_path),
                        "--format",
                        "json",
                        "--fail-on",
                        "high",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(status, 1)
            self.assertEqual(payload["finding_count"], 1)
            self.assertEqual(payload["findings"][0]["path"], str(new.path))

    def test_cli_creates_refuses_and_explicitly_updates_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / "baseline.json"
            current = finding(root / "Vault.sol")

            def run(option: str) -> tuple[int, str]:
                errors = io.StringIO()
                with (
                    patch(
                        "contract_holes.cli.Scanner.scan_paths",
                        return_value=([current], 1),
                    ),
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(errors),
                ):
                    status = main(
                        [
                            "contracts",
                            "--no-config",
                            option,
                            str(baseline_path),
                            "--format",
                            "json",
                        ]
                    )
                return status, errors.getvalue()

            self.assertEqual(run("--write-baseline")[0], 0)
            status, errors = run("--write-baseline")
            self.assertEqual(status, 2)
            self.assertIn("refusing to overwrite", errors)
            self.assertEqual(run("--update-baseline")[0], 0)


if __name__ == "__main__":
    unittest.main()
