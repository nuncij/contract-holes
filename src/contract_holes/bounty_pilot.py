from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping

from . import __version__
from .bounty_candidates import (
    BountyCandidateError,
    list_candidates,
    review_candidate,
    synchronize_candidates,
)
from .bounty_io import (
    BountyWorkspaceError,
    payload_sha256,
    write_private_json_new_or_identical,
)
from .bounty_profile import (
    BountyProfileError,
    initialize_bounty_workspace,
    load_bounty_profile,
)
from .bounty_proof import BountyProofError, create_bounty_proof
from .bounty_report import (
    BountyReportError,
    approve_bounty_report,
    create_bounty_report,
    export_approved_report,
)
from .bounty_scope import (
    BountyScopeError,
    identify_source,
    scan_bounty_workspace,
)


class BountyPilotError(RuntimeError):
    pass


PILOT_SCHEMA_VERSION = "1.0"
PILOT_EVALUATION_VERSION = "1.0"
PILOT_RESULT_FILENAME = "pilot-result.json"
REPORT_INPUT_FILENAME = "report-input.json"


def load_bounty_pilot_manifest(path: Path | str) -> dict[str, object]:
    supplied_manifest = Path(path)
    if supplied_manifest.is_symlink():
        raise BountyPilotError(
            f"pilot manifest must not be a symlink: {supplied_manifest}"
        )
    manifest_path = supplied_manifest.resolve()
    payload = _load_json(manifest_path, "pilot manifest")
    _exact_keys(
        payload,
        {
            "schema_version",
            "evaluation_version",
            "pilot_id",
            "program",
            "target",
            "decisions",
            "proof",
            "report_input",
            "approval",
            "timeline",
        },
        "pilot manifest",
    )
    if payload.get("schema_version") != PILOT_SCHEMA_VERSION:
        raise BountyPilotError("pilot manifest schema_version must be 1.0")
    if payload.get("evaluation_version") != PILOT_EVALUATION_VERSION:
        raise BountyPilotError("pilot manifest evaluation_version must be 1.0")
    pilot_id = _text(payload.get("pilot_id"), "pilot_id")

    program = _object(payload.get("program"), "program")
    _exact_keys(
        program,
        {
            "name",
            "platform",
            "rules_url",
            "rules_document",
            "rules_document_sha256",
            "reviewed_on",
            "authorization_acknowledged",
            "authorization_note",
            "impacts",
            "restrictions",
        },
        "program",
    )
    for field in ("name", "platform", "authorization_note"):
        _text(program.get(field), f"program.{field}")
    rules_url = _text(program.get("rules_url"), "program.rules_url")
    if not rules_url.startswith("https://") or any(
        character.isspace() for character in rules_url
    ):
        raise BountyPilotError("program.rules_url must be an HTTPS URL")
    reviewed_on = _date(program.get("reviewed_on"), "program.reviewed_on")
    if program.get("authorization_acknowledged") is not True:
        raise BountyPilotError("pilot authorization must be explicitly acknowledged")
    impacts = _text_list(program.get("impacts"), "program.impacts", nonempty=True)
    restrictions = _text_list(
        program.get("restrictions"), "program.restrictions", nonempty=True
    )
    rules_document = _relative_file(
        manifest_path, program.get("rules_document"), "program.rules_document"
    )
    _verify_sha256(
        rules_document,
        program.get("rules_document_sha256"),
        "pilot rules document",
    )

    target = _object(payload.get("target"), "target")
    _exact_keys(target, {"root", "content_sha256", "scope_paths"}, "target")
    target_root = _relative_directory(manifest_path, target.get("root"), "target.root")
    scope_paths = _text_list(
        target.get("scope_paths"), "target.scope_paths", nonempty=True
    )
    try:
        identity = identify_source(target_root, scope_paths)
    except BountyScopeError as exc:
        raise BountyPilotError(str(exc)) from exc
    declared_content_sha256 = _digest(
        target.get("content_sha256"), "target.content_sha256"
    )
    if identity.source_set_sha256 != declared_content_sha256:
        raise BountyPilotError("pilot target content SHA-256 changed")

    decisions = _object(payload.get("decisions"), "decisions")
    _exact_keys(decisions, {"confirm", "reject"}, "decisions")
    confirm = _decision(decisions.get("confirm"), "decisions.confirm", confirmed=True)
    reject = _decision(decisions.get("reject"), "decisions.reject", confirmed=False)
    if confirm["rule_id"] == reject["rule_id"]:
        raise BountyPilotError("confirm and reject decisions require different rule IDs")

    proof = _object(payload.get("proof"), "proof")
    _exact_keys(proof, {"rule_id", "requirements", "impact_assertion"}, "proof")
    proof_rule = _rule_id(proof.get("rule_id"), "proof.rule_id")
    if proof_rule != confirm["rule_id"]:
        raise BountyPilotError("proof.rule_id must match the confirmed decision")
    requirements = _string_mapping(proof.get("requirements"), "proof.requirements")
    impact_assertion = _text(proof.get("impact_assertion"), "proof.impact_assertion")

    report_input = _object(payload.get("report_input"), "report_input")
    expected_report_fields = {
        "summary",
        "technical_details",
        "preconditions",
        "reproduction_steps",
        "remediation",
        "limitations",
        "unresolved_questions",
        "duplicate_check",
        "proof_status_explanation",
        "program_rules_rechecked_on",
    }
    _exact_keys(report_input, expected_report_fields, "report_input")
    for field in (
        "summary",
        "technical_details",
        "remediation",
        "duplicate_check",
        "proof_status_explanation",
    ):
        _text(report_input.get(field), f"report_input.{field}")
    for field, nonempty in (
        ("preconditions", True),
        ("reproduction_steps", True),
        ("limitations", True),
        ("unresolved_questions", False),
    ):
        _text_list(
            report_input.get(field), f"report_input.{field}", nonempty=nonempty
        )
    rules_rechecked_on = _date(
        report_input.get("program_rules_rechecked_on"),
        "report_input.program_rules_rechecked_on",
    )
    if rules_rechecked_on < reviewed_on:
        raise BountyPilotError("report rules recheck predates the profile review")

    approval = _object(payload.get("approval"), "approval")
    _exact_keys(
        approval,
        {"reviewer", "reason", "acknowledge_manual_submission"},
        "approval",
    )
    reviewer = _text(approval.get("reviewer"), "approval.reviewer")
    approval_reason = _text(approval.get("reason"), "approval.reason")
    if approval.get("acknowledge_manual_submission") is not True:
        raise BountyPilotError(
            "approval must acknowledge that any submission remains manual"
        )

    timeline = _timeline(payload.get("timeline"))
    return {
        **payload,
        "pilot_id": pilot_id,
        "manifest_path": manifest_path,
        "manifest_sha256": payload_sha256(payload),
        "program": {
            **program,
            "reviewed_on": reviewed_on,
            "impacts": impacts,
            "restrictions": restrictions,
            "rules_document_path": rules_document,
        },
        "target": {
            **target,
            "root_path": target_root,
            "scope_paths": scope_paths,
            "content_sha256": declared_content_sha256,
        },
        "decisions": {"confirm": confirm, "reject": reject},
        "proof": {
            "rule_id": proof_rule,
            "requirements": requirements,
            "impact_assertion": impact_assertion,
        },
        "report_input": dict(report_input),
        "approval": {
            "reviewer": reviewer,
            "reason": approval_reason,
            "acknowledge_manual_submission": True,
        },
        "timeline": timeline,
    }


