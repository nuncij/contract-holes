from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Callable

from .bounty_candidates import (
    BountyCandidateError,
    CandidateContext,
    load_candidate_context,
    review_candidate,
)
from .bounty_io import (
    BountyWorkspaceError,
    load_private_json,
    payload_sha256,
    redact_sensitive_text,
    rendered_json_bytes,
    write_private_json_new_or_identical,
)
from .bounty_proof import (
    BountyProofError,
    load_bounty_proof,
    load_bounty_proof_result,
)
from .bounty_scope import BountyScopeError, validate_profile_source


class BountyReportError(RuntimeError):
    pass


REPORT_SCHEMA_VERSION = "1.0"
APPROVAL_SCHEMA_VERSION = "1.0"
REPORTS_ROOT = "reports"
APPROVALS_ROOT = "approvals"
PRIVATE_REPORT_JSON = "private-report.json"
PRIVATE_REPORT_MARKDOWN = "private-report.md"
APPROVAL_FILENAME = "approval.json"
MAX_REPORT_INPUT_BYTES = 2 * 1024 * 1024
REPORT_INPUT_KEYS = frozenset(
    {
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
)


def create_bounty_report(
    workspace: Path | str,
    candidate_id: str,
    *,
    report_input_path: Path | str | None = None,
    proof_sha256: str | None = None,
    created_at: str | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, object]:
    context = _context(workspace, candidate_id)
    _revalidate_source(context)
    finding = _finding_payload(context)
    supplied = (
        load_report_input(
            report_input_path,
            private_paths=(context.profile.workspace, context.profile.source_root),
        )
        if report_input_path is not None
        else None
    )
    content = supplied or _default_draft_content(finding)
    proof_manifest: dict[str, object] | None = None
    proof_result: dict[str, object] | None = None
    if proof_sha256 is not None:
        try:
            _, proof_manifest = load_bounty_proof(context, proof_sha256)
            proof_result = load_bounty_proof_result(context, proof_sha256)
        except BountyProofError as exc:
            raise BountyReportError(str(exc)) from exc
    review = context.review
    state = str(review.get("state")) if review else "new"
    impact = review.get("impact") if review else None
    checklist = _report_checklist(
        content,
        state=state,
        impact=impact,
        proof_manifest=proof_manifest,
        proof_result=proof_result,
    )
    complete = all(checklist.values())
    timestamp = _timestamp(created_at, now=now)
    reviews_digest = context.reviews_record.get("reviews_sha256")
    payload: dict[str, object] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "status": "complete" if complete else "draft-incomplete",
        "classification": (
            "human-confirmed-candidate" if state == "confirmed" else "review-hypothesis"
        ),
        "created_at": timestamp,
        "profile_sha256": context.profile.digest,
        "source_manifest_sha256": context.source_manifest["manifest_sha256"],
        "candidates_sha256": context.candidates_record["candidates_sha256"],
        "reviews_sha256": reviews_digest,
        "report_input_sha256": payload_sha256(content),
        "target": {
            "program": context.profile.program_name,
            "platform": context.profile.platform,
            "rules_url": context.profile.rules_url,
            "profile_reviewed_on": context.profile.reviewed_on,
            "program_rules_rechecked_on": content["program_rules_rechecked_on"],
            "source": context.source_manifest["source"],
            "scope_paths": list(context.profile.scope_paths),
            "in_scope_impacts": list(context.profile.impacts),
        },
        "finding": {
            "rule_id": finding["rule_id"],
            "fingerprint": finding["fingerprint"],
            "severity": finding["severity"],
            "confidence": finding["confidence"],
            "title": finding["title"],
            "path": finding["path"],
            "line": finding["line"],
            "column": finding["column"],
            "message": finding["message"],
            "evidence": finding.get("metadata", {}),
        },
        "review": {
            "state": state,
            "reason": review.get("reason") if review else None,
            "impact": impact,
            "reviewer": review.get("reviewer") if review else None,
            "updated_at": review.get("updated_at") if review else None,
        },
        "content": content,
        "proof": {
            "proof_sha256": proof_sha256,
            "generator_status": _nested(proof_manifest, "generator", "status"),
            "execution_status": proof_result.get("status") if proof_result else None,
            "result_sha256": proof_result.get("result_sha256") if proof_result else None,
        },
        "completeness": checklist,
        "limitations": [
            "This is a private candidate report, not proof that the target is exploitable.",
            "A clean Contract Holes scan is not evidence that a contract is safe.",
            "Program scope, duplicate status, deployed reachability, and impact require human verification.",
        ],
    }
    payload["report_sha256"] = payload_sha256(payload)
    _install_report(context, payload)
    return payload


