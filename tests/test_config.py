import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.cli import main
from contract_holes.config import (
    ConfigError,
    discover_config,
    load_config,
    selected_rules,
)
from contract_holes.models import Severity
from contract_holes.limits import ScanLimits


class ConfigTests(unittest.TestCase):
    def test_loads_paths_rules_severities_and_compiler_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / ".holes.toml"
            config_path.write_text(
                """schema_version = 1

[scan]
paths = ["contracts", "src/Vault.sol"]
exclude = ["generated/**", "*.skip.sol"]
include_dependencies = true
minimum_severity = "medium"

[rules]
enabled = ["SOL005"]
disabled = ["SOL007"]

[rules.severity]
SOL005 = "critical"

[compiler]
enabled = true
offline = true

[limits]
max_files = 42
max_source_bytes = 4096
compiler_timeout_seconds = 2.5
scan_timeout_seconds = 8
max_python_memory_mb = 64
""",
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(
                config.paths,
                ((root / "contracts").resolve(), (root / "src/Vault.sol").resolve()),
            )
            self.assertEqual(config.exclude, ("generated/**", "*.skip.sol"))
            self.assertTrue(config.include_dependencies)
            self.assertEqual(config.minimum_severity, Severity.MEDIUM)
            self.assertEqual(
                [rule.info.rule_id for rule in selected_rules(config)],
                ["SOL005"],
            )
            self.assertEqual(config.severity_overrides, {"SOL005": Severity.CRITICAL})
            self.assertTrue(config.compiler_enabled)
            self.assertTrue(config.compiler_offline)
            self.assertEqual(
                config.limits,
                ScanLimits(
                    max_files=42,
                    max_source_bytes=4096,
                    compiler_timeout_seconds=2.5,
                    scan_timeout_seconds=8,
                    max_python_memory_bytes=64 * 1024 * 1024,
                ),
            )

    def test_discovers_nearest_parent_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / ".holes.toml"
            expected.write_text("schema_version = 1\n", encoding="utf-8")
            nested = root / "a" / "b"
            nested.mkdir(parents=True)

            self.assertEqual(discover_config(nested), expected)

    def test_rejects_unknown_conflicting_and_invalid_settings(self) -> None:
        cases = {
            "unknown": "[scan]\nunknown = true\n",
            "unknown rule": '[rules]\nenabled = ["SOL999"]\n',
            "overlap": (
                '[rules]\nenabled = ["SOL005"]\n'
                'disabled = ["SOL005"]\n'
            ),
            "offline": "[compiler]\nenabled = false\noffline = true\n",
            "severity": '[scan]\nminimum_severity = "urgent"\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, content in cases.items():
                with self.subTest(label=label):
                    path = root / f"{label}.toml"
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(path)

    def test_cli_uses_config_paths_rule_selection_and_severity_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contracts = root / "contracts"
            contracts.mkdir()
            (contracts / "Configured.sol").write_text(
                """pragma solidity ^0.8.20;
contract Configured {
    function destroy() external { selfdestruct(payable(msg.sender)); }
    function origin() external view returns (bool) { return tx.origin == msg.sender; }
}
""",
                encoding="utf-8",
            )
            (contracts / "Ignored.skip.sol").write_text(
                """pragma solidity ^0.8.20;
contract Ignored { function destroy() external { selfdestruct(payable(msg.sender)); } }
""",
                encoding="utf-8",
            )
            config = root / ".holes.toml"
            config.write_text(
                """[scan]
paths = ["contracts"]
exclude = ["*.skip.sol"]
minimum_severity = "critical"

[rules]
enabled = ["SOL004"]

[rules.severity]
SOL004 = "critical"
""",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                status = main(["--config", str(config), "--format", "json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["files_scanned"], 1)
            self.assertEqual(payload["finding_count"], 1)
            self.assertEqual(payload["findings"][0]["rule_id"], "SOL004")
            self.assertEqual(payload["findings"][0]["severity"], "critical")

    def test_explicit_no_compile_overrides_compiler_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".holes.toml"
            config.write_text(
                """[scan]
paths = ["contracts"]

[compiler]
enabled = true
offline = true
""",
                encoding="utf-8",
            )
            with (
                patch(
                    "contract_holes.cli.Scanner.scan_paths",
                    return_value=([], 1),
                ) as scan,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                status = main(
                    ["--config", str(config), "--no-compile", "--format", "json"]
                )

            self.assertEqual(status, 0)
            scan.assert_called_once_with(
                [(root / "contracts").resolve()],
                minimum_severity=Severity.INFO,
                include_dependencies=False,
                exclude_patterns=(),
                compile_sources=False,
                compiler_offline=False,
            )

    def test_cli_resource_limit_overrides_are_passed_to_scanner(self) -> None:
        with (
            patch("contract_holes.cli.Scanner") as scanner_type,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            scanner_type.return_value.scan_paths.return_value = ([], 1)
            status = main(
                [
                    "Example.sol",
                    "--no-config",
                    "--format",
                    "json",
                    "--max-files",
                    "7",
                    "--max-source-bytes",
                    "8192",
                    "--compiler-timeout",
                    "3.5",
                    "--scan-timeout",
                    "9",
                    "--max-memory-mb",
                    "32",
                ]
            )

        self.assertEqual(status, 0)
        self.assertEqual(
            scanner_type.call_args.kwargs["limits"],
            ScanLimits(
                max_files=7,
                max_source_bytes=8192,
                compiler_timeout_seconds=3.5,
                scan_timeout_seconds=9,
                max_python_memory_bytes=32 * 1024 * 1024,
            ),
        )


if __name__ == "__main__":
    unittest.main()
