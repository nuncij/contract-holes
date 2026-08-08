import json
from pathlib import Path
import shutil
import tempfile
import unittest

from contract_holes.proof_runner import (
    ProofRunnerError,
    proof_runner_exit_status,
    run_foundry_proofs,
)
from contract_holes.proofs import generate_foundry_proofs
from tests.test_proofs import packed_finding


def make_bundle(directory: Path) -> Path:
    return generate_foundry_proofs([packed_finding()], directory)[0]


def make_fake_forge(directory: Path, body: str) -> Path:
    executable = directory / "fake-forge"
    executable.write_text(f"#!/usr/bin/env python3\n{body}\n", encoding="utf-8")
    executable.chmod(0o755)
    return executable


class ProofRunnerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("forge"), "Foundry is required for proof tests")
    def test_runs_bundle_offline_without_modifying_proof_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root)
            before = sorted(path.name for path in root.iterdir())

            payload = run_foundry_proofs(root, timeout_seconds=30)

            self.assertEqual(proof_runner_exit_status(payload), 0)
            self.assertEqual(
                payload["summary"],
                {
                    "artifacts": 1,
                    "passed": 1,
                    "failed": 0,
                    "timed_out": 0,
                    "unsupported": 0,
                    "all_passed": True,
                },
            )
            self.assertEqual(payload["results"][0]["status"], "passed")
            self.assertIn("1 passed", payload["results"][0]["stdout"])
            self.assertEqual(
                sorted(path.name for path in root.iterdir()),
                before,
            )

    def test_failed_process_is_structured_and_isolated_path_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root)
            fake = make_fake_forge(
                root,
                """import pathlib
import sys
isolated = pathlib.Path(sys.argv[sys.argv.index("--root") + 1])
(isolated / "runner-marker").write_text("isolated")
print(isolated)
raise SystemExit(3)""",
            )

            payload = run_foundry_proofs(
                root,
                timeout_seconds=5,
                forge_executable=str(fake),
            )

            result = payload["results"][0]
            self.assertEqual(proof_runner_exit_status(payload), 1)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["exit_code"], 3)
            self.assertIn("<isolated-project>", result["stdout"])
            self.assertFalse((root / "runner-marker").exists())

    def test_timeout_is_reported_per_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root)
            fake = make_fake_forge(
                root,
                """import time
print("starting", flush=True)
time.sleep(1)""",
            )

            payload = run_foundry_proofs(
                root,
                timeout_seconds=0.05,
                forge_executable=str(fake),
            )

            result = payload["results"][0]
            self.assertEqual(result["status"], "timed_out")
            self.assertIsNone(result["exit_code"])
            self.assertIn("exceeded", result["diagnostic"])
            self.assertEqual(payload["summary"]["timed_out"], 1)

    def test_modified_source_hash_is_rejected_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = make_bundle(root)
            fake = make_fake_forge(root, "raise SystemExit(0)")
            proof.write_text("modified", encoding="utf-8")

            with self.assertRaisesRegex(ProofRunnerError, "hash does not match"):
                run_foundry_proofs(root, forge_executable=str(fake))

    def test_unsupported_profile_is_reported_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_bundle(root)
            fake = make_fake_forge(root, "raise SystemExit(99)")
            manifest_path = next(root.glob("*.proof.json"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["profiles"]["generated_tests"]["chain"]["mode"] = "fork"
            manifest_path.write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            payload = run_foundry_proofs(root, forge_executable=str(fake))

            self.assertEqual(payload["summary"]["unsupported"], 1)
            self.assertEqual(payload["results"][0]["status"], "unsupported")
            self.assertIn("only local", payload["results"][0]["diagnostic"])

    def test_requires_positive_timeout_and_manifest_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = make_fake_forge(root, "raise SystemExit(0)")
            with self.assertRaisesRegex(ProofRunnerError, "positive finite"):
                run_foundry_proofs(
                    root,
                    timeout_seconds=0,
                    forge_executable=str(fake),
                )
            with self.assertRaisesRegex(ProofRunnerError, "no .proof.json"):
                run_foundry_proofs(root, forge_executable=str(fake))


if __name__ == "__main__":
    unittest.main()
