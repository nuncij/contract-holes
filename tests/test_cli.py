import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from contract_holes.cli import main
from contract_holes.benchmark import BenchmarkError
from contract_holes.inspector import InspectionError, InspectionFilters
from contract_holes.models import Finding, Severity
from contract_holes.proof_runner import ProofRunnerError


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

    def test_generate_proofs_forwards_compiler_findings_to_generator(self) -> None:
        finding = Finding(
            rule_id="SOL005",
            severity=Severity.HIGH,
            title="Reentrancy",
            message="interaction before write",
            path=Path("contracts/Vault.sol"),
            line=10,
            column=5,
            excerpt="target.call(\"\")",
            recommendation="update state first",
        )
        output = io.StringIO()
        errors = io.StringIO()
        with (
            patch(
                "contract_holes.cli.Scanner.scan_paths",
                return_value=([finding], 1),
            ),
            patch(
                "contract_holes.cli.generate_foundry_proofs",
                return_value=[Path("proofs/Vault_SOL005.t.sol")],
            ) as generate,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            status = main(
                [
                    "contracts",
                    "--compile",
                    "--generate-proofs",
                    "proofs",
                    "--no-color",
                ]
            )

        self.assertEqual(status, 0)
        generate.assert_called_once_with([finding], Path("proofs"))
        self.assertIn("wrote 1 Foundry proof test", errors.getvalue())

    def test_proofs_command_forwards_limits_and_returns_runner_status(self) -> None:
        output = io.StringIO()
        payload = {"schema_version": "1.0", "summary": {"all_passed": False}}
        with (
            patch(
                "contract_holes.cli.run_foundry_proofs",
                return_value=payload,
            ) as run,
            contextlib.redirect_stdout(output),
        ):
            status = main(
                [
                    "proofs",
                    "proofs-dir",
                    "--timeout",
                    "12.5",
                    "--allow-downloads",
                ]
            )

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue()), payload)
        run.assert_called_once_with(
            "proofs-dir",
            timeout_seconds=12.5,
            allow_downloads=True,
        )

    def test_proofs_command_reports_runner_configuration_errors(self) -> None:
        errors = io.StringIO()
        with (
            patch(
                "contract_holes.cli.run_foundry_proofs",
                side_effect=ProofRunnerError("bad manifest"),
            ),
            contextlib.redirect_stderr(errors),
        ):
            status = main(["proofs", "proofs-dir"])

        self.assertEqual(status, 2)
        self.assertIn("holes proofs: error: bad manifest", errors.getvalue())

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

    def test_benchmark_command_does_not_fail_for_performance_regressions(self) -> None:
        output = io.StringIO()
        payload = {
            "schema_version": "1.0",
            "correctness": {"status": "passed"},
            "performance_comparison": {
                "status": "reported",
                "regressions": ["modes.compiler.duration_seconds"],
            },
        }
        with (
            patch("contract_holes.cli.benchmark_paths", return_value=payload) as benchmark,
            contextlib.redirect_stdout(output),
        ):
            status = main(
                [
                    "benchmark",
                    "contracts",
                    "--offline",
                    "--expectations",
                    "expected.json",
                    "--baseline",
                    "previous.json",
                ]
            )

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), payload)
        benchmark.assert_called_once_with(
            ["contracts"],
            include_dependencies=False,
            offline=True,
            expectations_path="expected.json",
            baseline_path="previous.json",
        )

    def test_benchmark_command_fails_only_for_correctness_or_execution(self) -> None:
        failed = {"correctness": {"status": "failed"}}
        with (
            patch("contract_holes.cli.benchmark_paths", return_value=failed),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(main(["benchmark", "contracts"]), 1)

        errors = io.StringIO()
        with (
            patch(
                "contract_holes.cli.benchmark_paths",
                side_effect=BenchmarkError("no compiler"),
            ),
            contextlib.redirect_stderr(errors),
        ):
            self.assertEqual(main(["benchmark", "contracts"]), 2)
        self.assertIn("holes benchmark: error: no compiler", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
