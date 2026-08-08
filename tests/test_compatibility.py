import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

from contract_holes.cli import main
from contract_holes.compatibility import (
    FOUNDRY_MAXIMUM_EXCLUSIVE,
    FOUNDRY_MINIMUM,
    REFERENCE_MATRIX,
    SUPPORTED_EVM_TARGETS,
    compatibility_payload,
    parse_version,
    version_is_supported,
)


class CompatibilityTests(unittest.TestCase):
    def test_version_parser_and_range_boundaries_are_explicit(self) -> None:
        self.assertEqual(parse_version("forge Version: 1.7.1-stable"), (1, 7, 1))
        self.assertEqual(parse_version("Version: 0.8.36+commit.abc"), (0, 8, 36))
        self.assertIsNone(parse_version("nightly unknown"))

        self.assertTrue(
            version_is_supported((1, 5, 0), FOUNDRY_MINIMUM, FOUNDRY_MAXIMUM_EXCLUSIVE)
        )
        self.assertTrue(
            version_is_supported((1, 7, 99), FOUNDRY_MINIMUM, FOUNDRY_MAXIMUM_EXCLUSIVE)
        )
        self.assertFalse(
            version_is_supported((1, 4, 9), FOUNDRY_MINIMUM, FOUNDRY_MAXIMUM_EXCLUSIVE)
        )
        self.assertFalse(
            version_is_supported((1, 8, 0), FOUNDRY_MINIMUM, FOUNDRY_MAXIMUM_EXCLUSIVE)
        )

    def test_payload_publishes_policy_matrix_and_observed_statuses(self) -> None:
        observed = [
            subprocess.CompletedProcess(
                ["forge", "--version"],
                0,
                "forge Version: 1.7.1-stable",
                "",
            ),
            subprocess.CompletedProcess(
                ["solc", "--version"],
                0,
                "Version: 0.8.36+commit.example",
                "",
            ),
        ]
        with (
            patch("contract_holes.compatibility.shutil.which", side_effect=lambda name: f"/bin/{name}"),
            patch("contract_holes.compatibility.subprocess.run", side_effect=observed),
        ):
            payload = compatibility_payload()

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["policy_version"], "1.0")
        self.assertEqual(payload["supported"]["python"]["minimum"], "3.10.0")
        self.assertEqual(
            payload["supported"]["solidity"]["maximum_exclusive"],
            "0.8.37",
        )
        self.assertEqual(payload["supported"]["evm_targets"], list(SUPPORTED_EVM_TARGETS))
        self.assertEqual(payload["reference_matrix"], list(REFERENCE_MATRIX))
        self.assertEqual(payload["observed"]["foundry"]["status"], "supported")
        self.assertEqual(payload["observed"]["solidity"]["version"], "0.8.36")

    def test_missing_optional_tools_are_reported_without_failing_command(self) -> None:
        output = io.StringIO()
        with (
            patch("contract_holes.compatibility.shutil.which", return_value=None),
            contextlib.redirect_stdout(output),
        ):
            status = main(["compatibility"])

        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["observed"]["foundry"]["status"], "unavailable")
        self.assertEqual(payload["observed"]["solidity"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