def approve_bounty_report(
    workspace: Path | str,
    candidate_id: str,
    report_sha256: str,
    *,
    reviewer: str,
    reason: str,
    rules_rechecked_on: str,
    acknowledge_manual_submission: bool,
    occurred_at: str | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, object]:
    context = _context(workspace, candidate_id)
    _revalidate_source(context)
    already_approved = (
        context.review is not None and context.review.get("state") == "approved"
    )
    report = load_bounty_report(
        context,
        report_sha256,
        allow_post_approval_review=already_approved,
    )
    if report.get("status") != "complete" or not all(
        value is True for value in report.get("completeness", {}).values()
    ):
        raise BountyReportError("only a complete report can be approved")
    if not acknowledge_manual_submission:
        raise BountyReportError(
            "approval requires acknowledgement that submission remains manual and private"
        )
    reviewer = _text(reviewer, "approval reviewer")
    reason = _text(reason, "approval reason")
    rules_date = _review_date(rules_rechecked_on)
    if report["target"].get("program_rules_rechecked_on") != rules_date:
        raise BountyReportError(
            "approval rules review date must match the complete report"
        )
    if rules_date < context.profile.reviewed_on:
        raise BountyReportError("program rules recheck predates the bounty profile")
    if context.review is None or context.review.get("state") not in {
        "confirmed",
        "approved",
    }:
        raise BountyReportError("candidate must be human-confirmed before approval")
    if not already_approved and report.get("reviews_sha256") != context.reviews_record.get(
        "reviews_sha256"
    ):
        raise BountyReportError("report is stale because human review state changed")
    if already_approved:
        if (
            context.review.get("reviewer") != reviewer
            or context.review.get("reason") != reason
        ):
            raise BountyReportError(
                "approval retry must use the reviewer and reason in the approved review"
            )
        timestamp = str(context.review.get("updated_at", ""))
        if occurred_at is not None and _timestamp(occurred_at, now=now) != timestamp:
            raise BountyReportError(
                "approval retry timestamp does not match the approved review"
            )
        approved_context = context
    else:
        timestamp = _timestamp(occurred_at, now=now)
        impact = context.review.get("impact")
        approval_directory = _approval_directory(context, report_sha256)
        approval_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            approval_directory.chmod(0o700)
        try:
            review_candidate(
                workspace,
                candidate_id,
                state="approved",
                reason=reason,
                reviewer=reviewer,
                impact=str(impact) if impact is not None else None,
                occurred_at=timestamp,
                allow_approval=True,
            )
        except BountyCandidateError as exc:
            raise BountyReportError(str(exc)) from exc
        approved_context = _context(workspace, candidate_id)
    approval: dict[str, object] = {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "report_sha256": report_sha256,
        "profile_sha256": approved_context.profile.digest,
        "source_manifest_sha256": approved_context.source_manifest["manifest_sha256"],
        "candidates_sha256": approved_context.candidates_record["candidates_sha256"],
        "reviews_sha256": approved_context.reviews_record["reviews_sha256"],
        "reviewer": reviewer,
        "reason": reason,
        "approved_at": timestamp,
        "program_rules_rechecked_on": rules_date,
        "submission_policy": {
            "automatic_submission": False,
            "network_action": False,
            "manual_private_submission_acknowledged": True,
        },
    }
    approval["approval_sha256"] = payload_sha256(approval)
    path = _approval_directory(approved_context, report_sha256) / APPROVAL_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.parent.chmod(0o700)
    try:
        write_private_json_new_or_identical(path, approval)
    except BountyWorkspaceError as exc:
        raise BountyReportError(str(exc)) from exc
    return approval