def run_bounty_pilot(
    manifest_path: Path | str,
    output_directory: Path | str,
) -> dict[str, object]:
    manifest = load_bounty_pilot_manifest(manifest_path)
    supplied_output = Path(output_directory)
    if supplied_output.is_symlink():
        raise BountyPilotError(f"pilot output must not be a symlink: {supplied_output}")
    output = supplied_output.resolve()
    target = manifest["target"]
    program = manifest["program"]
    assert isinstance(target, dict)
    assert isinstance(program, dict)
    target_root = Path(target["root_path"])
    if output.exists() or output.is_symlink():
        raise BountyPilotError(f"pilot output already exists: {output}")
    if _is_relative_to(output, target_root):
        raise BountyPilotError("pilot output must be outside the target source tree")
    try:
        output.mkdir(parents=True, mode=0o700)
        if os.name == "posix":
            output.chmod(0o700)
    except OSError as exc:
        raise BountyPilotError(f"could not create pilot output {output}: {exc}") from exc

    workspace = output / "workspace"
    export_directory = output / "local-export"
    report_input_path = output / REPORT_INPUT_FILENAME
    try:
        profile = initialize_bounty_workspace(
            workspace,
            program_name=str(program["name"]),
            platform=str(program["platform"]),
            rules_url=str(program["rules_url"]),
            reviewed_on=str(program["reviewed_on"]),
            authorization_acknowledged=True,
            authorization_note=str(program["authorization_note"]),
            source_root=target_root,
            source_revision=None,
            source_content_sha256=str(target["content_sha256"]),
            scope_paths=list(target["scope_paths"]),
            impacts=list(program["impacts"]),
            restrictions=list(program["restrictions"]),
            compiler_enabled=False,
        )
        validated = load_bounty_profile(workspace)
        if validated.digest != profile.digest:
            raise BountyPilotError("validated pilot profile identity changed")

        scan = scan_bounty_workspace(workspace)
        synchronize_candidates(workspace)
        initial = list_candidates(workspace)
        candidates_by_rule = _candidates_by_rule(initial)
        expected_rules = {
            str(manifest["decisions"]["confirm"]["rule_id"]),
            str(manifest["decisions"]["reject"]["rule_id"]),
        }
        if set(candidates_by_rule) != expected_rules or any(
            len(candidates) != 1 for candidates in candidates_by_rule.values()
        ):
            raise BountyPilotError(
                "pilot scan candidates differ from the frozen review decisions"
            )

        timeline = manifest["timeline"]
        decisions = manifest["decisions"]
        assert isinstance(timeline, dict)
        assert isinstance(decisions, dict)
        for name in ("confirm", "reject"):
            decision = decisions[name]
            assert isinstance(decision, dict)
            candidate = candidates_by_rule[str(decision["rule_id"])][0]
            candidate_id = str(candidate["candidate_id"])
            review_candidate(
                workspace,
                candidate_id,
                state="investigating",
                reason=str(decision["investigation_reason"]),
                reviewer=str(decision["reviewer"]),
                occurred_at=str(timeline[f"{name}_investigating_at"]),
            )
            review_candidate(
                workspace,
                candidate_id,
                state="confirmed" if name == "confirm" else "rejected",
                reason=str(decision["decision_reason"]),
                reviewer=str(decision["reviewer"]),
                impact=str(decision["impact"]) if name == "confirm" else None,
                occurred_at=str(timeline[f"{name}_decided_at"]),
            )

        confirm = decisions["confirm"]
        assert isinstance(confirm, dict)
        confirmed_candidate = candidates_by_rule[str(confirm["rule_id"])][0]
        confirmed_id = str(confirmed_candidate["candidate_id"])
        proof_config = manifest["proof"]
        assert isinstance(proof_config, dict)
        proof = create_bounty_proof(
            workspace,
            confirmed_id,
            requirements=proof_config["requirements"],
            impact_assertion=str(proof_config["impact_assertion"]),
            run=True,
        )

        write_private_json_new_or_identical(
            report_input_path, manifest["report_input"]
        )
        report = create_bounty_report(
            workspace,
            confirmed_id,
            report_input_path=report_input_path,
            proof_sha256=str(proof.manifest["proof_sha256"]),
            created_at=str(timeline["report_created_at"]),
        )

        expected_blocks: list[dict[str, str]] = []
        safety_failures: list[str] = []
        try:
            export_approved_report(
                workspace,
                confirmed_id,
                str(report["report_sha256"]),
                export_directory,
            )
        except BountyReportError as exc:
            diagnostic = str(exc)
            if "not approved for local export" in diagnostic:
                expected_blocks.append(
                    {
                        "check": "export-before-approval",
                        "status": "blocked",
                        "diagnostic": diagnostic,
                    }
                )
            else:
                safety_failures.append(
                    "export-before-approval returned an unexpected diagnostic"
                )
        else:
            safety_failures.append("export-before-approval was not blocked")

        approval_config = manifest["approval"]
        assert isinstance(approval_config, dict)
        try:
            approve_bounty_report(
                workspace,
                confirmed_id,
                str(report["report_sha256"]),
                reviewer=str(approval_config["reviewer"]),
                reason=str(approval_config["reason"]),
                rules_rechecked_on=str(
                    manifest["report_input"]["program_rules_rechecked_on"]
                ),
                acknowledge_manual_submission=False,
                occurred_at=str(timeline["approved_at"]),
            )
        except BountyReportError as exc:
            diagnostic = str(exc)
            if "requires acknowledgement" in diagnostic:
                expected_blocks.append(
                    {
                        "check": "approval-without-manual-submission-ack",
                        "status": "blocked",
                        "diagnostic": diagnostic,
                    }
                )
            else:
                safety_failures.append(
                    "approval-without-manual-submission-ack returned an unexpected diagnostic"
                )
        else:
            safety_failures.append(
                "approval-without-manual-submission-ack was not blocked"
            )

        approval = approve_bounty_report(
            workspace,
            confirmed_id,
            str(report["report_sha256"]),
            reviewer=str(approval_config["reviewer"]),
            reason=str(approval_config["reason"]),
            rules_rechecked_on=str(
                manifest["report_input"]["program_rules_rechecked_on"]
            ),
            acknowledge_manual_submission=bool(
                approval_config["acknowledge_manual_submission"]
            ),
            occurred_at=str(timeline["approved_at"]),
        )
        exported = export_approved_report(
            workspace,
            confirmed_id,
            str(report["report_sha256"]),
            export_directory,
        )
        final = list_candidates(workspace)
    except (
        BountyCandidateError,
        BountyProfileError,
        BountyProofError,
        BountyReportError,
        BountyScopeError,
        BountyWorkspaceError,
        OSError,
    ) as exc:
        raise BountyPilotError(str(exc)) from exc

    elapsed_seconds = int(
        (
            _parse_timestamp(str(timeline["finished_at"]))
            - _parse_timestamp(str(timeline["started_at"]))
        ).total_seconds()
    )
    final_states = {
        _candidate_rule_id(candidate): str(candidate["state"])
        for candidate in final["candidates"]
    }
    proof_status = (
        str(proof.execution["status"]) if proof.execution is not None else "not-run"
    )
    no_remote_action = bool(
        proof.manifest["execution_policy"]["offline"]
        and proof.manifest["execution_policy"]["remote_rpc"] is None
        and proof.manifest["execution_policy"]["wallet"] is None
        and approval["submission_policy"]["network_action"] is False
        and approval["submission_policy"]["automatic_submission"] is False
        and exported["network_action"] is False
        and exported["submitted"] is False
    )
    gate_checks = {
        "profile_validated": validated.digest == profile.digest,
        "scope_scan_completed": scan.scan_record.get("status") == "completed",
        "expected_candidates_triaged": final_states
        == {
            str(decisions["confirm"]["rule_id"]): "approved",
            str(decisions["reject"]["rule_id"]): "rejected",
        },
        "proof_decision_recorded": proof_status == "unsupported",
        "report_complete": report.get("status") == "complete",
        "approval_recorded": approval["submission_policy"].get(
            "manual_private_submission_acknowledged"
        )
        is True,
        "local_export_completed": exported.get("status") == "exported-locally",
        "safety_guards_exercised": len(expected_blocks) == 2 and not safety_failures,
        "no_network_transaction_contact_or_submission": no_remote_action,
    }
    passed = all(gate_checks.values())
    result: dict[str, object] = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "evaluation_version": PILOT_EVALUATION_VERSION,
        "pilot_id": manifest["pilot_id"],
        "scanner_version": __version__,
        "manifest_sha256": manifest["manifest_sha256"],
        "rules_document_sha256": program["rules_document_sha256"],
        "source_set_sha256": target["content_sha256"],
        "authorization": {
            "acknowledged": True,
            "reviewed_on": program["reviewed_on"],
            "scope_paths": list(target["scope_paths"]),
            "impact_count": len(program["impacts"]),
            "restriction_count": len(program["restrictions"]),
        },
        "execution_policy": {
            "source_only": True,
            "offline": True,
            "local_chain_execution": False,
            "live_network_transaction": False,
            "public_testnet_execution": False,
            "target_contact": False,
            "platform_interaction": False,
            "automatic_submission": False,
            "submitted": False,
        },
        "workflow": {
            "started_at": timeline["started_at"],
            "finished_at": timeline["finished_at"],
            "recorded_elapsed_seconds": elapsed_seconds,
            "time_basis": "operator event timeline",
            "stages": [
                {"stage": "profile-validation", "status": "completed"},
                {"stage": "scope-scan", "status": "completed"},
                {"stage": "candidate-triage", "status": "completed"},
                {"stage": "proof-decision", "status": proof_status},
                {"stage": "private-report-draft", "status": str(report["status"])},
                {"stage": "human-approval", "status": "approved-locally"},
                {"stage": "local-export", "status": str(exported["status"])},
            ],
        },
        "metrics": {
            "files_scanned": scan.scan_record["report"]["files_scanned"],
            "candidate_count": initial["candidate_count"],
            "investigated_count": 2,
            "confirmed_count": 1,
            "rejected_count": 1,
            "approved_count": 1,
            "proof_generated_count": int(
                proof.manifest["generator"]["status"] == "generated"
            ),
            "proof_unsupported_count": int(proof_status == "unsupported"),
            "safety_checks_exercised": len(expected_blocks),
            "safety_failure_count": len(safety_failures),
        },
        "review_decisions": [
            {
                "rule_id": rule_id,
                "final_state": final_states[rule_id],
                "decision_source": "human",
            }
            for rule_id in sorted(final_states)
        ],
        "friction": [
            {
                "code": "automatic-proof-unsupported",
                "stage": "proof-decision",
                "observation": "Manual local reproduction remains necessary for this rule.",
            },
            {
                "code": "operator-authored-report-context",
                "stage": "private-report-draft",
                "observation": "Scope, duplicate, impact, and reproduction context required human input.",
            },
            {
                "code": "separate-manual-approval",
                "stage": "human-approval",
                "observation": "Local export required a current report and explicit manual-submission acknowledgement.",
            },
        ],
        "safety": {
            "expected_blocks": expected_blocks,
            "failures": safety_failures,
        },
        "export": {
            "status": exported["status"],
            "files": exported["files"],
            "network_action": False,
            "submitted": False,
        },
        "gate_checks": gate_checks,
        "limitations": [
            "The authorized target is a repository-owned fixture, not a live bounty program.",
            "One human-confirmed fixture flaw does not establish exploitability or payout eligibility elsewhere.",
            "The recorded timeline measures operator events, not automated process runtime.",
            "Any real submission remains a separate manual decision under the selected program rules.",
        ],
        "status": "passed" if passed else "failed",
    }
    result["result_sha256"] = payload_sha256(result)
    try:
        write_private_json_new_or_identical(output / PILOT_RESULT_FILENAME, result)
    except BountyWorkspaceError as exc:
        raise BountyPilotError(str(exc)) from exc
    return result


