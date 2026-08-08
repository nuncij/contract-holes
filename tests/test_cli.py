import contextlib
import io
import json
import unittest

from contract_holes.cli import main


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


if __name__ == "__main__":
    unittest.main()
