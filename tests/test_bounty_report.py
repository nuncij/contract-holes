import contextlib
import io
from importlib.resources import files
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.bounty_candidates import (
    list_candidates,
    review_candidate,
    synchronize_candidates,
)
from contract_holes.bounty_report import (
    BountyReportError,
    approve_bounty_report,
    create_bounty_report,
    export_approved_report,
    load_bounty_report,
)
from contract_holes.bounty_io import BountyWorkspaceError
from contract_holes.bounty_scope import scan_bounty_workspace
from contract_holes.cli import main
from tests.test_bounty_scope import create_source, directory_profile


def report_input() -> dict[str, object]:
    return {
        "summary": "An unprivileged caller can satisfy the authorization condition.",
        "technical_details": "The authorization path relies on tx.origin rather than the immediate caller.",
        "preconditions": ["A privileged account initiates a transaction through attacker-controlled code."],
        "reproduction_steps": [
            "Deploy the target and a local forwarding contract.",
            "Call the forwarding contract from the privileged local test account.",
            "Observe that the target accepts the forwarded authorization path.",
        ],
        "remediation": "Use msg.sender with explicit role or ownership checks.",
        "limitations": ["The repository fixture is not a deployed production protocol."],
        "unresolved_questions": ["Confirm whether equivalent code is deployed."],
        "duplicate_check": "Reviewed the repository issues and supplied audit notes; no duplicate was identified.",
        "proof_status_explanation": "The automatic generator is unsupported; the local reproduction steps cover the candidate.",
        "program_rules_rechecked_on": "2026-08-09",
    }


