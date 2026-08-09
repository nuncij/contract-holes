from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Callable, Sequence

from .bounty_io import (
    BountyWorkspaceError,
    load_private_json,
    payload_sha256,
    replace_managed_private_json,
)
from .bounty_profile import BountyProfile, BountyProfileError, load_bounty_profile
from .bounty_scope import SCAN_RECORD_FILENAME, SOURCE_MANIFEST_FILENAME


class BountyCandidateError(RuntimeError):
    pass


CANDIDATES_FILENAME = "candidates.json"
REVIEWS_FILENAME = "reviews.json"
CANDIDATE_SCHEMA_VERSION = "1.0"
REVIEW_SCHEMA_VERSION = "1.0"
REVIEW_STATES = frozenset(
    {"new", "investigating", "rejected", "confirmed", "approved"}
)
_TRANSITIONS = {
    "new": frozenset({"investigating", "rejected"}),
    "investigating": frozenset({"rejected", "confirmed"}),
    "rejected": frozenset({"investigating"}),
    "confirmed": frozenset({"investigating", "rejected", "approved"}),
    "approved": frozenset(),
}
_SEVERITY_POINTS = {
    "critical": 50,
    "high": 40,
    "medium": 25,
    "low": 10,
    "info": 0,
}
_CONFIDENCE_POINTS = {"high": 20, "medium": 10, "low": 0}


@dataclass(frozen=True, slots=True)
class CandidateContext:
    profile: BountyProfile
    candidate: dict[str, object]
    review: dict[str, object] | None
    candidates_record: dict[str, object]
    reviews_record: dict[str, object]
    source_manifest: dict[str, object]
    scan_record: dict[str, object]


def synchronize_candidates(workspace: Path | str) -> dict[str, object]:
    profile, scan, source_manifest = _workspace_inputs(workspace)
    report = scan.get("report")
    findings = report.get("findings") if isinstance(report, dict) else None
    if not isinstance(findings, list):
        raise BountyCandidateError("scan record contains no findings array")
    scan_digest = _required_digest(scan, "scan_sha256", "scan record")
    source_digest = _required_digest(
        source_manifest, "manifest_sha256", "source manifest"
    )
    path = profile.workspace / CANDIDATES_FILENAME
    existing_payload, existing_bytes_digest = _load_candidates_if_present(
        path, profile.digest, source_digest
    )
    existing = {
        str(candidate["candidate_id"]): candidate
        for candidate in existing_payload.get("candidates", [])
        if isinstance(candidate, dict) and isinstance(candidate.get("candidate_id"), str)
    }
    active_ids: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise BountyCandidateError("scan finding must be an object")
        candidate_id = candidate_identifier(
            profile.digest,
            source_digest,
            str(scan.get("scanner_version", "")),
            finding,
        )
        active_ids.add(candidate_id)
        observation = _observation(finding)
        current = existing.get(candidate_id)
        if current is None:
            existing[candidate_id] = {
                "candidate_id": candidate_id,
                "observation": observation,
                "first_seen_scan_sha256": scan_digest,
                "last_seen_scan_sha256": scan_digest,
                "active": True,
            }
            continue
        if current.get("observation") != observation:
            raise BountyCandidateError(
                f"candidate observation changed for stable ID {candidate_id}"
            )
        current["last_seen_scan_sha256"] = scan_digest
        current["active"] = True
    for candidate_id, candidate in existing.items():
        if candidate_id not in active_ids:
            candidate["active"] = False
    candidates = sorted(existing.values(), key=lambda item: str(item["candidate_id"]))
    payload: dict[str, object] = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "profile_sha256": profile.digest,
        "source_manifest_sha256": source_digest,
        "latest_scan_sha256": scan_digest,
        "candidates": candidates,
    }
    payload["candidates_sha256"] = payload_sha256(payload)
    try:
        replace_managed_private_json(
            path,
            payload,
            expected_existing_sha256=existing_bytes_digest,
        )
    except BountyWorkspaceError as exc:
        raise BountyCandidateError(str(exc)) from exc
    return payload