def export_approved_report(
    workspace: Path | str,
    candidate_id: str,
    report_sha256: str,
    output_directory: Path | str,
) -> dict[str, object]:
    context = _context(workspace, candidate_id)
    _revalidate_source(context)
    if context.review is None or context.review.get("state") != "approved":
        raise BountyReportError("candidate is not approved for local export")
    report = load_bounty_report(context, report_sha256, allow_post_approval_review=True)
    approval = _load_approval(context, report_sha256)
    if approval.get("reviews_sha256") != context.reviews_record.get("reviews_sha256"):
        raise BountyReportError("approval is stale because review state changed")
    destination = Path(output_directory).resolve()
    if destination.exists():
        raise BountyReportError(f"export destination already exists: {destination}")
    if _is_relative_to(destination, context.profile.workspace) or _is_relative_to(
        destination, context.profile.source_root
    ):
        raise BountyReportError("export destination must be outside workspace and target")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
    )
    try:
        if os.name == "posix":
            staging.chmod(0o700)
        shareable = _shareable_payload(report)
        approval_export = _redact_payload(
            approval,
            private_paths=(context.profile.workspace, context.profile.source_root),
        )
        report_json = rendered_json_bytes(shareable)
        approval_json = rendered_json_bytes(approval_export)
        markdown = _render_report_markdown(shareable).encode("utf-8")
        artifacts = {
            "report.json": report_json,
            "report.md": markdown,
            "approval.json": approval_json,
        }
        for name, content in artifacts.items():
            path = staging / name
            path.write_bytes(content)
            if os.name == "posix":
                path.chmod(0o600)
        checksums = "".join(
            f"{hashlib.sha256(content).hexdigest()}  {name}\n"
            for name, content in sorted(artifacts.items())
        )
        checksum_path = staging / "SHA256SUMS"
        checksum_path.write_text(checksums, encoding="utf-8")
        if os.name == "posix":
            checksum_path.chmod(0o600)
        staging.rename(destination)
    except (OSError, UnicodeError) as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise BountyReportError(f"could not export approved report: {exc}") from exc
    return {
        "schema_version": "1.0",
        "command": "bounty.export",
        "status": "exported-locally",
        "candidate_id": candidate_id,
        "report_sha256": report_sha256,
        "approval_sha256": approval["approval_sha256"],
        "output_directory": str(destination),
        "files": sorted((*artifacts, "SHA256SUMS")),
        "network_action": False,
        "submitted": False,
    }


def load_report_input(
    path: Path | str,
    *,
    private_paths: tuple[Path | str, ...] = (),
) -> dict[str, object]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise BountyReportError(f"report input is not a regular file: {source}")
    try:
        if source.stat().st_size > MAX_REPORT_INPUT_BYTES:
            raise BountyReportError(
                f"report input exceeds {MAX_REPORT_INPUT_BYTES} bytes"
            )
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BountyReportError(f"could not read report input: {exc}") from exc
    if not isinstance(payload, dict):
        raise BountyReportError("report input root must be an object")
    unknown = set(payload) - REPORT_INPUT_KEYS
    missing = REPORT_INPUT_KEYS - set(payload)
    if unknown:
        raise BountyReportError(
            "unknown report input field: " + ", ".join(sorted(unknown))
        )
    if missing:
        raise BountyReportError(
            "missing report input field: " + ", ".join(sorted(missing))
        )
    result: dict[str, object] = {
        "summary": _text(payload["summary"], "summary", private_paths=private_paths),
        "technical_details": _text(
            payload["technical_details"], "technical_details", private_paths=private_paths
        ),
        "preconditions": _text_list(
            payload["preconditions"], "preconditions", nonempty=True, private_paths=private_paths
        ),
        "reproduction_steps": _text_list(
            payload["reproduction_steps"],
            "reproduction_steps",
            nonempty=True,
            private_paths=private_paths,
        ),
        "remediation": _text(
            payload["remediation"], "remediation", private_paths=private_paths
        ),
        "limitations": _text_list(
            payload["limitations"], "limitations", nonempty=True, private_paths=private_paths
        ),
        "unresolved_questions": _text_list(
            payload["unresolved_questions"],
            "unresolved_questions",
            nonempty=False,
            private_paths=private_paths,
        ),
        "duplicate_check": _text(
            payload["duplicate_check"], "duplicate_check", private_paths=private_paths
        ),
        "proof_status_explanation": _text(
            payload["proof_status_explanation"],
            "proof_status_explanation",
            private_paths=private_paths,
        ),
        "program_rules_rechecked_on": _review_date(
            payload["program_rules_rechecked_on"]
        ),
    }
    return result


