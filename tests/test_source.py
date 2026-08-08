from pathlib import Path
import unittest

from contract_holes.source import SoliditySource, mask_comments_and_strings


class MaskingTests(unittest.TestCase):
    def test_mask_preserves_length_and_newlines(self) -> None:
        source = 'tx.origin; // tx.origin\nstring x = "tx.origin"; /* hi\nthere */\n'
        masked = mask_comments_and_strings(source)

        self.assertEqual(len(masked), len(source))
        self.assertEqual(masked.count("\n"), source.count("\n"))
        self.assertEqual(masked.count("tx.origin"), 1)

    def test_extracts_contract_functions_and_state(self) -> None:
        source = SoliditySource.from_path(Path("tests/fixtures/VulnerableVault.sol"))

        self.assertEqual(len(source.contracts), 1)
        self.assertIn("balances", source.contracts[0].state_variables)
        self.assertIn("implementation", source.contracts[0].state_variables)
        self.assertIn("withdraw", {function.name for function in source.functions})

    def test_location_is_one_based(self) -> None:
        source = SoliditySource(Path("Inline.sol"), "one\ntwo\n")
        self.assertEqual(source.location(4), (2, 1))


if __name__ == "__main__":
    unittest.main()

