from pathlib import Path
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


class ProofTests(unittest.TestCase):
    def test_generates_dependency_free_foundry_test(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            generated = generate_foundry_proofs([packed_finding()], Path(directory))

            self.assertEqual(len(generated), 1)
            content = generated[0].read_text(encoding="utf-8")
            self.assertIn("test_SOL007_packedEncodingCollision", content)
            self.assertIn('abi.encodePacked("a", "bc")', content)
            self.assertNotIn("forge-std", content)

    def test_generation_is_idempotent_but_does_not_overwrite_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generated = generate_foundry_proofs([packed_finding()], output)
            self.assertEqual(generate_foundry_proofs([packed_finding()], output), generated)

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


if __name__ == "__main__":
    unittest.main()
