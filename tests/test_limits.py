from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.compiler import CompilerError, ForgeCompiler
from contract_holes.limits import ScanLimits
from contract_holes.scanner import ScanError, Scanner


class ScanLimitTests(unittest.TestCase):
    def test_limits_reject_invalid_values(self) -> None:
        invalid = (
            {"max_files": 0},
            {"max_source_bytes": -1},
            {"compiler_timeout_seconds": float("inf")},
            {"scan_timeout_seconds": 0},
            {"max_python_memory_bytes": True},
            {"compiler_timeout_seconds": 2, "scan_timeout_seconds": 1},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                ScanLimits(**values)

    def test_file_count_limit_stops_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.sol").write_text("contract A {}", encoding="utf-8")
            (root / "B.sol").write_text("contract B {}", encoding="utf-8")
            scanner = Scanner(limits=ScanLimits(max_files=1))

            with self.assertRaisesRegex(ScanError, r"\[files\]"):
                scanner.scan_paths([root])

    def test_total_source_byte_limit_stops_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Large.sol"
            source.write_text("contract Large {}", encoding="utf-8")
            scanner = Scanner(limits=ScanLimits(max_source_bytes=4))

            with self.assertRaisesRegex(ScanError, r"\[source-bytes\]"):
                scanner.scan_paths([source])

    def test_total_scan_time_is_checked_between_phases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Slow.sol"
            source.write_text("contract Slow {}", encoding="utf-8")
            scanner = Scanner(
                limits=ScanLimits(
                    compiler_timeout_seconds=0.5,
                    scan_timeout_seconds=1,
                )
            )

            with (
                patch(
                    "contract_holes.scanner.time.monotonic",
                    side_effect=(0.0, 2.0),
                ),
                self.assertRaisesRegex(ScanError, r"\[scan-time\]"),
            ):
                scanner.scan_paths([source])

    def test_python_peak_memory_limit_is_checked_between_phases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Memory.sol"
            source.write_text("contract Memory {}", encoding="utf-8")
            scanner = Scanner(limits=ScanLimits(max_python_memory_bytes=1))

            with self.assertRaisesRegex(ScanError, r"\[python-memory\]"):
                scanner.scan_paths([source])

    def test_foundry_compilation_has_a_hard_timeout(self) -> None:
        with (
            patch("contract_holes.compiler.shutil.which", return_value="/usr/bin/forge"),
            patch(
                "contract_holes.compiler.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["forge"], 0.25),
            ),
        ):
            with self.assertRaisesRegex(
                CompilerError, r"\[compiler-time\].*0\.25 seconds"
            ):
                ForgeCompiler(timeout=0.25).compile(
                    [Path("Example.sol")], project_root=Path.cwd()
                )


if __name__ == "__main__":
    unittest.main()