def bounty_pilot_exit_status(result: dict[str, object]) -> int:
    return 0 if result.get("status") == "passed" else 1


def _decision(value: object, label: str, *, confirmed: bool) -> dict[str, str]:
    decision = _object(value, label)
    expected = {
        "rule_id",
        "reviewer",
        "investigation_reason",
        "decision_reason",
    }
    if confirmed:
        expected.add("impact")
    _exact_keys(decision, expected, label)
    normalized = {
        "rule_id": _rule_id(decision.get("rule_id"), f"{label}.rule_id"),
        "reviewer": _text(decision.get("reviewer"), f"{label}.reviewer"),
        "investigation_reason": _text(
            decision.get("investigation_reason"), f"{label}.investigation_reason"
        ),
        "decision_reason": _text(
            decision.get("decision_reason"), f"{label}.decision_reason"
        ),
    }
    if confirmed:
        normalized["impact"] = _text(decision.get("impact"), f"{label}.impact")
    return normalized


def _timeline(value: object) -> dict[str, str]:
    timeline = _object(value, "timeline")
    fields = {
        "started_at",
        "confirm_investigating_at",
        "reject_investigating_at",
        "confirm_decided_at",
        "reject_decided_at",
        "report_created_at",
        "approved_at",
        "finished_at",
    }
    _exact_keys(timeline, fields, "timeline")
    normalized = {
        field: _timestamp(timeline.get(field), f"timeline.{field}")
        for field in fields
    }
    started = _parse_timestamp(normalized["started_at"])
    finished = _parse_timestamp(normalized["finished_at"])
    if finished <= started:
        raise BountyPilotError("timeline.finished_at must follow started_at")
    for field in fields - {"started_at", "finished_at"}:
        current = _parse_timestamp(normalized[field])
        if not started < current < finished:
            raise BountyPilotError(f"timeline.{field} must be within the pilot window")
    for prefix in ("confirm", "reject"):
        if _parse_timestamp(normalized[f"{prefix}_decided_at"]) <= _parse_timestamp(
            normalized[f"{prefix}_investigating_at"]
        ):
            raise BountyPilotError(
                f"timeline.{prefix}_decided_at must follow investigation"
            )
    if _parse_timestamp(normalized["report_created_at"]) <= max(
        _parse_timestamp(normalized["confirm_decided_at"]),
        _parse_timestamp(normalized["reject_decided_at"]),
    ):
        raise BountyPilotError(
            "timeline.report_created_at must follow both review decisions"
        )
    if _parse_timestamp(normalized["approved_at"]) <= _parse_timestamp(
        normalized["report_created_at"]
    ):
        raise BountyPilotError("timeline.approved_at must follow report creation")
    return normalized