def list_candidates(
    workspace: Path | str,
    *,
    states: Sequence[str] = (),
) -> dict[str, object]:
    profile, _, source_manifest = _workspace_inputs(workspace)
    source_digest = _required_digest(
        source_manifest, "manifest_sha256", "source manifest"
    )
    candidates, _ = _load_candidates_if_present(
        profile.workspace / CANDIDATES_FILENAME,
        profile.digest,
        source_digest,
        required=True,
    )
    reviews, _ = _load_reviews_if_present(
        profile.workspace / REVIEWS_FILENAME,
        profile.digest,
        source_digest,
    )
    review_by_id = {
        str(review["candidate_id"]): review
        for review in reviews.get("reviews", [])
        if isinstance(review, dict) and isinstance(review.get("candidate_id"), str)
    }
    selected_states = set(states)
    unknown = selected_states - REVIEW_STATES
    if unknown:
        raise BountyCandidateError(
            "unknown candidate state: " + ", ".join(sorted(unknown))
        )
    combined: list[dict[str, object]] = []
    for candidate in candidates["candidates"]:
        assert isinstance(candidate, dict)
        candidate_id = str(candidate["candidate_id"])
        review = review_by_id.get(candidate_id)
        state = str(review.get("state")) if review else "new"
        if selected_states and state not in selected_states:
            continue
        priority = candidate_review_priority(candidate)
        combined.append(
            {
                **candidate,
                "state": state,
                "review": review,
                "review_priority": priority,
            }
        )
    combined.sort(
        key=lambda item: (
            -int(item["review_priority"]["score"]),
            str(item["candidate_id"]),
        )
    )
    return {
        "schema_version": "1.0",
        "command": "bounty.candidates",
        "status": "completed",
        "profile_sha256": profile.digest,
        "source_manifest_sha256": source_digest,
        "program_impacts": list(profile.impacts),
        "candidate_count": len(combined),
        "candidates": combined,
    }


def load_candidate_context(
    workspace: Path | str, candidate_id: str
) -> CandidateContext:
    profile, scan, source_manifest = _workspace_inputs(workspace)
    source_digest = _required_digest(
        source_manifest, "manifest_sha256", "source manifest"
    )
    candidates, _ = _load_candidates_if_present(
        profile.workspace / CANDIDATES_FILENAME,
        profile.digest,
        source_digest,
        required=True,
    )
    candidate = next(
        (
            item
            for item in candidates["candidates"]
            if isinstance(item, dict) and item.get("candidate_id") == candidate_id
        ),
        None,
    )
    if candidate is None:
        raise BountyCandidateError(f"unknown candidate ID: {candidate_id}")
    reviews, _ = _load_reviews_if_present(
        profile.workspace / REVIEWS_FILENAME,
        profile.digest,
        source_digest,
    )
    review = next(
        (
            item
            for item in reviews["reviews"]
            if isinstance(item, dict) and item.get("candidate_id") == candidate_id
        ),
        None,
    )
    return CandidateContext(
        profile=profile,
        candidate=candidate,
        review=review,
        candidates_record=candidates,
        reviews_record=reviews,
        source_manifest=source_manifest,
        scan_record=scan,
    )


