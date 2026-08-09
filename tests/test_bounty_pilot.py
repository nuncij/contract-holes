import contextlib
import io
from importlib.resources import files
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.bounty_io import payload_sha256
from contract_holes.bounty_pilot import (
    BountyPilotError,
    load_bounty_pilot_manifest,
    run_bounty_pilot,
)
from contract_holes.cli import main


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/fixtures/bounty_pilot/manifest.json"
EXPECTED = ROOT / "evaluation/bounty-pilot-1.0.json"


class BountyPilotTests(unittest.TestCase):
    def test_manifest_pins_rules_authorization_scope_and_source(self) -> None:
        manifest = load_bounty_pilot_manifest(MANIFEST)
        self.assertTrue(manifest["program"]["authorization_acknowledged"])
        self.assertEqual(
            manifest["target"]["scope_paths"],
            ["src/AuthorizedPilotVault.sol"],
        )
        self.assertEqual(
            {decision["rule_id"] for decision in manifest["decisions"].values()},
            {"SOL001", "SOL002"},
        )
        self.assertEqual(len(manifest["target"]["content_sha256"]), 64)

    def test_complete_pilot_matches_versioned_result_and_stays_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "pilot"
            result = run_bounty_pilot(MANIFEST, output)
            expected = json.loads(EXPECTED.read_text(encoding="utf-8"))

            self.assertEqual(result, expected)
            self.assertEqual(result["status"], "passed")
            self.assertTrue(all(result["gate_checks"].values()))
            self.assertEqual(result["metrics"]["candidate_count"], 2)
            self.assertEqual(result["metrics"]["rejected_count"], 1)
            self.assertEqual(result["metrics"]["safety_failure_count"], 0)
            material = dict(result)
            digest = material.pop("result_sha256")
            self.assertEqual(digest, payload_sha256(material))
            rendered = json.dumps(result)
            self.assertNotIn(str(ROOT), rendered)
            self.assertNotIn(str(output), rendered)
            self.assertFalse((output / "local-export" / "submit.json").exists())
            self.assertTrue((output / "workspace" / "reviews.json").is_file())
            self.assertTrue((output / "local-export" / "report.md").is_file())
            if os.name == "posix":
                self.assertEqual(output.stat().st_mode & 0o777, 0o700)
                self.assertEqual(
                    (output / "pilot-result.json").stat().st_mode & 0o777,
                    0o600,
                )

    def test_repeated_outputs_are_deterministic_and_use_no_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = run_bounty_pilot(MANIFEST, root / "first")
            with (
                patch.object(
                    socket,
                    "create_connection",
                    side_effect=AssertionError("network connection attempted"),
                ),
                patch.object(
                    socket,
                    "socket",
                    side_effect=AssertionError("network socket attempted"),
                ),
            ):
                second = run_bounty_pilot(MANIFEST, root / "second")
            self.assertEqual(first, second)
            self.assertFalse(second["execution_policy"]["target_contact"])
            self.assertFalse(second["execution_policy"]["submitted"])

    def test_tampering_missing_authorization_and_overwrite_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            shutil.copytree(MANIFEST.parent, fixture)
            source = fixture / "target/src/AuthorizedPilotVault.sol"
            source.write_text(
                source.read_text(encoding="utf-8") + "\n// changed\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BountyPilotError, "content SHA-256 changed"):
                load_bounty_pilot_manifest(fixture / "manifest.json")

        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            shutil.copytree(MANIFEST.parent, fixture)
            manifest_path = fixture / "manifest.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["program"]["authorization_acknowledged"] = False
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(BountyPilotError, "explicitly acknowledged"):
                load_bounty_pilot_manifest(manifest_path)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "existing"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("keep\n", encoding="utf-8")
            with self.assertRaisesRegex(BountyPilotError, "already exists"):
                run_bounty_pilot(MANIFEST, output)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep\n")

        if hasattr(os, "symlink"):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest_link = root / "manifest.json"
                manifest_link.symlink_to(MANIFEST)
                with self.assertRaisesRegex(BountyPilotError, "manifest must not"):
                    load_bounty_pilot_manifest(manifest_link)

            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                redirect = root / "redirect"
                output = root / "output"
                output.symlink_to(redirect)
                with self.assertRaisesRegex(BountyPilotError, "must not be a symlink"):
                    run_bounty_pilot(MANIFEST, output)

            with tempfile.TemporaryDirectory() as temporary:
                fixture = Path(temporary) / "fixture"
                shutil.copytree(MANIFEST.parent, fixture)
                rules = fixture / "RULES.md"
                rules_copy = fixture / "RULES-COPY.md"
                rules_copy.write_bytes(rules.read_bytes())
                rules.unlink()
                rules.symlink_to(rules_copy.name)
                with self.assertRaisesRegex(BountyPilotError, "must not contain a symlink"):
                    load_bounty_pilot_manifest(fixture / "manifest.json")

        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            shutil.copytree(MANIFEST.parent, fixture)
            manifest_path = fixture / "manifest.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["timeline"]["report_created_at"] = "2026-08-09T10:04:30Z"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(BountyPilotError, "both review decisions"):
                load_bounty_pilot_manifest(manifest_path)

    def test_pilot_schemas_are_packaged(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        manifest = json.loads(
            schema_directory.joinpath(
                "bounty-pilot-manifest-1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        result = json.loads(
            schema_directory.joinpath(
                "bounty-pilot-result-1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(result["properties"]["schema_version"]["const"], "1.0")


class BountyPilotCliTests(unittest.TestCase):
    def test_cli_runs_local_authorized_pilot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = io.StringIO()
            destination = Path(temporary) / "pilot"
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "bounty",
                        "pilot",
                        str(MANIFEST),
                        "--output",
                        str(destination),
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["status"], "passed")
            self.assertFalse(payload["execution_policy"]["automatic_submission"])
            self.assertTrue((destination / "pilot-result.json").is_file())


if __name__ == "__main__":
    unittest.main()
