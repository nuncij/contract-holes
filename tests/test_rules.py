from pathlib import Path
import unittest

from contract_holes.scanner import Scanner
from contract_holes.source import SoliditySource


FIXTURES = Path("tests/fixtures")


class RuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scanner = Scanner()

    def test_vulnerable_fixture_triggers_every_initial_rule(self) -> None:
        source = SoliditySource.from_path(FIXTURES / "VulnerableVault.sol")
        findings = self.scanner.scan_source(source)
        by_rule = {finding.rule_id: finding for finding in findings}

        self.assertEqual(set(by_rule), {"SOL001", "SOL002", "SOL003", "SOL004", "SOL005", "SOL006"})
        self.assertEqual(by_rule["SOL005"].metadata["state_variable"], "balances")
        self.assertEqual(by_rule["SOL005"].metadata["function"], "withdraw")
        unchecked_kinds = {
            finding.metadata["call_kind"]
            for finding in findings
            if finding.rule_id == "SOL002"
        }
        self.assertEqual(unchecked_kinds, {"call", "delegatecall"})

    def test_cast_target_low_level_call_is_detected(self) -> None:
        source = SoliditySource(
            Path("Cast.sol"),
            "contract Cast { function ping(address target) external { payable(target).call(\"\"); } }",
        )
        findings = self.scanner.scan_source(source)
        self.assertIn("SOL002", {finding.rule_id for finding in findings})

    def test_safe_fixture_has_no_findings(self) -> None:
        source = SoliditySource.from_path(FIXTURES / "SafeVault.sol")
        self.assertEqual(self.scanner.scan_source(source), [])

    def test_comments_and_strings_do_not_trigger_rules(self) -> None:
        source = SoliditySource(
            Path("Comments.sol"),
            '''
            contract Comments {
                // tx.origin and selfdestruct(payable(msg.sender))
                string constant EXAMPLE = "target.delegatecall(payload)";
            }
            ''',
        )
        self.assertEqual(self.scanner.scan_source(source), [])

    def test_rule_can_be_suppressed_on_preceding_line(self) -> None:
        source = SoliditySource(
            Path("Suppressed.sol"),
            '''
            contract Suppressed {
                function owner() external view returns (address) {
                    // holes-ignore-next-line SOL001 -- legacy behavior
                    return tx.origin;
                }
            }
            ''',
        )
        self.assertEqual(self.scanner.scan_source(source), [])


if __name__ == "__main__":
    unittest.main()
