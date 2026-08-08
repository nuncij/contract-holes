from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from contract_holes.models import Finding, Severity
from contract_holes.proofs import ProofGenerationError, generate_foundry_proofs


def packed_finding() -> Finding:
    return Finding(
        rule_id="SOL007",
        severity=Severity.MEDIUM,
        title="Packed collision",
        message="ambiguous",
        path=Path("contracts/Auth.sol"),
        line=42,
        column=9,
        excerpt="keccak256(abi.encodePacked(a, b))",
        recommendation="use abi.encode",
    )


def reentrancy_finding() -> Finding:
    return Finding(
        rule_id="SOL005",
        severity=Severity.HIGH,
        title="Reentrancy ordering",
        message="interaction precedes state update",
        path=Path("contracts/Vault.sol"),
        line=18,
        column=9,
        excerpt="recipient.call{value: amount}(\"\")",
        recommendation="apply checks-effects-interactions",
        confidence="medium",
        metadata={
            "evidence": "compiler-interprocedural-data-flow",
            "entry_function": "Vault.withdraw",
            "interaction_function": "Vault._pay",
            "state_write_function": "Vault._record",
            "state_variable": "balances",
            "trace": [
                {"kind": "call"},
                {"kind": "interaction"},
                {"kind": "write"},
            ],
        },
    )


class ProofTests(unittest.TestCase):
    def test_generates_dependency_free_foundry_test(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            generated = generate_foundry_proofs([packed_finding()], Path(directory))

            self.assertEqual(len(generated), 1)
            content = generated[0].read_text(encoding="utf-8")
            self.assertIn("test_SOL007_packedEncodingCollision", content)
            self.assertIn('abi.encodePacked("a", "bc")', content)
            self.assertNotIn("forge-std", content)

    def test_generates_configurable_reentrancy_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            generated = generate_foundry_proofs(
                [reentrancy_finding()], Path(directory)
            )

            self.assertEqual(len(generated), 1)
            content = generated[0].read_text(encoding="utf-8")
            self.assertIn("function run(", content)
            self.assertIn("bytes calldata reentryCalldata_", content)
            self.assertIn("test_SOL005_reentrancyPrimitive", content)
            self.assertIn("function runSequence(", content)
            self.assertIn("bytes[] calldata calls_", content)
            self.assertIn("MAX_SEQUENCE_STEPS = 32", content)
            self.assertIn("testFuzz_SOL005_transactionSequence", content)
            self.assertIn("entry Vault.withdraw", content)
            self.assertIn("later write Vault._record.balances", content)
            self.assertIn("not by itself proof of protocol impact", content)
            self.assertNotIn("forge-std", content)

    @unittest.skipUnless(shutil.which("forge"), "Foundry is required for proof tests")
    def test_reentrancy_probe_compiles_and_executes_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test_directory = root / "test"
            test_directory.mkdir()
            (root / "src").mkdir()
            (root / "foundry.toml").write_text(
                """[profile.default]
src = "src"
test = "test"
libs = []
solc_version = "0.8.25"
""",
                encoding="utf-8",
            )
            generate_foundry_proofs([reentrancy_finding()], test_directory)

            result = subprocess.run(
                ["forge", "test", "--root", str(root), "--offline"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("3 passed", result.stdout)

    def test_generates_user_supplied_invariant_api_and_assertion_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            generated = generate_foundry_proofs(
                [reentrancy_finding()], Path(directory)
            )
            content = generated[0].read_text(encoding="utf-8")

            self.assertIn("function check(address target_)", content)
            self.assertIn("function runSequenceWithInvariant(", content)
            self.assertIn("event HolesInvariantAssertion(", content)
            self.assertIn("error HolesInvariantViolation(", content)
            self.assertIn("function assertLastInvariant()", content)
            self.assertIn("test_SOL005_invariantReportsViolation", content)

    def test_generation_is_idempotent_but_does_not_overwrite_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generated = generate_foundry_proofs([packed_finding()], output)
            self.assertEqual(
                generate_foundry_proofs([packed_finding()], output), generated
            )

            generated[0].write_text("user modification", encoding="utf-8")
            with self.assertRaisesRegex(ProofGenerationError, "refusing to overwrite"):
                generate_foundry_proofs([packed_finding()], output)

    def test_unsupported_findings_do_not_create_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proofs"
            finding = packed_finding()
            unsupported = Finding(
                rule_id="SOL001",
                severity=finding.severity,
                title=finding.title,
                message=finding.message,
                path=finding.path,
                line=finding.line,
                column=finding.column,
                excerpt=finding.excerpt,
                recommendation=finding.recommendation,
            )
            self.assertEqual(generate_foundry_proofs([unsupported], output), [])
            self.assertFalse(output.exists())

    def test_source_only_reentrancy_signal_is_not_treated_as_a_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proofs"
            finding = reentrancy_finding()
            unsupported = Finding(
                rule_id=finding.rule_id,
                severity=finding.severity,
                title=finding.title,
                message=finding.message,
                path=finding.path,
                line=finding.line,
                column=finding.column,
                excerpt=finding.excerpt,
                recommendation=finding.recommendation,
                metadata={"evidence": "source-heuristic"},
            )
            self.assertEqual(generate_foundry_proofs([unsupported], output), [])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
