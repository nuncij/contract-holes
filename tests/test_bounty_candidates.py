import contextlib
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
from importlib.resources import files
import json
from pathlib import Path
import tempfile
import unittest

from contract_holes.bounty_candidates import (
    BountyCandidateError,
    candidate_identifier,
    list_candidates,
    review_candidate,
    synchronize_candidates,
)
from contract_holes.bounty_io import payload_sha256, rendered_json_bytes
from contract_holes.bounty_scope import scan_bounty_workspace
from contract_holes.cli import main
from tests.test_bounty_scope import create_source, directory_profile


class BountyCandidateTests(unittest.TestCase):
    def create_scanned_workspace(self, root: Path) -> Path:
        create_source(root)
        profile = directory_profile(root)
        scan_bounty_workspace(profile.workspace)
        synchronize_candidates(profile.workspace)
        return profile.workspace

    def test_candidate_identity_observation_and_ranking_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_scanned_workspace(Path(temporary))
            first = list_candidates(workspace)
            second = list_candidates(workspace)

            self.assertEqual(first, second)
            self.assertEqual(first["candidate_count"], 1)
            candidate = first["candidates"][0]
            self.assertRegex(candidate["candidate_id"], r"^BNT-[0-9a-f]{24}$")
            self.assertEqual(candidate["state"], "new")
            self.assertIsNone(candidate["review"])
            self.assertIn("observation", candidate)
            self.assertNotIn("state", candidate["observation"])
            priority = candidate["review_priority"]
            self.assertGreater(priority["score"], 0)
            self.assertEqual(
                priority["meaning"],
                "review ordering only; not exploitability, bounty severity, or payout",
            )
            self.assertIn("severity:high", priority["reason_codes"])
            self.assertNotIn("impact", priority["components"])

            finding = candidate["observation"]["finding"]
            changed = candidate_identifier(
                first["profile_sha256"],
                first["source_manifest_sha256"],
                "different-scanner",
                finding,
            )
            self.assertNotEqual(changed, candidate["candidate_id"])

    def test_human_state_machine_requires_reason_impact_and_ordered_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_scanned_workspace(Path(temporary))
            candidate_id = list_candidates(workspace)["candidates"][0]["candidate_id"]

            with self.assertRaisesRegex(BountyCandidateError, "invalid.*new -> confirmed"):
                review_candidate(
                    workspace,
                    candidate_id,
                    state="confirmed",
                    reason="looks real",
                    reviewer="alice",
                    impact="Loss of funds",
                    occurred_at="2026-08-09T10:00:00Z",
                )
            investigating = review_candidate(
                workspace,
                candidate_id,
                state="investigating",
                reason="Trace authorization and reachability",
                reviewer="alice",
                occurred_at="2026-08-09T10:00:00Z",
            )
            self.assertEqual(investigating["state"], "investigating")
            with self.assertRaisesRegex(BountyCandidateError, "requires.*impact"):
                review_candidate(
                    workspace,
                    candidate_id,
                    state="confirmed",
                    reason="Reproduced",
                    reviewer="alice",
                    occurred_at="2026-08-09T10:01:00Z",
                )
            confirmed = review_candidate(
                workspace,
                candidate_id,
                state="confirmed",
                reason="Local reproduction demonstrates authorization bypass",
                reviewer="alice",
                impact="Unauthorized privileged operation",
                occurred_at="2026-08-09T10:01:00Z",
            )
            self.assertEqual(confirmed["state"], "confirmed")
            self.assertEqual(len(confirmed["history"]), 2)
            self.assertEqual(
                list_candidates(workspace, states=["confirmed"])["candidate_count"],
                1,
            )
            with self.assertRaisesRegex(BountyCandidateError, "approval workflow"):
                review_candidate(
                    workspace,
                    candidate_id,
                    state="approved",
                    reason="not enough",
                    reviewer="alice",
                    occurred_at="2026-08-09T10:02:00Z",
                )

    def test_rejected_review_survives_rescan_and_inactive_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_scanned_workspace(Path(temporary))
            candidate_id = list_candidates(workspace)["candidates"][0]["candidate_id"]
            review_candidate(
                workspace,
                candidate_id,
                state="rejected",
                reason="Guard dominates the reported source pattern",
                reviewer="bob",
                occurred_at="2026-08-09T11:00:00Z",
            )
            synchronize_candidates(workspace)
            self.assertEqual(
                list_candidates(workspace)["candidates"][0]["state"], "rejected"
            )

            scan_path = workspace / "scan.json"
            scan = json.loads(scan_path.read_text(encoding="utf-8"))
            scan["report"]["findings"] = []
            scan["report"]["finding_count"] = 0
            scan.pop("scan_sha256")
            scan["scan_sha256"] = payload_sha256(scan)
            scan_path.write_bytes(rendered_json_bytes(scan))
            synchronize_candidates(workspace)
            candidate = list_candidates(workspace)["candidates"][0]
            self.assertFalse(candidate["active"])
            self.assertEqual(candidate["state"], "rejected")
            self.assertEqual(len(candidate["review"]["history"]), 1)

    def test_tampered_candidate_or_review_digest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_scanned_workspace(Path(temporary))
            candidate_id = list_candidates(workspace)["candidates"][0]["candidate_id"]
            review_candidate(
                workspace,
                candidate_id,
                state="investigating",
                reason="Review",
                reviewer="alice",
                occurred_at="2026-08-09T12:00:00Z",
            )
            reviews_path = workspace / "reviews.json"
            reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
            reviews["reviews"][0]["reason"] = "tampered"
            reviews_path.write_text(json.dumps(reviews), encoding="utf-8")
            with self.assertRaisesRegex(BountyCandidateError, "integrity digest"):
                list_candidates(workspace)

    def test_candidate_and_review_schemas_are_packaged(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        candidates = json.loads(
            schema_directory.joinpath("bounty-candidates-1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        reviews = json.loads(
            schema_directory.joinpath("bounty-reviews-1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(candidates["properties"]["schema_version"]["const"], "1.0")
        self.assertIn(
            "confirmed",
            reviews["properties"]["reviews"]["items"]["properties"]["state"]["enum"],
        )


class BountyCandidateCliTests(unittest.TestCase):
    def test_scan_creates_candidates_and_review_command_records_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root)
            profile = directory_profile(root)
            with contextlib.redirect_stdout(io.StringIO()):
                status = main(["bounty", "scan", str(profile.workspace)])
            self.assertEqual(status, 0)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["bounty", "candidates", str(profile.workspace)])
            listing = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            candidate_id = listing["candidates"][0]["candidate_id"]

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "bounty",
                        "review",
                        str(profile.workspace),
                        candidate_id,
                        "--state",
                        "investigating",
                        "--reason",
                        "Manual trace started",
                        "--reviewer",
                        "alice",
                        "--at",
                        "2026-08-09T13:00:00Z",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["command"], "bounty.review")
            self.assertEqual(payload["review"]["state"], "investigating")


if __name__ == "__main__":
    unittest.main()