def load_bounty_report(
    context: CandidateContext,
    report_sha256: str,
    *,
    allow_post_approval_review: bool = False,
) -> dict[str, object]:
    _digest(report_sha256, "report SHA-256")
    path = _report_directory(context, report_sha256) / PRIVATE_REPORT_JSON
    try:
        report = load_private_json(path)
    except BountyWorkspaceError as exc:
        raise BountyReportError(str(exc)) from exc
    _validate_self_digest(report, "report_sha256", "bounty report")
    expected = {
        "candidate_id": context.candidate["candidate_id"],
        "profile_sha256": context.profile.digest,
        "source_manifest_sha256": context.source_manifest["manifest_sha256"],
        "candidates_sha256": context.candidates_record["candidates_sha256"],
    }
    for field, value in expected.items():
        if report.get(field) != value:
            raise BountyReportError(f"report {field} is stale or mismatched")
    if report.get("report_sha256") != report_sha256:
        raise BountyReportError("report directory does not match report digest")
    current_reviews = context.reviews_record.get("reviews_sha256")
    if not allow_post_approval_review and report.get("reviews_sha256") != current_reviews:
        raise BountyReportError("report is stale because human review state changed")
    return report


def _install_report(context: CandidateContext, payload: dict[str, object]) -> None:
    destination = _report_directory(context, str(payload["report_sha256"]))
    if destination.exists():
        existing = load_bounty_report(context, str(payload["report_sha256"]))
        if existing != payload:
            raise BountyReportError("existing report differs from requested report")
        return
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        parent.chmod(0o700)
    temporary = Path(tempfile.mkdtemp(prefix=".report-", dir=parent))
    try:
        if os.name == "posix":
            temporary.chmod(0o700)
        write_private_json_new_or_identical(
            temporary / PRIVATE_REPORT_JSON, payload
        )
        markdown_path = temporary / PRIVATE_REPORT_MARKDOWN
        markdown_path.write_text(_render_report_markdown(payload), encoding="utf-8")
        if os.name == "posix":
            markdown_path.chmod(0o600)
        temporary.rename(destination)
    except (OSError, BountyWorkspaceError) as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        raise BountyReportError(f"could not install private report: {exc}") from exc


def _report_checklist(
    content: dict[str, object],
    *,
    state: str,
    impact: object,
    proof_manifest: dict[str, object] | None,
    proof_result: dict[str, object] | None,
) -> dict[str, bool]:
    proof_addressed = bool(content.get("proof_status_explanation"))
    if proof_result is not None and proof_result.get("status") == "passed":
        proof_addressed = True
    return {
        "human_confirmed": state == "confirmed",
        "in_scope_impact_recorded": isinstance(impact, str) and bool(impact.strip()),
        "summary_complete": bool(content.get("summary")),
        "technical_details_complete": bool(content.get("technical_details")),
        "preconditions_complete": bool(content.get("preconditions")),
        "reproduction_complete": bool(content.get("reproduction_steps")),
        "remediation_complete": bool(content.get("remediation")),
        "limitations_complete": bool(content.get("limitations")),
        "duplicate_check_recorded": bool(content.get("duplicate_check")),
        "program_rules_rechecked": bool(content.get("program_rules_rechecked_on")),
        "proof_status_addressed": proof_addressed,
    }