def review_candidate(
    workspace: Path | str,
    candidate_id: str,
    *,
    state: str,
    reason: str,
    reviewer: str,
    impact: str | None = None,
    occurred_at: str | None = None,
    allow_approval: bool = False,
    now: Callable[[], datetime] | None = None,
) -> dict[str, object]:
    profile, _, source_manifest = _workspace_inputs(workspace)
    source_digest = _required_digest(
        source_manifest, "manifest_sha256", "source manifest"
    )
    candidates, _ = _load_candidates_if_present(
        profile.workspace / CANDIDATES_FILENAME,
        profile.digest,
        source_digest,
        required=True,
    )
    candidate_ids = {
        str(candidate["candidate_id"])
        for candidate in candidates["candidates"]
        if isinstance(candidate, dict)
    }
    if candidate_id not in candidate_ids:
        raise BountyCandidateError(f"unknown candidate ID: {candidate_id}")
    if state not in REVIEW_STATES:
        raise BountyCandidateError(f"unknown candidate state: {state}")
    if state == "new":
        raise BountyCandidateError("review transitions cannot set state back to new")
    if state == "approved" and not allow_approval:
        raise BountyCandidateError(
            "approved requires the report approval workflow, not bounty review"
        )
    reason = _review_text(reason, "reason")
    reviewer = _review_text(reviewer, "reviewer")
    impact = _optional_review_text(impact, "impact")
    if state == "confirmed" and impact is None:
        raise BountyCandidateError("confirmed requires a non-empty impact statement")
    timestamp = _timestamp(occurred_at, now=now)
    path = profile.workspace / REVIEWS_FILENAME
    payload, existing_bytes_digest = _load_reviews_if_present(
        path, profile.digest, source_digest
    )
    reviews = {
        str(review["candidate_id"]): review
        for review in payload.get("reviews", [])
        if isinstance(review, dict) and isinstance(review.get("candidate_id"), str)
    }
    current = reviews.get(candidate_id)
    current_state = str(current.get("state")) if current else "new"
    if state not in _TRANSITIONS[current_state]:
        raise BountyCandidateError(
            f"invalid candidate state transition: {current_state} -> {state}"
        )
    event: dict[str, object] = {
        "from": current_state,
        "to": state,
        "reason": reason,
        "reviewer": reviewer,
        "occurred_at": timestamp,
        **({"impact": impact} if impact is not None else {}),
    }
    history = list(current.get("history", [])) if current else []
    if history and str(history[-1].get("occurred_at", "")) >= timestamp:
        raise BountyCandidateError(
            "review event occurred_at must be later than the previous event"
        )
    history.append(event)
    reviews[candidate_id] = {
        "candidate_id": candidate_id,
        "state": state,
        "reason": reason,
        "reviewer": reviewer,
        "updated_at": timestamp,
        "impact": impact,
        "history": history,
    }
    result: dict[str, object] = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "profile_sha256": profile.digest,
        "source_manifest_sha256": source_digest,
        "reviews": sorted(reviews.values(), key=lambda item: str(item["candidate_id"])),
    }
    result["reviews_sha256"] = payload_sha256(result)
    try:
        replace_managed_private_json(
            path,
            result,
            expected_existing_sha256=existing_bytes_digest,
        )
    except BountyWorkspaceError as exc:
        raise BountyCandidateError(str(exc)) from exc
    return reviews[candidate_id]


def candidate_identifier(
    profile_sha256: str,
    source_manifest_sha256: str,
    scanner_version: str,
    finding: dict[str, object],
) -> str:
    rule_id = finding.get("rule_id")
    fingerprint = finding.get("fingerprint")
    if not isinstance(rule_id, str) or not isinstance(fingerprint, str):
        raise BountyCandidateError("finding lacks rule_id or fingerprint")
    material = "\0".join(
        (
            "contract-holes-candidate-v1",
            profile_sha256,
            source_manifest_sha256,
            scanner_version,
            rule_id,
            fingerprint,
        )
    )
    return "BNT-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def candidate_review_priority(candidate: dict[str, object]) -> dict[str, object]:
    observation = candidate.get("observation")
    finding = observation.get("finding") if isinstance(observation, dict) else None
    if not isinstance(finding, dict):
        raise BountyCandidateError("candidate contains no finding observation")
    severity = str(finding.get("severity", ""))
    confidence = str(finding.get("confidence", ""))
    if severity not in _SEVERITY_POINTS or confidence not in _CONFIDENCE_POINTS:
        raise BountyCandidateError("candidate severity or confidence is invalid")
    score = _SEVERITY_POINTS[severity] + _CONFIDENCE_POINTS[confidence]
    reasons = [f"severity:{severity}", f"confidence:{confidence}"]
    components: dict[str, int] = {
        "severity": _SEVERITY_POINTS[severity],
        "confidence": _CONFIDENCE_POINTS[confidence],
        "evidence": 0,
        "reachability": 0,
        "proof_support": 0,
    }
    metadata = finding.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    evidence = metadata.get("evidence")
    if isinstance(evidence, str) and evidence:
        components["evidence"] += 10
        score += 10
        reasons.append("evidence:labelled")
        if "compiler" in evidence:
            components["evidence"] += 5
            score += 5
            reasons.append("evidence:compiler")
    trace = metadata.get("trace")
    if isinstance(trace, list) and trace:
        components["evidence"] += 5
        components["reachability"] += 5
        score += 10
        reasons.extend(("evidence:trace", "reachability:trace"))
    if isinstance(metadata.get("entry_function"), str):
        components["reachability"] += 5
        score += 5
        reasons.append("reachability:entry-function")
    if finding.get("rule_id") in {"SOL005", "SOL007"}:
        components["proof_support"] += 5
        score += 5
        reasons.append("proof:generator-available")
    score = min(score, 100)
    label = "highest" if score >= 80 else "high" if score >= 60 else "normal" if score >= 35 else "low"
    return {
        "score": score,
        "label": label,
        "components": components,
        "reason_codes": reasons,
        "meaning": "review ordering only; not exploitability, bounty severity, or payout",
    }


