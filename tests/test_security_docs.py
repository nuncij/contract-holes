import os
from pathlib import Path
import unittest
from unittest.mock import patch

from contract_holes.process_environment import sanitized_subprocess_environment


class SecurityDocumentationTests(unittest.TestCase):
    def test_security_policy_defines_private_reporting_and_response_targets(self) -> None:
        policy = Path("SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("Report a vulnerability privately", policy)
        self.assertIn("Security → Advisories", policy)
        self.assertIn("three business days", policy)
        self.assertIn("seven business days", policy)
        self.assertIn("every 14 days", policy)
        self.assertIn("docs/THREAT_MODEL.md", policy)
        self.assertIn("docs/SECURE_USE.md", policy)

    def test_threat_model_and_secure_use_cover_every_execution_boundary(self) -> None:
        threat_model = Path("docs/THREAT_MODEL.md").read_text(encoding="utf-8")
        secure_use = Path("docs/SECURE_USE.md").read_text(encoding="utf-8")

        for boundary in (
            "Source-only scanning",
            "Foundry and compiler mode",
            "Generated proofs",
            "Verified-source ingestion",
            "AI explanation",
            "Reports, baselines, suppressions, and CI",
        ):
            self.assertIn(boundary, threat_model)
        for guidance in (
            "least-privilege",
            "--offline",
            "private key",
            "Exit `0`",
            "production RPC",
            "Pin the scanner",
        ):
            self.assertIn(guidance, secure_use)

    def test_subprocess_environment_removes_common_secrets_and_requested_prefixes(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PATH": "/usr/bin",
                "OPENAI_API_KEY": "secret",
                "GITHUB_TOKEN": "secret",
                "SSH_AUTH_SOCK": "/tmp/agent",
                "FOUNDRY_ETH_RPC_URL": "https://rpc.invalid",
                "FOUNDRY_SOLC_VERSION": "0.8.25",
            },
            clear=True,
        ):
            compiler_environment = sanitized_subprocess_environment()
            proof_environment = sanitized_subprocess_environment(
                remove_prefixes=("FOUNDRY_",)
            )

        self.assertEqual(compiler_environment["PATH"], "/usr/bin")
        self.assertEqual(compiler_environment["FOUNDRY_SOLC_VERSION"], "0.8.25")
        self.assertNotIn("OPENAI_API_KEY", compiler_environment)
        self.assertNotIn("GITHUB_TOKEN", compiler_environment)
        self.assertNotIn("SSH_AUTH_SOCK", compiler_environment)
        self.assertNotIn("FOUNDRY_ETH_RPC_URL", compiler_environment)
        self.assertNotIn("FOUNDRY_SOLC_VERSION", proof_environment)


if __name__ == "__main__":
    unittest.main()
