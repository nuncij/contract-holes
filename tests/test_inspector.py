from pathlib import Path
import tempfile
import unittest

from contract_holes.inspector import InspectionError, inspect_paths


class InspectorTests(unittest.TestCase):
    def test_empty_directory_is_actionable_without_starting_compiler(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                InspectionError, "no Solidity source files found"
            ):
                inspect_paths([Path(directory)], offline=True)


if __name__ == "__main__":
    unittest.main()
