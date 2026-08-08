import contextlib
import io
import json
import unittest
from unittest.mock import patch

from contract_holes.cli import main
from contract_holes.inspector import InspectionError, InspectionFilters


class CliTests(unittest.TestCase):
    def test_json_output_and_fail_threshold(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                [
                    "tests/fixtures/VulnerableVault.sol",
                    "--format",
                    "json",
                    "--fail-on",
                    "high",
                ]
            )

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())["finding_count"], 7)

    def test_safe_contract_exits_successfully(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["tests/fixtures/SafeVault.sol", "--no-color"])

        self.assertEqual(status, 0)
        self.assertIn("No findings", output.getvalue())

    def test_inspect_command_emits_json_and_forwards_filters(self) -> None:
        output = io.StringIO()
        payload = {"schema_version": "1.0", "summary": {"functions": 1}}
        with (
            patch("contract_holes.cli.inspect_paths", return_value=payload) as inspect,
            contextlib.redirect_stdout(output),
        ):
            status = main(
                [
                    "inspect",
                    "contracts",
                    "--offline",
                    "--file",
                    "Vault.sol",
                    "--contract",
                    "Vault",
                    "--function",
                    "withdraw",
                ]
            )

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), payload)
        inspect.assert_called_once_with(
            ["contracts"],
            include_dependencies=False,
            offline=True,
            filters=InspectionFilters.create(
                files=["Vault.sol"],
                contracts=["Vault"],
                functions=["withdraw"],
            ),
        )

    def test_inspect_command_reports_compiler_errors_separately(self) -> None:
        errors = io.StringIO()
        with (
            patch(
                "contract_holes.cli.inspect_paths",
                side_effect=InspectionError("compiler unavailable"),
            ),
            contextlib.redirect_stderr(errors),
        ):
            status = main(["inspect", "contracts"])

        self.assertEqual(status, 2)
        self.assertIn("holes inspect: error: compiler unavailable", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