def _default_draft_content(finding: dict[str, object]) -> dict[str, object]:
    return {
        "summary": str(finding.get("message") or finding.get("title") or ""),
        "technical_details": str(finding.get("message") or ""),
        "preconditions": [],
        "reproduction_steps": [],
        "remediation": str(finding.get("recommendation") or ""),
        "limitations": ["Static scanner observation requires manual validation."],
        "unresolved_questions": [
            "Is the path reachable in the deployed target?",
            "Is the issue already known or duplicated?",
        ],
        "duplicate_check": "",
        "proof_status_explanation": "",
        "program_rules_rechecked_on": None,
    }


def _render_report_markdown(report: dict[str, object]) -> str:
    target = report["target"]
    finding = report["finding"]
    review = report["review"]
    content = report["content"]
    proof = report["proof"]
    assert isinstance(target, dict)
    assert isinstance(finding, dict)
    assert isinstance(review, dict)
    assert isinstance(content, dict)
    assert isinstance(proof, dict)
    lines = [
        f"# {finding['title']}",
        "",
        f"Status: **{report['status']}**  ",
        f"Classification: **{report['classification']}**  ",
        f"Candidate: `{report['candidate_id']}`  ",
        f"Report SHA-256: `{report['report_sha256']}`",
        "",
        "## Target and scope",
        "",
        f"- Program: {target['program']}",
        f"- Platform: {target['platform']}",
        f"- Rules: {target['rules_url']}",
        f"- Rules rechecked: {target['program_rules_rechecked_on']}",
        f"- Location: `{finding['path']}:{finding['line']}:{finding['column']}`",
        f"- Rule: `{finding['rule_id']}` ({finding['severity']}, {finding['confidence']} confidence)",
        f"- Human review state: {review['state']}",
        f"- In-scope impact: {review['impact']}",
        "",
        "## Summary",
        "",
        str(content["summary"]),
        "",
        "## Technical details",
        "",
        str(content["technical_details"]),
        "",
        "## Preconditions",
        "",
        *_markdown_list(content["preconditions"]),
        "",
        "## Reproduction",
        "",
        *_markdown_numbered(content["reproduction_steps"]),
        "",
        "## Proof status",
        "",
        f"- Generator: {proof['generator_status']}",
        f"- Execution: {proof['execution_status']}",
        f"- Reviewer explanation: {content['proof_status_explanation']}",
        "",
        "## Remediation",
        "",
        str(content["remediation"]),
        "",
        "## Limitations",
        "",
        *_markdown_list([*report["limitations"], *content["limitations"]]),
        "",
        "## Unresolved questions",
        "",
        *_markdown_list(content["unresolved_questions"]),
        "",
        "## Duplicate check",
        "",
        str(content["duplicate_check"]),
        "",
    ]
    return "\n".join(lines)


def _shareable_payload(report: dict[str, object]) -> dict[str, object]:
    allowed = {
        key: report[key]
        for key in (
            "schema_version",
            "candidate_id",
            "status",
            "classification",
            "created_at",
            "profile_sha256",
            "source_manifest_sha256",
            "report_sha256",
            "target",
            "finding",
            "review",
            "content",
            "proof",
            "completeness",
            "limitations",
        )
    }
    return _redact_payload(allowed, private_paths=())


def _redact_payload(value: object, *, private_paths: tuple[Path | str, ...]) -> object:
    if isinstance(value, str):
        return redact_sensitive_text(value, private_paths=private_paths)
    if isinstance(value, list):
        return [_redact_payload(item, private_paths=private_paths) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _redact_payload(item, private_paths=private_paths)
            for key, item in value.items()
        }
    return value


def _load_approval(
    context: CandidateContext, report_sha256: str
) -> dict[str, object]:
    path = _approval_directory(context, report_sha256) / APPROVAL_FILENAME
    try:
        approval = load_private_json(path)
    except BountyWorkspaceError as exc:
        raise BountyReportError(str(exc)) from exc
    _validate_self_digest(approval, "approval_sha256", "approval record")
    expected = {
        "candidate_id": context.candidate["candidate_id"],
        "report_sha256": report_sha256,
        "profile_sha256": context.profile.digest,
        "source_manifest_sha256": context.source_manifest["manifest_sha256"],
        "candidates_sha256": context.candidates_record["candidates_sha256"],
    }
    for field, value in expected.items():
        if approval.get(field) != value:
            raise BountyReportError(f"approval {field} is stale or mismatched")
    return approval


