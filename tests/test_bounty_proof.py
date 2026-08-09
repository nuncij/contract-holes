import contextlib
import io
from importlib.resources import files
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.bounty_candidates import list_candidates, synchronize_candidates
from contract_holes.bounty_proof import (
    BountyProofError,
    create_bounty_proof,
    load_bounty_proof,
    load_bounty_proof_result,
    parse_requirements,
)
from contract_holes.bounty_scope import scan_bounty_workspace
from contract_holes.cli import main
from tests.test_bounty_scope import create_source, directory_profile


class BountyProofTests(unittest.TestCase):
    def create_candidate(self, root: Path):
        create_source(root)
        profile = directory_profile(root)
        scan_bounty_workspace(profile.workspace)
        synchronize_candidates(profile.workspace)
        candidate_id = list_candidates(profile.workspace)["candidates"][0]["candidate_id"]
        return profile, candidate_id

    def test_unsupported_proof_records_unknowns_without_claiming_impact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile, candidate_id = self.create_candidate(Path(temporary))
            proof = create_bounty_proof(
                profile.workspace,
                candidate_id,
                requirements={"actors": "attacker and unprivileged user"},
                impact_assertion="Test whether authorization can be bypassed",
                run=True,
            )

            self.assertEqual(proof.manifest["generator"]["status"], "unsupported")
            self.assertEqual(proof.execution["status"], "unsupported")
            self.assertEqual(
                proof.manifest["requirements"]["actors"]["status"], "supplied"
            )
            self.assertEqual(
                proof.manifest["requirements"]["balances"]["status"], "unknown"
            )
            self.assertIn("primitive", proof.manifest["generator"]["meaning"])
            self.assertIsNone(proof.manifest["execution_policy"]["remote_rpc"])
            self.assertIsNone(proof.manifest["execution_policy"]["wallet"])
            self.assertTrue(proof.manifest["compiler"]["offline"])

    def test_generated_proof_execution_is_normalized_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile, candidate_id = self.create_candidate(Path(temporary))

            def fake_generate(findings, output):
                source = output / "Candidate_SOL001.t.sol"
                source.write_text("contract Proof {}\n", encoding="utf-8")
                manifest = output / "Candidate_SOL001.proof.json"
                manifest.write_text('{"schema_version":"1.0"}\n', encoding="utf-8")
                return [source]

            runner = {
                "schema_version": "1.0",
                "runner_version": "1.0",
                "proof_directory": str(profile.workspace),
                "summary": {
                    "artifacts": 1,
                    "passed": 1,
                    "failed": 0,
                    "timed_out": 0,
                    "unsupported": 0,
                    "all_passed": True,
                },
                "results": [
                    {
                        "manifest": "Candidate_SOL001.proof.json",
                        "status": "passed",
                        "duration_seconds": 1.234,
                        "stdout": f"ok in {profile.workspace}",
                        "stderr": "",
                    }
                ],
            }
            with (
                patch(
                    "contract_holes.bounty_proof.generate_foundry_proofs",
                    side_effect=fake_generate,
                ),
                patch(
                    "contract_holes.bounty_proof.run_foundry_proofs",
                    return_value=runner,
                ) as run,
            ):
                proof = create_bounty_proof(
                    profile.workspace,
                    candidate_id,
                    requirements={"deployment": "deploy local fixture"},
                    impact_assertion="Unauthorized state transition",
                    run=True,
                )

            run.assert_called_once()
            self.assertFalse(run.call_args.kwargs["allow_downloads"])
            self.assertEqual(proof.execution["status"], "passed")
            self.assertNotIn("duration_seconds", proof.execution["results"][0])
            self.assertNotIn(str(profile.workspace), json.dumps(proof.execution))
            context = __import__(
                "contract_holes.bounty_candidates", fromlist=["load_candidate_context"]
            ).load_candidate_context(profile.workspace, candidate_id)
            directory, loaded = load_bounty_proof(
                context, proof.manifest["proof_sha256"]
            )
            result = load_bounty_proof_result(
                context, proof.manifest["proof_sha256"]
            )
            self.assertEqual(directory, proof.directory)
            self.assertEqual(loaded, proof.manifest)
            self.assertEqual(result, proof.execution)

            generated = next(
                path
                for path in proof.directory.iterdir()
                if path.name.endswith(".t.sol")
            )
            generated.write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(BountyProofError, "hash changed"):
                load_bounty_proof(context, proof.manifest["proof_sha256"])

    def test_requirements_reject_unknown_or_secret_values(self) -> None:
        with self.assertRaisesRegex(BountyProofError, "unknown proof requirement"):
            parse_requirements(["rpc=anything"])
        with self.assertRaisesRegex(BountyProofError, "credential or secret"):
            parse_requirements(["deployment=password=hunter2"])
        with self.assertRaisesRegex(BountyProofError, "unique"):
            parse_requirements(["actors=one", "actors=two"])

    def test_proof_schemas_are_packaged(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        manifest = json.loads(
            schema_directory.joinpath("bounty-proof-1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        result = json.loads(
            schema_directory.joinpath(
                "bounty-proof-result-1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(result["properties"]["schema_version"]["const"], "1.0")


class BountyProofCliTests(unittest.TestCase):
    def test_cli_creates_unsupported_local_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root)
            profile = directory_profile(root)
            scan_bounty_workspace(profile.workspace)
            synchronize_candidates(profile.workspace)
            candidate_id = list_candidates(profile.workspace)["candidates"][0]["candidate_id"]

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "bounty",
                        "proof",
                        str(profile.workspace),
                        candidate_id,
                        "--requirement",
                        "actors=unprivileged caller",
                        "--impact-assertion",
                        "Authorization bypass",
                        "--run",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["command"], "bounty.proof")
            self.assertEqual(payload["execution"]["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