class BountyReportTests(unittest.TestCase):
    def create_confirmed_candidate(self, root: Path):
        create_source(root)
        profile = directory_profile(root)
        scan_bounty_workspace(profile.workspace)
        synchronize_candidates(profile.workspace)
        candidate_id = list_candidates(profile.workspace)["candidates"][0]["candidate_id"]
        review_candidate(
            profile.workspace,
            candidate_id,
            state="investigating",
            reason="Trace local reachability",
            reviewer="alice",
            occurred_at="2026-08-09T10:00:00Z",
        )
        review_candidate(
            profile.workspace,
            candidate_id,
            state="confirmed",
            reason="Local reproduction confirms the authorization primitive",
            reviewer="alice",
            impact="Unauthorized privileged operation",
            occurred_at="2026-08-09T10:01:00Z",
        )
        return profile, candidate_id

    def write_input(self, root: Path, payload: dict[str, object] | None = None) -> Path:
        path = root / "report-input.json"
        path.write_text(
            json.dumps(payload or report_input(), indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def test_draft_remains_hypothesis_until_human_confirmation_and_complete_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root)
            profile = directory_profile(root)
            scan_bounty_workspace(profile.workspace)
            synchronize_candidates(profile.workspace)
            candidate_id = list_candidates(profile.workspace)["candidates"][0]["candidate_id"]

            draft = create_bounty_report(
                profile.workspace,
                candidate_id,
                created_at="2026-08-09T09:00:00Z",
            )
            self.assertEqual(draft["status"], "draft-incomplete")
            self.assertEqual(draft["classification"], "review-hypothesis")
            self.assertFalse(draft["completeness"]["human_confirmed"])
            self.assertFalse(draft["completeness"]["reproduction_complete"])

    def test_complete_report_approval_and_local_export_are_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile, candidate_id = self.create_confirmed_candidate(root)
            report = create_bounty_report(
                profile.workspace,
                candidate_id,
                report_input_path=self.write_input(root),
                created_at="2026-08-09T10:02:00Z",
            )
            self.assertEqual(report["status"], "complete")
            self.assertTrue(all(report["completeness"].values()))
            self.assertEqual(report["classification"], "human-confirmed-candidate")

            with self.assertRaisesRegex(BountyReportError, "acknowledgement"):
                approve_bounty_report(
                    profile.workspace,
                    candidate_id,
                    report["report_sha256"],
                    reviewer="alice",
                    reason="Report is complete",
                    rules_rechecked_on="2026-08-09",
                    acknowledge_manual_submission=False,
                    occurred_at="2026-08-09T10:03:00Z",
                )
            approval = approve_bounty_report(
                profile.workspace,
                candidate_id,
                report["report_sha256"],
                reviewer="alice",
                reason="Scope, impact, reproduction, and report were reviewed",
                rules_rechecked_on="2026-08-09",
                acknowledge_manual_submission=True,
                occurred_at="2026-08-09T10:03:00Z",
            )
            self.assertFalse(approval["submission_policy"]["automatic_submission"])
            self.assertFalse(approval["submission_policy"]["network_action"])
            self.assertEqual(
                list_candidates(profile.workspace)["candidates"][0]["state"],
                "approved",
            )

            destination = root / "local-export"
            exported = export_approved_report(
                profile.workspace,
                candidate_id,
                report["report_sha256"],
                destination,
            )
            self.assertEqual(exported["status"], "exported-locally")
            self.assertFalse(exported["network_action"])
            self.assertFalse(exported["submitted"])
            self.assertEqual(
                set(exported["files"]),
                {"SHA256SUMS", "approval.json", "report.json", "report.md"},
            )
            markdown = (destination / "report.md").read_text(encoding="utf-8")
            self.assertIn("## Reproduction", markdown)
            self.assertIn(report["report_sha256"], markdown)
            self.assertNotIn(str(profile.workspace), markdown)
            self.assertFalse((destination / "submit.json").exists())

    def test_report_becomes_stale_when_review_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile, candidate_id = self.create_confirmed_candidate(root)
            report = create_bounty_report(
                profile.workspace,
                candidate_id,
                report_input_path=self.write_input(root),
                created_at="2026-08-09T11:00:00Z",
            )
            review_candidate(
                profile.workspace,
                candidate_id,
                state="investigating",
                reason="New assumption requires validation",
                reviewer="alice",
                occurred_at="2026-08-09T11:01:00Z",
            )
            with self.assertRaisesRegex(BountyReportError, "stale"):
                approve_bounty_report(
                    profile.workspace,
                    candidate_id,
                    report["report_sha256"],
                    reviewer="alice",
                    reason="Should fail",
                    rules_rechecked_on="2026-08-09",
                    acknowledge_manual_submission=True,
                    occurred_at="2026-08-09T11:02:00Z",
                )

    def test_report_input_rejects_secrets_private_paths_and_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile, candidate_id = self.create_confirmed_candidate(root)
            payload = report_input()
            payload["technical_details"] = "password=hunter2"
            with self.assertRaisesRegex(BountyReportError, "secret"):
                create_bounty_report(
                    profile.workspace,
                    candidate_id,
                    report_input_path=self.write_input(root, payload),
                    created_at="2026-08-09T12:00:00Z",
                )
            payload = report_input()
            payload["technical_details"] = f"See {profile.workspace}/scan.json"
            with self.assertRaisesRegex(BountyReportError, "private local path"):
                create_bounty_report(
                    profile.workspace,
                    candidate_id,
                    report_input_path=self.write_input(root, payload),
                    created_at="2026-08-09T12:00:00Z",
                )

    def test_approval_write_can_recover_after_review_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile, candidate_id = self.create_confirmed_candidate(root)
            report = create_bounty_report(
                profile.workspace,
                candidate_id,
                report_input_path=self.write_input(root),
                created_at="2026-08-09T12:30:00Z",
            )
            arguments = {
                "reviewer": "alice",
                "reason": "Reviewed complete report",
                "rules_rechecked_on": "2026-08-09",
                "acknowledge_manual_submission": True,
                "occurred_at": "2026-08-09T12:31:00Z",
            }
            with patch(
                "contract_holes.bounty_report.write_private_json_new_or_identical",
                side_effect=BountyWorkspaceError("simulated interrupted write"),
            ):
                with self.assertRaisesRegex(BountyReportError, "interrupted write"):
                    approve_bounty_report(
                        profile.workspace,
                        candidate_id,
                        report["report_sha256"],
                        **arguments,
                    )
            self.assertEqual(
                list_candidates(profile.workspace)["candidates"][0]["state"],
                "approved",
            )
            approval = approve_bounty_report(
                profile.workspace,
                candidate_id,
                report["report_sha256"],
                **arguments,
            )
            self.assertEqual(approval["approved_at"], "2026-08-09T12:31:00Z")

    def test_report_and_approval_schemas_are_packaged(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        names = (
            "bounty-report-input-1.0.schema.json",
            "bounty-report-1.0.schema.json",
            "bounty-approval-1.0.schema.json",
        )
        report_input, report, approval = [
            json.loads(schema_directory.joinpath(name).read_text(encoding="utf-8"))
            for name in names
        ]
        self.assertEqual(report_input["additionalProperties"], False)
        self.assertEqual(report["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(approval["properties"]["schema_version"]["const"], "1.0")


class BountyReportCliTests(unittest.TestCase):
    def test_cli_report_approve_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper = BountyReportTests()
            profile, candidate_id = helper.create_confirmed_candidate(root)
            input_path = helper.write_input(root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "bounty",
                        "report",
                        str(profile.workspace),
                        candidate_id,
                        "--input",
                        str(input_path),
                        "--at",
                        "2026-08-09T13:00:00Z",
                    ]
                )
            report_payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            report_sha = report_payload["report"]["report_sha256"]

            with contextlib.redirect_stdout(io.StringIO()):
                status = main(
                    [
                        "bounty",
                        "approve",
                        str(profile.workspace),
                        candidate_id,
                        "--report-sha",
                        report_sha,
                        "--reviewer",
                        "alice",
                        "--reason",
                        "Reviewed complete report",
                        "--rules-rechecked-on",
                        "2026-08-09",
                        "--acknowledge-manual-submission",
                        "--at",
                        "2026-08-09T13:01:00Z",
                    ]
                )
            self.assertEqual(status, 0)

            destination = root / "export"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "bounty",
                        "export",
                        str(profile.workspace),
                        candidate_id,
                        "--report-sha",
                        report_sha,
                        "--output",
                        str(destination),
                    ]
                )
            exported = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(exported["command"], "bounty.export")
            self.assertFalse(exported["submitted"])


if __name__ == "__main__":
    unittest.main()