def _revalidate_source(context: CandidateContext) -> None:
    try:
        identity = validate_profile_source(context.profile)
    except BountyScopeError as exc:
        raise BountyReportError(str(exc)) from exc
    if identity.source_set_sha256 != context.source_manifest.get("source_set_sha256"):
        raise BountyReportError("current source identity does not match source manifest")


def _context(workspace: Path | str, candidate_id: str) -> CandidateContext:
    try:
        return load_candidate_context(workspace, candidate_id)
    except BountyCandidateError as exc:
        raise BountyReportError(str(exc)) from exc


def _finding_payload(context: CandidateContext) -> dict[str, object]:
    observation = context.candidate.get("observation")
    finding = observation.get("finding") if isinstance(observation, dict) else None
    if not isinstance(finding, dict):
        raise BountyReportError("candidate contains no finding observation")
    return finding


def _report_directory(context: CandidateContext, report_sha256: str) -> Path:
    return (
        context.profile.workspace
        / REPORTS_ROOT
        / str(context.candidate["candidate_id"])
        / report_sha256
    )


def _approval_directory(context: CandidateContext, report_sha256: str) -> Path:
    return (
        context.profile.workspace
        / APPROVALS_ROOT
        / str(context.candidate["candidate_id"])
        / report_sha256
    )


def _validate_self_digest(payload: dict[str, object], field: str, label: str) -> None:
    supplied = payload.get(field)
    material = dict(payload)
    material.pop(field, None)
    if not isinstance(supplied, str) or supplied != payload_sha256(material):
        raise BountyReportError(f"{label} integrity digest does not match")


def _digest(value: str, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise BountyReportError(f"{label} is invalid")
    return value


def _review_date(value: object) -> str:
    if not isinstance(value, str):
        raise BountyReportError("program_rules_rechecked_on must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise BountyReportError("program_rules_rechecked_on must be YYYY-MM-DD") from exc
    if parsed > date.today():
        raise BountyReportError("program_rules_rechecked_on must not be in the future")
    return parsed.isoformat()


def _timestamp(
    supplied: str | None, *, now: Callable[[], datetime] | None
) -> str:
    if supplied is None:
        instant = (now or (lambda: datetime.now(timezone.utc)))()
    else:
        try:
            instant = datetime.fromisoformat(supplied.replace("Z", "+00:00"))
        except ValueError as exc:
            raise BountyReportError("event time must be RFC 3339") from exc
    if instant.tzinfo is None:
        raise BountyReportError("event time must include a timezone")
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(
    value: object,
    label: str,
    *,
    private_paths: tuple[Path | str, ...] = (),
) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BountyReportError(f"{label} must be a non-empty string")
    if len(value) > 100_000:
        raise BountyReportError(f"{label} is too long")
    if redact_sensitive_text(value, private_paths=private_paths) != value:
        raise BountyReportError(f"{label} contains a secret or private local path")
    return value


def _text_list(
    value: object,
    label: str,
    *,
    nonempty: bool,
    private_paths: tuple[Path | str, ...],
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise BountyReportError(f"{label} must be a {qualifier}array")
    if len(value) > 100:
        raise BountyReportError(f"{label} contains too many entries")
    return [
        _text(item, f"{label} entry", private_paths=private_paths) for item in value
    ]


def _nested(
    value: dict[str, object] | None, table: str, field: str
) -> object:
    nested = value.get(table) if isinstance(value, dict) else None
    return nested.get(field) if isinstance(nested, dict) else None


def _markdown_list(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["- None recorded."]
    return [f"- {item}" for item in value]


def _markdown_numbered(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["1. No reproduction steps recorded."]
    return [f"{index}. {item}" for index, item in enumerate(value, 1)]


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