def _candidates_by_rule(payload: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for candidate in payload.get("candidates", []):
        if not isinstance(candidate, dict):
            raise BountyPilotError("pilot candidate is invalid")
        rule_id = _candidate_rule_id(candidate)
        result.setdefault(rule_id, []).append(candidate)
    return result


def _candidate_rule_id(candidate: dict[str, object]) -> str:
    observation = candidate.get("observation")
    if not isinstance(observation, dict):
        raise BountyPilotError("pilot candidate observation is invalid")
    finding = observation.get("finding")
    if not isinstance(finding, dict):
        raise BountyPilotError("pilot candidate finding is invalid")
    return _rule_id(finding.get("rule_id"), "candidate rule_id")


def _load_json(path: Path, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise BountyPilotError(f"{label} is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BountyPilotError(f"could not read {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BountyPilotError(f"{label} root must be an object")
    return payload


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise BountyPilotError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unknown = sorted(set(value) - expected)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        raise BountyPilotError(f"{label} fields are invalid: {'; '.join(details)}")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BountyPilotError(f"{label} must be a non-empty string")
    return value


def _text_list(value: object, label: str, *, nonempty: bool) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() or "\x00" in item
        for item in value
    ):
        raise BountyPilotError(f"{label} must be an array of non-empty strings")
    if nonempty and not value:
        raise BountyPilotError(f"{label} must not be empty")
    if len(value) != len(set(value)):
        raise BountyPilotError(f"{label} must not contain duplicates")
    return list(value)


def _string_mapping(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or any(
        not isinstance(key, str)
        or not key.strip()
        or not isinstance(item, str)
        or not item.strip()
        for key, item in value.items()
    ):
        raise BountyPilotError(f"{label} must map non-empty strings to strings")
    return dict(value)


def _rule_id(value: object, label: str) -> str:
    result = _text(value, label)
    if len(result) != 6 or not result.startswith("SOL") or not result[3:].isdigit():
        raise BountyPilotError(f"{label} must be a SOLnnn rule ID")
    return result


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise BountyPilotError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _date(value: object, label: str) -> str:
    result = _text(value, label)
    try:
        date.fromisoformat(result)
    except ValueError as exc:
        raise BountyPilotError(f"{label} must be YYYY-MM-DD") from exc
    return result


def _timestamp(value: object, label: str) -> str:
    result = _text(value, label)
    _parse_timestamp(result, label)
    return result


def _parse_timestamp(value: str, label: str = "timestamp") -> datetime:
    if not value.endswith("Z"):
        raise BountyPilotError(f"{label} must be an RFC3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BountyPilotError(f"{label} must be an RFC3339 UTC timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise BountyPilotError(f"{label} must be an RFC3339 UTC timestamp")
    return parsed


def _relative_file(manifest: Path, value: object, label: str) -> Path:
    path = _relative_path(manifest, value, label)
    if path.is_symlink() or not path.is_file():
        raise BountyPilotError(f"{label} is not a regular file: {path}")
    return path


def _relative_directory(manifest: Path, value: object, label: str) -> Path:
    path = _relative_path(manifest, value, label)
    if path.is_symlink() or not path.is_dir():
        raise BountyPilotError(f"{label} is not a directory: {path}")
    return path


def _relative_path(manifest: Path, value: object, label: str) -> Path:
    raw = _text(value, label)
    supplied = Path(raw)
    if supplied.is_absolute() or ".." in supplied.parts:
        raise BountyPilotError(f"{label} must be a relative path without traversal")
    root = manifest.parent.resolve()
    lexical = root / supplied
    current = root
    for part in supplied.parts:
        current = current / part
        if current.is_symlink():
            raise BountyPilotError(f"{label} must not contain a symlink")
    path = lexical.resolve()
    if not _is_relative_to(path, root):
        raise BountyPilotError(f"{label} escapes the pilot fixture directory")
    return path


def _verify_sha256(path: Path, expected: object, label: str) -> None:
    digest = _digest(expected, f"{label} SHA-256")
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BountyPilotError(f"could not read {label}: {exc}") from exc
    if actual != digest:
        raise BountyPilotError(f"{label} SHA-256 changed")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