def _workspace_inputs(
    workspace: Path | str,
) -> tuple[object, dict[str, object], dict[str, object]]:
    try:
        profile = load_bounty_profile(workspace)
        scan = load_private_json(profile.workspace / SCAN_RECORD_FILENAME)
        source = load_private_json(profile.workspace / SOURCE_MANIFEST_FILENAME)
    except (BountyProfileError, BountyWorkspaceError) as exc:
        raise BountyCandidateError(str(exc)) from exc
    _validate_self_digest(scan, "scan_sha256", "scan record")
    _validate_self_digest(source, "manifest_sha256", "source manifest")
    if scan.get("profile_sha256") != profile.digest or source.get("profile_sha256") != profile.digest:
        raise BountyCandidateError("workspace records do not match bounty profile")
    if scan.get("source_manifest_sha256") != source.get("manifest_sha256"):
        raise BountyCandidateError("scan record does not match source manifest")
    return profile, scan, source


def _load_candidates_if_present(
    path: Path,
    profile_digest: str,
    source_digest: str,
    *,
    required: bool = False,
) -> tuple[dict[str, object], str | None]:
    if not path.exists():
        if required:
            raise BountyCandidateError("candidate record does not exist; run bounty scan")
        return {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "profile_sha256": profile_digest,
            "source_manifest_sha256": source_digest,
            "candidates": [],
        }, None
    try:
        raw = path.read_bytes()
        payload = load_private_json(path)
    except (OSError, BountyWorkspaceError) as exc:
        raise BountyCandidateError(str(exc)) from exc
    _validate_self_digest(payload, "candidates_sha256", "candidate record")
    if payload.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        raise BountyCandidateError("unsupported candidate record schema")
    if payload.get("profile_sha256") != profile_digest or payload.get("source_manifest_sha256") != source_digest:
        raise BountyCandidateError("candidate record does not match workspace identity")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise BountyCandidateError("candidate record candidates must be an array")
    return payload, hashlib.sha256(raw).hexdigest()


def _load_reviews_if_present(
    path: Path,
    profile_digest: str,
    source_digest: str,
) -> tuple[dict[str, object], str | None]:
    if not path.exists():
        return {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "profile_sha256": profile_digest,
            "source_manifest_sha256": source_digest,
            "reviews": [],
        }, None
    try:
        raw = path.read_bytes()
        payload = load_private_json(path)
    except (OSError, BountyWorkspaceError) as exc:
        raise BountyCandidateError(str(exc)) from exc
    _validate_self_digest(payload, "reviews_sha256", "review record")
    if payload.get("schema_version") != REVIEW_SCHEMA_VERSION:
        raise BountyCandidateError("unsupported review record schema")
    if payload.get("profile_sha256") != profile_digest or payload.get("source_manifest_sha256") != source_digest:
        raise BountyCandidateError("review record does not match workspace identity")
    reviews = payload.get("reviews")
    if not isinstance(reviews, list):
        raise BountyCandidateError("review record reviews must be an array")
    return payload, hashlib.sha256(raw).hexdigest()


def _validate_self_digest(payload: dict[str, object], field: str, label: str) -> None:
    supplied = payload.get(field)
    if not isinstance(supplied, str):
        raise BountyCandidateError(f"{label} contains no {field}")
    material = dict(payload)
    material.pop(field, None)
    if supplied != payload_sha256(material):
        raise BountyCandidateError(f"{label} integrity digest does not match")


def _required_digest(payload: dict[str, object], field: str, label: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise BountyCandidateError(f"{label} contains no {field}")
    return value


def _observation(finding: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "finding": finding,
        "observation_sha256": payload_sha256(finding),
    }


def _review_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BountyCandidateError(f"review {label} must be a non-empty string")
    if len(value) > 10_000:
        raise BountyCandidateError(f"review {label} is too long")
    return value


def _optional_review_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _review_text(value, label)


def _timestamp(
    supplied: str | None, *, now: Callable[[], datetime] | None
) -> str:
    if supplied is None:
        instant = (now or (lambda: datetime.now(timezone.utc)))()
    else:
        try:
            instant = datetime.fromisoformat(supplied.replace("Z", "+00:00"))
        except ValueError as exc:
            raise BountyCandidateError("review occurred_at must be RFC 3339") from exc
    if instant.tzinfo is None:
        raise BountyCandidateError("review occurred_at must include a timezone")
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
